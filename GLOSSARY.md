# Glossary

Canonical source of agreed terminology and definitions for the firebreak repo.

Every term used in firebreak artifacts shapes downstream agent behavior. Misleading or value-laden terminology steers the model in unintended directions; even subtle priors (virtue, judgment, expectation) propagate through agentic reads. This document captures the agreed meaning of each term *and* the priors it activates in a context-empty agent reading it for the first time.

## Authoring principles

- Each entry names the term, gives a one-sentence agreed definition, and notes the LLM priors it activates (what a fresh agent would assume).
- Where a term loads a value judgment, state whether the loading is intended (e.g., "this term is intentionally value-loaded to signal X") or accidental and tolerated (e.g., "term is retained for historical reasons; downstream readers should weight the value-loading at zero").
- New terms enter the glossary when a spec or context asset introduces them. Spec-review and asset-authoring gates verify that newly-introduced terms have entries.
- Prefer renaming over annotating when a term is actively misleading and not yet load-bearing across the repo.

## Entries

### wave

**Definition**: a unit of parallel tasks within a structured workflow. The size and shape of a wave is determined by task dependencies — a wave with no internal cross-dependencies can run all its tasks in parallel; a wave whose tasks depend serially on each other runs them one at a time. The surrounding context determines which kind of wave is being discussed.

**LLM priors activated**: generic workflow/scheduling concept; minimal value-loading. Risk of conflation between distinct wave instances is bounded by the surrounding text, which always names the specific wave instance.

**Usage examples in firebreak**:
- `/fbk-implement`'s per-wave verification — a wave is a task-batch within a single feature's implementation, indexed by `task.json`'s `wave_id`
- Remediation flow's foundation-first wave order — a wave is a module group within a cycle, ordered by the module dependency graph (see `ai-docs/remediation-flow/remediation-flow-overview.md` §"Cycle and wave order")

Both uses are valid instances of the same underlying concept. The wave term is reserved for "unit of parallel tasks"; no renaming is needed to distinguish the two contexts because their surrounding text always disambiguates.

---

### dispatch

**Definition**: The planned automation layer for firebreak. Provisions Firebreak's quality pipeline for scheduled, cron-style work that doesn't originate from a live human session. Deferred until the four code-quality layers ship first so automated runs inherit the quality gates rather than retrofit them.

**LLM priors activated**: Generic computer-science term — event dispatch, message dispatch, system dispatcher. Risk: confusion with low-level dispatcher mechanisms. In firebreak context, dispatch refers specifically to the automation layer that orchestrates pipeline runs against a tier × messiness classification.

---

### dispatch complexity tier

**Definition**: One of two orthogonal axes used by dispatch to classify a scheduled job (the other is the messiness axis). Tier classifies the *scope* of a change — how much code area is touched and what shape the work has — which drives decomposition, agent count, and whether design judgment is required before implementation. Six tiers from single-touch through architectural-replace.

**LLM priors activated**: "Tier" activates generic hierarchical/ranked priors. Risk: assumption that tiers are linear quality levels rather than discrete shape categories. The six tiers are discrete shapes; "higher" tiers do not mean "harder" or "more important" in a generic sense — they mean "this specific shape of work."

**Determined by**: context volume, decomposition need, multi-session need, design judgment need.

**Not determined by**: subject-matter labels, greenfield-vs-brownfield, remediation-vs-new-work. These are orthogonal to tier.

---

### single-touch

**Definition**: A dispatch complexity tier. A change consisting of one read, one edit, one spot. Provisions one prompt, one agent, no task tracking.

**LLM priors activated**: Risk: "single" may activate "trivial" or "easy" connotations. Single-touch is not necessarily easy — it is simply small in scope. A single-touch change may still require care.

---

### single-module

**Definition**: A dispatch complexity tier. A change with multiple edits, all within one module. Provisions one agent with task tracking on.

**LLM priors activated**: Neutral. The term "module" is project-relative — what counts as a module depends on the codebase being worked in.

---

### cross-module

**Definition**: A dispatch complexity tier. A change that touches multiple modules but in a known shape — propagating a field through call sites, renaming an API, threading a parameter. The picture is small enough for one agent to hold. Provisions one agent plus task tracking.

**LLM priors activated**: Mostly neutral. The "known shape" qualifier is load-bearing — cross-module is distinguished from decomposed by whether the work shape is already understood, not by sheer count of modules touched.

