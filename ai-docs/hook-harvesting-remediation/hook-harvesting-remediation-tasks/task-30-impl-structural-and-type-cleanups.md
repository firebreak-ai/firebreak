---
id: task-30
type: implementation
wave: 2
covers: [AC-17, AC-18]
files_to_modify:
  - assets/fbk-scripts/fbk/capture/chokepoint.py
  - assets/fbk-scripts/fbk/capture/retention.py
  - ai-docs/hook-harvesting/design/contracts.md
test_tasks: [task-18]
dependencies: []
completion_gate: "mypy reports zero errors on fbk/capture/chokepoint.py and fbk/capture/retention.py (pre-fix baseline: 4 errors — retention.py:21 assignment, chokepoint.py:71 and :82 return-value, chokepoint.py:152 misc); tests/test_capture_chokepoint.py, tests/test_capture_chokepoint_integration.py, and tests/test_capture_retention.py stay green"
---

## Objective

Normalise the chokepoint's fast-path return types, annotate retention's optional-`fcntl` fallback so the type-checker is clean, and correct the prior feature's contract document where its wording no longer matches (or never matched) the shipped behavior.

## Context

Slice: structural-and-type-cleanups (contract-preserving — no behavior change anywhere; the gate is mypy plus existing tests). The current mypy baseline on the two modules is exactly four errors:

```
fbk/capture/retention.py:21: error: Incompatible types in assignment (expression has type "None", variable has type Module)  [assignment]
fbk/capture/chokepoint.py:71: error: Incompatible return value type (got "int | None", expected "int")  [return-value]
fbk/capture/chokepoint.py:82: error: Incompatible return value type (got "int | None", expected "int")  [return-value]
fbk/capture/chokepoint.py:152: error: Exception must be derived from BaseException  [misc]
```

`record_dispatch` is typed `-> int` and its own docstring promises "0 when run_fn returns None", but the not-instrumented fast path (line 71) and the redirect-install-failure path (line 82) both `return run_fn()`, propagating `None`. (`fbk.py:44` happens to re-normalise at the CLI boundary, so this has no observable CLI effect — the fix makes the typed contract true at its source.) Line 152's error is mypy not narrowing `original_exit: SystemExit | None` through the separate `raised` flag.

Contract-document corrections — AC-18 names exactly three, all in `ai-docs/hook-harvesting/design/contracts.md` (repo-relative path; this is the prior feature's contract doc the spec explicitly amends — the ONLY file outside the package this task may touch; do not read the remediation's own design/ directory):

- **IF-D-07 consumed-by line** claims "the report command (reuses `stage_summary` for the full table)". Verified false: `stage_summary`'s only caller is `retro_injector.inject_stage_metrics` (retro_injector.py:46); `_render_table` never calls it.
- **IF-D-06** claims the gate "computes total raised, total confirmed, and rounds-to-quiet". Verified: the gate computes `total_raised`/`total_survived` only (code_review.py:150-151); `rounds_to_quiet` was never implemented and nothing consumes it. **Pinned resolution (the AC-18-permitted cheap option): REMOVE `rounds_to_quiet` from the contract** — computing and writing it would mint a dead field with no consumer, the same defect class as the removed `round_count`. Do not add code to `code_review.py`; this task does not touch that file (the per-round slice owns it in this wave).
- **IF-D-04** claims the gate-result payload is "summarized at standard, verbatim at full". Verified: the chokepoint puts the raw buffered stdout in `data["output"]` (chokepoint.py:115-124); `"output"` is a `FREETEXT_KEYS` member, so central redaction strips it entirely at `standard` and preserves it verbatim at `full` — nothing summarizes. **Pinned resolution: correct the wording** to match the shipped behavior.

The dead `round_count` removal AC-18 also names is implemented in `fbk/report.py` by the per-round task (task-26, this same wave) — it is NOT part of this task's file scope; do not touch `fbk/report.py`.

Invariants to preserve: chokepoint behavior byte-identical from the caller's perspective (same outcomes, same re-raise, same fail-silent discards); retention behavior unchanged (annotation only).

Multi-file justification: the three files share one acceptance criterion pair (type-checker clean + no misleading contract wording) and none overlaps any other wave-2 task; splitting would create three near-empty tasks.

