#!/usr/bin/env -S uv run -q --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["radon==6.0.1", "cognitive_complexity==1.3.0"]
# ///
"""Scorecard for one finished maintainer run: measure.py <change-dir> <out-dir>  -> <out-dir>/measure.json + one line
(score.sh calls it; <change-dir> is the change's folder under local/.)

Everything is computed; nothing is judged. A "code file" is a .py file that is not a test file; a test file is under
tests/ or named test_*.py or conftest.py. The diff is start commit..HEAD of <out-dir>/project (run.sh commits the result).

outcome     new / regression hidden cases passed and total (hidden-new.json, hidden-regression.json, from score.sh);
            the project's own suite after the change; session exit code; timed_out = exit code 124 (run.sh's timeout).
attention   looks_before_first_code_edit: Read, Grep, Glob and Bash calls made before the first call that changed a
            code file (Bash calls that themselves changed a file are not looks). files_read_before_first_code_edit:
            distinct project files named in those Read/Grep calls, or in a Bash command segment that starts with
            cat, head, tail, sed -n, grep, rg, wc, nl, less or awk. tool_calls, turns, seconds; cost_usd and
            output_tokens are secondary.
landed      per group (code, tests): files, new_files, deleted_files, lines added/removed.
            places = diff hunks with git's default 3 lines of context (changes fewer than 7 lines apart are one place);
            change_runs = unbroken runs of changed lines (hunks with no context).
            Functions are every def, named Class.method / outer.inner. A changed line belongs to the innermost def
            holding it; a pure insertion or deletion belongs to the innermost def holding both neighbouring lines.
            functions_modified = defs present at start and end with a changed line on either side;
            functions_added / functions_deleted = names only at the end / only at the start;
            functions_touched = the three together; places_outside_functions = change runs in no def.
difficulty  for each functions_modified def, measured on the start commit: length in lines (decorators to last line),
            cyclomatic complexity (radon 6.0.1; nested defs not included), cognitive complexity (cognitive_complexity
            1.3.0, Sonar's rules; nested defs included). count, median, max of each; lines_held = sum of the lengths.
rework      An edit = one tool call changing one project .py file: an Edit or Write call that succeeded, or a Bash call
            (whatever its exit code) whose result carries a recorded file diff (bashEditDiff; sessions often edit
            through shell scripts).
            Each edit's recorded hunks are replayed on the file from the start commit, so every line is known to be
            original or written earlier in this session. The headline numbers, over code files:
            lines_written = lines the recorded edits added (the "+" lines of their hunks; a Write is diffed against
            the replayed file, so only lines that differ count; a new file's lines all count).
            lines_rewritten = lines the recorded edits removed that an earlier edit of the session had written (a
            changed line is one removed and one added; a line moved elsewhere also counts). A line written three
            times counts three times as written and twice as rewritten.
            rewritten_share = lines_rewritten / lines_written, null when nothing was written.
            rewritten_in_tests holds the same two counts for test files.
            reliable = false when the record is incomplete for code files: code_files_changed_unrecorded or
            code_files_not_reproduced is not empty, code_edit_gaps > 0, or attention.first_code_edit_seen is false.
            The counts then miss work.
            Kept for continuity, but they grow with the number of files a change is spread over, not with wasted
            work: edits_per_file and code_edits count the edits;
            repeated_same_lines = edits that rewrite or remove a line an earlier edit of the session wrote, or insert
            between two such lines. repeated_same_function = edits that change a def (same innermost-def rule, on the
            file before and after the edit) that an earlier edit already changed; edits outside every def count here
            only when they are repeated_same_lines. A new file's lines all count as written by the session.
            edits_out_of_step = edits whose recorded context did not match the replayed file (a file change the record
            does not show); edits_without_diff = files a Bash call changed beyond the diffs it recorded; both count
            test files too. code_edit_gaps = the two together for code files only.
            code_files_not_reproduced = code files with a recorded edit whose replayed text, after the last one, is
            not the file at the end commit (something else changed it, such as a script whose call recorded no diff).
            test_runs = Bash calls whose command contains the word pytest; test_runs_failed = those with an error
            result or a pytest summary line ("<n> failed ... in <t>s" or "<n> error(s) ... in <t>s", n > 0) in the output.
            code_files_changed_unrecorded = code files in the final diff that no recorded edit touched (a shell call
            moved to the background records no diff); when it is not empty, or attention.first_code_edit_seen is
            false, the looks-before-first-edit and rework numbers undercount.
own_tests   test functions (name starts with "test", any class) modified / deleted / added between start and end;
            old_tests_failing = the start commit's test files run against the changed code, cases failed or in error;
            test_to_code_lines = changed test lines / changed code lines (added + removed).
missed      hidden_failures = new + regression cases not passed; missed_by_own_tests = that number when the own suite
            is green (some passed, none failed), else null.
audit       Where the session reached outside its work folder (the cwd of the record's init event). Scanned: every tool
            call's command, file_path, path, notebook_path and glob input, and a Glob call's pattern.
            outside_paths = the distinct paths found there that are not in the work folder: absolute paths (also ~/
            and $HOME/ ones; only those whose first folder is a standard root folder or the work folder's, so sed
            and grep patterns are not taken for paths; a bare / only after find, ls, cd, tree or du), and relative
            paths that leave it. A relative path is read from the folder the command had moved to by then (its cd
            calls so far, and $NAME for each NAME=/path it sets; the work folder when a cd cannot be followed, and
            at the start of every call), so .. after "cd /tmp/x" is scratch, and is listed as written when read from
            the work folder (.., ../..), else as the path it comes to. Left out: /tmp, /dev, and the Python
            installation the project's .venv points at.
            answer_paths = those of them that name an answer or sibling-run location, or something in one: the kit
            folder (all of it except this run's own out-dir), the problem set, other sessions' records under
            ~/.claude/projects, the EXTRA_ANSWER_PATHS setting's folders, and the folder that holds the work folder (its siblings are other runs). An absolute
            path that holds one of these (/, /home) counts when its call is a Grep or Glob, or a Bash command with
            find, tree, du, rg, grep -r or ls -R anywhere in it (a search from there reaches them).
            touched_answers = answer_paths is not empty; it says a location was named, not that anything was read:
            read the calls in the record to tell.
"""
import ast, difflib, json, os, pathlib, re, shutil, statistics, subprocess, sys, tempfile

