"""Runs side by side: table.py [--ref <base-name>] <out-dir>...

One row per run (from each <out-dir>/measure.json; change and base names come from run.json through measure.py), then the
median of every measure per change and base when a group holds more than one run or there are several bases, and with
--ref each median as a ratio to the named base's median for the same change.
Columns: new, regr = hidden cases passed/total; own = own suite passed/failed; looks, files = Read/Grep/Glob/Bash calls
and distinct files read before the first code edit; calls, min; code = code files changed, +/- lines, chg = the two
together; places = diff hunks in code; funcs = functions touched; mod = pre-existing functions modified, then their max
length, max cyclomatic, max cognitive complexity and summed length (held); written = code lines the session's recorded
edits wrote, rewr = those a later edit changed or removed, share = rewr / written; runs = test runs/failed; t:c =
test-to-code changed lines; broke = old tests failing; missed = hidden failures on a green own suite; out = paths outside
the work folder named in the session's tool calls.
Marks in the run rows: ? after share = the edit record is incomplete (rework.reliable is false), so written and rewr
miss work; ! after out = one of the paths names an answer or sibling-run location (audit.touched_answers).
The medians take every run, marked or not; unrel and ans count the marked runs in each group.
"""
import json, pathlib, statistics, sys

args = sys.argv[1:]
ref = args.pop(args.index("--ref") + 1) if "--ref" in args else None
args = [a for a in args if a != "--ref"]
frac = lambda a, b: "-" if a is None else f"{a}/{b}"
show = lambda v: "-" if v is None else f"{v:g}" if isinstance(v, float) else str(v)
# Numeric measures: column name -> path in measure.json.
NUM = {"looks": "attention.looks_before_first_code_edit", "files": "attention.files_read_before_first_code_edit",
       "calls": "attention.tool_calls", "min": "attention.minutes", "code": "landed.code.files", "+": "landed.code.lines_added",
       "-": "landed.code.lines_removed", "chg": "landed.code.lines_changed", "places": "landed.code.places", "funcs": "landed.code.functions_touched",
       "mod": "difficulty.functions", "len": "difficulty.length.max", "cc": "difficulty.cyclomatic.max",
       "cog": "difficulty.cognitive.max", "held": "difficulty.lines_held", "written": "rework.lines_written",
       "rewr": "rework.lines_rewritten", "share": "rework.rewritten_share", "runs": "rework.test_runs",
       "runs-f": "rework.test_runs_failed", "t:c": "own_tests.test_to_code_lines", "broke": "own_tests.old_tests_failing",
       "missed": "missed.missed_by_own_tests", "out": "audit.outside", "new-f": "outcome.new_failed", "regr-f": "outcome.regression_failed"}
MARK = {"share": ("rework.reliable", False, "?"), "out": ("audit.touched_answers", True, "!")}  # column -> field, marked value, mark


def get(m, path):
    for k in path.split("."):
        m = m.get(k) if isinstance(m, dict) else None
    return m


runs = []
for d in args:
    f = pathlib.Path(d) / "measure.json"
    if not f.exists():
        print(f"no measure.json in {d}", file=sys.stderr); continue
    m = json.loads(f.read_text()); o = m["outcome"]
    m["attention"]["minutes"] = round(m["attention"]["seconds"] / 60, 1)
    o["new_failed"] = None if o["new_total"] is None else o["new_total"] - o["new_passed"]
    o["regression_failed"] = None if o["regression_total"] is None else o["regression_total"] - o["regression_passed"]
    m["landed"]["code"]["lines_changed"] = m["landed"]["code"]["lines_added"] + m["landed"]["code"]["lines_removed"]
    if m.get("audit"):
        m["audit"]["outside"] = len(m["audit"]["outside_paths"])
    runs.append((pathlib.Path(d).name, m))


def table(head, rows):
    width = [max(len(str(r[i])) for r in [head] + rows) for i in range(len(head))]
    for r in [head] + rows:
        print("  ".join(str(c).ljust(w) if i < 3 else str(c).rjust(w) for i, (c, w) in enumerate(zip(r, width))).rstrip())
    print()


cols = [c for c in NUM if c not in ("new-f", "regr-f")]
marked = lambda m, c: c in MARK and get(m, MARK[c][0]) is MARK[c][1]
table(["run", "change", "base", "new", "regr", "own"] + cols,
      [[name, m["change"], m["base"], frac(m["outcome"]["new_passed"], m["outcome"]["new_total"]),
        frac(m["outcome"]["regression_passed"], m["outcome"]["regression_total"]),
        frac(m["outcome"]["own_passed"], m["outcome"]["own_failed"])] + [show(get(m, NUM[c])) + (MARK[c][2] if marked(m, c) else "") for c in cols]
       for name, m in runs])

groups = {}
for _, m in runs:
    groups.setdefault((m["change"], m["base"]), []).append(m)


def median(ms, path):
    v = [x for x in (get(m, path) for m in ms) if isinstance(x, (int, float)) and not isinstance(x, bool)]
    return statistics.median(v) if v else None


med = {k: {c: median(ms, p) for c, p in NUM.items()} for k, ms in groups.items()}
if len(groups) < len(runs) or len({b for _, b in groups}) > 1:
    print("Medians per change and base (n = runs; new-f, regr-f = hidden cases not passed; unrel = runs with an incomplete edit "
          "record, ans = runs that named an answer location)")
    table(["change", "base", "n"] + list(NUM) + ["unrel", "ans"], [[c, b, len(groups[c, b])] + [show(med[c, b][k]) for k in NUM] +
          [sum(marked(m, k) for m in groups[c, b]) for k in MARK] for c, b in sorted(groups)])
if ref:
    rows = []
    for c, b in sorted(groups):
        base = med.get((c, ref))
        if base is None:
            print(f"no runs of reference base {ref} for change {c}", file=sys.stderr); continue
        ratio = lambda k: "-" if med[c, b][k] is None or not base[k] else f"{med[c, b][k] / base[k]:.2f}"
        rows.append([c, b, len(groups[c, b])] + [ratio(k) for k in NUM])
    print(f"Each median as a ratio to base {ref} for the same change (- where {ref}'s median is 0 or missing)")
    table(["change", "base", "n"] + list(NUM), rows)
