---
id: task-09
type: test
wave: 1
covers: [AC-08]
files_to_modify:
  - assets/fbk-scripts/tests/test_capture_event_writer.py
completion_gate: "Rebuilt standard-level redaction test collects cleanly at the current tree and FAILS (rounds list stripped entirely) from a second git worktree at the pre-fix commit (40ec021 at spec time) with the file copied in; failing output captured in the per-round-detail slice's completion notes."
---

## Objective

Rebuild the standard-level strip test with a nested-round fixture: free text inside a round entry is stripped while the round's numeric fields and enum severity tag survive.

## Context

Slice: per-round-detail-survives-redaction (this rebuild's red-then-green run is owned by this slice per the spec's ownership split; the `schema.SOURCES`-driven enumeration of the same file belongs to the redaction-coverage slice, task-16, staggered to wave 2). Today `schema.FREETEXT_KEYS` contains `"rounds"`, so `schema.redact` deletes the entire per-round list at `standard` — the report can never render per-round detail. The fix removes `"rounds"` from `FREETEXT_KEYS` and makes `redact` recurse into nested structures as defense-in-depth behind the gate's allowlist projection.

**Declared schema contract (the implementation task copies this):** `"rounds"` is removed from `FREETEXT_KEYS`; `schema.redact(data, level)` at any non-`full` level removes every key in `FREETEXT_KEYS` at the top level AND recursively inside nested dicts and inside dicts contained in nested lists, returning copies (input never mutated).

`"reason_text"` is an existing `FREETEXT_KEYS` member — it is the nested free-text key the fixture plants inside a round entry (a known key under recursion; the unknown-key case is the gate projection's job, task-08).

## Instructions

1. Rebuild `test_standard_level_strips_freetext_payload` in `tests/test_capture_event_writer.py` (keep the name — it is the corrected guard the spec names):
   - Call the production path: `event_writer.write("CODE_REVIEW_ROUNDS", "code_review", data, "s", "IMPLEMENTING", "standard", path)` with
     `data = {"rounds": [{"raised": 3, "survived": 1, "severity": "major", "reason_text": "NESTED-FREETEXT sentinel"}], "total_raised": 3, "total_survived": 1, "tool_input": {"command": "secret"}, "count": 2}`.
   - Read the single written line and assert, on `record["data"]`:
     - `"tool_input"` absent (top-level strip still works);
     - `data["count"] == 2` and `data["total_raised"] == 3` and `data["total_survived"] == 1` (structural/numeric survival);
     - `data["rounds"] == [{"raised": 3, "survived": 1, "severity": "major"}]` — exact equality: the round survives redaction, its numeric fields and enum severity tag intact, the nested free-text key stripped by the recursion.
   - Assert the raw written line contains neither `"NESTED-FREETEXT"` nor `"secret"`.
   - Docstring: pre-fix, `"rounds"` is itself a denylist key, so the whole list is stripped and the exact-equality assertion fails red; post-fix the recursion strips only the nested free-text key.
   Done when the exact-equality and raw-line assertions are present.
2. Do not touch `test_full_level_preserves_payload` or add any `SOURCES` enumeration here — that is task-16 (wave 2, same file; the wave stagger is deliberate).
3. Red run: from the pre-fix worktree with the file copied in, run the rebuilt test; capture the failing output in the per-round-detail slice's completion notes.

## Files to create/modify

- `assets/fbk-scripts/tests/test_capture_event_writer.py` (modify)

## Test requirements

- Unit (production write path) — at `standard`: written `data["rounds"]` equals exactly `[{"raised": 3, "survived": 1, "severity": "major"}]`; `count == 2`, `total_raised == 3`, `total_survived == 1` survive; `tool_input` absent; raw line free of both sentinel strings.

## Acceptance criteria

- AC-08 (redaction half): the per-round numeric fields are not stripped by redaction, and redaction recurses into nested round entries so a free-text string inside a round entry is stripped at `standard` while the numeric counts and enum severity tag survive.

## Model

Sonnet

## Wave

Wave 1
