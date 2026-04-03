---
id: task-17
type: implementation
wave: 3
covers: [AC-55, AC-56, AC-57, AC-61, AC-23, AC-24, AC-25, AC-26, AC-27, AC-28, AC-29]
files_to_modify:
  - assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md
test_tasks: [task-02, task-06]
completion_gate: "task-02 and task-06 tests pass"
---

## Objective

Migrates the code review guide from single-axis category classification to two-axis type+severity classification, replaces format templates and category definitions, adds the `linter` detection source, and adds 7 new instructional sections.

## Context

This is the highest-complexity task in 0.3.3: it modifies one file (`code-review-guide.md`, currently 95 lines) with 11 ACs across migration and new content. The file roughly doubles in size. All additions use clearly headed subsections to preserve scannability.

The file is the canonical source of truth for finding classification. Detector, Challenger, existing-code-review.md, and SKILL.md all reference this file's definitions. The migration replaces:
- `Category:` field in sighting and finding format templates with `Type:` + `Severity:` fields
- `## Category Values` section with `## Finding Classification` containing canonical two-axis definitions
- Detection source values gain `linter`

The 7 new additions (AC-23 through AC-29) are new subsections or inline additions.

Current file structure (by line):
- Lines 1-9: `## Behavioral Comparison Methodology`
- Lines 11-34: `## Sighting Format` (template has `Category:` on line 18)
- Lines 36-51: `## Finding Format` (template has `Category:` on line 44)
- Lines 53-58: `## Category Values` (4 values including semantic-drift, nit)
- Lines 60-76: `## Orchestration Protocol`
- Lines 78-83: `## Source of Truth Handling`
- Lines 85-95: `## Retrospective Fields`

## Instructions

### Sighting format migration (AC-55)

1. In the sighting format template (code block starting at line 15), replace the line:
   ```
   Category: [semantic-drift | structural | test-integrity | nit]
   ```
   with these two lines:
   ```
   Type: [behavioral | structural | test-integrity | fragile]
   Severity: [critical | major | minor | info]
   ```

### Finding format migration (AC-56)

2. In the finding format template (code block starting at line 41), replace the line:
   ```
   Category: [semantic-drift | structural | test-integrity | nit]
   ```
   with these two lines:
   ```
   Type: [behavioral | structural | test-integrity | fragile]
   Severity: [critical | major | minor | info]
   ```

3. Delete the paragraph after the finding format code block: `A 'nit' is an observation that is accurate but functionally irrelevant — naming, formatting, style, or minor inconsistency that does not affect behavior or maintainability.` (This is superseded by the nit exclusion instruction in AC-26.)

### Category-to-type section replacement (AC-57)

4. Replace the entire `## Category Values` section (heading and all 4 bullet points) with the following:

```
## Finding Classification

Classification uses two orthogonal axes. Canonical definitions are here; Detector, Challenger, and existing-code-review.md reference this section.

### Type axis

Assigned by the Detector. Describes what kind of issue was found.

- `behavioral` — code does something different from what its name, documentation, or spec says
- `structural` — code organization issue (duplication, dead code, dead infrastructure, bare literals)
- `test-integrity` — test provides less coverage than it appears to. Includes name-scope mismatch: test name claims broader scope than its assertions actually cover
- `fragile` — code works now but breaks under likely future changes (string-based dispatch, sentinel confusion, context bypass)

**Disambiguation rule:** When an issue fits multiple types, classify by the primary risk. If the code produces wrong results now, it is `behavioral`. If it produces correct results but will break under realistic changes, it is `fragile`. If it is a code organization problem with no correctness risk, it is `structural`. If a test provides less coverage than it appears to, it is `test-integrity`.

### Severity axis

Initial estimate by the Detector, validated or adjusted by the Challenger.

- `critical` — affects production correctness, security, or data integrity now
- `major` — significant risk under realistic conditions
- `minor` — should be addressed but not urgently
- `info` — informational; accurate observation but no action required

### Nit exclusion

Nits (naming, formatting, style, minor inconsistency with no behavioral or maintainability impact) are excluded from findings entirely. They do not receive type or severity classification. The Challenger rejects nit-level sightings from the findings list and counts them separately in the retrospective.
```

