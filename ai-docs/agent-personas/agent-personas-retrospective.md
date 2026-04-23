# Agent Personas — Retrospective

## Timeline

- Stage 1 (Spec): 2026-04-18
- Stage 2 (Spec Review): 2026-04-18
- Stage 3 (Breakdown): 2026-04-18

## Key decisions

1. **Enterprise activation as cross-cutting baseline, not per-agent optimization** — The spec started with individual agent improvements but reframed around a central thesis: enterprise role personas shift the entire pipeline's output distribution from demo/tutorial-grade to production-grade. This framing emerged from the user's articulation of the core intent. (Stage 1)

2. **Personas target maintainability; pipeline handles correctness** — Research (CodePromptEval, PRISM) showed expert personas hurt code correctness but improve maintainability metrics. Rather than viewing this as a problem, we recognized it as complementary to Firebreak's architecture: deterministic gates (spec gates, test-first dev, per-wave verification) engineer correctness; personas cover the gap those gates cannot reach. (Stage 1)

3. **Agent definitions scoped separately from skill workflow modifications** — Creating agent personas and modifying skills to spawn them are separate concerns. This spec creates agent definitions only. Skill integration (spawning, interaction model) is a future spec. (Stage 1)

4. **Council restructuring, not rewrite** — The 6 council agents keep their existing roles and specializations. The change is from description-heavy personas (~75 lines, identity/expertise/style sections) to activation-focused personas (20-35 lines, role activation + quality bars). (Stage 1)

5. **No skill contains extractable persona content** — Investigation confirmed that `/fbk-spec`, `/fbk-breakdown`, and `/fbk-implement` contain workflow instructions but no inline persona framing. No splash-damage skill edits required. (Stage 1)

6. **CHANGELOG update deferred to release-prep, not a breakdown task** — The spec listed a CHANGELOG entry under Documentation impact, but it maps to no AC and the project CLAUDE.md scopes CHANGELOG to release-prep. Including it as an impl task would have required a fake `test_tasks` reference to pass the task-reviewer gate. Dropped from the breakdown; tracked as release-prep per CLAUDE.md convention. (Stage 3)

7. **Task-compiler kept as one agent serving two skill roles** — Spec review F-05 questioned whether test-task and impl-task compilation warrant separate agent definitions. The breakdown preserves the single-agent design: persona content (activation, quality bars, anti-defaults) is identical across both roles; only the spawn-prompt context differs (spec-only for test tasks, spec + test task files for impl tasks). Splitting would duplicate an identical persona across two files differing only in description. (Stage 3)

## Scope changes

- **Removed**: Skill modifications (AC-06/07/08 for `/fbk-spec`, `/fbk-breakdown`, `/fbk-implement` spawning new agents). These were scoped out after clarifying that this spec covers agent definitions, not skill workflows.
- **Removed**: Skill-agent integration UV steps (UV-3/4 invoking skills). UV steps now focus on reading agent files, not exercising skill workflows.
- **Added**: Research-grounded rationale as a deliverable in `agents.md` (not just the spec). Agent authors need to understand why personas are structured this way.
- **Removed at Stage 3**: CHANGELOG update task. Spec lists CHANGELOG under Documentation impact, but it maps to no AC and the project CLAUDE.md scopes CHANGELOG to release-prep. Handling it as a breakdown task would require a fake `test_tasks` reference; deferred to release-prep.

## Stage 1: Spec

**Clarifying questions that revealed ambiguity:**
- Whether council agents should be rewritten or restructured — user clarified restructuring (adjustments, not full rewrites)
- Whether to separate agents from skills or use inline personas — user chose separation for reuse and separation of concerns
- Whether T1 detector boilerplate was in scope — discovered T1 detectors aren't on this branch, making the question moot
- Whether skill workflow modifications were in scope — user clarified that only splash-damage edits (removing extracted persona content) would be in scope, and investigation showed no skills contain persona content to extract

**Scope inclusions:**
- Persona authoring guidance in `agents.md` with research rationale
- 6 council agent restructurings
- 2 existing agent persona additions (test-reviewer, improvement-analyst)
- 3 new agent definitions (spec-author, task-compiler, implementer)

**Scope exclusions:**
- T1 detector agents (not on this branch)
- Detector/Challenger personas (already the quality standard)
- Skill workflow modifications (separate concern)
- Skill orchestration logic changes

**Open questions deferred to later stages:** None — the `/fbk-spec` interaction model question (spawn subagent vs inject persona) was identified but belongs in a skill integration spec, not this one.

## Stage 2: Spec Review

