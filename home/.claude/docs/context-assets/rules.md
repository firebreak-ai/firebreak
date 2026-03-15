Place critical constraints in the first 3 lines of every rule file.
Scope every rule with `paths:` frontmatter unless it genuinely applies to every session.
Keep each rule file to a single concern.

## `paths:` Frontmatter

Add YAML frontmatter with a `paths:` field to scope when the rule loads. Treat a rule without `paths:` as equivalent to CLAUDE.md — it loads unconditionally every session.

```yaml
---
paths:
  - "**/*.go"
---
```

The `paths:` field accepts a YAML list of glob patterns. Quote patterns that start with `*` or `{` to avoid YAML parsing errors.

### Supported glob patterns

| Pattern | Matches |
|---------|---------|
| `"**/*.go"` | All Go files in any directory |
| `"src/api/**/*.ts"` | All TypeScript files under `src/api/` |
| `.claude/docs/**/*.md` | All markdown files under `.claude/docs/` |
| `"**/*.{ts,tsx}"` | All `.ts` and `.tsx` files (brace expansion) |

Specify multiple patterns as separate list items:

```yaml
---
paths:
  - "**/*.go"
  - "**/*_test.go"
  - "cmd/**/*"
---
```

## One Rule, One Concern

Give each rule file a single topic. Split a rule covering both Go error handling and Git commit messages into two files: `go-error-handling.md` and `git-commit-messages.md`.

Name files in kebab-case, descriptive of the concern: `api-naming-conventions.md`, `test-fixtures.md`, `database-migrations.md`.

## Scoping Decisions

Use `paths:` scoping when the content applies only when touching specific file types or directories. This is the default — most rules are conditional.

Use an unscoped rule (no `paths:` frontmatter) only when the content is relevant regardless of what files the agent is editing. This is rare and equivalent to CLAUDE.md loading behavior.

## Scope

`paths:` frontmatter in `~/.claude/rules/` is currently unreliable — global rules may load unconditionally regardless of `paths:` patterns. Place path-scoped rules at project level (`.claude/rules/`) where `paths:` works correctly. Use global rules only for genuinely unconditional constraints.

## Structure

Place the most critical constraints at the top of the rule file.

Keep rules concise. When a rule requires extensive detail, write a brief directive in the rule and reference a `.claude/docs/` file for the full guidance.
