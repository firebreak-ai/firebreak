#!/usr/bin/env bash
# Build a SlopCodeBench problem checkpoint by checkpoint in one workspace, with one workflow.
# Usage: chain-scb.sh <run-dir> <arm> [problem] [first-cp] [last-cp]
#   arm: tdd | exact | exsub (the lab's Claude Code workflows) | plain (no workflow files; one prompt per checkpoint)
#        fbktl | fbktl-own | fbktl-one | fbktl-one-tidy (Firebreak's test-list trial, the fbk-testplan skill, one session per checkpoint: a
#        separate author writes and locks the test bodies; or the implementer writes each body at its step; or that one
#        session does all the work itself, with no subagents; or it does all but the closing tidy-up, which goes to one
#        fresh subagent). FBK_ASSETS names the
#        Firebreak version installed, as in fbk-drive.sh: a commit of this repository or the absolute path of an assets
#        folder; it has no default here. No operator is present: the prompt approves the printed plan in advance.
#   Firebreak builds are driven turn by turn by an agent acting as the operator: fbk-drive.sh.
#   START=<folder made by prepare-start.sh>: a new workspace is cloned from that common start instead of the empty skeleton
#   and tagged cp<first-1>; prompt.md then also says the project has a passing test suite (render-prompt.py's `tests`).
# Every arm gets the same start (the EXACT lab's Python stack skeleton and a ready .venv) and the same request per checkpoint
# (SlopCodeBench's just-solve prompt, in prompt.md). Each checkpoint runs in fresh sessions, as SlopCodeBench does;
# the workspace carries over. After each checkpoint: commit + tag cpN. No scoring here: score-build.sh runs the hidden
# tests for every tag afterwards, with the lock off.
# The workspace is outside the kit for the whole chain, in $WORK/<16 random hex digits> (WORK, default ~/.cache/wk, has
# mode 300: a folder there can be entered by name but not listed, as in change/run.sh). When the chain ends, also
# after an interrupt, a session still running is stopped and the workspace is moved to <run-dir>/project; a chain that
# continues an earlier one takes it from there again. The run's files (requests, session records, logs) are written to
# a second folder under $WORK and moved to <run-dir> at the same moment; until then <run-dir> holds only chain.log.
# While lock.sh's lock is on, the ended run is locked with the other answers.
# Every session gets change/clean-settings.sh's settings: no instruction files from folders above the workspace.
# Every checkpoint's request is rendered before the first session and held in memory: the specs cannot be read while
# the lock is on. PROMPTS=<folder of cpN.md rendered ahead> is read instead and removed (batch-build.sh renders before
# it locks). Each request is kept as cpN.prompt.md when its checkpoint starts.
# Session records: cpN.jsonl is the full stream; cpN.json holds its final result event, the object --output-format
# json prints.
set -uo pipefail
. "$(dirname "$0")/../settings.sh"; need SCB_PROBLEMS EXACT_LAB
LAB=$EXACT_LAB/experiments
R="$(realpath -m "$1")"; ARM=$2; PROB=${3:-etl_pipeline}; FIRST=${4:-1}
[ -n "${START:-}" ] && START="$(realpath "$START")"
LAST=${5:-$(ls "$SCB_PROBLEMS/$PROB"/checkpoint_*.md | wc -l)}
case $ARM in tdd) WF=baselines/baseline-inline-tdd-v1-cc;; exact) WF=exact-coding/sol/exact-ptdd-v1-cc;;
  exsub) WF=exact-coding/sol/exact-ptdd-v1.1-refactor-subagent-cc;; plain|fbktl|fbktl-own|fbktl-one|fbktl-one-tidy) WF=;;
  fbk) echo "Firebreak builds are driven turn by turn: see fbk-drive.sh" >&2; exit 2;; *) echo "unknown arm $ARM" >&2; exit 2;; esac
D="$R/project"; WORK=${WORK:-$HOME/.cache/wk}; log() { echo "$(date +%T) $*" | tee -a "$R/chain.log"; }
ASK="Read prompt.md and complete the exercise following the workflow rules."; [ "$ARM" = plain ] && ASK="Read prompt.md and complete the task."
. "$K/build/build-lib.sh"  # CLEAN_ENV, name, await, result, clone_start

