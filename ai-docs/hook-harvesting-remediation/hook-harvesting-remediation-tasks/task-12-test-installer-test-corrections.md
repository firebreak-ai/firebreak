---
id: task-12
type: test
wave: 1
covers: [AC-19]
files_to_modify:
  - assets/fbk-scripts/tests/test_install_migration.py
  - assets/fbk-scripts/tests/test_capture_gate_check_hardening.py
completion_gate: "Rewritten migration tests and the strengthened symlink test collect cleanly and pass at the current tree; the pre-fix run is captured with an explicit note that these are test-fidelity corrections over already-correct production behavior (green at pre-fix is the expected outcome), in the installer-test-corrections completion notes."
---

## Objective

Rewrite the two installer-migration tests to drive the production `merge_settings`-only path (no `remove_hook_command` calls, no file-level skip guard) and add the missing not-instrumented assertion to the symlinked-config test.

## Context

Slice: installer-test-corrections (cross-cutting, test-only). Verified against the code: `merge_settings` in `installer/merge-settings.py` already strips the leftover router registration internally (it calls `remove_hook_command(existing_hooks, ROUTER_ANCHOR)` at line 114), so `remove_hook_command` remains a production-internal helper — but the installer shell never calls it separately. Two tests (`test_second_run_is_idempotent`, `test_unrelated_hook_left_byte_intact`) bolt a separate `remove_hook_command` call onto the merge result, so they exercise a path the installer does not run; and the module-level skip guard (`pytestmark` keyed on `remove_hook_command` being absent, lines 36-43) would silently skip ALL production-path coverage if that helper were ever renamed.

In `tests/test_capture_gate_check_hardening.py::test_symlinked_config_refused`, production `project_is_instrumented` already returns `False` for a symlinked `capture.cfg` (gate_check.py:199-201), but the test asserts only `resolve_capture_level == "off"` — the instrumentation half of the contract is unguarded.

These corrections fix wrong TESTS over already-correct production code, so the rewritten tests are GREEN at the pre-fix commit; AC-21's red-run record for AC-19 must state that explicitly rather than fabricate a failure.

## Instructions

1. In `tests/test_install_migration.py`, delete the skip-guard block: the `_remove_hook_command = getattr(...)` / `_missing_removal` lines and the module-level `pytestmark` (lines 36-43). Done when the module runs with no skip machinery.
2. Rewrite `TestSecondRunIsIdempotent.test_second_run_is_idempotent` as merge-only:
   - `once, _ = merge_settings_mod.merge_settings(settings_with_leftover, new_entries_template)`; `twice, _ = merge_settings_mod.merge_settings(once, new_entries_template)`.
   - Assert byte-identity of the serialized settings file content: `json.dumps(twice, indent=2, sort_keys=True) == json.dumps(once, indent=2, sort_keys=True)`.
   - Keep it distinct from `test_merge_alone_is_idempotent` (which asserts dict equality) by additionally pinning the second-run property: after the second merge, exactly one command across all hook groups contains `"hook_router.py"`, and it contains `_GLOBAL_COMMAND_PREFIX`.
   - No `remove_hook_command` call anywhere in the test.
   Done when both assertions are present and the helper is not referenced.
3. Rewrite `TestUnrelatedHookLeftByteIntact.test_unrelated_hook_left_byte_intact` as merge-only:
   - Single `merge_settings(settings_with_leftover, new_entries_template)` call over the fixture carrying the unrelated operator hook.
   - Assert the unrelated entry survives byte-intact: find the group in the merged hooks equal to the `unrelated_entry` fixture and assert `json.dumps(found, sort_keys=True) == json.dumps(unrelated_entry, sort_keys=True)`.
   - Keep it distinct from `test_merge_alone_preserves_unrelated_entry` (membership check) by the byte-level serialization comparison.
   - No `remove_hook_command` call.
   Done when the byte-level assertion is present and the helper is not referenced.
4. Leave `test_merge_alone_is_idempotent` and the other merge-alone tests untouched (the spec confirms them green as-is). Note: `TestGlobalRegistrationResolvesToGlobalPath` and the first `TestLeftoverProjectRegistrationRemoved` test still reference `remove_hook_command`; they are outside this task's spec scope — do not modify them.
5. In `tests/test_capture_gate_check_hardening.py::test_symlinked_config_refused`, add `assert gate_check.project_is_instrumented(root) is False` immediately before the existing `resolve_capture_level(root) == "off"` assertion. Done when both assertions are present.
6. Run both files; confirm green. Capture the pre-fix run from the worktree at the recorded commit with the corrected files copied in, recording the expected-green outcome and its rationale in the slice's completion notes.

## Files to create/modify

- `assets/fbk-scripts/tests/test_install_migration.py` (modify)
- `assets/fbk-scripts/tests/test_capture_gate_check_hardening.py` (modify)

## Test requirements

- Unit (production merge path) — second-run idempotency: serialized output byte-identical after the second merge; exactly one router command, pointing at the global prefix.
- Unit (production merge path) — unrelated operator hook byte-identical (serialized comparison) after a single merge.
- Unit — symlinked `capture.cfg`: `project_is_instrumented` is exactly `False` AND `resolve_capture_level` is exactly `"off"`.

## Acceptance criteria

- AC-19: the two installer-migration tests exercise the production `merge_settings`-only path, and the symlinked-config test asserts `project_is_instrumented is False`.

## Model

Sonnet

## Wave

Wave 1
