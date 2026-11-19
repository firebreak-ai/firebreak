#!/usr/bin/env bash
# Run SlopCodeBench's hidden tests for one checkpoint (with earlier checkpoints' tests as regression), as its PytestRunner does.
# The procedure (which test files, the pytest options and markers, the pass groups) follows SlopCodeBench (MIT, see NOTICE.md).
# Usage: hidden-tests.sh <workspace> <checkpoint-number> [problem] [report.json]   (prints pass counts by test group)
set -euo pipefail
WS=$(realpath "$1"); CP=$2; PROB=${3:-etl_pipeline}; OUT_ARG=${4:-}
. "$(dirname "$0")/../settings.sh"; need SCB_PROBLEMS; P=$SCB_PROBLEMS/$PROB
OUT=$(realpath -m "${OUT_ARG:-$(dirname "$WS")/hidden-$(basename "$WS")-cp$CP.json}")
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
cp -r "$WS"/. "$T"/; rm -rf "$T/tests" "$T/.venv" "$T/conftest.py"; mkdir "$T/tests"
cp "$P/tests/conftest.py" "$T/tests/"
for f in "$P"/tests/*; do b=$(basename "$f"); case $b in test_checkpoint_*) n=${b#test_checkpoint_}; n=${n%.py}; [ "$n" -le "$CP" ] && cp "$f" "$T/tests/";; conftest.py) ;; *) cp -r "$f" "$T/tests/";; esac; done
printf '[pytest]\ntestpaths = tests\nmarkers =\n    error: e\n    functionality: f\n    regression: r\n' > "$T/pytest.ini"
cd "$T"
if [ -f requirements.txt ]; then uv venv -q .venv >/dev/null 2>&1; uv pip install -q --python .venv/bin/python -r requirements.txt >/dev/null 2>&1 || true; fi
EF=$(sed -n 's/^entry_file:[[:space:]]*//p' "$P/config.yaml"); ENTRY="$T/.venv/bin/python $EF.py"
DEPS=$(sed -n '/^test_dependencies:/,/^[^ -]/s/^[[:space:]]*-[[:space:]]*\(.*\)/--with \1/p' "$P/config.yaml")
[ -x .venv/bin/python ] || uv venv -q .venv
uvx -q $DEPS --with pytest-json-report --with pytest-timeout --with jsonschema --with deepdiff pytest -q -p no:cacheprovider --timeout=60 \
  --entrypoint="$ENTRY" --checkpoint=checkpoint_$CP --confcutdir=tests --json-report --json-report-file="$OUT" tests >/dev/null 2>&1 || true
python3 - "$OUT" "$CP" <<'PY'
import json,sys,re
r=json.load(open(sys.argv[1])); cp=int(sys.argv[2]); g={}
for t in r["tests"]:
    n=int(re.search(r"test_checkpoint_(\d+)",t["nodeid"]).group(1)); kws=t.get("keywords",[])
    grp="regression" if n<cp else ("error" if "error" in kws else "functionality" if "functionality" in kws else "core")
    a=g.setdefault(grp,[0,0]); a[1]+=1; a[0]+= t["outcome"]=="passed"
print(" ".join(f"{k}={v[0]}/{v[1]}" for k,v in sorted(g.items())))
PY
