---
id: task-19
type: implementation
wave: 4
covers: [AC-12, AC-13, AC-14, AC-15, AC-59]
files_to_modify:
  - assets/agents/fbk-code-review-challenger.md
test_tasks: [task-02, task-03, task-04]
completion_gate: "task-02 test 10, task-03 tests 7, 9, 11, and task-04 tests pass"
---

## Objective

Updates the Challenger agent to validate type+severity classification, adds adjacent observation channel, caller tracing for behavioral sightings, verified-pending-execution status, and replaces nit-downgrade with nit-rejection.

## Context

The Challenger agent (`assets/agents/fbk-code-review-challenger.md`) currently:
- Line 13-14: Verification protocol says "Preserve the sighting's location and category (you may reclassify the category if evidence warrants)."
- Line 18: `**Downgrade to nit:**` section that describes downgrading sightings to `nit` category.
- Line 20-21: Scope discipline says "Do not generate new sightings."

The migration to two-axis classification requires:
- AC-12: Challenger validates or adjusts both type and severity on verified findings
- AC-59: "Downgrade to nit" becomes "reject as nit" — nits are excluded from findings and counted separately
- AC-13: Adjacent observation channel (informational items for the retrospective, not findings)
- AC-14: Caller tracing for `behavioral` type sightings
- AC-15: `verified-pending-execution` status for `test-integrity` sightings needing test execution

Also update the `description` field to reflect new capabilities. The canonical type values are: behavioral, structural, test-integrity, fragile. The canonical severity values are: critical, major, minor, info.

## Instructions

1. Update the frontmatter `description` to:
   ```
   description: "Performs adversarial verification of code review sightings with type and severity validation, demanding concrete evidence before promoting a sighting to a verified finding. Supports adjacent observations, caller tracing for behavioral sightings, and verified-pending-execution status. Use for evidence-based assessment, skeptical review, and adversarial verification tasks."
   ```

2. In the `## Verification protocol` section, in the "**Verified finding:**" paragraph, replace:
   ```
   Preserve the sighting's location and category (you may reclassify the category if evidence warrants).
   ```
   with:
   ```
   Validate or adjust the sighting's type (`behavioral`, `structural`, `test-integrity`, `fragile`) and severity (`critical`, `major`, `minor`, `info`) classification. You have more context from evidence tracing than the Detector had — reclassify when evidence warrants.
   ```

3. Replace the entire `**Downgrade to nit:**` paragraph with:

   ```
   **Reject as nit:** If the sighting is technically accurate but functionally irrelevant (naming, formatting, style, minor inconsistency with no behavioral or maintainability impact), reject it as a nit. Nits are excluded from the verified findings list entirely — they do not receive type or severity classification. Count nits separately in the retrospective output.
   ```

4. After the "**Rejection:**" paragraph and before the new "**Reject as nit:**" paragraph, add:

   ```
   **Caller tracing for behavioral sightings:** For sightings classified as `behavioral` type, cross-reference the callers of the affected function or method. Trace at least one call path from an entry point to the observed behavior to confirm the behavioral claim is reachable in production. If no production caller exercises the behavioral path, reclassify as `structural` (dead code) or reject.

   **Verified-pending-execution:** For `test-integrity` type sightings that require test execution to confirm (e.g., a test that appears to pass trivially but might fail under different conditions), assign a `verified-pending-execution` status instead of full verification. This signals the orchestrator that the finding is credible from code reading but requires test execution for definitive confirmation.
   ```

5. After the "**Reject as nit:**" paragraph and before `## Scope discipline`, add:

   ```
   **Adjacent observations:** When verification of a sighting reveals a related issue that was not reported by the Detector, record it as an adjacent observation. Adjacent observations are informational — they do not surface as findings and do not feed back into the detection loop. The orchestrator appends them to the retrospective as informational items. Format: "Adjacent to S-NN: [brief description of the related issue observed]."
   ```

6. In `## Scope discipline`, update the first sentence from:
   ```
   Do not generate new sightings.
   ```
   to:
   ```
   Do not generate new sightings. Adjacent observations (see above) are informational annotations, not new sightings.
   ```

## Files to create/modify

- `assets/agents/fbk-code-review-challenger.md` (modify)

## Test requirements

Tests from task-02: Test 10 (reject as nit present, downgrade to nit absent).
Tests from task-03: Test 7 (validates type and severity), Test 9 (all four type values), Test 11 (all four severity values).
Tests from task-04: Tests 1-2 (adjacent observation keyword, informational), Tests 3-4 (caller tracing, scoped to behavioral), Tests 5-6 (verified-pending-execution, scoped to test-integrity).

## Acceptance criteria

- AC-12: Challenger validates or adjusts both type and severity on verified findings.
- AC-13: Adjacent observation channel present, documented as informational (not findings).
- AC-14: Caller tracing requirement present, scoped to `behavioral` type sightings.
- AC-15: `verified-pending-execution` status present, scoped to `test-integrity` type sightings.
- AC-59: "Downgrade to nit" replaced with "reject as nit" — nits excluded from findings, counted separately.

## Model

Sonnet

## Wave

Wave 4
