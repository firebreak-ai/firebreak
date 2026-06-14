---
id: task-07
type: test
wave: 1
covers: [AC-07]
files_to_modify:
  - assets/fbk-scripts/tests/test_capture_retention.py
completion_gate: "Concurrency test collects cleanly and passes deterministically (run it 5 times in a row locally) at the post-fix tree; the slice is contract-preserving, so no red run is required — note that explicitly in the retention slice's completion notes."
---

## Objective

Author the spec-mandated concurrency guard: a baseline lock created during an active write protects its spec's lines through the prune.

## Context

Slice: retention-locked-set-under-lock — contract-preserving, normally no new test, BUT the spec's testing strategy explicitly mandates this one concurrency unit test (AC-07), and that spec requirement wins. AC-07 is deliberately absent from AC-21's red-run list: no pre-fix failure demonstration is required.

The defect: `event_writer.write` (fbk/capture/event_writer.py:117-126) appends under `retention.file_lock`, releases the lock, THEN reads the locked-spec set via `_locked_specs` as a one-shot snapshot, then calls `retention.prune_if_needed` (which takes the lock again). A lock file dropped after the snapshot but before the prune's rewrite is not honored.

**Implementation shape (pinned by the implementation task — informational only; do NOT encode it in the test).** The fix takes the IF-S-06-permitted retention-side alternative: `retention._prune_locked` re-reads the `locked/` directory within its own locked section and unions that fresh set with the caller-passed `protect_specs` snapshot. (A single combined lock scope inside `event_writer` is not buildable: `file_lock` is a same-process flock, so re-entering it from `prune_if_needed` while held would deadlock — proven by `test_file_lock_is_exclusive` — and it would break `test_write_runs_prune_check_after_append`, which monkeypatches `prune_if_needed` and asserts the 3-arg call.) The test asserts only the observable contract — a lock created during an active write protects its spec's lines — and must stay valid under any compliant mechanism.

Mechanics available (all owned code or the real filesystem — no stand-ins): `retention.file_lock(events_path)` is a public context manager; `retention.DEFAULT_MAX_BYTES` is 5 MB; `_locked_specs` reads empty files under `<capture_dir>/locked/`; lines whose `spec` is protected are never dropped while protected bytes stay under `DEFAULT_MAX_BYTES * PROTECTED_FRACTION` (2.5 MB). Existing helpers in this file: `_events_path(base)`, `_specs_in_file(path)`, `_warning_path(base)`.

## Instructions

1. Add `test_lock_created_during_active_write_protects_spec_lines(tmp_path)` to `tests/test_capture_retention.py`:
   - Build the events file directly (setup, not the path under test) at `<tmp_path>/.fbk-capture/events.jsonl` with `capture_fixtures.build_event` + `write_events`, using `event_type="TOOL_USE"` for both fixture groups (any non-`"LIFECYCLE"` type — the final assertion counts exactly 1 `LIFECYCLE` line to confirm the thread's appended event survived): exactly 2000 lines with `spec="locked-spec"` followed by 4000 lines with `spec="other-spec"`, each carrying `data={"pad_field": "y" * 1000}` so each line is roughly 1.1 KB. Comment the arithmetic: protected bytes ~2.2 MB stay under the 2.5 MB protected ceiling (so no locked drop / no sentinel), total ~6.6 MB exceeds the 5 MB cap (so the prune fires).
   - Acquire the events lock in the main thread: enter `retention.file_lock(events_path)` via `contextlib.ExitStack` or a `with` block structured so steps below happen inside it.
   - While holding the lock: start `threading.Thread(target=event_writer.write, args=("LIFECYCLE", "hook_router", {}, "other-spec", None, "standard", events_path))` — the production write path; it must block on the lock.
   - Still holding the lock: create the baseline lock file `<tmp_path>/.fbk-capture/locked/locked-spec` (empty file, parent dir created). This is the "lock created during an active write".
   - Release the events lock; `thread.join(timeout=30)`; assert `not thread.is_alive()`.
   - Assertions on `events.jsonl`:
     - every one of the 2000 `locked-spec` lines survived: count of lines with `spec == "locked-spec"` is exactly 2000;
     - the prune actually ran: file size is at most `retention.DEFAULT_MAX_BYTES`, and the count of `other-spec` lines is strictly less than 4001 (presence pair: also assert it is at least 1);
     - the thread's appended event survived as the newest unprotected line: exactly 1 line with `event_type == "LIFECYCLE"`;
     - no `.retention-warning` sentinel exists (locked bytes stayed under the ceiling — a sentinel here means locked lines were wrongly dropped).
   - Docstring: state the OBSERVABLE contract only (a lock created during an active write protects its spec's lines) plus the sequencing guarantee — the test holds the events lock until after the lock file exists, and the prune's protected-set determination happens inside a lock scope that cannot begin until the test releases, by which time the lock file is on disk; so the protection is honored regardless of thread scheduling (deterministic, no sleeps). Do not name or assert the internal mechanism (no monkeypatching, no assertions on `_locked_specs`/`_prune_locked` call shapes) — the guard must stay valid under any compliant implementation.
   Done when the test passes 5 consecutive runs at the post-fix tree.
2. Note in the slice's Context for completion notes: contract-preserving slice; this guard is a spec-mandated addition (AC-07), exempt from the red-run discipline.

## Files to create/modify

- `assets/fbk-scripts/tests/test_capture_retention.py` (modify)

## Test requirements

- Unit (concurrency, real threads + real flock) — after a contended write with the lock file created mid-write: exactly 2000 protected lines survive; file size ≤ `DEFAULT_MAX_BYTES`; other-spec lines pruned (count ≥ 1 and < 4001); exactly 1 appended `LIFECYCLE` line present; no retention-warning sentinel.

## Acceptance criteria

- AC-07: a baseline lock created during an active write is honored — the locked-spec set is read inside the prune's lock scope, and the constructed concurrent test confirms the lines survive.

## Model

Sonnet

## Wave

Wave 1
