#!/usr/bin/env -S uv run -q --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["mutmut==3.8.0"]
# ///
"""What a repo's own tests are worth, test by test.

  testq.py build <repo> [--n 600] [--seed 1] [--jobs 8] [--hidden <folder> --entry <file.py> --runner <python>]
  testq.py swap <repo whose tests> <repo whose code> ...

build prints one JSON object. The repo needs a .venv with its test tools; nothing is written into it.
  kills     the mutants.py sample (same engine, same draw for the same n and seed), each mutant run against the whole
            suite without stopping at the first failure, so every test that fails on it is known. A mutant that stops a
            test file from being collected, or runs into the time limit, is caught but credited to no single test.
  hidden    with --hidden (a folder prepared as build/hidden-tests.sh prepares it: the code, the hidden tests, pytest.ini,
            and checkpoint.txt naming the checkpoint; --runner is a python that has the hidden tests' own tools) each
            mutant is also run against the hidden tests, stopping at the first failure. A mutant they catch breaks
            behaviour the request specifies. own catch rate on those = "specified"; mutants the own suite catches and
            the hidden tests do not = "own only": sharper tests, or tests that pin a detail nobody asked for.
  cover     a greedy smallest set of tests that catches every mutant some single test catches.
  gutted    every top-level function and method with its body replaced by `return None` (docstring kept): "checked"
            when the suite then fails, "unchecked" when the suite ran the function and still passes, "never run" when
            the suite does not run it at all (by the repo's coverage; unknown without it).
  internals test functions that name a private name of the code (a leading underscore, defined in a code file and not
            in a test file) or replace parts of the code (mock, patch, monkeypatch.setattr).
swap runs the first repo's test files against each other repo's code files (its other files stay) and prints, per code
repo, each test's outcome: passed, "interface" (the test could not be collected, or failed with ImportError,
AttributeError, NameError or TypeError: it names something that repo does not have) or "result" (any other failure).
With --start, tests whose file and function name exist at that ref of the tests' repo are listed as old.
"""
import ast, concurrent.futures as cf, json, os, pathlib, queue, re, shutil, signal, subprocess, sys, tempfile, time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from measure import functions, git, is_code, is_test

INTERFACE = {"ImportError", "ModuleNotFoundError", "AttributeError", "NameError", "TypeError"}
args = sys.argv[1:]
MODE = args.pop(0)


def popopt(name, default=None):
    if name in args:
        i = args.index(name); args.pop(i)
        return args.pop(i)
    return default


def tracked(repo):
    return [f for f in git(repo, "ls-files").splitlines() if (repo / f).is_file()]


def run(py, work, cmd, timeout, env=(), out=None):
    """Run python with cmd in work: ('pass' | 'fail' | 'timeout', the plugin's record or None)."""
    pyc = tempfile.mkdtemp(dir=work.parent)
    e = {**os.environ, "PYTHONHASHSEED": "0", "TDD_REPORTER_OFF": "1", "PYTHONPYCACHEPREFIX": pyc,
         "PATH": str(pathlib.Path(py).parent) + os.pathsep + os.environ.get("PATH", ""), **dict(env)}
    e["PYTHONPATH"] = str(HERE) + os.pathsep + e.get("PYTHONPATH", "")  # where testq_plugin is
    e.pop("TESTQ_OUT", None)
    if out:
        out.unlink(missing_ok=True); e["TESTQ_OUT"] = str(out)
    p = subprocess.Popen([str(py), *cmd], cwd=work, env=e, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    try:
        res = "pass" if p.wait(timeout=timeout) == 0 else "fail"
    except subprocess.TimeoutExpired:
        res = "timeout"
    try:
        os.killpg(p.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    p.wait(); shutil.rmtree(pyc, ignore_errors=True)
    rec = None
    if out and out.exists():
        try:
            rec = json.loads(out.read_text())
        except ValueError:
            pass
    return res, rec


OWN = ("-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "testq_plugin", "--continue-on-collection-errors")


def failed(rec):
    """(tests that failed, files or nodes that could not be collected) from a plugin record."""
    return sorted(t for t, o in rec["tests"].items() if o not in ("passed", "skipped")), sorted(rec["collect"])


def test_file(nodeid):
    return nodeid.split("::")[0]


# ---------------------------------------------------------------- build
def gut(text, first_body, last, indent, keep_doc_to):
    lines = text.splitlines(keepends=True)
    start = keep_doc_to if keep_doc_to else first_body - 1
    return "".join(lines[:start] + [" " * indent + "return None\n"] + lines[last:])


def guttable(text):
    """Top-level functions and methods worth gutting: name -> (line, changed source)."""
    out = {}
    for name, (_, last, node) in functions(text).items():
        body = node.body
        if body[0].lineno == node.lineno:  # a one-line def
            continue
        doc = isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) and isinstance(body[0].value.value, str)
        rest = body[1:] if doc else body
        if not rest or all(isinstance(s, ast.Pass) or (isinstance(s, ast.Return) and s.value is None) or isinstance(s, ast.Raise)
                           or (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant)) for s in rest):
            continue
        if any(isinstance(n, (ast.Yield, ast.YieldFrom)) for n in ast.walk(node)):
            continue  # a generator turned into a plain function is caught by its type, not by a test of what it does
        out[name] = (node.lineno, gut(text, rest[0].lineno, last, rest[0].col_offset, body[0].end_lineno if doc else None), rest[0].lineno, last)
    return out


def top_level(text):
    """Qualified names of top-level functions and of methods of top-level classes."""
    tree = ast.parse(text)
    names = set()
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(n.name)
        elif isinstance(n, ast.ClassDef):
            names |= {f"{n.name}.{m.name}" for m in n.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))}
    return names


