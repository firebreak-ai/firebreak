---
title: "Refactored SDL: Decision Spine"
type: synthesis
sources:
  - remediation validation experiment (external source material, operator's wiki)
  - firebreak-sdl-workflow
  - firebreak-spec-grilling-brainstorm
  - validation-experiment-firebreak-postmortem
tags:
  - sdl-pipeline
  - architectural-decision-record
  - refactored-sdl
created: 2026-05-26
updated: 2026-05-29
---

## Refactored SDL: Decision Spine

Single cumulative log of the architectural decisions made while designing the refactored SDL improvement cycle. Each entry captures the decision, the context that forced it, the alternatives considered, and the rationale. New decisions during implementation are appended in order; superseded decisions are reframed in place rather than deleted.

**Scope evolution.** This design was trimmed in two scope passes. The first cut a durable cross-feature memory layer ("project-memory") and its capture gate (Decision 15). The second (2026-05-29) cut complexity-classification machinery, the architectural-review-meeting, and mutation sampling; reframed scope-appropriateness as a capability-entry model; replaced project-memory with a lightweight durable-artifact discipline; and settled the agent model. The load-bearing remediation learnings — intent/design/spec separation, the four slice shapes, hybrid gates, preserved test-integrity locking — are intact. The cycle is "markdown design pages plus a small number of gate scripts."

Source materials: the remediation validation experiment's lessons (external source material in the operator's wiki — not a page in this package), [[validation-experiment-firebreak-postmortem]], [[firebreak-spec-grilling-brainstorm]], [[slop-compounding-and-threshold]], [[anthropic-practice-alignment]], plus the [[firebreak-quality-rubric-sketch]] for code-quality patterns adapted into the quality-scan technique.

### Decision 1 — Six phases (intent → design → spec → breakdown → implementation → code-review)

**Context.** The as-shipped SDL is four high-level stages (Spec → Review → Breakdown → Implement) collapsed from 12. Remediation work surfaced that ambiguity closes too early — by spec authoring, the agent has already silently made product decisions that propagate through breakdown into implementation. Need to separate "what should this do?" from "how does it work?" without inflating ceremony.

**Decision.** Six phases, each with its own skill, inputs/outputs, and hybrid gate: intent, design, spec, breakdown, implementation, code-review. How much of the chain a given piece of work runs is governed by the capability-entry model (Decision 2), not by a classifier.

**Alternatives considered.**
- *Three or four phases* (consolidating intent into spec, or design into spec). Rejected because the consolidation is precisely the conflation remediation work demonstrated as harmful.
- *Calling implementation an "execution step" rather than a phase.* Rejected — implementation has its own skill ([[fbk-implement]]), its own per-task verification via `TaskCompleted` hook, and its own per-wave verification. It is a phase.

**Why this works.** The separation is the single biggest remediation win. The six phases name the real cognitive jobs; collapsing any pair is what produced the failures remediation recovered from.

### Decision 2 — Capability-entry replaces tier-driven depth; complexity-classification functionality is cut

**Context.** An earlier design applied all six phases uniformly to every dispatch-complexity tier, with the tier "modulating depth," and inserted a tier-classification eval that tagged each spec. But nothing consumed the tag — routing off it is explicitly a later project — so the eval produced a recorded tag that changed no behavior. And "uniform phases for all work" raised the obvious fear: a one-line fix crushed under six phases of ceremony.

**Decision.** Drop all complexity-classification *functionality* — no eval, no recorded tier tag, no tier-driven depth. The six-tier *definitions* stay in the glossary as shared vocabulary (the dispatch work and other contexts use them), but no skill or gate in this cycle acts on them. Scope-appropriateness is handled instead by a **capability-entry model**: each phase is an independently invocable capability, and the human enters the chain at the point that fits the work. A large change starts at intent and walks the whole chain; a small change can start at the spec, or go lighter still — conversationally from "here's what I want" to "how would we build this?" to implementation — never formally invoking the upstream phase skills. Nothing forces the full chain; Firebreak suggests the next step, the human decides. Depth is human judgment about scope, not a classifier output.

This is the existing [[mid-pipeline-entry]] protocol generalized: invoking a phase directly checks that its prerequisites hold and offers to run the missing upstream phase, rather than blocking. It also matches the existing corrective/fast-track workflow, where a bugfix already enters downstream rather than running the full ceremony.

