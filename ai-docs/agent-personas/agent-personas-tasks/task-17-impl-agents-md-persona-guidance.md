---
id: task-17
type: implementation
wave: 1
covers: [AC-01]
files_to_modify:
  - assets/fbk-docs/fbk-context-assets/agents.md
test_tasks: [task-05]
completion_gate: "task-05 tests pass"
---

## Objective

Add a new top-level `## Persona authoring` section to `assets/fbk-docs/fbk-context-assets/agents.md` that covers the seven required subsections: enterprise activation baseline, correctness-vs-maintainability rationale, persona structure (role activation, output quality bars, anti-defaults), personas and spawn prompts precedence, reference implementations (Detector and Challenger), what not to include, and when personas are unnecessary.

## Context

`agents.md` is the authoring guidance document for Firebreak agents. It currently has top-level sections `## Agent Definition Structure`, `## When to Use an Agent vs. Alternatives`, `## Capability Scoping`, `## Instruction Design`, `## Scope`, and `## Security`. This task adds one new top-level section covering how to write effective persona content. The section applies to all Firebreak agents and is the primary documentation deliverable for the agent-personas spec.

The paired test `tests/sdl-workflow/test-agents-md-persona-guidance.sh` verifies the new section exists and that each required subsection is present by grepping for content-anchor phrases:

- `enterprise` AND `activation` (anchor phrase "enterprise activation")
- `maintainability` AND `correctness`
- `role activation`
- `output quality bars`
- `anti-default` (or `anti-defaults`)
- `spawn prompt`
- `Detector` AND `Challenger` (case-sensitive, proper nouns)
- `what not to include` OR `not to include`
- `unnecessary`
- `mechanical`

The correctness-vs-maintainability rationale should be 1-2 sentences and point readers to the spec for the full argument (per the spec's section 4.1 note: "include the conclusion, not the research argument. The detailed rationale with citations lives in the agent-personas spec"). Do not include academic citations inline.

The new section must be placed so the `^## .*[Pp]ersona` grep (any top-level heading with "Persona" in the text) matches. Place it after `## Instruction Design` and before `## Scope` so it reads in context with the other authoring guidance.

## Instructions

1. Read the current file at `assets/fbk-docs/fbk-context-assets/agents.md`.
2. Locate the line `## Scope` (line 101 in the current file).
3. Insert a new section immediately above `## Scope`, and below the `## Instruction Design` section and its example (i.e., after the closing ``` of the "Report findings only. Leave source and test files unmodified." example block). The new section content is (verbatim):

   ```
   ## Persona authoring

   An agent's persona shapes which training distribution the model draws from when producing output. Without persona activation, agents default to the demo/tutorial distribution that dominates training data. A persona that grounds the agent in an enterprise professional role activates a smaller but higher-quality distribution — one characteristic of production codebases, professional engineering documentation, and senior-engineer code review.

   ### Enterprise activation as the baseline

   Every agent persona grounds the agent in a professional role within an enterprise software development organization. This is the single highest-leverage persona instruction — it shifts the output distribution from demo-grade to production-grade along quality dimensions the pipeline cannot gate deterministically: maintainability, code structure, naming clarity, appropriate abstraction levels, and professional standards. The role activation line names the seniority level, the domain, and the enterprise context. Domain specialization (architecture, security, testing, implementation) layers on top of this baseline.

   ### Correctness vs. maintainability

   Persona activation improves maintainability (reduced code smells, cyclomatic and cognitive complexity) while correctness is neutral to slightly reduced. This is the intended tradeoff for Firebreak: the pipeline's deterministic gates (spec gates, test-first development, per-wave verification, mutation testing) engineer correctness. Personas cover the gap those gates cannot reach. The detailed research rationale is documented in `ai-docs/agent-personas/agent-personas-spec.md`.

   ### Structure of an effective persona

   An effective persona has three components:

   1. **Role activation** (1-2 sentences): Ground the agent in a senior professional role within an enterprise engineering organization. Name the expertise level and domain. This is the single most impactful line — it determines which training distribution the model draws from. Example: "You are a staff engineer at an enterprise software company who writes maintainable, production code that other engineers can pick up and work with."
   2. **Output quality bars** (3-6 items): State what the output must demonstrate, not how to produce it. Each bar is a falsifiable constraint — the output either meets it or does not.
   3. **Anti-defaults** (1-3 items, optional): Name the specific default behavior the persona counteracts. Include only when the default is both likely and harmful.

   ### Personas and spawn prompts

   The persona defines what quality the output demonstrates. The spawn prompt defines what the task is and what format to use. Quality bars and anti-defaults belong in the persona; task details, output format, and workflow steps belong in the spawn prompt. When both address the same concern, the persona's quality bar takes precedence.

   ### Reference implementations

   The Detector (`assets/agents/fbk-code-review-detector.md`) and Challenger (`assets/agents/fbk-code-review-challenger.md`) are the canonical examples of the activation-focused pattern. The Challenger is especially concise — role activation line, two quality outcomes, no section headings — demonstrating the minimal effective persona.

   ### What not to include

   Do not include:

   - Expertise lists (the model already has the knowledge; the role activation line selects the distribution)
   - Communication style guidance (quality bars constrain output better than style descriptions)
   - Personality descriptions (narrative, not activation)
   - Generic professional advice (true of all professional communication; adds no activation signal)

   ### When a persona is unnecessary

   A persona adds value when the model's default distribution produces noticeably lower quality than the activated distribution. For purely mechanical tasks (sighting deduplication, format validation, file enumeration), a persona is unnecessary — the task instructions are sufficient.

   ```

4. Preserve the existing `## Scope` section and all content below it byte-for-byte.
5. Run `bash tests/sdl-workflow/test-agents-md-persona-guidance.sh`. All 12 assertions must pass.

## Files to create/modify

- **Modify**: `assets/fbk-docs/fbk-context-assets/agents.md` — insert the new `## Persona authoring` section between `## Instruction Design` and `## Scope`. All other sections preserved.

## Test requirements

No new tests. The paired test task `task-05-test-agents-md-persona-guidance.md` covers the 12 subsection anchor-phrase assertions.

## Acceptance criteria

- `tests/sdl-workflow/test-agents-md-persona-guidance.sh` — all 12 assertions pass
- Covers AC-01 (persona authoring guidance in `agents.md`)
- Existing top-level sections and their content preserved byte-for-byte

## Model

Sonnet

## Wave

1
