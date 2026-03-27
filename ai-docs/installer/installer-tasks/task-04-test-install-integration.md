---
id: T-04
type: test
wave: 4
covers: [AC-03, AC-04, AC-06, AC-07, AC-09, AC-10, AC-11]
files_to_create: [tests/installer/test-install.sh]
completion_gate: "Tests compile and fail before implementation begins"
---

## Objective

Write integration tests for `installer/install.sh` covering fresh install, asset enumeration, manifest creation, backup behavior, prerequisite errors, project-level install, and dry-run mode.

## Context

The installer (`installer/install.sh`) creates a temp-based or user-specified target directory, copies `fbk-`-prefixed files from the source tree, merges hooks/env into `settings.json`, writes a manifest at `<target>/.firebreak-manifest.json`, and backs up existing `settings.json`.

These tests create isolated temp directories, run `install.sh` against them (bypassing the interactive prompt by passing the target path as an argument or environment variable), and verify the filesystem results.

The installer requires a mock source tree with representative `fbk-`-prefixed files. Each test creates this mock source tree in a temp directory with 3-5 files across `skills/fbk-spec/`, `agents/`, `hooks/fbk-sdl-workflow/`, and `docs/fbk-sdl-workflow/` subdirectories.

Follow the TAP format pattern in `tests/sdl-workflow/test-spec-validator.sh`.

## Instructions

1. Create `tests/installer/test-install.sh`. Set up TAP boilerplate.

2. Define variables: `SCRIPT_DIR`, `PROJECT_ROOT`, `INSTALL_SCRIPT="$PROJECT_ROOT/installer/install.sh"`.

3. Create a `setup_mock_source()` function that builds a minimal mock source tree in a temp directory:
   - `home/dot-claude/skills/fbk-spec/prompt.md` containing "mock spec prompt"
   - `home/dot-claude/agents/fbk-code-review-detector.md` containing "mock agent"
   - `home/dot-claude/hooks/fbk-sdl-workflow/task-completed.sh` containing "#!/usr/bin/env bash\necho done"
   - `home/dot-claude/docs/fbk-sdl-workflow/guide.md` containing "mock doc"
   - `home/dot-claude/settings.json` containing the firebreak settings entries (hooks + env)
   - `home/dot-claude/CLAUDE.md` containing "should not be installed"
   The function prints the temp directory path to stdout.

4. Create a `setup_target()` function that creates an empty temp directory to serve as the install target. Prints the path to stdout.

5. Register cleanup with `trap` to remove all temp directories on exit.

6. Write test: **fresh install creates fbk-prefixed files**. Set up mock source and empty target. Run `bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE/home/dot-claude"`. Assert exit 0. Assert files exist: `$TARGET/skills/fbk-spec/prompt.md`, `$TARGET/agents/fbk-code-review-detector.md`, `$TARGET/hooks/fbk-sdl-workflow/task-completed.sh`, `$TARGET/docs/fbk-sdl-workflow/guide.md`. Assert file contents match the mock source.

7. Write test: **CLAUDE.md not installed**. After fresh install (reuse target from test 6 or set up new), assert `$TARGET/CLAUDE.md` does not exist.

8. Write test: **no non-fbk files created**. After fresh install, list all files in the target (excluding `settings.json`, `.firebreak-manifest.json`, and backup files). Assert every file path contains `fbk-` in its directory or filename.

9. Write test: **manifest created with correct structure**. After fresh install, assert `$TARGET/.firebreak-manifest.json` exists. Parse it with `python3 -c` to verify: `schema_version` is `"1.0.0"`, `files` is an array containing at least 4 entries, each entry in `files` contains `fbk-`, `settings_entries` has `hooks_added` and `env_added` keys.

10. Write test: **existing settings.json backed up with .pre-firebreak suffix**. Set up target with a pre-existing `settings.json` containing `{"hooks":{}}`. Run install. Assert `$TARGET/settings.json.pre-firebreak` exists and contains `{"hooks":{}}`.

11. Write test: **timestamped backup when .pre-firebreak already exists**. Set up target with both `settings.json` and `settings.json.pre-firebreak` already present. Run install. Assert a timestamped backup file exists matching the pattern `settings.json.pre-firebreak.*` (use a glob or `ls` check). Assert the original `settings.json.pre-firebreak` was not overwritten.

12. Write test: **missing Python 3 exits with error**. Set up mock source and target. Run `PATH=/usr/bin:/bin bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE/home/dot-claude"` but with Python 3 hidden. Create a wrapper: `mkdir "$TMPDIR/no-python" && ln -s /bin/bash "$TMPDIR/no-python/bash"` and similar for needed utils, then run with `PATH="$TMPDIR/no-python"`. Assert exit code is non-zero. Assert stderr contains "Python 3" (case-insensitive). Assert target directory has no new files (install made no changes).

13. Write test: **project-level install**. Set up mock source. Create a project directory `$TMPDIR/my-project`. Run install with target `$TMPDIR/my-project/.claude`. Assert files are installed under `$TMPDIR/my-project/.claude/skills/fbk-spec/`, etc.

14. Write test: **dry-run makes no changes**. Set up mock source and empty target. Run `bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE/home/dot-claude" --dry-run`. Assert exit 0. Assert stdout contains descriptive output (check for "would" or file paths). Assert target directory is still empty (no files created, no `settings.json`, no manifest).

15. Write test: **existing non-fbk files untouched**. Set up target with a pre-existing file `$TARGET/skills/my-custom-skill/prompt.md` containing "user content". Run install. Assert `$TARGET/skills/my-custom-skill/prompt.md` still contains "user content".

16. End with summary and exit.

## Files to create/modify

- `tests/installer/test-install.sh` (create)

No existing file is the right location — this is a new integration test in the new `tests/installer/` directory.

## Test requirements

Tests to write (all in `test-install.sh`):
1. Fresh install creates fbk-prefixed files in target
2. CLAUDE.md is not installed
3. No non-fbk files created (except settings.json, manifest, backups)
4. Manifest created with correct schema and contents
5. Existing settings.json backed up with .pre-firebreak suffix
6. Timestamped backup when .pre-firebreak already exists
7. Missing Python 3 exits with error, makes no changes
8. Project-level install creates files at correct path
9. Dry-run prints operations but makes no changes
10. Existing non-fbk files in target are untouched

## Acceptance criteria

- AC-03: The installer does not install or modify CLAUDE.md in the target directory.
- AC-04: All firebreak assets exist with `fbk-` prefixed names. No non-`fbk-` files are created, modified, or removed (except `settings.json`, manifest, backups).
- AC-06: A manifest file records every installed file path and every merged settings entry.
- AC-07: A `.pre-firebreak` backup is created before modifying `settings.json`. Timestamped backup if `.pre-firebreak` already exists.
- AC-09: The installer exits with a clear error and makes no changes when Python 3 is missing.
- AC-10: The installer supports both global and project-level targets.
- AC-11: `--dry-run` prints all planned operations without modifying any files.

## Model

Sonnet

## Wave

2
