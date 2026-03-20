# Phase 1.5: Core Enhancement — Retrospective

## Factual Data

### Per-Task Results

| Task | Type | Model | Status | Re-plans | Agent success? | Files |
|------|------|-------|--------|----------|----------------|-------|
| T-01 | test | Sonnet | complete | 0 | Yes (agent) | 7 created, 1 modified |
| T-02 | test | Sonnet | complete | 0 | Yes (agent) | 3 created |
| T-03 | impl | Sonnet | complete | 0 | No — 2 agent attempts failed (permissions). Team lead executed. | 1 modified |
| T-04 | impl | Sonnet | complete | 0 | No — agent failed (permissions). Team lead executed. | 1 modified |
| T-05 | impl | Haiku | complete | 0 | No — agent failed (permissions). Team lead executed. | 1 modified |
| T-06 | impl | Sonnet | complete | 0 | Preempted — team lead executed directly after observing pattern. | 1 modified |
| T-07 | impl | Sonnet | complete | 0 | Preempted — team lead executed directly after observing pattern. | 1 modified |
| T-08 | impl | Sonnet | complete | 0 | No — agent failed (permissions). Team lead executed. | 1 modified |
| T-09 | impl | Sonnet | complete | 0 | No — agent failed (permissions). Team lead executed. | 1 created |
| T-10 | impl | Sonnet | complete | 0 | Yes (agent) | 1 created |
| T-11 | impl | Sonnet | complete | 0 | Yes (agent) | 1 modified |

### Summary

- **11 tasks, 3 waves, 0 formal re-plans**
- **15 automated tests, all passing** (9 pre-existing + 6 new category tests)
- **Agent success rate**: 4 of 11 tasks completed by agents (36%). 7 tasks required team lead execution due to permissions.
- **Model routing**: 10 Sonnet, 1 Haiku. No escalations needed (but Haiku task T-05 failed on permissions, not capability).
- **Task sizing**: All within constraints. T-01 (7 files) justified and succeeded. T-02 (3 files) justified and succeeded.

### Permissions Failure Pattern

The dominant implementation finding: **subagents cannot edit files under `home/dot-claude/`**. The `bypassPermissions` agent mode does not override Claude Code's permission checks on this directory. Every task targeting `home/dot-claude/agents/`, `home/dot-claude/docs/`, or `home/dot-claude/hooks/` failed for the agent and was executed by the team lead.

Tasks targeting `ai-docs/` and `tests/` paths succeeded as agents (T-01, T-02, T-10, T-11).

| Path prefix | Agent attempts | Agent successes | Failure rate |
|-------------|---------------|-----------------|-------------|
| `home/dot-claude/` | 7 (including 2 retries for T-03) | 0 | 100% |
| `ai-docs/` | 3 | 3 | 0% |
| `tests/` | 2 | 2 | 0% |

This is live empirical data for the permissions friction audit (T-10) and validates the spec's identification of permissions friction as a significant pipeline issue. The team lead compensated by executing the tasks directly — the implementation quality was unaffected, but the intended parallel agent execution model was not realized for most tasks.

**Implication for the permissions mitigation phase**: The `home/dot-claude/` directory appears to be categorically restricted for subagents, regardless of the `bypassPermissions` flag. The mitigation is either: (a) allowlist rules that pre-approve specific edit patterns for that directory, (b) helper scripts that operate on the files and are themselves pre-approved, or (c) running context-asset-editing tasks in the main agent context rather than as subagents. Option (c) is what happened here by necessity.

## Upstream Traceability

