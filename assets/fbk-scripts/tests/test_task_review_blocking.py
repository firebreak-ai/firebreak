"""Structural and artifact-shape assertions for the fbk-task-review preset (AC-20).

Covers two halves of AC-20:
- Artifact shape: a task-review.md body carries exactly one anchored Verdict: line,
  proven against a hand-built representative body. Green immediately — pins the contract.
- Preset skill: assets/skills/fbk-task-review/SKILL.md exists, references task-lens,
  and documents task-review.md with a Verdict: line as its output. Red until task-38
  authors the skill.

The breakdown-wiring half of AC-20 (skill invokes the task-review preset, reads
task-review.md between the task-reviewer-gate and breakdown-gate calls, and blocks
on needs-revision) is asserted by task-18 in wave 3, which parses fbk-breakdown/SKILL.md.
"""

import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parents[3]
_TASK_REVIEW_SKILL = _REPO_ROOT / "assets" / "skills" / "fbk-task-review" / "SKILL.md"

# ---------------------------------------------------------------------------
# Verdict-line helper
# ---------------------------------------------------------------------------

_VERDICT_PATTERN = re.compile(r"^Verdict: (accepted|needs-revision)$", re.MULTILINE)


def count_verdict_lines(text: str) -> int:
    """Return the number of full-line anchored Verdict: lines in text.

    Matches only lines of exactly: Verdict: accepted  or  Verdict: needs-revision
    A line with extra trailing content or a different value does not match.
    """
    return len(_VERDICT_PATTERN.findall(text))


# ---------------------------------------------------------------------------
# Artifact verdict-shape assertions (green immediately — pins the contract)
# ---------------------------------------------------------------------------


class TestTaskReviewArtifactVerdictShape:
    """task-review.md carries exactly one anchored Verdict: line (AC-20).

    Uses a hand-built representative body so these assertions are green
    before any implementation exists.  They pin the contract that the
    preset implementation must satisfy.
    """

    _SINGLE_VERDICT_BODY = """\
## Task review: task-07

**Reviewed task:** task-07 — implement the scoring gate
**Date:** 2026-06-23

### Summary

The task file is well-formed. The acceptance criteria are covered.
The completion gate is unambiguous. Wave ordering is correct.

### Findings

No issues found.

Verdict: needs-revision
"""

    _TWO_VERDICT_BODY = """\
## Task review: task-07

Verdict: accepted

Some body text.

Verdict: needs-revision
"""

    def test_single_verdict_body_has_one_verdict_line(self):
        """Representative task-review.md body with one Verdict: line returns count 1."""
        assert count_verdict_lines(self._SINGLE_VERDICT_BODY) == 1

    def test_parsed_verdict_value_equals_needs_revision(self):
        """The verdict value parsed from the representative body equals 'needs-revision'."""
        matches = _VERDICT_PATTERN.findall(self._SINGLE_VERDICT_BODY)
        assert len(matches) == 1
        assert matches[0] == "needs-revision"

    def test_two_verdict_body_returns_count_two(self):
        """Body with two Verdict: lines returns count 2 — discipline is non-vacuous.

        This negative check confirms that count_verdict_lines detects duplicates,
        so the == 1 assertion in test_single_verdict_body_has_one_verdict_line
        would catch a body that carries multiple verdicts.
        """
        assert count_verdict_lines(self._TWO_VERDICT_BODY) == 2

    def test_inline_verdict_not_matched(self):
        """A Verdict: token mid-line (not a full-line match) is not counted.

        Confirms the regex is anchored so prose mentions of 'Verdict:' do
        not spuriously inflate the count.
        """
        body_with_inline = """\
## Discussion

The reviewer noted that Verdict: accepted is not a decision yet.
"""
        assert count_verdict_lines(body_with_inline) == 0


# ---------------------------------------------------------------------------
# Preset skill structural assertions (red before task-38)
# ---------------------------------------------------------------------------


class TestTaskReviewPresetSkillExists:
    """assets/skills/fbk-task-review/SKILL.md exists and references task-lens (AC-20).

    Red before task-38 authors the fbk-task-review skill.
    """

    def test_task_review_skill_file_exists(self):
        """assets/skills/fbk-task-review/SKILL.md is present in the skills directory."""
        assert _TASK_REVIEW_SKILL.exists(), (
            f"Skill file not found: {_TASK_REVIEW_SKILL} — "
            "fbk-task-review/SKILL.md must be created by the task-review-preset implementation (task-38)"
        )

    def test_task_review_skill_references_task_lens(self):
        """fbk-task-review SKILL.md references 'task-lens', the per-type lens it loads."""
        if not _TASK_REVIEW_SKILL.exists():
            pytest.skip("fbk-task-review/SKILL.md not yet created (red-phase skip)")
        text = _TASK_REVIEW_SKILL.read_text()
        assert "task-lens" in text, (
            "SKILL.md must reference 'task-lens' — "
            "the per-type lens the preset loads when reviewing a task file"
        )


class TestTaskReviewPresetDeclatesVerdictArtifact:
    """fbk-task-review SKILL.md names task-review.md and a Verdict: line as its output (AC-20).

    Red before task-38 authors the fbk-task-review skill.
    """

    def test_skill_names_task_review_artifact(self):
        """SKILL.md names 'task-review.md' as the output artifact."""
        if not _TASK_REVIEW_SKILL.exists():
            pytest.skip("fbk-task-review/SKILL.md not yet created (red-phase skip)")
        text = _TASK_REVIEW_SKILL.read_text()
        assert "task-review.md" in text, (
            "SKILL.md must name 'task-review.md' as the output artifact — "
            "downstream gates locate the verdict in this file"
        )

    def test_skill_declares_verdict_line_in_output(self):
        """SKILL.md documents that the output carries a Verdict: line."""
        if not _TASK_REVIEW_SKILL.exists():
            pytest.skip("fbk-task-review/SKILL.md not yet created (red-phase skip)")
        text = _TASK_REVIEW_SKILL.read_text()
        assert "Verdict:" in text, (
            "SKILL.md must document a 'Verdict:' line in its output — "
            "the verdict-bearing contract must be documented in the preset"
        )
