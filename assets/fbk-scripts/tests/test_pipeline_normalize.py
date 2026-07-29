"""Unit tests for pipeline.normalize — researcher framing strip and location fold.

Tests cover:
- normalize() returns exactly the six allowlisted handoff fields and no others
- Every researcher framing field (title, detection_source, origin, pattern,
  remediation, reasoning, location) is absent from the result
- The structured location object does not survive as a standalone key; its
  locator (file and start_line) is folded into the evidence string
- Allowlisted values (type, severity, mechanism, consequence,
  source_of_truth_ref) pass through unchanged from the input finding

Subcommand tests (list-level normalize):
- pipeline normalize subcommand reads a finding list on stdin, applies normalize()
  to each record in input order, and writes the result
- Empty array yields [] (exit zero)
- Non-JSON input raises exit non-zero with ERROR: malformed JSON input
- Finding missing source fields yields empty strings for them
"""

import json
import sys
from pathlib import Path
import subprocess

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


# ---------------------------------------------------------------------------
# Subcommand tests (list-level normalize via subprocess)
# ---------------------------------------------------------------------------


def _fbk_py():
    """Return the path to the fbk.py dispatcher."""
    return Path(__file__).parent.parent / "fbk.py"


def _run_normalize(stdin_text):
    """Run `fbk.py pipeline normalize` with stdin_text as input.

    Returns the CompletedProcess so the caller can inspect returncode, stdout, and stderr.
    Raises on timeout (hard 15-second limit per invocation).
    """
    fbk_py = _fbk_py()
    if not fbk_py.exists():
        pytest.skip("fbk.py dispatcher not found")

    return subprocess.run(
        [sys.executable, str(fbk_py), "pipeline", "normalize"],
        input=stdin_text,
        capture_output=True,
        text=True,
        timeout=15,
    )