### Detection source addition (AC-61)

5. In the "Detection source values:" list (currently after the sighting format template), add a fourth bullet:
   ```
   - `linter` — triggered by project-native linter or static analysis tool output provided as supplementary context
   ```

### AC verification precision (AC-23)

6. After the `## Behavioral Comparison Methodology` section (after the "Don't" line), add:

```
### AC verification precision

When reviewing against spec acceptance criteria, verify each AC individually. Produce a separate sighting for each AC that the code does not satisfy. Do not batch multiple AC violations into a single sighting — each AC represents a distinct behavioral contract.
```

### Dead infrastructure check (AC-25)

7. After the new "AC verification precision" subsection, add:

```
### Dead and disconnected infrastructure

Check for components that are constructed, initialized, or declared but never invoked in the application's runtime path. Dead infrastructure is reachable code that is simply never called — distinct from dead code (unreachable branches). Produce a `structural` type sighting for each instance.
```

### Origin guidance (AC-28)

8. In the `## Source of Truth Handling` section, after the "**No spec available**" paragraph, add:

```
**Codebase-wide reviews**: When reviewing code that is not tied to a specific change set (e.g., a full codebase audit), default the origin field to `pre-existing` for all sightings. Override to `introduced` only when git history or PR context confirms the issue was created by a recent change.
```

### Quality-detection reference in no-spec section (AC-29)

9. In the `## Source of Truth Handling` section, in the "**No spec available**" paragraph, after the sentence ending "...when the feature spec is absent or incomplete.", add: `Supplement with the structural detection targets from \`fbk-docs/fbk-design-guidelines/quality-detection.md\` for framework-aware pattern detection.`

### Structural sub-categorization (AC-27)

10. In the `## Retrospective Fields` section, in the first bullet point ("Sighting counts"), after "Include breakdown by detection source (spec-ac, checklist, structural-target)", append: `. For structural-type findings, include sub-categorization (duplication, dead code, dead infrastructure, bare literals, composition opacity)`

### Orchestration protocol nit termination update

11. In the `## Orchestration Protocol` section, update bullet 6 from:
    ```
    6. The loop terminates when a round produces only `nit`-category sightings (or no sightings), or after a maximum of 5 rounds
    ```
    to:
    ```
    6. The loop terminates when a round produces no new sightings above `info` severity, or after a maximum of 5 rounds
    ```

12. In the "Post-output steps" section, in bullet 1, replace `each verified finding's ID, category, and one-line description` with `each verified finding's ID, type, severity, and one-line description`.

## Files to create/modify

- `assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md` (modify)

## Test requirements

Tests from task-02: Tests 1-8 (Type/Severity fields present, Category absent from code blocks, no "Category Values" heading, canonical type axis values, canonical severity axis values, disambiguation rule).
Tests from task-06: Tests 1-7 (AC verification precision, name-scope mismatch, dead infrastructure, nit exclusion, structural sub-categorization, origin guidance, quality-detection reference in no-spec section).

## Acceptance criteria

- AC-55: Sighting format uses `Type:` and `Severity:` fields, not `Category:`.
- AC-56: Finding format uses `Type:` and `Severity:` fields, not `Category:`.
- AC-57: Canonical two-axis definitions with disambiguation rule replace old Category Values section.
- AC-61: Detection source values include `linter`.
- AC-23: AC verification precision requirement present.
- AC-24: Test-integrity definition includes name-scope mismatch.
- AC-25: Dead/disconnected infrastructure check present.
- AC-26: Nit exclusion instruction present.
- AC-27: Structural-target sub-categorization in retrospective fields.
- AC-28: Origin guidance for codebase-wide reviews present.
- AC-29: No-spec section references quality-detection.md.

## Model

Sonnet

## Wave

Wave 3