Constraints: do NOT modify any test file; file scope is exactly the three files listed. Package paths relative to `/home/rahvin/context-assets/assets/fbk-scripts/`; the contracts file is repo-relative.

## Instructions

1. In `fbk/capture/chokepoint.py`, normalise the not-instrumented fast path (lines 70-71):
   ```python
   if not instrumented:
       result = run_fn()
       return 0 if result is None else result
   ```
   and the redirect-failure path (lines 80-82) the same way:
   ```python
   except Exception:
       # Redirect install failed: run directly with real stdout, record nothing.
       result = run_fn()
       return 0 if result is None else result
   ```
   (A `SystemExit` raised by `run_fn` on these paths propagates unchanged, exactly as today.) Done when both fast paths can only return `int`.
2. Still in `chokepoint.py`, fix the re-raise narrowing: change `if raised: raise original_exit` (lines 151-152) to `if original_exit is not None: raise original_exit`, and delete the now-unused `raised` flag (the `raised = False` initialisation at line 89 and the `raised = True` assignment at line 96). `original_exit` is set if and only if the flag was — behavior identical. Done when mypy reports zero errors on the file.
3. In `fbk/capture/retention.py`, annotate the fallback at line 21: `fcntl = None  # type: ignore[assignment]` — the documented pattern for an optional platform module; behavior unchanged. Done when mypy reports zero errors on the file. (Coordination note: task-25 — wave 3 — later adds a `_locked_specs` helper to this module; this task must not restructure anything beyond the one annotation.)
4. In `ai-docs/hook-harvesting/design/contracts.md`, make exactly three wording corrections:
   - IF-D-07's consumed-by line: replace `consumed-by: the state engine's transition_state() (calls the injector); the report command (reuses stage_summary for the full table)` with `consumed-by: the state engine's transition_state() (calls the injector); the injector is stage_summary's only consumer — the report command renders its table independently and never calls stage_summary. [Corrected by the hook-harvesting remediation: the original line claimed report-command reuse that was never built.]`
   - IF-D-06's Post invariant: replace "computes total raised, total confirmed, and rounds-to-quiet" with "computes total raised and total survived"; append to the entry: `[Resolved by the hook-harvesting remediation: rounds-to-quiet was specified but never implemented and has no consumer; it is removed from this contract rather than computed into a dead field. The gate also allowlist-projects each round entry (raised, survived, enum-validated severity) before writing, per the remediation spec.]`
   - IF-D-04's Post invariant: replace "and the gate-result payload (summarized at standard, verbatim at full)" with "and the gate-result payload carried verbatim in the event's output field (central redaction strips output entirely at standard and preserves it at full)"; append to the entry: `[Corrected by the hook-harvesting remediation: nothing summarizes the payload — the "summarized at standard" wording described behavior that does not exist.]`
   No other contract entry is edited. Done when the three bracketed remediation notes are present and the stale claims are gone.
5. Run the completion gate: `mypy fbk/capture/chokepoint.py fbk/capture/retention.py` (zero errors), then the three named test files.

## Files to create/modify

- `assets/fbk-scripts/fbk/capture/chokepoint.py` (modify)
- `assets/fbk-scripts/fbk/capture/retention.py` (modify)
- `ai-docs/hook-harvesting/design/contracts.md` (modify — repo-relative)

## Test requirements

- No new tests gate this task (contract-preserving).
- Must stay green: `tests/test_capture_chokepoint.py`, `tests/test_capture_chokepoint_integration.py`, `tests/test_capture_retention.py`, `tests/test_capture_event_writer.py`.

## Acceptance criteria

- AC-17: the chokepoint's not-instrumented and redirect-fail fast paths return an `int` (None normalised to 0), and the type-checker is clean on `chokepoint.py` and `retention.py`.
- AC-18 (this task's share): `rounds_to_quiet` is removed from IF-D-06; the gate-result "summarized" wording in IF-D-04 is corrected; the stage-summary consumed-by line in IF-D-07 is corrected. (The dead `round_count` removal is delivered by the per-round task in `fbk/report.py`; the decisions-log entry by the docs task.)

## Model

Sonnet

## Wave

Wave 2
