# Discipline restoration and fresh assessment — 2026-09-11

Three scoped implementation agents completed the authoring, reviewer and consultation
changes. Three different fresh-context agents then independently compared the current
sources against `e889a0b` and, where relevant, the earlier specialized reviewers at
`c2a03c6`. Assessors received the user constraints, original sources and raw pre-change
files, without implementation summaries or prior audit conclusions. No live model
benchmark was run. This report records that requested assessment; it does not treat
newly identified concerns as already repaired.

The restoration is substantially correct and preserves the streamlined architecture.
The fresh assessment does not establish complete legacy coverage or empirical parity.
Its strongest residual findings concern delivery of authoring instructions and the
actual source evidence needed by change-sensitive review.

**Changes completed**

| Track | Result |
| --- | --- |
| Authoring | Added [repository grounding](../../assets/fbk-docs/workflow/repository-grounding.md) and routed design/spec/breakdown/implementation authors to it. Restored existing-implementation search, distinct callers, dependency verification, producer/value/consumer wiring, applicable result/error handling and complete agreed migrations. Existing and planned behavior are distinguished. Fresh task packets embed the installed guidance; missing/empty/unreadable guidance produces an actionable diagnostic. |
| Reviewer | Extracted [test integrity criteria](../../assets/fbk-docs/review/test-integrity.md) shared by standalone test review and managed breakdown/implementation. Guidance participates in review identity; managed output schemas remain unchanged. Test-specific evidence instructions are phase-scoped. Added affected durable-doc discovery to existing detection audits. Narrowed fresh-eyes exceptions to authorized changes and legitimate deferrals that preserve current obligations. |
| Consultation | Added six concrete [selected-role responsibilities](../../assets/skills/fbk-council/references/consultation.md), including user burden/lost value and measurement/collection evidence. Preserved Builder/Architect cost duties, source-based challenge, minority concerns and bounded discussion. |

The script changes deliver prompt content through existing entry points. The task
packet gains descriptive authoring guidance; the existing 16,000-character limit
remains. Its shared grounding text adds approximately 2,287 characters. SubagentStart
now emits the existing nonblocking attention diagnostic when a workflow error would
previously have been silently discarded. No acceptance gates, review stages, budgets,
review-result schemas or task-state schemas were added.

**Fresh findings and lead judgment**

