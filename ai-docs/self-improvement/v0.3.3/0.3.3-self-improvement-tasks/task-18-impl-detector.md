---
id: task-18
type: implementation
wave: 4
covers: [AC-09, AC-10, AC-11, AC-58]
files_to_modify:
  - assets/agents/fbk-code-review-detector.md
test_tasks: [task-02, task-03]
completion_gate: "task-02 test 9 and task-03 tests pass"
---

## Objective

Removes Bash from the Detector agent's tools, deletes the linter discovery section, and migrates the sighting output from single `category` field to `type` + `severity` + `pattern` fields.

## Context

The Detector agent definition (`assets/agents/fbk-code-review-detector.md`) currently:
- Frontmatter line 4: `tools: Read, Grep, Glob, Bash`
- Lines 9-11: `## Project-native tool discovery` section that instructs the Detector to run linters via Bash
- Line 16: `Assign a category to each sighting: \`semantic-drift\`, \`structural\`, \`test-integrity\`, or \`nit\`.`

AC-09 removes Bash from tools and deletes the linter discovery section (linter execution relocates to SKILL.md, handled in task-20). The Detector becomes strictly read-only.

AC-10 replaces the `category` assignment instruction with `type` (behavioral, structural, test-integrity, fragile) and `severity` (critical, major, minor, info) fields. These values match the canonical definitions in `code-review-guide.md` (established by task-17 in Wave 3).

AC-11 adds a cross-cutting pattern label field.

AC-58 ensures `category` no longer appears in the Detector's body.

Also update the `description` field in frontmatter to reflect that the agent no longer runs linters.

## Instructions

1. In the frontmatter, change `tools: Read, Grep, Glob, Bash` to `tools: Read, Grep, Glob`.

2. Update the `description` field from:
   ```
   description: "Analyzes code through behavioral comparison, producing sightings of potential issues by describing what code does and comparing against specs or the AI failure mode checklist. Use for code analysis, pattern detection, and behavioral comparison tasks."
   ```
   to:
   ```
   description: "Analyzes code through behavioral comparison, producing sightings with type and severity classification. Compares code behavior against specs, the AI failure mode checklist, and linter output provided by the orchestrator. Read-only — does not execute tools or modify files."
   ```

3. Delete the entire `## Project-native tool discovery` section (heading and its paragraph, lines 9-11). This removes all content from "Before reading code manually..." through "...when no project-native tools are available."

4. In the `## Sighting output` section, replace:
   ```
   Assign a category to each sighting: `semantic-drift`, `structural`, `test-integrity`, or `nit`. Describe what you observed in behavioral terms — what the code does, not what is wrong with it.
   ```
   with:
   ```
   Assign a type to each sighting: `behavioral`, `structural`, `test-integrity`, or `fragile`. Assign an initial severity estimate: `critical`, `major`, `minor`, or `info`. Type and severity definitions are in `code-review-guide.md` under Finding Classification. Assign a cross-cutting pattern label when the sighting is an instance of a pattern observed across multiple locations (e.g., "string-error-dispatch", "dead-handler-registration"). Leave the pattern label empty when the sighting is isolated. Describe what you observed in behavioral terms — what the code does, not what is wrong with it.
   ```

5. Verify the word `category` does not appear anywhere in the file body (after frontmatter). The only instance was in the sighting output section, now replaced.

## Files to create/modify

- `assets/agents/fbk-code-review-detector.md` (modify)

## Test requirements

Tests from task-03: Test 1 (no Bash in tools), Test 2 (Read, Grep, Glob preserved), Test 3 (no linter discovery section), Tests 4-6 (type, severity, pattern fields in body), Tests 8, 10 (all four type values, all four severity values present).
Test from task-02: Test 9 (body does not contain `category`).

## Acceptance criteria

- AC-09: Tools list is `Read, Grep, Glob` (no Bash); linter discovery section deleted.
- AC-10: Sighting output includes type (behavioral, structural, test-integrity, fragile) and severity (critical, major, minor, info) fields.
- AC-11: Sighting output includes cross-cutting pattern label field.
- AC-58: Body does not contain the word `category`.

## Model

Haiku

## Wave

Wave 4
