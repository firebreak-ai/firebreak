---
description: >-
  Top-five quality scan of a diff or change set. Surfaces at most five ranked,
  severity-tagged quality opportunities. Invocable standalone or as part of
  code-review ceremony. Scan-only — no auto-fix.
argument-hint: "[diff or feature-name]"
---

Surface the top quality opportunities in the change set. This is a scan-only technique — it does not apply fixes. The operator decides what to do with each finding.

## Reviewer execution

Resolve the installed directory from `${CLAUDE_PROJECT_DIR:-$PWD}/.claude` when
it contains `fbk-scripts/fbk.py`, otherwise `$HOME/.claude`. Read
`fbk-docs/workflow/reviewer-execution.md` there and launch each reviewer as it
describes. Publish the requested report after the round completes. A missing
check is a limitation, never an invented result.

## Workflow

1. Write the reviewer's instruction file under `.fbk/runtime/` (for example `.fbk/runtime/quality-scan-instructions.txt`). It contains, in this order: `fbk-docs/review/researcher-role.md` in full; `fbk-docs/fbk-review-lenses/quality-lens.md`; the cardinality statement (zero challengers, round cap 1) per the shared review-loop spine in `fbk-docs/fbk-review-lenses/review-loop.md`; the target diff or change set; and the output instructions: read the target diff or change set, apply the quality-lens detection areas (readability, maintainability, structural clarity, naming, duplication, fragile patterns), and return at most 5 sightings ranked by priority under `result`. Each sighting must include a `Severity:` field tagged as `critical`, `substantive`, or `minor`. Include no authoring history and no prior conversation context; the researcher reads cold. Because the lens declares `output_mode: scan`, output bypasses `validate_sighting()` and is checked only against the lens's own output schema.

   Then launch the round, with `firebreak_dir` resolved as the reviewer-execution section describes and `--required` naming the files in the change set:

   ```bash
   python3 "$firebreak_dir/fbk-scripts/fbk.py" review-round begin --root "$PWD" \
     --instructions .fbk/runtime/quality-scan-instructions.txt \
     --contributors reviewer --required <changed-files>
   python3 "$firebreak_dir/fbk-scripts/fbk.py" review-round run --round ID --contributors reviewer
   python3 "$firebreak_dir/fbk-scripts/fbk.py" review-round require-complete --round ID
   ```

   Use the returned round ID. Read the reviewer's result path that `run` returns; the sightings are under `result`.

2. Collect the reviewer's sightings from the round result. If more than five sightings are returned, keep only the top five by severity and rank.

3. Write the results to `reviews/quality-scan.md`. Each finding entry must carry a `Severity:` field. The report is the operator's decision surface — no changes are applied automatically.

## Output format

The report lists at most 5 findings, ranked from highest to lowest severity. Each finding includes:

- **Severity**: `critical` / `substantive` / `minor`
- **Location**: file and line range
- **Description**: what the quality issue is and why it matters
- **Opportunity**: what a better approach would look like

## Scan-only constraint

This skill does not invoke any agent with Write or Edit tools. The operator reviews the ranked findings and decides which, if any, to act on.
