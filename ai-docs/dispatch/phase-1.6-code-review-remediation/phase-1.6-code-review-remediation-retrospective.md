# Phase 1.6: Code Review and Remediation — Retrospective

## Factual Data

### Per-Task Results

| Task | Type | Model | Status | Re-plans | Agent success? | Files |
|------|------|-------|--------|----------|----------------|-------|
| T-01 | test | Haiku | complete | 0 | Yes | 1 created |
| T-02 | test | Haiku | complete | 0 | Yes | 1 created |
| T-03 | test | Sonnet | complete | 0 | Yes | 7 created |
| T-04 | impl | Haiku | complete | 0 | Yes | 1 created |
| T-05 | impl | Haiku | complete | 0 | Yes | 1 created |
| T-06 | impl | Haiku | complete | 1 | No — first attempt wrote to `~/.claude/` instead of project path. Retry with explicit path correction succeeded. | 2 created |
| T-07 | impl | Sonnet | complete | 0 | Yes | 3 created |
| T-08 | impl | Haiku | complete | 0 | Yes | 1 modified |
| T-09 | impl | Haiku | complete | 0 | Yes | 3 modified |

### Summary

- **9 tasks, 6 waves, 1 re-plan** (T-06 path confusion)
- **181 tests, all passing** (121 pre-existing + 60 new: 24 structural + 16 skill + 20 integration)
- **Agent success rate**: 8 of 9 tasks completed on first attempt (89%). T-06 required one retry.
- **Model routing**: 7 Haiku, 2 Sonnet. No escalations needed. Sonnet correctly used for multi-file cross-reference tasks (T-03, T-07).
- **Task sizing**: All within constraints. T-03 (7 files) justified as cohesive test fixture.

### Permissions Friction

**This was the first implementation run after renaming `home/.claude/` to `home/dot-claude/`.** The rename resolved the Phase 1.5 permissions blocker — subagent file operations on `home/dot-claude/` paths succeeded without the categorical 100% failure rate previously observed on `home/.claude/` paths. User confirmed significantly fewer permission requests overall. The rename is validated as an effective mitigation.

## Upstream Traceability

### Post-breakdown adjustments (upstream leaks)

| Adjustment | Root cause classification | Upstream stage |
|---|---|---|
| T-06 path confusion: agent wrote to `~/.claude/` instead of `home/dot-claude/` | **Compilation gap** — task file used `home/dot-claude/agents/` as the path, which is correct, but the agent interpreted it as an install-target convention. The task didn't explicitly state "project source path, not user install path." | Breakdown (task instructions) |
| Challenger missing `S-` ID reference (caught by T-03 test 7) | **Compilation gap** — T-06 task instructions for the Challenger didn't include the cross-reference requirement that sighting IDs use `S-NN` format and the Challenger should reference them. The spec's finding format defines this, but it wasn't compiled into the task's interface contract. | Breakdown (interface contract) |
| T-03 `covers` field needed Tier 2 ACs added to satisfy gate | **Gate gap** — the task-reviewer gate requires every spec AC to appear in a test task's `covers` field, but has no concept of Tier 2 ACs that are validated through manual testing only. Workaround: added Tier 2 ACs to T-03's covers with a comment explaining they are manual-test-only. | Gate design |
| Task file paths needed `../../` prefix for gate's project_root | **Gate gap** — known issue from Phase 1.5 retrospective. The gate derives project_root by going up 2 directories from the tasks directory, which breaks for features nested more than 2 levels deep (e.g., `ai-docs/dispatch/phase-1.6-code-review-remediation/`). Still not fixed. | Gate design |
| T-09 missing `test_tasks` field | **Compilation gap** — the compilation agent left `test_tasks: []` instead of referencing T-03. | Breakdown (manifest schema compliance) |
| Orchestrator nearly ended session after breakdown | **Orchestrator error** — the implement skill's instructions clearly state the next step after breakdown is implementation, but the orchestrator offered to "commit and wrap up." Not an upstream leak; a facilitation mistake. | Implementation (orchestrator) |

