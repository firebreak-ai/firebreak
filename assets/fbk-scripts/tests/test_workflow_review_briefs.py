from pathlib import Path

import pytest

from fbk.workflow import review
from fbk.workflow.store import WorkflowError


@pytest.fixture
def installation(tmp_path, monkeypatch):
    """A copy of the shipped review briefs the runtime reads instead of the repository's."""
    canonical = Path(review.__file__).resolve().parents[3] / "fbk-docs"
    module = tmp_path / "fbk-scripts/fbk/workflow/review.py"
    module.parent.mkdir(parents=True)
    for relative in review.REVIEW_BRIEFS:
        target = tmp_path / "fbk-docs" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text((canonical / relative).read_text())
    monkeypatch.setattr(review, "__file__", str(module))
    return tmp_path / "fbk-docs"


def test_a_phase_brief_missing_a_section_names_the_file_and_section(installation):
    brief = installation / "review/phase-spec.md"
    brief.write_text(brief.read_text().replace("## Check", "## Checks"))
    with pytest.raises(WorkflowError, match=r"review/phase-spec\.md is missing its Check section"):
        review.phase_brief("spec")


def test_editing_a_brief_changes_the_review_fingerprint(installation):
    before = review.review_brief_digests()
    brief = installation / "review/reviewer-brief.md"
    brief.write_text(brief.read_text() + "Keep findings short.\n")
    after = review.review_brief_digests()
    assert after["review/reviewer-brief.md"] != before["review/reviewer-brief.md"]
    assert {k: v for k, v in after.items() if k != "review/reviewer-brief.md"} == {
        k: v for k, v in before.items() if k != "review/reviewer-brief.md"
    }


def test_a_persona_gives_its_role_and_only_this_phase_focus(installation):
    text = review.persona("builder", "design")
    assert text.startswith("Council member: builder. Identity: You are a staff engineer")
    assert "Duty: Contest any proposal" in text
    assert "Design focus: The hard part of each choice" in text
    assert "Breakdown focus" not in text and "Spec focus" not in text


def test_a_persona_without_a_duty_omits_it(installation):
    assert "Duty:" not in review.persona("architect", "spec")


def test_a_persona_missing_its_phase_section_names_the_file_and_section(installation):
    brief = installation / "review/council/guardian.md"
    brief.write_text(brief.read_text().replace("## Spec", "## Specs"))
    with pytest.raises(WorkflowError, match=r"review/council/guardian\.md is missing its Spec section"):
        review.persona("guardian", "spec")


def test_the_council_brief_gives_the_shared_part_and_this_step_only(installation):
    text = review.council_brief("Opening", "spec", "demo")
    assert text.startswith("You are one member of a review council for the spec work of Firebreak unit demo.")
    assert "Read the work alone" in text
    assert "Give support or contest" not in text


def test_editing_a_persona_changes_the_review_fingerprint(installation):
    before = review.review_brief_digests()
    brief = installation / "review/council/analyst.md"
    brief.write_text(brief.read_text() + "Keep findings short.\n")
    assert review.review_brief_digests()["review/council/analyst.md"] != before["review/council/analyst.md"]


def test_the_reviewer_brief_gives_only_the_sections_asked_for(installation):
    full = review.reviewer_brief("spec", "demo")
    assert full.startswith("Independently review the spec work for Firebreak unit demo.")
    evidence = review.reviewer_brief("spec", "demo", ("Evidence",))
    assert "Do not infer a defect from a missing explanation" in evidence
    assert "Independently review" not in evidence
    assert "Report every blocker" not in evidence
    assert "Report every blocker" in review.reviewer_brief("spec", "demo", ("Evidence", "Reporting"))
    assert "Report every blocker" not in review.reviewer_brief("spec", "demo", ("Evidence", "Findings"))
    assert "Report every blocker" in full


def test_a_reviewer_brief_missing_a_section_names_it(installation):
    brief = installation / "review/reviewer-brief.md"
    brief.write_text(brief.read_text().replace("## Evidence", "## Proof"))
    with pytest.raises(WorkflowError, match=r"review/reviewer-brief\.md is missing its Evidence section"):
        review.reviewer_brief("spec", "demo")
