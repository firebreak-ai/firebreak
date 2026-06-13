---
id: task-21
type: test
wave: 6
covers: [AC-15, AC-20, AC-01]
files_to_create:
  - assets/fbk-scripts/tests/test_capture_e2e_seam.py
completion_gate: "tests compile and fail before implementation"
---

# Objective

Write the two end-to-end seam tests: a fixture cycle producing BOTH router events and chokepoint events yields one report table whose rows draw on both sources with consistent envelope fields joinable on `(spec, stage)`; and a session run in a project that is neither Firebreak-managed nor marked produces no entries in any capture file and no router output.

# Context

This is the cross-cutting seam slice — it has NO paired implementation task; the behaviors it exercises are built by the other slices (event writer, router, chokepoint, report, gate). These tests confirm the pieces join correctly end to end:

- **Two-source join.** A single cycle records events from two producers — the standalone hook router (Claude-level events like `TOOL_USE`) and the dispatch chokepoint (`PIPELINE_COMMAND` events). Both write the same envelope shape to one `.fbk-capture/events.jsonl`, and the report aggregates both into one table, joining on `(spec, stage)` with consistent envelope fields. This backs the operator's UV-3 inspection (events from both sources, same fields) and UV-1's report.
- **Uninstrumented privacy.** In a project that is neither Firebreak-managed (no marker sentinel) nor marked (no `capture.cfg`), the router and chokepoint record nothing and the router emits no output — the governing privacy constraint, end to end. This backs UV-4.

Drive real producers: feed the router a payload via subprocess (as in the router task) and run a real dispatched command through `fbk.py` (as in the chokepoint-real task), both in the same instrumented `tmp_path` project, then run `fbk.py report <spec>`. Build the project with `capture_fixtures.make_project` and payloads with `hook_payload`. Guard the file to skip if the capture subsystem is absent (`from fbk.capture import event_writer` inside `try/except ImportError`, skipif). Define `FBK_PY` and `ROUTER` paths as in the upstream tasks.

# Instructions

1. Create `tests/test_capture_e2e_seam.py`; guard with `try/except ImportError` + module-level skipif on the capture subsystem; define `FBK_PY = Path(__file__).parent.parent / "fbk.py"` and `ROUTER = Path(__file__).parent.parent / "fbk" / "capture" / "hook_router.py"`.
2. `test_two_source_cycle_joins_in_one_report`: in one instrumented project (marked Firebreak, `STATE_DIR` set under it):
   a. `fbk.py state create demo-spec`, then a transition INTO a working stage (`fbk.py state transition demo-spec VALIDATING`), then a transition through that working stage's COMPLETION (`fbk.py state transition demo-spec VALIDATED`). Each transition is a dispatched command, so each produces a `PIPELINE_COMMAND` chokepoint event; the working-stage completion (`VALIDATING` → `VALIDATED`) also fires the retrospective injector.
   b. Feed the router a `PostToolUse` payload via subprocess (cwd=project) — produces a `TOOL_USE` router event.
   c. Assert `<project>/.fbk-capture/events.jsonl` now contains BOTH a `PIPELINE_COMMAND` event and a `TOOL_USE` event, and that they carry the SAME envelope field set (the eight envelope keys) — consistent shape across the two producers.
   d. Run `fbk.py report demo-spec` (cwd=project, STATE_DIR set); assert it exits 0 and the table draws on both sources — at minimum assert the table renders a row reflecting the dispatched command and a row/section reflecting the tool-use capture, joined under the spec. Assert the report did not error on the mixed stream and the `(spec, stage)` join is reflected (both producers' events appear under the same spec in the output).
   e. Assert the SECOND half of AC-20 — the machine-marked retrospective block: open `<project>/ai-docs/demo-spec/demo-spec-retrospective.md` and assert it contains a `## VALIDATING — metrics` heading opened by a provenance marker matched by STRUCTURE (the fixed `<!-- fbk-metrics stage=VALIDATING spec=demo-spec generated=` prefix, with the `generated=` timestamp as a free field — not exact-string equality). This makes the e2e verify both halves of AC-20 in one cycle: the joined report AND the deterministic retrospective injection.
3. `test_uninstrumented_project_records_nothing_end_to_end`: in a BARE `tmp_path` project (no marker sentinel, no `capture.cfg`):
   a. Feed the router a payload via subprocess (cwd=project); assert the router exits 0, writes NO `.fbk-capture/events.jsonl`, and emits NO stdout.
   b. Run a real dispatched command (`fbk.py state create demo-spec` then a transition, cwd=project, STATE_DIR set); assert the command behaves normally (exit code unchanged) and STILL no `.fbk-capture/events.jsonl` is created — the chokepoint records nothing in an uninstrumented project.
   c. Assert no capture file exists anywhere under the project after both producers ran.
4. For the join assertion in step 2d, match on structure (the spec name appearing in the report alongside both a command-derived and a tool-use-derived datum), not body vocabulary. The provenance/envelope consistency is matched by the shared eight-field key set, not exact values.

# Files to create/modify

- `tests/test_capture_e2e_seam.py`

# Test requirements

- `test_two_source_cycle_joins_in_one_report` (e2e): router + chokepoint events in one stream with a consistent eight-field envelope; report aggregates both, joined on `(spec, stage)`, exits 0; and the completed working stage's retrospective carries a structurally-matched provenance metrics block (both halves of AC-20).
- `test_uninstrumented_project_records_nothing_end_to_end` (e2e): bare project → router writes nothing and emits no stdout; chokepoint records nothing; commands behave normally; no capture file anywhere.

# Acceptance criteria

AC-15 (both sources in one joinable stream), AC-20 (single cycle → report draws on both sources + state, consistent envelope), AC-01 (uninstrumented project records nothing end to end). Gate: tests compile and fail before implementation. This slice is test-only — no paired implementation task.

# Model

Sonnet — multi-producer end-to-end orchestration through subprocess with join assertions.

# Wave

6
