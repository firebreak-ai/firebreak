# Python Migration — Retrospective

## Timeline

| Stage | Started | Completed |
|---|---|---|
| Stage 1: Spec | 2026-04-17 | 2026-04-17 |
| Stage 2: Spec Review | 2026-04-17 | 2026-04-17 |
| Stage 3: Breakdown | 2026-04-17 | 2026-04-18 |

## Key decisions

1. **Dropped version frontmatter feature** — The manifest already tracks installed version. Per-file version stamps are redundant. (Stage 1)
2. **Dropped uv as runtime dependency** — Only two modules need PyYAML; uv adds install complexity for minimal dependency resolution benefit at current scale. (Stage 1)
3. **Single dispatcher pattern over per-script entry points** — `fbk.py` resolves imports relative to `__file__`, eliminates path-resolution mismatch between context assets and agent working directory. (Stage 1)
4. **`~/.claude/fbk-scripts/` directory over embedding in shared `~/.claude/` space** — Namespaced directory avoids collision with Claude Code's own files and contains the Python project cleanly. (Stage 1)
5. **Python chosen for cross-platform support** — Bash limits users to Linux/macOS. Python runs everywhere Claude Code runs. (Stage 1)
6. **Standardized on `"$HOME"/.claude/fbk-scripts/fbk.py` absolute path** — Eliminates inconsistent path conventions (relative, `~`, `$HOME`) across context assets. Agent doesn't need to resolve paths relative to its PWD. (Stage 1)
7. **Dropped `src/` layout** — Unnecessary for a non-installed project. `fbk/` is a direct sibling of `fbk.py`. (Stage 2)
8. **Relocated `fbk-presets.json` into the package** — Pipeline module's `__file__`-relative path resolution would break after relocation. Moving the data file into `fbk/data/` keeps the resolution self-contained. (Stage 2)
9. **Cross-platform file locking over narrowing the Windows goal** — User expects Windows users. Conditional `fcntl`/`msvcrt` imports preferred over dropping the cross-platform claim. (Stage 2)

## Scope changes

- **Version frontmatter removed from scope** — Originally the primary feature. Dropped after determining the manifest already covers the use case. Spec became single-feature: Python migration.
- **Prerelease versioning not pursued** — Considered and rejected as premature for single-developer workflow.
- **uv removed from scope** — Originally the execution model. Replaced with direct `python3` invocation after evaluating that one dependency (PyYAML) doesn't justify a package manager requirement.
- **Splash damage expanded scope** — 24 existing tests (including `test-preset-config.sh`), 38 context asset references, 4 fbk-docs files, and 1 test fixture added to scope after tracing all callers of the scripts being moved.
- **`fbk-presets.json` added to migration** — Discovered during review that `fbk-pipeline.py` uses `__file__`-relative path resolution to find `config/fbk-presets.json`. The data file must move into the package.
- **Script conversion reclassified** — Review revealed `spec-gate.sh` has 126 lines of bash logic, not a thin wrapper. Reclassified from 2 categories to 3 for accurate effort estimation.

## Stage 1: Spec

**Clarifying questions that revealed ambiguity:**
- "Which files get version frontmatter?" led to discovering JSON files can't have frontmatter, which led to questioning whether frontmatter was needed at all, which led to dropping the feature entirely
- "uv as runtime or dev dependency?" led to evaluating the `~/.claude/` shared directory problem, which led to the `fbk-scripts/` namespaced directory, which led to dropping uv when the simpler dispatcher pattern emerged
- "Is Python the right choice?" surfaced the real motivation (cross-platform) that was missing from the original problem statement

**Scope inclusions:**
- Existing test suite updates (23 files) — discovered via splash damage analysis
- Context asset reference standardization (38 references across 11 files) — discovered via reference tracing
- fbk-docs path updates (4 files) — discovered via reference tracing

**Scope exclusions:**
- Installer modifications — out of scope per user direction; existing file-copy mechanism works without changes
- State machine harness — this migration creates the foundation but doesn't build it
- Per-file versioning — dropped in favor of existing manifest

**Open questions deferred:** None — all resolved during authoring.

## Stage 2: Spec Review

**Perspectives invoked:** Architecture, Pragmatism, Quality (Quick Council — Discussion mode)

