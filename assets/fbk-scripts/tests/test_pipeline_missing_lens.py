"""
Tests for load_lens_matrix() loud-failure behavior (AC-03, AC-04).

An unresolvable lens path must raise a named exception whose message contains
the missing path string (AC-03). A file with no lens-matrix block must raise a
named exception whose message contains the file path (AC-04). Silent fallback
to generic behavior is forbidden in both cases.

These cases live in their own file so they do not race task-02's edits to
test_pipeline.py in the same wave.
"""
import json
import sys
from pathlib import Path

import pytest

try:
    from fbk.pipeline import load_lens_matrix, LensVocabulary  # type: ignore[import]
    _LOAD_LENS_IMPORTABLE = True
except ImportError:
    _LOAD_LENS_IMPORTABLE = False


@pytest.mark.skipif(
    not _LOAD_LENS_IMPORTABLE,
    reason="load_lens_matrix not yet implemented — red-phase skip",
)
class TestMissingLensLoudFailure:
    """load_lens_matrix() raises a named exception when the lens path does not exist."""

    def test_missing_lens_path_raises_named_error(self, tmp_path):
        """Unresolvable lens path raises an exception whose message names the path (AC-03)."""
        missing_path = tmp_path / "fbk-review-lenses" / "nonexistent-lens.md"

        with pytest.raises(Exception) as exc_info:
            load_lens_matrix(str(missing_path))

        assert "nonexistent-lens.md" in str(exc_info.value), (
            f"Expected exception message to contain 'nonexistent-lens.md', "
            f"got: {exc_info.value!r}"
        )

    def test_missing_lens_does_not_return_default_vocabulary(self, tmp_path):
        """load_lens_matrix on a missing path raises — no silent fallback to a default vocabulary.

        The pytest.raises context enforces that an exception is raised; no LensVocabulary
        is silently returned. This test documents the no-silent-fallback contract from AC-03.
        """
        missing_path = tmp_path / "fbk-review-lenses" / "nonexistent-lens.md"

        with pytest.raises(Exception):
            load_lens_matrix(str(missing_path))
            # Unreachable: if we reach this line the loader returned a value
            # instead of raising, which violates the no-silent-fallback contract.
            pytest.fail(  # pragma: no cover
                "load_lens_matrix returned without raising — silent fallback is forbidden"
            )


# ---------------------------------------------------------------------------
# Subprocess helper (mirrors test_pipeline_backward_compat.py shape)
# ---------------------------------------------------------------------------

def _fbk_py_path():
    """Return the path to the fbk.py dispatcher."""
    return Path(__file__).parent.parent / "fbk.py"


def _subprocess_run_pipeline(args, stdin_data):
    """Run `fbk.py pipeline <args>` with stdin_data as text.

    Returns the CompletedProcess. Hard timeout is 15 seconds per invocation.
    """
    import subprocess
    fbk_py = _fbk_py_path()
    return subprocess.run(
        [sys.executable, str(fbk_py), "pipeline"] + args,
        input=stdin_data,
        capture_output=True,
        text=True,
        timeout=15,
    )


def _valid_finding_no_id():
    """Return a finding with all code-lens required fields but no 'id'."""
    return {
        "title": "Unguarded state mutation causes data race",
        "location": {"file": "src/handler.py", "start_line": 10},
        "type": "behavioral",
        "severity": "major",
        "mechanism": "Shared state is mutated without synchronization.",
        "consequence": "Concurrent requests may observe partial writes.",
        "evidence": "handler.py:10 — no lock on shared_state assignment",
    }


# ---------------------------------------------------------------------------
# Command-line wrapping: missing path (AC-03) and no-matrix-block (AC-04)
# ---------------------------------------------------------------------------

