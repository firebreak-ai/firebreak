# Live-trial remediation plan

## Bounded consolidation, 2026-09-09

After remediation validation, the human authorized a consolidation pass: clarify shared execution ownership, reconcile active review instructions, and script repetitive existing pipeline sequencing where it removes agent coordination work. Preserve approved review gates, authorization, evidence, budgets and test assertions; do not introduce a new workflow engine or policy. The earlier combined-validation report describes the pre-consolidation snapshot until refreshed checks are recorded here.

- Move shared active-wall execution, cancellation, recovery and extension into `review_execution.py`; both managed review and standalone contributors use it. Keep the persisted state format unchanged.
- Give standalone code review an explicit binding for detector/challenger roles and existing pipeline options, so normalized findings actually reach the challenger and validated merged findings reach remediation. Reuse the existing pipeline, preserving generic contributor execution.
- Simplify the active skill and round guide around the runtime route; separate imported supporting evidence from runtime contributor output.

The execution extraction passed 41 focused tests and independent AST comparison against the validated installed source; all six moved definitions preserve behavior. Mechanical test import/patch-target updates follow the moved execution owner; assertions are unchanged. The explicit pipeline binding and shorter instructions are implemented. The combined runner currently reports 583 passed and one new regression blocked on human approval to correct its declaration evidence field name (reference versus full evidence). Installer assessments pass 66/66; additional evaluators pass eight cases and 24 subtests. Evidence: `/tmp/fbk-consolidation-python/run-pbvyke1c` and `/tmp/fbk-consolidation-installer/run-pj0xkdjo`. A fresh agent independently created an isolated project, installed the assets, began the bound review and constructed the next contributor commands from the revised skill. No native reviewer was launched. Its two vocabulary findings are being reconciled in the canonical guide. This is not a new complete live-model lifecycle.

Status: integration validation refreshed 2026-09-09. Packages A–E have implemented runtime or guidance changes and bounded validation; they are not merely queued assignments. All current deterministic suites pass; package F has not run against this combined revision. See [combined validation](combined-validation-2026-09-09.md) for current evidence, completed fixture migrations and implemented policies. No live project was modified by this validation.

## Current delivery status

| Package | Current implementation and evidence | Remaining boundary |
| --- | --- | --- |
| A: task handoffs/preparation | Accepted per-task checks, consumed-file scheduling, output lineage, inherited preparation evidence and required task completion are implemented. | Approved closure fixture and live-smoke migrations now execute declared tasks and pass combined validation. Semantic test applicability remains a reviewer judgment. |
| B: review rounds/budgets | Durable snapshots/results, contributor launch, shared active wall budget, interruption recovery, investigation continuation and strict native object parsing are implemented. | Runtime provenance enforcement and delegated malformed-envelope rejection pass combined validation; fresh live model validation remains. |
| C: independent execution | Disposable bounded investigations and fresh verifier execution are wired into the runtime. | Controlled deterministic paths pass; the actual verifier trial exhausted its turn cap and did not yield accepted verification. |
| D: remediation quality | Sibling accounting, declaration/change gates, independent behavior/regression verification and focused follow-up guidance are implemented; bounded behavioral evaluation exists. | Late registration recovery is implemented and independently checked. No claim that all model-generated verification is reliable. |
| E: scope/structure | Structural guidance evaluation and post-acceptance drift reporting are implemented. | Approved acceptance setup migration completes task execution before testing drift; all drift tests pass. |
| F: comparative trials | Trial design remains available below. | No fresh complete combined lifecycle or comparative trial; do not use older lifecycle evidence as validation of this revision. |

Current validation: the ordinary Python runner passes 578 cases (493 source, 61 workflow benchmark, 24 reporting); the additional remediation/structural evaluators pass eight cases and 24 subtests; 98 selected installed runtime tests and 66 installer assessment rows pass. No failures, errors or skips remain in these runs. Installed and source tests overlap; these totals describe different scopes. A fresh bounded live-install trial remains the next step.

## Approved first assignments

The human resolved these boundaries through the grilling interview:

- **Review budgets:** make the reviewer turn budget configurable and its failure diagnostics explicit; preserve the initial default of 12. Exhausted budgets escalate to the human. No automatic extensions or unlimited retries.
- **Task completion checks:** define each task's definition of done and concrete passing check during breakdown. Firebreak reviews and accepts these before human approval to enter implementation. Individual task inspection is optional for the human. Implementers cannot substitute weaker completion criteria. Focused checks may pass while unrelated planned work remains red; whole-unit checks run at final closure.
- **Structural review:** evaluate existing guidance at design, spec, and code review. Demonstrated consequential structural defects can block acceptance despite passing tests; preferences and arbitrary size thresholds cannot. Record late discoveries clearly in retrospectives, with evidence tracing missed prevention to design/spec where justified. Reopen only when correction changes an accepted architectural decision or contract; local corrections remain in implementation. Targeted guidance improvements supported by evaluation are authorized; phase-boundary or approval-policy changes return to the human.

These three bounded assignments were delegated independently. Each implementer writes meaningful regression tests first, observes the relevant failure, and then keeps those tests fixed while implementing. A discovered incorrect test requires escalation to the human before correction. Structural guidance needs behavioral evaluation, including cases that should not trigger refactoring, rather than tests that merely assert wording. Dependency lineage and inherited preparation evidence remain coordinated with the human in parallel. Splitting breakdown remains an available design choice, not part of these independent assignments.

Further agreed dependency boundaries: breakdown declares scheduling dependencies separately from consumed files. Plan validation and runtime scheduling must prevent managed tasks from modifying another running task's consumed files, including read/write conflicts between otherwise disjoint owners. Unexpected input changes are flagged as interference; preserve the work but require refresh and revalidation before acceptance. This is a recovery path for external edits or a framework scheduling defect, not normal managed execution. Authorized output evolution after consumers complete must preserve applicable historical test evidence without treating it as proof that new work is current.

Further agreed preparation and requirement-change boundaries:

- A plan-only reopen preserves applicable recorded red evidence when tests and their governing requirements remain unchanged and intervening implementation was authorized. New or changed tests need fresh applicable evidence; do not revert valid implementation merely to recreate red.
- A requirement change triggers a reviewed impact determination rather than automatic invalidation of all evidence. Assess whether each affected test still asserts wanted behavior: a changed requirement can invalidate a test even when it still passes. Preserve unrelated evidence. Hash equality or inequality alone cannot establish semantic applicability.
- Firebreak review identifies and justifies necessary changes to locked tests. Human approval covers those proposed changes together; approval of a requirement change alone does not silently unlock its tests. Unrelated tests remain locked, and implementers cannot reinterpret requirements to weaken checks.
- Updated tests that already pass because the implementation satisfies the revised requirement may use reviewed preservation evidence. Review must establish that the tests meaningfully detect violations of the revised requirement; a green result alone is insufficient. Do not alter correct production code merely to manufacture red. New behavior that is not yet implemented still requires meaningful red evidence before implementation.

First assignment results (agent-reported, 2026-09-08): configurable review budgets and explicit exhaustion escalation passed 128 focused tests; accepted task checks, independent execution outside the project lock, and stale-result rejection passed the full Python suite of 389 tests. All seven structural evaluation cases matched their unchanged expected decisions after human-approved fixture/scorer corrections; see `structural-review-validation.md` for evidence and limits. These are historical first-wave results; the current delivery table above supersedes their implementation status and test totals.

Second independent assignments were launched with human authorization and subsequently implemented: dependency graph/consumed-file scheduling and authorized output lineage; durable preparation evidence across reopen with safe review of applicability; and bounded post-acceptance drift reporting. The drift assignment reports changed accepted content and discoverable out-of-scope tests without expanding scope or manufacturing acceptance. Agents coordinate shared files and retain the tests-first/test-correction approval boundary. Review transport, independent execution and remediation verification subsequently received runtime implementations; the remaining policy decisions are listed in the current validation report.

## Agreed investigation policy

Reviewers and remediators may inspect actual dependencies, current documentation and runtime behavior rather than relying on recalled knowledge. Both may conduct temporary experiments in disposable workspaces without separate human approval. This grants no authority to modify the reviewed deliverable.

Perform small, bounded inspections and focused checks directly. Delegate exploratory investigations, noisy multi-step debugging, and code-modifying experiments to fresh experimental subagents. Give each a concrete question, source revision, relevant requirements and constraints; return reproducible evidence and limitations rather than the exploration transcript. The reviewer remains responsible for interpretation. A remediator's helper provides context isolation, not independent verification of its own remediation.

