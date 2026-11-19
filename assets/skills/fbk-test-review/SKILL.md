---
description: >-
  Independently review test plans, catching power, requirement coverage and test
  integrity, including existing regressions and integration behavior.
argument-hint: "<test-path or unit-name>"
---

Resolve `firebreak_dir` in each shell invocation: use
`${CLAUDE_PROJECT_DIR:-$PWD}/.claude` when it contains `fbk-scripts/fbk.py`, otherwise
`$HOME/.claude`. Run from the project root when `CLAUDE_PROJECT_DIR` is unset.
Read all `fbk-docs/` references below under that directory.

Read `fbk-docs/fbk-review-lenses/test-lens.md`, `shared-detection.md` in the same
folder, `fbk-docs/review/test-integrity.md`, and
`fbk-docs/workflow/reviewer-execution.md`. Use
`fbk-docs/workflow/review-rounds.md` for execution, completion and recovery.

## Assemble the review inputs

Identify whether the target is a plan, executable tests before implementation, or
final/changed code. For managed units, read `.fbk/<unit>/spec.md`, `scope.json`,
accepted task verification expectations and applicable test locks. Collect relevant
production interfaces/callers, tests, fixtures/helpers and existing regressions for
the affected module. For changed or retired tests include baseline content and
current authorization, not prior review opinions. Name unavailable inputs.

Create a report at `.fbk/runtime/reports/test-review-<unit-or-target>.md`. Capture
the review stage, scope, governing sources and complete contributor instructions
in `.fbk/runtime/test-review-instructions.txt` before beginning. Workers do not
inherit this skill: include the actual lens, shared test-integrity criteria, shared detection and generic
researcher/challenger instructions, plus the execution guidance. Keep instructions
role-specific; do not include prior review results or author reasoning.

- **Detector:** inspect the test set cold; apply every relevant targeted test check
  in the shared criteria. Return `result: {findings: [...], coverage: [...]}` using the lens's
  evidence account, including when no findings exist. Request focused execution
  where it can decide a material uncertainty. Do not invent requirements or findings
  from model preferences, style or missing labels alone.
- **Challenger:** inspect the tests and cited sources independently, then normalized
  candidates. Trace the faulty behavior a test would miss. Use execution when needed
  to decide the claim. Return `result: [...]` with one verdict per candidate; an
  undecided runtime fact is `unresolvable`, not verified. Coverage conclusions from
  the Detector are coordinator-only evidence.

## Run the review

Use the existing bound Detector/Challenger runtime with the test lens. `--lens-only`
omits code-domain filtering: the lens owns the test types, with no duplicate preset.
Default minimum severity is `minor` unless the user sets another threshold.

```bash
firebreak_dir="${CLAUDE_PROJECT_DIR:-$PWD}/.claude"
if [ ! -f "$firebreak_dir/fbk-scripts/fbk.py" ]; then
    firebreak_dir="$HOME/.claude"
fi
python3 "$firebreak_dir/fbk-scripts/fbk.py" review-round begin --root "$PWD" \
  --instructions .fbk/runtime/test-review-instructions.txt \
  --contributors detector challenger --code-review detector challenger \
  --lens "$firebreak_dir/fbk-docs/fbk-review-lenses/test-lens.md" \
  --lens-only --min-severity minor --required <governing-project-paths>
```

Use the returned ID with `review-round run --round ID --contributors detector`,
then `review-round run --round ID --contributors challenger`. Resolve the driver
path each time. Both readers can request tests through the same bounded investigation
protocol; neither edits reviewed sources. Include otherwise excluded governing files
using `--required`. Baselines supplied outside the project must first be captured as
review inputs; do not claim a comparison based only on a hash or unavailable git history.

The runtime validates coverage shape and findings, filters severity, retains full
records and gives the Challenger only six-field normalized candidates. It validates
verdicts, rejoins by position and retains confirmed and unresolved records. Do not
repeat this pipeline manually or fabricate runtime result envelopes. Even an empty
candidate list requires the declared Challenger's completed contribution.

## Report the evidence

Read Detector coverage from its complete runtime result and confirmed/unresolved
findings from the Challenger artifacts described in `review-rounds.md`. Report
material requirement coverage, applicable targeted checks, executed commands and
outcomes, limitations and missing evidence. A timeout, skipped test, collection
error or unavailable dependency does not establish clean coverage. Preserve an
execution caveat on `verified-pending-execution`; use it only where source evidence
already establishes the defect.

Run `review-round require-complete --round ID` before claiming the round complete.
A successful runtime gate establishes transport/execution completeness, not semantic
coverage. Report gaps and unknowns even when there are no confirmed findings. This
skill reviews; it does not change test locks, remediate or grant managed acceptance.
