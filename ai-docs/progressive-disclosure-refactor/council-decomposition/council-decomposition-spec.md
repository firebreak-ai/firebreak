# Council Decomposition

Child spec for Finding 1 of `ai-docs/progressive-disclosure-refactor/progressive-disclosure-refactor-spec.md`.

Applies the parent spec's progressive-disclosure principles (strict relevance, per-load-path Necessity, asset-type taxonomy, tree-shaped routing) and Decision 8 (judgment-based council sizing; topmost-where-always-relevant placement) to `assets/skills/fbk-council/SKILL.md`.

---

## Problem

`assets/skills/fbk-council/SKILL.md` is 947 lines. A single file conflates: trigger phrases, council members table, two prescriptive tier protocols (Quick / Full), every facilitation phase (0 through 5.5), orchestrator persona content, decision protocol, conflict resolution, compaction recovery, Ralph Wiggum integration, immutable-core security boundary, and the full observability/logging command reference.

Every council invocation loads the entire file. Most invocations do not encounter compaction recovery, are not running inside a Ralph loop, do not require the full decision-protocol or conflict-resolution machinery, and do not need the advanced observability command reference. The current structure violates strict relevance (instructions for inactive modes load every time), per-load-path Necessity (multiple modes' content occupies context simultaneously), and asset-type discipline (the skill body holds substantial reference content that belongs in routed leaves).

## Goals

**In scope:**

- Reduce per-invocation context load by extracting conditionally-relevant content to leaves under `assets/fbk-docs/fbk-council/`, loaded only when their condition fires.
- Replace the Quick/Full tier prescription with a single judgment-based instruction: the orchestrator sizes the council appropriately for the task by selecting relevant members from the members table.
- Reduce orchestrator-persona content to the minimal facilitator instructions that pass the Necessity Test (~5 instructions). Keep them inline in the SKILL since the user's main Claude IS the orchestrator and no subagent extraction is performed.
- Preserve every existing trigger phrase, downstream caller, command-line interface, and observable output schema.
- Apply the "topmost where always relevant" placement principle: instructions live at the most-trunk-like node where they are *always* relevant when the parent loads. Always-relevant content stays in the SKILL; conditionally-relevant content extracts to leaves.

**Non-goals:**

- No changes to the six council member agent personas (`fbk-council-{architect,builder,guardian,security,advocate,analyst}.md`). They remain as separate agent files spawned by the orchestrator.
- No changes to `assets/fbk-scripts/fbk/council/session_state.py`, `session_logger.py`, `session_manager.py`, `ralph.py`, or their command-line interfaces.
- No changes to the council recommendation output schema, Phase 5 consensus output structure, or Phase 5.5 self-evaluation output structure.
- No changes to the immutable-core security boundary (still inline in SKILL).
- No new authoring of asset-graph detectors. Verification depends on the preceding `asset-graph-detectors` spec; this spec consumes those detectors but does not author them.
- No removal of `--no-log`, `--no-log` quick variant, `/fbk-assemble`, `/fbk-qcouncil`, or any "convene the council" / "assemble the team" / "quick council" semantic trigger.
- No new top-level `fbk` commands.
- No restructuring of council-state.json schema or its consumers.

## User-facing behavior

Trigger phrases, output schemas, and downstream caller contracts are preserved. Existing invocation paths produce equivalent output to the current SKILL with one acknowledged behavioral change for `/fbk-council quick` and `/fbk-qcouncil` (see §3.1 below).

Equivalent paths:

- `/fbk-council` with a substantive task → orchestrator selects an appropriate council, runs the existing phases, produces the existing Phase 5 output schema.
- `/fbk-council quick` and `/fbk-qcouncil` → see §3.1 (acknowledged behavioral change pending DECISION-B in spec review).
- `/fbk-council --no-log` and `/fbk-council quick --no-log` → logging is suppressed.
- `/fbk-assemble`, "assemble the team", "convene the council", "quick council" → all still trigger the skill.
- Resuming after auto-compaction → recovery dispatch in the SKILL runs `recovery-check`; when `recovering: true` is returned, the orchestrator reads the compaction-recovery leaf and resumes from the recorded `current_phase`.
- Running inside a Ralph loop → Ralph dispatch in the SKILL routes to the Ralph integration leaf; the orchestrator emits the same `<!-- COUNCIL_STATUS: CONTINUE -->` / `<!-- COUNCIL_STATUS: COUNCIL_COMPLETE -->` markers and updates `~/.claude/council-logs/council-state.json` with the same schema.
- Consensus-failure path (Round 1 ends without consensus, optionally surfacing unresolved conflict) → consensus-failure leaf loads; weighted-voting / evidence-consensus produces the same documented decision output, and the same conflict-resolution rules apply for any surfaced deadlock — single leaf, no dispatch chain.
- `/fbk-spec-review` → continues to invoke `/fbk-council` with no caller change required.

### 3.1 Quick council semantics

`/fbk-council quick` and `/fbk-qcouncil` carry a soft default: a 3-agent council biased toward Architect + Builder + Guardian, with Phase 1 alignment-round skipped. The orchestrator may override the default per task — substituting members or running Phase 1 — when task content explicitly requires it (e.g., the task names security, users/UX, or metrics, in which case the corresponding member is substituted). This preserves user habits ("quick = fast, technical, predictable composition") while leaving room for judgment when the default would mislead.

The default is observable but soft. Users invoking `/fbk-qcouncil` for a typical "quick technical opinion" task will see Architect+Builder+Guardian as before. Users invoking it for a task that names a non-default domain will see appropriate substitution.

Aside from this single overridable default, the only user-observable difference from the current SKILL is faster orchestrator setup on invocations where conditional content does not load. No content is removed from the system; only relocated.

## Technical approach

### 4.1 Final structure

```
assets/skills/fbk-council/SKILL.md          (rewritten; ~300-400 lines, down from 947)
assets/fbk-docs/fbk-council/                (new directory)
├── consensus-failure.md                    (new — merged decision-protocol + conflict-resolution)
├── compaction-recovery.md                  (new)
└── ralph-integration.md                    (new)
tests/sdl-workflow/test-council-skill-structure.sh  (new — see §5.1)
```

**Naming convention precedent.** Council content lives at `assets/fbk-docs/fbk-council/` rather than `fbk-docs/fbk-sdl-workflow/` because `/fbk-council` is not part of the SDL pipeline. This establishes a convention: skills outside the SDL pipeline that need conditional leaves use `fbk-docs/<skill-name>/`. SDL-pipeline skills continue to use `fbk-docs/fbk-sdl-workflow/<topic>.md`. This precedent applies to the parent spec's Findings 6 (`code-review-guide-split`) and 7 (`test-reviewer-overhaul`), which will create per-area subdirectories under the same convention.

### 4.2 SKILL.md inline contents (always relevant when council fires)

The rewritten SKILL contains, in order:

1. YAML frontmatter — `name: fbk-council` (unchanged); description updated to reflect judgment-based sizing. New description verbatim: `Assembles the development council — a team of specialized agents (selected per task from architect, builder, guardian, security, advocate, analyst) who discuss collaboratively, ask clarifying questions, and work toward consensus recommendations.` Preserves all discovery-relevant keywords (architect, builder, guardian, security, advocate, analyst, council, consensus, collaboratively, clarifying, recommendations) while removing the literal "6" that no longer accurately describes the post-refactor behavior.
2. Trigger phrases section (unchanged: `/fbk-council`, `/fbk-council quick`, `/fbk-qcouncil`, `/fbk-council --no-log`, `/fbk-council quick --no-log`, `/fbk-assemble`, "assemble the team", "convene the council", "quick council").
3. Council Members table — six rows (Architect, Builder, Guardian, Security, Advocate, Analyst) with `Subagent Type` column referencing the existing agent names. Complexity-Watchdog note and Research-Expectation note both retained verbatim from current SKILL.md lines 21–23.
4. Council-sizing instruction (replaces tier selection):
    - **Default sizing for `quick` / `/fbk-qcouncil`:** "When the trigger is `quick` or `/fbk-qcouncil`, default to a 3-agent council of Architect + Builder + Guardian unless task content explicitly requires a different domain. If the task names security/auth/credentials, substitute Security for one of the defaults (typically Guardian). If the task names users/UX/accessibility, substitute Advocate. If the task names performance/metrics/observability, substitute Analyst. Quick councils default to skipping the Phase 1 alignment round; run Phase 1 alignment only if agents explicitly request it during discussion."
    - **Default sizing for `/fbk-council` (no `quick`):** "Size the council for the current task. Select members from the table whose domain is relevant. Smaller councils for focused single-component decisions; larger councils for cross-cutting changes that touch security, user experience, or measurement."
    - **Common to both triggers:** "If a new dimension emerges during discussion that requires a member you did not initially select, spawn that member as an additional teammate."
5. Compaction recovery dispatch — one-line instruction: "Before initializing a new session, run `python3 \"$HOME\"/.claude/fbk-scripts/fbk.py session-state recovery-check`. If `recovering` is `true` in the JSON output, read `assets/fbk-docs/fbk-council/compaction-recovery.md` and resume from the returned `current_phase`."
5a. Per-phase checkpoint trigger (always-relevant; not gated by recovery) — one-line instruction: "After EACH phase completes, write checkpoint state via `python3 \"$HOME\"/.claude/fbk-scripts/fbk.py session-state checkpoint <phase-name> --session-id \"$SESSION_ID\" --completed <comma-list> --summary <str> --decisions <comma-list>`. This populates the state file that `recovery-check` reads on subsequent resume." Inline in SKILL because the WRITE side of recovery applies on every session — only the READ side (recovery-check return + leaf load) is conditional.
6. Phase 0: Task Intake — session initialization commands (register, log init), abort check, Multi-Iteration Awareness reference (see Ralph dispatch below).
7. Phase 1: Internal Alignment — full prompt template, research guidance table, constraints. Phase 1 fires on every council session as a checkpoint; what runs *within* it differs by trigger: `/fbk-council` quick councils (per §4.2 item 4) skip the alignment round by default but still run the agent-by-agent initial assessment in parallel; full-mode `/fbk-council` runs the alignment round. The orchestrator can flex either direction per task — a quick council that surfaces cross-cutting concerns during initial assessments may run alignment; a full council on a narrow task may compress it.
8. Phase 2: User Clarification — full inline content at parity with other phases:
    - Trigger condition: only fires if Phase 1 produced user-required clarifications.
    - Present only the filtered questions that survived internal alignment.
    - Group questions by theme rather than by agent (reduces redundancy when multiple agents converged on similar questions).
    - Wait for user responses before proceeding to Phase 3.
    - If Phase 1 resolved all questions internally, skip directly to Phase 3.
9. Phase 3: Independent Discussion — full prompt template, round-management rules.
10. Phase 4: Final Questions — full prompt template.
11. Phase 5: Consensus Output — the required output schema (unchanged).
12. Phase 5.5: Self-Evaluation — orchestrator reflection, logging command, visibility rules, output schema. Mandatory every session. Inline.
13. Immutable Core (security boundary) — kept inline since this is a load-bearing security invariant that must always be visible to the orchestrator.
14. Consensus-failure dispatch — one-line instruction: "When Round 1 of Phase 3 ends without consensus, read `assets/fbk-docs/fbk-council/consensus-failure.md` and apply the decision protocol for the task type; if the decision protocol surfaces an unresolved conflict between agents, apply the resolution-by-conflict-type rules in the same leaf."
16. Ralph dispatch — instruction: "When invoked inside a Ralph loop, read `assets/fbk-docs/fbk-council/ralph-integration.md` and follow its checkpointing and exit-marker protocol. Detection: state file `~/.claude/council-logs/council-state.json` exists AND its `status` field equals `CONTINUE` AND `iteration` < `max_iterations`, OR explicit invocation via `/ralph-loop`. A stale state file with `status: COUNCIL_COMPLETE` or with `iteration` >= `max_iterations` does NOT activate Ralph mode — those are leftover artifacts from prior completed sessions and the orchestrator should clean them via `session-state cleanup` before proceeding with a normal `/fbk-council` session." Plus a one-sentence decision pointer to keep the always-relevant guidance at the trunk: "Use Ralph mode for multi-phase implementation, complex refactoring requiring deliberation at decision points, or exploratory work where scope may evolve across iterations. Avoid for quick one-off questions, time-sensitive work, or tasks with unclear success criteria."
17. Logging-flag handling and default commands — `--no-log` flag is parsed from the invocation argument string at the start of Phase 0; when present, all `session-logger` invocations are suppressed (but `session-manager register` / `unregister` still run, since they track session lifetime independently of logging). When `--no-log` is absent, the four default logging commands fire on every session: `session-logger init`, `session-logger phase-start`, `session-logger phase-end`, `session-logger finalize`. Both `session-manager register` (Phase 0) and `unregister` (Phase 5 cleanup) are inline since they bracket every session.

    **Tier argument value.** The `session-manager register` and `session-logger init --tier` calls require a `<tier>` argument that the prior tier prescription supplied as `quick` or `full`. Post-refactor, the orchestrator passes the literal string `full` for both, regardless of council size. Rationale: `full` is the existing default at `session_logger.py:124`; preserving it keeps log analytics consistent across the refactor boundary (existing analytics queries that group by tier continue to work); and the tier field is now a vestigial schema requirement, not an operational signal — the actual council composition is captured by per-agent contribution logging. No CLI signature change required.

    **Logging transparency note.** The SKILL must state inline that session logging is automatic by default, that logs are written under `~/.claude/council-logs/`, and that `--no-log` suppresses the four default logging commands. One sentence; preserves user agency over a feature that records their session.
18. *(Removed — observability.md was deleted per DECISION-D in spec review. Non-default logging commands are documented in `python3 "$HOME"/.claude/fbk-scripts/fbk.py session-logger --help` and in the hook implementations under `assets/fbk-scripts/`. The orchestrator does not invoke them during a live session — they are operational tooling for scripts and hooks. Future hookification, when authored, will move even more logging out of orchestrator-invoked context; see parent spec's Future work section.)*
19. Facilitator instructions (the surviving orchestrator persona — expanded from initial 5 to 9 to retain operationally load-bearing items from current SKILL.md `Execution Guidelines`):
    - "Do not contribute technical opinions. Facilitate. Manage the process; do not become a seventh voice."
    - "Name specific agents when attributing views. Do not synthesize anonymously."
    - "Surface minority views prominently in the Dissenting Views section. Dissent is signal, not noise."
    - "Default to one discussion round. Extend to two only when critical dissent remains unresolved after Round 1. Empirical research (ACL 2025) shows additional rounds decrease decision quality."
    - "Maintain a running transcript visible to each agent across phases."
    - "Phase Sequence (mandatory): Phase 0 → Phase 1 → Phase 2 (if needed) → Phase 3 → Phase 4 (if new questions) → Phase 5 → Phase 5.5 → Session State Footer. Phase 5.5 self-evaluation is mandatory after Phase 5 output and before the Session State Footer; never skip it."
    - "Parallel Invocation: when invoking multiple agents in the same phase, use a SINGLE message with multiple Task tool calls to maximize parallelism. Sequential spawns waste latency."
    - "Per-phase checkpoint: after each phase completes, invoke the checkpoint trigger (§4.2 item 5a). Compaction can occur between phases; the state file is the only mechanism that survives it."
    - "Time management: if discussion goes in circles, move to the next phase. Don't let phases drag."
20. Example invocation (preserved).

### 4.3 Leaf contents (conditionally loaded)

Each leaf is loaded only when its condition fires. Each leaf contains content that does not need to be evaluated unless the condition holds. All leaves live under `assets/fbk-docs/fbk-council/`.

**`consensus-failure.md`** — Loaded when Round 1 of Phase 3 ends without consensus. Single leaf containing both the decision protocol (always applied first) and the conflict resolution rules (applied if the decision protocol surfaces unresolved conflict). Single SKILL dispatch (§4.2 item 14); no leaf-to-leaf chaining; no ambiguity about where the second-stage routing fires.

Contents (combined from current SKILL.md `Decision Protocol` lines 500–554 and `Conflict Resolution` lines 558–613):

*Decision protocol section:*
- Task classification (Reasoning vs Knowledge)
- Weighted voting protocol (vote weights by domain relevance, tally rules, tie-breaker)
- Evidence-Based Consensus protocol (research, citation, convergence, conflict noting)
- Decision documentation schema (the markdown block to add to Phase 5 output)

*Conflict resolution section (applied when the decision protocol surfaces unresolved conflict):*
- Resolution by conflict type (Technical Disagreement, Security vs Usability, Quality vs Speed, Feature Scope) with tie-breaking authority rules
- Deadlock protocol (orchestrator summary, escalation to user, user-decision documentation)
- Conflict documentation schema (the Dissenting Views markdown block)

**`compaction-recovery.md`** — Loaded only when `recovery-check` returns `recovering: true`.

Contents migrated from current SKILL.md `Compaction Resilience` section (lines 420–497), READ side only:
- Recovery protocol steps (adopt returned `session_id`, skip `completed_phases`, seed agent context with `transcript_summary` and `key_decisions`, resume from `current_phase`)
- Recovery acknowledgment phrase ("Resumed from checkpoint after context compaction")
- State Persistence JSON schema for `~/.claude/council-logs/council-state.json` — included here for recovery-time reference; the WRITE side that produces this schema lives inline in SKILL §4.2 item 5a.
- Session Cleanup commands (`session-manager unregister`, `session-state cleanup`) for COUNCIL_COMPLETE outcome

**Note on the WRITE/READ split:** The per-phase `session-state checkpoint` invocation that POPULATES the state file is always-relevant during a live session and lives inline in SKILL §4.2 item 5a — not in this leaf. This leaf contains only the READ side (recovery protocol after compaction). Without this split, the checkpoint instruction would load only after a compaction it depends on, breaking the cycle.

**Note on Session State Footer placement (resolved post-implementation per F-02):** The Session State Footer markdown templates (CONTINUE and COUNCIL_COMPLETE variants) live inline in SKILL.md (after Phase 5.5 / Immutable Core), NOT in this leaf. Earlier drafts placed templates here, but facilitator instruction 6 mandates the footer on every session — including non-recovering sessions that never load this leaf. Templates moved to SKILL during code-review remediation; AC-01 expanded to enumerate the Session State Footer section as required SKILL inline content.

**`ralph-integration.md`** — Loaded only when invoked inside a Ralph loop.

Contents migrated from current SKILL.md `Ralph Wiggum Integration` section (lines 771–947):
- "What is Ralph Wiggum" overview and council-plus-Ralph diagram
- Basic and phased invocation examples
- Guardrails table (max iterations, escape hatch, state checkpointing, stuck detection)
- Escape hatches (`council-abort`, `council-pause`, `/cancel-ralph`)
- State file format JSON schema (the multi-iteration variant with `completed_phases` array, `iteration` counter, `max_iterations`)
- Best practices and "When to use Ralph + Council" guidance
- Monitoring commands (`session-state show`, log directory listing, `jq`-piped status query)

*(`observability.md` was proposed in earlier drafts of this spec but deleted per DECISION-D. Non-default logging commands (`contribution`, `tool-use`, `outcome`, `show`, `permission-request`) are not invoked by the orchestrator during a live session — they are operational tooling for scripts and hooks. Documenting them as orchestrator-loadable context violates the "every leaf earns its load" principle, and these commands are also strong candidates for future hookification (see parent spec's Future work). The four default logging commands remain inline in SKILL §4.2 item 17.)*

### 4.4 Migration mapping

| Current SKILL.md lines | Section | Destination |
|---|---|---|
| 1–9 | Frontmatter, header | SKILL (unchanged) |
| 11–24 | Council Members table + Complexity Watchdogs note + Research-Expectation note | SKILL (unchanged) |
| 26–59 | Council Tiers, Quick/Full descriptions, Tier Selection Heuristics | REPLACED with §4.2 item 4 (sizing instruction); §3.1 documents the acknowledged behavioral change |
| 60–108 | Phase 0 (Compaction Check, Session Init, Multi-Iteration Awareness, Escape Hatch, intake prompt) | SKILL (Compaction Check becomes one-line dispatch §4.2 item 5; per-phase checkpoint write-side becomes §4.2 item 5a; rest stays inline as §4.2 item 6; Multi-Iteration Awareness folded into Ralph dispatch §4.2 item 16) |
| 110–208 | Phase 1 (Internal Alignment, Research, prompt template) + Phase 2 (User Clarification, lines 155–164) | SKILL inline (§4.2 item 7 for Phase 1; §4.2 item 8 for Phase 2 facilitation rules) |
| 210–263 | Phase 3 (Independent Discussion, prompt template, round management) | SKILL inline (§4.2 item 9) |
| 264–291 | Phase 4 (Final Questions) — note pre-existing label defect: lines 273–291 carry header "Prompt template for Phase 3" but appear under Phase 4 heading; this is corrected in the rewrite to "Prompt template for Phase 4" | SKILL inline (§4.2 item 10) |
| 294–339 | Phase 5 (Consensus Output schema) | SKILL inline (§4.2 item 11) |
| 341–402 | Phase 5.5 (Self-Evaluation) | SKILL inline (§4.2 item 12) |
| 404–419 | Immutable Core | SKILL inline (§4.2 item 13) |
| 420–497 | Compaction Resilience | SPLIT: WRITE side (`session-state checkpoint` invocation pattern) inline in SKILL §4.2 item 5a; READ side (recovery protocol, recovery acknowledgment, state schema reference, cleanup) to `compaction-recovery.md` |
| 500–554 | Decision Protocol | `consensus-failure.md` (decision-protocol section) |
| 558–613 | Conflict Resolution | `consensus-failure.md` (conflict-resolution section, same leaf) |
| 617–660 | Orchestrator + Execution Guidelines | REDUCED to 9 facilitator instructions (§4.2 item 19) — preserves Phase Sequence ordering, Phase 5.5 mandatory guard, Parallel Invocation, per-phase checkpoint trigger, and time management. The remaining "you facilitate, you don't participate" descriptive prose dissolves under Necessity Test as duplicating the surviving instructions. |
| 664–751 | Observability | SPLIT: 4 default logging commands + tier-argument value + transparency note inline in SKILL §4.2 item 17; non-default commands NOT migrated to a leaf (per DECISION-D, they are operational tooling for scripts/hooks, not orchestrator-loadable context). Reference for non-default commands: `fbk.py session-logger --help`. |
| 753–769 | Trigger Phrases, Example Invocation | SKILL (unchanged location and content) |
| 771–947 | Ralph Wiggum Integration | `ralph-integration.md`, plus a one-sentence "When to use Ralph" decision pointer inline in SKILL §4.2 item 16 (so the always-relevant decision aid is reachable before the leaf loads) |
| All inter-section dividers (`---`), blank-line separators, and umbrella headers (e.g., "## Discussion Phases" at line 60) | (separators) | Regenerated as needed in the rewritten SKILL; no requirement to preserve specific divider locations. |

### 4.5 Module touch policy

- [ ] `assets/skills/fbk-council/SKILL.md` — **refactor-then-extend**: substantial body rewrite. Trigger phrases, members table, phases, immutable core preserved verbatim where possible; tier selection content rewritten as the sizing instruction; condition-block content extracted to leaves; orchestrator persona reduced.
- [ ] `assets/fbk-docs/fbk-council/consensus-failure.md` — **new file** (no existing module to extend). Merges the decision protocol and conflict resolution sections into one leaf — they fire in sequence in the same code path; merging eliminates the dispatch-chain ambiguity of two separate leaves.
- [ ] `assets/fbk-docs/fbk-council/compaction-recovery.md` — **new file**.
- [ ] `assets/fbk-docs/fbk-council/ralph-integration.md` — **new file**.
- [ ] `assets/agents/fbk-council-architect.md` — **leave alone**.
- [ ] `assets/agents/fbk-council-builder.md` — **leave alone**.
- [ ] `assets/agents/fbk-council-guardian.md` — **leave alone**.
- [ ] `assets/agents/fbk-council-security.md` — **leave alone**.
- [ ] `assets/agents/fbk-council-advocate.md` — **leave alone**.
- [ ] `assets/agents/fbk-council-analyst.md` — **leave alone**.
- [ ] `assets/fbk-scripts/fbk/council/session_state.py` — **leave alone** (interface preserved; not modified).
- [ ] `assets/fbk-scripts/fbk/council/session_logger.py` — **leave alone**.
- [ ] `assets/fbk-scripts/fbk/council/session_manager.py` — **leave alone**.
- [ ] `assets/fbk-scripts/fbk/council/ralph.py` — **leave alone**.
- [ ] `tests/sdl-workflow/test-council-skill-references.sh` — **delete**, but first migrate its still-valuable assertions into the new `test-council-skill-structure.sh` (see §5.1) or `test-no-old-path-patterns.sh`: (1) SKILL contains a `session-manager` dispatcher reference, (2) SKILL contains a `session-logger` dispatcher reference, (3) no `~/.claude/skills/fbk-council/session-` substrings remain, (4) no `~/.claude/skills/fbk-council/ralph-` substrings remain. Assertions (1) and (2) belong in the new structure test (verify defaults stay inline). Assertions (3) and (4) belong in `test-no-old-path-patterns.sh`. Only after these migrate is the original deleted.
- [ ] `tests/sdl-workflow/test-council-skill-structure.sh` — **new file** (see §5.1). Structural smoke test for the rewritten SKILL.
- [ ] `tests/sdl-workflow/test-old-locations-empty.sh` — **extend**: keep the existing SKILL.md existence check and the "no `.py` files under `assets/skills/fbk-council/`" check; add assertions that `assets/fbk-docs/fbk-council/` exists and contains the three new leaf files.
- [ ] `tests/sdl-workflow/test-no-old-path-patterns.sh` — **extend**: add the three new leaf paths to its `files=()` array so the old-path detector covers them; absorb assertions (3) and (4) from the deleted `test-council-skill-references.sh`.
- [ ] `tests/sdl-workflow/test-council-agent-personas.sh` — **leave alone** (council member personas are not touched).
- [ ] `tests/sdl-workflow/test-review-integration.sh` — **leave alone**, but note dependency: Test 6 of this file (`grep -qi 'council' "$SKILL_FILE"` against `fbk-spec-review/SKILL.md`) and Test 8 validate the AC-12 guarantee that fbk-spec-review preserves its council invocation. Trigger name `/fbk-council` is preserved by this refactor; this test must continue to pass without modification. Listed here so the implementer is alerted to verify it still passes post-refactor.

### 4.6 Integration seams

- [ ] **SKILL → leaves**: routing references use `read assets/fbk-docs/fbk-council/<leaf>.md` form. Both source-tree (`assets/...`) and install-tree (`~/.claude/...`) path conventions must resolve. Verified by the link-resolution detector from the future `asset-graph-detectors` spec when it lands; until then, verified by `test-council-skill-structure.sh` (see §5.1) which asserts each dispatch reference points to an existing leaf file.
- [ ] **SKILL → council member agents**: spawn references unchanged. The orchestrator spawns members via the Task tool with `subagent_type` matching the agent's `name` frontmatter (`fbk-council-architect`, `fbk-council-builder`, etc.).
- [ ] **SKILL → `fbk.py session-state` subcommands**: `recovery-check`, `checkpoint`, `cleanup`, `show`, `check-abort` invocations preserved verbatim. Recovery dispatch reads JSON field `recovering` (boolean) and `current_phase` (string) from `recovery-check` output.
- [ ] **SKILL → `fbk.py session-logger` subcommands**: `init`, `phase-start`, `phase-end`, `finalize` invocations preserved verbatim and inline. The `contribution`, `tool-use`, `outcome`, `show`, `permission-request` subcommands are referenced from `observability.md` with identical invocation syntax.
- [ ] **SKILL → `fbk.py session-manager` subcommands**: `register` and `unregister` invocations preserved verbatim and inline.
- [ ] **SKILL → `~/.claude/council-logs/council-state.json`**: state file path and JSON schema preserved verbatim. Compaction-recovery and Ralph integration leaves both reference this file with the same schema documented in the current SKILL.md.
- [ ] **Downstream caller `/fbk-spec-review` → `/fbk-council`**: trigger name preserved. `assets/skills/fbk-spec-review/SKILL.md:35` continues to work without modification.
- [ ] **Cross-doc reference `assets/fbk-docs/fbk-sdl-workflow/review-perspectives.md:54` → `/fbk-council`**: trigger name preserved. No update required.
- [ ] **Trigger phrases**: every existing trigger string (`/fbk-council`, `/fbk-council quick`, `/fbk-qcouncil`, `/fbk-council --no-log`, `/fbk-council quick --no-log`, `/fbk-assemble`, "assemble the team", "convene the council", "quick council") matches the rewritten SKILL.
- [ ] **Ralph monitoring commands**: the `ralph-integration.md` leaf inherits the current SKILL's monitoring-command set (`session-state show`, log directory listing, `jq`-piped status query). No `ralph.py` CLI invocations are introduced on the skill side; `ralph.py` remains an external user-facing control surface unchanged by this refactor.

### 4.7 Runtime value precision

Limited to values the SKILL rewrite authors fresh (where a typo would break dispatch). Implementation details owned by the Python helpers (session ID format, CLI signatures) are documented in script docstrings, not here.

- Trigger phrases are listed verbatim in §4.6 and the SKILL's Trigger Phrases section; matching is exact-string against user input.
- Recovery dispatch reads JSON output of `python3 "$HOME"/.claude/fbk-scripts/fbk.py session-state recovery-check`, parses field `recovering` (boolean), and conditionally branches.
- Ralph dispatch reads `~/.claude/council-logs/council-state.json` and inspects fields `status` (string; `CONTINUE` activates Ralph mode), `iteration` (integer), and `max_iterations` (integer).
- State file path: `~/.claude/council-logs/council-state.json` (literal, expanded at runtime).
- Conditional leaf paths: `assets/fbk-docs/fbk-council/consensus-failure.md`, `assets/fbk-docs/fbk-council/compaction-recovery.md`, `assets/fbk-docs/fbk-council/ralph-integration.md`.
- Subagent type strings (for Task tool spawn): `fbk-council-architect`, `fbk-council-builder`, `fbk-council-guardian`, `fbk-council-security`, `fbk-council-advocate`, `fbk-council-analyst`.
- Tier argument value passed to `session-manager register` and `session-logger init --tier`: literal string `full` (rationale in §4.2 item 17).
- Ralph status markers: literal HTML comments `<!-- COUNCIL_STATUS: CONTINUE -->` and `<!-- COUNCIL_STATUS: COUNCIL_COMPLETE -->`.
- `--no-log` flag literal: matched as exact string in invocation argument parsing.

## Testing strategy

Refactor verification relies on a new structural smoke test plus extensions to existing tests. The future `asset-graph-detectors` spec will deliver general orphan + link-resolution detectors that further validate the asset tree, but this spec does not depend on them — it is independently verifiable.

### 5.1 New tests needed

**Integration test: `tests/sdl-workflow/test-council-skill-structure.sh`** — Structural smoke test for the entire refactor (rewritten SKILL, leaves, modified existing tests, downstream caller integrity, CHANGELOG, README). TAP-format shell test, auto-discovered by the existing CI glob (`for test in tests/sdl-workflow/test-*.sh`). Covers AC-01 (static content presence), AC-02 (negative — banned headers absent), AC-03 + AC-13 (sizing instruction phrases), AC-04 (consensus-failure.md content), AC-06 (compaction-recovery.md content), AC-07 (ralph-integration.md content), AC-09 (reachability via dispatch references; leaves exist), AC-10 (modified-test extensions present, deleted test absent), AC-11 (trigger phrases verbatim), AC-12 (downstream callers preserved via grep on fbk-spec-review SKILL and review-perspectives.md), AC-14 (CHANGELOG and README post-refactor content).

Concrete assertions the test must perform (each assertion is one TAP line; failure names which sub-claim regressed):

1. `assets/skills/fbk-council/SKILL.md` exists and is non-empty.
2. SKILL frontmatter parses as YAML, contains `name: fbk-council`, and the description field contains the literal substrings `selected per task` and `architect, builder, guardian, security, advocate, analyst` (verifies the updated description per §4.2 item 1; AC-01 part (a)). The description does NOT contain the literal substring `team of 6` (negative assertion — verifies the literal "6" was removed).
3. SKILL's "Trigger Phrases" section contains each of the nine literal trigger strings: `/fbk-council`, `/fbk-council quick`, `/fbk-qcouncil`, `/fbk-council --no-log`, `/fbk-council quick --no-log`, `/fbk-assemble`, `assemble the team`, `convene the council`, `quick council` (one assertion per phrase).
4. SKILL contains the literal string `--no-log` in the logging-flag handling section (FIND-013 anti-typo guard).
5. SKILL contains the literal string `session-manager` (default-dispatcher reference; ported from the deleted `test-council-skill-references.sh` assertions 1–2).
6. SKILL contains the literal string `session-logger` (default-dispatcher reference; ported from the deleted test).
7. SKILL contains required section headers: `Council Members`, `Phase 5: Consensus Output`, `Phase 5.5`, `Immutable Core`, `Trigger Phrases` (one assertion per header).
8. SKILL does NOT contain the banned headers `Quick Council`, `Full Council`, `Tier Selection Heuristics`, `Auto-escalation` (one negative assertion per header; covers AC-02).
9. SKILL contains a dispatch reference to each of the three conditional leaf paths: `assets/fbk-docs/fbk-council/consensus-failure.md`, `…/compaction-recovery.md`, `…/ralph-integration.md` (one assertion per path; covers AC-09 reachability).
10. Each of the three leaf files exists at the expected path (covers AC-09 link resolution; one assertion per file).
11. `consensus-failure.md` contains the literal strings `Weighted Voting`, `Evidence-Based Consensus`, `Reasoning`, `Knowledge` (decision-protocol section), AND `Technical Disagreement`, `Security vs Usability`, `Quality vs Speed`, `Feature Scope`, `Deadlock` (conflict-resolution section). Covers AC-04 — one assertion per term.
12. *(merged into assertion 11)*
13. `compaction-recovery.md` contains the literal strings `Recovery Protocol`, `Session State Footer`, `COUNCIL_STATUS: CONTINUE`, `COUNCIL_STATUS: COUNCIL_COMPLETE` (covers AC-06; one assertion per term).
14. `ralph-integration.md` contains the literal strings `What is Ralph Wiggum`, `Guardrails`, `Escape Hatches`, `When to Use Ralph` (covers AC-07; one assertion per term).
15. *(removed — observability.md deleted per DECISION-D)*
16. SKILL contains the per-phase checkpoint trigger string `session-state checkpoint` (validates §4.2 item 5a inline, anti-regression for FIND-002).
17. SKILL contains the literal phrases that codify the AC-13 soft default: `Architect + Builder + Guardian`, `substitute Security`, `substitute Advocate`, `substitute Analyst`, `skipping the Phase 1 alignment round` (one assertion per phrase; covers AC-13).

Each assertion is a single grep / file-test — fast (sub-second), deterministic, no LLM invocation. Total: ~50 assertions across one shell file. The test is ~80 lines.

### 5.2 Existing tests impacted

Search for tests covering the files this spec touches:

- `tests/sdl-workflow/test-council-skill-references.sh` — covers `assets/skills/fbk-council/SKILL.md`. Asserts (1) SKILL contains a `session-manager` dispatcher reference, (2) SKILL contains a `session-logger` dispatcher reference, (3) no `~/.claude/skills/fbk-council/session-` substrings remain, (4) no `~/.claude/skills/fbk-council/ralph-` substrings remain. **Delete after migration.** Assertions (1)–(2) are migrated into `test-council-skill-structure.sh` items 5–6 (§5.1). Assertions (3)–(4) are migrated into `test-no-old-path-patterns.sh` (anti-regression guards). Only after these migrations are confirmed is the original deleted. Covers AC-10.
- `tests/sdl-workflow/test-old-locations-empty.sh` — covers `assets/skills/fbk-council/`. Asserts `SKILL.md` exists at the canonical path and no `.py` files appear under the skills subtree. **Extend.** Add assertions that `assets/fbk-docs/fbk-council/` directory exists with the three expected leaf files. The SKILL.md path check stays. Covers AC-10.
- `tests/sdl-workflow/test-no-old-path-patterns.sh` — covers a `files=()` array including `assets/skills/fbk-council/SKILL.md`. **Extend.** Add the three new leaf paths to the array so the old-path detector covers them; absorb assertions (3) and (4) from the deleted `test-council-skill-references.sh`. Covers AC-10.
- `tests/sdl-workflow/test-council-agent-personas.sh` — covers the six member agent files. **Leave alone.** Member agents are not touched.
- `tests/sdl-workflow/test-review-integration.sh` — Test 6 (`grep -qi 'council' "$SKILL_FILE"` against `fbk-spec-review/SKILL.md`) and Test 8 directly validate the AC-12 guarantee that `/fbk-spec-review` preserves its council invocation. **Leave alone.** Trigger name `/fbk-council` is preserved by this refactor; this test must continue to pass without modification post-refactor. Listed here so the implementer is alerted to verify it still passes. Covers AC-12.

No other test in `tests/` references council assets.

### 5.3 Test infrastructure changes

None new for this spec. The structural smoke test (`test-council-skill-structure.sh`) uses only `bash`, `grep`, `test`, and standard POSIX tools — no new dependencies. The `fbk asset-graph` Python helper from the future `asset-graph-detectors` spec, if and when it lands, will further validate the asset tree (multi-hop reachability, dual-path link resolution); until then, the structural smoke test is sufficient to verify this spec's acceptance criteria.

### 5.4 Mocking justifications

N/A. No mocks introduced.

### 5.5 User verification steps

- **UV-1**: Invoke `/fbk-council` in a fresh session with a substantive task (e.g., "review this architecture decision"). Observable outcome: orchestrator selects an appropriate-size council based on task content (members named in Phase 0 setup), runs Phase 1 internal alignment, produces Phase 5 consensus output in the existing schema, runs Phase 5.5 self-evaluation, emits the Session State Footer.
- **UV-2**: Invoke `/fbk-qcouncil` (or `/fbk-council quick`) with a typical focused technical task (e.g., "should we extract this function?"). Observable outcome: orchestrator selects exactly Architect + Builder + Guardian (the soft default), skips the Phase 1 alignment round, produces output.
- **UV-2b**: Invoke `/fbk-qcouncil` with a focused task that names a non-default domain (e.g., "is this auth flow safe?" or "will users find this onboarding clear?"). Observable outcome: orchestrator substitutes Security (or Advocate) for one of the defaults, still produces a 3-agent council, still skips Phase 1 alignment round. Verifies the soft-default override path in §4.2 item 4.
- **UV-3**: Pre-seed `~/.claude/council-logs/council-state.json` with a `recovering: true` state and a `current_phase: "Phase-3-Discussion"`. Invoke `/fbk-council`. Observable outcome: orchestrator runs `recovery-check`, reads `compaction-recovery.md`, announces "Resumed from checkpoint after context compaction", skips Phase 0/1/2, resumes at Phase 3.
- **UV-4**: Invoke `/fbk-council` from inside a Ralph loop (or simulate by setting up a council-state.json with `iteration: 1, max_iterations: 5, status: CONTINUE`). Observable outcome: orchestrator detects Ralph context, reads `ralph-integration.md`, produces output ending with `<!-- COUNCIL_STATUS: CONTINUE -->`, updates `council-state.json` with `iteration: 2`.
- **UV-4b**: Pre-seed `~/.claude/council-logs/council-state.json` with a stale completed-but-not-cleaned-up session (set `task` field, set `status: COUNCIL_COMPLETE`). Invoke `/fbk-council` fresh (without `/ralph-loop`). Observable outcome: orchestrator does NOT enter Ralph mode; runs a normal Phase 0 session; the stale state is cleaned via `session-state cleanup` before proceeding. Verifies the §4.2 item 16 trigger condition is robust to leftover state.
- **UV-5**: Run a council session designed to surface dissent (e.g., contradictory requirements). Observable outcome: end of Round 1 produces unresolved disagreement; orchestrator reads `consensus-failure.md`, applies weighted voting, documents the result in the Decision Protocol Used section of Phase 5 output. If the disagreement is irreducible (e.g., Architect vs Builder on approach), the orchestrator continues into the conflict-resolution section of the same leaf and documents the resolution per the appropriate rule.
- **UV-6**: Run `bash tests/sdl-workflow/test-council-skill-structure.sh`. Observable outcome: all assertions pass (TAP "ok" output for each of ~50 assertions); script exits 0.
- **UV-7**: Run `bash tests/sdl-workflow/test-old-locations-empty.sh` and `bash tests/sdl-workflow/test-no-old-path-patterns.sh`. Observable outcome: both scripts exit 0; output confirms `assets/fbk-docs/fbk-council/` directory exists with the three expected leaves and no old-path substrings appear in any council asset. Confirm `tests/sdl-workflow/test-council-skill-references.sh` is absent from the repository (deleted post-migration of its assertions).
- *(UV-8 removed — observability.md deleted per DECISION-D.)*

UV-1 covers AC-01 (behavioral), AC-03, AC-11 (live invocation), AC-12 (caller continues to work). UV-2 covers AC-03, AC-11, AC-13 (quick default behavior). UV-2b covers AC-13 (quick-default override path). UV-3 covers AC-06. UV-4 covers AC-07 (active Ralph). UV-4b covers AC-07 (negative case — no false trigger from stale state). UV-5 covers AC-04 (both decision-protocol and conflict-resolution sections in the merged leaf). UV-6 covers AC-01 (static content), AC-02 (banned headers absent), AC-04, AC-06, AC-07, AC-09, AC-10, AC-11, AC-12, AC-13, AC-14 (all structural assertions in the smoke test). UV-7 covers AC-10 (live execution of the modified existing tests). UV-1 also serves as the behavioral preservation smoke test required by the parent spec's cross-cutting concerns.

## Documentation impact

### 6.1 Project documents to update

- `CHANGELOG.md` — add a Changed entry under the next release: "Decomposed `/fbk-council` skill body. Extracted compaction recovery, decision protocol, conflict resolution, Ralph loop integration, and advanced observability commands to conditional leaves under `assets/fbk-docs/fbk-council/`. Replaced Quick/Full tier prescription with judgment-based council sizing."
- `README.md` — line 99 (in the slash-command table) currently reads `| `/fbk-council` | Assemble 6 agents (architect, builder, guardian, security, analyst, advocate) to discuss any problem |`. Replace with: `| `/fbk-council` | Assemble specialized agents (architect, builder, guardian, security, advocate, analyst) — selected per task — to discuss any problem |`. User-approved 2026-05-03. Drops literal "6 agents", preserves all agent names, mirrors the SKILL frontmatter description language.

### 6.2 New documentation to create

None. The three new leaf files are context assets, not user-facing documentation.

## Acceptance criteria

- **AC-01**: `assets/skills/fbk-council/SKILL.md` contains: (a) YAML frontmatter with `name: fbk-council` and the updated description per §4.2 item 1 (drops literal "6"; preserves all discovery keywords); (b) all trigger phrases enumerated in §4.6; (c) the council members table with all six rows including the Complexity Watchdogs note and Research-Expectation note; (d) Phases 0 through 5 with their full prompt templates including Phase 2 facilitation rules per §4.2 item 8; (e) Phase 5.5 self-evaluation with its output schema; (f) the Immutable Core section; (g) the nine facilitator instructions enumerated in §4.2 item 19; (h) the four default logging commands (`session-logger init`, `session-logger phase-start`, `session-logger phase-end`, `session-logger finalize`) plus `session-manager register` (Phase 0) AND `session-manager unregister` (Phase 5 cleanup, operational instruction not just reference example); (i) the `--no-log` flag-parsing instruction; (j) the per-phase checkpoint trigger per §4.2 item 5a; (k) dispatch one-liners routing to each of the three conditional leaves; (l) the Session State Footer section with CONTINUE and COUNCIL_COMPLETE markdown templates verbatim (placed after Phase 5.5 / Immutable Core, before Ralph Integration dispatch — added per F-02 resolution).
- **AC-02**: `assets/skills/fbk-council/SKILL.md` no longer contains the section headers "Quick Council", "Full Council", "Tier Selection Heuristics", or "Auto-escalation"; no longer contains prescriptive 3-agent or 6-agent counts as protocol invariants; no longer contains the Tier Selection Heuristics table.
- **AC-03**: `assets/skills/fbk-council/SKILL.md` contains a single sizing instruction (§4.2 item 4) directing the orchestrator to select members from the table by judgment, with criteria for smaller-vs-larger sizing and instruction to spawn additional members mid-discussion when new dimensions emerge.
- **AC-04**: `assets/fbk-docs/fbk-council/consensus-failure.md` exists. Its decision-protocol section contains the task-classification table (Reasoning vs Knowledge), the weighted voting protocol with vote weights and tie-breaker, the Evidence-Based Consensus protocol, and the decision documentation schema. Its conflict-resolution section contains the four resolution-by-conflict-type rules (Technical, Security-vs-Usability, Quality-vs-Speed, Feature Scope), the Deadlock Protocol steps, and the Conflict Documentation schema. Both sections live in the same file under a single dispatch from the SKILL.
- **AC-06**: `assets/fbk-docs/fbk-council/compaction-recovery.md` exists and contains the recovery protocol steps (4 steps per spec §4.3 — adopt session_id, skip completed_phases, seed agent context with transcript_summary/key_decisions, resume from current_phase), the recovery acknowledgment phrase, the State Persistence JSON schema, and the Session Cleanup commands. The Session State Footer markdown templates live inline in SKILL.md (per F-02 resolution), NOT in this leaf — the footer is mandated every session including non-recovering ones, so its templates belong at the topmost-where-always-relevant placement (the SKILL).
- **AC-07**: `assets/fbk-docs/fbk-council/ralph-integration.md` exists and contains the Ralph overview and diagram, the basic and phased invocation examples, the Guardrails table, the three Escape Hatches, the multi-iteration State File JSON schema, the Best Practices and "When to Use" guidance, and the monitoring command reference.
- **AC-09**: `tests/sdl-workflow/test-council-skill-structure.sh` exists, follows TAP format, contains the assertions enumerated in §5.1, and passes (exits 0; all "ok" lines) when run against the rewritten SKILL and the three leaf files. When the future `asset-graph-detectors` spec lands, its orphan and link-resolution detectors also report zero orphans and zero broken links against the council subtree — but their existence is not a precondition for AC-09.
- **AC-10**: `tests/sdl-workflow/test-council-skill-references.sh` is deleted from the repository AFTER its assertions (1) and (2) are migrated into `test-council-skill-structure.sh` and assertions (3) and (4) are migrated into `test-no-old-path-patterns.sh`; `tests/sdl-workflow/test-old-locations-empty.sh` and `tests/sdl-workflow/test-no-old-path-patterns.sh` are updated per §4.5 and both pass when run by the existing CI glob `for test in tests/sdl-workflow/test-*.sh`. `tests/sdl-workflow/test-review-integration.sh` continues to pass without modification.
- **AC-11**: Every existing trigger phrase enumerated in §4.6 (`/fbk-council`, `/fbk-council quick`, `/fbk-qcouncil`, `/fbk-council --no-log`, `/fbk-council quick --no-log`, `/fbk-assemble`, "assemble the team", "convene the council", "quick council") appears verbatim in the rewritten SKILL's "Trigger Phrases" section. Verifiable by grep: each literal string returns at least one match against `assets/skills/fbk-council/SKILL.md`. Live invocation behavior verified by UV-1 and UV-2.
- **AC-12**: `assets/skills/fbk-spec-review/SKILL.md` continues to invoke `/fbk-council` (verifiable by `grep -F '/fbk-council' assets/skills/fbk-spec-review/SKILL.md` returning at least one match); `assets/fbk-docs/fbk-sdl-workflow/review-perspectives.md` continues to reference `/fbk-council` (same verification); `tests/sdl-workflow/test-review-integration.sh` continues to pass post-refactor. Content-based, not line-based — line numbers may shift if surrounding files re-flow but the trigger reference remains.
- **AC-13**: The rewritten SKILL contains the literal text of the §4.2 item 4 sizing instruction, including: (a) explicit recognition of the `quick` and `/fbk-qcouncil` triggers as soft defaults to Architect + Builder + Guardian, (b) substitution rules for security/auth, users/UX, and performance/metrics task-content keywords, (c) Phase 1 alignment-round skip default for quick councils with override clause, (d) the spawn-additional-members instruction for emergent dimensions. Verifiable by grep against the SKILL for the literal phrases "Architect + Builder + Guardian", "substitute Security", "substitute Advocate", "substitute Analyst", and "skipping the Phase 1 alignment round".
- **AC-14**: (a) `CHANGELOG.md` contains a Changed entry under the active release describing the council decomposition (verifiable by `grep -F 'Decomposed' CHANGELOG.md` AND `grep -F '/fbk-council' CHANGELOG.md` — both return at least one match for the new entry). (b) `README.md` line referencing `/fbk-council` is updated to drop the literal "6 agents" phrasing while preserving all six agent names and the slash-command listing format (verifiable by `grep -F 'Assemble specialized agents' README.md` returns one match AND `grep -F 'Assemble 6 agents' README.md` returns zero matches). User-approved README wording: `| /fbk-council | Assemble specialized agents (architect, builder, guardian, security, advocate, analyst) — selected per task — to discuss any problem |`.

## Open questions

None outstanding. All scope decisions were resolved during authoring; see Decision 8 in the parent spec at `ai-docs/progressive-disclosure-refactor/progressive-disclosure-refactor-spec.md` and the migration mapping at §4.4 of this spec for the resolved direction.

## Dependencies

- **`asset-graph-detectors` future spec (soft dependency)** — provides the `fbk asset-graph` Python helper plus `tests/sdl-workflow/test-asset-graph-orphans.sh` and `tests/sdl-workflow/test-asset-graph-links.sh`. This council-decomposition spec does NOT block on the asset-graph-detectors spec — AC-09 is verified by the local structural smoke test (`test-council-skill-structure.sh`, §5.1). The general detectors, when authored, will subsume `test-council-skill-structure.sh` for cross-asset reachability checks; until then, the smoke test is independently sufficient.
- **Parent spec** — `ai-docs/progressive-disclosure-refactor/progressive-disclosure-refactor-spec.md`. Cross-cutting concerns (tree-shaped routing, asset-type taxonomy, behavioral preservation, documentation discipline, adaptive structural detectors), Decision 8 (council-decomposition direction).
- **Six council member agents** — `assets/agents/fbk-council-architect.md`, `assets/agents/fbk-council-builder.md`, `assets/agents/fbk-council-guardian.md`, `assets/agents/fbk-council-security.md`, `assets/agents/fbk-council-advocate.md`, `assets/agents/fbk-council-analyst.md`. Already exist; spawned by the orchestrator; no changes required.
- **Python session helpers** — `assets/fbk-scripts/fbk/council/session_state.py`, `session_logger.py`, `session_manager.py`, `ralph.py`. Command-line interfaces preserved; not modified.
- **`assets/fbk-docs/fbk-context-assets.md`** — defines progressive disclosure and Necessity Test principles applied throughout this refactor.
- **Downstream callers (must continue to function unchanged)**:
  - `assets/skills/fbk-spec-review/SKILL.md:35` — invokes `/fbk-council`.
  - `assets/fbk-docs/fbk-sdl-workflow/review-perspectives.md:54` — references `/fbk-council` skill.
- **CI** — existing workflow at `.github/workflows/ci.yml` auto-discovers tests under `tests/sdl-workflow/test-*.sh`. No CI changes required.
