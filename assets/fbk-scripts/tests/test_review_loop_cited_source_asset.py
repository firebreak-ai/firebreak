"""Structural asset tests for the cited-source discipline in the shared review loop.

Asserts two contracts documented in the review loop spine and challenger role agent:

- Injection (IF-S-03 injection half): the loop coordinator collects the document
  named in a candidate's ``source_of_truth_ref`` and injects it into the
  challenger spawn payload.
- Unresolvable status (AC-07): when a cited source cannot be located the finding
  is recorded with challenger status ``unresolvable``; the challenger does not
  issue a verified or rejected ruling on it.

These tests are RED until ``review-loop.md`` and ``fbk-review-challenger.md``
exist.  They pass once the review-loop-spine and role-agents implementation
lands and documents the rules explicitly.
"""

import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Asset paths
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parents[3]

_REVIEW_LOOP_MD = _REPO_ROOT / "assets" / "fbk-docs" / "fbk-review-lenses" / "review-loop.md"
_CHALLENGER_MD = _REPO_ROOT / "assets" / "agents" / "fbk-review-challenger.md"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_asset(path: Path) -> str:
    """Return the text of an asset file.

    Raises FileNotFoundError (red-phase failure) when the asset does not exist.
    """
    return path.read_text(encoding="utf-8")


def _region_around(text: str, anchor: str, window: int = 400) -> str:
    """Return up to ``window`` characters centred on the first occurrence of ``anchor``.

    Useful for co-occurrence checks that should hold in a local region of the
    document rather than requiring all tokens to appear near each other
    regardless of document length.
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


class TestCitedSourceInjection:
    """The loop coordinator injects the cited-source document into the challenger spawn."""

    def test_loop_documents_cited_source_injection(self):
        """review-loop.md names the source_of_truth_ref field and an inject/collect instruction.

        Both tokens must appear in the same local region, pinning that the
        coordinator is instructed to gather the named document and supply it to
        the challenger.
        """
        text = _read_asset(_REVIEW_LOOP_MD)

        assert "source_of_truth_ref" in text, (
            "review-loop.md must mention 'source_of_truth_ref' to document "
            "the cited-source injection contract"
        )

        # Look for inject or collect co-occurring near source_of_truth_ref.
        region = _region_around(text, "source_of_truth_ref", window=500)
        has_injection_instruction = bool(
            re.search(r"\b(inject|collect)\b", region, re.IGNORECASE)
        )
        assert has_injection_instruction, (
            "review-loop.md must co-locate 'source_of_truth_ref' with an "
            "inject/collect instruction within 500 characters; "
            f"region around 'source_of_truth_ref': {region!r}"
        )


class TestUnresolvableStatus:
    """'unresolvable' is a defined member of the challenger verdict status enum."""

    def test_loop_or_challenger_defines_unresolvable_status(self):
        """The challenger agent or review-loop.md lists 'unresolvable' alongside 'verified' and 'rejected'.

        All three status names must appear in the same file so that
        'unresolvable' is a defined enum member rather than an ad-hoc string.
        """
        challenger_text = _read_asset(_CHALLENGER_MD)

        # The challenger agent is the primary home for the verdict status set.
        # Fall back to review-loop.md if the challenger delegates status
        # definition upward.
        loop_text = _read_asset(_REVIEW_LOOP_MD)
        combined = challenger_text + "\n" + loop_text

        assert "unresolvable" in combined, (
            "Neither fbk-review-challenger.md nor review-loop.md defines "
            "'unresolvable' as a challenger verdict status"
        )
        assert "verified" in combined, (
            "The verdict status set must include 'verified'"
        )
        assert "rejected" in combined, (
            "The verdict status set must include 'rejected'"
        )

        # All three must co-occur in at least one of the two files.
        for text, label in [(challenger_text, "fbk-review-challenger.md"), (loop_text, "review-loop.md")]:
            if "unresolvable" in text and "verified" in text and "rejected" in text:
                return  # At least one file contains the full enum definition.

        raise AssertionError(
            "Neither fbk-review-challenger.md nor review-loop.md contains all "
            "three verdict statuses ('verified', 'rejected', 'unresolvable') in a "
            "single file; the enum definition must be self-contained in one asset"
        )


class TestUnlocatableSourceRouting:
    """An unlocatable cited source routes to 'unresolvable', not verified/rejected."""

    def test_unlocatable_source_routes_to_unresolvable(self):
        """The asset states that an unlocatable source yields 'unresolvable' and forbids a verified/rejected ruling.

        Three conditions must hold in a local region:
        1. 'unresolvable' appears.
        2. A not-located token ('cannot be located', 'not found', 'cannot locate',
           'not locatable', 'unlocatable') appears nearby.
        3. A no-ruling instruction ('does not', 'not issue', 'no ruling', 'skip',
           'without ruling') appears nearby, pinning the prohibition on
           verified/rejected verdicts when the source is absent.
        """
        # Check both assets; either may carry this rule.
        challenger_text = _read_asset(_CHALLENGER_MD)
        loop_text = _read_asset(_REVIEW_LOOP_MD)

        not_located_pattern = re.compile(
            r"cannot be located|not found|cannot locate|not locatable|unlocatable",
            re.IGNORECASE,
        )
        no_ruling_pattern = re.compile(
            r"does not (?:issue|rule|produce)|not issue|no ruling|without (?:a )?ruling|skip.*ruling|no verified|no rejected",
            re.IGNORECASE,
        )

        for text, label in [(challenger_text, "fbk-review-challenger.md"), (loop_text, "review-loop.md")]:
            if "unresolvable" not in text:
                continue

            region = _region_around(text, "unresolvable", window=600)

            has_not_located = bool(not_located_pattern.search(region))
            has_no_ruling = bool(no_ruling_pattern.search(region))

            if has_not_located and has_no_ruling:
                return  # Contract documented correctly in this file.

        raise AssertionError(
            "No asset documents the unresolvable routing rule with all three "
            "required elements co-occurring near 'unresolvable': "
            "(1) 'unresolvable', "
            "(2) a not-located token (e.g. 'cannot be located', 'not found'), "
            "(3) a no-ruling instruction (e.g. 'does not issue', 'no ruling'). "
            "Check fbk-review-challenger.md and review-loop.md."
        )


class TestChallengerNoNewFindings:
    """The challenger generates no new finding objects; observations go to adjacent notes."""

    def test_challenger_generates_no_new_findings(self):
        """fbk-review-challenger.md documents that it generates no new finding objects.

        'adjacent' and a no-new-findings instruction must co-occur in the
        challenger agent text, pinning the IF-S-03 error-path discipline that
        prevents 'unresolvable' from becoming a backdoor for new findings.
        """
        text = _read_asset(_CHALLENGER_MD)

        assert "adjacent" in text, (
            "fbk-review-challenger.md must mention 'adjacent' observations as "
            "the outlet for things the challenger notices beyond its ruling; "
            "this pins the no-new-findings discipline"
        )

        no_new_findings_pattern = re.compile(
            r"no new find(?:ing)?s?|does not (?:generate|produce|add|create) (?:new )?find(?:ing)?s?|"
            r"not (?:generate|produce|add|create) (?:new )?find(?:ing)?s?|"
            r"generates? no (?:new )?find(?:ing)?s?",
            re.IGNORECASE,
        )

        region = _region_around(text, "adjacent", window=600)
        has_no_new_findings = bool(no_new_findings_pattern.search(region))

        assert has_no_new_findings, (
            "fbk-review-challenger.md must co-locate 'adjacent' with a "
            "no-new-findings instruction within 600 characters; "
            f"region around 'adjacent': {region!r}"
        )
