"""Regression tests for the ``pipeline keep-confirmed`` command.

Covers the behavioural requirements for the confirmed-set filter:

1. Records with status ``verified`` pass through to stdout.
2. Records with status ``verified-pending-execution`` pass through to stdout.
3. Records with status ``rejected`` are dropped (do not appear on stdout).
4. Records with status ``rejected-as-nit`` are dropped (do not appear on stdout).
5. Records with status ``unresolvable`` are surfaced to stderr and excluded from stdout.
6. Malformed JSON input (non-array, non-dict items) causes a non-zero exit and a message on stderr.
"""

import json
import subprocess
import sys


def _run(records, *, extra_args=()):
    """Run ``pipeline keep-confirmed`` with *records* as stdin.

    Returns (stdout_parsed, stderr_text, returncode).
    ``stdout_parsed`` is None when stdout is not valid JSON.
    """
    cmd = [sys.executable, "-m", "fbk.pipeline", "keep-confirmed", *extra_args]
    result = subprocess.run(
        cmd,
        input=json.dumps(records),
        capture_output=True,
        text=True,
    )
    try:
        stdout_parsed = json.loads(result.stdout) if result.stdout.strip() else []
    except json.JSONDecodeError:
        stdout_parsed = None
    return stdout_parsed, result.stderr, result.returncode


def _make_record(status, *, title="A finding with enough context", finding_id="S-01"):
    """Return a minimal merged record with the given status."""
    return {
        "id": finding_id,
        "title": title,
        "status": status,
        "location": {"file": "src/foo.py", "start_line": 10},
        "type": "behavioral",
        "severity": "major",
        "mechanism": "Test mechanism for this finding",
        "consequence": "Test consequence for this finding",
        "evidence": "Test evidence",
    }


class TestKeepConfirmedVerified:
    """Records with status ``verified`` are kept on stdout."""

    def test_verified_passes_through(self):
        records = [_make_record("verified")]
        stdout, _stderr, rc = _run(records)
        assert rc == 0
        assert isinstance(stdout, list)
        assert len(stdout) == 1
        assert stdout[0]["status"] == "verified"

    def test_verified_preserves_all_fields(self):
        record = _make_record("verified")
        record["verification_evidence"] = "Confirmed by inspection of line 42"
        stdout, _stderr, rc = _run([record])
        assert rc == 0
        assert stdout[0]["verification_evidence"] == "Confirmed by inspection of line 42"


class TestKeepConfirmedVerifiedPendingExecution:
    """Records with status ``verified-pending-execution`` are kept on stdout."""

    def test_verified_pending_execution_passes_through(self):
        records = [_make_record("verified-pending-execution")]
        stdout, _stderr, rc = _run(records)
        assert rc == 0
        assert len(stdout) == 1
        assert stdout[0]["status"] == "verified-pending-execution"


class TestKeepConfirmedRejected:
    """Records with status ``rejected`` are silently dropped from stdout."""

    def test_rejected_not_on_stdout(self):
        records = [_make_record("rejected")]
        stdout, _stderr, rc = _run(records)
        assert rc == 0
        assert stdout == []

    def test_rejected_produces_no_stderr_notice(self):
        # The challenger already logged its rationale; we do not duplicate it.
        records = [_make_record("rejected")]
        _stdout, stderr, rc = _run(records)
        assert rc == 0
        assert "rejected" not in stderr.lower()


class TestKeepConfirmedRejectedAsNit:
    """Records with status ``rejected-as-nit`` are silently dropped from stdout."""

    def test_rejected_as_nit_not_on_stdout(self):
        records = [_make_record("rejected-as-nit")]
        stdout, _stderr, rc = _run(records)
        assert rc == 0
        assert stdout == []

    def test_rejected_as_nit_produces_no_stderr_notice(self):
        records = [_make_record("rejected-as-nit")]
        _stdout, stderr, rc = _run(records)
        assert rc == 0
        assert "rejected" not in stderr.lower()


class TestKeepConfirmedUnresolvable:
    """Records with status ``unresolvable`` appear on stderr and not on stdout."""

    def test_unresolvable_not_on_stdout(self):
        records = [_make_record("unresolvable", finding_id="S-03")]
        stdout, _stderr, rc = _run(records)
        assert rc == 0
        assert stdout == []

    def test_unresolvable_surfaced_to_stderr(self):
        records = [_make_record("unresolvable", finding_id="S-03")]
        _stdout, stderr, rc = _run(records)
        assert rc == 0
        assert "UNRESOLVABLE" in stderr
        assert "S-03" in stderr

    def test_unresolvable_includes_title_in_stderr(self):
        records = [_make_record("unresolvable", title="A finding with enough context")]
        _stdout, stderr, rc = _run(records)
        assert "A finding with enough context" in stderr


class TestKeepConfirmedMixedInput:
    """With a mixed batch, only confirmed findings reach stdout."""

    def test_mixed_statuses_only_confirmed_on_stdout(self):
        records = [
            _make_record("verified", finding_id="S-01"),
            _make_record("rejected", finding_id="S-02"),
            _make_record("rejected-as-nit", finding_id="S-03"),
            _make_record("unresolvable", finding_id="S-04"),
            _make_record("verified-pending-execution", finding_id="S-05"),
        ]
        stdout, stderr, rc = _run(records)
        assert rc == 0
        assert len(stdout) == 2
        statuses = {r["status"] for r in stdout}
        assert statuses == {"verified", "verified-pending-execution"}
        assert "UNRESOLVABLE" in stderr

    def test_empty_input_produces_empty_output(self):
        stdout, _stderr, rc = _run([])
        assert rc == 0
        assert stdout == []


class TestKeepConfirmedMalformedInput:
    """Malformed input causes a non-zero exit and an error message on stderr."""

    def test_non_json_input_exits_nonzero(self):
        cmd = [sys.executable, "-m", "fbk.pipeline", "keep-confirmed"]
        result = subprocess.run(
            cmd,
            input="not valid json at all",
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "ERROR" in result.stderr

    def test_non_dict_item_exits_nonzero(self):
        records_with_string = ["this is not a dict"]
        cmd = [sys.executable, "-m", "fbk.pipeline", "keep-confirmed"]
        result = subprocess.run(
            cmd,
            input=json.dumps(records_with_string),
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "ERROR" in result.stderr

    def test_non_dict_item_error_names_index(self):
        records_with_int = [42]
        cmd = [sys.executable, "-m", "fbk.pipeline", "keep-confirmed"]
        result = subprocess.run(
            cmd,
            input=json.dumps(records_with_int),
            capture_output=True,
            text=True,
        )
        assert "index 0" in result.stderr
