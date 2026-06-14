---
id: task-15
type: test
wave: 2
covers: [AC-09]
files_to_modify:
  - assets/fbk-scripts/tests/test_report_rendering.py
completion_gate: "Token-boundary test collects cleanly at the current tree and FAILS (VALIDATING shows in=1000, the checkpoint turn siphoned into a non-rendered bucket) from a second git worktree at the pre-fix commit (40ec021 at spec time) with the file copied in; failing output captured in the token-boundary slice's completion notes."
---

## Objective

Author the guard that per-stage token totals attribute turns during checkpoint periods to the adjacent working stage, with every fixture turn accounted for in exact sums.

## Context

Slice: token-boundary-working-stages (contract-evolving). `fbk/report.py` main (lines 556-572) builds the transition-boundary list handed to `token_harvester.harvest` from EVERY `stage_timestamps` key — including checkpoint states like `VALIDATED`. A turn that lands in a checkpoint window is attributed to a checkpoint bucket the table never renders, silently understating the adjacent working stage's totals (F-10).

**Declared contract (the implementation task copies this):** the report builds the transitions list only from `stage_timestamps` keys NOT in `NON_ACTIVE_STATES` (the shared constant from `fbk/state.py` — equivalently, only `WORKING_STAGES` members), so the harvester's hard-split windows run working-stage-start to next-working-stage-start and checkpoint-period turns fall into the preceding working stage's window.

Harvester facts (verified): `harvest(transcript_paths, transitions)` builds boundaries from the transitions in timestamp order; `_attribute_turn` assigns a turn to the latest boundary whose start is at-or-before the turn. Transcripts live at `<project>/.claude/projects/<spec>/*.jsonl`; `capture_fixtures.write_transcript` builds the production record shape. The report prints per-stage rows as `tokens: in=<n> out=<n>`.

Wave note: wave 2 because task-08 owns `tests/test_report_rendering.py` in wave 1.

## Instructions

1. Add `test_checkpoint_period_turn_attributed_to_adjacent_working_stage(tmp_path)` to `tests/test_report_rendering.py`, following the file's `_run_report` subprocess pattern:
   - State (via `capture_fixtures.build_state` / `write_state`, `current_state="REVIEWING"`):
     `{"QUEUED": "2025-12-31T23:00:00+00:00", "VALIDATING": "2026-01-01T00:00:00+00:00", "VALIDATED": "2026-01-01T01:00:00+00:00", "REVIEWING": "2026-01-01T02:00:00+00:00"}`.
   - Empty events list is fine (write an events file with zero events or skip it — token rows derive from transcripts).
   - Transcript at `<project>/.claude/projects/<spec>/session.jsonl` with exactly three turns (model `"claude-opus-4-8"`, no sidechain, no tools):
     - 00:30:00 — input 1000, output 200 (VALIDATING window);
     - 01:30:00 — input 500, output 100 (the VALIDATED checkpoint window — the contested turn; comment it);
     - 02:30:00 — input 2000, output 400 (REVIEWING window).
   - Run the report; assert rc 0; pin by regex:
     - `VALIDATING ... tokens: in=1500 out=300` — hand-derived: 1000+500 / 200+100; the checkpoint-period turn belongs to the adjacent (preceding) working stage;
     - `REVIEWING ... tokens: in=2000 out=400`.
   - Turn-accounting comment: rendered sums 1500+2000 = 3500 in and 300+400 = 700 out equal the fixture's full turn totals — no turn dropped into a non-rendered bucket.
   - Docstring red mechanics: pre-fix, `VALIDATED` is a boundary, the 01:30 turn lands in its non-rendered bucket, and VALIDATING reads in=1000 — failing the in=1500 pin.
   Done when both pinned-row assertions and the accounting comment are present.
2. Verification step (no modification): run `tests/test_capture_token_harvester.py` and the rest of `tests/test_report_rendering.py`; confirm green (the harvester itself is unchanged — only the report's transitions list narrows).
3. Red run: from the pre-fix worktree with this file copied in, run the test; capture the failing output in the slice's completion notes.

## Files to create/modify

- `assets/fbk-scripts/tests/test_report_rendering.py` (modify)

## Test requirements

- Integration (subprocess report over real transcript fixture) — VALIDATING tokens exactly `in=1500 out=300`; REVIEWING exactly `in=2000 out=400`; rendered totals account for every fixture turn (3500/700, derived by hand in comments).

## Acceptance criteria

- AC-09: per-stage token totals attribute turns during checkpoint/idle periods to the adjacent working stage; exact per-stage sums with every fixture turn accounted for.

## Model

Sonnet

## Wave

Wave 2