**Alternatives considered.**
- *Keep the tier eval, build the router later.* Rejected — building an evaluator whose output nothing consumes is work for its own sake; it can be added when a router needs it.
- *Keep a lightweight recorded tier tag.* Rejected — even a recorded tag with no consumer is ceremony; the human's scope judgment at entry is the real signal.
- *Uniform six phases forced for all work.* Rejected — it's the small-feature ceremony tax made mandatory; capability-entry gives the same discipline without forcing it.

**Why this works.** Removes machinery nothing uses, resolves the small-feature concern at its root, and matches how invocable skills actually behave (you call them; they don't auto-chain uncommanded).

### Decision 3 — Four technique skills extracted (grilling, fresh-eyes, quality-scan, test-review)

**Context.** Several capabilities are needed across multiple phase skills: ambiguity grilling (intent, design, spec), comprehension review (intent, design, spec gates), quality scan (code-review), test review (breakdown + code-review). Embedding these inline in each phase skill duplicates instructions and produces inconsistent operator experience.

**Decision.** Extract four [[technique-skill]] capabilities: [[grilling-technique]], [[fresh-eyes-technique]], [[quality-scan-technique]], [[test-review-technique]]. Each callable by phase skills *and* invocable out-of-ceremony when a meaningful operator use case exists. Extraction criterion: two consumers, where the operator counts as a consumer if a real out-of-ceremony scenario exists.

**Alternatives considered.**
- *Embed each capability inline in each phase skill.* Rejected — duplication and drift.
- *Extract every capability into its own skill (more than four).* Rejected — single-consumer skills carry asset-management overhead without payoff.

**Why this works.** Each of the four has at least two consumers. Each has a clean input/output contract. Phase skills become orchestrators rather than monoliths.

### Decision 4 — Agents encode expertise; skills encode mode

**Context.** The new intent and design phases need context-isolated worker agents (the existing pattern — the spec author drafts in isolation). The question was whether to mint a new agent definition per skill. The existing roster is entirely engineering/review personas: there is no product/requirements-elicitation persona, and the architect persona exists only as a *council reviewer*, not an authoring agent.

**Decision.** An agent definition encodes a *role and expertise*; the skill it pairs with supplies the *mode and task*. The same senior architect both drafts a design and critiques one — what differs is the skill's instruction, not the agent. Concretely:
- **New requirements/product author** for the intent phase — plain-language, capability-framed, interview-grounded, composes grilling for ambiguity. No existing persona fits; the roster has nothing product-facing.
- **New general-purpose senior architect** for the design phase (authoring mode). Written as a superset the existing council architect can later collapse *into*.
- **Reuse** the existing spec author (spec), test reviewer (test-review), and council members (council). **Thin-new** cold reviewer for fresh-eyes (its value is being uncontaminated, so no specialist lens). **Adapt** the existing code-review detector for quality-scan (both surface issues).

**Alternatives considered.**
- *One new author agent per phase (1:1 skill:agent).* Rejected — proliferation; reuse where a role-appropriate definition exists.
- *Generalize and rename the council architect now.* Rejected for *this cycle* — it would force changes into the shipped council skill and the other council members. Instead, create the standalone general architect now and pin the council migration as future work (Decision 15). Temporary duplication of two architect definitions is consciously accepted.

**Why this works.** Matches the project's asset-type split (agents own persona, skills own routing/mode), reuses where it can, and lays the foundation for a cleaner council without dragging council changes into scope.

### Decision 5 — Hybrid gate pattern (mechanical anchor + semantic anchor on technique-skill artifact)

**Context.** The as-shipped two-layer gate pattern (structural + semantic) leaves the semantic layer to "human or AI judgment" without specifying how that judgment becomes a gate input. Semantic gates are then non-deterministic — same artifact, two runs, different verdicts — which breaks pipeline reasoning.

**Decision.** Every phase gate uses the [[hybrid-gate-pattern]]: a deterministic mechanical check plus a semantic check anchored on an artifact produced by a technique skill. The semantic work happens *inside the technique skill* (where its expense and non-determinism are contained); the gate's verdict is mechanical given the artifact. Phase skills may run a reconciliation step between the technique skill producing its raw output and the gate consuming it (e.g., deduplicating fresh-eyes observations against the grilling decision log so the operator isn't asked to address ambiguities already resolved during authoring).