wf_label() { echo "${WF:-none}"; }
install_arm() { [ -z "$WF" ] || cp -r "$LAB/workflows/$WF/.claude" .; }
case $ARM in fbktl*)
  case ${FBK_ASSETS:?set FBK_ASSETS to the Firebreak commit or assets folder to install} in /*) A=$FBK_ASSETS;; *) A="$LOCAL/assets-$FBK_ASSETS"
    [ -d "$A" ] || { mkdir "$A.new" && git -C "$REPO" archive "$FBK_ASSETS" assets | tar -x -C "$A.new" --strip-components=1 && mv "$A.new" "$A"; } || { for _ in $(seq 60); do [ -d "$A" ] && break; sleep 1; done; [ -d "$A" ]; } || exit 2;; esac  # a parallel build may be exporting the same commit: wait for it
  BODIES=; [ "$ARM" = fbktl-own ] && BODIES=' Start the plan with `--bodies implementer`.'; [ "$ARM" = fbktl-one ] && BODIES=' Start the plan with `--session one`.'; [ "$ARM" = fbktl-one-tidy ] && BODIES=' Start the plan with `--session one --tidy agent`.'
  ASK=$(sed "s/BODIES/$BODIES/" "${ASK_FILE:-$K/prompts/fbk-testplan/build.txt}")  # ASK_FILE: another wording of the session's prompt (interview-batch.sh)
  wf_label() { echo "firebreak-testplan $(basename "$A")"; }
  install_arm() { bash "$REPO/installer/install.sh" --target "$PWD/.claude" --source "$A" > "$L/install.log" 2>&1; };; esac
if [ -n "${START:-}" ] && [ ! -e "$D" ]; then NEW=start
elif [ "$FIRST" = 1 ]; then [ -e "$D" ] && { echo "Refusing: $D exists" >&2; exit 1; }; NEW=empty
else [ -d "$D" ] || { echo "No project to continue in $R" >&2; exit 1; }; NEW=; fi
SF=$(cat "$R/start-first-cp.txt" 2>/dev/null); TESTS=; { [ -n "${START:-}" ] || [ -n "$SF" ]; } && TESTS=tests  # SF: the first checkpoint built on a common start
declare -A PROMPT
for cp in $(seq "$FIRST" "$LAST"); do
  if [ -n "${PROMPTS:-}" ]; then PROMPT[$cp]=$(cat "$PROMPTS/cp$cp.md"); else PROMPT[$cp]=$(python3 "$K/setup/render-prompt.py" "$cp" "$PROB" $TESTS); fi ||
    { echo "No request for checkpoint $cp (are the answers locked?)" >&2; exit 2; }
done
[ -n "${PROMPTS:-}" ] && { rm -f "$PROMPTS"/cp*.md; rmdir "$PROMPTS"; }
mkdir -p "$R" "$WORK" && chmod 300 "$WORK" || exit 2
W="$WORK/$(name)"; L="$WORK/$(name)"; mkdir "$L" || exit 2
SET=$("$K/change/clean-settings.sh" "$W" "$LAB/docker/claude-config/settings.json") || exit 2
finish() {  # stop a session still running, bring the workspace and the run's files home, lock the run with the other answers
  [ -n "$SP" ] && { kill "$SP" 2>/dev/null; wait "$SP" 2>/dev/null; }
  cd "$R" || exit 2
  if [ -d "$W" ]; then mv "$W" "$D" || echo "the project stays in $W: it could not be moved to $D" | tee -a "$R/chain.log" >&2; fi
  mv "$L"/* "$R"/ 2>/dev/null; rmdir "$L" || echo "the run's files stay in $L: they could not be moved to $R" | tee -a "$R/chain.log" >&2
  log "${DONE:-chain stopped early}"; "$K/change/lock.sh" add "$R"
}
trap finish EXIT; trap 'exit 143' INT TERM
if [ "$NEW" = start ]; then clone_start || exit 1; SF=$FIRST
elif [ "$NEW" = empty ]; then
  mkdir -p "$W"; cd "$W" || exit 1
  cp -r "$LAB/stacks/python-pytest/." .; rm -f install.sh
  "$LAB/stacks/python-pytest/install.sh" > "$L/venv.log" 2>&1
  printf '.venv/\n__pycache__/\n.pytest_cache/\n.tdd-events*\nprompt.md\n' > .gitignore
  git init -q; git config user.email e2e@example.invalid; git config user.name e2e
  echo 'tdd-events*' >> .git/info/exclude
  install_arm
  git add -A; git commit -qm "Start: stack skeleton and $ARM workflow"; git tag cp0
  echo "$ARM $(wf_label) claude-opus-5-5 $PROB" > "$L/arm.txt"
else
  mv "$D" "$W" && cd "$W" || exit 1
  for f in .venv/bin/*; do  # the environment's scripts name the folder it was made in; point them at this one
    [ -L "$f" ] || [ "$(head -c2 "$f")" != '#!' ] || sed -i "1s|^#!.*/\.venv/bin/python[0-9.]*\$|#!$W/.venv/bin/python|" "$f"; done
fi

for cp in $(seq "$FIRST" "$LAST"); do
  printf '%s\n' "${PROMPT[$cp]}" | tee "$L/cp$cp.prompt.md" > prompt.md
  log "cp$cp start"; start=$(date +%s)
  "${CLEAN_ENV[@]}" CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1 timeout --signal=TERM --kill-after=30s "${CP_LIMIT:-7200}" \
    claude --dangerously-skip-permissions --strict-mcp-config --setting-sources project,local \
    --settings "$SET" --model claude-opus-5-5 --output-format stream-json --verbose --print \
"$ASK" > "$L/cp$cp.jsonl" 2> "$L/cp$cp.err" & await; echo $? > "$L/cp$cp.exit"; result "$L/cp$cp"
  echo $(( $(date +%s) - start )) > "$L/cp$cp.seconds"; echo 0 > "$L/cp$cp.stops"
  git add -A; git commit -qm "checkpoint $cp ($ARM)" --allow-empty; git tag -f cp$cp >/dev/null
  log "cp$cp done in $(cat "$L/cp$cp.seconds")s"
done
DONE="chain done"
