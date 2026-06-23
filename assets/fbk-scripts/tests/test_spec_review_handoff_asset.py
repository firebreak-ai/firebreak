"""Structural asset tests for the independent test-review handoff in fbk-spec-review/SKILL.md.

Asserts that the handoff section is re-expressed as a unified-shape test-review instance
and that the council review document is excluded from the researcher's spawn materials
(IF-S-08, asset half).

Tests are RED until the spec-review handoff migration lands:
- The routing assertion fails because the current section names the ``test-reviewer``
  agent directly and references no test lens.
- The exclusion assertion (absence of council review document) is non-vacuous because
  the presence assertion (spec file named) and the non-empty-section guard both hold
  after migration.
"""

import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Asset path
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parents[3]
_SKILL_MD = _REPO_ROOT / "assets" / "skills" / "fbk-spec-review" / "SKILL.md"

# The heading text that identifies the independent test-review handoff section.
# Matches "## Independent test-review" (current) and any heading whose text
# contains "test-review" (after migration retitle).
_HANDOFF_HEADING_PATTERN = re.compile(
    r"^##\s+.*test-review.*$",
    re.IGNORECASE | re.MULTILINE,
)

# Tokens that indicate the new unified-shape routing: a test lens reference
# or the generic researcher agent name.
_SHAPE_ROUTING_PATTERN = re.compile(
    r"\btest-lens\b|\breview-researcher\b",
    re.IGNORECASE,
)

# Lower-bound presence: the handoff names the spec file in its spawn materials.
_SPEC_FILE_PATTERN = re.compile(
    r"\*-spec\.md\b|spec file",
    re.IGNORECASE,
)

# Tokens that would indicate the council review document is in scope.
# The council output artifact is referred to as "review document" or review.md.
_COUNCIL_REVIEW_PATTERN = re.compile(
    r"review\.md\b|review document",
    re.IGNORECASE,
)

# Non-trivial section: at least this many characters after stripping whitespace.
_MIN_SECTION_LENGTH = 100


# ---------------------------------------------------------------------------
# Helper: slice the handoff section
# ---------------------------------------------------------------------------


def _read_skill() -> str:
    """Return the full text of the spec-review SKILL.md.

    Raises FileNotFoundError (red-phase failure) if the file does not exist.
    """
    return _SKILL_MD.read_text(encoding="utf-8")


def _extract_handoff_section(text: str) -> str:
    """Return the text of the test-review handoff section, from its heading to the next ## heading.

    Returns an empty string when the heading is not found, causing the
    non-empty-section guard to fail rather than producing a misleading empty-range pass.
    """
    match = _HANDOFF_HEADING_PATTERN.search(text)
    if not match:
        return ""

    section_start = match.start()

    # Find the next ## heading after the section start.
    next_heading_match = re.search(
        r"^##\s+",
        text[match.end():],
        re.MULTILINE,
    )
    if next_heading_match:
        section_end = match.end() + next_heading_match.start()
    else:
        section_end = len(text)

    return text[section_start:section_end]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestHandoffSection:
    """The independent test-review handoff section exists and is non-trivial."""

    def test_handoff_section_is_nonempty(self):
        """The sliced test-review handoff section is non-trivial (above minimum length).

        Guards the exclusion and presence assertions against a coincidentally empty
        or missing section — an empty slice would make the absence check vacuously true.
        """
        text = _read_skill()
        section = _extract_handoff_section(text)

        assert len(section.strip()) >= _MIN_SECTION_LENGTH, (
            f"The test-review handoff section is missing or too short "
            f"(got {len(section.strip())} chars, expected at least {_MIN_SECTION_LENGTH}); "
            "verify the heading pattern matches the section in fbk-spec-review/SKILL.md"
        )


class TestHandoffRoutesThoughSharedShape:
    """The handoff section references the unified shape, not the old direct test-reviewer spawn."""

    def test_handoff_routes_through_shared_shape(self):
        """The handoff section names the test lens or generic researcher routing.

        Asserts that the section text contains 'test-lens' or 'review-researcher',
        proving it routes through the unified review shape rather than spawning
        the test-reviewer agent directly.

        RED before migration: the current section names 'test-reviewer' with no lens.
        """
        text = _read_skill()
        section = _extract_handoff_section(text)

        assert _SHAPE_ROUTING_PATTERN.search(section), (
            "The test-review handoff section must name 'test-lens' or 'review-researcher' "
            "to confirm it routes through the unified review shape; "
            "current text references the old 'test-reviewer' direct spawn. "
            f"Section text:\n{section}"
        )


class TestHandoffSpawnMaterials:
    """The handoff section's spawn materials include the spec file and exclude the council review document."""

    def test_handoff_passes_spec_file(self):
        """The handoff section names the spec file in its spawn materials.

        Lower-bound presence assertion: the section text contains a '*-spec.md' reference
        or the literal token 'spec file'.
        """
        text = _read_skill()
        section = _extract_handoff_section(text)

        assert _SPEC_FILE_PATTERN.search(section), (
            "The test-review handoff section must name the spec file in its spawn materials "
            "(expected a '*-spec.md' reference or 'spec file'); "
            f"section text:\n{section}"
        )

    def test_handoff_excludes_council_review_document(self):
        """The handoff section does not name the council review document in its spawn materials.

        Absence assertion paired with the spec-file presence assertion and the non-empty-section
        guard so the exclusion is non-vacuous: the section exists and names the spec file,
        but must not name 'review.md' or 'review document'.
        """
        text = _read_skill()
        section = _extract_handoff_section(text)

        assert not _COUNCIL_REVIEW_PATTERN.search(section), (
            "The test-review handoff section must not reference the council review document "
            "('review.md' or 'review document') in its spawn materials; "
            "the test reviewer must receive only the spec file, the test lens, and the schema. "
            f"Section text:\n{section}"
        )
