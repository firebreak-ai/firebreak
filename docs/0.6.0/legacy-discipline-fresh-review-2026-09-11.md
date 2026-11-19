# Fresh legacy comparison — 2026-09-11

## Conclusion

Three fresh, separately scoped assessors found **no confirmed material remaining
regression** in the reviewed authoring, reviewer and Council disciplines. The current
working tree preserves the relevant legacy failure-prevention objectives through
shared references, explicit worker delivery and deterministic workflow controls.
This is a source-supported assessment, not proof of equal or better live-model
effectiveness.

## Method

Each assessor started without conversation history and received only its track,
original source locations, applicable operator decisions and assessment criteria.
They compared the current working tree with `e889a0b` (before the 0.6 rewrite) and
`c2a03c6` (earlier specialized agents), using original Git sources. Prior audit,
restoration and follow-up reports were excluded. Assessors worked independently
and made no product edits, installations or live model calls.

The three tracks were reviewer detection/test review/challenge/source access;
authoring/test preparation/task handoffs; and Council roles/deliberation/complexity
decisions. Findings required a concrete failure consequence and checking equivalent
coverage in actual loading paths. Missing legacy wording alone was insufficient.
The lead checked shared installation and delivery paths, inspected reported evidence,
and requested a narrow follow-up on standalone documentation reconciliation.

## Coverage retained or improved

| Track | Source-supported result |
| --- | --- |
| Authoring | [Shared grounding](../../assets/fbk-docs/workflow/repository-grounding.md) preserves searches for existing implementations, distinct callers, verified dependencies, producer-to-consumer wiring, error/result composition and complete migrations. [Spec](../../assets/fbk-docs/workflow/spec.md) settles conventions before breakdown; tasks carry their governing references. Organization is judged through concrete responsibility, dependency, cohesion and maintenance consequences. |
| Test preparation and handoffs | [Test authoring](../../assets/fbk-docs/workflow/test-authoring.md) retains real production boundaries, discriminating fixtures, meaningful behavioral failures, minimal stubs and preservation checks. [Task packets](../../assets/fbk-scripts/fbk/workflow/handoff.py) load installed canonical guidance, with test-specific content limited to test assignments. Required checks execute independently, and accepted preparation evidence retains its source lineage. |
| Reviewers | [Detection references](../../assets/fbk-docs/review/ai-failure-modes.md), [test integrity](../../assets/fbk-docs/review/test-integrity.md), researcher and challenger instructions retain concrete mechanisms, triggers, caller impact, vacuous tests, mock fidelity, stale markers, integration coverage and justified retirement. [Managed review](../../assets/fbk-scripts/fbk/workflow/review.py) embeds applicable guidance; standalone skills explicitly compose it. |
| Source and execution evidence | [Snapshot policy](../../assets/fbk-scripts/fbk/workflow/review_context.py) excludes workflow/session history while retaining original-source investigation. [Baseline selection](../../assets/fbk-scripts/fbk/workflow/review_baseline.py) supplies at most the latest applicable accepted source tree, with explicit unavailability. [Investigations](../../assets/fbk-scripts/fbk/workflow/investigations.py) enable executable checks in disposable workspaces. Normalized challenger inputs and missing-evidence dispositions reduce unsupported acceptance. |
| Council | [Consultation](../../assets/skills/fbk-council/references/consultation.md) retains all six role quality bars. Early authoring owns the Builder's cost/simplification duty and the operator's decision. [Managed Council](../../assets/fbk-scripts/fbk/workflow/council.py) supplies phase-specific responsibilities, conditional Guardian numeric guidance, independent initial readers and complete candidate dispositions. Supported minority findings survive; no-findings results avoid extra stages and required-reader failures cannot silently fall back. |

Blanket private-signature prescriptions, numerical task-size rules, mandatory mock
policies, transcript-heavy deliberation and unconditional numeric matrices were not
treated as safeguards to restore. Their material objectives are represented by
behavior-oriented instructions consistent with the operator's current decisions.

## Remaining limitations

**Inherited documentation-reconciliation noise.** The standalone
[doc-reconcile skill](../../assets/skills/fbk-doc-reconcile/SKILL.md) loads its own
[lens](../../assets/fbk-docs/fbk-review-lenses/doc-reconcile-lens.md), which still
treats recorded decisions and changelog discrepancies broadly as drift. These
rules are unchanged from `e889a0b`. The newer operative-authority and release-timing
qualifications in [detection audits](../../assets/fbk-docs/review/detection-audits.md)
do not reliably reach that route. A superseded decision or historical entry can
therefore produce unnecessary advisory output. The scan proposes no fixes and
does not gate acceptance. This is an inherited noise limitation, not a demonstrated
rewrite regression. An optional narrow remedy would qualify the existing lens
bullets; no additional pass or reviewer is warranted.

**Semantic effectiveness remains unmeasured.** Delivery tests establish available
instructions, not consumption or judgment quality. Standalone review composition
and unassigned design/spec worker routing still depend on the lead following the
explicit instructions. Coverage accounts are model claims even when their shape
is validated. No observed failure justified adding new gates for these duties.

## Validation

| Check | Result |
| --- | --- |
| Fresh authoring/preparation/handoff suites | 67 passed |
| Fresh Council/progress/Guardian suites | 12 passed |
| Fresh reviewer/test-review/baseline/source/pipeline suites | 30 passed, 1 existing failure |
| Lead shared-guidance delivery checks | 14 passed |

These are overlapping focused suites; their counts must not be added together.
The full suite was not rerun for this read-only assessment.

The existing failure is
`test_workflow_code_review_pipeline.py::test_runtime_neutral_handoff_rejoins_full_records_for_material_declaration`.
Its final assertion reads `declaration['finding']['mechanism']`; production preserves
the finding reference there and retains the full record in `finding_evidence`.
Earlier handoff and merged-evidence assertions pass. Inspection supports correcting
the stale assertion, not a claim of lost finding evidence. No test was changed here.

## Recommendation

Do not add more instructions solely to recreate the legacy wording. The next
useful evidence is a bounded live evaluation of missed requirements, meaningful
test catching power, unnecessary findings, review retries, operator interventions
and the cost of a follow-up feature change. Source comparison and passing transport
tests cannot establish those outcomes. Any observed failure should be traced first
to the earliest phase where it could have been prevented.
