"""Tests for fbk.gates.code_review validation logic."""

import json
import subprocess
import sys
import pytest
import hashlib
import datetime
from pathlib import Path

try:
    from fbk.gates.code_review import validate_code_review
except ImportError:
    validate_code_review = None

from fbk.gates.test_hash import create_manifest, verify_manifest


FBK_PY = Path(__file__).parent.parent / "fbk.py"

pytestmark = pytest.mark.skipif(
    validate_code_review is None,
    reason="fbk.gates.code_review not yet implemented",
)


def make_code_review_dir(tmp_path):
    """Create a minimal valid code-review artifact tree under tmp_path.

    Returns (tmp_path, feature_dir) where feature_dir is tmp_path/ai-docs/sample.

    The manifest locks only test_module.py (not the markdown artifacts) using
    list-driven lock mode — passing the tests/ subdir as scope and locked_files
    explicitly so that test-review-final.md is not swept into the manifest.
    """
    feature_dir = tmp_path / "ai-docs" / "sample"
    feature_dir.mkdir(parents=True)

    (feature_dir / "quality-scan.md").write_text(
        "# Quality Scan\n\nSeverity: minor\n\n"
        "1. Finding one — low impact\n"
        "2. Finding two — style\n"
        "3. Finding three — docs gap\n"
    )
    (feature_dir / "test-review-final.md").write_text(
        "# Test Review\n\nVerdict: accepted\n"
    )

    tests_dir = feature_dir / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_module.py").write_text("# test module\ndef test_placeholder(): pass\n")

    create_manifest(
        tests_dir,
        manifest_path=feature_dir / "test-hashes.json",
        locked_files=[str(tests_dir / "test_module.py")],
    )

    manifest = json.loads((feature_dir / "test-hashes.json").read_text())
    assert not any("test-review-final" in k for k in manifest.get("files", {})), (
        "test-review-final.md must not appear in the manifest — list-driven lock mode broke"
    )

    return tmp_path, feature_dir


# ---------------------------------------------------------------------------
# Passing case
# ---------------------------------------------------------------------------

class TestCodeReviewGatePasses:

    def test_all_artifacts_present_and_hashes_intact_passes(self, tmp_path):
        """Gate passes when quality-scan and test-review artifacts are present and hashes match."""
        _, feature_dir = make_code_review_dir(tmp_path)
        result = validate_code_review(str(feature_dir))
        assert result["result"] == "pass"


# ---------------------------------------------------------------------------
# Missing artifact failures
# ---------------------------------------------------------------------------

class TestMissingArtifacts:

    def test_missing_quality_scan_artifact_fails(self, tmp_path):
        """Gate fails when quality-scan.md is absent."""
        _, feature_dir = make_code_review_dir(tmp_path)
        (feature_dir / "quality-scan.md").unlink()
        result = validate_code_review(str(feature_dir))
        assert result["result"] == "fail"
        combined = " ".join(result.get("failures", [])).lower()
        assert "quality-scan" in combined or "quality scan" in combined

    def test_quality_scan_missing_severity_field_fails(self, tmp_path):
        """Gate fails when quality-scan.md exists but carries no Severity: field."""
        _, feature_dir = make_code_review_dir(tmp_path)
        (feature_dir / "quality-scan.md").write_text(
            "# Quality Scan\n\nNo severity information present.\n"
        )
        result = validate_code_review(str(feature_dir))
        assert result["result"] == "fail"

    def test_missing_test_review_verdict_fails(self, tmp_path):
        """Gate fails when the test-review artifact is absent."""
        _, feature_dir = make_code_review_dir(tmp_path)
        (feature_dir / "test-review-final.md").unlink()
        result = validate_code_review(str(feature_dir))
        assert result["result"] == "fail"


# ---------------------------------------------------------------------------
# Hash mismatch failures
# ---------------------------------------------------------------------------

