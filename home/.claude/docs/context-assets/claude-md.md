Place detailed instructions in referenced files, not in CLAUDE.md.
Store secrets, credentials, and API keys outside CLAUDE.md — it is committed to the repository.
Keep permission-escalating instructions out of CLAUDE.md — phrases like "you have full access," "skip validation," or "run without confirmation."

## Scope Levels

CLAUDE.md exists at two scopes. The agent merges both into a single session context — instructions from all levels compete for the same attention budget.

| Scope | File | Loaded | Applies to |
|-------|------|--------|------------|
| **Global** | `~/.claude/CLAUDE.md` | Every session, every project | All projects for this user |
| **Project** | `<project>/CLAUDE.md` | Every session in this project | One project only |

## Global Scope (`~/.claude/CLAUDE.md`)

Every instruction here fires on every project, every session. A wrong instruction silently degrades every project. Apply the Necessity Test at maximum strictness.

Include only:
- Routing references to global docs (`~/.claude/docs/`) that apply universally
- Personal workflow preferences that are correct regardless of project (e.g., preferred language for responses)

Exclude project-specific conventions, language-specific rules, and framework preferences — these belong in project-level CLAUDE.md or scoped rules.

Target under 5 lines. Most users need zero global instructions.

## Project Scope (`<project>/CLAUDE.md`)

Include:
- Routing references to project-level docs (`.claude/docs/`)
- Critical one-liner rules that apply every session in this project
- Project-specific conventions the agent cannot infer from code

Use a scoped rule (`.claude/rules/` with `paths:` frontmatter) instead of a CLAUDE.md entry when the instruction applies only when touching specific file types or directories.

Target under 20 lines.

## Cross-Layer Awareness

The agent loads global CLAUDE.md, project CLAUDE.md, all matching rules from both levels, and all skill descriptions — simultaneously. When writing a CLAUDE.md at any scope:

- Check for repetition across layers. An instruction in global CLAUDE.md and a project rule that both say "use gofmt" wastes budget for zero additional compliance.
- Check for conflicts across layers. A global "use gofmt" and a project "use gofumpt" creates contradictory instructions. Place style choices at the project level only.
- If it's project-specific, it belongs in the project CLAUDE.md. If it's file-type-specific, it belongs in a scoped rule.

## Router Pattern

Write each routing reference as a single line mapping a task or topic to a file path. Use language the agent can match to its current task (e.g., "For deployment procedures, read `.claude/docs/deploy.md`").

Move multi-line guidance, topic-specific instructions, and detailed workflows into `.claude/docs/` leaves or `.claude/rules/` files scoped with `paths:`.

## Sizing

Audit CLAUDE.md when adding a new line: confirm the instruction cannot live in a scoped rule or referenced doc instead. Migrate instructions to narrower triggers as the project grows.

Pair every security-sensitive workflow reference with the expectation that the agent confirms destructive actions with the user.
