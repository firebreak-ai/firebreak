---
id: task-25
type: implementation
wave: 2
covers: [AC-16]
files_to_create:
  - assets/fbk-scripts/fbk/capture/known_agents.py
test_tasks: [task-07]
completion_gate: "task-07 tests pass"
---

# 1 Objective

Produce the known-Firebreak-agent set: derived at import from the `name:` frontmatter of installed persona files under a scan root (env-overridable), with a hardcoded fallback set and a `STALE_FALLBACK` flag when the scan fails, plus a membership predicate that rejects empty/unknown identities.

# 2 Context

Subagent-completion events are aggregated only when the agent identity matches a known Firebreak agent. The known set is every `name:` value found in the persona files — verified against `assets/agents/fbk-implementer.md`, whose frontmatter key is `name:` (value `fbk-implementer`). Deriving the set from those files means adding a persona updates the filter with no separate maintenance step. When the scan fails (no persona tree, unreadable dir), the module falls back to a hardcoded set of the current agents and raises a `STALE_FALLBACK` flag the report later surfaces as a warning. A scan failure never raises. Events with an empty or unrecognized identity are still recorded elsewhere but excluded from aggregated counts — this module just answers "is this a known agent?".

The scan root honors env override `FBK_AGENTS_DIR` (default `~/.claude/agents`), so a test can point it at a fixture persona dir to exercise the success branch without an installed persona tree.

# 3 Instructions

1. Create `fbk/capture/known_agents.py`. Define a hardcoded fallback set `FALLBACK_AGENTS` containing the current Firebreak agent names — derive the list by globbing `assets/agents/*.md` frontmatter at authoring time; at minimum include `fbk-implementer` and the council personas (e.g. `fbk-council-architect`). Include the agents present under `assets/agents/`. Completion: the fallback set is non-empty and contains `fbk-implementer`.
2. Implement `derive_known_agents(scan_root: str) -> tuple[set[str], bool]`. Glob `*.md` under `scan_root`; for each file read its frontmatter and extract the `name:` value (the first `name:` key in the leading `---`-fenced YAML-ish block — a simple line scan `^name:\s*(\S+)` is sufficient; do NOT import a YAML library, matching the no-new-dependency rule). Return `(set_of_names, stale_flag)`. On a scan that yields at least one name → `(names, False)`. On any failure or an empty result (no files / unreadable root) → return `(set(FALLBACK_AGENTS), True)` without raising. Completion: a fixture dir with a `name: fbk-implementer` file → set contains `fbk-implementer`, stale `False`; a nonexistent root → fallback set, stale `True`, no raise.
3. At import time, resolve the active scan root from `os.environ.get("FBK_AGENTS_DIR", os.path.expanduser("~/.claude/agents"))`, call `derive_known_agents` once, and store the result in module-level `_KNOWN_AGENTS` and `STALE_FALLBACK`. Completion: importing the module sets `STALE_FALLBACK` and a known-set.
4. Implement `is_known_agent(agent_type: str | None) -> bool`. Return `False` for `None` or empty string; otherwise return membership in the active known-set. IMPORTANT for testability: resolve the active set by re-reading `FBK_AGENTS_DIR` at call time (call `derive_known_agents` on the current env value) rather than freezing only the import-time set — so a test that sets `FBK_AGENTS_DIR` via `monkeypatch.setenv` and then calls `is_known_agent` sees the fixture set, and a test pointing at a nonexistent dir still gets fallback answers and a truthy `STALE_FALLBACK`. Keep the import-time derivation too (for the production hot path) but let the predicate honor a per-call env override. Update the module-level `STALE_FALLBACK` to reflect the most recent derivation so the report reads the right flag. Completion: with `FBK_AGENTS_DIR` at a fixture dir, `is_known_agent("fbk-implementer")` is True and `is_known_agent("totally-unknown-agent")`/`is_known_agent("")`/`is_known_agent(None)` are False; with `FBK_AGENTS_DIR` at a nonexistent dir, `is_known_agent("fbk-implementer")` is True (fallback) and `STALE_FALLBACK` is truthy.

# 4 Files to create/modify

- Create `fbk/capture/known_agents.py`

# 5 Test requirements

Makes task-07 (`tests/test_capture_known_agents.py`) pass: `derive_known_agents` returns the fixture persona's `name:` with stale `False`; unknown/empty/None identities rejected; a nonexistent root returns the fallback set with stale `True` without raising; a successful derive clears the stale flag.

# 6 Acceptance criteria

Primary: task-07's tests pass. Covers AC-16 (subagent identity filtering and stale-fallback).

# 7 Model

Sonnet

# 8 Wave

2
