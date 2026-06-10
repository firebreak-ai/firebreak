"""Tests for fbk.capture.schema — event-envelope vocabulary, drift checks, and redaction."""

import os
import tempfile
import pytest

try:
    from fbk.capture import schema
except ImportError:
    schema = None

from tests import capture_fixtures


pytestmark = pytest.mark.skipif(
    schema is None,
    reason="fbk.capture.schema not yet implemented",
)


# ---------------------------------------------------------------------------
# Vocabulary guard tests
# ---------------------------------------------------------------------------


def test_vocabulary_is_exactly_the_six_known_types():
    """EVENT_TYPES exports the exact six-member vocabulary."""
    assert set(schema.EVENT_TYPES) == {
        "PIPELINE_COMMAND",
        "VERIFICATION_RESULT",
        "CODE_REVIEW_ROUNDS",
        "TOOL_USE",
        "SUBAGENT_STOP",
        "LIFECYCLE",
    }
    assert len(set(schema.EVENT_TYPES)) == 6


def test_known_event_type_is_recognized():
    """A vocabulary member is present in EVENT_TYPES."""
    assert "TOOL_USE" in schema.EVENT_TYPES


def test_unknown_event_type_is_rejected():
    """A foreign event type is absent from EVENT_TYPES."""
    assert "MADE_UP" not in schema.EVENT_TYPES


# ---------------------------------------------------------------------------
# Drift check tests
# ---------------------------------------------------------------------------


def test_drift_check_passes_on_canonical_sources(tmp_path):
    """check_drift returns empty list when scanning shipped fbk.capture source."""
    capture_pkg_root = os.path.join(
        os.path.dirname(__file__),
        "..",
        "fbk",
        "capture",
    )
    # Only run if the module exists; otherwise skip (red phase).
    if not os.path.isdir(capture_pkg_root):
        pytest.skip("fbk.capture package not yet created")

    result = schema.check_drift(capture_pkg_root)
    assert isinstance(result, list)
    assert result == []


def test_drift_check_flags_a_foreign_event_type(tmp_path):
    """check_drift returns non-empty list containing flagged event type."""
    # Write a .py file that references a foreign event type as a string literal.
    fixture_file = tmp_path / "foreign_events.py"
    fixture_file.write_text(
        'event_type = "GHOST_EVENT"\n'
        'another = "LEGITIMATE_EVENT"\n'
    )

    result = schema.check_drift(str(tmp_path))
    assert isinstance(result, list)
    assert len(result) > 0
    assert "GHOST_EVENT" in result


# ---------------------------------------------------------------------------
# Redaction tests
# ---------------------------------------------------------------------------


def test_redact_strips_freetext_at_standard():
    """schema.redact("standard") removes free-text payload fields."""
    data = {
        "tool_input": {"command": "rm -rf /"},
        "prompt_text": "secret instructions",
        "files": ["a.py", "b.py"],
        "count": 3,
    }

    result = schema.redact(data, "standard")

    # Free-text payload keys must be absent or emptied.
    assert "tool_input" not in result
    assert "prompt_text" not in result

    # Structural/numeric fields survive.
    assert result.get("count") == 3
    # files is free-text list; it must be absent at standard.
    assert "files" not in result


def test_redact_preserves_payload_at_full():
    """schema.redact("full") returns payload unchanged."""
    data = {
        "tool_input": {"command": "rm -rf /"},
        "prompt_text": "secret instructions",
        "files": ["a.py", "b.py"],
        "count": 3,
    }

    result = schema.redact(data, "full")

    # All fields present and equal to input.
    assert result == data
    assert result["tool_input"] == {"command": "rm -rf /"}
    assert result["prompt_text"] == "secret instructions"
    assert result["files"] == ["a.py", "b.py"]
    assert result["count"] == 3


def test_redact_off_level_strips_like_standard_or_stricter():
    """schema.redact("off") carries no free-text payload."""
    data = {
        "tool_input": {"command": "rm -rf /"},
        "prompt_text": "secret instructions",
        "files": ["a.py", "b.py"],
        "count": 3,
    }

    result = schema.redact(data, "off")

    # Off-level is at least as strict as standard: no free-text payloads.
    assert "tool_input" not in result
    assert "prompt_text" not in result
    assert "files" not in result
