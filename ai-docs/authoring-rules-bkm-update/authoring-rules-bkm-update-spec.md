# Authoring Rules BKM Update — Spec

## Problem

The Firebreak context asset authoring rules at `assets/fbk-docs/fbk-context-assets.md` and its leaves under `assets/fbk-docs/fbk-context-assets/` predate a coherent body of prompting research synthesized into the llm-wiki in May 2026 (`strategic-under-specification`, `objective-driven-prompting`, `meta-prompting`, `over-prompting`, `anchoring-effect`, `specification-drift`, `semi-formal-reasoning`, `instruction-following-degradation`, and `anthropic-2026-prompting-best-practices`). The existing rules are well-aligned with foundational principles (Necessity Test, progressive disclosure, positive framing, single verifiable constraint, cap-at-5 examples) but lack three operational principles the new research establishes: that capable models do better with stated objectives + measurable acceptance criteria than with enumerated procedural steps; that example diversity is as load-bearing as example count (homogeneous clusters anchor the agent on specific instances rather than the broader pattern); and that "ignore the previous example" / "be objective" / "don't be influenced by X" instructions do not work because anchoring operates at shallow processing layers below instruction-following control. Additionally, the BKM update exposes an inherited misframe in `agents.md` `## Instruction Design` (lines 72–101) that treats agents as workflow-bearing task runners — contradicting the more recent `## Persona authoring` section in the same file, which correctly frames agents as personas that activate a higher-quality training distribution while workflow steps belong in the spawn prompt.

## Goals

- Add one new principle to `assets/fbk-docs/fbk-context-assets.md` ("Objectives over Procedural Steps") that consolidates objectives + measurable acceptance criteria + the output-structure-is-not-procedural-prescription distinction + the workflow-routing position (workflow lives in skills, docs, or spawn prompts — never in agent definition bodies) into one coherent section.
- Fix the Trigger Types table cell in `assets/fbk-docs/fbk-context-assets.md` `## Choose the Right Trigger and Content Strategy` that currently describes Agents as holding "Specialized personas or delegated workflows" — replace with persona-only framing aligned with the new principle and with the restructured `agents.md`.
- Add one instruction to the parent doc's `## Write for Agents, Not Humans` section covering the anti-bias-instruction rule (restructure to remove bias-sources rather than instructing the agent to ignore them).
- Restructure `assets/fbk-docs/fbk-context-assets/agents.md` `## Instruction Design` section (lines 72–101) into a tighter `## Description field` section that retains only what is genuinely not covered by `## Persona authoring` or by the existing body-content paragraph at lines 27–29. This removes a real internal contradiction and aligns the file with what agents are for: persona activation, not workflow execution.
- Extend the existing body-content paragraph at `agents.md` lines 27–29 with two additions: (a) the constraint-ordering instruction "Place critical constraints first" — preserved from deleted line 74, since `## Persona authoring` does not state this rule; (b) a one-line forward pointer to `## Persona authoring` and the Detector/Challenger canonical examples, so an author landing on the file sees the path to body-content structure without having to skim past three sections.
- Sharpen the cap-at-5 rule in `assets/fbk-docs/fbk-context-assets/referenced-docs.md` by splitting it into two single-constraint rules (cap + diversity), each with a one-clause generalization-aiding why.
- Add three verbatim research/vendor citations: one in the new parent-doc principle (`anthropic-2026-prompting-best-practices`, `cemri-2025-multi-agent-systems-fail`, `ugare-2026-agentic-code-reasoning`), one in the new "Write for Agents" instruction (`huang-2026-anchoring-effect-llm`), one on the cap-at-5 update (`tang-2025-few-shot-dilemma`, `huang-2026-anchoring-effect-llm`).
- Self-apply: every added or replacement instruction passes the Necessity Test, frames positively (or pairs prohibition with positive alternative), and states a single verifiable constraint. Each "why" included is one clause and load-bearing for generalization, not literary description.

### Non-goals

- Audit the existing corpus of context assets (agents, skills, rules, hooks, docs across `.claude/` and `assets/`) for compliance with the updated rules. Deferred to a follow-up spec — see "Decisions resolved during scoping" below.
- Rewrite or renumber the existing six principles in the parent doc. The new principle is added as a seventh; existing principles remain unchanged.
- Modify `assets/fbk-docs/fbk-context-assets/skills.md`, `claude-md.md`, `rules.md`, or `hooks.md`. None contains the same misframe as the agents.md `Instruction Design` section.
- Update SDL workflow documents, design guidelines, the wiki, or any context asset outside the three files in scope.
- Add citation footnotes to the existing six principles. Citations are scoped to the new content only.
- Refresh the Detector and Challenger reference implementations (`Persona authoring` already references them as canonical examples; they remain authoritative).

