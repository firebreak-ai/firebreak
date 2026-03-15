# Task 01: Create SDL Workflow Index Doc

## Objective

Create the routing index document that maps pipeline stages to their detailed leaf docs.

## Context

The SDL workflow uses the progressive disclosure pattern: an index routes the agent to the correct leaf based on which pipeline stage is active. The index also carries cross-stage principles too important to defer to leaves.

The pipeline has 4 stages, each with a dedicated leaf doc:

| Stage | Skill | Leaf doc |
|-------|-------|----------|
| 1: Feature Spec | `/spec` | `sdl-workflow/feature-spec-guide.md` |
| 2: Spec Review | `/spec-review` | `sdl-workflow/review-perspectives.md` |
| 3: Task Breakdown | `/breakdown` | `sdl-workflow/task-compilation.md` |
| 4: Implementation | `/implement` | `sdl-workflow/implementation-guide.md` |

An additional leaf, `sdl-workflow/threat-modeling.md`, loads on-demand during Stage 2 when the user chooses to create a threat model.

Cross-stage principles to include in the index (these apply at every stage boundary):

1. **Verification gate model**: Two layers — structural prerequisites (deterministic, automated) then semantic evaluation (human/AI judgment). Structural pass means "ready for review," not "ready to advance." Report the two layers as separate concerns — do not anchor semantic judgment to structural results.
2. **External feedback rule**: Every iteration loop requires an external signal (human judgment, test results, council perspective, deterministic gate). Self-refinement without external feedback is counterproductive. Valid: human, tests, lint, council agent with distinct perspective. Invalid: same agent re-reading its own output.
3. **Iteration caps**: Stage 1 = human-driven (no hard cap); Stage 2 = 1 thorough review + 1 revision if blocking findings; Stage 3 = 2 compilation attempts; Stage 4 = 2 re-plans per task then escalate.
4. **Stage transitions**: Human-approved, agent-facilitated. Agent runs gate, reports results, offers next stage. Compaction between stages — write artifacts to disk, summarize completed stage, compact, then invoke next skill.
5. **Mid-pipeline entry**: If user invokes a stage directly, check the immediately prior stage's structural gate. Report what failed and offer to run the prior stage to resolve it.

Artifact structure for reference (the index should mention but not elaborate):
- Feature-level: `ai-docs/<feature-name>/` with spec, review, threat model, tasks subdirectory
- Project-level: `ai-docs/<project-name>/` with overview + feature subdirectories

## Instructions

1. Create `home/.claude/docs/sdl-workflow/` directory if it doesn't exist.
2. Create `home/.claude/docs/sdl-workflow.md` with this structure:

**Opening (first 3 lines)**: State the pipeline model (4-stage: Spec → Review → Breakdown → Implement) and the external feedback rule. These are the highest-attention lines.

**`## Pipeline Principles`**: Write the 5 cross-stage principles listed in Context as direct imperatives. Each principle: 2-4 lines. Enough to prevent mistakes without duplicating leaf docs. Include iteration caps as a compact table.

**`## Stage Guides`**: A condition-to-path routing table. Use "When..." conditions that match how the agent frames its work (e.g., "When co-authoring a feature specification" → `sdl-workflow/feature-spec-guide.md`). Include the conditional threat-modeling entry: "When creating a threat model during spec review" → `sdl-workflow/threat-modeling.md`.

**`## Stage Transitions`**: Brief protocol — the compaction-and-invoke pattern. 4-5 lines: write artifacts to disk, summarize stage, compact, invoke next skill with feature name. Mention mid-pipeline entry: check prior stage's gate first.

**`## Artifact Layout`**: Two bullet points showing feature-level and project-level directory patterns under `ai-docs/`. Include the `.gitignore` rule for threat models: `*threat-model*`.

3. Target length: 50-80 lines. This routes; the leaves instruct.
4. Read `home/.claude/docs/context-assets.md` for authoring principles. Follow them.

## Files to Create/Modify

- **Create**: `home/.claude/docs/sdl-workflow.md`

## Acceptance Criteria

- AC-01: Routes to correct leaf for each of 4 stages plus conditional threat-modeling doc
- AC-15: Follows authoring principles — starts with first instruction, imperatives, no preamble

## Model

Haiku

## Wave

1
