---
id: T-02
type: test
wave: 3
covers: ["AC-07"]
files_to_create: ["tests/sdl-workflow/test-code-review-skill.sh"]
completion_gate: "Test script runs and all tests fail (skill files do not exist yet)"
---

## Objective

Creates a bash test script that validates the `/code-review` skill file routes to both path-specific references and that the `/implement` skill contains the post-implementation stage-transition prompt.

## Context

Phase 1.6 creates a `/code-review` skill with dual-mode routing and modifies the `/implement` skill to add a post-implementation review prompt. Wave 3 implementation tasks produce:

- `home/dot-claude/skills/code-review/SKILL.md` — The skill entry point with YAML frontmatter (`description`, `argument-hint`, `allowed-tools` fields). The body loads shared docs from `docs/sdl-workflow/` (code-review-guide.md, ai-failure-modes.md) and routes to path-specific references based on invocation context:
  - `references/existing-code-review.md` for standalone conversational review
  - `references/post-impl-review.md` for post-implementation findings-only mode
- `home/dot-claude/skills/code-review/references/existing-code-review.md` — Conversational review flow and spec co-authoring guidance
- `home/dot-claude/skills/code-review/references/post-impl-review.md` — Post-implementation findings-only flow

The `/implement` skill at `home/dot-claude/skills/implement/SKILL.md` receives a one-line addition: after implementation completion, it asks the user "would you like to review the implementation?" following the existing stage-transition pattern used elsewhere in the pipeline.

This test covers AC-07: the code review skill works as a standalone invocation and as a post-implementation pipeline stage.

Follow the TAP format and boilerplate conventions established in `tests/sdl-workflow/test-review-integration.sh`.

## Instructions

1. Create `tests/sdl-workflow/test-code-review-skill.sh` as a bash test script. Use `set -uo pipefail`. Define `PASS`, `FAIL`, `TOTAL` counters. Define `ok()` and `not_ok()` helper functions matching the pattern in existing tests. Print `TAP version 13` before the first test.

2. Determine project root using `cd "$(dirname "$0")/../.." && pwd`. Define these path variables:
   - `SKILL_FILE="$PROJECT_ROOT/home/dot-claude/skills/code-review/SKILL.md"`
   - `EXISTING_REF="$PROJECT_ROOT/home/dot-claude/skills/code-review/references/existing-code-review.md"`
   - `POSTIMPL_REF="$PROJECT_ROOT/home/dot-claude/skills/code-review/references/post-impl-review.md"`
   - `IMPLEMENT_SKILL="$PROJECT_ROOT/home/dot-claude/skills/implement/SKILL.md"`

3. Write test: SKILL.md exists and is non-empty. Assert `-s "$SKILL_FILE"`.

4. Write test: SKILL.md has valid YAML frontmatter. Assert line 1 is `---`, at least 2 `---` lines exist, and frontmatter contains `description:`.

5. Write test: SKILL.md frontmatter contains `allowed-tools` field. Extract frontmatter. Assert it contains a line matching `allowed-tools:`. The spec requires: Read, Grep, Glob, Write, Edit, Bash, Agent.

6. Write test: SKILL.md `allowed-tools` includes Agent. Assert the `allowed-tools:` line contains `Agent`. The skill needs Agent to spawn Detector/Challenger subagents.

7. Write test: SKILL.md references the existing-code-review reference file. Search the skill body for `existing-code-review` or `existing code review` (case-insensitive). Assert at least one match.

8. Write test: SKILL.md references the post-impl-review reference file. Search the skill body for `post-impl-review` or `post-impl review` or `post-implementation review` (case-insensitive). Assert at least one match.

9. Write test: SKILL.md loads shared code-review-guide. Search the skill body for `code-review-guide` or `code review guide` (case-insensitive). Assert at least one match, confirming the skill loads the shared behavioral comparison methodology.

10. Write test: SKILL.md loads shared ai-failure-modes checklist. Search for `ai-failure-modes` or `ai failure modes` or `failure mode` (case-insensitive). Assert at least one match.

11. Write test: SKILL.md implements path routing. Search for language indicating routing between standalone and post-implementation modes. Assert the body contains one of: `invocation context`, `standalone`, `post-implementation`, `path`, `route`, `mode` combined with evidence of conditional behavior.

12. Write test: existing-code-review.md reference file exists and is non-empty. Assert `-s "$EXISTING_REF"`.

13. Write test: existing-code-review.md contains conversational review guidance. Search for `conversation` or `conversational` or `user` combined with `spec` or `co-author` or `draft` (case-insensitive). Assert at least one match.

14. Write test: post-impl-review.md reference file exists and is non-empty. Assert `-s "$POSTIMPL_REF"`.

15. Write test: post-impl-review.md contains findings-only guidance. Search for `findings` or `findings-only` or `non-interactive` (case-insensitive). Assert at least one match.

16. Write test: post-impl-review.md does not include spec co-authoring. Search for `co-author` or `spec draft` or `draft spec` in the post-impl reference. Assert zero matches (or that any matches are explicitly saying NOT to do spec co-authoring). The post-impl path produces findings only — no spec conversation.

17. Write test: `/implement` skill contains post-implementation review prompt. Search `$IMPLEMENT_SKILL` for `review the implementation` or `code review` or `code-review` (case-insensitive). Assert at least one match, confirming the stage-transition prompt was added.

18. Write test: `/implement` skill's review prompt follows stage-transition pattern. Search for language indicating user choice: `would you like` or `ask` combined with `review` (case-insensitive). Assert at least one match. The existing stage-transition pattern asks the user rather than auto-triggering.

19. End the script with a summary: print `echo ""`, then `echo "# $PASS/$TOTAL tests passed"`. Exit 0 if `$FAIL` is 0, exit 1 otherwise.

## Files to create/modify

- `tests/sdl-workflow/test-code-review-skill.sh` (create)

## Test requirements

This is a test task. Tests to write (all in `test-code-review-skill.sh`):

1. Structural: SKILL.md exists and is non-empty
2. Structural: SKILL.md has valid YAML frontmatter with description
3. Structural: SKILL.md frontmatter contains allowed-tools field
4. Structural: SKILL.md allowed-tools includes Agent for subagent spawning
5. Structural: SKILL.md references existing-code-review reference
6. Structural: SKILL.md references post-impl-review reference
7. Structural: SKILL.md loads shared code-review-guide
8. Structural: SKILL.md loads shared ai-failure-modes checklist
9. Structural: SKILL.md implements path routing between modes
10. Structural: existing-code-review.md exists and is non-empty
11. Structural: existing-code-review.md contains conversational review guidance
12. Structural: post-impl-review.md exists and is non-empty
13. Structural: post-impl-review.md contains findings-only guidance
14. Structural: post-impl-review.md excludes spec co-authoring
15. Structural: /implement skill contains post-implementation review prompt (AC-07 post-impl trigger)
16. Structural: /implement skill's review prompt follows stage-transition pattern

## Acceptance criteria

- AC-07: The code review skill works as standalone invocation (SKILL.md routes to existing-code-review.md) and as post-implementation pipeline stage (SKILL.md routes to post-impl-review.md; /implement skill contains the stage-transition prompt)

## Model

Haiku

## Wave

Wave 3
