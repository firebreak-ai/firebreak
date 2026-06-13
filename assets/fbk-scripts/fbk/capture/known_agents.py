"""Known Firebreak agent set: derived from installed persona files with stale-fallback.

Derives the set of known agent identities at import time by scanning the persona
files under a configurable root (env-overridable via FBK_AGENTS_DIR). When the
scan fails or yields no names, falls back to a hardcoded set and raises the
STALE_FALLBACK flag so the report can surface a warning.

The membership predicate is_known_agent re-reads FBK_AGENTS_DIR on each call so
tests can point it at a fixture directory via monkeypatch.setenv without
reimporting the module.
"""

import glob
import os
import re

# ---------------------------------------------------------------------------
# Hardcoded fallback set
# ---------------------------------------------------------------------------

# Derived from the agent definition frontmatter at authoring time.
# Update this set when agents are added or removed.
FALLBACK_AGENTS = frozenset({
    "fbk-implementer",
    "fbk-architect",
    "fbk-spec-author",
    "fbk-product-author",
    "fbk-task-compiler",
    "fbk-improvement-analyst",
    "fbk-fresh-eyes-reviewer",
    "fbk-council-architect",
    "fbk-council-analyst",
    "fbk-council-builder",
    "fbk-council-guardian",
    "fbk-council-security",
    "fbk-council-advocate",
    "code-review-challenger",
    "code-review-detector",
    "test-reviewer",
})

# Regex to extract the name: value from frontmatter (first occurrence).
_NAME_PATTERN = re.compile(r"^name:\s*(\S+)", re.MULTILINE)


# ---------------------------------------------------------------------------
# Core derivation function
# ---------------------------------------------------------------------------


def derive_known_agents(scan_root: str) -> tuple[set[str], bool]:
    """Scan persona files under scan_root and return the known name set.

    Globs *.md files under scan_root, reads each file's leading frontmatter,
    and extracts the ``name:`` value. Returns a (names, stale) tuple:

    - On success (at least one name found): (names, False)
    - On any failure or empty result (no files, unreadable root, no names):
      (set(FALLBACK_AGENTS), True)

    Never raises.

    Args:
        scan_root: The directory to glob for *.md persona files.

    Returns:
        A tuple of (set of agent name strings, stale flag bool).
    """
    try:
        pattern = os.path.join(scan_root, "*.md")
        files = glob.glob(pattern)
        names: set[str] = set()

        for filepath in files:
            try:
                with open(filepath, encoding="utf-8") as f:
                    # Read only the first 4 KB — frontmatter is always near the top.
                    text = f.read(4096)
            except OSError:
                continue

            match = _NAME_PATTERN.search(text)
            if match:
                names.add(match.group(1))

        if names:
            return (names, False)

        # No names found (empty dir, no frontmatter, etc.) — fall back.
        return (set(FALLBACK_AGENTS), True)

    except Exception:  # noqa: BLE001
        return (set(FALLBACK_AGENTS), True)


# ---------------------------------------------------------------------------
# Module-level initialisation (import-time derivation for the production path)
# ---------------------------------------------------------------------------

_DEFAULT_SCAN_ROOT = os.environ.get(
    "FBK_AGENTS_DIR", os.path.expanduser("~/.claude/agents")
)

_KNOWN_AGENTS, STALE_FALLBACK = derive_known_agents(_DEFAULT_SCAN_ROOT)


# ---------------------------------------------------------------------------
# Membership predicate
# ---------------------------------------------------------------------------


def is_known_agent(agent_type: str | None) -> bool:
    """Return True if agent_type is a known Firebreak agent identity.

    Re-reads FBK_AGENTS_DIR on each call so the result honors per-call env
    overrides (e.g. monkeypatch.setenv in tests). Also updates the module-level
    STALE_FALLBACK so the report reads the current flag.

    Returns False for None or empty string without a scan.

    Args:
        agent_type: The agent identity string to check, or None.

    Returns:
        True if agent_type is in the current known-agent set, False otherwise.
    """
    if not agent_type:
        return False

    # Re-derive from the current env value so per-call overrides are honoured.
    global _KNOWN_AGENTS, STALE_FALLBACK  # noqa: PLW0603

    scan_root = os.environ.get(
        "FBK_AGENTS_DIR", os.path.expanduser("~/.claude/agents")
    )
    _KNOWN_AGENTS, STALE_FALLBACK = derive_known_agents(scan_root)

    return agent_type in _KNOWN_AGENTS