sys.setrecursionlimit(20000)
READ_VERB = re.compile(r"(cat|head|tail|sed -n|grep|rg|wc|nl|less|awk)\b")
HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", re.M)
FAILED = re.compile(r"\b[1-9]\d* (failed|errors?)\b[^\n]* in [\d.]+s")  # pytest's summary line
DEF = (ast.FunctionDef, ast.AsyncFunctionDef)
KIT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT))
from settings import setting

RECORDS = os.path.expanduser("~/.claude/projects")  # Claude Code keeps every session's record here, in a folder named after its cwd
ANSWERS = [p for p in [str(KIT), setting("SCB_PROBLEMS"), RECORDS, *setting("EXTRA_ANSWER_PATHS").split()] if p]  # the audit's answer locations
ROOTS = {"home", "usr", "etc", "var", "opt", "proc", "sys", "run", "bin", "sbin", "lib", "lib64", "root", "mnt", "srv", "tmp", "dev", "boot", "media"}
PATH = re.compile(r"(?<![\w./:@+$~{}-])((?:~|\$HOME|\$\{HOME\}|[\w.@+-]+)?(?:/[\w.@+-]*)+|\.\.)(?![\w.])")
SLASH = re.compile(r"\b(?:find|ls|cd|tree|du)\s+(?:-\S+\s+)*/(?=[\s;|&)]|$)")  # the root folder itself as a command's target
SET = re.compile(r"\b([A-Za-z_]\w*)=[\"']?(/[\w./@+-]*)")
CD = re.compile(r"\bcd\s+[\"']?([^\s\"';&|)]+)")
SEARCH = re.compile(r"\b(?:find|tree|du|rg)\b|\bgrep\s+(?:\S+\s+)*?-\w*[rR]|\bls\s+(?:\S+\s+)*?-\w*R")


