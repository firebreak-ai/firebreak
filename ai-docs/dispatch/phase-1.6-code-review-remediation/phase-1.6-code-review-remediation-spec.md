# Phase 1.6: Code Review and Remediation — Spec

## Problem

The SDL pipeline produces behaviorally correct code but has no mechanism for reviewing *existing* code — either its own output or code in brownfield codebases. Post-implementation code review found 14 issues in code that passed all 172 tests (Phase 1.5 retrospective). The pipeline can build new features correctly but cannot diagnose or improve existing code.

Developers with AI-degraded codebases — where bug fixes silently bypass core mechanisms, tests validate surface behavior without exercising intended architecture, and iterative AI changes accumulate semantic drift — have no structured entry point into the SDL pipeline. They need a way to audit what exists, understand what's wrong, and produce specs that drive remediation through the existing spec → review → breakdown → implement flow.

## Goals / Non-goals

**Goals:**
- Add a `/code-review` skill that audits code and conversationally co-authors remediation specs with the user
- The skill uses two new focused agents (Detector, Challenger) with adversarial verification in an iterative loop
- The primary output is a spec (or spec tree) that enters the existing SDL pipeline — findings are internal evidence, not the deliverable
- Support three entry scenarios: cleanup (structural issues against the AI failure mode checklist), spec-backed remediation (behavioral comparison against existing specs), and intent recovery (reverse-author specs from code with the user)
- The skill also serves as a post-implementation pipeline stage, where findings-only output (no spec conversation) is appropriate
- Validate the behavioral comparison prompting technique on a real brownfield codebase

**Non-goals:**
- Automated fix application — v1 is suggestion-only
- A separate "remediation pipeline" — remediation flows through the existing SDL pipeline once the code review conversation produces specs
- Multi-agent parallel detection architecture — v1 uses a focused agent pair, multi-agent is the validated target for future phases
- Mutation testing integration — deferred
- Support for untrusted/adversarial codebases — v1 assumes the user owns the target codebase

## User-facing behavior

The `/code-review` skill has two primary paths, sharing the same agents and behavioral comparison methodology but with different interaction models and outputs.

### Path 1: Existing code review (conversational)

The user invokes `/code-review` to review existing code. The experience is a guided conversation — the user directs the review, the agent researches and documents.

**The user steers.** The user defines what's in scope, what to focus on, and what the code is supposed to do. The agent follows the user's direction, reads the code they point to, and runs detection/verification on what they care about:
- "Let's start with the auth module"
- "Focus on the session handling — that's where I think the problems are"
- "Skip the utility functions, they're fine"
- "Actually, let's also look at the data layer — I think the caching is being bypassed"

**The agent researches.** As the user directs, the agent reads the indicated code and runs the Detector/Challenger loop. Confirmed findings surface as evidence in the conversation — not as a formal report, but as observations the agent presents for discussion:
- "I see the session validation at session.ts:45 only checks token expiry. The spec's AC-03 requires both expiry and signature validation. The signature check appears to have been removed."
- "There's duplicated order processing logic in checkout.ts and returns.ts — lines 67-89 in each are near-identical."

**The user provides design intent.** This is the highest-value interaction. The agent's observations are starting points; the user's corrections and additions are the substance:
- "Right — the signature check got dropped when an AI assistant fixed the timeout bug three releases ago. It needs to come back."
- "That duplication is actually the bigger problem. Both were supposed to call OrderProcessor, but somewhere along the way they started reimplementing the logic inline."
- "The caching layer bypass is the real issue. The whole data module was designed to go through CacheService. None of it does anymore."

**The conversation produces a spec.** As the picture clarifies, the agent drafts spec sections. The Problem section emerges from findings. Goals from the user's intent. Technical Approach from the discussion of how things should work. The agent recognizes scope — a focused review produces a feature-level spec, a broad review produces a project overview with child feature specs — the same scope recognition the `/spec` skill uses.

The user may discover scope through the conversation. They might start with "review the auth module" and end up with a spec tree covering auth, session management, and the data layer — because the conversation revealed those are interconnected. The spec grows organically from what the user cares about.

As the conversation progresses, the agent periodically presents draft spec sections for user confirmation — "Based on our discussion, here's what I have for the Problem section and Goals. Does this capture your intent?" — before moving on to the next area. This follows the same iterative drafting pattern as `/spec` co-authoring.

