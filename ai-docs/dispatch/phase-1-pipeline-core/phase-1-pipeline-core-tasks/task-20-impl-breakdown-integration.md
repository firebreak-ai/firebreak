## Objective

Modify the existing `/breakdown` skill to implement sequential context-independent breakdown via two Agent Teams teammates and create the brownfield breakdown-stage instruction doc.

## Context

The `/breakdown` skill at `home/dot-claude/skills/breakdown/SKILL.md` currently compiles tasks in a single pass following `task-compilation.md`. This task replaces the monolithic compilation with two sequential Agent Teams teammates: a test task agent (receives only the spec, produces test tasks) and an implementation task agent (receives spec plus test task files, produces implementation tasks). Both run as separate Agent Teams teammates with independent context windows. After both complete, the task overview is assembled and the task reviewer gate (deterministic + test reviewer checkpoint 2) runs before the existing breakdown gate.

The brownfield doc at `home/dot-claude/docs/brownfield-breakdown.md` provides 5 instructions for both agents to load when producing task files in existing codebases.

All existing behavior around input validation, review gate check, and stage transitions must be preserved. The core change is how tasks are produced (two agents instead of one pass) and the addition of task reviewer + test reviewer invocations before the breakdown gate.

## Instructions

1. Read `home/dot-claude/skills/breakdown/SKILL.md` to understand the current structure.

2. Read `home/dot-claude/docs/sdl-workflow/task-compilation.md` to understand the current task compilation rules that the two agents must follow.

3. Preserve the existing frontmatter, argument handling, input location, input verification, and Stage 2 gate invocation (lines 1 through the review gate check). These remain unchanged.

4. Replace the current task compilation paragraph ("Compile tasks following the rules in `task-compilation.md`...") with the sequential agent execution described in steps 5-8 below.

5. Add a section `## Test task agent` with these instructions:
   - Invoke an Agent Teams teammate with independent context.
   - The teammate receives only the spec file (`ai-docs/$FEATURE/$FEATURE-spec.md`). It does NOT receive the review document, threat model, or any other artifacts.
   - Load brownfield instructions from `home/dot-claude/docs/brownfield-breakdown.md` and include them in the teammate's prompt.
   - The teammate produces test tasks from the spec's testing strategy and acceptance criteria. One task per AC or logical test group.
   - Each test task specifies: files to create, test framework conventions to follow, AC identifiers covered, and a completion gate (tests compile and fail before implementation).
   - Output: task files written to `ai-docs/$FEATURE/$FEATURE-tasks/` as `task-NN-test-<behavior>.md`.
   - Task files use Markdown with YAML frontmatter containing: `id`, `type: test`, `wave`, `covers` (AC identifiers), `files_to_create`, `completion_gate`. Markdown body contains implementation instructions.

6. Add a section `## Implementation task agent` with these instructions:
   - Invoke a second Agent Teams teammate with independent context, after the test task agent completes.
   - The teammate receives the spec file AND the test task files produced by the test task agent. It receives the test task files as artifacts — not the test task agent's reasoning or conversation.
   - Load brownfield instructions from `home/dot-claude/docs/brownfield-breakdown.md` and include them in the teammate's prompt.
   - The teammate produces implementation tasks from the spec's technical approach and acceptance criteria. Each task specifies: files to create/modify (explicit paths), AC identifiers satisfied, references to specific test tasks as completion gates, and constraints (file scope, no test modification).
   - Each implementation task references specific test task IDs. The completion gate for each implementation task is: the referenced tests pass.
   - Output: task files written to `ai-docs/$FEATURE/$FEATURE-tasks/` as `task-NN-impl-<behavior>.md`.
   - Task files use Markdown with YAML frontmatter containing: `id`, `type: implementation`, `wave`, `covers` (AC identifiers), `files_to_create`, `files_to_modify`, `test_tasks` (references to test task IDs), `completion_gate`. Markdown body contains implementation instructions.
   - Include wave assignments in each task's frontmatter. Wave N+1 tasks may reference files or behaviors produced by Wave N.

7. Add a section `## Task overview assembly` with these instructions:
   - After both agents complete, assemble `ai-docs/$FEATURE/$FEATURE-tasks/task-overview.md` with: dependency DAG (which tasks depend on which), wave assignments (summary table), model routing summary (which model for each task), and AC coverage map (which ACs are covered by which tasks, verifying completeness).

8. Add a section `## Task review` with these instructions:
   - Run the task reviewer's deterministic layer: `"$HOME"/.claude/hooks/sdl-workflow/task-reviewer-gate.sh "ai-docs/$FEATURE/$FEATURE-spec.md" "ai-docs/$FEATURE/$FEATURE-tasks"`. If it fails, report each failure and return to the test task agent step with specific feedback.
   - Invoke the test reviewer agent (`test-reviewer`) as an Agent Teams teammate with checkpoint 2 context. Pass the spec file and the task files as artifacts. If it fails, add its findings to the feedback and return to the test task agent step.
   - If both pass, proceed to the existing breakdown gate.

9. Preserve the existing Stage 3 gate invocation (`breakdown-gate.sh`). It runs after the task review step passes. Keep the existing gate invocation code and error handling verbatim.

10. Preserve the existing summary and next-steps section. Update the summary to reflect the new structure: total task count (test + implementation), wave count, test task count, implementation task count, and any task reviewer findings.

11. Preserve the existing context compaction and `/implement` invocation at the end.

12. Create `home/dot-claude/docs/brownfield-breakdown.md` with the following content (direct-address imperatives, no preamble, no heading):

    Paragraph 1: `Search the codebase for related functionality before producing task files. Map each task to specific existing files where possible.`

    Paragraph 2: `Each task that modifies existing code must reference files by path. Each task that creates a new file must state why an existing file is not the right location.`

    Paragraph 3: `When the codebase has an established pattern for the type of work a task describes, include a "follow the pattern in [file/function]" reference.`

    Paragraph 4: `Do not introduce new dependencies when the project already provides equivalent functionality. Search package manifests and existing imports before specifying new libraries.`

    Paragraph 5: `If a task would create a function, utility, or abstraction, search for existing equivalents first. Reference the search in the task instructions so the implementing agent inherits the context.`

    Each instruction is a separate paragraph (blank line between them). No heading, no preamble, no closing text.

13. Verify the brownfield doc:
    - Starts with the first instruction (no heading or preamble)
    - Contains exactly 5 instruction paragraphs
    - Each instruction uses direct-address imperative voice

14. Verify the modified skill file preserves: frontmatter, argument handling, input location, input verification, Stage 2 gate, Stage 3 gate (breakdown-gate.sh), summary, and transition logic.

## Files to create/modify

- `home/dot-claude/skills/breakdown/SKILL.md` (modify)
- `home/dot-claude/docs/brownfield-breakdown.md` (create)

## Test requirements

Tests from task-19 must pass. Run `bash tests/sdl-workflow/test-breakdown-integration.sh` from project root and verify all tests pass.

## Acceptance criteria

AC-07: Breakdown produces test tasks and implementation tasks sequentially from context-independent Agent Teams teammates. Test task agent receives spec only. Implementation task agent receives spec plus test task output. Test tasks cover every AC. Implementation tasks reference specific test tasks as completion gates. Tasks are structured (no prose) and organized into waves.

Primary AC: all tests from task-19 pass.

## Model

Sonnet

## Wave

3