---

### decomposed

**Definition**: A dispatch complexity tier. A change too large for one agent's working set. Requires explicit task breakdown into parallel or sequential sub-units. Provisions an orchestrator plus sub-agents with bounded contexts and hand-off artifacts.

**LLM priors activated**: "Decomposed" activates standard software-engineering decomposition connotations. The term refers to dispatch-level decomposition (a job becomes many sized tasks), not function-level decomposition or code refactoring decomposition. Risk: conflation with those other uses.

---

### architectural-extend

**Definition**: A dispatch complexity tier. A change that requires design judgment before implementation and introduces a new pattern that fits the existing system. Provisions a design phase plus decomposed implementation.

**LLM priors activated**: "Architectural" activates expectations of high-stakes structural work; this loading is intended. "Extend" signals additive change rather than replacement; this loading is intended and distinguishes the tier from architectural-replace.

---

### architectural-replace

**Definition**: A dispatch complexity tier. A change that requires design judgment AND displaces an existing pattern. Provisions a design phase plus the isolation-firebreak flow, because pattern removal has the same cost shape as remediation.

**LLM priors activated**: "Replace" signals destructive change; this loading is intended because architectural-replace work has remediation-cost shape. Risk: connotation that the replaced pattern was "wrong." Replacement may be driven by changing requirements rather than pattern badness; the term carries no judgment about why replacement is needed.

---

### technique-skill

**Definition**: A capability extracted into its own callable skill because at least two consumers benefit from invoking it with a stable interface. A consumer is either another skill (typically a phase skill) or the human operator invoking the capability out-of-ceremony when a meaningful standalone use case exists. Distinct from a phase skill (which orchestrates a stage of the SDL) and from an agent (which embodies a persona); technique skills are the capability layer between them.

**LLM priors activated**: Neutral; the term defines a specific asset class in the firebreak taxonomy. The four technique skills today are grilling, fresh-eyes, quality scan, and test review.

---

### slice shape

**Definition**: One of four discrete test-discipline categories declared per slice in the spec. Each shape implies a different test-task structure, a different relationship to existing tests, and a different test-review behavior. The four shapes are new-contract, contract-preserving, contract-evolving, and cross-cutting.

**LLM priors activated**: "Shape" signals a discrete category, not a position on a continuum — this loading is intended. Risk: conflation with broader "shape" terms (e.g., test shape, code shape, work shape) that appear elsewhere in firebreak vocabulary. Surrounding context always names "slice shape" specifically.

---

### test-discipline

**Definition**: The YAML field in a slice declaration that records the slice's shape (one of new-contract, contract-preserving, contract-evolving, cross-cutting). Read by breakdown to drive the slice's test-task and impl-task structure.

**LLM priors activated**: Names what the field controls (which test discipline applies to this slice), not what taxonomy the value comes from. Reads naturally in YAML context: `test-discipline: contract-preserving`. Prose may refer to the values as "slice shapes" or "test-discipline modes" interchangeably; the field name itself is stable.

---

### new-contract

**Definition**: A slice shape. The slice introduces behavior that does not exist in the codebase. The test-task agent writes new tests against the slice's defined contract; the tests must fail against an empty implementation (red). Hash-locking applies to the new tests. The impl-task agent writes code that turns the tests green without modifying them. Classical red → green discipline.

**LLM priors activated**: "New" and "contract" are both neutral. Risk: confusion with greenfield-vs-brownfield framing — new-contract is independent of that axis; a new-contract slice can appear in either greenfield or brownfield work.

---

### contract-preserving

**Definition**: A slice shape. The slice changes implementation while preserving an existing contract. Existing tests cover the contract and must continue to pass; no new tests are written for the contract itself. Hash-locking applies to the existing tests. No red phase because the test is already green against the old implementation.

**LLM priors activated**: "Preserving" signals stability of behavior, which is intended. Risk: implies the slice is purely internal — but contract-preserving slices can also be performance optimizations, refactors, or replacements as long as the observable contract is unchanged.

---

### contract-evolving

**Definition**: A slice shape. The slice changes both implementation and contract. Some existing tests may need to be retired because they tested behavior the new contract no longer guarantees; new tests are written for behaviors the new contract introduces. The slice declaration must list which existing tests are retired and why.