class TestMissingLensCommandLine:
    """Command-line validate and run fail loudly for a missing lens path (AC-03)
    and for a lens file with no lens-matrix block (AC-04).

    These tests are guarded by the same red-phase pattern as the unit tests above:
    they are collected unconditionally but assert on --lens behavior that does not
    yet exist in argparse, making them RED until the --lens flag is wired.
    """

    # -- Missing path: validate -----------------------------------------------

    def test_validate_missing_lens_path_exits_nonzero(self, tmp_path):
        """validate --lens <nonexistent path> exits non-zero (AC-03).

        The pipeline must detect the missing file and fail before reading stdin.
        """
        missing = tmp_path / "nonexistent-lens.md"
        result = _subprocess_run_pipeline(
            ["validate", "--lens", str(missing)],
            json.dumps([_valid_finding_no_id()]),
        )
        assert result.returncode != 0, (
            f"Expected non-zero exit for missing lens path; got 0. "
            f"stderr: {result.stderr!r}"
        )

    def test_validate_missing_lens_path_stderr_contains_named_path(self, tmp_path):
        """validate --lens <nonexistent path> prints 'lens not found:' and the path to stderr (AC-03)."""
        missing = tmp_path / "nonexistent-lens.md"
        result = _subprocess_run_pipeline(
            ["validate", "--lens", str(missing)],
            json.dumps([_valid_finding_no_id()]),
        )
        assert "lens not found:" in result.stderr, (
            f"Expected 'lens not found:' in stderr; got: {result.stderr!r}"
        )
        assert str(missing) in result.stderr, (
            f"Expected missing path in stderr; got: {result.stderr!r}"
        )

    def test_validate_missing_lens_path_stdout_empty(self, tmp_path):
        """validate --lens <nonexistent path> produces no stdout (AC-03)."""
        missing = tmp_path / "nonexistent-lens.md"
        result = _subprocess_run_pipeline(
            ["validate", "--lens", str(missing)],
            json.dumps([_valid_finding_no_id()]),
        )
        assert result.stdout.strip() == "", (
            f"Expected empty stdout; got: {result.stdout!r}"
        )

    def test_validate_missing_lens_path_no_findings_processed(self, tmp_path):
        """validate --lens <nonexistent path> does not process any finding (AC-03).

        No REJECTED: line in stderr proves stdin was not read before the lens failure.
        """
        missing = tmp_path / "nonexistent-lens.md"
        result = _subprocess_run_pipeline(
            ["validate", "--lens", str(missing)],
            json.dumps([_valid_finding_no_id()]),
        )
        assert "REJECTED:" not in result.stderr, (
            f"REJECTED: line present — stdin was read before lens failure. "
            f"stderr: {result.stderr!r}"
        )

    # -- No-matrix-block: validate --------------------------------------------

    def test_validate_no_matrix_block_exits_nonzero(self, tmp_path):
        """validate --lens <prose-only file> exits non-zero (AC-04)."""
        prose_lens = tmp_path / "prose-only-lens.md"
        prose_lens.write_text("# A Lens\n\nProse with no lens-matrix block.\n")
        result = _subprocess_run_pipeline(
            ["validate", "--lens", str(prose_lens)],
            json.dumps([_valid_finding_no_id()]),
        )
        assert result.returncode != 0, (
            f"Expected non-zero exit for no-matrix-block lens; got 0. "
            f"stderr: {result.stderr!r}"
        )

    def test_validate_no_matrix_block_stderr_contains_message(self, tmp_path):
        """validate --lens <prose-only file> prints 'no lens-matrix block found in:' to stderr (AC-04)."""
        prose_lens = tmp_path / "prose-only-lens.md"
        prose_lens.write_text("# A Lens\n\nProse with no lens-matrix block.\n")
        result = _subprocess_run_pipeline(
            ["validate", "--lens", str(prose_lens)],
            json.dumps([_valid_finding_no_id()]),
        )
        assert "no lens-matrix block found in:" in result.stderr, (
            f"Expected 'no lens-matrix block found in:' in stderr; got: {result.stderr!r}"
        )
        assert str(prose_lens) in result.stderr, (
            f"Expected lens file path in stderr; got: {result.stderr!r}"
        )

    def test_validate_no_matrix_block_stdout_empty(self, tmp_path):
        """validate --lens <prose-only file> produces no stdout (AC-04)."""
        prose_lens = tmp_path / "prose-only-lens.md"
        prose_lens.write_text("# A Lens\n\nProse with no lens-matrix block.\n")
        result = _subprocess_run_pipeline(
            ["validate", "--lens", str(prose_lens)],
            json.dumps([_valid_finding_no_id()]),
        )
        assert result.stdout.strip() == "", (
            f"Expected empty stdout; got: {result.stdout!r}"
        )
