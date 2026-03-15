# Task 007: Create skills.md Leaf

**Output file**: `.claude/docs/context-assets/skills.md`
**Dependencies**: 001 (must be consistent with index principles)

## Context

This leaf covers authoring guidance for Claude Code skills (`.claude/skills/<name>/SKILL.md`). It loads when the agent is writing or modifying a skill.

Read `ai-docs/mvp-000/plan.md` section: "File descriptions > 5-10 > skills.md"

## Output Specification

Create `.claude/docs/context-assets/skills.md` covering:

### Critical constraints (first 3 lines)

The most important rules for skill authoring.

### Main guidance

Research current Claude Code skill documentation to confirm accurate technical details before writing. Cover these topics:

1. **YAML frontmatter options**
   - `user-invocable`: true (slash command) vs. false (description-matched)
   - `description`: purpose and how it affects matching
   - `allowed-tools`: restricting the skill's tool access
   - Any other supported frontmatter fields — confirm against current documentation

2. **User-invocable skills (slash commands)**
   - When to use: user-initiated workflows, specific commands the user will invoke by name
   - Description writing: short, clear statement of what the skill does
   - Naming: the directory name becomes the slash command name

3. **Non-user-invocable skills (description-matched)**
   - When to use: reference knowledge loaded automatically on relevance, background guidance for specific scenarios
   - Description writing for reliable discovery: agents sometimes fail to invoke available skills, so descriptions must use clear, concrete, matchable language
   - Use specific scenario keywords the agent will encounter, not abstract categories
   - A vague description that matches too broadly consumes budget unnecessarily

4. **Content strategy**
   - Inline content when the skill is the sole consumer (Separation of Concerns principle)
   - Reference `.claude/docs/` files when multiple triggers need the same content
   - Keep skill body focused — a skill that requires extensive reference material should route to docs rather than inlining everything

5. **Security**
   - Use `allowed-tools` to restrict capability surface to what the skill actually needs
   - A skill that only needs to read files should not have write or bash access
   - Least-privilege principle: start restrictive, expand only when necessary

## Verification Criteria

- [ ] Critical constraints in first 3 lines
- [ ] Covers: frontmatter options, user-invocable vs. non-invocable, description writing, content strategy, security
- [ ] Frontmatter schema is accurate per current Claude Code documentation
- [ ] Includes specific guidance on description writing for discovery reliability
- [ ] Security section covers `allowed-tools` with least-privilege guidance
- [ ] Positive framing, atomic constraints, no preamble
- [ ] No duplication of index principles (reference them, apply them, but state leaf-specific guidance only)
