# Architecture overview

Firebreak brings Claude Code skills, review role documents, hooks, and a Python workflow runtime to a target repository. The target application does not import Firebreak. Installation places assets in a project or the operator's `.claude/` directory.

## The 0.6.0 workflow

New work opts in with `fbk.py workflow-init` and lives under `.fbk/<unit>/`. A feature proceeds through intent, optional design, spec, breakdown, and implementation. A project defines a parent contract and ends after spec. Small features keep their documents short and omit design when architecture and shared contracts are unchanged. Standalone review skills remain useful without opening a unit.

The [workflow guide](../assets/fbk-docs/state-driven-workflow.md) is the executable process contract. The [0.6.0 plan](0.6.0/plan.md) explains the evidence and decisions; [validation](0.6.0/validation.md) records what has actually been tested. Superseded proposals remain in git history.

Each unit has human-readable requirements (`prd.md`), optional design pages, a behavioral specification (`spec.md`), a repository-relative scope and check declaration (`scope.json`), and task dependencies (`tasks.json`). Private function signatures are implementation choices unless they form a shared contract. Documents define observable success and constraints; they do not attempt to script every reasoning step.

Each document carries one named section of items: `prd.md` has Commitments, each design file Design choices, and `spec.md` Requirements. An item is a heading one level below its section; it links the upstream items it serves with ordinary Markdown links to heading anchors. Design close checks that every design choice links a commitment and every commitment is linked; spec close does the same for requirements against design choices, or against commitments in a unit without design. Both closes name every failing item before any review round is spent. A child's links to its parent's accepted items count. One parser in `traceability.py` reads headings, sections and links for these checks from a defined subset of Markdown: inside a section it accepts only a fixed list of plain line shapes, and it refuses everything else, naming the file, line and item. Its anchor function also resolves task references and reference repairs. Tasks link the requirements they serve by anchor; breakdown close checks that every task links a requirement of its unit and that every requirement is linked by an implementation task and a test task. A requirement whose first line is `Checked by review: <reason>` is review-only: it needs no test task, the spec review judges whether a test truly cannot check it, and the implementation review returns a verdict on each one through every reader and the adjudication pass, with each standing not met verdict recorded as a blocker. At launch a task's context carries its requirements' sections with their design choices and commitments. That chain and the rest of the context each have a 16,000-character limit; breakdown close checks both for every task, launch checks them again, and a refusal names the largest sections or fields.

Source-attributed human decisions are recorded separately from authored requirements. Exact quotes and immutable source hashes make corrections and supersession visible to subsequent agents. Applicable decisions participate in phase revisions. The optional `scope.json` context list names governing contracts and conventions that must remain current.

Breakdown scales the execution plan to the spec. One task is valid, as is a dependency graph with one task per wave and fully serial execution. Independent tasks may run in parallel when ownership and available capacity permit it. Task count and parallelism are not success measures.

## Runtime and evidence

`assets/fbk-scripts/fbk/workflow/` separates storage, evidence, transitions, review execution, close coordination, CLI parsing, and hook adaptation. The dispatcher exposes this package and the standalone review pipeline and cross-model runner.

A versioned `state.json` contains ownership, grants, test locks, review attempts, acceptance evidence, and audit events. Writers use a project file lock and atomic replacement; readers see complete snapshots without taking the writer lock. A checksum detects accidental record corruption. Phase status is derived from recorded facts and the current input files. Adding, removing, or editing an accepted input makes acceptance stale.

Standing sourced repair authority supports narrow reference corrections and prose repairs against already settled intent. A deterministic reference proof can preserve previously current acceptance with a recorded patch. A semantic correction needs an independent source-based check and invalidates affected acceptance while retaining review attempts. A durable pending journal precedes file replacement; recovery completes only the known patch or abandons it with acceptance still invalid.

Close reserves the current revision under lock, releases the lock while running checks and independent review, then revalidates the reservation, ownership, parent contract, and inputs before committing acceptance. A recovered reservation cannot later commit. Review rounds persist across fixes and sessions. Reopening starts a new review generation and supersedes later acceptance. Reopening breakdown or an earlier phase, or a contradiction repair that invalidates breakdown, also clears the test locks and the test checkpoint's acceptance, so tests are reviewed and locked again; reopening implement keeps both.

