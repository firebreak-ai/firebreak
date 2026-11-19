"""
Tests for --lens flag on the pipeline validate and run commands (AC-01, AC-03, AC-04, AC-11).

Covers:
  AC-01: lens-required set accepts id-less finding; no-lens rejects with
         "missing field 'id'"
  AC-03: missing lens exits non-zero with "lens not found:" before any
         finding is processed
  AC-04: no-matrix-block lens exits non-zero with "no lens-matrix block
         found in:" before any finding is processed
  AC-11: code-lens path on validate and run accepts id-less findings
"""

import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _fbk_py():
    """Return the path to the fbk.py dispatcher."""
    return Path(__file__).parent.parent / "fbk.py"


if not _fbk_py().is_file():
    raise FileNotFoundError(f"Required fbk.py dispatcher not found: {_fbk_py()}")


def _lens(name):
    """Return the repo-relative path for a named lens file.

    Example: _lens("code-lens.md") resolves to
    <repo-root>/assets/fbk-docs/fbk-review-lenses/code-lens.md
    """
    return Path(__file__).parents[3] / "assets" / "fbk-docs" / "fbk-review-lenses" / name


# ---------------------------------------------------------------------------
# Subprocess helper
# ---------------------------------------------------------------------------

def _run(args, stdin_data):
    """Run `python fbk.py pipeline <args>` with stdin_data as a string.

    Returns the CompletedProcess. Hard timeout is 15 seconds per invocation.
    """
    import subprocess
    fbk_py = _fbk_py()
    return subprocess.run(
        [sys.executable, str(fbk_py), "pipeline"] + args,
        input=stdin_data,
        capture_output=True,
        text=True,
        timeout=15,
    )


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _id_less_valid_code_finding():
    """Return a finding that satisfies the code-lens required set but has NO 'id'.

    The code-lens required set is:
      title, location, type, severity, mechanism, consequence, evidence
    — no 'id'. The type/severity combination (behavioral/major) is valid
    in both the code-lens matrix and the module-level VALID_COMBINATIONS.
    """
    return {
        "title": "Missing boundary check on input slice",
        "location": {"file": "src/processor.py", "start_line": 42},
        "type": "behavioral",
        "severity": "major",
        "mechanism": "The processor reads past the end of the input slice when the offset parameter exceeds the buffer length.",
        "consequence": "Downstream consumers receive truncated data and may produce incorrect output silently.",
        "evidence": "processor.py:42 — offset += step without bounds check",
    }


def _id_less_valid_run_finding():
    """Return an id-less finding suitable for the run command with behavioral-only preset.

    behavioral/major satisfies the code-lens required set, the behavioral-only
    preset domain filter, and the minor-or-above severity filter.
    """
    return {
        "title": "Unguarded state mutation on concurrent request",
        "location": {"file": "src/handler.py", "start_line": 18},
        "type": "behavioral",
        "severity": "major",
        "mechanism": "The request handler mutates shared state without a lock, allowing a second request to observe a partial write.",
        "consequence": "Concurrent requests produce inconsistent responses that depend on scheduling order.",
        "evidence": "handler.py:18 — shared_state[key] = value with no synchronization",
    }


def _id_less_missing_mechanism():
    """Return an id-less finding that is missing the 'mechanism' field.

    Used in ordering-proof tests to prove that the lens error fires before
    any finding is read — even one that would otherwise be rejected.
    """
    return {
        "title": "Missing input sanitization on user data",
        "location": {"file": "src/sanitizer.py", "start_line": 7},
        "type": "behavioral",
        "severity": "major",
        # mechanism is intentionally absent
        "consequence": "Unsanitized user data reaches the output layer and may cause rendering defects.",
        "evidence": "sanitizer.py:7 — pass-through with no sanitization call",
    }


# ---------------------------------------------------------------------------
# AC-01 / AC-11: id-less acceptance under lens (validate)
# ---------------------------------------------------------------------------

class TestIdLessAcceptanceUnderLens:
    """validate --lens code-lens.md accepts an id-less finding and assigns an S-NN id."""

    def test_validate_with_lens_accepts_id_less_finding(self):
        """validate --lens code-lens.md over an id-less otherwise-valid finding exits 0.

        The code-lens required set omits 'id'. An id-less finding with all
        other required fields present and min-lengths met must be accepted.
        Stdout must be a JSON list of length 1; the single record's 'id'
        must match the S-NN pattern assigned by the pipeline.
        """
        lens_path = _lens("code-lens.md")
        finding = _id_less_valid_code_finding()
        result = _run(["validate", "--lens", str(lens_path)], json.dumps([finding]))

        assert result.returncode == 0, (
            f"Expected exit 0 for valid id-less finding with lens; "
            f"got {result.returncode}. stderr: {result.stderr!r}"
            f"\nargv: {result.args!r}\nstdout: {result.stdout!r}"
        )

        records = json.loads(result.stdout)
        assert len(records) == 1, (
            f"Expected stdout list of length 1, got {len(records)}. "
            f"stdout: {result.stdout!r}"
        )
        assigned_id = records[0].get("id", "")
        assert re.match(r"^S-\d{2}$", assigned_id), (
            f"Expected assigned id to match S-NN pattern, got: {assigned_id!r}"
        )


