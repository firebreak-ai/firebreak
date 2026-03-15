## Objective

Write a bash test script that validates the modified breakdown skill specifies sequential agent execution with context isolation and the brownfield breakdown-stage instruction doc exists with required content.

## Context

The `/breakdown` skill at `home/.claude/skills/breakdown/SKILL.md` is being modified to replace the current monolithic task compilation with sequential context-independent Agent Teams teammates: (1) the test task agent receives only the spec and produces test tasks, then (2) the implementation task agent receives the spec plus the test task output and produces implementation tasks. Both agents are invoked as separate Agent Teams teammates with independent context — the implementation agent receives test task files as artifacts, not the test task agent's reasoning.

A new brownfield instruction doc at `home/.claude/docs/brownfield-breakdown.md` provides 5 codebase-awareness instructions loaded by the `/breakdown` skill when producing task files. These instructions ensure tasks reference existing code, follow established patterns, avoid new dependencies when equivalents exist, and search for existing equivalents before creating new abstractions.

The test validates structural modifications to the skill file and existence/content of the brownfield doc. It does not test runtime behavior.

## Instructions

1. Create `tests/sdl-workflow/test-breakdown-integration.sh` as a bash test script. Use `set -uo pipefail`. Define a test counter and pass/fail tracking at the top. Each test prints `ok <n> - <description>` on pass or `not ok <n> - <description>` on fail (TAP format).

2. Determine project root using `cd "$(dirname "$0")/../.." && pwd`. Define `SKILL_FILE` pointing to `home/.claude/skills/breakdown/SKILL.md` relative to project root. Define `BROWNFIELD_DOC` pointing to `home/.claude/docs/brownfield-breakdown.md` relative to project root.

3. Write test: skill file exists. Assert `$SKILL_FILE` exists and is a non-empty file.

4. Write test: skill file has valid YAML frontmatter. Assert the file starts with `---` on line 1 and contains a second `---` delimiter. Assert frontmatter contains a `description:` field.

5. Write test: skill specifies sequential agent execution. Search the skill file for language indicating sequential or ordered execution of two agents (e.g., "sequential", "first" and "then", "step 1" and "step 2", "before" and "after", numbered agent descriptions, or "followed by"). Assert the file describes two distinct agents that run in order.

6. Write test: skill defines test task agent. Search the skill file for "test task agent" or "test task" combined with "agent" or "teammate" (case-insensitive). Assert a match exists.

7. Write test: skill specifies test task agent receives only the spec. Search the context around the test task agent reference for language indicating it receives the spec as its primary or sole input (e.g., "only the spec", "spec only", "receives the spec", "spec as input", "spec artifact"). Assert no mention of task files or implementation output as input to the test task agent.

8. Write test: skill defines implementation task agent. Search the skill file for "implementation task agent" or "implementation task" combined with "agent" or "teammate" (case-insensitive). Assert a match exists.

9. Write test: skill specifies implementation task agent receives test task output. Search the context around the implementation task agent reference for language indicating it receives test task output, test task files, or the spec plus test tasks. Assert the implementation agent's input includes both the spec and test task output.

10. Write test: skill specifies Agent Teams invocation for context isolation. Search the skill file for "Agent Teams" or "teammate" (case-insensitive). Assert at least two matches exist (one per agent), confirming both agents use Agent Teams.

11. Write test: implementation agent receives artifacts not reasoning. Search the skill file for language distinguishing artifacts/output from reasoning/context (e.g., "artifacts, not", "not the test task agent's reasoning", "output as artifacts", "independent context", "files as input", "task files" combined with "not" and "reasoning", or "context isolation"). Assert a match exists.

12. Write test: skill specifies test task agent runs before implementation task agent. Find the line numbers for the test task agent description and the implementation task agent description. Assert the test task agent line number is less than the implementation task agent line number.

13. Write test: skill preserves existing gate invocation. Search the skill file for "breakdown-gate" (case-insensitive). Assert a match exists, confirming the existing gate is still referenced.

14. Write test: skill references task reviewer. Search the skill file for "task-reviewer" or "task reviewer" (case-insensitive). Assert a match exists.

15. Write test: skill references test reviewer checkpoint 2. Search the skill file for "checkpoint 2" or "test reviewer" combined with "task" in the context of review after breakdown. Assert a match exists.

16. Write test: brownfield doc exists. Assert `$BROWNFIELD_DOC` exists and is a non-empty file.

17. Write test: brownfield doc contains instruction about searching for related functionality. Search the doc for "search" and "related" or "existing" or "functionality". Assert a match exists.

18. Write test: brownfield doc contains instruction about referencing files by path. Search for "reference" or "path" combined with "file" or "existing code". Assert a match exists.

19. Write test: brownfield doc contains instruction about following established patterns. Search for "pattern" combined with "follow" or "established". Assert a match exists.

20. Write test: brownfield doc contains instruction about avoiding new dependencies. Search for "dependencies" or "dependency" combined with "new" or "equivalent" or "existing". Assert a match exists.

21. Write test: brownfield doc contains instruction about searching for existing equivalents. Search for "existing" combined with "equivalent" or "search" in the context of functions, utilities, or abstractions. Assert a match exists.

22. End the script with a summary: `echo "# <pass-count>/<total-count> tests passed"`. Exit 0 if all passed, exit 1 otherwise.

## Files to create/modify

- `tests/sdl-workflow/test-breakdown-integration.sh` (create)

## Test requirements

This is a test task. Tests to write (all in `test-breakdown-integration.sh`):
1. Structural: skill file exists and is non-empty
2. Structural: skill file has valid YAML frontmatter
3. Structural: skill specifies sequential agent execution (two agents in order)
4. Structural: skill defines test task agent
5. Structural: test task agent receives only the spec
6. Structural: skill defines implementation task agent
7. Structural: implementation task agent receives spec plus test task output
8. Structural: skill specifies Agent Teams invocation (at least two references)
9. Structural: implementation agent receives artifacts not reasoning
10. Structural: test task agent ordered before implementation task agent
11. Structural: skill preserves existing breakdown-gate invocation
12. Structural: skill references task reviewer
13. Structural: skill references test reviewer checkpoint 2
14. Structural: brownfield doc exists and is non-empty
15. Structural: brownfield doc contains search-for-related-functionality instruction
16. Structural: brownfield doc contains reference-files-by-path instruction
17. Structural: brownfield doc contains follow-established-patterns instruction
18. Structural: brownfield doc contains avoid-new-dependencies instruction
19. Structural: brownfield doc contains search-for-existing-equivalents instruction

## Acceptance criteria

AC-07: Breakdown produces test tasks and implementation tasks sequentially from context-independent Agent Teams teammates. Test task agent receives spec only. Implementation task agent receives spec plus test task output. Test tasks cover every AC. Implementation tasks reference specific test tasks as completion gates. Tasks are structured (no prose) and organized into waves.

## Model

Haiku

## Wave

3
