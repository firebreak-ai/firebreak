# Task 010: Create referenced-docs.md Leaf

**Output file**: `.claude/docs/context-assets/referenced-docs.md`
**Dependencies**: 001 (must be consistent with index principles)

## Context

This leaf covers authoring guidance for `.claude/docs/` files — the content layer that indexes and leaves live in. It covers the progressive disclosure pattern as implemented through docs files. It loads when the agent is writing or modifying any docs file.

Read `ai-docs/mvp-000/plan.md` sections: "File descriptions > 5-10 > referenced-docs.md" and "Progressive Disclosure Pattern"

## Output Specification

Create `.claude/docs/context-assets/referenced-docs.md` covering:

### Critical constraints (first 3 lines)

The most important rules for docs file authoring.

### Main guidance

Cover these topics:

1. **The index + leaf pattern**
   - Index files (`.claude/docs/<topic>.md`) map tasks/conditions to leaf file paths — they route, they don't instruct in detail
   - Leaf files (`.claude/docs/<topic>/<subtopic>.md`) contain detailed, self-contained instructions for one concern
   - Use an index when a topic has multiple subtopics that the agent should load selectively
   - Use a standalone doc (no index) when a topic is self-contained and doesn't need routing

2. **When to create a docs file vs. inline content**
   - Extract to `.claude/docs/` when multiple triggers (rules, skills) need the same content
   - Keep content inline in the trigger when only one trigger uses it
   - `.claude/docs/` is a content convention, not an auto-loading mechanism — files load when the agent reads them in response to a routing instruction

3. **Naming conventions**
   - kebab-case, all lowercase with hyphens
   - Index: `.claude/docs/<topic>.md`
   - Leaves: `.claude/docs/<topic>/<subtopic>.md`
   - Names should describe the concern, not the audience (e.g., `error-handling.md` not `developer-guide.md`)

4. **Content strategy: rules vs. examples**
   - Use declarative rules for unambiguous constraints (naming conventions, required file structure, mandatory sections)
   - Use 2-3 concrete examples for style, format, and tone guidance that resists articulation as rules
   - Cap at 5 examples per document — over-prompting degrades performance
   - Examples are powerful for demonstrating desired output format; rules are better for binary constraints

5. **Routing instruction clarity**
   - Agents sometimes fail to load on-demand content — routing language must be prominent and use matchable terms
   - Write routing instructions with the same verbs and nouns the agent will encounter in the task
   - Place routing tables in high-attention positions (document top or bottom)

6. **Document structure**
   - Place the most critical constraints in the first 3 lines of any doc
   - Use section headers (`##`) when documents exceed ~20 lines — flat lists lose mid-document attention
   - Keep each doc self-contained — a reader should not need to load another doc to understand the current one

## Verification Criteria

- [ ] Critical constraints in first 3 lines
- [ ] Covers: index+leaf pattern, when to extract vs. inline, naming, rules vs. examples, routing clarity, document structure
- [ ] Content strategy includes the 2-3 examples / cap at 5 guidance
- [ ] Routing reliability concern is addressed
- [ ] Naming conventions match the plan (kebab-case)
- [ ] Positive framing, atomic constraints, no preamble
- [ ] No duplication of index principles (reference them, apply them, but state leaf-specific guidance only)
