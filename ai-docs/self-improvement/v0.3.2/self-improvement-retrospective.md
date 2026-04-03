# Self-Improvement: Implementation Retrospective

## Factual Data

### Per-Task Results

| Task | Type | Model | Wave | Result | Re-plans | Files |
|------|------|-------|------|--------|----------|-------|
| T-01 | test | Haiku | 1 | pass | 0 | 1 created |
| T-02 | impl | Sonnet | 1 | pass | 0 | 1 created |
| T-03 | test | Haiku | 2 | pass | 0 | 1 created |
| T-04 | impl | Sonnet | 2 | pass | 0 | 1 created |
| T-05 | test | Haiku | 3 | pass | 0 | 1 created |
| T-06 | impl | Sonnet | 3 | pass | 0 | 2 modified |
| T-07 | test | Sonnet | 3 | pass | 0 | 1 created |
| T-08 | test | Haiku | 3 | pass | 0 | 1 modified |

### Task Sizing Accuracy

All tasks stayed within declared file scope. No task exceeded the 2-file constraint. T-06 (2 files modified) was the largest; all others touched 1 file.

### Model Routing Accuracy

- Haiku tasks (T-01, T-03, T-05, T-08): 4/4 succeeded without escalation
- Sonnet tasks (T-02, T-04, T-06, T-07): 4/4 succeeded

No model escalations required. Haiku was sufficient for all bounded TAP test tasks.

### Verification Gate Pass Rates

- Wave 1: passed first attempt
- Wave 2: passed first attempt
- Wave 3: passed first attempt
- Final verification: passed first attempt

### Test Results Summary

| Test file | Result |
|-----------|--------|
| test-improvement-agent.sh (new) | 11/11 |
| test-improvement-skill.sh (new) | 17/17 |
| test-improvement-integration.sh (new) | 11/11 |
| test-reference-integrity.sh (new) | 60/65 (5 pre-existing orphans) |
| test-code-review-integration.sh (modified) | 20/21 (1 pre-existing) |

## Upstream Traceability

- Stage 2 review: 1 iteration. 4 findings resolved (AS-1 missing seam, AS-2 spawn contract, AS-3 install path discovery, UI-1 no opt-out). All resolved in spec before breakdown.
- Stage 3 compilation: 1 attempt. Gate passed on first run.
- Task review (pre-implementation): 5 defects found by test reviewer. 3 fixed mechanically (T-07 gate wording, T-01 missing anti-speculation assertion, T-03 absence-to-presence check). 2 dispositioned by user (UV coverage exclusion accepted, T-05/T-08 duplication documented).
- Breakdown gate: passed after task review fixes.

## Failure Attribution

No task failures occurred. No re-plans needed.

## Process Observations

### Installer bug: project settings.json not populated

The project-level `.claude/settings.json` was empty `{}`. The `TaskCompleted` hook was only present in the global `~/.claude/settings.json`. The installer should populate both project and global settings with the hook configuration. This session was covered by the global hook, but a user without the global settings would have no per-task verification.

**Classification**: Installer gap — not specific to this feature, but discovered during implementation setup.

### Reference integrity test surfaced pre-existing orphaned docs

T-07's reference integrity test found 5 orphaned leaf docs in the existing asset tree:
- `fbk-docs/fbk-dispatch/research-findings.md`
- `fbk-docs/fbk-sdl-workflow/config-yml-schema.md`
- `fbk-docs/fbk-sdl-workflow/corrective-workflow.md`
- `fbk-docs/fbk-sdl-workflow/task-file-schema.md`
- `fbk-docs/fbk-sdl-workflow/verify-yml-schema.md`

These are docs that exist but are not referenced by any routing table or other asset file. They may be intentionally standalone or may be wiring gaps. The test now provides ongoing regression detection for orphaned docs.

### Task review caught real defects before implementation

The pre-implementation task review identified 5 defects that would have caused test gaps or false passes. Three were mechanical fixes; two required design decisions. Running the review before implementation avoided wasted implementation cycles.

### Clean execution suggests well-specified feature

Zero re-plans across 8 tasks and 3 waves. The spec, review, and breakdown process produced task files that were unambiguous enough for all agents (including Haiku) to execute without errors. The feature's scope — context assets only, no application code — contributed to this: structural tests with grep assertions have deterministic pass/fail behavior.