**Perspectives invoked:** Architecture, Pragmatism (Builder), Measurability (Analyst) — discussion mode with 3 agents. Guardian and Security not invoked (no runtime behavior changes, no trust boundaries). Advocate not invoked (no user-facing workflow changes, complexity-watchdog covered by Builder).

**Blocking findings and resolutions:**
1. F-01 (Architect): 40-line structural validation ceiling fails test-reviewer (172 lines) and improvement-analyst (47 lines). Resolution: split validation into persona-only agents (40-line full file) vs agents with task logic (40-line persona section only).
2. F-10 (Analyst): Goal 1 has no baseline or falsifiability. Resolution: explicitly stated that quality shift is assessed by human review during pipeline use, not by automated metrics.

**Spec revisions from review:**
- Line target adjusted from 15-25 to 20-35 (Builder finding — original was unrealistic given Detector at 35 lines body)
- Added "Personas and spawn prompts" precedence principle to authoring guidance (Architect finding)
- Added Detector/Challenger as reference implementations in guidance (Architect finding)
- Added follow-up work section naming skills that need updating (Builder finding)
- Council skill template overlap acknowledged as explicit non-goal (Architect finding)
- Task compiler single-agent justification added (Architect finding)
- Research rationale scoped to conclusion-only in agents.md, citations remain in spec (Builder finding)
- MetaGPT citation softened to match verifiable claim (Analyst finding)
- AC-06 "falsifiable" criterion given litmus test, accepted as human judgment (Analyst finding)
- Spot-check renamed to "persona quality assessment," mechanical anchor added (Analyst finding)
- Documentation content validation test added for AC-01 (test reviewer CP1 defect)

**Test strategy review:** FAIL initially (2 defects: AC-01 untraced, UV-2 unmapped). Remediated by adding documentation content validation test.

**Threat model determination:** No — markdown context assets only, no security surface.

**Iteration count:** 1 round of council discussion, no re-review needed. All blocking findings resolved in spec revisions.

**Informational notes carried forward:**
- Frontmatter `description` field updates are unaddressed (Architect). These are functional (Claude uses them for delegation) and could be tightened. Deferred — not blocking for this spec.
- ChatDev "structural differentiation" interpretation is the spec author's reading, not a direct finding from the paper (Analyst). Acceptable for a spec but would need to be flagged if repeated in a published document.

## Stage 3: Breakdown

**Compilation attempts:** 1 round through the test-task and impl-task agents, plus 1 correction round after the test reviewer flagged a blocking defect.

**Wave structure and rationale:**
- Single wave (Wave 1) containing 5 test tasks (tasks 01-05) and 12 implementation tasks (tasks 06-17).
- No inter-task dependencies were needed — each task modifies or creates a distinct file, so they can run in parallel.
- Test tasks precede impl tasks within the wave per the test-before-impl invariant.
- No Wave 2 was created after the CHANGELOG task was dropped.

**Task count:** 17 tasks (5 test + 12 implementation).
- Test tasks: 1 per AC, plus AC-06's structural half folded into tasks 01-04 alongside the AC they pair with.
- Implementation tasks: 6 council-agent restructurings (one per file), 2 persona-preservation tasks (test-reviewer, improvement-analyst), 3 new-agent creations (spec-author, task-compiler, implementer), and 1 documentation update (agents.md).

**Model routing:**
- Haiku: bounded single-file work with verbatim content specified in task instructions — all test tasks, all 6 council restructurings, all 3 new-agent creations (13 tasks).
- Sonnet: tasks that preserve existing content while adding new content (test-reviewer persona, improvement-analyst persona) and multi-subsection authoring (agents.md guidance) (3 tasks).

**Scope adjustments from compilation:**
- CHANGELOG update task removed (see Key Decision 6).
- Test 3 in task-02 and task-03 strengthened from "persona section non-empty" to "persona section ≥5 lines" after the test reviewer flagged that the original assertion passed trivially pre-implementation against the existing single-line bare instructions — the corrected assertion distinguishes the pre-implementation state (3 lines) from the post-implementation persona block (≥9 lines) and gives the tests genuine regression protection.

**Test reviewer iteration:** 1 blocking finding resolved. The initial test tasks defined Test 3 as "persona section exists (non-empty)" and Test 4 as "≤40 lines" — both assertions passed trivially against the pre-implementation agent files because the existing bare instruction line qualifies as non-empty and is well under 40 lines. The reviewer's option 2 (strengthen the assertion) was applied: Test 3 now requires ≥5 lines, which fails pre-implementation and passes post-implementation.

