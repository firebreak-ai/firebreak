"""testplan.py: the test files are the plan (trial variant, pytest projects).

A change is planned as pytest tests carrying `@pytest.mark.planned(...)`. This tool reads those marks,
prints the plan the operator approves, locks the tests, and switches planned tests on one at a time.
When a plan finishes, each planned mark becomes `@pytest.mark.acceptance(rule=...)`: the lasting label of a
behavioural acceptance test, which later plans leave alone.
State lives in `.fbk/testplan/` at the project root. Standard library only.
"""

import argparse
import ast
import datetime
import hashlib
import json
import pathlib
import re
import shlex
import subprocess
import sys

STATE_DIR = ".fbk/testplan"
ACTIONS = ("add", "change", "remove", "protect")
STEPPED = ("add", "change")  # switched off until the implementer reaches them
FIELDS = ("action", "rule", "source", "owner", "new_owner", "was", "reason", "skeleton")
BEGIN, END = "# --- fbk-testplan: begin (managed block) ---", "# --- fbk-testplan: end ---"
HOOKS = ("pytest_configure", "pytest_collection_modifyitems")
REGISTER = '''def pytest_configure(config):
    config.addinivalue_line(
        "markers", "planned(**plan): a test in the plan under way; its fields are the plan entry the operator approved")
    config.addinivalue_line(
        "markers", "acceptance(rule): behavioural acceptance test of the rule named, from a finished plan")
'''
SWITCH = '''

def pytest_collection_modifyitems(config, items):
    import json
    import os
    import pytest
    if os.environ.get("FBK_TESTPLAN_ALL"):  # run every test, switched on or not: for writing and reviewing test bodies
        return
    try:
        state = json.loads((config.rootpath / "%s" / "plan.json").read_text())
    except (OSError, ValueError):
        return
    on, approved = set(state.get("on", [])), bool(state.get("approved"))
    for item in items:
        mark = item.get_closest_marker("planned")
        if mark is None:
            continue
        action = mark.kwargs.get("action", "add")
        if action in ("add", "change") and item.nodeid.split("[")[0] not in on:
            item.add_marker(pytest.mark.skip(reason="planned: not switched on yet"))
        elif action == "remove" and approved:
            item.add_marker(pytest.mark.skip(reason="planned: marked for removal"))
''' % STATE_DIR


class Refused(Exception):
    """The command cannot go ahead; the message says what to do."""


# ---------- state ----------

def state_path(root):
    return root / STATE_DIR / "plan.json"  # not state.json: the runtime reads every .fbk/**/state.json as a unit


def load(root):
    try:
        return json.loads(state_path(root).read_text())
    except OSError:
        raise Refused(f"No plan here: run `testplan.py init --request <file>` in the project root ({root}).") from None


def save(root, state):
    path = state_path(root)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=1, sort_keys=True) + "\n")
    tmp.replace(path)


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def squash(text):
    return " ".join(text.split()).lower()


# ---------- reading the plan out of the test files ----------

def test_files(root, state):
    found = set()
    for pattern in state["tests"]:
        found.update(p for p in root.glob(pattern) if p.is_file() and ".fbk" not in p.parts)
    return sorted(found)


def _mark_call(decorator):
    if not isinstance(decorator, ast.Call):
        return None
    func = decorator.func
    if isinstance(func, ast.Attribute) and func.attr == "planned":
        return decorator
    return None


def _label(decorator):
    target = decorator.func if isinstance(decorator, ast.Call) else decorator
    return isinstance(target, ast.Attribute) and target.attr == "acceptance"


def label_finished(root, state):
    """Turn every planned mark into the lasting label `acceptance(rule=...)`, replacing a label the test already had."""
    for path in test_files(root, state):
        text = path.read_text()
        lines = text.splitlines(keepends=True)
        edits = []  # (first line, last line, replacement), 1-based and inclusive
        for node in ast.walk(ast.parse(text)):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            call = next(filter(None, map(_mark_call, node.decorator_list)), None)
            if call is None:
                continue
            rule = next((ast.literal_eval(k.value) for k in call.keywords if k.arg == "rule"), "")
            prefix = ast.get_source_segment(text, call.func).rsplit(".", 1)[0]
            indent = lines[call.lineno - 1][: call.col_offset - 1]
            edits.append((call.lineno, call.end_lineno, f"{indent}@{prefix}.acceptance(rule={json.dumps(rule, ensure_ascii=False)})\n"))
            edits.extend((d.lineno, d.end_lineno, "") for d in node.decorator_list if _label(d))
        if not edits:
            continue
        for first, last, replacement in sorted(edits, reverse=True):
            lines[first - 1:last] = [replacement] if replacement else []
        relabelled = "".join(lines)
        ast.parse(relabelled)
        path.write_text(relabelled)


