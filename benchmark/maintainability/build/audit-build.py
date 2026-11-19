"""Where a build's sessions reached outside their work folder: audit-build.py <run-dir>  -> <run-dir>/audit.json + a line a checkpoint

Applies measure/measure.py's audit (see "audit" in its docstring) to every session record of a chained run: cpN.jsonl
(one session a checkpoint) and cpN-t*.jsonl (Firebreak's turns). The run folder is the sessions' own; the answer
locations are the kit, the problem set, other sessions' records, any EXTRA_ANSWER_PATHS and the folder holding the work folder. Left out, as
there: /tmp, /dev and the Python installation the project's .venv points at.
"""
import json, pathlib, re, sys

K = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(K.parent / "measure"))
from measure import ANSWERS, audit

R = pathlib.Path(sys.argv[1]).resolve()
cfg = R / "project/.venv/pyvenv.cfg"  # its "home" line names the bin folder of the Python installation the .venv points at
python = [str(pathlib.Path(l.split("=", 1)[1].strip()).parent) for l in (cfg.read_text().splitlines() if cfg.exists() else []) if l.startswith("home")]
by_cp = {}
for f in sorted(R.glob("cp*.jsonl")):
    if m := re.fullmatch(r"cp(\d+)(-t.*)?", f.stem):
        by_cp.setdefault(int(m[1]), {})[f.name] = audit(f, python, [str(R)], ANSWERS)
(R / "audit.json").write_text(json.dumps({f"cp{cp}": recs for cp, recs in sorted(by_cp.items())}, indent=1))
for cp, recs in sorted(by_cp.items()):
    seen = [a for a in recs.values() if a]
    outside, answers = sorted({p for a in seen for p in a["outside_paths"]}), sorted({p for a in seen for p in a["answer_paths"]})
    print(f"cp{cp} | {len(recs)} records, {len(recs) - len(seen)} without a work folder | outside paths {len(outside)}"
          f"{': ' + ' '.join(outside) if outside else ''}{' | NAMES AN ANSWER LOCATION: ' + ' '.join(answers) if answers else ''}")
if not by_cp:
    print("no session records (cpN.jsonl) in", R)
