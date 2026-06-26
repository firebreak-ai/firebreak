"""Structural assertions for the two generic role agents: review-researcher and review-challenger.

Tests cover:
- fbk-review-researcher.md exists and carries the exact registry name "review-researcher"
- fbk-review-challenger.md exists and carries the exact registry name "review-challenger"
- The researcher persona states it surfaces candidates without fix authority and without issuing verdicts
- The challenger persona states it reads the artifact cold before receiving candidates and generates no new findings
- Neither persona hardcodes a specific review domain (code-review, test-review, fresh-eyes, doc-reconcile,
  quality-scan) into its identity, keeping the agents reusable across lenses
"""

import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parents[3]
_RESEARCHER_AGENT = _REPO_ROOT / "assets" / "agents" / "fbk-review-researcher.md"
_CHALLENGER_AGENT = _REPO_ROOT / "assets" / "agents" / "fbk-review-challenger.md"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NAME_PATTERN = re.compile(r"^name:\s*(\S+)", re.MULTILINE)


def _read_name(text: str) -> str | None:
    """Extract the first 'name:' frontmatter value from agent text.

    Uses the same regex shape as fbk.capture.known_agents (^name:\\s*(\\S+)).
    Returns None when no match is found.
    """
    match = _NAME_PATTERN.search(text)
    return match.group(1) if match else None


# ---------------------------------------------------------------------------
# Registry name assertions
# ---------------------------------------------------------------------------


class TestResearcherRegistryName:
    """fbk-review-researcher.md exists and carries the exact registry name "review-researcher"."""

    def test_researcher_agent_exists(self):
        """fbk-review-researcher.md is present in the agents directory."""
        assert _RESEARCHER_AGENT.exists(), (
            f"Agent file not found: {_RESEARCHER_AGENT} — "
            "fbk-review-researcher.md must be created by the role-agents implementation"
        )

    def test_researcher_agent_has_exact_registry_name(self):
        """fbk-review-researcher.md frontmatter name: equals exactly "review-researcher"."""
        if not _RESEARCHER_AGENT.exists():
            pytest.skip("fbk-review-researcher.md not yet created")
        text = _RESEARCHER_AGENT.read_text()
        assert _read_name(text) == "review-researcher"


class TestChallengerRegistryName:
    """fbk-review-challenger.md exists and carries the exact registry name "review-challenger"."""

    def test_challenger_agent_exists(self):
        """fbk-review-challenger.md is present in the agents directory."""
        assert _CHALLENGER_AGENT.exists(), (
            f"Agent file not found: {_CHALLENGER_AGENT} — "
            "fbk-review-challenger.md must be created by the role-agents implementation"
        )

    def test_challenger_agent_has_exact_registry_name(self):
        """fbk-review-challenger.md frontmatter name: equals exactly "review-challenger"."""
        if not _CHALLENGER_AGENT.exists():
            pytest.skip("fbk-review-challenger.md not yet created")
        text = _CHALLENGER_AGENT.read_text()
        assert _read_name(text) == "review-challenger"


# ---------------------------------------------------------------------------
# Researcher discipline assertions
# ---------------------------------------------------------------------------


class TestResearcherPersonaDisciplines:
    """The researcher persona states it surfaces candidates with no fix authority and no verdicts."""

    def test_researcher_claims_no_fix_authority_or_verdicts(self):
        """Researcher persona body contains a no-fix token and a no-verdict token.

        Checks co-occurrence of:
        - no-fix token: "no fix authority" or "does not fix"
        - no-verdict token: "no verdict" or "does not rule"
        """
        if not _RESEARCHER_AGENT.exists():
            pytest.skip("fbk-review-researcher.md not yet created")
        text = _RESEARCHER_AGENT.read_text().lower()
        has_no_fix = ("no fix authority" in text) or ("does not fix" in text)
        has_no_verdict = ("no verdict" in text) or ("does not rule" in text)
        assert has_no_fix, (
            "Researcher persona must state it has no fix authority "
            "(expected 'no fix authority' or 'does not fix')"
        )
        assert has_no_verdict, (
            "Researcher persona must state it issues no verdicts "
            "(expected 'no verdict' or 'does not rule')"
        )


# ---------------------------------------------------------------------------
# Challenger discipline assertions
# ---------------------------------------------------------------------------


class TestChallengerPersonaDisciplines:
    """The challenger persona states it reads cold before receiving candidates and adds no new findings."""

    def test_challenger_reads_cold_and_adds_no_findings(self):
        """Challenger persona body contains a cold-read token and a no-new-findings token.

        Checks co-occurrence of:
        - cold-read token: "cold" or "before receiving"
        - no-new-findings token: "no new finding" or "generates no"
        """
        if not _CHALLENGER_AGENT.exists():
            pytest.skip("fbk-review-challenger.md not yet created")
        text = _CHALLENGER_AGENT.read_text().lower()
        has_cold_read = ("cold" in text) or ("before receiving" in text)
        has_no_new_findings = ("no new finding" in text) or ("generates no" in text)
        assert has_cold_read, (
            "Challenger persona must state it reads the artifact cold "
            "(expected 'cold' or 'before receiving')"
        )
        assert has_no_new_findings, (
            "Challenger persona must state it generates no new findings "
            "(expected 'no new finding' or 'generates no')"
        )


# ---------------------------------------------------------------------------
# Generic-persona (no-domain) assertions
# ---------------------------------------------------------------------------

_DOMAIN_TOKENS = frozenset(
    {"code-review", "test-review", "fresh-eyes", "doc-reconcile", "quality-scan"}
)


class TestPersonasNameNoDomain:
    """Neither persona hardcodes a specific review domain into its identity.

    Pins the generic-persona contract that makes the agents reusable across lenses.
    Asserts absence of bare domain tokens: code-review, test-review, fresh-eyes,
    doc-reconcile, quality-scan.
    """

    def test_researcher_persona_names_no_domain(self):
        """Researcher persona body contains none of the domain-specific review-type tokens."""
        if not _RESEARCHER_AGENT.exists():
            pytest.skip("fbk-review-researcher.md not yet created")
        text = _RESEARCHER_AGENT.read_text().lower()
        present_tokens = [token for token in _DOMAIN_TOKENS if token in text]
        assert not present_tokens, (
            f"Researcher persona must not name a specific review domain; "
            f"found domain tokens: {present_tokens}"
        )

    def test_challenger_persona_names_no_domain(self):
        """Challenger persona body contains none of the domain-specific review-type tokens."""
        if not _CHALLENGER_AGENT.exists():
            pytest.skip("fbk-review-challenger.md not yet created")
        text = _CHALLENGER_AGENT.read_text().lower()
        present_tokens = [token for token in _DOMAIN_TOKENS if token in text]
        assert not present_tokens, (
            f"Challenger persona must not name a specific review domain; "
            f"found domain tokens: {present_tokens}"
        )