def is_test(f):
    name = pathlib.PurePosixPath(f).name
    if f.startswith((".claude/", ".fbk/")):
        return False
    return f.startswith("tests/") or "/tests/" in f or (name.startswith("test_") and name.endswith(".py")) or name == "conftest.py"


def is_workflow(f):  # a workflow's own installed files and state, not the project's code or tests
    return f.startswith((".claude/", ".fbk/"))


def is_code(f):
    return f.endswith(".py") and not is_test(f) and not is_workflow(f)


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True).stdout


def functions(text):
    """Every def in a source text: qualified name -> (first line with decorators, last line, node). {} if it does not parse."""
    out = {}
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, RecursionError):
        return out

    def walk(node, prefix):
        for ch in ast.iter_child_nodes(node):
            if isinstance(ch, DEF + (ast.ClassDef,)):
                q = prefix + ch.name
                if isinstance(ch, DEF):
                    while q in out:  # a name defined twice in one scope
                        q += "'"
                    out[q] = (min([d.lineno for d in ch.decorator_list] + [ch.lineno]), ch.end_lineno, ch)
                walk(ch, q + ".")
            else:
                walk(ch, prefix)

    walk(tree, "")
    return out


def hit(funcs, first, count):
    """Innermost defs holding lines first..first+count-1; for count 0, the one holding both first and first+1."""
    def inner(lo, hi):
        c = [(v[0], k) for k, v in funcs.items() if v[0] <= lo and hi <= v[1]]
        return max(c)[1] if c else None
    return ({inner(l, l) for l in range(first, first + count)} if count else {inner(first, first + 1)}) - {None}


def cyclomatic(text):
    """def line -> radon cyclomatic complexity, for every function, method and nested def."""
    from radon.complexity import cc_visit
    out, todo = {}, list(cc_visit(text))
    while todo:
        b = todo.pop()
        if type(b).__name__ == "Function":
            out.setdefault(b.lineno, b.complexity)
        todo += list(getattr(b, "closures", [])) + list(getattr(b, "methods", [])) + list(getattr(b, "inner_classes", []))
    return out


def spread(values):
    values = [v for v in values if v is not None]
    return {"median": statistics.median(values) if values else None, "max": max(values, default=None)}


def footprint(repo, start, end="HEAD"):
    """Where a change landed and how big and tangled the functions it modified were at the start."""
    from cognitive_complexity.api import get_cognitive_complexity
    status = dict(reversed(l.split("\t")) for l in git(repo, "diff", "--name-status", "--no-renames", start, end).splitlines())
    lines = {}
    for l in git(repo, "diff", "--numstat", "--no-renames", start, end).splitlines():
        a, r, f = l.split("\t")
        lines[f] = (int(a) if a.isdigit() else 0, int(r) if r.isdigit() else 0)
    hunks = lambda f, ctx: [(int(a), int(b or 1), int(c), int(d or 1)) for a, b, c, d in
                            HUNK.findall(git(repo, "diff", f"-U{ctx}", "--no-renames", start, end, "--", f))]
    groups = {"code": sorted(f for f in status if is_code(f)), "tests": sorted(f for f in status if f.endswith(".py") and is_test(f))}
    landed = {}
    for g, files in groups.items():
        landed[g] = {"files": len(files), "new_files": sum(status[f] == "A" for f in files),
                     "deleted_files": sum(status[f] == "D" for f in files),
                     "lines_added": sum(lines[f][0] for f in files), "lines_removed": sum(lines[f][1] for f in files),
                     "places": sum(len(hunks(f, 3)) for f in files), "change_runs": sum(len(hunks(f, 0)) for f in files),
                     "file_list": files}
    modified, added, deleted, outside, detail = [], [], [], 0, []
    for f in groups["code"]:
        old = git(repo, "show", f"{start}:{f}") if status[f] != "A" else ""
        new = git(repo, "show", f"{end}:{f}") if status[f] != "D" else ""
        fo, fn, t_old, t_new = functions(old), functions(new), set(), set()
        for a, b, c, d in hunks(f, 0):
            ho, hn = hit(fo, a, b), hit(fn, c, d)
            t_old |= ho; t_new |= hn; outside += not (ho or hn)
        cc = cyclomatic(old) if fo else {}
        for q in sorted(fo, key=lambda q: fo[q][0]):
            if q in fn and (q in t_old or q in t_new):
                first, last, node = fo[q]
                modified.append(f"{f}::{q}")
                detail.append({"function": f"{f}::{q}", "lines": last - first + 1, "cyclomatic": cc.get(node.lineno),
                               "cognitive": get_cognitive_complexity(node)})
        added += [f"{f}::{q}" for q in fn if q not in fo]
        deleted += [f"{f}::{q}" for q in fo if q not in fn]
    landed["code"] |= {"functions_touched": len(modified) + len(added) + len(deleted), "functions_modified": len(modified),
                       "functions_added": len(added), "functions_deleted": len(deleted), "places_outside_functions": outside,
                       "functions_added_list": added, "functions_deleted_list": deleted}
    landed["other_files"] = sorted(f for f in status if not f.endswith(".py"))
    difficulty = {"functions": len(detail), "length": spread([d["lines"] for d in detail]),
                  "cyclomatic": spread([d["cyclomatic"] for d in detail]), "cognitive": spread([d["cognitive"] for d in detail]),
                  "lines_held": sum(d["lines"] for d in detail), "detail": detail}
    return landed, difficulty


