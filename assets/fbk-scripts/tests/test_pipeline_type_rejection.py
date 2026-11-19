"""Tests for type-enum rejection and lens-based validation.

This test suite verifies that:

1. The `validate --lens <type>-lens.md` command rejects findings whose type
   is outside the lens's type matrix, exercising the type-enum branch
   (not the required-field branch), and logs `REJECTED: invalid type '<t>'`.

These tests exercise the real subprocess pipeline against real repo-relative
lens files.
"""

import json
import sys
from pathlib import Path
import subprocess

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fbk_py():
    """Return the path to the fbk.py dispatcher."""
    return Path(__file__).parent.parent / "fbk.py"


def _lens(name):
    """Return the repo-relative path to a lens file by name (e.g., 'test-lens.md')."""
    return Path(__file__).parents[3] / "assets" / "fbk-docs" / "fbk-review-lenses" / name


@pytest.fixture(scope="module", autouse=True)
def required_pipeline_assets():
    for path in [_fbk_py(), *(_lens(f"{name}-lens.md") for name in ("test",))]:
        if not path.is_file():
            pytest.fail(f"Required pipeline test asset is missing: {path}")


def _make_finding(type_, severity):
    """Return a fully-populated, otherwise-valid finding dict with the given type and severity.

    All required fields are present with minimum-length content. The only thing
    that may be wrong is the type.
    """
    return {
        "title": "Test finding title with sufficient length",
        "location": {"file": "src/module.py", "start_line": 42},
        "type": type_,
        "severity": severity,
        "mechanism": "Test mechanism description for validation",
        "consequence": "Test consequence description for validation",
        "evidence": "Test evidence string for validation",
    }


def _run_validate_lens(findings_list, lens_path):
    """Run `fbk.py pipeline validate --lens <lens_path>` with findings on stdin.

    Returns the CompletedProcess so caller can inspect stdout, stderr, and returncode.
    Raises on timeout (hard 15-second limit per invocation).
    """
    fbk_py = _fbk_py()
    return subprocess.run(
        [sys.executable, str(fbk_py), "pipeline", "validate", "--lens", str(lens_path)],
        input=json.dumps(findings_list),
        capture_output=True,
        text=True,
        timeout=15,
    )


# ---------------------------------------------------------------------------
# Test class: Type rejection under lenses
# ---------------------------------------------------------------------------


class TestTypeRejectionUnderLenses:
    """Verify that findings with out-of-type types are rejected at validation."""

    def test_test_lens_rejects_out_of_type_behavioral(self):
        """validate --lens test-lens.md rejects a finding typed 'behavioral'.

        test-lens.md types are: weakened-assertion, untested-behavior,
        trivially-passing, manifest-drift. A behavioral finding is out of type.

        Fixture: otherwise-valid finding with all required fields present,
        min-lengths met, but type='behavioral' which is not in test-lens's matrix.

        Expected: exit code 0 (command runs), stdout is an empty JSON list,
        stderr contains exactly `REJECTED: invalid type 'behavioral'`.
        """
        test_lens = _lens("test-lens.md")
        finding = _make_finding(type_="behavioral", severity="major")
        result = _run_validate_lens([finding], test_lens)

        # Exit code 0: command ran successfully
        assert result.returncode == 0, (
            f"Expected exit code 0; command result: {result!r}"
        )

        # stdout is an empty JSON list
        stdout_list = json.loads(result.stdout)
        assert isinstance(stdout_list, list), (
            f"Expected stdout to be a JSON list, got: {type(stdout_list)}"
        )
        assert len(stdout_list) == 0, (
            f"Expected empty stdout list (all findings rejected), got {len(stdout_list)} items"
        )

        # stderr contains the exact rejection message
        assert "REJECTED: invalid type 'behavioral'" in result.stderr, (
            f"Expected rejection message in stderr, got: {result.stderr!r}"
        )

    def test_test_lens_accepts_in_type_untested_behavior(self):
        """Positive control: validate --lens test-lens.md accepts a valid in-type finding.

        Finding typed 'untested-behavior' (a valid test-lens type) with severity='major'
        (a valid combination in test-lens's matrix) should pass validation.

        Fixture: otherwise-valid finding with type='untested-behavior', severity='major'.

        Expected: exit code 0, stdout is a JSON list with one item (the accepted finding),
        stderr has no rejection message.

        This positive control ensures the rejection tests above are non-vacuous —
        that the lens accepts a valid type and rejects only the out-of-type case.
        """
        test_lens = _lens("test-lens.md")
        finding = _make_finding(type_="untested-behavior", severity="major")
        result = _run_validate_lens([finding], test_lens)

        assert result.returncode == 0, (
            f"Expected exit code 0; command result: {result!r}"
        )

        stdout_list = json.loads(result.stdout)
        assert isinstance(stdout_list, list), (
            f"Expected stdout to be a JSON list, got: {type(stdout_list)}"
        )
        assert len(stdout_list) == 1, (
            f"Expected 1 accepted finding in stdout, got {len(stdout_list)}"
        )

        # Verify the finding in the list has the type we sent
        assert stdout_list[0].get("type") == "untested-behavior", (
            f"Expected type='untested-behavior' in output, got: {stdout_list[0].get('type')!r}"
        )