# ---------------------------------------------------------------------------
# AC-01: no-lens rejects id-less finding (validate, no --lens)
# ---------------------------------------------------------------------------

class TestNoLensRejectsIdLessFinding:
    """validate without --lens rejects an id-less finding with 'missing field id'."""

    def test_validate_without_lens_rejects_id_less_finding(self):
        """validate (no --lens) over an id-less finding exits 0 but stdout is empty list.

        Without a lens, the built-in required set includes 'id'. The finding
        is rejected; stdout is an empty JSON list; stderr contains
        "missing field 'id'".
        """
        finding = _id_less_valid_code_finding()
        result = _run(["validate"], json.dumps([finding]))

        assert result.returncode == 0, (
            f"Expected exit 0 (command runs, finding rejected); "
            f"got {result.returncode}. stderr: {result.stderr!r}"
            f"\nargv: {result.args!r}\nstdout: {result.stdout!r}"
        )

        records = json.loads(result.stdout)
        assert records == [], (
            f"Expected empty list when id-less finding is rejected without lens; "
            f"got: {records!r}"
        )

        assert "missing field 'id'" in result.stderr, (
            f"Expected \"missing field 'id'\" in stderr; got: {result.stderr!r}"
        )


# ---------------------------------------------------------------------------
# AC-11: run acceptance under lens
# ---------------------------------------------------------------------------

class TestRunAcceptanceUnderLens:
    """run --preset behavioral-only --min-severity minor --lens code-lens.md accepts id-less finding."""

    def test_run_with_lens_accepts_id_less_finding(self):
        """run --lens code-lens.md over a behavioral/major id-less finding exits 0.

        The code-lens required set omits 'id'. With the behavioral-only preset
        and minor-or-above severity filter, a behavioral/major finding passes
        all pipeline stages. Stdout must be a JSON list of length 1.
        """
        lens_path = _lens("code-lens.md")
        finding = _id_less_valid_run_finding()
        result = _run(
            ["run", "--preset", "behavioral-only", "--min-severity", "minor",
             "--lens", str(lens_path)],
            json.dumps([finding]),
        )

        assert result.returncode == 0, (
            f"Expected exit 0 for valid id-less finding through run with lens; "
            f"got {result.returncode}. stderr: {result.stderr!r}"
            f"\nargv: {result.args!r}\nstdout: {result.stdout!r}"
        )

        records = json.loads(result.stdout)
        assert len(records) == 1, (
            f"Expected stdout list of length 1, got {len(records)}. "
            f"stdout: {result.stdout!r}"
        )


# ---------------------------------------------------------------------------
# AC-03 / AC-04: ordering-proof tests — lens failure is the SOLE stderr line
#
# These tests send a deliberately bad payload alongside a bad lens and assert
# that the lens error appears before stdin is read. The "sole stderr line"
# assertion is the crux: if any finding-processing diagnostic appears
# (REJECTED:, ERROR: malformed JSON input, a traceback) the ordering contract
# is violated.
# ---------------------------------------------------------------------------

def _assert_sole_stderr_line(result, expected_message, label):
    """Assert that stderr contains exactly one non-empty line and it is expected_message.

    Also asserts that no REJECTED: line, no "ERROR: malformed JSON input", and
    no traceback marker ("Traceback") appears in stderr.
    """
    non_empty_lines = [l for l in result.stderr.splitlines() if l.strip()]
    assert len(non_empty_lines) == 1, (
        f"{label}: expected exactly one non-empty stderr line; "
        f"got {len(non_empty_lines)}: {result.stderr!r}"
    )
    assert non_empty_lines[0] == expected_message, (
        f"{label}: expected sole stderr line to be {expected_message!r}; "
        f"got: {non_empty_lines[0]!r}"
    )
    assert "REJECTED:" not in result.stderr, (
        f"{label}: REJECTED: line present — stdin was read before lens failure"
    )
    assert "ERROR: malformed JSON input" not in result.stderr, (
        f"{label}: 'ERROR: malformed JSON input' present — stdin was read before lens failure"
    )
    assert "Traceback" not in result.stderr, (
        f"{label}: traceback present in stderr: {result.stderr!r}"
    )


