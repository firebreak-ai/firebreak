# Quality Scan — example-feature

**Date**: 2026-06-23
**Change set**: example change set for contract fixture
**Mode**: scan-only; no fixes applied. Ranked highest priority first.

---

## Finding 1

- **Severity**: critical
- **Location**: `assets/fbk-scripts/fbk/parser.py`, lines 12–34
- **Description**: The parser accepts arbitrary-length input strings with no upper bound. A caller passing a large payload causes linear memory growth proportional to the input, with no early-exit path. The public API docstring implies the caller controls input size, but the function itself makes no assertion.
- **Opportunity**: Add a length guard at the entry point and raise `ValueError` with a clear message when the input exceeds the documented limit.

---

## Finding 2

- **Severity**: substantive
- **Location**: `assets/fbk-scripts/fbk/pipeline.py`, line 88
- **Description**: When `resolve_lens()` returns `None` for an unknown lens name, the pipeline proceeds with `None` as the active lens. Downstream callers that dereference the lens object raise `AttributeError` at an unrelated site, making the root cause hard to diagnose.
- **Opportunity**: Assert the resolved lens is not `None` immediately after the call and raise a descriptive error naming the unrecognised lens identifier.

---

## Finding 3

- **Severity**: substantive
- **Location**: `assets/fbk-scripts/fbk/report.py`, lines 45–60
- **Description**: The renderer iterates sightings in insertion order and assumes the highest-severity items appear first. The dict is populated in the order findings arrive from the researcher, which is undocumented and subject to agent non-determinism. A run that produces findings in a different order silently emits a misordered report.
- **Opportunity**: Sort sightings by a stable severity-rank key before rendering rather than relying on insertion order.

---

## Finding 4

- **Severity**: minor
- **Location**: `assets/fbk-scripts/fbk/config.py`, line 7
- **Description**: `DEFAULT_LENS_PATHS` is defined as a plain `list` and appended to in two call sites. Module-level mutable state that is modified at runtime makes test isolation harder: a test that triggers one append path leaves the list in a different state for subsequent tests unless explicitly cleaned up.
- **Opportunity**: Declare `DEFAULT_LENS_PATHS` as a `tuple` (immutable) and pass a derived list to callers that need to extend it, so the module-level state is never mutated.

---

## Finding 5

- **Severity**: minor
- **Location**: `assets/fbk-scripts/fbk/gates/review.py`, lines 101–108
- **Description**: Three branches emit the same `"Round limit reached without consensus"` string literal. A future edit that changes the wording must find and update all three sites; the duplication is not commented as intentional.
- **Opportunity**: Extract the string to a named module-level constant and reference it from all three branches.
