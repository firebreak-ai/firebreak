---
id: task-08
type: test
wave: 2
covers: [AC-06, AC-17]
files_to_create:
  - assets/fbk-scripts/tests/test_capture_token_harvester.py
completion_gate: "tests compile and fail before implementation"
---

# Objective

Write the unit tests for the post-hoc token harvester: hard-split stage attribution on transition timestamps, the missing/unreadable transcript marked `unavailable` (never `0`), cross-session aggregation into one per-stage total set, and the per-stage boundary-adjacent turn count.

# Context

The harvester is a pure reader of Claude Code session transcripts. It attributes each transcript turn to the stage active at the turn's timestamp by a hard split on the state engine's transition timestamps: a turn strictly before a boundary goes to the earlier stage, a turn at-or-after the boundary goes to the later stage. Multiple session/subagent transcripts of one cycle aggregate into one per-stage total set. A missing or unreadable transcript marks the affected stage's token rows the literal `unavailable`, never `0` — the unavailable-vs-zero distinction is load-bearing. The harvester also emits, per stage, a count of boundary-adjacent turns (turns within one transition-interval of a stage boundary) so a consumer can see how much of a stage's total sits near a boundary; the report labels tokens-per-stage a coarse indicator. The harvester never writes events.

Transcript shape (from the validated prototype): assistant records carry `.message.usage` with `input_tokens`/`output_tokens`/`cache_read_input_tokens`/`cache_creation_input_tokens`, `.message.model`, top-level `.timestamp`, `.isSidechain`; tool_use blocks live in assistant `.message.content[]`. Build fixtures with `capture_fixtures.build_transcript`/`write_transcript`/`write_unreadable_transcript`. Stage boundaries come from a state file's `stage_timestamps` (`capture_fixtures.build_state`).

Import `from fbk.capture import token_harvester` inside `try/except ImportError` with a module-level skipif. The harvester is a pure reader; its internals port from the prototype `harvest_file`/`harvest_session`.

Pinned signature (call verbatim):
`token_harvester.harvest(transcript_paths: list[str], transitions: list[dict]) -> dict[str, dict]`
- `transitions` is the ordered state history, each entry `{"stage": str, "timestamp": <iso8601>}`.
- Returns a dict keyed by stage name → `{"tokens_by_type": dict, "tokens_by_model": dict, "tool_calls": int, "tool_errors": int, "boundary_adjacent_turns": int, "available": bool}`.
- Attribution: a turn strictly before a boundary timestamp → the earlier stage; at-or-after → the later stage.
- A missing/unreadable transcript marks the affected stages `"available": False` (which the report renders as `unavailable`, never `0`).

# Instructions

1. Create `tests/test_capture_token_harvester.py`; import `token_harvester` inside `try/except ImportError`; module-level skipif. Build `transitions` as a list of `{"stage", "timestamp"}` entries (you may derive these from a `capture_fixtures.build_state` `stage_timestamps`, or construct the list directly).
2. `test_turn_before_boundary_attributes_to_earlier_stage`: build transitions with two boundaries (`IMPLEMENTING` at T1, `IMPLEMENTED` at T2); build a transcript with one assistant turn timestamped strictly before T2 and one at-or-after T2; call `harvest([transcript_path], transitions)`; assert `result["IMPLEMENTING"]["tokens_by_type"]` carries the earlier turn's tokens and `result["IMPLEMENTED"]["tokens_by_type"]` the later turn's. Assert the exact per-stage input/output token totals from the known fixture values, and assert both stages have `"available": True`.
3. `test_turn_exactly_at_boundary_attributes_to_later_stage`: a turn whose timestamp equals the boundary T2 attributes to the later stage (`IMPLEMENTED`), confirming the at-or-after rule. Assert exact attribution.
4. `test_missing_transcript_marks_unavailable_not_zero`: call `harvest([<nonexistent or unreadable path>], transitions)`; assert the affected stages carry `"available": False` and that their token totals are NOT `0` / not presented as zero. Assert `result[<stage>]["available"] is False` explicitly (this is what the report renders as the literal `unavailable`).
5. `test_two_transcripts_aggregate_into_one_total_set`: build two transcripts for the same cycle (e.g. a main session and a subagent session) each contributing turns to the same stage; call `harvest([path_a, path_b], transitions)`; assert the per-stage `tokens_by_type` total equals the SUM of both transcripts' contributions for that stage (exact integer sum), proving aggregation into one set.
6. `test_boundary_adjacent_turn_count_emitted`: build a transcript with some turns close to a boundary (within one transition-interval) and some far; harvest; assert `result[<stage>]["boundary_adjacent_turns"]` equals the known number of near-boundary turns. Pair the exact count with a presence assertion that the field exists.

# Files to create/modify

- `tests/test_capture_token_harvester.py`

# Test requirements

- `test_turn_before_boundary_attributes_to_earlier_stage` (unit): hard-split attribution, exact per-stage totals.
- `test_turn_exactly_at_boundary_attributes_to_later_stage` (unit): at-or-after rule sends the boundary turn to the later stage.
- `test_missing_transcript_marks_unavailable_not_zero` (unit): missing transcript → literal `"unavailable"`, never `0`.
- `test_two_transcripts_aggregate_into_one_total_set` (unit): two transcripts sum into one per-stage total.
- `test_boundary_adjacent_turn_count_emitted` (unit): per-stage boundary-adjacent turn count equals the known near-boundary turn count.

# Acceptance criteria

AC-06 (stage attribution, aggregation, unavailable-vs-zero, boundary-adjacent count), AC-17 (unavailable distinct from zero). Gate: tests compile and fail before implementation.

# Model

Sonnet — timestamp attribution edge cases and aggregation need judgment.

# Wave

2