def internals(repo, files):
    code_private, test_defined = set(), set()
    for f in files:
        try:
            tree = ast.parse((repo / f).read_text())
        except SyntaxError:
            continue
        names = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
        names |= {t.id for n in ast.walk(tree) if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name)}
        names |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute) and isinstance(n.ctx, ast.Store)}
        if is_code(f):
            code_private |= {x for x in names if re.match(r"_[A-Za-z]", x)}
        elif is_test(f):
            test_defined |= names
    private = code_private - test_defined
    tests = reach = swap = 0
    for f in files:
        if not (is_test(f) and f.endswith(".py")):
            continue
        try:
            tree = ast.parse((repo / f).read_text())
        except SyntaxError:
            continue
        for n in ast.walk(tree):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test"):
                used = {x.attr for x in ast.walk(n) if isinstance(x, ast.Attribute)} | {x.id for x in ast.walk(n) if isinstance(x, ast.Name)}
                tests += 1; reach += bool(used & private)
                swap += bool(used & {"patch", "Mock", "MagicMock", "mocker"}) or ("monkeypatch" in used and "setattr" in used)
    return {"test_functions": tests, "name_private_code": reach, "replace_code": swap}


def cover(by_test, universe):
    """Greedy: tests picked until every mutant in universe is caught; the picks in order."""
    left, picks = set(universe), []
    while left:
        t = max(sorted(by_test), key=lambda t: len(by_test[t] & left))
        if not by_test[t] & left:
            break
        picks.append(t); left -= by_test[t]
    return picks


