#!/usr/bin/env bash
# Measure the plan step's interview: build single checkpoints from a short request, with and without a simulated operator.
#   interview-batch.sh            (env: CPS "6 7 8", CONDS "floor interview", LEVEL paragraph|line, RUNS 3, JOBS 3,
#                                  ARM fbktl-one-tidy, FBK_ASSETS <commit or assets folder>, OUT local/iv-builds)
# Each run is one checkpoint in one session, named <cond>-<level>-cp<N>-<n> under OUT. Its request is the usual prompt
# wording around local/interview/cp<N>/request-<level>.md and interface.md: names and shapes, with the rules left out.
#   floor      no operator: the session takes its own recommendation wherever it would ask (prompts/fbk-testplan/build.txt)
#   interview  the session asks through a command; build/operator-server.py answers from the full specification with
#              local/interview/operator-brief.md, and logs every question and answer to <run>/operator.jsonl
# Starts: checkpoint 6 from local/starts/circuit_eval-cp5; checkpoint N > 6 from STARTS/circuit_eval-iv-cp<N-1>, one
# finished full-specification build at that checkpoint (made here once from SRCBUILD, default local/runs-ce/fbktl-one-tidy-2,
# its installed workflow removed). So every checkpoint is measured from a correct program, and none depends on another run.
# Everything that reads the answers happens before the lock goes on. No scoring here: score-build.sh <OUT>/<run> afterwards.
. "$(dirname "$0")/../settings.sh"; need SCB_PROBLEMS EXACT_LAB
PROB=circuit_eval; O=$(realpath -m "${OUT:-$LOCAL/iv-builds}"); WORK=${WORK:-$HOME/.cache/wk}; IV=$LOCAL/interview
ARM=${ARM:-fbktl-one-tidy}; LEVEL=${LEVEL:-paragraph}; SB=$(realpath "${SRCBUILD:-$LOCAL/runs-ce/fbktl-one-tidy-2}")
: "${FBK_ASSETS:?set FBK_ASSETS to the Firebreak commit or assets folder to install}"; export FBK_ASSETS
mkdir -p "$O" "$WORK" && chmod 300 "$WORK" || exit 2
TOOLS="$HOME/.cache/wk-tools"; mkdir -p "$TOOLS" && chmod 300 "$TOOLS" || exit 2
start_for() {  # the start a checkpoint builds on; made once from the source build's tag
  local cp=$1 s; [ "$cp" = 6 ] && { echo "$LOCAL/starts/$PROB-cp5"; return; }
  s="$LOCAL/starts/$PROB-iv-cp$((cp-1))"
  [ -d "$s" ] || { mkdir "$s" && git -C "$SB/project" archive "cp$((cp-1))" | tar -x -C "$s" && rm -rf "$s/.claude" &&
    ( cd "$s" && git init -q && git config user.email e2e@example.invalid && git config user.name e2e && git add -A &&
      git commit -qm "Starting codebase" && git tag start ) || return 1; }
  echo "$s"
}
HEAD="Implement a program that 100% solves the specification. That is all you need to do.
Keep using the same virtual environment you started with, update \`requirements.txt\` with any new dependencies you need.
The project already has a test suite in \`tests/\` that passes; it is run with \`.venv/bin/python -m pytest\`.

Your task is:"
declare -A PD ST AF; RUNSLIST=(); SERVERS=(); port=${PORT0:-47300}
for cp in ${CPS:-6 7 8}; do
  s=$(start_for "$cp") || { echo "no start for checkpoint $cp" >&2; exit 2; }
  spec="$TOOLS/spec-$cp-$$.md"; python3 "$K/setup/render-prompt.py" "$cp" "$PROB" tests > "$spec" || exit 2
  for cond in ${CONDS:-floor interview}; do for n in $(seq "${RUNS:-3}"); do
    r="$cond-$LEVEL-cp$cp-$n"; [ -e "$O/$r" ] && { echo "skipping $r: it exists"; continue; }
    mkdir "$O/$r" || exit 2; ST[$r]=$s; RUNSLIST+=("$r")
    PD[$r]="$WORK/$(od -An -N8 -tx1 /dev/urandom | tr -d ' \n')"; mkdir "${PD[$r]}"
    { printf '%s\n' "$HEAD"; sed 's/\bcircopt \(stats\|lint\|dot\|cone\|truth-table\|equiv\|opt\) /python circopt.py \1 /' "$IV/cp$cp/request-$LEVEL.md"; echo
      sed 's/^    circopt /    python circopt.py /' "$IV/cp$cp/interface.md"; } > "${PD[$r]}/cp$cp.md" || exit 2
    AF[$r]=
    if [ "$cond" = interview ]; then
      t="$TOOLS/$(od -An -N8 -tx1 /dev/urandom | tr -d ' \n')"; mkdir "$t"; port=$((port+1))
      printf '#!/usr/bin/env bash\n[ -n "$*" ] || { echo "usage: ask-operator \\"<question>\\"" >&2; exit 2; }\nprintf "%%s" "$*" | curl -sS --max-time 660 --data-binary @- http://127.0.0.1:%s/\necho\n' "$port" > "$t/ask-operator"; chmod 755 "$t/ask-operator"
      python3 "$K/build/operator-server.py" "$port" "$spec" "$IV/operator-brief.md" "$t/operator.jsonl" < /dev/null > "$t/server.err" 2>&1 & SERVERS+=($!); disown
      sed "s|ASKCMD|$t/ask-operator|" "$K/prompts/fbk-testplan/build-interview.txt" > "$t/ask.txt"; AF[$r]="$t/ask.txt"; echo "$t" > "$O/$r/tools.txt"
    fi
  done; done
done
sleep 2; rm -f "$TOOLS"/spec-*-$$.md  # the servers hold the specifications in memory from here on
set -m; "$K/change/lock.sh" lock || { kill "${SERVERS[@]}" 2>/dev/null; exit 1; }
"$K/change/lock.sh" add "$IV"  # the withheld rules; the servers and the rendered requests already hold what they need
cleanup() { for j in $(jobs -p); do kill -- -$j 2>/dev/null; done; wait 2>/dev/null; kill "${SERVERS[@]}" 2>/dev/null; "$K/change/lock.sh" unlock
  for r in "${RUNSLIST[@]}"; do t=$(cat "$O/$r/tools.txt" 2>/dev/null) && [ -f "$t/operator.jsonl" ] && cp "$t/operator.jsonl" "$O/$r/"; done; }
trap cleanup EXIT; trap 'exit 130' INT TERM
for r in "${RUNSLIST[@]}"; do
  while [ "$(jobs -rp | wc -l)" -ge "${JOBS:-3}" ]; do wait -n; done
  cp=${r%-*}; cp=${cp##*cp}
  START=${ST[$r]} ASK_FILE=${AF[$r]} PROMPTS=${PD[$r]} WORK=$WORK "$K/build/chain-scb.sh" "$O/$r/run" "$ARM" "$PROB" "$cp" "$cp" > "$O/$r/chain.out" 2>&1 &
done
wait
echo ALLDONE
