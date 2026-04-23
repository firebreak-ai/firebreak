"""Tests for fbk.gates.spec section validation and open-questions logic."""

import pytest
from fbk.gates.spec import check_section, check_open_questions


class TestCheckSection:
    """Tests for check_section() behavioral contract."""

    def test_missing_section_produces_failure(self):
        """Spec missing ## Problem section produces failure."""
        spec = "## Overview\nSome content here"
        failures = check_section(spec, "## Problem")
        assert len(failures) > 0
        assert any("Missing section" in f for f in failures)

    def test_empty_section_produces_failure(self):
        """Spec with ## Problem but only whitespace body produces failure."""
        spec = "## Problem\n   \n\n## Overview\nSome content"
        failures = check_section(spec, "## Problem")
        assert len(failures) > 0
        assert any("Empty section" in f for f in failures)

    def test_valid_section_passes(self):
        """Spec with ## Problem and body content produces no failure."""
        spec = "## Problem\nThis is a valid problem statement with content."
        failures = check_section(spec, "## Problem")
        assert len(failures) == 0


class TestCheckOpenQuestions:
    """Tests for check_open_questions() behavioral contract."""

    def test_bare_question_without_rationale_fails(self):
        """Bullet with only '- Why?' and no rationale produces failure."""
        bullets = ["- Why?"]
        failures = check_open_questions(bullets)
        assert len(failures) > 0
        assert any("rationale" in f.lower() for f in failures)

    def test_inline_rationale_passes(self):
        """Bullet with inline rationale '- Why? Because X' produces no failure."""
        bullets = ["- Why? Because X"]
        failures = check_open_questions(bullets)
        assert len(failures) == 0

    def test_indented_continuation_rationale_passes(self):
        """Bullet with indented continuation line produces no failure."""
        bullets = ["- Why?", "  Because the reason is clear"]
        failures = check_open_questions(bullets)
        assert len(failures) == 0
