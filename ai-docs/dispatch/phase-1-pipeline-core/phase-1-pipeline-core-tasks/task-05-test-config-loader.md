## Objective

Write bash test scripts that validate the config loader's layered config merging, cold-start detection, and verify.yml loading.

## Context

The config loader is a Python script (`config-loader.py`) that merges configuration from three layers with more-specific-wins precedence: hardcoded defaults < project `config.yml` < spec YAML frontmatter. It also loads `verify.yml` and performs cold-start detection (warns on missing prerequisites without blocking).

Default values (hardcoded):
- token_budget: null
- max_concurrent_agents: 1
- replan_cap: 2
- model: "sonnet"

Config file locations:
- Project: `<project-root>/.claude/automation/config.yml`
- Verify: `<project-root>/.claude/automation/verify.yml`
- Spec frontmatter: YAML between `---` markers at top of spec .md file

CLI interface: `python3 config-loader.py <command> <project-root> [spec-path]`
- `load <project-root> [spec-path]` — outputs merged config JSON
- `load-verify <project-root>` — outputs verify.yml as JSON
- `cold-start-check <project-root>` — outputs warnings to stderr, exit 0

Cold-start checks: test runner (package.json, Cargo.toml, go.mod, pytest.ini, pyproject.toml, Makefile with test target), linting config (.eslintrc*, ruff/flake8 in pyproject.toml, .golangci.yml), CLAUDE.md in project root.

## Instructions

1. Create `tests/sdl-workflow/test-config-loader.sh` as a bash test script. Use `set -uo pipefail`, TAP output format, test counter, pass/fail tracking.

2. Define a setup function that creates a temporary directory to serve as a mock project root. Create subdirectory `.claude/automation/` within it. Register cleanup with `trap cleanup EXIT`.

3. Define `LOADER` variable pointing to `home/dot-claude/hooks/sdl-workflow/config-loader.py` (relative to project root).

4. Create fixture files in `tests/fixtures/config/`:
   - `valid-config.yml`: YAML with `token_budget: 5000`, `max_concurrent_agents: 3`, `replan_cap: 5`.
   - `valid-verify.yml`: YAML with two checks — one required (`run-tests`, command `npm test`, required true) and one advisory (`lint-check`, command `npm run lint`, required false, threshold 0.9).
   - `spec-with-frontmatter.md`: Markdown file with YAML frontmatter between `---` markers containing `token_budget: 8000` and `model: "haiku"`, followed by a `## Problem` section.
   - `malformed-config.yml`: Invalid YAML (e.g., `key: [unclosed bracket`).

5. Write test: defaults returned when no config files exist. Run `load` against an empty project root (no config.yml, no spec). Parse output JSON. Assert: `token_budget` is null, `max_concurrent_agents` is 1, `replan_cap` is 2, `model` is `sonnet`.

6. Write test: project config.yml overrides defaults. Copy `valid-config.yml` to mock project root at `.claude/automation/config.yml`. Run `load`. Assert: `token_budget` is 5000, `max_concurrent_agents` is 3, `replan_cap` is 5, `model` is `sonnet` (not in config, so default preserved).

7. Write test: spec frontmatter overrides project config. Copy both `valid-config.yml` and `spec-with-frontmatter.md` to appropriate locations. Run `load <project-root> <spec-path>`. Assert: `token_budget` is 8000 (spec overrides project's 5000), `max_concurrent_agents` is 3 (from project config), `model` is `haiku` (spec overrides default).

8. Write test: defaults only when spec has no frontmatter. Create a spec file with no frontmatter (just `## Problem` heading). Run `load <project-root> <spec-path>` with no config.yml. Assert output matches defaults.

9. Write test: cold-start detects missing test runner. Run `cold-start-check` against empty project root. Assert exit 0. Capture stderr. Assert stderr contains a warning about missing test runner.

10. Write test: cold-start detects missing linting config. Same as above, assert stderr mentions missing linting configuration.

11. Write test: cold-start detects missing CLAUDE.md. Same as above, assert stderr mentions missing CLAUDE.md.

12. Write test: cold-start passes when prerequisites exist. Create `package.json`, `.eslintrc.json`, and `CLAUDE.md` in the mock project root. Run `cold-start-check`. Assert exit 0. Assert stderr is empty or contains no warnings.

13. Write test: verify.yml loads correctly. Copy `valid-verify.yml` to `.claude/automation/verify.yml` in mock project root. Run `load-verify`. Assert exit 0. Parse output as JSON. Assert there are 2 checks. Assert first check has `required` true, second has `required` false.

14. Write test: malformed config.yml produces error. Copy `malformed-config.yml` to `.claude/automation/config.yml`. Run `load`. Assert exit code is non-zero. Assert stderr contains an error message (not silent failure).

15. End the script with a summary line and appropriate exit code.

## Files to create/modify

- `tests/sdl-workflow/test-config-loader.sh` (create)
- `tests/fixtures/config/valid-config.yml` (create)
- `tests/fixtures/config/valid-verify.yml` (create)
- `tests/fixtures/config/spec-with-frontmatter.md` (create)
- `tests/fixtures/config/malformed-config.yml` (create)

Justification for multiple files: test fixtures are separate files by definition — each represents a distinct configuration scenario that the config loader must handle.

## Test requirements

This is a test task. Tests to write:
1. Unit: defaults returned when no config files exist
2. Unit: project config.yml overrides specific default values
3. Integration: spec frontmatter overrides project config (3-layer merge)
4. Unit: spec without frontmatter returns defaults
5. Unit: cold-start detects missing test runner
6. Unit: cold-start detects missing linting config
7. Unit: cold-start detects missing CLAUDE.md
8. Integration: cold-start passes when all prerequisites exist
9. Unit: verify.yml loads with mixed required/advisory checks
10. Unit: malformed config.yml produces clear error, not silent failure

## Acceptance criteria

AC-03: Project configuration loads `config.yml` and `verify.yml` with layered precedence (global -> project -> spec). Cold-start detection warns on missing prerequisites without blocking.

## Model

Haiku

## Wave

1