## User-facing behavior

The "users" of these rules are agents authoring context assets and human contributors reading or maintaining them. Behavior changes:

- An agent loaded with the parent doc and asked to author a new skill or doc-leaf produces objectives paired with measurable acceptance criteria, and uses procedural step lists only when step order matters for correctness (runbooks, deterministic verification sequences, audit trails).
- An agent asked to author or modify an agent definition (in `.claude/agents/`) reads the new principle and the corrected Trigger Types table; both establish that workflow content lives in skills, referenced docs, or the spawn prompt — not in the agent body. The agent declines to embed workflow steps in an agent definition body, and routes such content to a skill, a referenced doc, or guidance for the orchestrator's spawn prompt instead.
- An agent asked to add an "ignore the previous example" / "be objective" / "don't be influenced by X" instruction to a context asset declines and instead restructures the asset to remove the bias-source.
- An agent asked to author a new agent definition reads `agents.md` and finds: a frontmatter table, an extended body-content paragraph that names "place critical constraints first" and points forward to `## Persona authoring` (with Detector and Challenger as canonical examples), a tight `## Description field` section, capability scoping, and the persona authoring discipline — with no contradictory `Instruction Design` section telling the agent body to contain workflow steps. Agent bodies follow the role-activation + quality-bars + anti-defaults structure exclusively. Workflow steps go in the spawn prompt that invokes the agent.
- An agent asked to add examples to a doc considers diversity across the category (different points across the category boundary, not different surface details), not only count.
- An agent reading the cap-at-5 rule sees citations to `tang-2025-few-shot-dilemma` and `huang-2026-anchoring-effect-llm`. An agent reading the new principles sees citations to `anthropic-2026-prompting-best-practices`, `cemri-2025-multi-agent-systems-fail`, `ugare-2026-agentic-code-reasoning`, and `huang-2026-anchoring-effect-llm`.
- A human contributor reading the principles list sees the new principle in the same imperative voice and single-verifiable-constraint form as the existing six.

Edge case: an author writing a runbook, deterministic verification sequence, or audit trail can still produce a numbered step list — the new principle explicitly carves out the order-matters case.

## Technical approach

### Scope

Modify three files in `assets/fbk-docs/`. Plus update CHANGELOG.md.

### Module touch policy

- [ ] `assets/fbk-docs/fbk-context-assets.md`: extend (add one new principle section after `## Trust the Agent's Native Capabilities`; fix the Agents row of the Trigger Types table in `## Choose the Right Trigger and Content Strategy`; append one paragraph in `## Write for Agents, Not Humans`)
- [ ] `assets/fbk-docs/fbk-context-assets/agents.md`: refactor-then-extend (replace the entire `## Instruction Design` section at lines 72–101 with a tighter `## Description field` section; extend the body-content paragraph at lines 27–29 with the constraint-ordering instruction and a forward pointer to `## Persona authoring`)
- [ ] `assets/fbk-docs/fbk-context-assets/referenced-docs.md`: extend (split line 34 into two single-constraint rules with a citation footnote)
- [ ] `assets/fbk-docs/fbk-context-assets/claude-md.md`: leave alone
- [ ] `assets/fbk-docs/fbk-context-assets/rules.md`: leave alone
- [ ] `assets/fbk-docs/fbk-context-assets/skills.md`: leave alone
- [ ] `assets/fbk-docs/fbk-context-assets/hooks.md`: leave alone
- [ ] `CHANGELOG.md`: extend (one "Changed" entry under next unreleased version)

### Conventions in modified files

The implementer follows these conventions in the three modified files:

- **Heading level:** all top-level principles in `fbk-context-assets.md` use `##`; sub-points use `###`. New principle in Change 1a uses `##` and matches sibling principle headings.
- **Blank-line spacing:** one blank line between a section heading and its content; one blank line between paragraphs within a section.
- **Citation block placement:** end of section, after the last content paragraph, separated by a blank line. Wrap the citation in italic parentheticals.
- **Voice:** imperative direct-address. Write "State the agent's objective..." not "Authors should state...".
- **Table column counts:** preserve the existing column counts of any table being edited (Trigger Types is 3 columns); new tables introduced by this spec follow their own internal logic (drift-prone vs. drift-resistant is 2 columns).

