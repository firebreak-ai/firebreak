"""Tests for fbk.gates.coherence validation logic."""

import pytest
from pathlib import Path

try:
    from fbk.gates.coherence import validate_coherence
except ImportError:
    validate_coherence = None

pytestmark = pytest.mark.skipif(
    validate_coherence is None,
    reason="fbk.gates.coherence not yet implemented",
)


def make_feature_dir(tmp_path, body=None):
    """Create a feature dir under tmp_path/ai-docs/sample.

    When body is given, writes it to coherence-review.md inside the feature
    dir.  When body is None, no coherence-review.md is written — simulating
    the missing-file case.

    Returns the feature_dir Path.
    """
    feature_dir = tmp_path / "ai-docs" / "sample"
    feature_dir.mkdir(parents=True)
    if body is not None:
        (feature_dir / "coherence-review.md").write_text(body)
    return feature_dir


class TestAcceptedVerdictPasses:

    def test_accepted_verdict_passes(self, tmp_path):
        """Gate passes when coherence-review.md ends with Verdict: accepted."""
        feature_dir = make_feature_dir(
            tmp_path,
            body="# Coherence Review\n\nContracts reviewed.\n\nVerdict: accepted\n",
        )
        result = validate_coherence(str(feature_dir))
        assert result["result"] == "pass"


class TestMissingFileFails:

    def test_missing_file_fails(self, tmp_path):
        """Gate fails when coherence-review.md is absent, and names the file in failures."""
        feature_dir = make_feature_dir(tmp_path, body=None)
        result = validate_coherence(str(feature_dir))
        assert result["result"] == "fail"
        failures = result.get("failures", [])
        assert len(failures) > 0, "failures list must be non-empty when the file is missing"
        combined = " ".join(failures).lower()
        assert "coherence-review.md" in combined, (
            f"failure reason must name the missing file 'coherence-review.md'; got: {failures!r}"
        )


class TestMissingVerdictLineFails:

    def test_missing_verdict_line_fails(self, tmp_path):
        """Gate fails when coherence-review.md exists but contains no Verdict: line."""
        feature_dir = make_feature_dir(
            tmp_path,
            body="# Coherence Review\n\nSome prose about contracts and seams.\n",
        )
        result = validate_coherence(str(feature_dir))
        assert result["result"] == "fail"


class TestNonAcceptedVerdictFails:

    def test_needs_revision_verdict_fails(self, tmp_path):
        """Gate fails when the final Verdict: line is needs-revision."""
        feature_dir = make_feature_dir(
            tmp_path,
            body="# Coherence Review\n\nFindings listed.\n\nVerdict: needs-revision\n",
        )
        result = validate_coherence(str(feature_dir))
        assert result["result"] == "fail"


class TestTrivialAcceptBodyPasses:

    def test_trivial_accept_body_passes(self, tmp_path):
        """Gate passes for a trivial-accept body (no contracts/seams note + Verdict: accepted).

        The gate reads the verdict, not the body — a one-liner note plus accepted verdict
        must pass exactly the same as a fully-elaborated review.
        """
        feature_dir = make_feature_dir(
            tmp_path,
            body="No cross-module contracts or seams identified.\n\nVerdict: accepted\n",
        )
        result = validate_coherence(str(feature_dir))
        assert result["result"] == "pass"


class TestFinalVerdictLineIsAuthoritative:

    def test_final_verdict_line_is_authoritative(self, tmp_path):
        """Gate keys on the final Verdict: line, not an earlier prose mention.

        A body that contains 'Verdict: needs-revision' in prose followed by a
        final 'Verdict: accepted' line must pass — the final verdict wins.
        """
        body = (
            "# Coherence Review\n\n"
            "In the first round the finding was Verdict: needs-revision "
            "because the seam was ambiguous.\n\n"
            "After re-inspection the seam was clarified.\n\n"
            "Verdict: accepted\n"
        )
        feature_dir = make_feature_dir(tmp_path, body=body)
        result = validate_coherence(str(feature_dir))
        assert result["result"] == "pass"
