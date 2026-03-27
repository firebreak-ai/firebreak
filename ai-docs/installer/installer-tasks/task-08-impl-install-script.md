---
id: T-08
type: implementation
wave: 5
covers: [AC-03, AC-04, AC-05, AC-06, AC-07, AC-08, AC-09, AC-10, AC-11]
files_to_create: [installer/install.sh]
files_to_modify: []
test_tasks: [T-04, T-05]
completion_gate: "Tests from T-04 and T-05 pass"
---

## Objective

Implement the main installer shell script that copies fbk-prefixed assets, merges settings via the Python merge script, manages manifests and backups, and supports install/upgrade/uninstall/dry-run modes.

## Context

The installer is a single bash 3.2+ compatible shell script. It copies firebreak assets from a source tree into a target directory (`~/.claude/` or a project `.claude/`), merges hooks and env into `settings.json` by calling `installer/merge-settings.py`, writes a manifest recording everything installed, and supports surgical uninstall via manifest.

The test tasks T-04 and T-05 call this script with `--target` and `--source` flags to bypass the interactive prompt and control paths. T-04 tests fresh install, backup, prerequisite errors, project-level install, and dry-run. T-05 tests upgrade and uninstall.

**bash 3.2+ constraint**: No associative arrays (`declare -A`), no `mapfile`, no `readarray`. Use indexed arrays, temp files, or positional parameters.

Follow the TAP test pattern established in `tests/sdl-workflow/` for understanding how tests call scripts. Follow the `home/dot-claude/hooks/sdl-workflow/breakdown-gate.sh` pattern for bash script structure (shebang, set flags, function definitions, main flow).

## Instructions

### Argument parsing

1. Create `installer/install.sh` with shebang `#!/usr/bin/env bash` and `set -uo pipefail`.

2. Parse arguments in a while loop over `"$@"`:
   - `--target <path>`: Set `TARGET_DIR` to the given path. When provided, skip the interactive prompt.
   - `--source <path>`: Set `SOURCE_DIR` to the given path. Default: auto-detect from script location as `"$(cd "$(dirname "$0")/../home/dot-claude" && pwd)"`.
   - `--uninstall`: Set `MODE=uninstall`.
   - `--dry-run`: Set `DRY_RUN=1`.
   - `--help`: Print usage and exit 0.
   - Default: `MODE=install`, `DRY_RUN=0`.

### Prerequisite checking

3. Implement `check_prerequisites()`:
   - Verify `python3` is on PATH: `command -v python3 >/dev/null 2>&1`. If missing, print to stderr: `"Error: Requires Python 3 for JSON merging. Install Python 3 and retry."` and exit 1.
   - Verify target directory is writable: if `TARGET_DIR` exists, check `[ -w "$TARGET_DIR" ]`; if it does not exist, check that the parent directory is writable. On failure, print to stderr: `"Error: Cannot write to <path>. Check permissions."` and exit 1.

### Target selection (interactive mode)

4. Implement `prompt_target()`:
   - Print the selection prompt to stderr (so stdout stays clean for piping):
     ```
     Install firebreak globally (~/.claude) or into a project directory?
       [1] Global (~/.claude/)
       [2] Project directory (enter path)
     >
     ```
   - Read user input. On `1`, set `TARGET_DIR="$HOME/.claude"` and `INSTALL_MODE=global`. On `2`, prompt for path, set `TARGET_DIR` to the entered path with `/.claude` appended if not already ending in `.claude`, and set `INSTALL_MODE=project`.
   - Only called when `--target` is not provided.
   - When `--target` is provided, set `INSTALL_MODE=project` (or `global` if the path matches `$HOME/.claude`).

### Asset enumeration