def build():
    hidden, entry, hpy = popopt("--hidden"), popopt("--entry"), popopt("--runner")
    sys.argv = [sys.argv[0], *args]
    if "--n" not in args:
        sys.argv += ["--n", "600"]
    if "--jobs" not in args:
        sys.argv += ["--jobs", "8"]
    import mutants as M
    R, PY, N, JOBS = M.R, M.PY, M.N, M.JOBS
    files = tracked(R); code = sorted(f for f in files if is_code(f))
    res = {"repo": str(R), "sample": N, "seed": M.SEED, "jobs": JOBS}
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        base = M.copy(tmp / "base" / "w")
        t = time.time(); ok, rec = run(PY, base, OWN, 1800, out=tmp / "base.json"); secs = time.time() - t
        if ok != "pass" or not rec:
            return {**res, "skipped": "the unmutated suite does not pass in a scratch copy"}
        tests = sorted(t for t, o in rec["tests"].items() if o == "passed")
        res |= {"suite_seconds": round(secs, 1), "tests": len(tests), "skipped_tests": sum(o == "skipped" for o in rec["tests"].values()),
                "test_lines": sum(len((R / f).read_text().splitlines()) for f in files if is_test(f) and f.endswith(".py"))}
        cov = M.coverage(base)
        executed = {}
        try:
            executed = {f: set(v["executed_lines"]) for f, v in json.loads((base / "coverage-state.json").read_text())["files"].items()}
        except (OSError, ValueError, KeyError):
            pass
        res["coverage_pct"] = cov and cov["pct"]
        (tmp / "pyproject.toml").write_text('[tool.mutmut]\nsource_paths = ["."]\n'); os.chdir(tmp)
        found = {f: M.mutants_of(f) for f in code}
        take = M.shares({f: len((R / f).read_text().splitlines()) for f in code}, {f: len(m) for f, (_, m) in found.items()}, N)
        import random
        picked = [(f, i) for f in code for i in sorted(random.Random(f"{M.SEED}:{f}").sample(range(len(found[f][1])), take[f]))]
        made = {(f, i): M.changed(f, found[f][0], found[f][1][i]) for f, i in picked}
        limit = max(60, 10 * secs)
        works = queue.Queue()
        for j in range(JOBS):
            works.put(M.copy(tmp / f"j{j}" / "w"))
        hworks = queue.Queue()
        if hidden:
            hidden = pathlib.Path(hidden).resolve()
            for j in range(JOBS):
                w = tmp / f"h{j}" / "w"; shutil.copytree(hidden, w, symlinks=True); hworks.put(w)
            hcmd = ("-m", "pytest", "-x", "-q", "-p", "no:cacheprovider", "--timeout=60", f"--entrypoint={PY} {entry}",
                    "--checkpoint=" + (hidden / "checkpoint.txt").read_text().strip(), "--confcutdir=tests", "tests")
            # the hidden suite fails a few cases on the unmutated code, so -x would stop at once: those are left out below
            t = time.time(); _, r0 = run(hpy, hidden, tuple(c for c in hcmd if c != "-x") + ("-p", "testq_plugin"), 3600, out=tmp / "h0.json"); hsecs = time.time() - t
            if not r0 or not r0["tests"]:
                return {**res, "skipped": "the hidden tests did not run on the unmutated code"}
            bad = [t for t, o in r0["tests"].items() if o not in ("passed", "skipped")]
            res |= {"hidden_seconds": round(hsecs, 1), "hidden_cases": len(r0["tests"]), "hidden_failing_unmutated": len(bad)}
            hx = hcmd + tuple(x for b in bad for x in ("--deselect", b))

        def with_change(pool, f, text, fn):
            work = pool.get()
            try:
                orig = (work / f).read_text(); (work / f).write_text(text)
                try:
                    return fn(work)
                finally:
                    (work / f).write_text(orig)
            finally:
                pool.put(work)

        def own(pick):
            f, i = pick
            def go(work):
                o, r = run(PY, work, OWN, limit, out=work.parent / "out.json")
                if o == "timeout" or r is None:
                    return {"own": "timeout" if o == "timeout" else "crash", "tests": [], "collect": []}
                ft, fc = failed(r)
                return {"own": "caught" if (ft or fc or o == "fail") else "missed", "tests": ft, "collect": fc}
            return with_change(works, f, made[f, i][1], go)

        t = time.time()
        with cf.ThreadPoolExecutor(max_workers=JOBS) as pool:
            outcome = list(pool.map(own, picked))
        res["own_seconds"] = round(time.time() - t, 1)
        if hidden:
            def hid(pick):
                f, i = pick
                return with_change(hworks, f, made[f, i][1], lambda work: run(hpy, work, hx, max(120, 3 * hsecs))[0])

            t = time.time()
            with cf.ThreadPoolExecutor(max_workers=JOBS) as pool:
                for o, h in zip(outcome, pool.map(hid, picked)):
                    o["hidden"] = {"pass": "missed", "fail": "caught"}.get(h, h)
            res["hidden_mutant_seconds"] = round(time.time() - t, 1)
        for (f, i), o in zip(picked, outcome):
            o |= {"file": f, "line": made[f, i][0]}
        # gutted functions
        guts = [(f, name, g) for f in code for name, g in sorted(guttable((R / f).read_text()).items())
                if name in top_level((R / f).read_text())]
        def gutrun(item):
            f, name, (line, text, b0, last) = item
            o = with_change(works, f, text, lambda work: run(PY, work, OWN[:2] + ("-x",) + OWN[2:], limit)[0])
            ran = bool(executed.get(f, set()) & set(range(b0, last + 1))) if f in executed else None
            return {"file": f, "function": name, "line": line, "outcome": "checked" if o != "pass" else ("unchecked" if ran or ran is None else "never run")}
        t = time.time()
        with cf.ThreadPoolExecutor(max_workers=JOBS) as pool:
            res["gutted"] = list(pool.map(gutrun, guts))
        res["gut_seconds"] = round(time.time() - t, 1)
    # ---- summary
    caught = [o for o in outcome if o["own"] != "missed"]
    by_test = {t: set() for t in tests}
    for k, o in enumerate(outcome):
        for t in o["tests"]:
            by_test.setdefault(t, set()).add(k)
    credited = set().union(*by_test.values()) if by_test else set()
    picks = cover(by_test, credited)
    once = [k for k in credited if sum(k in s for s in by_test.values()) == 1]
    g = [x["outcome"] for x in res["gutted"]]
    s = {"mutants": len(outcome), "caught": len(caught), "catch_rate": round(len(caught) / len(outcome), 3),
         "caught_by_no_single_test": len(caught) - len(credited),
         "tests_catching_nothing": sum(not v for v in by_test.values()), "tests_with_a_catch_no_other_makes": len({t for t, v in by_test.items() if v & set(once)}),
         "smallest_set": len(picks), "smallest_set_share": round(len(picks) / len(tests), 3) if tests else None,
         "catches_per_100_test_lines": round(100 * len(caught) / res["test_lines"], 2) if res["test_lines"] else None,
         "functions_gutted": len(g), "checked": g.count("checked"), "unchecked": g.count("unchecked"), "never_run": g.count("never run")}
    if hidden:
        spec = [o for o in outcome if o["hidden"] != "missed"]
        s |= {"hidden_catch_rate": round(len(spec) / len(outcome), 3), "specified": len(spec),
              "specified_caught_by_own": sum(o["own"] != "missed" for o in spec),
              "specified_catch_rate": round(sum(o["own"] != "missed" for o in spec) / len(spec), 3) if spec else None,
              "own_only": sum(o["hidden"] == "missed" for o in caught), "own_only_share_of_own_catches": round(sum(o["hidden"] == "missed" for o in caught) / len(caught), 3) if caught else None,
              "caught_by_neither": sum(o["own"] == "missed" and o["hidden"] == "missed" for o in outcome)}
    res |= {"summary": s, "internals": internals(R, files), "smallest_set_tests": picks, "mutants": outcome,
            "kills_by_test": {t: len(v) for t, v in sorted(by_test.items())}}
    return res


