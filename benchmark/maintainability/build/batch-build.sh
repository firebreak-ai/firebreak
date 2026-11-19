#!/usr/bin/env bash
# Builds of one or several arms side by side under one lock, then each scored (Firebreak builds: fbk-drive.sh):
#   batch-build.sh <arm | "arm arm ..."> [builds of each arm, default 3] [first number, default 1]
# The runs are local/runs-ce/<arm>-<n>, at most JOBS going at a time (default 3), in the order 1st of each arm, 2nd of each arm, ...; refuses
# when one of them exists.
# Env: START (default local/starts/circuit_eval-cp5), PROBLEM (circuit_eval), CPS (first and last checkpoint, "6 8"), WORK
# (the folder holding the work folders, ~/.cache/wk), MUTANTS (passed to score-build.sh), OUT (the folder the runs go
# in, default local/runs-ce).
# Before the lock goes on, every run's requests are rendered into a folder of its own under WORK, which its chain reads
# and removes before its first session. The answers are locked (change/lock.sh) for the whole batch. On exit, also
# after an interrupt or a kill, the chains still going are stopped first (each stops its session and brings its
# workspace home) and then the answers are unlocked. A batch that ran to the end is then scored, one run at a time.
. "$(dirname "$0")/../settings.sh"; need SCB_PROBLEMS EXACT_LAB; ARMS=${1:?usage: batch-build.sh <arm | "arm arm ..."> [builds] [first number]}; N=${2:-3}; F=${3:-1}; O=$(realpath -m "${OUT:-$LOCAL/runs-ce}")
START=$(realpath "${START:-$LOCAL/starts/circuit_eval-cp5}"); PROB=${PROBLEM:-circuit_eval}; read -r C1 C2 <<< "${CPS:-6 8}"; WORK=${WORK:-$HOME/.cache/wk}
for a in $ARMS; do case $a in tdd|exact|exsub|plain|fbktl|fbktl-own|fbktl-one|fbktl-one-tidy) ;; *) echo "unknown arm $a" >&2; exit 2;; esac; done
RUNS=$(for n in $(seq "$F" $((F+N-1))); do for a in $ARMS; do echo "$a-$n"; done; done)  # run names, <arm>-<n>
for r in $RUNS; do [ -e "$O/$r" ] && { echo "refusing: $O/$r exists" >&2; exit 1; }; done
mkdir -p "$O" "$WORK" && chmod 300 "$WORK" || exit 2
declare -A PD
for r in $RUNS; do PD[$r]="$WORK/$(od -An -N8 -tx1 /dev/urandom | tr -d ' \n')"; mkdir "${PD[$r]}"
  for cp in $(seq "$C1" "$C2"); do python3 "$K/setup/render-prompt.py" "$cp" "$PROB" tests > "${PD[$r]}/cp$cp.md" || { rm -rf "${PD[@]}"; exit 2; }; done; done
set -m; "$K/change/lock.sh" lock || { rm -rf "${PD[@]}"; exit 1; }
trap 'for j in $(jobs -p); do kill -- -$j 2>/dev/null; done; wait; rm -rf "${PD[@]}"; "$K/change/lock.sh" unlock' EXIT; trap 'exit 130' INT TERM
for r in $RUNS; do
  while [ "$(jobs -rp | wc -l)" -ge "${JOBS:-3}" ]; do wait -n; done
  START=$START PROMPTS=${PD[$r]} WORK=$WORK "$K/build/chain-scb.sh" "$O/$r" "${r%-*}" "$PROB" "$C1" "$C2" > "$O/$r.out" 2>&1 &
done
wait
trap - EXIT; rm -rf "${PD[@]}"; "$K/change/lock.sh" unlock || exit 1
for r in $RUNS; do s=$(date +%s); "$K/build/score-build.sh" "$O/$r" > "$O/$r.score.out" 2>&1; echo "$r scored rc=$? secs=$(( $(date +%s)-s ))"; done
echo ALLDONE