**Review iterations:** 2 (initial review + re-review after fixes)

**Blocking findings and resolutions (initial review — 10 blocking):**
- R-01: `fbk-presets.json` path breaks after relocation → relocated into `fbk/data/`
- R-02: `fcntl` Windows incompatibility → added conditional `fcntl`/`msvcrt` imports
- R-07: Script complexity misclassified → reclassified into 3 categories
- R-13: Pipeline test `uv run` scope understated → detailed 60+ line transformation
- R-14: `uv run` assertion change unspecified → specified assertion premise change
- R-15: Installer test mock redesign ungrouped → itemized specific assertions
- T-01: AC-05/06/07/09 missing tests → added test entries
- T-02: UV-3/4/5 missing tests → added entries, UV-4 marked manual
- T-03: 2 benchmark tests not enumerated → listed with "not impacted" caveat
- T-04: Council SKILL.md seam untested → added integration test

**Re-review result:** All 10 blockers verified resolved. 1 new important finding (missed `test-preset-config.sh`) fixed during re-review. Test reviewer found 1 defect (error-absence assertion in session-manager test) — fixed.

**Spec revisions made:** Dropped `src/` layout, dropped `[build-system]`, reclassified scripts to 3 categories, added cross-platform locking, relocated `fbk-presets.json`, added dispatcher specification details (realpath, argv, stdin, version check), expanded existing tests impacted section with itemized assertions, added 11 new test entries for AC/UV traceability gaps.

**Threat model decision:** No — no new trust boundaries, no data handling changes.

## Stage 3: Breakdown

**Compilation attempts:** 2 (initial compilation + fixes after test reviewer)

**Wave structure and rationale (post-council consolidation):**
- Wave 1 (30 tasks: 14 test, 16 impl): All new Python module creation — pytest unit tests for every gate, hook, and shared module, plus all implementation tasks creating the dispatcher, converting bash scripts, and relocating Python modules.
- Wave 2 (17 tasks: 10 test, 7 impl): Integration tests (gate output, state/session, context asset checks, e2e golden fixture parity), context asset reference updates (38 refs across 11 files), existing test path updates (4 consolidated tasks), settings.json update.
- Wave 3 (2 tasks: 1 test, 1 impl): Old file deletion and verification that old locations are empty.

**Task count:** 49 total (25 test, 24 implementation) — consolidated from initial 71

**Scope adjustments from compilation:**
- Initial compilation produced 71 tasks across 4 waves
- Council review identified 12 duplicate tasks (Wave 3 impl tasks mirroring Wave 2 test tasks) — deleted
- Council recommended merging 12 trivial test-path-update tasks into 4 consolidated tasks
- Council recommended merging 6 reference-update tasks into 3
- E2e parity tests converted from live bash comparison to golden fixture approach (bash originals deleted before e2e wave)
- Old file deletion moved to Wave 3 (after e2e golden fixtures captured in Wave 2)
- Same-wave dependencies removed from task.json — the breakdown gate enforces strictly-earlier-wave dependencies, not same-wave ordering (which is handled by test-before-impl invariant)
- task-47 renamed from `task-47-impl-test-hash-gate.md` to `task-47-impl-hash-gate.md` to avoid false matches in test-task glob patterns

**Test reviewer findings (6 blocking, all resolved):**
1. task-17: session integration tests had no behavioral assertions (exit 0 only) — added file existence and registry entry assertions
2. task-22/23: wave frontmatter (4) contradicted body section (3) — fixed body to match
3. task-04: missing test-before-impl validation test — added assertion for "Test ordering" failure
4. task-13: dispatcher import mechanism unspecified — specified COMMAND_MAP must be outside `__main__` for testability
5. task-47: filename contained `-test-` despite being implementation type — renamed
6. task-14: UV-2 (empty file) test case missing — added `/dev/null` input test

**Gate script limitation discovered:** `task-reviewer-gate.sh` and `breakdown-gate.sh` pass all task file contents as a single command-line argument to an embedded Python heredoc. With 71 task files, this exceeds the OS argument list size limit (`E2BIG`). Validation was run using equivalent Python logic reading files directly from disk. This is a pre-existing infrastructure issue, not introduced by this feature.
