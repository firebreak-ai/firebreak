"""Tests for fbk.capture.retro_injector — per-stage retrospective block injection.

Tests cover:
- A metrics block appended under a distinct "## <STAGE> — metrics" heading with a
  structurally-matched provenance marker.
- Existing plain "## <STAGE>" prose sections preserved; metrics block coexists.
- Two injections (simulating rework) produce two marked blocks.
- An internal failure is swallowed; inject_stage_metrics returns None and never raises.
"""

import os
import pytest

try:
    from fbk.capture import retro_injector
    RETRO_INJECTOR_AVAILABLE = True
except ImportError:
    RETRO_INJECTOR_AVAILABLE = False

from fbk import retro
from tests import capture_fixtures

pytestmark = pytest.mark.skipif(
    not RETRO_INJECTOR_AVAILABLE,
    reason="fbk.capture.retro_injector module not yet implemented",
)


# ---------------------------------------------------------------------------
# Shared project setup
# ---------------------------------------------------------------------------

_STATE_DIR_DEFAULT = ".claude/automation/state"


def _setup_project(tmp_path, spec, stage, monkeypatch):
    """Lay down the minimal project fixtures the injector reads.

    Writes events at <tmp_path>/.fbk-capture/events.jsonl and state at
    <tmp_path>/<STATE_DIR>/<spec>.json; changes cwd to tmp_path.

    Events: three VERIFICATION_RESULT events with production payload shape:
      - fail at 2026-01-01T00:01:00  (first-try, before the 00:02 park)
      - pass at 2026-01-01T00:01:30  (first-try, before the 00:02 park)
      - pass at 2026-01-01T00:03:00  (after-rework, after READY at 00:02:30)

    Hand-derived expectations:
      first-try attempts: fail + pass (both < 00:02) → rate = 1/2 = 0.50
      after-rework attempts: one pass (>= READY 00:02:30) → rate = 1.0
      parks: 1 (one entry in error_history for stage)
      rework: 1 (one error_history entry for stage)
    """
    monkeypatch.chdir(tmp_path)
    # Ensure _load_state uses the default path relative to cwd, not any ambient STATE_DIR.
    monkeypatch.delenv("STATE_DIR", raising=False)

    events_path = os.path.join(str(tmp_path), ".fbk-capture", "events.jsonl")
    events = [
        capture_fixtures.build_event(
            event_type="VERIFICATION_RESULT",
            source="task_completed",
            spec=spec,
            stage=stage,
            timestamp="2026-01-01T00:01:00+00:00",
            data={"failing_test_count": 1, "lint_error_count": 0, "out_of_scope_files": [], "tests_passed": False},
        ),
        capture_fixtures.build_event(
            event_type="VERIFICATION_RESULT",
            source="task_completed",
            spec=spec,
            stage=stage,
            timestamp="2026-01-01T00:01:30+00:00",
            data={"failing_test_count": 0, "lint_error_count": 0, "out_of_scope_files": [], "tests_passed": True},
        ),
        capture_fixtures.build_event(
            event_type="VERIFICATION_RESULT",
            source="task_completed",
            spec=spec,
            stage=stage,
            timestamp="2026-01-01T00:03:00+00:00",
            data={"failing_test_count": 0, "lint_error_count": 0, "out_of_scope_files": [], "tests_passed": True},
        ),
    ]
    capture_fixtures.write_events(events_path, events)

    # State with one park (PARKED at 00:02) and re-entry (READY at 00:02:30).
    state = capture_fixtures.build_state(
        spec=spec,
        stage_timestamps={
            stage: "2026-01-01T00:00:00+00:00",
            "PARKED": "2026-01-01T00:02:00+00:00",
            "READY": "2026-01-01T00:02:30+00:00",
        },
        current_state=stage,
        error_history=[
            {"stage": stage, "error": "gate failed", "timestamp": "2026-01-01T00:02:00+00:00"}
        ],
    )
    state_dir = os.path.join(str(tmp_path), _STATE_DIR_DEFAULT)
    capture_fixtures.write_state(state_dir, state)


def _retro_path(tmp_path, spec):
    """Return the path where the injector should write the retrospective file."""
    return os.path.join(str(tmp_path), "ai-docs", spec, f"{spec}-retrospective.md")