def recorded_edits(name, inp, res):
    """The file changes one tool call's result records: [(absolute path, hunks or None, whole new text or None)]."""
    if not isinstance(res, dict):
        return []
    if name in ("Edit", "Write", "MultiEdit") and (res.get("filePath") or inp.get("file_path")):
        path, patch = res.get("filePath") or inp["file_path"], res.get("structuredPatch") or []
        return [(path, patch, None)] if patch else [(path, None, res.get("content", inp.get("content")))]
    diff = res.get("bashEditDiff") or {}
    with_hunks = [(x["filePath"], x.get("hunks") or [], None) for x in diff.get("files", [])]
    return with_hunks + [(p, None, None) for p in diff.get("changedFiles", []) if p not in {x[0] for x in with_hunks}]


def outside(calls, cwd, skip, own, answers):
    """The audit numbers: paths in the calls' inputs outside the work folder cwd. skip = folders left out; own = folders
    that are the session's own, listed but never an answer; answers = answer folders, besides the folder holding cwd."""
    home, under = os.path.expanduser("~"), lambda p, d: p == d or p.startswith(d.rstrip("/") + "/")
    found, hits, own = set(), set(), own + [RECORDS + "/" + re.sub(r"[^A-Za-z0-9]", "-", cwd)]  # and its own record
    for name, inp in calls.values():
        text = "\n".join(str(v) for k, v in inp.items() if k in ("command", "file_path", "path", "notebook_path", "glob") or (k, name) == ("pattern", "Glob"))
        for _ in range(2):  # $NAME becomes its path for every NAME=/path the command itself sets
            for k, v in SET.findall(text):
                text = re.sub(r"\$\{?" + k + r"\b\}?", lambda m: v, text)
        search = name in ("Grep", "Glob") or name == "Bash" and bool(SEARCH.search(text))
        cds = [(m.start(1), m.group(1)) for m in CD.finditer(text)] if name == "Bash" else []
        tokens = [(m.start(), re.sub(r"(?<=\w)\.+$", "", m.group())) for m in PATH.finditer(text) if m.group().strip("/")]
        for at, t in tokens + [(m.end() - 1, "/") for m in SLASH.finditer(text) if name == "Bash"]:
            base = cwd  # the folder the command had moved to by then; the work folder again after a cd this cannot follow
            for _, d in [c for c in cds if c[0] < at]:
                base = cwd if "$" in d or "`" in d else os.path.normpath(os.path.join(base, home + d[1:] if d.startswith("~") else d))
            if t.startswith(("~/", "$HOME/", "${HOME}/")):
                p = shown = os.path.normpath(home + t[t.index("/"):])
            elif t.startswith("/"):
                p = shown = os.path.normpath(t)
                if p != "/" and p.split("/")[1] not in ROOTS | {cwd.split("/")[1]}:
                    continue
            else:
                p = os.path.normpath(os.path.join(base, t))
                shown = os.path.normpath(t) if base == cwd else p
            if any(under(p, d) for d in [cwd, "/tmp", "/dev"] + skip):
                continue
            found.add(shown)
            if not any(under(p, d) for d in own) and any(under(p, a) or search and under(a, p) for a in answers + [os.path.dirname(cwd)]):
                hits.add(shown)
    return {"outside_paths": sorted(found), "answer_paths": sorted(hits), "touched_answers": bool(hits)}


