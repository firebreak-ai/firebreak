# Changelog

## [0.3.4] — 2026-04-03

### Changed
- **Full test suite definition.** `implementation-guide.md` now defines "full test suite" by output requirement: the project's test runner that compiles test files, executes every test, and reports per-test pass/fail results. Build/compile commands explicitly do not satisfy this requirement. All existing "full test suite" references inherit this definition.
- **Retrospectives are rolling documents.** Every pipeline stage (spec, review, breakdown, implementation, code review) now writes to the same retrospective file with create-if-absent semantics and read-before-write to preserve prior stages. Previously, retrospectives were only created at the end of implementation, losing upstream context across session boundaries.
- **Retrospective structure extracted** from `fbk-sdl-workflow.md` inline content to `fbk-sdl-workflow/retrospective-guide.md` leaf doc. Defines cumulative sections (timeline, key decisions, scope changes) updated by each stage, plus per-stage sections appended once.
- **Implementation guide retrospective** changed from "Write" (create new) to create-if-absent + append Stage 4 section, referencing the retrospective guide.
- **Struct field removal guidance** in task compilation: when removing a struct field, combine caller migrations into one task or mark downstream tasks as expected-superseded — agents fix all downstream compile errors in one pass.
- **Test/impl wave ordering** clarified: implementation tasks reference test tasks in strictly earlier waves.
- **Runtime value precision** strengthened in feature-spec-guide: when a value must be resolved at implementation time, name the concrete source and resolution path.
- **Post-impl review convergence criterion** aligned with code-review-guide: "no new sightings above `info` severity" replaces incorrect "`nit`-category" reference.

### Added
- **GitHub Actions CI.** Workflow runs all 31 test scripts (SDL workflow + installer) on push and PR. CI status badge added to README.
- **Call-site grep requirement.** When a task removes, renames, or changes a symbol's signature, grep the codebase for all call sites — spec impact sections are a starting point, not a complete enumeration. Added to `task-compilation.md`, `feature-spec-guide.md` Section 5b, `fbk-spec/SKILL.md` gate, `fbk-spec-review/SKILL.md` council invocation, `fbk-breakdown/SKILL.md` implementation task agent.
- **3 new AI failure mode checklist items**: semantically incoherent test fixtures (item 12), dead conditional guards (item 13), always-nil feature parameters (item 14 — deferred, documented only).
- **Test fixture authoring guidelines**: fixture consistency (cross-object field matching) and zero-value fixture fields (explicitly set every field the production function reads) in `test-authoring.md`.
- **Dead guard detection** across 3 assets: `ai-failure-modes.md` checklist item, `function-design.md` removal cleanup instruction, `existing-code-review.md` detection target.
- **Value reachability check** in task compilation: verify that values prescribed in task instructions are reachable at the target file; create prerequisite tasks instead of placeholder values.
- **All-instances pattern search** in code review: grep the same file and package for all instances of a verified pattern before applying fixes. Added to `code-review-guide.md` orchestration protocol and `fbk-code-review/SKILL.md` detection-verification loop.
- **Post-fix verification** in code review skill: run the full test suite after all fixes are applied before closing the review.
- **Pre-detection test gate** in post-impl review: run the full test suite before spawning Detector agents.
- **Mandatory test gate** in SDL workflow Pipeline Principles: Stage 4 must run the full test suite before offering any commit.
- **Corrective workflow retest scope**: Step 7 now specifies "run the full test suite (not just the diagnostic tests from step 2)."
- **Test task scope boundary** in task compilation: test tasks modify only test files; production dependencies require an extraction task as a prerequisite.
- **Process gap** failure attribution category in implementation guide retrospective: orchestrator skipped or substituted a required verification step.
- **Observability check** in feature-spec-guide: verify code path produces testable output before listing a test requirement.
- **Composition value provenance** in spec-design-thinking: identify the concrete source of threaded values at the outermost wiring point.
- **Extraction cleanup** in function-design: after extracting shared logic, verify every caller uses the extracted function and remove duplicate constructions.
- **Hook escalation principle** in context-assets authoring guide: when a retrospective documents a gap already addressed by a prior corrective action, escalate from rule to hook.
- **Brownfield spec routing**: `fbk-spec/SKILL.md` now conditionally loads `fbk-brownfield-spec.md` for brownfield work — file was previously unreachable by any routing path.
- **Retrospective sections** added to `fbk-spec/SKILL.md`, `fbk-spec-review/SKILL.md`, and `fbk-breakdown/SKILL.md` — each writes its stage section with create-if-absent + read-before-write semantics.

