"""Tests for fbk.precheck.check_prerequisites — upstream artifact probe."""

import pytest
from pathlib import Path
from fbk.precheck import check_prerequisites


@pytest.fixture
def feature_dir(tmp_path):
    feature = tmp_path / "sample"
    feature.mkdir()
    return feature, "sample"


class TestIntentMissingAtDesign:

    def test_design_fails_when_prd_missing(self, feature_dir):
        """design phase with no prd.md returns ready=False, names prd.md and intent phase."""
        result = check_prerequisites("design", str(feature_dir[0]))
        assert result["ready"] is False
        assert any(
            item["artifact"] == "prd.md" and item["upstream_phase"] == "intent"
            for item in result["missing"]
        )

    def test_design_passes_when_prd_present(self, feature_dir):
        """design phase with prd.md present returns ready=True and empty missing list."""
        (feature_dir[0] / "prd.md").write_text("# PRD")
        result = check_prerequisites("design", str(feature_dir[0]))
        assert result["ready"] is True
        assert result["missing"] == []


class TestDesignMissingAtSpec:

    def test_spec_fails_when_design_manifest_missing(self, feature_dir):
        """spec phase with no design-manifest.md returns ready=False, names design-manifest.md and design phase."""
        result = check_prerequisites("spec", str(feature_dir[0]))
        assert result["ready"] is False
        assert any(
            item["artifact"] == "design-manifest.md" and item["upstream_phase"] == "design"
            for item in result["missing"]
        )

    def test_spec_passes_when_design_manifest_present(self, feature_dir):
        """spec phase with design-manifest.md present returns ready=True."""
        (feature_dir[0] / "design-manifest.md").write_text("# Design Manifest")
        result = check_prerequisites("spec", str(feature_dir[0]))
        assert result["ready"] is True
        assert result["missing"] == []


class TestSpecMissingAtBreakdown:

    def test_breakdown_fails_when_spec_missing(self, feature_dir):
        """breakdown phase with no <feature>-spec.md returns ready=False, names spec artifact and spec phase."""
        result = check_prerequisites("breakdown", str(feature_dir[0]))
        assert result["ready"] is False
        missing_artifacts = [item["artifact"] for item in result["missing"]]
        assert any(artifact.endswith("-spec.md") for artifact in missing_artifacts)
        assert any(item["upstream_phase"] == "spec" for item in result["missing"])

    def test_breakdown_passes_when_spec_present(self, feature_dir):
        """breakdown phase with sample-spec.md present returns ready=True."""
        (feature_dir[0] / "sample-spec.md").write_text("# Spec")
        result = check_prerequisites("breakdown", str(feature_dir[0]))
        assert result["ready"] is True
        assert result["missing"] == []


class TestImplMissingAtCodeReview:

    def test_code_review_fails_when_impl_absent(self, feature_dir):
        """code-review phase with no implementation/ directory returns ready=False, names implementation/ and implement phase."""
        result = check_prerequisites("code-review", str(feature_dir[0]))
        assert result["ready"] is False
        assert any(
            item["artifact"] == "implementation/" and item["upstream_phase"] == "implement"
            for item in result["missing"]
        )

    def test_code_review_passes_when_impl_present(self, feature_dir):
        """code-review phase with implementation/ directory present returns ready=True."""
        (feature_dir[0] / "implementation").mkdir()
        result = check_prerequisites("code-review", str(feature_dir[0]))
        assert result["ready"] is True
        assert result["missing"] == []


class TestReturnStructure:

    def test_return_dict_has_required_keys(self, feature_dir):
        """check_prerequisites returns a dict with phase, ready, and missing keys; phase value echoes the requested phase; missing is a list."""
        result = check_prerequisites("design", str(feature_dir[0]))
        assert "ready" in result
        assert isinstance(result["missing"], list)
        # 'phase' presence and value are the unique contract assertions here;
        # per-item shape is exercised by the behavioral fail/pass tests.
        assert result["phase"] == "design"
