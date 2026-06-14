# Pre-Lock Test Review — Hook-Harvesting Remediation

**Feature:** hook-harvesting-remediation
**Mode:** Pre-lock (breakdown stage — test tasks authored, no new test code exists yet)
**Date:** 2026-06-12
**Reviewer:** test-reviewer agent (independent context)

**Reviewed file set:**
- Spec: `ai-docs/hook-harvesting-remediation/hook-harvesting-remediation-spec.md`
- Test task files: task-01 through task-18 (all 18 test tasks)
- Pre-existing test files under lock consideration: `assets/fbk-scripts/tests/test_capture_retention.py`, `tests/test_capture_chokepoint.py`, `tests/test_capture_chokepoint_integration.py`
- Implementation tasks cross-checked: task-25 (retention lock), task-30 (structural/type cleanups)

---

## Section 1 — Lock-readiness of the pre-existing test files

### 1a. `test_capture_retention.py`

Behavioral validity: all six existing tests make four-sided, behaviorally specific assertions (exact line counts, byte bounds, sentinel presence/absence, byte-level identity on failure and no-op paths) against the real module and real filesystem. Compatible with task-25's planned change: every existing test passes an explicit `protect_specs` set and creates no `locked/` directory, so the implementation's union with the re-read locked set is a no-op for them; the three-argument public signature of `prune_if_needed` is preserved.

**Finding 1 — blocking (resolved by lock-set narrowing, see addendum).** Task-07 must add `test_lock_created_during_active_write_protects_spec_lines` to this file; locking the file before task-07 executes would make the lock a contradiction. The six existing tests are sound, but the file is not yet in its final state. Lock only after task-07 completes.

### 1b. `test_capture_chokepoint.py`

Behavioral validity: four tests pin exact exit codes, event counts, outcome strings, and field values. Compatibility with task-30's `None`→`0` normalisation confirmed: no existing test pins the `None` return case (`run_fn` fixtures return explicit integers); no `is None` assertion exists against `record_dispatch`'s return value. No test task modifies this file.

**Finding 2 — pass.** Safe to lock.

### 1c. `test_capture_chokepoint_integration.py`

Behavioral validity: five tests with specific, exact assertions across subprocess-driven and direct paths. Compatible with task-30's normalisation (no `None` pinning).

**Finding 3 — blocking (resolved by lock-set narrowing, see addendum).** Task-17 (wave 3) must add the two single-writer guard tests to this file; task-29 (wave 4) depends on them for AC-12. Lock only after task-17 completes.

## Section 2 — Tier 1 mechanical checks on test tasks

Silent-failure detection: cleared — all 18 tasks specify concrete behavioral assertions; confirm-green tasks state the expected outcome explicitly with exact pinned values. Empty-gate tests: cleared. Advisory assertions: cleared — task-06's wall-clock companion is explicitly non-gating and is paired with a gating correctness assertion (`resolve_capture_level(root) == "standard"`).

## Section 3 — AC traceability

All test tasks trace to spec ACs (AC-01…AC-16, AC-19, AC-20, AC-21 covered across tasks 01-18). AC-17 and the AC-18 structural cleanups have no dedicated test task by design: the contract-preserving slice's gate is the pinned mypy baseline reaching zero plus existing tests staying green — a legitimate, spec-documented exception confirmed in the task manifest.

## Section 4 — Red-before-implementation discipline

All contract-evolving and new-contract tasks specify an explicit red run from a second worktree at the pre-fix commit (`40ec021`) with the failure mechanism stated (e.g. subagent count fails 0 ≠ 2; bounded read fails on correctness via the divergence fixture, not timing). The five expected-green-at-pre-fix corrections (task-07 contract-preserving guard, task-11 source-literal regression locks, task-12 test-fidelity corrections, task-16 source-parametrized redaction, task-14's boundary-stability companion) each state the exemption and rationale, consistent with AC-21's expected-green list.

**Finding 4 — overridden.** Task-04's two-phase pre-fix failure description (sanity count 4 ≠ 2 from duplicated gate writes first; stub-block failure after the single-writer fix lands) is an honest, documented description of a cross-slice seam guard, not a weak test.

## Section 5 — Catching power

Implementation-embedding: cleared for all new tasks (the one existing monkeypatch pattern in `test_write_runs_prune_check_after_append` is acknowledged as a constraint on task-25, not a new pattern). Assertion strength: all new tests pin exact values (exact counts, exact fractions, identity checks).

**Finding 5 — overridden.** Task-07's range assertion on surviving "other-spec" lines (≥ 1 and < 4001) is appropriately paired upper/lower bounding for a size-driven prune; the locked-spec count is exact (2000).

**Finding 6 — pass.** No mocking of owned code anywhere; the single third-party stand-in (the fake `uv` shim in task-05) is explicitly justified. Fixture arithmetic verified sound (2000 × ~1.1 KB ≈ 2.2 MB < 2.5 MB protected ceiling; ~6.6 MB total > 5 MB cap).

## Section 6 — No lock conflicts among test tasks

Multi-task test files are correctly wave-staggered: `test_report_arithmetic.py` (waves 1/2), `test_capture_event_writer.py` (waves 1/2/3), `test_report_rendering.py` (waves 1/2). The only conflicts were between tasks 07/17 and the originally proposed lock set — resolved by narrowing the set (addendum).

## Section 7 — Traceability of locked coverage

The retention tests protect the unchanged portion of the AC-07 contract (the lock-scope fix itself is task-07's new guard). The chokepoint tests protect the behavioral contract that must survive the AC-17 type fix. Sound on both.

---

## Lock-set determination (final)

**Locked now:**
- The 18 test task files (`task-01-…` through `task-18-…` in `ai-docs/hook-harvesting-remediation/hook-harvesting-remediation-tasks/`) — locking the compiled test instructions against quiet weakening during implementation.
- `assets/fbk-scripts/tests/test_capture_chokepoint.py` — the one pre-existing file cleared for locking.

**Deferred locks (implement-stage obligations):**
- `assets/fbk-scripts/tests/test_capture_retention.py` — lock immediately after task-07 lands its concurrency guard.
- `assets/fbk-scripts/tests/test_capture_chokepoint_integration.py` — lock immediately after task-17 lands the single-writer guards.

## Addendum — verdict on the narrowed lock set (2026-06-12)

The two blocking findings dissolve completely under the narrowed scope. Finding 1 raised that `test_capture_retention.py` cannot be pre-locked because task-07 must write to it — that file is now excluded from the lock set, so the conflict is gone. Finding 3 raised the same concern for `test_capture_chokepoint_integration.py` — likewise excluded. The one file cleared for locking, `test_capture_chokepoint.py`, has no test task touching it, its existing assertions are behaviorally sound, and the planned task-30 normalisation does not contradict any of them. The 18 test task files are documentation artifacts, not code under active modification by implementation agents, so locking them against quiet weakening is safe at this stage. No other findings were blocking.

accepted