### Change 1a — New principle in `fbk-context-assets.md`

Insert a new `## Objectives over Procedural Steps` section between the existing `## Trust the Agent's Native Capabilities` section (ends at line 91) and `## Choose the Right Trigger and Content Strategy` section (starts at line 93). Final content:

```markdown
## Objectives over Procedural Steps

State the agent's objective and a measurable acceptance criterion. Enumerate procedural steps only when step order matters for correctness — runbooks, deterministic verification sequences, audit trails.

Pair every objective with a measurable acceptance criterion that operationalizes "what good looks like" in checkable terms. Without one, the agent fills the gap with a statistically likely completion, and the drift compounds across steps.

| Drift-prone | Drift-resistant |
|-------------|-----------------|
| "Be concise" | "Under 75 words; action and deadline only" |
| "Find issues" | "Find any bug that could cause incorrect behavior, a test failure, or a misleading result" |

Output-structure prescription is not procedural prescription. Constraining the deliverable shape (required sections, schema, output fields) is compatible with leaving the path to the agent's reasoning.

Workflow content — sequenced steps, deterministic protocols, runbooks — lives in skills, referenced docs, or the spawn prompt that invokes an agent. It does not live in an agent definition body. The orchestrator composes persona (from the agent definition) and workflow (from a skill, doc, or spawn prompt) at spawn time. Embedding workflow in an agent body pre-empts that composition and forces every invocation of that agent through the same workflow regardless of the orchestrator's intent. When the workflow is small and has one consumer, route it via the spawn prompt — `## Separation of Concerns` governs the inline-vs-extract decision for workflow content the same way it does for instruction content.

*Backed by `anthropic-2026-prompting-best-practices` — "Prefer general instructions over prescriptive steps." Failure-mode analysis: `cemri-2025-multi-agent-systems-fail`. Output-structure refinement: `ugare-2026-agentic-code-reasoning`.*
```

### Change 1b — Fix Trigger Types table cell in `fbk-context-assets.md`

In the `## Choose the Right Trigger and Content Strategy` section's Trigger Types table (line 103 in the current file), replace the Agents row's "Example" cell. The current cell describes Agents as holding "Specialized personas or delegated workflows" — the "delegated workflows" phrase is the same misframe being corrected in `agents.md`, and it directly contradicts the new principle in Change 1a.

Final content of the row:

```markdown
| **Agents** (.claude/agents/) | Spawned as a subagent | Specialized personas (workflow comes from skills, docs, or the spawn prompt at composition time) |
```

The other rows (CLAUDE.md, Rules, Skills, Hooks) are unchanged. The header row, the content-strategies table, and the key-considerations subsection below are all unchanged.

### Change 2 — New paragraph in `fbk-context-assets.md` `## Write for Agents`

Insert a new paragraph in the `## Write for Agents, Not Humans` section after the existing positive-framing instruction at line 139. Final content:

```markdown
Remove bias-sources by restructuring the asset rather than instructing the agent to disregard them. Anchoring operates at shallow processing layers below instruction-following control, so "ignore the previous example", "be objective", and "don't be influenced by X" do not work. Restructure instead: drop the offending example, balance with diverse alternatives, or reorder so the bias-source is not in a high-attention position.

*See `huang-2026-anchoring-effect-llm`.*
```

### Change 3 — Restructure `agents.md` `## Instruction Design` and extend the body-content paragraph

**Part A — Extend the body-content paragraph at lines 27–29.** Final content of the paragraph:

```markdown
The Markdown body below the frontmatter becomes the agent's system prompt.

Focus the body on what makes this agent different from the default: its role, constraints, and behavioral boundaries. Place critical constraints first. Avoid duplicating general project knowledge the agent can read from CLAUDE.md or discover from the codebase.

For body-content structure (role activation, quality bars, anti-defaults), see `## Persona authoring` below — the Detector and Challenger agents are canonical examples.
```

Two additions: the constraint-ordering instruction "Place critical constraints first" (preserved from deleted line 74, since `## Persona authoring` does not state this rule) and a forward pointer to `## Persona authoring` with the canonical-examples reference (so an author landing on `agents.md` does not need to skim past the frontmatter table, the When-to-Use guide, and Capability Scoping to find the body-content structure).