**LLM priors activated**: "Evolving" signals incremental change rather than wholesale replacement, which is the intended distinction from new-contract (where no prior contract exists) and from contract-preserving (where the contract is unchanged). The explicit retirement list is the load-bearing detail — a contract-evolving slice without a retirement list is malformed.

---

### cross-cutting

**Definition**: A slice shape. The slice modifies behavior that spans multiple existing modules or seams. Tests live at the seams — integration tests, contract tests between modules, or end-to-end tests for a flow. Cross-cutting is test-only: it produces seam tests but no paired implementation (the implementation already exists across the other slices).

**LLM priors activated**: Standard software-engineering term for behavior that spans multiple modules. Generally neutral. Risk: assumed to mean "complex" or "hard" — cross-cutting refers only to where the behavior lives (at seams), not to difficulty.

---

### hybrid gate pattern

**Definition**: The general shape every phase gate takes in firebreak's SDL: a deterministic mechanical check that validates structure, plus a semantic check anchored on a verifiable artifact produced by a technique skill. The mechanical part is hook-ready (can migrate to deterministic hook enforcement when hooks support it). The semantic part anchors on the technique-skill's structured output so the gate has something concrete to inspect rather than re-running judgment.

**LLM priors activated**: "Hybrid" signals two-mode operation, which is intended (mechanical + semantic). Risk: read as "approximate" or "best-of-both" rather than as a specific architectural pattern. The pattern formalizes the existing two-layer gate concept by specifying how the semantic layer surfaces its verdict.

---

### advisory finding

**Definition**: A gate signal that surfaces a problem for human triage without blocking the gate — added to the result's `findings` list, not `failures`. A gate emits one only when the problem needs human judgment (e.g. test drift: a locked test renamed but content-identical). When a problem is instead agent-fixable (missing or unreadable artifact, hash mismatch), the gate blocks via a failure so the agent redoes the work. The rule: block when agent-fixable, advise when it needs a human.

**LLM priors activated**: "Advisory" and "finding" read as generic. Risk: mistaken for a mere lower-severity failure. It is not a severity level — it is a routing decision about *who acts*. The code-review gate derives one from the test-review artifact's `Verdict:` line, making that line a vocabulary contract between the test-reviewer agent and the gate — the same guide↔gate drift the slice-shape sentinel guards.

---

### design manifest

**Definition**: A per-feature index file at `ai-docs/<feature-name>/design-manifest.md` listing every design page the design phase produced under `ai-docs/<feature-name>/design/`. The mechanical anchor for the design-phase hybrid gate's bidirectional check (every manifest entry exists as a page in the feature directory; every design page in that directory appears in the manifest). A ceremony product — deleted at squash-merge along with the rest of the feature directory.

**LLM priors activated**: "Manifest" signals a structured listing for verification, which is the intended use. Risk: conflated with other firebreak manifests (task manifest, test-lock manifest); surrounding context disambiguates.

---

### grilling technique

**Definition**: A technique skill. The one-question-at-a-time ambiguity-resolution capability invoked when an artifact contains decisions the operator should make rather than the agent guessing at. Surfaces decisions with full natural-language context, the agent's recommendation, and the justification — then waits for the operator's answer and reflects it back before moving on. Invoked by intent, design, and spec phases; also invocable out-of-ceremony via `/grill-me`.

**LLM priors activated**: "Grilling" signals adversarial questioning, which is partially intended — the technique is rigorous and surfaces ambiguity that inference would close. Risk: connotes hostile or aggressive register; the technique is structured and respectful, not confrontational. The reflect-back-to-confirm step is load-bearing and not implied by the name.

---

### fresh-eyes

