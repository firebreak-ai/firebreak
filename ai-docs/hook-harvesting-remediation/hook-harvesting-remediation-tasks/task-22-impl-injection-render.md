---
id: task-22
type: implementation
wave: 7
covers: [AC-04]
files_to_modify:
  - assets/fbk-scripts/fbk/report.py
test_tasks: [task-03, task-04]
dependencies: [task-03, task-04, task-23, task-24]
completion_gate: "task-03 tests pass (tests/test_capture_retro_injector.py and the strengthened tests/test_capture_e2e_seam.py test); task-04's seam guard (tests/test_capture_injection_seam.py) passes — its prerequisites (stage-attribution task-19, gate-rate task-23, rework-boundary task-24, single-writer task-29) have all landed in earlier waves"
---

## Objective

Replace the `stage_summary` stub with a real render: load the events file and the state, compute the stage's gate rates, parks, and rework, and return them in the pinned line formats the injector writes into every retrospective.

## Context

Slice: injection-render. `report.stage_summary` (fbk/report.py:209-227) is a stub: it returns only the provenance marker plus `stage:`/`spec:` label lines, so the `## <STAGE> — metrics` block injected into every retrospective is an empty shell. Its only caller is `fbk/capture/retro_injector.py:46` (`inject_stage_metrics`, fired by the state engine on working-stage completion); the report command never calls it. The injector swallows all exceptions, so a load failure inside `stage_summary` can never block a state transition — but prefer returning a well-formed block over raising.

**Block contract (copied verbatim from task-03 — do not paraphrase).** `stage_summary(spec, stage)` returns these lines in order, after the existing marker / `stage:` / `spec:` lines:

```
first-try rate: <f"{rate:.2f}">
after-rework rate: <f"{rate:.2f}">
parks: <int>
rework: <int>
```

where first-try / after-rework rates come from `classify_gate_attempts` + `first_try_pass_rate` over the stage's events (loaded the same way the report command loads them: events from `<cwd>/.fbk-capture/events.jsonl`, state via `fbk.report._load_state(spec)`), `parks` is `len(derive_parks(st, stage))`, and `rework` is `derive_rework(st, stage)`.

By wave 7 the classifier already includes `PIPELINE_COMMAND` gate outcomes (task-23, wave 5) and uses the first-park boundary (task-24, wave 6) — `stage_summary` picks both up by calling `classify_gate_attempts`, which is why this task is sequenced after them.

Invariants to preserve: the marker line format and the `stage:`/`spec:` lines are unchanged (existing structural tests assert them); tokens stay excluded from the injected block; no stdout writes (the injector can run inside a chokepoint stdout-redirect frame — `stage_summary` returns a string, it must not print).

Constraints: do NOT modify any test file; file scope is exactly `fbk/report.py`. Path relative to `/home/rahvin/context-assets/assets/fbk-scripts/`.

## Instructions

1. Rewrite the body of `stage_summary` (fbk/report.py:209-227), keeping the signature and the first four lines of output exactly as today (marker, `stage: {stage}`, `spec: {spec}`):
   ```python
   events = _load_events(os.getcwd())
   st = _load_state(spec)
   attempts = classify_gate_attempts(events, st, stage)
   ftr = first_try_pass_rate(attempts)
   after_rework_attempts = [a for a in attempts if a["phase"] == "after_rework"]
   after_rework_rate = (
       sum(1 for a in after_rework_attempts if a["passed"]) / len(after_rework_attempts)
       if after_rework_attempts else 0.0
   )
   lines.append(f"first-try rate: {ftr:.2f}")
   lines.append(f"after-rework rate: {after_rework_rate:.2f}")
   lines.append(f"parks: {len(derive_parks(st, stage))}")
   lines.append(f"rework: {derive_rework(st, stage)}")
   ```
   The after-rework computation mirrors `_render_table` (lines 439-443) exactly — same divide-by-zero guard, same 0.0 default. `classify_gate_attempts` filters by stage internally, so passing the full events list is correct. Note `_load_events`/`_load_state` already return safe empties on missing files, so a no-events project renders `0.00`/`0.00`/`0`/`0` rather than raising. Done when the function returns all eight lines in order.
2. Update the `stage_summary` docstring: it loads events and state itself (events from the current working directory's `.fbk-capture/events.jsonl`, state via `_load_state`), renders the stage's real gate-rate/parks/rework values beneath the provenance marker, and is consumed only by `retro_injector.inject_stage_metrics`. Done when the docstring names the injector as the sole caller.
3. Run the gating tests. Expected fixture arithmetic (task-03): one fail + one pass before the park, one pass after → `first-try rate: 0.50`, `after-rework rate: 1.00`, `parks: 1`, `rework: 1`. The e2e two-source cycle drives no gate and no park → `first-try rate: 0.00`, `parks: 0`, `rework: 0`. The seam guard (task-04) computes `0.50`/`1.00`/`1`/`1` through real producers.

## Files to create/modify

- `assets/fbk-scripts/fbk/report.py` (modify)

## Test requirements

- Gating: task-03's extended `tests/test_capture_retro_injector.py::test_injects_block_under_metrics_heading` and strengthened `tests/test_capture_e2e_seam.py::test_two_source_cycle_joins_in_one_report`; task-04's `tests/test_capture_injection_seam.py::test_real_producer_cycle_injects_exact_metrics`.
- Must stay green: the other three tests in `tests/test_capture_retro_injector.py` (prose preservation, two marked blocks, swallowed exception); `tests/test_report_rendering.py` (the table renderer is untouched).

## Acceptance criteria

- AC-04: the per-stage block produced by `stage_summary` and injected into the retrospective contains the stage's real gate-rate, parks, and rework values.

## Model

Sonnet

## Wave

Wave 7
