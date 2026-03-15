# Task 03: Create Review Perspectives Doc

## Objective

Create the leaf doc that provides detailed Stage 2 (Spec Review) guidance for agents orchestrating SDL review via council agents.

## Context

This doc is loaded by the `/spec-review` skill when Stage 2 is active. It guides the agent through council classification, review invocation, finding synthesis, and threat model determination.

### Council agent classification

Classification determines which agents to invoke and how. The agent analyzes spec content and project context, then selects agents — the user can intervene but the default is forward motion.

**Classification inputs**:
- Spec content: what the feature does, what it touches
- Project context: complexity, existing architecture, project-level threat model
- Stage context: what kind of review is needed at this point

**Classification outputs**:
- Which agents to invoke (subset of 6)
- Invocation mode: solo (1 agent), discussion (2+ build toward consensus), or full council (all 6)
- Brief rationale for each selection (transparent reasoning the user can evaluate)

### SDL concerns and responsible agents

| SDL concern | Primary | Supporting | Review prompt framing |
|-------------|---------|-----------|----------------------|
| Architectural soundness | Architect | Builder | "Evaluate the technical approach for integration risks, performance implications, and conflicts with existing architecture" |
| Over-engineering / pragmatism | Builder | Advocate | "Identify areas where the design is more complex than the requirements justify" |
| Testing strategy and impact | Guardian | Analyst | "Validate that the testing strategy covers all acceptance criteria at the appropriate level. Verify that impacted existing tests are identified — search the test suite for coverage of affected files and functions. Flag any AC that lacks a corresponding test plan." |
| Threat modeling | Security | Architect | "Identify trust boundaries, data flows, entry points, and threats; compare against project threat model" |
| User impact / scope creep | Advocate | Builder | "Evaluate whether each requirement serves the stated user need without unnecessary scope expansion" |
| Measurability | Analyst | Guardian | "Verify that acceptance criteria are quantifiable and that success can be measured, not just asserted" |
| Documentation impact | (deterministic) | — | Verify the documentation impact section is present, specific, and cross-checked against feature scope |

### Classification signals (when to invoke each agent)

| Agent | Invoke when... |
|-------|---------------|
| Architect | New system boundaries, data flow changes, integration with existing systems |
| Builder | Complex technical approach, scope that could be simplified, aggressive sizing |
| Guardian | Behavioral changes needing test coverage, failure-sensitive code paths |
| Security | Auth/authz, data storage, external APIs, trust boundary changes |
| Advocate | User-facing behavior changes, scope that may exceed stated user need |
| Analyst | Quantifiable success conditions, claims requiring evidence, metrics |

### Invocation modes

- **Solo**: One perspective clearly dominates (e.g., pure security concern → Security agent alone).
- **Discussion**: Concerns cross boundaries (e.g., security vs. usability → Security + Advocate). 2-3 agents review and build toward consensus on blocking issues.
- **Full council**: Multiple classification signals fire or the feature is high-stakes.

One thorough pass over multiple fast passes. Give agents detailed, stage-specific review prompts — not brief generic ones. Prefer 2-3 agents with thorough instructions over 6 agents quickly.

### Invocation mechanism

All council invocations route through the existing `/council` skill. The classification step determines which agents and frames the review prompt with SDL context. The pipeline does not reimplement council infrastructure.

### Threat model determination

Every feature requires an active decision — not a passive default in either direction.

1. Summarize the feature's security-relevant characteristics: data touched, trust boundaries crossed, new entry points, auth/access control changes.
2. Ask the user: "Does this feature need a threat model?" Present the security summary as context.
3. Record the decision and rationale in the review document regardless of answer.

**If yes**: Read project threat model (`ai-docs/threat-model.md`) if it exists. Load `sdl-workflow/threat-modeling.md` for the detailed threat modeling process. Produce `<feature-name>-threat-model.md`.

**If no**: Record in review document: decision + rationale (e.g., "No new trust boundaries, no data handling changes"). Security concerns still surface through normal review if Security agent is invoked — the skip applies only to the structured threat model artifact.

### On re-run

When the user revises a spec and re-runs Stage 2, the review document is replaced entirely. Stale findings from prior reviews create confusion. Previous reviews are recoverable from git history.

### Review document structure

The review document organizes findings by SDL concern, not by agent. Each finding includes:
- **Severity**: blocking (must resolve before Stage 3), important (should address), or informational (note for awareness)
- **Category**: which SDL concern
- **Description**: actionable and specific — not generic observations

### Verification gate

**Structural prerequisites**:
- Review document contains findings from all classified (or user-selected) perspectives
- Each finding has severity classification (blocking/important/informational)
- Threat model determination recorded (decision + rationale)
- If threat model requested: document exists with required sections (assets, threat actors, trust boundaries, threats)
- Testing strategy coverage entries for all 3 categories (new, impacted, infrastructure) — empty categories have explicit "none" with justification

**Semantic evaluation** (human decides):
- Blocking findings genuinely resolved — addressed in spec revision or accepted with rationale and risk owner
- Review findings are actionable and specific, not generic observations

### Transition

After presenting findings:
1. Run structural prerequisites.
2. If blocking findings exist: "There are N blocking findings. Would you like to revise the spec to address them, or accept with documented rationale?"
3. If all resolved: "The review is structurally complete. Would you like to proceed to task breakdown?"
4. If agreed: invoke `/breakdown <feature-name>`.

## Instructions

1. Create `home/.claude/docs/sdl-workflow/review-perspectives.md`.
2. Read `home/.claude/docs/context-assets.md` for authoring principles. Apply them.
3. Write for the agent running Stage 2 — direct imperatives.
4. Structure the doc with these sections:

   - **Classification process** — Inputs, outputs, how to select agents and mode.
   - **SDL concerns table** — The full table with primary agent, supporting agent, and review prompt framing.
   - **Classification signals** — When to invoke each agent.
   - **Invocation modes** — Solo, discussion, full council. Include the "one thorough pass" principle.
   - **Invoking the council** — Route through `/council`, frame prompts with SDL context.
   - **Threat model determination** — The active decision flow (summarize, ask, record).
   - **Review document structure** — How to organize and format findings.
   - **On re-run** — Replace entirely, don't append.
   - **Verification gate** — Structural checks and semantic criteria.
   - **Transition** — Blocking finding resolution and next-stage offer.

5. The SDL concerns table and classification signals are the doc's highest-value content — the agent cannot derive this information. Invest tokens there. Generic "be thorough" advice fails the Necessity Test.
6. Target: 140-180 lines.

## Files to Create/Modify

- **Create**: `home/.claude/docs/sdl-workflow/review-perspectives.md`

## Acceptance Criteria

- AC-03: Enables council classification, prompt framing per SDL concern, invocation modes, and threat model determination
- AC-15: Follows authoring principles

## Model

Sonnet

## Wave

1
