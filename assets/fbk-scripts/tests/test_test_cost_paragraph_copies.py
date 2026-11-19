"""The paragraph on what a test costs lives in three files; the copies must not drift.

Each reader receives only its own brief, so the spec guide, the test-authoring
guide and the test cleanup trim brief each carry the paragraph (decisions log,
2026-11-05). The trim brief's copy omits one clause by decision: a brownfield
suite has no spec examples. Change one copy and this test names the others.
"""

from pathlib import Path
import re


ASSETS = Path(__file__).resolve().parents[2]
GUIDES = ("fbk-docs/workflow/spec.md", "fbk-docs/workflow/test-authoring.md")
TRIM_BRIEF = "skills/fbk-test-cleanup/test-trim.md"
SPEC_ONLY_CLAUSE = "; spec examples become those tests"
PARAGRAPH = re.compile(r"Tests add maintenance work.*?fails at least one\.", re.DOTALL)


def paragraph(relative):
    match = PARAGRAPH.search((ASSETS / relative).read_text(encoding="utf-8"))
    assert match, f"{relative}: the paragraph on what a test costs was not found"
    return match.group(0)


def test_guides_carry_the_same_paragraph():
    spec, test_authoring = (paragraph(guide) for guide in GUIDES)
    assert spec == test_authoring, (
        f"{GUIDES[0]} and {GUIDES[1]} differ; carry the change to both and to {TRIM_BRIEF}"
    )


def test_trim_brief_carries_the_guides_paragraph_without_the_spec_clause():
    guide = paragraph(GUIDES[1])
    assert SPEC_ONLY_CLAUSE in guide
    assert paragraph(TRIM_BRIEF) == guide.replace(SPEC_ONLY_CLAUSE, ""), (
        f"{TRIM_BRIEF} differs from {GUIDES[1]} by more than the spec clause; "
        f"carry the change to all three copies"
    )
