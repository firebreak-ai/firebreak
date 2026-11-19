#!/usr/bin/env -S uv run -q --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["radon==6.0.1", "cognitive_complexity==1.3.0"]
# ///
"""The code as it stands, repos side by side: state.py [--ref <name>] [--json <path>] [--mutants [N]] [--seed S] [--jobs J] <repo>...

One row per measure, one column per git repo, and with --ref a column beside each other repo giving its number as a ratio
to the named repo's (- where that one's is 0 or missing). A repo is named after its folder, or the folder above when that
is "project". --json also writes everything to a file. Nothing else is written or kept between runs.

Code, over the tracked code files (measure.py's rule: .py files that are not test files):
files; lines = all their lines; largest = lines of the longest file; funcs = defs (measure.py's rule: every function,
method and nested def); longest, len mean, len median = lines of a def, decorators to last line; cc>10 = defs with radon
cyclomatic complexity above 10; cc, cc mean = highest and mean cyclomatic complexity of a def; cog>15, cog, cog mean = the
same for cognitive complexity (same tools and versions as measure.py; a nested def also counts inside its parent's cog).
From scb-check 0.1.3 (SlopCodeBench's checker, run as quality.py runs it, on a copy holding only the code files): loc = its
count of source lines; dup = lines in duplicated blocks (clone_loc); erosion; verbosity.

Smells, EXACT's four groups: ruff findings on the same copy, with the rule selection, limits and grouping of the EXACT
lab's Python arm (see RUFF_TOML and GROUPS). smells = the four together; smells/kloc = per 1,000 of "lines".

Tests, over the tracked test files (measure.py's rule: under tests/, test_*.py, conftest.py): test files; test lines;
tests = defs whose name starts with "test"; test/code = test lines per code line.

With --mutants (slow, see mutants.py): suite s = seconds of one plain run of the repo's own suite; coverage % = code
statements that run executes; mutants = sampled changes run (N, default 150, seed 1); caught, missed, timeout; catch =
(caught + timeout) / mutants.
"""
import json, pathlib, shutil, statistics, subprocess, sys, tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from measure import cyclomatic, functions, git, is_code, is_test

# The lint settings of EXACT's Python stack, copied from agentic_coding_lab/experiments/stacks/python-pytest/pyproject.toml
# (Copyright (c) 2026 Marco Emrich, MIT; see NOTICE.md)
# ([tool.ruff.lint*]); ruff is pinned to the version in its requirements-dev.txt. target-version stands for that file's
# requires-python = ">=3.11". analyze-run.sh runs `ruff check src/ --output-format json` with these and no other flags.
RUFF = "ruff@0.16.8"
RUFF_TOML = """target-version = "py311"
[lint]
select = ["C901", "PLR", "PLW", "SIM", "ARG", "F", "B", "RET", "RUF"]
[lint.mccabe]
max-complexity = 10
[lint.pylint]
max-args = 4
max-branches = 12
max-statements = 30
max-nested-blocks = 3
"""
# The grouping of analyze-run.sh ("Python smells come from ruff"): these three lists, every other finding is "other",
# and C901 is counted nowhere (there it only carries the cyclomatic score).
GROUPS = {"smell complexity": {"PLR0912", "PLR0913", "PLR0915", "PLR1702"}, "smell duplication": {"PLR0133", "SIM114"},
          "smell numbers": {"PLR2004"}}
ROWS = ["files", "lines", "largest", "funcs", "longest", "len mean", "len median", "cc>10", "cc", "cc mean", "cog>15", "cog",
        "cog mean", "loc", "dup", "erosion", "verbosity", *GROUPS, "smell other", "smells", "smells/kloc",
        "test files", "test lines", "tests", "test/code"]
MUTANT_ROWS = ["suite s", "coverage %", "mutants", "caught", "missed", "timeout", "catch"]

args = sys.argv[1:]


def take(name):
    """Remove an option and its value from args; the value, or None when the option is absent."""
    if name not in args:
        return None
    i = args.index(name); args.pop(i)
    return args.pop(i) if i < len(args) else None


ref, out, seed, jobs = take("--ref"), take("--json"), take("--seed") or "1", take("--jobs") or "4"
mutants = None
if "--mutants" in args:
    i = args.index("--mutants"); args.pop(i)
    mutants = args.pop(i) if i < len(args) and args[i].isdigit() else "150"
show = lambda v: "-" if v is None else f"{v:.3f}" if isinstance(v, float) else str(v)
mean = lambda v: round(statistics.mean(v), 3) if v else None


def tool(*cmd, cwd=None):
    """The JSON a command prints, or None."""
    try:
        return json.loads(subprocess.run(cmd, capture_output=True, text=True, cwd=cwd).stdout)
    except json.JSONDecodeError:
        return None


