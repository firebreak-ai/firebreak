# Review-loop remediation, 2026-09-11

The completed task-tracker trial and reconstructed breakdown retrospective showed
several distinct problems: missing phase observations, incomplete review inspection
declarations, stale task assignments after test preparation, ineffective prescribed
fixtures, and repeated review concerns whose severity and rationale changed.
Evidence and attribution are indexed in
`test-results/live-install/analysis-2026-09-11/issue-map.md` and its three scoped
evidence packets. Those local trial files are not installed assets.

The user authorized three implementation tracks with narrowly scoped agent
context. Two fresh agents implemented upstream authoring and review changes. The
coordinator implemented runtime recovery because the session's thread limit
prevented starting the third implementation agent.

## Changes

| Track | Result |
| --- | --- |
| Upstream authoring | Phase guidance ties precision to actual user/consumer needs, avoids promoting incidental examples into requirements, asks for distinguishing test examples, and checks fixture prerequisites through the consumer's actual runner. Existing explicit human decisions remain authoritative. |
| Phase handoffs | Plan validation resolves existing input paths, anchors and lines. Missing future inputs need an ordered producer; task launch requires the actual input. Existing `input_refs` establish consumption without requiring a second list. Preparation capture, progress and close report affected stale tasks and refresh steps without rewriting assignment provenance. |
| Review | Blockers need a governing requirement, reachable scenario and material consequence. Remedies must exercise the claimed failure. A bounded prior-verdict packet preserves classifications/refutations and changed-source paths, prioritizes blockers and identifies omissions. It remains fallible context, with current original sources governing the verdict. |
| Runtime recovery | A blocked direct slash expansion returns actionable context without entering the phase. Skill tool calls still receive denial feedback. Malformed managed investigation declarations are rejected before experiment creation; missing inspection declarations list exact paths. Each logical reader gets at most one correction shared between these declaration failures per round, under the existing shared clock and durable usage accounting. Generic errors, timeouts, turn exhaustion and absent authorization do not get automatic correction. |
| Retrospectives | The earlier change in this worktree requires the model's own phase observations, linked to each latest acceptance event. Phase crossings and final completion expose and enforce missing accounts. Recording observations is not opt-in. |

Diagnostics identify the affected task, reference or field, explain the failure,
and supply a concrete next action. Missing inspection declarations are claims to
correct after actual reading, not a list the runtime fabricates. Rejected
investigation diagnostics retain a request hash and field names rather than
arbitrary commands or authorization quotations.

## Validation

Run from the repository root:

```
PYTHONPATH=assets/fbk-scripts python3 -m pytest -q assets/fbk-scripts/tests
PYTHONPATH=assets/fbk-scripts python3 -m pytest -q benchmark/workflow/tests benchmark/remediation-review/tests benchmark/structural-review/tests
ruff check assets/fbk-scripts/fbk/workflow assets/fbk-scripts/tests/test_workflow_protocol_recovery.py
```

Results: **531 runtime tests passed, one pre-existing test failed**; **69 benchmark
tests and 24 subtests passed**. Ruff passed. A final focused run of protocol recovery
and review continuity passed all **17 tests** after tightening the exhausted
correction message and accounting for all omitted refutations.

The existing failure is
`test_workflow_code_review_pipeline.py::test_runtime_neutral_handoff_rejoins_full_records_for_material_declaration`.
It reads `declaration['finding']['mechanism']`; the current declaration retains the
reference under `finding` and the joined record under `finding_evidence`. This was
already recorded in the consolidation baseline and remains outside these changes.

New regressions cover missing/unordered future inputs, invalid anchors and lines,
path confinement, stale preparation reports, preserved assignment records,
review continuity, exact inspection diagnostics, correction exhaustion across
restart, retained usage, no retry for host errors, no unauthorized experiment
launch, and unchanged phase state on slash recovery.

## Limits and next evaluation

No live model calls, installation changes, or trial artifact changes were made.
Structural validation establishes reference availability, dependency ordering and
protocol completeness; it cannot establish semantic test adequacy or prove that a
reviewer actually read a declared file. Prompt improvements remain unmeasured
behavioral interventions.

A fresh small-task trial should compare actual introduced defects and remediation
quality alongside completed versus failed review rounds, worker usage, repeated
concerns and human escalations. Fewer rounds alone is not evidence of better
review. Pay particular attention to whether early authoring avoids incidental
requirements and whether prescribed fixtures reach the claimed failure. Timeout
and max-turn failures still need evidence-based budget/host diagnosis; this change
does not claim to eliminate them by increasing budgets.
