---
id: task-16
type: test
wave: 2
covers: [AC-14]
files_to_modify:
  - assets/fbk-scripts/tests/test_capture_event_writer.py
completion_gate: "SOURCES-driven redaction tests collect cleanly and pass at the current tree; the pre-fix run is captured with an explicit note that this is a test-coverage correction (production redaction already strips registered free-text keys, so green at pre-fix is the expected outcome), in the redaction-coverage completion notes."
---

## Objective

Rebuild the full-level preservation test and add the central-redaction guard so both enumerate `schema.SOURCES` dynamically — a new registered producer is covered automatically instead of staying invisible.

## Context

Slice: redaction-coverage-from-sources (cross-cutting, test-only; retires the single hand-built payload in `test_full_level_preserves_payload`). The current standard/full redaction tests hard-code one `hook_router` payload, so a producer added to `schema.SOURCES` ships with zero redaction coverage. The rebuilt tests derive the producer list and the free-text key set from the registry (`schema.SOURCES`, `schema.FREETEXT_KEYS`) at runtime — that derivation is the registry enumeration AC-14 mandates, not a re-implementation of the redaction algorithm; the expected survival/strip outcomes stay pinned by hand.

Deriving the payload keys from `schema.FREETEXT_KEYS` is load-bearing for coexistence with the per-round fix: after task-09's schema change removes `"rounds"` from the denylist, a hard-coded `"rounds"` sentinel would wrongly survive and break this test; the dynamic key set adapts.

Wave note: wave 2 — task-09 owns `tests/test_capture_event_writer.py` in wave 1; task-17 takes it in wave 3.

These are test-fidelity corrections over already-correct production redaction: green at the pre-fix commit is the expected red-run outcome, and AC-21's record for AC-14 must say so explicitly.

## Instructions

1. Rebuild `test_full_level_preserves_payload` as a parametrized test over `schema.SOURCES` (`@pytest.mark.parametrize("source", schema.SOURCES)`):
   - Per source, use its own events file (`tmp_path / source / ...`) for isolation; build `payload = {key: f"FREETEXT-SENTINEL-{key}" for key in sorted(schema.FREETEXT_KEYS)}` plus `{"count": 7}`; call `event_writer.write("TOOL_USE", source, payload, "s", "IMPLEMENTING", "full", path)`.
   - Assert exactly 1 line written and `record["data"] == payload` (exact dict equality — full preserves everything verbatim).
   Done when the parametrization replaces the single hand-built payload.
2. Add `test_standard_level_strips_freetext_for_every_registered_source`, parametrized the same way:
   - Same payload construction, written at `"standard"`.
   - Assert exactly 1 line written; `"FREETEXT-SENTINEL"` does not appear anywhere in the raw written line (string-level check catches leaks under any key); `record["data"]["count"] == 7` (numeric survival); and every key remaining in `record["data"]` is absent from `schema.FREETEXT_KEYS`.
   Done when all three assertion families are present.
3. Add the registry lower-bound guard inside the standard-level test (module-level asserts don't report well): `assert len(schema.SOURCES) >= 4 and "hook_router" in schema.SOURCES` — the presence pair that keeps the dynamic enumeration from passing trivially on an emptied registry.
4. Pre-fix run: from the worktree at the recorded commit with the file copied in, run both tests; record the outcome with the expected-green rationale in the slice's completion notes.

## Files to create/modify

- `assets/fbk-scripts/tests/test_capture_event_writer.py` (modify)

## Test requirements

- Unit (production write path, parametrized over `schema.SOURCES`) — full level: written `data` exactly equals the sentinel-bearing payload for every registered source.
- Unit (parametrized) — standard level: no sentinel string survives anywhere in the raw line for any registered source; `count == 7` survives; no surviving key is a `FREETEXT_KEYS` member; registry lower bound `len(schema.SOURCES) >= 4` with `"hook_router"` present.

## Acceptance criteria

- AC-14: the central-redaction test derives its producer list dynamically from `schema.SOURCES`, so a new producer that bypasses the writer is caught by the test rather than silently invisible.

## Model

Sonnet

## Wave

Wave 2