# ---------------------------------------------------------------- swap
MISSING = '''
class _TestqMissing:
    """Stands in for a name the code under test does not have: any use of it fails that one test as a missing interface."""
    def __init__(self, name): object.__setattr__(self, "_n", name)
    def _no(self, *a, **k): raise ImportError("not in this code: " + object.__getattribute__(self, "_n"))
    __getattr__ = __call__ = __iter__ = __getitem__ = __instancecheck__ = __subclasscheck__ = __mro_entries__ = _no
'''


def lazy_imports(text):
    """text of a test file with each module-level import made per-name and forgiving: a name the code lacks becomes a
    stand-in that fails only the tests that use it, instead of the import failing every test in the file."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return text
    lines, edits = text.splitlines(), []
    for n in tree.body:
        if isinstance(n, ast.ImportFrom) and n.module != "__future__" and not any(a.name == "*" for a in n.names):
            mod = "." * n.level + (n.module or "")
            new = [f"try:\n    from {mod} import {a.name} as {a.asname or a.name}\nexcept (ImportError, AttributeError):\n"
                   f"    {a.asname or a.name} = _TestqMissing({mod + '.' + a.name!r})" for a in n.names]
        elif isinstance(n, ast.Import):
            new = []
            for a in n.names:
                bound = a.asname or a.name.split(".")[0]
                stmt = f"import {a.name}" + (f" as {a.asname}" if a.asname else "")
                root = f"    try:\n        import {bound}\n    except ImportError:\n        {bound} = _TestqMissing({a.name!r})" if not a.asname and "." in a.name \
                    else f"    {bound} = _TestqMissing({a.name!r})"
                new.append(f"try:\n    {stmt}\nexcept ImportError:\n{root}")
        else:
            continue
        edits.append((n.lineno, n.end_lineno, new))
    if not edits:
        return text
    for a, b, new in reversed(edits):
        lines[a - 1:b] = new
    # the stand-in class goes after any docstring and __future__ imports
    at = 0
    body = ast.parse("\n".join(lines)).body
    for n in body:
        if (isinstance(n, ast.Expr) and isinstance(getattr(n, "value", None), ast.Constant) and isinstance(n.value.value, str) and n is body[0]) \
                or (isinstance(n, ast.ImportFrom) and n.module == "__future__"):
            at = n.end_lineno
        else:
            break
    lines[at:at] = MISSING.splitlines()
    return "\n".join(lines) + "\n"


def swap():
    start = popopt("--start"); jobs = int(popopt("--jobs", "8"))
    A, others = pathlib.Path(args[0]).resolve(), [pathlib.Path(a).resolve() for a in args[1:]]
    py = A / ".venv/bin/python"; fa = tracked(A)
    old = set()
    if start:
        for f in git(A, "ls-tree", "-r", "--name-only", start).splitlines():
            if is_test(f) and f.endswith(".py"):
                try:
                    old |= {(f, n.name) for n in ast.walk(ast.parse(git(A, "show", f"{start}:{f}"))) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
                except SyntaxError:
                    pass
    is_old = lambda t: (test_file(t), re.sub(r"\[.*", "", t.split("::")[-1])) in old
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        def lay(code_repo, to, lazy=False):
            for f in tracked(code_repo):
                if not is_test(f):
                    (to / f).parent.mkdir(parents=True, exist_ok=True); shutil.copy2(code_repo / f, to / f)
            for f in fa:
                if is_test(f):
                    (to / f).parent.mkdir(parents=True, exist_ok=True); shutil.copy2(A / f, to / f)
                    if lazy and f.endswith(".py"):
                        (to / f).write_text(lazy_imports((A / f).read_text()))
            return to
        _, own = run(py, lay(A, tmp / "own" / "w"), OWN, 1800, out=tmp / "own.json")
        tests = sorted(t for t, o in own["tests"].items() if o == "passed")
        _, own_lazy = run(py, lay(A, tmp / "ownlazy" / "w", lazy=True), OWN, 1800, out=tmp / "ownlazy.json")
        lazy_ok = own_lazy is not None and all(own_lazy["tests"].get(t) == "passed" for t in tests)
        def one(B):
            w = lay(B, tmp / B.parent.name / "w", lazy=True)
            o, rec = run(py, w, OWN, 1800, out=tmp / f"{B.parent.name}.json")
            if rec is None:  # the suite could not start on this code: every test fails on the interface
                rec = {"tests": {}, "collect": {}, "no_start": True}
            gone = set(rec["collect"])
            out = {}
            for t in tests:
                r = rec["tests"].get(t)
                out[t] = "passed" if r == "passed" else "interface" if (r is None or r in INTERFACE or test_file(t) in gone) else "result"
            cnt = lambda ts: {k: sum(out[t] == k for t in ts) for k in ("passed", "interface", "result")}
            o_, n_ = [t for t in tests if is_old(t)], [t for t in tests if not is_old(t)]
            return {"code": str(B), "all": cnt(tests), "old": cnt(o_), "new": cnt(n_), "started": not rec.get("no_start", False),
                    "kinds": {t: rec["tests"].get(t) for t, v in out.items() if v != "passed"},
                    "not_passed": {t: v for t, v in out.items() if v != "passed"}}
        with cf.ThreadPoolExecutor(max_workers=jobs) as pool:
            rows = list(pool.map(one, others))
    return {"tests_of": str(A), "forgiving_imports_keep_own_suite_green": lazy_ok, "tests": len(tests), "old_tests": sum(map(is_old, tests)), "against": rows}


print(json.dumps(build() if MODE == "build" else swap()))