**Part B — Replace the `## Instruction Design` section (lines 72–101) with a tighter `## Description field` section.** Final content:

```markdown
## Description field

Write the `description` field using specific, matchable language that mirrors how users phrase relevant tasks.

Include "use proactively" in the description if the agent should be invoked automatically for relevant tasks.
```

Removed pieces and the rationale for each removal:

- Section heading `## Instruction Design`: replaced with `## Description field` to match the actual remaining content.
- Line 73 (`State the agent's role and scope in the first lines of the body. Place critical constraints before detailed instructions.`): the role-and-scope half duplicates `## Persona authoring`'s role-activation component; the place-critical-constraints-first half is preserved by Part A above.
- Line 76 (`Tell the agent what to do when invoked -- provide a clear workflow or checklist of steps.`): contradicts `## Persona authoring`'s explicit guidance that "task details, output format, and workflow steps belong in the spawn prompt."
- Line 82 (`Personas belong in the body; see ## Persona authoring for activation-focused structure.`): rendered redundant by Part A's forward pointer.
- Lines 84–101 (`### Example structure` test-runner block): contradicts `## Persona authoring`'s canonical examples. The Detector and Challenger references at line 127 of the Persona authoring section carry the example burden authoritatively (now reachable via Part A's forward pointer).

### Change 4 — Split cap-at-5 rule in `referenced-docs.md`

Replace line 34 of `referenced-docs.md`. Final content:

```markdown
Cap examples at 5 per document — additional examples degrade compliance rather than improve it.

Diversify examples across the category. Homogeneous clusters anchor the agent on those specific instances rather than the broader pattern.

*Backed by `tang-2025-few-shot-dilemma` (cap) and `huang-2026-anchoring-effect-llm` (diversity).*
```

### Change 5 — CHANGELOG.md update

Add one "Changed" entry under the next unreleased version. Final content (exact wording subject to reading the existing CHANGELOG format at implementation time):

```markdown
- Updated context asset authoring rules with prompting BKMs from May 2026 wiki research: added "Objectives over Procedural Steps" principle (with measurable acceptance criteria and output-structure distinction); added anti-bias-instruction guidance in "Write for Agents"; restructured `agents.md` `Instruction Design` section into a tighter `Description field` section, removing a contradiction with `Persona authoring`; sharpened the cap-at-5 example rule with diversity guidance. Added research/vendor citations.
```

### Integration seams

- [ ] `agents.md` `## Persona authoring` section survives the restructure with no incidental edits. The restructured `## Description field` section relies on `Persona authoring` being authoritative for body-content structure.
- [ ] `agents.md` body-content paragraph at lines 27–29 retains the existing two sentences and adds only the two specified additions (constraint-ordering instruction and forward pointer). All other sections of `agents.md` outside lines 27–29 and the deleted lines 72–101 are unchanged.

### Sequence

1. Modify `referenced-docs.md` (smallest change — split one rule into two with citation).
2. Modify `fbk-context-assets.md` parent: insert new `## Objectives over Procedural Steps` principle section (Change 1a), fix the Agents row of the Trigger Types table (Change 1b), append the new paragraph in `## Write for Agents, Not Humans` (Change 2).
3. Modify `agents.md`: restructure `## Instruction Design` → `## Description field`, then extend the body-content paragraph at lines 27–29 with the constraint-ordering instruction and the forward pointer to `## Persona authoring`.
4. Self-application audit: re-read all three modified files end-to-end and document the Necessity Test outcome for each added or replacement instruction. Confirm positive framing, single verifiable constraint, and load-bearing why-clauses.
5. Run deterministic integrity check on `agents.md`: `git diff` scoped to the preserved sections (`## When to Use an Agent vs. Alternatives`, `## Capability Scoping`, `## Persona authoring`, `## Scope`, `## Security`). Pass criterion: zero lines changed in those sections. Body-content paragraph at lines 27–29 shows only the two additions specified in Change 3 Part A.
6. Run `tests/sdl-workflow/test-agents-md-persona-guidance.sh` and `tests/sdl-workflow/test-reference-integrity.sh` pre-commit. Both must pass.
7. Update CHANGELOG.md.

## Testing strategy

