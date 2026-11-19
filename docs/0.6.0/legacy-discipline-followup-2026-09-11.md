# Agreed discipline follow-ups — 2026-09-11

This follows the [fresh restoration assessment](legacy-discipline-restoration-review-2026-09-11.md).
The operator discussed and approved each of its five principal gaps separately.
The earlier report remains a record of the assessment before these follow-ups.

## Decisions and implementation

| Area | Agreed result |
| --- | --- |
| Review comparison | Current original sources remain primary. Readers can investigate the complete current tree and at most one accepted same-phase source baseline. First implementation may use the active accepted breakdown. Missing or untrustworthy capture produces an explicit comparison limitation, never substitution of an older tree. Prior reviewer findings, verdicts and transcripts remain excluded. |
| Test authoring | One [shared authoring reference](../../assets/fbk-docs/workflow/test-authoring.md) supplies real-interface, discriminating-fixture, minimal-stub and meaningful-red duties to the breakdown lead and fresh test workers. Lead administration and review adjudication stay in their respective guides. |
| Conventions | Resolve applicable conventions by spec, optionally earlier through intent, design or grilling. Explicit human decisions govern; otherwise discover applicable existing conventions. Greenfield work need not invent inherited conventions. Downstream workers apply settled authority and investigate implementation facts, surfacing specific consequential conflicts. [Shared grounding](../../assets/fbk-docs/workflow/repository-grounding.md) retains universal responsibility, dependency and cohesion discipline for maintenance and extension within accepted scope. |
| Remediation verification | One [shared methodology](../../assets/fbk-docs/review/remediation-verification.md) reaches standalone review, managed implementation review and fresh delegated remediation verifiers. It distinguishes meaningful regression evidence from setup failures, requires inspection of actual assertions and safeguards, and identifies execution limitations. Runtime protocol and orchestration remain separate. |
| Guardian specificity | The selected Guardian receives a short conditional reference (`assets/skills/fbk-council/references/numeric-controls.md`, since removed) for numeric controls that could disable required behavior. Values are investigation leads judged against the contract and runtime, not universal invalid inputs or a required test matrix. |

Shared text is loaded from the active installation through existing entry points.
Reviewers retain autonomous source investigation and disposable execution. These
changes add no review stages or model-selected style requirements.

## Independent integration assessment

Fresh scoped assessors inspected the actual source and worker delivery paths without
the implementation agents' conclusions. They found a missed standalone verifier
consumer and two baseline defects: unchanged unavailable captures could invalidate
approval retries, and reopening after mechanical reference repair could select the
older acceptance. All three were repaired. The standalone verifier now embeds the
installed canonical methodology. Runtime comparison provenance records what a
reader actually received outside its source tree, allowing reuse of the same
explicit unavailable state while rejecting missing or changed provenance. Reopen
retains the latest accepted source identity without reviewer narrative; a repaired
acceptance with no matching captured bodies is explicitly unavailable.

The fresh follow-up check confirmed standalone verifier delivery and Guardian
reader-cache invalidation. The lead inspected the baseline repairs and their public
approval and repair/reopen regression tests.

## Validation

- Combined Python suite: **658 passed, one known pre-existing failure** in
  `test_workflow_code_review_pipeline.py::test_runtime_neutral_handoff_rejoins_full_records_for_material_declaration`.
  Its assertion reads `finding['mechanism']`, while the full finding evidence is
  stored separately from that reference. The same failure preceded these changes.
- Benchmark regression suites: **75 passed and 24 subtests passed**.
- Baseline repair focused suite: **93 passed**, including real close/approval and
  reference-repair/reopen paths with mocked reader responses.
- Fresh shared-guidance follow-up: **13 remediation tests and 4 Guardian tests passed**.
  Focused counts overlap the combined suite and are not additional totals.
- `git diff --check` and this report's local reference checks passed.

Deterministic tests establish source delivery, comparison selection and retry
behavior; they do not establish live-model compliance, legacy detection parity or
fewer defects produced. No live model evaluations were run for these follow-ups.