class TestOrderingProofMissingLens:
    """Lens must fail before stdin is read: missing lens + malformed stdin.

    Malformed stdin (non-JSON) is sent alongside a missing lens path.
    The sole stderr output must be the 'lens not found:' message — no
    JSON parse error, no REJECTED: line, no traceback.
    """

    def test_validate_missing_lens_sole_stderr_before_stdin(self, tmp_path):
        """validate --lens <missing> with malformed stdin: sole stderr is 'lens not found: <path>'."""
        missing = tmp_path / "nonexistent-lens.md"
        expected_message = f"lens not found: {missing}"
        result = _run(["validate", "--lens", str(missing)], "not json at all")

        assert result.returncode != 0, (
            f"Expected non-zero exit; got 0. stderr: {result.stderr!r}"
            f"\nargv: {result.args!r}\nstdout: {result.stdout!r}"
        )
        assert result.stdout.strip() == "", (
            f"Expected empty stdout; got: {result.stdout!r}"
        )
        _assert_sole_stderr_line(result, expected_message, "validate+missing-lens+malformed-stdin")

    def test_run_missing_lens_sole_stderr_before_stdin(self, tmp_path):
        """run --lens <missing> with malformed stdin: sole stderr is 'lens not found: <path>'."""
        missing = tmp_path / "nonexistent-lens.md"
        expected_message = f"lens not found: {missing}"
        result = _run(
            ["run", "--preset", "behavioral-only", "--min-severity", "minor",
             "--lens", str(missing)],
            "not json at all",
        )

        assert result.returncode != 0, (
            f"Expected non-zero exit; got 0. stderr: {result.stderr!r}"
            f"\nargv: {result.args!r}\nstdout: {result.stdout!r}"
        )
        assert result.stdout.strip() == "", (
            f"Expected empty stdout; got: {result.stdout!r}"
        )
        _assert_sole_stderr_line(result, expected_message, "run+missing-lens+malformed-stdin")


class TestOrderingProofNoMatrixBlock:
    """Lens must fail before stdin is read: no-matrix-block lens + would-be-rejected finding.

    A finding missing 'mechanism' is sent alongside a no-matrix-block lens.
    The sole stderr output must be the 'no lens-matrix block found in:' message —
    no REJECTED: line for the missing-mechanism finding, no traceback.
    """

    def test_validate_no_matrix_block_sole_stderr_before_stdin(self, tmp_path):
        """validate --lens <no-matrix> with would-be-rejected finding: sole stderr is 'no lens-matrix block found in: <path>'."""
        prose_lens = tmp_path / "prose-only-lens.md"
        prose_lens.write_text(
            "# A Lens File\n\nThis file has prose but no lens-matrix block.\n"
        )
        expected_message = f"no lens-matrix block found in: {prose_lens}"
        finding = _id_less_missing_mechanism()
        result = _run(["validate", "--lens", str(prose_lens)], json.dumps([finding]))

        assert result.returncode != 0, (
            f"Expected non-zero exit; got 0. stderr: {result.stderr!r}"
            f"\nargv: {result.args!r}\nstdout: {result.stdout!r}"
        )
        assert result.stdout.strip() == "", (
            f"Expected empty stdout; got: {result.stdout!r}"
        )
        _assert_sole_stderr_line(
            result, expected_message,
            "validate+no-matrix-block+would-be-rejected-finding",
        )

    def test_run_no_matrix_block_sole_stderr_before_stdin(self, tmp_path):
        """run --lens <no-matrix> with would-be-rejected finding: sole stderr is 'no lens-matrix block found in: <path>'."""
        prose_lens = tmp_path / "prose-only-lens.md"
        prose_lens.write_text(
            "# A Lens File\n\nThis file has prose but no lens-matrix block.\n"
        )
        expected_message = f"no lens-matrix block found in: {prose_lens}"
        finding = _id_less_missing_mechanism()
        result = _run(
            ["run", "--preset", "behavioral-only", "--min-severity", "minor",
             "--lens", str(prose_lens)],
            json.dumps([finding]),
        )

        assert result.returncode != 0, (
            f"Expected non-zero exit; got 0. stderr: {result.stderr!r}"
            f"\nargv: {result.args!r}\nstdout: {result.stdout!r}"
        )
        assert result.stdout.strip() == "", (
            f"Expected empty stdout; got: {result.stdout!r}"
        )
        _assert_sole_stderr_line(
            result, expected_message,
            "run+no-matrix-block+would-be-rejected-finding",
        )