def _entries(path, relative, problems):
    try:
        tree = ast.parse(path.read_text())
    except (SyntaxError, UnicodeDecodeError) as error:
        problems.append(f"{relative}: cannot be read as Python ({error})")
        return
    def walk(node, prefix):
        for child in node.body:
            if isinstance(child, ast.ClassDef):
                yield from walk(child, prefix + [child.name])
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                call = next(filter(None, map(_mark_call, child.decorator_list)), None)
                if call is None:
                    continue
                name = "::".join([relative, *prefix, child.name])
                entry = {"id": name, "line": child.lineno, "doc": " ".join((ast.get_docstring(child) or "").split())}
                if call.args:
                    problems.append(f"{name}: the planned mark takes named fields only")
                for keyword in call.keywords:
                    try:
                        value = ast.literal_eval(keyword.value)
                    except ValueError:
                        problems.append(f"{name}: field `{keyword.arg}` must be a plain literal so the plan can be printed")
                        continue
                    if keyword.arg not in FIELDS:
                        problems.append(f"{name}: unknown field `{keyword.arg}` (fields: {', '.join(FIELDS)})")
                    else:
                        entry[keyword.arg] = value
                entry.setdefault("action", "add")
                yield entry
    yield from walk(tree, [])


def read_plan(root, state):
    """Every marked test, in file then line order, and the problems that keep the plan from being approved."""
    problems, entries = [], []
    for path in test_files(root, state):
        entries.extend(_entries(path, path.relative_to(root).as_posix(), problems))
    request = squash((root / STATE_DIR / "request.md").read_text())
    for entry in entries:
        problems.extend(f"{entry['id']}: {text}" for text in _entry_problems(entry, request, state))
    return entries, problems


def _entry_problems(entry, request, state):
    action = entry["action"]
    if action not in ACTIONS:
        yield f"action must be one of {', '.join(ACTIONS)}"
        return
    for field in ("rule", "source", "owner", "new_owner", "was", "reason"):
        if field in entry and not (isinstance(entry[field], str) and entry[field].strip()):
            yield f"field `{field}` must be non-empty text"
            return
    if not entry.get("rule"):
        yield "needs `rule`: the rule this test belongs to, in plain words"
    if not entry["doc"]:
        yield "needs a docstring: the example in plain words with its concrete values"
    if action != "remove" and not entry.get("owner"):
        yield "needs `owner`: the function or module the test goes through"
    if action in ("change", "remove") and not entry.get("reason"):
        yield "needs `reason`: why the existing test no longer holds"
    if action == "change" and not entry.get("was"):
        yield "needs `was`: what the test says today, in plain words"
    if action == "protect":
        if "source" in entry:
            yield "a protective test takes no `source`: it guards behaviour that already exists"
        return
    source = entry.get("source", "")
    kind, _, body = source.partition(":")
    body = body.strip()
    if kind == "request" and body:
        if squash(body) not in request:
            yield "its `source` quotes words that are not in the request; quote the request exactly"
    elif kind == "answer" and body.isdigit():
        if not 1 <= int(body) <= len(state["answers"]):
            yield f"its `source` names answer {body}, which is not recorded (see `testplan.py answer`)"
    else:
        yield "needs `source`: `request: <exact words from the request>` or `answer: <number>`"


def fingerprint(entries, *, without_removed=False):
    rows = [
        [e["id"], e["doc"], *[e.get(f) for f in FIELDS]]
        for e in entries if not (without_removed and e["action"] == "remove")
    ]
    return hashlib.sha256(json.dumps(sorted(rows, key=lambda r: r[0])).encode()).hexdigest()


def file_hashes(root, state):
    paths = [*test_files(root, state), root / "conftest.py"]
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}


# ---------- tasks ----------

def tasks(entries):
    """Stepped tests grouped by owner, in the order each owner first appears; skeleton tests form the first task."""
    groups = {}
    for entry in entries:
        if entry["action"] in STEPPED:
            key = (not entry.get("skeleton"), entry["owner"] if not entry.get("skeleton") else "")
            groups.setdefault(key, []).append(entry)
    ordered = sorted(groups.items(), key=lambda item: item[0][0])
    return [{"number": n, "owner": tests[0]["owner"], "tests": tests} for n, (_, tests) in enumerate(ordered, 1)]


