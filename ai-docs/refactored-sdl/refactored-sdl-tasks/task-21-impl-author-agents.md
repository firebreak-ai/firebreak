---
id: task-21
type: implementation
wave: 1
covers: [AC-15]
files_to_create:
  - assets/agents/fbk-product-author.md
  - assets/agents/fbk-architect.md
test_tasks: [task-03]
dependencies: []
completion_gate: "the referenced test tasks pass"
---

## 1. Objective

Produces the two new authoring-persona agents — `fbk-product-author` (requirements/product author for the intent phase) and `fbk-architect` (senior architect for the design phase, author-only this cycle) — each carrying tools Read, Grep, Glob with no Write or Edit.

## 2. Context

The intent and design phases delegate artifact authoring to dedicated persona agents while the phase skills own the file writes (matching the existing `fbk-spec-author` pattern, where the agent returns prose and the skill writes the file).

- `fbk-product-author` — a requirements/product author persona: plain-language, capability-framed, interview-grounded. It returns PRD prose; the `fbk-intent` skill owns the artifact write. Tools: `Read, Grep, Glob` (no Write — the skill owns writes). Model: sonnet.
- `fbk-architect` — a senior architect persona for the `fbk-design` authoring mode. Scope **this cycle: author designs in isolation only**. The future "superset the council architect collapses into" framing is dropped from the build requirement (recorded in the decisions log by task-15) — do not encode it here. Tools: `Read, Grep, Glob`. Model: sonnet.

Both agents are observe/author-only personas that carry **no Write or Edit tool** so they cannot auto-fix or write files directly (AC-15 covers the observe/scan agents; these author agents follow the same no-Write convention so the skill stays the sole writer).

Asset-type rules: an agent owns persona only; workflow comes from the phase skill or spawn prompt at composition time. Do not embed workflow steps in the agent body. Follow the existing agent frontmatter and body shape in `assets/agents/fbk-spec-author.md` (frontmatter `name`/`description`/`tools`/`model`; body is persona + output quality bars + anti-defaults). Use plain language and capability framing.

The paired test (`tests/sdl-workflow/test-technique-skills.sh`) does not directly assert on these two agents by name (it checks the fresh-eyes/detector/test-reviewer agents). The installer e2e test (task-13, wave 4) asserts these two files install (T10 fbk-architect, T9 fbk-product-author). The AC-15 no-Write/no-Edit property for these agents is a structural criterion verified by reading the frontmatter. Author them so the tools line carries exactly Read, Grep, Glob.

## 3. Instructions

1. Read `assets/agents/fbk-spec-author.md` for the persona-agent shape (frontmatter + output quality bars + anti-defaults; no embedded workflow).

2. Create `assets/agents/fbk-product-author.md` with frontmatter:
   - `name:` `fbk-product-author`
   - `description:` a capability-framed one-liner: a product/requirements author that turns interview notes and the architecture overview into a plain-language PRD; surfaces ambiguity rather than guessing.
   - `tools: Read, Grep, Glob`
   - `model: sonnet`
   Body: persona (requirements/product author), output quality bars (plain language, capability-framed, interview-grounded, no identifier-jargon), and an anti-default note that the model's default is compliant drafting — activate the interview-before-drafting discipline. Completion: `grep '^tools:' assets/agents/fbk-product-author.md` shows `Read, Grep, Glob` with no Write/Edit.

3. Create `assets/agents/fbk-architect.md` with frontmatter:
   - `name:` `fbk-architect`
   - `description:` a capability-framed one-liner: a senior architect that proposes a module shape, contracts, and a decomposition rationale for the design phase; author-only.
   - `tools: Read, Grep, Glob`
   - `model: sonnet`
   Body: persona (senior architect), output quality bars (specific contracts, named integration seams, decomposition rationale, one decision surfaced at a time with a recommendation), and a one-line scope note that this agent authors designs in isolation this cycle. Do not reference a future council collapse. Completion: `grep '^tools:' assets/agents/fbk-architect.md` shows `Read, Grep, Glob` with no Write/Edit.

4. Confirm neither agent file contains a `Write` or `Edit` tool: `grep '^tools:' assets/agents/fbk-product-author.md assets/agents/fbk-architect.md | grep -c -E 'Write|Edit'` returns 0.

5. Run the technique-skills test to confirm no regression: `bash tests/sdl-workflow/test-technique-skills.sh`.

## 4. Files to create/modify

- `assets/agents/fbk-product-author.md` (create)
- `assets/agents/fbk-architect.md` (create)

File-scope justification: two files, both new author-persona agents in the same `technique-skills-and-agents` slice, each a single-file bounded persona definition. They are paired here because they share the identical no-Write authoring convention and the AC-15 structural criterion; authoring them together keeps that convention consistent.

## 5. Test requirements

This task makes no new test assertions go from red to green directly in task-03 (which checks other agents), but it is the implementation half for the AC-15 structural criterion on the two author agents and supplies the files the wave-4 installer test (task-13) asserts. No new tests are written here. Do not edit any test file.

## 6. Acceptance criteria

- AC-15: both author agents declare tools Read, Grep, Glob and no Write or Edit, so they cannot auto-fix or write files directly.
- Structural criterion: both files carry valid agent frontmatter (`name`, `description`, `tools`, `model`) and persona-only bodies (no embedded workflow).
- Primary criterion: the task-03 technique-skills test stays green; the files exist for the wave-4 installer assertions.

## 7. Model

Sonnet

## 8. Wave

Wave 1