See [fresh-eyes technique](#fresh-eyes-technique).

---

### fresh-eyes technique

**Definition**: A technique skill. A context-clear comprehension check. A reviewer (typically a subagent in isolated context) reads the artifact cold — without authoring context — and surfaces what doesn't make sense as structured observations classified by severity. The reviewer does not have authority to fix; fixes go back to the authoring agent. Used as the semantic anchor for the intent and design gates (the spec gate uses the related, existing council pattern).

**LLM priors activated**: "Fresh eyes" signals untainted perspective, which is intended. Risk: read as "casual" or "informal" — the technique is structured, has a defined output format, and runs under enforced context isolation. The "no fix authority" rule is load-bearing.

---

### quality scan

See [quality scan technique](#quality-scan-technique).

---

### quality scan technique

**Definition**: A technique skill. A top-five code-quality scan run during code review (the *Pocock pattern*: surface the five highest-priority quality opportunities, ranked, and act on them as a separate decision). Surfaces the five issues in the change set as structured findings, each with severity (critical / substantive / minor). Scan-only — does not auto-fix. The operator decides what to do with each finding. Invoked by code-review; also invocable out-of-ceremony for any diff.

**LLM priors activated**: "Quality" is generic; "scan" signals breadth-first inspection. Together they read as standard tooling. Risk: confused with the broader firebreak quality rubric (a multi-dimensional eval system for self-improvement loops). The quality scan is the focused operator-facing top-five list at code-review time, sharing vocabulary with the rubric but smaller in scope.

---

### test review technique

**Definition**: A technique skill. Validates that AI-written tests actually catch the behavior they claim to cover, looking for known AI test failure modes (implementation-embedding, weak assertions, magic-number assertions, internally-contradictory fixtures, mocked dependencies that bypass the behavior under test). Invoked at multiple checkpoints: pre-lock (before hash-locking) by breakdown, and as a final pass by code-review. Formalizes the existing fbk-test-reviewer agent persona as a callable capability.

**LLM priors activated**: Generic software-engineering term. Risk: conflated with general code review or with the existing test-reviewer agent's pre-remediation narrow role. The technique is broader than the original agent and runs at more checkpoints; the existing persona is preserved as one implementation of the technique.

---

### test-lock manifest

**Definition**: A feature-directory file (typically `test-lock-manifest.json`) recording, for each accepted test file: relative path, SHA-256 hash at acceptance time, the slice declaration the test belongs to, and the slice's test-discipline. The structural protection against test mutation during implementation. The mechanical anchor for the code-review gate's hash check. A ceremony product — deleted at squash-merge along with the rest of the feature directory.

**LLM priors activated**: "Lock" signals enforcement, which is intended. Risk: implies the lock is global or persistent — it is per-feature and bounded by the feature's lifetime. The manifest itself is ceremony; the locked tests outlive the feature.

---

### capability-entry

**Definition**: The model by which scope-appropriateness is handled in the SDL: the six phases are independently invocable capabilities, and the human enters the chain at the point that fits the work, rather than a classifier deciding which phases run. Replaces tier-driven depth. A bugfix may enter at the spec or go lighter; a large change starts at intent.

**LLM priors activated**: "Entry" frames the phases as doors the human chooses, not a conveyor belt. Risk: read as "phases are optional to skip mid-run" — the SDL itself does not silently drop a phase the chain reached; skipping is a human *entry* decision, not an in-flight omission.

---

### durable-artifact discipline

**Definition**: The discipline governing the small curated set of git-tracked markdown that outlives a feature — the glossary, the decisions log, and the architecture/intent overview — as opposed to spent scaffolding (spec, breakdown, manifests, reports, retrospective) deleted at squash-merge. Durable docs are updated in the feature branch and merge with the change; git co-location keeps them in sync. Not a memory system or wiki: no tooling, index, or install contract.

**LLM priors activated**: "Durable" signals persistence, intended. Risk: conflated with the cut project-memory wiki — this is plainer (just files plus an authoring habit) and deliberately lighter. "Discipline" signals a practice, not infrastructure.

---

### architecture/intent overview

**Definition**: A living, edited-in-place durable doc describing what a project is and how it works, now — kept to onboarding length, the doc a new human hire or a cold agent reads to come up to speed. Where sticky project intent lives; the intent and design phases read it to inherit context and update it when intent shifts.

**LLM priors activated**: "Overview" signals breadth at low depth, intended (not exhaustive design documentation). Risk: confused with the per-feature PRD — the PRD is feature-scoped and ephemeral; the overview is project-scoped and durable.

---

### decisions log

**Definition**: A durable, append-only, chronological git-tracked file recording the *why* behind enduring choices — what was decided, the alternatives, the rationale, what it constrains. Produced by the design phase and any phase that makes a constraining decision. Append-only: a new entry supersedes rather than rewriting an old one.

**LLM priors activated**: "Log" signals chronological append, intended. Risk: conflated with the per-feature decision spine that was its earlier (ephemeral, feature-directory) form — the decisions log is durable and project-level.

---

*(Additional entries accrete as specs and context assets introduce vetted terms.)*
