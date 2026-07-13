Use the gated pipeline for complex features: Intent → Design → Spec → Spec Review → Breakdown → Implement → Code Review. Intent and design precede spec — intent captures what and why, design resolves how before any spec is authored. Require external feedback at every iteration — valid sources: human judgment, test results, lint passes, council agents with distinct perspectives, or a cross-model review. Self-refinement without external signals is counterproductive.

## Pipeline Principles

**Verification gates use two layers**: Structural prerequisites (deterministic, automated) and semantic evaluation (human/AI judgment). Report these as separate concerns. Structural pass means "ready for review," not "ready to advance."

**Every iteration requires external feedback**. Valid sources are human judgment, test results, lint passes, council agents with distinct perspectives, or a cross-model review from a different model family. Invalid: same agent re-reading its own output.

**A revision earns a fresh review round.** When a stage's artifact is revised in response to review findings, run a new review pass against the revised artifact before treating the stage as closed — a fix pass can introduce defects of its own. Convergence is reached when a round returns no findings at or above the stage's severity threshold, or when finding severity is clearly falling while the reviewers' rejection rate is clearly rising round over round — with every confirmed finding from the final round still resolved before the stage closes. Escalate to the user if convergence is not reached within the review loop's round cap.

**Prefer cross-model review as the fresh-round instrument.** Where a project has cross-model review enabled, use it — not a same-model-family council or fresh-eyes pass — as the fresh review pass required by "a revision earns a fresh review round": a fix pass is itself a defect source, and cross-model review has repeatedly caught fix-introduced defects that same-family reviews miss. A scoped round covering only the fix set is the standard shape for this pass.

**Cap iterations per stage** based on the stage's nature:

| Stage | Iteration Cap | Notes |
|-------|---------------|-------|
| 1: Intent | Human-driven, no hard cap | User drives iteration frequency |
| 2: Design | Human-driven, no hard cap | User drives iteration frequency |
| 3: Feature Spec | Human-driven, no hard cap | User drives iteration frequency |
| 4: Spec Review | Review-fix-reverify until convergence (see "a revision earns a fresh review round") | Escalate to the user if the round cap is reached without convergence |
| 5: Task Breakdown | 2 compilation attempts | Escalate if compilation fails twice. Applies to the deterministic compilation gate only |
| 5b: Breakdown Review | Review-fix-reverify until convergence | Semantic review of the compiled task set (task review, coherence, cross-model), distinct from compilation attempts |
| 6: Implementation | 2 task escalations per task, then escalate to user | Escalate to user if escalation limit reached. After the final wave, run the full test suite before offering any commit. |
| 7: Code Review | Review-fix-reverify until convergence | Escalate to the user if the round cap is reached without convergence |

A **task escalation** is a task rewrite assigned to a different teammate after in-session resolution fails. **In-session retries** — TaskCompleted hook rejections resolved by the teammate without escalation — are not task escalations. Track both metrics separately in the retrospective.

**Stage transitions are human-approved, agent-facilitated**. Agent runs the gate, reports results, offers the next stage and a cross-model second opinion (`/fbk-cross-model-review`) on the stage's artifact — the skill no-ops for projects that have not opted in. See "Stage Transitions" below for the write/summarize/compact/invoke sequence.

**Mid-pipeline entry**: If the user invokes a stage directly, check the immediately prior stage's structural gate first. Report what failed and offer to run the prior stage to resolve it.

## Stage Guides

When co-authoring intent → `/fbk-intent` skill loads `fbk-sdl-workflow/intent-guide.md`

When co-authoring a design → `/fbk-design` skill loads `fbk-sdl-workflow/design-guide.md`

When co-authoring a feature specification → `/fbk-spec` skill loads `fbk-sdl-workflow/feature-spec-guide.md`

When performing a specification review → `/fbk-spec-review` skill loads `fbk-sdl-workflow/review-perspectives.md`

When creating a threat model during spec review → Load on demand: `fbk-sdl-workflow/threat-modeling.md`

When creating or modifying `.claude/automation/config.yml` → `fbk-sdl-workflow/config-yml-schema.md`

When creating or modifying `.claude/automation/verify.yml` → `fbk-sdl-workflow/verify-yml-schema.md`

When compiling a specification into tasks → `/fbk-breakdown` skill loads `fbk-sdl-workflow/task-compilation.md`

When identifying slices during breakdown → `fbk-sdl-workflow/slice-shapes.md` (routes to the four shape leaves)

When a phase is invoked directly (mid-pipeline entry) → `fbk-sdl-workflow/capability-entry.md`

When implementing tasks from a breakdown → `/fbk-implement` skill loads `fbk-sdl-workflow/implementation-guide.md`

When reviewing code or running post-implementation review → `/fbk-code-review` skill loads `fbk-sdl-workflow/code-review-guide.md`

When following a corrective or diagnostic workflow → `fbk-sdl-workflow/corrective-workflow.md`

When analyzing retrospectives for pipeline improvement → `/fbk-improve` skill spawns the improvement analyst agent

When writing or updating a feature retrospective → `fbk-sdl-workflow/retrospective-guide.md`

## Stage Transitions

At the end of each stage, follow this protocol: Write all artifacts to disk. Summarize the completed stage (one paragraph: what was delivered, what's ready for the next stage). Compact context by reading from the written artifacts instead of regenerating state. Invoke the next skill with the feature name to initialize the next stage.

## Artifact Layout

**Feature-level directory**: `ai-docs/<feature-name>/` contains the spec, review, optional threat model, and tasks subdirectory. Add `*threat-model*` to `.gitignore` before writing the threat model file.

**Project-level directory**: `ai-docs/<project-name>/` contains a project overview, then feature subdirectories, each following the feature-level structure.