**Gate results:**
- task-reviewer gate: pass (17 tasks, 6 ACs covered, 1 wave).
- breakdown gate: pass (6 spec ACs, 17 tasks, 1 wave).

## Stage 4: Implementation

### Timeline
- 2026-04-18: Implementation executed in a single session via `/fbk-implement`.

### Factual data

**Team configuration:**
- Test phase: 5 Haiku teammates (one per test task).
- Implementation phase: 9 Haiku + 3 Sonnet teammates (12 total, one per impl task).
- All teammates spawned fresh per task — no reuse across tasks.

**Per-task outcomes (17 tasks):**
- All 17 tasks completed on first attempt with zero escalations.
- task-01 through task-05 (test tasks, Haiku): pass — each test script exits non-zero against pre-implementation files as required.
- task-06 through task-11 (council restructurings, Haiku): pass — all 6 agents rewritten to activation-focused pattern, bodies ≤40 lines.
- task-12 (test-reviewer persona, Sonnet): pass — persona prepended, existing checkpoint logic preserved.
- task-13 (improvement-analyst persona, Sonnet): pass — persona prepended, existing workflow preserved.
- task-14 through task-16 (new agent files, Haiku): pass — 3 new agent files created.
- task-17 (agents.md guidance, Sonnet): pass — `## Persona authoring` section added with all 7 subsections.

**In-session retry count:** 0 (no TaskCompleted hook configured on this project — per-task verification surfaced at per-wave verification instead).

**Task sizing accuracy:** All declared file scopes respected. `git diff --name-only` matches the union of declared scopes for the 17 tasks, plus one authorized out-of-scope edit (`tests/sdl-workflow/test-test-reviewer-agent.sh` regex update — see Failure attribution below).

**Model routing accuracy:**
- Haiku (14 tasks): 14/14 succeeded on first attempt. The verbatim-content bounded tasks matched Haiku's strength well.
- Sonnet (3 tasks): 3/3 succeeded on first attempt.
- No model re-routing occurred.

**Verification gate pass rates:**
- 5 new persona test scripts: 30+10+11+21+12 = 84 assertions total. 84/84 pass post-implementation.
- Baseline shell test suite: 56 tests, all passing at start.
- Post-wave shell test suite: 61/61 passing (56 baseline + 5 new).
- Python test suite: 98/98 passing (unchanged).
- Two regressions detected at per-wave verification; both resolved before wave advancement (see Failure attribution).

**Wall-clock:**
- Test phase: ~20 seconds (5 teammates in parallel).
- Impl phase: ~60 seconds (12 teammates in parallel, longest on Sonnet multi-subsection authoring).
- Verification and regression fixes: ~3 minutes.

### Upstream traceability
- Stage 2 review iterations: 1 round of council discussion, no re-review. All blocking findings resolved in spec revisions.
- Blocking findings count: 2 (F-01 40-line ceiling for agents with task logic; F-10 falsifiability of Goal 1). Both led to spec revisions.
- Stage 3 compilation attempts: 1 round + 1 correction round (test reviewer flagged Test 3 triviality — strengthened to ≥5 lines).

### Failure attribution

**Regression 1 — `test-reference-integrity.sh` fail (2 assertions).**
- Root cause: **Compilation gap**. Task-17 verbatim content instructed `assets/agents/fbk-code-review-detector.md` (source-tree path), but the `test-reference-integrity.sh` convention (established elsewhere in the codebase, e.g., `corrective-workflow.md`) uses `.claude/agents/...` (installed path). The reference-integrity test resolves bare `fbk-X.md` filenames against `fbk-docs/`, which fails for files under `agents/`.
- Resolution: In-place fix of agents.md changing `assets/agents/` to `.claude/agents/` for both references. Test now passes.
- Note: This matches the `feedback_install_paths` memory — context assets should reference installed paths, not source-tree paths.

**Regression 2 — `test-test-reviewer-agent.sh` test 5 fail (1 assertion).**
- Root cause: **Spec gap**. The spec's verbatim persona for `fbk-test-reviewer` uses `evaluate` as the verb ("You evaluate test artifacts at pipeline checkpoints"), but the pre-existing test asserts the first 10 body lines contain `reviewer|review|validate`. The spec didn't anticipate that an existing test would gate on specific role-word vocabulary.
- Resolution: User-authorized update of the test regex to accept `evaluate` as a role-word synonym. This is test maintenance tracking a persona refactor, not test weakening — the semantic assertion (body identifies test + review/evaluate role) is preserved.

### Open questions / follow-up observations

