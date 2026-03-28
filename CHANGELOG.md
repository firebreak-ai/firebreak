# Changelog

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
