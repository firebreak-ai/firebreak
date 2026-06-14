---
id: task-33
type: implementation
wave: 4
covers: [AC-05, AC-27]
files_to_modify:
  - assets/fbk-scripts/fbk/gates/code_review.py
  - assets/skills/fbk-code-review/SKILL.md
test_tasks: [task-16]
completion_gate: "task-16 tests pass"
dependencies: [task-27]
---

# 1 Objective

Extend the code-review gate to read the skill-written `.code-review-rounds.json` at check time and emit a `CODE_REVIEW_ROUNDS` event carrying per-round raised/survived/severity and totals — emitting no event with unchanged pass/fail when the file is absent, and treating a malformed or out-of-bounds file as malformed (no event, a stderr warning, unchanged pass/fail). Add the skill instruction that writes the file during the detection loop.

# 2 Context

The code-review gate `fbk/gates/code_review.py` validates the review artifact tree (`validate_code_review`) and exits pass/fail. This feature adds a new read of `.code-review-rounds.json` (written by the code-review skill in the feature directory) and a `CODE_REVIEW_ROUNDS` event at check time — an agent-to-deterministic trust boundary: an agent-mediated skill writes a file a deterministic gate consumes. The gate's existing artifact-check and pass/fail logic are UNCHANGED; the event is a side effect.

Round file shape: `{"schema_version": "1.0", "spec": <str>, "rounds": [{"round": <int>, "raised": <int>, "survived": <int>, "severity_breakdown": <obj>}, ...]}`. Its values are bounded — integer types, non-negative ranges, a maximum rounds-list length, and a maximum file size — and a file violating ANY bound is malformed: no event, a stderr warning, unchanged pass/fail. Absent file → no event, gate logic unaffected. Malformed (unparseable or out-of-bounds) → no event plus a stderr warning.

Pinned bounds (document them in the gate as constants comfortably above any realistic run): max 100 rounds in the list, max file size 64 KB. A round's `raised`/`survived` must be non-negative integers.

The events file goes under the project root the gate runs in — `os.path.join(os.getcwd(), ".fbk-capture", "events.jsonl")`. The level is `gate_check.resolve_capture_level(os.getcwd())`.

# 3 Instructions

1. In `fbk/gates/code_review.py`, add `from fbk.capture import event_writer, gate_check` (lazy/function-level import is fine). Define bound constants `MAX_ROUNDS = 100` and `MAX_ROUND_FILE_BYTES = 64 * 1024`.
2. Implement a helper `_read_round_log(feature_dir) -> dict | None` that returns the validated round-log dict or `None`. Steps: build the path `<feature_dir>/.code-review-rounds.json`; if absent → return `None` (no event, no warning). If present: reject when the file size exceeds `MAX_ROUND_FILE_BYTES` (malformed); parse JSON (a parse failure is malformed); validate the shape — `rounds` is a list no longer than `MAX_ROUNDS`, each round's `raised`/`survived` are non-negative integers (a negative or non-integer count is malformed). On any malformed condition, print a stderr warning and return a sentinel distinguishing "malformed" from "absent" (e.g. raise no exception but return `None` after warning — and ensure the absent case does NOT warn). Completion: a valid file returns the parsed dict; an unparseable, over-size, over-length, or negative-count file warns on stderr and yields no event; an absent file yields no event and no warning.
3. In `main()` (after `validate_code_review` computes the result and the gate prints its JSON, BEFORE `sys.exit`), read the round log via the helper. When a valid round log is present, compute totals (total_raised, total_survived/confirmed) and emit ONE `CODE_REVIEW_ROUNDS` event fail-silently: `event_writer.write("CODE_REVIEW_ROUNDS", "code_review", {"spec": <spec>, "rounds": <per-round list>, "total_raised": <int>, "total_survived": <int>}, <spec>, None, gate_check.resolve_capture_level(os.getcwd()), <events_path>)`. The gate's pass/fail and exit code are unchanged by the event. Completion: a valid round file emits a `CODE_REVIEW_ROUNDS` event with per-round entries and totals matching the fixture; absent/malformed → no event; pass/fail unchanged in every case.
4. Fail-silence: wrap the read+write so a write failure or any exception never changes the gate's pass/fail or exit code, and no traceback escapes. Completion: an unwritable events path leaves the gate result unchanged with no traceback.
5. **Skill instruction (`assets/skills/fbk-code-review/SKILL.md`):** in the iterative detection-and-verification loop section (the numbered list ending at "Terminate ... after a maximum of 5 rounds"), add an instruction that the orchestrator writes `.code-review-rounds.json` in the feature directory during/after the loop, recording per-round `round`, `raised`, `survived`, and `severity_breakdown` plus `schema_version` and `spec`, so the code-review gate can emit the detection-round metrics. Phrase it as a capability the orchestrator performs (what to record and where), consistent with the existing numbered steps' voice — and note the gate reads it at check time. Completion: the skill instructs writing the round log with the documented schema in the feature directory.

# 4 Files to create/modify

- Modify `fbk/gates/code_review.py` (add round-log read + `CODE_REVIEW_ROUNDS` event)
- Modify `assets/skills/fbk-code-review/SKILL.md` (add the write-`.code-review-rounds.json` instruction)

# 5 Test requirements

Makes task-16 (new `TestCodeReviewRoundsEvent` in `tests/test_gates_code_review.py`) pass: a valid round file emits a `CODE_REVIEW_ROUNDS` event with exact per-round and total counts (pass/fail unchanged); an absent file emits no event (pass/fail unchanged); a malformed file emits no event with a stderr warning; out-of-bounds values (negative count, over-length rounds list) are treated malformed. Existing gate pass/fail assertions stay green.

# 6 Acceptance criteria

Primary: task-16's tests pass. Covers AC-05 (round logging + trust boundary) and AC-27 (round-log bounds).

# 7 Model

Sonnet

# 8 Wave

4
