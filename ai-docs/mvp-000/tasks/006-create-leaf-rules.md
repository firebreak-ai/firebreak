# Task 006: Create rules.md Leaf

**Output file**: `.claude/docs/context-assets/rules.md`
**Dependencies**: 001 (must be consistent with index principles)

## Context

This leaf covers authoring guidance for Claude Code rules (`.claude/rules/*.md`). It loads when the agent is writing or modifying a rule file.

Read `ai-docs/mvp-000/plan.md` section: "File descriptions > 5-10 > rules.md"

## Output Specification

Create `.claude/docs/context-assets/rules.md` covering:

### Critical constraints (first 3 lines)

The most important rules for rule authoring — the mistakes that cause the most damage.

### Main guidance

Cover these topics:

1. **paths: frontmatter — when and how to scope**
   - Research current Claude Code documentation to confirm the exact YAML frontmatter syntax for `paths:` in rules
   - Rules without `paths:` scoping load every session, just like CLAUDE.md — use scoping when content is conditional
   - Provide 2-3 example path patterns (e.g., `**/*.go`, `.claude/docs/**/*.md`)
   - Glob pattern syntax: confirm what patterns are supported

2. **One rule, one concern**
   - Each rule file covers one topic. A rule covering both "Go error handling" and "Git commit messages" should be two files.
   - File naming: kebab-case, descriptive of the concern (e.g., `go-error-handling.md`, `api-naming-conventions.md`)

3. **Scoping decisions**
   - When to use `paths:` scoping: content is relevant only when touching specific file types
   - When to use an unscoped rule: content applies every session regardless of files being edited (rare — this is essentially CLAUDE.md-equivalent loading)
   - Over-triggering is the same problem as putting everything in CLAUDE.md

4. **Structural advice**
   - Place the most critical constraints at the top of the rule file (Lost in the Middle — mid-document instructions get less attention)
   - Keep rules concise — a rule that requires extensive detail should reference a `.claude/docs/` file instead

### Writing style

All content must follow index principles. Use the rule trigger file created in task 002 as a concrete example of a well-structured rule (reference it by path if helpful).

## Verification Criteria

- [ ] Critical constraints in first 3 lines
- [ ] Covers: paths frontmatter syntax, one-concern rule, scoping decisions, structural advice
- [ ] Includes 2-3 example path patterns
- [ ] Technical details (YAML syntax, glob patterns) are accurate per current Claude Code documentation
- [ ] Positive framing, atomic constraints, no preamble
- [ ] No duplication of index principles
