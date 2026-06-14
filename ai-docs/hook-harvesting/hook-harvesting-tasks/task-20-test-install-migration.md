---
id: task-20
type: test
wave: 5
covers: [AC-19]
files_to_create:
  - assets/fbk-scripts/tests/test_install_migration.py
completion_gate: "tests compile and fail before implementation"
---

# Objective

Write the integration tests proving the installer's settings merge removes a leftover project-level router registration (leaving exactly one global registration), leaves an unrelated operator-added hook entry byte-intact, is idempotent across a second run, and that the new global router registration resolves to the single global fbk-scripts path.

# Context

The installer registers the global router for the Claude hook events by merging entries into the `settings.json` template, and removes any leftover project-level router registration from the earlier capture experiment so a previously-instrumented project cannot double-record. The removal is NET-NEW logic — today `installer/merge-settings.py`'s `merge_hooks` is add-only (canonicalize-and-append, no removal path). The removal must be anchored to the exact old command string, leave every other hook entry byte-intact, and be idempotent across re-runs, so a single tool call records one event, not two. The old registration's command points at the prototype's per-project path `$CLAUDE_PROJECT_DIR/hooks/hook_router.py`; the new one must resolve to the single global fbk-scripts path on both global and project installs.

`installer/merge-settings.py` is a directly-callable Python module: `load_json`, `merge_hooks(existing_hooks, new_hooks)`, `merge_settings(existing, new_entries)`, and a `main()` taking an existing path and a new-entries path. The removal capability's home is pinned (compilation decision): a callable `remove_hook_command(existing_hooks: list, command_anchor: str) -> list` in `merge-settings.py`, invoked by the merge path — hermetically testable. The test calls it (and the merge) directly; both halves are authored at the Python layer.

The installer lives at the repo root under `installer/`, NOT under the fbk-scripts package. Import it by path. Use `tmp_path` for settings fixtures.

# Instructions

1. Create `tests/test_install_migration.py`. Import the merge module by path: add the repo `installer/` dir to `sys.path` (compute it relative to the test file: `Path(__file__).parents[3] / "installer"` — verify the depth; the test file is at `assets/fbk-scripts/tests/`, so the repo root is `parents[3]` and `installer/` sits under it) and `import importlib.util` to load `merge-settings.py` (its hyphenated name requires `spec_from_file_location`). Skip the file's tests if `remove_hook_command` is absent on the loaded module (`getattr(merge_settings_mod, "remove_hook_command", None)` → skipif), matching the red-phase pattern.
2. Build fixtures: a `settings.json` dict carrying (a) a leftover project-level router hook entry whose command is the exact old string `$CLAUDE_PROJECT_DIR/hooks/hook_router.py` under a hook event, and (b) an unrelated operator-added hook entry under a different command. Build the new-entries template carrying the global router registration.
3. `test_leftover_project_registration_removed`: invoke the removal via `remove_hook_command(existing_hooks, "$CLAUDE_PROJECT_DIR/hooks/hook_router.py")` as exercised by the merge path over the fixture settings; assert the resulting hooks contain NO entry with the old `$CLAUDE_PROJECT_DIR/hooks/hook_router.py` command, and contain exactly ONE router registration (the global one). Pair the absence (old removed) with the presence (exactly one global remains).
4. `test_unrelated_hook_left_byte_intact`: assert the operator-added unrelated hook entry survives the merge unchanged (deep-equal to its input) — the removal is anchored to the old router command only and touches nothing else.
5. `test_second_run_is_idempotent`: run the merge/migration a second time over its own output; assert the result deep-equals the first run's output (no further change) — the global registration is not duplicated and the removal does not re-fire destructively.
6. `test_global_registration_resolves_to_global_path`: assert the merged router registration's command resolves to the single global fbk-scripts path (not the per-project `$CLAUDE_PROJECT_DIR/...` form). Assert the command string matches the global form the template ships; if the global form is a documented token/path the spec pins, assert that exact form, otherwise assert it is NOT the old per-project string and points under the global fbk-scripts tree.
7. `test_capture_dir_gitignored`: assert the installer gitignores `.fbk-capture/`. The merge template ships the gitignore directive; assert it at the Python layer where the merge writes/declares the gitignore entry (the same merge fixture path), confirming `.fbk-capture/` is covered. If the gitignore is written by `install.sh` shell rather than the Python merge layer, assert the directive the template carries that the shell consumes (the `.fbk-capture/` ignore line) is present in the merged/template output.

# Files to create/modify

- `tests/test_install_migration.py`

# Test requirements

- `test_leftover_project_registration_removed` (integration): old `$CLAUDE_PROJECT_DIR/hooks/hook_router.py` registration removed; exactly one global router registration remains.
- `test_unrelated_hook_left_byte_intact` (integration): an unrelated operator hook entry survives unchanged.
- `test_second_run_is_idempotent` (integration): a second migration run produces no further change.
- `test_global_registration_resolves_to_global_path` (integration): the router command resolves to the single global fbk-scripts path, not the per-project form.
- `test_capture_dir_gitignored` (integration): `.fbk-capture/` is gitignored by the installer (the gitignore directive is present in the merged/template output).

# Acceptance criteria

AC-19 (anchored duplicate-registration removal, byte-intact siblings, idempotent re-run, global-path resolution). Gate: tests compile and fail before implementation.

# Model

Sonnet — settings-merge migration with anchored removal and idempotency over a hyphenated-name module loaded by path.

# Wave

5
