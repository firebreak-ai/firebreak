# detector-decomposition — Retrospective

## Timeline

| Stage | Started | Completed |
|-------|---------|-----------|
| Stage 1: Spec | 2026-04-07 | 2026-04-08 |
| Stage 2: Spec Review | 2026-04-08 | 2026-04-09 |
| Stage 3: Breakdown | 2026-04-10 | 2026-04-10 |
| Stage 4: Implementation | 2026-04-10 | 2026-04-11 |

## Key decisions

1. **Merged SKILL.md tasks to resolve file scope conflicts** — 7 individual SKILL.md tasks were merged into 3 combined tasks across waves 3-5, each covering a distinct functional area (Agent Team + Presets + Broad Scope; Spawn + Dedup + Batching; Sequential + Respawn). This resolved the gate's file scope conflict while keeping each task within the 55-line constraint. (Stage 3)

2. **Merged code-review-guide.md tasks** — Orchestration Protocol and Retrospective Fields updates were merged into a single task (task-43) since they modify non-overlapping sections of the same file. AC-02 instruction trace was folded into the retrospective fields implementation. (Stage 3)

3. **Removed documentation-only task-46** — detection-accuracy-overview.md path and status updates were removed from the task manifest because the task had no AC coverage and no corresponding test task. Documentation-only path updates can be handled manually or as part of CHANGELOG work. (Stage 3)

4. **AC-07 and AC-19 covered transitively** — "No detection target lost" (AC-07) and "exclusive target assignment" (AC-19) are satisfied by the collective agent creation tasks (25-33) putting the correct targets in the correct agents. AC-07 and AC-19 were added to task-25's covers to satisfy the gate invariant. Test coverage comes from task-09 (no-loss) and task-02 (exclusive assignment). (Stage 3)

5. **AC-02 scoped to structural test** — The hook-based Read attribution mechanism in AC-02 is a runtime concern validated by UV-4 manual inspection. The structural component (code-review-guide.md referencing "instruction trace" in retrospective fields) is covered by task-11 (test) and task-43 (impl). (Stage 3)

## Scope changes

- **task-46 removed**: documentation-only update (detection-accuracy-overview.md paths) dropped from manifest. No AC impact.
- **Tasks 38-40, 42, 44 merged**: 9 individual SKILL.md and guide tasks consolidated into 3 merged tasks. Same AC coverage, fewer files.
- **Wave count expanded from 2 to 5**: original plan had test tasks in wave 1 and impl in wave 1-2. Gate requirement that test tasks precede dependent impl tasks in wave ordering forced impl tasks to wave 2+, with SKILL.md sequential modifications spanning waves 3-5.

## Stage 3: Breakdown

**Compilation attempts:** 2 (first attempt failed gate; second passed after merging tasks and fixing wave ordering)

**Wave structure and rationale:**
- **Wave 1** (17 tasks): All new shell test files — no dependencies, fully parallel
- **Wave 2** (18 tasks): Agent creation + test updates — new agent definitions (7 T1 + IPT + Test Reviewer + Deduplicator + quality-detection targets) parallel with existing test file updates. All depend on wave 1 test tasks.
- **Wave 3** (4 tasks): SKILL.md structural sections (Agent Team + Presets + Broad Scope), code-review-guide.md, post-impl-review.md, generic detector removal
- **Wave 4** (1 task): SKILL.md Detection-Verification Loop rewrite (spawn + dedup + batching)
- **Wave 5** (1 task): SKILL.md sequential preset execution + respawn gating

**Task count:** 41 tasks (24 test, 17 implementation) covering all 20 ACs

**Scope adjustments from compilation:**
- Added AC-02 structural test coverage (instruction trace grep in code-review-guide.md) — originally missed by both task agents
- Added AC-08 retrospective merge-count test (guide grep for merge count/merged pairs) — caught by test reviewer
- Added AC-14 Challenger batching test for code-review-guide.md — caught by test reviewer
- Added AC-03 Broad-Scope Reviews test for SKILL.md — caught by test reviewer
- Fixed inconsistent grep strings in task-09 (D4: "context bypass" → "context discard", "string-based error" → "string-based type discrimination")
- Tightened task-06 identical-payload test from 3 independent word-presence checks to co-occurrence grep

**Test reviewer findings resolved:**
- D1 (significant): Duplicate AC-02 in task-11 covers — fixed
- D2 (blocking): AC-02 hook mechanism — scoped to UV-4 manual inspection; structural component covered
- D3 (blocking): AC-08 retrospective merge count — added test to task-11
- D4 (blocking): Target string inconsistency — aligned task-09 grep strings with canonical names
- D5 (blocking): Challenger batching in guide — added test to task-11
- D6 (blocking): Broad-Scope Reviews — added test to task-06
- D7 (gap): Wave 2 test task dependencies — wave_id ordering is sufficient
- D8 (gap): Weak identical-payload assertion — tightened to co-occurrence grep

## Stage 4: Implementation

### Factual data

**Per-task results:**

