#!/usr/bin/env bash
# Have one plain session write the frozen starting test suite for a prepared start, from the spec for the checkpoints the start covers.
# Usage: write-start-suite.sh <problem> <checkpoint> <run-dir>   (start must exist in local/starts/; result is left in <run-dir>/project/tests)
set -uo pipefail
. "$(dirname "$0")/../settings.sh"; need SCB_PROBLEMS EXACT_LAB; LAB=$EXACT_LAB/experiments
PROB=$1; CP=$2; R="$(realpath -m "$3")"; W="$R/project"
[ -e "$W" ] && { echo "Refusing: $W exists" >&2; exit 1; }
mkdir -p "$R"; git clone -q "$LOCAL/starts/$PROB-cp$CP" "$W" || exit 1; cd "$W"; git remote remove origin
git config user.email e2e@example.invalid; git config user.name e2e
"$LAB/stacks/python-pytest/install.sh" > "$R/venv.log" 2>&1
for n in $(seq 1 "$CP"); do echo "# Part $n"; python3 "$K/setup/render-prompt.py" "$n" "$PROB" | sed '1,/^Your task is:$/d'; echo; done > spec.md
cp "$K/setup/suite-writer.txt" "$R/prompt.txt"
env -u CLAUDE_CODE_CHILD_SESSION -u CLAUDE_CODE_SESSION_ID -u CLAUDECODE -u CLAUDE_CODE_BRIDGE_SESSION_ID \
  -u CLAUDE_CODE_MESSAGING_SOCKET -u CLAUDE_CODE_MESSAGING_TOKEN -u CLAUDE_CODE_SESSION_ATTENDED CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1 \
  timeout --signal=TERM --kill-after=30s 7200 claude --dangerously-skip-permissions --strict-mcp-config --setting-sources project,local \
  --settings "$LAB/docker/claude-config/settings.json" --model claude-opus-5-5 --output-format json --print < "$R/prompt.txt" > "$R/session.json" 2> "$R/session.err"
git status --short > "$R/changed.txt"; .venv/bin/python -m pytest -q tests > "$R/pytest.txt" 2>&1; tail -1 "$R/pytest.txt"
