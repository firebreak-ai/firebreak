---
id: task-11
type: test
wave: 3
covers: [AC-07, AC-08, AC-06, AC-17, AC-25]
files_to_create:
  - assets/fbk-scripts/tests/test_report_rendering.py
completion_gate: "tests compile and fail before implementation"
---

# Objective

Write the integration tests that run `fbk.py report <spec>` over fixture event + state + transcript inputs and assert the rendered table: full-row coverage of every required row kind, mid-cycle partial rows, the literal `unavailable` token vs an empty-but-present parks row, the empty-vs-absent row discriminator, and the retention over-cap warning surfaced in the table.

# Context

`python3 fbk.py report <spec>` prints one metrics table aggregating the events stream, the state engine, and the harvester output, runnable at any pipeline point with no special mode (partial rows mid-cycle). The table carries at minimum: per-stage duration; per-gate first-try and after-rework rates; parks per stage with reason; tasks completed and reworked; scope violations; detection rounds with raised-to-confirmed counts and kill rate; tokens per stage. Two literal-rendering rules are load-bearing: a missing transcript renders the literal token `unavailable` (not `0`) in that token cell; a row for which no event of a kind occurred is present and empty (e.g. a stage that ran its parks-producing path with zero parks) and is distinct from a row omitted because its producing step never ran. The retention over-cap warning surfaces in the table the same way the stale-fallback warning does.

This task drives the CLI via subprocess, matching the suite's gate-CLI pattern (`FBK_PY = Path(__file__).parent.parent / "fbk.py"`, `subprocess.run([sys.executable, str(FBK_PY), "report", spec], ...)`, asserting on `returncode` and stdout). Input locations are pinned: the report reads `.fbk-capture/events.jsonl` relative to `os.getcwd()`, and the state via `fbk.state.get_state_dir()` = `os.environ.get("STATE_DIR", ".claude/automation/state")` with `get_state_path(spec) = <state_dir>/<spec>.json`. So the subprocess sets `cwd=<project>` (the events-file authority) and `env={**os.environ, "STATE_DIR": <state dir>}`. Build inputs with `capture_fixtures`. Assert on structural table markers (row labels / headings), not body vocabulary.

# Instructions

1. Create `tests/test_report_rendering.py`. Define `FBK_PY = Path(__file__).parent.parent / "fbk.py"`. Add a fixture that lays down, under a `tmp_path` project: `.fbk-capture/events.jsonl` (events across stages), the state file at `<state dir>/<spec>.json`, and transcripts; run the report via `subprocess.run([sys.executable, str(FBK_PY), "report", "<spec>"], cwd=<project>, env={**os.environ, "STATE_DIR": <state dir>}, capture_output=True, text=True)`.
2. `test_report_renders_all_required_row_kinds`: over a full fixture cycle (events for gate attempts, parks, tasks, scope violations, code-review rounds; a state with durations; a transcript with tokens), assert the table contains a structural row label for each required kind: per-stage duration, first-try rate, after-rework rate, parks, tasks completed, tasks reworked, scope violations, detection rounds, kill rate, tokens per stage. Assert each label substring is present (one assertion per row kind). Pair with `returncode == 0`.
3. `test_report_runs_mid_cycle_with_partial_rows`: build a fixture where only the early stages have run (state stops mid-pipeline); assert the report exits 0, prints rows for the stages that ran, and does not error on the absent later stages.
4. `test_missing_transcript_renders_literal_unavailable`: fixture where one stage's transcript is missing; assert the token cell for that stage renders the literal token `unavailable` and NOT `0`. Assert the substring `unavailable` is present in that stage's token row and that the row is not rendered as `0`.
5. `test_zero_parks_renders_present_empty_row`: fixture where a stage ran its parks-producing path with zero parks; assert the parks row for that stage is present (the stage's row label appears) and empty (no park entries), distinct from an error.
6. `test_empty_vs_absent_row_discriminator`: fixture distinguishing a stage that ran its parks path with zero parks (row present and empty) from a stage whose parks-producing step never executed (row absent); assert present-and-empty in the first case and the row omitted in the second — so a renderer that simply drops all-zero rows does not pass.
7. `test_over_cap_retention_warning_surfaced`: place the over-cap sentinel `.fbk-capture/.retention-warning` under the project (the durable signal the pruner writes when it drops locked lines past the protected-bytes ceiling); run the report; assert the table renders the over-cap warning text so an operator sees why locked lines were dropped. In a sibling case with no sentinel, assert the warning is absent.

# Files to create/modify

- `tests/test_report_rendering.py`

# Test requirements

- `test_report_renders_all_required_row_kinds` (integration): table carries every required row label; exits 0.
- `test_report_runs_mid_cycle_with_partial_rows` (integration): partial rows mid-cycle, no error.
- `test_missing_transcript_renders_literal_unavailable` (integration): missing transcript → literal `unavailable`, not `0`.
- `test_zero_parks_renders_present_empty_row` (integration): zero-park stage → present-and-empty parks row.
- `test_empty_vs_absent_row_discriminator` (integration): present-and-empty vs omitted-row discriminator.
- `test_over_cap_retention_warning_surfaced` (integration): over-cap retention warning rendered in the table.

# Acceptance criteria

AC-07 (full table), AC-08 (ad-hoc mid-cycle invocation), AC-06/AC-17 (unavailable-vs-zero and present-empty rendering), AC-25 (over-cap warning surfaced). Gate: tests compile and fail before implementation.

# Model

Sonnet — subprocess CLI integration with structural table assertions and discriminator cases.

# Wave

3