class TestHashMismatch:

    def test_modified_locked_test_fails(self, tmp_path):
        """Gate fails when a locked test file has been modified since the manifest was written."""
        _, feature_dir = make_code_review_dir(tmp_path)
        (feature_dir / "tests" / "test_module.py").write_text(
            "# test module — tampered\ndef test_placeholder(): assert False\n"
        )
        result = validate_code_review(str(feature_dir))
        assert result["result"] == "fail"
        combined = " ".join(result.get("failures", [])).lower()
        assert "modified" in combined or "hash mismatch" in combined

    def test_shadow_test_fails(self, tmp_path):
        """Gate fails when an unlisted test file appears inside a locked directory."""
        _, feature_dir = make_code_review_dir(tmp_path)
        (feature_dir / "tests" / "test_shadow.py").write_text(
            "# shadow test\ndef test_shadow(): pass\n"
        )
        result = validate_code_review(str(feature_dir))
        assert result["result"] == "fail"
        combined = " ".join(result.get("failures", [])).lower()
        assert "shadow" in combined or "unexpected" in combined


# ---------------------------------------------------------------------------
# Non-failing conditions
# ---------------------------------------------------------------------------

class TestNonFailingConditions:

    def test_critical_severity_quality_finding_does_not_fail(self, tmp_path):
        """Critical-severity quality finding does not block the gate — it is for operator triage."""
        _, feature_dir = make_code_review_dir(tmp_path)
        (feature_dir / "quality-scan.md").write_text(
            "# Quality Scan\n\nSeverity: critical\n\n"
            "1. Critical finding requiring operator attention\n"
        )
        result = validate_code_review(str(feature_dir))
        assert result["result"] == "pass"

    def test_missing_hash_kind_discrepancy_does_not_fail(self, tmp_path):
        """A 'missing' hash discrepancy (manifest entry whose file is gone) surfaces as a
        finding but does not fail the gate — only 'modified' or 'unexpected' kinds fail."""
        _, feature_dir = make_code_review_dir(tmp_path)
        # Delete the locked test file so verify_manifest returns kind: missing
        (feature_dir / "tests" / "test_module.py").unlink()
        result = validate_code_review(str(feature_dir))
        assert result["result"] == "pass"
        # The missing path should appear somewhere in findings/warnings, not failures
        all_failures = result.get("failures", [])
        assert len(all_failures) == 0 or not any(
            "missing" in f.lower() and "fail" in f.lower() for f in all_failures
        )
        findings_or_warnings = result.get("findings", result.get("warnings", []))
        assert len(findings_or_warnings) > 0 or "test_module" not in str(result.get("failures", []))

    def test_test_review_drift_finding_does_not_fail_gate(self, tmp_path):
        """A test-review verdict whose body documents a drift finding does not fail the gate.

        Per AC-09/AC-11, only hash mismatches (modified/unexpected) or shadow tests fail the
        gate.  A needs-revision verdict flagging drift is for operator triage — not a blocker.
        """
        _, feature_dir = make_code_review_dir(tmp_path)
        (feature_dir / "test-review-final.md").write_text(
            "# Test Review\n\n"
            "Verdict: needs-revision\n\n"
            "## Finding: drift\n\n"
            "A locked test has drifted (renamed) but remains content-identical. "
            "Surface for operator triage per AC-11.\n"
        )
        result = validate_code_review(str(feature_dir))
        assert result["result"] == "pass"


# ---------------------------------------------------------------------------
# Delegation contract
# ---------------------------------------------------------------------------