### Detection attribution

| Issue | Detected by | Could earlier stage have caught it? |
|---|---|---|
| T-06 path confusion | Agent failure (permission request surfaced the symptom), orchestrator context (identified the cause) | **Yes** — a PostToolUse hook checking that Write/Edit targets are within the project tree could catch this deterministically. No such hook exists. |
| Challenger missing `S-` ID | T-03 integration test 7 (structural check for `S-` in Challenger body) | **Yes** — the task-reviewer gate could validate that when a spec defines a cross-reference format (S-NN → F-NN), all agent definitions on both sides of the handoff reference that format. This is an interface contract gap. |
| Gate path resolution | Known — flagged in Phase 1.5 retrospective | **Yes** — fix the gate script's project_root heuristic. Deferred twice now. |

## Process Observations

### What worked well

1. **Test-first caught a real issue.** T-03's integration test 7 caught the Challenger's missing `S-` ID reference — a genuine cross-file consistency gap. The test was written to validate the handoff format, and it found that one side of the handoff wasn't documented. This is the test-first pattern working as designed.

2. **Parallel execution worked cleanly.** Waves 2 and 4 ran 2 tasks each in parallel with no conflicts. The file-scope separation was correct — no merge conflicts, no interference.

3. **The `home/dot-claude/` rename is validated.** First implementation run since the rename, and the categorical permissions blocker from Phase 1.5 did not recur. User confirmed significantly reduced permission friction. The rename should be considered the permanent solution.

4. **Haiku handled 7 of 9 tasks correctly.** Single-file context asset creation with clear instructions is well within Haiku's capability. The two Sonnet tasks (T-03 multi-file fixture, T-07 cross-referenced skill files) were correctly routed — they required cross-file consistency understanding.

5. **The explicit path correction on retry worked immediately.** When T-06 failed on path confusion, adding "CRITICAL PATH NOTE: project source paths, NOT user home directory" to the retry prompt resolved it on first attempt. This suggests the fix is a task instruction improvement, not a model capability issue.

### What needs improvement

1. **Task instructions for this project need explicit "project path vs install path" disambiguation.** The `home/dot-claude/` directory is a template that gets installed to `~/.claude/`. Agents don't inherently know which convention to follow. Every task that creates files in `home/dot-claude/` should include: "Create at the project source path `home/dot-claude/...`, not the user install path `~/.claude/...`."

2. **Interface contracts should include cross-reference formats.** When a spec defines a structured format that crosses agent boundaries (sighting ID `S-NN` produced by Detector, consumed by Challenger), the breakdown should compile this into both agents' task instructions as an explicit interface contract. The spec had this information; the compilation didn't transfer it.

3. **The task-reviewer gate needs Tier 2 AC awareness.** The gate's invariant that every AC must appear in a test task's `covers` field doesn't accommodate ACs that can only be validated through manual testing. The current workaround (adding Tier 2 ACs to a test task's covers with a comment) is fragile. Options: add a `tier2_acs` field to task.json, or add a `manual_test_only` flag per AC in the spec.

4. **The gate's project_root heuristic is still broken for deeply nested features.** This is the second phase where `../../` path prefixes are needed as a workaround. The fix (search upward for `.git` or a marker file) was identified in Phase 1.5 and deferred. It should be addressed.

### Notes

- The `/code-review` skill and its agents are now structurally complete and tested. The next validation step is a human-directed code review session against the user's brownfield test project, which will validate the Tier 2 ACs (loop termination, spec conflict detection, user-directed scoping, project-native tool usage) and the behavioral comparison technique at real-world scale.
- The implementation produced all deliverables as specified: 7 new context assets, 3 test scripts, 6 test fixture files, 3 documentation updates. Total new test assertions: 60.
- This phase's retrospective data should inform improvements to the breakdown compilation process — specifically, the path convention disambiguation and interface contract completeness patterns identified above.
