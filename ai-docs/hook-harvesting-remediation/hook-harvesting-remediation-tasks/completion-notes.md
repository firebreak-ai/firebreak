# Task-18 completion notes — final verification ledger

**Wave:** 9  
**Date:** 2026-06-12  
**Pre-fix commit:** `40ec021` (feature-branch `fbk/hook-harvesting` tip at implementation start)  
**Post-fix tree:** `fbk/hook-harvesting` HEAD (after all waves)  
**Red-run discipline:** second git worktree at `40ec021` (`git worktree add /tmp/fbk-redrun-task-18 40ec021`); corrected/new test files copied in from the post-fix tree; runs executed with the main repo's venv (`/home/rahvin/context-assets/assets/fbk-scripts/venv/bin/pytest`); worktree removed after capture.

---

## Full-suite result

**Command:** `cd assets/fbk-scripts && venv/bin/pytest tests/ -q`  
**Result:** `401 passed in 3.45s` — zero failures, zero errors.

**Collection check:** `venv/bin/pytest --collect-only -q tests/` — `401 tests collected in 0.08s` — zero collection errors.

---

## Per-slice red/green ledger

### AC-03 — subagent count reads identity field, not envelope source

**Tests:**
- `tests/test_report_arithmetic.py::test_subagent_count_excludes_unknown_identity` (rebuilt)
- `tests/test_report_arithmetic.py::test_subagent_count_is_exact_over_production_envelopes` (new)

**Pre-fix run at `40ec021` (worktree):** FAIL — both fail `0 != expected` because the pre-fix `count_known_subagents` reads `ev.get("source") or ev.get("data", {}).get("agent_type")`; the production envelope's truthy `source="hook_router"` always wins, the identity fallback never fires, and the count is always 0.

```
FAILED tests/test_report_arithmetic.py::test_subagent_count_excludes_unknown_identity
AssertionError: expected count 1 (only the scanned probe identity is known), got 0
FAILED tests/test_report_arithmetic.py::test_subagent_count_is_exact_over_production_envelopes
AssertionError: expected exactly 2 known-agent events (probe-a and probe-b), got 0
2 failed in 0.03s
```

**Post-fix run at HEAD:** PASSED — `2 passed`.

---

### AC-04 — stage_summary renders real metric lines (not the stub's heading-only output)

**Tests:**
- `tests/test_capture_retro_injector.py::test_injects_block_under_metrics_heading` (extended)
- `tests/test_capture_e2e_seam.py::test_two_source_cycle_joins_in_one_report` (strengthened)
- `tests/test_capture_injection_seam.py::test_real_producer_cycle_injects_exact_metrics` (new)

**Pre-fix run at `40ec021` (worktree):** FAIL — the stub `stage_summary` emits only the heading marker and stage/spec labels; none of the metric lines (`first-try rate:`, `after-rework rate:`, `parks:`, `rework:`) are present; the sanity pin on `test_real_producer_cycle_injects_exact_metrics` sees 4 spec-gate events (each dispatch writes a gate-own duplicate) instead of the expected 2.

```
FAILED tests/test_capture_retro_injector.py::test_injects_block_under_metrics_heading
AssertionError: exact line 'first-try rate: 0.50' not found in retrospective
FAILED tests/test_capture_e2e_seam.py::test_two_source_cycle_joins_in_one_report
AssertionError: expected exactly 2 spec-gate PIPELINE_COMMAND events, got 4; ...
FAILED tests/test_capture_injection_seam.py::test_real_producer_cycle_injects_exact_metrics
AssertionError: expected exactly 2 spec-gate PIPELINE_COMMAND events, got 4; ...
3 failed in 0.37s
```

**Post-fix run at HEAD:** PASSED — `3 passed`.

---

### AC-06 — after-rework boundary derived from first park in error_history