Scoped tests are whole files matching `scope.json` tests, or test regions: the end of a source file, from the first line a declared start expression matches, for languages that keep unit tests beside the code. A region-bearing file is two things at once. Its region is a scoped test, fingerprinted on its own in the writing-tests baseline, the checkpoint revision, the locks, and the boundary checks; the code above it is a production file. The write hook works out each Edit or Write's result to tell which part changes, and refuses when it cannot. Restore replaces only the region and keeps the code above. Review snapshots and diffs show the file whole.

A plan with no test task is accepted only when every requirement is review-only. Entering implement then records one of two outcomes with the writing-tests baseline, as a `test-outcome-recorded` event that a breakdown-or-earlier reopen, or a contradiction repair invalidating breakdown, clears. When scoped tests exist, a preservation checkpoint runs at once: every declared check must pass, no scoped test may differ from the baseline, its reviewer judges whether the tests protect the code the unit will change, and it locks them. When none exist, the empty inventory is recorded and the unit writes code without a checkpoint or lock; task boundaries and implementation close refuse any scoped test that appears, and implement's review compares against the baseline. Neither outcome allows an unlock, since no test task could rework a test.

Implementation requires a revision-bound authorization and explicit test integrity evidence. A recorded failing check must be declared in scope; a preservation reason supports refactoring existing behavior. The semantic reviewer checks whether failures and assertions exercise the intended behavior. Declared checks execute as argument arrays, with bounded timeouts and no shell interpretation. Headless reviews use authenticated `claude -p` with read-only tools; an optional second reader adds an independent candidate set and adjudication. The default does not require another provider or API credentials.

Intent, design, spec and breakdown each have a persisted single-reviewer or council
choice. `review-plan` records the unit decision; `review-default` records an ongoing
project preference. Hooks and status expose the selection. Design and spec close
require it; intent and breakdown default to one reviewer. Every council includes the
builder. Changing
mode or membership invalidates review reuse and revision-bound approvals without
resetting attempts. Existing accepted evidence stays valid until explicit reopen.

The runtime mediates the council as a short discussion, each step a fresh native
headless session. Members open with independent reads of at most eight proposals,
each takes one turn in a rotating order to contest, concede, withdraw or replace,
then every member supports or contests every proposal. A count decides what stands:
majority support stands with dissent, majority contest drops, a tied suggestion
stands, and a tied blocker gets one second round before standing as a suggestion.
A final session writes the standing proposals as findings at the counted severity.
Member personas and the council brief are shipped review briefs. Any failed or
incomplete session fails the close, with completed step results preserved. Openings
and stances run concurrently outside the transaction lock; long model calls never run inside command hooks. These
reviewers are subprocesses, not teammates in the authoring session.

The optional second reader's assessor delivers corrected operative findings; original candidates and every disposition remain in audit history. Native sessions run with `--safe-mode --restricted` in temporary original-source snapshots, retaining Claude authentication while excluding workflow state, logs and automatic host customization. The full snapshot is rechecked for in-flight changes and cached-review reuse. Governing conventions and additional reported authorities remain acceptance dependencies; mutable implementation targets are distinguished from governing sources.

Review outputs declare completeness and inspected sources. Validation rejects missing inputs and incomplete reports; these declarations remain model claims. Prompts prioritize current phase targets and governing authority, and bounded diagnostic excerpts point to complete captured check evidence inside the snapshot. Optional external reader processes receive the snapshot but depend on their own host for filesystem confinement.

## Hooks and sessions

`UserPromptExpansion` handles direct phase slash commands; `PreToolUse(Skill)` handles model-invoked skills. Both use the same transition engine as explicit `phase-enter`. Covered write tools check ownership, phase, declared scope, and locked tests; breakdown writes tasks only, so no project file is written then, and during implementation only an assigned subagent may write project files. Worker start/stop events prevent closing while known workers remain active. `Stop` supplies bounded feedback, while `suspend`, `takeover`, and `recover-close` make handoffs and interrupted work explicit.

