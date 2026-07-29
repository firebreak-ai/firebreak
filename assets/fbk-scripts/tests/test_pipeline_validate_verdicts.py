"""Tests for the pipeline validate-verdicts subcommand.

validate-verdicts checks each challenger verdict's status against the five
allowed values and the evidence or reason its status requires, failing loudly
on a violation and passing a valid array through unchanged.

This closes the silent-loss path where a bad status word would slip past the
verified filter, causing the confirmed finding to vanish.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

# Mirror the import setup from test_pipeline.py so this file resolves the module
# the same way regardless of which directory pytest is invoked from.
sys.path.insert(0, str(Path(__file__).parent.parent))


def _fbk_py_path():
    """Return the path to the fbk.py dispatcher."""
    return Path(__file__).parent.parent / "fbk.py"


def _run(stdin_text):
    """Run `fbk.py pipeline validate-verdicts` with input on stdin.

    Returns the CompletedProcess so the caller can inspect stdout, stderr, and
    exit code. Raises on timeout (hard 15-second limit per invocation).
    """
    fbk_py = _fbk_py_path()
    if not fbk_py.exists():
        pytest.skip("fbk.py dispatcher not found")

    return subprocess.run(
        [sys.executable, str(fbk_py), "pipeline", "validate-verdicts"],
        input=stdin_text,
        capture_output=True,
        text=True,
        timeout=15,
    )


class TestValidateVerdicts:
    """Tests for the validate-verdicts subcommand."""

    def test_out_of_enum_status_fails_loudly(self):
        """Out-of-enum status fails non-zero with stderr naming the record.

        A status value outside the five allowed statuses (verified,
        verified-pending-execution, rejected, rejected-as-nit, unresolvable)
        must fail loud: non-zero exit and stderr names the offending record
        position and what failed.
        """
        verdict = {
            "status": "not-a-real-status",
            "verification_evidence": "evidence text here to pass length check"
        }
        verdicts = [verdict]
        stdin_text = json.dumps(verdicts)

        result = _run(stdin_text)

        assert result.returncode != 0, (
            f"Expected non-zero exit for invalid status, got exit {result.returncode}"
        )
        assert "0" in result.stderr or "index" in result.stderr.lower(), (
            f"Expected stderr to name the record position (0/index), got: {result.stderr!r}"
        )
        assert "not-a-real-status" in result.stderr or "status" in result.stderr.lower(), (
            f"Expected stderr to mention the status or the offending value, got: {result.stderr!r}"
        )

    def test_silent_loss_closed_approved_rejected_loudly(self):
        """SILENT-LOSS-CLOSED: 'approved' status rejected loudly, not dropped silently.

        'approved' is a plausible-but-not-real status. Before validate-verdicts,
        such a status would fail silently: the verified filter would reject it
        downstream and the finding would disappear. Now it must fail LOUDLY here
        with a named record, proving the bad status is caught and reported.
        """
        verdict = {
            "status": "approved",
            "verification_evidence": "evidence text here to pass length check"
        }
        verdicts = [verdict]
        stdin_text = json.dumps(verdicts)

        result = _run(stdin_text)

        assert result.returncode != 0, (
            f"Expected non-zero exit for 'approved' status, got exit {result.returncode}"
        )
        assert "0" in result.stderr or "record" in result.stderr.lower(), (
            f"Expected stderr to name the record, got: {result.stderr!r}"
        )

    def test_verified_with_empty_evidence_fails(self):
        """Verified without evidence (empty string) fails non-zero.

        AC-15: when status is 'verified', verification_evidence must be
        present and at least 10 characters. Empty string fails.
        """
        verdict = {
            "status": "verified",
            "verification_evidence": ""
        }
        verdicts = [verdict]
        stdin_text = json.dumps(verdicts)

        result = _run(stdin_text)

        assert result.returncode != 0, (
            f"Expected non-zero exit for empty evidence, got exit {result.returncode}"
        )
        assert "0" in result.stderr or "record" in result.stderr.lower(), (
            f"Expected stderr to name the record, got: {result.stderr!r}"
        )

    def test_verified_with_short_evidence_fails(self):
        """Verified with evidence under 10 characters fails non-zero.

        AC-15: when status is 'verified', verification_evidence must be at
        least 10 characters. Under-10-character evidence fails.
        """
        verdict = {
            "status": "verified",
            "verification_evidence": "short"
        }
        verdicts = [verdict]
        stdin_text = json.dumps(verdicts)

        result = _run(stdin_text)

        assert result.returncode != 0, (
            f"Expected non-zero exit for under-10-char evidence, got exit {result.returncode}"
        )
        assert "0" in result.stderr or "record" in result.stderr.lower(), (
            f"Expected stderr to name the record, got: {result.stderr!r}"
        )

    def test_verified_pending_execution_with_empty_evidence_fails(self):
        """Verified-pending-execution without evidence (empty string) fails non-zero.

        AC-15: when status is 'verified-pending-execution', verification_evidence
        must be present and at least 10 characters. Empty string fails.
        """
        verdict = {
            "status": "verified-pending-execution",
            "verification_evidence": ""
        }
        verdicts = [verdict]
        stdin_text = json.dumps(verdicts)

        result = _run(stdin_text)

        assert result.returncode != 0, (
            f"Expected non-zero exit for empty evidence, got exit {result.returncode}"
        )
        assert "0" in result.stderr or "record" in result.stderr.lower(), (
            f"Expected stderr to name the record, got: {result.stderr!r}"
        )

    def test_verified_pending_execution_with_short_evidence_fails(self):
        """Verified-pending-execution with evidence under 10 characters fails non-zero.

        AC-15: when status is 'verified-pending-execution', verification_evidence
        must be at least 10 characters. Under-10-character evidence fails.
        An implementation that only guards 'verified' must fail here.
        """
        verdict = {
            "status": "verified-pending-execution",
            "verification_evidence": "short"
        }
        verdicts = [verdict]
        stdin_text = json.dumps(verdicts)

        result = _run(stdin_text)

        assert result.returncode != 0, (
            f"Expected non-zero exit for under-10-char evidence, got exit {result.returncode}"
        )
        assert "0" in result.stderr or "record" in result.stderr.lower(), (
            f"Expected stderr to name the record, got: {result.stderr!r}"
        )

    def test_rejected_without_reason_fails(self):
        """Rejected verdict missing rejection_reason fails non-zero.

        AC-15: when status is 'rejected', rejection_reason must be present
        and at least 10 characters. Missing rejection_reason fails.
        """
        verdict = {
            "status": "rejected"
        }
        verdicts = [verdict]
        stdin_text = json.dumps(verdicts)

        result = _run(stdin_text)

        assert result.returncode != 0, (
            f"Expected non-zero exit for missing rejection_reason, got exit {result.returncode}"
        )
        assert "0" in result.stderr or "record" in result.stderr.lower(), (
            f"Expected stderr to name the record, got: {result.stderr!r}"
        )

    def test_rejected_with_short_reason_fails(self):
        """Rejected verdict with rejection_reason under 10 characters fails non-zero.

        AC-15: when status is 'rejected', rejection_reason must be at least
        10 characters. Under-10-character rejection_reason fails.
        """
        verdict = {
            "status": "rejected",
            "rejection_reason": "short"
        }
        verdicts = [verdict]
        stdin_text = json.dumps(verdicts)

        result = _run(stdin_text)

        assert result.returncode != 0, (
            f"Expected non-zero exit for under-10-char rejection_reason, got exit {result.returncode}"
        )
        assert "0" in result.stderr or "record" in result.stderr.lower(), (
            f"Expected stderr to name the record, got: {result.stderr!r}"
        )

    def test_all_valid_passthrough(self):
        """All-valid verdict array passes through unchanged with exit zero.

        An array covering multiple valid statuses (verified with sufficient
        evidence, rejected with sufficient reason, unresolvable) must exit
        zero and pass through stdout unchanged.
        """
        verdicts = [
            {
                "status": "verified",
                "verification_evidence": "sufficient evidence text for verification"
            },
            {
                "status": "rejected",
                "rejection_reason": "sufficient reason text for rejection"
            },
            {
                "status": "unresolvable"
            }
        ]
        stdin_text = json.dumps(verdicts)

        result = _run(stdin_text)

        assert result.returncode == 0, (
            f"Expected exit zero for all-valid array, got exit {result.returncode}. "
            f"stderr: {result.stderr!r}"
        )

        # Parse stdout and verify it matches input (passed through unchanged)
        output_list = json.loads(result.stdout)
        assert isinstance(output_list, list), (
            f"Expected stdout to be a JSON list, got: {type(output_list)}"
        )
        assert output_list == verdicts, (
            f"Expected stdout to match input verdicts unchanged, got: {output_list}"
        )

    def test_empty_array_passes(self):
        """Empty array passes with exit zero.

        An empty verdict array [] must exit zero and output [].
        """
        stdin_text = "[]"

        result = _run(stdin_text)

        assert result.returncode == 0, (
            f"Expected exit zero for empty array, got exit {result.returncode}. "
            f"stderr: {result.stderr!r}"
        )

        output_list = json.loads(result.stdout)
        assert output_list == [], (
            f"Expected stdout to be empty list, got: {output_list}"
        )
