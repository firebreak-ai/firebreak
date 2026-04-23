---
id: task-48
type: implementation
wave: 1
covers: [AC-01, AC-08]
files_to_create:
  - assets/fbk-scripts/fbk/hooks/task_completed.py
test_tasks: [task-07]
completion_gate: "task-07 tests pass"
---

## Objective

Convert `assets/hooks/fbk-sdl-workflow/task-completed.sh` to `assets/fbk-scripts/fbk/hooks/task_completed.py`, reimplementing all bash logic in Python.

## Context

`task-completed.sh` (98 lines, pure bash) fires on Claude Code `TaskCompleted` events. It reads JSON from stdin, extracts `task_description` and `cwd`, detects test runners and linters by checking for marker files, runs them, and checks file scope against task declarations. The module must expose `detect_test_cmd(directory)` and `detect_lint_cmd(directory)` as testable functions. The `main()` function reads stdin (important: do not consume stdin before it's needed).

Detection logic for `detect_test_cmd(d)`:
- `package.json` exists → `"npm test"`
- `Cargo.toml` exists → `"cargo test"`
- `go.mod` exists → `"go test ./..."`
- `pytest.ini` exists OR `pyproject.toml` contains `[tool.pytest` → `"python -m pytest"`
- `Makefile` exists with `test:` target → `"make test"`
- Otherwise → `""` (empty string)

Detection logic for `detect_lint_cmd(d)`:
- `.eslintrc*` files exist → `"npx eslint ."`
- `pyproject.toml` contains `[tool.ruff]` → `"ruff check ."`
- `pyproject.toml` contains `[tool.flake8]` → `"flake8 ."`
- `Cargo.toml` exists → `"cargo clippy"`
- `.golangci.yml` or `.golangci.yaml` exists → `"golangci-lint run"`
- Otherwise → `""` (empty string)

## Instructions

1. Create `assets/fbk-scripts/fbk/hooks/task_completed.py`
2. Implement `detect_test_cmd(directory)` — check for marker files in the given directory path, return the test command string or empty string. Use `os.path.exists`, `os.path.isfile`, and file content search (for pyproject.toml checks)
3. Implement `detect_lint_cmd(directory)` — check for linter config files, return the lint command string or empty string. Use `glob.glob` for `.eslintrc*` pattern
4. Implement `main()`:
   - Read all stdin as JSON (`json.load(sys.stdin)`)
   - Extract `task_description` and `cwd` from input
   - Extract SDL task file path from description via regex `r'ai-docs/\S*/tasks/task-\S*\.md'`
   - If no task file path found, exit 0 silently (not an SDL task)
   - Run `detect_test_cmd(cwd)` and `detect_lint_cmd(cwd)`, execute via `subprocess.run` if found
   - Check file scope against task declarations (read declared files from `## Files to create/modify` section)
   - On failures: print to stderr, exit 2. On pass: exit 0

## Files to create/modify

- **Create**: `assets/fbk-scripts/fbk/hooks/task_completed.py`

## Test requirements

- task-07: `detect_test_cmd` returns correct command for npm, cargo, go, pytest, makefile, empty. `detect_lint_cmd` returns correct command for eslint, ruff, empty

## Acceptance criteria

- AC-01: task-completed.sh converted to Python module
- AC-08: detection functions return correct commands for each project type

## Model

Sonnet

## Wave

1
