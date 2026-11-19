---
description: >-
  Code review and remediation. Use when reviewing existing code, auditing
  for AI failure modes, performing post-implementation review, or
  co-authoring remediation specs from code review findings.
argument-hint: "[target-path or feature-name]"
allowed-tools: Read, Grep, Glob, Write, Edit, Bash, Agent
---

Review the requested code against the user's intent and repository contracts. Apply
fixes only within existing authorization. Standalone completion records findings;
managed acceptance still requires `phase-close`.

Resolve `firebreak_dir` in each shell invocation: use
`${CLAUDE_PROJECT_DIR:-$PWD}/.claude` when it contains `fbk-scripts/fbk.py`, otherwise
`$HOME/.claude`. Run from the project root when `CLAUDE_PROJECT_DIR` is unset;
shell variables do not persist between tool calls.

Read all `fbk-docs/` references below under that directory. Read
`fbk-docs/review/code-review-guide.md` for behavioral comparison, finding format,
remediation quality and retrospective fields. Use these references at the relevant
step rather than rebuilding their protocols:

| Reference | Use |
| --- | --- |
| `fbk-docs/fbk-review-lenses/code-lens.md` and `fbk-docs/fbk-review-lenses/review-loop.md` | Sighting/verdict schema, classifications and detection/challenge rules. |
| `fbk-docs/workflow/review-rounds.md` | Launch, runtime result artifacts, completion gates and recovery. |
| `fbk-docs/workflow/investigations.md` | Bounded checks and fresh experimental workers. |
| `fbk-docs/workflow/remediation-verification.md` | Material-fix declarations, independent behavior/regression verification and late registration. |

## Establish intent and the review contract

Create `.fbk/runtime/reports/fbk-code-review-<YYYY-MM-DD>-<HHMM>.md` immediately.
Keep the intent register, findings and retrospective there as the review progresses.

Find feature specs in `.fbk/<unit>/spec.md` or repository documentation, then README,
CLAUDE.md, CONTRIBUTING.md and architecture docs, then module documentation and
CI/deployment/API contracts. Use existing specs' acceptance criteria and validation
steps as the primary comparison target. For standalone and broad reviews, also
extract documented behavioral claims outside the specs. Without specs, use those
claims and the AI failure-mode checklist. If neither documentation nor code context
is available, ask what to review.

Write up to 30 specific, verifiable intent claims and a Mermaid module/data-flow
diagram in the report. Use `graph TD` or `graph LR`, short labels, behavioral edge
labels and simple subgraphs; avoid advanced renderer features. Show the user the
report and resolve silent or contradictory requirements before launching reviewers.
Carry already-settled decisions forward. Supplement remaining documentation gaps
from code structure, making inferred intent distinguishable from documented intent.

Discover available linter and typechecker commands and record their purpose here;
execution needs a round ID. In the captured Detector assignment, require it to
request the available typechecker through a bounded investigation before producing
sightings. After launch, the runtime executes the request and resumes the Detector
with the evidence. Preserve full outputs and retrieval references for excerpts;
treat results as review context, not findings already proved. Tag derived sightings
with detection source `linter`.

Capture all contributor instructions before beginning the round. Workers do not
inherit this skill. Include the intent register, governing references, checks,
role assignments and relevant guidance:

- **Detector:** Include `fbk-docs/review/researcher-role.md` in full, then the code
  lens. Inspect target code
  first, then check output and intent. Apply `review/code-review-guide.md`,
  `review/ai-failure-modes.md`, `review/security-patterns.md`,
  `review/detection-audits.md` and `review/quality-detection.md` under `fbk-docs/`.
  Include affected durable-doc discovery and comparison from the detection audits,
  including relevant docs omitted from the change set.
  Supply the sighting schema and type/severity definitions last. Return sightings
  tagged `spec-ac`, `checklist`, `structural-target`, `audit-pass`, `intent` or `linter`.
- **Challenger:** Include `fbk-docs/review/challenger-role.md` in full, then the code
  lens. Read target code
  cold, then the lens, normalized candidates and the actual cited source documents;
  supply verification instructions and the type/severity matrix last. Return one
  JSON verdict per candidate. Verify claims by opening their sources and requesting
  bounded experiments when execution can decide them; do not guess from recalled
  behavior. Preserve claims with necessary missing source or execution evidence as
  `unresolvable`; a claim that needs execution to establish the defect is not verified.

