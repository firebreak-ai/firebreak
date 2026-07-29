"""Tests for the `pipeline rejoin` subcommand.

The rejoin subcommand overlays challenger verdicts onto kept findings by position.
Position is the only correlation key — a reversal, off-by-one, or always-verdict[0]
bug must fail on every record, not just the first.

These tests are RED before implementation: `pipeline rejoin` does not exist yet,
so argparse exits non-zero on the unknown subcommand.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

# Resolve the fbk.py dispatcher the same way other pipeline tests do.
sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fbk_py():
    """Return the absolute path to the fbk.py dispatcher."""
    return Path(__file__).parent.parent / "fbk.py"


def _run_rejoin(kept_list, verdicts_list, tmp_path):
    """Run `fbk.py pipeline rejoin --verdicts <file>` with kept findings on stdin.

    Writes verdicts_list as JSON to tmp_path/verdicts.json, passes kept_list as
    JSON on stdin. Returns the CompletedProcess so callers can inspect returncode,
    stdout, and stderr.
    """
    verdicts_file = tmp_path / "verdicts.json"
    verdicts_file.write_text(json.dumps(verdicts_list))

    fbk_py = _fbk_py()
    if not fbk_py.exists():
        pytest.skip("fbk.py dispatcher not found")

    return subprocess.run(
        [sys.executable, str(fbk_py), "pipeline", "rejoin", "--verdicts", str(verdicts_file)],
        input=json.dumps(kept_list),
        capture_output=True,
        text=True,
        timeout=15,
    )


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------

def _make_kept_finding(index, type_="behavioral", severity="major"):
    """Return a kept finding with known per-index neutral-field values.

    The neutral fields carry distinct sentinel values per index so tests can
    assert the merged output retains them from the kept finding, not from a verdict.
    """
    return {
        "id": f"F-0{index + 1}",
        "title": f"Kept finding {index} title text here",
        "location": {"file": f"src/module_{index}.py", "start_line": 10 + index},
        "type": type_,
        "severity": severity,
        "mechanism": f"MECHANISM-KEPT-{index}-AAAAAAAAAA",
        "consequence": f"CONSEQUENCE-KEPT-{index}-AAAAAAAAAA",
        "evidence": f"EVIDENCE-KEPT-{index}-AAAAAAAAAA",
        "source_of_truth_ref": f"SOT-REF-KEPT-{index}-AAAAAAAAAA",
    }


def _make_verdict(status, verification_evidence, adjacent_observations,
                  rejection_reason=None, reclassified_from=None,
                  type_override=None, severity_override=None):
    """Return a verdict dict with the given fields set.

    Fields not provided are omitted or set to their natural empty/None equivalent
    so tests can assert on presence or absence precisely.
    """
    verdict = {
        "status": status,
        "verification_evidence": verification_evidence,
        "adjacent_observations": adjacent_observations,
    }
    if rejection_reason is not None:
        verdict["rejection_reason"] = rejection_reason
    if reclassified_from is not None:
        verdict["reclassified_from"] = reclassified_from
    if type_override is not None:
        verdict["type"] = type_override
    if severity_override is not None:
        verdict["severity"] = severity_override
    return verdict


def _make_verdict_with_neutral_sentinels(status, verification_evidence,
                                         adjacent_observations):
    """Return a verdict that also carries sentinel-different values for all six
    neutral fields. Used to prove neutral fields are never copied back from a verdict.
    """
    verdict = _make_verdict(status, verification_evidence, adjacent_observations)
    verdict["mechanism"] = "MECHANISM-VERDICT-SENTINEL-AAAA"
    verdict["consequence"] = "CONSEQUENCE-VERDICT-SENTINEL-AAA"
    verdict["evidence"] = "EVIDENCE-VERDICT-SENTINEL-AAAAAAA"
    verdict["type"] = "NEUTRAL-TYPE-SENTINEL"
    verdict["severity"] = "NEUTRAL-SEVERITY-SENTINEL"
    verdict["source_of_truth_ref"] = "SOT-REF-VERDICT-SENTINEL-AAAA"
    return verdict


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRejoinPositionRigor:
    """Overlay is applied by position; per-index sentinels catch reversal and off-by-one bugs."""

    def test_three_kept_three_verdicts_each_index_carries_its_own_sentinels(self, tmp_path):
        """rejoin with 3 kept findings and 3 verdicts exits zero, returns 3 merged records,
        and each merged record[i] carries verdict[i]'s exact status, verification_evidence,
        and adjacent_observations — not another verdict's.

        The distinct per-index verification_evidence sentinels mean a reversal, off-by-one,
        or always-verdict[0] bug fails on every record, not just the first.
        """
        kept = [_make_kept_finding(i) for i in range(3)]

        verdicts = [
            _make_verdict(
                status="verified",
                verification_evidence="EVIDENCE-ALPHA-0123456789",
                adjacent_observations="ADJ-ALPHA",
            ),
            _make_verdict(
                status="rejected",
                verification_evidence="EVIDENCE-BRAVO-0123456789",
                adjacent_observations="ADJ-BRAVO",
                rejection_reason="REASON-BRAVO-0123456789",
            ),
            _make_verdict(
                status="unresolvable",
                verification_evidence="EVIDENCE-CHARLIE-012345678",
                adjacent_observations="ADJ-CHARLIE",
            ),
        ]

        result = _run_rejoin(kept, verdicts, tmp_path)

        assert result.returncode == 0, (
            f"Expected exit 0; got {result.returncode}. stderr: {result.stderr!r}"
        )

        merged = json.loads(result.stdout)
        assert len(merged) == 3, (
            f"Expected 3 merged records, got {len(merged)}"
        )

        # Record 0: verdict 0 sentinels (verified / ALPHA)
        assert merged[0]["status"] == "verified", (
            f"merged[0] status: expected 'verified', got {merged[0].get('status')!r}"
        )
        assert merged[0]["verification_evidence"] == "EVIDENCE-ALPHA-0123456789", (
            f"merged[0] verification_evidence: expected ALPHA sentinel, "
            f"got {merged[0].get('verification_evidence')!r}"
        )
        assert merged[0]["adjacent_observations"] == "ADJ-ALPHA", (
            f"merged[0] adjacent_observations: expected ADJ-ALPHA, "
            f"got {merged[0].get('adjacent_observations')!r}"
        )

        # Record 1: verdict 1 sentinels (rejected / BRAVO)
        assert merged[1]["status"] == "rejected", (
            f"merged[1] status: expected 'rejected', got {merged[1].get('status')!r}"
        )
        assert merged[1]["verification_evidence"] == "EVIDENCE-BRAVO-0123456789", (
            f"merged[1] verification_evidence: expected BRAVO sentinel, "
            f"got {merged[1].get('verification_evidence')!r}"
        )
        assert merged[1]["adjacent_observations"] == "ADJ-BRAVO", (
            f"merged[1] adjacent_observations: expected ADJ-BRAVO, "
            f"got {merged[1].get('adjacent_observations')!r}"
        )
        assert merged[1]["rejection_reason"] == "REASON-BRAVO-0123456789", (
            f"merged[1] rejection_reason: expected BRAVO reason sentinel, "
            f"got {merged[1].get('rejection_reason')!r}"
        )

        # Record 2: verdict 2 sentinels (unresolvable / CHARLIE)
        assert merged[2]["status"] == "unresolvable", (
            f"merged[2] status: expected 'unresolvable', got {merged[2].get('status')!r}"
        )
        assert merged[2]["verification_evidence"] == "EVIDENCE-CHARLIE-012345678", (
            f"merged[2] verification_evidence: expected CHARLIE sentinel, "
            f"got {merged[2].get('verification_evidence')!r}"
        )
        assert merged[2]["adjacent_observations"] == "ADJ-CHARLIE", (
            f"merged[2] adjacent_observations: expected ADJ-CHARLIE, "
            f"got {merged[2].get('adjacent_observations')!r}"
        )


class TestRejoinNeutralFieldProtection:
    """The six neutral fields (mechanism, consequence, evidence, type, severity,
    source_of_truth_ref) are never copied back from verdicts to merged records.
    """

    def test_neutral_fields_come_from_kept_findings_not_verdicts(self, tmp_path):
        """When verdicts carry sentinel-different values for all six neutral fields,
        each merged record's six neutral fields equal the kept finding's values — not
        the verdict's. Merged evidence equals kept evidence byte-for-byte.
        """
        kept = [_make_kept_finding(i) for i in range(3)]

        # Verdicts carry neutral fields with DIFFERENT sentinel values than kept findings.
        # If rejoin copies any neutral field from the verdict, it will be caught.
        verdicts = [
            _make_verdict_with_neutral_sentinels(
                status="verified",
                verification_evidence="EVIDENCE-ALPHA-0123456789",
                adjacent_observations="ADJ-ALPHA",
            ),
            _make_verdict_with_neutral_sentinels(
                status="verified",
                verification_evidence="EVIDENCE-BRAVO-0123456789",
                adjacent_observations="ADJ-BRAVO",
            ),
            _make_verdict_with_neutral_sentinels(
                status="verified",
                verification_evidence="EVIDENCE-CHARLIE-012345678",
                adjacent_observations="ADJ-CHARLIE",
            ),
        ]

        result = _run_rejoin(kept, verdicts, tmp_path)

        assert result.returncode == 0, (
            f"Expected exit 0; got {result.returncode}. stderr: {result.stderr!r}"
        )

        merged = json.loads(result.stdout)
        assert len(merged) == 3, f"Expected 3 merged records, got {len(merged)}"

        for i, (m, k) in enumerate(zip(merged, kept)):
            assert m["mechanism"] == k["mechanism"], (
                f"merged[{i}] mechanism should equal kept's '{k['mechanism']}', "
                f"got '{m.get('mechanism')}'"
            )
            assert m["consequence"] == k["consequence"], (
                f"merged[{i}] consequence should equal kept's '{k['consequence']}', "
                f"got '{m.get('consequence')}'"
            )
            # evidence byte-for-byte equality
            assert m["evidence"] == k["evidence"], (
                f"merged[{i}] evidence must equal kept byte-for-byte: "
                f"expected '{k['evidence']}', got '{m.get('evidence')}'"
            )
            assert m["source_of_truth_ref"] == k["source_of_truth_ref"], (
                f"merged[{i}] source_of_truth_ref should equal kept's "
                f"'{k['source_of_truth_ref']}', got '{m.get('source_of_truth_ref')}'"
            )
            # type and severity from kept (verdicts carry sentinel-different values;
            # reclassified_from is absent so reclassification rule does not apply)
            assert m["type"] == k["type"], (
                f"merged[{i}] type should equal kept's '{k['type']}' "
                f"(no reclassified_from in verdict), got '{m.get('type')}'"
            )
            assert m["severity"] == k["severity"], (
                f"merged[{i}] severity should equal kept's '{k['severity']}' "
                f"(no reclassified_from in verdict), got '{m.get('severity')}'"
            )


class TestRejoinReclassification:
    """Overlay type/severity only when reclassified_from is a non-empty object."""

    def test_non_empty_reclassified_from_overlays_type_and_severity(self, tmp_path):
        """When a verdict carries a non-empty reclassified_from object, the merged record
        takes the verdict's new type and severity, and reclassified_from is carried
        onto the merged record exactly.
        """
        kept = [_make_kept_finding(0, type_="behavioral", severity="major")]

        verdicts = [
            _make_verdict(
                status="verified",
                verification_evidence="EVIDENCE-RECLASS-OVERLAY",
                adjacent_observations="ADJ-RECLASS",
                reclassified_from={"type": "behavioral", "severity": "major"},
                type_override="structural",
                severity_override="minor",
            )
        ]

        result = _run_rejoin(kept, verdicts, tmp_path)

        assert result.returncode == 0, (
            f"Expected exit 0; got {result.returncode}. stderr: {result.stderr!r}"
        )

        merged = json.loads(result.stdout)
        assert len(merged) == 1, f"Expected 1 merged record, got {len(merged)}"

        m = merged[0]
        assert m["type"] == "structural", (
            f"Expected overlaid type 'structural', got '{m.get('type')}'"
        )
        assert m["severity"] == "minor", (
            f"Expected overlaid severity 'minor', got '{m.get('severity')}'"
        )
        assert m.get("reclassified_from") == {"type": "behavioral", "severity": "major"}, (
            f"Expected reclassified_from carried exactly, got {m.get('reclassified_from')!r}"
        )

    def test_empty_reclassified_from_retains_kept_type_and_severity(self, tmp_path):
        """When a verdict carries reclassified_from == {}, the merged record retains the
        kept finding's original type and severity even if the verdict body carries
        different type/severity values. No reclassified_from is carried onto the merged record.
        """
        kept = [_make_kept_finding(0, type_="behavioral", severity="major")]

        # Verdict has different type/severity but empty reclassified_from — must NOT override.
        verdicts = [
            _make_verdict(
                status="verified",
                verification_evidence="EVIDENCE-NO-RECLASS",
                adjacent_observations="ADJ-NO-RECLASS",
                reclassified_from={},
                type_override="structural",
                severity_override="minor",
            )
        ]

        result = _run_rejoin(kept, verdicts, tmp_path)

        assert result.returncode == 0, (
            f"Expected exit 0; got {result.returncode}. stderr: {result.stderr!r}"
        )

        merged = json.loads(result.stdout)
        assert len(merged) == 1, f"Expected 1 merged record, got {len(merged)}"

        m = merged[0]
        assert m["type"] == "behavioral", (
            f"Expected kept type 'behavioral' retained (empty reclassified_from), "
            f"got '{m.get('type')}'"
        )
        assert m["severity"] == "major", (
            f"Expected kept severity 'major' retained (empty reclassified_from), "
            f"got '{m.get('severity')}'"
        )
        # reclassified_from should not be carried (or carried empty)
        rf = m.get("reclassified_from")
        assert not rf, (
            f"Expected no reclassified_from on merged record (empty reclassified_from "
            f"in verdict), got {rf!r}"
        )


class TestRejoinCountGuard:
    """Count guard rejects any mismatch between kept findings and verdicts, in either direction."""

    def test_more_verdicts_than_kept_exits_nonzero_naming_both_counts(self, tmp_path):
        """Three kept findings with four verdicts: exit non-zero and stderr names
        both the kept count (3) and the verdict count (4).
        """
        kept = [_make_kept_finding(i) for i in range(3)]
        verdicts = [
            _make_verdict("verified", f"EVIDENCE-GUARD-{i}", f"ADJ-{i}")
            for i in range(4)
        ]

        result = _run_rejoin(kept, verdicts, tmp_path)

        assert result.returncode != 0, (
            f"Expected non-zero exit for 3 kept / 4 verdicts mismatch; "
            f"got returncode {result.returncode}"
        )
        assert "3" in result.stderr, (
            f"Expected stderr to name kept count '3'; got: {result.stderr!r}"
        )
        assert "4" in result.stderr, (
            f"Expected stderr to name verdict count '4'; got: {result.stderr!r}"
        )

    def test_fewer_verdicts_than_kept_exits_nonzero_naming_both_counts(self, tmp_path):
        """Three kept findings with two verdicts: exit non-zero and stderr names
        both the kept count (3) and the verdict count (2).
        """
        kept = [_make_kept_finding(i) for i in range(3)]
        verdicts = [
            _make_verdict("verified", f"EVIDENCE-GUARD-{i}", f"ADJ-{i}")
            for i in range(2)
        ]

        result = _run_rejoin(kept, verdicts, tmp_path)

        assert result.returncode != 0, (
            f"Expected non-zero exit for 3 kept / 2 verdicts mismatch; "
            f"got returncode {result.returncode}"
        )
        assert "3" in result.stderr, (
            f"Expected stderr to name kept count '3'; got: {result.stderr!r}"
        )
        assert "2" in result.stderr, (
            f"Expected stderr to name verdict count '2'; got: {result.stderr!r}"
        )
