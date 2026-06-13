---
id: task-04
type: test
wave: 1
covers: [AC-04, AC-15]
files_to_create:
  - assets/fbk-scripts/tests/test_capture_injection_seam.py
files_to_modify:
  - assets/fbk-scripts/tests/capture_fixtures.py
completion_gate: "Seam-guard test collects cleanly at the current tree and FAILS from a second git worktree (first failure pre-fix: the sanity event count reads 4 instead of 2 because each gate dispatch writes a duplicate envelope; once the single-writer fix lands the remaining failure is the stub block carrying no metric lines — this is a cross-slice seam guard) at the pre-fix commit (40ec021 at spec time) with both files copied in; failing output captured in the seam-guards completion notes."
---

## Objective

Author the end-to-end injection-seam guard (real producers through the writer into the injector) and the shared real-producer-to-report fixture it and the gate-rate task reuse.

## Context

Slice: seam-guards (cross-cutting; no paired implementation in this slice). The injection seam broke silently while the suite stayed green: the state engine calls `retro_injector.inject_stage_metrics`, which calls `report.stage_summary` — a stub. This guard drives the real producer chain end-to-end so a future regression turns the suite red.

This task OWNS the spec's "real-producer-to-report integration fixture" (Test infrastructure changes). It lives in `tests/capture_fixtures.py` (the established shared-builder module) and is REUSED by task-13 (gate-rate); task-13 must not touch `capture_fixtures.py`.

Two-files note: the fixture and the first test that exercises it land together per the breakdown's fixture-ownership rule (one owning task per fixture).

New-file rationale: this is a new e2e guard; the breakdown staggers it away from `tests/test_capture_e2e_seam.py` (strengthened in task-03, same wave) to satisfy the wave-collision rule.

Producer facts (verified against the codebase): `fbk.py` dispatches every command through `chokepoint.record_dispatch`, which writes one `PIPELINE_COMMAND` event with `data["command_name"]`, `data["outcome"]` (`"pass"`/`"fail"` from exit code), and the resolver-stamped spec/stage. The task-completed hook (`fbk.py task-completed`) writes a `VERIFICATION_RESULT` with `data["tests_passed"]`; with no detectable test runner or linter in the project it passes cleanly. The state engine (`fbk.py state transition`) records parks in `error_history` and fires the injector on working-stage completion.

## Instructions

1. In `tests/capture_fixtures.py`, add a "Real-producer drivers" section at the end of the file with:
   - Module constants:
     - `FBK_PY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fbk.py")`
     - `MINIMAL_VALID_SPEC_MD` — a spec markdown string that passes the spec gate: copy the exact text produced by `_make_minimal_spec()` in `tests/test_gates_spec.py` (the `# Feature Specification` header plus `_MINIMAL_VALID_SECTIONS`), with a comment crediting that file as the source of truth for a gate-passing spec.
     - `BROKEN_SPEC_MD = "# Feature Specification\n\n## Problem\nOnly one section present.\n"`
   - Helper `def run_fbk(args, project_root, state_dir, stdin_text=None):` — subprocess wrapper identical in shape to `_run_fbk` in `tests/test_capture_report_integration.py` (`[sys.executable, FBK_PY] + args`, `cwd=project_root`, env `STATE_DIR=state_dir`, `capture_output=True, text=True, timeout=30`).
   - Builder `def drive_gate_fail_park_recover(project_root, state_dir, spec):` performing, in order, asserting the stated return code after each step:
     1. `run_fbk(["state", "create", spec], ...)` — rc 0.
     2. `run_fbk(["state", "transition", spec, "VALIDATING"], ...)` — rc 0.
     3. Write `<project_root>/ai-docs/<spec>/tasks/task-01.md` containing `"# Task 01\n\nDo the thing.\n"` (no declared-files section), then `run_fbk(["task-completed"], ..., stdin_text=json.dumps({"task_description": f"Implement ai-docs/{spec}/tasks/task-01.md", "cwd": project_root}))` — rc 0 (no test runner/linter present → passing verification).
     4. Write `<project_root>/broken-spec.md` = `BROKEN_SPEC_MD`; `run_fbk(["spec-gate", "broken-spec.md"], ...)` — rc 2 (chokepoint records spec-gate fail).
     5. `run_fbk(["state", "transition", spec, "PARKED", "--reason", "spec gate failed"], ...)` — rc 0 (first park recorded in error_history).
     6. `run_fbk(["state", "transition", spec, "READY"], ...)` — rc 0; then `run_fbk(["state", "transition", spec, "VALIDATING"], ...)` — rc 0 (re-entry).
     7. Write `<project_root>/sample-spec.md` = `MINIMAL_VALID_SPEC_MD`; `run_fbk(["spec-gate", "sample-spec.md"], ...)` — rc 0 (chokepoint records spec-gate pass, after the park).
     Return the parsed event dicts from `<project_root>/.fbk-capture/events.jsonl`.
   Done when the builder runs green standalone against the current tree (the producers all exist today).
