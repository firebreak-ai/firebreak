---
id: task-05
type: test
wave: 1
covers: [AC-11, AC-16, AC-20]
files_to_create:
  - assets/fbk-scripts/tests/test_install_seam.py
completion_gate: "Both install-seam tests collect cleanly at the current tree and FAIL from a second git worktree at the pre-fix commit (40ec021 at spec time) with the file copied in (no sentinel → uninstrumented; cp keeps the settings.json inode); failing output captured in the installer slice's completion notes."
---

## Objective

Author the install→gate→capture seam guard (installer arms capture with no manual step) and the atomic settings.json write guard against the real `installer/install.sh`.

## Context

Slices: installer-sentinel-and-atomic-write (new-contract — red phase required) and seam-guards (the install guard seam). Today `installer/install.sh` never creates the `.fbk-managed` sentinel, so a freshly installed project is uninstrumented and captures nothing (F-03); and `merge_settings()` writes the merged settings via `cp "$SETTINGS_JSON_FILE" "$TARGET_DIR/settings.json"` from a `/tmp` mktemp — an in-place truncate-and-write that an interrupted install can leave truncated (F-22).

**Declared installer contract (the implementation task copies this verbatim).**
- Sentinel: during a non-dry-run install, install.sh creates the empty file `"$TARGET_DIR/automation/.fbk-managed"` (creating `"$TARGET_DIR/automation"` if needed). `$TARGET_DIR` is the `.claude` directory, so relative to the project root this is `.claude/automation/.fbk-managed` — the existing shared token `gate_check.FBK_MARKER_SENTINEL` (`".fbk-managed"`, already defined in `fbk/capture/gate_check.py:44`; reuse it, do not mint a new name).
- Atomic write: `merge_settings()` writes the merged JSON to a temp file created IN `$TARGET_DIR` (e.g. `mktemp "$TARGET_DIR/.settings.json.tmp.XXXXXX"`), then `mv -f` it onto `"$TARGET_DIR/settings.json"`. Same-directory placement is load-bearing: a rename from another filesystem (a `/tmp` temp file) silently degrades to a non-atomic copy.

New-file rationale: `tests/test_install_migration.py` is unit-scope (it imports `merge-settings.py` functions) and is modified by task-12 in the same wave; this task is the new e2e installer harness, and the breakdown's e2e-harness exception allows harness plus tests in one task.

Harness facts (verified): install.sh requires `python3` and `uv` on PATH (`check_uv` aborts otherwise) — `uv` is third-party, so a fake `uv` shim on PATH is a permitted stand-in (code we do not own). With a `--source` directory containing only `settings.json`, `enumerate_assets` installs zero files (it skips `settings.json`), `setup_python_venv` warns and returns 0, and `merge_settings` still runs the full production merge path. `tests/test_install_migration.py` resolves the repo root as `Path(__file__).parents[3]`.

## Instructions

1. Create `tests/test_install_seam.py` with module constants `_REPO_ROOT = Path(__file__).parents[3]`, `INSTALL_SH = _REPO_ROOT / "installer" / "install.sh"`, `TEMPLATE_SETTINGS = _REPO_ROOT / "assets" / "settings.json"`, `ROUTER = Path(__file__).parent.parent / "fbk" / "capture" / "hook_router.py"`, and a module skip guard: skip when `shutil.which("bash") is None` or `not INSTALL_SH.exists()`. Import `gate_check` with the usual try/skip pattern. Done when the file collects cleanly.
2. Add three helpers:
   - `_fake_uv_bin(tmp_path)`: create `<tmp>/bin/uv` containing `#!/bin/sh\nexit 0\n`, chmod 0o755, return the bin dir as str.
   - `_minimal_source(tmp_path)`: create `<tmp>/source/` containing a copy of `TEMPLATE_SETTINGS` as `settings.json`; return the dir as str.
   - `_run_install(target_dir, source_dir, fake_bin)`: `subprocess.run(["bash", str(INSTALL_SH), "--target", target_dir, "--source", source_dir], env={**os.environ, "PATH": fake_bin + os.pathsep + os.environ["PATH"]}, capture_output=True, text=True, timeout=120)`.