The spec uses the standard 9-section template, passes through spec-gate.sh, and enters the existing SDL pipeline for review → breakdown → implement.

**Module-by-module for large codebases.** The agent naturally scopes the conversation to manageable pieces, following the user's direction. Each module's review fits within context limits, and the spec tree grows incrementally as the conversation covers more ground.

**When only structural issues surface.** If the review conversation reveals only structural issues (duplication, dead code, magic numbers) and the user confirms no design intent is needed, the conversation naturally stays lightweight — the agent presents findings against the AI failure mode checklist, and the user confirms or dismisses them. This isn't a separate mode the user selects; it's the organic outcome when specs aren't needed. If the user later says "actually, let me explain what that module was supposed to do," the conversation transitions naturally into spec co-authoring.

### Path 2: Post-implementation review (automated)

After `/implement` completes, the user is asked "would you like to review the implementation?" (following the existing stage-transition pattern). If accepted, the skill runs a code review against the implementation output. This path is non-interactive — a structural quality check, not a conversation.

**Scope**: The files modified by the implementation.
**Source of truth**: The feature spec that drove the implementation (its ACs and UV steps).
**Output**: Structured findings only — issues the implementation introduced or left unaddressed.
**Interaction**: Minimal. The user sees findings and triages through the existing corrective workflow.

This path uses the same Detector/Challenger agents and behavioral comparison methodology, but the orchestrator runs the full loop without further user involvement and presents the final confirmed findings.

### Progressive disclosure and file organization

Shared methodology lives in `docs/` (accessible to multiple skills and agents). Skill-specific path instructions live in the skill's `references/` directory (following Anthropic's recommended skill structure).

```
home/dot-claude/
  docs/sdl-workflow/
    ai-failure-modes.md            — shared: referenced by code review, test reviewer, and future flows
    code-review-guide.md           — shared: behavioral comparison methodology, finding format, orchestration protocol
  skills/code-review/
    SKILL.md                       — entry point: loads shared docs, routes to path-specific references
    references/
      existing-code-review.md      — skill-specific: conversational review flow, spec co-authoring guidance
      post-impl-review.md          — skill-specific: post-implementation review, findings-only flow
```

`SKILL.md` loads shared methodology from `docs/sdl-workflow/` and routes to path-specific instructions in `references/` based on invocation context.

**Deferred**: Existing skills (`/spec`, `/spec-review`, `/breakdown`, `/implement`) use an older convention where all reference docs live in `docs/sdl-workflow/` regardless of whether they are shared or skill-specific. A future phase should revisit existing skills to align with the shared-in-docs / skill-specific-in-references pattern established here.

## Technical approach

### Skill architecture: three layers

**Layer 1 — The skill (the recipe).** Owns the methodology: behavioral comparison lens, AI failure mode checklist reference, orchestration protocol, finding format, spec drafting guidance. The skill defines *what* to look for and *how* to frame the analysis. Stored in `.claude/skills/code-review/`. The skill's SKILL.md should stay under 500 lines per the skills authoring guide, with detailed instructions in `references/`. The skill specifies `allowed-tools` for the minimum set it requires to orchestrate (Read, Grep, Glob, Write, Edit, Bash, Agent — it reads code and docs, writes spec drafts and retrospectives, spawns agents).

**Layer 2 — The agents (the perspectives).** Two new focused agent definitions, always spawned as an agent team with fresh context per invocation. The agents never operate in the main session — they always get clean context through the team model.

- **Detector** (`home/dot-claude/agents/code-review-detector.md`): Scans code within the user-defined scope. Reads code through the behavioral comparison lens injected by the orchestrator at spawn time (from `docs/sdl-workflow/code-review-guide.md`). Describes what the code does, compares against the source of truth (spec ACs or failure mode checklist from `docs/sdl-workflow/ai-failure-modes.md`), and records **sightings** — observations of potential issues, not yet confirmed. Brings an analytical perspective informed by design coherence and pattern consistency. The agent definition includes an instruction to check for project-native analysis tools (lint configs, type checkers, static analysis) before falling back to manual code reading — this is a prompt instruction, not a tool integration. The agent uses Bash to run whatever the project already has. Description field should use matchable language for code analysis and pattern detection tasks.

