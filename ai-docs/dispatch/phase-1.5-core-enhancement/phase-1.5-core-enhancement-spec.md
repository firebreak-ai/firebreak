# Phase 1.5: Core Enhancement

## Problem

The SDL workflow's greenfield test (10 features, 74 tasks, zero re-plans) demonstrated that the pipeline produces correctly-implemented modules that don't work together. All five bugs discovered occurred at integration seams — the boundaries between modules where unit tests mock across. The application passed 124 tests but failed when a human tried to use it.

Root cause analysis traced every failure to specific upstream gaps:

1. **Missing criteria, not ignored warnings.** The test reviewer agent classified testing gaps as "informational" because its criteria didn't define test-level adequacy or behavioral completeness as blocking conditions. The reviewer correctly identified that canvas checks "could pass from a static background fill alone" (Finding 8, e2e infrastructure review) — then accepted it, because no criterion required it to block. This is a missing-criteria problem, not an ignored-warning problem.
2. **Spec template lacks user-verification requirements.** No spec asked "how would a human verify this works?" — so no spec included e2e tests for user-facing behavior.
3. **Breakdown skill doesn't specify interface contracts** across task boundaries, causing independently-compiled tasks to make incompatible assumptions about shared interfaces (import conventions, key strings, rendering paths, wiring patterns).
4. **Task reviewer gate doesn't accommodate corrective or infrastructure work**, forcing workarounds for bugfix and testing-infrastructure features.
5. **Full ceremony applied uniformly** regardless of whether the work involves design decisions or mechanical fixes.

Critically, the test-driven flow itself is validated by these same results. The pipeline produced zero formal re-plans across ~80 tasks. Every module was correctly implemented against its tests. Model routing worked — 87% of tasks succeeded on Haiku, complex tasks routed to Sonnet all succeeded first attempt. Spec review actively improved designs before implementation (Power-Up System simplification cascade, forward-referencing validated across features). The breakdown gate learning curve flattened (2-3 attempts early, first-attempt late). When the missing e2e tests were added, 4 of 9 failed immediately — and the bugs were fixed easily because the implementation was sound, only the wiring was wrong. The bug-fix cycle proves the core thesis: when tests cover the right behavior at the right level, the pipeline produces working software. The gaps are entirely in what the tests covered, not in how the pipeline used them.

The structured retrospectives produced after each feature are the mechanism that makes all of this actionable. A single test project — 13 features, ~80 tasks — generated enough structured data to trace every bug to a specific upstream gap, identify the exact criteria the test reviewer was missing, quantify model routing effectiveness, measure ceremony overhead, and design targeted fixes. This is the agile retrospective loop operating as intended: observe behavior, identify patterns, refine the process. Human teams aspire to this but rarely close the loop — retrospective findings sit in wikis and don't change the process. The SDL workflow can close the loop because the process *is* context assets, and context assets can be edited. This spec is the self-improvement loop described in the harness patterns analysis already operating at the human+agent level — and the results of implementing it will feed the next iteration. The retrospective data is the pipeline's most important diagnostic output after the code and tests themselves.

The bug-fix cycle that resolved these issues was itself a valuable test — effectively a small brownfield exercise that validated a diagnostic workflow distinct from the standard spec-driven flow. The standard flow is **spec-first** (write spec → derive tests → implement). The corrective flow is **test-first** (write behavioral tests defining "working" → run to surface failures → diagnose → fix). Key findings from this cycle:

| Phase | Standard flow | Corrective flow |
|-------|--------------|-----------------|
| Entry | User describes a feature | User reports a bug or test gap is identified |
| First artifact | Spec (what to build) | Behavioral tests (what "working" means) |
| Diagnosis | N/A — building something new | Context-independent agents identify root cause |
| Spec | Full feature spec | Fix spec constrained by diagnosis findings |
| Tests | Derived from spec, written during implementation | Written before diagnosis, used as completion gate |
| Iteration | Single pass (spec→review→breakdown→implement) | Multiple passes (test→diagnose→fix→retest) |
| Ceremony | Uniform across features | Varies within a single corrective arc |

Five specific tensions between the standard flow and corrective work emerged:

