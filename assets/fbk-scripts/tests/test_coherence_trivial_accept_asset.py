"""Structural asset tests for the coherence-review trivial-accept routing rule (AC-10 routing half).

When a feature declares no contracts and no seams — including the case where
``design/contracts.md`` is absent — the coherence preset must route to a
trivial-accept note plus ``Verdict: accepted``, not to the missing-lens loud
failure (IF-S-01).  These are distinct paths: the loud failure is for an absent
*lens*, not an absent contracts file.

These tests assert that the trivial-accept routing rule is documented as an
explicit branch in the coherence skill and/or lens, so the loop coordinator has
an unambiguous instruction and the rule cannot silently regress to a loud
failure.

Tests are RED until ``assets/skills/fbk-coherence-review/SKILL.md`` and/or
``assets/fbk-docs/fbk-review-lenses/coherence-lens.md`` exist and document the
trivial-accept branch.

The live routing run (coherence preset writes the trivial-accept artifact for a
real no-contracts feature) is UV-6, a source-of-truth manual gate on the
coherence-review impl task — intentionally not compiled here.
"""

import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Asset paths
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parents[3]

_COHERENCE_SKILL = (
    _REPO_ROOT / "assets" / "skills" / "fbk-coherence-review" / "SKILL.md"
)
_COHERENCE_LENS = (
    _REPO_ROOT / "assets" / "fbk-docs" / "fbk-review-lenses" / "coherence-lens.md"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_asset(path: Path) -> str:
    """Return the text of an asset file.

    Raises FileNotFoundError (red-phase failure) when the asset does not exist.
    """
    return path.read_text(encoding="utf-8")


def _combined_coherence_text() -> str:
    """Return the concatenation of the coherence skill and lens texts.

    Either or both assets may carry the trivial-accept rule; checking the
    combined text lets either file satisfy the assertions without forcing a
    single canonical home before the implementation author decides.

    Raises FileNotFoundError when neither asset exists (red-phase failure).
    """
    parts: list[str] = []
    for path in (_COHERENCE_SKILL, _COHERENCE_LENS):
        if path.exists():
            parts.append(path.read_text(encoding="utf-8"))

    if not parts:
        # Force a readable FileNotFoundError pointing at the primary asset.
        _read_asset(_COHERENCE_SKILL)

    return "\n".join(parts)


def _region_around(text: str, anchor: str, window: int = 400) -> str:
    """Return up to ``window`` characters centred on the first occurrence of ``anchor``.

    Returns an empty string when ``anchor`` is not found.
    """
    idx = text.find(anchor)
    if idx == -1:
        return ""
    start = max(0, idx - window)
    end = min(len(text), idx + len(anchor) + window)
    return text[start:end]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def _extract_section_under_heading(text: str, heading_pattern: str) -> str:
    """Return the body of the first section whose ## heading matches ``heading_pattern``.

    Searches case-insensitively.  Returns the text from the line after the heading
    up to (but not including) the next ## heading, or to the end of the document.
    Returns an empty string when no matching heading is found.
    """
    lines = text.splitlines(keepends=True)
    capturing = False
    collected: list[str] = []
    pattern = re.compile(heading_pattern, re.IGNORECASE)
    for line in lines:
        if line.startswith("## ") or line.startswith("## "):
            if capturing:
                break
            if pattern.search(line):
                capturing = True
                continue
        if capturing:
            collected.append(line)
    return "".join(collected)


class TestCoherenceSkillDocumentsTrivialAccept:
    """The coherence skill names the trivial-accept branch as an explicit routing option."""

    def test_coherence_skill_documents_trivial_accept(self):
        """The coherence skill (SKILL.md) has a dedicated heading or instruction block for trivial-accept routing.

        The assertion is anchored to the structure of the routing rule, not to a
        bare anywhere-in-file token search.  The token ``trivial-accept`` must appear
        either:

        1. In a ``##`` heading whose text contains ``trivial`` or ``routing``, OR
        2. In a paragraph that also contains a conditional keyword (``condition``,
           ``when``, ``if``), proving it appears inside an explicit routing instruction
           rather than an incidental prose mention.

        This prevents a bare word-match against a comment, a code example label,
        or a retrospective note from satisfying the test.
        """
        text = _read_asset(_COHERENCE_SKILL)
        text_lower = text.lower()

        # Condition 1: a ## heading whose text itself contains "trivial" or "routing"
        heading_has_trivial = bool(
            re.search(r"^##\s+.*(trivial|routing).*$", text_lower, re.MULTILINE)
        )

        # Condition 2: trivial-accept appears in a paragraph that also contains a
        # conditional keyword — proving it is inside a routing instruction block.
        ta_pos = text_lower.find("trivial-accept")
        in_instruction_context = False
        if ta_pos != -1:
            # Look at the surrounding paragraph (up to 600 chars on each side).
            para_start = max(0, ta_pos - 600)
            para_end = min(len(text_lower), ta_pos + 600)
            para = text_lower[para_start:para_end]
            in_instruction_context = bool(
                re.search(r"\b(condition|when both|when either|if .{0,40}hold|skip the review)\b", para)
            )

        assert heading_has_trivial or in_instruction_context, (
            "fbk-coherence-review/SKILL.md must document the trivial-accept branch "
            "in a structural context (a ## heading containing 'trivial' or 'routing', "
            "or a paragraph co-located with a conditional routing keyword like "
            "'condition', 'when both', 'when either', 'skip the review'). "
            "A bare anywhere-in-file token does not satisfy this check."
        )


class TestAbsentContractsRoutesToAcceptNotLoudFailure:
    """An absent design/contracts.md routes to trivial-accept, not to the missing-lens loud failure."""

    def test_absent_contracts_routes_to_accept_not_loud_failure(self):
        """The skill or lens states that an absent contracts file routes to trivial-accept.

        Three conditions must hold in a local region of at least one asset:
        1. A reference to ``contracts`` (for the absent contracts file).
        2. A route-to-accept token (``accept``, ``trivial``) nearby.
        3. No co-occurrence of an error/fail instruction in the same region for
           the absent-contracts case — asserts the routing is to accept, not to
           a loud failure.

        This keeps the distinction from IF-S-01 honest: the loud failure is for
        an absent *lens*, not an absent contracts file.
        """
        text = _combined_coherence_text()
        text_lower = text.lower()

        # Find the region around the first mention of 'contracts' in the
        # context of the absent-contracts routing case.
        # We look for 'contracts' co-occurring with an absence indicator.
        absent_contracts_pattern = re.compile(
            r"absent contracts|no contracts|contracts.{0,60}(?:absent|missing|not present|does not exist)",
            re.IGNORECASE | re.DOTALL,
        )

        match = absent_contracts_pattern.search(text)
        assert match is not None, (
            "The coherence skill or lens must reference the absent-contracts case "
            "(e.g. 'absent contracts', 'no contracts', 'contracts ... missing'). "
            "Check assets/skills/fbk-coherence-review/SKILL.md and "
            "assets/fbk-docs/fbk-review-lenses/coherence-lens.md."
        )

        # Extract a window around the match to test co-occurrences locally.
        idx = match.start()
        start = max(0, idx - 200)
        end = min(len(text_lower), idx + 600)
        region = text_lower[start:end]

        # Condition 2: the region routes to accept/trivial.
        has_accept_routing = bool(re.search(r"\b(accept|trivial)\b", region))
        assert has_accept_routing, (
            "The absent-contracts region must co-occur with a route-to-accept "
            "instruction ('accept' or 'trivial') within 600 characters. "
            f"Region around the absent-contracts reference: {region!r}"
        )

        # Condition 3: the absent-contracts sentence does NOT instruct an
        # error/fail outcome.  We scan a tighter window (the sentence span)
        # so that a separately-documented loud-failure for missing lenses does
        # not bleed into this check.
        sentence_start = text_lower.rfind("\n", start, idx)
        sentence_start = sentence_start + 1 if sentence_start != -1 else start
        sentence_end = text_lower.find("\n", idx + len(match.group()))
        sentence_end = sentence_end if sentence_end != -1 else end
        sentence_region = text_lower[sentence_start:sentence_end]

        has_error_instruction = bool(
            re.search(r"\b(error|fail|loud.fail|raise)\b", sentence_region)
        )
        assert not has_error_instruction, (
            "The absent-contracts sentence must NOT instruct an error/fail outcome. "
            "Absent contracts routes to trivial-accept; the loud failure is reserved "
            "for an absent *lens* (IF-S-01). "
            f"Sentence region: {sentence_region!r}"
        )


class TestTrivialAcceptArtifactShapeDocumented:
    """The documented trivial-accept artifact carries both a one-line note and a Verdict: accepted line."""

    def test_trivial_accept_artifact_shape_documented(self):
        """The coherence skill or lens shows the ``Verdict: accepted`` form for the trivial case.

        Both of the following must appear in a single local region:
        1. ``Verdict: accepted`` — the exact verdict line for the trivial case.
        2. A one-line note indicator (``one-line``, ``one line``, or ``brief note``)
           that pins the shape of the trivial-accept output.

        Together they document that the trivial-accept artifact is a short note
        plus the standard verdict line, preventing regression to a verbose
        analysis or a missing verdict.
        """
        text = _combined_coherence_text()

        # Condition 1: the exact verdict form must appear.
        assert "Verdict: accepted" in text, (
            "The coherence skill or lens must show the exact verdict form "
            "'Verdict: accepted' for the trivial-accept case. "
            "Check assets/skills/fbk-coherence-review/SKILL.md and "
            "assets/fbk-docs/fbk-review-lenses/coherence-lens.md."
        )

        # Condition 2: a one-line note indicator must co-occur near the verdict.
        region = _region_around(text, "Verdict: accepted", window=500)
        has_one_line_note = bool(
            re.search(r"one[- ]line|brief note", region, re.IGNORECASE)
        )
        assert has_one_line_note, (
            "The coherence skill or lens must document the trivial-accept artifact "
            "shape as a one-line note co-occurring with 'Verdict: accepted' within "
            "500 characters. Expected 'one-line', 'one line', or 'brief note'. "
            f"Region around 'Verdict: accepted': {region!r}"
        )