- **Challenger** (`home/dot-claude/agents/code-review-challenger.md`): Reads the Detector's sightings and the code. Following Anthropic's code review model, each sighting is either **verified** (with evidence) or **rejected** (with counter-evidence). Demands concrete proof — "show me the code path where this actually fails" or "show me the spec AC this contradicts." Brings a skeptical, pragmatic perspective. Uses the behavioral comparison framing injected by the orchestrator. Description field should use matchable language for adversarial verification and evidence-based assessment tasks.

The Detector uses `tools: Read, Grep, Glob, Bash` — read-only access plus Bash for project-native tool discovery (lint, AST, static analysis). The Challenger uses `tools: Read, Grep, Glob` — pure analysis, no tool execution needed. Neither agent can write files. The orchestrator (main session) is the single writer — it captures agent output into findings, spec drafts, and retrospectives.

Agents do not inherit skills from the parent conversation. The orchestrator reads the shared methodology docs (`docs/sdl-workflow/code-review-guide.md` for the behavioral comparison lens, `docs/sdl-workflow/ai-failure-modes.md` for the checklist) and injects the relevant content into each agent's spawn prompt. This ensures agents receive the methodology without requiring `skills` frontmatter or context inheritance.

**Terminology**: The Detector produces *sightings*. The Challenger produces *verified findings* or *rejections*. Only verified findings surface in the conversation or the findings report. This distinction prevents unverified observations from reaching the user.

**Layer 3 — The orchestrator (the skill as facilitator).** The `/code-review` skill manages the agent team and the iterative adversarial verification loop:

*Existing code review path:*
1. User directs the agent to specific code areas
2. Spawns Detector with indicated code + source of truth + behavioral comparison instructions
3. Collects sightings
4. Spawns Challenger with sightings + code + "verify or reject each sighting with evidence"
5. Collects verification results; runs additional rounds for weakened sightings
6. **Continues the detection/verification loop until a round produces only `nit`-category sightings (or no sightings at all), or after a maximum of 5 rounds, whichever comes first.** The category classification is part of the sighting — the Detector assigns category, the Challenger can reclassify during verification. The hard cap is a safety net against pathological cases.
7. Presents verified findings as conversation evidence — the user discusses, provides intent
8. Agent drafts spec sections as the conversation progresses
9. Repeats steps 1-8 as the user directs the review to additional code areas
10. Spec (or spec tree) is finalized when the user and agent agree the review is complete

*Post-implementation review path:*
1. Automatically triggered after `/implement` verification passes
2. Spawns Detector with modified files + feature spec ACs
3. Spawns Challenger to verify sightings
4. Loops until a round produces only `nit`-category sightings or no sightings, or after 5 rounds
5. Presents verified findings to user — no conversation, no spec authoring
6. User triages findings through the corrective workflow

The orchestrator facilitates without contributing opinions — it manages the loop, not the analysis.

**Broad-scope reviews ("review everything"):** When the user requests a full codebase review rather than directing specific modules, the orchestrator takes on decomposition responsibility:
1. Surveys the project structure and identifies reviewable units (modules, directories, logical groupings)
2. Proposes a review order to the user — the user can adjust or accept
3. Spawns fresh Detector/Challenger pairs per unit, isolating each unit's code in clean agent contexts to prevent context overload
4. Accumulates verified findings across units, watching for cross-module patterns (shared dependencies misused in multiple places, consistent drift patterns)
5. Checkpoints with the user after each unit: summarizes findings so far, asks whether to continue reviewing or start speccing what's been found
6. The orchestrator's context grows with findings but never with raw code — the agents handle code reading in their isolated contexts

### Retrospective

Each code review run produces a retrospective following the pipeline's existing retrospective pattern. The retrospective captures:

