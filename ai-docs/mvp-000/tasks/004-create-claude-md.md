# Task 004: Create CLAUDE.md Project Router

**Output file**: `CLAUDE.md` (project root)
**Dependencies**: 001 (index must exist to reference it)

## Context

This is the project's own CLAUDE.md — it demonstrates the router pattern it teaches. It loads every session and routes to the context-assets index.

Read `ai-docs/mvp-000/plan.md` section: "File descriptions > Content > 3."

## Output Specification

Create `CLAUDE.md` at the project root with:

### Content

A terse router that:
1. References `.claude/docs/context-assets.md` for context asset authoring guidance
2. Demonstrates the minimal router pattern (this file IS a context asset — it should practice what it preaches)

**Specific requirements:**
- Start with the routing reference. No project description, no "welcome to..." preamble.
- Keep the entire file under 10 lines. A CLAUDE.md that teaches minimalism must itself be minimal.
- This project's CLAUDE.md appropriately references authoring guidance because the project IS about context assets. Include a note that for other projects, this reference would only be relevant if the project maintains context assets.

### Scope boundaries

Include only the routing reference and essential session-level context. Leave these to other files:
- Project structure discovery (the agent uses `ls` and `glob`)
- Technology stack information
- Build/run commands
- Detailed authoring instructions (those live in the index and leaves)

## Verification Criteria

- [ ] File is under 10 lines
- [ ] First line is substantive (not a title or preamble)
- [ ] References `.claude/docs/context-assets.md` by exact path
- [ ] Contains no content that belongs in the index or leaves
- [ ] Follows its own principles (no description, no motivational framing, routing only)
