"""Characterization tests for backward-compat of validate_sighting single-argument form.

These tests pin two behaviors that must survive the upcoming signature change from
validate_sighting(s) to validate_sighting(finding, vocab=None):

  1. Single-argument call sites continue to accept/reject exactly as today.
  2. The 30%-rejection warning on the pipeline validate CLI path fires and stays
     byte-identical after the refactor.

Because the behavior already exists, these tests are green against current code
and must remain green after the vocab parameter is added.
"""

import json
import sys
from pathlib import Path

import pytest

# Mirror the import setup from test_pipeline.py so this file resolves the module
# the same way regardless of which directory pytest is invoked from.
sys.path.insert(0, str(Path(__file__).parent.parent))

from fbk.pipeline import validate_sighting

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _make_sighting(type_, severity):
    """Return a fully-populated sighting dict with the given type and severity."""
    return {
        "id": "bc-001",
        "title": "Backward compat test sighting",
        "location": {"file": "src/module.py", "start_line": 42},
        "type": type_,
        "severity": severity,
        "mechanism": "Test mechanism description text",
        "consequence": "Test consequence description",
        "evidence": "Test evidence string",
    }


def _fbk_py_path():
    """Return the path to the fbk.py dispatcher."""
    return Path(__file__).parent.parent / "fbk.py"


# ---------------------------------------------------------------------------
# Unit tests: single-argument form
# ---------------------------------------------------------------------------

class TestSingleArgumentBackwardCompat:
    """Pins that the single-argument form of validate_sighting behaves identically
    after the function gains its optional vocab parameter."""

    def test_single_arg_valid_sighting_still_passes(self):
        """validate_sighting(sighting) returns None for a valid code-review sighting.

        behavioral+critical is a valid combination in the built-in vocab.
        After the signature gains vocab=None, the same call with no second arg
        must still return None — the vocab=None branch must fall back to module
        constants and produce the same accept result.
        """
        sighting = _make_sighting(type_="behavioral", severity="critical")
        result = validate_sighting(sighting)
        assert result is None, (
            f"Expected None for valid behavioral+critical sighting, got: {result!r}"
        )

    def test_single_arg_invalid_combination_same_reason(self):
        """validate_sighting(sighting) returns a string containing 'type-severity' for
        an invalid type-severity combination.

        structural+critical is not a valid combination. The rejection string must
        contain 'type-severity' — the same text current code produces — so callers
        that pattern-match on that substring keep working after the refactor.
        """
        sighting = _make_sighting(type_="structural", severity="critical")
        result = validate_sighting(sighting)
        assert result is not None, (
            "Expected a rejection reason for structural+critical, got None"
        )
        assert "type-severity" in result, (
            f"Expected rejection reason to contain 'type-severity', got: {result!r}"
        )

    # -----------------------------------------------------------------------
    # CLI path: 30%-rejection warning
    # -----------------------------------------------------------------------

    def test_validate_cli_emits_30pct_warning(self):
        """pipeline validate prints the 30%-rejection warning when >30% are rejected.

        Four sightings, two with an invalid type: rejection rate is 50%, which
        exceeds the 30% threshold. The warning must appear on stderr and the
        surviving valid sightings must appear as a JSON list on stdout.

        Pairing: the upper-bound warning assertion is paired with a lower-bound
        assertion that the surviving valid sightings appear in stdout (stdout JSON
        parses to a list whose length equals the number of valid inputs).
        """
        fbk_py = _fbk_py_path()
        if not fbk_py.exists():
            pytest.skip("fbk.py dispatcher not found")

        valid_sightings = [
            _make_sighting(type_="behavioral", severity="critical"),
            _make_sighting(type_="behavioral", severity="major"),
        ]
        invalid_sightings = [
            _make_sighting(type_="nonexistent-type", severity="critical"),
            _make_sighting(type_="also-invalid", severity="major"),
        ]
        all_sightings = valid_sightings + invalid_sightings  # 2 valid, 2 invalid = 50%

        result = subprocess_run_pipeline_validate(fbk_py, all_sightings)

        # Upper-bound: warning is present
        assert "sightings rejected" in result.stderr, (
            f"Expected '... sightings rejected ...' in stderr; got: {result.stderr!r}"
        )
        assert "check prompt compliance" in result.stderr, (
            f"Expected 'check prompt compliance' in stderr; got: {result.stderr!r}"
        )

        # Lower-bound: the surviving valid sightings appear in stdout
        stdout_list = json.loads(result.stdout)
        assert isinstance(stdout_list, list), (
            f"Expected stdout to be a JSON list, got: {type(stdout_list)}"
        )
        assert len(stdout_list) == len(valid_sightings), (
            f"Expected {len(valid_sightings)} surviving sightings in stdout, "
            f"got {len(stdout_list)}"
        )

    def test_validate_cli_below_threshold_no_warning(self):
        """pipeline validate does not print the 30%-rejection warning when <30% are rejected.

        Five sightings, one invalid: rejection rate is 20%, below the 30% threshold.
        Asserting the warning is absent keeps the above warning-present assertion
        non-vacuous — it proves the warning fires only when the threshold is crossed.
        """
        fbk_py = _fbk_py_path()
        if not fbk_py.exists():
            pytest.skip("fbk.py dispatcher not found")

        valid_sightings = [
            _make_sighting(type_="behavioral", severity="critical"),
            _make_sighting(type_="behavioral", severity="major"),
            _make_sighting(type_="fragile", severity="minor"),
            _make_sighting(type_="fragile", severity="major"),
        ]
        invalid_sightings = [
            _make_sighting(type_="nonexistent-type", severity="critical"),
        ]
        all_sightings = valid_sightings + invalid_sightings  # 4 valid, 1 invalid = 20%

        result = subprocess_run_pipeline_validate(fbk_py, all_sightings)

        assert "check prompt compliance" not in result.stderr, (
            f"Expected no 30%-warning for 20% rejection rate; got stderr: {result.stderr!r}"
        )


