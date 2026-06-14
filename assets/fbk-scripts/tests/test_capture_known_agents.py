"""Unit tests for fbk.capture.known_agents — identity filtering and stale-fallback.

Tests cover:
- derive_known_agents matches a fixture persona dir and returns stale=False
- is_known_agent returns True for a known persona name via FBK_AGENTS_DIR
- Unknown agent identity returns False
- Empty and None identity return False
- derive_known_agents on a nonexistent dir returns the hardcoded fallback and stale=True
- A successful scan clears the stale flag
"""

import os
import pytest

# Red phase: known_agents module does not exist yet.
try:
    from fbk.capture import known_agents
    KNOWN_AGENTS_AVAILABLE = True
except ImportError:
    KNOWN_AGENTS_AVAILABLE = False

from tests import capture_fixtures  # noqa: F401  (imported for consistency; not used directly here)

pytestmark = pytest.mark.skipif(
    not KNOWN_AGENTS_AVAILABLE,
    reason="fbk.capture.known_agents module not yet implemented",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_persona(base_dir, filename, name_value):
    """Write a minimal .md persona file with a name: frontmatter key."""
    path = os.path.join(str(base_dir), filename)
    with open(path, "w") as f:
        f.write(f"---\nname: {name_value}\n---\n\nPersona body.\n")
    return path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDeriveKnownAgents:
    """Tests for known_agents.derive_known_agents(scan_root: str) -> tuple[set[str], bool]."""

    def test_known_persona_matches_via_derive(self, tmp_path, monkeypatch):
        """derive_known_agents reads name: frontmatter and returns the name set with stale=False.

        Also verifies that is_known_agent returns True when FBK_AGENTS_DIR points
        at the same fixture directory.
        """
        persona_dir = tmp_path / "agents"
        persona_dir.mkdir()
        _write_persona(persona_dir, "fbk-implementer.md", "fbk-implementer")

        name_set, stale = known_agents.derive_known_agents(str(persona_dir))

        assert "fbk-implementer" in name_set
        assert stale is False

        monkeypatch.setenv("FBK_AGENTS_DIR", str(persona_dir))
        assert known_agents.is_known_agent("fbk-implementer") is True

    def test_scan_success_clears_stale_fallback(self, tmp_path):
        """A successful derive call returns stale=False."""
        persona_dir = tmp_path / "agents"
        persona_dir.mkdir()
        _write_persona(persona_dir, "fbk-council-architect.md", "fbk-council-architect")

        _, stale = known_agents.derive_known_agents(str(persona_dir))

        assert stale is False

    def test_scan_failure_sets_stale_fallback(self, tmp_path, monkeypatch):
        """derive_known_agents on a nonexistent root returns stale=True and the hardcoded fallback.

        The call must not raise. The fallback set must be non-empty and contain
        at least one current agent (fbk-implementer). When FBK_AGENTS_DIR points
        at the nonexistent dir, is_known_agent still returns True via the fallback,
        and the module-level STALE_FALLBACK flag is truthy.
        """
        nonexistent = tmp_path / "does-not-exist"

        name_set, stale = known_agents.derive_known_agents(str(nonexistent))

        assert stale is True
        assert len(name_set) > 0
        assert "fbk-implementer" in name_set

        monkeypatch.setenv("FBK_AGENTS_DIR", str(nonexistent))
        assert known_agents.is_known_agent("fbk-implementer") is True
        assert known_agents.STALE_FALLBACK


class TestIsKnownAgent:
    """Tests for known_agents.is_known_agent(agent_type: str | None) -> bool."""

    def test_unknown_identity_rejected(self, tmp_path, monkeypatch):
        """An agent name not present in the persona dir returns False."""
        persona_dir = tmp_path / "agents"
        persona_dir.mkdir()
        _write_persona(persona_dir, "fbk-implementer.md", "fbk-implementer")

        monkeypatch.setenv("FBK_AGENTS_DIR", str(persona_dir))
        assert known_agents.is_known_agent("totally-unknown-agent") is False

    def test_empty_identity_rejected(self, tmp_path, monkeypatch):
        """Empty string and None identity both return False."""
        persona_dir = tmp_path / "agents"
        persona_dir.mkdir()
        _write_persona(persona_dir, "fbk-implementer.md", "fbk-implementer")

        monkeypatch.setenv("FBK_AGENTS_DIR", str(persona_dir))
        assert known_agents.is_known_agent("") is False
        assert known_agents.is_known_agent(None) is False
