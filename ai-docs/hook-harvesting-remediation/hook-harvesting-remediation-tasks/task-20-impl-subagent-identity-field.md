---
id: task-20
type: implementation
wave: 3
covers: [AC-03]
files_to_modify:
  - assets/fbk-scripts/fbk/report.py
test_tasks: [task-02]
dependencies: [task-02]
completion_gate: "task-02 tests pass (rebuilt test_subagent_count_excludes_unknown_identity and new test_subagent_count_is_exact_over_production_envelopes); the rest of tests/test_report_arithmetic.py stays green"
---

## Objective

Make the report's known-subagent count read the agent identity the router actually writes, so the count stops being permanently zero.

## Context

Slice: subagent-identity-field. The hook router writes `SUBAGENT_STOP` envelopes with `source` always the literal `"hook_router"` (the writer name — `fbk/capture/hook_router.py:175`) and the agent identity in `data["agent_type"]` plus a precomputed `data["is_known_agent"]` boolean (`_assemble_data`, hook_router.py:117-123). `report.count_known_subagents` (fbk/report.py:198) reads `ev.get("source") or ev.get("data", {}).get("agent_type") or ""` — on a production envelope the truthy `source` always wins, the fallback never fires, `"hook_router"` is never a known agent, and the count is always 0.

New contract (IF-S-02): the identity comes from the event's `data`, never the envelope `source`. The pinned read is `data["agent_type"]` passed through `known_agents.is_known_agent` — this keeps the existing persona-scan side effects (the `STALE_FALLBACK` flag behavior the warning path and existing tests rely on) exactly as they are. Reading `data["is_known_agent"]` instead is permitted by the spec but NOT chosen here: pick the `agent_type` read; do not implement both.

Invariants to preserve: events with empty or unrecognised identities are excluded from the count but still recorded; no other row's computation changes.

Constraints: do NOT modify any test file; file scope is exactly `fbk/report.py`. Path is relative to `/home/rahvin/context-assets/assets/fbk-scripts/`.

## Instructions

1. In `count_known_subagents` (fbk/report.py:183-201), replace line 198:
   ```python
   identity = ev.get("source") or ev.get("data", {}).get("agent_type") or ""
   ```
   with:
   ```python
   identity = ev.get("data", {}).get("agent_type") or ""
   ```
   Done when the function never reads the envelope `source`.
2. Update the function docstring (lines 184-193): the count reads the agent identity from the event's `data["agent_type"]` — the envelope `source` is the writer's provenance name (always `"hook_router"` for these events) and is never treated as an agent identity. Done when the docstring states the producer field explicitly.
3. Run the gating tests. Expected arithmetic: one known + one empty + one unknown identity → exactly 1; two known + one unknown → exactly 2.

## Files to create/modify

- `assets/fbk-scripts/fbk/report.py` (modify)

## Test requirements

- Gating: task-02's two tests in `tests/test_report_arithmetic.py` (production envelope shape, `source="hook_router"`, exact counts 1 and 2).
- Must stay green: every other test in `tests/test_report_arithmetic.py`, including `test_stale_fallback_warning_fires_with_zero_subagent_events`; `tests/test_report_rendering.py` (the `known subagents:` line still renders).

## Acceptance criteria

- AC-03: the known-subagent count reads the identity the router writes (`data["agent_type"]`) and equals the exact number of known-agent events.

## Model

Haiku

## Wave

Wave 3
