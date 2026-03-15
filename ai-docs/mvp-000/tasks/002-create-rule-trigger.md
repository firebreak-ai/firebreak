# Task 002: Create the Rule Trigger — SUPERSEDED

**Status**: Superseded — rule trigger deleted.

**Reason**: `paths:` frontmatter in `~/.claude/rules/` is silently ignored (GitHub #21858). The rule loaded unconditionally for every session, adding noise without providing path-scoped activation. Path resolution is project-root-relative, so it cannot match `~/.claude/` files even if fixed. The skill trigger (task 003) provides the correct activation via description matching.

**Action taken**: Deleted `home/.claude/rules/context-asset-authoring.md`. Updated `rules.md` leaf with scope warning about `paths:` unreliability at user scope.

---

*Original task below for traceability.*

**Output file**: `.claude/rules/context-asset-authoring.md`
**Dependencies**: 001 (index must exist to reference it)

## Context (Original)

This rule auto-loads when the agent edits files in context asset directories. It is a thin trigger — its only job is to route the agent to the index document.

Read `ai-docs/mvp-000/plan.md` section: "File descriptions > Triggers > 1."

## Output Specification

Create `.claude/rules/context-asset-authoring.md` with:

### Frontmatter

YAML frontmatter with `paths:` scoped to context asset file patterns:

```yaml
---
paths:
  - .claude/skills/**/*.md
  - .claude/docs/**/*.md
  - .claude/rules/**/*.md
  - .claude/agents/**/*.md
  - "**/CLAUDE.md"
---
```

Confirm the correct YAML syntax for Claude Code rule frontmatter by checking existing rules in the project or Claude Code documentation.

### Body

One concise instruction directing the agent to read `.claude/docs/context-assets.md` for authoring guidelines. Maximum 2-3 sentences. This trigger exists to route, not to instruct.

**Scoping rationale** (do not include in the file — this is implementation context):
- Scopes to `.md` files in context asset directories, not to all of `.claude/`
- Excludes `.claude/settings.json` (shared config — would over-trigger for non-hook edits)
- Excludes `.claude/settings.local.json` (same reason)

## Verification Criteria

- [ ] Frontmatter `paths:` includes all 5 patterns listed above
- [ ] Body is 2-3 sentences maximum
- [ ] Body references `.claude/docs/context-assets.md` by exact path
- [ ] No authoring guidance in the body itself — routing only
- [ ] File follows its own principles (no preamble, positive framing, imperative)
