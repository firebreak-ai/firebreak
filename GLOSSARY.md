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

Both uses are valid instances of the same underlying concept. The wave term is reserved for "unit of parallel tasks"; no renaming is needed to distinguish the two contexts because their surrounding text always disambiguates.

---

### technique-skill

**Definition**: A capability extracted into its own callable skill because at least two consumers benefit from invoking it with a stable interface. A consumer is either another skill (typically a phase skill) or the human operator invoking the capability out-of-ceremony when a meaningful standalone use case exists. Distinct from a phase skill (which orchestrates a stage of the SDL) and from an agent (which embodies a review or analysis role); technique skills are the capability layer between them.

**LLM priors activated**: Neutral; the term defines a specific asset class in the firebreak taxonomy. The four technique skills today are grilling, fresh-eyes, quality scan, and test review.

---

### advisory finding

**Definition**: A gate signal that surfaces a problem for human triage without blocking the gate — added to the result's `findings` list, not `failures`. A gate emits one only when the problem needs human judgment (e.g. test drift: a locked test renamed but content-identical). When a problem is instead agent-fixable (missing or unreadable artifact, hash mismatch), the gate blocks via a failure so the agent redoes the work. The rule: block when agent-fixable, advise when it needs a human.

**LLM priors activated**: "Advisory" and "finding" read as generic. Risk: mistaken for a mere lower-severity failure. It is not a severity level — it is a routing decision about *who acts*. The code-review gate derives one from the test-review artifact's `Verdict:` line, making that line a vocabulary contract between the test-reviewer agent and the gate — the same guide↔gate drift the slice-shape sentinel guards.

---

### grilling technique

**Definition**: A technique skill. The one-question-at-a-time ambiguity-resolution capability invoked when an artifact contains decisions the operator should make rather than the agent guessing at. Surfaces decisions with full natural-language context, the agent's recommendation, and the justification — then waits for the operator's answer and reflects it back before moving on. Invoked by intent, design, and spec phases; also invocable out-of-ceremony via `/grill-me`.

**LLM priors activated**: "Grilling" signals adversarial questioning, which is partially intended — the technique is rigorous and surfaces ambiguity that inference would close. Risk: connotes hostile or aggressive register; the technique is structured and respectful, not confrontational. The reflect-back-to-confirm step is load-bearing and not implied by the name.

---

### fresh-eyes