def find_task(entries, number):
    for task in tasks(entries):
        if task["number"] == number:
            return task
    raise Refused(f"No task {number}; `testplan.py tasks` lists them.")


# ---------- checks ----------

def run(root, state, extra=()):
    done = subprocess.run([*state["check"], *extra], cwd=root, capture_output=True, text=True, check=False)
    return done.returncode, (done.stdout + done.stderr)[-3000:]


def require_green(root, state, when, only=()):
    """The whole suite must pass, or just the test files in `only` when a step is checked."""
    code, output = run(root, state, only)
    if code != 0:
        what = "The task's test files" if only else "The suite"
        raise Refused(f"{what} must pass {when}; `{shlex.join([*state['check'], *only])}` exited {code}:\n{output}")


FINDING = re.compile(r"^(\S.*?):\d+:\d+: ([A-Z]+\d+)\b")


def lint_findings(root, state):
    """Each finding line of the lint command, keyed by (file, rule); the command prints `path:line:col: RULE message`."""
    done = subprocess.run(state["lint"], cwd=root, capture_output=True, text=True, check=False)
    found = {}
    for line in done.stdout.splitlines():
        match = FINDING.match(line)
        if match:
            found.setdefault("::".join(match.groups()), []).append(line)
    return found


def require_no_new_findings(root, state):
    if not state.get("lint"):
        return
    found = lint_findings(root, state)
    before, total = state["lint_start"], sum(map(len, found.values()))
    if total <= sum(before.values()):
        return
    risen = [line for key, lines in sorted(found.items()) if len(lines) > before.get(key, 0) for line in lines]
    raise Refused(
        f"The linter reports {total} findings against {sum(before.values())} when the plan started. A step leaves no more "
        "findings than the plan began with: fix what this work added by restructuring the code, not by silencing the "
        "rule. Findings in the files and rules that rose:\n" + "\n".join(risen[:40])
    )


def require_plan_unchanged(root, state, entries, problems):
    if problems:
        raise Refused("The plan no longer reads cleanly:\n" + "\n".join(f"- {p}" for p in problems))
    if not state.get("approved"):
        raise Refused("The operator has not approved the plan (`testplan.py plan`, then `approve`).")
    if fingerprint(entries) != state["approved"]["fingerprint"]:
        raise Refused(
            "The plan differs from the one the operator approved: a test was added, dropped or renamed, or a "
            "mark or docstring changed. Restore it, or show the operator the new plan and run `approve` again."
        )


def require_lock(root, state):
    if state["bodies"] != "author" or state.get("removing"):
        return
    if not state.get("locked"):
        raise Refused("The tests are not locked yet: write and review the test bodies, then run `testplan.py lock`.")
    current = file_hashes(root, state)
    changed = sorted(p for p in set(current) | set(state["locked"]) if current.get(p) != state["locked"].get(p))
    if changed:
        raise Refused(
            "Locked test files changed: " + ", ".join(changed) + ". Restore them (for example with `git checkout`). "
            "A test that contradicts the request is reported to the lead, not edited."
        )


# ---------- the conftest block ----------

def write_block(root, body):
    path = root / "conftest.py"
    text = path.read_text() if path.exists() else ""
    outside = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?", "", text, flags=re.S)
    clash = [h for h in HOOKS if re.search(rf"^def {h}\b", outside, flags=re.M)]
    if clash:
        raise Refused(f"conftest.py already defines {', '.join(clash)}; merge the managed block's hooks by hand.")
    path.write_text(outside.rstrip("\n") + ("\n\n\n" if outside.strip() else "") + f"{BEGIN}\n{body}{END}\n")


# ---------- commands ----------

def cmd_init(root, args):
    folder = root / STATE_DIR
    if state_path(root).exists():
        raise Refused(f"A plan already exists in {folder}; `testplan.py finish` ends it.")
    request = pathlib.Path(args.request).read_text()
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "request.md").write_text(request)
    write_block(root, REGISTER + SWITCH)
    if args.session == "one" and args.bodies == "author":
        raise Refused("One session doing all the work writes each test body at its step: use `--bodies implementer`, or leave `--bodies` out.")
    state = {
        "bodies": "implementer" if args.session == "one" else (args.bodies or "author"), "session": args.session,
        "tidy": args.tidy or ("self" if args.session == "one" else "agent"),
        "tests": args.tests, "check": shlex.split(args.check),
        "answers": [], "parked": [], "on": [], "steps": [], "started": now(),
    }
    if args.lint:
        state["lint"] = shlex.split(args.lint)
        state["lint_start"] = {key: len(lines) for key, lines in lint_findings(root, state).items()}
    save(root, state)
    print(f"Plan started. The request is saved in {STATE_DIR}/request.md; conftest.py now skips planned tests until "
          "they are switched on.")