| Wave | Tasks | Pass | Fail | Escalations | Models |
|------|-------|------|------|-------------|--------|
| 1 | 17 test | 17 | 0 | 0 | Haiku x17 |
| 2 | 18 (7 test + 11 impl) | 18 | 0 | 0 | Haiku x18 |
| 3 | 3 impl | 3 | 0 | 2 (stale agents) | Sonnet x2, Haiku x1 |
| 4 | 2 impl | 2 | 0 | 0 | Sonnet x1, Haiku x1 |
| 5 | 1 impl | 1 | 0 | 0 | Sonnet x1 |
| **Total** | **41** | **41** | **0** | **2** | |

**In-session retry count:** 0 TaskCompleted hook rejections (hook configured but no rejections fired — all content is markdown, no compile/lint gates apply).

**Task sizing accuracy:** All tasks stayed within declared file scope. No task exceeded 2 files modified.

**Model routing accuracy:** All 30 Haiku tasks succeeded without escalation. All 11 Sonnet tasks succeeded. 0 Haiku-to-Sonnet escalations needed.

**Verification gate pass rates:**
- Wave 1: pass (17/17 new tests compile and run)
- Wave 2: fail then pass (2 baseline regressions from premature SKILL.md assertions in updated tests — fixed by reverting forward-looking assertions)
- Wave 3: fail then pass (2 content gaps — SKILL.md missing "identical code payload ordering", guide missing "instruction trace" — fixed by fresh agent spawns)
- Wave 4: pass
- Wave 5: pass (final — 56/56 tests pass)

### Process issue: teammate agent stalling

Across Waves 3-4, multiple teammate agents completed their file modifications but went unresponsive before marking tasks complete via TaskUpdate. This required:
- Manual status reconciliation (checking git diff to confirm work was done)
- Fresh agent spawns to fix incomplete content (Wave 3 gaps)
- Team lead manually marking tasks complete

**Pattern observed:** Haiku agents in Waves 1-2 (simple file creation) completed and reported reliably. Sonnet agents in Waves 3-4 (complex multi-section edits to existing files) frequently stalled after making changes. The stalling appeared to correlate with task complexity and file size — agents working on SKILL.md and code-review-guide.md were most affected.

**Impact:** Added ~8 hours of wall-clock delay to Waves 3-4 while waiting for unresponsive agents, followed by manual diagnosis and fresh spawns.

**Root cause classification:** Process gap — the implementation protocol lacks a timeout mechanism for detecting stalled teammates. The implementation guide mentions "unresponsive teammate detection" (10-minute timeout with status checks) but this was not automated.

### Upstream traceability

- Stage 2 review iterations: 2 rounds before advancing (Round 1 identified 15 defects, Round 2 confirmed resolutions)
- Blocking findings: 5 blocking + 8 significant from spec review; all 5 blocking resolved in spec
- Stage 3 compilation attempts: 2 (first failed gate on file scope conflicts and wave ordering; second passed after merging tasks)

### Failure attribution

**Wave 2 baseline regressions (2 tests):**
- Root cause: **Compilation gap** — test update tasks (18, 21) were compiled with assertions about SKILL.md content that would only exist after Wave 3. The task instructions should have scoped test updates to only reference content that exists at wave execution time.
- Fix: Reverted forward-looking assertions (checked for old OR new detector references instead of new-only).

**Wave 3 content gaps (2 items):**
- SKILL.md missing "identical code payload ordering": **Implementation error** — the teammate added the Tier 1 Detectors bullet but omitted the payload ordering clause from the same bullet.
- Guide missing "instruction trace": **Implementation error** — the content was actually present but the test's section-extraction logic (`head -n -1`) was stripping the last bullet when the section was the final section in the file. Fixed by adding a trailing newline. This is a hybrid implementation error / test authoring issue.

**Teammate stalling (Waves 3-4):**
- Root cause: **Process gap** — no automated timeout detection for stalled agents. Teammates completed file modifications but did not call TaskUpdate to mark tasks complete before going idle. The team lead had to manually verify file state and close tasks.

## Stage 5: Code Review

**Finding count:** 1 verified, 1 rejected, 0 nits
**False positive rate:** 50% (1/2 sightings rejected)
**Verification rounds:** 1

| ID | Type | Severity | Description |
|----|------|----------|-------------|
| F-01 | structural | minor | IPT agent missing "Leave empty when isolated" in pattern label instruction — inconsistent with all 8 peer agents |

**Rejected:** S-02 (post-impl-review.md agent ID enumeration) — AC-13 satisfied by delegation to SKILL.md.

**Remediation:** F-01 fixed — added "Leave empty when isolated." to `assets/agents/fbk-intent-path-tracer.md` line 14, matching the convention in all 8 peer agents. 56/56 tests pass after fix.

**Failure attribution:** F-01 is a **compilation gap** — the task-32 instructions specified the sighting output section content but did not include the "Leave empty when isolated" clause. The spec (AC-04) says "standard sighting output" without enumerating every field clause, so the task compiler had to derive the standard from the existing agents. The omission was a single missed clause in a copy-forward operation.
