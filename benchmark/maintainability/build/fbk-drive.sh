#!/usr/bin/env bash
# Drive one Firebreak build a turn at a time. An agent acting as the operator calls this: it sends a phase's prompt,
# reads the reply, and either answers the questions asked or sends the next phase's prompt.
#   fbk-drive.sh start  <run>                                  lock the answers, prepare the project from the common start
#   fbk-drive.sh turn   <run> <cp> <turn-name> <prompt-file>   one fresh headless session with that message
#   fbk-drive.sh close  <run> <cp>                             commit and tag cpN; write cpN.seconds, cpN.stops, cpN.exit
#   fbk-drive.sh finish <run>                                  bring the project and the run's files home, unlock
#   fbk-drive.sh abort  <run>                                  stop a turn still running, bring home what exists, unlock
#   fbk-drive.sh resume <run>                                  put an aborted build back where it was and lock again; then turn, close, finish as before
# Then score-build.sh local/runs-ce/<run>, as for any build. Several Firebreak builds can go at once under one lock:
# the first start takes it, each later start joins it (local/.fbk-builds lists the builds going), and the finish or
# abort of the last one releases it; a build that ends earlier has its run folder locked with the other answers.
# A build that joins cannot render its requests (the problem set is locked), so its start needs REQUESTS: a folder
# holding request-cp<N>.md for each checkpoint, rendered beforehand with setup/render-prompt.py. Scoring waits for
# the lock to come off. The lock stays on when a turn is interrupted (its session is stopped; send another turn or abort).
# Firebreak runs one unit per checkpoint (<problem>-cp<N>), five phases each. <turn-name> is t<n>-<phase>, plus -<word>
# for an operator answer: t1-intent, t1-intent-a1, t2-design, t3-spec, t4-breakdown, t5-implement. The first turn of a
# phase takes prompts/fbk/<n>-<phase>.txt; an answer takes a file the operator writes (prompts/fbk/continue.txt says
# "use your own recommendation"). In the prompt file UNIT becomes the unit's name and PREAMBLE the opening of the request.
# Each turn is a new session; Firebreak picks the unit up from .fbk/<unit>/ in the project. A turn prints the session's
# final reply, then how many review rounds each phase has had and with which reviewers, then accepted or open for each
# phase of the unit, both from Firebreak's status command. 90-minute cap a turn.
# cpN.seconds is the sum of the turns' time, cpN.stops the turns beyond the first of each phase (the operator's
# answers), cpN.exit the highest exit code of a turn (124: the cap; 143: interrupted).
# Every session also gets prompts/fbk/author-system.md appended to its system prompt.
# Env for start: START (default local/starts/circuit_eval-cp5), PROBLEM (circuit_eval), CPS ("6 8"), FBK_ASSETS (the
# Firebreak version installed: a commit of this repository, whose assets/ are exported once to local/assets-<commit>,
# or the absolute path of an assets folder; default eddf9bb). Env for all: OUT (default local/runs-ce), WORK (default
# ~/.cache/wk).
# Isolation is chain-scb.sh's: the project and the run's files (requests, session records, drive.log) are in two
# folders with random names under $WORK until finish; every checkpoint's request is rendered before the lock goes on;
# sessions get change/clean-settings.sh's settings. Between calls the two folder names are kept in
# <run-dir>/drive.state, and <run-dir> is locked with the other answers.
set -uo pipefail
. "$(dirname "$0")/../settings.sh"; need SCB_PROBLEMS EXACT_LAB
LAB=$EXACT_LAB/experiments; FBK_ASSETS=${FBK_ASSETS:-eddf9bb}
. "$K/build/build-lib.sh"  # CLEAN_ENV, name, await, result, clone_start
die() { echo "$*" >&2; exit 2; }
CMD=${1:-}; RUN=${2:-}
[ -n "$RUN" ] && [ "$RUN" = "$(basename "$RUN")" ] || die "usage: fbk-drive.sh start|turn|close|finish|abort|resume <run> ... (see the top of this file)"
R="$(realpath -m "${OUT:-$LOCAL/runs-ce}")/$RUN"; D="$R/project"; WORK=${WORK:-$HOME/.cache/wk}; ARM=fbk; LOCK="$K/change/lock.sh"; HOLD="$LOCAL/.fbk-builds"
log() { echo "$(date +%T) $*" >> "$L/drive.log"; }
assets() {  # the assets folder FBK_ASSETS names, exported from that commit on first use
  case $FBK_ASSETS in /*) echo "$FBK_ASSETS"; return;; esac; local d="$LOCAL/assets-$FBK_ASSETS"
  [ -d "$d" ] || { mkdir "$d.new" && git -C "$REPO" archive "$FBK_ASSETS" assets | tar -x -C "$d.new" --strip-components=1 && mv "$d.new" "$d"; } || return 1; echo "$d"
}
wf_label() { echo "firebreak $(basename "$A")"; }
install_arm() { bash "$REPO/installer/install.sh" --target "$W/.claude" --source "$A" > "$L/install.log" 2>&1; }
phase_ok() { python3 -c "import json,sys; s=json.load(open('.fbk/$1/state.json')); sys.exit(0 if s.get('phases',{}).get('$2',{}).get('evidence') else 1)" 2>/dev/null; }
phases_report() {  # for unit $1, from the project folder: each phase's review rounds and reviewers, then accepted or open a phase
  local j now seen=1 ph  # Firebreak's own status command says where the unit is; its state file is read only when that fails
  j=$(uv run --project .claude/fbk-scripts python .claude/fbk-scripts/fbk.py status "$1" 2>/dev/null | jq -ce '.[0] | select(.phase)' 2>/dev/null) || j=
  if [ -n "$j" ]; then
    echo "=== reviews of $1"
    jq -r '. as $s | ["intent","design","spec","breakdown","implement","test-checkpoint"][] | . as $p
      | "\($p): \($s.review_rounds[$p] // 0) rounds" + (($s.review_plans[$p] // null) as $r | if $r then ", \($r.mode)" + (if ($r.members // []) | length > 0 then " (" + ($r.members | join(", ")) + ")" else "" end) else "" end)' <<< "$j"
    now=$(jq -r .phase <<< "$j"); echo "=== phases of $1"
    for ph in intent design spec breakdown implement; do [ "$ph" = "$now" ] && seen=; [ -n "$seen" ] && echo "$ph accepted" || echo "$ph open"; done
  else
    echo "=== phases of $1 (read from its state file: the status command gave nothing)"
    for ph in intent design spec breakdown implement; do phase_ok "$1" $ph && echo "$ph accepted" || echo "$ph open"; done
  fi
}
running() { [ -f "$L/turn.pid" ] && kill -0 "$(cat "$L/turn.pid")" 2>/dev/null; }
home() {  # bring the project and the run's files to <run-dir>, then unlock
  chmod u+rwx "$R"; rm -f "$R/drive.state" "$L/turn.pid"; log "$1"
  if [ -d "$W" ]; then mv "$W" "$D" || echo "the project stays in $W: it could not be moved to $D" >&2; fi
  mv "$L"/* "$R"/ 2>/dev/null; rmdir "$L" || echo "the run's files stay in $L: they could not be moved to $R" >&2
  ( flock 9; grep -vxF "$RUN" "$HOLD" > "$HOLD.new" 2>/dev/null; mv "$HOLD.new" "$HOLD"
    if [ -s "$HOLD" ]; then [ -d "$R" ] && "$LOCK" add "$R"; echo "the answers stay locked: $(wc -l < "$HOLD") other build(s) going"
    else rm -f "$HOLD"; "$LOCK" unlock; fi ) 9> "$HOLD.lock"
}

if [ "$CMD" = start ]; then
  [ -e "$R" ] && die "refusing: $R exists"
  JOIN=; if [ -e "$LOCAL/.locked" ]; then [ -s "$HOLD" ] || die "refusing: the answers are locked by something other than a Firebreak build"; JOIN=1
    [ -n "${REQUESTS:-}" ] || die "refusing: another build is going, so the requests cannot be rendered; set REQUESTS (see the top of this file)"; fi
  START=$(realpath "${START:-$LOCAL/starts/circuit_eval-cp5}"); PROB=${PROBLEM:-circuit_eval}; read -r FIRST LAST <<< "${CPS:-6 8}"
  A=$(assets) && [ -d "$A" ] || die "no Firebreak assets for FBK_ASSETS=$FBK_ASSETS"
  mkdir -p "$(dirname "$R")" "$WORK" && chmod 300 "$WORK" || exit 2
  W="$WORK/$(name)"; L="$WORK/$(name)"; mkdir "$L" || exit 2
  for cp in $(seq "$FIRST" "$LAST"); do
    if [ -n "${REQUESTS:-}" ]; then cp "$REQUESTS/request-cp$cp.md" "$L/cp$cp.prompt.md"; else python3 "$K/setup/render-prompt.py" "$cp" "$PROB" tests > "$L/cp$cp.prompt.md"; fi ||
      { rm -f "$L"/cp*.prompt.md; rmdir "$L"; die "no request for checkpoint $cp"; }; done
  ( flock 9  # take the lock, or join the one other Firebreak builds hold; either way this build is listed
    if [ -e "$LOCAL/.locked" ]; then [ -s "$HOLD" ] && [ -n "$JOIN" ] || exit 1; else "$LOCK" lock || exit 1; : > "$HOLD"; fi
    echo "$RUN" >> "$HOLD" ) 9> "$HOLD.lock" || { rm -f "$L"/cp*.prompt.md; rmdir "$L"; die "could not take or join the lock"; }
  mkdir "$R"; trap 'home "start failed"' EXIT; trap 'exit 143' INT TERM  # <run-dir> is made after the lock, which would lock it; a failure from here on unlocks
  SET=$("$K/change/clean-settings.sh" "$W") || exit 2
  for v in W L SET PROB FIRST; do printf '%s=%q\n' "$v" "${!v}"; done > "$R/drive.state"
  clone_start || exit 1
  trap - EXIT; "$LOCK" add "$R"; echo "started $RUN: $PROB checkpoints $FIRST-$LAST, answers locked"; exit 0
fi

if [ "$CMD" = resume ]; then  # an aborted build goes back under $WORK, in the project folder it had, and takes or joins the lock
  [ -d "$D" ] && [ ! -e "$R/drive.state" ] && [ -f "$R/start-first-cp.txt" ] || die "refusing: $R is not a build that abort brought home"
  W=$(cat "$R"/cp*-t*.jsonl 2>/dev/null | jq -rR 'fromjson? | .cwd // empty' 2>/dev/null | head -1)  # the venv and Firebreak's records name this path
  [ -n "$W" ] && [ "$(dirname "$W")" = "$WORK" ] && [ ! -e "$W" ] || die "refusing: the build's project folder ($W) cannot be used again"
  PROB=${PROBLEM:-circuit_eval}; FIRST=$(cat "$R/start-first-cp.txt"); L="$WORK/$(name)"
  ( flock 9
    if [ -e "$LOCAL/.locked" ]; then [ -s "$HOLD" ] || exit 1; else "$LOCK" lock || exit 1; : > "$HOLD"; fi
    echo "$RUN" >> "$HOLD" ) 9> "$HOLD.lock" || die "could not take or join the lock"
  chmod 755 "$R"; mkdir "$L" || exit 2; trap 'home "resume failed"' EXIT
  mv "$D" "$W" || exit 2; mv "$R"/* "$L"/ || exit 2; SET=$("$K/change/clean-settings.sh" "$W") || exit 2
  for v in W L SET PROB FIRST; do printf '%s=%q\n' "$v" "${!v}"; done > "$R/drive.state"
  trap - EXIT; log "build resumed"; "$LOCK" add "$R"; chmod 000 "$R"; echo "resumed $RUN, answers locked"; exit 0
fi

# Every other command continues a started build: read where it is, and leave <run-dir> closed again.
[ -e "$LOCAL/.locked" ] && chmod 700 "$R" 2>/dev/null || die "no build in progress named $RUN"
. "$R/drive.state" 2>/dev/null; rc=$?; chmod 000 "$R"; [ $rc = 0 ] || die "no build in progress named $RUN"

case $CMD in
turn)
  [ $# -eq 5 ] || die "usage: fbk-drive.sh turn <run> <cp> <turn-name> <prompt-file>"
  cp=$3; T=$4; f="$L/cp$cp-$T"; U=${PROB//_/-}-cp$cp
  [[ $T =~ ^t[1-5]-(intent|design|spec|breakdown|implement)(-[a-z0-9]+)?$ ]] || die "turn name: t<n>-<phase>[-<word>], e.g. t1-intent or t1-intent-a1"
  [ -f "$L/cp$cp.prompt.md" ] || die "no checkpoint $cp in this build"; [ -e "$L/cp$cp.exit" ] && die "checkpoint $cp is closed"
  [ -e "$f.jsonl" ] && die "turn $T of checkpoint $cp exists"; running && die "a turn is still running"
  PRE='change the program in this project as `prompt.md` in the project folder describes. The program was built by earlier units for earlier parts of the same task; this part extends it, and what earlier parts required must keep working.'
  [ "$cp" = "$FIRST" ] && PRE='change the program in this project as `prompt.md` in the project folder describes. The program already exists in the project; this part extends it, and what the existing program does must keep working.'
  txt=$(sed "s/UNIT/$U/g" "$5") || exit 2; printf '%s\n' "${txt//PREAMBLE/$PRE}" > "$f.prompt"
  cd "$W" || exit 2; cp "$L/cp$cp.prompt.md" prompt.md; echo $$ > "$L/turn.pid"; start=$(date +%s); rc=143
  ended() {  # also after an interrupt: stop the session, keep the turn's time and exit code
    [ -n "$SP" ] && { kill "$SP" 2>/dev/null; wait "$SP" 2>/dev/null; }
    echo $rc > "$f.exit"; echo $(( $(date +%s) - start )) > "$f.seconds"; rm -f "$L/turn.pid"; log "cp$cp $T ended: exit $rc, $(cat "$f.seconds")s"
  }
  trap ended EXIT; trap 'exit 143' INT TERM; log "cp$cp $T start"
  "${CLEAN_ENV[@]}" ANTHROPIC_MODEL=claude-opus-5-5 timeout --kill-after=30s 5400 claude -p --setting-sources project,local --settings "$SET" \
    --permission-mode bypassPermissions --append-system-prompt-file "$K/prompts/fbk/author-system.md" --output-format stream-json --verbose \
    < "$f.prompt" > "$f.jsonl" 2> "$f.err" & await; rc=$?; result "$f"
  echo "=== cp$cp $T: exit $rc, $(( $(date +%s) - start ))s, cost \$$(jq -r '.total_cost_usd // "?"' "$f.json" 2>/dev/null)"
  { jq -er '.result // empty' "$f.json" 2>/dev/null || { echo "(no final reply; the end of the session's error output follows)"; tail -5 "$f.err"; }; } |
    sed "s|$W|<project>|g; s|$WORK|<work>|g"  # the reply is the session's own words; the folder names stay out of what is printed
  phases_report "$U" ;;
close)
  cp=${3:?usage: fbk-drive.sh close <run> <cp>}; cd "$W" || exit 2; running && die "a turn is still running"
  ls "$L"/cp$cp-t*.jsonl > /dev/null 2>&1 || die "checkpoint $cp has no turns"
  turns=$(ls "$L"/cp$cp-t*.jsonl | wc -l); phases=$(ls "$L"/cp$cp-t*.jsonl | sed 's|.*/cp[0-9]*-t\([1-5]\)-.*|\1|' | sort -u | wc -l)
  echo $(( $(cat "$L"/cp$cp-t*.seconds | paste -sd+) )) > "$L/cp$cp.seconds"; echo $((turns - phases)) > "$L/cp$cp.stops"
  cat "$L"/cp$cp-t*.exit | sort -n | tail -1 > "$L/cp$cp.exit"
  git add -A; git commit -qm "checkpoint $cp ($ARM)" --allow-empty; git tag -f cp$cp > /dev/null
  log "cp$cp closed"; echo "cp$cp closed: $turns turns, $(cat "$L/cp$cp.seconds")s, $(cat "$L/cp$cp.stops") operator answers, exit $(cat "$L/cp$cp.exit")" ;;
finish) running && die "a turn is still running (abort stops it)"; home "build finished" ;;
abort)  if running; then p=$(cat "$L/turn.pid"); kill "$p"; for _ in $(seq 60); do kill -0 "$p" 2>/dev/null || break; sleep 1; done; fi; home "build aborted" ;;
*) die "unknown command $CMD" ;;
esac
