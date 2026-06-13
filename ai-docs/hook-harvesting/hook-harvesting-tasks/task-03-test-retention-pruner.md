---
id: task-03
type: test
wave: 2
covers: [AC-14, AC-25]
files_to_create:
  - assets/fbk-scripts/tests/test_capture_retention.py
completion_gate: "tests compile and fail before implementation"
---

# Objective

Write the unit tests for the size-cap retention pruner: it drops oldest lines past the cap, never drops a protected (baseline-locked) spec's lines until those exceed a defined fraction of the cap, caps protected bytes past that ceiling by dropping oldest locked lines too with a surfaced warning, and leaves the file intact on any failure.

# Context

The events file `.fbk-capture/events.jsonl` self-prunes at a size cap (default ~5MB) by dropping the oldest lines. Lines whose spec has an empty lock file under `.fbk-capture/locked/` are protected from pruning — this is the before/after-baseline-comparison guarantee. To stop a lock from growing the file without bound, protected lines are themselves capped at a defined fraction of the cap; past that ceiling the pruner drops oldest locked lines too and surfaces a warning that the report later renders.

The over-cap warning's durable channel is pinned: when the pruner drops locked lines past the protected-bytes ceiling, it writes a sentinel file `.fbk-capture/.retention-warning` (under the realpath-confined capture dir). A normal prune (no locked lines dropped) does not write it. The report reads this sentinel and renders the over-cap warning the same way the stale-fallback warning surfaces.

The pruner is a pure file operation exercised through `tmp_path`. Each event line carries a `spec` field; `protect_specs` is the set of locked spec names. Import inside `try/except ImportError` with a module-level skipif, matching the suite pattern. Use `from tests import capture_fixtures` to build event streams (`build_event` + `write_events`).

Signature to call verbatim: `retention.prune_if_needed(events_path, max_bytes, protect_specs) -> None`.

# Instructions

1. Create `tests/test_capture_retention.py`; import `from fbk.capture import retention` inside `try/except ImportError`; module-level `pytestmark = pytest.mark.skipif(...)`.
2. `test_drops_oldest_lines_past_cap`: write an events file of many lines from one unprotected spec whose byte size exceeds a small `max_bytes` you pass; call `retention.prune_if_needed(path, max_bytes, set())`; assert the resulting file size is `<= max_bytes` AND the file still has at least one line (pair the upper bound with a lower-bound presence assertion), AND the surviving lines are the newest (assert the last original line is still present and an early original line is gone).
3. `test_never_drops_protected_spec_under_ceiling`: write an events file mixing an unprotected spec (many lines) and a protected spec (a few lines, total well under the protected-bytes ceiling); call with `protect_specs={"<protected-spec>"}` and a `max_bytes` that forces pruning; assert every protected-spec line survives (count them before and after — exact equality) while unprotected lines were dropped to bring the file under cap.
4. `test_protected_bytes_capped_past_ceiling`: write an events file where the protected spec's lines alone exceed the defined protected-bytes fraction of `max_bytes`; call the pruner; assert the protected spec's surviving line count is strictly less than its original count (oldest locked lines dropped) AND at least one protected line survives — pair the upper bound (some dropped) with the lower bound (not all dropped). The defined fraction is an implementation detail; assert the *behavior* (some locked lines dropped once protected bytes exceed a fraction of the cap), not a specific numeric ratio.
5. `test_over_cap_condition_is_surfaced`: after the over-ceiling prune in the previous scenario, assert the sentinel `.fbk-capture/.retention-warning` exists. Then, in a separate normal-prune scenario (drops only unlocked lines, no locked lines dropped), assert the sentinel does NOT exist — pinning the signal to the over-ceiling case only.
6. `test_leaves_file_intact_on_failure`: point the pruner at a path that triggers a failure (e.g. a directory path, or a read-only file when a rewrite is required); call it; assert it raises nothing AND the original bytes are unchanged (read before and after, assert equal).
7. `test_no_prune_when_under_cap`: write a small events file under `max_bytes`; call the pruner; assert the file is byte-for-byte unchanged.

# Files to create/modify

- `tests/test_capture_retention.py`

# Test requirements

- `test_drops_oldest_lines_past_cap` (unit): over-cap file pruned to `<= max_bytes`, newest lines retained, at least one line survives.
- `test_never_drops_protected_spec_under_ceiling` (unit): locked spec lines all survive while unlocked lines drop.
- `test_protected_bytes_capped_past_ceiling` (unit): locked lines past the protected-bytes ceiling are partially dropped (oldest first), some survive.
- `test_over_cap_condition_is_surfaced` (unit): the `.fbk-capture/.retention-warning` sentinel exists after an over-ceiling prune, absent after a normal prune.
- `test_leaves_file_intact_on_failure` (unit): a failing prune raises nothing and leaves bytes unchanged.
- `test_no_prune_when_under_cap` (unit): an under-cap file is left byte-identical.

# Acceptance criteria

AC-14 (size cap + baseline protection), AC-25 (protected-bytes ceiling + surfaced warning). Gate: tests compile and fail before implementation.

# Model

Sonnet — byte-level pruning with ordering and protected-fraction judgment.

# Wave

2
