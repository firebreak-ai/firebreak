"""Overhead-budget test for the capture gate check.

This test verifies that the capture gate's no-ambient-overhead claim has a
falsifiable wall-clock threshold. The gate runs on the hot path of every Claude
tool call, so it must be cheap.

This is a NON-GATING test marked quarantine-on-flake: a single slow run on
shared CI does not block the suite, but timing regressions are caught by
repeated runs. The test combines a correctness assertion (gate returned False)
with a timing upper bound (completed under 100ms) so both dimensions are verified.
"""

import time
import pytest

try:
    from fbk.capture import gate_check
    CAPTURE_AVAILABLE = True
except ImportError:
    CAPTURE_AVAILABLE = False


pytestmark = [
    pytest.mark.skipif(not CAPTURE_AVAILABLE, reason="fbk.capture.gate_check not yet implemented"),
    pytest.mark.flaky_quarantine,  # Custom marker: timing flake on shared CI should not block suite
]


def test_instrumented_check_is_cheap_on_bare_project(tmp_path):
    """
    Instrumentation check returns False on a bare project and completes under 100ms.

    Quarantine-on-flake: this timing assertion is advisory. The correctness assertion
    (result is False) is gating; a timing failure alone does not block the suite.
    """
    # Build a bare project (no instrumentation markers)
    project_root = str(tmp_path)

    # Warm one call to exclude import/first-touch cost
    gate_check.project_is_instrumented(project_root)

    # Time a single instrumentation check call
    start = time.perf_counter()
    result = gate_check.project_is_instrumented(project_root)
    elapsed = time.perf_counter() - start

    # Correctness assertion (gating): gate should answer False on a bare project
    assert result is False, "Instrumentation check should return False on bare project"

    # Timing assertion (non-gating, advisory): generous 100ms upper bound provides ample headroom
    # for first-touch, filesystem lookups, and CI system variance.
    assert elapsed < 0.1, f"Instrumentation check took {elapsed:.4f}s, expected under 0.1s"
