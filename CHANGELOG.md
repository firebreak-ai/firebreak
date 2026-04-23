# Changelog

## [0.4.0]

### Changed
- **Full-repo benchmark methodology for Martian evaluation.** Added `fetch_pr_shas.py` (GitHub API SHA enrichment), `clone_repos.py` (shared bare caches + per-PR worktrees with diff applied, head_sha fallback), `benchmark-prompt-fullrepo.md`, and `--mode {full-repo,diff-only}` flag on `run_reviews.sh`. Full-repo is the new default; diff-only preserved for reproducibility. Benchmark peers (Devin, Augment, Greptile, etc.) review forked repos at HEAD with full repo visibility; Firebreak was prior reviewing with diff-only context, which systematically suppressed findings whose consequence chain required extra-diff verification. Pilot result (single cycle, 50 PRs): F1 41.3% (vs diff-only 37.6% on the same 50). See `ai-docs/detection-accuracy/martian-benchmark/results/0.4.0-fullrepo-50pr-results.md`.
- **Challenger uncertainty-as-rejection behavior fixed in `assets/agents/fbk-code-review-challenger.md`.** The verification rule now explicitly distinguishes "mechanism unverifiable" (reject) from "mechanism real, intent unclear" (verify with intent-ambiguity note in evidence field). The rejection criteria tightened to "explicitly documented intent (specs, ACs, code comments)" — Challenger inferences about what the author "might have meant" no longer count as grounds to reject. Motivation: 0.4.0 broad-behavioral run found PR79265's S-03 (sync TagDevice blocking auth — golden #2) was rejected because intent was unclear, demoted to "adjacent observation" instead of being verified-with-caveat. The benchmark spot-check estimated ~3-5pp F1 lift addressable with this fix.
- **Detector and Challenger agent instructions synced with broadened behavioral definition.** Both `assets/agents/fbk-code-review-detector.md` and `assets/agents/fbk-code-review-challenger.md` previously held their own copies of the type definitions using the narrow "constructible failing input" wording. They now use the validation-engineer activation, ship-decision test, and broadened behavioral scope from the canonical guide. Without this sync, the orchestrator was reading the broadened guide while the Detector classified using the old narrow rules — net effect: more sightings produced but more filtered out as fragile/structural. Discovered when the first broad-behavioral benchmark attempt regressed (PR8087: 5→0 findings, PR10600: 6→1).
- **Benchmark extraction regex fix in `extract_candidates.py`.** Old regex (`^### F-\d+`) missed reviews using `### S-NN` heading format (no F- prefix) and reviews using em-dash separators. New regex matches both `F` and `S` prefixes and accepts `:`, `—`, ` - ` as separators. Section-restriction logic also dropped — heading-based extraction implicitly filters to verified findings since rejected sightings appear as bold-numbered bullets, not h3 headings. Discovered when PR10600 broad-behavioral re-run reported 0 findings via the wrapper grep but actually had 6 verified findings.
- **Behavioral type definition broadened in `code-review-guide.md`.** The `behavioral` finding type is now anchored on the ship decision ("you would not ship") and a senior validation-engineer mental model rather than the narrow "concrete, constructible input" test that pushed real bugs into `fragile`. The pattern list is explicitly illustrative-not-exhaustive. Disambiguation rules call out the most common misclassification (downgrading to `fragile` when the trigger is runtime state, concurrent execution, or untested code paths). Type-severity validity matrix unchanged. Motivation: the 0.4.0 single-detector benchmark spot-check found 5-6 golden matches dropped because the Detector classified them as `fragile` (race conditions, sync-call-in-auth, predictable OAuth state, broken Zod schema) — all are bugs a human reviewer would block on.
- **Behavioral comparison preamble rephrased from confirmation to active testing.** Replaced "verify whether that behavior aligns" with "test whether the behavior matches... surface any divergence as a finding." Removed "prevents fixation on 'bugs' and focuses on behavioral alignment" framing that suppressed mistake-finding. Grounding rule expanded to name four divergence types (failed AC, failure-mode pattern, architectural mismatch, user-intent contradiction) so the agent does not restrict findings to spec-AC violations alone.
- **Council agent personas restructured to activation-focused pattern.** The 6 council agents (architect, analyst, builder, guardian, security, advocate) now use a role activation line, `## Output quality bars`, and optional `## Anti-defaults` / `## Authority` sections. Description-heavy sections (`## Your Identity`, `## Your Expertise`, `## How You Contribute`, `## Your Communication Style`, `## In Council Discussions`, `## Critical Behaviors`) removed. Body length capped at 40 lines per agent.
- **Test reviewer and improvement analyst gained role-activation personas.** `fbk-test-reviewer` now activates "senior QA engineer with authority to block releases"; `fbk-improvement-analyst` activates "process improvement engineer analyzing production incidents." Existing checkpoint logic, input contract, workflow, and proposal format preserved byte-for-byte.
- **Python migration of shell scripts and hooks into a structured `fbk-scripts/` project.** 15 previously-scattered script files (SDL gate scripts, TaskCompleted hook, dispatch-status hook, council session manager, council session logger, ralph loop, shared state/config/audit utilities, JSON preset data) consolidated into `assets/fbk-scripts/fbk/` with a single `fbk.py` dispatcher. New invocation pattern: `python3 "$HOME"/.claude/fbk-scripts/fbk.py <command> <args>`. 38 context asset references updated across skills, agents, hooks, and docs to use the new path. 13 pytest test files (~200 unit/integration tests) plus preserved 50/50 bash test baseline. Motivation: shell scripts accumulated inconsistencies in error handling, logging, path conventions, and test isolation — each difficult to test without invoking the whole harness. Spec and task breakdown at `ai-docs/python-uv-migration/`.
- **Code-review pipeline CLI (`fbk.py pipeline …`).** Exposes `validate` (schema + type/severity matrix + ID assignment), `domain-filter` (preset-based type filtering), `severity-filter` (threshold filtering), `to-markdown` (JSON → review-report markdown), and `run` (chained validate → domain-filter → severity-filter in a single invocation). Called by the `fbk-code-review` SKILL after each Detector pass to reshape sightings before Challenger verification. Replaces inline shell logic that previously varied across reviews. Preset definitions live in `fbk-scripts/fbk/data/fbk-presets.json`.
- **Council session-state operations consolidated into `fbk.py session-state`.** Previously-inline bash + `python3 -c "…"` heredocs in `fbk-council/SKILL.md` (recovery check, abort check, checkpoint write, cleanup, state display) moved into `assets/fbk-scripts/fbk/council/session_state.py` with pytest coverage. Motivation: every state operation now reaches Claude Code as a `python3 …fbk.py session-state …` call matching the existing `Bash(python3:*)` allow rule, so the council no longer triggers permission prompts for session bookkeeping. SKILL.md net −38 lines (29 added, 67 removed).