def cmd_answer(root, args):
    state = load(root)
    state["answers"].append({"question": args.question, "answer": args.answer})
    save(root, state)
    print(f"Recorded as answer {len(state['answers'])}; a test built on it uses source=\"answer: {len(state['answers'])}\".")


def cmd_park(root, args):
    state = load(root)
    state["parked"].append(args.title)
    save(root, state)
    print(f"Parked: {args.title}")


def render(state, entries):
    lines = ["# The plan", ""]
    count = lambda action: sum(e["action"] == action for e in entries)
    rules = list(dict.fromkeys(e.get("rule", "(no rule)") for e in entries if e["action"] != "protect"))
    lines.append(f"{len(rules)} rules; {count('add')} new tests, {count('change')} existing tests to change, "
                 f"{count('remove')} to remove, {count('protect')} protecting existing behaviour.")
    for rule in rules:
        lines += ["", f"## {rule}"]
        for entry in (e for e in entries if e.get("rule") == rule and e["action"] != "protect"):
            lines += _render_entry(state, entry)
    protect = [e for e in entries if e["action"] == "protect"]
    if protect:
        lines += ["", "## Protecting existing behaviour", "",
                  "These tests guard behaviour that already works and that this change puts at risk."]
        for entry in protect:
            lines += ["", f"- **{entry.get('rule', '')}:** {entry['doc']}", f"  - Goes through: `{entry.get('owner', '?')}`",
                      f"  - Test: `{entry['id']}`"]
    lines += ["", "## Your answers"]
    lines += [f"{n}. {a['question']} — **{a['answer']}**" for n, a in enumerate(state["answers"], 1)] or ["None asked."]
    lines += ["", "## Parked, not part of this change"]
    lines += [f"- {title}" for title in state["parked"]] or ["Nothing parked."]
    return "\n".join(lines)


def _render_entry(state, entry):
    label = {"add": "New test", "change": "Existing test to change", "remove": "Existing test to remove"}[entry["action"]]
    out = ["", f"- **{label}:** {entry['doc']}"]
    if entry["action"] == "change":
        out.append(f"  - Today it says: {entry.get('was', '?')}")
    if entry["action"] in ("change", "remove"):
        out.append(f"  - Why: {entry.get('reason', '?')}")
    if entry["action"] != "remove":
        owner = f"`{entry.get('owner', '?')}`"
        if entry.get("new_owner"):
            owner += f" (new; no existing owner fits because: {entry['new_owner']})"
        out.append(f"  - Goes through: {owner}")
    kind, _, body = entry.get("source", "").partition(":")
    body = body.strip()
    if kind == "answer" and body.isdigit() and 1 <= int(body) <= len(state["answers"]):
        out.append(f"  - From your answer {body}")
    elif kind == "request":
        out.append(f"  - From the request: \"{body}\"")
    out.append(f"  - Test: `{entry['id']}`")
    return out


def cmd_plan(root, args):
    state = load(root)
    entries, problems = read_plan(root, state)
    print(render(state, entries))
    if problems:
        raise Refused("The plan cannot be approved yet:\n" + "\n".join(f"- {p}" for p in problems))


def cmd_approve(root, args):
    state = load(root)
    entries, problems = read_plan(root, state)
    if problems:
        raise Refused("The plan cannot be approved yet:\n" + "\n".join(f"- {p}" for p in problems))
    if not entries:
        raise Refused("The plan has no tests.")
    if state["on"]:
        raise Refused("Tests are already switched on; a changed plan needs a fresh start (`finish --abandon`, then `init`).")
    require_green(root, state, "with the planned tests switched off")
    state["approved"] = {"fingerprint": fingerprint(entries), "kept": fingerprint(entries, without_removed=True),
                         "reason": args.reason, "at": now()}
    state.pop("locked", None)
    save(root, state)
    follow = "write and review the test bodies, then `testplan.py lock`" if state["bodies"] == "author" else "`testplan.py tasks`"
    print(f"Approved: {len(entries)} tests. Next: {follow}.")


