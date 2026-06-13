---
id: task-10
type: test
wave: 3
covers: [AC-07, AC-17, AC-16]
files_to_create:
  - assets/fbk-scripts/tests/test_report_arithmetic.py
completion_gate: "tests compile and fail before implementation"
---

# Objective

Write the unit tests for the report's exact-value computations: first-try vs after-rework gate classification keyed on park boundaries, the first-try pass-rate denominator, the code-review kill-rate value, state-derived parks-with-reasons and rework rows, and report-time subagent identity filtering.

# Context

The report aggregates events and the state engine into one table. Its rate formulas are defined, and the report computes exact values, not just labels:

- **First-try vs after-rework.** "First-try" attempts are every gate attempt before the stage's first park; "after-rework" are every attempt from the first ready re-entry onward. The first-try pass rate is `first-try attempts that passed / first-try attempts made`.
- **Kill rate.** `(total_raised − total_confirmed) / total_raised`, presented as a relative trend signal with an acknowledged-true-positive caveat label.
- **State-derived rows.** Parks per stage come from the state engine's `error_history` (each entry has `stage`, `error`, `timestamp`); a park with an empty reason renders a visible "(no reason recorded)" row rather than being dropped. Rework is derived from stage re-entry: a stage appearing twice in the timestamps / `error_history` produces a non-empty rework row and after-rework classification. This depends on the state store retaining repeated entries — a regression to last-write-wins must be caught.
- **Subagent filtering.** Subagent-completion events are counted only when the agent identity is a known Firebreak agent.

The report lives flat at `fbk/report.py`, registered `report` in `COMMAND_MAP`. This task targets the report's pure computation helpers, which the implementation MUST expose as importable functions (these tests mandate them). Pinned names and signatures (call verbatim):
- `report.classify_gate_attempts(events, state, stage) -> list[dict]` — each entry `{"phase": "first_try" | "after_rework", "passed": bool}`; "first_try" = attempts before the stage's first park, "after_rework" = attempts from the first READY re-entry onward.
- `report.first_try_pass_rate(attempts) -> float` — first-try attempts that passed / first-try attempts made.
- `report.kill_rate(rounds) -> float` — `(total_raised − total_confirmed) / total_raised`.
- `report.derive_parks(state, stage) -> list[dict]` — each `{"reason": str | None}`; an empty reason renders "(no reason recorded)".
- `report.derive_rework(state, stage) -> int` — re-entry count derived from repeated stage timestamps.
- `report.stage_summary(spec, stage) -> str` — the per-stage block body (IF-D-07).

Import `import fbk.report as report` inside `try/except ImportError` with a module-level skipif. Build events with `capture_fixtures.build_event`/`write_events` and state with `build_state`/`write_state`.

# Instructions

1. Create `tests/test_report_arithmetic.py`; import `report` inside `try/except ImportError`; module-level skipif.
2. `test_attempt_before_park_classifies_first_try`: build a stage's gate-attempt events all before the first park and a state with no re-entry; call `report.classify_gate_attempts(events, state, stage)` and assert every returned entry has `phase == "first_try"`.
3. `test_attempt_after_ready_reentry_classifies_after_rework`: build a state where the stage was parked then re-entered (READY → stage) and gate attempts after the re-entry; call `classify_gate_attempts(...)` and assert those attempts have `phase == "after_rework"`.
4. `test_first_try_pass_rate_is_exact_fraction`: build three first-try gate attempts for one stage with outcomes fail, fail, pass (all before any park); pass the first-try attempts to `report.first_try_pass_rate(attempts)` and assert it equals exactly `pytest.approx(1/3)`. Pair the value with a presence assertion that the first-try attempt list passed in is non-empty.
5. `test_kill_rate_is_exact_value`: build a `rounds` input with known per-round raised/survived such that total_raised=10 and total_confirmed=3; call `report.kill_rate(rounds)` and assert it equals exactly `0.7` (`(10 - 3) / 10`). Assert the exact float.
6. `test_park_with_empty_reason_renders_no_reason_row`: build a state whose `error_history` has a park with an empty `error` string; call `report.derive_parks(state, stage)`; assert the returned list contains one entry for that park with `reason` empty/None, and confirm the renderer surfaces it as "(no reason recorded)" (assert the derived entry exists rather than being dropped).
7. `test_rework_derived_from_repeated_stage_entry`: build a state where a stage appears twice (re-entered after a park — present in `error_history` and/or a second timestamp); call `report.derive_rework(state, stage)` and assert it returns a count `>= 1` (reflects the re-entry); additionally call `classify_gate_attempts(...)` and assert at least one attempt carries `phase == "after_rework"`. This guards against a last-write-wins regression in the state store.
8. `test_subagent_count_excludes_unknown_identity`: build SUBAGENT_STOP events, some with a known agent identity (e.g. `fbk-implementer`, recognized by the fallback set) and some with empty/unknown identity; assert the report's aggregated subagent count includes only the known-identity events. Use a known agent name the fallback set recognizes so the test does not depend on a fixture scan root.

# Files to create/modify

- `tests/test_report_arithmetic.py`

# Test requirements

- `test_attempt_before_park_classifies_first_try` (unit): `classify_gate_attempts` labels pre-park attempts `phase == "first_try"`.
- `test_attempt_after_ready_reentry_classifies_after_rework` (unit): `classify_gate_attempts` labels post-re-entry attempts `phase == "after_rework"`.
- `test_first_try_pass_rate_is_exact_fraction` (unit): `first_try_pass_rate` of fail/fail/pass → exact `1/3`.
- `test_kill_rate_is_exact_value` (unit): `kill_rate` for raised=10/confirmed=3 → exact `0.7`.
- `test_park_with_empty_reason_renders_no_reason_row` (unit): `derive_parks` keeps an empty-reason park as a present entry → "(no reason recorded)".
- `test_rework_derived_from_repeated_stage_entry` (unit): `derive_rework` returns `>= 1` for a repeated stage entry + after-rework classification.
- `test_subagent_count_excludes_unknown_identity` (unit): subagent aggregate counts only known-identity events.

# Acceptance criteria

AC-07 (defined rate formulas computed exactly + kill rate), AC-17 (state-derived parks/rework, empty-reason row), AC-16 (report-time subagent filtering). Gate: tests compile and fail before implementation.

# Model

Sonnet — exact-value rate/classification arithmetic with park-boundary logic.

# Wave

3
