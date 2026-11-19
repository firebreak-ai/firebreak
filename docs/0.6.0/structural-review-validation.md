# Structural review validation

Status: source guidance and both human-approved evaluation corrections implemented; all seven bounded post-change decisions match their expected outcomes.

The canonical code-review guide previously defined structural findings as “you would ship; flag only on request,” while the code lens allowed requesting changes and implementation review already required maintainability inspection. Structural detection targets also read as unconditional triggers for single-use abstractions, mixed I/O and computation, and similar patterns. The updated existing guidance requires a concrete maintenance consequence and permits consequential structural defects to block despite green tests; it explicitly protects reasonable small designs and test seams. No new lens or phase is introduced.

Design/spec authoring guides and managed review objectives now examine shared policy ownership and verification that detects drifting consumers. Code review and retrospective guidance distinguish evidenced upstream design/spec omissions from implementation departures. Only a correction that changes an accepted architectural decision or contract requires reopening; recording an upstream observation does not itself reopen a phase.

## Evaluation evidence and limitations

`benchmark/structural-review/evaluate.py` defines seven paired decisions across design, spec, and implementation, including justified reopening versus local correction and supported retrospective attribution. Expected decisions are withheld from fresh read-only Claude sessions. Its frozen initial SHA256 is `f27651358cace77472e3c1f825449c85134849b11bfefecaf3054281c9ac58e2`.

Two baseline cases actually ran with the `opus` alias (reported canonical model `claude-opus-5`). Raw answers, citations, timings, usage and source hashes are retained locally in `test-results/structural-review/before.json`.

- `code-policy`: reviewer correctly requested changes, reopening design, and design-origin attribution in 48.388 seconds. The scorer incorrectly rejected valid quotations from supplied guidance because its citation lookup included only fixture files.
- `code-small`: reviewer blocked in 57.505 seconds because the illustrative fixture promised a CLI and tests without providing executable wiring or test files. This is a flawed healthy-control fixture, not evidence of an unnecessary structural refactor.

These runs expose evaluation defects, not a red-to-green demonstration of guidance effectiveness. The user approved validating citations against the exact fixture plus guidance snapshot; that correction is implemented and the decisive-fixture requirement remains enforced. Three scorer regressions cover supported guidance, unsupported evidence, and the requirement for case-specific evidence. The supported-guidance case failed before the fix; all three pass afterward. The user also approved completing runnable code/test fixtures. The three implementation cases now include real unittest checks; the healthy CLI includes argument parsing and subprocess entry-point coverage. Every structural decision expectation remains unchanged.

Focused existing review, handoff, source, retrospective and lens tests: **74 passed** using `assets/fbk-scripts/.venv/bin/python -m pytest` on `test_workflow_review.py`, `test_workflow_review_handoffs.py`, `test_workflow_review_sources.py`, `test_workflow_retrospective.py`, and `test_pipeline_lens.py`. These establish compatibility, not reviewer judgment quality. The live project was not modified.

All three corrected code fixtures independently pass their executable checks (two policy cases with one parameterized test each; healthy CLI with three tests). In isolated copies, a wrong retry limit in each policy case and wrong printed output in the CLI case all fail assertions. This demonstrates useful fixture checks; it does not claim tests prove structural quality.

The four post-change design/spec decisions match their oracles, with source-supported reasons, in `test-results/structural-review/after-design-spec.json`. The spec-small reviewer noted but waived omitted `scope.json`; this narrow exercise is not evidence that a real spec lacking required scope could close. No runtime scope enforcement was changed.

The three post-change implementation cases also match their oracles in `test-results/structural-review/after-code.json`: accepted design duplication blocks and reopens design (68.326 seconds), implementation-only duplication blocks and stays local (63.519 seconds), and the complete small CLI is accepted without extraction or reopening (68.176 seconds). The reviewer explicitly judged the supplied checks adequate while separating maintenance risk from currently correct behavior. Across the two reports, **7/7 expected structural decisions matched**, with supported citations. These are single fresh-session observations on small cases, not repeated trials, council convergence evidence, or a causal before/after improvement measurement.

The final evaluator SHA256 after approved corrections is `24fabf7b085653257d4cd867733cd871d7aea5ca148ecb6efed5f115e8ad327e`. Baseline reports remain historical evidence of evaluation defects; they were not rewritten or rescored against changed guidance.
