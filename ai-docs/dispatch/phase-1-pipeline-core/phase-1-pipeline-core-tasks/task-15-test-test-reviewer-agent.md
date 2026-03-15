## Objective

Write a bash test script that validates the test reviewer agent definition file exists and contains all required structural elements.

## Context

The test reviewer agent is a Claude Code agent definition at `home/.claude/agents/test-reviewer.md`. It uses YAML frontmatter and a Markdown body following the patterns in `home/.claude/docs/context-assets/agents.md`. The agent validates test quality at 5 pipeline checkpoints with pipeline-blocking authority. Each checkpoint must define: artifact set (what it receives), evaluation criteria, pass/fail conditions, and output format. The agent operates under context isolation — each invocation is independent with no access to other agents' reasoning.

The 5 checkpoints are:
1. Spec review (Stage 3) — receives spec + spec schema
2. Task review (Stage 5) — receives spec + task files
3. Test code review (Stage 7) — receives spec + test code
4. Test integrity (Stage 9) — receives spec + implemented code + tests
5. Mutation testing (Stage 9) — receives spec + implemented code only (NOT test code)

The test validates structural completeness only. It does not evaluate whether the agent definition produces correct behavior when invoked — that is validated through pipeline operation.

## Instructions

1. Create `tests/sdl-workflow/test-test-reviewer-agent.sh` as a bash test script. Use `set -uo pipefail`. Define a test counter and pass/fail tracking at the top. Each test prints `ok <n> - <description>` on pass or `not ok <n> - <description>` on fail (TAP format).

2. Determine project root using `cd "$(dirname "$0")/../.." && pwd`. Define `AGENT_FILE` pointing to `home/.claude/agents/test-reviewer.md` relative to project root.

3. Write test: agent file exists. Assert `$AGENT_FILE` exists and is a non-empty file.

4. Write test: file has YAML frontmatter. Assert the file starts with `---` on line 1. Assert a second `---` appears on a subsequent line (closing the frontmatter block).

5. Write test: frontmatter contains `name` field. Extract the frontmatter (lines between the two `---` delimiters). Assert it contains a line matching `name:` with a non-empty value.

6. Write test: frontmatter contains `description` field. Assert frontmatter contains a line matching `description:` with a non-empty value.

7. Write test: body contains agent role/persona. Assert the Markdown body (content after the closing `---`) contains the word "test" and one of "reviewer", "review", or "validate" within the first 10 lines of the body, confirming the agent's role is stated.

8. Write test: body defines checkpoint 1 (spec review). Search the body for a section or heading containing "spec review" (case-insensitive). Assert the section exists. Assert the section contains "spec" and "schema" (the artifact set). Assert the section contains "testing strategy" or "AC" (evaluation criteria).

9. Write test: body defines checkpoint 2 (task review). Search for a section containing "task review" (case-insensitive). Assert it exists. Assert it contains "task files" or "task file" (artifact set). Assert it references "testing strategy" or "breakdown" (evaluation criteria).

10. Write test: body defines checkpoint 3 (test code review). Search for a section containing "test code review" (case-insensitive). Assert it exists. Assert it contains "test code" (artifact set). Assert it references "compile" or "fail" or "trace" (evaluation criteria).

11. Write test: body defines checkpoint 4 (test integrity). Search for a section containing "test integrity" or "integrity" (case-insensitive). Assert it exists. Assert it contains "implementation" or "implemented" (artifact set). Assert it references "weaken" or "coverage" or "trivial" or "quality" or "regression" or "adequate" (evaluation criteria).

12. Write test: body defines checkpoint 5 (mutation testing). Search for a section containing "mutation" (case-insensitive). Assert it exists. Assert it contains "implemented code" or "implementation" (artifact set). Assert it does NOT contain language indicating it receives test code as input (the mutation checkpoint generates its own mutations). Assert it references "mutation" and one of "detection rate", "hash", "verified", "kill", or "survive".

13. Write test: pipeline-blocking authority specified. Assert the body contains "pipeline-blocking" or "block" or "blocking" combined with "authority" or "fail" or "reject" or "prevent" within a proximate context.

14. Write test: context isolation specified. Assert the body contains "context isolation" or "independent context" or "no access" or "independent" or "isolated" combined with "reasoning" or "memory" or "prior" or "context" or "conversation".

15. Write test: output format specified for each checkpoint. Assert the body contains "pass" and "fail" in the context of output or format. Assert the body references structured output (e.g., "structured", "format", "findings", "defect").

16. Write test: each checkpoint specifies its artifact set. For each of the 5 checkpoint sections found in steps 8-12, assert the section contains "receives" or "artifact" or "input" describing what the checkpoint is given.

17. Write test: brownfield mode mentioned. Assert the body contains "brownfield" at least once.

18. Write test: on-demand invocation pattern. Assert the body or frontmatter contains "test-review" (the slash command name for on-demand use outside the pipeline).

19. End the script with a summary: `echo "# <pass-count>/<total-count> tests passed"`. Exit 0 if all passed, exit 1 otherwise.

## Files to create/modify

- `tests/sdl-workflow/test-test-reviewer-agent.sh` (create)

## Test requirements

This is a test task. Tests to write (all in `test-test-reviewer-agent.sh`):
1. Structural: agent file exists and is non-empty
2. Structural: file has YAML frontmatter with opening and closing delimiters
3. Structural: frontmatter contains `name` field
4. Structural: frontmatter contains `description` field
5. Structural: body establishes agent role/persona
6. Structural: checkpoint 1 (spec review) defined with artifact set and evaluation criteria
7. Structural: checkpoint 2 (task review) defined with artifact set and evaluation criteria
8. Structural: checkpoint 3 (test code review) defined with artifact set and evaluation criteria
9. Structural: checkpoint 4 (test integrity) defined with artifact set and evaluation criteria
10. Structural: checkpoint 5 (mutation testing) defined with correct artifact set (no test code input)
11. Structural: pipeline-blocking authority specified
12. Structural: context isolation requirement specified
13. Structural: output format specified (structured pass/fail with findings)
14. Structural: each checkpoint specifies its artifact set
15. Structural: brownfield mode mentioned
16. Structural: on-demand invocation pattern present

## Acceptance criteria

AC-06: Test reviewer agent validates test quality at checkpoints 1 (spec review), 2 (task review), and 3 (test code review) with pipeline-blocking authority. Each checkpoint receives only its appropriate artifacts (context isolation).

## Model

Haiku

## Wave

2
