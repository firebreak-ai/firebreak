# Refactored SDL — Product Requirements Document

## Vision

This project takes the disciplines that worked during the remediation cycle and applies them to Firebreak's general software-development lifecycle. The remediation cycle was set up to recover a codebase that had degraded past the point where in-place fixes were rational. Along the way it produced something more interesting than a clean rewrite: it produced a way of working that eliminated whole categories of AI-generated bugs at the design level rather than catching them at the code-review level. Eight of the twelve failure pattern classes that had marked the original code were structurally unable to appear in the rewrite. The remaining bugs changed character — small-radius spec deviations and test-fixture issues instead of confident hardcoding and happy-path optimism.

The strategic frame is prevention versus recovery. The remediation flow is the recovery path: it exists for codebases that have already crossed the threshold where the cost of remediation exceeds the cost of a full rewrite. The general SDL is the prevention path: it is where everything else gets built. If the prevention path carries the remediation disciplines, the threshold becomes much harder to reach in the first place. Greenfield work and brownfield work that sits on a firm foundation both produce cleaner code through the same authoring and interaction practices that produced the clean remediation substrate. The two flows together cover the full lifecycle of a codebase — prevention for what is being built fresh or maintained well, recovery for what has already crossed the line.

## Problem statement

Today's general SDL has three concrete gaps that the remediation cycle exposed.

The first is that there is no front-of-pipeline phase for extracting intent. The current flow begins at the spec — a document that answers "how" without a separate, prior step that pins down "what" and "why" in the operator's own words. The remediation cycle made the value of a separate intent phase obvious. Letting an interviewer agent draw out what the operator actually wants, in plain language, before any structural commitments were made, was the single change with the largest downstream effect. The general SDL has no equivalent.

The second is that spec authoring carries too much load. When the remediation cycle ran the spec phase on top of validated intent and architecture artifacts, the spec produced an 1800-line consolidated document that felt thinner and less faithful than the upstream artifacts it was summarizing. The spec's role had collapsed into translation rather than creation. The general SDL has the same overload problem in a different form: the spec is being asked to do intent work, design work, and how-to-build-it work all at once, and the quality of each suffers.

The third is that breakdown tries to do two different cognitive jobs in one head. Identifying the seams of the work — what carving lets parallel agents proceed without stepping on each other — is one job. Writing the actual work units along those seams is another. The current breakdown skill collapses both into a single agent context, and the result degrades as the work gets larger. The remediation cycle made it clear that with a precise enough spec, the work can be carved into vertical slices and each slice's work units written in a form a less-familiar agent could follow — but only if the seam-identification and unit-writing steps are separated from each other.

A fourth concern is more diffuse but no less real. Several of the remediation wins came from authoring and interaction practices that are not tied to any particular phase — simple language understandable to a non-coder technical lead, descriptions of features in prose instead of bare identifiers, capability framing instead of current-shape framing, an interview-before-drafting ethos, a fresh-eyes comprehension check at the end of any phase that produces design. These practices are not in the asset authoring rules or the project's CLAUDE.md today. They were maintained by hand during the remediation cycle. To carry forward they need to be encoded.

## Goals and non-goals

### Goals

