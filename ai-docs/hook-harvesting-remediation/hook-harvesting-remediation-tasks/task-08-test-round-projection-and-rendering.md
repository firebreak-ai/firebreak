---
id: task-08
type: test
wave: 1
covers: [AC-08]
files_to_modify:
  - assets/fbk-scripts/tests/test_gates_code_review.py
  - assets/fbk-scripts/tests/test_report_rendering.py
completion_gate: "New projection and per-round rendering tests collect cleanly at the current tree and FAIL from a second git worktree at the pre-fix commit (40ec021 at spec time) with both files copied in (projection symbol absent; renderer collapses to one row per event); failing output captured in the per-round-detail slice's completion notes."
---

## Objective

Author the code-review gate's allowlist-projection guard (unknown keys dropped, out-of-enum severity rejected at the untrusted round-log boundary) and the report's one-row-per-detection-round rendering guard.

## Context

Slice: per-round-detail-survives-redaction (contract-evolving). Two defects: (a) the code-review gate (fbk/gates/code_review.py:155-168) writes round entries verbatim from `.code-review-rounds.json` — untrusted input per the project threat model — so free text under an unknown key would reach the events file under a key the redaction denylist has never met; (b) the report renderer (fbk/report.py:411-424, 493-503) collapses each `CODE_REVIEW_ROUNDS` event to a single total row instead of one row per detection round, and at `standard` the whole `rounds` list is currently stripped by redaction (handled by task-09).

**Declared new interface in `fbk/gates/code_review.py` (the implementation task copies this verbatim):**

```python
# Fixed severity vocabulary for round entries (matches fbk.pipeline.VALID_SEVERITIES).
ROUND_SEVERITIES = ("critical", "major", "minor", "info")

def project_round_entries(rounds: list) -> list:
    """Allowlist-project round entries read from the untrusted round log.

    Returns a new list: each entry becomes {"raised": ..., "survived": ...}
    plus "severity" only when entry.get("severity") is a member of
    ROUND_SEVERITIES.  Every other key is dropped.  Order is preserved.
    raised/survived are already int-validated by _read_round_log.
    """
```

`main()` applies `project_round_entries` to the rounds before computing totals and writing the event (totals are computed from raised/survived, which projection preserves, so totals are unchanged).

**Declared render contract for `fbk/report.py` (implementation copies verbatim):** the detection-rounds section prints one line per entry of each `CODE_REVIEW_ROUNDS` event's `data["rounds"]`, flattened in event order and numbered from 1: `  detection round {i}: raised={raised}  survived={survived}  severity={severity}` — the `severity=` segment omitted when the entry has no severity key. The dead `round_count` field is removed. The kill-rate line keeps its current computation from per-event `total_raised`/`total_survived`.

Two-files note: the projection (producer side) and the per-round render (consumer side) are the two halves of one seam contract; both files are touched only by this task in wave 1.

## Instructions

1. In `tests/test_gates_code_review.py`, add `test_project_round_entries_allowlists_exactly_three_keys`:
   - Input: `[{"raised": 3, "survived": 1, "severity": "major"}, {"raised": 2, "survived": 0, "severity": "minor", "notes": "FREE-TEXT-LEAK attempt"}, {"raised": 1, "survived": 1, "severity": "catastrophic"}]`.
   - Assert the return equals exactly `[{"raised": 3, "survived": 1, "severity": "major"}, {"raised": 2, "survived": 0, "severity": "minor"}, {"raised": 1, "survived": 1}]` — unknown key dropped, out-of-enum severity rejected (key dropped), known keys preserved in order. Also assert the input list objects were not mutated.
   Done when the exact-equality assertion is present.
2. In the same file, add `test_round_log_projected_before_event_write(tmp_path, monkeypatch)` driving the production entry point (follow the in-process `main()` pattern of `TestSpecGateWritesEnvelope` in `tests/test_gates_spec.py`: `capture_fixtures.make_project(..., instrumented=True, marked=True)`, `monkeypatch.chdir`, `monkeypatch.setattr(sys, "argv", ...)`, `pytest.raises(SystemExit)`):
   - Create a feature dir inside the project containing ONLY `.code-review-rounds.json` with `{"spec": "demo-spec", "rounds": <the three entries from step 1>}` (quality-scan/test-review artifacts deliberately absent — the gate fails with exit code 2, but event emission is an unconditional side effect; assert the SystemExit code is 2).
   - Read `<project>/.fbk-capture/events.jsonl`: exactly one `CODE_REVIEW_ROUNDS` event; assert `event["source"] == "code_review"` (the producer's exact source literal pin); `data["rounds"]` equals exactly the projected list from step 1; `data["total_raised"] == 6` and `data["total_survived"] == 2` (pinned hand-sums); and the raw file text contains neither `"FREE-TEXT-LEAK"` nor `"catastrophic"`.
   - Capture level resolves `standard` (marked project, no cfg) — so this also pins that projected per-round numerics survive standard-level redaction end-to-end.
   Done when all assertions are present. (Without the unknown-key case the guard cannot see the leak it exists to prevent.)
3. In `tests/test_report_rendering.py`, add `test_standard_level_renders_one_row_per_detection_round(tmp_path)` using the file's existing `_run_report`/project-setup helpers:
   - Events file: one `CODE_REVIEW_ROUNDS` event, `source="code_review"`, `capture_level="standard"`, `data={"spec": spec, "rounds": [{"raised": 3, "survived": 1, "severity": "major"}, {"raised": 2, "survived": 0, "severity": "minor"}], "total_raised": 5, "total_survived": 1}` — the post-projection production shape. State: any single ran stage (reuse `_build_full_state` or a minimal one).
   - Assert exactly 2 lines match the regex `detection round \d+:` (exact count, no collapsed single total).
   - Assert line content by structural regex: `detection round 1: raised=3\s+survived=1\s+severity=major` and `detection round 2: raised=2\s+survived=0\s+severity=minor`.
   - Assert the kill-rate line shows exactly `kill rate: 0.80` ((5-1)/5, hand-derived).
   Done when the exact-count and per-row assertions are present.
4. Verification step (no modification): run the rest of `tests/test_report_rendering.py` and `tests/test_gates_code_review.py`; confirm green.
5. Red run: from the pre-fix worktree with both files copied in, run the three tests; capture the failing output in the slice's completion notes.

## Files to create/modify

- `assets/fbk-scripts/tests/test_gates_code_review.py` (modify)
- `assets/fbk-scripts/tests/test_report_rendering.py` (modify)

## Test requirements

- Unit — `project_round_entries` over the three-entry fixture returns the exact projected list (unknown key dropped, out-of-enum severity rejected, order preserved).
- Integration (gate `main()` → events file) — one `CODE_REVIEW_ROUNDS` event with `source == "code_review"`, exactly the projected rounds, `total_raised == 6`, `total_survived == 2`; raw file free of the leak strings.
- Integration (subprocess report) — exactly 2 per-round rows with pinned raised/survived/severity values; `kill rate: 0.80`.

## Acceptance criteria

- AC-08: at `standard` the report renders per-round raised/survived/severity; the gate allowlist-projects each round entry to exactly `raised`, `survived`, enum-validated `severity` before the event is written; the guard fixture covers the unknown-key and out-of-enum cases.

## Model

Sonnet

## Wave

Wave 1
