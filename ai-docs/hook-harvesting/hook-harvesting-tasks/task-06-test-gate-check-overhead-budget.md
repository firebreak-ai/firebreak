---
id: task-06
type: test
wave: 2
covers: [AC-01]
files_to_create:
  - assets/fbk-scripts/tests/test_capture_gate_check_overhead.py
completion_gate: "tests compile and fail before implementation"
---

# Objective

Write the single overhead-budget test that gives the gate's no-ambient-overhead claim a falsifiable wall-clock threshold, marked non-gating so a slow CI run cannot fail the suite.

# Context

The capture gate runs on the hot path of every Claude tool call, so it must be cheap. `project_is_instrumented` on an uninstrumented project should complete well inside the PRD's "well under a second" budget — a generous upper bound such as 100ms is plenty of headroom. Wall-clock assertions flake on shared CI, so this test is quarantine-on-flake (non-gating): it is marked so a single slow run does not block the suite.

Import `from fbk.capture import gate_check` inside `try/except ImportError` with a module-level skipif. Use `tmp_path` for an uninstrumented project and the standard-library `time.perf_counter` for the measurement.

Signature called: `gate_check.project_is_instrumented(cwd) -> bool`.

# Instructions

1. Create `tests/test_capture_gate_check_overhead.py`; import `gate_check` inside `try/except ImportError`; module-level `pytestmark` combining the skipif with a non-gating marker. Use a custom marker `@pytest.mark.flaky_quarantine` (register it in the file via a `pytestmark` list or a `pytest.ini`-free local marker; if the suite has no marker registration, add the marker name to the test and document in a comment that it is advisory/non-gating). The key property: this test must not block the gate when it is the only failure.
2. `test_instrumented_check_is_cheap_on_bare_project`: build a bare `tmp_path` project (no markers); warm one call (to exclude import/first-touch cost), then time a single `project_is_instrumented(root)` call with `time.perf_counter`; assert the result is `False` (correctness) AND the elapsed time is under a generous bound (e.g. `elapsed < 0.1` seconds). Pair the timing upper bound with the correctness assertion so the test also verifies the gate answered correctly, not just quickly.
3. Add a comment at the test marking it explicitly as quarantine-on-flake / non-gating, so a reviewer and the implement-phase harness treat a lone timing failure as advisory.

# Files to create/modify

- `tests/test_capture_gate_check_overhead.py`

# Test requirements

- `test_instrumented_check_is_cheap_on_bare_project` (unit, non-gating): a bare-project instrumentation check returns `False` and completes under a generous wall-clock bound; marked quarantine-on-flake so a slow run is advisory, not blocking.

# Acceptance criteria

AC-01 (the no-ambient-overhead half of the per-project gate, given a falsifiable threshold). Gate: test compiles and fails before implementation (skips on absent module). Note: once implemented, this test's *timing* assertion is non-gating; the suite gate rests on the correctness assertion and the other foundation tasks.

# Model

Haiku — single bounded timing test.

# Wave

2
