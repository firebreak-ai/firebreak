## Objective

Write a bash test script that validates the modified spec-review skill references the test reviewer agent and the brownfield spec-stage instruction doc exists with required content.

## Context

The `/spec-review` skill at `home/.claude/skills/spec-review/SKILL.md` is being modified to add a test strategy review step. After the council review produces findings and before the gate invocation, the skill must invoke the test reviewer agent (checkpoint 1) as an Agent Teams teammate for context isolation. The test reviewer receives the spec and spec schema, evaluates the testing strategy, and its pass/fail result is incorporated into the review document.

A new brownfield instruction doc at `home/.claude/docs/brownfield-spec.md` provides 5 codebase-awareness instructions loaded by the `/spec` skill when writing the technical approach. These instructions come from the spec's brownfield intercepts section and address: searching for overlapping code, identifying established patterns, distinguishing new from extended code, requiring removal of replaced functionality, and preferring extension over duplication.

The test validates that the skill file was modified correctly and that the brownfield doc exists with the required content. It does not test runtime behavior of the skill invocation.

## Instructions

1. Create `tests/sdl-workflow/test-review-integration.sh` as a bash test script. Use `set -uo pipefail`. Define a test counter and pass/fail tracking at the top. Each test prints `ok <n> - <description>` on pass or `not ok <n> - <description>` on fail (TAP format).

2. Determine project root using `cd "$(dirname "$0")/../.." && pwd`. Define `SKILL_FILE` pointing to `home/.claude/skills/spec-review/SKILL.md` relative to project root. Define `BROWNFIELD_DOC` pointing to `home/.claude/docs/brownfield-spec.md` relative to project root.

3. Write test: skill file exists. Assert `$SKILL_FILE` exists and is a non-empty file.

4. Write test: skill file has valid YAML frontmatter. Assert the file starts with `---` on line 1 and contains a second `---` delimiter. Assert frontmatter contains a `description:` field.

5. Write test: skill references test reviewer agent. Search the skill file content for "test-reviewer" or "test reviewer" (case-insensitive). Assert at least one match exists, confirming the skill knows to invoke the test reviewer.

6. Write test: skill specifies checkpoint 1 context. Search the skill file for content referencing "checkpoint 1" or "spec review" in the context of the test reviewer invocation. Assert the skill describes that the test reviewer evaluates the testing strategy.

7. Write test: skill specifies Agent Teams invocation. Search the skill file for "Agent Teams" or "teammate" (case-insensitive). Assert at least one match exists, confirming the invocation uses Agent Teams for context isolation.

8. Write test: skill preserves council invocation. Search the skill file for "council" (case-insensitive). Assert the file still contains a reference to the council invocation (existing behavior preserved).

9. Write test: skill preserves gate invocation. Search the skill file for "review-gate" or "gate invocation" or "Gate invocation" (case-insensitive). Assert the file still contains a reference to the gate script.

10. Write test: test strategy review is positioned between council and gate. Extract line numbers for: (a) the council invocation section (line containing "council" in a heading or instruction context), (b) the test strategy review section (line containing "test-reviewer" or "test strategy review"), (c) the gate invocation section (line containing "review-gate" or "Gate invocation"). Assert the test strategy review line number is greater than the council line number and less than the gate invocation line number.

11. Write test: brownfield doc exists. Assert `$BROWNFIELD_DOC` exists and is a non-empty file.

12. Write test: brownfield doc contains instruction about searching for overlapping code. Search the brownfield doc for "search" and "overlap" or "existing code" within the file. Assert a match exists.

13. Write test: brownfield doc contains instruction about identifying established patterns. Search for "pattern" or "convention" or "abstraction" in the doc. Assert a match exists.

14. Write test: brownfield doc contains instruction about distinguishing new from extended code. Search for "distinguish" or "new" combined with "extend" or "modify" in the doc. Assert a match exists.

15. Write test: brownfield doc contains instruction about replacing existing functionality. Search for "replace" or "removal" or "migration" in the doc. Assert a match exists.

16. Write test: brownfield doc contains instruction about avoiding duplication. Search for "duplicate" or "duplication" in the doc. Assert a match exists.

17. End the script with a summary: `echo "# <pass-count>/<total-count> tests passed"`. Exit 0 if all passed, exit 1 otherwise.

## Files to create/modify

- `tests/sdl-workflow/test-review-integration.sh` (create)

## Test requirements

This is a test task. Tests to write (all in `test-review-integration.sh`):
1. Structural: skill file exists and is non-empty
2. Structural: skill file has valid YAML frontmatter
3. Structural: skill references test reviewer agent
4. Structural: skill specifies checkpoint 1 context (testing strategy evaluation)
5. Structural: skill specifies Agent Teams invocation for context isolation
6. Structural: skill preserves existing council invocation
7. Structural: skill preserves existing gate invocation
8. Structural: test strategy review is positioned between council and gate sections
9. Structural: brownfield doc exists and is non-empty
10. Structural: brownfield doc contains search-for-overlapping-code instruction
11. Structural: brownfield doc contains identify-patterns instruction
12. Structural: brownfield doc contains distinguish-new-from-extended instruction
13. Structural: brownfield doc contains replace-existing-functionality instruction
14. Structural: brownfield doc contains avoid-duplication instruction

## Acceptance criteria

AC-05: Review integration invokes council review via `/spec-review` and parses output for pass/fail. Failing reviews set state to PARKED with feedback attached.

## Model

Haiku

## Wave

3