### Fixed
- `fbk-brownfield-spec.md` had no routing path — no skill or guide loaded it. Added conditional load from `fbk-spec/SKILL.md`.
- Reference integrity test (`test-reference-integrity.sh`) had a blind spot for top-level `fbk-docs/` files. Orphan scan now includes depth-1 `fbk-*.md` files excluding known index files. 68 → 78 tests.
- Post-impl review convergence criterion referenced non-existent "`nit`-category" instead of canonical "`info` severity" threshold.

## [0.3.3] — 2026-03-30

### Changed
- **Two-axis finding classification.** Code review findings are now classified on two orthogonal axes — type (behavioral, structural, test-integrity, fragile) and severity (critical, major, minor, info) — aligned with industry standards (SonarQube, CodeClimate, CodeRabbit). Replaces the single-axis `category` field. Canonical definitions in code-review-guide.md, referenced by Detector, Challenger, and existing-code-review.md.
- **Detector is read-only.** Removed Bash from Detector tools and deleted linter discovery section. Linter execution relocated to SKILL.md orchestrator as a pre-spawn step — orchestrator discovers and runs linters, passes results as supplementary context to Detector agent teams.
- **Challenger nit handling.** "Downgrade to nit" replaced with "reject as nit" — nits are excluded from findings entirely and counted separately in retrospectives.
- AI failure modes checklist expanded from 5 to 11 items: bare literals (expanded from magic numbers), non-enforcing tests (expanded from test name contradictions), dead infrastructure, comment-code drift, zero-value sentinel ambiguity, context bypass, string-based error classification.
- Fresh agent per task — workers are no longer reused across tasks to prevent context pollution.

### Added
- **Detection scope expansion.** 5 new structural detection targets in quality-detection.md: parallel collection coupling, dead infrastructure, semantic drift, silent error and context discard, string-based type discrimination.
- **6 new review instructions** in existing-code-review.md: dual-path verification, sentinel value confusion, test-production string alignment, string-based error classification, dead infrastructure detection, severity-ordered finding presentation.
- **Code review orchestration hardening.** Pre-spawn linter execution with 100-finding truncation. Parallel Detector agent team spawning. Stuck-agent recovery (relaunch once, then escalate — never substitute). Cross-unit pattern deduplication and naming. Detection source tagging. `quality-detection.md` reference in Detector spawn instructions.
- **Challenger extensions.** Adjacent observation channel (informational items appended to retrospective). Caller tracing requirement for behavioral-type sightings. `verified-pending-execution` status for test-integrity sightings requiring execution.
- **Test reviewer expansion.** 3 new Tier 1 criteria: stale failure annotations, empty gate tests, advisory assertions. 3 new checkpoint checks: unconditionally skipped tests, phantom assertion strings, build-tag consistency.
- **Implementation pipeline rules.** Hook-rejection retry cap (3 retries). Foreground execution for all verification and hook commands. E2E harness task exception (combined test+impl). Per-site completion conditions for multi-mutation tasks.
- **Quality quantification framework** (`ai-docs/research/quality-quantification.md`): measurement framework for tracking code quality across remediation phases, with per-phase linter data, post-remediation review analysis, and industry comparison.
- Benchmark research document (`ai-docs/research/benchmark-research.md`).
- 8 new structural test scripts covering all 0.3.3 acceptance criteria (194 total test assertions).

### Fixed
- Sighting format template and retrospective fields omitted `linter` as a detection source value despite being added to the canonical list.
- SKILL.md termination condition used stale "nit-category" language inconsistent with the two-axis classification system.
- Redundant checklist item (bare string literal type discrimination) removed — content already covered by expanded bare literals item and string-based error classification item.

## [0.3.2] — 2026-03-29

### Changed
- **Improvement analyst traces routing chains.** Per-asset analysis followed by a path-tracing pass that spawns chain-scoped analysts for skills with execution handoffs. Addresses blind spot where per-file analysis misdiagnosed cross-file routing dead-ends as behavioral problems (same misdiagnosis in Phase 4 and Phase 5).
- Checklist item threshold in code review tests lowered from 10 to 5, matching the research-grounded ai-failure-modes.md checklist size.
- Config loader test and fixture updated for `replan_cap` → `escalation_cap` rename from 0.3.1.
- Task reviewer gate accepts optional project root argument for test isolation.

### Added
- **Execution path completeness test** (`test-execution-paths.sh`): Self-enforcing structural test that discovers skills with `references/` directories, extracts terminal sections from SKILL.md, and verifies every reference file reaches those sections. No manifest required.
- **New-interface signature rule** in task compilation: test+impl tasks sharing a function that does not yet exist must state the exact signature in both task files.
- Schema/constant drift spot-check in per-wave verification.
- Retrospective and `/fbk-improve` finalization steps in both code review reference paths (post-impl and standalone), closing a routing dead-end that caused missed finalization in two consecutive phases.