This is a documentation change to context assets that govern agent behavior. There is no automated test suite for the rule files themselves. Verification combines manual review against the rules' own self-application criteria, integrity verification of unchanged sections, and a behavioral smoke check.

### New tests needed

- **Self-application audit** (manual, recorded in retrospective): For each added or replacement instruction across the three modified files, the implementer records one row in a `## Self-application audit` table in the implementation retrospective with the five columns specified in AC-08. Citation accuracy is verified in the same pass: each new wiki slug resolves to a file under `~/llm-wiki/wiki/{concepts,summaries,entities}/`. Covers AC-07 and AC-08.
- **Integrity check on `agents.md`** (deterministic + manual, pre-commit): Run `git diff` scoped to the preserved sections (`## When to Use an Agent vs. Alternatives`, `## Capability Scoping`, `## Persona authoring`, `## Scope`, `## Security`); pass criterion zero lines changed. Verify by inspection that the body-content paragraph at lines 27–29 retains its two existing sentences and gains exactly the two specified additions. Covers AC-06.

No unit, integration, or e2e tests are added — there is no executable artifact to test. The testing surface is the rule documents themselves and the agent behavior they elicit.

An optional post-commit behavioral sanity check is described in UV-5; it is not load-bearing on any AC.

### Existing tests impacted

Two TAP test scripts exercise the modified files. Both should pass post-restructure without modification, but both must be run pre-commit to confirm:

- **`tests/sdl-workflow/test-agents-md-persona-guidance.sh`** — 12 TAP assertions against `agents.md`. The three assertions touched by this restructure (Test 2 on `^## .*[Pp]ersona`, Test 9 on the `Detector` and `Challenger` names, Test 10 on `what not to include`) all anchor on content inside the preserved `## Persona authoring` section. Each should pass without modification because the restructure does not touch `## Persona authoring`. Pre-commit run required to confirm.
- **`tests/sdl-workflow/test-reference-integrity.sh`** — walks asset files for path references and verifies every leaf is referenced from at least one other asset. No file paths change in this spec, so the test should pass without modification. Pre-commit run required to confirm.

Inbound documentation references to the modified files (`.claude/CLAUDE.md` line 1; the routing table within `fbk-context-assets.md` itself) need no updating because no file paths or section names referenced from outside the three files change. The routing table in the parent doc still maps to the six leaves correctly.

### Test infrastructure changes

None.

### Mocking justifications

None — no mocks involved.

### User verification steps

UV-1: Read updated `assets/fbk-docs/fbk-context-assets.md` between `## Trust the Agent's Native Capabilities` and `## Choose the Right Trigger and Content Strategy` → A `## Objectives over Procedural Steps` section is present with the imperative rule, the acceptance-criterion paragraph, the drift-prone vs. drift-resistant table, the output-structure paragraph, the workflow-routing paragraph (workflow lives in skills, docs, or spawn prompts; orchestrator composes at spawn time; references `## Separation of Concerns` for the inline-vs-extract decision on small single-consumer workflows), and a citation line to `anthropic-2026-prompting-best-practices`, `cemri-2025-multi-agent-systems-fail`, and `ugare-2026-agentic-code-reasoning`.

