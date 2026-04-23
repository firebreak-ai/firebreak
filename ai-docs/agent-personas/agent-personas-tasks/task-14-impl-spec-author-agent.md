---
id: task-14
type: implementation
wave: 1
covers: [AC-05, AC-06]
files_to_create:
  - assets/agents/fbk-spec-author.md
test_tasks: [task-04]
completion_gate: "task-04 tests pass"
---

## Objective

Create `assets/agents/fbk-spec-author.md` — a new persona-only agent definition for the spec author role. The file must have valid YAML frontmatter (with `name`, `description`, and a `tools` allowlist restricted to `Read, Grep, Glob`), a body at or below 40 lines containing a role-activation line, an `## Output quality bars` section, and an `## Anti-defaults` section.

## Context

The `/fbk-spec` skill currently runs in the main session with no agent delegation — specs are drafted without role activation. The spec creates a named agent definition so future skill integration can spawn a persona-activated spec author. The agent is persona-only: no task workflow sections, no input contract. The skill that spawns it supplies task context via the spawn prompt.

The reference implementations are `assets/agents/fbk-code-review-challenger.md` (21-line minimal persona) and `assets/agents/fbk-code-review-detector.md` (47-line full pattern with quality bars). This new file follows the same shape.

Tool scoping: the spec says Read, Grep, Glob — read-only, because the skill handles file writes. Do not grant Edit, Write, or Bash.

## Instructions

1. Verify the file does not already exist (the test task expects it to be missing pre-implementation).
2. Create `assets/agents/fbk-spec-author.md` with this exact content:

   ```
   ---
   name: fbk-spec-author
   description: "Principal engineer drafting technical specifications. Surfaces ambiguity in behavioral contracts, demands specificity in technical approach sections, refuses to hand-wave integration points."
   tools: Read, Grep, Glob
   model: sonnet
   ---

   You are a principal engineer at an enterprise software company writing technical specifications. You treat spec drafting as adversarial design review — the spec is not done until a reviewer can challenge every decision and a task compiler can derive tasks without follow-up questions.

   ## Output quality bars

   - Surface ambiguity in behavioral contracts rather than silently assuming an answer. When a requirement admits two reasonable interpretations, name both and ask — do not guess.
   - Technical approach sections are specific enough that a reviewer can challenge design decisions and a task compiler can derive tasks without follow-up questions. Vague phrases like "appropriate handling" or "sensible defaults" do not meet this bar.
   - Refuse to hand-wave integration points. Name the components involved, the data flow between them, and the failure modes at each boundary.

   ## Anti-defaults

   - The model's default spec-writing mode is compliant drafting — agreeing with the user's framing rather than probing for gaps. Activate the adversarial design review distribution: when the user's framing is underspecified, surface the gap before drafting around it.
   ```

3. Verify the body (post-frontmatter) line count is at or below 40:
   ```bash
   awk '/^---$/{c++; if(c==2){found=1; next}} found' assets/agents/fbk-spec-author.md | wc -l
   ```
4. Verify frontmatter `tools:` field lists exactly `Read, Grep, Glob` and does not contain `Edit`, `Write`, or `Bash`.
5. Run `bash tests/sdl-workflow/test-new-persona-agents.sh`. The 7 assertions targeting this file (existence, frontmatter validity, ≤40-line body, `## Output quality bars` heading, non-empty `name`/`description`, tools allowlist matches, role-activation phrase `principal engineer`) must pass.

## Files to create/modify

- **Create**: `assets/agents/fbk-spec-author.md` — new file. This file cannot be co-located with an existing agent because Claude Code agent definitions are one-file-per-agent, identified by filename and the frontmatter `name` field.

## Test requirements

No new tests. The paired test task `task-04-test-new-agent-files.md` covers structural assertions for this file.

## Acceptance criteria

- `tests/sdl-workflow/test-new-persona-agents.sh` — all 7 assertions for `fbk-spec-author.md` pass
- Covers AC-05 (new persona agent) and the structural half of AC-06
- Frontmatter tools list restricted to Read, Grep, Glob (no Edit, Write, Bash)

## Model

Haiku

## Wave

1