SessionStart prioritizes the current unit and supplies bounded continuation context, including pending work, sourced decisions and remaining attempts. Omitted sections have explicit retrieval commands. Task launch and return records bind outcomes, acceptance references, ownership, supporting inputs and dependency outputs to the accepted breakdown. Close checks task completion and evidence freshness; worker-reported checks supplement independently executed verification. These handoffs support deliberate fresh sessions at completed boundaries without automatically clearing an active conversation.

Hooks are a cooperative workflow aid. Shell commands, external tools, disabled hooks, and command-hook timeouts can bypass prevention. Close independently checks current evidence. Host permissions and sandboxing provide the security boundary.

## Shipped assets

The five phase skills load the shared workflow guide and their phase reference. Council and spec-review skills route units to the same close protocol. The improvement analyst supports evidence-based process analysis. The researcher and challenger role documents under `fbk-docs/review/` supply the reviewer text that standalone rounds include in their instructions; the improvement analyst is the one remaining agent definition. Consultation remains advisory.

The [branch cleanup](0.6.0/cleanup.md) records the retained and removed surfaces. The branch ships one workflow protocol under `.fbk/`. Superseded phase instructions, gates, state management, capture, and their tests remain in git history. Standalone review tools write findings in the project's review directory and do not establish managed acceptance.

Install from this checkout to try this branch. Upgrades prune files no longer shipped and replace unchanged installer-owned hook settings while preserving operator additions. Python commands use `uv run --project <installation>/fbk-scripts python ...`. Command hooks use only the standard library.

## Durable docs and observability

The [testing guide](testing.md) describes behavioral and installation checks and their diagnostic reports.

Keep requirements, accepted evidence, scope, and task history with code in git. `.fbk/runtime/` is ignored and contains locks, recovery copies of saved test evidence, and an optional bounded event log. Events omit prompts and tool arguments; telemetry failure cannot determine policy. `workflow-report` reports recorded review usage only, not total authoring-session cost.

`workflow-report` defaults to current work; `--history` explicitly expands earlier events and review rounds. `current-findings` returns current-attempt evidence with targeted retrieval for additional findings. The [handoff validation](0.6.0/handoff-validation.md) records deterministic checks, mutation sensitivity and the bounded live evaluation, including an initial response-schema pollution failure.

Reports expose capture health without claiming complete host coverage. Optional context-emission records identify packet hashes, sizes, omissions and requested sections; they establish emission, not consumption. Final close-attempt records include the final outcome and operation identity, including rejection after source revalidation. Ambiguous unit attribution remains unknown.

`retrospective <unit>` supplies a bounded evidence index with targeted historical retrieval. Attributed observations separate incident descriptions, source references, suspected causes and uncertainty. `/fbk-improve` routes managed units through that evidence. It investigates relevant causes and permits runtime changes, instruction simplification and no-change conclusions. The unit's improvement ledger binds proposals, adopted target revisions and subsequent evaluations; changed evaluated evidence requires re-evaluation. Adoption is distinct from a demonstrated outcome, and recorded judgments do not establish causality. These records remain outside ordinary handoffs and acceptance-review snapshots. The [observability validation](0.6.0/observability-validation.md) records integration checks and independent skill use.

Every unit initializes an observation ledger. The author appends its own observations throughout each phase and records a phase account citing the latest acceptance event before advancing. Status and continuation preserve pending observations across sessions; final completion and Stop feedback require the final phase account. Clean phases need observations too. Recording is mandatory; historical evidence retrieval and improvement proposals remain separate activities. Observation prose stays outside acceptance-review snapshots.

`GLOSSARY.md` defines terms, `docs/decisions-log.md` records superseding decisions, and this overview describes the current architecture. These plain Markdown docs stay short enough to guide subsequent work. Research does not yet establish long-term maintainability gains for this workflow; evaluate it on real follow-up changes as well as first-pass tests.