**Alternatives considered.**
- *Pure mechanical gates.* Rejected — miss semantic problems.
- *Pure semantic gates.* Rejected — non-deterministic gate verdicts break pipeline reasoning.
- *Fresh-eyes consumes the grilling decision log as additional context.* Rejected — would compromise fresh-eyes' cold-context discipline. Deduplication is the phase skill's job, not fresh-eyes'.

**Why this works.** Determinism at the gate layer is preserved; semantic judgment is preserved; the technique-skill artifact is the contract between them.

### Decision 6 — Four slice shapes, with per-shape instructions loaded by progressive disclosure

**Context.** The classical red-green-refactor discipline assumes new tests precede new code. Brownfield work that preserves an existing contract has no red phase. A test-discipline that only handles greenfield is operationally narrow.

**Decision.** Four [[slice-shapes]] declared per slice in the spec: new-contract, contract-preserving, contract-evolving, cross-cutting. Each shape implies a different test-task structure. The instructions for each shape live in their own leaf; once a slice is classified into a shape, the breakdown agent reads only that shape's instructions ([[progressive-disclosure]]), so it isn't reasoning about three irrelevant disciplines while building one slice. Catching power is checked by the test-review-by-reading step (Decision 9); new-contract slices additionally use the plain red check (tests fail against an empty implementation). (Earlier the universal catching-power check was mutation sampling; that is deferred — Decision 15.)

**Alternatives considered.**
- *Greenfield-only TDD.* Rejected as operationally narrow.
- *Greenfield vs brownfield binary.* Rejected — mixes contract-newness with code-newness.
- *Three shapes / five-plus shapes.* Rejected — three drops a real discipline (seam tests), five-plus fragments without gain.
- *Trim to a starter subset for v1.* Rejected — dropping contract-preserving/evolving would gut the brownfield-on-firm-foundation use case, a primary scenario; the shapes are declarative and cheap.

**Why this works.** The shapes correspond to actual test-discipline differences; progressive disclosure keeps each slice's context clean.

### Decision 7 — Schemas-from-design (with new-vs-existing delimiter)

**Context.** Where do typed schemas come from? PRD is behavioral, not technical. Pure greenfield-vs-brownfield doesn't work because brownfield work can introduce new schemas and greenfield work can be constrained by external systems.

**Decision.** New schemas come from the design phase, regardless of greenfield-vs-brownfield context. Existing schemas are detected by AST scan or codebase inspection and reflected in design pages as constraints. The delimiter is new-vs-existing (compatibility vs design), not greenfield-vs-brownfield.

**Alternatives considered.**
- *Schemas from PRD.* Rejected — PRD is behavioral.
- *Schemas from spec.* Rejected — spec consumes schemas, doesn't originate them.
- *Greenfield-vs-brownfield binary.* Rejected — wrong axis.

**Why this works.** The new-vs-existing rule is compositional; mixed work handles cleanly.

### Decision 8 — Quality scan is scan-only (no auto-fix)

**Context.** Quality scan surfaces top-five issues at code-review. Natural temptation: also fix the top one. But auto-fix couples the capability to a specific decision about what to do with findings.

**Decision.** [[quality-scan-technique]] is scan-only. The operator (or a downstream skill invocation) decides what to do — address inline, spin up a follow-up feature via [[fbk-design]], or defer with rationale.

**Alternatives considered.**
- *Scan + auto-fix-top-one.* Rejected — fix-application bypasses SDL discipline.
- *Scan with operator-selected fix mode.* Rejected — added complexity, same result as scan-only plus "design a fix for the top one."

**Why this works.** Modular capability composes cleanly; fixes go through the full SDL discipline.

### Decision 9 — Test-review at two checkpoints (pre-lock and final code-review)

**Context.** AI-written tests fail in characteristic ways (implementation-embedding, weak assertions). Locking a bad test is worse than no lock. But review at acceptance only catches problems at one moment; tests can become misaligned during implementation as call sites shift.

**Decision.** [[test-review-technique]] runs at two checkpoints — pre-lock (before [[test-integrity-locking]] applies hashes) and final code-review (after implementation complete). Pre-lock is the substantive review and the primary catching-power judgment (by reading); final is the drift check.

**Alternatives considered.**
- *Single checkpoint at acceptance.* Rejected — misses drift.
- *Single checkpoint at code-review.* Rejected — locking a bad test is the failure mode the technique exists to prevent.
- *Continuous review during implementation.* Rejected as expensive and disruptive.