Each investigation has a shared bounded budget for experiment attempts and elapsed execution time, within the enclosing review's overall limit. Retries, delegation and context resets do not renew the budget. Exhaustion stops further investigation and escalates to the human with gathered evidence and the unresolved question. Approved configurable trial defaults are three experiment attempts and 600 seconds of execution per investigation, capped by the enclosing review's remaining budget. An attempt is a bounded investigative assignment, not an individual shell command. Record actual usage and the exhausted limit so defaults can be tuned from evidence. The runtime now implements these budgets through bounded investigations and shared review execution; manual submissions now remain supporting evidence and cannot satisfy required contributor completion without runtime execution provenance.

The human approved an explicit configurable full Council active wall-clock limit, including investigations and reviewer continuations. Parallel workers share that elapsed-time window; do not sum their execution durations to enforce it. Preserve consumed time across retries and exclude time awaiting human input. Record active wall time, total elapsed time, human waiting, and aggregate worker execution/model usage separately to assess developer delay, computation cost and recovery overhead. This replaces reliance on independent per-session timeouts as the enclosing round budget.

Public documentation lookups and isolated local experiments are available by default. Checks against authenticated services or shared environments, and external state-changing actions, require explicit authorization covering the target and permitted effects. Task-specific authorization or a sourced standing policy is sufficient and carries forward without repeated permission requests. Isolation of local files does not itself authorize external effects.

## Agreed review completion policy

Remediation waits until every assigned contributor has completed the round and its full results are durably recorded. Partial, truncated, missing, or failed contributor output leaves the round visibly incomplete. Recovery or explicit human disposition is required before fixes begin; receipt of a fragment or silence cannot imply completion.

If reviewed source changes during a round, finish against the original immutable snapshot and retain the findings as historical evidence. Clearly flag the unexpected change in round status and durable retrospective evidence, including affected paths, detection time, original revision and observed current revision. Require a current review before acceptance. Treat this as a corner case to diagnose, not routine managed concurrency; an old review cannot approve new source.

Interrupted rounds may reuse completed contributor results only when the source snapshot, review instructions and configuration are unchanged. Resume missing work only, preserve consumed budget, and visibly record reused results. A changed review contract requires a new round; restarting transport or agent context does not replenish investigation or review budgets.

## Agreed remediation verification policy

For material bug fixes, an independent verifier checks both the corrected behavior and whether the regression test detects the demonstrated defect. Use the original defect or a representative incorrect implementation in an isolated copy. A remediator or its experimental helper cannot supply the sole independent verification. Permit evidence-backed exceptions for interacting safeguards or inseparable changes: removing each guard individually need not make a test fail. Record what the test actually rejects and the limits of the verification.

An authorized fix covers other occurrences of the same demonstrated defect within accepted scope. Inspect related paths and account for each relevant occurrence as fixed, already safe, or outside scope with a reason. New behavior or a broader architectural change requires a separate decision; sibling coverage is not authority for speculative rewrites.

After a fix, a fresh review covers affected behavior and related paths, rather than only changed lines. Expand to the full artifact when consequences are broader. Justify the selected review scope; do not automatically restart every review in full. Preserve cumulative budgets and unresolved findings across these follow-up passes.

Evaluation evidence fidelity is distinct from whether evidence supports a conclusion. Exact quotations of decoded execution output are valid only when attributed to the specific artifact and field (for example, a JSON pointer to stdout); do not search arbitrary output fields for a match. Keep raw-artifact quotations valid, reject paraphrases presented as exact quotations, and do not rewrite historical answers or infer missing field attribution to improve scores.

Register each material fix against its finding, affected behavior and expected scope before production edits begin. Framework completion must account for the resulting changes; undeclared changes cannot silently bypass independent verification. Registration can be script-driven and does not introduce a routine human approval checkpoint. Routine formatting or documentation edits do not require experimental proof; their classification does not authorize unaccounted behavioral changes.

Manually imported review results are supporting evidence only and cannot satisfy the completion gate. Completion requires runtime-recorded reviewer execution tied to the reviewed snapshot, contract and execution budget; importing an artifact cannot substitute for that provenance.

If an authorized material fix already exists without prior registration, permit explicit late registration tied to the original finding, pre-fix snapshot and existing authorized scope. Visibly record the missed registration as recovery evidence. Independent verification remains mandatory; late registration neither expands authorization nor approves the changed code. Do not revert correct implementation merely to recreate the registration sequence.

## Objective

