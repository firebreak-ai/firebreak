---
id: task-21
type: implementation
wave: 2
covers: [AC-11, AC-20]
files_to_modify:
  - installer/install.sh
test_tasks: [task-05]
dependencies: [task-05]
completion_gate: "task-05 tests pass (tests/test_install_seam.py — sentinel + armed capture, same-dir rename with inode change and no temp residue); tests/test_install_migration.py stays green"
---

## Objective

Make the installer create the capture sentinel so a freshly-installed Firebreak project records events with no manual step, and write `settings.json` via a same-directory temp file renamed into place so an interrupted install cannot leave it truncated.

## Context

Slice: installer-sentinel-and-atomic-write. Two defects in `installer/install.sh` (this path is repo-relative — the file lives at the repository root under `installer/`, NOT under `assets/fbk-scripts/`):

- The installer never creates the `.fbk-managed` sentinel the capture gate keys on (`gate_check.project_is_instrumented` checks `.claude/automation/.fbk-managed`; the constant is `FBK_MARKER_SENTINEL = ".fbk-managed"` at `assets/fbk-scripts/fbk/capture/gate_check.py:44`). After a normal install the project is uninstrumented and captures nothing.
- `merge_settings()` (install.sh:312-370) writes the merged settings via `cp "$SETTINGS_JSON_FILE" "$TARGET_DIR/settings.json"` at line 369, where `SETTINGS_JSON_FILE` is a `/tmp` mktemp — an in-place truncate-and-rewrite that an interrupted install can leave truncated.

**Installer contract (copied verbatim from task-05 — do not paraphrase).**
- Sentinel: during a non-dry-run install, install.sh creates the empty file `"$TARGET_DIR/automation/.fbk-managed"` (creating `"$TARGET_DIR/automation"` if needed). `$TARGET_DIR` is the `.claude` directory, so relative to the project root this is `.claude/automation/.fbk-managed` — the existing shared token `gate_check.FBK_MARKER_SENTINEL` (`".fbk-managed"`, already defined in `fbk/capture/gate_check.py:44`; reuse it, do not mint a new name).
- Atomic write: `merge_settings()` writes the merged JSON to a temp file created IN `$TARGET_DIR` (e.g. `mktemp "$TARGET_DIR/.settings.json.tmp.XXXXXX"`), then `mv -f` it onto `"$TARGET_DIR/settings.json"`. Same-directory placement is load-bearing: a rename from another filesystem (a `/tmp` temp file) silently degrades to a non-atomic copy.

Codebase-grounded additions (verified against the script):
- `$TARGET_DIR` may not exist yet when `merge_settings` runs (the main flow calls `merge_settings` at line 651, before `install_files` at line 664, and the seam test installs into a project whose `.claude/` does not pre-exist). The same-dir mktemp therefore requires `mkdir -p "$TARGET_DIR"` first.
- `write_gitignore` (line 373) and the manifest assembly read `$SETTINGS_JSON_FILE` AFTER `merge_settings` returns. Do NOT repurpose `SETTINGS_JSON_FILE` as the same-dir temp (renaming it away would silently break `write_gitignore`'s early-return check at line 376). Add a separate same-dir temp used only for the final write.

Invariants to preserve: dry-run makes no filesystem changes; the backup (`settings.json.pre-firebreak`) behavior is unchanged; the cleanup trap leaves no temp residue beside the target on any exit path.

Constraints: do NOT modify any test file; file scope is exactly `installer/install.sh`. No new dependencies (`mktemp` with a template path and `mv -f` are POSIX-standard and already used in this script).

## Instructions

1. Add a global `SETTINGS_TMP_FILE=""` beside the other temp-file globals (after line 28), and extend `cleanup_temps()` (lines 30-35) with `[ -n "$SETTINGS_TMP_FILE" ] && rm -f "$SETTINGS_TMP_FILE"` so an interrupted install leaves no `.settings.json.tmp.*` residue. Done when the trap covers the new temp.
2. In `merge_settings()`, immediately after the dry-run early return (line 323), add `mkdir -p "$TARGET_DIR"` with a one-line comment: the same-directory temp file below requires the target directory to exist. Done when a fresh install into a project without `.claude/` proceeds.
3. Replace line 369 (`cp "$SETTINGS_JSON_FILE" "$TARGET_DIR/settings.json"`) with the atomic write:
   ```bash
   # Write merged settings atomically: temp file in the SAME directory as the
   # target, then rename. Same-directory placement is load-bearing — a /tmp
   # temp would sit on another filesystem and mv would silently degrade to a
   # non-atomic copy, recreating the truncation hazard this exists to close.
   SETTINGS_TMP_FILE="$(mktemp "$TARGET_DIR/.settings.json.tmp.XXXXXX")" || {
     echo "Error: failed to create temp file in $TARGET_DIR." >&2
     exit 1
   }
   if ! cp "$SETTINGS_JSON_FILE" "$SETTINGS_TMP_FILE"; then
     echo "Error: failed to stage merged settings.json." >&2
     exit 1
   fi
   mv -f "$SETTINGS_TMP_FILE" "$TARGET_DIR/settings.json"
   SETTINGS_TMP_FILE=""
   ```
   (`$SETTINGS_JSON_FILE` itself stays a `/tmp` temp — `write_gitignore` and the manifest record still read it afterwards.) Done when no `cp` writes directly onto `$TARGET_DIR/settings.json`.
4. Add a `create_capture_sentinel()` function after `merge_settings()`:
   ```bash
   # --- Capture sentinel ---
   # Marks the target as Firebreak-managed so the per-project capture gate arms
   # with no manual step. The filename is the shared token the gate keys on:
   # gate_check.FBK_MARKER_SENTINEL = ".fbk-managed"
   # (assets/fbk-scripts/fbk/capture/gate_check.py). $TARGET_DIR is the .claude
   # directory, so this lands at .claude/automation/.fbk-managed in the project.
   create_capture_sentinel() {
     if [ "$DRY_RUN" = "1" ]; then
       echo "Would create capture sentinel at $TARGET_DIR/automation/.fbk-managed"
       return
     fi
     mkdir -p "$TARGET_DIR/automation"
     : > "$TARGET_DIR/automation/.fbk-managed"
   }
   ```
   Done when the function exists with the dry-run branch.
5. Call `create_capture_sentinel` in the main install flow on the line after `merge_settings` (line 651), before `write_gitignore`. (Uninstall deliberately does not remove the sentinel — out of this task's scope; do not touch `uninstall()`.) Done when a non-dry-run install produces the sentinel and a dry-run prints the would-create line without creating it.
6. Run the gating tests (`tests/test_install_seam.py` from `assets/fbk-scripts/`): fresh install → sentinel exists at the shared-token path, `project_is_instrumented` True, level `standard`, router event recorded; pre-existing settings.json → merged intact, inode changed by the rename, backup byte-equal, no temp residue.

## Files to create/modify

- `installer/install.sh` (modify — repo-relative path, at the repository root)

## Test requirements

- Gating: task-05's `tests/test_install_seam.py::test_install_arms_capture_with_no_manual_step` and `::test_settings_json_written_by_same_dir_rename`.
- Must stay green: `tests/test_install_migration.py` (merge-settings unit scope — `merge-settings.py` is untouched).

## Acceptance criteria

- AC-11: the installer creates the `.fbk-managed` sentinel, so a freshly-installed Firebreak project is instrumented and records events with no manual step.
- AC-20: `settings.json` is written via a temp file created in the same directory as the target and renamed into place, so an interrupted install cannot leave it truncated.

## Model

Sonnet

## Wave

Wave 2
