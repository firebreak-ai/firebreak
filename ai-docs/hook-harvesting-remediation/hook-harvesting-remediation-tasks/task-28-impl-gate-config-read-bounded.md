---
id: task-28
type: implementation
wave: 2
covers: [AC-10]
files_to_modify:
  - assets/fbk-scripts/fbk/capture/gate_check.py
test_tasks: [task-06]
dependencies: [task-06]
completion_gate: "task-06 tests pass (tests/test_capture_gate_check.py::test_oversized_first_segment_resolves_safe_default and ::test_giant_single_line_cfg_stays_fast); the rest of tests/test_capture_gate_check.py and tests/test_capture_gate_check_hardening.py stay green"
---

## Objective

Byte-bound both hot-path config reads in the capture gate so a hostile repository whose `capture.cfg` (or capture-level marker file) is one giant newline-less line cannot stall every tool call.

## Context

Slice: gate-config-read-bounded. The capture gate runs on EVERY tool call via the hook router and the chokepoint. `_read_cfg_level` (fbk/capture/gate_check.py:101-102) calls an unbounded `f.readline()` — a multi-megabyte single-line `capture.cfg` is read in full on the hot path. `_full_corroborated` (lines 151-153) has the same unbounded `readline()` pair over operator marker files. The feature's threat model names this exact denial-of-service and names a bounded single-line read as its mitigation.

**Declared bound (copied verbatim from task-06 — do not paraphrase).** `_read_cfg_level` reads `f.readline(256)`; the `_full_corroborated` marker-file reads are bounded with `f.readline(4096)` (realpath line) — both hot-path reads byte-capped, behavior otherwise unchanged: a first segment with no parseable `capture_level=` token yields `None`, and the gate falls back to the safe default.

Semantics with the cap (how the divergence test exercises it): `readline(256)` returns at most 256 bytes of the first line. For a line of 256 spaces followed by `capture_level=full`, the bounded read returns only the spaces → `strip()` → empty → no `=` → `None` → `resolve_capture_level` falls through to `"standard"` (Firebreak-marked, no readable cfg). The unbounded pre-fix read resolves `full`. The 4096 cap on the marker reads is sized for the realpath line (PATH_MAX is 4096 on Linux); a path longer than the cap simply fails the equality match and corroboration is refused — the safe direction.

Invariants to preserve: every error path returns the safe default (`None` / `False`), never raises; symlink refusals unchanged; no new imports (the module deliberately uses only `os`/`sys` + bounded file I/O).

Constraints: do NOT modify any test file; file scope is exactly `fbk/capture/gate_check.py`. Path relative to `/home/rahvin/context-assets/assets/fbk-scripts/`.

## Instructions

1. In `_read_cfg_level` (line 102), change `line = f.readline().strip()` to `line = f.readline(256).strip()`. Update the docstring line "Only one line is read regardless of file size." to state the read is byte-bounded (first 256 bytes of the first line) so a giant newline-less file cannot stall the hot path; a window with no parseable token yields None and the caller's safe default. Done when no unbounded readline remains in this function.
2. In `_full_corroborated` (lines 152-153), change both reads to `line1 = f.readline(4096).strip()` and `line2 = f.readline(4096).strip()`, with a one-line comment: byte-capped (4096 covers PATH_MAX for the realpath line); an over-cap line fails the match and corroboration is refused — fail-closed. Done when no unbounded readline remains in the module.
3. Run the gating tests. Expected: with `FBK_CAPTURE_LEVEL=full` set and a cfg line of 256 spaces + `capture_level=full`, `resolve_capture_level` returns exactly `"standard"`; the 5 MB single-line cfg also resolves `"standard"`.

## Files to create/modify

- `assets/fbk-scripts/fbk/capture/gate_check.py` (modify)

## Test requirements

- Gating: task-06's `tests/test_capture_gate_check.py::test_oversized_first_segment_resolves_safe_default` (the divergence guard) and `::test_giant_single_line_cfg_stays_fast` (correctness gating, timing advisory).
- Must stay green: the rest of `tests/test_capture_gate_check.py` (valid one-line cfgs are far under 256 bytes), `tests/test_capture_gate_check_hardening.py` (symlink/confinement behavior untouched), `tests/test_capture_gate_check_overhead.py`.

## Acceptance criteria

- AC-10: both hot-path reads in `gate_check.py` are byte-bounded; a `capture.cfg` that is one giant newline-less line cannot stall tool calls; the guard proves the bound by divergence, not timing.

## Model

Haiku

## Wave

Wave 2
