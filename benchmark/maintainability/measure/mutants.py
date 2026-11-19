#!/usr/bin/env -S uv run -q --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["mutmut==3.8.0"]
# ///
"""How much of a sample of small code changes a repo's own tests catch: mutants.py <repo> [--n 150] [--seed 1] [--jobs 4]

Prints one JSON object. Called by state.py --mutants; writes nothing into the repo.

Mutants: every change mutmut 3.8.0 would make (BSD-3-Clause, used as a library; the engine and version EXACT's lab pins
in compute-mutation-score.py; see NOTICE.md), listed by its own create_mutations() over the tracked code files (measure.py's
rule), keeping its rule that only code inside a top-level function or method is changed. Its operators: numbers, strings,
names (True/False, deepcopy/copy), assignments (value -> None), augmented assignments (-> plain), unary operator removal,
call arguments (removal, -> None, dict keyword rename), string-method swaps, lambda bodies, keywords (break/continue,
is/is not, in/not in ...), operator swaps (+/-, </<=, and/or ...), match-case removal, conditional-expression flips.
Unlike the lab, no file is left out (the lab skips src/cli.py because only its outside suite runs it; here the own tests
start circopt.py themselves), and each mutant is written as plain changed source, one per suite run, instead of mutmut's
switchable copies, so tests that start the program as a subprocess meet the change too.

Sample: n mutants, shared among the files in proportion to their line counts (largest remainders; a file with too few
mutants gives its surplus to the others), drawn within each file by random.Random(f"{seed}:{file}"). Same repo, n and seed
give the same mutants.

Each mutant: the suite (the repo's .venv python, -m pytest -x -q) in a scratch copy of the tracked files, PYTHONHASHSEED=0,
a fresh bytecode folder per run so no stale compiled file is used. Outcomes: caught = the suite fails; missed = it passes;
timeout = stopped after max(30 s, 10 x the unmutated run), counted as caught as the lab's formula does:
share = (caught + timeout) / run. The unmutated suite is run first in the same scratch copy; if it fails nothing is scored.

Coverage: statements of the code files run by the suite, by the repo's own coverage.py with its subprocess patch
(needs coverage >= 7.10 in the repo's .venv; null when that does not work).
"""
import concurrent.futures as cf, json, os, pathlib, queue, random, shutil, signal, subprocess, sys, tempfile, time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from measure import git, is_code

args = sys.argv[1:]
opt = lambda name, default: int(args.pop(args.index(name) + 1)) if name in args else default
N, SEED, JOBS = opt("--n", 150), opt("--seed", 1), opt("--jobs", 4)
R = pathlib.Path([a for a in args if not a.startswith("--")][0]).resolve()
PY = R / ".venv/bin/python"
tracked = [f for f in git(R, "ls-files").splitlines() if (R / f).is_file()]
code = sorted(f for f in tracked if is_code(f))