Preserve alignment with human intent and meaningful test-first implementation while removing avoidable recovery loops, unreliable review handoffs, and fix-induced defects. Control each agent's context through explicit assignments, original source references, durable evidence, and clear completion conditions. Phase names and document counts are implementation choices, not quality targets.

The immediate deliverable is a reliable lifecycle that can be exercised again. A shorter lifecycle and changes to author-context reset policy require comparative evaluation before becoming defaults.

## Evidence and boundaries

The task-tracker trial is under `test-results/live-install/task-tracker/`. Its unit state, ten observations, `fbk-effectiveness-report-2026-09-08.md`, and `fbk-code-review-2026-09-08-1420.md` are the evidence sources. They are local trial artifacts, not required installed assets. Implementation work should cite the relevant durable event/observation identifiers and preserve the source hashes used for diagnosis.

Established observations:

- A legitimate storage implementation invalidated another task's frozen dependency outputs and forced breakdown to reopen.
- The original three test files had identical hashes across both locks. The first red run was 65 failed / 1 passed. After storage implementation, the re-opened preparation showed 32 failed / 34 passed. Fresh reviewers lacked usable original red evidence and treated legitimate prior work as suspect.
- A reviewer prescribed expected exit 1 for an implementation task, contrary to the runtime contract. A narrower passing storage check was sufficient for the task; the whole suite belonged at implementation close.
- Required-file inspection reporting and the fixed 12-turn reviewer limit each consumed a failed review attempt.
- The standalone review reports truncated results, premature completion, changing source files during reviews, incorrect runtime claims, and fixes whose purported regression tests did not detect their removal.
- Structured observations now exist. The next improvement step is linking them to proposed changes and evaluations, not adding another observation ledger.

Limitations: the claimed one-shot cost and equivalent correctness were not measured. Context accumulation is a plausible contributor, not an isolated cause. Standalone remediation introduced additional behavior after managed acceptance; its later green suite is not evidence that the managed acceptance is current.

## Execution order

| Package | Priority | Depends on | Completion criterion |
| --- | --- | --- | --- |
| A. Executable task handoffs and preparation evidence | First | None | The original branching task graph completes without weakening freshness or recreating valid red evidence |
| B. Durable review rounds and explicit budgets | First | None | Partial, stale, or failed review output cannot be accepted as a completed round |
| C. Independent executable verification | Next | B's snapshot/result contracts | Disputed runtime claims have reproducible evidence separate from remediation |
| D. Class-level remediation and bounded context | Next | B and C | Controlled exercises detect ineffective fixes and sibling omissions without speculative rewrites |
| E. Scope, structure, and managed acceptance | Next | A and B; uses D's evaluation | Review respects accepted scope, assesses organization, and reconciles authorized post-close changes |
| F. Comparative lifecycle trials | After fixes | A–E | Defaults are selected from measured quality and cost rather than this trial's counterfactual estimates |

A and B can be developed independently once their shared revision/evidence contract is agreed. Integrate and validate each package before using it as another package's foundation.

## A. Executable task handoffs and preparation evidence

Primary seams: `assets/fbk-scripts/fbk/workflow/{handoff,test_preparation,engine,close,review}.py`, the breakdown and handoff guides, and workflow lifecycle tests.

1. Distinguish governing inputs, immutable test evidence, and implementation outputs expected to evolve. Make each task's consumed dependency outputs explicit; a scheduling dependency must not silently freeze every file its predecessor produced.
2. Track authorized output replacement through producer/dependency lineage. A completed test task remains historically valid when an authorized implementation task replaces its stub. Current consumers must receive the appropriate current outputs. Arbitrary edits, stale governing contracts, and unauthorized test changes still invalidate work.
3. Validate task-plan executability before accepting breakdown. Extend existing scope and cycle checks to detect contradictory ownership/consumption contracts and impossible stage transitions. Do not claim to decide semantic task adequacy with graph validation alone.
4. Preserve accepted preparation evidence across a plan-only reopen. Supply fresh reviewers with runtime-produced evidence identifying test hashes, original source/stub hashes, executed commands, captured results, and the prior acceptance boundary. Expose the evidence without requiring reviewers to read authoring transcripts or previous review verdicts.
5. Support mixed preparation explicitly: unchanged tests with valid earlier red evidence, preserved existing behavior, and newly authored tests needing new red evidence. A changed test or governing contract cannot inherit old evidence automatically. Reopening must not require undoing valid production work merely to recreate a failure.
6. Separate focused task checks from whole-unit checks. Implementation tasks report passing checks for their own outcomes; final closure independently runs the declared whole-unit suite. Supply this same structured contract to reviewers and authors. Do not use unrelated remaining failures as proof that a task's own behavior is verified.

