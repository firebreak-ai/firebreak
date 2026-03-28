# Changelog

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