UV-1b: Read the Trigger Types table in `## Choose the Right Trigger and Content Strategy` → The Agents row's Example cell reads "Specialized personas (workflow comes from skills, docs, or the spawn prompt at composition time)" — no longer references "delegated workflows." All other rows of the table are unchanged.
UV-2: Read updated `## Write for Agents, Not Humans` section in `fbk-context-assets.md` → A new paragraph after the positive-framing instruction states the anti-bias-instruction rule with its corrective ("restructure instead") and a citation to `huang-2026-anchoring-effect-llm`.
UV-3: Read updated `assets/fbk-docs/fbk-context-assets/agents.md` → The `## Instruction Design` section is replaced by a `## Description field` section containing only the two description-field instructions; the body-content paragraph at lines 27–29 retains its two existing sentences and now includes the constraint-ordering instruction ("Place critical constraints first") and a forward pointer to `## Persona authoring` with Detector and Challenger named as canonical examples; `git diff` shows zero lines changed in the five preserved sections (`## When to Use an Agent vs. Alternatives`, `## Capability Scoping`, `## Persona authoring`, `## Scope`, `## Security`).
UV-4: Read updated `assets/fbk-docs/fbk-context-assets/referenced-docs.md` → The single cap-at-5 line is replaced by two single-constraint rules (cap + diversify) followed by a citation line to `tang-2025-few-shot-dilemma` and `huang-2026-anchoring-effect-llm`.
UV-5 (optional post-commit sanity check, not load-bearing on any AC): In a fresh session, ask the agent to "draft a placeholder skill that finds dead code in a repo" → The agent produces a skill that leads with an objective and a measurable acceptance criterion, not a numbered procedural step list (or, if a step list appears, it is justified by step order mattering for correctness). Rejection criteria: the check fails if the produced acceptance criterion uses unfalsifiable qualifiers like "appropriate", "reasonable", "good", "clean", or "thorough" without an operationalization. Without this calibration, a tester pattern-matching on "looks objective-y" would pass weak outputs.
UV-6: Read CHANGELOG.md → A "Changed" entry under the next unreleased version summarizes the rules update.
UV-7: Read the `## Self-application audit` section in the implementation retrospective → Contains a table with one row per added/replacement instruction across the three modified files. No instruction is absent. No row has empty or non-specific cells in the five columns (instruction, Necessity outcome, framing, single-constraint, why-clause status).
UV-8: Verify each new wiki citation slug exists at `~/llm-wiki/wiki/concepts/`, `~/llm-wiki/wiki/summaries/`, or `~/llm-wiki/wiki/entities/` → All cited slugs resolve to real wiki pages.

UV-1 maps to AC-01, AC-02, AC-03 (output-structure + workflow-routing portions). UV-1b maps to AC-03 (Trigger Types table cell portion). UV-2 maps to AC-05. UV-3 maps to AC-06. UV-4 maps to AC-04. UV-5 is an optional behavioral sanity check, not load-bearing on any AC. UV-6 maps to AC-09. UV-7 maps to AC-08. UV-8 maps to AC-07.

## Documentation impact

### Project documents to update

- **CHANGELOG.md**: Add a "Changed" entry under the next unreleased version summarizing the rules update (objectives-over-procedural-steps principle, measurable acceptance criteria, output-structure distinction, anti-bias-instruction rule, agents.md restructure, cap-at-5 diversity sharpening, three citations).
- **README.md**: Audit only — confirm no required update. README references context asset authoring at a high level; this update does not change which file holds the rules or their top-level shape, and the routing table in the parent doc still maps to the six leaves correctly.

### New documentation to create

None. The spec, retrospective, and review report are SDL-stage artifacts created by the workflow; they are not project documentation.

## Acceptance criteria

