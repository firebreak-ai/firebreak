"""Unit tests for pipeline.normalize — researcher framing strip and location fold.

Tests cover:
- normalize() returns exactly the six allowlisted handoff fields and no others
- Every researcher framing field (title, detection_source, origin, pattern,
  remediation, reasoning, location) is absent from the result
- The structured location object does not survive as a standalone key; its
  locator (file and start_line) is folded into the evidence string
- Allowlisted values (type, severity, mechanism, consequence,
  source_of_truth_ref) pass through unchanged from the input finding
"""

import pytest

# Red phase: normalize does not exist yet.
try:
    from fbk.pipeline import normalize
    NORMALIZE_AVAILABLE = True
except ImportError:
    NORMALIZE_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not NORMALIZE_AVAILABLE,
    reason="pipeline.normalize not yet implemented",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def researcher_finding():
    """One researcher candidate carrying all six allowlisted fields plus every
    framing field that normalize() must strip."""
    return {
        # Allowlisted handoff fields
        "mechanism": "Token is written to a world-readable temp file before use.",
        "consequence": "Any local process can read the token and impersonate the user.",
        "evidence": "auth.py:42 — open('/tmp/token', 'w') called without umask restriction.",
        "type": "behavioral",
        "severity": "critical",
        "source_of_truth_ref": "docs/auth-design.md#token-storage",
        # Framing fields that must be stripped
        "title": "World-readable temp file exposes auth token",
        "detection_source": "intent",
        "origin": "researcher",
        "pattern": "insecure-temp-file",
        "remediation": "Write token to a mode-0600 file under a per-user directory.",
        "reasoning": "The umask was not set before the open() call.",
        # Structured location that must fold into evidence, not survive standalone
        "location": {"file": "auth.py", "start_line": 42},
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_returns_exactly_six_fields(researcher_finding):
    """normalize() returns a dict with exactly the six allowlisted keys."""
    result = normalize(researcher_finding)
    expected_keys = {"mechanism", "consequence", "evidence", "type", "severity", "source_of_truth_ref"}
    # Upper bound: no extra keys
    assert len(result) == 6
    # Lower bound: every required key is present
    assert set(result.keys()) == expected_keys


def test_each_framing_field_is_absent(researcher_finding):
    """normalize() strips every researcher framing field from the result."""
    result = normalize(researcher_finding)
    assert "title" not in result
    assert "detection_source" not in result
    assert "origin" not in result
    assert "pattern" not in result
    assert "remediation" not in result
    assert "reasoning" not in result
    assert "location" not in result


def test_location_folds_into_evidence(researcher_finding):
    """normalize() folds the location locator into evidence; location does not survive as a key."""
    result = normalize(researcher_finding)
    assert "location" not in result
    assert "auth.py" in result["evidence"]
    assert "42" in result["evidence"]


def test_allowlisted_values_pass_through_unchanged(researcher_finding):
    """normalize() passes allowlisted field values through unchanged from the input."""
    result = normalize(researcher_finding)
    assert result["type"] == researcher_finding["type"]
    assert result["severity"] == researcher_finding["severity"]
    assert result["mechanism"] == researcher_finding["mechanism"]
    assert result["consequence"] == researcher_finding["consequence"]
    assert result["source_of_truth_ref"] == researcher_finding["source_of_truth_ref"]