5. Implement `enumerate_assets()`:
   - Walk the source directory (`SOURCE_DIR`) and list all files, excluding `CLAUDE.md` and `settings.json`.
   - For each file, compute the destination path relative to `TARGET_DIR` by stripping the `SOURCE_DIR` prefix.
   - Store the pairs in two indexed arrays: `SRC_FILES` and `DST_FILES`, where `SRC_FILES[i]` maps to `DST_FILES[i]`.
   - Use `find "$SOURCE_DIR" -type f` piped through a while-read loop. Skip files named `CLAUDE.md` or `settings.json` (basename check).
   - Each destination path preserves the directory structure from the source. Since the source tree already has `fbk-` prefixed names (after the prerequisite rename task), no path translation is needed.

### File installation

6. Implement `install_files()`:
   - For each pair in `SRC_FILES`/`DST_FILES`:
     - If `DRY_RUN=1`, print `"Would copy: <src> -> <dst>"` and continue.
     - Create the destination directory: `mkdir -p "$(dirname "$dst")"`.
     - Copy the file: `cp "$src" "$dst"`.
     - Append the relative destination path (relative to `TARGET_DIR`) to a `MANIFEST_FILES` indexed array.
   - On copy failure, print the error to stderr and exit 1 with message: `"Error: Failed to copy <src>. Run --uninstall to clean up."`.

### Settings merging

7. Implement `merge_settings()`:
   - Locate the merge script: `MERGE_SCRIPT="$(cd "$(dirname "$0")" && pwd)/merge-settings.py"`.
   - Determine the firebreak settings source: `"$SOURCE_DIR/settings.json"`. If this file does not exist, skip merging (no hooks/env to add) and return.
   - If `DRY_RUN=1`, print `"Would merge settings from <source> into <target>/settings.json"` and return.
   - If `"$TARGET_DIR/settings.json"` exists, create a backup:
     - If `"$TARGET_DIR/settings.json.pre-firebreak"` does not exist, copy to `"$TARGET_DIR/settings.json.pre-firebreak"`. Record in `BACKUP_FILE="settings.json.pre-firebreak"`.
     - If it already exists, create a timestamped backup: `"$TARGET_DIR/settings.json.pre-firebreak.$(date +%Y%m%d%H%M%S)"`. Record in `BACKUP_FILE`.
   - Run: `python3 "$MERGE_SCRIPT" "$TARGET_DIR/settings.json" "$SOURCE_DIR/settings.json"`. Capture stdout to a temp file. If exit code is non-zero, relay stderr and exit 1.
   - Split the output on `---MANIFEST---`: everything before is the merged settings JSON, everything after is the manifest record.
   - Write the merged settings JSON to `"$TARGET_DIR/settings.json"`.
   - Parse the manifest record to extract `hooks_added` and `env_added` into shell variables (write to temp files for later manifest assembly).

### Manifest writing

8. Implement `write_manifest()`:
   - If `DRY_RUN=1`, print `"Would write manifest to <target>/.firebreak-manifest.json"` and return.
   - Build the manifest JSON using `python3 -c` with a here-document:
     - `schema_version`: `"1.0.0"`
     - `installer_version`: `"0.1.0"`
     - `firebreak_version`: `"0.1.0"`
     - `install_mode`: value of `INSTALL_MODE` (`global` or `project`)
     - `installed_at`: current ISO 8601 timestamp (use `python3 -c "import datetime; print(datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'))"`)
     - `updated_at`: same as `installed_at` for fresh install; updated to current time on upgrade
     - `target`: value of `TARGET_DIR`
     - `files`: the `MANIFEST_FILES` array entries as a JSON array
     - `settings_entries`: the `hooks_added` and `env_added` dicts from the merge script output
     - `backups`: dict mapping `"settings.json"` to the backup filename, if a backup was created
   - Write to `"$TARGET_DIR/.firebreak-manifest.json"`.
   - On upgrade (manifest already existed), read the existing `installed_at` and preserve it, update only `updated_at`.

### Uninstall