class TestVerifyManifestDelegation:

    def test_hash_check_delegates_to_verify_manifest(self, tmp_path, monkeypatch):
        """Gate must delegate hash/shadow checking to test_hash.verify_manifest rather than
        re-implementing a second hash-comparison path (AC-08).

        Monkeypatching is used here specifically to verify the delegation contract — that the
        correct function is called with the correct arguments — not to stub hash-comparison
        behavior itself.  This is the only monkeypatched test in this file; all others use
        real files.
        """
        _, feature_dir = make_code_review_dir(tmp_path)

        calls = []

        import fbk.gates.test_hash as th

        def recording_verify_manifest(feature_dir_arg, manifest_path=None):
            calls.append({"feature_dir": feature_dir_arg, "manifest_path": manifest_path})
            return []

        monkeypatch.setattr(th, "verify_manifest", recording_verify_manifest)
        # Also patch the name as imported in code_review if it uses a direct import
        import fbk.gates.code_review as cr
        if hasattr(cr, "verify_manifest"):
            monkeypatch.setattr(cr, "verify_manifest", recording_verify_manifest)

        validate_code_review(str(feature_dir))

        assert len(calls) == 1, f"Expected verify_manifest called once, got {len(calls)} calls"
        first_call = calls[0]
        # The gate should pass feature_dir (as Path or str) as the first argument
        assert str(first_call["feature_dir"]) == str(feature_dir), (
            f"Expected feature_dir={feature_dir}, got {first_call['feature_dir']}"
        )
        # The call must NOT pass a second hand-rolled path that bypasses manifest_path=None default
        # (manifest_path may be None or the canonical default location — either is acceptable)


# ---------------------------------------------------------------------------
# Path guard (subprocess)
# ---------------------------------------------------------------------------

