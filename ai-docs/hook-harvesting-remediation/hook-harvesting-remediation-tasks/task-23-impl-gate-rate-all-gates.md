---
id: task-23
type: implementation
wave: 5
covers: [AC-05]
files_to_modify:
  - assets/fbk-scripts/fbk/report.py
test_tasks: [task-13]
dependencies: [task-13, task-19, task-29]
completion_gate: "task-13's new test passes (tests/test_capture_report_integration.py::test_gate_outcomes_drive_exact_first_try_fraction — first-try 0.50, after-rework 1.00, reworked 1) and its strengthened ::test_real_producers_drive_nonzero_report_rows passes (first-try exactly 1.0: passing verification + passing code-review-gate dispatch); tests/test_report_arithmetic.py::test_first_try_pass_rate_is_exact_fraction, ::test_kill_rate_is_exact_value, ::test_stale_fallback_warning_fires_with_zero_subagent_events stay green"
---

## Objective

Extend the gate-rate classifier so first-try and after-rework pass rates include spec, task-reviewer, and code-review gate outcomes read from the chokepoint's `PIPELINE_COMMAND` events — not only task-completion verification.

## Context

Slice: gate-rate-all-gates. `report.classify_gate_attempts` (fbk/report.py:31-89) collects only `VERIFICATION_RESULT` events (the filter at lines 47-51), so the spec, task-reviewer, and code-review gates never reach the rates. After the single-writer fix (task-29, wave 4) the chokepoint is the only producer of gate-outcome events: one `PIPELINE_COMMAND` per dispatch carrying `data["command_name"]`, `data["outcome"]` (`"pass"`/`"fail"`), and the resolver-stamped spec/stage (corrected by task-19, wave 2). Those two prerequisites are why this task sits in wave 5 — the spec pins that no implementation stop boundary may fall between the three slices.

**Classifier contract (copied verbatim from task-13 — do not paraphrase).** In `fbk/report.py`:

```python
# Gate dispatch command names whose PIPELINE_COMMAND outcomes count as gate attempts.
GATE_COMMAND_NAMES = ("spec-gate", "task-reviewer-gate", "code-review-gate")
```

`classify_gate_attempts` treats as an attempt, in timestamp order: every `VERIFICATION_RESULT` for the stage (as today), plus every `PIPELINE_COMMAND` for the stage whose `data["command_name"]` is in `GATE_COMMAND_NAMES`, with `passed = (data["outcome"] == "pass")`. `task-completed` dispatches are NOT counted (their outcome reaches the rates through their `VERIFICATION_RESULT`; counting both would double-count). The phase split (first-try vs after-rework) follows the first-park boundary (task-14's contract).

The three command names are verified against `COMMAND_MAP` in `fbk/__init__.py` — they are the exact dispatcher keys the chokepoint stamps into `data["command_name"]`.

Phase-split note: at this wave the boundary logic (lines 54-86) is still the pre-fix READY-based code; task-24 (wave 6) replaces it. Do not touch the boundary logic here — change only the attempt collection and the per-event pass/fail read. Task-13's fixture passes under either boundary implementation (its single park precedes the re-entry which precedes the post-park attempt).

Invariants to preserve: the report runs at any pipeline point with partial rows; `_event_passed` keeps accepting the three verification payload shapes; the `tasks completed` row (lines 466-471) keeps counting `task-completed` dispatches and is untouched.

Strengthened-test note (fixture resolved upstream in the amended task-13): `tests/test_capture_report_integration.py::test_real_producers_drive_nonzero_report_rows` now writes the two artifacts the code-review gate requires (`quality-scan.md` with a `Severity:` field, `test-review-final.md`), so its real code-review-gate dispatch passes (rc 0, `data["outcome"] == "pass"`, stage IMPLEMENTING) and is asserted as exactly one `PIPELINE_COMMAND` with `command_name == "code-review-gate"`. Under this task's classifier extension the IMPLEMENTING first-try attempts are the passing verification plus that passing gate dispatch → exactly 2/2 = 1.0, matching the test's kept pin; kill rate 0.60 and tasks-completed 1 are unaffected. The test is therefore a gating green at this task's completion: a sub-1.0 reading there means the classifier is miscounting (double-counting `task-completed`, or misreading `outcome`), not a fixture problem.

Constraints: do NOT modify any test file; file scope is exactly `fbk/report.py`. Path relative to `/home/rahvin/context-assets/assets/fbk-scripts/`.

## Instructions

1. Add the `GATE_COMMAND_NAMES` constant (verbatim block above, including its comment line) in `fbk/report.py` immediately after the imports, above the "Pure computation helpers" divider (before line 31). Done when the constant is module-level (task-13's docstrings reference it by name).
2. In `classify_gate_attempts`, replace the collection filter (lines 47-52) with:
   ```python
   gate_events = [
       e for e in events
       if e.get("stage") == stage
       and (
           e.get("event_type") == "VERIFICATION_RESULT"
           or (
               e.get("event_type") == "PIPELINE_COMMAND"
               and e.get("data", {}).get("command_name") in GATE_COMMAND_NAMES
           )
       )
   ]
   gate_events.sort(key=lambda e: e.get("timestamp", ""))
   ```
   Done when both event types are collected in one timestamp-ordered list.
3. In the per-event loop (lines 66-87), make the pass/fail read type-dependent — replace the single `passed = _event_passed(data)` (line 71) with:
   ```python
   if ev.get("event_type") == "PIPELINE_COMMAND":
       passed = data.get("outcome") == "pass"
   else:
       passed = _event_passed(data)
   ```
   Done when a `PIPELINE_COMMAND` gate event never routes through `_event_passed`.
4. Update the `classify_gate_attempts` docstring (lines 32-45): attempts are `VERIFICATION_RESULT` events plus `PIPELINE_COMMAND` events whose `command_name` is a known gate (`GATE_COMMAND_NAMES`); `task-completed` dispatches are excluded to avoid double-counting their verification. Done when the docstring states the exclusion rationale.
5. Run the gating tests. Expected arithmetic (task-13 fixture): verification pass + spec-gate fail before the park → first-try exactly 1/2; spec-gate pass after the park → after-rework exactly 1.00; one park → reworked 1.

## Files to create/modify

- `assets/fbk-scripts/fbk/report.py` (modify)

## Test requirements

- Gating: task-13's `tests/test_capture_report_integration.py::test_gate_outcomes_drive_exact_first_try_fraction` and the strengthened `::test_real_producers_drive_nonzero_report_rows` (first-try exactly 1.0 from passing verification + passing code-review-gate dispatch; exactly one `code-review-gate` `PIPELINE_COMMAND`; kill rate 0.60; tasks completed 1).
- Must stay green: `tests/test_report_arithmetic.py::test_first_try_pass_rate_is_exact_fraction`, `::test_kill_rate_is_exact_value`, `::test_stale_fallback_warning_fires_with_zero_subagent_events` (named by the spec); `tests/test_report_rendering.py` (its fixtures carry no gate-named `PIPELINE_COMMAND` events for rendered stages).

## Acceptance criteria

- AC-05: first-try and after-rework pass rates include spec, task-reviewer, and code-review gate outcomes read from `PIPELINE_COMMAND`; a fail-then-pass gate beside one first-try pass yields exactly 1/2.

## Model

Sonnet

## Wave

Wave 5