- AC-01: `assets/fbk-docs/fbk-context-assets.md` contains a new `## Objectives over Procedural Steps` section between `## Trust the Agent's Native Capabilities` and `## Choose the Right Trigger and Content Strategy`. The section contains a rule stating: state the agent's objective and a measurable acceptance criterion; enumerate procedural steps only when step order matters for correctness.
- AC-02: The same section contains an instruction to pair every objective with a measurable acceptance criterion, with at least one drift-prone vs. drift-resistant example pair illustrating the pairing.
- AC-03: The same section contains (a) a paragraph stating that output-structure prescription is not procedural prescription, with at least one example of output-structure constraints (sections, schema, output fields), AND (b) a workflow-routing paragraph stating that workflow content lives in skills, referenced docs, or the spawn prompt — not in an agent definition body. The workflow-routing paragraph names the orchestrator-composes-at-spawn-time mechanism, states the failure mode of embedding workflow in an agent body, and references `## Separation of Concerns` for the inline-vs-extract decision on small single-consumer workflows. AND (c) the Trigger Types table in `## Choose the Right Trigger and Content Strategy` Agents row Example cell reads "Specialized personas (workflow comes from skills, docs, or the spawn prompt at composition time)" — the prior "delegated workflows" phrase is removed; the other four rows (CLAUDE.md, Rules, Skills, Hooks) and the content-strategies table and key-considerations subsection below are unchanged.
- AC-04: `assets/fbk-docs/fbk-context-assets/referenced-docs.md` line 34 is replaced by two single-constraint rules: a cap-at-5 rule with a one-clause why, and a diversity rule with a one-clause why. A citation line follows.
- AC-05: `assets/fbk-docs/fbk-context-assets.md` `## Write for Agents, Not Humans` section contains a new paragraph after the positive-framing instruction stating that asset authors restructure to remove bias-sources rather than instructing the agent to ignore them. The paragraph names anchoring as the mechanism and lists three example failed instructions ("ignore the previous example", "be objective", "don't be influenced by X").
- AC-06: `assets/fbk-docs/fbk-context-assets/agents.md` restructure is complete as a unit: (a) no `## Instruction Design` section remains; (b) a `## Description field` section in its place contains exactly the two description-field instructions (specific matchable language; "use proactively" pattern) and nothing else; (c) the body-content paragraph at lines 27–29 retains its two existing sentences and adds exactly two items — the constraint-ordering instruction "Place critical constraints first" and a forward pointer to `## Persona authoring` naming Detector and Challenger as canonical examples; (d) `## When to Use an Agent vs. Alternatives`, `## Capability Scoping`, `## Persona authoring`, `## Scope`, and `## Security` sections survive with no incidental edits. Verified deterministically by `git diff` scoped to the preserved sections (zero lines changed) plus inspection of the body-content paragraph and the new `## Description field` section.
- AC-07: At least three new citations to wiki page slugs appear across the modified files. Required slugs: `anthropic-2026-prompting-best-practices`, `huang-2026-anchoring-effect-llm`, `tang-2025-few-shot-dilemma`. Acceptable additional citations: `cemri-2025-multi-agent-systems-fail`, `ugare-2026-agentic-code-reasoning`. Each cited slug exists as a file in `~/llm-wiki/wiki/concepts/`, `~/llm-wiki/wiki/summaries/`, or `~/llm-wiki/wiki/entities/`.
- AC-08: Self-application — the implementation retrospective contains a `## Self-application audit` section with a table holding one row per added or replacement instruction across the three modified files. Columns: (1) instruction (short identifier or verbatim quote); (2) Necessity Test outcome (yes/no with one-clause why — "removing would cause X"); (3) framing (positive, or paired prohibition); (4) single verifiable constraint (yes/no); (5) why-clause status (one clause and load-bearing for generalization, n/a if no why-clause). Absence of any added/replacement instruction from the table fails the AC. Empty or non-specific cells fail the AC.
- AC-09: CHANGELOG.md contains a one-paragraph "Changed" entry under the next unreleased version summarizing the rules update.

## Open questions

None.

## Dependencies

None. This is a documentation-only change to three files in `assets/fbk-docs/fbk-context-assets/` (or the parent `fbk-context-assets.md`) plus CHANGELOG.md. No external systems, libraries, APIs, or other features are required.

---

## Decisions resolved during scoping

