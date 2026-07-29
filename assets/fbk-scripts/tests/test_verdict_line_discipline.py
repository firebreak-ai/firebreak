"""Characterization tests pinning the verdict-line discipline for all verdict-bearing artifacts.

Every verdict-bearing artifact in the review shape must contain exactly one line
matching ``^Verdict: (accepted|needs-revision)$``.  These tests verify:

- the structural check itself is non-vacuous (the duplicate case catches a regression),
- the real gate helper resolves the single canonical line, and
- the set of artifact names subject to the discipline is explicitly enumerated.
"""

import re
from pathlib import Path

import pytest

from fbk.gates.review import read_test_review_verdict


# ---------------------------------------------------------------------------
# Canonical artifact names that the verdict-line discipline applies to.
# coherence-review.md and task-review.md are covered jointly by this module
# and the per-artifact tests for AC-08 / AC-20; the list here pins the shared
# format contract so that adding or removing a name is a deliberate edit.
# ---------------------------------------------------------------------------

VERDICT_BEARING_ARTIFACTS = [
    "test-review-spec.md",
    "test-review-pre-lock.md",
    "test-review-final.md",
    "coherence-review.md",
    "task-review.md",
]

_VERDICT_PATTERN = re.compile(r"^Verdict: (accepted|needs-revision)$", re.MULTILINE)


def count_verdict_lines(text: str) -> int:
    """Return the number of lines matching ``^Verdict: (accepted|needs-revision)$``."""
    return len(_VERDICT_PATTERN.findall(text))


# ---------------------------------------------------------------------------
# Structural helpers — non-vacuous by design
# ---------------------------------------------------------------------------


class TestVerdictLineStructure:
    """The exactly-one discipline and the duplicate-detection case."""

    def test_well_formed_artifact_has_exactly_one_verdict_line(self):
        """A well-formed artifact body with one Verdict line counts as exactly one."""
        text = """\
## Summary

The test plan covers all acceptance criteria with appropriate fixtures.

## Findings

No issues found.

Verdict: accepted
"""
        assert count_verdict_lines(text) == 1

    def test_duplicate_verdict_lines_are_detectable(self):
        """A malformed body carrying both accepted and needs-revision counts as two.

        This proves the check is non-vacuous: an exactly-one rule catches a
        conflicting/duplicate verdict that the gate would silently misread by
        returning only the first match.
        """
        text = """\
## Summary

Verdict: accepted

## Addendum

Verdict: needs-revision
"""
        assert count_verdict_lines(text) == 2


# ---------------------------------------------------------------------------
# Real gate helper — exercises the production path with a tmp_path fixture
# ---------------------------------------------------------------------------


class TestGateHelperReadsSingleVerdict:
    """The real read_test_review_verdict gate helper resolves a single canonical line."""

    def test_gate_helper_reads_single_verdict(self, tmp_path: Path):
        """Gate helper returns 'accepted' for a well-formed test-review-spec.md."""
        artifact = tmp_path / "test-review-spec.md"
        artifact.write_text(
            "## Test Review\n\nAll criteria satisfied.\n\nVerdict: accepted\n",
            encoding="utf-8",
        )
        result = read_test_review_verdict(tmp_path)
        assert result == "accepted"

    def test_gate_helper_with_two_verdict_lines_does_not_silently_pick_one(self, tmp_path: Path):
        """Gate helper must not silently return the first verdict when two conflict.

        An artifact containing both 'Verdict: accepted' and 'Verdict: needs-revision'
        is ambiguous.  The shared strict parser raises on ambiguity rather than
        silently picking one, and the gate turns that into a blocking failure.
        """
        artifact = tmp_path / "test-review-spec.md"
        artifact.write_text(
            "## Section A\n\nVerdict: accepted\n\n"
            "## Section B\n\nVerdict: needs-revision\n",
            encoding="utf-8",
        )
        with pytest.raises(Exception, match=r"verdict"):
            read_test_review_verdict(tmp_path)

    def test_gate_helper_with_zero_verdict_lines_returns_none(self, tmp_path: Path):
        """Gate helper returns None when the artifact contains no Verdict: line.

        An artifact with no verdict is treated as absent by the gate — the caller
        sees None and can report a blocking failure.  Returning None is the correct
        contract; raising would also be acceptable, but silence (returning a non-None
        value) would hide the missing verdict.
        """
        artifact = tmp_path / "test-review-spec.md"
        artifact.write_text(
            "## Test Review\n\nNo verdict line present in this document.\n",
            encoding="utf-8",
        )
        result = read_test_review_verdict(tmp_path)
        assert result is None, (
            "read_test_review_verdict must return None when no Verdict: line is found; "
            f"got {result!r}"
        )


# ---------------------------------------------------------------------------
# Artifact name enumeration — pins the discipline's scope explicitly
# ---------------------------------------------------------------------------


class TestCanonicalArtifactNames:
    """The list of verdict-bearing artifact names is explicitly enumerated and well-formed."""

    def test_each_canonical_artifact_name_uses_the_format(self):
        """Each name in VERDICT_BEARING_ARTIFACTS ends in .md and is non-empty."""
        assert len(VERDICT_BEARING_ARTIFACTS) == 5, (
            f"Expected 5 canonical artifact names, got {len(VERDICT_BEARING_ARTIFACTS)}: "
            f"{VERDICT_BEARING_ARTIFACTS}"
        )
        for name in VERDICT_BEARING_ARTIFACTS:
            assert name.endswith(".md"), f"Artifact name does not end in .md: {name!r}"
            assert name.strip(), f"Artifact name is blank: {name!r}"

    def test_all_five_names_are_referenced(self):
        """The five canonical artifact names are each present in the constant."""
        expected = {
            "test-review-spec.md",
            "test-review-pre-lock.md",
            "test-review-final.md",
            "coherence-review.md",
            "task-review.md",
        }
        actual = set(VERDICT_BEARING_ARTIFACTS)
        assert actual == expected, (
            f"Canonical artifact set mismatch.\n  expected: {sorted(expected)}\n  actual:   {sorted(actual)}"
        )
