---
id: task-26
type: implementation
wave: 2
covers: [AC-06, AC-17]
files_to_create:
  - assets/fbk-scripts/fbk/capture/token_harvester.py
test_tasks: [task-08]
completion_gate: "task-08 tests pass"
---

# 1 Objective

Produce the post-hoc token harvester: a pure reader of Claude Code session transcripts that attributes each turn to the stage active at its timestamp by a hard split on the state engine's transition timestamps, aggregates across multiple transcripts of one cycle into one per-stage total set, marks a missing/unreadable transcript's stages `available: False` (never zero), and emits a per-stage count of boundary-adjacent turns. It never writes events.

# 2 Context

The harvester reads what the harness already records — it adds no live instrumentation. It ports its file-parsing internals from the validated prototype at `ai-docs/hook-harvesting/transcript_harvest.py` (`harvest_file`/`harvest_session`): assistant records carry `.message.usage` with `input_tokens`/`output_tokens`/`cache_read_input_tokens`/`cache_creation_input_tokens`, `.message.model`, top-level `.timestamp`, `.isSidechain`; tool_use blocks live in assistant `.message.content[]`; tool results (with `is_error`) arrive in user records. Reuse that parsing logic; the new responsibility is stage attribution and the unavailable/boundary-adjacent accounting.

Attribution is a hard split on transition timestamps: a turn STRICTLY BEFORE a boundary timestamp belongs to the earlier stage; a turn AT-OR-AFTER the boundary belongs to the later stage. Tokens-per-stage is a coarse indicator, so the harvester also reports, per stage, how many of its turns sit within one transition-interval of a stage boundary (the boundary-adjacent count) so a consumer can judge how much of a stage's total sits near a boundary.

The unavailable-vs-zero distinction is load-bearing: a missing or unreadable transcript marks its contributed stages `available: False` (the report renders the literal `unavailable`), never `0`.

# 3 Instructions

1. Create `fbk/capture/token_harvester.py`. Port the per-file parsing from the prototype's `harvest_file` (timestamp parse, assistant usage tally by token type and model, tool_use call counting, tool_result error counting). Keep it a pure reader: open files read-only, never write events. Completion: parsing a fixture transcript yields per-turn token/model/tool data.
2. Implement `harvest(transcript_paths: list[str], transitions: list[dict]) -> dict[str, dict]`. `transitions` is the ordered state history, each entry `{"stage": str, "timestamp": <iso8601>}`. Parse each transition timestamp; build the ordered list of (stage, start_ts) so a turn's timestamp maps to exactly one stage by the hard split (strictly-before → earlier stage, at-or-after a boundary → later stage). The interval length for boundary-adjacency is the gap between a stage's start and the next stage's start. Completion: with boundaries `IMPLEMENTING@T1`, `IMPLEMENTED@T2`, a turn before T2 attributes to `IMPLEMENTING` and a turn at-or-after T2 to `IMPLEMENTED`.
3. For each turn across all transcripts, accumulate into the owning stage's totals: `tokens_by_type` (dict: `input`/`output`/`cache_read`/`cache_creation`), `tokens_by_model` (dict: model → token dict), `tool_calls` (int), `tool_errors` (int), and `boundary_adjacent_turns` (int — incremented when the turn's timestamp is within one transition-interval of the nearest boundary of its stage). Each returned stage entry also carries `available: bool`. Completion: per-stage entries carry exactly `{"tokens_by_type", "tokens_by_model", "tool_calls", "tool_errors", "boundary_adjacent_turns", "available"}`.
4. Aggregation across transcripts: multiple transcript paths for one cycle sum into ONE per-stage total set (a main session plus a subagent session both contribute to the same stage's totals). Completion: two transcripts contributing to one stage yield that stage's `tokens_by_type` equal to the exact integer sum of both.
5. Unavailable handling: when a transcript path is missing or cannot be opened, mark every stage it would have contributed to with `available: False` and do NOT present its token totals as `0` — leave the totals absent/None-like so the report renders `unavailable`. Concretely: if the ONLY transcript(s) covering a stage are unreadable, that stage's entry has `available: False`; a stage with at least one readable contributing transcript is `available: True`. Practically, when every provided transcript path is unreadable, every stage in `transitions` is marked `available: False`. Completion: `harvest([<nonexistent path>], transitions)` returns each affected stage with `available is False` and its token totals not rendered as zero.
6. Return the dict keyed by stage name. A stage present in `transitions` but with no turns and a readable transcript set is `available: True` with zeroed counts (legitimately empty, distinct from unavailable). Completion: the keys are the stage names from `transitions`.

# 4 Files to create/modify

- Create `fbk/capture/token_harvester.py`

# 5 Test requirements

Makes task-08 (`tests/test_capture_token_harvester.py`) pass: turn-before-boundary → earlier stage with exact totals; turn-at-boundary → later stage; missing transcript → `available: False` not zero; two transcripts aggregate into one per-stage total set (exact integer sum); per-stage boundary-adjacent turn count equals the known near-boundary count.

# 6 Acceptance criteria

Primary: task-08's tests pass. Covers AC-06 (stage attribution, aggregation, unavailable-vs-zero, boundary-adjacent count) and AC-17 (unavailable distinct from zero).

# 7 Model

Sonnet

# 8 Wave

2