1. **The task-17 verbatim content path convention is a systematic risk.** Any task that specifies verbatim cross-asset references should use install-path conventions (`.claude/...`) to avoid reference-integrity regressions. The `feedback_install_paths` memory is already in place but was not consulted during task-17 authoring.
2. **Pre-existing tests that assert on natural-language vocabulary are brittle to persona refactors.** When a refactor changes agent verbs (review→evaluate, analyze→inspect, etc.), these tests may break. The `test-test-reviewer-agent.sh` pattern (grep first 10 body lines for role words) is a general anti-pattern — structural tests should assert on section headings, not verb choices.
3. **TaskCompleted hook silently no-op'd due to stale context regex.** The hook is installed globally (`~/.claude/hooks/fbk-sdl-workflow/...`) and should fire on every `TaskCompleted` event — but its context-scoping regex expected `ai-docs/<feature>/tasks/task-*.md` (legacy path convention), while current breakdown-compiled tasks live under `ai-docs/<feature>/<feature>-tasks/`. The regex never matched, so the hook exited 0 (pass-through) for every task in this run — per-task verification was silently skipped and regressions only surfaced at per-wave verification. Fixed in this session: regex widened to `ai-docs/\S+?/\S*tasks/task-\S*\.md` (matches both conventions) plus regression tests added. Residual lesson: the installer/install deliverables need a path-convention test suite so breakdown-convention drift doesn't silently disable the hook.
4. **Teammates idled without delivering work summaries for test tasks 02-05.** Summaries for those tasks were reconstructed by the team lead from file inspection and test output. Future runs should prompt teammates to deliver summaries before idling, or delegate summary collection to the team lead's verification step (which is what happened here).

## Post-implementation code review

Run at: `fbk-code-review-2026-04-18-2106.md`
Preset: behavioral-only (Groups 1-4 + Intent Path Tracer)
Sightings total: 33 — Verified: 14 — Rejected (with reasoning): 6 — Rejected-as-nits: 4
False positive rate: 30% total; 18% substantive (excluding nits)

**Verified findings (14):**
- F-01 [test-integrity, major]: No role-activation assertion in test-council-agent-personas.sh
- F-02 [test-integrity, minor]: Bare sentinel 999 in test-new-persona-agents.sh conflates missing-file with 999-line body
- F-03 [test-integrity, minor]: test-test-reviewer-persona.sh Test 5 scans full body instead of persona_section
- F-04 [test-integrity, minor]: test-agents-md-persona-guidance.sh validates AC-01 subsections via keyword grep, not anchored heading grep
- F-05 [test-integrity, minor]: No `## Authority` assertion for builder/advocate in test-council-agent-personas.sh
- F-06 [fragile, minor]: tools-check in test-new-persona-agents.sh handles only inline YAML format
- F-07 [test-integrity, minor]: Test B validates only YAML delimiters, not required frontmatter fields
- F-08 [test-integrity, minor]: Forbidden-heading regex `'^## How You Contribute$'` misses `'## How You Contribute to Discussions'`
- F-09 [test-integrity, minor]: persona_section upper-bound in test-test-reviewer-persona.sh measures only preamble, not full persona
- F-10 [structural, minor]: Test 5 assertion string in test-test-reviewer-agent.sh misrepresents regex by omitting `evaluate`
- F-11 [structural, minor]: Builder quality bar 3 encodes authority grant instead of falsifiable constraint; duplicates `## Authority`
- F-12 [structural, minor]: Advocate quality bar 3 duplicates `## Authority` section with authority-grant language
- F-13 [structural, minor]: Role-activation strings hardcoded in test-new-persona-agents.sh without spec-reference annotation
- F-14 [structural, minor]: Forbidden-heading blocklist is inline bare compound regex without named variable or spec reference

**Rejected findings summary:**
- 6 rejections with reasoning (spec-allowed Authority section, install-path convention per `feedback_install_paths`, AC-06 framing, spec follow-up declarations for new agents and skill overlap, non-prescribed placement)
- 4 rejected-as-nits (bare literal 40, dead body() helper, case-sensitive heading grep, variable reuse between tests)

**Cross-finding patterns:**
1. Missing structural-test coverage (F-01, F-05, F-07, F-08, F-09): 5 of 14 findings are missing test assertions — the test author prioritized ceilings over presence checks.
2. Label/regex drift (F-03, F-10): Test assertion labels describe narrower checks than regexes perform.
3. Quality-bar falsifiability violations (F-11, F-12): Two council agents placed authority grants inside quality bars, contradicting AC-06.
4. Spec-discriminator bare literals (F-13, F-14): Spec-defined test values without provenance annotation.

