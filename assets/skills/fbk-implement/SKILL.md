---
description: >-
  Implement a feature from compiled task files. Use when implementing,
  building, or executing a task breakdown. Manages parallel agent team
  with wave-based execution and verification gates.
argument-hint: "[feature-name]"
---

This skill is phase six of the six-phase refactored SDL (intent → design → spec → breakdown → code-review → implement).

Read `.claude/fbk-docs/fbk-sdl-workflow/implementation-guide.md` for the complete wave execution protocol, verification rules, escalation protocol, checkpoint format, and retrospective structure. Follow that doc at every step below.

## Input

If `$ARGUMENTS` is empty, ask: "Which feature do you want to implement? Provide the feature name (matching the directory under `ai-docs/`)."

Set `FEATURE=$ARGUMENTS`. Paths used throughout:
- Task manifest: `ai-docs/$FEATURE/$FEATURE-tasks/task.json`
- Tasks dir: `ai-docs/$FEATURE/$FEATURE-tasks/`
- Spec: `ai-docs/$FEATURE/$FEATURE-spec.md`
- Review log: `ai-docs/$FEATURE/$FEATURE-review.md`
- Retrospective: `ai-docs/$FEATURE/$FEATURE-retrospective.md`

Read `task.json`. Verify it exists and is valid JSON conforming to the task manifest schema in `.claude/fbk-docs/fbk-sdl-workflow/task-compilation.md`. If missing or malformed, stop and tell the user what is absent.

## Prerequisite Gates

### Breakdown Gate

Run:

```
python3 "$HOME"/.claude/fbk-scripts/fbk.py breakdown-gate \
  "ai-docs/$FEATURE/$FEATURE-spec.md" \
  "ai-docs/$FEATURE/$FEATURE-tasks/"
```

If exit code is non-zero, report the failures and offer to run `/fbk-breakdown` to recompile the tasks. Do not proceed.

### Coherence Gate

Run:

```
python3 "$HOME"/.claude/fbk-scripts/fbk.py coherence-gate "ai-docs/$FEATURE"
```

If exit code is non-zero, report the failures and offer to run `/fbk-breakdown` (which produces the coherence artifact). Do not proceed.

## Team Setup

Check that `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` is set. If not, stop and inform the user — teammates cannot be spawned without this flag.

Follow the team setup protocol in the implementation guide for wave-width selection, team-lead role, and model assignment.

## Wave Loop

For each wave, follow the protocol in the implementation guide.

When creating native tasks for a wave's test or implementation tasks, use this spawn-prompt template:

```
Task file: ai-docs/$FEATURE/$FEATURE-tasks/task-NN-name.md
Read that task file and execute it. Treat the task file as your work specification — do not pull in other project context unless this prompt directs you to.

When the task involves authoring tests, also read `.claude/fbk-docs/fbk-design-guidelines/test-authoring.md` for the test-authoring rules — including the mocks rule (stand-ins only for code we don't own).

Before your turn ends, send a work summary message to the team lead describing what you created, what verification you ran, and any caveats. A turn ending without this message is incomplete work.
```

## Escalation Protocol

Follow the escalation protocol in the implementation guide.

## Final Verification

After the final wave checkpoint, run the structural and semantic checks per the implementation guide.

## Retrospective

Write the Implementation section per the implementation guide.

## Team Shutdown

Follow the team-shutdown protocol in the implementation guide. After completing that protocol (including the closing summary), ask the user: "Would you like to review the implementation with /fbk-code-review?"
