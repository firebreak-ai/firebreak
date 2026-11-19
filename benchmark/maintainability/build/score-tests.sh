#!/usr/bin/env bash
# What one finished build's own tests are worth, at its last checkpoint: score-tests.sh <run-dir>
# The last checkpoint tag of <run-dir>/project is cloned to a scratch folder with a fresh .venv from its own requirements,
# the hidden tests are laid out beside a second copy as hidden-tests.sh lays them out, and measure/testq.py build does the
# rest -> <run-dir>/testq.json. MUTANTS=<n> (default 600), JOBS=<n> (default 8). The project itself is left as it is.
# Refuses while lock.sh's lock is on: the hidden tests cannot be read then.
set -uo pipefail
[ $# -eq 1 ] || { echo "usage: score-tests.sh <run-dir>" >&2; exit 2; }
. "$(dirname "$0")/../settings.sh"; need SCB_PROBLEMS; R=$(realpath "$1"); W="$R/project"
[ -e "$LOCAL/.locked" ] && { echo "refusing: the answers are locked; run $K/change/lock.sh unlock first" >&2; exit 2; }
[ -d "$W/.git" ] || { echo "no project in $R" >&2; exit 2; }
PROB=$(sed -n 's/.* claude-opus-5-5 \([^ ]*\).*/\1/p' "$R/arm.txt"); P=$SCB_PROBLEMS/$PROB
LAST=$(git -C "$W" tag | grep -x 'cp[0-9]*' | sort -V | tail -1); CP=${LAST#cp}
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
git -c advice.detachedHead=false clone -q --branch "$LAST" "$W" "$T/code" || exit 2
(cd "$T/code" && uv venv -q .venv && { [ -f requirements-dev.txt ] && uv pip install -q --python .venv/bin/python -r requirements-dev.txt
   grep -qv '^[[:space:]]*\(#.*\)\?$' requirements.txt 2>/dev/null && uv pip install -q --python .venv/bin/python -r requirements.txt
   .venv/bin/python -c 'import pytest' 2>/dev/null || uv pip install -q --python .venv/bin/python pytest; }) > "$R/testq-venv.log" 2>&1
RUNNER=$LOCAL/testq-runner
[ -x "$RUNNER/bin/python" ] || { uv venv -q "$RUNNER" && uv pip install -q --python "$RUNNER/bin/python" pytest pytest-timeout jsonschema deepdiff \
  $(sed -n '/^test_dependencies:/,/^[^ -]/s/^[[:space:]]*-[[:space:]]*\(.*\)/\1/p' "$P/config.yaml"); } >> "$R/testq-venv.log" 2>&1
H=$T/hidden; mkdir "$H"; git -C "$T/code" archive HEAD | tar -x -C "$H"; rm -rf "$H/tests" "$H/conftest.py"; mkdir "$H/tests"
cp "$P/tests/conftest.py" "$H/tests/"
for f in "$P"/tests/*; do b=$(basename "$f"); case $b in test_checkpoint_*) n=${b#test_checkpoint_}; n=${n%.py}; [ "$n" -le "$CP" ] && cp "$f" "$H/tests/";; conftest.py) ;; *) cp -r "$f" "$H/tests/";; esac; done
printf '[pytest]\ntestpaths = tests\nmarkers =\n    error: e\n    functionality: f\n    regression: r\n' > "$H/pytest.ini"; echo "checkpoint_$CP" > "$H/checkpoint.txt"
EF=$(sed -n 's/^entry_file:[[:space:]]*//p' "$P/config.yaml")
uv run -q --script "$K/measure/testq.py" build "$T/code" --n "${MUTANTS:-600}" --jobs "${JOBS:-8}" --hidden "$H" --entry "$EF.py" --runner "$RUNNER/bin/python" > "$R/testq.json.new" 2> "$R/testq.err" \
  && mv "$R/testq.json.new" "$R/testq.json" && python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(json.dumps(d.get("summary") or d.get("skipped")))' "$R/testq.json"
