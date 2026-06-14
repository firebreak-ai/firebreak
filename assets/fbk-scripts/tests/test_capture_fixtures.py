"""Self-check tests for the capture_fixtures helper module.

These tests validate the fixtures themselves — they own no production
dependency, so they pass in the red phase before any metrics-plane
implementation exists.
"""

import os
import pytest
from tests import capture_fixtures


_ENVELOPE_FIELDS = {
    "schema_version",
    "event_type",
    "timestamp",
    "spec",
    "stage",
    "source",
    "capture_level",
    "data",
}


def test_event_builder_yields_full_envelope():
    """build_event returns a dict whose key set equals the eight envelope field names."""
    ev = capture_fixtures.build_event(
        event_type="LIFECYCLE",
        source="test-source",
        spec="my-spec",
        stage="QUEUED",
    )
    assert set(ev.keys()) == _ENVELOPE_FIELDS


def test_make_project_writes_sentinel_only_when_marked(tmp_path):
    """sentinel exists only under marked=True; it is absent under marked=False."""
    root_unmarked = capture_fixtures.make_project(str(tmp_path / "a"), instrumented=True, marked=False)
    sentinel_unmarked = os.path.join(root_unmarked, ".claude", "automation", ".fbk-managed")
    assert not os.path.exists(sentinel_unmarked)

    root_marked = capture_fixtures.make_project(str(tmp_path / "b"), instrumented=True, marked=True)
    sentinel_marked = os.path.join(root_marked, ".claude", "automation", ".fbk-managed")
    assert os.path.exists(sentinel_marked)