def read_record(record):
    """A stream-json session record as (work folder, {call id: (tool, input)}, {call id: (is error, text, result)},
    the final result event). The work folder is the cwd of the init event, "" when the record has none."""
    events = []
    for line in pathlib.Path(record).read_text().splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    cwd = next((e["cwd"] for e in events if e.get("subtype") == "init" and e.get("cwd")), "")
    calls, results, final = {}, {}, {}
    for e in events:
        msg = e.get("message")  # some system records (a denied command) carry a plain string here
        content = msg.get("content") if isinstance(msg, dict) else None
        for b in content if isinstance(content, list) else []:
            if e.get("type") == "assistant" and b.get("type") == "tool_use":
                calls.setdefault(b["id"], (b["name"], b.get("input") or {}))
            elif e.get("type") == "user" and b.get("type") == "tool_result":
                c = b.get("content")
                text = c if isinstance(c, str) else "\n".join(str(p.get("text", "")) for p in c or [] if isinstance(p, dict))
                results[b["tool_use_id"]] = (bool(b.get("is_error")), text, e.get("tool_use_result"))
        if e.get("type") == "result":
            final = e
    return cwd, calls, results, final


def audit(record, skip=(), own=(), answers=()):
    """The audit numbers of one session record on its own (see outside()); None when it names no work folder."""
    cwd, calls, _, _ = read_record(record)
    return outside(calls, cwd, list(skip), list(own), list(answers)) if cwd else None