def _marker_prefix(stage, spec):
    """Return the fixed prefix portion of a provenance marker line."""
    return f"<!-- fbk-metrics stage={stage} spec={spec} generated="


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_injects_block_under_metrics_heading(tmp_path, monkeypatch):
    """inject_stage_metrics writes a metrics block under '## <STAGE> — metrics'.

    The file must contain the heading and a provenance marker whose fixed prefix
    and suffix are correct; the generated= timestamp field is non-empty but not
    matched exactly.
    """
    spec = "demo-spec"
    stage = "IMPLEMENTING"
    _setup_project(tmp_path, spec, stage, monkeypatch)

    retro_injector.inject_stage_metrics(spec, stage)

    retro_file = _retro_path(tmp_path, spec)
    assert os.path.exists(retro_file), "retrospective file was not created"
    text = open(retro_file, encoding="utf-8").read()

    assert f"## {stage} — metrics" in text, "metrics heading absent"

    # Match the marker by structure: correct prefix, non-empty generated= value, ends with ' -->'.
    prefix = _marker_prefix(stage, spec)
    marker_lines = [
        line for line in text.splitlines()
        if line.startswith(prefix) and line.endswith(" -->")
    ]
    assert len(marker_lines) >= 1, (
        f"no structurally-valid provenance marker found; expected a line starting with "
        f"'{prefix}' and ending with ' -->'"
    )
    # The generated= value between prefix and ' -->' must not be empty.
    sample = marker_lines[0]
    generated_value = sample[len(prefix): -len(" -->")]
    assert generated_value, "generated= field is empty in provenance marker"

    # Assert exact metric lines are present in the file (the stub emits none of
    # these; their absence is the test's failing condition against the stub).
    file_lines = text.splitlines()
    assert "first-try rate: 0.50" in file_lines, (
        "exact line 'first-try rate: 0.50' not found in retrospective"
    )
    assert "after-rework rate: 1.00" in file_lines, (
        "exact line 'after-rework rate: 1.00' not found in retrospective"
    )
    assert "parks: 1" in file_lines, (
        "exact line 'parks: 1' not found in retrospective"
    )
    assert "rework: 1" in file_lines, (
        "exact line 'rework: 1' not found in retrospective"
    )


def test_does_not_disturb_existing_prose_section(tmp_path, monkeypatch):
    """Existing plain '## <STAGE>' prose section is byte-intact after injection.

    The prose section and the metrics block coexist in the file; the metrics
    block appears after the prose section.
    """
    spec = "demo-spec"
    stage = "IMPLEMENTING"
    _setup_project(tmp_path, spec, stage, monkeypatch)

    # Pre-create the retrospective with a plain prose section.
    retro_file = _retro_path(tmp_path, spec)
    os.makedirs(os.path.dirname(retro_file), exist_ok=True)
    prose_content = "Agent wrote prose here."
    retro.append_section(retro_file, stage, prose_content)
    original_text = open(retro_file, encoding="utf-8").read()

    retro_injector.inject_stage_metrics(spec, stage)

    text = open(retro_file, encoding="utf-8").read()

    # Original plain heading and prose must still be present.
    assert f"## {stage}\n" in text, "original plain prose heading was removed"
    assert prose_content in text, "original prose content was removed"

    # The metrics heading must also be present.
    assert f"## {stage} — metrics" in text, "metrics heading absent"

    # Metrics block appears after the prose section.
    prose_pos = text.find(prose_content)
    metrics_pos = text.find(f"## {stage} — metrics")
    assert metrics_pos > prose_pos, "metrics block appeared before existing prose section"


def test_rework_produces_two_marked_blocks(tmp_path, monkeypatch):
    """Two calls to inject_stage_metrics produce two separate marked metrics blocks.

    The load-bearing assertion is that the file contains two provenance-marker
    lines for the given stage/spec. When the injector guarantees distinct
    timestamps, the markers should also differ.
    """
    spec = "demo-spec"
    stage = "IMPLEMENTING"
    _setup_project(tmp_path, spec, stage, monkeypatch)

    retro_injector.inject_stage_metrics(spec, stage)
    retro_injector.inject_stage_metrics(spec, stage)

    retro_file = _retro_path(tmp_path, spec)
    assert os.path.exists(retro_file), "retrospective file was not created"
    text = open(retro_file, encoding="utf-8").read()

    prefix = _marker_prefix(stage, spec)
    marker_lines = [
        line for line in text.splitlines()
        if line.startswith(prefix) and line.endswith(" -->")
    ]
    # The load-bearing assertion: two distinct blocks.
    assert len(marker_lines) == 2, (
        f"expected 2 provenance-marker lines after two injections, found {len(marker_lines)}"
    )


def test_injector_exception_is_swallowed(tmp_path, monkeypatch):
    """An internal failure inside inject_stage_metrics returns None and never raises.

    Force a failure by monkeypatching retro.append_section to raise, then
    confirm the call completes normally.
    """
    spec = "demo-spec"
    stage = "IMPLEMENTING"
    _setup_project(tmp_path, spec, stage, monkeypatch)

    monkeypatch.setattr(retro, "append_section", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("forced failure")))

    # Must not raise; must return None.
    result = retro_injector.inject_stage_metrics(spec, stage)
    assert result is None