- **Should the audit-existing-corpus task be in scope?** No — deferred to a follow-up spec. Rationale: (a) reading and modifying the existing corpus of context assets is fundamentally different work from updating the rules — the audit reads and edits dozens of files across `.claude/` and `assets/`, the rules update touches three files; (b) the rules update should land first so it provides the standard against which the audit runs; (c) the user's own ranking placed the audit as "lower leverage." A follow-up spec — provisionally `context-asset-corpus-audit` — would consume the updated rules as input.
- **Add new principles or restructure the existing six?** Add one consolidated new principle ("Objectives over Procedural Steps") that absorbs three related rules (objectives, measurable acceptance criteria, output-structure distinction). Rationale: the three rules form one coherent principle and reading them as three separate sections would force the agent to navigate forward to find the corrective for the failure mode. Consolidation also keeps the principle count moving from 6 to 7 (not 9), preserving the existing structure.
- **Where does the "don't instruct around bias" guidance live?** Inside the existing `## Write for Agents, Not Humans` section, as a new paragraph. Rationale: it is a writing rule (about how to write asset content), not a separate principle. Promoting it to a top-level principle would over-weight it relative to its scope of application.
- **`agents.md` line 76 — invert with task-framing language, or restructure the whole `## Instruction Design` section?** Restructure. Rationale: line 76 is one symptom of a deeper inherited misframe — `## Instruction Design` treats agents as workflow-bearing task runners, contradicting the `## Persona authoring` section in the same file, which correctly frames agents as personas (workflow steps belong in the spawn prompt). Patching line 76 alone would leave the contradiction in place and would import task framing onto a persona-shaped asset. Restructuring removes the contradiction and aligns the file with what agents are for.
- **Where to preserve the constraint-ordering instruction from deleted line 74?** Extend the body-content paragraph at `agents.md` lines 27–29 with "Place critical constraints first." Rationale: an initial council-review pass identified that the deleted line 74's "Place critical constraints before detailed instructions" instruction is not covered by `## Persona authoring` or by the existing body-content paragraph — `Persona authoring` covers role activation + quality bars + anti-defaults (the structure of the body) but does not state the constraint-ordering rule. Without preservation, the restructure loses one real instruction. The body-content paragraph at lines 27–29 is the natural home (it already discusses what goes in the body); extending it costs one sentence and keeps the `## Description field` section narrowly about the description frontmatter field.
- **How does an author find body-content structure after the restructure?** Add a one-line forward pointer in the extended body-content paragraph naming `## Persona authoring` and the Detector/Challenger canonical examples. Rationale: removing the test-runner inline example leaves no in-line example in `agents.md`. The Detector and Challenger references in `## Persona authoring` (line 127 of the current file) carry the example burden, but an author landing on `agents.md` for the first time may skim past three sections before reaching them. The forward pointer in the body-content paragraph (which is right after the frontmatter table) gives a direct path.
- **Why does the new principle include asset-type routing (workflow lives in skills/docs/spawn prompts), not just procedural-vs-objective framing?** Because Claude Code's actual subagent composition mechanics establish persona and workflow as separately-routed concerns, and any rule about how to handle procedural content has to name where the procedural content lives. The orchestrator can pass workflow instructions to a persona-defined subagent at spawn time (via the Agent tool's `prompt` parameter), can route the subagent to load a skill or referenced doc, and can preload a fixed workflow via the agent definition's `skills:` frontmatter. Embedding workflow in the agent body pre-empts that composition. A principle that only addresses "how to write a step list" without addressing "where the step list lives" would leave authors free to embed workflow in agent bodies — the exact misframe the `agents.md` restructure (Change 3) corrects. Verified against `code.claude.com/docs/en/agent-sdk/subagents.md` and `code.claude.com/docs/en/skills.md`.
- **What about agents like `fbk-code-review-detector` and `fbk-code-review-challenger` that currently embed workflow in their body?** That embedding is a current implementation choice, not a rule. Per Claude Code's documented composition mechanics, the orchestrator can compose persona + workflow at spawn time: agent definition body holds the persona, workflow comes from a skill, a referenced doc, or the spawn prompt. Pipeline agents that currently embed workflow in the persona body are compliant with the *prior* rules but inconsistent with the new principle (Change 1a) and the restructured `agents.md` (Change 3). Reconciliation is corpus-audit work (deferred to the follow-up spec). The principle, the table cell fix (Change 1b), and the agents.md restructure in this update are the standard against which that audit will run.
- **Should we constrain spawn-prompt authors too?** No. Per Claude Code's documented composition mechanics, the Agent tool's `prompt` parameter is the canonical workflow-composition channel. Workflow-in-spawn-prompt is the design, not drift. The procedural content the new principle redirects out of agent bodies has three legitimate destinations — skills, referenced docs, and spawn prompts — and constraining the spawn-prompt destination would close off the most flexible of the three.
- **Test-runner example — refresh or remove?** Remove (with the surrounding `## Instruction Design` section). Rationale: the example uses procedural steps in the agent body, which the `Persona authoring` section explicitly forbids. The Detector and Challenger references at line 127 of Persona authoring carry the example burden authoritatively.
- **Cascade into SDL workflow docs or design guidelines?** No, scope is `assets/fbk-docs/fbk-context-assets.md` plus its leaves only. Rationale: the SDL guides have their own purpose and audience; cascading is a separate analysis worth its own spec if warranted.
- **Citation format?** Inline italic parenthetical at end of relevant paragraph or section, no bibliography section, citations only on new content (not back-applied to existing principles). Rationale: citations are wiki pointers, not formal academic apparatus; bibliography would add maintenance burden without benefit; back-applying citations to existing principles is scope creep that does not change behavior.
- **"Why" clauses on rules — include or omit?** Include only when load-bearing for generalization; omit when literary. Rationale: per `objective-driven-prompting`, explaining why the rule exists lets the model generalize the rule to unanticipated cases (Anthropic's ellipses example). But essay-style descriptions of the failure mode (e.g., "vague qualitative objectives cause the agent to fill interpretive gaps with statistically plausible but use-case-incorrect completions") read as written-for-a-human prose and do not aid generalization. The test: would removing the why-clause change what the agent does in a novel situation? If no, remove.
