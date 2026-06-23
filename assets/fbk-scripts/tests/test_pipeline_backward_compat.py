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
