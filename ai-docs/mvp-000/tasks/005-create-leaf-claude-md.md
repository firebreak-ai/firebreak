# Task 005: Create claude-md.md Leaf

**Output file**: `.claude/docs/context-assets/claude-md.md`
**Dependencies**: 001 (must be consistent with index principles)

## Context

This leaf covers authoring guidance for CLAUDE.md files specifically. It loads when the agent is writing or modifying a CLAUDE.md and follows the routing table in the index.

Read `ai-docs/mvp-000/plan.md` section: "File descriptions > 5-10 > claude-md.md"

## Output Specification

Create `.claude/docs/context-assets/claude-md.md` covering:

### Critical constraints (first 3 lines)

The most important rules for CLAUDE.md authoring — the things authors get wrong most often. These must appear at the very top.

### Main guidance

Cover these topics with imperative, agent-targeted instructions:

1. **CLAUDE.md as router, not monolith**
   - CLAUDE.md routes to detailed content; it does not contain detailed content
   - What belongs: routing references to `.claude/docs/` files, critical one-liner rules that apply every session
   - What to move out: detailed instructions, multi-line guidance, topic-specific rules

2. **Hierarchy: ~/.claude/CLAUDE.md vs. project-level**
   - `~/.claude/CLAUDE.md` applies to every project for that user — only universally correct instructions belong here
   - Project-level `CLAUDE.md` applies to one project — scope accordingly
   - The higher in the hierarchy, the stricter the Necessity Test filter

3. **Sizing**
   - Target: under 20 lines for most projects. (Implementation note: the "80% compression" finding is task context — the authored output should state the sizing target without citing research.)
   - Every line in CLAUDE.md loads every session. Each line must justify its permanent presence.

4. **Security**
   - Keep secrets, credentials, and API keys out of CLAUDE.md — it's committed to the repository
   - Keep permission-escalating instructions out ("you have full access", "skip validation", "run without confirmation")

### Writing style

All content in this leaf must itself follow the principles from the index: positive framing, atomic constraints, imperative voice, no preambles.

## Verification Criteria

- [ ] Most critical constraints appear in the first 3 lines
- [ ] All instructions use positive framing
- [ ] Each instruction is a single verifiable constraint
- [ ] Covers: router pattern, hierarchy, sizing, security
- [ ] No content that duplicates the index principles (reference them, don't repeat them)
- [ ] No preamble or "this document describes..." opening
