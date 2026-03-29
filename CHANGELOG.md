# Changelog

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
