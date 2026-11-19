"""Per-checkpoint numbers for one chained run: quality.py <run-dir>   -> <run-dir>/quality.json and a table on stdout

For each tag cpN in the run's project: hidden-test pass counts (hidden-cpN.json), cost and seconds for that checkpoint,
lines changed since cpN-1 (code vs tests), and scb-check 0.1.3 (SlopCodeBench's pinned quality checker, fetched from PyPI; see NOTICE.md) on the snapshot,
once on everything the agent wrote (as SlopCodeBench does) and once on code without tests.
Not counted: the workflow's own files (.claude, .fbk), the stack skeleton's conftest.py, prompt.md.
"""
import glob, json, pathlib, re, shutil, subprocess, sys, tempfile

R = pathlib.Path(sys.argv[1]).resolve(); W = R / "project"
SKIP = {".claude", ".fbk", ".venv", "conftest.py", "prompt.md", ".gitignore", "experiment-done.txt"}
git = lambda *a: subprocess.run(["git", "-C", str(W), *a], capture_output=True, text=True).stdout
is_test = lambda f: f.startswith("tests/") or "/tests/" in f or pathlib.Path(f).name.startswith("test_")
skipped = lambda f: f.split("/")[0] in SKIP


def scb(d):
    p = subprocess.run(["uvx", "-q", "scb-check==0.1.3", "check", "--report", "--include-all", str(d)], capture_output=True, text=True)
    try:
        r = json.loads(p.stdout)
    except json.JSONDecodeError:
        return {}
    keep = ["verbosity", "erosion", "cog_erosion", "total_loc", "clone_loc", "trivial_wrappers", "total_functions",
            "high_cc_functions", "high_cog_functions"]
    return {k: r.get(k) for k in keep}


def hidden(cp):
    f = R / f"hidden-cp{cp}.json"
    if not f.exists():
        return {}
    g = {}
    for t in json.loads(f.read_text())["tests"]:
        n = int(re.search(r"test_checkpoint_(\d+)", t["nodeid"]).group(1)); kws = t.get("keywords", [])
        grp = "regression" if n < cp else "error" if "error" in kws else "functionality" if "functionality" in kws else "core"
        a = g.setdefault(grp, [0, 0]); a[1] += 1; a[0] += t["outcome"] == "passed"
    return g


def cost(cp):
    total = 0.0
    for f in glob.glob(str(R / f"cp{cp}.json")) + glob.glob(str(R / f"cp{cp}-t*.json")):
        try:
            total += json.load(open(f)).get("total_cost_usd") or 0
        except Exception:
            pass
    return round(total, 2)


rows = []
tags = sorted((int(t[2:]) for t in git("tag").split() if re.fullmatch(r"cp\d+", t) and t != "cp0"))
for cp in tags:
    lines = {"code": [0, 0], "tests": [0, 0]}
    for l in git("diff", "--numstat", f"cp{cp-1}", f"cp{cp}").splitlines():
        a, d, f = l.split("\t")
        if skipped(f) or not f.endswith(".py"):
            continue
        k = "tests" if is_test(f) else "code"
        lines[k][0] += int(a) if a.isdigit() else 0; lines[k][1] += int(d) if d.isdigit() else 0
    with tempfile.TemporaryDirectory() as t:
        full = pathlib.Path(t) / "full"; full.mkdir()
        subprocess.run(f"git -C {W} archive cp{cp} | tar -x -C {full}", shell=True, check=True)
        for s in SKIP:
            p = full / s
            shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink(missing_ok=True)
        code = pathlib.Path(t) / "code"; shutil.copytree(full, code)
        for p in sorted(code.rglob("*"), key=lambda p: -len(p.parts)):
            rel = str(p.relative_to(code))
            if p.exists() and is_test(rel):
                shutil.rmtree(p) if p.is_dir() else p.unlink()
        rows.append({"cp": cp, "hidden": hidden(cp), "cost": cost(cp),
                     "seconds": int((R / f"cp{cp}.seconds").read_text()) if (R / f"cp{cp}.seconds").exists() else None,
                     "lines_changed": lines, "scb_all": scb(full), "scb_code": scb(code)})
(R / "quality.json").write_text(json.dumps(rows, indent=1))
print(f"{R.name}")
print("cp | strict pass | core | cost $ | min | code +/- | test +/- | code loc | erosion | verbosity | high-cc fns | erosion(all) | verbosity(all)")
for r in rows:
    h = r["hidden"]; tot = [sum(v[0] for v in h.values()), sum(v[1] for v in h.values())]
    c, a = r["scb_code"], r["scb_all"]
    print(f"{r['cp']} | {tot[0]}/{tot[1]} | {'/'.join(map(str, h.get('core', ['-'])))} | {r['cost']} | {(r['seconds'] or 0)//60} | "
          f"+{r['lines_changed']['code'][0]}/-{r['lines_changed']['code'][1]} | +{r['lines_changed']['tests'][0]}/-{r['lines_changed']['tests'][1]} | "
          f"{c.get('total_loc')} | {c.get('erosion', 0):.3f} | {c.get('verbosity', 0):.3f} | {c.get('high_cc_functions')} | "
          f"{a.get('erosion', 0):.3f} | {a.get('verbosity', 0):.3f}")
