---
id: task-07
type: implementation
wave: 2
covers: [AC-01, AC-02, AC-03, AC-09, AC-11, AC-12, AC-13]
files_to_modify:
  - assets/skills/fbk-council/SKILL.md
test_tasks: [task-01]
completion_gate: "task-01 passes end-to-end (all assertions ok), tests/sdl-workflow/test-review-integration.sh continues to pass, tests/sdl-workflow/test-council-agent-personas.sh continues to pass"
---

## 1. Objective

Rewrites `assets/skills/fbk-council/SKILL.md` from 947 lines down to ~300–400 lines, following the nineteen-item structural assembly defined in council-decomposition-spec §4.2. Replaces the prescriptive Quick/Full tier system with a single judgment-based council-sizing instruction; extracts conditionally-relevant content (compaction recovery READ side, decision protocol, conflict resolution, Ralph integration) to dispatch one-liners pointing at the three new conditional leaves; preserves all triggers, the members table, every phase, the Immutable Core, and reduces orchestrator-persona content to nine load-bearing facilitator instructions.

## 2. Context

The `/fbk-council` skill body conflates trigger phrases, members table, two prescriptive tier protocols, every facilitation phase, orchestrator persona, decision protocol, conflict resolution, compaction recovery, Ralph integration, immutable-core security boundary, and a full observability command reference. Every invocation loads the entire file; most invocations do not encounter compaction, are not in a Ralph loop, do not need the decision protocol or conflict resolution machinery, and do not need the advanced observability reference.

The decomposition extracts conditionally-relevant content to leaves and replaces the Quick/Full tier prescription with a single sizing instruction that lets the orchestrator size the council per task. The user-observable behavior is preserved with one acknowledged change: `/fbk-council quick` and `/fbk-qcouncil` carry a soft default to a 3-agent Architect+Builder+Guardian council with the Phase 1 alignment round skipped, with substitution rules when task content names a non-default domain (security/auth → substitute Security; users/UX → substitute Advocate; performance/metrics → substitute Analyst).

This is an **orchestrator file** rewrite (per `task-compilation.md` §"Orchestrator tasks"): it wires triggers, members, dispatch routing, phase sequencing, and the load-bearing security boundary. Per the task-compilation rule, this task is routed to Sonnet minimum and includes an explicit wiring checklist (section 9 below).

The full nineteen-item assembly order, content sources, and verbatim strings are specified in the spec at §4.2. **Read the spec section §4.2 in full before beginning** — the spec is the canonical source for what the rewritten SKILL must contain. The spec also gives line ranges in the current SKILL for each preserved-verbatim block (members table, phase prompts, Phase 5 schema, Phase 5.5, Immutable Core, trigger phrases, default logging commands).

The three conditional leaves dispatched from the rewritten SKILL are authored in parallel by task-04 (consensus-failure), task-05 (compaction-recovery), and task-06 (ralph-integration). The dispatch one-liners in the rewritten SKILL must point at the leaf paths exactly:
- `assets/fbk-docs/fbk-council/consensus-failure.md`
- `assets/fbk-docs/fbk-council/compaction-recovery.md`
- `assets/fbk-docs/fbk-council/ralph-integration.md`

### Verbatim strings the rewritten SKILL must contain

The following literal strings are quoted by the spec and must appear verbatim in the rewritten SKILL. The structural smoke test (task-01) asserts on most of these:

**Updated YAML description (item 1)** — replace the current description value with this exact string:

```
Assembles the development council — a team of specialized agents (selected per task from architect, builder, guardian, security, advocate, analyst) who discuss collaboratively, ask clarifying questions, and work toward consensus recommendations.
```

The updated description preserves all discovery keywords (architect, builder, guardian, security, advocate, analyst, council, consensus, collaboratively, clarifying, recommendations) and removes the literal substring `team of 6` that no longer accurately describes post-refactor behavior.

**Council-sizing instruction (item 4)** — three sub-items, each verbatim. Use bullet or paragraph form; the test asserts on substring presence not block structure:

- Default sizing for `quick` / `/fbk-qcouncil`: "When the trigger is `quick` or `/fbk-qcouncil`, default to a 3-agent council of Architect + Builder + Guardian unless task content explicitly requires a different domain. If the task names security/auth/credentials, substitute Security for one of the defaults (typically Guardian). If the task names users/UX/accessibility, substitute Advocate. If the task names performance/metrics/observability, substitute Analyst. Quick councils default to skipping the Phase 1 alignment round; run Phase 1 alignment only if agents explicitly request it during discussion."
- Default sizing for `/fbk-council`: "Size the council for the current task. Select members from the table whose domain is relevant. Smaller councils for focused single-component decisions; larger councils for cross-cutting changes that touch security, user experience, or measurement."
- Common to both triggers: "If a new dimension emerges during discussion that requires a member you did not initially select, spawn that member as an additional teammate."