A technique skill. See [technique-skill](#technique-skill).

---

### quality scan

A technique skill. See [technique-skill](#technique-skill).

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

### interface contract

**Definition**: A declared, named boundary between two components — a function signature, HTTP route, message schema, or equivalent — together with the invariants both sides agree to honor. In the firebreak SDL, interface contracts are authored in the design phase (on the design contracts page) and carried or minted in the spec. The `## Interface contracts` section of a feature spec is the per-feature record of every new, changed, or blast-radius contract the feature touches.

**LLM priors activated**: "Contract" activates Eiffel/design-by-contract connotations (preconditions, postconditions, invariants), which are the intended priors — both sides of a seam must uphold the invariants. Risk: conflated with legal contracts or SLAs; "interface" narrows the scope to a code-level boundary.

---

### blast radius

**Definition**: What a change reaches beyond what the unit's accepted documents state: the critical path, a new function or module, an interface (inputs, outputs, printed text, exit codes, errors), or a file outside the unit's scope. When sorting review findings, a remedy with blast radius is escalated to the operator rather than fixed by the author.

**LLM priors activated**: "Blast radius" activates destructive-change risk connotations, which are the intended priors: a change propagates outward and its reach must be assessed. Risk: read as catastrophist; a remedy with blast radius is not dangerous, it only needs the operator's answer before the author acts.

---

### contract drift

**Definition**: The condition where an interface contract as written in the spec diverges from the same contract on the design contracts page — different signature, changed invariants, or mismatched covers list. Contract drift is the defect class the design-anchor check detects. Drift can also emerge between the spec and the implementation when a coder edits the implementation without updating the spec or the design page.

**LLM priors activated**: "Drift" activates gradual-divergence connotations, which are intended. Risk: read as always gradual or accidental; drift can also be introduced intentionally (a deliberate change to one document without updating the other), which is a process failure rather than an oversight.

---

### integration seam

**Definition**: A declared pair of interacting components identified in `## Technical approach`, together with the convention both sides must honor — the shared state or interface and the specific data shape, key string, event name, or API path that crosses the boundary. Each seam appears as a checklist entry in the integration seam declaration. The test reviewer at the first checkpoint validates that every declared seam has integration or end-to-end test coverage.

**LLM priors activated**: "Seam" activates Michael Feathers's seam concept (a place where behavior can be observed or altered) — this loading is partially intended, but firebreak's use is narrower: a seam here is a declared, named interface boundary between two specific components in the spec, not a general code-seam in the Feathers sense. Risk: read as a testing artifact only; the seam is first a specification artifact (the declaration in `## Technical approach`) that the test coverage requirement is derived from.

---

### adversarial review pattern

**Definition**: The one generic review shape every Firebreak review type runs as a preset over: a researcher surfaces candidate problems from a cold read, a challenger independently verifies or rejects each one, confirmed problems survive, and the loop repeats until a round comes back clean or a round cap is reached. The loop, the isolation rules, and the carried review-quality behaviors live in this one pattern; only the per-type lens varies. Replaces the former arrangement where code review, test review, and fresh-eyes each reimplemented their own review machinery.

**LLM priors activated**: "Adversarial" signals an intended stance — the challenger is built to disprove, not to agree — which is the load-bearing property, not a tone. Risk: read as conflict-for-its-own-sake; the adversarial relationship is between roles over a finding, not hostility toward the author. "Pattern" signals a reusable shape, which is correct — it is a template instantiated per review type, not a single running process.

---

### researcher

**Definition**: The role in the adversarial review pattern that reads an artifact cold and surfaces candidate problems as structured findings. It does not fix, does not issue verdicts, and never receives a prior round's output or another role's framing. Always spawned as a cleared agent so its cold read is structural, not a behavioral promise. The type-specific knowledge of what to look for reaches it through the review lens injected at spawn, not through its own persona. The role text is `fbk-docs/review/researcher-role.md`, included in a round contributor's instructions.

**LLM priors activated**: "Researcher" frames the role as open investigation across any artifact kind (code, tests, a contract, a plan), which is the intended type-neutral reading. Chosen over "detector" (too code-and-defect-flavored to travel across review types) and "finder." Risk: "researcher" could imply web/literature research; in Firebreak it means the surfacing role of a review, paired with [challenger].

---

### challenger

**Definition**: The role in the adversarial review pattern that independently verifies or rejects each candidate finding the researcher produced. It reads the artifact cold first, then receives only de-framed candidate claims and their cited sources — never the researcher's reasoning, confidence, or framing. Its four outcomes are verified, verified-pending-execution, rejected, and rejected-as-nit. It generates no new findings; it rules on what it received. Always spawned as a cleared agent. Carries the generic disciplines: read the cited source before ruling, and trace provenance before confirming dead material. The role text is `fbk-docs/review/challenger-role.md`, included in a round contributor's instructions.

**LLM priors activated**: "Challenger" signals an intended skeptical stance — demand proof, default to rejection without evidence — which is the point. Risk: read as adversarial toward the researcher personally; the challenge is against the finding's claim, enforced structurally by starving the challenger of the researcher's framing (the isolation invariant).

---

### review lens

**Definition**: A single per-type knowledge document that carries everything a review type needs to know about what to look for and how to classify it — the type's finding types, severities, detection passes, and any type-specific challenger disciplines. The researcher and challenger receive it injected at spawn; swapping the lens is what turns one generic review pattern into a specific review type. Genuinely shared detection passes are not copied into each lens; they live once in a referenced shared-detection document the lenses point to.

**LLM priors activated**: "Lens" signals a way of looking — a perspective laid over the same underlying mechanism — which is exactly intended: the loop is fixed, the lens changes what the eye attends to. Risk: read as a code module or a purely optical metaphor with no operational meaning; here it is a concrete markdown document with a required format, loaded as reference material rather than as an agent persona.

---

### review preset

**Definition**: A thin configured instance of the adversarial review pattern that wires one review type together: it names the lens to load, sets the cardinality (how many researchers, how many challengers), declares the artifact paths it writes, and calls the review loop. It holds no knowledge of what to look for. Standalone review skills supply these settings for their domain.

**LLM priors activated**: "Preset" signals a saved configuration over a general mechanism — intended: a preset is a small set of dials over the shared loop, not a new machine. Risk: read as a rigid or trivial setting; a preset can carry preset-specific pre-work and post-work (code review's linting and post-loop passes) while still delegating the loop itself to the shared spine.

---

### composable pipe

**Definition**: The `validate --lens <type>-lens.md | severity-filter --min-severity <threshold>` command shape that test review uses for detection, in place of code review's single `run` invocation. The lens-parameterized validator does the type-filtering, so it needs no preset entry and no domain-filter step — the two small pipeline commands chained on the shell pipe do the whole detection-side job. The same two commands recompose elsewhere (the post-challenge re-validation reuses `validate --lens`), which is the point of keeping them separate rather than fusing them into one subcommand.

**LLM priors activated**: "Composable" signals small single-purpose commands joined by a pipe — intended: each command reads stdin and writes stdout so they chain freely, Unix-style. Risk: read as a vague design-pattern buzzword; here it is a concrete two-command shell pipe with a fixed order (validate first, then severity-filter), not an abstract principle.

---

### neutral handoff

**Definition**: The six-field normalized record the challenger receives in place of the researcher's full finding — exactly `mechanism`, `consequence`, `evidence`, `type`, `severity`, and `source_of_truth_ref`, produced by `pipeline normalize`. It strips the researcher's framing (confidence, narration, persuasion) so the challenger rules on the claim and its cited source alone, never on how the researcher pitched it. The handoff is "neutral" because it carries the facts a verdict needs and nothing that would steer the verdict.

**LLM priors activated**: "Neutral" signals deliberately de-framed, value-stripped input — intended: it names the isolation invariant in positive terms (what the challenger does receive) rather than as a prohibition. Risk: read as "unimportant" or "default"; here neutral is an active property the `normalize` step enforces, and it is load-bearing — the adversarial review only stays honest because the framing never crosses the handoff.

---

### cross-model review

**Definition**: A second-opinion review run against a different external model (e.g. Codex / GPT-5.5) that produces candidate findings, not verified findings. Candidate findings feed into the adversarial review loop as researcher output and are subject to the same challenger-verification step as any other finding. Opt-in only — enabling it sends the reviewed content to the external third-party model. Configured via the `cross_model_review` block in `.claude/automation/config.yml`.

**LLM priors activated**: "Cross-model" signals multi-model comparison, which is the intended reading. Risk: read as implying the external model's findings are lower-quality or should be down-weighted — they are treated as ordinary candidate findings, subject to the same verification bar. "Review" activates general review-process priors; the "candidate findings" qualification is load-bearing and distinguishes this from a verified quality verdict.

---

*(Additional entries accrete as specs and context assets introduce vetted terms.)*

---

### workflow unit (0.6.0)

**Definition**: A named project or feature under `.fbk/`, with requirements, phase inputs, and one durable state record; a project ends at spec and a feature continues through implementation.

**LLM priors activated**: A bounded piece of work, not necessarily a process or an agent.

### acceptance evidence (0.6.0)

**Definition**: The recorded input revision, verification results, review findings, and any scoped approval supporting a phase close; changed inputs make that acceptance stale.

**LLM priors activated**: Evidence supports an engineering decision, not proof of perfect correctness or maintainability.

### approval grant (0.6.0)

**Definition**: A recorded human authorization bound to a particular crossing, phase, input revision, and any named test scope, consumed by the relevant operation.

**LLM priors activated**: Permission is specific rather than blanket. The agent records genuine existing authorization; the record itself does not authenticate the human.

### review generation (0.6.0)

**Definition**: A phase's interval between opening and explicit reopening, within which attempts share a persisted budget and completed reviews of unchanged inputs can be reused.

**LLM priors activated**: A bookkeeping boundary, not a model generation or an excuse to reset the budget after ordinary fixes.

### review plan (0.6.0)

**Definition**: The saved single-reviewer or council choice for a unit's intent, design, spec or breakdown phase, including selected council perspectives, the applicable preference, and rationale. Design and spec require one; intent and breakdown default to a single reviewer.

**LLM priors activated**: A decision about how an artifact is reviewed, independent of whether the design phase runs; it does not grant approval to implement or override findings.

### council review (0.6.0)

**Definition**: A runtime-mediated discussion among the builder and one or two other selected perspectives: independent opening proposals, one rotating turn each, closing stances, a count that decides which proposals stand, and a final session that writes them as findings.

**LLM priors activated**: Multiple perspectives contribute evidence; consensus and role titles do not establish correctness. Distinguish managed acceptance review from consultation, a council the operator convenes to discuss a question.

### continuation (0.6.0)

**Definition**: A generated current-unit view containing the phase, governing source references, current decisions, pending work, findings and next action. Bounded views identify omitted sections and how to retrieve them.

**LLM priors activated**: Resuming from durable authority and current evidence, rather than treating a summary of earlier conversation as authority.

### sourced decision (0.6.0)

**Definition**: A recorded interpretation of human intent linked to an exact quote in an immutable source file, with the earliest applicable phase and explicit supersession when corrected.

**LLM priors activated**: Attributable evidence of a decision; agent-supplied attribution does not authenticate consent or establish that the interpretation is correct.

### routine repair (0.6.0)

**Definition**: A bounded correction under sourced standing authority. Mechanically verified reference corrections may preserve current acceptance; independently checked prose corrections against settled intent invalidate affected acceptance and retain review attempts.

**LLM priors activated**: A specific authorized correction whose validation depends on its class. Patch size and model confidence do not establish unchanged meaning.

### review source snapshot (0.6.0)

**Definition**: A temporary copy of original review inputs and repository sources, excluding managed workflow history and host runtime state. Native review file tools are confined to this copy; its manifest supports freshness checks.

**LLM priors activated**: A controlled reading surface with a known revision, not proof that a model inspected or understood every source.

### retrospective evidence (0.6.0)

**Definition**: An explicitly requested view of a unit's recorded actions, outcomes, source references and attributed observations, with capture limitations and targeted access to historical detail.

**LLM priors activated**: Investigating original evidence while separating observations, explanations and unknowns; history does not become authoring authority.

### improvement evaluation (0.6.0)

**Definition**: A recorded assessment of a proposed change against its baseline and success criterion, linked to the adopted target revision and check or follow-up evidence. Changed evaluated evidence requires re-evaluation.

**LLM priors activated**: Testing an intervention rather than assuming that applying it helps. Adoption, reported results and established causal effects are different claims.

### constraint registry

**Definition**: The single ordered list, in `fbk-scripts/fbk/workflow/constraints.py`, of every deterministic rule the runtime enforces on a reviewer session's structured response. Each entry names the rule once, the session kinds it applies to, the validator that rejects a breach, and its sentence (a callable when a number comes from configuration or a schema). The registry renders the `rules` block every reviewer prompt carries; two tests hold it to the code, one asserting each entry is stated in the assembled prompt and one asserting each rejection site names an entry. Documented in `fbk-docs/workflow/constraints.md`.

**LLM priors activated**: "Registry" signals a central lookup table, intended. Risk: read as a runtime service or a schema; it is a Python list read at prompt-assembly time, and host-side JSON schema limits are covered by the schema walker, not by registry markers. "Constraint" here means a rule on model output, never a design or requirement constraint.

### decision kind (0.6.0)

**Definition**: The required `kind` on a recorded workflow decision: `governs` when it constrains the work product (behavior, scope, contracts, plan rules), `process` when it records how the work was run (review plans, approvals, dispositions, overrides). Only governing decisions reach reviewers and work agents; process decisions stay in the record and still count toward staleness. Documented in `fbk-docs/workflow/decisions.md`.

**LLM priors activated**: "Governs" signals authority over the deliverable, intended. Risk: "process" read as unimportant; process decisions remain binding on how Firebreak runs, they are only kept out of readers' context.

### decision amendment (0.6.0)

**Definition**: A governing decision whose `amends` names an earlier, accepted phase whose document it changes without reopening that phase. It reaches every later phase's readers, and the amended phase's if reopened, until that phase is accepted again after the amendment was recorded, at which point the document has absorbed it. Superseding an earlier phase's decision makes the new decision an amendment of that phase automatically.

**LLM priors activated**: "Amendment" signals a recorded change to an accepted text that overrides it where they differ, intended. Risk: read as an edit to the earlier document itself; the document is unchanged until its phase is reopened.

### test checkpoint (0.6.0)

**Definition**: The review gate inside the implement phase that judges whether the tests test tasks wrote would catch code that deviates from the design, and on a pass locks exactly the reviewed tests. It runs when every test task has a completed, current run, keeps its own review record and round budget beside the phases without being a phase, and refuses to run again while its acceptance is current. Implementation tasks write code only while a current checkpoint stands behind the locks.

**LLM priors activated**: "Checkpoint" signals a point where work is verified before continuing, intended. Risk: read as a saved state to roll back to; it saves nothing to restore, it is a review that authorizes the next stage.

### preservation checkpoint (0.6.0)

**Definition**: The test checkpoint of a unit whose requirements are all review-only, whose plan therefore has no test task, and which had scoped tests when implement was entered. Every declared check must pass, a scoped test that differs from the writing-tests baseline is refused, and the reviewer judges whether the existing tests protect the code the unit will change; on a pass every scoped test locks. A unit with no test task and no scoped test has no checkpoint at all: Firebreak records the empty test inventory and refuses any scoped test that appears later.

**LLM priors activated**: "Preservation" signals keeping behavior already built, intended. Risk: read as a test task that declares exit 0 for a test preserving behavior; that happens inside the normal checkpoint, while a preservation checkpoint has no test task at all.

### test region

**Definition**: The end of a source file that holds that file's unit tests, declared in `scope.json` `test_regions` by the files it applies to and a start expression. It starts at the first line the expression matches and runs to the end of the file; a file with no such line has an empty region. The region is a scoped test, locked and protected by its own fingerprint, while the code above it stays an ordinary production file that implementation workers keep editing after the test checkpoint. Firebreak finds it by matching text, never by parsing the language, and tests interleaved through a file are not supported.

**LLM priors activated**: "Region" signals a delimited span of a file, intended. Risk: read as any marked block, including ones in the middle of a file; a test region always runs to the end of the file.

### writing-tests baseline (0.6.0)

**Definition**: Saved copies, with fingerprints, file modes and symbolic-link targets, of every scoped test and production file, recorded whenever the unit begins or returns to writing tests: first entry into implement, an unlock approval, a governing decision that makes the checkpoint stale, and re-entry after a breakdown-or-earlier reopen. The test checkpoint compares the current tree against it to tell tests the test tasks changed from untouched ones, refuse production changes no test task declared, and show declared production changes to the reviewer as diffs. Relaunching, cancelling, or rejecting work never re-records it.

**LLM priors activated**: "Baseline" signals a fixed reference point for comparison, intended. Risk: read as git's last commit; it is the tree as it stood when test writing began, including uncommitted changes.

### commitment (0.6.0)

**Definition**: Anything the unit promises, written as one heading in the Commitments section of `prd.md`. The term covers every kind of promise: a commitment can be a user story, a constraint the unit must respect, or a quality target such as speed or reliability. Design choices link it by anchor (requirements do, in a unit without design), and design close (or spec close without design) refuses a commitment nothing links. A promise deliberately left out of scope is removed or moved to an out-of-scope note, not left as a commitment.

**LLM priors activated**: "Commitment" signals a binding promise, intended. Risk: read as any statement in the PRD; only headings in the Commitments section are commitments. Chosen over "story", which would steer authors toward the "As a user, I want" form, leave constraints out, and be confused with a unit of work (Firebreak's units of work are tasks).

### design choice (0.6.0)

**Definition**: A decision a design file makes, written as one heading in that file's Design choices section, linking the commitments it serves by anchor. Design close refuses a design choice with no commitment link, and spec close refuses one no requirement links. A design file without the section makes no design choices.

**LLM priors activated**: "Choice" signals a selection among alternatives, intended. Risk: read as any decision discussed in a design file; only headings in the Design choices section are design choices.

### requirement (0.6.0)

**Definition**: Something the unit must deliver, usually a behavior (see review-only requirement for the exception), written as one heading in the Requirements section of `spec.md`, linking the design choices it comes from (or commitments, in a unit without design) by anchor. Spec close refuses a requirement with no such link.

**LLM priors activated**: "Requirement" carries the broad sense of anything the work must satisfy, including the PRD's needs. Risk: read as a PRD statement or a constraint elsewhere in the spec; in the workflow a requirement is a heading in spec.md's Requirements section.

### review-only requirement (0.6.0)

**Definition**: A requirement that no executable check can meaningfully verify, such as a naming convention or a documentation obligation, marked by the line `Checked by review: <reason>` directly under its heading. Breakdown plans no test for it, the spec review judges whether the marker is honest, and the implementation review gives a met or not met verdict on it; a not met verdict blocks implementation close. Every other requirement is behavioral and needs a test.

**LLM priors activated**: "Review-only" can read as a lighter, optional check. Risk: read as best-effort or as a way to skip a test; the implementation review must assess each one, a review that leaves one out is refused, and a marker on a requirement whose behavior a test could check is a blocker at spec review.

### fix, escalate, refute (0.6.0)

**Definition**: The three ways the authoring agent sorts each review finding before changing anything. Fix: the remedy only corrects what accepted documents already state, and the agent applies it alone. Escalate: the remedy adds scope or has blast radius, or the right remedy is unclear, so the operator answers fix now, defer or decline. Refute: the agent shows with evidence that the failure cannot happen or is required behavior. The sort is separate from severity, which only decides whether the phase can close with the finding open.

**LLM priors activated**: "Fix" reads as the default response to any finding. Risk: an agent treats every valid finding as a fix; the sort exists so that a valid finding whose remedy widens scope goes to the operator. "Refute" can read as arguing a finding away; it needs evidence, and a wrong citation alone does not refute.

### spec trim (0.6.0)

**Definition**: The step at the start of spec close in which a fresh session cuts the draft spec before its review: it merges examples that would catch the same wrong implementation, removes examples and text that catch nothing the rest miss, and never adds. Firebreak lists the cuts at the end of the spec under "Removed on purpose", whose opening says a removed item is not a gap and only a later code review may restore one. It runs once per spec draft; a session that gives no result is retried once, then the spec goes to review untrimmed; a trimmed spec that fails a check goes back to its author.

**LLM priors activated**: "Trim" reads as light tidying of wording. Risk: read as cosmetic; its main effect is fewer examples, and so fewer tests, while every rule keeps at least one example and nothing a human decision names is cut.

### change detector

**Definition**: A test that fails when the code is changed in a way that keeps every agreed rule true, for example an internal function renamed or a message nobody decided reworded. It costs upkeep on every correct change and catches no bug the rules define. Test cleanup confirms one by running the test against a correct rewrite from its scoring kit.

**LLM priors activated**: "Detector" sounds useful, as if the test guards something; the name is intentionally ironic, since what it detects is change, not error. Risk: read as any test that fails after a code change; a test that fails because a rule broke is doing its job.

### test cleanup

**Definition**: The standalone skill `fbk-test-cleanup`, which works on an existing project's tests one operator-chosen target at a time, outside any workflow unit. It settles the rules the code must follow from evidence (a document states it, something outside the target depends on it, or it guards safety or security) and asks the operator only when sources conflict; the tests are trimmed, strengthened where a plausible bug would escape, and merged, all checked against a scoring kit; the result is a test-only commit with a committed report at `.fbk/test-cleanup/<target>.md`, followed by tests-first commits for any production change the operator approves.

**LLM priors activated**: "Cleanup" reads as tidying style or formatting. Risk: read as cosmetic; it removes and rewrites tests and can add them, and every change carries run evidence.

### scoring kit

**Definition**: The set of small code changes test cleanup judges a suite with: wrong versions, each breaking one rule in a way an implementer plausibly might, and correct rewrites, each keeping every rule true while changing what no rule fixes. A separate subagent writes it from the rules and the production code alone, without seeing the tests, before any test changes, and the subagent that edits the tests never sees it, so the kit result measures the tests rather than serving as their target. Each change is applied only in a disposable copy of the project.

**LLM priors activated**: "Scoring" suggests a numeric grade; the kit gives a pass or fail per change, not a score. "Kit" suggests reusable tooling; it is rebuilt when the production code changes.