### Added
- **Procedural detection audits** at `assets/fbk-docs/fbk-sdl-workflow/detection-audits.md`, wired into the Detector spawn prompt via the code-review SKILL. Four audits seeded from the 0.4.0 full-repo 50-PR false-negative retrospective: concurrency (read-modify-write, check-then-act, double-checked locking, lazy init); logic-inversion branch enumeration (decision-table diff for changed predicates/operators/variables); test-integrity (per-test name/mock/strictness/shared-default audit); and cross-function API trace (exported-symbol caller enumeration on signature/return-shape changes). Kept separate from `ai-failure-modes.md` because these are procedural enumeration passes rather than pattern descriptors — the retrospective found the Detector recognizes patterns when they jump out but does not systematically enumerate sites. New `audit-pass` value added to `detection_source`; Detector agent gained an "Audit passes" directive section and explicit permission for cross-file Grep/Read during API trace. Expected directional lift (single-cycle pilot estimate): ~15-20 TPs on 136 goldens if every audit delivers as estimated — not a guarantee. See `ai-docs/detection-accuracy/martian-benchmark/results/0.4.0-fullrepo-50pr-fn-retrospective.md`.
- **Security detection targets reference** at `assets/fbk-docs/fbk-sdl-workflow/security-patterns.md`, wired into the Detector's source of truth via the code-review SKILL. Five initial pattern-focused entries seeded from the 50-PR full-repo benchmark's missed security goldens: unescaped interpolation (XSS/injection family), unvalidated server-side URL fetch (SSRF), weak origin validation (postMessage/CORS/referer), disabled or weakened browser security header, and non-deterministic key derivation for cross-process state. Kept separate from `ai-failure-modes.md` because security defects are not AI-specific.
- **Typechecker execution in Pre-Spawn Tool Execution.** `assets/skills/fbk-code-review/SKILL.md` now discovers typecheck configs (`tsconfig.json`, `mypy.ini`, `go.mod`, `build.gradle`, `pom.xml`) alongside linter configs, and runs project-native typecheckers (`tsc --noEmit`, `go build ./...`, `go vet ./...`, `mypy --strict`, `javac -Xlint`) when present. Typechecker output is piped into the Detector's spawn prompt as supplementary context using the existing `linter` detection-source tag — no schema change. Motivation: 3 full-repo 50-PR false negatives (Grafana Go arity, Cal.com TS fetch Response, Keycloak Java direct-exit) were deterministically visible to the project's own typechecker but never surfaced because no mechanical check ran.
- **Persona authoring guidance** in `assets/fbk-docs/fbk-context-assets/agents.md`: enterprise activation baseline, correctness-vs-maintainability rationale, persona structure (role activation, output quality bars, anti-defaults), personas-and-spawn-prompts precedence, reference implementations (Detector and Challenger), what not to include, and when personas are unnecessary.
- **Three new agent definitions** for roles previously spawned as anonymous teammates: `fbk-spec-author` (principal engineer writing technical specifications, read-only), `fbk-task-compiler` (tech lead decomposing reviewed specs, read-only), and `fbk-implementer` (senior engineer implementing against reviewed spec, full implementation tools). These agent definitions are not yet wired into their spawning skills — skill integration is a separate spec.
- **5 new structural test scripts** validating council agent structure, test-reviewer persona section, improvement-analyst persona section, new persona agent files, and agents.md persona guidance subsections (84 new TAP assertions total).

