---
id: task-16
type: implementation
wave: 1
covers: [AC-05, AC-06]
files_to_create:
  - assets/agents/fbk-implementer.md
test_tasks: [task-04]
completion_gate: "task-04 tests pass"
---

## Objective

Create `assets/agents/fbk-implementer.md` — a new persona-only agent definition for the implementer role. The file must have valid YAML frontmatter (with `name`, `description`, and a `tools` allowlist containing all six of `Read, Grep, Glob, Edit, Write, Bash`), a body at or below 40 lines containing a role-activation line, an `## Output quality bars` section, and an `## Anti-defaults` section.

## Context

The `/fbk-implement` skill currently spawns anonymous teammates with inline implementation instructions. The spec creates a named agent definition so future skill integration can spawn a persona-activated implementer. Unlike the spec-author and task-compiler, this agent needs full implementation capability — Edit, Write, Bash are required alongside the read tools.

The reference implementations are `assets/agents/fbk-code-review-challenger.md` and `assets/agents/fbk-code-review-detector.md`. This new file follows the same activation-focused shape.

The persona targets maintainability — the anti-default section specifically calls out tutorial-grade code as the default to resist. The pipeline's test-first gates and per-wave verification handle correctness; the persona's job is to ensure the code that passes those gates is also code other engineers can read, modify, and extend.

## Instructions

1. Verify the file does not already exist.
2. Create `assets/agents/fbk-implementer.md` with this exact content:

   ```
   ---
   name: fbk-implementer
   description: "Senior engineer implementing against a reviewed specification. Follows the spec's technical approach, writes maintainable code, flags ambiguity rather than guessing."
   tools: Read, Grep, Glob, Edit, Write, Bash
   model: sonnet
   ---

   You are a senior engineer at an enterprise software company implementing against a reviewed specification. Other engineers will inherit the code you write — you optimize for their ability to read, modify, and extend it, not just for passing tests on the first run.

   ## Output quality bars

   - Implementation follows the spec's technical approach, not an alternative design you prefer. When the spec is wrong, raise the mismatch; do not silently correct it.
   - Code passes the referenced test tasks, not tests you write ad-hoc. The test tasks define behavioral completeness; additional tests are scope.
   - When the task file is ambiguous, implement the conservative interpretation and flag the ambiguity in the task summary rather than guessing the expansive interpretation.

   ## Anti-defaults

   - The model's default implementation mode produces tutorial-grade code — working for the happy path but harder to maintain than necessary. Prefer composition over deep inheritance, name variables for their domain meaning, extract repeated logic into named functions, and follow the existing code patterns in the codebase over introducing new ones.
   ```

3. Verify the body (post-frontmatter) line count is at or below 40:
   ```bash
   awk '/^---$/{c++; if(c==2){found=1; next}} found' assets/agents/fbk-implementer.md | wc -l
   ```
4. Verify frontmatter `tools:` field lists all six of `Read`, `Grep`, `Glob`, `Edit`, `Write`, `Bash`.
5. Run `bash tests/sdl-workflow/test-new-persona-agents.sh`. The 7 assertions targeting this file (existence, frontmatter validity, ≤40-line body, `## Output quality bars` heading, non-empty `name`/`description`, tools allowlist includes all six, role-activation phrase `senior engineer`) must pass.

## Files to create/modify

- **Create**: `assets/agents/fbk-implementer.md` — new file. Agent definitions are one-file-per-agent.

## Test requirements

No new tests. The paired test task `task-04-test-new-agent-files.md` covers structural assertions for this file.

## Acceptance criteria

- `tests/sdl-workflow/test-new-persona-agents.sh` — all 7 assertions for `fbk-implementer.md` pass
- Covers AC-05 and the structural half of AC-06
- Frontmatter tools list includes Read, Grep, Glob, Edit, Write, Bash

## Model

Haiku

## Wave

1
