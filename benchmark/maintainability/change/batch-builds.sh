#!/usr/bin/env bash
# Maintainer runs on chosen codebases: every change x codebase x repeat, then scores them one at a time and prints the table.
# batch-builds.sh <model> <tag> <repeats> <codebase>...   where <codebase> names a folder of local/anchors/<problem>/
# The first run goes alone as a check that a real session finishes cleanly; the rest go PAR at a time (default 6); runs
# that exist are skipped. The answers are locked (lock.sh) while sessions run and unlocked for scoring. On exit, also
# after an interrupt or a kill, the runs still going are stopped first and then the answers are unlocked.
# Env: OUT (the folder the runs go in, default local/runs-maint), PAR, CHANGES (default: all three).
. "$(dirname "$0")/../settings.sh"; M=$1; T=$2; N=$3; shift 3; O=$(realpath -m "${OUT:-$LOCAL/runs-maint}"); PAR=${PAR:-6}
CHANGES=${CHANGES:-"02-all-errors 03-unknown-values 01-speed"}
mkdir -p "$O"; set -m; "$K/change/lock.sh" lock || exit 1
trap 'for j in $(jobs -p); do kill -- -$j 2>/dev/null; done; wait; "$K/change/lock.sh" status | grep -q "^locked" && "$K/change/lock.sh" unlock' EXIT; trap 'exit 130' INT TERM
one() {  # <change> <codebase> <out-dir>; a signal does not end it before its run has ended, so the batch's wait covers the run's cleanup
  trap : INT TERM; "$K/change/run.sh" "$1" "$LOCAL/anchors/${PROBLEM:-circuit_eval}/$2" "$3" "$M" > "$3.out" 2>&1; tail -1 "$3.out"
}
first=1
for r in $(seq 1 "$N"); do for c in $CHANGES; do for a in "$@"; do
  o=$O/$c.$a.$T.$r; [ -e "$o" ] && continue
  if [ $first = 1 ]; then
    first=0; one "$c" "$a" "$o" & wait
    tail -1 "$o.out" | grep -q " exit=0 " || { echo "CHECK FAILED: the first run did not finish cleanly; see $o"; exit 1; }
    echo "check passed"; continue
  fi
  while [ "$(jobs -rp | wc -l)" -ge "$PAR" ]; do wait -n; done
  one "$c" "$a" "$o" &
done; done; done
wait
"$K/change/lock.sh" unlock; echo SESSIONS-DONE
for d in "$O"/*."$T".*/; do d=${d%/}; [ -f "$d/measure.json" ] && continue; c=$(basename "$d"); c=${c%%.*}
  s=$(date +%s); bash "$K/change/score.sh" "$c" "$d" > "$d/score.out" 2>&1; echo "$(basename "$d") scored rc=$? secs=$(( $(date +%s)-s ))"; done
uv run -q "$K/measure/table.py" "$O"/*."$T".*/ > "$O/table-$T.tsv" 2>"$O/table-$T.err"; echo ALLDONE
