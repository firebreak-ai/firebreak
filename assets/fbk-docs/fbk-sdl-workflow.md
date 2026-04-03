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
| 4: Implementation | 2 task escalations per task, then escalate to user | Escalate to user if escalation limit reached. After the final wave, run the full test suite before offering any commit. |

A **task escalation** is a task rewrite assigned to a different teammate after in-session resolution fails. **In-session retries** — TaskCompleted hook rejections resolved by the teammate without escalation — are not task escalations. Track both metrics separately in the retrospective.

**Stage transitions are human-approved, agent-facilitated**. Agent runs the gate, reports results, offers the next stage. Write artifacts to disk, summarize the completed stage, compact context, then invoke the next skill.

**Mid-pipeline entry**: If the user invokes a stage directly, check the immediately prior stage's structural gate first. Report what failed and offer to run the prior stage to resolve it.

## Stage Guides

When co-authoring a feature specification → `/spec` skill loads `fbk-sdl-workflow/feature-spec-guide.md`

When performing a specification review → `/spec-review` skill loads `fbk-sdl-workflow/review-perspectives.md`

When creating a threat model during spec review → Load on demand: `fbk-sdl-workflow/threat-modeling.md`

When creating or modifying `.claude/automation/config.yml` → `fbk-sdl-workflow/config-yml-schema.md`

When creating or modifying `.claude/automation/verify.yml` → `fbk-sdl-workflow/verify-yml-schema.md`

When compiling a specification into tasks → `/breakdown` skill loads `fbk-sdl-workflow/task-compilation.md`

When implementing tasks from a breakdown → `/implement` skill loads `fbk-sdl-workflow/implementation-guide.md`

When reviewing code or running post-implementation review → `/code-review` skill loads `fbk-sdl-workflow/code-review-guide.md`

When following a corrective or diagnostic workflow → `fbk-sdl-workflow/corrective-workflow.md`

When analyzing retrospectives for pipeline improvement → `/fbk-improve` skill spawns the improvement analyst agent

When writing or updating a feature retrospective → `fbk-sdl-workflow/retrospective-guide.md`

## Stage Transitions

At the end of each stage, follow this protocol: Write all artifacts to disk. Summarize the completed stage (one paragraph: what was delivered, what's ready for the next stage). Compact context by reading from the written artifacts instead of regenerating state. Invoke the next skill with the feature name to initialize the next stage. For mid-pipeline entry, validate the prior stage's structural gate before proceeding.

## Artifact Layout

**Feature-level directory**: `ai-docs/<feature-name>/` contains the spec, review, optional threat model, and tasks subdirectory. Add `*threat-model*` to `.gitignore` before writing the threat model file.

**Project-level directory**: `ai-docs/<project-name>/` contains a project overview, then feature subdirectories, each following the feature-level structure.