class TestPathGuard:

    def test_missing_feature_dir_exits_2(self, tmp_path):
        """Gate exits 2 when called with a non-existent feature directory."""
        nonexistent = str(tmp_path / "does_not_exist")
        proc = subprocess.run(
            [sys.executable, str(FBK_PY), "code-review-gate", nonexistent],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 2

    def test_binary_quality_scan_degrades_gracefully(self, tmp_path):
        """Gate does not raise an unhandled traceback when quality-scan.md contains binary data."""
        _, feature_dir = make_code_review_dir(tmp_path)
        (feature_dir / "quality-scan.md").write_bytes(b"\x00\xff\xfe\xfd binary garbage")
        proc = subprocess.run(
            [sys.executable, str(FBK_PY), "code-review-gate", str(feature_dir)],
            capture_output=True,
            text=True,
        )
        assert "Traceback" not in proc.stderr
        assert proc.returncode in (0, 2)


# ---------------------------------------------------------------------------
# CODE_REVIEW_ROUNDS event (AC-05, AC-27)
# ---------------------------------------------------------------------------

try:
    from fbk.capture import event_writer as _event_writer_module  # noqa: F401
    _EVENT_WRITER_AVAILABLE = True
except ImportError:
    _EVENT_WRITER_AVAILABLE = False


@pytest.mark.skipif(
    not _EVENT_WRITER_AVAILABLE,
    reason="fbk.capture.event_writer not available",
)
class TestCodeReviewRoundsEvent:
    """Gate emits a CODE_REVIEW_ROUNDS event when a valid round file is present.

    These tests run the gate as a subprocess with cwd set to an instrumented
    tmp project tree so that event writes land in <project>/.fbk-capture/events.jsonl.
    The feature dir lives under that project and the .code-review-rounds.json file
    sits in the feature dir.

    All assertions are integration-level — they exercise the real gate subprocess.
    """

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _make_instrumented_project(self, tmp_path):
        """Build a minimal instrumented project tree and return its root path.

        The sentinel .claude/automation/.fbk-managed marks the project as
        instrumented so the gate knows where to write events.
        """
        project_root = tmp_path / "project"
        sentinel = project_root / ".claude" / "automation" / ".fbk-managed"
        sentinel.parent.mkdir(parents=True)
        sentinel.write_text("")
        return project_root

    def _read_events(self, project_root):
        """Return all parsed event envelopes from <project_root>/.fbk-capture/events.jsonl.

        Returns an empty list when the events file does not exist.
        """
        events_file = project_root / ".fbk-capture" / "events.jsonl"
        if not events_file.exists():
            return []
        lines = events_file.read_text().splitlines()
        return [json.loads(line) for line in lines if line.strip()]

    def _rounds_events(self, project_root):
        """Filter events to CODE_REVIEW_ROUNDS entries only."""
        return [
            ev for ev in self._read_events(project_root)
            if ev.get("event_type") == "CODE_REVIEW_ROUNDS"
        ]

    def _run_gate(self, project_root, feature_dir):
        """Run the code-review-gate subprocess with cwd=project_root.

        Returns the CompletedProcess result.
        """
        return subprocess.run(
            [sys.executable, str(FBK_PY), "code-review-gate", str(feature_dir)],
            capture_output=True,
            text=True,
            cwd=str(project_root),
        )

    def _make_feature_dir_in_project(self, project_root):
        """Create the artifact tree inside the instrumented project and return feature_dir."""
        # Replicate make_code_review_dir but rooted under project_root instead of tmp_path.
        from fbk.gates.test_hash import create_manifest as _create_manifest

        feature_dir = project_root / "ai-docs" / "sample"
        feature_dir.mkdir(parents=True)

        (feature_dir / "quality-scan.md").write_text(
            "# Quality Scan\n\nSeverity: minor\n\n"
            "1. Finding one — low impact\n"
            "2. Finding two — style\n"
        )
        (feature_dir / "test-review-final.md").write_text(
            "# Test Review\n\nVerdict: accepted\n"
        )

        tests_dir = feature_dir / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_module.py").write_text(
            "# test module\ndef test_placeholder(): pass\n"
        )

        _create_manifest(
            tests_dir,
            manifest_path=feature_dir / "test-hashes.json",
            locked_files=[str(tests_dir / "test_module.py")],
        )

        return feature_dir

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_valid_round_file_emits_event(self, tmp_path):
        """Valid .code-review-rounds.json causes the gate to emit a CODE_REVIEW_ROUNDS
        event carrying the total counts; pass/fail is unchanged.

        At the default standard capture level the per-round breakdown (which can
        carry severity detail) is redacted, so only the aggregate totals survive.
        """
        project_root = self._make_instrumented_project(tmp_path)
        feature_dir = self._make_feature_dir_in_project(project_root)

        round_file = feature_dir / ".code-review-rounds.json"
        round_data = {
            "schema_version": "1.0",
            "spec": "sample",
            "rounds": [
                {"round": 1, "raised": 5, "survived": 2, "severity_breakdown": {"minor": 3, "major": 2}},
                {"round": 2, "raised": 1, "survived": 0, "severity_breakdown": {"minor": 1}},
            ],
        }
        round_file.write_text(json.dumps(round_data))

        proc = self._run_gate(project_root, feature_dir)

        # Gate pass/fail is unchanged — artifact tree is valid.
        assert proc.returncode == 0, f"Expected gate to pass; stderr: {proc.stderr}"

        rounds_events = self._rounds_events(project_root)
        assert len(rounds_events) == 1, (
            f"Expected exactly one CODE_REVIEW_ROUNDS event, got {len(rounds_events)}"
        )

        event = rounds_events[0]
        data = event["data"]

        # Total counts (the report's inputs): raised=6 (5+1), survived=2 (2+0).
        assert data.get("total_raised") == 6, (
            f"Expected total_raised=6, got {data.get('total_raised')!r}"
        )
        assert data.get("total_survived") == 2, (
            f"Expected total_survived=2, got {data.get('total_survived')!r}"
        )

        # Per-round detail is redacted at standard level — the breakdown that
        # could carry severity text must not survive on the recorded event.
        assert "rounds" not in data, (
            "per-round breakdown must be redacted at standard capture level; "
            f"data still carried it: {data!r}"
        )

    def test_absent_round_file_emits_no_event_unchanged_passfail(self, tmp_path):
        """With no .code-review-rounds.json present, the gate emits no CODE_REVIEW_ROUNDS event
        and gate pass/fail is unchanged.
        """
        project_root = self._make_instrumented_project(tmp_path)
        feature_dir = self._make_feature_dir_in_project(project_root)

        # Confirm the round file is absent.
        assert not (feature_dir / ".code-review-rounds.json").exists()

        proc = self._run_gate(project_root, feature_dir)

        # Gate still passes — artifact tree is valid.
        assert proc.returncode == 0, f"Expected gate to pass; stderr: {proc.stderr}"

        rounds_events = self._rounds_events(project_root)
        assert len(rounds_events) == 0, (
            f"Expected no CODE_REVIEW_ROUNDS event when round file is absent, "
            f"got {len(rounds_events)}"
        )

    def test_malformed_round_file_no_event_warns_unchanged(self, tmp_path):
        """An unparseable .code-review-rounds.json causes: no CODE_REVIEW_ROUNDS event,
        a warning on stderr, and gate pass/fail unchanged.
        """
        project_root = self._make_instrumented_project(tmp_path)
        feature_dir = self._make_feature_dir_in_project(project_root)

        (feature_dir / ".code-review-rounds.json").write_text("{ broken")

        proc = self._run_gate(project_root, feature_dir)

        # Gate pass/fail is unchanged — artifact tree is still valid.
        assert proc.returncode == 0, f"Expected gate to pass; stderr: {proc.stderr}"

        # No event written.
        rounds_events = self._rounds_events(project_root)
        assert len(rounds_events) == 0, (
            f"Expected no CODE_REVIEW_ROUNDS event for malformed round file, "
            f"got {len(rounds_events)}"
        )

        # A warning appears on stderr; no unhandled traceback.
        assert "Traceback" not in proc.stderr, "Malformed round file must not cause an unhandled traceback"
        assert proc.stderr.strip() != "", (
            "Expected a stderr warning for malformed round file, got no stderr output"
        )

    @pytest.mark.parametrize(
        "label,round_data_override",
        [
            (
                "negative_raised_count",
                {
                    "schema_version": "1.0",
                    "spec": "sample",
                    "rounds": [
                        {"round": 1, "raised": -1, "survived": 0, "severity_breakdown": {}},
                    ],
                },
            ),
            (
                "over_length_rounds_list",
                # 200 rounds is obviously past any reasonable maximum.
                {
                    "schema_version": "1.0",
                    "spec": "sample",
                    "rounds": [
                        {"round": i + 1, "raised": 1, "survived": 0, "severity_breakdown": {}}
                        for i in range(200)
                    ],
                },
            ),
        ],
    )
    def test_out_of_bounds_round_value_treated_malformed(self, tmp_path, label, round_data_override):
        """Out-of-bounds values in .code-review-rounds.json are treated as malformed:
        no CODE_REVIEW_ROUNDS event, a stderr warning, and gate pass/fail unchanged.

        Precise thresholds (max rounds list length, max file size) are implementation
        details not pinned here; the test exercises obviously-invalid inputs — a negative
        raised count and a rounds list of 200 entries.
        """
        project_root = self._make_instrumented_project(tmp_path)
        feature_dir = self._make_feature_dir_in_project(project_root)

        (feature_dir / ".code-review-rounds.json").write_text(json.dumps(round_data_override))

        proc = self._run_gate(project_root, feature_dir)

        # Gate pass/fail is unchanged — artifact tree is still valid.
        assert proc.returncode == 0, (
            f"[{label}] Expected gate to pass; stderr: {proc.stderr}"
        )

        # No event written for out-of-bounds input.
        rounds_events = self._rounds_events(project_root)
        assert len(rounds_events) == 0, (
            f"[{label}] Expected no CODE_REVIEW_ROUNDS event for out-of-bounds round file, "
            f"got {len(rounds_events)}"
        )

        # A warning appears on stderr; no unhandled traceback.
        assert "Traceback" not in proc.stderr, (
            f"[{label}] Out-of-bounds round file must not cause an unhandled traceback"
        )
        assert proc.stderr.strip() != "", (
            f"[{label}] Expected a stderr warning for out-of-bounds round file"
        )
