---
description: >-
  Top-five quality scan of a diff or change set. Surfaces at most five ranked,
  severity-tagged quality opportunities. Invocable standalone or as part of
  code-review ceremony. Scan-only — no auto-fix.
argument-hint: "[diff or feature-name]"
---

Surface the top quality opportunities in the change set. This is a scan-only technique — it does not apply fixes. The operator decides what to do with each finding.

## Workflow

1. Spawn the `fbk-code-review-detector` agent in quality-opportunity mode via the spawn prompt. Instruct it to: read the target diff or change set, identify code-quality opportunities (readability, maintainability, structural clarity, naming, duplication, fragile patterns), and return at most 5 sightings ranked by priority. Each sighting must include a `Severity:` field tagged as `critical`, `substantive`, or `minor`.

2. Collect the detector's output. If more than five sightings are returned, keep only the top five by severity and rank.

3. Write the results to `ai-docs/<feature>/quality-scan.md`. Each finding entry must carry a `Severity:` field. The report is the operator's decision surface — no changes are applied automatically.

## Output format

The report lists at most 5 findings, ranked from highest to lowest severity. Each finding includes:

- **Severity**: `critical` / `substantive` / `minor`
- **Location**: file and line range
- **Description**: what the quality issue is and why it matters
- **Opportunity**: what a better approach would look like

## Scan-only constraint

This skill does not invoke any agent with Write or Edit tools. The operator reviews the ranked findings and decides which, if any, to act on.
