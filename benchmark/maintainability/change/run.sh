#!/usr/bin/env bash
# One maintainer session: run.sh <change> <base-repo> <out-dir> [model]
# <change> names a folder of prompts/changes-<problem>/ (a path to one works too: its last part is the name).
# Fresh clone of the base at its HEAD, a plain headless Claude Code session (default effort, no workflow files) given
# the change's request.md, full session record, then one commit of whatever it left.
# The session works outside the kit, in $WORK/<16 random hex digits>: $WORK has mode 300, so its owner can enter a
# folder there by name but cannot list it, and one session cannot find another's folder by browsing or searching. The
# run's files (prompt, session record, logs) are written to a second folder there, so <out-dir> stays empty while the
# session runs. When the session has ended, also after an interrupt (the session is stopped first), the work folder is
# moved to <out-dir>/project and the run's files to <out-dir>; the session record keeps the work folder as its cwd.
# While lock.sh's lock is on, the ended <out-dir> is locked with the other answers.
# The session gets clean-settings.sh's settings: no instruction files from folders above the work folder.
# No scoring here: score.sh does that later, serially (the speed cases must not share the machine with other jobs).
# Env: PROBLEM (default circuit_eval) names the SlopCodeBench problem; BASE_NAME overrides the base's folder name;
# WORK (default ~/.cache/wk) is the folder that holds the work folders.
set -uo pipefail
[ $# -ge 3 ] || { echo "usage: run.sh <change> <base-repo> <out-dir> [model]" >&2; exit 2; }
. "$(dirname "$0")/../settings.sh"; need SCB_PROBLEMS; E=$K/change; C=$K/prompts/changes-${PROBLEM:-circuit_eval}/$(basename "$1"); B=$(realpath "$2"); OUT=$(realpath -m "$3"); MODEL=${4:-claude-opus-5-5}
P=$SCB_PROBLEMS/${PROBLEM:-circuit_eval}
[ -f "$C/request.md" ] || { echo "no request.md in $C" >&2; exit 2; }
[ -e "$OUT" ] && { echo "refusing: $OUT exists" >&2; exit 2; }
EF=$(sed -n 's/^entry_file:[[:space:]]*//p' "$P/config.yaml"); [ -n "$EF" ] || { echo "no entry_file in $P/config.yaml" >&2; exit 2; }
WORK=${WORK:-$HOME/.cache/wk}; mkdir -p "$OUT" "$WORK" && chmod 300 "$WORK" || exit 2
name() { od -An -N8 -tx1 /dev/urandom | tr -d ' \n'; }
W="$WORK/$(name)"; L="$WORK/$(name)"; mkdir "$L" || exit 2; SP=
await() { SP=$!; wait "$SP"; local rc=$?; SP=; return $rc; }  # the session runs in the background, so an interrupt reaches this script at once
finish() {  # stop a session still running, bring the work folder and the run's files home, lock the run with the other answers
  [ -n "$SP" ] && { kill "$SP" 2>/dev/null; wait "$SP" 2>/dev/null; }
  cd "$OUT" || exit 2
  if [ -d "$W" ]; then mv "$W" "$OUT/project" || echo "the project stays in $W: it could not be moved to $OUT/project" >&2; fi
  mv "$L"/* "$OUT"/ 2>/dev/null; rmdir "$L" || echo "the run's files stay in $L: they could not be moved to $OUT" >&2
  "$E/lock.sh" add "$OUT"
}
trap finish EXIT; trap 'exit 143' INT TERM
SET=$("$E/clean-settings.sh" "$W") || exit 2
git clone -q "$B" "$W" || exit 2; cd "$W" || exit 2; git remote remove origin
printf '.venv/\n__pycache__/\n.pytest_cache/\n' >> .git/info/exclude
git rev-parse HEAD > "$L/start"
(uv venv -q .venv && { [ -f requirements-dev.txt ] && uv pip install -q --python .venv/bin/python -r requirements-dev.txt
   grep -qv '^[[:space:]]*\(#.*\)\?$' requirements.txt 2>/dev/null && uv pip install -q --python .venv/bin/python -r requirements.txt
   .venv/bin/python -c 'import pytest' 2>/dev/null || uv pip install -q --python .venv/bin/python pytest; }) > "$L/venv.log" 2>&1
jq -n --arg change "$(basename "$C")" --arg base "${BASE_NAME:-$(basename "$B")}" --arg commit "$(cat "$L/start")" \
   --arg model "$MODEL" --arg started "$(date -u +%FT%TZ)" --arg problem "${PROBLEM:-circuit_eval}" \
   '{change: $change, base: $base, base_commit: $commit, model: $model, started: $started, problem: $problem}' > "$L/run.json"
TAIL="Make this change. Update or add tests so the suite covers it, in the style the project already uses. Keep all tests passing. The program runs as \`python $EF.py\`; the project's Python environment is in \`.venv\`."
{ cat "$C/request.md"; printf '\n%s\n' "$TAIL"; } > "$L/prompt.txt"
start=$(date +%s)
env -u OLDPWD -u CLAUDE_CODE_CHILD_SESSION -u CLAUDE_CODE_SESSION_ID -u CLAUDECODE -u CLAUDE_CODE_BRIDGE_SESSION_ID \
    -u CLAUDE_CODE_MESSAGING_SOCKET -u CLAUDE_CODE_MESSAGING_TOKEN -u CLAUDE_CODE_SESSION_ATTENDED -u MAX_THINKING_TOKENS \
    timeout --kill-after=30s 5400 claude -p --model "$MODEL" --setting-sources project,local --settings "$SET" \
    --permission-mode bypassPermissions --output-format stream-json --verbose < "$L/prompt.txt" > "$L/session.jsonl" 2> "$L/stderr.txt" & await
echo $? > "$L/exit"; echo $(( $(date +%s) - start )) > "$L/seconds"
git add -A; git -c user.name=maintainer -c user.email=maintainer@x commit -q --allow-empty -m "Maintainer's change: $(basename "$C")"
echo "$(basename "$C") ${BASE_NAME:-$(basename "$B")} exit=$(cat "$L/exit") seconds=$(cat "$L/seconds") $(git diff --shortstat "$(cat "$L/start")" HEAD)"
