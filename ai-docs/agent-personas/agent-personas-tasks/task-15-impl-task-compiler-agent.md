---
id: task-15
type: implementation
wave: 1
covers: [AC-05, AC-06]
files_to_create:
  - assets/agents/fbk-task-compiler.md
test_tasks: [task-04]
completion_gate: "task-04 tests pass"
---

## Objective

Create `assets/agents/fbk-task-compiler.md` — a new persona-only agent definition for the task compiler role. The file must have valid YAML frontmatter (with `name`, `description`, and a `tools` allowlist restricted to `Read, Grep, Glob`), a body at or below 40 lines containing a role-activation line, an `## Output quality bars` section, and an `## Anti-defaults` section.

## Context

The `/fbk-breakdown` skill currently spawns anonymous teammates with inline task-compilation instructions. The spec creates a named agent definition so future skill integration can spawn a persona-activated task compiler. A single file serves both the test-task and impl-task compiler roles — the persona (role activation, quality bars, anti-defaults) is invariant across the two roles; what differs is the task context injected by the spawn prompt (spec-only for test tasks, spec + test task files for impl tasks).

The reference implementations are `assets/agents/fbk-code-review-challenger.md` and `assets/agents/fbk-code-review-detector.md`. This new file follows the same activation-focused shape.

Tool scoping: Read, Grep, Glob — read-only, because the skill handles file writes. Do not grant Edit, Write, or Bash.

## Instructions

1. Verify the file does not already exist.
2. Create `assets/agents/fbk-task-compiler.md` with this exact content:

   ```
   ---
   name: fbk-task-compiler
   description: "Tech lead decomposing a reviewed spec into implementable units. Traces every AC to tasks, specifies file paths and completion gates, orders waves by actual dependency."
   tools: Read, Grep, Glob
   model: sonnet
   ---

   You are a tech lead at an enterprise software company decomposing a reviewed specification into implementable units for a team. You produce tasks that a peer engineer can execute without needing to re-read the spec.

   ## Output quality bars

   - Every AC traces to at least one task, and every task traces to at least one AC. An AC without task coverage or a task without an AC is a compilation defect, not a drafting preference.
   - Tasks include explicit file paths and completion gates. "Update the relevant files" does not meet this bar; name each file and state the verifiable condition that proves the task is done.
   - Wave ordering reflects actual dependencies, not arbitrary sequencing. When two tasks touch the same file, assign them to sequential waves. When tasks are independent, they parallelize in the same wave.

   ## Anti-defaults

   - The model's default decomposition produces tasks that are either too granular (one function per task) or too coarse (one wave per feature). Match task boundaries to behavioral boundaries — each task is a single verifiable behavior with a 1-2 file scope.
   ```

3. Verify the body (post-frontmatter) line count is at or below 40:
   ```bash
   awk '/^---$/{c++; if(c==2){found=1; next}} found' assets/agents/fbk-task-compiler.md | wc -l
   ```
4. Verify frontmatter `tools:` field lists exactly `Read, Grep, Glob` and does not contain `Edit`, `Write`, or `Bash`.
5. Run `bash tests/sdl-workflow/test-new-persona-agents.sh`. The 7 assertions targeting this file (existence, frontmatter validity, ≤40-line body, `## Output quality bars` heading, non-empty `name`/`description`, tools allowlist matches, role-activation phrase `tech lead`) must pass.

## Files to create/modify

- **Create**: `assets/agents/fbk-task-compiler.md` — new file. Agent definitions are one-file-per-agent; this file cannot be merged with an existing agent.

## Test requirements

No new tests. The paired test task `task-04-test-new-agent-files.md` covers structural assertions for this file.

## Acceptance criteria

- `tests/sdl-workflow/test-new-persona-agents.sh` — all 7 assertions for `fbk-task-compiler.md` pass
- Covers AC-05 and the structural half of AC-06
- Frontmatter tools list restricted to Read, Grep, Glob (no Edit, Write, Bash)

## Model

Haiku

## Wave

1
