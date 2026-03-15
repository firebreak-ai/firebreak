Use a 4-stage pipeline for complex features: Spec → Review → Breakdown → Implement. Require external feedback at every iteration — valid sources: human judgment, test results, lint passes, council agents with distinct perspectives. Self-refinement without external signals is counterproductive.

## Pipeline Principles

**Verification gates use two layers**: Structural prerequisites (deterministic, automated) and semantic evaluation (human/AI judgment). Report these as separate concerns. Structural pass means "ready for review," not "ready to advance."

**Every iteration requires external feedback**. Valid sources are human judgment, test results, lint passes, or council agents with distinct perspectives. Invalid: same agent re-reading its own output.

**Cap iterations per stage** based on the stage's nature:

| Stage | Iteration Cap | Notes |
|-------|---------------|-------|
| 1: Feature Spec | Human-driven, no hard cap | User drives iteration frequency |
| 2: Spec Review | 1 thorough review + 1 revision if blocking findings | Escalate if blocking findings persist |
| 3: Task Breakdown | 2 compilation attempts | Escalate if compilation fails twice |
| 4: Implementation | 2 re-plans per task, then escalate | Escalate to user if re-plan limit reached |

**Stage transitions are human-approved, agent-facilitated**. Agent runs the gate, reports results, offers the next stage. Write artifacts to disk, summarize the completed stage, compact context, then invoke the next skill.

**Mid-pipeline entry**: If the user invokes a stage directly, check the immediately prior stage's structural gate first. Report what failed and offer to run the prior stage to resolve it.

## Stage Guides

When co-authoring a feature specification → `/spec` skill loads `sdl-workflow/feature-spec-guide.md`

When performing a specification review → `/spec-review` skill loads `sdl-workflow/review-perspectives.md`

When creating a threat model during spec review → Load on demand: `sdl-workflow/threat-modeling.md`

When compiling a specification into tasks → `/breakdown` skill loads `sdl-workflow/task-compilation.md`

When implementing tasks from a breakdown → `/implement` skill loads `sdl-workflow/implementation-guide.md`

## Stage Transitions

At the end of each stage, follow this protocol: Write all artifacts to disk. Summarize the completed stage (one paragraph: what was delivered, what's ready for the next stage). Compact context by reading from the written artifacts instead of regenerating state. Invoke the next skill with the feature name to initialize the next stage. For mid-pipeline entry, validate the prior stage's structural gate before proceeding.

## Artifact Layout

**Feature-level directory**: `ai-docs/<feature-name>/` contains the spec, review, optional threat model, and tasks subdirectory. Add `*threat-model*` to `.gitignore`.

**Project-level directory**: `ai-docs/<project-name>/` contains a project overview, then feature subdirectories, each following the feature-level structure.