### "Re-plan" metric is misleading

"Zero re-plans" reads as "everything worked first try," but re-plan has a narrow definition: a teammate fails per-wave verification, the team lead rewrites the task file, and a different teammate retries. Tasks where a teammate self-corrected after a TaskCompleted hook rejection, or where the team lead caught an issue during the test compilation check and gave inline feedback, do not count as re-plans. The metric underreports friction and overreports smoothness. Consider renaming to "task rewrite" or "escalated retry" to make the scope clearer, and tracking in-session retries separately.

## Self-Improvement Proposals

`/fbk-improve` was run against this retrospective. 6 analysts examined key assets; 14 proposals produced across 5 assets (code review skill: 0). Proposals are recorded here for future analysis — none were applied in this session.

### Implementation Guide (`fbk-sdl-workflow/implementation-guide.md`) — 4 proposals

1. **Re-Plan Protocol step 6: sharpen escalation payload** — Add explicit payload (which task, attempt count, last verification output) and "do not advance the wave." Prevents vague escalation.
2. **TaskCompleted Hook: remove unreliable idle-detection trigger** — Remove "goes idle" as a re-plan trigger; keep only "messages you without resolving." Idle detection is model-dependent and may never fire.
3. **Retrospective template: distinguish in-session retries from re-plans** — Clarify re-plan count excludes hook retries; add separate in-session retry count metric. Prevents future retrospectives from reproducing the misleading metric.
4. **Team Setup: verify project-level TaskCompleted hook** — Check `.claude/settings.json` for TaskCompleted hook before spawning; add it if missing. Addresses the installer bug observation.

### Implement Skill (`fbk-implement/SKILL.md`) — 1 proposal

5. **Re-Plan Protocol: clarify hook retries don't count toward cap** — Add "In-session retries triggered by TaskCompleted hook rejections do not count toward this cap." The implementation guide defines this distinction but the skill's re-plan section doesn't, risking premature task parking.

### Task Compilation Guide (`fbk-sdl-workflow/task-compilation.md`) — 3 proposals

6. **Model Routing: echo orchestrator Sonnet requirement** — Add "Orchestrator tasks always route to Sonnet minimum" to the Model Routing section. Currently only stated in Interface Contracts; reading order determines compliance.
7. **Verification Gate: add in-session retry tracking to semantic evaluation** — Add "In-session retries are distinct from re-plans — record them separately." Prevents semantic reviewers from treating zero re-plans as zero friction.
8. **Structural Prerequisites: sync AC/test-task coverage with Invariants** — Add "No AC may be satisfied exclusively by implementation tasks." Invariants section states this but Structural Prerequisites list omits it, producing a weaker gate script.

### Breakdown Skill (`fbk-breakdown/SKILL.md`) — 2 proposals

9. **Split compound instruction: gate failure handling (line 75)** — Split "report each failure and return" into two separate statements. Authoring rules quality review.
10. **Split compound instruction: test-reviewer failure handling (line 77)** — Split "add findings to feedback and return" into two statements with consistent "failure list" terminology. Authoring rules quality review.

### SDL Workflow Index (`fbk-sdl-workflow.md`) — 4 proposals

11. **Stage Transitions: clarify human approval vs. auto-invoke** — Change "Invoke the next skill" to "Offer the next skill to the user." Current wording contradicts Pipeline Principles' "human-approved, agent-facilitated" transitions.
12. **Pipeline Principles: define "re-plan" scope** — Add formal definition distinguishing re-plans from in-session retries. Prevents agents from omitting retry friction in reports.
13. **Artifact Layout: add .gitignore ordering constraint** — Specify ".gitignore before writing the threat model file." Prevents accidental commit of sensitive content.
14. **Stage Guides: add routing entries for 4 orphaned leaf docs** — Add routing for `config-yml-schema.md`, `corrective-workflow.md`, `task-file-schema.md`, `verify-yml-schema.md`. *Note: leaf file contents need verification before finalizing trigger conditions.*

### Skill observation: pre-filter needed for large installations

With 40 assets in the installation, spawning one analyst per asset path is expensive and most return no proposals. The skill should add a pre-filter step: match retrospective observations to likely-relevant assets before spawning analysts, rather than analyzing everything. This session manually selected 6 key assets; a future iteration should make that selection a first-class step in the skill's workflow.