- **Stage 1 (spec)**: Iterative co-authoring session. Spec evolved significantly from preliminary version — started with 5 ACs and 5 sections, ended with 12 ACs and 8 sections. Two council sessions during spec authoring (design questions council, independent review council) produced the two-tier enforcement model and identified 3 missing sightings.
- **Stage 2 (spec review)**: 4-agent discussion review (Architect, Builder, Guardian, Advocate). 3 blocking findings, 14 important, 2 informational. All blocking findings resolved in spec revision. Test reviewer checkpoint returned FAIL with 9 defects (testing strategy referenced ACs not UV steps) — resolved by restructuring.
- **Stage 3 (task breakdown)**: 2 gate attempts. First failed on AC-05a/b/c format (gate expects AC-NN) and `files_to_modify` path resolution (gate's project_root heuristic breaks for deeply-nested task directories). Both resolved. Quick council validation found 5 targeted fixes (T-11 re-route to Sonnet, 6th test case for T-01, explicit paths for T-10, stronger T-02 checklist, T-05 design choice removal).

## Failure Attribution

No formal re-plans occurred. The only failures were permissions-related, not capability-related:

- **Root cause**: Claude Code's permission system restricts subagent file operations on `home/dot-claude/` paths. The `bypassPermissions` mode on Agent invocations does not override this restriction.
- **Classification**: Environment constraint — not a spec gap, compilation gap, or implementation error.
- **Impact**: Team lead executed 7 of 11 tasks directly. The work quality was identical — the team lead had full spec context and produced the same changes the agents specified. The cost was serialized execution rather than parallel execution.

## Process Observations

### What worked well

1. **Spec co-authoring produced a thorough design.** The iterative spec session explored every design dimension: two-tier enforcement, baseline-snapshot model, three-level verification, corrective workflow, permissions friction. Two council sessions independently validated and refined the design. The spec entered breakdown with all major decisions resolved.

2. **Council reviews at multiple stages caught real issues.** The design questions council produced the two-tier enforcement model unanimously. The independent review council found the task.json schema mismatch (blocking — the gate doesn't read task.json). The breakdown validation council caught T-11's Haiku routing and T-02's missing sabotage scenarios. Each review added concrete value.

3. **Gate scripts caught structural issues deterministically.** The spec gate caught open-question formatting. The task reviewer gate caught AC-05a/b/c format and file path resolution. The breakdown gate caught T-02's unjustified file count. Every gate failure was actionable and resolved quickly.

4. **The permissions audit generated live validation data.** T-10 predicted that `home/dot-claude/` paths would be the highest-friction source. The implementation phase immediately confirmed this with a 100% agent failure rate on those paths. The audit artifact now has both predicted and observed data.

### What needs improvement

1. **Subagent permissions for context asset editing.** The pipeline's core deliverables (context assets in `home/dot-claude/`) are in a directory that subagents can't write to. This fundamentally blocks the parallel agent execution model for context-asset-editing features. This needs to be resolved before the next phase — either through allowlist rules, helper scripts, or a different execution model.

2. **Task.json path resolution in the gate script.** The gate derives `project_root` by going up 2 directories from the tasks directory. This breaks for features nested more than 2 levels deep (like `ai-docs/dispatch/phase-1.5-core-enhancement/`). The workaround (relative paths with `../../`) is fragile. The gate should either accept an explicit project root argument or use a more robust heuristic (search upward for a `.git` directory or a known marker file).

3. **The spec grew substantially during iteration.** From 5 ACs to 12 ACs, from 5 sections to 8 sections. Each addition was justified by retrospective evidence and council analysis, but the cumulative scope growth meant the breakdown was larger than initially anticipated. The Advocate's scope-split recommendation (Phase 1.5a testing quality, Phase 1.5b rest) would have produced faster delivery of the highest-impact changes.

### Notes

- The irony of hitting permissions friction during the implementation of the permissions friction audit is worth documenting. T-10 predicted the exact failure class that T-03 through T-09 experienced. This is the self-improvement loop in action — the pipeline is generating data about its own weaknesses during operation.
- Context asset features have a fundamentally different execution profile from code features. Code features benefit from parallel agent execution (each agent writes to a different file). Context asset features often target a small number of files in a restricted directory. The execution model should adapt to the work type.
- The 3-wave structure worked well: test fixtures (Wave 1) → parallel edits (Wave 2) → cross-referencing (Wave 3). The dependency structure was clean — the breakdown council confirmed no hidden inter-task dependencies in Wave 2.
