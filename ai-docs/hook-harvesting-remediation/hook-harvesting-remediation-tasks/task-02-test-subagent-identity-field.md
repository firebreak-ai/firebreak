---
id: task-02
type: test
wave: 1
covers: [AC-03]
files_to_modify:
  - assets/fbk-scripts/tests/test_report_arithmetic.py
completion_gate: "Rebuilt and new subagent-count tests collect cleanly at the current tree and FAIL (count 0 != expected) from a second git worktree at the pre-fix commit (40ec021 at spec time) with the test file copied in; failing output captured in the subagent-identity slice's completion notes."
---

## Objective

Rebuild the subagent-count guard with the production envelope shape so it can only pass when the report reads the agent identity field, and add an exact-count guard.

## Context

Slice: subagent-identity-field (contract-evolving). The hook router writes `SUBAGENT_STOP` envelopes with `source` always the literal `"hook_router"` (the writer name) and the agent identity in `data["agent_type"]` plus a precomputed `data["is_known_agent"]` boolean (see `fbk/capture/hook_router.py`, `_assemble_data`). The current `report.count_known_subagents` (fbk/report.py:198) reads `ev.get("source") or ev.get("data", {}).get("agent_type")` — on a production envelope the truthy `source` (`"hook_router"`) always wins, the fallback never fires, and the count is always 0. The retired test masked this by building `source=<agent-name>`, a shape no producer emits.

New contract: `count_known_subagents` reads the identity from `data["agent_type"]` (or the precomputed `data["is_known_agent"]`); the envelope `source` is never treated as an agent identity. Fixtures must set BOTH data fields consistently (same truth value the persona scan would produce) so the test passes under either permitted read.

The file's existing `_write_persona` helper and the `FBK_AGENTS_DIR` monkeypatch pattern (see `test_subagent_count_excludes_unknown_identity`) are the established way to control the known-agent set; keep using them. The probe identity must stay absent from `known_agents.FALLBACK_AGENTS` (keep the existing sanity guard).

## Instructions

1. Rebuild `test_subagent_count_excludes_unknown_identity` in place: keep the persona-dir setup, the `FALLBACK_AGENTS` sanity guard, and the `STALE_FALLBACK is False` post-assertion. Change the three events so every event pins `source="hook_router"` (the production literal) and carries identity only in `data`:
   - `data={"agent_type": "fbk-scan-probe", "is_known_agent": True}` (counted),
   - `data={"agent_type": "", "is_known_agent": False}` (excluded),
   - `data={"agent_type": "random-unknown-bot", "is_known_agent": False}` (excluded).
   Assert `count == 1` exactly. Update the docstring to state the production-shape rationale (source is the writer name, never the identity). Done when no event in this test carries an agent name in `source`.
2. Add `test_subagent_count_is_exact_over_production_envelopes`: write two personas (`fbk-scan-probe-a`, `fbk-scan-probe-b`) into the temp agents dir, point `FBK_AGENTS_DIR` at it; build three `SUBAGENT_STOP` events, all `source="hook_router"`: probe-a (`is_known_agent: True`), probe-b (`is_known_agent: True`), `"random-unknown-bot"` (`is_known_agent: False`). Assert `report.count_known_subagents(events) == 2` exactly. Include a comment stating the red mechanics: the pre-fix read takes the truthy envelope `source` first — always `"hook_router"`, never a known agent — so the pre-fix count is exactly 0 and the test fails red as 0 != 2. Done when the comment and the exact assertion are present.
3. Red run: from the pre-fix worktree with this file copied in, run both tests; capture the failing output (count 0) in the slice's completion notes. Done when both pre-fix and post-fix runs are captured.

## Files to create/modify

- `assets/fbk-scripts/tests/test_report_arithmetic.py` (modify)

## Test requirements

- Integration (production envelope shape, real `known_agents` scan via `FBK_AGENTS_DIR`) — rebuilt exclusion test: one known + one empty + one unknown identity, all `source="hook_router"` → count exactly 1; `known_agents.STALE_FALLBACK is False`.
- Integration — exact-count test: two known + one unknown, all `source="hook_router"` → count exactly 2.

## Acceptance criteria

- AC-03: the known-subagent count reads the identity the router writes (`data["agent_type"]` / `data["is_known_agent"]`) and equals the exact number of known-agent events; the rebuilt guard pins `source="hook_router"` and an exact expected count.

## Model

Sonnet

## Wave

Wave 1
