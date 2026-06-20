"""Unit tests for fbk.shapes — closed shape vocabulary and resolution.

Tests cover:
- SHAPE_VOCABULARY is a frozenset with exactly five members: distill, implement,
  review, synthesize, gate
- resolve_shape() maps known agent-type names to their shape
- resolve_shape() returns the shape unchanged when given a shape string (caller
  already holding a shape gets it back)
- resolve_shape() returns None for unknown inputs and None input (never invents
  a shape)
- Return for unknown input is None specifically, not a falsy value
"""

import pytest

try:
    from fbk import shapes
    SHAPES_AVAILABLE = True
except ImportError:
    SHAPES_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not SHAPES_AVAILABLE,
    reason="fbk.shapes module not yet implemented",
)


# ---------------------------------------------------------------------------
# Vocabulary tests
# ---------------------------------------------------------------------------


class TestShapeVocabulary:
    """SHAPE_VOCABULARY is a closed set of exactly five members."""

    def test_vocabulary_is_frozenset(self):
        """SHAPE_VOCABULARY is a frozenset."""
        assert isinstance(shapes.SHAPE_VOCABULARY, frozenset)

    def test_vocabulary_contains_exactly_five_members(self):
        """SHAPE_VOCABULARY equals exactly {"distill", "implement", "review", "synthesize", "gate"}."""
        expected = frozenset({"distill", "implement", "review", "synthesize", "gate"})
        assert shapes.SHAPE_VOCABULARY == expected


# ---------------------------------------------------------------------------
# Agent-type resolution tests
# ---------------------------------------------------------------------------


class TestAgentTypeResolution:
    """resolve_shape() maps known agent types to their shape."""

    def test_resolve_fbk_implementer_to_implement(self):
        """resolve_shape("fbk-implementer") returns "implement"."""
        assert shapes.resolve_shape("fbk-implementer") == "implement"

    def test_resolve_test_reviewer_to_review(self):
        """resolve_shape("test-reviewer") returns "review"."""
        assert shapes.resolve_shape("test-reviewer") == "review"

    def test_resolve_code_review_detector_to_review(self):
        """resolve_shape("code-review-detector") returns "review"."""
        assert shapes.resolve_shape("code-review-detector") == "review"

    def test_resolve_fbk_product_author_to_distill(self):
        """resolve_shape("fbk-product-author") returns "distill"."""
        assert shapes.resolve_shape("fbk-product-author") == "distill"


# ---------------------------------------------------------------------------
# Shape self-mapping tests
# ---------------------------------------------------------------------------


class TestShapeSelfMapping:
    """resolve_shape() returns the shape unchanged when given a shape string."""

    def test_distill_resolves_to_itself(self):
        """resolve_shape("distill") returns "distill"."""
        assert shapes.resolve_shape("distill") == "distill"

    def test_implement_resolves_to_itself(self):
        """resolve_shape("implement") returns "implement"."""
        assert shapes.resolve_shape("implement") == "implement"

    def test_review_resolves_to_itself(self):
        """resolve_shape("review") returns "review"."""
        assert shapes.resolve_shape("review") == "review"

    def test_synthesize_resolves_to_itself(self):
        """resolve_shape("synthesize") returns "synthesize"."""
        assert shapes.resolve_shape("synthesize") == "synthesize"

    def test_gate_resolves_to_itself(self):
        """resolve_shape("gate") returns "gate"."""
        assert shapes.resolve_shape("gate") == "gate"


# ---------------------------------------------------------------------------
# Unknown-input and None-input tests
# ---------------------------------------------------------------------------


class TestUnknownInputResolution:
    """resolve_shape() returns None for unknown and None inputs."""

    def test_unknown_persona_returns_none(self):
        """resolve_shape("not-a-real-persona") returns None."""
        assert shapes.resolve_shape("not-a-real-persona") is None

    def test_none_input_returns_none(self):
        """resolve_shape(None) returns None."""
        assert shapes.resolve_shape(None) is None

    def test_unknown_input_returns_none_not_falsy_value(self):
        """resolve_shape("xyz") returns None specifically (identity check, not falsy)."""
        assert shapes.resolve_shape("xyz") is None
