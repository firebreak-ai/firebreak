# Task 10: Create TaskCompleted Validation Script

## Objective

Create a hook script that validates per-task prerequisites when a teammate marks a task complete during Stage 4 implementation.

## Context

This script runs as a `TaskCompleted` hook during Stage 4. It prevents a task from being marked complete unless all per-task verification checks pass. The hook fires when a teammate attempts to mark their task done.

### What to validate

**1. Full test suite passes**: Run the project's test suite. Not just the task's new tests — ALL tests across the project. This confirms the task's implementation satisfies its tests AND did not break existing behavior.

The test runner command varies by project. The script must determine the test runner dynamically:
- Check for common test runner indicators: `package.json` (npm test), `Makefile` (make test), `pytest.ini`/`pyproject.toml` (pytest), `Cargo.toml` (cargo test), `go.mod` (go test ./...), etc.
- If no recognized test runner: skip this check and warn (do not block).

**2. No new lint errors**: Run the project's linter and check for new errors. Similar to tests, the linter command varies:
- Check for: `.eslintrc*` (eslint), `pyproject.toml` with `[tool.ruff]` or `[tool.flake8]` (ruff/flake8), `Cargo.toml` (cargo clippy), `golangci-lint.yml`, etc.
- If no recognized linter: skip and warn.

**3. File scope respected**: The task's declared file scope (from "Files to create/modify" in the task file) defines which files the teammate may change. Check that `git diff --name-only` against the task's starting point includes only files in the declared scope.

To determine declared scope: the hook receives task context via stdin JSON. The task file path is included in the task description (convention from the `/implement` skill: task description includes the path). Read the task file, extract the "Files to create/modify" section, compare against actual changed files.

### Input/output contract

**Input** (stdin JSON from TaskCompleted event):
```json
{
  "task_id": "...",
  "task_name": "...",
  "task_description": "...",
  "session_id": "...",
  "cwd": "..."
}
```

The `task_description` field contains the path to the task file (by convention set in `/implement` skill).

**Exit 0**: All checks pass. Task may be marked complete.
**Exit 2**: One or more checks fail. Stderr: which checks failed with output. The teammate receives this feedback and retries.

### Script location

`home/.claude/hooks/sdl-workflow/task-completed.sh`

### Hook scoping: context check

This hook is configured in user-global settings (`~/.claude/settings.json`) and fires on every `TaskCompleted` event across all projects. The script scopes itself by checking for SDL context on every invocation:

1. Parse the task description from stdin JSON for a task file path matching the pattern `ai-docs/*/tasks/task-*.md`.
2. If no match: exit 0 immediately (pass-through, <1ms). This is not an SDL implementation task.
3. If match: proceed with validation checks.

**Why not skill-scoped hooks**: Skill-scoped hooks (`hooks` in YAML frontmatter) are session-local — they do not propagate to teammates. The `TaskCompleted` event fires on teammate sessions, not on the team lead's session where the `/implement` skill is active. A skill-scoped hook would never reach the teammates that need it.

**Why not dynamic configuration**: Writing hooks to settings.json at runtime is fragile — if the skill crashes, the hook persists as orphaned config.

### Hook configuration

This task also creates/updates `home/.claude/settings.json` with the `TaskCompleted` hook entry:

```json
{
  "hooks": {
    "TaskCompleted": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"$HOME\"/.claude/hooks/sdl-workflow/task-completed.sh"
          }
        ]
      }
    ]
  }
}
```

If `home/.claude/settings.json` already exists, use `jq` to merge the hooks entry: deep-merge the new `TaskCompleted` entry into the existing `hooks` object, preserving all other top-level keys and existing hook entries. If `jq` is not available, warn and provide manual instructions. If the file doesn't exist, create it with just the hooks entry.

## Instructions

1. Create `home/.claude/hooks/sdl-workflow/task-completed.sh`.
2. Use bash. Keep it portable.
3. Structure:

   a. **Context check**: Parse stdin JSON for the task description. Check if it contains a path matching `ai-docs/*/tasks/task-*.md`. If no match, exit 0 immediately (not an SDL task — pass through).
   b. **Parse stdin**: Read the TaskCompleted JSON from stdin. Extract task_description (which contains the task file path) and cwd.
   c. **Extract declared scope**: Read the task file. Parse the "Files to create/modify" section for the list of allowed files.
   d. **Test suite check**: Detect the project's test runner. Run it. If tests fail, collect output for stderr.
   e. **Lint check**: Detect the project's linter. Run it. If new errors, collect output.
   f. **Scope check**: Run `git diff --name-only` in the task's working directory. Compare changed files against declared scope. Report any out-of-scope files.
   g. **Result**: If any check failed, exit 2 with all failure details on stderr. If all pass, exit 0.

4. For test runner and linter detection, support at minimum: Node.js (package.json), Python (pytest/ruff), Rust (cargo), Go (go test). Add others as reasonable.
5. When a check is skipped (no recognized tool), emit a warning but do NOT block. Missing tooling should not prevent task completion.
6. Target: under 150 lines.

## Files to Create/Modify

- **Create**: `home/.claude/hooks/sdl-workflow/task-completed.sh`
- **Create or merge**: `home/.claude/settings.json` (add `TaskCompleted` hook entry)

## Acceptance Criteria

- AC-14: Validates per-task prerequisites (test suite, lint, file scope) with appropriate scoping
- AC-15: Script is focused, deterministic, clear feedback on failure

## Model

Sonnet

## Wave

1
