"""End-to-end injection-seam guard: real producers → writer → injector → retrospective.

This module drives the full producer chain end-to-end — real fbk.py subprocess calls
through the dispatch chokepoint into the event writer, then through the retro injector
into the retrospective file — and asserts that the injected block carries the exact
computed metric lines for the stage.

This guard goes green only once the injection-render, gate-rate, and rework-boundary
fixes have all landed. It is the cross-slice seam guard, red at the pre-fix commit
by construction.
"""

import json
import os

import pytest

# ---------------------------------------------------------------------------
# Capture-availability skip guard — skip the whole module when the capture
# subsystem is absent (mirrors the pattern in test_capture_e2e_seam.py).
# ---------------------------------------------------------------------------

try:
    from fbk.capture import event_writer  # noqa: F401
    _CAPTURE_AVAILABLE = True
except ImportError:
    _CAPTURE_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _CAPTURE_AVAILABLE,
    reason="fbk.capture not yet implemented",
)

from tests import capture_fixtures  # noqa: E402 — after guard


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


def test_real_producer_cycle_injects_exact_metrics(tmp_path):
    """Real producer cycle writes exact gate-rate, parks, and rework lines to the retro.

    Drives fbk.py through a gate-fail → park → recover → complete cycle via the
    real dispatch chokepoint, then asserts:

    - exactly 2 PIPELINE_COMMAND events with command_name "spec-gate":
        one with outcome "fail" (the broken spec), one with outcome "pass"
        (the valid spec), both attributed to stage VALIDATING
    - exactly 1 VERIFICATION_RESULT with tests_passed True, attributed to
        stage VALIDATING
    - the VALIDATING stage completes (VALIDATING → VALIDATED), firing the
        real retro injector from the real state engine
    - the retrospective file contains the exact injected metric lines:
        first-try rate: 0.50, after-rework rate: 1.00, parks: 1, rework: 1

    Hand derivation (stated for review):
        first-try attempts  = verification pass + spec-gate fail (both before the park)
                            → 1 pass out of 2 total = 0.50
        after-rework rate   = spec-gate pass (after the park) → 1/1 = 1.00
        parks               = 1  (one PARKED transition)
        rework              = 1  (one re-entry: READY → VALIDATING)
    """
    project = capture_fixtures.make_project(str(tmp_path), instrumented=True, marked=True)
    state_dir = os.path.join(project, ".claude", "automation", "state")

    # Drive the gate-fail → park → recover cycle via real producers.
    events = capture_fixtures.drive_gate_fail_park_recover(project, state_dir, "demo-spec")

    # --- Sanity: producer events must be correctly attributed before completing ---

    spec_gate_events = [
        e for e in events
        if e.get("event_type") == "PIPELINE_COMMAND"
        and e.get("data", {}).get("command_name") == "spec-gate"
    ]
    assert len(spec_gate_events) == 2, (
        f"expected exactly 2 spec-gate PIPELINE_COMMAND events, "
        f"got {len(spec_gate_events)}; all events: {events!r}"
    )

    spec_gate_fail_events = [
        e for e in spec_gate_events if e.get("data", {}).get("outcome") == "fail"
    ]
    assert len(spec_gate_fail_events) == 1, (
        f"expected exactly 1 spec-gate fail event, "
        f"got {len(spec_gate_fail_events)}; spec_gate_events: {spec_gate_events!r}"
    )
    assert spec_gate_fail_events[0].get("stage") == "VALIDATING", (
        f"spec-gate fail event should carry stage VALIDATING, "
        f"got {spec_gate_fail_events[0].get('stage')!r}"
    )

    spec_gate_pass_events = [
        e for e in spec_gate_events if e.get("data", {}).get("outcome") == "pass"
    ]
    assert len(spec_gate_pass_events) == 1, (
        f"expected exactly 1 spec-gate pass event, "
        f"got {len(spec_gate_pass_events)}; spec_gate_events: {spec_gate_events!r}"
    )
    assert spec_gate_pass_events[0].get("stage") == "VALIDATING", (
        f"spec-gate pass event should carry stage VALIDATING, "
        f"got {spec_gate_pass_events[0].get('stage')!r}"
    )

    verification_events = [
        e for e in events
        if e.get("event_type") == "VERIFICATION_RESULT"
        and e.get("data", {}).get("tests_passed") is True
    ]
    assert len(verification_events) == 1, (
        f"expected exactly 1 passing VERIFICATION_RESULT event, "
        f"got {len(verification_events)}; all events: {events!r}"
    )
    assert verification_events[0].get("stage") == "VALIDATING", (
        f"VERIFICATION_RESULT event should carry stage VALIDATING, "
        f"got {verification_events[0].get('stage')!r}"
    )

    # --- Complete the stage via the production path; this fires the injector ---
    result = capture_fixtures.run_fbk(
        ["state", "transition", "demo-spec", "VALIDATED"],
        project,
        state_dir,
    )
    assert result.returncode == 0, (
        f"transition to VALIDATED failed (rc {result.returncode}): {result.stderr!r}"
    )

    # --- Assert the injected block carries exact metric lines ---
    retro_path = os.path.join(project, "ai-docs", "demo-spec", "demo-spec-retrospective.md")
    assert os.path.exists(retro_path), (
        f"expected retrospective file at {retro_path!r} after VALIDATED transition"
    )

    with open(retro_path, encoding="utf-8") as fh:
        retro_content = fh.read()

    assert "## VALIDATING — metrics" in retro_content, (
        f"expected '## VALIDATING — metrics' heading in retrospective; "
        f"content={retro_content!r}"
    )

    marker_prefix = "<!-- fbk-metrics stage=VALIDATING spec=demo-spec generated="
    assert marker_prefix in retro_content, (
        f"expected provenance marker starting with {marker_prefix!r} "
        f"in retrospective; content={retro_content!r}"
    )

    assert "first-try rate: 0.50" in retro_content, (
        f"expected 'first-try rate: 0.50' in retrospective; content={retro_content!r}"
    )
    assert "after-rework rate: 1.00" in retro_content, (
        f"expected 'after-rework rate: 1.00' in retrospective; content={retro_content!r}"
    )
    assert "parks: 1" in retro_content, (
        f"expected 'parks: 1' in retrospective; content={retro_content!r}"
    )
    assert "rework: 1" in retro_content, (
        f"expected 'rework: 1' in retrospective; content={retro_content!r}"
    )
