---
id: task-25
type: implementation
wave: 3
covers: [AC-07]
files_to_modify:
  - assets/fbk-scripts/fbk/capture/retention.py
  - assets/fbk-scripts/fbk/capture/event_writer.py
test_tasks: [task-07]
dependencies: [task-07]
completion_gate: "task-07's concurrency test passes 5 consecutive runs; tests/test_capture_retention.py fully green; tests/test_capture_event_writer.py fully green INCLUDING test_write_runs_prune_check_after_append (the prune_if_needed wiring monkeypatch) and test_file_lock_is_exclusive; mypy stays clean on retention.py"
---

## Objective

Make the prune consult a locked-spec set read while holding the events lock, so a baseline lock dropped during an active write is honored and its spec's lines survive the prune.

## Context

Slice: retention-locked-set-under-lock (contract-preserving — every existing retention and writer test must stay green throughout; task-07's new concurrency test is the only added guard, and no red run is required).

The defect: `event_writer.write` (fbk/capture/event_writer.py:117-126) appends under `retention.file_lock`, releases, reads the locked-spec set via `_locked_specs`, then calls `retention.prune_if_needed` (which re-takes the lock in `prune_if_needed`, line 104). A lock file created between the writer's locked-set read and the prune's lock acquisition is not in `protect_specs`, so the prune — now holding the lock — drops the newly-locked spec's lines.

**The observable contract (from task-07 / IF-S-06): the protected set consulted by the prune is read while holding the events lock.** IF-S-06 permits two shapes: the writer performs append + read + prune in one lock scope, OR "retention re-reads locked/ within its own locked section." This task pins the SECOND shape, for two codebase-verified reasons the first cannot survive:
- `tests/test_capture_event_writer.py::test_write_runs_prune_check_after_append` monkeypatches `retention.prune_if_needed` and asserts the writer calls it once with the events path and the same three-argument shape. A writer that bypasses `prune_if_needed` (calling `_prune_locked` directly under its own held lock) fails that test, and implementation agents may not modify tests.
- `retention.file_lock` uses `flock`, whose locks attach to the open file description: re-acquiring through `prune_if_needed`'s own `file_lock` while the writer already holds it deadlocks the process (same-process second fd blocks — proven by `test_file_lock_is_exclusive`).

So: `_prune_locked` re-derives the locked set from `<capture_dir>/locked/` AFTER acquiring the lock, and unions it with the caller-passed `protect_specs`. Every existing retention test passes an explicit set and creates no `locked/` directory, so the union is a no-op for them; task-07's scenario is protected because the lock file is on disk before the writer can ever reach the prune's locked section.

Invariants to preserve: fail-silent everywhere (no raise, no stdout); `prune_if_needed`'s public three-argument signature unchanged; the sentinel is written only when locked lines are actually dropped; the writer's append-then-prune sequence and its single `prune_if_needed` call are unchanged.

Two-files justification: the locked-set helper moves from the writer to retention (the module whose locked section consumes it) and the writer delegates to it — the move and the delegation are one rename landing atomically.

Constraints: do NOT modify any test file; file scope is exactly the two files listed. Paths relative to `/home/rahvin/context-assets/assets/fbk-scripts/`.

## Instructions

1. In `fbk/capture/retention.py`, add a private helper above `prune_if_needed` — the body is moved verbatim from `event_writer._locked_specs` (event_writer.py:135-153), with a return annotation that keeps mypy clean:
   ```python
   def _locked_specs(capture_dir: str) -> set[str]:
       """Return the set of spec names with an empty lock file under locked/.

       An absent or unreadable locked/ directory yields an empty set.
       """
   ```
   (same listdir/isfile/getsize-0 logic, same OSError swallow). Done when retention owns the helper.
2. In `retention._prune_locked` (line 112), immediately after the under-lock size re-check (lines 115-119), insert the under-lock re-read:
   ```python
   # Re-derive the locked set while holding the events lock and union it with
   # the caller's snapshot: a lock file dropped after the caller read its set
   # but before this prune acquired the lock is honored (IF-S-06 — the
   # protected set consulted by the prune is read under the lock).
   capture_dir = os.path.dirname(os.path.abspath(events_path))
   protect_specs = set(protect_specs) | _locked_specs(capture_dir)
   ```
   Done when the classification loop below reads only the unioned set.
3. Update `prune_if_needed`'s docstring `protect_specs` description: the caller's snapshot of protected specs; the locked section re-reads `locked/` and unions, so a concurrently-added lock is honored. Done when the docstring states the union.
4. In `fbk/capture/event_writer.py`, delete the local `_locked_specs` function (lines 135-153) and change line 123 to `protect_specs = retention._locked_specs(capture_dir)`. Update the comment above it (lines 121-122) to note the prune re-reads the set under its lock, so this read is a best-effort snapshot. Done when the writer contains no `_locked_specs` definition and its `write` body is otherwise byte-identical.
5. Run the gating tests, including five consecutive runs of task-07's `test_lock_created_during_active_write_protects_spec_lines`, then `mypy fbk/capture/retention.py` (must report no errors — the file is clean today apart from the `fcntl` fallback owned by task-30; do not touch lines 18-21).

## Files to create/modify

- `assets/fbk-scripts/fbk/capture/retention.py` (modify)
- `assets/fbk-scripts/fbk/capture/event_writer.py` (modify)

## Test requirements

- Gating: task-07's `tests/test_capture_retention.py::test_lock_created_during_active_write_protects_spec_lines` (2000 protected lines survive, prune ran, appended event present, no sentinel), deterministic across 5 runs.
- Must stay green: all of `tests/test_capture_retention.py` (explicit-set prunes, over-ceiling drops, sentinel rules); all of `tests/test_capture_event_writer.py`, especially `test_write_runs_prune_check_after_append` and `test_file_lock_is_exclusive`.

## Acceptance criteria

- AC-07: a baseline lock created during an active write is honored — the locked-spec set is read inside the prune's lock scope, and the constructed concurrent test confirms the lines survive.

## Model

Sonnet

## Wave

Wave 3
