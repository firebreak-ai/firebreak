---
id: task-27
type: implementation
wave: 8
covers: [AC-09]
files_to_modify:
  - assets/fbk-scripts/fbk/report.py
test_tasks: [task-15]
dependencies: [task-15, task-19]
completion_gate: "task-15's test passes (tests/test_report_rendering.py::test_checkpoint_period_turn_attributed_to_adjacent_working_stage — VALIDATING in=1500 out=300, REVIEWING in=2000 out=400); tests/test_capture_token_harvester.py and the rest of tests/test_report_rendering.py stay green"
---

## Objective

Restrict the transition-boundary list the report hands to the token harvester to working stages, so turns landing in checkpoint/idle windows are attributed to the adjacent working stage instead of vanishing into buckets the table never renders.

## Context

Slice: token-boundary-working-stages. `report.main` (fbk/report.py, the `transitions` comprehension in the lines following `stage_timestamps = st.get("stage_timestamps", {})` — lines 555-562 pre-fix) builds the boundary list from EVERY `stage_timestamps` key, including checkpoint states like `VALIDATED`. `token_harvester.harvest` hard-splits turns by these boundaries (`_attribute_turn` assigns a turn to the latest boundary at-or-before it), so a turn during a checkpoint window lands in a checkpoint bucket — and `_render_table` only renders working-stage rows, silently understating the adjacent working stage's totals.

**Contract (copied from task-15):** the report builds the transitions list only from `stage_timestamps` keys NOT in `NON_ACTIVE_STATES` (the shared constant from `fbk/state.py` — equivalently, only `WORKING_STAGES` members), so the harvester's hard-split windows run working-stage-start to next-working-stage-start and checkpoint-period turns fall into the preceding working stage's window.

`NON_ACTIVE_STATES` is already imported at module level by task-19 (wave 2) — use that binding, do not re-import.

Invariants to preserve: `token_harvester` itself is untouched (only the report's transitions list narrows); the no-transcripts placeholder branch and the empty-transitions branch keep their current shapes; the "coarse indicator" labeling is unchanged.

Constraints: do NOT modify any test file; file scope is exactly `fbk/report.py`. Path relative to `/home/rahvin/context-assets/assets/fbk-scripts/`.

## Instructions

1. In `report.main`, change the `transitions` comprehension to filter the keys:
   ```python
   transitions = [
       {"stage": k, "timestamp": v}
       for k, v in sorted(
           stage_timestamps.items(),
           key=lambda item: item[1] or "",
       )
       if k not in NON_ACTIVE_STATES
   ]
   ```
   Add a comment above it: boundaries are working stages only — a checkpoint-state boundary would siphon the turns that follow it into a bucket the table never renders, understating the adjacent working stage (the harvester's windows now run working-stage start to next working-stage start). Done when no checkpoint/idle key can reach `token_harvester.harvest`.
2. Leave the `elif transitions:` placeholder branch (the all-stages-unavailable dict) and the `else` branch untouched — the placeholder dict is keyed by `stage_timestamps` but only working-stage keys are ever rendered, so narrowing it would change nothing observable. Done when the diff touches only the comprehension and its comment.
3. Run the gating test. Expected arithmetic (task-15 fixture): turns at 00:30 (1000/200) and 01:30 (500/100) both fall in VALIDATING's window once VALIDATED stops being a boundary → `in=1500 out=300`; the 02:30 turn (2000/400) lands in REVIEWING → `in=2000 out=400`; rendered sums equal the fixture totals (3500/700) with no turn dropped.

## Files to create/modify

- `assets/fbk-scripts/fbk/report.py` (modify)

## Test requirements

- Gating: task-15's `tests/test_report_rendering.py::test_checkpoint_period_turn_attributed_to_adjacent_working_stage`.
- Must stay green: `tests/test_capture_token_harvester.py` (harvester unchanged); the rest of `tests/test_report_rendering.py`; `tests/test_capture_e2e_seam.py` (its token rows derive from working-stage boundaries already).

## Acceptance criteria

- AC-09: per-stage token totals attribute turns during checkpoint/idle periods to the adjacent working stage; exact per-stage sums account for every fixture turn, so no turn is dropped into a non-rendered bucket.

## Model

Sonnet

## Wave

Wave 8