Regression scenarios: test/stub producer feeding separate test and implementation consumers; sibling consumers followed by an integration task; unauthorized output edits; changed intent/spec or test hashes; additions/removals of tests; interruption and resumption; plan-only reopen after partial implementation; narrower task checks passing while other planned work remains red. Reproduce the trial's branching graph, not only a linear test→implementation chain.

## B. Durable review rounds and explicit budgets

Primary seams: managed `review.py`, `review_context.py`, `close.py`, council execution, standalone `fbk-code-review`, the shared review-loop guide, and pipeline validation.

1. Use immutable source snapshots and an explicit revision identity for both managed and standalone review. Keep candidate and adjudication evidence tied to the same revision. If live work advances, finish the snapshot review as historical evidence and require an applicable current review before acceptance.
2. Give every expected contributor an explicit lifecycle and result reference. A complete response must identify the contributor, revision, schema, and complete result artifact. Chunked transport requires an explicit manifest/completion signal; a quiet agent or a received fragment is not completion.
3. Persist results through a bounded output channel or isolated result-file area. Do not grant broad writes to the reviewed checkout merely to avoid message truncation. Reuse existing snapshot and serialization machinery where possible.
4. Start remediation only after the relevant review round is complete. Any intentionally concurrent work operates on separate revisions with explicit reconciliation. Late findings cannot arrive after a falsely reported clean close.
5. Make turn and wall-clock budgets visible, bounded, and configurable. Record which limit failed, the configured budget, and the missing inspection/result evidence. Avoid another unexplained default increase or unlimited retries. Use failures to calibrate budgets in the next trial; keep explicit human escalation at exhaustion.

Regression scenarios: truncated JSON; missing final chunk; duplicate/reordered chunks; missing contributor; late result; worker failure; changed source mid-review; stale adjudication; recovery after interruption; separate turn-limit and timeout failures; no acceptance or budget extension manufactured by retry handling. A deliberately large result should survive the transport intact.

## C. Independent executable verification

Primary seams: reviewer capability configuration, immutable execution workspaces, structured findings/probe evidence, and the standalone review workflow.

1. Provide at least one independent verification role a disposable checkout and command execution. It receives the original contract, relevant source, and a concrete claim to investigate; it does not receive authority to remediate production files.
2. Return reproducible commands, relevant environment assumptions, actual outcomes, and bounded diagnostics with retrievable full evidence. Attribute conclusions to the executor and retain contradictory results.
3. Use execution where the claim depends on runtime behavior, timing, encoding, framework behavior, or whether a test detects a bug. Static evidence can establish directly demonstrable defects; avoid mandating execution for every observation.
4. Keep unverified runtime claims visibly provisional. Do not silently turn inability to run a probe into either confirmation or rejection. Let the remediator reproduce the evidence, but do not make that agent its sole authority.

Evaluation cases: a real escaping exception; a plausible but false claim that a regression test cannot fail; a timing-sensitive pipe case; a locale-dependent case; and an unavailable prerequisite. Evaluate conclusions against known behavior while withholding the expected answers from the agents. Verify that probes leave the reviewed checkout unchanged.

## D. Class-level remediation and bounded context

Primary seams: code-review remediation instructions, existing consistency/quality guidance, test-integrity review, and task-context/result contracts.

1. Before assigning a fix, identify its mechanism, governing behavior, related call sites, and affected tests. The remediator must account for relevant siblings: fixed, already safe, or outside scope with a reason. Strengthen the existing sibling sweep rather than adding a duplicate checklist.
2. Give a fresh remediator a bounded assignment containing current source references, verified findings, reproduction evidence, and constraints. Preserve decisions and unfinished work before a reset. Do not carry the complete review transcript as implicit authority.
3. Require a regression test that detects the demonstrated behavior. For a material fix, challenge it with the original defect or a representative incorrect implementation in an isolated copy. Record what the test actually rejects. Treat defense-in-depth and inseparable changes explicitly; do not require every individual guard removal to fail independently.
4. Have independent verification check both the fix and the test. Then review the resulting change on a stable snapshot. Broaden review only when the changed mechanism or interfaces justify it.
5. Prefer a common mechanism when it fits the accepted responsibility boundary. Do not turn every repeated conditional into an abstraction or use a defect as authorization for a broad rewrite.

