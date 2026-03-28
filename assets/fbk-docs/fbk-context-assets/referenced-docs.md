Every docs file must be self-contained — a reader understands it without loading another file.
Place the most critical constraints in the first 3 lines of every doc.
`.claude/docs/` is a content convention, not an auto-loading mechanism — files load when the agent reads them in response to a routing instruction.

## Index + Leaf Pattern

Use an **index** (`.claude/docs/<topic>.md`) when a topic has multiple subtopics the agent should load selectively. The index maps tasks or conditions to leaf file paths — it routes, it does not instruct in detail.

Use a **leaf** (`.claude/docs/<topic>/<subtopic>.md`) for detailed, self-contained instructions on one concern.

Use a **standalone doc** (no index, no subdirectory) when a topic is self-contained and does not need routing.

## When to Extract vs. Inline

Extract content to `.claude/docs/` when multiple triggers (rules, skills, CLAUDE.md) need the same instructions.

Keep content inline in the trigger when only one trigger uses it.

## Naming Conventions

Use kebab-case: all lowercase, words separated by hyphens.

- Index: `.claude/docs/<topic>.md`
- Leaf: `.claude/docs/<topic>/<subtopic>.md`

Name files by the concern they cover, not the audience. Use `error-handling.md`, not `developer-guide.md`.

## Content Strategy: Rules vs. Examples

Use declarative rules for unambiguous constraints — naming conventions, required file structure, mandatory sections.

Use 2-3 concrete examples for style, format, and tone guidance that resists articulation as rules. Examples are effective for demonstrating desired output format; rules are better for binary constraints.

Cap examples at 5 per document. Beyond that, additional examples degrade rather than improve compliance.

## Routing Instruction Clarity

Agents sometimes fail to load on-demand content. Write routing instructions to maximize discovery:

- Use the same verbs and nouns the agent will encounter in the task. Match routing language to how the agent frames the work.
- Place routing tables at the top or bottom of documents — these are the highest-attention positions.
- Make routing entries scannable. Use a table or bulleted list with clear condition-to-path mappings.

## Document Structure

Use section headers (`##`) when a document exceeds roughly 20 lines. Flat lists lose mid-document attention.

Place critical constraints at the document top — first 3 lines get the highest recall.

Keep each doc to one concern. If a document covers two unrelated topics, split it into two files.