- Add a dedicated intent phase to the front of the SDL, producing a product requirements document and structured attachments that downstream phases consume directly. The intent phase reads the project's durable architecture/intent overview to inherit existing intent, and updates it when a feature shifts project intent.
- Add a dedicated design phase, separate from the spec phase, producing architecture artifacts that the spec phase then consumes. Design pages live in the feature directory as ephemeral working memory; the enduring decisions the phase makes are appended to the project's durable decisions log, and any shift in project shape is reflected in the durable architecture/intent overview. A design manifest in the feature directory indexes the design pages so the design gate can verify them.
- Narrow the spec phase to "how mapped to what and why" so it stops doing intent work and design work as a side effect. The spec phase's grilling is narrowed correspondingly — it grills on approach, integration, module-touch, and contracts, not on intent. The spec declares each work slice's test discipline mode so breakdown knows which slice shape to produce.
- Reshape the breakdown phase to carve the spec into vertical slices, with a per-slice work-unit structure determined by the slice's test discipline mode. Each shape's instructions are loaded by progressive disclosure once a slice is classified, so an agent building one slice isn't carrying the rules for the other three. Catching power is judged by the test-review-by-reading step; new-contract slices additionally use the plain red check (tests fail against an empty implementation). A test-lock manifest records accepted test files' paths and sha256 hashes so implementation work units cannot modify locked tests — preserving the existing hash-lock mechanism.
- Make scope-appropriateness a matter of capability-entry rather than complexity classification. The six phases are independently invocable capabilities; the human enters the chain at the point that fits the work, and nothing forces the full chain. There is no complexity-classification eval and no recorded tier tag in this cycle — the six-tier definitions remain in the glossary as shared vocabulary, but no skill or gate acts on them.
- Extend the code-review phase to invoke a top-five quality scan after the existing bug-finding pass. The scan surfaces and ranks five quality opportunities. It does not auto-fix; what to do with the surfaced list is a separate decision the caller makes. The code-review phase also runs a final test-review pass that verifies the test-lock manifest's hashes are intact and that the locked tests still exercise the behavior they claim, given the final implementation. The existing bug-finding machinery — intent extraction and the detector/challenger detection loop — is preserved; the quality scan and final test-review are additive.
- Define phase gates that share a hybrid pattern — mechanical structural checks plus a semantic anchor on a verifiable artifact (typically a technique skill's output). The hybrid pattern positions the SDL for future hook infrastructure: as hooks come online, the operator-confirmation parts of the semantic anchors migrate to hook-enforced checks and the gates become more mechanical over time without changing their position in the flow.
- Extract grilling, fresh-eyes comprehension check, top-five quality scan, and test-review as reusable technique skills. Phase skills compose them rather than re-implementing them. The extraction criterion: a technique earns its own skill when at least two real consumers exist, where the human operator counts as a consumer if there is a significantly useful and common scenario for invoking the technique outside any ceremony.
- Move the always-on disciplines from the remediation cycle into the asset authoring rules and the project's CLAUDE.md so every agent on every task carries them. The always-on disciplines are simple language, descriptions over identifiers, capability framing, interview before drafting, and structural-principles awareness. (CLAUDE.md carries behavioral rules of this kind; it is not a home for project intent — that lives in the durable architecture/intent overview.)
- Establish a lightweight durable-artifact discipline for the content that should outlive a feature: the glossary, an append-only decisions log, and a living architecture/intent overview. These are plain git-tracked markdown, updated in feature branches and merged with the change they describe. Spent scaffolding (spec, breakdown, manifests, reports, retrospective) stays throwaway in the feature directory.
- Give the new intent and design phases context-isolated worker agents under the rule that agents encode expertise and skills encode mode: a new requirements/product author for intent, a new general-purpose senior architect for design, reusing existing agents (spec author, test reviewer, council) where a role-appropriate definition already exists.

### Non-goals

- This project does not build complexity-classification functionality. There is no tier eval and no recorded tier tag; routing off complexity is a later project. The tier definitions stay in the glossary as vocabulary only.
- This project does not touch hooks, the command-line tooling around the SDL, the configuration layer, the audit log, or the state machine that ties skills together. Those are a separate orchestration project. The hybrid gate pattern is designed to consume hook infrastructure when it arrives, but does not build it. (Known downstream dependency: when that project wires phases together, the two new phases will need state-machine entries.)
- This project does not design the classifier mechanism for the cross-module versus decomposed boundary. That problem belongs to the dispatch project, and this project consumes whatever classifier the dispatch project eventually produces.
- This project does not build AST-based schema extraction tooling. The PRD and spec sections that carry interface contracts are structured to be ready for AST-extracted schemas when the tooling exists, but the tooling itself is a near-term follow-on project, not part of this cycle.
- This project does not build a durable cross-feature memory *system*. The durable-artifact discipline is plain git-tracked markdown with no tooling, index, or install contract. A heavier project-memory layer is a deferred future feature, captured as a brainstorm.
- This project does not modify the council or the other shipped council agents. The general architect is created standalone; migrating the council members onto the agents-encode-expertise model is pinned for future work.
- This project does not build mutation sampling. Programmatic mutation of the implementation to prove catching power is deferred as its own future feature; the reading-based test-review carries the core test-quality discipline in this cycle.
- This project does not treat spec redundancy as a separate concern to solve. The concern dissolves once the spec phase has a narrower job and the intent and design phases carry the work that used to bloat the spec.

## Use cases

The primary user is the operator running a feature or project through the Firebreak SDL. The operator is a technical lead in spirit — comfortable making product and architecture decisions, less comfortable writing code at the level of detail the agents produce, and reliant on the agents to translate between intent and implementation.

The secondary users are the agents themselves, executing skills along the SDL. They are users of the new artifacts as much as the operator is, and the design has to work for them: skill transitions need to flow seamlessly without the operator orchestrating handoffs by hand, and the artifacts each phase produces need to be in a form the next phase can consume directly.

Three scenarios cover the relevant ground.

**Greenfield feature.** The operator has an idea for a feature in a project that does not yet have a structure to fit it into. The intent skill takes the operator through an interview, drawing out what the feature is, what it does, why it matters, who depends on it. The design skill takes the intent artifacts and proposes a structural shape — modules, dependencies between them, contracts at each seam — and writes those artifacts into the feature directory, indexed by a design manifest, while recording the enduring decisions in the durable decisions log. The spec skill takes the design and the intent and writes how the work will be built — tech stack choices, file-level organization, integration approach, testing strategy with declared test discipline mode per slice, acceptance criteria mapped back to what the operator said they wanted. The breakdown carves the spec into vertical slices and writes the work-unit structure each slice's test discipline mode calls for. Implementation runs against locked tests. Code review and the final test-review pass close the cycle, after which the feature directory is squash-merged away and the durable docs merge with it.

**Brownfield work on a firm foundation.** The operator wants to extend or modify code that is well-structured to begin with. The intent phase reads the durable architecture/intent overview to inherit what the project already is, then captures the delta. The same flow applies, with the test discipline modes carrying most of the brownfield-specific texture. Slices that change an implementation while keeping its contract intact run as contract-preserving slices — existing tests cover the contract, get locked, and the implementation changes against them. Slices that evolve a contract run as contract-evolving slices — some tests survive, some retire, some are newly written. Existing schemas the work has to honor are surfaced as constraints in the intent phase; new schemas come from the design phase. Brownfield work on a foundation that is *not* firm is out of scope here — it routes to the remediation flow.

**Small change inheriting existing intent.** The operator has a bugfix or a one-line change in an established project. It inherits the project's intent almost entirely and changes none of it, so the heavy front of the chain adds no value. Under capability-entry the operator starts downstream — at the spec, or lighter still, conversationally ("here's the bug; how would we fix it?" → "yes, do that"). Nothing forces an intent or design phase for work that establishes no new intent. This is the same shape as the existing corrective/fast-track workflow.

## Functional requirements

The system is a sequence of skills. Each skill owns one phase. Each phase consumes the previous phase's artifacts and produces its own. Some skills are *phase skills* that orchestrate a stage of the SDL. Others are *technique skills* — small, reusable capabilities that phase skills (and humans, ad hoc) compose. Phase gates close out each phase before the next begins; they share a hybrid pattern of mechanical structural checks plus semantic anchors on verifiable artifacts.

The phases are invocable capabilities, not a forced chain — see "Capability-entry" below. The behavior inventory attachment to this document lists the per-behavior detail; this section gives the shape of each phase, the gates between them, and the disciplines they carry.

### The intent phase

The intent phase produces a product requirements document and a behavior inventory. It begins by reading the project's durable architecture/intent overview, so it inherits the existing project intent rather than re-deriving it; for an established project most intent is inherited and the phase captures only the delta. When the work has to honor existing schemas — file shapes, API contracts, message formats — those existing schemas appear in the product requirements document as constraints. When the work introduces new contracts, the intent phase describes them only at the meaning level; their shape is the design phase's job. When a feature shifts project intent, the durable overview is updated in the feature branch so it merges with the change.

The skill that owns this phase interviews the operator before drafting anything. The interview is not a checklist of questions; it is a conversation aimed at extracting what the operator actually wants the system to do and why. The skill composes the grilling technique skill when ambiguity needs to be closed, and composes the fresh-eyes comprehension check at completion. It drafts in small batches and checks before moving on. Drafting is delegated to a context-isolated requirements/product author agent.

The artifacts are a single canonical markdown product requirements document and a structured behavior inventory in YAML, with interface contracts attached when existing schemas constrain the work.

### The design phase

The design phase produces architecture artifacts: a list of modules, a graph of dependencies between them, a prose contract for each module describing what it does and what it exposes, a typed contract for each module's boundary that downstream implementation will compile against, and a decomposition rationale that explains why this shape over alternatives. New schemas the work introduces are designed here. Significant decisions that emerge are appended to the durable decisions log.

The design skill writes its design pages into the feature directory under a `design/` subdirectory, with a *design manifest* that indexes every design page produced. The design pages are ephemeral working memory — they sharpen the spec and are deleted at squash-merge. What persists is the durable record: the enduring decisions in the decisions log, and any change to project shape reflected in the architecture/intent overview. Drafting is delegated to a context-isolated general-purpose senior architect agent.

The skill carries the structural principles explicitly: loose coupling, single responsibility, dependency inversion, deep modules with small interfaces, and KISS as the tiebreaker when multiple designs satisfy the others. It composes the grilling technique skill on structural choices and the fresh-eyes comprehension check at completion. (An iterative multi-persona design deliberation was considered and deferred — see the decision spine; the design phase ships with grilling plus fresh-eyes.)

### The spec phase

The spec phase answers "how" mapped to the product requirements document's "what" and "why" and the design phase's structural shape. It reads the durable docs and the upstream feature artifacts to set context, and grills the operator (via the grilling technique) where the inherited intent or design is thin. Its content is narrower than today: tech stack choices, file-level organization, the integration approach, the testing strategy, the module-touch policy, declared seams and interface contracts at those seams, the test discipline mode for each anticipated slice, and acceptance criteria mapped back to the product requirements document. It does not re-derive intent, and it does not re-decompose the design. When the upstream artifacts already contain the relevant content, the spec links to them rather than restating them.

The testing strategy section in particular carries the test discipline signal — for each anticipated slice (or for the work overall), the spec declares whether the slice is new-contract, contract-preserving, contract-evolving, or cross-cutting. The spec also names cross-cutting test needs explicitly: which seams require dedicated tests beyond per-slice coverage. This signal flows to the breakdown phase.

The spec phase composes the grilling technique skill, but narrowed to "how" questions — module ownership, integration boundaries, scope of touch, naming, test approach. It does not re-grill the intent or the structural shape. Drafting continues to use the existing spec author agent.

### The breakdown phase

The breakdown phase reads the spec and design and produces a set of vertical slices. Each slice's work-unit structure depends on the slice's test discipline mode, declared in the spec. Once a slice is classified, the breakdown agent loads only that shape's instruction leaf (progressive disclosure), so it isn't reasoning about three irrelevant disciplines while building one slice.

A slice is one end-to-end path through the changed modules — one capability that can be tested and verified on its own. The spec's seams, interface contracts, and testing strategy tell breakdown where the slice boundaries are and which discipline applies to each. Small features have one slice; large features have many.

The four test discipline modes:

- **New-contract slice.** A new capability is being added; no tests cover it yet. Work-unit pair: test-creation and implementation, with a test-review checkpoint between them (the checkpoint is a review action, not a counted work unit). Tests are expected to fail until the implementation lands (the plain red check).
- **Contract-preserving slice.** Implementation is changing but the contract isn't. Existing tests already cover the contract and pass. The authored work is the implementation change, then verification that the locked tests still pass; the existing test-review process runs first over all tests covering the module (validating and hash-locking them). A coverage gap surfaced by that review is resolved by adding the needed tests — the slice stays contract-preserving.
- **Contract-evolving slice.** The contract itself is changing. Some existing tests survive; some retire; some new tests are needed. Work-unit shape: test-creation for the new behavior plus a retired-tests list for behavior the new contract drops, followed by implementation. The existing test-review process (over all tests covering the module) validates surviving and new tests and confirms the retirements; hash-locking applies to surviving and newly written tests.
- **Cross-cutting test slice.** Tests at seams or for behaviors spanning multiple other slices. Test-only: a test-creation unit with a test-review checkpoint, no paired implementation (the implementation exists across other slices already).

Every slice exercises a *test discipline pass* before implementation. The pass takes different shapes per mode, but the property it establishes is catching power — that the tests actually exercise the behavior they claim. In this cycle catching power is judged by the test-review-by-reading checkpoint — the existing test-review process run over all tests covering the changed module(s), not just the new or modified ones — with new-contract slices additionally using the plain red check. (Programmatic mutation sampling as an empirical catching-power proof was considered and deferred — see the decision spine.)

Tests accepted at the test-review checkpoint are recorded in the *test-lock manifest*, an artifact in the feature directory. Each entry pairs a test file's path with its sha256 hash, plus the slice and test-discipline mode it belongs to. Implementation work units cannot modify locked test files; hash verification at completion catches any tampering. The lock applies whether the test is newly written or pre-existing.

Work units are sized so a less-familiar agent could execute them. When breakdown cannot write work units that small, that is treated as a signal the spec is incomplete — breakdown bounces back to the spec phase rather than pushing the gap forward.

Breakdown is internally split into a slice-identification step followed by per-slice work-unit authoring. The second step is parallelizable across slices.

### The code-review phase

The code-review phase runs its existing bug-finding pass on the change — intent extraction followed by the detector/challenger detection loop — unchanged. After that pass, it invokes the top-five quality-scan technique skill. The scan surfaces five ranked code-quality opportunities — patterns the code could express better, duplication that should be consolidated, structural improvements that fall short of bugs but would meaningfully improve the substrate. The scan is surface-only; what to do with each opportunity is a separate decision the operator makes after reading the list.

The phase also runs a *final test-review pass*. The test-reviewer reads the final state of the code, verifies the test-lock manifest's hashes match the current state of every locked test file (no tampering crossed implementation), checks that no new tests were added that shadow the locked ones, and confirms by reading that the locked tests still exercise the behavior they claim given the final implementation (the drift check). Drift is surfaced as a finding rather than a hard gate failure; the operator decides whether to strengthen the tests in this cycle or defer.

### The phase gates

Gates close out each phase before the next phase begins. They share a hybrid pattern: mechanical structural checks plus a semantic anchor on a verifiable artifact (typically a technique skill's output).

- **Intent gate.** Mechanical: PRD and behavior inventory exist with required structure; existing schemas referenced where applicable; grilling log present. Semantic: anchored on the fresh-eyes comprehension check's output. Operator confirms intent capture matches.
- **Design gate.** Mechanical: design manifest exists; bidirectional check (every manifest entry resolves to a real design page in the feature directory; every design page in the directory appears in the manifest); decomposition rationale present; new schemas designed where the work introduces them. Semantic: anchored on fresh-eyes scoped to "could a spec author write the spec from this design, and could a downstream breakdown agent eventually carve slices from it?"
- **Spec gate.** Mechanical: required sections present (tech stack, file organization, testing strategy, module-touch policy, declared seams and contracts, per-slice test discipline modes); every behavior in the inventory covered by at least one slice; design pages referenced by the spec exist; grilling log present. Semantic: anchored on the council review (the existing multi-persona spec review) scoped to "could a breakdown agent identify the slices and write executable work units from this spec?" Operator confirms the spec does not duplicate intent or design content.
- **Breakdown gate.** Lighter than the others. Mechanical: per-slice work-unit structure matches the slice's declared test-discipline mode (the structure each mode calls for, per the slice-shapes definitions); the pre-lock test-review verdict gated lock application; cross-references resolve; no unresolved bounce-back markers. Operator confirms breakdown ran cleanly. No fresh-eyes pass — the bounce-back mechanism is the executability check.
- **Implementation gate.** Mechanical: per-task `TaskCompleted` hook runs tests and linter; test-lock hashes verified unchanged per task; per-wave verification gates pass. No dedicated semantic anchor — the locked tests are the contract; semantic review happens downstream at code-review.
- **Code-review gate.** Heaviest mechanical load. Mechanical: bug-finding pass complete; top-five quality scan complete; final test-review pass complete; test-lock manifest hashes all match current state; no shadow tests added. Operator triages findings and quality opportunities.

The hybrid pattern positions the SDL for the deterministic future. As hook infrastructure comes online, the operator-confirmation parts of the semantic anchors migrate to hook-enforced checks. The gates get more mechanical and less operator-dependent over time without changing their position in the flow.

### Capability-entry and scope-appropriate use

The six phases are independently invocable capabilities. Scope-appropriateness is the operator's judgment about where to enter, not a classifier's output:

- A large or unfamiliar change starts at intent and walks the whole chain.
- A change in an established project that adds or bends some intent can start at design or spec, inheriting the rest from the durable docs.
- A small change that establishes no new intent — a bugfix, a one-line correction — can start at the spec or go lighter still, conversationally, never formally invoking the upstream phase skills.

Nothing forces the full chain. When a phase is invoked directly, it follows the existing mid-pipeline-entry protocol: it checks that its prerequisites hold (the prior phase's gate is satisfiable) and, if not, reports what's missing and offers to run the upstream phase — rather than blocking. Firebreak suggests the next step; the operator decides. The amount of intent and design work a piece of work warrants scales with how much project intent it changes (see "Intent as sticky alignment").

### Intent as sticky alignment

Intent is the alignment between what the operator/team wants and what the agents comprehend, such that agent output is predictable and on-target. It is sticky: it carries across features. A bugfix inherits the project's intent almost entirely; a new feature mostly inherits and bends a piece; only greenfield establishes intent from nothing.

The durable architecture/intent overview is where sticky project intent lives — a plain-language document that orients a new team member or a cold agent to what the project is and how it works. The intent and design phases read it to inherit context and update it when intent shifts; the spec phase reads it (and the rest of the durable docs) to set context, grilling the operator where the inherited intent is thin. The fresh-eyes technique doubles as the overview's quality check: "could a new team member understand the project from this?" is exactly the cold-context comprehension fresh-eyes performs.

### The technique skills

Four reusable technique skills are introduced or formalized by this project. Each does one thing well, has multiple real consumers, and can be invoked either by phase skills as part of ceremony or by the operator directly outside any flow.

- **The grilling technique skill.** Reflects back what was said, asks targeted questions, surfaces ambiguity, gets explicit confirmation before recording a decision. Consumed by the intent skill (intent grilling), the design skill (design grilling), the spec skill (how grilling), and the operator directly when working through any unresolved decision.
- **The fresh-eyes comprehension check technique skill.** Hands an artifact to a context-clear reviewer, asks "does this stand on its own?", surfaces what does not. Consumed by the intent and design gates as the semantic anchor, by the architecture/intent overview's quality check, and by the operator directly when checking any artifact for cold-reader clarity. The council (the existing multi-persona spec review) is a related cold-review pattern used at the spec gate; it is not rebuilt here.
- **The top-five quality-scan technique skill.** Surfaces and ranks the top five code-quality opportunities in a given diff or scope. Surface-only; fixing decisions live with the caller. Consumed by the code-review phase as part of ceremony and by the operator directly when running an ad-hoc quality assessment on any code.
- **The test-review technique skill.** Validates test quality at two checkpoints — catches inlined implementations, weak assertions, trivial coverage by reading; confirms hash-lock integrity and checks for shadow tests at the final pass. Consumed by the breakdown phase (pre-lock, where its verdict gates lock application) and the code-review phase (final drift check), and invokable by the operator ad hoc on any code. The existing test-reviewer agent and /test-review skill are the basis; the invocation contract widens to handle the modes the new SDL needs.

The extraction criterion: a technique earns its own skill when at least two real consumers exist. The human operator counts as a consumer if there is a significantly useful and common scenario for invoking the technique outside any ceremony. Techniques that are ceremony-only and have only one ceremony consumer stay embedded in their phase skill.

### Worker agents

Phase skills delegate drafting and review to context-isolated worker agents. The rule is that an agent definition encodes a *role and expertise*, while the skill it pairs with supplies the *mode and task* — so one definition can serve multiple skills and modes.

- **Intent → new requirements/product author.** Plain-language, capability-framed, interview-grounded; composes grilling for ambiguity. No existing persona fits — the roster has nothing product-facing.
- **Design → new general-purpose senior architect.** Used in authoring mode by the design skill. Written as a superset the existing council architect can later collapse into; the council migration is deferred.
- **Spec → existing spec author.** Unchanged.
- **Fresh-eyes → thin new cold reviewer.** Its value is being uncontaminated, so it carries no specialist lens.
- **Quality-scan → the existing code-review detector, adapted.** Both surface issues; the detector's definition adapts to quality opportunities.
- **Test-review → existing test reviewer. Council → existing council members.** Unchanged.

### The always-on disciplines

The disciplines that apply across every phase live in the asset authoring rules and the project's CLAUDE.md. They are:

- **Simple language.** Every artifact, every conversation, every agent-human exchange uses language a non-coder technical lead could follow. Jargon is used only when it adds clarity rather than removing it.
- **Descriptions over identifiers.** In prose meant for human consumption, features and components are referred to by name and short description rather than by bare identifier. Identifiers stay in structured artifacts where machines need them.
- **Capability framing.** Artifacts describe what the system does (its capability) rather than what its current code happens to look like (its shape). The exception is when a specific structural choice is the point being made.
- **Interview before drafting.** Phases that draw out the operator's intent start with conversation and confirm before drafting. The rev count is the diagnostic — if the same artifact gets rewritten three times, the interview wasn't done.
- **Structural principles awareness.** Phases that produce structural artifacts carry loose coupling, single responsibility, dependency inversion, deep modules, and KISS as conscious considerations.

These are authoring rules, not phase steps. They apply continuously, not at gates. The fresh-eyes comprehension check picks up most failures of these rules as part of its work; the rules themselves stay in CLAUDE.md so every agent on every task carries them.

### The durable-artifact discipline

Most SDL artifacts are spent scaffolding — the spec, the design pages, the design manifest, the breakdown task list, the test-lock manifest, the reports, the retrospective. They live in the feature directory during work and are deleted at squash-merge. A small, curated set of artifacts is *durable* instead, because it carries value across features:

- **Glossary** — aligned terminology. Edited in place.
- **Decisions log** — the *why* behind enduring choices. Append-only, chronological.
- **Architecture/intent overview** — what the project is and how it works, now. Living, edited in place, kept to onboarding length.

The durable set is plain git-tracked markdown in the repo's normal doc locations — no tooling, no index, no install contract. It is governed by a comprehensibility discipline: persists in git, doesn't accrete into clutter, stays simple-language and bounded with intuitive names and folders, comprehensible to both human teams and cold agents. Durable docs are **updated in the feature branch and merge into main with the change they describe**, so branch docs describe the branch and main docs describe main — they stay as in-sync as the code because they are part of the same change. A stale overview shows up in the diff as "this PR changed behavior but didn't touch the overview"; parallel edits resolve as ordinary git merge conflicts. Git co-location is the mechanism that keeps the durable docs honest.

## Non-functional requirements

**Operator time.** The intent phase should complete in a single working session for a typical feature. If the operator has to break the interview across multiple sessions, the skill must resume cleanly without losing context — by reading the existing artifacts at the start of the next session and asking the operator where to pick up.

**Skill transitions.** Moving from one phase to the next must not require the operator to manually pass artifacts or context. Each skill knows what its predecessor produced and reads it directly. The operator's role at a transition is to decide whether to proceed, not to orchestrate the handoff.

**Artifact inspectability.** Every artifact every phase produces is a file the operator can open, read, and edit by hand. There is no opaque state, no database, no internal-only representation. If the operator wants to correct something between phases, the artifact is plain markdown or plain YAML.

**Durable-doc comprehensibility.** The durable docs must stay readable by both humans and cold agents: simple language, bounded file length, intuitive names and folder structure. The architecture/intent overview in particular is held to "a new team member could orient from this" — enforced by the fresh-eyes check.

**Backward compatibility.** Existing skills not modified by this project continue to work. Specs already in flight under the current SDL continue through the current SDL — the new shape does not retroactively apply.

**Gate determinism over time.** Today's gates are hybrid. Each gate's mechanical portion should be implemented in a way that allows future hook infrastructure to subsume the operator-confirmation portions without restructuring the gate. The mechanical checks are the durable surface; the operator confirmation is the temporary scaffolding.

## Edge cases and failure modes

**The intent phase doesn't converge.** The operator and the interviewing agent keep rewriting the same artifact. The diagnostic is the rev count — the skill surfaces it explicitly and prompts the operator to step back and ask whether the underlying intent is unclear, not just the prose. If the fresh-eyes check repeatedly returns ambiguity, the skill surfaces that the ambiguity is real and asks the operator to decide whether to resolve it now or accept it as an open question the downstream phase will inherit.

**The design phase can't honor the intent cleanly.** The constraints from existing schemas or external dependencies force the design into a shape that doesn't fit the intent, or two capabilities the intent describes are hard to put under loose coupling given the constraints. The skill surfaces the tension explicitly rather than choosing silently. The operator decides whether to relax the intent, renegotiate the constraint, or accept the tension.

**The spec phase finds the design isn't decisive enough.** The spec author finds itself making design decisions because the design phase didn't pin them down. The right move is to send the work back to the design phase rather than absorbing the decisions into the spec. The skill is explicit about this and offers to invoke the design skill again rather than continuing.

**A phase is entered directly but its prerequisites are missing.** The operator invokes a downstream phase (capability-entry) but the upstream artifacts or durable context it relies on aren't there. The phase runs the mid-pipeline-entry check, reports specifically what's missing, and offers to run the upstream phase rather than proceeding on a thin foundation.

**Breakdown can't write executable work units.** The breakdown phase tries to write a work unit for a slice but cannot produce one a less-familiar agent could follow. This is treated as a signal that the spec is incomplete. Breakdown surfaces the gap, names what is missing (which contract, which boundary, which module-touch policy, which test discipline declaration), and offers to invoke the spec phase to fill the gap rather than proceeding with unclear units.

**Test review on a contract-preserving slice surfaces a gap.** Reviewing all tests covering the module shows they don't actually have catching power against the contract being preserved. The slice handles this by adding the needed tests for the uncovered part of the contract; it stays contract-preserving (adding tests does not change the contract). The same test-review process catches and resolves the gap.

**Test-lock hash drift detected at code review.** A locked test file's current hash doesn't match the manifest. Implementation modified the test, even though the work unit instructions said not to. The code-review gate fails. The work goes back to the implementation step with a clear "do not modify locked tests" reinforcement; tests are re-verified against the original locked state.

**A locked test drifts out of relevance.** The implementation was restructured such that a locked test no longer exercises the path it claims, even though its hash is intact. The final test-review pass catches this by reading and surfaces it as a finding; the operator decides whether to strengthen the test now or defer.

**The durable overview goes stale.** A feature changes behavior but the branch didn't update the architecture/intent overview. Because the overview is git-co-located, the gap is visible in the PR diff (behavior changed, overview untouched) for a human or agent reviewer to catch, rather than drifting silently in a separate store.

## Dependencies

- The existing Firebreak SDL infrastructure — the current skills, the existing artifact conventions, the gate scripts, the retrospective pattern, and the self-improvement loop that consumes retrospectives.
- The existing code-review machinery — intent extraction and the detector/challenger detection loop — which the reshaped code-review phase preserves and builds on.
- The existing threat-model artifact and its project-model evolution protocol, preserved unchanged.
- The dispatch complexity tier taxonomy in the project glossary — retained as shared vocabulary; this cycle does not emit or act on tier tags.
- The existing remediation flow — work that crosses the remediation threshold routes there unchanged.
- The existing global grilling skill — modified to make reflect-back-to-confirm explicit, otherwise untouched. Becomes the technique skill that phase skills compose.
- The existing /test-review skill and test-reviewer agent — invocation contract widens to handle the new SDL's checkpoints; existing functionality preserved.
- The existing spec author, code-review detector, and council agents — reused (the detector adapted for quality-scan).
- The asset authoring rules in the project's fbk-docs directory — modified to absorb the always-on disciplines.
- The project's CLAUDE.md — modified to surface the always-on behavioral disciplines at session start.
- The project's durable docs — the glossary, the decisions log, and the architecture/intent overview — which the intent, design, and spec phases read and (for the first two) update.

A near-term follow-on dependency that this cycle is structured to consume when it exists: AST-based schema extraction tooling. The product requirements document and spec sections for interface contracts are shaped to be populated from AST extraction once the tool is built. Until then, existing schemas are referenced or hand-described.

## Success metrics

The qualitative signal is the most important one. Code produced through the new SDL should resemble the remediation clean-substrate signature — small-radius spec deviations rather than confident hardcoding, structural elimination of failure classes rather than catch-and-fix at review time. A diff-by-diff comparison between work produced through the new SDL and work produced through the old SDL should show fewer of the architectural-blindness pattern classes that the remediation validation experiment catalogued.

The operational signals tell whether the new shape is being used at all:

- The intent skill gets invoked at the start of new feature work rather than skipped, and reads the durable overview to inherit existing intent.
- The design skill produces design pages that the spec skill cites rather than restates, and records enduring decisions in the durable decisions log.
- The spec skill produces specs that are meaningfully shorter than today's specs and declare a test discipline mode per slice.
- Breakdown produces vertical slices with work-unit shapes matching their test discipline modes; bounces back to spec when work units cannot be written executably.
- Test-lock manifests are produced and verified at the code-review gate.
- The code-review top-five scan runs on every review, and the existing detection loop still runs ahead of it.
- The technique skills get invoked by phase skills and by the operator directly.
- Every new and reshaped phase appends its section to the retrospective, so the self-improvement loop sees the full new flow.
- The durable docs are updated in feature branches and merge with the change; the architecture/intent overview stays current rather than drifting.
- Feature directories are cleaned up at squash-merge and the main branch does not accumulate spent ceremony products.

The strategic signal is whether the threshold-crossing rate drops over time. Projects that go through this SDL should reach the remediation-feasibility threshold less often than projects that did not. This signal is slow and indirect, but it is the one that matters most — it is the prevention-vs-recovery distinction made concrete.

## Open questions

- The exact shape of the interview prompts in the new intent skill. The remediation intent prompt is a strong starting point, but the prompts in the new skill will need to handle features that are not single-module rewrites, and the read-the-overview-to-inherit-intent step.
- The exact format of the per-slice work-unit handoff from the spec to the breakdown agents. Slices are derived from the spec's seams and contracts, but the precise artifact each breakdown sub-step receives needs design work.
- The exact maintenance mechanism for the architecture/intent overview — how strongly the phases enforce updating it, and whether the fresh-eyes check plus diff-visibility is enough to keep it from going stale, or whether a lighter explicit prompt is also needed.
- Whether the append-only decisions log earns its keep in practice, or whether enduring decisions are better captured inside the architecture/intent overview. This cycle treats the separate decisions log as an experiment.
- The set of code-quality patterns the top-five scan looks for. A starting set can be pulled from the remediation validation experiment's pattern taxonomy, but the scan will improve as it accumulates examples.
- How the gates' mechanical portions are implemented in a way that's ready to be subsumed by future hook infrastructure. Today they run as scripts the gate-step invokes; tomorrow they may run as hooks fired by the state machine.
