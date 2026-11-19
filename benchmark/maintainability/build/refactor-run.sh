#!/usr/bin/env bash
# One headless run of the fbk-refactor skill on a copy of a finished codebase: refactor-run.sh <codebase-repo> <target> <out-dir>
# The copy gets a fresh .venv and the Firebreak assets of this working tree (FBK_SOURCE, default the repo's assets/),
# installed into .claude and left out of git. No operator is present: the prompt names the target and the test command
# and has the session take its own recommendation where the skill would ask. The work happens in a folder under WORK
# (default ~/.cache/wk) and is moved to <out-dir>/project at the end with the session record. No hidden tests are run here.
set -uo pipefail
. "$(dirname "$0")/../settings.sh"; [ $# -eq 3 ] || { echo "usage: refactor-run.sh <codebase-repo> <target> <out-dir>" >&2; exit 2; }
B=$(realpath "$1"); TARGET=$2; OUT=$(realpath -m "$3"); [ -e "$OUT" ] && { echo "refusing: $OUT exists" >&2; exit 2; }
WORK=${WORK:-$HOME/.cache/wk}; mkdir -p "$OUT" "$WORK" && chmod 300 "$WORK" || exit 2
. "$K/build/build-lib.sh"; W="$WORK/$(name)"; L="$WORK/$(name)"; mkdir "$L" || exit 2
finish() { [ -n "$SP" ] && { kill "$SP" 2>/dev/null; wait "$SP" 2>/dev/null; }; cd "$OUT" || exit 2
  [ -d "$W" ] && mv "$W" "$OUT/project"; mv "$L"/* "$OUT"/ 2>/dev/null; rmdir "$L"; }
trap finish EXIT; trap 'exit 143' INT TERM
SET=$("$K/change/clean-settings.sh" "$W") || exit 2
git clone -q "$B" "$W" || exit 2; cd "$W" || exit 2; git remote remove origin; git tag -f before-run >/dev/null
printf '.venv/\n__pycache__/\n.pytest_cache/\n.claude/\n' >> .git/info/exclude
git config user.email e2e@example.invalid; git config user.name e2e
(uv venv -q .venv && { [ -f requirements-dev.txt ] && uv pip install -q --python .venv/bin/python -r requirements-dev.txt
   grep -qv '^[[:space:]]*\(#.*\)\?$' requirements.txt 2>/dev/null && uv pip install -q --python .venv/bin/python -r requirements.txt
   .venv/bin/python -c 'import pytest' 2>/dev/null || uv pip install -q --python .venv/bin/python pytest; }) > "$L/venv.log" 2>&1
bash "$REPO/installer/install.sh" --target "$W/.claude" --source "${FBK_SOURCE:-$REPO/assets}" > "$L/install.log" 2>&1 || { echo "install failed" >&2; exit 2; }
SKILL=${SKILL:-fbk-refactor}  # fbk-refactor, or fbk-test-cleanup (test changes only: production changes it would propose are deferred)
EXTRA="when the test check finds unguarded rules or pinned details, proceed and list them in the report. Start every subagent in the foreground and wait for its result before you go on: this session ends when your turn ends, so nothing may be left running in the background. Work through the commit and then stop."
[ "$SKILL" = fbk-test-cleanup ] && EXTRA="defer every production change the skill would bring to the operator and list it in the report as a follow-up, and answer a subagent's questions yourself from the project's own evidence. Start every subagent in the foreground and wait for its result before you go on: this session ends when your turn ends, so nothing may be left running in the background. Work through the test-only commit and then stop."
cat > "$L/prompt.txt" <<P
/$SKILL $TARGET

No operator is present for this run. The target is \`$TARGET\`. The command that runs the tests covering it is \`.venv/bin/python -m pytest -q\`. Where the skill has you ask the operator or stop for a decision, take your own recommendation, record it in the report as yours, and proceed; $EXTRA
P
start=$(date +%s)
"${CLEAN_ENV[@]}" CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1 timeout --signal=TERM --kill-after=30s "${LIMIT:-7200}" \
  claude --dangerously-skip-permissions --strict-mcp-config --setting-sources project,local --settings "$SET" \
  --model "${MODEL:-claude-opus-5-5}" --output-format stream-json --verbose --print < "$L/prompt.txt" > "$L/session.jsonl" 2> "$L/stderr.txt" & await
echo $? > "$L/exit"; echo $(( $(date +%s) - start )) > "$L/seconds"; result "$L/session"
echo "$SKILL $TARGET exit=$(cat "$L/exit") seconds=$(cat "$L/seconds") $(git diff --shortstat before-run HEAD)"