### Fixed
- `tests/sdl-workflow/test-test-reviewer-agent.sh` — role-word regex expanded to accept `evaluate` as a synonym for `review`, tracking the new QA-engineer persona's verb choice.
- Installer no longer copies Python dev artifacts (`.venv/`, `__pycache__/`, `.pytest_cache/`, `*.pyc`, `.DS_Store`) when installed from a local source tree. `installer/install.sh` `enumerate_assets()` prunes these directories and skips these file patterns. Fixes a bug where a dev checkout install pulled ~1,300 files / 25MB of gitignored Python venv artifacts into `~/.claude/`. Users installing via `curl | bash` were unaffected because the GitHub tarball doesn't ship gitignored files.
- Installer detects missing PyYAML runtime dependency (required by `fbk/config.py`) and offers to install it via `python3 -m pip install --user pyyaml`. Interactive TTY prompts for install; non-interactive installs (e.g. `curl | bash`) print manual-install instructions instead. Never aborts the install. PEP 668 externally-managed environments get an explicit hint to use pipx or a venv.
- Shell tests `test-spec-validator.sh`, `test-gate-output-spec-python.sh`, `test-e2e-spec-gate-parity.sh`, and `test-task-reviewer.sh` now isolate audit logs via `LOG_DIR=$(mktemp -d)` with EXIT-trap cleanup. Previously each invocation of `spec-gate` / `task-reviewer-gate` wrote to `$CWD/.claude/automation/logs/`, leaking test artifacts into whatever directory the tests happened to be run from (seen in developer workflows as stray `.log` files under `assets/fbk-scripts/.claude/automation/`).
- `.gitignore` patterns for `.claude/settings.local.json`, `.claude/automation/`, and `.claude/memory/` now match at any depth via `**/` prefix. Previously they were anchored to the repo root and silently failed to ignore equivalent paths nested under `assets/` or other subdirectories.
- **`TaskCompleted` hook context regex** (`assets/fbk-scripts/fbk/hooks/task_completed.py`). The regex for matching task-file paths in hook context was stale — `ai-docs/\S+?/\S*tasks/task-\S*\.md` — causing the hook to silently exit 0 on every task completion. Corrected and covered by the new `tests/test_hooks_task_completed.py`. The `## TaskCompleted Hook` section was also removed from `implementation-guide.md` (hook internals are not agent-facing) and the agent-side hook-existence check in `fbk-implement` SKILL.md was removed (hooks are installation-managed, not per-project).
- **Task-reviewer category validation read the wrong directory.** `validate_tasks_from_files` in `fbk.gates.task_reviewer` derived `tasks_dir` from `os.path.dirname(spec_path)`, which is incorrect when spec and tasks live in different locations (the normal case). Added an explicit `tasks_dir` parameter and updated the 15 task-reviewer tests.
- **Shell tests synced with 0.4.0 persona and guide language changes.** `test-detector-persona.sh`, `test-challenger-persona.sh`, `test-guide-precision-alignment.sh`, and `test-benchmark-infrastructure.sh` had stale assertions from before the Detector/Challenger activation rewrite and the broadened behavioral type definition. 3 assertions updated (staff engineer → senior software validation engineer; structural "no wrong output" → "no path to user-visible failure"; single `benchmark-prompt.md` → split `benchmark-prompt-{fullrepo,diff}.md`); 4 deprecated assertions removed (behavioral "concrete failing input" requirement; fragile "specific change" language; Challenger "cannot reproduce → reject" rule; guide fragile "specific change" language). Also `test-config-loader.sh` and `test-task-reviewer.sh` now resolve PyYAML via the fbk-scripts venv Python, falling back to system `python3`.