2. Create `tests/test_capture_injection_seam.py` with the capture-availability skip guard pattern from `tests/test_capture_e2e_seam.py`, containing one test `test_real_producer_cycle_injects_exact_metrics(tmp_path)`:
   - `project = capture_fixtures.make_project(str(tmp_path), instrumented=True, marked=True)`; `state_dir = os.path.join(project, ".claude", "automation", "state")`.
   - `events = capture_fixtures.drive_gate_fail_park_recover(project, state_dir, "demo-spec")`.
   - Sanity presence assertions: exactly 2 `PIPELINE_COMMAND` events with `data["command_name"] == "spec-gate"` (one `outcome == "fail"`, one `outcome == "pass"`), and exactly 1 `VERIFICATION_RESULT` with `data["tests_passed"] is True`, all with `stage == "VALIDATING"`.
   - Complete the stage through the production path: `capture_fixtures.run_fbk(["state", "transition", "demo-spec", "VALIDATED"], project, state_dir)` — rc 0; this fires the injector from the real state engine.
   - Read `<project>/ai-docs/demo-spec/demo-spec-retrospective.md`; assert the `## VALIDATING — metrics` heading, the marker prefix `<!-- fbk-metrics stage=VALIDATING spec=demo-spec generated=`, and these exact lines: `first-try rate: 0.50`, `after-rework rate: 1.00`, `parks: 1`, `rework: 1`.
   - Hand derivation, stated in a comment: first-try attempts = verification pass + spec-gate fail (both before the park) → exactly 1/2; after-rework = spec-gate pass (after the park) → exactly 1.0; one park; one re-entry.
   - Note in the docstring: this guard goes green only once the injection-render, gate-rate, and rework-boundary fixes have all landed — it is the cross-slice seam guard, red at the pre-fix commit by construction.
   Done when the test is present with all listed assertions.
3. Red run: from the pre-fix worktree with both files copied in, run the test; capture the failing output in the seam-guards completion notes.

## Files to create/modify

- `assets/fbk-scripts/tests/test_capture_injection_seam.py` (create)
- `assets/fbk-scripts/tests/capture_fixtures.py` (modify — fixture owner; reused read-only by task-13)

## Test requirements

- E2E (subprocess fbk.py producers → writer → state engine → injector → retrospective file) — injected block contains exact lines `first-try rate: 0.50`, `after-rework rate: 1.00`, `parks: 1`, `rework: 1` under the `## VALIDATING — metrics` heading; producer events pinned (2 spec-gate dispatches with exact outcomes, 1 passing verification, all stage `VALIDATING`).

## Acceptance criteria

- AC-15: an end-to-end test drives a real producer through the writer into the injector and asserts the injected block's metric content.
- AC-04: the injected block contains the stage's real gate-rate, parks, and rework values.

## Model

Sonnet

## Wave

Wave 1
