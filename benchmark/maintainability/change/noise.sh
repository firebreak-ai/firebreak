#!/usr/bin/env bash
# Noise runs: repeats <from>..<to> of one change on one base, the first alone as a check that the real command works in
# the hidden work folder, the rest 4 at a time, answers locked throughout; then scored one at a time. noise.sh <change> <base> <from> <to>
# On exit, also after an interrupt or a kill, the runs still going are stopped first (each stops its session and brings
# its work folder and files home) and then the answers are unlocked. Env: OUT (the folder the runs go in, default local/runs-anchor), WORK.
. "$(dirname "$0")/../settings.sh"; C=$1; A=$2; F=$3; L=$4; R=$(realpath -m "${OUT:-$LOCAL/runs-anchor}"); WORK=${WORK:-$HOME/.cache/wk}
mkdir -p "$R"; set -m; "$K/change/lock.sh" lock || exit 1
trap 'for j in $(jobs -p); do kill -- -$j 2>/dev/null; done; wait; "$K/change/lock.sh" status | grep -q "^locked" && "$K/change/lock.sh" unlock' EXIT; trap 'exit 130' INT TERM
one() { trap : INT TERM; "$K/change/run.sh" "$C" "$LOCAL/anchors/circuit_eval/$A" "$R/$C.$A.opus.$1" claude-opus-5-5 > "$R/$C.$A.opus.$1.out" 2>&1; tail -1 "$R/$C.$A.opus.$1.out"; }  # a signal does not end it before its run has ended, so the wait on exit covers the run's cleanup
one $F & wait
"$K/change/lock.sh" unlock
o=$R/$C.$A.opus.$F
[ "$(cat $o/exit)" = 0 ] && grep -m1 '"subtype":"init"' $o/session.jsonl | grep -qF "$WORK/" || { echo "CHECK FAILED: first run did not finish cleanly in the hidden folder"; exit 1; }
echo "check passed"
"$K/change/lock.sh" lock || exit 1
for r in $(seq $((F+1)) $L); do while [ "$(jobs -rp | wc -l)" -ge 4 ]; do wait -n; done; one $r & done
wait
"$K/change/lock.sh" unlock
for r in $(seq $F $L); do d=$C.$A.opus.$r; s=$(date +%s); bash "$K/change/score.sh" "$C" "$R/$d" > $R/$d/score.out 2>&1; echo "$d scored rc=$? secs=$(( $(date +%s)-s ))"; done
echo ALLDONE