def cmd_lock(root, args):
    state = load(root)
    if state["bodies"] != "author":
        raise Refused("This plan has the implementer write each test body, so there is no lock; go to `testplan.py tasks`.")
    entries, problems = read_plan(root, state)
    require_plan_unchanged(root, state, entries, problems)
    require_green(root, state, "with the planned tests switched off")
    state["locked"] = file_hashes(root, state)
    save(root, state)
    print(f"Locked {len(state['locked'])} test files. Next: `testplan.py tasks`.")


def cmd_tasks(root, args):
    state = load(root)
    entries, _ = read_plan(root, state)
    on = set(state["on"])
    for task in tasks(entries):
        done = sum(t["id"] in on for t in task["tests"])
        print(f"Task {task['number']}: {task['owner']} ({done} of {len(task['tests'])} tests switched on)")
        for test in task["tests"]:
            print(f"  {'on ' if test['id'] in on else 'off'} {test['id']}")


def cmd_brief(root, args):
    state = load(root)
    entries, problems = read_plan(root, state)
    require_plan_unchanged(root, state, entries, problems)
    task = find_task(entries, args.task)
    owners = {}
    for entry in entries:
        if entry["action"] != "remove":
            owners.setdefault(entry["owner"], []).append(entry.get("rule", ""))
    print(f"# Task {task['number']}: {task['owner']}\n")
    print(f"Check command: `{shlex.join(state['check'])}`")
    if state.get("lint"):
        print(f"Lint command: `{shlex.join(state['lint'])}` ({sum(state['lint_start'].values())} findings when the plan started)")
    print(f"Test bodies: {'written and locked; they are not yours to edit' if state['bodies'] == 'author' else 'you write each one when it is switched on'}\n")
    print("## Tests, in order")
    for test in task["tests"]:
        print(f"- `{test['id']}`\n  - Rule: {test['rule']}\n  - Example: {test['doc']}")
    print("\n## Who owns what in this change")
    for owner, rules in owners.items():
        print(f"- `{owner}`: {'; '.join(dict.fromkeys(rules))}")
    print(f"\nSwitch on the first test with `testplan.py next {task['number']}`.")


def cmd_next(root, args):
    state = load(root)
    entries, problems = read_plan(root, state)
    require_plan_unchanged(root, state, entries, problems)
    require_lock(root, state)
    task = find_task(entries, args.task)
    on = set(state["on"])
    reviewed = {s["id"] for s in state["steps"]}
    open_step = next((t for t in task["tests"] if t["id"] in on and t["id"] not in reviewed), None)
    upcoming = next((t for t in task["tests"] if t["id"] not in on), None)
    # A step is checked against the task's own test files; the whole suite runs when the task ends.
    only = sorted({t["id"].split("::")[0] for t in task["tests"]}) if upcoming else ()
    if open_step:
        if not (args.review and args.review.strip()):
            raise Refused(f"Finish the step for `{open_step['id']}` first: tidy the code it touched, then pass "
                          "`--review \"<what you reviewed and what you changed, or why nothing needed changing>\"`.")
        require_green(root, state, "before the next test is switched on" if upcoming else "before the task ends", only)
        require_no_new_findings(root, state)
        state["steps"].append({"id": open_step["id"], "task": task["number"], "review": args.review, "at": now()})
    else:
        require_green(root, state, "before a test is switched on" if upcoming else "before the task ends", only)
    if upcoming is None:
        save(root, state)
        print(f"Task {task['number']} is complete: every test is switched on and the whole suite passes.")
        return
    state["on"].append(upcoming["id"])
    save(root, state)
    code, _ = run(root, state, [upcoming["id"]])
    print(f"Switched on `{upcoming['id']}`\n  Rule: {upcoming['rule']}\n  Example: {upcoming['doc']}")
    if state["bodies"] == "implementer":
        print("  Write this test's body now, see it fail for the right reason, then make it pass.")
    elif code == 0:
        print("  It passes already: earlier work covers it. Review, then move on.")
    else:
        print("  It fails, as a test for unbuilt behaviour should. Make it pass with the smallest change.")


def tidy_by(state):
    return state.get("tidy") or ("self" if state.get("session") == "one" else "agent")