| Finding | Evidence and consequence | Judgment |
| --- | --- | --- |
| Fresh test workers still lack stage-specific authoring guidance | [Task packets](../../assets/fbk-scripts/fbk/workflow/handoff.py#L425) embed grounding, while real-interface, discriminating-fixture, minimal-stub and meaningful-red duties remain in the lead's [breakdown guide](../../assets/fbk-docs/workflow/breakdown.md#L41). The handoff explicitly routes delegated design/spec authors but lacks an equivalent test-worker route. A worker can construct a mock that supplies the effect it claims to verify. Legacy implementation guidance explicitly loaded a matching task-type leaf. | Accept as a concrete instruction-routing omission. Route only relevant test-authoring content to test workers through the existing packet; do not send lead-only phase administration or add another reviewer. This restores prevention before review. |
| Shared-convention discovery/reconciliation lacks an explicit authoring trigger | [Grounding](../../assets/fbk-docs/workflow/repository-grounding.md#L3) covers existing code/configuration, but does not explicitly distinguish authoritative shared conventions from an exceptional existing implementation or resolve consequential conflicts. Legacy `e889a0b:assets/fbk-docs/fbk-sdl-workflow/design-guide.md:19` did. A locally coherent event/config interface can contradict a governing convention. | Accept a narrow semantic addition: discover the applicable shared authority and surface a consequential unresolved conflict with a recommendation, preserving settled decisions. No mandatory conventions inventory or new approval gate. |
| Managed change-sensitive review lacks old source bodies | [Review inputs](../../assets/fbk-scripts/fbk/workflow/review.py#L823) supply lock names/red evidence and historical hashes/checks; [snapshot policy](../../assets/fbk-scripts/fbk/workflow/review_context.py#L13) excludes Git. [Test criteria](../../assets/fbk-docs/review/test-integrity.md#L11) and branch-change audits require before/after content. Authorized assertion changes, retired tests and changed conditions cannot be fully compared from the current input. | Accept as the highest-priority evidence-delivery gap. Stronger prose cannot supply missing assertions. Determine which existing revision-bound original sources can be captured and delivered narrowly; keep reviewer opinions excluded. Do not claim a comparison was completed from hashes. The current instructions properly expose missing evidence, but may therefore leave review incomplete. |
| Embedded managed methodology references an unavailable leaf | [Shared detection](../../assets/fbk-docs/fbk-review-lenses/shared-detection.md#L9) and [detection audits](../../assets/fbk-docs/review/detection-audits.md#L27) refer to the remediation-verification section of code-review-guide.md, which the [managed guidance loader](../../assets/fbk-scripts/fbk/workflow/review.py#L479) does not supply. A global installation cannot assume that document exists in the reviewed project snapshot. | Accept a narrow loading omission. Supply the applicable methodology, not the entire standalone orchestration. Some core verification principles already reach reviewers; this is not complete absence of verification. |
| Managed Guardian lacks an explicit degenerate-number search target | Consultation retains zero/negative/non-finite configurable values. Managed Guardian focus plus common prompts direct boundary/failure review generally, without this particular target. A zero timeout or NaN comparison could silently disable behavior. | Medium-confidence specificity loss, not a demonstrated miss. A conditional selected-Guardian instruction is reasonable to consider; it is not evidence for restoring all persona examples or adding a stage. Other shorter Council role descriptions are adequately covered by combined operative prompts and were not elevated to findings. |

An inherited lower-priority inconsistency remains in standalone doc reconciliation:
its decision/changelog comparison wording is broader than the authority/supersession
and release-timing distinctions in the restored managed detection guidance. It may
produce advisory noise after legitimate change. It predates this restoration and
was not presented as a newly introduced defect.

The first two residual findings can be addressed through semantic content and existing
worker loading. The unavailable methodology is also a loading repair. Baseline source
delivery requires inspecting the available original artifacts and implementing a
reliable input path; it cannot honestly be described as a wording-only repair. This
assessment does not authorize a new history subsystem or infer that prior reviewer
opinions should be exposed.

**Preserved disciplines confirmed by the fresh assessors**

All three assessors recognized stronger concrete guidance and proportionality.
Repository reuse, callers, runtime wiring, complete migrations, and planned-versus-
existing work now have operative authoring instructions. Managed reviewers actually
receive code and test failure searches. Fresh-eyes preserves current authority while
allowing planned work. Standalone consultation has concrete roles and retains early
cost/simplification discussion. Fresh initial Council readers, complete candidate
dispositions, supported minority findings, bounded stages, and explicit user authority
remain intact. No assessor justified restoring removed personas, weighted consensus,
full discussion histories, private signature mandates or additional ceremony.

**Validation**

- Combined Python suite: **630 passed, one known pre-existing failure** in
  `test_workflow_code_review_pipeline.py::test_runtime_neutral_handoff_rejoins_full_records_for_material_declaration`.
  It expects `declaration['finding']['mechanism']`; the finding reference and full
  finding evidence are stored separately. This assertion and production behavior
  were not changed in this task.
- Benchmark regression suites: **75 passed and 24 subtests passed**.
- Authoring agent focused checks: **56 passed**. Reviewer agent focused checks:
  **44 passed**. These overlap the combined suite and are not additional totals.
- `git diff --check` passed. Generic skill validation rejects the repository's
  pre-existing Claude `argument-hint` metadata; it was not removed to satisfy an
  incompatible validator.

Runtime tests establish content delivery, stage scoping, identity changes and clear
missing-guidance behavior. Fresh analysis establishes source-supported instruction
and input gaps. Neither establishes measured model compliance, detection-quality
parity or fewer defects created. The next evaluation should continue to separate
those outcomes from review round counts, apparent agreement and green transport tests.
