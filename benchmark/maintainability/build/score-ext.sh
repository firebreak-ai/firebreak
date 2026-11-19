#!/usr/bin/env bash
# Score a build that extend-builds.sh continued: score-ext.sh <run-dir>
# For each added checkpoint (extension.txt: "cpN <change>"), the code at tag cpN is run against that change's hidden cases
# and against the hidden regression suite as amended by every change made so far; the earlier changes' hidden cases are
# run again as well. Results go to <run-dir>/ext-score/cpN.<what>.json and one summary line each. Run alone: speed cases are timed.
set -uo pipefail
. "$(dirname "$0")/../settings.sh"; need SCB_PROBLEMS; R=$(realpath "$1"); P=$R/project; C=$LOCAL/changes-${PROBLEM:-circuit_eval}; O=$R/ext-score; mkdir -p "$O"
[ -e "$LOCAL/.locked" ] && { echo "refusing: the answers are locked" >&2; exit 2; }
count() { python3 - "$1" "${2:-}" <<'PY'
import json,sys
try: r=json.load(open(sys.argv[1]))
except Exception as e: print("no report"); sys.exit()
skip=set(filter(None,sys.argv[2].split(",")))
t=[x for x in r["tests"] if not any(s in x["nodeid"] for s in skip)]
bad=[x["nodeid"].split("::")[-1] for x in t if x["outcome"] not in("passed","skipped")]
print(f"{len(t)-len(bad)}/{len(t)}", "failing:", bad[:12] if bad else "none")
PY
}
newtests() { # <code-dir> <change> <out.json>
  local T; T=$(mktemp -d); tar -C "$1" --exclude=./tests --exclude=./conftest.py --exclude=./pytest.ini --exclude=./pyproject.toml --exclude=./setup.cfg -cf - . | tar -C "$T" -xf -
  mkdir "$T/tests"; tar -C "$C/$2/tests" --exclude=__pycache__ -cf - . | tar -C "$T/tests" -xf -
  (cd "$T" && timeout 7200 uvx -q --with pytest-json-report --with pytest-timeout pytest -q -p no:cacheprovider --timeout=600 --rootdir=. \
    --entrypoint="$P/.venv/bin/python $T/circopt.py" --confcutdir=tests --json-report --json-report-file="$3" tests) > "${3%.json}.txt" 2>&1 || true; rm -rf "$T"; }
stack() {  # the regression suite after both the error-reporting and the unknown-values change: 02's amended suite with 03's amendments merged in, made once
  local S=$C/stack-0302/regression-tests B=$SCB_PROBLEMS/${PROBLEM:-circuit_eval}/tests f n; [ -d "$S" ] && return
  mkdir -p "$S.new" && cp "$C"/02-all-errors/regression-tests/*.py "$S.new/" || return 1
  for f in "$C"/03-unknown-values/regression-tests/*.py; do n=$(basename "$f"); cmp -s "$f" "$B/$n" && continue
    if cmp -s "$S.new/$n" "$B/$n"; then cp "$f" "$S.new/$n"; else git merge-file -q "$S.new/$n" "$B/$n" "$f" || { echo "the two changes amend $n in conflicting ways" >&2; return 1; }; fi; done
  mv "$S.new" "$S"; }
done_=""
while read -r cp ch; do
  D=$(mktemp -d); git -C "$P" archive "$cp" | tar -x -C "$D"
  case "$done_ $ch" in *02-all-errors*03-unknown*|*03-unknown*02-all-errors*) stack || exit 2; RT="$C/stack-0302/regression-tests"; RS=$C/02-all-errors/run-regression.sh;;
    *03-unknown*) RT=$C/03-unknown-values/regression-tests; RS=$C/03-unknown-values/run-regression.sh;;
    *02-all-errors*) RT=$C/02-all-errors/regression-tests; RS=$C/02-all-errors/run-regression.sh;; *) RT=; RS=;; esac
  if [ -n "$RS" ]; then bash "$RS" "$D" "$O/$cp.regression.json" "$RT" > "$O/$cp.regression.txt" 2>&1 || true
  else "$K/build/hidden-tests.sh" "$D" 8 "${PROBLEM:-circuit_eval}" "$O/$cp.regression.json" > "$O/$cp.regression.txt" 2>&1 || true; fi
  echo "$cp $ch regression $(count "$O/$cp.regression.json")"
  for c in $done_ $ch; do newtests "$D" "$c" "$O/$cp.new-$c.json"; skip=; [ "$c" = 02-all-errors ] && case "$done_" in *03-unknown*) skip=test_json_syntax_errors_hide_validation_errors;; esac
    echo "$cp $ch new-cases-of $c $(count "$O/$cp.new-$c.json" "$skip")"; done
  done_="$done_ $ch"; rm -rf "$D"
done < "$R/extension.txt"
echo SCORED
