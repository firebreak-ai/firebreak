# Task 14: Create /implement Skill

## Objective

Create the user-invocable skill that serves as the Stage 4 entry point for team-based wave execution of compiled tasks.

## Context

The `/implement` skill is the most complex skill in the pipeline. It manages an agent team: spawning teammates, advancing waves, handling verification failures, re-planning, and producing a retrospective. The main thread (team lead) runs this skill while teammates execute individual tasks.

### Skill behavior

1. **Argument handling**: Expects `/implement <feature-name>`. If omitted, ask.

2. **Read task overview**: Load from `ai-docs/<feature-name>/<feature-name>-tasks/task-overview.md`.

3. **Fail fast**: Check Stage 3 gate. Call: `"$HOME"/.claude/hooks/sdl-workflow/breakdown-gate.sh <spec-path> <tasks-dir>`. If fail, report and offer to run `/breakdown`.

4. **Load guidance**: Read `home/dot-claude/docs/sdl-workflow/implementation-guide.md` for wave execution protocol.

5. **Team setup**:
   - Check for `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` flag.
   - Verify the `TaskCompleted` hook is configured in `~/.claude/settings.json`. If missing, warn the user that per-task verification won't fire and ask whether to proceed.
   - Create an agent team.
   - Spawn teammates matching maximum wave width.

6. **Wave execution**: Advance wave by wave per the implementation guide protocol:
   - Create test task natives → verify compilation → create impl task natives → per-wave verification → wave checkpoint.
   - Test tasks before impl tasks within each wave.
   - Create native tasks wave by wave (not all upfront).
   - Each native task's description includes the path to its task file.

7. **Task isolation**: Teammates read only their task file. The skill ensures non-overlapping scopes (guaranteed by Stage 3).

8. **Verification**: Per-wave checks after all wave tasks complete. Final verification after last wave.

9. **Failure handling**: Re-plan protocol per the implementation guide. Cap at 2 re-plans per task, then escalate.

10. **Wave checkpoint**: After each wave passes verification — summarize, report test results, offer commit.

11. **Final verification + retrospective**: Run final checks. Write retrospective to `ai-docs/<feature-name>/<feature-name>-retrospective.md`.

12. **Team shutdown**: Shut down teammates, clean up team, summarize completion.

### Frontmatter

```yaml
---
description: >-
  Implement a feature from compiled task files. Use when implementing,
  building, or executing a task breakdown. Manages parallel agent team
  with wave-based execution and verification gates.
argument-hint: "[feature-name]"
---
```

### Key design decisions for the implementing agent

- **TaskCompleted hook**: Already configured in user-global settings (`~/.claude/settings.json`) with a context-check script that no-ops outside SDL. The skill does not need to configure or remove it — it is always present and self-scoping. The skill should verify the hook is configured (check settings for the `TaskCompleted` entry) and warn the user if missing.
- **Teammate model routing**: Task files specify Haiku or Sonnet. Use the `model` parameter when spawning teammates via the Agent tool to match the task's model assignment.
- **Native task descriptions**: Include the full path to the task file so the teammate can read it as its sole context.
- **Wave advancement control**: Only create next-wave native tasks after current wave passes all verification.

## Instructions

1. Create directory `home/dot-claude/skills/implement/` if it doesn't exist.
2. Create `home/dot-claude/skills/implement/SKILL.md`.
3. Read the created docs at:
   - `home/dot-claude/docs/sdl-workflow/implementation-guide.md` (primary doc)
   - `home/dot-claude/docs/context-assets/skills.md` (skill authoring principles)
4. Write the skill with:

   **Frontmatter**: As specified above.

   **Body**:

   - **First line**: Route to the implementation guide doc.
   - **Input loading**: Read task overview. Verify it exists with expected structure.
   - **Prior stage gate**: Run breakdown gate script. If fail, offer `/breakdown`.
   - **Team setup**: Check experimental flag. Verify TaskCompleted hook is in settings (warn if missing). Create team. Spawn teammates. The implementation guide has the full protocol — reference it here, don't duplicate.
   - **Wave loop**: High-level loop structure: for each wave, create test tasks → verify compile → create impl tasks → per-wave verification → checkpoint. Reference the doc for details at each step.
   - **Failure handling**: Re-plan protocol reference. Include the escalation cap (2 attempts, then user).
   - **Final verification**: After last wave checkpoint.
   - **Retrospective**: Write the retrospective artifact.
   - **Team shutdown**: Clean up and summary.

5. This skill will be longer than the others due to team management complexity. Target: 100-130 lines. The implementation guide doc carries the detailed protocol — the skill provides the control flow skeleton.
6. Do NOT use `allowed-tools` — needs full access including Agent tool for team management, Bash for running tests/gates, Read/Write for artifacts.

## Files to Create/Modify

- **Create**: `home/dot-claude/skills/implement/SKILL.md`

## Acceptance Criteria

- AC-10: Skill loads doc, manages team waves, runs verification, produces retrospective
- AC-15: Follows skill authoring principles

## Model

Sonnet

## Wave

2