**Compaction recovery dispatch (item 5)** — verbatim:

```
Before initializing a new session, run `python3 "$HOME"/.claude/fbk-scripts/fbk.py session-state recovery-check`. If `recovering` is `true` in the JSON output, read `assets/fbk-docs/fbk-council/compaction-recovery.md` and resume from the returned `current_phase`.
```

**Per-phase checkpoint trigger (item 5a)** — verbatim. Inline in SKILL because the WRITE side of recovery applies on every session; only the READ side (the recovery-check return + leaf load) is conditional:

```
After EACH phase completes, write checkpoint state via `python3 "$HOME"/.claude/fbk-scripts/fbk.py session-state checkpoint <phase-name> --session-id "$SESSION_ID" --completed <comma-list> --summary <str> --decisions <comma-list>`. This populates the state file that `recovery-check` reads on subsequent resume.
```

**Consensus-failure dispatch (item 14)** — verbatim:

```
When Round 1 of Phase 3 ends without consensus, read `assets/fbk-docs/fbk-council/consensus-failure.md` and apply the decision protocol for the task type; if the decision protocol surfaces an unresolved conflict between agents, apply the resolution-by-conflict-type rules in the same leaf.
```

**Ralph dispatch (item 16)** — verbatim, plus the one-sentence decision pointer:

```
When invoked inside a Ralph loop, read `assets/fbk-docs/fbk-council/ralph-integration.md` and follow its checkpointing and exit-marker protocol. Detection: state file `~/.claude/council-logs/council-state.json` exists AND its `status` field equals `CONTINUE` AND `iteration` < `max_iterations`, OR explicit invocation via `/ralph-loop`. A stale state file with `status: COUNCIL_COMPLETE` or with `iteration` >= `max_iterations` does NOT activate Ralph mode — those are leftover artifacts from prior completed sessions and the orchestrator should clean them via `session-state cleanup` before proceeding with a normal `/fbk-council` session.
```

Followed by the one-sentence decision pointer (verbatim):

```
Use Ralph mode for multi-phase implementation, complex refactoring requiring deliberation at decision points, or exploratory work where scope may evolve across iterations. Avoid for quick one-off questions, time-sensitive work, or tasks with unclear success criteria.
```

**Tier argument value (item 17)** — the orchestrator passes literal string `full` to the `--tier` argument of both `session-manager register` and `session-logger init` regardless of council size. Use the literal `full` in the inline command examples; do not use a placeholder like `[quick|full]`.

**Logging transparency note (item 17)** — one-sentence statement (paraphrased to fit context, but must include the substantive content): session logging is automatic by default, logs are written under `~/.claude/council-logs/`, and `--no-log` suppresses the four default logging commands (`session-logger init`, `session-logger phase-start`, `session-logger phase-end`, `session-logger finalize`).

**Facilitator instructions (item 19)** — exactly nine instructions, each verbatim:

1. "Do not contribute technical opinions. Facilitate. Manage the process; do not become a seventh voice."
2. "Name specific agents when attributing views. Do not synthesize anonymously."
3. "Surface minority views prominently in the Dissenting Views section. Dissent is signal, not noise."
4. "Default to one discussion round. Extend to two only when critical dissent remains unresolved after Round 1. Empirical research (ACL 2025) shows additional rounds decrease decision quality."
5. "Maintain a running transcript visible to each agent across phases."
6. "Phase Sequence (mandatory): Phase 0 → Phase 1 → Phase 2 (if needed) → Phase 3 → Phase 4 (if new questions) → Phase 5 → Phase 5.5 → Session State Footer. Phase 5.5 self-evaluation is mandatory after Phase 5 output and before the Session State Footer; never skip it."
7. "Parallel Invocation: when invoking multiple agents in the same phase, use a SINGLE message with multiple Task tool calls to maximize parallelism. Sequential spawns waste latency."
8. "Per-phase checkpoint: after each phase completes, invoke the checkpoint trigger (§4.2 item 5a). Compaction can occur between phases; the state file is the only mechanism that survives it."
9. "Time management: if discussion goes in circles, move to the next phase. Don't let phases drag."