### Fixed
- Code review reference files were routing dead-ends — agent followed `references/post-impl-review.md` to completion without reaching the Retrospective section in SKILL.md. Both reference paths now terminate with their own finalization steps.
- Orphaned `research-findings.md` moved from `assets/fbk-docs/fbk-dispatch/` to `ai-docs/dispatch/research/`. Stale path reference in dispatch-overview.md updated.
- Pre-existing test failures resolved: 5 failures across 4 test suites, all from post-0.3.1 drift (rename residue, threshold mismatch, fixture path resolution).

## [0.3.1] — 2026-03-28

### Changed
- **Rename "re-plan" to "task escalation"** across all pipeline assets. Clearer terminology: "zero escalations" no longer implies "zero friction."
- Define two-tier friction model in Pipeline Principles: **task escalations** (team lead rewrites and reassigns) vs. **in-session retries** (hook rejections self-corrected by teammate).
- Align task ID format from `T-NN` to `task-NN`, matching the `task-NN-<description>.md` filename convention.
- Merge task file frontmatter schema into `task-compilation.md`; breakdown skill references compilation guide instead of inlining field lists.
- Split compound instructions in breakdown skill failure handling.

### Added
- **Unresponsive agent timeout**: 10-minute initial wait, then 3 status checks at 2-minute intervals before declaring teammate unresponsive.
- **Interface change split rule** in task compilation: split definition changes from caller migration at 5+ callers, with sequential wave constraints for same-file batches.
- **Commit control policy**: teammates do not commit; all commits controlled by team lead at wave checkpoints.
- **Escalation payload**: parked tasks must include task ID, attempt count, and last verification output in the `note` field.
- **In-session retry count** as a retrospective metric alongside escalation count.
- **Post-output steps** in code review orchestration: auto-append findings to retrospective, offer `/fbk-improve` transition.
- **Origin breakdown** in code review finding quality retrospective field.
- **Routing entries** for previously orphaned docs: `config-yml-schema.md`, `verify-yml-schema.md`, `corrective-workflow.md`.
- Corrective workflow reference wired from `/spec` skill on corrective intent detection.
- `.gitignore` ordering constraint: write entry before threat model file.

### Removed
- `task-file-schema.md` standalone doc (content merged into `task-compilation.md`).
- "Goes idle" as an escalation trigger (replaced by timeout mechanism).

## [0.3.0] — 2026-03-27

### Added
- **Code review and remediation** (`/fbk-code-review`): Audits code for AI failure modes — works as a post-implementation pipeline stage or as a standalone conversational review against any project. Co-authors remediation specs from findings. Full Phase 1.6 delivery.
- **Self-improvement pipeline** (`/fbk-improve`): Analyzes retrospectives to propose targeted improvements to Firebreak context assets. Completed its first cycle on its own implementation.
- **Installer** (`installer/install.sh`, `installer/merge-settings.py`): One-line install to `~/.claude/` or any project directory. Merges settings non-destructively. Full test suite included.
- Brownfield validation retrospectives from field-testing the code review pipeline on real codebases.

### Changed
- **Breaking: namespace migration.** Source assets moved from `home/dot-claude/` to `assets/` with `fbk-` prefix on all skills, agents, and docs. All internal references updated.
- README rewritten for clarity — leads with what Firebreak does and how to install it.
- LICENSE updated; project metadata overhauled.

### Fixed
- Subagent permissions blocker resolved by renaming `home/.claude` to `home/dot-claude`.

## [0.2.0] — 2026-03-19

### Added
- **Phase 1.5 Core Enhancement**: Progressive disclosure in spec authoring, deterministic verification gates, and adversarial review via council agents.
- Brownfield retrospective documenting Phase 1.5 field results.
- Task reviewer test infrastructure (`test-task-reviewer.sh`).

### Changed
- SDL workflow broadened to include bug fixes (not just features).
- Autonomous execution model clarified — friction minimization as explicit design goal.
- README improved for first-time visitors.
- Harness analysis updated with self-improvement loop design, testing plan, and revised changelogs.

## [0.1.0] — 2026-03-15

### Added
- Initial release: Firebreak framework for structured agentic development.
- SDL workflow with spec authoring (`/fbk-spec`), spec review (`/fbk-spec-review`), task breakdown (`/fbk-breakdown`), and implementation (`/fbk-implement`).
- Context asset authoring guidelines and skill (`/fbk-context-asset-authoring`).
- Council-based review system with 6 specialized agent perspectives.
- Research documentation linking design decisions to published findings.
