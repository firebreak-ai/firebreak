---
id: task-13
type: test
wave: 2
covers: [AC-05]
files_to_modify:
  - assets/fbk-scripts/tests/test_capture_report_integration.py
completion_gate: "New gate-rate test and strengthened producer test collect cleanly at the current tree; the new test FAILS (first-try rate 1.00 != 0.50) from a second git worktree at the pre-fix commit (40ec021 at spec time) with the file copied in; failing output captured in the gate-rate-all-gates slice's completion notes."
---

## Objective

Author the guard that first-try and after-rework pass rates include spec/task-reviewer/code-review gate outcomes read from `PIPELINE_COMMAND`, pinned to exact fractions, and strengthen the existing producer-driven report test to exact values.

## Context

Slice: gate-rate-all-gates (contract-evolving). `report.classify_gate_attempts` (fbk/report.py:46-51) reads only `VERIFICATION_RESULT`, so the spec, task-reviewer, and code-review gates never reach the rates (F-06). The chokepoint is the single writer of gate-outcome events (after task-10/17's single-writer resolution): one `PIPELINE_COMMAND` per dispatch with `data["command_name"]` and `data["outcome"]`.

**Declared classifier contract (the implementation task copies this verbatim).** In `fbk/report.py`:

```python
# Gate dispatch command names whose PIPELINE_COMMAND outcomes count as gate attempts.
GATE_COMMAND_NAMES = ("spec-gate", "task-reviewer-gate", "code-review-gate")
```

`classify_gate_attempts` treats as an attempt, in timestamp order: every `VERIFICATION_RESULT` for the stage (as today), plus every `PIPELINE_COMMAND` for the stage whose `data["command_name"]` is in `GATE_COMMAND_NAMES`, with `passed = (data["outcome"] == "pass")`. `task-completed` dispatches are NOT counted (their outcome reaches the rates through their `VERIFICATION_RESULT`; counting both would double-count). The phase split (first-try vs after-rework) follows the first-park boundary (task-14's contract).

This task REUSES `capture_fixtures.drive_gate_fail_park_recover` and `capture_fixtures.run_fbk`, authored by task-04 (wave 1). Do NOT modify `tests/capture_fixtures.py` here (fixture-ownership rule).

Consistency note for the strengthened producer test: `test_real_producers_drive_nonzero_report_rows` already dispatches the real code-review gate, and its feature dir lacks the artifacts the gate requires, so today that dispatch FAILS (exit 2) — invisible to the pre-fix rates, but under `GATE_COMMAND_NAMES` it becomes a failing first-try attempt on IMPLEMENTING and would drag the rate to 1/2. The resolution is to make the dispatch deterministically PASS by completing the fixture (a fail-route re-pin to 0.50 would be fragile — the failure reason could drift). Gate pass conditions, verified against `validate_code_review` in `fbk/gates/code_review.py` and `verify_manifest` in `fbk/gates/test_hash.py`: `quality-scan.md` exists in the feature dir and contains the text `Severity:`; `test-review-final.md` exists (any content); an absent `test-hashes.json` manifest yields only a `missing`-kind discrepancy, which lands in the non-blocking `findings` list, never `failures` — so no hash manifest is needed.

Wave note: wave 2 because it consumes the wave-1 fixture and because `tests/test_capture_report_integration.py` must not collide with wave-1 bookings of sibling files.

## Instructions

1. Add `test_gate_outcomes_drive_exact_first_try_fraction(tmp_path)` to `tests/test_capture_report_integration.py`:
   - `project = capture_fixtures.make_project(str(tmp_path), instrumented=True, marked=True)`; `state_dir = os.path.join(project, ".claude", "automation", "state")`.
   - `events = capture_fixtures.drive_gate_fail_park_recover(project, state_dir, _SPEC ... )` — use spec name `"demo-spec"` consistently with the helper.
   - Sanity presence: exactly 2 `PIPELINE_COMMAND` events with `data["command_name"] == "spec-gate"` and exactly 1 passing `VERIFICATION_RESULT`, all `stage == "VALIDATING"`.
   - Run the real report (`_run_fbk(["report", "demo-spec"], project, state_dir)`), assert rc 0, and pin via the file's `_row_value` regex helper:
     - `VALIDATING ... first-try rate:` exactly `0.50` — hand derivation in a comment: first-try attempts = verification pass + spec-gate fail (both before the park) → 1/2; the spec-gate pass lands after the park → after-rework;
     - `after-rework rate:` exactly `1.00`;
     - `VALIDATING ... tasks reworked:` exactly `1` (one park-driven re-entry).
   - Docstring: red mechanics — the pre-fix classifier ignores `PIPELINE_COMMAND`, sees only the passing verification, and reports first-try 1.00, failing red against the 0.50 pin.
   Done when all three pinned-row assertions are present.
2. Strengthen `test_real_producers_drive_nonzero_report_rows`:
   - Make the code-review-gate dispatch deterministically pass: in the fixture's feature dir (`<project>/ai-docs/demo-spec/`, beside the existing `.code-review-rounds.json`), write `quality-scan.md` containing the line `Severity: minor` and `test-review-final.md` containing `# Test review — final pass\n` (exact artifact names; the gate's third check tolerates the absent `test-hashes.json` as a non-blocking finding). Change the `_run_fbk(["code-review-gate", ...])` call to capture its result and assert rc `== 0`, locking the pass deterministically.
   - Add a sanity assertion that the events stream now carries exactly 1 `PIPELINE_COMMAND` with `data["command_name"] == "code-review-gate"` and `data["outcome"] == "pass"`, `stage == "IMPLEMENTING"`.
   - Change the tasks-completed assertion from `>= 1` to exactly `== 1` (one real task-completion was driven), updating its message.
   - Keep the first-try-rate assertion at exactly `1.0`, updating its comment with the hand derivation: two first-try attempts on IMPLEMENTING — the passing verification plus the passing code-review-gate dispatch — 2/2 = 1.0.
   - Keep the kill-rate assertion at exactly `0.60` (5 raised / 2 survived; unaffected by the gate outcome).
   Done when the dispatch rc is asserted 0, both artifacts are written, and no `>=` remains on the tasks-completed row.
3. Verification step (no modification): run `tests/test_report_arithmetic.py::test_first_try_pass_rate_is_exact_fraction`, `::test_kill_rate_is_exact_value`, and `::test_stale_fallback_warning_fires_with_zero_subagent_events`; confirm green after the gate-rate extension.
4. Red run: from the pre-fix worktree with this file copied in (and the wave-1 `capture_fixtures.py` alongside it, since the helper is new), run the new test; capture the failing output in the slice's completion notes.

## Files to create/modify

- `assets/fbk-scripts/tests/test_capture_report_integration.py` (modify)

## Test requirements

- Integration (real producers via fbk.py subprocesses → real report) — first-try rate exactly `0.50`, after-rework rate exactly `1.00`, tasks reworked exactly `1` for VALIDATING; presence sanity on the driving events.
- Integration (existing test strengthened) — code-review-gate dispatch passes (rc 0, with `quality-scan.md` carrying `Severity:` and `test-review-final.md` present); exactly 1 code-review-gate `PIPELINE_COMMAND` with outcome `pass` on IMPLEMENTING; tasks completed exactly `1`; first-try rate exactly `1.0` (2/2: passing verification + passing code-review-gate dispatch); kill rate exactly `0.60`.

## Acceptance criteria

- AC-05: first-try and after-rework pass rates include spec, task-reviewer, and code-review gate outcomes read from `PIPELINE_COMMAND`; the guard pins an exact fraction (a fail-then-pass gate beside one first-try pass yields exactly 1/2).

## Model

Sonnet

## Wave

Wave 2