**Why this works.** The two checkpoints align with the two distinct failure modes (test was bad to start vs test drifted during implementation).

### Decision 10 — Fresh-eyes is a standalone technique; the council is the existing related pattern

**Context.** Multiple gates need cold-context review. An earlier design grouped three review patterns into a "fresh-eyes family": single cold pass, parallel multi-persona council, and an iterative multi-persona meeting. The meeting was then deferred (Decision 15), leaving a "family" of two — one new (fresh-eyes) and one already shipped and unchanged (council).

**Decision.** Drop the "family" framing. [[fresh-eyes-technique]] is a standalone technique — a cold, context-isolated reviewer producing structured observations, used as the semantic anchor at the intent and design gates. The council ([[council-deliberation]] via [[fbk-spec-review]]) is the *existing* multi-persona cold-review pattern, used at the spec gate; it is related but not rebuilt, and it isn't dressed up as a "variant" of a new abstraction.

**Alternatives considered.**
- *Keep the family abstraction for the two remaining patterns.* Rejected — a formalized family of two, where one member already exists and isn't changing, is a thin abstraction the operator never sees.

**Why this works.** Ships the one new technique on its own merits; relates it to the existing council in passing without inventing taxonomy. If the meeting returns later, the family framing can return with it.

### Decision 11 — Preserve the existing hash-lock; the manifest gains slice metadata

**Context.** Hash-locking accepted tests before implementation is an existing, shipped Firebreak feature. The question was what this cycle changes about it.

**Decision.** Preserve the shipped hash-lock mechanism unchanged: tests are SHA-256 locked by the test reviewer before implementation, modification trips the verification gate, locks recorded in the feature-directory test-lock manifest. This cycle's only additions: the manifest entries gain slice metadata (the slice and its test-discipline mode), and contract-preserving slices also lock the pre-existing tests they rely on. A future cycle intends to wire the lock to hooks for more deterministic enforcement; that is out of scope here.

**Alternatives considered.**
- *Treat hash-locking as a new feature.* Rejected — it already ships; this cycle preserves it.
- *Add mutation sampling as the catching-power proof now.* Deferred — Decision 15.

**Why this works.** Keeps a proven mechanism intact; the slice metadata is the minimal addition the new slice-shape model needs.

### Decision 12 — Durable-artifact discipline replaces project-memory

**Context.** Project-memory (Decision 15) was cut, which left a real question: intent is *sticky* and carries across features (Decision 13), so it needs somewhere durable to live — but per-feature artifacts are squashed away. A heavyweight wiki was rejected; the answer had to be lightweight.

**Decision.** A small, curated set of plain git-tracked markdown docs — not a memory system, no tooling, no index, no install contract:
- **Glossary** — aligned terminology. Edited in place.
- **Decisions log** — the *why* behind enduring choices. Append-only, chronological.
- **Architecture/intent overview** — what the project is and how it works, now. Living, edited in place, bounded to onboarding length — the doc a new human hire (or a cold agent) reads to come up to speed.

These live in the repo's normal doc locations and are governed by a comprehensibility discipline: persists in git, not throwaway like a spent task breakdown, doesn't accrete into clutter, stays simple-language and bounded with intuitive names and folders. They are **updated in feature branches** and **merge into main with the change they describe**, so branch docs describe the branch and main docs describe main — the docs stay as in-sync as the code, because they *are* part of the change. A stale overview shows up as "this PR changed behavior but didn't touch the overview" right in the diff; parallel edits resolve as ordinary git merge conflicts. Git co-location *is* the sync mechanism the wiki lacked. Spent scaffolding (spec, breakdown, manifests, reports, retrospective) stays throwaway in the feature directory.

This **supersedes the earlier "all design output is ephemeral" position.** Not everything is ephemeral: the durable *why* and the onboarding overview persist; the spent scaffolding does not. CLAUDE.md is reserved for agent behavioral rules, not project intent.

**Alternatives considered.**
- *Project-memory wiki.* Cut — Decision 15.
- *All design output ephemeral, no durable trail.* Rejected once intent-stickiness made a durable substrate necessary.
- *Put durable intent in CLAUDE.md.* Rejected — CLAUDE.md is for behavioral rules; it bloats and is the wrong home for project content.

**Why this works.** Solves the wiki's drift failure structurally (git co-location), at the cost of three disciplined markdown files and an authoring habit — no machinery.

### Decision 13 — Intent is sticky alignment, not a per-feature document

