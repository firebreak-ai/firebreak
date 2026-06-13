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
        # The missing path must be routed to findings (non-blocking), never to failures.
        assert result.get("failures", []) == [], (
            "A 'missing' discrepancy must not appear in failures"
        )
        assert any("test_module" in f for f in result.get("findings", [])), (
            "A 'missing' discrepancy must surface in findings so the operator can see it"
        )

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