9. Implement `uninstall()`:
   - Check that `"$TARGET_DIR/.firebreak-manifest.json"` exists. If not, print to stderr: `"Error: No firebreak installation found at <target>."` and exit 1.
   - Read the manifest with `python3 -c`.
   - **Remove files**: For each path in `manifest.files`, delete `"$TARGET_DIR/$path"`. Count removals.
   - **Remove settings entries**: Call a Python snippet (inline, via `python3 -c`) that:
     - Reads `"$TARGET_DIR/settings.json"`.
     - For each hook event in `manifest.settings_entries.hooks_added`: removes matching matcher groups from the hook event array. Uses the same canonical JSON comparison as the merge script. If the array becomes empty, removes the event key entirely.
     - For each key in `manifest.settings_entries.env_added`: removes the key from `env` ONLY if the current value matches the manifest value. If the user changed it, leaves it.
     - Writes the updated settings.json back.
     - Prints a summary to stdout: number of hooks removed, number of env keys removed.
   - **Clean empty fbk directories**: Walk `TARGET_DIR` for directories containing `fbk-` in the name. Remove empty ones with `rmdir` (non-recursive, bottom-up). Use `find "$TARGET_DIR" -type d -name '*fbk-*' -empty -delete` or equivalent.
   - **Remove manifest**: `rm "$TARGET_DIR/.firebreak-manifest.json"`.
   - Print summary to stderr.

### Main flow

10. Implement the main flow at the bottom of the script:
    - Parse arguments (step 2).
    - If `MODE=uninstall`:
      - If `TARGET_DIR` not set, call `prompt_target()`.
      - Call `uninstall()`.
      - Exit.
    - If `MODE=install`:
      - If `TARGET_DIR` not set, call `prompt_target()`.
      - Call `check_prerequisites()`.
      - If existing manifest detected, print `"Existing installation detected — upgrading"` to stderr.
      - Call `enumerate_assets()`.
      - Call `install_files()`.
      - Call `merge_settings()`.
      - Call `write_manifest()`.
      - Print summary to stderr:
        ```
        Firebreak installed to <target>/
          Files installed: <count>
          Hooks added: <count>
          Backups: <backup_path or "none">
        ```
      - If `DRY_RUN=1`, prefix summary with `"[DRY RUN] "` and note that no changes were made.

### Dry-run behavior

11. `--dry-run` participates in the full flow (enumerate, would-copy, would-merge, would-manifest) but every mutating operation is gated by `if [ "$DRY_RUN" = "1" ]` checks that print instead of executing. The script exits 0 after printing the full plan.

## Files to create/modify

- `installer/install.sh` (create) -- New file in new `installer/` directory. This is the top-level entry point for the installer, not a runtime asset installed into `.claude/`.

## Test requirements

Run `bash tests/installer/test-install.sh` from project root. All 10 tests pass.
Run `bash tests/installer/test-upgrade-uninstall.sh` from project root. All 13 tests pass.

## Acceptance criteria

- AC-03: The installer does not install or modify CLAUDE.md in the target directory.
- AC-04: All firebreak assets exist with `fbk-` prefixed names. No non-`fbk-` files are created, modified, or removed (except `settings.json`, manifest, backups).
- AC-05: Re-running the installer overwrites `fbk-` files with current versions and updates the manifest.
- AC-06: A manifest file at `<target>/.firebreak-manifest.json` records every installed file path and every merged settings entry.
- AC-07: Before modifying `settings.json`, a `.pre-firebreak` backup is created. Timestamped backup if `.pre-firebreak` already exists.
- AC-08: `--uninstall` removes only `fbk-`-prefixed files and settings entries recorded in the manifest. Env keys removed only if current value matches.
- AC-09: The installer exits with a clear error and makes no changes when Python 3 is missing or target settings.json is malformed.
- AC-10: The installer supports both global (`~/.claude/`) and project-level (`.claude/`) targets.
- AC-11: `--dry-run` prints all planned operations without modifying any files or settings.

## Model

Opus

## Wave

2