**Tests:**
- `tests/test_report_arithmetic.py::test_attempt_after_ready_reentry_classifies_after_rework` (rebuilt)
- `tests/test_report_arithmetic.py::test_rework_derived_from_repeated_stage_entry` (rebuilt)
- `tests/test_report_arithmetic.py::test_two_parks_boundary_is_first_park` (new) — **expected-green** (see annotation)

**Pre-fix run at `40ec021` (worktree):** Two rebuilds FAIL, new test PASSES.

- Both rebuilt tests fail `['after_rework', 'after_rework'] != ['first_try', 'after_rework']` — pre-fix `classify_gate_attempts` reads `stage_timestamps['READY']` (stale T2 from another stage's earlier re-entry) as the boundary; T4 >= READY(T2) misclassifies T4 as `after_rework`.
- `test_two_parks_boundary_is_first_park` passes at pre-fix because both parks yield `['first_try', 'after_rework', 'after_rework']` under either implementation — the fixture's two consecutive parks on the same stage do not expose the stale-READY bug.

```
FAILED tests/test_report_arithmetic.py::test_attempt_after_ready_reentry_classifies_after_rework
AssertionError: expected phases ['first_try', 'after_rework'] but got ['after_rework', 'after_rework']
FAILED tests/test_report_arithmetic.py::test_rework_derived_from_repeated_stage_entry
AssertionError: expected phases ['first_try', 'after_rework'] but got ['after_rework', 'after_rework']
PASSED tests/test_report_arithmetic.py::test_two_parks_boundary_is_first_park
2 failed, 1 passed in 0.02s
```

**Expected-green annotation for `test_two_parks_boundary_is_first_park`:** This test guards the two-park boundary stability — phases `['first_try', 'after_rework', 'after_rework']` for a stage parked twice — not the stale-READY misclassification. With no second stage involved, both the pre-fix `stage_timestamps['READY']` read and the post-fix first-park read agree on the same boundary (IMPLEMENTING's own first park), so the test passes on both. This is a test-fidelity correction that adds coverage for a distinct scenario; it is not a fabricated failure.

**Post-fix run at HEAD:** PASSED — `3 passed`.

---

### AC-08 — per-round detail survives redaction; one rendered row per round

**Tests:**
- `tests/test_gates_code_review.py::TestProjectRoundEntries` (projection tests) — skip at pre-fix (expected)
- `tests/test_gates_code_review.py::TestRoundLogProjectedBeforeEventWrite` (integration) — skip at pre-fix (expected)
- `tests/test_report_rendering.py::test_standard_level_renders_one_row_per_detection_round` (new)
- `tests/test_capture_event_writer.py::test_standard_level_strips_freetext_payload` (rebuilt)

**Pre-fix run at `40ec021` (worktree):** Rendering and event-writer tests FAIL; projection tests skip cleanly.

- `test_standard_level_renders_one_row_per_detection_round`: fails `1 != 2` — the renderer collapses both rounds into a single totals row instead of one row per entry.
- `test_standard_level_strips_freetext_payload`: fails because `'rounds'` is in `FREETEXT_KEYS`, so the entire rounds list is stripped (`data.get('rounds')` is `None`).
- `TestProjectRoundEntries` and `TestRoundLogProjectedBeforeEventWrite`: skip cleanly (both guarded by `pytest.importorskip`/`skipif` on the absence of `project_round_entries`/`ROUND_SEVERITIES`).

```
FAILED tests/test_report_rendering.py::test_standard_level_renders_one_row_per_detection_round
AssertionError: Expected exactly 2 detection-round lines (one per entry), got 1
FAILED tests/test_capture_event_writer.py::test_standard_level_strips_freetext_payload
AssertionError: expected rounds to survive with nested free-text stripped, but data['rounds'] was: None
SKIPPED tests/test_gates_code_review.py::TestProjectRoundEntries::test_project_round_entries_allowlists_exactly_three_keys
SKIPPED tests/test_gates_code_review.py::TestRoundLogProjectedBeforeEventWrite::test_round_log_projected_before_event_write
2 failed, 2 skipped in 0.08s
```

**Post-fix run at HEAD:** PASSED — all 4 pass (projection tests unskipped, rendering and event-writer tests green).

---

### AC-10 — bounded config read falls back to safe default for oversized first segment

**Test:**
- `tests/test_capture_gate_check.py::TestResolveCaptureLevel::test_oversized_first_segment_resolves_safe_default` (rebuilt)

**Pre-fix run at `40ec021` (worktree):** FAIL — the pre-fix unbounded `readline()` reads the full line, finds `capture_level=full`, and returns `'full'`; the bounded implementation returns `'standard'`. Assertion `'full' != 'standard'`.

```
FAILED tests/test_capture_gate_check.py::TestResolveCaptureLevel::test_oversized_first_segment_resolves_safe_default
AssertionError: assert 'full' == 'standard'
1 failed in 0.02s
```

**Post-fix run at HEAD:** PASSED — `1 passed`.

---

### AC-14 — schema.SOURCES-parametrized redaction enumeration

**Tests:**
- `tests/test_capture_event_writer.py::test_full_level_preserves_payload[hook_router/chokepoint/task_completed/code_review]` (rebuilt, parametrized over all 4 sources)
- `tests/test_capture_event_writer.py::test_standard_level_strips_freetext_for_every_registered_source[hook_router/chokepoint/task_completed/code_review]` (new, parametrized)

**Pre-fix run at `40ec021` (worktree):** EXPECTED GREEN — all 8 parametrized tests pass.

**Expected-green annotation:** Production `redact()` was already correct for all registered sources before this remediation; the defect was single-source coverage (tests ran only against one source). The test correction drives the enumeration dynamically from `schema.SOURCES` so future source additions are automatically covered. This is a test-fidelity correction over already-correct production behavior; no fabricated failure applies.

```
8 passed in 0.01s
```

**Post-fix run at HEAD:** PASSED — `8 passed` (same; the tests remain green).

---

### AC-19 — installer migration tests rewritten to production merge path; symlinked-config test strengthened

**Tests:**
- `tests/test_install_migration.py::TestSecondRunIsIdempotent::test_second_run_is_idempotent` (rewritten)
- `tests/test_install_migration.py::TestUnrelatedHookLeftByteIntact::test_unrelated_hook_left_byte_intact` (rewritten)
- `tests/test_capture_gate_check_hardening.py::test_symlinked_config_refused` (strengthened)

**Pre-fix run at `40ec021` (worktree):** EXPECTED GREEN — all 3 tests pass.

**Expected-green annotation:** `merge_settings` already strips leftover project-router entries internally; the test corrections remove a spurious `remove_hook_command` call that was bolted on top of merge and never tested the production path. The symlinked-config test correction adds a `project_is_instrumented is False` assertion that was missing from the original. Both are test-fidelity corrections over already-correct production code; the pre-fix tree runs them correctly because the production behavior is unchanged.

```
3 passed in 0.02s
```

**Post-fix run at HEAD:** PASSED — `3 passed`.

---

## Worktree hygiene

- Pre-fix commit used: `40ec021` (the feature-branch tip recorded at implementation start, not the import-failing merge-base `4437a6c`).
- All red runs executed from a separate git worktree (`/tmp/fbk-redrun-task-18`) checked out at `40ec021`, using the main repo's venv. No stashes were used.
- Worktree removed after capture: `git worktree remove --force /tmp/fbk-redrun-task-18`.

---

## Gate result

**Full suite:** 401 passed, 0 failed, 0 errors — PASS.  
**Collection:** 401 tests collected, 0 collection errors — PASS.  
**Red/green ledger:** complete for all AC-03, AC-04, AC-06, AC-08, AC-10, AC-14, AC-19 entries, with explicit expected-green annotations for AC-06 (`test_two_parks_boundary_is_first_park`), AC-14 (schema.SOURCES parametrization), and AC-19 (merge-path and symlink corrections).

**AC-21 acceptance criterion: MET.**
