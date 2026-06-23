"""Closed work-capability vocabulary and resolver.

The substrate labels every unit of work with one "shape" — the kind of work
an agent did. The vocabulary is fixed and closed at five members:
distill, implement, review, synthesize, gate.

The resolver maps from a recorded agent-type name to a shape via a plain
dictionary. It returns None for unknown values (never invents or guesses a
shape), preserving the integrity of the durable record.
"""

import sys

# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------

SHAPE_VOCABULARY = frozenset({"distill", "implement", "review", "synthesize", "gate"})

_PERSONA_TO_SHAPE = {
    # Self-mappings: each vocabulary member maps to itself
    "distill": "distill",
    "implement": "implement",
    "review": "review",
    "synthesize": "synthesize",
    "gate": "gate",
    # Canonical persona-name entries
    "fbk-implementer": "implement",
    "test-reviewer": "review",
    "code-review-detector": "review",
    "review-researcher": "review",
    "review-challenger": "review",
    "fbk-product-author": "distill",
    "fbk-architect": "distill",
    "fbk-task-compiler": "distill",
    "fbk-spec-author": "distill",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def resolve_shape(raw: str | None) -> str | None:
    """Resolve an agent-type name or shape string to a vocabulary member.

    Args:
        raw: An agent-type identifier, a shape string, or None.

    Returns:
        The resolved shape string (a member of SHAPE_VOCABULARY), or None if
        the input is None or has no mapping.

    When raw is a non-null string with no mapping, prints a stderr warning
    naming the unmapped value and returns None. Never returns a value outside
    SHAPE_VOCABULARY and never raises.
    """
    if raw is None:
        return None

    if raw in _PERSONA_TO_SHAPE:
        return _PERSONA_TO_SHAPE[raw]

    # Unmapped non-null string: warn and return None
    print(
        f"fbk.shapes: unmapped persona {raw!r}",
        file=sys.stderr,
    )
    return None
