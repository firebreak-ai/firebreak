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
- is_known_agent() recognizes the two new generic role agents: review-researcher
  and review-challenger
"""

import pytest

try:
    from fbk import shapes
    SHAPES_AVAILABLE = True
except ImportError:
    SHAPES_AVAILABLE = False

try:
    from fbk.capture import known_agents
    KNOWN_AGENTS_AVAILABLE = True
except ImportError:
    KNOWN_AGENTS_AVAILABLE = False

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

    def test_resolve_review_researcher_to_review(self):
        """resolve_shape("review-researcher") returns "review"."""
        assert shapes.resolve_shape("review-researcher") == "review"

    def test_resolve_review_challenger_to_review(self):
        """resolve_shape("review-challenger") returns "review"."""
        assert shapes.resolve_shape("review-challenger") == "review"

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


# ---------------------------------------------------------------------------
# Known-agent recognition tests
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not KNOWN_AGENTS_AVAILABLE,
    reason="fbk.capture.known_agents module not yet implemented",
)
class TestKnownAgentsRecognizesNewRoleAgents:
    """is_known_agent() recognizes the two new generic role agents."""

    def test_known_agents_recognizes_new_role_agents(self, tmp_path, monkeypatch):
        """is_known_agent returns True for review-researcher and review-challenger.

        Writes minimal persona files into a tmp dir, points FBK_AGENTS_DIR at
        it, then asserts each new agent name is recognized.  This exercises the
        live file-scan path in is_known_agent, not the hardcoded fallback.
        """
        persona_dir = tmp_path / "agents"
        persona_dir.mkdir()

        for name in ("review-researcher", "review-challenger"):
            path = persona_dir / f"{name}.md"
            path.write_text(f"---\nname: {name}\n---\n\nPersona body.\n")

        monkeypatch.setenv("FBK_AGENTS_DIR", str(persona_dir))

        assert known_agents.is_known_agent("review-researcher") is True
        assert known_agents.is_known_agent("review-challenger") is True