def session_stats(record, start_text=lambda f: "", tracked=(), skip=(), own=(), answers=(), end_text=None):
    """Attention, rework and audit numbers from a stream-json session record. start_text(file) is the file at the start
    commit ("" if absent) and end_text(file) the same at the end commit; tracked is the set of project files at the
    start; skip, own and answers are passed to outside(). See the module docstring for each definition."""
    cwd, calls, results, final = read_record(record)
    rel = lambda p: os.path.normpath(p[len(cwd) + 1:] if cwd and p.startswith(cwd + "/") else p)
    text, mine, seen = {}, {}, {}  # per file: current lines, "written this session" per line, defs edited so far
    per_file, looks, read, first = {}, 0, set(), None
    n = {k: 0 for k in ("out_of_step", "without_diff", "code_gaps", "tool", "shell", "runs", "runs_failed")}
    rep = {"code": {"same_lines": 0, "same_function": 0}, "tests": {"same_lines": 0, "same_function": 0}}
    wrote = {"code": {"lines_written": 0, "lines_rewritten": 0}, "tests": {"lines_written": 0, "lines_rewritten": 0}}

    def replay(f, hunks, whole):
        """Apply one edit to the replayed file; return (touches session-written lines, defs changed, lines added,
        lines removed that the session had written)."""
        if f not in text:
            text[f] = start_text(f).splitlines(); mine[f] = [False] * len(text[f])
        old, was, spans_old, spans_new, again = text[f], mine[f], [], [], False
        if hunks is None:  # whole new content (a Write that created or replaced the file)
            new = (whole or "").splitlines()
            ops = difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes()
            hunks = [{"oldStart": i1 + 1 if i2 > i1 else i1, "oldLines": i2 - i1, "newStart": j1 + 1, "newLines": j2 - j1,
                      "lines": ["-" + l for l in old[i1:i2]] + ["+" + l for l in new[j1:j2]]} for t, i1, i2, j1, j2 in ops if t != "equal"]
        new, now, shift, added, redone = list(old), list(was), 0, 0, 0
        for h in sorted(hunks, key=lambda h: h["oldStart"]):
            o = h["oldStart"] - 1 if h["oldLines"] else h["oldStart"]  # 0-based index of the hunk's first old line
            at, body, flags, run = o + shift, [], [], None
            if [l[1:] for l in h["lines"] if l[:1] in ("", " ", "-")] != old[o:o + h["oldLines"]]:
                n["out_of_step"] += 1; n["code_gaps"] += is_code(f)
            for l in h["lines"] + [None]:  # None closes a change run that ends the hunk
                kind = " " if l is None else l[:1] or " "
                if kind in "-+":
                    run = run or [o, 0, at + len(body), 0]
                    run[1 if kind == "-" else 3] += 1
                    added += kind == "+"; redone += kind == "-" and o < len(was) and was[o]
                elif run:
                    a, removed, c, inserted = run
                    again |= any(was[a:a + removed]) if removed else (0 < a < len(was) and was[a - 1] and was[a])
                    spans_old.append((a + 1, removed) if removed else (a, 0))
                    spans_new.append((c + 1, inserted) if inserted else (c, 0))
                    run = None
                if kind == "+" or (kind == " " and l is not None):
                    body.append(l[1:]); flags.append(kind == "+" or (o < len(was) and was[o]))
                o += kind in " -"
            new[at:at + h["oldLines"]] = body; now[at:at + h["oldLines"]] = flags
            shift += len(body) - h["oldLines"]
        fo, fn = functions("\n".join(old)), functions("\n".join(new))
        defs = set().union(*[hit(fo, a, c) for a, c in spans_old], *[hit(fn, a, c) for a, c in spans_new])
        text[f], mine[f] = new, now
        return again, defs, added, redone

    for i, (cid, (name, inp)) in enumerate(calls.items()):
        err, out, res = results.get(cid, (False, "", None))
        cmd = inp.get("command", "") if name == "Bash" else ""
        edits = [(rel(p), h, w) for p, h, w in recorded_edits(name, inp, res)]  # a failed Edit or Write records none
        edits = [(f, h, w) for f, h, w in edits if not f.startswith(("/", "..")) and f.endswith(".py")]
        if edits:
            n["shell" if name == "Bash" else "tool"] += 1
        for f, hunks, whole in edits:
            per_file[f] = per_file.get(f, 0) + 1
            if first is None and is_code(f):
                first = i
            if hunks is None and whole is None:
                n["without_diff"] += 1; n["code_gaps"] += is_code(f); continue
            if name != "Bash" and isinstance(res.get("originalFile"), str) and f in text and res["originalFile"].splitlines() != text[f]:
                n["out_of_step"] += 1; n["code_gaps"] += is_code(f)  # the file changed outside the record: take the real text, keep marks on equal lines
                real = res["originalFile"].splitlines(); marks = [False] * len(real)
                for a, b, size in difflib.SequenceMatcher(None, text[f], real, autojunk=False).get_matching_blocks():
                    marks[b:b + size] = mine[f][a:a + size]
                text[f], mine[f] = real, marks
            again, defs, added, redone = replay(f, hunks, whole)
            g, w = rep["tests" if is_test(f) else "code"], wrote["tests" if is_test(f) else "code"]
            w["lines_written"] += added; w["lines_rewritten"] += redone
            g["same_lines"] += again; g["same_function"] += bool(again or defs & seen.setdefault(f, set()))
            seen[f] |= defs
        if first is None and not edits and name in ("Read", "Grep", "Glob", "Bash"):
            looks += 1
            named = [inp.get("file_path") or inp.get("path") or ""] if name in ("Read", "Grep") else []
            for seg in re.split(r"&&|\|\||[;|\n]", cmd):
                if READ_VERB.match(seg.strip()):
                    named += re.findall(r"[\w./@+-]+", seg)
            read |= {rel(p) for p in named if p} & set(tracked) if tracked else {rel(p) for p in named if p and "." in p}
        if name == "Bash" and re.search(r"\bpytest\b", cmd):
            n["runs"] += 1; n["runs_failed"] += bool(err or FAILED.search(out))
    code_edits = {f: c for f, c in sorted(per_file.items()) if is_code(f)}
    attention = {"looks_before_first_code_edit": looks, "files_read_before_first_code_edit": len(read), "files_read_list": sorted(read),
                 "first_code_edit_seen": first is not None, "tool_calls": len(calls), "turns": final.get("num_turns"),
                 "cost_usd": final.get("total_cost_usd"), "output_tokens": (final.get("usage") or {}).get("output_tokens")}
    w = wrote["code"]
    rework = {**w, "rewritten_share": round(w["lines_rewritten"] / w["lines_written"], 3) if w["lines_written"] else None,
              "rewritten_in_tests": wrote["tests"], "code_edit_gaps": n["code_gaps"],
              "code_files_not_reproduced": sorted(f for f in code_edits if end_text and text.get(f, start_text(f).splitlines()) != end_text(f).splitlines()),
              "edits_per_file": code_edits, "edits_per_test_file": {f: c for f, c in sorted(per_file.items()) if is_test(f)},
              "code_edits": sum(code_edits.values()), "edit_calls_by_tool": n["tool"], "edit_calls_by_shell": n["shell"],
              "repeated_same_lines": rep["code"]["same_lines"], "repeated_same_function": rep["code"]["same_function"],
              "repeated_in_tests": rep["tests"], "edits_out_of_step": n["out_of_step"], "edits_without_diff": n["without_diff"],
              "test_runs": n["runs"], "test_runs_failed": n["runs_failed"]}
    return attention, rework, outside(calls, cwd, list(skip), list(own), list(answers)) if cwd else None