# ---------------------------------------------------------------------------
# Byte-identity tests for default path (no --lens)
# ---------------------------------------------------------------------------

class TestDefaultPathByteIdentical:
    """Pins byte-identical stdout, stderr, exit code for validate/run with no --lens.

    The upcoming signature change from validate_sighting(s) to validate_sighting(finding, vocab=None)
    adds an optional vocab parameter. When vocab is None, the default path (called when no --lens
    is passed) must produce output that is byte-for-byte identical to today's behavior.

    These tests capture golden values for the default path and assert byte-identical output.
    They are expected to pass against current code and must remain green after the vocab
    parameter is added.
    """

    @staticmethod
    def _make_byte_identity_fixture():
        """Build a fixed fixture exercising both acceptance and rejection paths.

        Includes 3 valid sightings and 2 invalid sightings so that:
        - stdout contains non-empty survivor list
        - stderr contains REJECTED lines and the 40% warning (above 30% threshold)
        No randomness or timestamps.
        """
        valid = [
            _make_sighting(type_="behavioral", severity="critical"),
            _make_sighting(type_="structural", severity="minor"),
            _make_sighting(type_="test-integrity", severity="major"),
        ]
        # Make them distinguishable by modifying the id field
        valid[0]["id"] = "sighting-001"
        valid[1]["id"] = "sighting-002"
        valid[2]["id"] = "sighting-003"

        invalid = [
            _make_sighting(type_="invalid-type-1", severity="critical"),
            _make_sighting(type_="invalid-type-2", severity="major"),
        ]
        invalid[0]["id"] = "sighting-004"
        invalid[1]["id"] = "sighting-005"

        return valid + invalid  # 3 valid, 2 invalid = 40% rejection rate

    def test_validate_default_path_exit_code(self):
        """pipeline validate with no --lens exits with code 0."""
        fbk_py = _fbk_py_path()
        if not fbk_py.exists():
            pytest.skip("fbk.py dispatcher not found")

        fixture = self._make_byte_identity_fixture()
        result = subprocess_run_pipeline_validate(fbk_py, fixture)

        assert result.returncode == 0, (
            f"Expected exit code 0, got {result.returncode}; "
            f"stderr: {result.stderr!r}"
        )

    def test_validate_default_path_stdout_golden(self):
        """pipeline validate with no --lens produces byte-identical stdout.

        stdout must be the JSON-serialized list of survivors (3 valid sightings),
        with ids reassigned to S-01, S-02, S-03 and defaults filled in.
        The format is json.dumps with indent=2, ensure_ascii=False, plus trailing newline.
        """
        fbk_py = _fbk_py_path()
        if not fbk_py.exists():
            pytest.skip("fbk.py dispatcher not found")

        fixture = self._make_byte_identity_fixture()
        result = subprocess_run_pipeline_validate(fbk_py, fixture)

        # Construct the expected golden: 3 survivors with defaults filled and ids reassigned
        valid_sightings = [s for s in fixture if s.get("type") in ["behavioral", "structural", "test-integrity", "fragile"]]
        assert len(valid_sightings) == 3, f"Expected 3 valid sightings, got {len(valid_sightings)}"

        expected_survivors = []
        for i, s in enumerate(valid_sightings, 1):
            survivor = dict(s)
            survivor["id"] = f"S-{i:02d}"
            for key, default in [("origin", "unknown"), ("detection_source", "intent"), ("source_of_truth_ref", ""), ("pattern", ""), ("remediation", "")]:
                if key not in survivor or survivor[key] is None:
                    survivor[key] = default
            expected_survivors.append(survivor)

        expected_stdout = json.dumps(expected_survivors, indent=2, ensure_ascii=False) + "\n"

        assert result.stdout == expected_stdout, (
            f"stdout mismatch.\nExpected:\n{expected_stdout!r}\n\nGot:\n{result.stdout!r}"
        )

        # Presence assertion paired with byte-identity: stdout parses to a non-empty list
        parsed = json.loads(result.stdout)
        assert isinstance(parsed, list), f"Expected stdout to parse to a list, got {type(parsed)}"
        assert len(parsed) > 0, "Expected non-empty survivor list in stdout"

    def test_validate_default_path_stderr_golden(self):
        """pipeline validate with no --lens produces byte-identical stderr.

        stderr contains REJECTED lines for the 2 invalid sightings and the 40%-warning.
        The warning text is: "WARNING: 2/5 sightings rejected (40%) — check prompt compliance"
        """
        fbk_py = _fbk_py_path()
        if not fbk_py.exists():
            pytest.skip("fbk.py dispatcher not found")

        fixture = self._make_byte_identity_fixture()
        result = subprocess_run_pipeline_validate(fbk_py, fixture)

        # The fixture has 5 total sightings, 2 invalid (40% rejection rate)
        # Construct expected stderr: REJECTED lines + warning
        invalid_sightings = [s for s in fixture if s.get("type") not in ["behavioral", "structural", "test-integrity", "fragile"]]
        assert len(invalid_sightings) == 2, f"Expected 2 invalid sightings, got {len(invalid_sightings)}"

        rejected_lines = []
        for s in invalid_sightings:
            reason = "invalid type '{}'".format(s.get("type"))
            rejected_lines.append(f"REJECTED: {reason}: {json.dumps(s, ensure_ascii=False)}")

        warning_line = "WARNING: 2/5 sightings rejected (40%) — check prompt compliance"
        expected_stderr = "\n".join(rejected_lines) + "\n" + warning_line + "\n"

        assert result.stderr == expected_stderr, (
            f"stderr mismatch.\nExpected:\n{expected_stderr!r}\n\nGot:\n{result.stderr!r}"
        )

        # Presence assertion paired with byte-identity: stderr is non-empty
        assert len(result.stderr) > 0, "Expected non-empty stderr (rejections and warning)"

    def test_run_default_path_exit_code(self):
        """pipeline run with no --lens exits with code 0."""
        fbk_py = _fbk_py_path()
        if not fbk_py.exists():
            pytest.skip("fbk.py dispatcher not found")

        fixture = self._make_byte_identity_fixture()
        result = subprocess_run_pipeline_run(fbk_py, fixture, preset="full", min_severity="minor")

        assert result.returncode == 0, (
            f"Expected exit code 0, got {result.returncode}; "
            f"stderr: {result.stderr!r}"
        )

    def test_run_default_path_stdout_golden(self):
        """pipeline run with no --lens produces byte-identical stdout.

        run applies domain and severity filters on top of validation.
        With preset=full and min_severity=minor:
        - 3 valid survivors from validation
        - domain filter: all 3 pass (all types are in full preset)
        - severity filter: all 3 pass (critical, minor, major all >= minor)
        - ids are reassigned S-01, S-02, S-03
        stdout is json.dumps with indent=2, ensure_ascii=False, plus trailing newline.
        """
        fbk_py = _fbk_py_path()
        if not fbk_py.exists():
            pytest.skip("fbk.py dispatcher not found")

        fixture = self._make_byte_identity_fixture()
        result = subprocess_run_pipeline_run(fbk_py, fixture, preset="full", min_severity="minor")

        # Expected output: 3 survivors (all pass validation, domain, and severity filters)
        valid_sightings = [s for s in fixture if s.get("type") in ["behavioral", "structural", "test-integrity", "fragile"]]
        assert len(valid_sightings) == 3

        expected_survivors = []
        for i, s in enumerate(valid_sightings, 1):
            survivor = dict(s)
            survivor["id"] = f"S-{i:02d}"
            for key, default in [("origin", "unknown"), ("detection_source", "intent"), ("source_of_truth_ref", ""), ("pattern", ""), ("remediation", "")]:
                if key not in survivor or survivor[key] is None:
                    survivor[key] = default
            expected_survivors.append(survivor)

        expected_stdout = json.dumps(expected_survivors, indent=2, ensure_ascii=False) + "\n"

        assert result.stdout == expected_stdout, (
            f"stdout mismatch.\nExpected:\n{expected_stdout!r}\n\nGot:\n{result.stdout!r}"
        )

        # Presence assertion: stdout parses to a non-empty list
        parsed = json.loads(result.stdout)
        assert isinstance(parsed, list), f"Expected stdout to parse to a list, got {type(parsed)}"
        assert len(parsed) > 0, "Expected non-empty survivor list in stdout"

    def test_run_default_path_stderr_golden(self):
        """pipeline run with no --lens produces byte-identical stderr.

        stderr contains REJECTED lines for the 2 invalid sightings and the 40%-warning.
        No DROPPED lines because all 3 survivors pass both domain and severity filters.
        """
        fbk_py = _fbk_py_path()
        if not fbk_py.exists():
            pytest.skip("fbk.py dispatcher not found")

        fixture = self._make_byte_identity_fixture()
        result = subprocess_run_pipeline_run(fbk_py, fixture, preset="full", min_severity="minor")

        # Expected: REJECTED lines for 2 invalid sightings + warning (no DROPPED lines)
        invalid_sightings = [s for s in fixture if s.get("type") not in ["behavioral", "structural", "test-integrity", "fragile"]]
        assert len(invalid_sightings) == 2

        rejected_lines = []
        for s in invalid_sightings:
            reason = "invalid type '{}'".format(s.get("type"))
            rejected_lines.append(f"REJECTED: {reason}: {json.dumps(s, ensure_ascii=False)}")

        warning_line = "WARNING: 2/5 sightings rejected (40%) — check prompt compliance"
        expected_stderr = "\n".join(rejected_lines) + "\n" + warning_line + "\n"

        assert result.stderr == expected_stderr, (
            f"stderr mismatch.\nExpected:\n{expected_stderr!r}\n\nGot:\n{result.stderr!r}"
        )

        # Presence assertion: stderr is non-empty
        assert len(result.stderr) > 0, "Expected non-empty stderr (rejections and warning)"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def subprocess_run_pipeline_validate(fbk_py, sightings):
    """Run `fbk.py pipeline validate` with sightings as JSON on stdin.

    Returns the CompletedProcess so the caller can inspect stdout and stderr.
    Raises on timeout (hard 15-second limit per invocation).
    """
    import subprocess
    return subprocess.run(
        [sys.executable, str(fbk_py), "pipeline", "validate"],
        input=json.dumps(sightings),
        capture_output=True,
        text=True,
        timeout=15,
    )


def subprocess_run_pipeline_run(fbk_py, sightings, preset, min_severity):
    """Run `fbk.py pipeline run --preset <p> --min-severity <s>` with sightings as JSON on stdin.

    Returns the CompletedProcess so the caller can inspect stdout and stderr.
    Raises on timeout (hard 15-second limit per invocation).
    """
    import subprocess
    return subprocess.run(
        [sys.executable, str(fbk_py), "pipeline", "run", "--preset", preset, "--min-severity", min_severity],
        input=json.dumps(sightings),
        capture_output=True,
        text=True,
        timeout=15,
    )