def cmd_status(root, args):
    state = load(root)
    entries, problems = read_plan(root, state)
    stepped = [e for e in entries if e["action"] in STEPPED]
    print(f"Work done by: {('this one session, with no subagents' if tidy_by(state) == 'self' else 'this one session') if state.get('session') == 'one' else 'a subagent for each piece'}")
    print(f"Closing tidy-up by: {'this session' if tidy_by(state) == 'self' else 'a fresh subagent'}")
    print(f"Bodies written by: the {'test author (locked)' if state['bodies'] == 'author' else 'implementer'}")
    print(f"Plan: {len(entries)} tests, {len(problems)} problems; "
          f"approved: {'yes' if state.get('approved') else 'no'}; locked: {'yes' if state.get('locked') else 'no'}")
    print(f"Switched on: {sum(e['id'] in state['on'] for e in stepped)} of {len(stepped)}; steps reviewed: {len(state['steps'])}")


def cmd_finish(root, args):
    state = load(root)
    if not args.abandon:
        entries, problems = read_plan(root, state)
        if problems:
            raise Refused("The plan no longer reads cleanly:\n" + "\n".join(f"- {p}" for p in problems))
        if not state.get("approved"):
            raise Refused("Nothing was approved; `finish --abandon` drops the plan.")
        stepped = [e["id"] for e in entries if e["action"] in STEPPED]
        missing = [i for i in stepped if i not in state["on"] or i not in {s["id"] for s in state["steps"]}]
        if missing:
            raise Refused("These tests have not been switched on and reviewed: " + ", ".join(missing))
        removed = [e["id"] for e in entries if e["action"] == "remove"]
        if removed:
            if not state.get("removing"):
                require_lock(root, state)
                state["removing"] = True  # the lock is released so the marked tests can be deleted
                save(root, state)
            raise Refused("Delete these tests, which the plan marks for removal, then run `finish` again: " + ", ".join(removed))
        if fingerprint(entries) != state["approved"]["kept"]:
            raise Refused("The remaining tests differ from the approved plan; only the tests marked for removal may go.")
        require_lock(root, state)
        require_no_new_findings(root, state)
        label_finished(root, state)
        write_block(root, REGISTER)
        require_green(root, state, "with every test switched on")
    else:
        write_block(root, REGISTER)
    state["finished"] = now()
    save(root, state)
    state_path(root).rename(root / STATE_DIR / f"finished-{state['finished'].replace(':', '')}.json")
    print("Abandoned: tests still carrying a planned mark will join the next plan unless the mark is removed." if args.abandon
          else "Finished: every planned test is on and passing and now carries the `acceptance` label in place of its plan mark.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=".", help="project root (default: current folder)")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("init", help="start a plan from the operator's request")
    p.add_argument("--request", required=True, help="file holding the request, word for word")
    p.add_argument("--bodies", choices=("author", "implementer"),
                   help="who writes test bodies: a separate author before the lock (the default), or the implementer at each step")
    p.add_argument("--session", choices=("agents", "one"), default="agents",
                   help="who does the work: a subagent for each piece (the default), or this one session for all of it")
    p.add_argument("--tidy", choices=("self", "agent"),
                   help="who does the closing tidy-up: a fresh subagent (the default with a subagent for each piece), or this session (the default with one session)")
    p.add_argument("--tests", nargs="+", default=["tests/**/*.py"], help="globs of the test files")
    p.add_argument("--check", default="python -m pytest -q", help="command that runs the whole suite")
    p.add_argument("--lint", help="linter command over the production code, printing `path:line:col: RULE message` lines; "
                                  "each step and the finish then leave no more findings than the plan started with")
    p = sub.add_parser("answer", help="record an operator answer")
    p.add_argument("question")
    p.add_argument("answer")
    p = sub.add_parser("park", help="record something left out of this change")
    p.add_argument("title")
    sub.add_parser("plan", help="print the plan for the operator")
    p = sub.add_parser("approve", help="record the operator's approval of the printed plan")
    p.add_argument("--reason", required=True, help="the operator's words")
    sub.add_parser("lock", help="lock the reviewed test files")
    sub.add_parser("tasks", help="list tasks, grouped by owner")
    p = sub.add_parser("brief", help="print one task's brief for its implementer")
    p.add_argument("task", type=int)
    p = sub.add_parser("next", help="finish the current step and switch on the task's next test")
    p.add_argument("task", type=int)
    p.add_argument("--review", help="the review of the step just finished")
    sub.add_parser("status", help="where the plan stands")
    p = sub.add_parser("finish", help="end the plan")
    p.add_argument("--abandon", action="store_true", help="drop the plan without the closing checks")
    args = parser.parse_args(argv)
    try:
        globals()[f"cmd_{args.command}"](pathlib.Path(args.root).resolve(), args)
    except Refused as refusal:
        print(f"Refused: {refusal}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
