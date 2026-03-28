Every skill directory name becomes its slash command name — choose a clear, action-oriented kebab-case name.
Write the `description` field for the agent that will match it, not for a human reading the repo.
Restrict tool access with `allowed-tools` to the minimum the skill requires.

## YAML Frontmatter

Place optional YAML frontmatter between `---` markers at the top of `SKILL.md`.

| Field | Effect |
|-------|--------|
| `name` | Display name. Defaults to directory name. Lowercase letters, numbers, hyphens only (max 64 characters). |
| `description` | What the skill does and when to use it. Claude matches this text to decide when to load the skill. Defaults to the first paragraph of markdown content if omitted. |
| `user-invocable` | Set to `false` to hide from the `/` menu. Default: `true`. |
| `disable-model-invocation` | Set to `true` to prevent Claude from loading the skill automatically. Default: `false`. |
| `allowed-tools` | Comma-separated list of tools Claude can use when the skill is active (e.g., `Read, Grep, Glob`). |
| `argument-hint` | Hint shown during autocomplete (e.g., `[issue-number]`). |
| `context` | Set to `fork` to run in a forked subagent context. |
| `agent` | Subagent type when `context: fork` is set (e.g., `Explore`, `Plan`, `general-purpose`, or a custom agent name). |
| `model` | Override model selection when the skill is active. |
| `hooks` | Hooks scoped to this skill's lifecycle. |

## User-Invocable Skills (Slash Commands)

Use `user-invocable: true` (the default) for actions the user triggers by name: `/deploy`, `/review-pr`, `/fix-issue`.

Add `disable-model-invocation: true` when the skill has side effects or the user should control timing. This removes the skill description from Claude's context entirely.

Keep the `description` short — one sentence stating what the skill does. Users see this during autocomplete.

Use `$ARGUMENTS` in the skill body for user-provided input. Access positional arguments with `$ARGUMENTS[0]` or shorthand `$0`.

## Non-User-Invocable Skills (Description-Matched)

Use `user-invocable: false` for background knowledge that loads automatically when relevant. The user never invokes these directly — Claude matches the `description` to the current conversation and loads the skill when it fits.

### Writing descriptions for reliable discovery

The `description` field is the only signal Claude uses to decide whether to load a non-user-invocable skill.

Use specific scenario keywords the agent will encounter in real conversations. Write "Use when modifying database migration files or adding new model fields" — not "Database utilities."

Use concrete task triggers in descriptions ("Use when writing Terraform modules, configuring CI pipelines, or modifying Dockerfiles") rather than abstract category names ("Handles infrastructure concerns").

Scope descriptions narrowly to the skill's actual use cases.

Ensure the description resolves to a single string value. Use a YAML block scalar (`>-`) for long descriptions that need to wrap in the source file. Avoid plain multi-line strings — formatters can split them in ways that break skill discovery.

## Content Strategy

Keep `SKILL.md` under 500 lines. Move detailed reference material to supporting files in the skill directory and reference them from `SKILL.md`.

Use `!`command`` syntax for dynamic context injection — shell commands run before the skill content reaches Claude, and their output replaces the placeholder.

## Scope

Global skills (`~/.claude/skills/`) are available in all projects for that user. A skill that is only relevant to one project belongs at project level (`.claude/skills/`). Apply the Necessity Test more strictly at global scope.

## Security

Set `allowed-tools` to the narrowest set the skill requires. A read-only skill should specify `allowed-tools: Read, Grep, Glob`.

Skills that define `allowed-tools` grant those tools without per-use approval when active. Verify that every tool in the list is necessary for the skill's function.

Preserve the agent's built-in safety checks in skill bodies. Replace phrases like "skip confirmation" or "run without review" with explicit confirmation steps.