1. **Test-first ordering inverts the standard flow.** The 9 behavioral e2e tests were written first to define "working," preventing the fixing agent from writing tests that validate its own fix. The standard test/impl task pairing assumes tests are derived from the spec — in the corrective flow, the tests ARE the spec for what's broken.
2. **Diagnosis is a distinct phase.** Context-independent agents (without access to the implementing agents' reasoning) identified root causes accurately on first attempt. Context independence prevents inheriting the assumption that the code is correct.
3. **The iterative diagnose→fix→retest cycle.** The first fix resolved 2 of 3 failures; the third required a second diagnosis cycle revealing a test design issue, not a code bug. The corrective flow needs to support re-diagnosis with each cycle potentially revealing a different root cause category.
4. **Ceremony varies within a single corrective arc.** Writing behavioral tests needed review (test design matters). Diagnosis needed context-independent agents. The actual fixes were mechanical (3-5 lines each). One corrective effort spans multiple ceremony levels.
5. **Gate invariants assume feature development.** The task reviewer requires every AC to have both a test task and an implementation task. In corrective work, tests precede the fix and may not need corresponding implementation tasks.

What the cycle validated: test-first prevents fix-validation coupling (all 3 bugs caught by pre-existing tests), context-independent diagnosis is accurate (correct on first attempt), the iterative cycle converges (three passes to full resolution), and mechanical fixes after diagnosis are fast-track candidates (identical quality, 8x faster).

External research confirms the structural nature of these testing gaps: empirical studies show coding agents are measurably more likely to add mocks than human developers (Hora, MSR 2026), and mock assertion techniques miss 50% of defects that other techniques catch. Industry consensus treats deployment-integrity gates as blocking with documented override, not advisory.

These are not architectural problems — the pipeline's structure is validated. They are instruction and criteria gaps in existing context assets that can be addressed through targeted refinement.

## Goals / Non-goals

**Goals:**
- Elevate tests to a first-class quality gate by ensuring the workflow generates real user-perspective requirements with corresponding e2e tests. Unit tests are required but not sufficient. Error-absence tests are required but not sufficient. Every feature must have e2e tests that verify the feature works the way a human user would interact with it.
- Enhance the test reviewer agent with a two-tier enforcement model: one mechanical non-overridable check (silent failure detection) and four structured-judgment checks requiring the reviewer to show its work (test-level adequacy, behavioral completeness, integration seam coverage, seam declaration completeness)
- Add user-verification requirements and integration seam declarations to the spec template so e2e functional requirements are explicit, traceable, and structurally evaluable
- Improve breakdown task compilation to include verified interface contracts — the breakdown agent reads actual referenced files during compilation to verify conventions against real code, not just the spec's claims
- Add pattern consistency checks to the council review for brownfield and integration work
- Add lightweight per-task readiness checks at implementation time for inter-wave dependencies
- Add feature category support to the task reviewer gate for corrective and infrastructure work
- Define fast-track criteria for mechanical bugfixes with known root causes
- Audit permissions friction to identify prompt sources and candidates for elimination in a subsequent phase
- Instrument test reviewer effectiveness from day one with metrics that validate the new criteria are working

**Non-goals:**
- Architectural changes to the pipeline stages — the stage structure is validated and unchanged
- Automated self-improvement loop — this phase captures the criteria; automation is a future phase
- Dedicated troubleshooter or code review agent implementation — the corrective workflow (4h) uses context-independent diagnosis agents, which serve the troubleshooter role described in the harness patterns analysis. However, formalizing these as dedicated agent definitions with their own prompts and personas is deferred. This phase documents the workflow and the context-independence requirement; a future phase may create specialized agent definitions if the workflow demands it
- Lead agent for cross-task coordination — deferred pending failure data from brownfield testing
- Changes to the dispatch pipeline orchestration (phases 2-3) — those remain as designed

## User-facing behavior

The developer's workflow does not change. The same four slash commands (`/spec`, `/spec-review`, `/breakdown`, `/implement`) operate in the same sequence. The changes are internal to the skills and agents:

- During `/spec`, the developer is prompted to define user-verification steps (action → observable outcome format) and declare integration seams. These become the basis for e2e test requirements and seam coverage validation.
- During `/spec-review`, the test reviewer applies a two-tier enforcement model. Tier 1 (mechanical): silent failure detection is a non-overridable hard gate. Tier 2 (structured judgment): test-level adequacy, behavioral completeness, integration seam coverage, and seam declaration completeness require the reviewer to show its work — overridable with documented rationale from a structured reason category.
- During `/breakdown`, task instructions for tasks that touch shared interfaces include explicit interface contracts (import conventions, key string conventions, rendering path, wiring requirements).
- During `/breakdown`, corrective features (bugfixes, testing infrastructure) use relaxed gate invariants that don't require the test-task-plus-impl-task pairing for every AC.
- For corrective work (bugfixes, quality issues), the `/spec` skill recognizes the corrective entry point and prompts for the diagnostic workflow — behavioral tests first, then diagnosis, then fix spec. For mechanical bugfixes with known root causes and validated fix patterns, a fast-track mode bypasses council review, breakdown gate, and agent team.
- A permissions friction audit identifies where prompts fire during pipeline operation and which are candidates for elimination. Actual friction reduction (helper script encapsulation, allowlist updates) is deferred to a subsequent phase informed by the audit.

## Technical approach

All changes are to existing context assets — markdown instruction files, agent definitions, and gate scripts. No new code artifacts.

### 4a. Test reviewer agent enhancement

Modify `home/dot-claude/agents/test-reviewer.md` to add four evaluation criteria organized in a two-tier enforcement model. The tiers reflect a core design principle: mechanical checks that can be evaluated deterministically should never be overridable; judgment checks should require the reviewer to show its work and allow documented override.

#### Tier 1 — Mechanical checks (non-overridable)

This criterion is binary and cheap to satisfy. It blocks the pipeline with no override path.

1. **Silent failure detection**: Flag any test whose sole assertion is the absence of errors (no console errors, no exceptions, no crashes). If the only assertion is error-absence, the test needs a positive assertion that verifies something works, not just that nothing breaks. At CP1 (spec review), flag test descriptions where the expected outcome is "no errors." At CP3 (code review), flag test implementations where the only assertion is error-absence.

#### Tier 2 — Structured judgment checks (overridable with documented rationale)

These criteria require the reviewer to reason about test-behavior relationships. The reviewer must show its work — it cannot pass with a bare assertion of coverage.

2. **Test-level adequacy**: When the spec describes user-facing behavior that depends on a runtime environment materially different from the test environment, at least one test must target the real runtime. Flag when all tests for runtime-dependent behavior are mock-only. To reduce false positives, flag based on specific runtime-dependent indicators: Canvas/WebGL APIs, Web Audio API, real DOM geometry (`getBoundingClientRect`, `IntersectionObserver`), real network I/O, real filesystem operations. The reviewer cites which indicator triggered the flag.

3. **Behavioral completeness**: For each user-facing behavior in the spec (identified via user verification steps), the reviewer must name the specific test that covers it and describe how that test would produce a different result (pass→fail or fail→pass) if the behavior were removed or broken. If the reviewer cannot identify such a test for any user-facing behavior, that is a blocking finding. The reviewer states: "User verification step N is covered by [test name], which would fail because [specific mechanism]."

   For corrective specs (bugfix workflow), two additional "show your work" variants apply:
   - **Existing failing test**: "UV-N is covered by [existing test], which currently fails because [the bug]. The fix will make it pass by [fix mechanism]."
   - **Existing passing test (regression protection)**: "UV-N is covered by [existing test], which currently passes. This test must continue to pass after the fix."

   The reviewer evaluates whether the cited test genuinely covers the UV step, not whether a new test needs to be written.

4. **Integration seam coverage**: When the spec declares integration seams (components sharing mutable state with temporal ordering — identified in the spec's integration seam declaration), the reviewer must identify whether any test exercises the full chain end-to-end rather than mocking across it. If no test covers a declared seam, that is a blocking finding unless overridden.

5. **Seam declaration completeness**: The reviewer evaluates whether the spec's integration seam declaration is complete relative to the technical approach. If the technical approach describes module interactions that are not listed in the seam declaration, the reviewer flags the missing seams. This prevents the gap where an undeclared seam has no coverage check.

#### Override mechanism

Tier 1 findings have no override path — they are binary and the fix is always to add a positive assertion or a real-runtime test.

Tier 2 findings can be overridden by the spec author with a documented rationale anchored to a specific reason category:
- "Covered by existing integration test at [path]" — the seam is already tested elsewhere
- "Seam not testable in current infrastructure" — requires infrastructure that doesn't exist (e.g., visual regression tooling)
- "Behavior verified by [other mechanism]" — manual QA step, deployment smoke test, etc.

The rationale is recorded in the spec's testing strategy section and visible to future reviewers. Freeform justification is not accepted — the rationale must fit a defined category. The test reviewer evaluates whether the rationale is legitimate (the cited test actually exists, the infrastructure gap is real).

Override frequency is surfaced as a visible metric in pipeline output. If override rates trend upward, the criteria may be miscalibrated or the developer may be habituating to bypass.

#### Checkpoint applicability

At CP1 (spec review): All five criteria apply against the testing strategy, user verification steps, and integration seam declarations.

At CP2 (task review): CP2 remains a fidelity check. One structural check added: verify every user verification step from the spec has at least one corresponding test task in the breakdown. This is a fidelity check (did the breakdown translate the requirement?), not an adequacy check (is the requirement good enough?).

At CP3 (code review): Tier 1 criteria apply against test implementations. Tier 2 criteria are not re-evaluated — they were resolved at CP1.

At CP4-5 (integrity, mutation): Unchanged.

### 4b. Spec template enhancement

Modify `home/dot-claude/docs/sdl-workflow/feature-spec-guide.md` to add two required subsections:

#### User verification steps (new subsection in testing strategy)

"How would a human verify this feature works?" Numbered steps, each following a structured **action → observable outcome** format:

> UV-1: Press spacebar → projectile fires and moves upward
> UV-2: Projectile hits invader → invader is destroyed and explosion particles appear
> UV-3: All invaders destroyed → wave transition screen appears, next wave starts with faster invaders

Each step describes one observable user interaction and its expected outcome. Typically 3-8 steps for user-facing features. Infrastructure or internal features may have fewer with documented rationale. If a step cannot be parsed into an action-outcome pair, the spec is not ready for review.

Each user verification step maps to at least one e2e or integration test entry in the testing strategy's "new tests needed" subsection. The mapping is explicit: each test entry in "new tests needed" references the UV step(s) it covers (e.g., "E2e test: fire projectile and verify movement — covers UV-1"). A single e2e test can cover multiple steps if they share a code path — the mapping is step-to-test, not 1:1 step-to-test-file. The test reviewer at CP1 validates this mapping and evaluates whether the corresponding tests are genuine behavioral checks (Tier 2 behavioral completeness criterion). At CP2 (task review), the reviewer verifies this mapping survived into the task breakdown — every UV step with a test entry has a corresponding test task.

Justified gaps are permitted using the Tier 2 override mechanism (structured reason category, documented in the testing strategy).

#### Integration seam declaration (new subsection in technical approach)

When the feature introduces or modifies interactions between modules, declare the integration seams as a checklist:

> - [ ] InputHandler → WeaponSystem: key string convention (`event.key` values)
> - [ ] InvaderGrid → main.js: enemy projectile array wiring (spawn, update, collision, cleanup)
> - [ ] Renderer → Entity: coordinate transform path (drawSprite/drawRect vs raw context)

Each declared seam identifies the two components, the shared state or interface, and the convention that must be consistent across both sides. The test reviewer at CP1 validates that each declared seam has integration or e2e test coverage (Tier 2 integration seam coverage criterion).

This section uses a checklist format, not freeform prose. Spec authors cannot skip it when the feature's technical approach describes module interactions — the spec gate validates the section is present when the technical approach references multiple components.

#### Runtime value precision (new guidance in spec authoring)

When a spec references runtime values — key codes, event names, API paths, configuration keys, enum values, string constants — use the exact runtime representation, not conceptual shorthand.

Conventions that cross module boundaries should be documented once in the spec (or referenced from existing documentation) and used consistently. Example: "The InputHandler stores `event.key` values: `' '` for spacebar, `'Enter'` for enter, `'ArrowLeft'`/`'ArrowRight'` for movement."

### 4c. Council review pattern consistency

Modify `home/dot-claude/docs/sdl-workflow/review-perspectives.md` to add a pattern consistency criterion for brownfield and integration work.

When the spec's technical approach describes integrating with or extending existing modules, the council should verify:

- **Pattern consistency**: Does the proposed approach follow the existing pattern, or does it introduce a parallel path?
- **Integration point existence**: Do the integration points the spec references actually exist in the code?
- **Convention visibility**: Are there conventions in the existing code that the spec doesn't mention but tasks will need to follow? Flag these for breakdown discovery.

### 4d. Breakdown skill enhancement

Modify `home/dot-claude/docs/sdl-workflow/task-compilation.md` to add verified interface contracts and codebase-grounded compilation.

#### Verified interface contracts

When a task references files created or modified by other tasks, the task instructions must specify cross-task interface contracts. At minimum: import/export convention (default vs. named), module type (ESM/CJS), key string or enum conventions used by the referenced module, and any rendering or update-loop wiring patterns the task must follow. Extend this list with any additional cross-task assumptions specific to the project's technology stack — the listed contracts are a floor derived from the greenfield test's compilation gaps, not an exhaustive set.

When a task modifies the orchestrator file (the file that wires all modules together), it is higher-risk and requires additional specification: an explicit wiring checklist stating what must be imported, what must be initialized, what must be updated per frame/tick, and what must be cleaned up. Orchestrator tasks are routed to Sonnet minimum (regardless of other sizing heuristics) and include the wiring checklist as a dedicated section in the task file.

#### Codebase-grounded compilation

The breakdown agent reads the actual files that tasks will reference or modify during compilation — not just compiling from the spec's claims about the codebase. This applies to files that already exist at compilation time. For greenfield tasks creating new files, interface contracts are derived from the spec (the files don't exist yet to verify against).

When compiling interface contracts for existing files:
- **Read the referenced file** to determine the actual convention. If the spec says "spacebar input" but the InputHandler uses `event.key` returning `' '`, the task gets `' '`.
- **If the spec's claim doesn't match the code**, flag the mismatch. If the code is authoritative (existing convention), correct the task instruction to match the code. If the spec is authoritative (new design that intentionally changes the convention), report the conflict back to the user for resolution before completing compilation. The `/breakdown` skill presents the mismatch ("the spec says X but the code uses Y — which is correct?") and waits for a decision before continuing.
- **For brownfield work**, read existing test files to learn testing conventions, existing modules for import/export patterns, and existing configuration for environment requirements.

This expands the breakdown agent's context window (reading 10-20 source files in a brownfield project). The cost is proportionate: one codebase survey by one agent, amortized across all tasks, versus the alternative — compilation gap bugs that cost 2+ hours of full-ceremony corrective work each.

#### Implementation readiness check

Add to `home/dot-claude/docs/sdl-workflow/implementation-guide.md`: before writing code, each implementation agent performs a lightweight readiness check covering only what couldn't be verified at breakdown time:

1. **Prior-wave files exist**: Every file referenced in the task's interface contracts that was created by a prior wave (not pre-existing) is present.
2. **Tests compile**: For implementation tasks, the paired test task's tests compile (they should fail, but they should compile). Test tasks skip this check — they are creating the tests, not consuming them.
3. **Build succeeds**: The repo builds/compiles successfully in its current state.
4. **Contract staleness check**: When a task's interface contracts reference a file modified by a prior wave (detectable from git diff between baseline and current state), re-read the file and verify the specific conventions cited in the contracts still hold. This is a targeted check of specific claims, not a full codebase survey.

If any check fails, the agent reports the specific mismatch without attempting implementation. This saves the implementation token spend and gives the team lead a precise failure to diagnose.

**Sequencing**: The inter-wave regression check (4e) runs between waves as a wave-advancement gate. The readiness check runs per-task within a wave as a pre-implementation gate. The sequence is: Wave N completes → baseline regression check → Wave N+1 starts → each task in N+1 runs readiness check before coding.

What the readiness check does NOT include (already verified at breakdown):
- Full codebase survey — already done during compilation
- Re-verifying conventions of files not modified by prior waves — trust the breakdown's verified contracts

### 4e. Inter-wave regression check

Modify `home/dot-claude/docs/sdl-workflow/implementation-guide.md` to add a mandatory inter-wave verification step using a baseline-snapshot model.

#### The principle

The baseline is the set of tests that pass when wave execution begins. After each wave, the baseline tests must still pass. Any baseline test that now fails is a regression — the wave is not advanced until it's resolved.

This catches regressions introduced by Wave N before Wave N+1 agents build on a broken foundation. In brownfield work, where the pre-existing test suite is larger and more likely to break from new changes, this is especially important.

#### Baseline capture

Before Wave 1 starts, the `/implement` skill runs the full test suite and captures the results to `ai-docs/<feature>/baseline-snapshot.json` — a list of test identifiers (file path + test name) and their pass/fail status. Only passing tests enter the baseline. Tests already failing are excluded automatically.

The baseline is stored as a file so interrupted sessions can resume with the correct baseline. The format is framework-agnostic: test identity is file path + test name string, which is stable across runs unless a wave renames or moves tests.

#### Inter-wave check

After each wave completes and before the next wave starts, run the full test suite and compare results against the baseline snapshot. Any test that was "pass" in the baseline and is now "fail" is a regression. On failure, the wave is not advanced — the team lead diagnoses the regression and either fixes it or parks the feature.

This runs the full suite and diffs results rather than selectively executing baseline tests — avoiding the complexity of framework-specific test filtering.

#### Final verification

After the last wave, run the full test suite — all tests, not just the baseline. At this point, every test (including all newly-created tests from test-writing waves and all diagnostic tests from corrective workflows) should pass. Any failure here means the feature is not complete.

### 4f. Task reviewer gate enhancement

Modify `home/dot-claude/hooks/sdl-workflow/task-reviewer-gate.sh` to support a `category` field.

**Current gate architecture**: The gate script receives a task directory and spec path. It parses YAML frontmatter from individual `task-NN-*.md` files — it does not currently read `task.json`. The `task.json` manifest is produced by `/breakdown` and lives in the same directory, but the gate script does not consume it.

**Change required**: Update the gate script to also read `task.json` from the task directory to extract the `category` field. This is a targeted addition — the gate continues to parse task frontmatter for per-task fields (`id`, `type`, `wave`, `covers`, etc.) and reads `task.json` only for the feature-level `category`.

The `category` field is at the top level of `task.json`:

```json
{
  "spec": "ai-docs/<feature>/<feature>-spec.md",
  "category": "feature",
  "tasks": [...]
}
```

- `category: feature` (default) — current invariants apply: every AC requires both a test task and an implementation task.
- `category: corrective` — relaxed invariants: test tasks can cover ACs without a corresponding implementation task (tests precede the fix), implementation tasks can reference existing tests as completion gates.
- `category: testing-infrastructure` — relaxed invariants: test tasks can satisfy ACs directly without implementation tasks (tests are the product).

When `category` is absent, `feature` is assumed — preserving backward compatibility with existing task sets that lack `task.json` or lack the field.

### 4g. Permissions friction audit

Audit and characterize permissions friction during pipeline operation. Mitigations are deferred to a subsequent phase.

**Key constraint**: The agent cannot observe when the user receives a permissions prompt — tool calls that are auto-approved and user-approved are indistinguishable from the agent's perspective.

**Audit approach**:

1. **Static analysis of allowlist rules** — Analyze the current `settings.json` allowlists against tool call patterns in each pipeline stage's skill and agent definitions. Any tool call pattern that doesn't match an allowlist rule will trigger a prompt. Produces a predicted prompt map: which stage, which tool, which path, why it's not covered.

2. **Pipeline-wide logging hook design** — Specify a lightweight `PreToolUse` hook that logs every tool call (tool name, parameters, target path) during pipeline runs. Cross-referenced against allowlist rules, this produces an empirical prompt map.

The audit produces a prioritized list of prompt sources and candidates for the helper-script-encapsulation pattern. This list informs the mitigation phase.

### 4h. Corrective workflow documentation

Create `home/dot-claude/docs/sdl-workflow/corrective-workflow.md` formalizing the diagnostic workflow that emerged from the greenfield bug-fix cycle. The rationale and retrospective evidence are in the Problem section above; this section defines the workflow to implement.

#### Full diagnostic workflow (new bug class, unknown root cause)

1. Write behavioral tests that define "working" from the user's perspective
2. Run tests, identify failures — the failing tests are the bug specification
3. Root cause analysis by context-independent diagnosis agents (no access to implementing agents' reasoning)
4. Spec the fix, constrained by diagnosis findings and pre-existing tests
5. Review — council evaluates fix design and test coverage
6. Breakdown and implement — fix constrained by behavioral tests as completion gate; use `category: corrective` for relaxed gate invariants
7. Retest — if failures remain, return to step 3

#### Fast-track (known root cause, validated fix pattern)

Appropriate when:
- Root cause is known and identical to a previously-reviewed fix
- Fix is mechanical (same pattern, different file)
- Test patterns are already validated (reuse existing calibrated approaches)
- No design decisions involved

Process: Identify bug → write fix → write/update test → verify. No council review, no breakdown gate, no agent team — single agent executes the fix directly.

#### Escalation

If a fast-track fix does not resolve on first attempt, escalate to the full diagnostic workflow. Do not iterate within fast-track — the value of fast-track is that it works on the first try because the pattern is known.

#### Entry point classification

The `/spec` skill needs a mechanism to distinguish corrective work from feature work. The classification determines which workflow path applies:

- **User-initiated**: The developer invokes `/spec` with an explicit corrective signal — e.g., describing a bug report, referencing failing tests, or stating "fix" intent. The `/spec` skill detects corrective language and asks: "This sounds like corrective work. Should I follow the diagnostic workflow (behavioral tests first) or the standard feature flow?" The developer confirms.
- **Propagation**: The spec records the workflow type in its frontmatter or first section (e.g., `workflow: corrective`). This propagates to breakdown (which sets `category: corrective` in `task.json`) and to the gate (which applies relaxed invariants).
- **Fast-track bypass**: For known-pattern mechanical fixes, the developer skips `/spec` entirely and applies the fix directly. Fast-track does not enter the pipeline — it is a documented escape from the pipeline for cases where the pipeline's ceremony exceeds the work's complexity.

#### Integration with existing pipeline

- The test reviewer at CP1 accommodates corrective specs where diagnostic tests already exist and are failing (Tier 2 corrective guidance in section 4a)
- The task reviewer gate applies `category: corrective` invariants (section 4f)
- The baseline-snapshot regression check (section 4e) automatically excludes failing diagnostic tests from the baseline

## Testing strategy

### New tests needed

This feature modifies context assets (markdown instruction files, agent definitions, workflow documentation) and one gate script. The nature of these changes makes automated testing limited — agent instruction changes can only be validated by observing agent behavior when the instructions are applied, which requires running the pipeline against a real project. This is the same validation model used for the greenfield test that produced the retrospective data driving this spec.

**Automated (gate script only)**:
- Update `tests/sdl-workflow/test-task-reviewer.sh` for the `category` field. Test cases: (a) `category: corrective` manifest with AC covered by test task only → gate passes, (b) `category: corrective` manifest with AC covered by neither → gate rejects, (c) `category: testing-infrastructure` manifest with test-only ACs → gate passes, (d) `category: feature` (or absent) with test-only AC → gate rejects (existing behavior preserved), (e) corrective manifest with mixed coverage (some ACs have both test+impl, some test-only) → gate passes. Covers AC-08.

**Semi-manual validation (requires running the pipeline against a test project)**:
- Most ACs in this spec describe agent behavior changes: the test reviewer applying new criteria, the breakdown agent reading source files, the implementation agent running readiness checks. Validating these requires running the updated pipeline against a real or existing project and observing whether the agents behave as specified. This is inherently semi-manual — the human observes and confirms, the same way the Space Invaders retrospectives were produced.
- The planned brownfield testing phases (testing progression items 2 and 3) serve as the primary validation vehicle. The first brownfield test (modifying the Space Invaders project) will exercise the updated pipeline against code the pipeline itself produced, providing a controlled environment where expected behavior is well-understood.
- Before brownfield testing, a lightweight dry-run is valuable: run one existing Space Invaders feature spec (with known deficiencies — smoke-test-only e2e, no seam declarations) through the updated CP1 to confirm the new criteria fire. This is not a full validation — it's a smoke test that the instruction changes activate.

**Artifact review (no pipeline execution needed)**:
- The permissions audit (AC-12) produces analytical artifacts. Validation is human review of the artifacts for completeness.
- The corrective workflow documentation (AC-10) is a markdown file. Validation is structural review for required sections.

### Existing tests impacted

- `tests/sdl-workflow/test-task-reviewer.sh` — add test cases for `category: corrective` and `category: testing-infrastructure` in task.json manifests.
- `tests/fixtures/tasks/` — add fixture directories for corrective and testing-infrastructure task sets, including updated `task.json` manifests with the `category` field.

### Test infrastructure changes

New test fixtures needed for the corrective and testing-infrastructure task categories. No framework changes.

### User verification steps

- UV-1: Run a spec with smoke-test-only e2e coverage through `/spec-review` → test reviewer blocks with Tier 1 silent failure finding — covers AC-01
- UV-2: Run a spec with jsdom-only tests for a browser-rendered Canvas feature through `/spec-review` → test reviewer flags with Tier 2 test-level adequacy finding citing Canvas API as the runtime-dependent indicator — covers AC-02
- UV-3: Run a spec with user verification steps through `/spec-review` → test reviewer maps each step to a specific test and describes the failure mode (Tier 2 "show your work") — covers AC-02
- UV-4: Run a breakdown of a spec with user verification steps through task review → CP2 verifies every verification step has a corresponding test task — covers AC-06
- UV-5: Submit a corrective task set (`category: corrective`) through the task reviewer gate → gate applies relaxed invariants — covers AC-08
- UV-6: Run the static analysis against current allowlist rules → predicted prompt map identifies which pipeline tool calls trigger prompts and why — covers AC-12
- UV-7: Author a spec with module interactions that omits the integration seam declaration → test reviewer's seam declaration completeness criterion flags the missing section — covers AC-03
- UV-8: Run a breakdown where tasks reference shared interfaces → compiled task files contain interface contract sections with import convention, key strings, and wiring patterns; orchestrator tasks routed to Sonnet with wiring checklist — covers AC-05
- UV-9: Run a breakdown against existing code where the spec uses a conceptual value that doesn't match the actual code → breakdown agent flags the mismatch — covers AC-05
- UV-10: Run an implementation task where a prior-wave file is absent → agent reports readiness check failure without writing code — covers AC-07
- UV-11: Run a multi-wave implementation where Wave N breaks a baseline test → inter-wave check blocks Wave N+1 advancement — covers AC-09
- UV-12: Verify `corrective-workflow.md` contains sections for full diagnostic mode, fast-track mode, escalation criteria, and entry-point classification — covers AC-10

### Integration seam declaration

- [ ] Test reviewer CP1 criteria → spec template user verification steps: the reviewer must reference the verification steps section to evaluate behavioral completeness
- [ ] Test reviewer CP2 fidelity check → breakdown task manifest: CP2 must verify verification step coverage across test tasks
- [ ] Task reviewer gate → task.json category field: gate reads category from manifest and selects invariant set
- [ ] Breakdown codebase-grounded compilation → actual source files: contracts are verified at compilation time, but code could change between compilation and implementation if prior waves modify the same files. The readiness check's contract-staleness check (4d item 4) and inter-wave baseline snapshot (4e) mitigate this
- [ ] Corrective workflow documentation → /spec skill: corrective entry point recognition (bug report vs feature request classification). If the /spec skill does not detect corrective intent, the corrective workflow silently falls back to the standard flow

## Documentation impact

### Project documents to update

- `home/dot-claude/docs/sdl-workflow/feature-spec-guide.md` — add user verification steps subsection (action→outcome format, 3-8 steps), integration seam declaration subsection (checklist format), and runtime value precision guidance to the spec template.
- `home/dot-claude/docs/sdl-workflow/review-perspectives.md` — add pattern consistency criterion for brownfield and integration work (verify proposed approach follows existing patterns, integration points exist, conventions are flagged for breakdown discovery).
- `home/dot-claude/docs/sdl-workflow/task-compilation.md` — add verified interface contracts, codebase-grounded compilation requirements, orchestrator risk flagging, and `category` field to task.json schema.
- `home/dot-claude/docs/sdl-workflow/implementation-guide.md` — add inter-wave baseline-snapshot regression check and per-task lightweight readiness check (prior-wave files exist, tests compile, build succeeds).
- `home/dot-claude/agents/test-reviewer.md` — add two-tier enforcement model with four evaluation criteria, override mechanism, and checkpoint applicability rules. Add Tier 2 guidance for corrective specs where diagnostic tests already exist.
- `ai-docs/dispatch/harness-patterns-analysis.md` — update to reference phase 1.5 as the implementation of findings.

### New documentation to create

- `home/dot-claude/docs/sdl-workflow/corrective-workflow.md` — full diagnostic workflow, fast-track mode, escalation criteria, and differences from the standard spec-driven flow.

## Acceptance criteria

- **AC-01**: The test reviewer agent applies Tier 1 (silent failure detection) as a non-overridable hard gate. A spec whose testing strategy contains only error-absence assertions for user-facing behavior does not pass CP1. No override mechanism exists for Tier 1 findings.
- **AC-02**: The test reviewer agent applies Tier 2 criteria (test-level adequacy, behavioral completeness, integration seam coverage, seam declaration completeness) with structured "show your work" output. The reviewer names the specific test covering each user verification step and describes how it would fail. For test-level adequacy, the reviewer cites the specific runtime-dependent indicator that triggered the flag. Tier 2 findings can be overridden with documented rationale from a defined reason category; freeform justification is rejected.
- **AC-03**: The spec template includes a user verification steps subsection with action→outcome format and an integration seam declaration subsection with checklist format. Specs authored with `/spec` prompt the developer for both sections. Enforcement is instruction-based: the `/spec` skill follows the updated guide and the test reviewer at CP1 validates both sections are present and populated. A spec with module interactions in its technical approach that lacks an integration seam declaration is flagged by the test reviewer's seam declaration completeness criterion (Tier 2).
- **AC-04**: The council review evaluates pattern consistency for specs that integrate with or extend existing modules. The reviewer verifies the proposed approach follows existing patterns rather than introducing parallel paths, integration points referenced in the spec exist in the code, and conventions in existing code that tasks will need to follow are flagged for breakdown discovery.
- **AC-05**: Breakdown produces verified interface contracts: task instructions for shared-interface tasks include contracts (at minimum: import convention, module type, key strings, wiring patterns), orchestrator tasks are routed to Sonnet minimum with wiring checklists, and contracts match actual conventions in referenced files (mismatches flagged during compilation rather than silently passed through).
- **AC-06**: The test reviewer at CP2 verifies that every user verification step from the spec has at least one corresponding test task in the breakdown. A breakdown that omits test tasks for UV steps that had test entries in the approved testing strategy does not pass CP2.
- **AC-07**: Each implementation agent performs a lightweight readiness check before writing code: prior-wave files exist, paired test task's tests compile, and the build succeeds. On failure, the agent reports the mismatch without attempting implementation.
- **AC-08**: The task reviewer gate accepts `category: corrective` and `category: testing-infrastructure` in the task.json manifest and applies relaxed invariants accordingly. Default behavior for `category: feature` (or absent category field) is unchanged. The existing per-task `type` field (test/implementation) is unaffected.
- **AC-09**: Before Wave 1, the full test suite runs and the set of passing tests is captured as the baseline. After each wave, the baseline tests run — any baseline test that now fails blocks wave advancement. After the final wave, the full test suite runs and all tests (baseline + new) must pass.
- **AC-10**: The corrective workflow is documented with both modes (full diagnostic and fast-track), escalation criteria, and the specific differences from the standard spec-driven flow. The documentation covers test-first ordering, context-independent diagnosis, iterative retest cycles, and ceremony-level variation within a corrective arc.
- **AC-11**: The test reviewer output includes structured fields for override rationale and finding severity, enabling metric computation. Override frequency is captured and surfaced visibly in pipeline output. Defect escape rate and revision yield are deferred to a subsequent phase when enough brownfield data exists to define meaningful baselines.
- **AC-12**: A permissions friction audit is completed: static analysis of allowlist rules against pipeline tool call patterns produces a predicted prompt map, and a `PreToolUse` logging hook is designed for empirical validation. The audit identifies the most frequent non-safety-critical prompt sources and candidates for helper-script encapsulation. Actual mitigations are deferred to a subsequent phase.

## Open questions

- **OQ-01: Will baseline flakiness block brownfield wave advancement?**
  In brownfield codebases with flaky tests, a test that passes at capture time but fails intermittently could trigger false regression failures after a wave. This is unlikely in greenfield or disciplined brownfield (zero flakiness across 137 pipeline-produced tests) but is a real concern for undisciplined codebases (testing progression item 3). Candidate mitigations: (1) multiple baseline captures to exclude intermittent failures, (2) known-flaky allowlist from pre-implementation survey, (3) single retry on failure. **Deferral rationale:** No evidence of this problem yet. Defer until brownfield testing produces data. If flakiness blocks wave advancement, option 3 (retry) is the simplest first response.

- **OQ-02: Can Sonnet reliably evaluate Tier 2 criteria?**
  Tier 2 criteria (behavioral completeness "show your work", integration seam coverage) require reasoning about test-behavior relationships — qualitatively harder than Tier 1's mechanical checks. If Sonnet cannot reliably name the specific test and describe the failure mode, Tier 2 may need a higher-capability model or advisory-only status. **Deferral rationale:** Cannot be resolved without empirical testing. Validate during brownfield testing phase by running existing Space Invaders specs through the enhanced reviewer. Fallback: keep Tier 2 advisory and rely on Tier 1 hard gates plus user verification step mapping.

## Dependencies

- Completed greenfield test retrospectives (available — project retrospective and all feature retrospectives written)
- Harness patterns analysis document (available — updated with complete findings)
- Existing SDL workflow context assets (available — skills, agents, hooks, docs in `home/dot-claude/`)