Evaluation cases: a missing sibling error path, a test that merely checks its setup, a regression test that passes without the fix, a genuine defense-in-depth pair, a change that alters error precedence, and a partial completion followed by a context reset. Compare introduced defects and unresolved siblings, not whether the agent repeated prescribed terminology.

## E. Scope, structure, and managed acceptance

Primary seams: intent/design/spec guidance, existing structural quality detection, reviewer objectives, scope/test locks, and improvement records.

1. Make new design guarantees traceable to intent or an explicit design decision. Distinguish required behavior, necessary engineering support, accepted limitations, and optional hardening. Review consequential scope growth against the human's priorities, including keeping a small tool small.
2. Make absolute claims reviewable: state their domain and relevant exceptions, and include meaningful evidence for consequential guarantees. A finite list of examples does not prove an unrestricted guarantee; aspirations must not become hidden acceptance gates.
3. Exercise the existing module-responsibility and consistency review against known organization problems. Determine whether scope filtering, prompting, context, or remediation authority suppressed useful findings before adding a new lens. Suggest extraction where evidence supports it; file size alone is insufficient.
4. Keep standalone remediation and managed acceptance consistent. Surface changed accepted source and new tests outside declared scope. Reconcile authorized behavior and scope, obtain only genuinely missing decisions, and revalidate affected evidence. Never update hashes merely to make an old acceptance appear current.
5. Use the existing improvement ledger to link observations → proposals → regression/agent evaluations → adoption or rejection. Record measured outcomes and uncertainty; no second ledger or mandatory essays for routine successes.

Evaluation cases: an optional robustness suggestion presented as mandatory; a true violation of a broad guarantee; conflicting scope exceptions; a multi-responsibility module; a legitimate small module that should stay intact; and post-close remediation introducing a new test file. Include the current task-tracker acceptance drift as a reconciliation scenario without editing that live project during framework development.

## F. Comparative lifecycle trials

After deterministic failures are fixed, compare the repaired lifecycle with a shorter route on matched small tasks. Include a medium task to examine behavior beyond this one example. Use fresh checkouts and agent contexts, comparable models/settings, the same human requirements, and independent outcome assessment. Repeat enough to reveal obvious variability; treat a small sample as directional evidence.

Measure requirement satisfaction, independently demonstrated defects, unnecessary behavior, meaningful regression coverage, fix-induced defects, human product decisions versus recovery interruptions, review retries, model usage, and active execution time separately from wall-clock waiting. Artifact size is a cost indicator, not a correctness metric.

Evaluate lifecycle routing by behavioral ambiguity, interfaces, reversibility, and failure impact, not line count alone. Preserve explicit human preferences. A shorter route must still establish intent, meaningful test-first evidence, review, locks, and implementation verification.

Keep planning, test preparation, and review/locking as independently resumable stages. Split them into distinct phases if measured context pressure or recovery reliability warrants it; combine user-facing steps where that improves usability without hiding consequential decisions. Test fresh-author handoffs against continued-context authoring before imposing a reset every round.

## Delivery and release criteria

- Write meaningful regressions before assigning implementation fixes. Keep those tests fixed during the fixing assignment; proposed test corrections come to the user with evidence. For intentional contract changes, explain the corresponding fixture/expectation updates explicitly.
- Deliver small, reviewable source changes on the current branch while preserving existing work. Update the active hooks/scripts, skills/agent capabilities, installation assets, and tests together. Do not retain obsolete alternate instructions as compatibility clutter.
- Run focused tests per package and the required integration/installer checks at integration boundaries. Use isolated agent exercises for semantic behavior; passing deterministic tests does not prove reviewer quality.
- Before another end-to-end trial, A and B must reproduce and close the original failure scenarios. C and D must demonstrate usable execution evidence and fix/test verification in controlled exercises. E must prevent acceptance from silently drifting after standalone changes.
- Do not require zero review findings or zero human questions. Success is preserved requirements and useful tests, no demonstrated workflow deadlock or false completion, and a measurable reduction in avoidable retries and operator recovery work.
- Phase-profile defaults and broad review-budget changes remain experimental until F supplies evidence. Separate framework repair cost from ordinary task cost when assessing the next run.
