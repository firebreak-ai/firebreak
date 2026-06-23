"""Structural test: zero remaining callers for the four superseded domain-specific review agents.

The migration replaces four domain-named agents with two generic role agents.
Once migration is complete, the bare registry names of the removed agents must
not appear in any active context asset (assets/skills/** or assets/agents/**),
in prose or in structured fields.

Scope: assets/skills/ and assets/agents/ — by limiting the walk to these two
directories, ai-docs/ and assets/fbk-scripts/tests/ are excluded by construction.
Those paths are legitimately allowed to mention the old names (historical breakdown
notes and test fixtures); restricting the scope replaces an explicit allowlist.

Red phase: the old agent files still exist under assets/agents/ and their
frontmatter name: fields contain the bare removed names, so these tests fail
until task-42 deletes those agent files and removes all prose references.
"""

import re
from pathlib import Path
from typing import Iterator

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parents[3]

# Bare registry names that must not appear in any active context asset after migration.
REMOVED_NAMES = [
    "code-review-detector",
    "code-review-challenger",
    "test-reviewer",
    "fbk-fresh-eyes-reviewer",
]

# Active context asset directories — the allowlist is the scope itself.
_ACTIVE_DIRS = [
    _REPO_ROOT / "assets" / "skills",
    _REPO_ROOT / "assets" / "agents",
]

# Segments whose presence in a scanned path would indicate a scope violation.
_EXCLUDED_SEGMENTS = {"ai-docs", "tests"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _iter_active_md_files() -> Iterator[Path]:
    """Yield every *.md file under assets/skills/ and assets/agents/ (recursive)."""
    for directory in _ACTIVE_DIRS:
        yield from directory.rglob("*.md")


def _boundary_pattern(name: str) -> re.Pattern:
    """Return a whole-token boundary pattern for the given bare name.

    Uses a negative lookbehind and lookahead for word-boundary-compatible
    characters (word chars and hyphens) so that 'test-reviewer' does not
    match inside 'task-reviewer' or 'test-review'.
    """
    escaped = re.escape(name)
    return re.compile(rf"(?<![\w-]){escaped}(?![\w-])")


# ---------------------------------------------------------------------------
# Scope-guard test
# ---------------------------------------------------------------------------


class TestScopeExcludesHistoricalAndFixtures:
    """The active-file walk does not descend into ai-docs/ or tests/.

    Documents that the allowlist is the scope boundary itself: by restricting
    the walk to assets/skills/ and assets/agents/, historical breakdown notes
    and test fixtures are excluded without an explicit allowlist entry.
    """

    def test_scanned_paths_contain_no_excluded_segments(self):
        """No scanned path passes through ai-docs/ or assets/fbk-scripts/tests/."""
        violating = [
            str(p)
            for p in _iter_active_md_files()
            if any(segment in p.parts for segment in _EXCLUDED_SEGMENTS)
        ]
        assert not violating, (
            "Scope violation: the following paths are inside excluded directories "
            f"but were returned by the active-file walk: {violating}"
        )


# ---------------------------------------------------------------------------
# Word-boundary guard (inline correctness check)
# ---------------------------------------------------------------------------


class TestBoundaryPatternGuards:
    """The whole-token boundary match does not false-positive on sibling names.

    Verifies the pattern shape before trusting it to gate the zero-caller check.
    """

    def test_test_reviewer_pattern_does_not_match_task_reviewer(self):
        """Pattern for 'test-reviewer' does not match the string 'task-reviewer'."""
        pattern = _boundary_pattern("test-reviewer")
        assert not pattern.search("task-reviewer"), (
            "Boundary pattern for 'test-reviewer' must not match 'task-reviewer' — "
            "check the lookbehind/lookahead guards"
        )

    def test_test_reviewer_pattern_does_not_match_test_review(self):
        """Pattern for 'test-reviewer' does not match the bare string 'test-review'."""
        pattern = _boundary_pattern("test-reviewer")
        assert not pattern.search("test-review"), (
            "Boundary pattern for 'test-reviewer' must not match 'test-review'"
        )

    def test_test_reviewer_pattern_matches_exact_token(self):
        """Pattern for 'test-reviewer' matches 'test-reviewer' as a whole token."""
        pattern = _boundary_pattern("test-reviewer")
        assert pattern.search("spawn the test-reviewer agent"), (
            "Boundary pattern for 'test-reviewer' must match the exact token"
        )

    def test_code_review_detector_pattern_does_not_match_code_review(self):
        """Pattern for 'code-review-detector' does not match the prefix 'code-review'."""
        pattern = _boundary_pattern("code-review-detector")
        assert not pattern.search("spawn the code-review agent"), (
            "Boundary pattern for 'code-review-detector' must not match 'code-review'"
        )


# ---------------------------------------------------------------------------
# Zero-caller tests — parametrized over each removed name
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("removed_name", REMOVED_NAMES)
class TestNoActiveCallerForRemovedAgent:
    """Each removed agent name appears zero times across assets/skills/ and assets/agents/.

    A hit is any occurrence of the bare registry name as a whole token (word-boundary
    match) in any *.md file under the active context asset directories.
    """

    def test_no_active_caller_for_removed_agent(self, removed_name: str):
        """Bare removed name is absent from all active context assets.

        Scans prose and structured fields (including frontmatter name: lines) in
        every *.md file under assets/skills/ and assets/agents/. On failure, lists
        each offending file so the red-phase output directly enumerates what
        task-42 must remove or repoint.
        """
        pattern = _boundary_pattern(removed_name)
        hits = [
            str(path)
            for path in _iter_active_md_files()
            if pattern.search(path.read_text())
        ]
        assert not hits, (
            f"Removed agent '{removed_name}' still referenced in {len(hits)} active "
            f"context asset(s) — task-42 must remove or repoint each:\n"
            + "\n".join(f"  {h}" for h in sorted(hits))
        )
