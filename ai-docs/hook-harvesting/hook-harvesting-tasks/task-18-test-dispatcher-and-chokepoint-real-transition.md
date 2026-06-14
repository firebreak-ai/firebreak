---
id: task-18
type: test
wave: 5
covers: [AC-03]
files_to_create:
  - assets/fbk-scripts/tests/test_capture_chokepoint_integration.py
files_to_modify:
  - assets/fbk-scripts/tests/test_dispatcher.py
completion_gate: "tests compile and fail before implementation"
---

# Objective

Add the real-producer chokepoint integration test (driving `fbk.py state transition` end-to-end through the wrapped dispatch, asserting the multi-line indented JSON is re-emitted byte-for-byte, the int exit code propagates, and one `PIPELINE_COMMAND` event is written) and update the dispatcher test for the new wrapped call path and the command count 18→19 with `report` registered.

# Context

`fbk.py` wraps its single `module.main()` dispatch in the chokepoint. `fbk.py state transition` is itself a dispatched command, so a single transition runs through the chokepoint redirect: `state.transition_state` prints multi-line indented JSON (the state dict via `json.dumps(..., indent=2)`) and returns an int (0/1) rather than raising `SystemExit`. The chokepoint's normal-return path must re-emit that buffered multi-line stdout byte-for-byte, propagate the int exit code, and write one `PIPELINE_COMMAND` event. This exercises the normal-return path (every hook and the state command) and the multi-line-stdout case the stub chokepoint test does not cover.

The existing `tests/test_dispatcher.py` asserts `len(fbk.COMMAND_MAP) == 18` and an expected-commands set; registering the new `report` command makes it 19. The wrap interposes between `importlib.import_module` and the result/exit handling in `fbk.py` (lines 40–43), preserving the existing exit-code contract.

The state engine resolves its store from `STATE_DIR` (`fbk/state.py` `get_state_dir()` → `.claude/automation/state` under cwd, else `$STATE_DIR`). Run `fbk.py state transition` via subprocess with `cwd=<instrumented tmp project>` and `STATE_DIR` set, after creating a spec state (`fbk.py state create <spec>`), so the chokepoint writes `<project>/.fbk-capture/events.jsonl`. Build the instrumented project with `capture_fixtures.make_project`.

# Instructions

1. In `tests/test_dispatcher.py`, update `test_command_map_contains_all_18_commands`: change the count assertion from `== 18` to `== 19`, add `"report"` to the `expected_commands` set, and rename the test to `test_command_map_contains_all_19_commands` (update the docstring to "all 19 commands"). Keep the existing subset and exact-mapping assertions intact. Add an assertion `fbk.COMMAND_MAP["report"] == "fbk.report"` confirming `report` maps to the flat module.
2. Confirm the existing dispatcher exit-code subprocess tests (`test_unrecognized_command_exits_2`, etc.) still express the unchanged contract; no change needed there — the wrap preserves exit codes. Do not weaken them.
3. Create `tests/test_capture_chokepoint_integration.py`; guard with a skip if the capture subsystem is absent (`from fbk.capture import chokepoint` inside `try/except ImportError`, skipif). Define `FBK_PY = Path(__file__).parent.parent / "fbk.py"`.
4. `test_real_state_transition_reemits_multiline_json_and_propagates_exit`: in an instrumented project, `fbk.py state create demo-spec` (cwd=project, STATE_DIR set), then `fbk.py state transition demo-spec VALIDATING` (cwd=project, STATE_DIR set); assert the subprocess exit code is `0` (the int return propagates) AND stdout is the multi-line indented JSON of the new state (assert it contains multiple lines and parses as JSON with `current_state == "VALIDATING"`) AND exactly one `PIPELINE_COMMAND` event for the `state` command was written to the project events file, recording outcome and the multi-line gate-result payload (summarized at standard). Pair the event presence with a field assertion (command name `state`, outcome present).
5. `test_real_transition_invalid_propagates_nonzero_and_records`: run an invalid transition (e.g. `state transition demo-spec REVIEWED` from QUEUED) which returns 1; assert the subprocess exit code is `1` (int return propagated, not masked) AND a `PIPELINE_COMMAND` event was recorded for the attempt. This confirms the normal-return non-zero path.
6. Because the chokepoint runs inside the same process as the injector for `state transition`, assert (in step 4) that the re-emitted stdout is exactly the state JSON and carries NO stray injector output — the injector must never write to stdout. Assert the stdout, once stripped, parses cleanly as a single JSON object (no extra lines before/after the JSON).

# Files to create/modify

- `tests/test_dispatcher.py` (update count to 19, add `report`)
- `tests/test_capture_chokepoint_integration.py`

# Test requirements

- `test_command_map_contains_all_19_commands` (unit, modified): COMMAND_MAP has 19 entries including `report` → `fbk.report`.
- `test_real_state_transition_reemits_multiline_json_and_propagates_exit` (integration): real `state transition` → multi-line JSON re-emitted, exit 0 propagated, one PIPELINE_COMMAND event, no stray injector stdout.
- `test_real_transition_invalid_propagates_nonzero_and_records` (integration): invalid transition → exit 1 propagated, event recorded.

# Acceptance criteria

AC-03 (chokepoint normal-return + multi-line-stdout path, real producer; command count reflecting the registered report command). Gate: tests compile and fail before implementation. The dispatcher count change fails until `report` is registered.

# Model

Sonnet — real-producer subprocess integration plus the dispatcher count/command update.

# Wave

5
