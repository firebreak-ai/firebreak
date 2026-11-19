#!/usr/bin/env bash
# Anchor runs: every change x anchor x repeat for one maintainer model, 4 at a time; skips runs that exist. batch-anchors.sh <model> <tag> <repeats>
# The answers are locked (lock.sh) for the whole batch. On exit, also after an interrupt or a kill, the runs
# still going are stopped first (each stops its session and brings its work folder and files home) and then the answers
# are unlocked. Score afterwards. Env: OUT (the folder the runs go in, default local/runs-anchor).
. "$(dirname "$0")/../settings.sh"; M=$1; T=$2; N=${3:-3}; O=$(realpath -m "${OUT:-$LOCAL/runs-anchor}")
mkdir -p "$O"; set -m; "$K/change/lock.sh" lock || exit 1
trap 'for j in $(jobs -p); do kill -- -$j 2>/dev/null; done; wait; "$K/change/lock.sh" unlock' EXIT; trap 'exit 130' INT TERM
one() {  # <change> <anchor> <out-dir>; a signal does not end it before its run has ended, so the batch's wait covers the run's cleanup
  trap : INT TERM; "$K/change/run.sh" "$1" "$LOCAL/anchors/circuit_eval/$2" "$3" "$M" > "$3.out" 2>&1; tail -1 "$3.out"
}
for r in $(seq 1 $N); do for c in 01-speed 02-all-errors 03-unknown-values; do for a in top middle bottom; do
  o=$O/$c.$a.$T.$r; [ -e "$o" ] && continue
  while [ "$(jobs -rp | wc -l)" -ge 4 ]; do wait -n; done
  one "$c" "$a" "$o" &
done; done; done
wait