class TestNormalizeSubcommand:
    """Tests for the list-level `normalize` subcommand that applies normalize() to
    each finding in a JSON array read from stdin."""

    def test_multi_finding_order_and_shape(self):
        """normalize subcommand preserves input order, emits six fields per record, folds location.

        Three distinct findings with all source fields and framing fields are normalized.
        Assertions verify:
          - Exit code zero
          - Output parses to a JSON list of same length as input
          - Each record has exactly six keys (no more, no less)
          - Records appear in input order (distinct mechanism per record)
          - location is absent; file and start_line are folded into evidence
        """
        finding1 = {
            "mechanism": "Sentinel-One: Token written to world-readable file",
            "consequence": "Any process can read the token",
            "evidence": "auth.py:42 — open call without umask",
            "type": "behavioral",
            "severity": "critical",
            "source_of_truth_ref": "docs/auth.md",
            "title": "World-readable token file",
            "detection_source": "intent",
            "remediation": "Set umask to 0600",
            "location": {"file": "auth.py", "start_line": 42},
        }
        finding2 = {
            "mechanism": "Sentinel-Two: Hardcoded password in config",
            "consequence": "Config can be read by anyone with repo access",
            "evidence": "config.py:15 — password literal",
            "type": "behavioral",
            "severity": "major",
            "source_of_truth_ref": "docs/config-security.md",
            "title": "Hardcoded password",
            "detection_source": "design",
            "remediation": "Use environment variable",
            "location": {"file": "config.py", "start_line": 15},
        }
        finding3 = {
            "mechanism": "Sentinel-Three: Missing input validation",
            "consequence": "Attacker can inject malicious input",
            "evidence": "input.py:8 — no validation before use",
            "type": "structural",
            "severity": "critical",
            "source_of_truth_ref": "docs/input-validation.md",
            "title": "No input validation",
            "detection_source": "intent",
            "remediation": "Add input schema validation",
            "location": {"file": "input.py", "start_line": 8},
        }

        input_findings = [finding1, finding2, finding3]
        result = _run_normalize(json.dumps(input_findings))

        # Exit zero
        assert result.returncode == 0, (
            f"Expected exit code 0, got {result.returncode}. stderr: {result.stderr!r}"
        )

        # Output parses to a JSON list
        output_list = json.loads(result.stdout)
        assert isinstance(output_list, list), (
            f"Expected stdout to be a JSON list, got: {type(output_list)}"
        )

        # Same length as input
        assert len(output_list) == len(input_findings), (
            f"Expected {len(input_findings)} records in output, got {len(output_list)}"
        )

        # Each record has exactly six keys
        for i, record in enumerate(output_list):
            assert len(record) == 6, (
                f"Record {i} has {len(record)} keys, expected 6. Keys: {set(record.keys())}"
            )
            expected_keys = {"mechanism", "consequence", "evidence", "type", "severity", "source_of_truth_ref"}
            assert set(record.keys()) == expected_keys, (
                f"Record {i} has keys {set(record.keys())}, expected {expected_keys}"
            )

        # Records in input order (verify distinct mechanisms)
        expected_mechanisms = [
            "Sentinel-One: Token written to world-readable file",
            "Sentinel-Two: Hardcoded password in config",
            "Sentinel-Three: Missing input validation",
        ]
        for i, record in enumerate(output_list):
            assert record["mechanism"] == expected_mechanisms[i], (
                f"Record {i} mechanism mismatch: expected {expected_mechanisms[i]!r}, "
                f"got {record['mechanism']!r}"
            )

        # location is absent; file and start_line are in evidence
        for i, record in enumerate(output_list):
            assert "location" not in record, (
                f"Record {i} must not have 'location' key, but it does"
            )

        # Verify location was folded into evidence
        assert "auth.py" in output_list[0]["evidence"], (
            f"Record 0 evidence should contain 'auth.py', got: {output_list[0]['evidence']!r}"
        )
        assert "42" in output_list[0]["evidence"], (
            f"Record 0 evidence should contain '42', got: {output_list[0]['evidence']!r}"
        )
        assert "config.py" in output_list[1]["evidence"], (
            f"Record 1 evidence should contain 'config.py', got: {output_list[1]['evidence']!r}"
        )
        assert "15" in output_list[1]["evidence"], (
            f"Record 1 evidence should contain '15', got: {output_list[1]['evidence']!r}"
        )

    def test_missing_source_fields(self):
        """normalize subcommand returns empty strings for missing source fields.

        A finding lacking consequence and source_of_truth_ref is normalized.
        Assertions verify:
          - Exit code zero
          - Result record still has all six keys
          - Missing fields are empty strings, not null or absent
          - No exception raised
        """
        finding_incomplete = {
            "mechanism": "Token vulnerability",
            # consequence is missing
            "evidence": "auth.py:42",
            "type": "behavioral",
            "severity": "critical",
            # source_of_truth_ref is missing
            "title": "Missing fields test",
            "detection_source": "design",
            "location": {"file": "auth.py", "start_line": 42},
        }

        input_findings = [finding_incomplete]
        result = _run_normalize(json.dumps(input_findings))

        # Exit zero (no raise on missing fields)
        assert result.returncode == 0, (
            f"Expected exit code 0 for missing fields, got {result.returncode}. "
            f"stderr: {result.stderr!r}"
        )

        output_list = json.loads(result.stdout)
        assert len(output_list) == 1, (
            f"Expected 1 record in output, got {len(output_list)}"
        )

        record = output_list[0]

        # Record still has all six keys
        expected_keys = {"mechanism", "consequence", "evidence", "type", "severity", "source_of_truth_ref"}
        assert set(record.keys()) == expected_keys, (
            f"Expected keys {expected_keys}, got {set(record.keys())}"
        )
        assert len(record) == 6, (
            f"Expected 6 keys, got {len(record)}"
        )

        # Missing fields are empty strings
        assert record["consequence"] == "", (
            f"Expected consequence='', got {record['consequence']!r}"
        )
        assert record["source_of_truth_ref"] == "", (
            f"Expected source_of_truth_ref='', got {record['source_of_truth_ref']!r}"
        )

    def test_empty_array_input(self):
        """normalize subcommand returns empty array for empty input.

        Stdin: []
        Expected: stdout=[], exit code 0
        """
        result = _run_normalize("[]")

        # Exit zero
        assert result.returncode == 0, (
            f"Expected exit code 0 for empty array, got {result.returncode}. "
            f"stderr: {result.stderr!r}"
        )

        # Output parses to an empty list
        output_list = json.loads(result.stdout)
        assert isinstance(output_list, list), (
            f"Expected stdout to be a JSON list, got: {type(output_list)}"
        )
        assert len(output_list) == 0, (
            f"Expected empty list output, got {len(output_list)} items"
        )

    def test_non_json_input(self):
        """normalize subcommand rejects non-JSON input with error message.

        Stdin: garbage text (not valid JSON)
        Expected: exit code non-zero, stderr contains "ERROR: malformed JSON input"
        """
        result = _run_normalize("not valid json")

        # Exit non-zero
        assert result.returncode != 0, (
            f"Expected non-zero exit code for malformed JSON, got {result.returncode}"
        )

        # stderr contains error message
        assert "ERROR: malformed JSON input" in result.stderr, (
            f"Expected 'ERROR: malformed JSON input' in stderr, got: {result.stderr!r}"
        )