Use fresh contributors launched by `review-round run`, with the Detector first
and the Challenger after completed detection. Use `Read`, `Grep` and
`Glob` for inspection; request execution through investigations. Experimental
helpers preserve context but cannot independently verify their own remediator's fix.

## Run and interpret the round

Follow `review-rounds.md` for the concrete command sequence. Default to
`behavioral-only` and minimum severity `minor`, unless the user specifies otherwise.
Bind the Detector and Challenger roles, lens and filters to the round. Include
existing authorized edit scope at `begin`; review the immutable snapshot throughout.

The bound runtime composes the shared loop's existing pipeline: validate/domain-filter/severity-filter
sightings, retain full kept records, normalize the six neutral candidate fields,
validate Challenger verdicts, rejoin onto retained records, and validate merged
type/severity combinations. Read the artifact paths documented in `review-rounds.md`;
do not repeat those transformations manually or hand-publish merged results. Surface the warning when more
than 30% of sightings fail validation. Preserve JSON as the working format and
convert confirmed findings to Markdown only for the report.

To inspect the filter result independently, feed a sightings JSON array on stdin:

```bash
firebreak_dir="${CLAUDE_PROJECT_DIR:-$PWD}/.claude"
if [ ! -f "$firebreak_dir/fbk-scripts/fbk.py" ]; then
    firebreak_dir="$HOME/.claude"
fi
python3 "$firebreak_dir/fbk-scripts/fbk.py" pipeline run --preset <preset> --min-severity <threshold> --lens "$firebreak_dir/fbk-docs/fbk-review-lenses/code-lens.md"
```

Use the complete runtime-produced artifacts. Imported results are supporting
evidence; they cannot complete a contributor. Do not recreate runtime receipts or
edit durable findings to make a declaration pass. A quiet worker, truncated message
or missing peer is incomplete even when another contributor reports zero findings.

Append verified and `verified-pending-execution` findings with sequential F-IDs to
the report, keeping the latter's execution caveat visible. Report `unresolvable`
findings separately with the missing source/evidence needed to decide them; exclude
rejected sightings. Include adjacent observations and counts of candidates and
confirmed findings per round in the retrospective. Before fixing, require the
durable completion gate to pass.

## Remediate and finish

Register each material fix against its verified finding before editing, following
`remediation-verification.md`. This records existing authority without a routine
new approval checkpoint. Follow the canonical guide's **Remediation verification**
section: inspect relevant siblings, account for fixed/already-safe/out-of-scope
paths, and preserve accepted scope. When independently verifying a material fix,
read `fbk-docs/review/remediation-verification.md` for behavioral and regression evidence.

After edits, begin a fresh snapshot with `--previous ID`, carrying unresolved
findings, prior references and consumed budget. Justify review scope from affected
behavior and related paths; expand to the full artifact when warranted. Run
`remediation verify` for each material fix. Have a fresh contributor account for
other changed paths as nonmaterial only with a reason. Use `register-late` for a
missed declaration within the original recorded authority; preserve the original
finding and verification obligation rather than reverting correct code for ceremony.

Stop after a clean round or at five rounds. Before accepting an empty round, check
the Detector's inspection evidence for the required detection passes. Missing
inspection needs recovery within the same budgets, not an unbounded relaunch.
Exhaustion requires human help with the findings and missing evidence retained;
it does not imply a clean review. Require post-fix round completion and run the
full test suite with zero failures before reporting remediation complete.

Recheck affected durable-doc claims against the final authorized behavior, using
the existing review round. Summarize sources inspected, confirmed findings, unresolved evidence and checks
actually run. Use `fbk-test-review` for a dedicated test-integrity pass,
`fbk-quality-scan` for bounded quality review, `fbk-doc-reconcile` for documentation
and `fbk-cross-model-review` when requested. These do not create managed acceptance.
If remediation needs a new managed unit, enter `/fbk-intent` carrying settled user
decisions. For a process issue, preserve original retrospective evidence before
invoking `/fbk-improve` within the requested scope.
