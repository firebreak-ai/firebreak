---
id: task-19
type: test
wave: 5
covers: [AC-18, AC-11]
files_to_modify:
  - assets/fbk-scripts/tests/test_state.py
completion_gate: "tests compile and fail before implementation"
---

# Objective

Add coverage to the state-engine test file for the guarded injector call wired into `transition_state`: injection fires on a working-stage → checkpoint transition, does NOT fire on a working-stage → `PARKED` transition (nor when leaving a checkpoint, `QUEUED`, `PARKED`, or `READY`), passes the local previous state, and a failing injection never blocks the transition. Confirm existing transition assertions still pass.

# Context

`transition_state` gains a guarded `inject_stage_metrics` call after `save_state()`. The predicate fires only when BOTH hold: the previous state is one of the eight working stages (those whose `VALID_TRANSITIONS` entry contains `PARKED`: `VALIDATING`, `REVIEWING`, `BREAKING_DOWN`, `TASK_REVIEWING`, `TESTING`, `TEST_REVIEWING`, `IMPLEMENTING`, `VERIFYING`) AND the new state is not `PARKED`. The working-stage set is read from `VALID_TRANSITIONS`, not hardcoded; the call site passes the local `prev_state`, not the persisted `current_state`. The correction this guards: a working stage goes to `PARKED` on failure with the same working previous state, so keying on the previous state alone would inject a "completed" block on every park. Injection is additive and fail-silent — a failed injection never prevents the transition.

The existing `tests/test_state.py` uses the `set_state_dir` fixture (sets `STATE_DIR` to a tmp dir) and calls `create_state`, `transition_state`, `load_state` directly. The injector call is `retro_injector.inject_stage_metrics(spec, prev_state)` (the completed stage is the previous state). To observe whether injection fired without coupling to the retrospective file, monkeypatch the injector the state engine calls — record its invocations and arguments. Monkeypatching here verifies the wiring contract (called / not called, with which argument), not injector behavior, which is tested separately.

# Instructions

1. In `tests/test_state.py`, add a new test class `TestInjectorWiring`. Use a fixture that monkeypatches the injector the state engine invokes so calls are recorded. Determine the exact patch target by how `state.py` references the injector — likely `import fbk.capture.retro_injector` then `retro_injector.inject_stage_metrics(...)`, so patch `fbk.capture.retro_injector.inject_stage_metrics`. Guard the class to skip if the injector module is absent (`try/except ImportError`, skipif), since the wiring does not exist in the red phase.
2. The recorder fixture: `calls = []`; `monkeypatch.setattr("fbk.capture.retro_injector.inject_stage_metrics", lambda spec, completed_stage: calls.append((spec, completed_stage)))`. If `state.py` imports the function by name (`from fbk.capture.retro_injector import inject_stage_metrics`), patch `fbk.state.inject_stage_metrics` instead — state in the test which binding you patched.
3. `test_injection_fires_on_working_stage_to_checkpoint`: `create_state("s")`; transition QUEUED→VALIDATING (no fire — prev QUEUED is not a working stage); then VALIDATING→VALIDATED; assert the injector was called exactly once with `("s", "VALIDATING")` — fired on the working-stage→checkpoint transition, passing the previous (completed) working stage. Pair the call count with the argument assertion.
4. `test_injection_does_not_fire_on_park`: `create_state("s")`; VALIDATING; then VALIDATING→PARKED (with a reason); assert the injector was NOT called for the park (no call recorded with new state PARKED) — this is the park-exclusion the single-state predicate missed.
5. `test_injection_does_not_fire_leaving_queued_or_checkpoint_or_ready`: drive transitions QUEUED→VALIDATING (leaving QUEUED, no fire), VALIDATING→VALIDATED (fires once), VALIDATED→REVIEWING (leaving a checkpoint VALIDATED, no fire); assert the only recorded call is the one from the working-stage completion (VALIDATING) — leaving QUEUED and leaving a checkpoint do not fire.
6. `test_injection_does_not_fire_on_ready_resume`: park then READY then resume (READY→VALIDATING); assert no injector call fires on the PARKED→READY or READY→VALIDATING transitions (prev states PARKED and READY are not working stages).
7. `test_failed_injection_does_not_block_transition`: make the patched injector raise; perform a working-stage→checkpoint transition (VALIDATING→VALIDATED); assert `transition_state` still returns 0 AND the saved state's `current_state == "VALIDATED"` — the failed injection is swallowed and the transition succeeds.
8. Add a smoke assertion that the existing transition behavior is unchanged: in one test, with the injector patched to a no-op, run the multi-step transition the existing `test_multi_step_transition` covers and assert the final `current_state` — confirming injection is additive (the existing tests in the file must also continue to pass unmodified).

# Files to create/modify

- `tests/test_state.py` (add `TestInjectorWiring`)

# Test requirements

- `test_injection_fires_on_working_stage_to_checkpoint` (unit): injector called once with `(spec, prev_working_stage)` on completion.
- `test_injection_does_not_fire_on_park` (unit): working-stage → PARKED does not fire.
- `test_injection_does_not_fire_leaving_queued_or_checkpoint_or_ready` (unit): leaving QUEUED / a checkpoint does not fire.
- `test_injection_does_not_fire_on_ready_resume` (unit): PARKED→READY and READY→stage do not fire.
- `test_failed_injection_does_not_block_transition` (unit): a raising injector → transition still returns 0 and state advances.

# Acceptance criteria

AC-18 (pair-keyed predicate including park-exclusion, prev-state passed), AC-11 (fail-silent injection inside the transition). Gate: tests compile and fail before implementation. Existing `test_state.py` assertions remain unmodified and passing.

# Model

Sonnet — predicate edge cases across the transition graph with wiring-contract monkeypatch.

# Wave

5