- **Sighting counts**: total sightings, verified findings, rejections, nits at termination
- **Verification rounds**: how many detection/verification iterations before convergence
- **Scope assessment**: the code scope reviewed (files, modules, lines) relative to context usage
- **Context health proxies**: round count, sightings-per-round trend (declining sighting count may indicate context exhaustion rather than code quality), rejection rate per round (increasing rejections suggest declining sighting quality), whether the hard cap was reached. Per-agent token consumption is not currently observable from within Claude Code sessions (see [Issue #22625](https://github.com/anthropics/claude-code/issues/22625)), so these proxies serve as the empirical signal for whether future reviews of similar scope need decomposition.
- **Tool usage**: which project-native tools (lint, AST, static analysis) were available and used vs. grep/glob fallback
- **Finding quality**: false positive rate (findings the user dismissed during conversation), false negative signals (issues the user identified that the Detector missed)

This data feeds the decision about whether large-scope reviews need automatic decomposition (analogous to how `/breakdown` decomposes specs into tasks). The decomposition mechanism is a future extensibility concern — v1 relies on user-directed scoping, and retrospective data from real reviews will inform when and how automatic decomposition is needed.

### Behavioral comparison lens

The skill provides the behavioral comparison framing to both agents. This is a hard architectural constraint:

- **Do**: "Describe what `processOrder()` does. Compare that behavior to AC-03: 'Orders with expired coupons are rejected with error code COUPON_EXPIRED.'"
- **Don't**: "Find bugs in `processOrder()`."

Based on research showing 85.4% accuracy with behavioral comparison vs 11.0% with explain-and-fix prompting (arXiv:2508.12358). This figure justifies the framing choice; it is not a performance target for this system — real-world accuracy will depend on codebase complexity, spec quality, and model capability. The skill's instructions enforce this framing structurally — it is not left to agent discretion.

### AI failure mode checklist

The checklist lives in `home/dot-claude/docs/sdl-workflow/ai-failure-modes.md` — available to multiple flows, not embedded in the code review skill. The skill references it; the agent reads it when operating without specs. Known failure modes (from retrospective data):

1. Tests that re-implement production logic (test their own inline code, not the system)
2. Copy-paste duplication across state branches or modules
3. Magic numbers carried as bare literals across file boundaries
4. Dead code from abandoned approaches left in place
5. Hardcoded coupling where abstraction was specified
6. Inconsistent architectural patterns (correct in one file, bypassed in the next)
7. Middleware/layers defined but never connected
8. Trivially-true assertions (OR-conditions where one branch is always true)
9. Test names that don't match what the assertion verifies
10. Surface-level fixes that bypass core mechanisms

### Sighting and finding format

**Sightings** (Detector output — internal, not user-facing):
```
Sighting ID: S-01
Location: src/auth/session.ts:45-67
Category: semantic-drift | structural | test-integrity | nit
Observation: [What the Detector observed — behavioral description]
Expected: [From spec AC or failure mode checklist]
Source of truth: AC-03 from auth-spec.md | AI failure mode checklist item 5
```

**Verified findings** (Challenger output — surfaces in conversation or findings report):
```
Finding ID: F-01
Sighting: S-01
Location: src/auth/session.ts:45-67
Category: semantic-drift | structural | test-integrity | nit
Current behavior: [Confirmed behavioral description]
Expected behavior: [From spec AC or failure mode checklist]
Source of truth: AC-03 from auth-spec.md | AI failure mode checklist item 5
Evidence: [Challenger's verification evidence — code path, test result, or behavioral proof]
```

Findings are internal evidence used during the conversation, not a user-facing deliverable (except in cleanup and post-implementation modes).

### Source of truth handling

**Path 1 — Existing code review (conversational):** The agent checks for existing specs — provided by the user or discovered in `ai-docs/`. If specs exist, they serve as the starting comparison point for behavioral comparison against ACs and UV steps; conflicts between specs or between specs and code are surfaced for user discussion. If no specs exist, the agent uses the AI failure mode checklist for structural issues, and the conversation builds toward a spec that captures the user's design intent. The scenario emerges from the conversation, not from upfront classification — the agent handles the presence or absence of specs fluidly as part of the review.

**Path 2 — Post-implementation review (automated):** The feature spec that drove the implementation is always available. The agent uses its ACs and UV steps as the source of truth for non-interactive behavioral comparison.

### Integration seam declaration

- [ ] `/code-review` SKILL.md → `references/existing-code-review.md`: path routing based on invocation context (standalone vs post-implementation)
- [ ] `/code-review` SKILL.md → `references/post-impl-review.md`: path routing based on invocation context
- [ ] `/code-review` skill → Detector/Challenger agents: agent spawning with `tools` allowlist (Detector: Read, Grep, Glob, Bash; Challenger: Read, Grep, Glob), behavioral comparison lens injection, finding format specification
- [ ] `/code-review` skill → feature-spec-guide.md: remediation specs conform to the 9-section template defined in `home/dot-claude/docs/sdl-workflow/feature-spec-guide.md`
- [ ] `/code-review` skill → spec-gate.sh: remediation specs from conversational path pass the same gate as forward specs
- [ ] `/code-review` skill → AI failure mode checklist: reads `home/dot-claude/docs/sdl-workflow/ai-failure-modes.md` as source of truth when no specs available
- [ ] Detector agent → Challenger agent: sightings passed as structured input, verification output references sighting IDs and produces verified findings
- [ ] `/code-review` spec output → existing SDL pipeline: remediation specs enter `/spec-review` → `/breakdown` → `/implement` unchanged
- [ ] `/implement` skill → `/code-review` post-impl path: one-line addition to `/implement` completion — asks the user "would you like to review the implementation?" following the existing stage-transition pattern

### Runtime value precision

- Sighting IDs use the format `S-NN` (S-01, S-02, ...)
- Finding IDs use the format `F-NN` (F-01, F-02, ...)
- Category values are exactly: `semantic-drift`, `structural`, `test-integrity`, `nit`
- `nit` is defined as: observation is accurate but functionally irrelevant — naming, formatting, style, minor inconsistency that does not affect behavior or maintainability
- Both sightings and findings use `category` as the field name. The Challenger may reclassify during verification (e.g., upgrade a `nit` to `structural` or downgrade a `structural` to `nit`).

## Testing strategy

### New tests needed

- **Unit test**: Finding format validation — a generated finding conforms to the required schema (all fields present, category values from the allowed set) — covers AC-03
- **Unit test**: Behavioral comparison prompt construction — given a code path and an AC, the prompt uses "describe what this does, then compare" framing, never "find bugs" — covers AC-04
- **Integration test**: Detection-verification round trip — given a synthetic codebase with known issues (planted duplication, a function that contradicts its spec AC), the Detector produces findings and the Challenger confirms the real ones and disproves a planted false positive — covers AC-01, AC-02
- **Integration test**: Spec output from review — given confirmed findings and simulated user intent, the skill produces a spec draft that passes spec-gate.sh structural checks — covers AC-05
- **Integration test**: Cleanup mode (no specs) — given a codebase with known AI failure mode patterns (magic numbers, dead code), the skill produces findings referencing the checklist — covers AC-06
- **E2e test**: Full code review cycle — invoke `/code-review` against a test fixture codebase with a spec, verify findings are produced, verify the conversation produces a remediation spec that passes the gate, whose Problem section incorporates user-stated design intent, and where a confirmed structural finding appears in the spec's testing strategy section — covers UV-1 through UV-4
- **Structural test**: Dual-mode routing — SKILL.md references both path-specific reference files, both reference files exist at declared paths — covers AC-07
- **Structural test**: Agent read-only constraint — Detector and Challenger agent definitions use `tools:` allowlist restricting to read-only tools (Read, Grep, Glob, Bash) — covers AC-08
- **Structural test**: Retrospective schema — retrospective output contains all required fields (sighting counts, verification rounds, scope assessment, finding quality) — covers AC-12
- **Structural test**: Post-implementation stage-transition prompt — the `/implement` skill contains the stage-transition prompt text asking the user if they want a code review — covers AC-07 (post-impl trigger point)

**Tier 2 (validated through brownfield test project):**
- AC-07 (behavioral): Post-implementation path produces findings-only output without initiating spec co-authoring — verified by invoking `/code-review` after `/implement` during the brownfield test
- AC-09: Adversarial loop termination — verified by observing convergence behavior during real code reviews against the user's brownfield test project
- AC-10: Spec conflict detection — verified during spec-backed remediation of the test project's conflicting specs
- AC-11: User-directed scoping — verified during conversational review of the test project's modules
- AC-13: Project-native tool usage — verified during review of a test project that has lint/AST tools available; the Detector discovers and uses them via Bash natively, no special integration needed

### Existing tests impacted

None — this is a new skill. Existing gate scripts and test infrastructure are reused but not modified.

### Test infrastructure changes

- **Test fixture codebase**: A small synthetic project (~5 files) with planted issues: one function that contradicts its spec AC (semantic drift), one block of duplicated code (structural), one test that re-implements production logic (test integrity), and one intentional deviation documented in the spec. This fixture validates detection accuracy and false positive filtering.
- **Synthetic spec**: A spec for the test fixture with ACs that the planted issues violate.

### User verification steps

- UV-1: Invoke `/code-review` with a spec and target files → the skill surfaces findings and begins a conversation about them
- UV-2: Discuss a semantic-drift finding with the agent → the agent incorporates the user's design intent into a spec Problem section
- UV-3: Confirm a structural finding → the agent notes it for the spec's testing strategy or as a corrective workflow item
- UV-4: Complete the review conversation → a remediation spec is produced that passes spec-gate.sh
- UV-5: Invoke `/code-review` with no specs → findings use the AI failure mode checklist, lightweight mode
- UV-6: A planted false positive is disproved by the Challenger and does not appear in findings
- UV-7: Invoke `/code-review` as post-implementation review → findings-only output, no spec conversation

## Documentation impact

### Project documents to update

- **README.md**: Add `/code-review` to the slash commands table. Add code review to the pipeline diagram (post-implementation stage). Update "How It Works" to mention code review as both standalone and pipeline stage.
- **home/dot-claude/docs/sdl-workflow.md**: Add code review as a workflow stage in the SDL index.
- **ai-docs/dispatch/dispatch-overview.md**: Reference Phase 1.6 in the phase listing.

### New documentation to create

- **home/dot-claude/docs/sdl-workflow/code-review-guide.md**: Reference doc for the code review skill — behavioral comparison methodology, source of truth scenarios, orchestration protocol, finding format, modes (conversational / cleanup / post-implementation).
- **home/dot-claude/docs/sdl-workflow/ai-failure-modes.md**: Formalized AI failure mode checklist. Currently exists as retrospective data across multiple documents. Structured as a numbered checklist with pattern descriptions, detection heuristics, and example manifestations.
- **home/dot-claude/agents/code-review-detector.md**: Detector agent definition — focused persona for analytical code observation and behavioral comparison.
- **home/dot-claude/agents/code-review-challenger.md**: Challenger agent definition — focused persona for adversarial verification and evidence demands.

## Acceptance criteria

- AC-01: The `/code-review` skill produces confirmed findings when given target code and a spec to review against
- AC-02: Findings that survive adversarial verification are surfaced in the conversation; disproved findings are excluded
- AC-03: Each finding conforms to the defined schema: finding ID, sighting reference, location, category, current behavior, expected behavior, source of truth reference, evidence
- AC-04: Detector and Challenger agents use behavioral comparison framing exclusively — no defect-detection prompts
- AC-05: The review conversation produces a remediation spec (or spec tree) that passes spec-gate.sh
- AC-06: When no specs are provided, the skill audits against the AI failure mode checklist and produces findings referencing checklist items
- AC-07: The code review skill works as a standalone invocation and as a post-implementation pipeline stage (findings-only mode)
- AC-08: Detector and Challenger agents are read-only (via `tools` allowlist) — they cannot modify files. The orchestrator is the single writer for all artifacts.
- AC-09: The adversarial verification loop terminates when a round produces only `nit`-category sightings or no sightings, or after a maximum of 5 rounds
- AC-10: For the spec-backed scenario, the skill identifies spec conflicts and discusses them with the user as part of the conversation
- AC-11: For large codebases, the orchestrator decomposes the review into manageable units and spawns fresh agent pairs per unit to manage context limits
- AC-12: Each code review run produces a retrospective capturing sighting counts, verification rounds, scope assessment, context health, tool usage, and finding quality metrics
- AC-13: The Detector uses project-native lint/AST/static analysis tools when available, falling back to grep/glob/read when not

## Open questions

*Resolved during authoring — none remaining.*

## Dependencies

- **Existing infrastructure (minor modification)**: spec-gate.sh (no change), `/spec` skill (no change), corrective workflow fast-track criteria (no change), retrospective pattern (no change), `/implement` skill (one-line addition: ask user if they want a code review at completion, following existing stage-transition pattern)
- **New context assets**: AI failure mode checklist (formalized from retrospective data), code review guide, Detector agent definition, Challenger agent definition, existing-code-review reference, post-impl-review reference
- **Claude Code features used**: subagent spawning with `tools` allowlist, iterative adversarial verification loop
- **Research basis**: arXiv:2508.12358 (behavioral comparison prompting, 85.4% accuracy), Anthropic adversarial-review pattern (iterate until findings degrade to nitpicks), Anthropic skills guide (three-layer architecture: skill provides methodology, agents provide perspective, orchestrator manages flow)
