---
id: task-28
type: implementation
wave: 3
covers: [AC-07, AC-08, AC-17, AC-16, AC-06, AC-25, AC-15, AC-20]
files_to_create:
  - assets/fbk-scripts/fbk/report.py
files_to_modify:
  - assets/fbk-scripts/fbk/__init__.py
test_tasks: [task-10, task-11]
completion_gate: "task-10, task-11 tests pass"
dependencies: [task-22, task-25, task-26]
---

# 1 Objective

Produce the `report` command — `python3 fbk.py report <spec>` — that aggregates the events stream, the state engine, and the token harvester into one metrics table runnable at any pipeline point (partial rows mid-cycle), plus the importable pure helpers the unit tests call (gate-attempt classification, first-try pass rate, kill rate, parks derivation, rework derivation) and the reusable `stage_summary`. Register `report` in `COMMAND_MAP`.

# 2 Context

The report joins three deterministic streams on `(spec, stage)`: events from `.fbk-capture/events.jsonl` (relative to `os.getcwd()`), state from `fbk.state.get_state_path(spec)` (which resolves `STATE_DIR` env or `.claude/automation/state` under cwd), and per-stage tokens from the harvester (task-26). It ports aggregation shape from the prototype `ai-docs/hook-harvesting/fbk_report_prototype.py` (stage durations from `stage_timestamps`, event joins), but the rate/classification math below is the authoritative contract. The report lives flat at `fbk/report.py`, matching the existing flat single-command convention (`pipeline.py`, `state.py`, `retro.py`), and is registered `report` in `COMMAND_MAP`.

Defined formulas (computed as EXACT values, not labels):
- First-try pass rate = first-try attempts that passed / first-try attempts made. "First-try" = every gate attempt BEFORE the stage's first park; "after-rework" = every attempt from the first READY re-entry onward.
- Kill rate = (total_raised − total_confirmed) / total_raised. Presented as a relative trend signal with an acknowledged-true-positive caveat label.

Load-bearing rendering rules:
- A row for which no event of a kind occurred is PRESENT and reflects the true count (an empty parks row; a park with an empty reason renders "(no reason recorded)") — distinct from a row OMITTED because its producing step never ran.
- A missing transcript renders the literal token `unavailable` in the token cell, never `0`.
- Subagent-completion events count only when the agent identity is a known Firebreak agent (use `known_agents.is_known_agent`); a stale-fallback condition (`known_agents.STALE_FALLBACK`) surfaces as a report warning.
- An over-cap retention condition (the `.fbk-capture/.retention-warning` sentinel) surfaces as a report warning the same way the stale-fallback warning does.

# 3 Instructions