def suite(work, timeout, cmd=("-m", "pytest", "-x", "-q", "-p", "no:cacheprovider"), env=()):
    """Run the suite in work: 'pass', 'fail' or 'timeout', and the seconds it took."""
    pyc = tempfile.mkdtemp(dir=work.parent)
    e = {**os.environ, "PYTHONHASHSEED": "0", "TDD_REPORTER_OFF": "1", "PYTHONPYCACHEPREFIX": pyc,
         "PATH": str(PY.parent) + os.pathsep + os.environ.get("PATH", ""), **dict(env)}
    t = time.time()
    p = subprocess.Popen([str(PY), *cmd], cwd=work, env=e, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    try:
        out = "pass" if p.wait(timeout=timeout) == 0 else "fail"
    except subprocess.TimeoutExpired:
        out = "timeout"
    try:
        os.killpg(p.pid, signal.SIGKILL)  # also the programs the tests started
    except ProcessLookupError:
        pass
    p.wait(); shutil.rmtree(pyc, ignore_errors=True)
    return out, time.time() - t


def copy(to):
    for f in tracked:
        (to / f).parent.mkdir(parents=True, exist_ok=True); shutil.copy2(R / f, to / f)
    return to


def coverage(work):
    """Percent of the code files' statements the suite runs, subprocesses included; None if it cannot be had."""
    rc = work / ".coveragerc-state"
    rc.write_text(f"[run]\npatch = subprocess\nparallel = true\nsource = .\ndata_file = {work}/.coverage-state\n")
    if suite(work, 1800, ("-m", "coverage", "run", f"--rcfile={rc}", "-m", "pytest", "-q", "-p", "no:cacheprovider"))[0] != "pass":
        return None
    for cmd in (["combine", "-q"], ["json", "-q", "-o", "coverage-state.json"]):
        subprocess.run([str(PY), "-m", "coverage", cmd[0], f"--rcfile={rc}", *cmd[1:]], cwd=work, capture_output=True)
    try:
        files = json.loads((work / "coverage-state.json").read_text())["files"]
    except (OSError, ValueError, KeyError):
        return None
    s = [files[f]["summary"] for f in code if f in files]
    total = sum(x["num_statements"] for x in s)
    return {"statements": total, "covered": sum(x["covered_lines"] for x in s), "by_file": {f: files[f]["summary"]["percent_covered"] for f in code if f in files},
            "pct": round(100 * sum(x["covered_lines"] for x in s) / total, 1) if total else None}


def mutants_of(f):
    """(parsed file, its mutmut mutations inside top-level functions and methods, in mutmut's order)."""
    import libcst as cst
    from mutmut.mutation.file_mutation import create_mutations
    try:
        module, mutations, _, _ = create_mutations(f, (R / f).read_text())
    except cst.ParserSyntaxError:  # a file libcst cannot parse has no mutants
        return None, []
    return module, [m for m in mutations if m.contained_by_top_level_function is not None]


def changed(f, module, m):
    """(first changed line, whole changed source) for one mutation of file f."""
    from mutmut.mutation.file_mutation import deep_replace
    old, new = (R / f).read_text().splitlines(), deep_replace(module, m.original_node, m.mutated_node).code
    lines = new.splitlines()
    return next((i + 1 for i, (a, b) in enumerate(zip(old, lines)) if a != b), min(len(old), len(lines)) + 1), new


def shares(sizes, room, n):
    """n split among files in proportion to sizes, none above its room; what a full file cannot take goes to the rest."""
    take, open_ = {f: 0 for f in sizes}, {f for f in sizes if room[f]}
    while n and open_:
        total = sum(sizes[f] for f in open_) or 1
        exact = {f: n * sizes[f] / total for f in open_}
        add = {f: int(exact[f]) for f in open_}
        for f in sorted(open_, key=lambda f: (add[f] - exact[f], f))[:n - sum(add.values())]:
            add[f] += 1
        for f in sorted(open_):
            got = min(add[f], room[f] - take[f]); take[f] += got; n -= got
            if take[f] == room[f]:
                open_.discard(f)
    return take


def main():
    res = {"engine": "mutmut 3.8.0 operators, one plain-source mutant per full suite run", "sample": N, "seed": SEED, "jobs": JOBS}
    if not PY.exists():
        return {**res, "skipped": "no .venv/bin/python in the repo"}
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        base, secs = suite(copy(tmp / "base" / "w"), 1800)
        res["suite_seconds"] = round(secs, 1)
        if base != "pass":
            return {**res, "skipped": "the unmutated suite does not pass in a scratch copy"}
        res["coverage"] = coverage(tmp / "base" / "w")
        (tmp / "pyproject.toml").write_text('[tool.mutmut]\nsource_paths = ["."]\n')  # mutmut reads its settings from the
        os.chdir(tmp)  # current folder: only where the code is (which it insists on), every other setting at its default
        t = time.time()
        found = {f: mutants_of(f) for f in code}
        take = shares({f: len((R / f).read_text().splitlines()) for f in code}, {f: len(m) for f, (_, m) in found.items()}, N)
        picked = [(f, i) for f in code for i in sorted(random.Random(f"{SEED}:{f}").sample(range(len(found[f][1])), take[f]))]
        made = {(f, i): changed(f, found[f][0], found[f][1][i]) for f, i in picked}
        limit = max(30, 10 * secs)
        res |= {"mutants_possible": sum(len(m) for _, m in found.values()), "timeout_seconds": round(limit, 1), "list_seconds": round(time.time() - t, 1)}
        works = queue.Queue()
        for j in range(JOBS):
            works.put(copy(tmp / f"j{j}" / "w"))

        def one(pick):
            f, i = pick
            work = works.get()
            try:
                (work / f).write_text(made[f, i][1])
                return suite(work, limit)[0]
            finally:
                shutil.copy2(R / f, work / f); works.put(work)

        t = time.time()
        with cf.ThreadPoolExecutor(max_workers=JOBS) as pool:
            outcome = list(pool.map(one, picked))
        res["mutation_seconds"] = round(time.time() - t, 1)
    n = {k: outcome.count(k) for k in ("fail", "pass", "timeout")}
    res |= {"run": len(picked), "caught": n["fail"], "missed": n["pass"], "timeout": n["timeout"],
            "share": round((n["fail"] + n["timeout"]) / len(picked), 3) if picked else None,
            "per_file": {f: {"lines": len((R / f).read_text().splitlines()), "possible": len(found[f][1]), "run": take[f],
                             "missed": sum(o == "pass" for (g, _), o in zip(picked, outcome) if g == f)} for f in code},
            "mutants": [{"file": f, "line": made[f, i][0], "outcome": {"fail": "caught", "pass": "missed"}.get(o, o)} for (f, i), o in zip(picked, outcome)]}
    return res


if __name__ == "__main__":
    print(json.dumps(main()))
