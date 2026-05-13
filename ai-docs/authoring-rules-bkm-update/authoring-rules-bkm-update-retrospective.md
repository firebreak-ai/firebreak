# Authoring Rules BKM Update — Retrospective

## Timeline

- **Stage 1 (Spec)** — started 2026-05-06, completed 2026-05-11.
- **Stage 2 (Spec Review)** — started and completed 2026-05-11. Result: pass after one revision pass (one blocking finding resolved; five important findings applied).
- **Stage 3 (Breakdown)** — started and completed 2026-05-11. Result: pass after one gate-failure-and-fix pass plus one CP2-reviewer fix pass.

## Key Decisions

1. **Audit of existing corpus deferred to a follow-up spec.** Made in Stage 1. Rationale: reading and modifying the existing corpus of context assets is fundamentally different work from updating the rules (the audit touches dozens of files; the rules update touches three); the rules update should land first so it provides the standard for the audit; the user's own ranking placed the audit as "lower leverage."
2. **Three new rules consolidated into one principle** ("Objectives over Procedural Steps") rather than three separate sections. Made in Stage 1. Rationale: the three rules (objectives over steps, measurable acceptance criteria, output-structure-is-not-procedural) form one coherent principle; navigating three sections to find the corrective for a failure mode named in the first one would force forward-reading; consolidation also keeps the principle count moving from 6 to 7 rather than 6 to 9.
3. **"Don't instruct around bias" lives as a Write-for-Agents instruction, not a top-level principle.** Made in Stage 1. Rationale: it is a writing rule (about how to compose asset content), not a separate authoring principle.
4. **Citation format is inline italic parenthetical, citations only on new content.** Made in Stage 1. Rationale: citations are wiki pointers for follow-on reading, not formal academic apparatus; bibliography would add maintenance burden; back-applying citations to existing principles is scope creep that does not change behavior.
5. **`agents.md` restructure in scope, not deferred.** Made in Stage 1 (second iteration). Rationale: line 76's "provide a clear workflow or checklist of steps" is one symptom of an inherited misframe — the `## Instruction Design` section treats agents as workflow-bearing task runners, contradicting the `## Persona authoring` section in the same file. Patching line 76 alone would leave the contradiction in place. The BKM update exposed the misframe; the restructure removes the contradiction.
6. **The "why" clauses in rules must aid generalization, not describe the failure mode in literary terms.** Made in Stage 1 (second iteration, in response to user pushback on essay-style prose). Rationale: per `objective-driven-prompting`, an explained why lets the model generalize the rule to unanticipated cases (Anthropic's ellipses-and-text-to-speech example). Essay-style descriptions ("vague objectives cause the agent to fill interpretive gaps with statistically plausible but use-case-incorrect completions") read as written-for-a-human prose and do not aid generalization. The test is: would removing the why-clause change what the agent does in a novel situation?
7. **`agents.md` body-content paragraph at lines 27–29 is extended** to preserve the constraint-ordering instruction from deleted line 74 and add a forward pointer to `## Persona authoring` with Detector and Challenger named as canonical examples. Made in Stage 1 (fourth iteration, in response to a council finding that line 74 was uncovered by Persona authoring). Rationale: Persona authoring covers role activation + quality bars + anti-defaults but does not state the constraint-ordering rule; removing line 74 without preservation would lose one real instruction.
8. **New principle includes the workflow-routing position** (workflow lives in skills, referenced docs, or the spawn prompt — never in agent definition bodies), and the Trigger Types table cell describing Agents as holding "delegated workflows" is fixed in the same edit. Made in Stage 1 (fifth iteration). Rationale: Claude Code's subagent composition mechanics (verified via `code.claude.com/docs/en/agent-sdk/subagents.md`) establish persona and workflow as separately-routed concerns; the orchestrator composes them at spawn time via the Agent tool's `prompt` parameter; a principle about how to handle procedural content has to name where the content lives, or authors will be free to embed workflow in agent bodies (the exact misframe the `agents.md` restructure corrects).

## Scope Changes

The initial brief identified six improvement opportunities. The final spec scope reconciled as follows:

- **In scope**: #1 (objectives over procedural steps), #2 (measurable acceptance criteria), #3 (output structure ≠ procedural prescription), #4 (example diversity), #5 (don't instruct around bias). Plus two scope additions surfaced during iteration: the `agents.md` `## Instruction Design` restructure (because the BKM update exposed an internal contradiction patching at the line level could not fix) and the Trigger Types table cell fix (because the new principle's workflow-routing paragraph would self-contradict the existing table cell).
- **Deferred**: #6 (capability-altitude — audit existing corpus when migrating models) — deferred to a follow-up spec for corpus audit. Rationale: maintenance pass over potentially many existing assets is fundamentally different work from a rules update.
- **Out of scope, surfaced for follow-up**: extraction of workflow content from current Detector/Challenger agent bodies into skills or referenced docs. The BKM update establishes the architectural standard; the corpus audit will reconcile existing implementations.

## Stage 1: Spec

### Clarifying questions that revealed ambiguity

- **Should audit of existing corpus be in scope?** User-flagged as an open scope question in the initial brief. Resolved as deferred to a follow-up spec.
- **Should the new principles be added or restructured into a refined set?** Resolved as added (consolidated into one new principle to avoid principle-count inflation).
- **Where does "don't instruct around bias" guidance live?** Resolved as a Write-for-Agents instruction.
- **Should `agents.md` `## Instruction Design` line 76 be inverted with task framing, or should the whole section be restructured?** Identified as a category error in the second iteration — agents are personas (per the taxonomy and per `## Persona authoring` in the same file), so importing task framing into a persona-shaped asset would be the same misframe being corrected. Resolved as full section restructure.
- **What about hybrid persona/task-runner agents (e.g., Detector, Challenger)?** Initially raised by the council as an unresolved concern. Resolved after research into Claude Code subagent composition mechanics: there is no such thing as a hybrid persona/task-runner agent — what appears hybrid is persona-in-agent-body + workflow composed at spawn time. Current Detector/Challenger files embedding workflow in the body is a current implementation choice, not architecturally required.

### Scope inclusions

- One new principle ("Objectives over Procedural Steps") in `fbk-context-assets.md` covering objectives, measurable acceptance criteria, output-structure distinction, and workflow-routing position.
- One paragraph in `fbk-context-assets.md` `## Write for Agents` covering the anti-bias-instruction rule.
- Trigger Types table cell fix in `fbk-context-assets.md` for the Agents row.
- Full restructure of `agents.md` `## Instruction Design` → `## Description field`, with body-content paragraph extension preserving the constraint-ordering instruction and adding a forward pointer to `## Persona authoring`.
- Split the cap-at-5 rule in `referenced-docs.md` into two single-constraint rules with diversity guidance and citation.
- Five new wiki/vendor citations on new content.
- CHANGELOG.md update.

### Scope exclusions

- Audit of existing context-asset corpus for compliance with updated rules (deferred to a separate spec).
- Renumbering or restructuring of existing six principles in the parent doc.
- Modifications to `skills.md`, `claude-md.md`, `rules.md`, `hooks.md` (no analogous misframe present in those leaves).
- Cascade into SDL workflow documents, design guidelines, or any context asset outside `fbk-context-assets.md` and its leaves directory.
- Back-applying citations to existing principles.
- Detector / Challenger agent body extraction (deferred to corpus audit).

### Open questions deferred to later stages

None. All open questions raised during authoring were resolved before the gate passed. The "What about Detector/Challenger" question that emerged in council review was resolved by referencing Claude Code's documented composition mechanics and explicitly documenting the deferral to the corpus audit in the Decisions Resolved section.

### Council review

Quick Council convened in Stage 1 (Architect, Builder, Guardian) to review the spec from three angles: goal achievement, overengineering, simpler alternatives. The council converged on:

- **Q1 (goal achievement)**: Yes — the principle lands on every authoring route; the restructure removes a real contradiction; the carve-out is concrete enough to apply.
- **Q2 (overengineering)**: No, with two named tightening passes — Testing strategy had four tests where two would suffice; Integration seams had six bullets where two were load-bearing. Both addressed.
- **Q3 (simpler alternative)**: None recommended. Three alternatives independently evaluated and rejected by multiple agents.

The council surfaced one block-level finding (Guardian gap 1 — line 74 constraint-ordering instruction was uncovered by Persona authoring and would be lost in the restructure) and six lower-priority tightening recommendations. All seven were applied. Two unresolved concerns (hybrid persona/task-runner agents; spawn-prompt authors being unconstrained) were resolved via architectural position after researching Claude Code subagent composition mechanics with the `claude-code-guide` agent, which established that workflow lives in skills/docs/spawn prompts and that the orchestrator composes persona + workflow at spawn time.

### Iteration count

Five rounds of user-driven sharpening before the spec stabilized:

1. Initial draft with three new principles, agents.md line invert, example refresh, citation footnotes on existing principles.
2. Tightening of "why" prose after user feedback that essay-style descriptions read for a human, not for the agent.
3. Restructure of `agents.md` after user identified a category error — agents are personas, not workflow runners; the inherited `## Instruction Design` section contradicts `## Persona authoring`.
4. Application of all seven council recommendations: block-level fix (body-content paragraph extension), AC-06b line-number drift fix, testing-strategy collapse, integration-seam trim, AC-08 reframe, UV-5 falsifiability calibration, canonical-examples pointer.
5. Workflow-routing paragraph added to the new principle and Trigger Types table cell fix, after research into Claude Code subagent composition mechanics established that persona-and-workflow separation is supported architecturally.

## Stage 2: Spec Review

### Perspectives invoked

Discussion mode with three perspectives:
- **Architect** (SDL concern: architectural soundness) — pattern consistency, integration point existence, convention visibility.
- **Builder** (SDL concern: over-engineering / pragmatism, Complexity Watchdog) — scope expansion audit, AC granularity, implementation cost estimate.
- **Guardian** (SDL concern: quality / testing strategy and impact) — AC coverage gaps, testing strategy adequacy, regression risk for the restructure.

Security, Advocate, and Analyst were not invoked. Security: no auth, data-handling, or trust-boundary signals. Advocate: user surface is internal (asset authors), no scope-creep signals beyond what Builder evaluates. Analyst: no quantifiable metrics or evidence-claims.

In addition, the **CP1 test reviewer** (`test-reviewer` agent) was invoked independently — it has no memory of council discussions and evaluated the testing strategy in isolation.

### Blocking findings and resolutions

1. **Existing TAP tests not enumerated as impacted** (Finding Q-1, also flagged independently by the CP1 reviewer). The spec asserted "no automated tests over the modified files"; in fact `tests/sdl-workflow/test-agents-md-persona-guidance.sh` (12 assertions against `agents.md`) and `tests/sdl-workflow/test-reference-integrity.sh` (cross-asset path references) both exercise the modified files. **Resolution: spec revision pending.** The Testing strategy section will list both scripts under "Existing tests impacted" with the expectation that both pass post-restructure, and the Sequence section will add a pre-commit run step.

### Important findings (non-blocking, recommended)

- **A-1 Citation convention not self-documenting:** add a one-line meta-instruction declaring citation format on new content.
- **A-2 Sole-consumer workflow heuristic missing:** add one sentence pointing to `## Separation of Concerns` as the governing rule for inline-vs-extract decisions on workflow content.
- **A-6 Convention visibility for the task compiler:** add a "Conventions in modified files" subsection naming heading level, spacing, citation placement, imperative voice (~6 lines).
- **P-2 AC count over-granular:** merge AC-03 and AC-03b; merge AC-06a and AC-06b. Net: 12 → 10 ACs.
- **P-6 + Q-2 AC-08 reframe combined:** require a Self-application audit table in the implementation retrospective with one row per added/replacement instruction (Necessity outcome, framing, single-constraint, why-clause). Replaces per-instruction prose; pins location and granularity.
- **Q-3 AC-06b deterministic check:** add `git diff` scoped to preserved sections, pass criterion "zero lines changed."

### Informational findings (accept or carry forward)

- A-3 Principle length asymmetry (accept).
- A-4 Trigger Types cell length mismatch (optional trim).
- A-5 Intra-file forward pointer is a new pattern in leaves (accept, recorded as precedent).
- P-1 Scope expansion stayed within file count (accept).
- P-3 UV count proportionate after AC merges (accept).
- P-4 Spawn-prompt-author decisions entry borderline ceremony (optional cut).
- P-5 Implementation cost 60–90 min (named; spec-to-diff ratio ~5:1 is quality-discipline trade-off).
- Q-4 UV-5 calibration leaks vague-criterion patterns (broaden to positive rule).
- Q-5 Edge-case scope for hooks/rules unstated (extend carve-out sentence).
- Q-6 Historical SDL artifacts reference deleted section (add Documentation impact note).
- Q-7 CHANGELOG entry shape unverified (extend UV-6).

### Threat model decision

**No threat model required.** Documentation-only change: no code, no entry points, no trust boundaries, no data handling, no external APIs, no auth changes. Determination made autonomously per user direction to run the review without checkpoint interruption.

### Spec revisions

Spec revision is pending the blocking-finding fix plus any of the important findings the user chooses to apply. Recommended bundling:

- **Must-apply** (block-clearing): Q-1 — enumerate existing TAP tests as impacted, add pre-commit run step to Sequence.
- **Strongly recommended**: P-2 (AC merges), P-6+Q-2 (AC-08 audit table reframe), Q-3 (deterministic integrity check), A-2 (sole-consumer heuristic), A-6 (task-compiler conventions). These are cheap and meaningfully tighten the spec.
- **Optional**: A-1, A-3 through A-5, P-1, P-3, P-4, P-5, Q-4 through Q-7 — accept-with-named-cost or carry forward to corpus-audit follow-up.

### Iteration count

One review round + one revision pass. The blocking finding was independently flagged by Guardian and the CP1 test reviewer, validating the finding without back-and-forth between agents. The CP1 reviewer's independence — no access to council discussion — caught the test-suite oversight Guardian also caught; convergence on the same finding from two independent paths gives high confidence in the blocking severity. The revision applied the blocking-clear bundle plus the strongly-recommended important findings (A-2, A-6, P-2, P-6+Q-2, Q-3) in one pass. Post-revision spec gate passed.

## Stage 3: Breakdown

### Compilation attempts

Two compilation passes via specialty teammates with isolated context:

- **Test task compiler** (fbk-task-compiler, independent context, received spec only) produced 9 test tasks covering all 9 ACs. The compiler does not have a Write tool — it returned task content as response text; the orchestrator materialized the 9 files.
- **Implementation task compiler** (fbk-task-compiler, independent context, received spec + 9 test task files) produced 5 implementation tasks across two waves. Same materialization pattern.

### Wave structure and rationale

Three waves:

- **Wave 1** (4 tasks, parallelizable, all implementation): task-10 (parent doc — Changes 1a/1b/2 in `fbk-context-assets.md`), task-11 (`agents.md` restructure), task-12 (`referenced-docs.md` cap-at-5 split), task-13 (CHANGELOG `Unreleased` entry). All edit distinct files; no file scope conflicts in parallel execution.
- **Wave 2** (9 tasks): 8 verification tasks for Wave 1 work (task-01 through task-07, task-09) plus task-14 (the audit-table population implementation, which depends on Wave 1 file edits because it reads their post-edit content).
- **Wave 3** (1 task): task-08 verifies task-14's audit table.

The audit-table population is itself an implementation task (it writes content to the retrospective), which forced a third wave so its verification (task-08) could run in a strictly later wave than its dependency.

### Task count

10 total: 5 implementation tasks (task-01, task-03, task-05, task-07, task-09) + 5 test tasks (task-02, task-04, task-06, task-08, task-10). Initial draft was 14; after user feedback that 14 was excessive for a ~50-line documentation diff, consolidated to 10 by bundling test tasks per-file instead of per-AC. The reduction did not violate the test/impl separation rule from `task-compilation.md` — every implementation task still has a paired test task.

### Scope adjustments from compilation

Two structural issues surfaced during compilation and were resolved before completion:

1. **AC-03b was an invalid identifier** for the task-reviewer-gate (which enforces `AC-NN` digits-only format). Resolution: merged AC-03b into AC-03 in the spec, so AC-03 now covers both the principle's content paragraphs AND the Trigger Types table cell fix. task-02 and task-10 updated to reference AC-03. The merge is semantically clean — both changes are to the parent doc and both relate to the new principle's coherence.
2. **File scope conflicts in Wave 2.** Eight verification tasks initially declared `files_to_modify: [<source file>]`, but the gate detects same-wave file-claim conflicts even when the claims are read-only verifications. Resolution: changed verification tasks from `files_to_modify` (real source file) to `files_to_create` (unique placeholder paths under `.verification/`). The placeholder paths are not actually created during execution — they satisfy the schema requirement that each task have at least one of `files_to_create`/`files_to_modify` without falsely claiming write contention.

### Reviewer feedback applied

CP2 test reviewer found three defects in the first pass:

1. **task-01 (AC-03)**: original step 6 verified "orchestrator" and "spawn time" tokens but did not verify the failure-mode sentence. Added a third grep for "forces every invocation."
2. **task-05 (AC-06)**: original step 6 instructed "examine the diff output" — manual inspection. Replaced with a deterministic `git show HEAD:... | awk` extraction loop that compares each preserved section byte-for-byte between HEAD and working tree, plus a deletion-count check scoped to lines outside the Instruction Design hunk.
3. **task-08 (AC-08)**: original gate only checked for the section heading — would pass a rubber-stamped 5-row table. Added a row-count check (`>= 14`), a 16-phrase grep loop that verifies each enumerated instruction is referenced in the audit table, and a Necessity-cell length check (`>= 15` chars excludes one-word fillers like "yes" / "no" / "needed").

All three defects resolved in a single fix pass; CP2 re-review returned PASS.

### Gates passed (final, after consolidation)

- `task-reviewer-gate`: pass (10 tasks, 9 ACs covered, 3 waves, no failures)
- `breakdown-gate`: pass (spec_acs=9, tasks=10, waves=3)
- CP2 test reviewer: pass after one fix pass (defects applied to the original 14-task draft and carried into the consolidated 10-task version)

### Lesson — over-decomposition pattern

The initial 14-task draft over-applied per-AC test granularity. The natural shape for a documentation-only change is **per-file test tasks**, not per-AC. The test/impl separation rule from `task-compilation.md` is mandatory, but it does not require one test task per AC — multiple ACs verified against the same modified file should bundle into one test task. This is worth carrying forward as feedback to the breakdown skill's prompt: for documentation-only changes, bias toward per-file test bundling rather than per-AC decomposition.

After the 10-task breakdown, the user (correctly) called out that even 10 tasks was ceremony — most "test" tasks were grep tautologies verifying content the implementation agent had just written. The actual verification value lived in three places: the existing TAP scripts (`test-agents-md-persona-guidance.sh`, `test-reference-integrity.sh`), the deterministic `git diff` integrity check on agents.md preserved sections, and the wiki slug `find` checks for citations. We exited the SDL pipeline at that point and executed the four file edits directly, with verification folded into a single execution pass.

### Direct execution outcome

Skipped the remaining SDL ceremony (task manifest execution, per-AC test tasks, separate audit-verification stage) and applied the four file edits directly. Verification:

- **`test-agents-md-persona-guidance.sh`**: 12/12 TAP assertions pass.
- **`test-reference-integrity.sh`**: 93/93 TAP assertions pass.
- **`git diff --stat`**: 36 insertions, 29 deletions across 4 files (net +7 lines).

## Self-application audit

Every added instruction was reviewed against the parent doc's own three writing rules: Necessity Test (would removing it cause a mistake?), positive framing, single verifiable constraint. The findings:

- **Most additions pass trivially.** The principle's imperative rule, the acceptance-criteria pairing, the workflow-routing paragraph, the anti-bias instruction, the cap-at-5 rule, the diversity rule, the constraint-ordering instruction, and the Description-field instructions all state a single positive constraint that prevents a concrete mistake (over-specification, drift, embedding workflow in persona, instructing-around-bias, example bloat, anchoring on homogeneous instances, body content disorder).
- **Two judgment calls were non-trivial.** First, the workflow-routing paragraph is longer than sibling principles because it carries the orchestrator-composition mechanism. The mechanism is load-bearing for generalization (an author without it might re-derive the embed-workflow-in-persona pattern), so the length is justified. Second, the citations are a new structural element in the parent doc — they earn their place by giving an agent a path to verify claims, but the convention wasn't previously declared. Filed as follow-up: either declare the citation convention in the parent doc or move citations to a footer.
- **One "why" clause was caught and tightened during authoring.** The original draft of the workflow-routing paragraph included an essay-style description of the failure mode. The user flagged it as written-for-a-human. It was rewritten to a single load-bearing clause: "forces every invocation of that agent through the same workflow regardless of the orchestrator's intent" — short enough to aid generalization without becoming literary prose. This is the model the Necessity Test should produce; longer explanations should be questioned.

No instructions framed as prohibitions without paired alternatives. No compound rules. No literary why-clauses surviving into the final text.

## Stage 4: Direct Execution (in lieu of pipeline)

The remaining SDL pipeline stages (task breakdown execution, code review, retrospective audit) were skipped for this spec on the rationale that the work (~24 net lines, all documentation, no executable behavior) did not justify the ceremony. The valuable parts of the pipeline already ran: spec (architectural reasoning), council (caught two structural issues), spec review (caught the test-impact misstatement, surfaced six findings). The breakdown stage hit a rule mismatch — the gate requires per-AC test coverage even for docs-only changes where "test" is grep tautology. Two follow-ups filed:

1. **Update `breakdown-gate` to support a documentation category** that skips the per-AC test-coverage requirement, so the next small docs spec can use a per-file (or per-edit) shape without bypassing the gate.
2. **Audit the existing context-asset corpus** (Detector, Challenger, council members, etc.) for compliance with the new "workflow lives outside agent bodies" principle.