1. Create `fbk/report.py`. Import `from fbk.capture import known_agents, token_harvester` and read state via `import fbk.state as state` (use `state.get_state_path(spec)`). Read events from `os.path.join(os.getcwd(), ".fbk-capture", "events.jsonl")`.
2. Implement `classify_gate_attempts(events, state, stage) -> list[dict]`. Identify the stage's gate-attempt events (PIPELINE_COMMAND / VERIFICATION_RESULT events stamped with this stage that represent an attempt with a pass/fail outcome). Find the stage's first park (from `state["error_history"]` — the first entry whose `stage` equals this stage) and the first READY re-entry (a repeated stage start after a park). Each returned entry is `{"phase": "first_try" | "after_rework", "passed": bool}`: attempts before the first park are `first_try`; attempts from the first ready re-entry onward are `after_rework`. Completion: pre-park attempts classify `first_try`; post-re-entry attempts classify `after_rework`.
3. Implement `first_try_pass_rate(attempts) -> float` = count of first-try attempts that passed / count of first-try attempts made. Guard divide-by-zero (return 0.0 or a sentinel when no first-try attempts). Completion: fail/fail/pass → exactly `1/3`.
4. Implement `kill_rate(rounds) -> float` = (total_raised − total_confirmed) / total_raised, where per-round `confirmed = survived` (the rounds carry `raised`/`survived`); sum across rounds. Guard divide-by-zero. Completion: raised=10, confirmed=3 → exactly `0.7`.
5. Implement `derive_parks(state, stage) -> list[dict]`. From `state["error_history"]`, return one entry per park for this stage as `{"reason": <error string or None>}`; an empty reason stays as a present entry (rendered "(no reason recorded)"), never dropped. Completion: an empty-reason park yields a present entry with empty/None reason.
6. Implement `derive_rework(state, stage) -> int` = the re-entry count for this stage derived from repeated stage entries (a stage appearing more than once in the timestamps history / `error_history` indicates re-entry). Return `>= 1` when the stage was re-entered. Completion: a re-entered stage → `>= 1`, and `classify_gate_attempts` then yields at least one `after_rework`.
7. Implement `stage_summary(spec: str, stage: str) -> str` — a markdown metrics block body for one stage, opening with the provenance marker line and EXCLUDING tokens from the block (tokens belong to the full table; the per-stage injected block is the marker plus the stage's gate/park/rework metrics). The exact provenance marker first line is `<!-- fbk-metrics stage=<STAGE> spec=<SPEC> generated=<ISO-8601> -->` (no trailing space). Completion: `stage_summary("demo-spec", "IMPLEMENTING")` returns a string whose first line is that marker for the stage/spec.
8. Implement the CLI `main()`: read the spec from argv, load events + state + harvested tokens, and print ONE table with at least these row kinds (each as a labeled row/section): per-stage duration; per-gate first-try and after-rework rates; parks per stage with reason; tasks completed and reworked; scope violations; detection rounds with raised-to-confirmed counts and kill rate (with the true-positive caveat label); tokens per stage (literal `unavailable` when the harvester marks the stage unavailable). Render present-but-empty rows for kinds that ran with zero events; omit rows for kinds whose producing step never ran (the empty-vs-absent discriminator). Surface the stale-fallback warning (when `known_agents.STALE_FALLBACK`) and the over-cap retention warning (when `.fbk-capture/.retention-warning` exists). Run at any pipeline point with partial rows mid-cycle and exit 0. Completion: `fbk.py report <spec>` over a full fixture prints every required row label and exits 0; mid-cycle prints partial rows without error.
9. Subagent counting: aggregate SUBAGENT_STOP events only when `is_known_agent(<identity>)` — exclude empty/unknown identities from the count while the events remain in the stream. Completion: the subagent count includes only known-identity events.
10. Register the command: in `fbk/__init__.py`, add `"report": "fbk.report"` to `COMMAND_MAP` (making 19 entries). Completion: `COMMAND_MAP["report"] == "fbk.report"` and the map has 19 entries.

# 4 Files to create/modify

- Create `fbk/report.py`
- Modify `fbk/__init__.py` (add `"report": "fbk.report"` to `COMMAND_MAP`)

# 5 Test requirements

Makes task-10 (`tests/test_report_arithmetic.py` — the pure helpers: classification, exact first-try rate `1/3`, exact kill rate `0.7`, empty-reason park row, rework from repeated entry, subagent filtering) and task-11 (`tests/test_report_rendering.py` — CLI table: all required row labels, mid-cycle partial rows, literal `unavailable`, present-empty vs absent row discriminator, over-cap warning surfaced) pass. The `COMMAND_MAP` count change to 19 is asserted in task-18's dispatcher update (do not modify that test).

# 6 Acceptance criteria

Primary: task-10 and task-11 tests pass. Covers AC-07 (defined rate formulas computed exactly + full table), AC-08 (ad-hoc mid-cycle invocation), AC-17 (state-derived parks/rework + empty-vs-absent rows), AC-16 (report-time subagent filtering + stale-fallback warning), AC-06 (literal `unavailable` token cell), AC-25 (over-cap retention warning surfaced), AC-15 (joins both producers' events), AC-20 (end-to-end report rows across both sources + state).

# 7 Model

Sonnet

# 8 Wave

3
