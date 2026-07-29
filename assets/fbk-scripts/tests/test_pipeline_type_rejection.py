"""Tests for type-enum rejection and lens-based validation.

This test suite verifies that:

1. The `validate --lens <type>-lens.md` command rejects findings whose type
   is outside the lens's type matrix, exercising the type-enum branch
   (not the required-field branch), and logs `REJECTED: invalid type '<t>'`.

2. The fbk-presets.json file contains no preset entries for test, coherence,
   or task review types — the lens is the single type-filter authority.

These tests exercise the real subprocess pipeline against real repo-relative
lens files and the real fbk-presets.json file.
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


def _presets_json():
    """Return the path to fbk-presets.json."""
    return Path(__file__).parents[3] / "assets" / "fbk-scripts" / "fbk" / "data" / "fbk-presets.json"


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
    if not fbk_py.exists():
        pytest.skip("fbk.py dispatcher not found")

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
        if not test_lens.exists():
            pytest.skip(f"Lens not found: {test_lens}")

        finding = _make_finding(type_="behavioral", severity="major")
        result = _run_validate_lens([finding], test_lens)

        # Exit code 0: command ran successfully (argparse option exists or is not yet implemented)
        assert result.returncode == 0, (
            f"Expected exit code 0, got {result.returncode}. stderr: {result.stderr!r}"
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

    def test_coherence_lens_rejects_out_of_type_behavioral(self):
        """validate --lens coherence-lens.md rejects a finding typed 'behavioral'.

        coherence-lens.md types are: contract-mismatch, contract-gap,
        contract-ambiguity, orphan-declaration. A behavioral finding is out of type.

        Fixture: otherwise-valid finding with all required fields present,
        min-lengths met, but type='behavioral' which is not in coherence-lens's matrix.

        Expected: exit code 0, stdout is an empty JSON list,
        stderr contains exactly `REJECTED: invalid type 'behavioral'`.
        """
        coherence_lens = _lens("coherence-lens.md")
        if not coherence_lens.exists():
            pytest.skip(f"Lens not found: {coherence_lens}")

        finding = _make_finding(type_="behavioral", severity="major")
        result = _run_validate_lens([finding], coherence_lens)

        assert result.returncode == 0, (
            f"Expected exit code 0, got {result.returncode}. stderr: {result.stderr!r}"
        )

        stdout_list = json.loads(result.stdout)
        assert len(stdout_list) == 0, (
            f"Expected empty stdout list, got {len(stdout_list)} items"
        )

        assert "REJECTED: invalid type 'behavioral'" in result.stderr, (
            f"Expected rejection message in stderr, got: {result.stderr!r}"
        )

    def test_task_lens_rejects_out_of_type_behavioral(self):
        """validate --lens task-lens.md rejects a finding typed 'behavioral'.

        task-lens.md types are: under-specified, coverage-gap, sizing-violation,
        spec-conflict. A behavioral finding is out of type.

        Fixture: otherwise-valid finding with all required fields present,
        min-lengths met, but type='behavioral' which is not in task-lens's matrix.

        Expected: exit code 0, stdout is an empty JSON list,
        stderr contains exactly `REJECTED: invalid type 'behavioral'`.
        """
        task_lens = _lens("task-lens.md")
        if not task_lens.exists():
            pytest.skip(f"Lens not found: {task_lens}")

        finding = _make_finding(type_="behavioral", severity="major")
        result = _run_validate_lens([finding], task_lens)

        assert result.returncode == 0, (
            f"Expected exit code 0, got {result.returncode}. stderr: {result.stderr!r}"
        )

        stdout_list = json.loads(result.stdout)
        assert len(stdout_list) == 0, (
            f"Expected empty stdout list, got {len(stdout_list)} items"
        )

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
        if not test_lens.exists():
            pytest.skip(f"Lens not found: {test_lens}")

        finding = _make_finding(type_="untested-behavior", severity="major")
        result = _run_validate_lens([finding], test_lens)

        assert result.returncode == 0, (
            f"Expected exit code 0, got {result.returncode}. stderr: {result.stderr!r}"
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


# ---------------------------------------------------------------------------
# Test class: Preset absence
# ---------------------------------------------------------------------------


class TestPresetsAbsence:
    """Verify that fbk-presets.json has no test/coherence/task review preset entries."""

    def test_no_test_coherence_task_review_preset_entries(self):
        """fbk-presets.json parses and contains no test/coherence/task review preset keys.

        The three new review types (test, coherence, task) drive type-filtering
        through the lens, not through a preset. This test verifies that no preset
        entries exist for these types — the lens is the single type-filter authority.

        Expected:
        - The file parses as valid JSON.
        - No key names a test/coherence/task review preset (e.g., 'test-review',
          'test', 'coherence', 'coherence-review', 'task', 'task-review', or any
          plausible variant).
        - The existing preset entries ('behavioral-only', 'structural', 'test-only', 'full')
          are still present, confirming the test reads the real file.
        """
        presets_path = _presets_json()
        if not presets_path.exists():
            pytest.skip(f"Presets file not found: {presets_path}")

        # Parse the JSON
        with open(presets_path) as f:
            presets = json.load(f)

        assert isinstance(presets, dict), (
            f"Expected presets to be a dict, got: {type(presets)}"
        )

        # List of banned preset key names (test/coherence/task variants)
        banned_keys = {
            "test-review",
            "test",
            "coherence-review",
            "coherence",
            "task-review",
            "task",
        }

        # Check that no banned key exists
        found_banned = banned_keys & set(presets.keys())
        assert not found_banned, (
            f"Found banned preset keys in fbk-presets.json: {found_banned}. "
            f"These should not exist (lens is the type-filter authority)."
        )

        # Verify existing presets are still present (sanity check that we're
        # reading the real file, not an empty dict)
        expected_existing_keys = {"behavioral-only", "structural", "test-only", "full"}
        found_existing = expected_existing_keys & set(presets.keys())
        assert found_existing == expected_existing_keys, (
            f"Expected existing preset keys {expected_existing_keys}, "
            f"found {found_existing}. "
            f"All keys in file: {set(presets.keys())}"
        )
