# Task 08: Create Review Gate Validation Script

## Objective

Create a shell script that validates Stage 2 structural prerequisites for review and threat model artifacts.

## Context

The `/spec-review` skill calls this script during the transition check. The script performs deterministic structural validation on the review document and optionally the threat model document.

### What to validate

**Review document checks**:

1. **Perspective coverage**: The review document must contain findings from each classified perspective. Perspectives are passed as a comma-separated argument (e.g., "Architect,Guardian,Security"). For each perspective, check that a section heading or perspective label appears in the document.

2. **Severity classification**: Every finding must have a severity tag. Look for `blocking`, `important`, or `informational` labels (case-insensitive) associated with each finding entry. A finding without a severity tag is a structural failure.

3. **Threat model determination**: The review document must contain a section recording the threat model decision. Look for a heading like `## Threat Model Determination` or `## Threat Model Decision` with content that includes the decision (yes/no/skip) and rationale text.

4. **Testing strategy coverage**: The review must address all 3 testing categories:
   - New tests needed (or explicit "none" with justification)
   - Existing tests impacted (or explicit "none")
   - Test infrastructure changes (or explicit "none")
   Look for these as subsections or labeled entries under a testing-related heading.

**Threat model document checks** (only when threat model was requested):

5. **File existence**: `<feature-name>-threat-model.md` exists at the expected path.
6. **Required sections**: The threat model contains these headings (all must be present and non-empty):
   - `## Assets`
   - `## Threat actors` (or `## Threat Actors`)
   - `## Trust boundaries` (or `## Trust Boundaries`)
   - `## Threats`

### Input/output contract

- **Arguments**:
  - `$1`: Path to the review document
  - `$2`: Comma-separated list of classified perspectives (e.g., "Architect,Builder,Security")
  - `$3`: (optional) Path to the threat model document. If provided, threat model checks run. If omitted, only review checks run.
- **Exit 0**: All checks pass. Stdout: JSON summary.
- **Exit 2**: Failures found. Stderr: all failures listed.

### Script location

`home/dot-claude/hooks/sdl-workflow/review-gate.sh`

## Instructions

1. Create `home/dot-claude/hooks/sdl-workflow/review-gate.sh`.
2. Use bash with standard Unix tools.
3. Implement checks:

   a. **Argument validation**: Review path required, perspectives required.
   b. **Perspective coverage**: For each perspective in the comma-separated list, check that the perspective name appears in the review document (case-insensitive grep).
   c. **Severity tags**: Count findings without severity labels. A "finding" is identified by a pattern such as a numbered list item, a bold label, or a sub-heading under a perspective section. At minimum, check that `blocking`, `important`, or `informational` appears at least once per perspective section.
   d. **Threat model determination**: Check for the determination section with decision and rationale content. Match headings by case-insensitive prefix (e.g., `## Threat Model` matches `## Threat Model Determination` or `## Threat Model Decision`).
   e. **Testing coverage**: Check for all 3 testing categories under a testing-related heading (match by case-insensitive prefix: `## Testing`, `## Test`). Each category must appear as a labeled subsection or list item with content or explicit "none."
   f. **Threat model checks** (if `$3` provided): file exists, required headings present and non-empty.

4. Report ALL failures, not just the first.
5. On success: `{"gate": "review", "perspectives": [...], "threat_model": true|false, "result": "pass"}`.
6. Target: under 120 lines.

## Files to Create/Modify

- **Create**: `home/dot-claude/hooks/sdl-workflow/review-gate.sh`

## Acceptance Criteria

- AC-12: Validates all Stage 2 structural prerequisites from the enforcement mapping
- AC-15: Script is focused, one concern, clear error reporting

## Model

Sonnet

## Wave

1
