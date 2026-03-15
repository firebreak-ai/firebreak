# Task 003: Create the Skill Trigger

**Output file**: `.claude/skills/context-asset-authoring/SKILL.md`
**Dependencies**: 001 (index must exist to reference it)

## Context

This skill catches scenarios where no file path exists yet — creating new context assets, discussing context strategy, planning context structure. It uses `user-invocable: false` so the agent loads it via description matching rather than a slash command.

Read `ai-docs/mvp-000/plan.md` section: "File descriptions > Triggers > 2."

## Output Specification

Create `.claude/skills/context-asset-authoring/SKILL.md` with:

### Frontmatter

YAML frontmatter for a non-user-invocable skill:

```yaml
---
user-invocable: false
description: >-
  [Description for agent matching — see below]
---
```

Confirm the correct YAML frontmatter schema for Claude Code skills by checking Claude Code documentation. Key fields: `user-invocable`, `description`. Check whether `allowed-tools` or other fields are relevant.

### Description

Write a description that will match when the agent is:
- Creating a new context asset (CLAUDE.md, rule, skill, hook, agent, or docs file)
- Discussing context asset strategy or structure
- Planning how to organize project context

The description must use clear, matchable language — vague or overly broad descriptions reduce discovery reliability. (Implementation note: this guidance comes from research on skill discovery failure rates. The authored output should state the principle without citing the research.)

Keep the description focused. It should match context asset authoring scenarios specifically, not general coding tasks.

### Body

Same routing instruction as the rule trigger: direct the agent to read `.claude/docs/context-assets.md`. Maximum 2-3 sentences.

## Verification Criteria

- [ ] `user-invocable: false` is set
- [ ] Description is specific to context asset authoring scenarios
- [ ] Description uses clear, concrete language (not vague abstractions)
- [ ] Body references `.claude/docs/context-assets.md` by exact path
- [ ] Body is routing only — no authoring guidance inline
- [ ] File follows its own principles (no preamble, positive framing, imperative)
