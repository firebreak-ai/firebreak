---
id: task-18
type: test
wave: 9
covers: [AC-21]
files_to_create:
  - ai-docs/hook-harvesting-remediation/hook-harvesting-remediation-tasks/completion-notes.md
completion_gate: "Full suite passes with zero failures at the post-fix tree, and completion-notes.md records a captured pre-fix run and post-fix passing run for every corrected test named below, with explicit expected-green annotations where the correction was test-fidelity-only."
---

## Objective

Run the full post-implementation verification: the whole suite green, and the red-then-green demonstration record complete for every corrected test.

## Context

This is the global verification criterion, last wave, after all test and implementation waves. The pre-fix reference is the feature-branch commit recorded at implementation start (`40ec021` on `fbk/hook-harvesting` at spec time) — NOT the review's merge-base `4437a6c`, which predates the capture package and fails on imports. The shared discipline: each red run executes from a second git worktree checked out at the recorded pre-fix commit with the corrected/new test file copied in, using the rebuilt or net-new test versions only (the original versions are the masked guards and stay green there by construction).

Three corrections are test-fidelity-only over already-correct production behavior; their pre-fix runs are EXPECTED GREEN and the notes must say so explicitly rather than fabricate a failure: the `schema.SOURCES`-driven redaction enumeration (AC-14, task-16), the merge-path/symlink installer test corrections (AC-19, task-12), and the net-new two-park boundary-stability test within AC-06 (task-14; the two AC-06 rebuilds carry the red).

## Instructions

1. Run the full suite from `/home/rahvin/context-assets/assets/fbk-scripts`: `python -m pytest tests/ -q` (use the project venv the suite normally runs under). Done when it exits with zero failures and zero errors; record the summary line in `completion-notes.md`.
2. Verify `completion-notes.md` (in this tasks directory; create or complete it by collating each slice's captured runs) contains, for EVERY entry below, (a) the pre-fix worktree run output and (b) the post-fix passing run, each labeled with test id, owning slice, and commit hashes:
   - AC-03 — `tests/test_report_arithmetic.py::test_subagent_count_excludes_unknown_identity` (rebuilt), `::test_subagent_count_is_exact_over_production_envelopes` (new): pre-fix FAIL (count 0).
   - AC-04 — `tests/test_capture_retro_injector.py::test_injects_block_under_metrics_heading` (extended), `tests/test_capture_e2e_seam.py::test_two_source_cycle_joins_in_one_report` (strengthened), `tests/test_capture_injection_seam.py::test_real_producer_cycle_injects_exact_metrics` (new): pre-fix FAIL (stub block, no metric lines).
   - AC-06 — `tests/test_report_arithmetic.py::test_attempt_after_ready_reentry_classifies_after_rework`, `::test_rework_derived_from_repeated_stage_entry` (rebuilt): pre-fix FAIL (stale-READY misclassification); `::test_two_parks_boundary_is_first_park` (new): expected-green annotation.
   - AC-08 — `tests/test_gates_code_review.py` projection tests and `tests/test_report_rendering.py::test_standard_level_renders_one_row_per_detection_round` (new): pre-fix FAIL; `tests/test_capture_event_writer.py::test_standard_level_strips_freetext_payload` (rebuilt): pre-fix FAIL (rounds stripped).
   - AC-10 — `tests/test_capture_gate_check.py::test_oversized_first_segment_resolves_safe_default` (rebuilt): pre-fix FAIL (`'full' != 'standard'`).
   - AC-14 — the `schema.SOURCES`-parametrized redaction tests (rebuilt/new): expected-green annotation with rationale.
   - AC-19 — `tests/test_install_migration.py::test_second_run_is_idempotent`, `::test_unrelated_hook_left_byte_intact` (rewritten) and `tests/test_capture_gate_check_hardening.py::test_symlinked_config_refused` (strengthened): expected-green annotation with rationale.
   Done when every entry has both runs (or the explicit expected-green record) — any missing entry is a gate failure; obtain the missing capture by re-running the worktree procedure for that test before passing.
3. Spot-check the worktree hygiene: the notes name the actual pre-fix commit hash used (the one recorded at implementation start; `40ec021` if unchanged) and state that the red runs used a separate worktree, not stashes. Done when stated.
4. Confirm `pytest --collect-only -q tests/` reports zero collection errors at the current tree; record the collected-test count in the notes.

## Files to create/modify

- `ai-docs/hook-harvesting-remediation/hook-harvesting-remediation-tasks/completion-notes.md` (modify/create — repo-relative path; this is the verification ledger, not a package test)

## Test requirements

- E2E (whole suite) — `python -m pytest tests/ -q` exits 0 with zero failures; collection is clean; the red/green ledger is complete for every corrected test listed above.

## Acceptance criteria

- AC-21: the full suite passes with zero failures after all fixes, and every corrected test in AC-03/04/06/08/10/14/19 has its pre-fix run and post-fix passing run captured in completion notes (with explicit expected-green records where the correction was test-fidelity-only).

## Model

Sonnet

## Wave

Wave 9