def state(repo):
    from cognitive_complexity.api import get_cognitive_complexity
    tracked = [f for f in git(repo, "ls-files").splitlines() if (repo / f).is_file()]
    files, tests = [f for f in tracked if is_code(f)], [f for f in tracked if f.endswith(".py") and is_test(f)]
    sizes, lengths, cc, cog = [], [], [], []
    with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as cfg:
        for f in files:
            text = (repo / f).read_text()
            (pathlib.Path(tmp) / f).parent.mkdir(parents=True, exist_ok=True); shutil.copy(repo / f, pathlib.Path(tmp) / f)
            sizes.append(len(text.splitlines())); defs = functions(text); by_line = cyclomatic(text) if defs else {}
            for first, last, node in defs.values():
                lengths.append(last - first + 1); cc.append(by_line.get(node.lineno, 0)); cog.append(get_cognitive_complexity(node))
        (pathlib.Path(cfg) / "ruff.toml").write_text(RUFF_TOML)
        found = tool("uvx", "-q", RUFF, "check", "--config", f"{cfg}/ruff.toml", "--no-cache", "--exit-zero", "--output-format", "json", *files, cwd=tmp) if files else []
        scb = tool("uvx", "-q", "scb-check==0.1.3", "check", "--report", "--include-all", tmp) or {}
    codes = None if found is None else [x["code"] for x in found if x.get("code") and x["code"] != "C901"]  # no code = a file ruff cannot parse
    smell = {g: None if codes is None else sum(c in rules for c in codes) for g, rules in GROUPS.items()}
    smell["smell other"] = None if codes is None else len(codes) - sum(smell.values())
    test_text = [(repo / f).read_text() for f in tests]
    test_lines = sum(len(t.splitlines()) for t in test_text)
    return {"files": len(files), "lines": sum(sizes), "largest": max(sizes, default=0), "funcs": len(lengths), "longest": max(lengths, default=0),
            "len mean": mean(lengths), "len median": statistics.median(lengths) if lengths else None,
            "cc>10": sum(c > 10 for c in cc), "cc": max(cc, default=0), "cc mean": mean(cc),
            "cog>15": sum(c > 15 for c in cog), "cog": max(cog, default=0), "cog mean": mean(cog),
            "loc": scb.get("total_loc"), "dup": scb.get("clone_loc"), "erosion": scb.get("erosion"), "verbosity": scb.get("verbosity"),
            **smell, "smells": None if codes is None else len(codes),
            "smells/kloc": None if codes is None or not sizes else round(1000 * len(codes) / sum(sizes), 3),
            "test files": len(tests), "test lines": test_lines,
            "tests": sum(q.split(".")[-1].startswith("test") for t in test_text for q in functions(t)),
            "test/code": round(test_lines / sum(sizes), 3) if sum(sizes) else None}


def mutation(repo):
    """mutants.py's result for one repo: (the table's numbers, everything it reported)."""
    m = tool("uv", "run", "-q", "--script", str(HERE / "mutants.py"), str(repo), "--n", mutants, "--seed", seed, "--jobs", jobs) or {"skipped": "mutants.py failed"}
    if "skipped" in m:
        print(f"{repo}: no mutation result: {m['skipped']}", file=sys.stderr)
    return {"suite s": m.get("suite_seconds"), "coverage %": (m.get("coverage") or {}).get("pct"), "mutants": m.get("run"),
            "caught": m.get("caught"), "missed": m.get("missed"), "timeout": m.get("timeout"), "catch": m.get("share")}, m


def table(head, rows):
    width = [max(len(str(r[i])) for r in [head] + rows) for i in range(len(head))]
    for r in [head] + rows:
        print("  ".join(str(c).ljust(w) if i == 0 else str(c).rjust(w) for i, (c, w) in enumerate(zip(r, width))).rstrip())
    print()


vals, detail, paths = {}, {}, {}
for a in args:
    repo = pathlib.Path(a).resolve()
    name = repo.parent.name if repo.name == "project" else repo.name
    vals[name], paths[name] = state(repo), str(repo)
    if mutants:
        extra, detail[name] = mutation(repo)
        vals[name] |= extra
if ref and ref not in vals:
    print(f"no repo named {ref}", file=sys.stderr); ref = None
ratio = lambda n, k: None if vals[n][k] is None or not vals[ref][k] else round(vals[n][k] / vals[ref][k], 2)
ratios = {n: {k: ratio(n, k) for k in vals[n]} for n in vals if n != ref} if ref else {}
rows = ROWS + (MUTANT_ROWS if mutants else [])
table(["measure"] + [h for n in vals for h in [n] + ([f"/{ref}"] if n in ratios else [])],
      [[k] + [c for n in vals for c in [show(vals[n][k])] + (["-" if ratios[n][k] is None else f"{ratios[n][k]:.2f}"] if n in ratios else [])] for k in rows])
if ref:
    print(f"/{ref} = the number to its left as a ratio to {ref}'s (- where {ref}'s is 0 or missing)")
if out:
    pathlib.Path(out).write_text(json.dumps({"ref": ref, "ruff": RUFF, "measures": rows, "repos": {n: {"path": paths[n], "values": vals[n],
                                 "ratios": ratios.get(n), "mutation": detail.get(n)} for n in vals}}, indent=1))
    print(f"wrote {out}")