**Context.** Treating intent as a per-feature artifact misses that project intent carries across features. A bugfix inherits existing intent almost entirely; a new feature mostly inherits and bends a piece; only greenfield establishes intent from nothing.

**Decision.** Intent is the *alignment* between what the human/team wants and what the agent comprehends, such that agent output is predictable and on-target — sticky, and inherited. The architecture/intent overview (Decision 12) is where sticky project intent lives. The amount of intent work a piece of work needs scales with how much it changes project intent — which is the same signal as capability-entry (Decision 2): a bugfix inherits and enters downstream; a new feature runs a real intent phase. The intent and design skills are invocable capabilities that read the durable overview to inherit context and update it (in-branch) when intent shifts; the downstream design and spec skills read the durable docs to set context and grill the human (the grilling technique) on gaps. The fresh-eyes technique doubles as the overview's quality check — "could a new team member understand the project from this?" is exactly cold-context comprehension.

**Alternatives considered.**
- *Intent as a per-feature PRD only.* Rejected — loses cross-feature stickiness.
- *Reconstruct intent fresh each feature from code.* Rejected — code shows current state, not the *why*; that's what the overview holds.

**Why this works.** Names intent as a state to maintain rather than a document to produce, and gives it a concrete durable home and a maintenance ritual tied to the work that changes it.

### Decision 14 — New and reshaped phases integrate with existing cross-cutting machinery

**Context.** Adding phases risks silently dropping cross-cutting functionality the shipped SDL already relies on. An audit of the existing flow surfaced the integration points.

**Decision.** Every new and reshaped phase must:
- **Append its section to the feature retrospective**, so the self-improvement loop ([[fbk-improve]]) sees the new flow. The retrospective stays throwaway but is consumed at feature close before squash.
- **Follow the [[stage-transition-protocol]]** (write to disk → summarize → compact → invoke next) and **honor [[mid-pipeline-entry]]** (the basis for capability-entry).
- **Preserve existing code-review machinery** — the reshaped code-review phase keeps its intent-extraction step and detector/challenger detection loop; quality-scan and test-review are *additive*, not replacements. The threat-model artifact and its project-model evolution are likewise preserved.
- **Define iteration caps** for the new phases (intent is human-driven like spec; the others get caps and escalate to the operator on exhaustion).

The state machine, the configuration layer, and the audit log are existing orchestration infrastructure that this cycle **does not touch** (a standing non-goal). Known downstream dependency: when the orchestration project wires phases together, the two new phases will need state-machine entries.

**Why this works.** Keeps the new phases first-class members of the existing pipeline rather than bolt-ons that the self-improvement loop and gates can't see.

### Decision 15 — Deferred out of this cycle

Items cut to keep the cycle to "markdown plus a small number of gate scripts," each pinned for possible future work:

- **Project-memory and the capture gate.** A durable cross-feature memory wiki with a closeout capture gate. Cut because it added an install-time contract and a class of failure modes (bootstrap collisions, drift, graceful-degradation surface) that multiple reviewers flagged as the heaviest cost. Replaced by the durable-artifact discipline (Decision 12). Preserved as [[project-memory-brainstorm]].
- **Architectural-review-meeting.** An iterative multi-persona design deliberation. Cut because it had only one consumer (failing the two-consumer rule), was the least-specified piece, and is an *authoring* pattern misfiled among closure-review patterns. Parked design in `deferred/`.
- **Mutation sampling.** Programmatic mutation of the implementation to prove locked tests have catching power. Cut because it is the one genuinely-new piece of *tooling* (not markdown/prompts), it's advisory (non-blocking), and the reading-based test-review already carries the core test-quality discipline. Enough to be its own feature.
- **Council migration to general role-agents.** Generalizing the council members (architect first, then the rest) into mode-agnostic role agents per Decision 4. Cut from this cycle to avoid dragging council changes into scope; the new general architect lays the foundation.

**Why this works.** Each deferral removes cost or risk without losing a load-bearing remediation learning; the reasoning is recorded here so a future cycle can pick any of them up with context.

### Related

- `prd.md` — the artifact whose decisions are recorded here
- the remediation validation experiment's lessons (external source material, operator's wiki) · [[validation-experiment-firebreak-postmortem]] — source material
- `design-manifest.md` — index of the design pages produced this phase
- [[project-memory-brainstorm]] — the deferred memory idea (Decision 15)
