#!/usr/bin/env bash
# Continue finished builds with the maintainer change requests as further checkpoints, each through the build's own workflow:
#   extend-builds.sh <run>...        (run names as in local/runs-ce: exact-1, fbktl-2, ...)
# Each run is copied from SRC (default local/runs-ce) to OUT (default local/ext-builds; a name the lock does not
# cover until each chain ends, since a chain must find its copy when it starts) and continued there, so the
# original build stays as it is. CHANGES (default "03-unknown-values 01-speed 02-all-errors") become the checkpoints after
# LASTCP (default 8), in that order; each request is the change's request.md inside the same prompt wording the earlier
# checkpoints had. At most JOBS chains at a time (default 3). The answers are locked for the whole batch. No scoring here.
. "$(dirname "$0")/../settings.sh"; need SCB_PROBLEMS EXACT_LAB; [ $# -ge 1 ] || { echo "usage: extend-builds.sh <run>..." >&2; exit 2; }
S=$(realpath "${SRC:-$LOCAL/runs-ce}"); O=$(realpath -m "${OUT:-$LOCAL/ext-builds}"); PROB=${PROBLEM:-circuit_eval}; WORK=${WORK:-$HOME/.cache/wk}
CH=${CHANGES:-03-unknown-values 01-speed 02-all-errors}; C1=$(( ${LASTCP:-8} + 1 )); C2=$(( C1 + $(echo $CH | wc -w) - 1 ))
for r in "$@"; do [ -d "$S/$r/project" ] || { echo "no build $S/$r" >&2; exit 1; }; [ -e "$O/$r" ] && { echo "refusing: $O/$r exists" >&2; exit 1; }; done
mkdir -p "$O" "$WORK" && chmod 300 "$WORK" || exit 2
HEAD="Implement a program that 100% solves the specification. That is all you need to do.
Keep using the same virtual environment you started with, update \`requirements.txt\` with any new dependencies you need.
The project already has a test suite in \`tests/\` that passes; it is run with \`.venv/bin/python -m pytest\`.

Your task is:"
declare -A PD FA
for r in "$@"; do
  mkdir "$O/$r" && cp -a "$S/$r/project" "$O/$r/project" && cp "$S/$r/arm.txt" "$S/$r/start-first-cp.txt" "$O/$r/" || exit 2
  FA[$r]=; case ${r%-*} in fbktl*) FA[$r]=$(awk '{print $3}' "$S/$r/arm.txt"); FA[$r]=${FA[$r]#assets-};; esac
  PD[$r]="$WORK/$(od -An -N8 -tx1 /dev/urandom | tr -d ' \n')"; mkdir "${PD[$r]}"; cp=$C1
  for c in $CH; do { printf '%s\n' "$HEAD"; cat "$K/prompts/changes-$PROB/$c/request.md"; } > "${PD[$r]}/cp$cp.md" || exit 2; echo "cp$cp $c" >> "$O/$r/extension.txt"; cp=$((cp+1)); done
done
set -m; "$K/change/lock.sh" lock || exit 1
trap 'for j in $(jobs -p); do kill -- -$j 2>/dev/null; done; wait; "$K/change/lock.sh" unlock' EXIT; trap 'exit 130' INT TERM
for r in "$@"; do
  while [ "$(jobs -rp | wc -l)" -ge "${JOBS:-3}" ]; do wait -n; done
  a=${r%-*}
  FBK_ASSETS=${FA[$r]} PROMPTS=${PD[$r]} WORK=$WORK "$K/build/chain-scb.sh" "$O/$r" "$a" "$PROB" "$C1" "$C2" > "$O/$r.out" 2>&1 &
done
wait
trap - EXIT; "$K/change/lock.sh" unlock || exit 1
echo ALLDONE
