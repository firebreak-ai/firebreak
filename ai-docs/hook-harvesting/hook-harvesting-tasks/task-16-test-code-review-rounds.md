---
id: task-16
type: test
wave: 4
covers: [AC-05, AC-27]
files_to_modify:
  - assets/fbk-scripts/tests/test_gates_code_review.py
completion_gate: "tests compile and fail before implementation"
---

# Objective

Add new assertions to the code-review-gate test file proving the gate, when a valid `.code-review-rounds.json` is present, emits a `CODE_REVIEW_ROUNDS` event with per-round and total counts; with the file absent emits no event and leaves pass/fail unchanged; with a malformed or out-of-bounds file emits no event, warns on stderr, and leaves pass/fail unchanged.

# Context

The code-review gate `fbk/gates/code_review.py` validates the code-review artifact tree. This feature adds a new read of `.code-review-rounds.json` (written by the code-review skill in the feature directory) and a `CODE_REVIEW_ROUNDS` event at check time, carrying per-round raised/survived/severity and totals. This is an agent-to-deterministic trust boundary. The round file's shape: `{schema_version, spec, rounds: [{round, raised, survived, severity_breakdown}]}`. Its values are bounded — integer types, non-negative ranges, a maximum rounds-list length, and a maximum file size — and a file violating any bound is treated as malformed: no event, a stderr warning, unchanged gate pass/fail. Absent file → no event, gate logic unaffected. Malformed (unparseable or out-of-bounds) → no event plus a stderr warning. The existing artifact-check and pass/fail logic are unchanged.

The existing file `tests/test_gates_code_review.py` has a `make_code_review_dir(tmp_path)` helper that builds a passing artifact tree under `tmp_path/ai-docs/sample` and runs the gate via both `validate_code_review(str(feature_dir))` (direct) and `fbk.py code-review-gate <feature_dir>` (subprocess, `FBK_PY` defined at top). The event write happens at gate check time. To make the write land in a fixture location, run the gate subprocess with `cwd=<instrumented tmp project>`; place the round file in the feature dir the gate reads.

# Instructions

1. In `tests/test_gates_code_review.py`, add a new test class `TestCodeReviewRoundsEvent` guarded to skip when the event writer is absent (`from fbk.capture import event_writer` inside `try/except ImportError`, skipif). Reuse `make_code_review_dir`.
2. `test_valid_round_file_emits_event`: build the passing artifact tree; write a valid `.code-review-rounds.json` in the feature dir with two rounds of known raised/survived (e.g. round 1 raised=5 survived=2, round 2 raised=1 survived=0); run the gate subprocess with `cwd=<instrumented project>` (feature dir located under that project so the events file lands there); assert the gate result is unchanged (pass) AND a `CODE_REVIEW_ROUNDS` event was written carrying per-round entries and totals matching the fixture (total raised = 6, etc.). Assert exact per-round and total values.
3. `test_absent_round_file_emits_no_event_unchanged_passfail`: build the passing tree with NO round file; run the gate; assert the gate result is still pass AND no `CODE_REVIEW_ROUNDS` event was written (events file absent or contains zero CODE_REVIEW_ROUNDS lines).
4. `test_malformed_round_file_no_event_warns_unchanged`: write a `.code-review-rounds.json` that is not valid JSON (e.g. `"{ broken"`); run the gate; assert the gate result is unchanged (pass) AND no `CODE_REVIEW_ROUNDS` event AND a stderr warning appears (`"Traceback" not in stderr` but a warning line is present).
5. `test_out_of_bounds_round_value_treated_malformed`: write a round file with an out-of-range value — a negative `raised` count, or a non-integer count, or a rounds list past the max length, or a file past the max size; run the gate; assert no event, a stderr warning, and unchanged pass/fail. Cover at least two of these bound violations as separate parametrized cases or separate tests (negative count; over-length rounds list). If the exact max-rounds-length and max-file-size bounds are not pinned numerically by the spec/contract, assert the qualitative behavior (an obviously-too-large file and an obviously-negative count are rejected) and note in the test that the precise thresholds are an implementation detail.

# Files to create/modify

- `tests/test_gates_code_review.py` (add `TestCodeReviewRoundsEvent`)

# Test requirements

- `test_valid_round_file_emits_event` (integration): valid round file → CODE_REVIEW_ROUNDS event with exact per-round + total counts; pass/fail unchanged.
- `test_absent_round_file_emits_no_event_unchanged_passfail` (integration): absent file → no event, pass/fail unchanged.
- `test_malformed_round_file_no_event_warns_unchanged` (integration): unparseable file → no event, stderr warning, pass/fail unchanged.
- `test_out_of_bounds_round_value_treated_malformed` (integration, ≥2 cases): negative count / over-length rounds list → treated malformed (no event, warning, unchanged pass/fail).

# Acceptance criteria

AC-05 (round logging + trust boundary), AC-27 (round-log bounds). Gate: tests compile and fail before implementation. Existing gate pass/fail assertions unaffected.

# Model

Sonnet — trust-boundary parsing with bound-violation cases and subprocess gate runs.

# Wave

4