3. Add `test_install_arms_capture_with_no_manual_step(tmp_path)` (covers AC-11 + AC-16):
   - `project = tmp_path / "proj"`; `target = project / ".claude"`; `project.mkdir()`.
   - Run the installer; assert rc 0 (include stdout+stderr in the failure message).
   - Assert the sentinel file exists at `os.path.join(str(target), "automation", gate_check.FBK_MARKER_SENTINEL)` — built from the shared token, not a re-typed literal.
   - Assert `gate_check.project_is_instrumented(str(project)) is True` and `gate_check.resolve_capture_level(str(project)) == "standard"`.
   - Assert no hand-written cfg was needed: `not os.path.exists(project / ".fbk-capture" / "capture.cfg")`.
   - Run the router as a subprocess (`[sys.executable, str(ROUTER)]`, `cwd=str(project)`, stdin = `capture_fixtures.hook_payload("PostToolUse", tool_name="Bash")`, timeout 15): assert rc 0 and stdout `""`; then read `<project>/.fbk-capture/events.jsonl` and assert exactly 1 event with `event_type == "TOOL_USE"`, `source == "hook_router"`, `capture_level == "standard"`, `spec is None`, `stage is None` (null-not-absent; no SDL run is active). The seam under test is sentinel→gate→writer, so running the repo's router binary (same pattern as `tests/test_capture_e2e_seam.py`) is the production path.
   Done when all assertions are present.
4. Add `test_settings_json_written_by_same_dir_rename(tmp_path)` (covers AC-20):
   - Build project/target as above; pre-create `target/settings.json` with `{"hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": "python3 /usr/local/bin/my-custom-hook.py"}]}]}, "env": {"KEEP": "1"}}` (indent 2); record `original_bytes` and `os.stat(...).st_ino`.
   - Run the installer; assert rc 0.
   - Parse the resulting `settings.json`; assert the unrelated hook command string `"python3 /usr/local/bin/my-custom-hook.py"` is still present among the hook commands, `merged["env"]["KEEP"] == "1"`, and at least one command containing `"hook_router.py"` was added (the template registration landed — presence bound).
   - Assert `os.stat(target / "settings.json").st_ino != original_inode`, with a comment: a rename into place creates a new inode; the pre-fix `cp` truncates and rewrites the same inode, which is exactly the truncation hazard — this is the correctness divergence, not a timing test.
   - Assert the backup `settings.json.pre-firebreak` exists and its bytes equal `original_bytes`.
   - Assert no temp residue: no entry in `os.listdir(target)` contains `"tmp"`, and every entry starting with `"settings.json"` is in `{"settings.json", "settings.json.pre-firebreak"}`. Pair with the presence bound: `"settings.json"` is in the listing.
   Done when all assertions are present.
5. Red run (new-contract slice — mandatory): from the pre-fix worktree with this file copied in, run both tests; capture the failing output (missing sentinel; unchanged inode) in the installer slice's completion notes.

## Files to create/modify

- `assets/fbk-scripts/tests/test_install_seam.py` (create)

## Test requirements

- E2E (bash install.sh + router subprocess) — fresh install: sentinel exists at the shared-token path; `project_is_instrumented` is True; level resolves `standard`; one router event recorded with exact field values (`TOOL_USE`, `hook_router`, `standard`, spec/stage null) and no `capture.cfg` present.
- Integration (bash install.sh over pre-existing settings.json) — merged file intact (unrelated hook + env preserved, router registration added), inode changed by rename, backup byte-equal to the original, no temp residue beside the target.

## Acceptance criteria

- AC-11: the installer creates the `.fbk-managed` sentinel so a freshly-installed project records events with no manual step.
- AC-16: an end-to-end test runs the install routine then a router event and asserts capture armed.
- AC-20: settings.json is written via a same-directory temp file renamed into place, so an interrupted install cannot leave it truncated.

## Model

Sonnet

## Wave

Wave 1
