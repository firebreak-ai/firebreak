#!/usr/bin/env bash
# TaskCompleted hook: validates per-task prerequisites for SDL workflow tasks.
# Fires on every TaskCompleted event; scopes itself by checking for SDL task file paths.

set -uo pipefail

INPUT=$(cat)

# Context check: only proceed for SDL implementation tasks
TASK_DESC=$(printf '%s' "$INPUT" | jq -r '.task_description // ""')
TASK_FILE=$(printf '%s' "$TASK_DESC" | grep -oE 'ai-docs/[^[:space:]]*/tasks/task-[^[:space:]]*.md' | head -1)
[[ -z "$TASK_FILE" ]] && exit 0

CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // "."')
[[ "$TASK_FILE" != /* ]] && TASK_FILE="$CWD/$TASK_FILE"

FAILURES=()

# --- Test suite check ---
detect_test_cmd() {
  local d="$1"
  [[ -f "$d/package.json" ]] && { printf 'npm test'; return; }
  [[ -f "$d/Cargo.toml" ]] && { printf 'cargo test'; return; }
  [[ -f "$d/go.mod" ]] && { printf 'go test ./...'; return; }
  { [[ -f "$d/pytest.ini" ]] || grep -qs '\[tool\.pytest' "$d/pyproject.toml" 2>/dev/null; } && { printf 'python -m pytest'; return; }
  [[ -f "$d/Makefile" ]] && grep -qs '^test:' "$d/Makefile" && { printf 'make test'; return; }
  printf ''
}

TEST_CMD=$(detect_test_cmd "$CWD")
if [[ -z "$TEST_CMD" ]]; then
  printf '[WARN] No recognized test runner; skipping test suite check.\n' >&2
else
  test_out=$(cd "$CWD" && eval "$TEST_CMD" 2>&1) && test_rc=0 || test_rc=$?
  [[ $test_rc -ne 0 ]] && FAILURES+=("TEST SUITE FAILED:"$'\n'"$test_out")
fi

# --- Lint check ---
detect_lint_cmd() {
  local d="$1"
  ls "$d"/.eslintrc* 2>/dev/null | grep -q . && { printf 'npx eslint .'; return; }
  [[ -f "$d/pyproject.toml" ]] && grep -qs '\[tool\.ruff\]' "$d/pyproject.toml" && { printf 'ruff check .'; return; }
  [[ -f "$d/pyproject.toml" ]] && grep -qs '\[tool\.flake8\]' "$d/pyproject.toml" && { printf 'flake8 .'; return; }
  [[ -f "$d/Cargo.toml" ]] && { printf 'cargo clippy'; return; }
  { [[ -f "$d/.golangci.yml" ]] || [[ -f "$d/.golangci.yaml" ]]; } && { printf 'golangci-lint run'; return; }
  printf ''
}

LINT_CMD=$(detect_lint_cmd "$CWD")
if [[ -z "$LINT_CMD" ]]; then
  printf '[WARN] No recognized linter; skipping lint check.\n' >&2
else
  lint_out=$(cd "$CWD" && eval "$LINT_CMD" 2>&1) && lint_rc=0 || lint_rc=$?
  [[ $lint_rc -ne 0 ]] && FAILURES+=("LINT ERRORS:"$'\n'"$lint_out")
fi

# --- File scope check ---
# Compare modified files against declared scope in the task file
if [[ -f "$TASK_FILE" ]]; then
  # Extract declared files from "Files to create/modify" section
  DECLARED_FILES=$(sed -n '/^## Files to.*create.*modify/I,/^## /{ /^## Files/d; /^## /d; s/.*[`]\([^`]*\)[`].*/\1/p; }' "$TASK_FILE" | sort -u)

  if [[ -n "$DECLARED_FILES" ]]; then
    # Find task dir to locate task.json and determine feature root
    TASK_DIR=$(dirname "$TASK_FILE")
    if [[ -f "$TASK_DIR/task.json" ]]; then
      # Get task ID from matching filename
      TASK_BASENAME=$(basename "$TASK_FILE")
      TASK_TYPE=$(python3 -c "
import json, sys
manifest = json.load(open('$TASK_DIR/task.json'))
for t in manifest.get('tasks', []):
    if t.get('file') == '$TASK_BASENAME':
        print(t.get('type', '')); break
" 2>/dev/null)

      # Check git diff if available, otherwise skip
      if git -C "$CWD" rev-parse --git-dir >/dev/null 2>&1; then
        MODIFIED_FILES=$(cd "$CWD" && git diff --name-only HEAD 2>/dev/null | sort -u)
        if [[ -n "$MODIFIED_FILES" ]]; then
          UNDECLARED=$(comm -23 <(echo "$MODIFIED_FILES") <(echo "$DECLARED_FILES"))
          if [[ -n "$UNDECLARED" ]]; then
            printf '[WARN] Task %s modified files outside declared scope:\n%s\n' "$TASK_BASENAME" "$UNDECLARED" >&2
          fi
        fi
      fi
    fi
  fi
fi

# --- Result ---
if [[ ${#FAILURES[@]} -gt 0 ]]; then
  printf 'TaskCompleted validation failed:\n\n' >&2
  for f in "${FAILURES[@]}"; do printf '%s\n\n' "$f" >&2; done
  exit 2
fi

exit 0
