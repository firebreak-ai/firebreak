Use retrospective evidence to propose testable changes within the user's requested scope.
Keep observed facts separate from causal hypotheses. Record implementation and evaluated
outcomes separately; successful bookkeeping does not demonstrate better behavior.

## Evidence and analysis

Run the installed `fbk-scripts/fbk.py retrospective <unit>` to retrieve the managed
unit's evidence packet. Follow its targeted retrieval commands for observations,
review findings, checks, interventions, and original source references. Read enough
original evidence to test the selected claims, including counterevidence and missing
context. Capture new observations with `observation-record <unit> --request <file>`.

Inspect the relevant runtime, host behavior, task, context selection, and instruction
routing before choosing a cause. A defect can justify a code fix, a narrower context
packet, a simpler workflow, removal of an instruction, or no change. Read the installed
`fbk-docs/fbk-context-assets.md` when an intervention changes a context asset.

Group related observations into bounded investigations. Delegate independent groups
or a relevant routing chain to `fbk-improvement-analyst` when useful. Supply the packet
locators, targeted original evidence paths, relevant targets, authoring rules path,
and the proposal contract below. Keep the investigation sized to the evidence and
question. Collect no-change findings alongside proposals.

For an analyst with file-reading tools, save the selected evidence packet under
`.fbk/runtime/` and supply that path with its original references. The orchestrator
runs targeted retrieval commands when the analyst needs additional historical
detail; a command locator alone is insufficient for a file-only worker.

## Proposal and application

Use `improvement-record <unit> --request <file>` for the durable record. The JSON
request's `action` selects `propose`, `adopt`, `evaluate`, or `decision`. Mutations
require a session; use `--session <session>` or the host's session environment.

A `propose` request contains:

- `id`: a distinct local name; `hypothesis`: the proposed causal mechanism.
- `evidence`: original evidence references using the retrospective reference format.
- `targets`: repository-relative files; `change_kind`: `add`, `edit`, `remove`,
  `simplify`, or `no-change`; `change`: the concrete diff or no-change rationale.
- `check`: an object with `method`, `success_criterion`, and `baseline`. Describe the
  task or check that could distinguish the hypothesis from competing explanations,
  the measurable result expected, and the observed starting result.

Include necessity reasoning and competing explanations in the hypothesis. Bind the
baseline to evidence before editing. For a no-change conclusion, targets may be empty;
state what observation would justify reconsidering it.

Apply changes already authorized by the user, observing the active unit's actual
scope, phase, and test authority. Present a concrete proposal for any additional
permission needed. The ledger records evidence; recording a proposal or adoption
never grants write authority or modifies a file. Changes to a global installation
require authority covering that installation, rather than extrapolation from a
project retrospective. Use a scoped repository change when that is the authorized
intervention.

After editing, record `action: "adopt"`, `id`, and `reason`. This binds the actual
current hashes of all proposed target files, including absence for removed files.
Unchanged target sets cannot count as implementation. Record a new adoption after
further target edits. Preserve unrelated local work.

## Evaluation and follow-up

Run the planned check and capture its original evidence. Record `action: "evaluate"`,
`id`, `outcome` (`improved`, `regressed`, `inconclusive`, or `no-change`), `evidence`,
`comparison`, `limitations`, and `stage` (`check` or `followup`). Explain results
against the saved baseline and success criterion; identify confounders and the scope
of any demonstrated effect. Use a newly captured check or follow-up observation,
rather than recycling only proposal evidence. `improved` is the evaluator's assessment,
not a runtime-certified causal finding.

Evaluate meaningful real follow-up work through another evaluation with
`stage: "followup"`: report regressions, missed requirements, unnecessary work,
human corrections, and time or cost where observable. Preserve negative and
inconclusive evidence. A local replay can support a bounded result; longitudinal
maintainability remains unknown until observed.

Run `improvement-report <unit>` for bounded status and `--index N` (one-based) for the full
proposal, target snapshots, evaluations and decisions. Changed targets or evaluated
evidence make an evaluated result `needs-re-evaluation`; history remains intact.
An adoption without evaluation remains `implemented-unverified`.

Record `action: "decision"`, `id`, `decision` (`retain`, `rollback`, or `defer`), and
`reason` after considering results. A rollback decision records intent only. Perform
any authorized rollback as a separate reviewed change and record its resulting
adoption and evaluation. Keep new revisions and results visible instead of deleting
an unsuccessful experiment.
