#!/usr/bin/env bash
# Score one finished run, serially: score.sh <change> <out-dir>
# <change> names a folder of local/changes-<problem>/ holding the change's hidden tests (a path's last part is the name).
# Writes <out-dir>/hidden-new.json (the change's hidden cases), hidden-regression.json (the change's regression-tests
# through its run-regression.sh, else the problem's original suite through build/hidden-tests.sh), then measure.json.
# Run one at a time on a quiet machine: the speed cases are timed. The program runs under the project's own .venv python
# for the new cases; the two regression runners build their own environment from requirements.txt.
# Refuses while lock.sh's lock is on: the hidden tests and the finished runs cannot be read then.
set -uo pipefail
[ $# -eq 2 ] || { echo "usage: score.sh <change> <out-dir>" >&2; exit 2; }
. "$(dirname "$0")/../settings.sh"; need SCB_PROBLEMS; PROBLEM=${PROBLEM:-circuit_eval}; C=$LOCAL/changes-$PROBLEM/$(basename "$1"); OUT=$(realpath "$2"); W="$OUT/project"
[ -e "$LOCAL/.locked" ] && { echo "refusing: the answers are locked; run $K/change/lock.sh unlock first" >&2; exit 2; }
[ -d "$C/tests" ] || { echo "no hidden tests in $C" >&2; exit 2; }
[ -f "$OUT/exit" ] || { echo "no finished run in $OUT" >&2; exit 2; }
EF=$(sed -n 's/^entry_file:[[:space:]]*//p' "$SCB_PROBLEMS/$PROBLEM/config.yaml")
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
# The program without its own tests and pytest settings, so only the hidden cases and their conftest are collected.
tar -C "$W" --exclude=./.git --exclude=./.venv --exclude=./tests --exclude=./conftest.py --exclude=./pytest.ini \
    --exclude=./pyproject.toml --exclude=./setup.cfg --exclude=__pycache__ -cf - . | tar -C "$T" -xf -
mkdir "$T/tests"; tar -C "$C/tests" --exclude=__pycache__ -cf - . | tar -C "$T/tests" -xf -
rm -f "$OUT/hidden-new.json" "$OUT/hidden-regression.json"
# 600 s a case and 2 h overall: an unchanged program runs most speed cases into their limits (about 9 minutes in all).
(cd "$T" && timeout 7200 uvx -q --with pytest-json-report --with pytest-timeout pytest -q -p no:cacheprovider --timeout=600 --rootdir=. \
   --entrypoint="$W/.venv/bin/python $T/$EF.py" --confcutdir=tests --json-report --json-report-file="$OUT/hidden-new.json" tests) > "$OUT/hidden-new.txt" 2>&1 || true
if [ -x "$C/run-regression.sh" ] || [ -f "$C/run-regression.sh" ]; then
  bash "$C/run-regression.sh" "$W" "$OUT/hidden-regression.json" > "$OUT/hidden-regression.txt" 2>&1 || true
else
  "$K/build/hidden-tests.sh" "$W" "${CHECKPOINT:-8}" "$PROBLEM" "$OUT/hidden-regression.json" > "$OUT/hidden-regression.txt" 2>&1 || true
fi
uv run -q "$K/measure/measure.py" "$C" "$OUT"
