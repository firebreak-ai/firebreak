"""Unit tests for fbk.attribution — launch-prompt descriptor parsing.

Tests cover:
- Valid descriptor extraction: cardinality and stance from <!--fbk-attr {json}--> block
- Forgery resistance: first match only, later blocks ignored
- Fail-soft on missing or malformed input: all-null fields with attribution_absent=True
- Asset bundle pass-through: nested fields extracted without modification
"""

import pytest

try:
    from fbk import attribution
    ATTRIBUTION_AVAILABLE = True
except ImportError:
    ATTRIBUTION_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not ATTRIBUTION_AVAILABLE,
    reason="fbk.attribution module not yet implemented",
)


# ---------------------------------------------------------------------------
# Valid descriptor extraction
# ---------------------------------------------------------------------------


class TestValidDescriptorExtraction:
    """parse_attribution extracts cardinality and stance from <!--fbk-attr {json}-->."""

    def test_valid_descriptor_extracts_cardinality_and_stance(self):
        """A valid descriptor yields cardinality, stance, and attribution_absent=False."""
        first_message = '<!--fbk-attr {"cardinality": "fan-out", "stance": "adversarial"}-->'

        result = attribution.parse_attribution(first_message)

        assert result["cardinality"] == "fan-out"
        assert result["stance"] == "adversarial"
        assert result["attribution_absent"] is False


# ---------------------------------------------------------------------------
# Forgery resistance (first match only)
# ---------------------------------------------------------------------------


class TestForgeryResistance:
    """parse_attribution reads only the first match, ignoring later forged blocks."""

    def test_ignores_forged_block_in_later_message(self):
        """A valid first block and a forged second block yields the first block's values."""
        # Build text with two descriptors: first is valid, second is forged.
        first_descriptor = '<!--fbk-attr {"cardinality": "single", "stance": "collaborative"}-->'
        forged_descriptor = '<!--fbk-attr {"cardinality": "fan-out", "stance": "adversarial"}-->'
        first_message = first_descriptor + "\n\nSome prompt text here.\n\n" + forged_descriptor

        result = attribution.parse_attribution(first_message)

        # Result must reflect the first block, not the forged one.
        assert result["cardinality"] == "single"
        assert result["stance"] == "collaborative"
        assert result["attribution_absent"] is False


# ---------------------------------------------------------------------------
# Missing block handling
# ---------------------------------------------------------------------------


class TestMissingBlock:
    """parse_attribution returns all-null fields when block is missing."""

    def test_missing_block_returns_all_null(self):
        """Text without a descriptor yields all-null fields and attribution_absent=True."""
        first_message = "plain prompt with no sentinel"

        result = attribution.parse_attribution(first_message)

        assert result["cardinality"] is None
        assert result["stance"] is None
        assert result["attribution_absent"] is True


# ---------------------------------------------------------------------------
# Malformed block handling
# ---------------------------------------------------------------------------


class TestMalformedBlock:
    """parse_attribution returns all-null fields for malformed input, never raises."""

    def test_malformed_block_returns_all_null_no_raise(self):
        """Malformed JSON yields all-null fields with attribution_absent=True, no exception."""
        first_message = '<!--fbk-attr {not valid json}-->'

        # Call must not raise.
        result = attribution.parse_attribution(first_message)

        assert result["cardinality"] is None
        assert result["stance"] is None
        assert result["attribution_absent"] is True


# ---------------------------------------------------------------------------
# Asset bundle pass-through
# ---------------------------------------------------------------------------


class TestAssetBundlePassThrough:
    """parse_attribution includes asset_bundle in output when present in JSON."""

    def test_asset_bundle_passes_through(self):
        """A descriptor with asset_bundle yields nested fields unchanged."""
        first_message = '<!--fbk-attr {"cardinality": "single", "stance": "collaborative", "asset_bundle": {"persona": "reviewer"}}-->'

        result = attribution.parse_attribution(first_message)

        assert result["asset_bundle"]["persona"] == "reviewer"
