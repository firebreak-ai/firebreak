---
id: task-07
type: test
wave: 2
covers: [AC-16]
files_to_create:
  - assets/fbk-scripts/tests/test_capture_known_agents.py
completion_gate: "tests compile and fail before implementation"
---

# Objective

Write the unit tests for the known-Firebreak-agent set: it matches a known persona (scan root pointed at a fixture persona dir), rejects empty/unknown identity, and sets `STALE_FALLBACK` when the persona scan fails.

# Context

Subagent-completion events are aggregated only when the agent identity matches a known Firebreak agent. The known set is derived from a glob over installed persona files, reading the `name:` frontmatter key from each — the known set is every `name:` value. (Verified against `assets/agents/fbk-implementer.md`: the key is `name:`.) Adding a persona updates the filter with no separate maintenance step. A hardcoded fallback covers current agents when the scan fails, and a `STALE_FALLBACK` flag surfaces (later) as a report warning. Events with an empty or unrecognized agent identity are still recorded but excluded from aggregated subagent counts.

The scan root is parameterizable via the environment override `FBK_AGENTS_DIR` (default `~/.claude/agents`), so a test points it at a fixture persona directory (success branch) or a nonexistent dir (STALE_FALLBACK branch). The module exposes a test-callable re-derivation entry point so both branches are exercisable without import-time coupling.

Pinned contract (call verbatim):
- `known_agents.derive_known_agents(scan_root: str) -> tuple[set[str], bool]` — returns the `(known-name set, stale_fallback)` pair for a given scan root.
- `known_agents.is_known_agent(agent_type: str | None) -> bool` — membership predicate over the derived set.
- The module exposes a `STALE_FALLBACK` flag reflecting whether the active set came from the fallback.

Real persona files live at `assets/agents/*.md` carrying a `name:` frontmatter key (e.g. `fbk-implementer`, `fbk-council-architect`). Build a fixture persona dir under `tmp_path` with one or two `.md` files carrying a `name:` value, and point `FBK_AGENTS_DIR` there.

Import `from fbk.capture import known_agents` inside `try/except ImportError` with a module-level skipif.

# Instructions

1. Create `tests/test_capture_known_agents.py`; import `known_agents` inside `try/except ImportError`; module-level skipif. Build fixture persona files carrying the `name:` frontmatter key (e.g. a file whose frontmatter has `name: fbk-implementer`).
2. `test_known_persona_matches_via_derive`: build a `tmp_path` persona dir with a `.md` file whose frontmatter declares `name: fbk-implementer`; call `derive_known_agents(str(persona_dir))` and assert the returned name set contains `"fbk-implementer"` and the stale flag is `False`. Also assert, with `monkeypatch.setenv("FBK_AGENTS_DIR", str(persona_dir))`, that `is_known_agent("fbk-implementer") is True`.
3. `test_unknown_identity_rejected`: with the same fixture scan root via `FBK_AGENTS_DIR`, assert `is_known_agent("totally-unknown-agent") is False`.
4. `test_empty_identity_rejected`: assert `is_known_agent("") is False` and `is_known_agent(None) is False`.
5. `test_scan_failure_sets_stale_fallback`: call `derive_known_agents(str(tmp_path / "does-not-exist"))`; assert the returned stale flag is `True` AND the returned set is the non-empty hardcoded fallback (e.g. contains a current agent like `fbk-implementer`), and the call raised nothing. Also assert that with `FBK_AGENTS_DIR` pointed at the nonexistent dir, `is_known_agent("fbk-implementer") is True` (the fallback still answers) and the module's `STALE_FALLBACK` flag is truthy.
6. `test_scan_success_clears_stale_fallback`: call `derive_known_agents(str(valid_fixture_persona_dir))`; assert the returned stale flag is `False`.

# Files to create/modify

- `tests/test_capture_known_agents.py`

# Test requirements

- `test_known_persona_matches_via_derive` (unit): `derive_known_agents` returns a `name`-set containing the fixture persona's `name:` value with stale flag False; `is_known_agent` matches it.
- `test_unknown_identity_rejected` (unit): an unknown agent type → False.
- `test_empty_identity_rejected` (unit): empty/None identity → False.
- `test_scan_failure_sets_stale_fallback` (unit): `derive_known_agents` on a nonexistent root returns stale=True + the fallback set without raising; `STALE_FALLBACK` truthy.
- `test_scan_success_clears_stale_fallback` (unit): a successful derive returns stale=False.

# Acceptance criteria

AC-16 (subagent identity filtering and stale-fallback). Gate: tests compile and fail before implementation.

# Model

Sonnet — import-time derivation and scan-root override mechanism need judgment.

# Wave

2