### Content preserved verbatim from current SKILL

- **Council Members table** — current SKILL lines 11–24, including the Complexity Watchdogs note and the Research Expectation note. Copy verbatim.
- **Phase 0 (Task Intake)** content excluding the Compaction Recovery Check subsection (which is replaced by item 5 dispatch and item 5a checkpoint trigger) and excluding Multi-Iteration Awareness (which is folded into the Ralph dispatch at item 16). Keep: Session Initialization, Logging note, Escape Hatch Check, the substantial-task prompt. Source: current SKILL lines 60–108, selectively. **Modify the literal**: where the source uses `[quick|full]` placeholders in the `register` and `init` commands, replace with the literal string `full` (per the tier-argument-value rule above).
- **Phase 1 (Internal Alignment)** — full prompt template, research guidance table, constraints. Source: current SKILL lines 110–153. The Phase 1 prompt template at current lines 166–208 is also preserved (the source's Phase 2 section header at line 155 sits between Phase 1 instructions and the Phase 1 prompt template — re-order in the rewrite so the Phase 1 prompt template lives under the Phase 1 heading).
- **Phase 2 (User Clarification)** — facilitation rules per spec §4.2 item 8: trigger condition (only fires if Phase 1 produced clarifications); present only filtered questions; group by theme; wait for user response; skip to Phase 3 if Phase 1 resolved everything internally. Source: current SKILL lines 155–164.
- **Phase 3 (Independent Discussion)** — full prompt template and round-management rules. Source: current SKILL lines 210–262. Note the source's Phase 4 prompt-template label defect at line 273 (header reads "Prompt template for Phase 3" but appears under the Phase 4 heading at line 264) — correct to "Prompt template for Phase 4" in the rewrite.
- **Phase 4 (Final Questions)** — full prompt template (with corrected label per above). Source: current SKILL lines 264–291.
- **Phase 5 (Consensus Output)** — required output schema. Source: current SKILL lines 294–339.
- **Phase 5.5 (Self-Evaluation)** — orchestrator reflection instructions, logging command, visibility rules, self-evaluation output schema, constraints. Mandatory every session. Source: current SKILL lines 341–402.
- **Immutable Core** — security boundary section. Source: current SKILL lines 404–419. Copy verbatim — load-bearing security invariant.
- **Trigger Phrases** — the nine-item list. Source: current SKILL lines 753–769. **Update the parenthetical descriptions**: the current text says `Full council (6 agents)` and `Quick council (3 agents)`. The 6-agent claim is removed elsewhere in the rewrite; here, replace `(6 agents)` with a brief judgment-based description such as `(default trigger; orchestrator sizes the council per task)` and replace `(3 agents)` with `(soft default: Architect + Builder + Guardian, Phase 1 skipped — overridable per task)`. The literal trigger-phrase strings themselves (`/fbk-council`, `/fbk-council quick`, `/fbk-qcouncil`, `/fbk-council --no-log`, `/fbk-council quick --no-log`, `/fbk-assemble`, `assemble the team`, `convene the council`, `quick council`) must remain present and verbatim — task-01 asserts on each.
- **Default logging commands** — the four `session-logger` invocations (`init`, `phase-start`, `phase-end`, `finalize`) and the two `session-manager` invocations (`register`, `unregister`). Use the same modern invocation form (`python3 "$HOME"/.claude/fbk-scripts/fbk.py session-logger init "$SESSION_ID" --tier full --task "..."` etc.) already present in current SKILL Phase 0 and Compaction Resilience sections.
- **Example Invocation** — the brief block at current SKILL lines 765–769. Preserve.

### Content removed

- **Council Tiers** section (current lines 26–59) — Quick Council, Full Council, Tier Selection Heuristics, Auto-escalation. Replaced by the council-sizing instruction (item 4). The headers `Quick Council`, `Full Council`, `Tier Selection Heuristics`, `Auto-escalation` must NOT appear anywhere in the rewritten SKILL — task-01 asserts negatively on each.
- **Decision Protocol** section (current lines 500–554) — moved to `consensus-failure.md` (task-04). SKILL retains only the dispatch one-liner (item 14).
- **Conflict Resolution** section (current lines 558–613) — moved to `consensus-failure.md` (same leaf, same dispatch).
- **Compaction Resilience** section (current lines 420–497) — split. WRITE-side (per-phase `session-state checkpoint` invocation) stays inline as item 5a. READ-side (recovery protocol, acknowledgment phrase, footer templates, schema, cleanup) moves to `compaction-recovery.md` (task-05). SKILL retains only the recovery dispatch one-liner (item 5) and the per-phase checkpoint trigger (item 5a).
- **Most of Observability** section (current lines 664–751) — only the four default logging commands stay inline (item 17, plus the tier-argument value and transparency note). Non-default commands (`contribution`, `tool-use`, `outcome`, `show`, `permission-request`) are NOT migrated to a leaf per DECISION-D — they are operational tooling for scripts and hooks, not orchestrator-loadable context. Reference for operators: `fbk.py session-logger --help`.
- **Most of "The Orchestrator (You)" + "Execution Guidelines"** sections (current lines 617–660) — reduced to the nine facilitator instructions (item 19). The remaining "you facilitate, you don't participate" prose dissolves under the Necessity Test as duplicating the surviving instructions.
- **Ralph Wiggum Integration** section (current lines 771–947) — moved to `ralph-integration.md` (task-06). SKILL retains only the dispatch (item 16) plus the one-sentence "When to use Ralph" decision pointer.

## 3. Instructions

1. Read the current `assets/skills/fbk-council/SKILL.md` in full to capture the exact text of every preserved-verbatim block (line ranges noted in section 2 above). Read spec §4.2 in full to capture the verbatim strings the rewrite introduces. Read spec §4.4 (migration mapping) for the destination of every line range.

2. Rewrite the file in place by replacing its full contents with the new structure. The new file must contain, in this top-to-bottom order, exactly the nineteen items listed in spec §4.2 (with the addition of item 5a between items 5 and 6, and item 20 example invocation at the end). Do not reorder. Do not merge items. Do not add items not enumerated in the spec.

3. Each item maps to one of these three categories — apply the corresponding rule:
   - **Verbatim string from spec §4.2** (items 1, 4, 5, 5a, 14, 16, 17 tier-arg + transparency note, 19): copy the exact text from the spec section §4.2 (or from the verbatim block in section 2 above of this task).
   - **Preserved verbatim from current SKILL** (members table, Phase 1/3/4/5/5.5 prompt templates and content, Immutable Core, Trigger Phrases, Example Invocation, default logging commands): copy from the current SKILL line ranges noted in section 2.
   - **Light rewrite** (Phase 0 — strip the Compaction Recovery Check subsection and Multi-Iteration Awareness; replace `[quick|full]` placeholders with literal `full`; Phase 2 — distill the listed facilitation rules; Trigger Phrases — update the parenthetical descriptions): perform the specified transformation while preserving every literal substring the structural smoke test asserts on.

4. Author dispatch one-liners exactly as specified in section 2 — the literal leaf path strings `assets/fbk-docs/fbk-council/consensus-failure.md`, `assets/fbk-docs/fbk-council/compaction-recovery.md`, `assets/fbk-docs/fbk-council/ralph-integration.md` must each appear verbatim in the rewritten SKILL because task-01 (Tests 28–30) asserts on each path string.

5. Verify all banned headers are absent. After writing, grep the new file for `Quick Council`, `Full Council`, `Tier Selection Heuristics`, `Auto-escalation` — each must return zero matches. Also grep for `team of 6` — must return zero matches.

6. Verify all required headers and substrings are present by running `bash tests/sdl-workflow/test-council-skill-structure.sh`. After this task plus task-04, task-05, and task-06 complete, all assertions in task-01's structural smoke test must pass (exit code 0). If any assertion fails, fix the SKILL content rather than the test.

7. Verify caller compatibility:
   - Run `bash tests/sdl-workflow/test-review-integration.sh` — must exit 0. Tests 6 and 8 of this file validate that `assets/skills/fbk-spec-review/SKILL.md` continues to invoke `/fbk-council` (AC-12). The trigger name `/fbk-council` is preserved by this rewrite, so this test passes without modification.
   - Run `bash tests/sdl-workflow/test-council-agent-personas.sh` — must exit 0. The six member agent files are not touched; this test passes without modification.
   - Verify by `grep -F '/fbk-council' assets/skills/fbk-spec-review/SKILL.md` returns at least one match.
   - Verify by `grep -F '/fbk-council' assets/fbk-docs/fbk-sdl-workflow/review-perspectives.md` returns at least one match.

8. Verify no legacy path substrings appear in the rewritten SKILL: `grep -E '(hooks/fbk-sdl-workflow|scripts/fbk-pipeline|uv run|~/.claude/skills/fbk-council/)' assets/skills/fbk-council/SKILL.md` must return zero matches. The current SKILL already uses the modern invocation form, so this should hold automatically; verify after the rewrite to catch any reintroduction.

9. Review the README. Run `grep -in "council\|fbk-council\|6 agents\|3 agents" /home/rahvin/context-assets/README.md`. The current README at line 99 reads: `| `/fbk-council` | Assemble 6 agents (architect, builder, guardian, security, analyst, advocate) to discuss any problem |`. This still references "6 agents" while the rewritten SKILL drops that count. **Do not edit README in this task.** Per project CLAUDE.md ("After any `CHANGELOG.md` update, check the `README.md` for any required updates. Discuss proposed readme changes with the user.") and per the spec §6.1 ("Discuss any required edits with the user"), surface this as a finding in the task summary the agent reports back, naming the line and the proposed change ("Assemble specialized agents (architect, builder, guardian, security, analyst, advocate) — orchestrator sizes the council per task"). The user resolves the README change separately.

## 4. Files to create/modify

- **Modify**: `assets/skills/fbk-council/SKILL.md` (full body rewrite per spec §4.2)

## 5. Test requirements

This implementation task makes the following assertions from `task-01` (`tests/sdl-workflow/test-council-skill-structure.sh`) pass:

- Tests 1–5: SKILL existence, frontmatter, updated description (positive substrings + negative `team of 6`).
- Tests 6–14: nine trigger-phrase verbatim assertions.
- Tests 15–18: default-dispatcher references (`session-manager`, `session-logger`), `--no-log` literal, `session-state checkpoint` literal.
- Tests 19–23: required section headers (Council Members, Phase 5: Consensus Output, Phase 5.5, Immutable Core, Trigger Phrases).
- Tests 24–27: banned headers absent (Quick Council, Full Council, Tier Selection Heuristics, Auto-escalation).
- Tests 28–30: dispatch references to each of the three conditional leaf paths.
- Tests 51–55: AC-13 soft-default phrases (`Architect + Builder + Guardian`, `substitute Security`, `substitute Advocate`, `substitute Analyst`, `skipping the Phase 1 alignment round`).

This task does NOT author new tests. It also does NOT make leaf-content tests pass (those are owned by task-04, task-05, task-06).

Existing tests that must continue to pass without modification:

- `tests/sdl-workflow/test-review-integration.sh` (Tests 6 and 8 validate AC-12: `fbk-spec-review` continues to invoke `/fbk-council`).
- `tests/sdl-workflow/test-council-agent-personas.sh` (member agents are not touched).
- `tests/sdl-workflow/test-old-locations-empty.sh` (Test 5 verifies SKILL.md still exists at the canonical path).
- `tests/sdl-workflow/test-no-old-path-patterns.sh` (the rewritten SKILL must contain no legacy path substrings — `hooks/fbk-sdl-workflow`, `scripts/fbk-pipeline`, `uv run`, `~/.claude/skills/fbk-council/`).

## 6. Acceptance criteria

- **AC-01**: `assets/skills/fbk-council/SKILL.md` contains: (a) YAML frontmatter with `name: fbk-council` and the updated description (drops `team of 6`; preserves discovery keywords); (b) all nine trigger phrases enumerated in spec §4.6; (c) the council members table with all six rows including the Complexity Watchdogs note and Research-Expectation note; (d) Phases 0 through 5 with their full prompt templates including Phase 2 facilitation rules; (e) Phase 5.5 self-evaluation with its output schema; (f) the Immutable Core section; (g) the nine facilitator instructions; (h) the four default logging commands plus `session-manager register` and `session-manager unregister`; (i) the `--no-log` flag-parsing instruction; (j) the per-phase checkpoint trigger; (k) dispatch one-liners routing to each of the three conditional leaves.
- **AC-02**: `assets/skills/fbk-council/SKILL.md` no longer contains the section headers "Quick Council", "Full Council", "Tier Selection Heuristics", or "Auto-escalation"; no longer contains prescriptive 3-agent or 6-agent counts as protocol invariants; no longer contains the Tier Selection Heuristics table.
- **AC-03**: `assets/skills/fbk-council/SKILL.md` contains a single sizing instruction directing the orchestrator to select members from the table by judgment, with criteria for smaller-vs-larger sizing and instruction to spawn additional members mid-discussion when new dimensions emerge.
- **AC-09**: dispatch references to each of the three conditional leaf paths appear verbatim in the rewritten SKILL.
- **AC-11**: every existing trigger phrase enumerated in spec §4.6 appears verbatim in the rewritten SKILL's Trigger Phrases section.
- **AC-12**: `assets/skills/fbk-spec-review/SKILL.md` continues to invoke `/fbk-council` (verifiable by grep returning at least one match); `assets/fbk-docs/fbk-sdl-workflow/review-perspectives.md` continues to reference `/fbk-council`; `tests/sdl-workflow/test-review-integration.sh` continues to pass post-refactor.
- **AC-13**: the rewritten SKILL contains the literal phrases `Architect + Builder + Guardian`, `substitute Security`, `substitute Advocate`, `substitute Analyst`, and `skipping the Phase 1 alignment round`.
- task-01 passes end-to-end (all ~55 assertions return `ok`) once this task plus task-04, task-05, task-06 have all completed.

## 7. Model

Sonnet

## 8. Wave

Wave 2

## 9. Wiring Checklist

This task modifies the orchestrator file. Before declaring completion, verify each item:

- [ ] **Frontmatter**: `name: fbk-council` is unchanged. `description:` is replaced with the verbatim string from section 2 (item 1) of this task. The description does NOT contain the literal substring `team of 6`.
- [ ] **Nineteen-item structural assembly per spec §4.2** (with item 5a inserted between items 5 and 6, plus the example invocation at the end): every item appears exactly once, in the order specified.
- [ ] **All three dispatch references point at the exact leaf paths**:
  - `assets/fbk-docs/fbk-council/consensus-failure.md` (item 14)
  - `assets/fbk-docs/fbk-council/compaction-recovery.md` (item 5)
  - `assets/fbk-docs/fbk-council/ralph-integration.md` (item 16)
- [ ] **All nine trigger phrases are preserved verbatim**: `/fbk-council`, `/fbk-council quick`, `/fbk-qcouncil`, `/fbk-council --no-log`, `/fbk-council quick --no-log`, `/fbk-assemble`, `assemble the team`, `convene the council`, `quick council`. (Update the parenthetical descriptions next to `/fbk-council` and `/fbk-council quick` to remove the `(6 agents)` and `(3 agents)` claims; the literal trigger strings themselves are unchanged.)
- [ ] **Per-phase checkpoint write-side trigger (item 5a) is inline** — the literal string `session-state checkpoint` appears at least once in the SKILL body, not only inside a leaf.
- [ ] **`--no-log` parsing is inline (item 17)** — the literal string `--no-log` appears at least once.
- [ ] **Tier-argument value `full` is literally specified (item 17)** — the `register` and `init` commands use the literal `full`, not a `[quick|full]` placeholder.
- [ ] **Logging transparency note is inline (item 17)** — one sentence stating that logging is automatic by default, logs go under `~/.claude/council-logs/`, and `--no-log` suppresses the four default commands.
- [ ] **Immutable Core preserved verbatim (item 13)** — `## Immutable Core` (or equivalent header) section copied from current SKILL lines 404–419 without modification.
- [ ] **All nine facilitator instructions appear verbatim per item 19** — each of the nine bullets in section 2 of this task appears in the rewritten SKILL, in order, in a single section.
- [ ] **Phase 2 facilitation rules inline (item 8)** — the four bullets (trigger condition, present filtered questions, group by theme, wait/skip-to-Phase-3) appear inline as the Phase 2 section content.
- [ ] **AC-13 soft-default phrases verbatim (item 4)** — the literal phrases `Architect + Builder + Guardian`, `substitute Security`, `substitute Advocate`, `substitute Analyst`, and `skipping the Phase 1 alignment round` each appear at least once in the SKILL.
- [ ] **Banned headers absent**: `Quick Council`, `Full Council`, `Tier Selection Heuristics`, `Auto-escalation` each return zero `grep -F` matches.
- [ ] **No legacy path substrings**: `hooks/fbk-sdl-workflow`, `scripts/fbk-pipeline`, `uv run`, `~/.claude/skills/fbk-council/` each return zero matches.
- [ ] **Caller-compatibility tests pass**: `bash tests/sdl-workflow/test-review-integration.sh` exits 0; `bash tests/sdl-workflow/test-council-agent-personas.sh` exits 0.
- [ ] **Structural smoke test passes end-to-end** once paired with task-04, task-05, task-06: `bash tests/sdl-workflow/test-council-skill-structure.sh` exits 0 with all `ok` lines.
- [ ] **README finding surfaced (not edited)**: the work-summary message returned to the team lead names line 99 of `README.md` (`Assemble 6 agents …`) as needing user discussion, with a proposed replacement that drops the agent count.
