---
id: task-06
type: test
wave: 1
covers: [AC-10]
files_to_modify:
  - assets/fbk-scripts/tests/test_capture_gate_check.py
completion_gate: "Rebuilt divergence test collects cleanly at the current tree and FAILS (resolves 'full' where 'standard' is asserted) from a second git worktree at the pre-fix commit (40ec021 at spec time) with the file copied in; failing output captured in the gate-config-read-bounded slice's completion notes."
---

## Objective

Rebuild the bounded-read guard on a divergence fixture so the bounded and unbounded cfg reads provably return different values, plus a non-gating wall-clock companion.

## Context

Slice: gate-config-read-bounded (contract-evolving; retires `test_level_reads_only_one_line`). The retired test put its 5 MB payload on the SECOND line, so the unbounded `f.readline()` in `_read_cfg_level` (fbk/capture/gate_check.py:101-102) never exercised the attack: a `capture.cfg` that is one giant newline-less line stalls every tool call.

**Declared bound (the implementation task copies this verbatim).** `_read_cfg_level` reads `f.readline(256)`; the `_full_corroborated` marker-file reads are bounded with `f.readline(4096)` (realpath line) — both hot-path reads byte-capped, behavior otherwise unchanged: a first segment with no parseable `capture_level=` token yields `None`, and the gate falls back to the safe default.

**Fixture correction against the spec's example (flagged to the operator; the principle wins over the example).** The spec suggests `"x" * 256` filler, but `_read_cfg_level` partitions on the FIRST `=` and requires the key to strip to exactly `capture_level` — with x-filler the unbounded read also fails the key match and returns `standard`, so both implementations agree and the test proves nothing. Whitespace filler keeps the unbounded parse valid (`line.strip()` removes it), producing the required divergence: the bounded read sees 256 spaces (no token → safe default `standard`) while the unbounded read resolves the non-default `full` beyond the cap.

Corroboration is required for the divergence to be observable: `resolve_capture_level` clamps an uncorroborated `full` to `standard`. Setting `FBK_CAPTURE_LEVEL=full` makes the pre-fix path return `"full"` while the bounded path still returns `"standard"`.

## Instructions

1. Replace `test_level_reads_only_one_line` with `test_oversized_first_segment_resolves_safe_default(tmp_path, monkeypatch)`:
   - Build `root = capture_fixtures.make_project(str(tmp_path), instrumented=False)`; write `<root>/.fbk-capture/capture.cfg` whose single line is `" " * 256 + "capture_level=full\n"` (the parseable non-default token sits entirely beyond the 256-byte cap).
   - `monkeypatch.setenv("FBK_CAPTURE_LEVEL", "full")` — out-of-tree corroboration, so the pre-fix unbounded read resolves `"full"`, not a clamped `"standard"`.
   - Assert `gate_check.resolve_capture_level(root) == "standard"` — the bounded read finds no token in its byte window and returns the safe default; the test fails on the unbounded read by correctness, not timing.
   - Docstring must state the divergence design, including why the token beyond the cap must be the NON-default `full` (a `standard` token there would make both reads agree and the test would pass trivially on both implementations) and why whitespace filler replaces the spec's x-filler example.
   Done when the old test name is gone and the new test carries these assertions and docstring.
2. Add the non-gating companion `test_giant_single_line_cfg_stays_fast(tmp_path)`:
   - cfg = one newline-less line of `"x" * (5 * 1024 * 1024)`.
   - Gating correctness assertion: `resolve_capture_level(root) == "standard"` (cfg file exists → instrumented; no parseable token in the bounded window → safe default).
   - Advisory timing assertion: a single timed call completes in under 0.5 s, marked `@pytest.mark.flaky_quarantine` — follow the convention and comment style of `tests/test_capture_gate_check_overhead.py` (correctness gating, timing advisory).
   Done when the marker and both assertions are present.
3. Red run: from the pre-fix worktree with the file copied in, run the divergence test; capture the failing output (`'full' != 'standard'`) in the slice's completion notes.

## Files to create/modify

- `assets/fbk-scripts/tests/test_capture_gate_check.py` (modify)

## Test requirements

- Unit (divergence) — cfg line of 256 spaces followed by `capture_level=full` on the same line, with `FBK_CAPTURE_LEVEL=full` set: `resolve_capture_level` returns exactly `"standard"`.
- Unit (companion, non-gating on flake) — 5 MB single-line cfg: returns exactly `"standard"`; advisory sub-0.5 s timing under `flaky_quarantine`.

## Acceptance criteria

- AC-10: both hot-path reads in `gate_check.py` are byte-bounded; the guard proves the bound by divergence (safe default where the unbounded read resolves a non-default token beyond the cap), not by timing.

## Model

Sonnet

## Wave

Wave 1