def pytest_counts(python, cwd):
    try:
        p = subprocess.run([str(python), "-m", "pytest", "-q", "-p", "no:cacheprovider", "-rN"], cwd=cwd, capture_output=True,
                           text=True, timeout=1800, env={**os.environ, "TDD_REPORTER_OFF": "1"})
        last = (p.stdout.strip().splitlines() or [""])[-1]
    except subprocess.TimeoutExpired:
        last = "no result: stopped after 1800 s"
    count = lambda word: int(m.group(1)) if (m := re.search(rf"(\d+) {word}", last)) else 0
    return {"passed": count("passed"), "failed": count("failed") + count("error"), "summary": last}


def test_functions(text_by_file):
    return {f"{path}::{q}": ast.get_source_segment(text, v[2]) for path, text in text_by_file.items()
            for q, v in functions(text).items() if q.split(".")[-1].startswith("test")}


def hidden(report):
    if not report.exists():
        return None, None, None
    tests = json.loads(report.read_text()).get("tests", [])
    failing = sorted(t["nodeid"].split("::", 1)[-1] for t in tests if t["outcome"] != "passed")
    return len(tests) - len(failing), len(tests), failing


def main():
    change, out = pathlib.Path(sys.argv[1]).resolve(), pathlib.Path(sys.argv[2]).resolve()
    W, start = out / "project", (out / "start").read_text().strip()
    run = json.loads((out / "run.json").read_text())
    tracked = set(git(W, "ls-tree", "-r", "--name-only", start).splitlines())
    landed, difficulty = footprint(W, start)
    cfg = W / ".venv/pyvenv.cfg"  # its "home" line names the bin folder of the Python installation the .venv points at
    python = [str(pathlib.Path(l.split("=", 1)[1].strip()).parent) for l in (cfg.read_text().splitlines() if cfg.exists() else []) if l.startswith("home")]
    attention, rework, audit = session_stats(out / "session.jsonl", lambda f: git(W, "show", f"{start}:{f}") if f in tracked else "", tracked,
                                             python, [str(out)], ANSWERS, lambda f: git(W, "show", f"HEAD:{f}"))
    attention["seconds"] = int((out / "seconds").read_text())
    rework["code_files_changed_unrecorded"] = [f for f in landed["code"]["file_list"] if f not in rework["edits_per_file"]]
    rework["reliable"] = attention["first_code_edit_seen"] and not (rework["code_files_changed_unrecorded"] or rework["code_files_not_reproduced"]
                                                                    or rework["code_edit_gaps"])

    before = {f: git(W, "show", f"{start}:{f}") for f in tracked if f.endswith(".py") and is_test(f)}
    after = {f: (W / f).read_text() for f in git(W, "ls-files").splitlines() if f.endswith(".py") and is_test(f)}
    tb, ta = test_functions(before), test_functions(after)
    own = pytest_counts(W / ".venv/bin/python", W)
    with tempfile.TemporaryDirectory() as tmp:  # the starting tests against the changed code
        probe = pathlib.Path(tmp) / "probe"
        shutil.copytree(W, probe, ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", ".pytest_cache"))
        for f in after:
            (probe / f).unlink(missing_ok=True)
        for f, text in before.items():
            (probe / f).parent.mkdir(parents=True, exist_ok=True); (probe / f).write_text(text)
        old = pytest_counts(W / ".venv/bin/python", probe)

    np_, nt, nf = hidden(out / "hidden-new.json")
    rp, rt, rf = hidden(out / "hidden-regression.json")
    code_lines = landed["code"]["lines_added"] + landed["code"]["lines_removed"]
    test_lines = landed["tests"]["lines_added"] + landed["tests"]["lines_removed"]
    exit_code = int((out / "exit").read_text())
    green = own["passed"] > 0 and own["failed"] == 0
    hidden_failures = None if nf is None or rf is None else len(nf) + len(rf)
    m = {"change": run["change"], "base": run["base"], "base_commit": run["base_commit"], "model": run["model"],
         "outcome": {"new_passed": np_, "new_total": nt, "new_failing": nf, "regression_passed": rp, "regression_total": rt,
                     "regression_failing": rf, "own_passed": own["passed"], "own_failed": own["failed"], "own_summary": own["summary"],
                     "exit": exit_code, "timed_out": exit_code == 124},
         "attention": attention, "landed": landed, "difficulty": difficulty, "rework": rework,
         "audit": audit,
         "own_tests": {"modified": sorted(k for k in tb if k in ta and tb[k] != ta[k]), "deleted": sorted(k for k in tb if k not in ta),
                       "added": sorted(k for k in ta if k not in tb), "old_tests_failing": old["failed"], "old_tests_summary": old["summary"],
                       "test_to_code_lines": round(test_lines / code_lines, 3) if code_lines else None},
         "missed": {"hidden_failures": hidden_failures, "own_suite_green": green, "missed_by_own_tests": hidden_failures if green else None}}
    for k in ("modified", "deleted", "added"):
        m["own_tests"][f"{k}_count"] = len(m["own_tests"][k])
    (out / "measure.json").write_text(json.dumps(m, indent=1))
    o, a, c, d, r = m["outcome"], attention, landed["code"], difficulty, rework
    print(f"{m['change']} {m['base']} | new {np_}/{nt} regression {rp}/{rt} own {o['own_passed']} passed {o['own_failed']} failed exit {exit_code}"
          f" | {a['looks_before_first_code_edit']} looks, {a['files_read_before_first_code_edit']} files before first code edit; "
          f"{a['tool_calls']} calls, {a['seconds']} s | code {c['files']} files +{c['lines_added']}/-{c['lines_removed']}, {c['places']} places, "
          f"{c['functions_touched']} functions | modified {d['functions']}: max {d['length']['max']} lines, cyclomatic {d['cyclomatic']['max']}, "
          f"cognitive {d['cognitive']['max']}, {d['lines_held']} lines held | wrote {r['lines_written']} lines, rewrote {r['lines_rewritten']}"
          f"{'' if r['reliable'] else ' (record incomplete)'}; "
          f"{r['test_runs']} test runs, {r['test_runs_failed']} failed | old tests broken {m['own_tests']['old_tests_failing']} | "
          f"missed {m['missed']['missed_by_own_tests']} | outside paths {len(audit['outside_paths']) if audit else '-'}"
          f"{', NAMES AN ANSWER LOCATION' if audit and audit['touched_answers'] else ''}")


if __name__ == "__main__":
    main()