## [0.3.5] — 2026-04-05

### Changed
- **Intent extraction is mandatory.** The code review pipeline now requires intent extraction before detection begins — discover project documentation, build a structured intent register (prose claims + Mermaid diagram), present to the user for confirmation, supplement from code. Previously, intent extraction existed only in planning docs and was skipped in every review.
- **Code review output consolidates into a single review report file** (`fbk-code-review-<date>-<time>.md`). Intent register, verified findings, and retrospective accumulate in one file the user opens in VSCode to see rendered diagrams and results.
- **Retrospective output unified.** All three code review paths (SKILL.md, existing-code-review.md, code-review-guide.md) now write the retrospective to the review report file instead of separate feature retrospective paths.
- **Instruction-hygiene restructuring.** Deduplicated 3 redundant definitions (dead infrastructure, string-based classification, context bypass/silent error). Resolved scope contradiction in ai-failure-modes.md. Promoted 3 trapped heuristics to quality-detection.md. Split compound checklist item 12 into items 12+13. Added nit suppression to Detector, pattern-label handling to Challenger. Restructured prompt ordering (content-first, instructions-last). Loaded quality-detection.md in conversational review path.

### Added
- **`intent` detection source** in sighting and finding format — findings triggered by behavioral comparison against intent register claims.
- **Intent Extraction section** in SKILL.md: 4-step process (discover documentation, build intent register, user checkpoint, supplement from code).
- **Review Report section** in SKILL.md: establishes the consolidated output file early in the review flow.
- **Intent Register section** in existing-code-review.md: disambiguates "design intent" (user-provided during conversation) from "intent register" (doc-extracted before detection). Instructs register updates when user input contradicts documented claims.
- **Step 0** in code-review-guide.md Orchestration Protocol: intent extraction before the first detection round.
- **Intent register** in code-review-guide.md Retrospective Fields: claims extracted, findings attributed, claims invalidated.
- **Detection accuracy evaluation.** Three reviews of a TS AI agent project (pre-hygiene, post-hygiene, post-intent-fix) compared against 28 filed repo issues. Partial overlap improved from 14.3% to 39.3%. Intent extraction produced 12 findings (29% of total), both criticals intent-sourced. New finding type: "tests protecting bug" — tests that validate broken behavior against documented intent.
- **v0.4.0 plan refinements** based on evaluation: new Tier 2 detection targets (workflow completeness, concurrent path interaction), "tests protecting bug" as Test Reviewer detection target, 3 confirmed methodology gaps (unbounded growth, batch atomicity, intra-function redundancy).
- 5 new test scripts for instruction-hygiene structural coverage.

### Fixed
- Intent extraction skipped in every code review because no pipeline instruction document mentioned it — now structurally gated by section placement and cross-file references.
- Sighting format template in code-review-guide.md missing `intent` in detection source enum.
- code-review-guide.md Post-output steps referenced nonexistent `ai-docs/<feature>/<feature>-retrospective.md` path — now targets the review report file.

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
