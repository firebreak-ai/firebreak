# Quality Quantification Framework

Measurement framework for tracking code quality across remediation phases. Defines what to measure, why, and how to interpret results.

## Research Questions

### Q1: Does the pipeline introduce debt?

Remediation should not make things worse. Measure lint issues and cognitive complexity introduced by each phase, normalized by lines changed.

**Metrics:**
- Lint issues introduced per phase (`golangci-lint --new-from-rev=<phase-tag>`)
- Cognitive complexity of new/modified functions (gocognit, threshold >30)
- Issues per KLOC changed (defect introduction rate)

**Interpretation:** A phase that touches 400 files and introduces 2 production lint issues is qualitatively different from one that touches 10 files and introduces 2. Normalize by volume.

### Q2: Does the pipeline reduce existing debt?

Measures incidental improvement — the pipeline fixing things it wasn't explicitly asked to fix.

**Metrics:**
- Pre-existing lint issues that disappear phase-over-phase
- Functions that drop below cognitive complexity threshold after modification
- Net lint delta per phase (introduced minus resolved)

**Interpretation:** Incidental debt reduction is a signal that the pipeline's review stages catch pre-existing problems during implementation, not just new ones.

### Q3: Does the pipeline improve over time?

The self-improvement thesis: structured retrospective data should produce better outcomes in later phases than earlier ones.

**Metrics:**
- Per-phase defect introduction rate (issues per KLOC) — compare early phases against later phases
- Correlate with pipeline version (which Firebreak release was active during each phase)
- Escalation rate trend across phases

**Interpretation:** Improving rates across phases with the same pipeline version suggest the codebase is getting easier to work with. Improving rates after a pipeline revision suggest the revision worked. Distinguish these causes by tracking which pipeline version was active.

### Q4: What do linters miss that code review catches?

Quantifies the value of the adversarial review pipeline beyond what automated tooling provides.

**Metrics:**
- Overlap between linter findings and code review findings per phase
- Code review findings by category (semantic-drift, structural, test-integrity, nit)
- Linter-invisible rate: percentage of code review findings with no corresponding linter signal

**Baseline (Phase 5):** Zero overlap — 14 code review findings, all invisible to linters. If this ratio holds across phases, it validates the adversarial review pipeline as complementary to, not redundant with, static analysis.

### Q5: Does linter availability improve code review?

Testable from Phase 6 onward — the first phase with linter integration.

**Metrics:**
- Code review false positive rate (before vs after linter integration)
- Finding category distribution shift — more behavioral/structural findings, fewer mechanical ones
- Time or token cost per review cycle

**Prediction:** With linters handling mechanical checks (unchecked errors, unused variables, style), the Detector/Challenger pipeline should focus on behavioral and structural issues, producing higher-signal findings with fewer false positives.

## Tooling

### golangci-lint (primary, zero infrastructure)

Per-phase analysis using git tags at phase boundaries:

```bash
# Issues introduced by a specific phase
golangci-lint run --new-from-rev=<previous-phase-tag> ./...

# Full codebase (includes pre-existing debt)
golangci-lint run ./...
```

**Default linters** (errcheck, staticcheck, govet, unused, gosimple, ineffassign): Catch obvious bugs and dead code. Conservative, low false-positive rate.

**Aggressive linters** (+ gocognit, gocyclo, dupl, gocritic, revive): Catch complexity, duplication, and style issues. Higher noise in test files (unused-parameter in mocks is expected).

**Recommended filtering:** Report production code, test code, and experimental code separately. Unchecked error returns in test setup calls are standard Go practice and should not be counted as defects.

### SonarQube (optional, richer data)

Adds per-function cognitive complexity scores (distributions, not just threshold violations), technical debt ratio as a single number, duplication percentage with block-level matches, and security hotspot classification. Worth setting up for persistent dashboards across ongoing phases; not required for the core research questions.

### Code review findings (already captured)

Each phase retrospective documents code review results: sighting counts, verified findings, false positive rate, finding categories, and remediation outcomes. These are the primary data source for Q4 and Q5.

## What linting does not measure

- Spec-to-implementation fidelity (behavioral correctness beyond test passage)
- Test behavioral coverage vs line coverage (a test suite can have 100% coverage and 4% mutation score)
- Architectural coherence across modules
- Semantic drift (using bare strings instead of schema constants, predicate naming inconsistency)
- Dead state (code wired in but never invoked at runtime)

These gaps are where the adversarial code review pipeline operates. The measurement framework tracks both linter and review findings to quantify the contribution of each.

## Phase Boundary Tags

Each remediation phase is tagged at its final commit. Use these for `--new-from-rev` comparisons:

| Tag | Phase | Description |
|-----|-------|-------------|
| `pre-remediation` | — | Last commit before Firebreak remediation began |
| `phase-0-complete` | 0 | Security remediation |
| `phase-1-complete` | 1 | Test infrastructure |
| `phase-2-complete` | 2 | Structured prompt migration |
| `phase-3-complete` | 3 | Interface reconciliation |
| `phase-5-complete` | 4+5 | Configuration extraction + code review remediation |
| `phase-6-complete` | 6 | Corrective bug fixes + feature decorator |

## Per-Phase Data

Collected 2026-03-29 using golangci-lint default and aggressive linters at each phase boundary tag. This data captures a partially-completed, pre-planned phased remediation (6 of 8 phases). The initial code review produced findings too broad to remediate in a single pass, requiring decomposition into sequenced phases with distinct scopes. Expect churn in intermediate snapshots — the meaningful comparison is pre-remediation baseline vs post-final-phase, with per-phase data tracking the trajectory.

### Methodology note

The pre-remediation codebase had broken test compilation in `internal/extraction` and `internal/web` (mock interfaces with wrong signatures, test functions with wrong argument counts). golangci-lint cannot analyze packages that fail compilation — typecheck errors suppress all other findings in the affected package. To get a consistent comparison across all phases, per-phase snapshots exclude these packages and `experiments/`. The "full codebase" aggregate at Phase 5 (where compilation is clean) includes all packages.

### Default linters — per-phase snapshots (stable packages)

| Phase | Prod Issues | Test Issues | Total | Lines Changed |
|-------|------------|------------|-------|---------------|
| Pre-remediation (baseline) | 22 | 38 | 60 | — |
| Phase 0 (Security) | 22 | 40 | 62 | ~10K |
| Phase 1 (Test Infra) | 19 | 43 | 62 | ~3.4K |
| Phase 2 (Prompt Migration) | 17 | 43 | 60 | ~5.8K |
| Phase 3 (Psychology) | 17 | 43 | 60 | ~2.3K |
| Phase 4-5 (Config + Review) | 16 | 50 | 66 | ~17.7K |
| Phase 6 (Bug Fixes + Decorator) | 19 | 47 | 66 | ~11.2K |

Production issues: 22 → 16 → 19. The Phase 6 increase (+3) is from previously-broken packages (`internal/extraction`, `internal/web`) now compiling and exposing pre-existing issues — not new issues introduced by Phase 6. Phase 6 introduced 1 new production finding (deprecated API call in a modified function). Test issues: 38 → 50 → 47 (slight decrease as dead test code was deleted).

### Cognitive complexity — per-phase snapshots (stable packages, functions >30)

| Phase | Production | Test |
|-------|-----------|------|
| Pre-remediation | 16 | 8 |
| Phase 0 | 16 | 8 |
| Phase 1 | 16 | 8 |
| Phase 2 | 17 | 8 |
| Phase 3 | 17 | 10 |
| Phase 4-5 | 17 | 13 |
| Phase 6 | 17 | 14 |

Production complexity held steady across all phases (16 → 17, one new function in Phase 2, unchanged through Phase 6). Test complexity grew incrementally (8 → 14) from structural scan tests and observability assertion tests that are inherently complex.

### Full codebase aggregate (all packages)

#### Phase 5 boundary

| Category | Full codebase | Introduced by remediation (phases 0-5) | Pre-existing |
|----------|--------------|----------------------------------------|-------------|
| Production | 30 | 2 | 28 |
| Test | 50 | 19 | 31 |
| Experimental | 20 | 17 | 3 |
| **Total** | **100** | **38** | **62** |

#### Phase 6 boundary

| Category | Full codebase | Introduced by Phase 6 | Delta from Phase 5 |
|----------|--------------|----------------------|-------------------|
| Production | 26 | 1 (deprecated API) | -4 (dead code deleted, issues fixed by remediation) |
| Test | 54 | 3 (nil-deref pattern in DI test) | +4 (new test files) |
| Experimental | 20 | 0 | 0 |
| **Total** | **100** | **4** | **0 net** |

Phase 6 introduced 4 new lint findings (1 production, 3 test) while fixing 4 pre-existing ones, for net zero change. The production finding is a deprecated API call (`WriteQuad` → `WriteQuads`) in a function modified during remediation. The test findings are a nil-deref pattern in a dependency injection test — staticcheck flags the pattern `if err != nil { t.Fatal }; use(result)` even though `t.Fatal` stops execution.

**Aggressive linters (Phase 6 boundary):**

| Linter | Full codebase | Introduced by remediation (phases 0-6) |
|--------|--------------|----------------------------------------|
| Cognitive complexity (>30) — production | 22 functions | 0 (increase from 20 is newly-compilable packages, not new code) |
| Cognitive complexity (>30) — test | 14 functions | 6 (1 new in Phase 6: observability logging test) |
| Code duplication (dupl) | 0 | 0 |
| Cyclomatic complexity (gocyclo) | 0 | 0 |

### Q4 data: linter vs code review overlap

| Phase | Linter findings | Code review findings | Overlap |
|-------|----------------|---------------------|---------|
| Phase 5 (no linter during execution) | — | 14 verified | — |
| Phase 6 (linter available) | 2 (unused function, pre-existing unchecked error) | 4 verified (structural, semantic-drift, test-integrity, nit) | **0** |

Zero overlap across two measurement points. The linter catches mechanical issues (dead code, unchecked errors); the adversarial review catches behavioral issues (sort-broken parallel collections, missing AC-required metrics, test name/scope mismatch). The tools are fully complementary.

### Interpretation

**Production lint** decreased from 22 (pre-remediation, stable packages) to 16 at Phase 5 to 19 at Phase 6. The Phase 6 increase reflects previously-broken packages becoming compilable and exposing pre-existing issues, not new debt from remediation. On the full codebase, production lint dropped from 30 (Phase 5) to 26 (Phase 6) — a net decrease even with Phase 6's new code.

**Production cognitive complexity** held at 17 (stable packages) across all phases from Phase 2 onward. The remediation never introduced a high-complexity production function. Full-codebase count rose from 20 to 22, again from newly-compilable packages.

**Phase 6 introduced 1 production lint issue** (deprecated API) across ~11.2K lines of changes (45 files). The pipeline's per-phase production defect introduction rate remains below 0.1/KLOC.

**Linter + code review complementarity** (Q4): confirmed with zero overlap across Phase 5 and Phase 6. Linters enforce mechanical correctness; adversarial review enforces behavioral fidelity. Neither substitutes for the other.

## Post-Remediation Full-Codebase Review (Phase 6 Boundary)

After 7 phases of remediation (~85K lines of Go across 294 files, 28 packages), a full-codebase code review was run using the Detector/Challenger pipeline against the AI failure mode checklist and structural detection targets — no specs, no phase scoping.

**Results:** 60 verified findings, 0 rejections, ~15 nits excluded. Single round per review unit was sufficient.

### Adversarial verification matters

The initial review run had detector agents get stuck on 4 of 8 review units. The supervisor agent performed its own independent scan and reported those units as clean (0 findings). After relaunching with proper Detector/Challenger coverage, those same 4 units produced **32 additional findings**, including 3 behavioral bugs. The supervisor's shortcut bypassed the adversarial verification that catches non-obvious issues. Cost of the shortcut: 32 missed findings, including a critical bug that made the project's core feature silently non-functional for incremental operations.

### Finding classification

Each finding was classified by origin relative to the remediation phases:

| Category | Count | % | Description |
|----------|-------|---|-------------|
| **Caused by remediation** | 6 | 10% | Introduced by remediation phases themselves |
| **Revealed by remediation** | 5 | 8% | Pre-existing issues made visible by remediation changes |
| **Missed in previous scans** | 16 | 27% | In code that was reviewed per-phase but issues weren't caught |
| **Out of scope** | 33 | 55% | Pre-existing issues in code never targeted by any phase |

**10% introduction rate** across 7 phases changing 400+ files is low. The pipeline creates fewer issues than it resolves. The 55% out-of-scope finding shows the long tail: per-phase reviews are efficient but don't cover the full codebase. Periodic full-codebase sweeps are necessary.

### Finding type distribution by origin

| Type | Caused | Revealed | Missed | Out of scope |
|------|--------|----------|--------|-------------|
| structural | 1 | 0 | 5 | 12 |
| semantic-drift | 1 | 3 | 5 | 5 |
| test-integrity | 4 | 1 | 2 | 2 |
| bare literals / magic numbers | 0 | 0 | 4 | 14 |

**Key finding: remediation disproportionately causes test-integrity issues.** 4 of 6 remediation-caused findings are stale test comments, empty gate tests, or placeholder tests that were never filled in. Agents fix production code but leave test metadata stale. The pipeline has no automated check for test quality post-remediation beyond the test reviewer checkpoint — and that checkpoint validates spec coverage, not comment accuracy or assertion completeness.

### What per-phase spec-scoped reviews miss (Category C analysis)

The 16 missed findings cluster into systematic blind spots:

**1. Adjacent-code blind spot (7 findings).** The per-phase review examines code that was changed but not neighboring code in the same file or package. Error-swallowing in a function adjacent to the one that was fixed. Dead functions in the same package that was modified. A goroutine leak in the same struct's Submit() method while the review caught the identical bug in the worker() method.

**2. Cross-package consistency gap (4 findings).** When a phase centralizes shared resources (e.g., schema constants), the review verifies adoption within the phase's target package but doesn't grep all consumers across the codebase. Bare string literals survived in 18+ sites across packages that weren't in scope.

**3. Duplication within reviewed scope (3 findings).** Spec-scoped reviews check behavioral correctness against acceptance criteria but don't flag internal method duplication or dead feature paths in reviewed files. A scoring formula duplicated across 4 methods in the same file passed review because each method individually met its AC.

**4. Test quality for remediation's own output (2 findings).** Empty gate tests and unconditionally skipped tests were created by remediation phases' test tasks and not caught by per-phase reviews.

### Spec-scoped vs. checklist-scoped review

Per-phase reviews ask: "Did the implementation match the acceptance criteria?" This catches spec-violation bugs effectively — all per-phase findings were genuine and all were remediated.

The full-codebase review asks: "Does the code exhibit known AI failure modes?" This catches structural patterns regardless of whether they were in any phase's scope:

| Concern | Spec-scoped (per-phase) | Checklist-scoped (full-codebase) |
|---------|------------------------|--------------------------------|
| Behavioral correctness vs. spec | Strong | N/A (no spec) |
| Adjacent code quality | Blind | Covered |
| Cross-package consistency | Blind | Covered |
| Internal duplication | Blind | Covered |
| Dead infrastructure | Blind | Covered |
| Error handling / context propagation | Weak (catches only in-scope sites) | Covered (traces call chains) |

Both review modes are necessary. Spec-scoped reviews verify that each phase's changes are correct. Checklist-scoped reviews catch the debt that accumulates between phases.

### Cross-cutting AI failure mode patterns

The 60 findings cluster into 7 cross-cutting patterns that map to known AI code generation failure modes:

**Pattern: Copy-paste-modify instead of extract-and-parameterize (5 instances).** Message processing with ~200 lines duplicated between sync/async variants. Scoring formulas duplicated across 4 methods. Near-identical loader functions for different formats. AI agents generate each function independently and correctly, but never extract shared logic. Matches the GitClear finding of "8x growth in duplicated blocks and 60% collapse in refactoring activity."

**Pattern: Bare string literals despite existing constants (18+ sites across 3 packages).** Constants were defined but inconsistently adopted. Agents use constants in new code but don't migrate existing call sites. Each agent sees only its task scope and doesn't grep for other usage sites of the same string.

**Pattern: Dead/incomplete infrastructure (8 instances).** Interfaces defined but never implemented. Config fields declared but ignored by the code that should read them. Worker pools constructed but never used. Feature paths fully wired but permanently disabled with stale TODOs. Agents build scaffolding for anticipated future features that are never connected.

**Pattern: Silent error handling and context bypass (5 instances).** Functions that swallow errors with empty branches. Use of `context.Background()` instead of forwarding the caller's context, bypassing deadlines and cancellation. Agents reach for the simplest signature rather than threading context through call chains.

**Pattern: Test-integrity decay (9 instances).** Stale comments describing bugs that are now fixed. Empty gate tests with no assertions. Unconditionally skipped tests with behavioral names that imply coverage. Advisory assertions that log instead of failing. Tests whose assertions reference strings absent from the production code they test. This is the most insidious pattern: CI reports green while behavioral coverage has gaps.

**Pattern: Hand-rolled standard library reimplementation (3 instances).** O(n^2) selection and bubble sorts replacing stdlib sort functions. JSON extraction reimplemented with string indexing instead of using existing helpers. Agents write algorithms from scratch rather than using available standard library or project utilities.

**Pattern: String-based dispatch instead of typed errors (14 call sites).** API handlers using string matching on error messages for error classification, despite a typed error package existing in the same project. Agents reach for the approach that's locally simplest, even when the project has better infrastructure available.

### Pipeline strengths (confirmed)

1. **Per-phase reviews catch spec-violation bugs effectively.** All per-phase findings across phases 4-6 were genuine, verified, and remediated. The Detector/Challenger pattern produces low false-positive findings when scoped to acceptance criteria.

2. **Remediation is high quality.** 10% introduction rate (6 of 60 findings caused by remediation), and those 6 are predominantly test-integrity issues (stale comments, empty tests), not production behavioral bugs.

3. **Structural fixes stick.** Interface reconciliation, config wiring, namespace unification, dead code removal — all confirmed correct by the post-remediation review. The pipeline produces durable fixes.

4. **Linter integration is complementary.** Zero overlap between linter findings and code review findings across all measurement points.

5. **Self-improvement loop is working.** Each phase's failure modes are different from the last. Signature mismatches in Phase 5 were eliminated by the 0.3.2 new-interface rule. Routing dead-ends were caught by the execution path test. The pipeline is closing gaps, not cycling.

### Pipeline weaknesses (identified)

1. **Test-integrity is the pipeline's blind spot for its own output.** Agents fix production code and leave test metadata stale. No automated check validates test comment accuracy, assertion completeness, or skip-reason currency after remediation.

2. **Spec-scoped reviews have a fixed radius.** They don't see adjacent code, cross-package consistency, or internal duplication. A post-change grep for old patterns across the full codebase would catch many Category C findings with minimal cost.

3. **Dead infrastructure accumulates across phases.** Each phase builds scaffolding for its scope without auditing whether existing scaffolding from prior phases was ever connected. No phase has "audit unused interfaces/fields" in scope.

4. **No periodic full-codebase review.** 55% of findings were simply never in scope for any per-phase review. The per-phase model is efficient but leaves a long tail. A periodic full-codebase sweep (every N phases or at milestone boundaries) is necessary to catch accumulated debt.

5. **Error handling and context propagation are under-detected by spec-scoped reviews.** These require understanding call chains, not just individual file changes. The per-phase spec focuses on "does this function behave correctly?" not "does this function forward context and propagate errors correctly?"

### Industry comparison

Direct benchmarking against other AI code review tools is not possible with current data (see Benchmark Research). The Martian Code Review Bench is the closest public benchmark but measures PR-scoped review — a fundamentally different task from full-codebase review against a failure mode taxonomy.

Available comparison points:

| Dimension | Industry standard (AI code reviewers) | Firebreak (observed) |
|-----------|--------------------------------------|---------------------|
| Architecture | Single-pass LLM reads diff | Detector/Challenger adversarial loop |
| False positive rate | High (anecdotally 30-60%) | 0% post-remediation review; 0-22% per-phase |
| Linter overlap | High (most tools flag same things linters catch) | 0% across all measurement points |
| Finding depth | Style, obvious bugs, linter-equivalent | Behavioral bugs, dead infrastructure, test integrity, cross-package consistency |
| Scope | PR diff | Per-phase (spec-scoped) or full-codebase (checklist-scoped) |
| Evidence requirement | Comment with suggestion | Challenger demands code-path evidence before promotion |
| Supervisor bypass cost | N/A | 32 findings missed including 3 behavioral bugs (measured) |

The zero linter overlap is the strongest structural differentiator. If an AI code reviewer mostly finds things linters already catch, its marginal value is near zero. The Detector/Challenger pipeline finds a different class of issue entirely — behavioral bugs, semantic drift, dead infrastructure, test integrity gaps — that no linter or single-pass reviewer detects.

The supervisor bypass incident provides a controlled comparison: same codebase, same review scope, adversarial verification vs. single-pass scan. The single-pass scan missed 53% of findings (32 of 60), including all 3 behavioral bugs. This is the cost of skipping adversarial verification.

## Before/After: Remediation Impact on Finding Character

The brownfield project was reviewed twice with the same Detector/Challenger pipeline: once before remediation (driving the remediation plan) and once after 7 phases of remediation. The codebase grew 44% (from ~59K to ~85K lines) during remediation as new infrastructure was added.

### Finding category shift

| Category | Pre-remediation | Post-remediation |
|----------|----------------|-----------------|
| Security vulnerabilities | 5 (2 critical: arbitrary file read/write) | 0 |
| Concurrency crashes | 4 (race conditions, double-close, unsynchronized writes) | 0 |
| Disconnected interfaces | 6 (core feature's interfaces had incompatible signatures) | 0 |
| Dead architecture paths | 9 (major subsystems returning empty strings, production types only usable in tests) | 8 (unused worker pools, unimplemented interfaces — smaller scope) |
| Behavioral bugs | ~5 (core features non-functional) | 3 (non-crash, non-security — silent data gaps) |
| Test integrity | ~50 (tests exercising dead code, wrong mock wiring, non-enforcing assertions) | 9 (stale comments, empty gate tests, advisory assertions) |
| Code duplication | ~10 | ~15 |
| Bare literals / magic numbers | ~15 | ~15 |

The critical categories — security, concurrency, disconnected interfaces — went to zero. Behavioral bugs shifted from "core features don't work" to "silent data gaps in edge cases." Test integrity improved from ~50 issues (test suite provided no regression protection) to 9 issues (lower severity: stale comments, missing assertions in specific areas). Structural debt (duplication, bare literals) held steady; these were explicitly not targeted by any remediation phase.

### What this shows

The remediation moved the codebase from **architecturally broken** (security holes, crash-causing races, core feature non-functional) to **needs cleanup** (structural debt, some dead infrastructure, minor behavioral gaps). These are fundamentally different quality tiers.

The finding density also shifted. Pre-remediation: ~140 findings across ~59K lines (2.4 findings/KLOC). Post-remediation: 60 findings across ~85K lines (0.7 findings/KLOC). This comparison is directionally correct but not perfectly controlled — the reviews had different scopes and the codebase grew substantially. The category shift is more meaningful than the raw density numbers.

Notably, code added during remediation (new search infrastructure, scoring decorators, test harnesses) is structurally cleaner than the older code it sits alongside. Most post-remediation findings are concentrated in packages that predate the pipeline, while packages created during remediation came back with fewer or zero findings. This suggests the pipeline raises the quality bar for new code, not just patches existing code.

### Caveats

**Duplication increased** from ~10 to ~15 instances. The codebase grew 44%, so some increase is expected, but the pipeline didn't reduce existing duplication either. Each agent generates correct code independently without extracting shared logic — the GitClear "collapse in refactoring activity" pattern.

**6 findings were caused by remediation itself** (10% introduction rate). 4 of those 6 are test-integrity issues — stale comments on now-fixed bugs, empty gate tests, placeholder tests never filled in. The pipeline fixes production code effectively but introduces low-grade test debt.

**Bare literals and magic numbers held steady** (~15 before, ~15 after). When phases centralized constants in one package, they verified adoption within their target scope but didn't grep all consumers codebase-wide. This is a known blind spot of spec-scoped reviews (see Category C analysis above).

**The pre-remediation review drove the remediation plan**, making the two reviews not fully independent. The post-remediation review was designed as a follow-up, not a blind re-assessment. A fully independent review by a different team or tool would be a stronger comparison.

## Self-Improvement Proposals from Post-Remediation Review

The post-remediation review's retrospective was analyzed by 8 improvement analysts, producing 43 proposals (after deduplication) targeting 8 Firebreak assets. These proposals address both the specific blind spots revealed by the review and a broader gap: the pipeline's detection scope is shaped by its AI failure mode taxonomy, creating a blind spot for "normal engineering issues" that any competent reviewer would catch regardless of whether the code was AI-generated.

### Key theme: expanding detection scope beyond AI-specific failure modes

The AI failure mode taxonomy catches how AI code specifically fails (semantic drift, dead infrastructure, test integrity decay, copy-paste duplication). But the post-remediation review also found standard engineering issues — context propagation bugs, string-based error classification, sentinel value confusion, goroutine lifecycle management — that aren't in the taxonomy because they're not AI-specific. 33 of 60 findings (55%) were in code that was never in scope for any phase's review. Many of these would be caught by a broader detection scope that includes standard engineering review concerns alongside AI-specific ones.

The proposals below address this by expanding both the failure mode checklist and the structural detection targets to cover general engineering concerns. The Challenger's adversarial filtering prevents this broader scope from flooding the pipeline with noise.

### Detector agent (`fbk-code-review-detector.md`) — 3 proposals

| # | Change | Observation |
|---|--------|-------------|
| 1 | **Remove Bash from tools; delete project-native tool discovery section.** Analysis agents should be read-only per authoring rules. | A linter permission prompt blocked detector agents invisibly in the remote-control UI. Zero findings came from linter output. Enforces read-only at the tool level. |
| 2 | **Add severity signal to sighting output.** New field: `behavioral-bug`, `dead-infrastructure`, `fragile`, `debt`. | The retrospective tiered 60 findings into 4 severity levels post-hoc. Without severity signaling, a critical silent behavioral bug looks identical to a hand-rolled sort nit. |
| 3 | **Add cross-cutting pattern label to sightings.** Short label linking related sightings across review units. | 7 cross-cutting patterns were manually derived after all units completed. Detectors had no linking metadata to support automated consolidation. |

### Challenger agent (`fbk-code-review-challenger.md`) — 4 proposals

| # | Change | Observation |
|---|--------|-------------|
| 4 | **Add severity tier classification to verified findings.** Tiers 1-4 matching detector severity. | Severity assignment shapes remediation priority. Without it, triage requires re-reading every finding. |
| 5 | **Add "adjacent observation" channel.** Replace flat "do not generate new sightings" with: note related issues as adjacent observations in verification output; orchestrator decides whether to promote. | 0% rejection rate suggests challengers found related issues but had no sanctioned channel to report them. Prevents information loss while preserving scope discipline. |
| 6 | **Add cross-reference caller tracing for semantic-drift sightings.** Trace at least one caller to confirm drift has behavioral impact. | Category boundary between semantic-drift and dead infrastructure was ambiguous for several findings. Caller tracing prevents mislabeled categories leading to wrong fix strategies. |
| 7 | **Add `verified-pending-execution` status for test-integrity sightings requiring test execution.** State what command the orchestrator should run. | Stale "currently fails" comments required running tests to verify. The Challenger has no execution tools. Closes the verification gap without adding execution capabilities to the Challenger. |

### Code review skill (`fbk-code-review/SKILL.md`) — 7 proposals

| # | Change | Observation |
|---|--------|-------------|
| 8 | **Add parallel Detector spawning instruction for broad-scope reviews.** | The review used 8 parallel detectors. The skill doesn't specify parallel vs sequential. Sequential processing would multiply wall-clock time by the number of units. |
| 9 | **Add stuck-agent recovery instruction.** Check for permission prompts or other blockers before assuming failure. | Permission prompts blocked agents invisibly. No recovery strategy existed. The supervisor's workaround (performing its own scan) bypassed adversarial verification and missed 32 findings. |
| 10 | **Add cross-unit pattern deduplication and naming instruction.** After all units complete, group findings under named cross-cutting patterns. | Cross-cutting patterns were the most analytically valuable part of the retrospective but nothing instructed producing them. |
| 11 | **Add selective Challenger allocation guidance.** Prioritize units with high sighting counts or semantic-drift findings over structural-only units. | Only 2 of 8 units received Challengers. 0% rejection rate on clear-cut structural findings validates selective allocation. Note: this trades thoroughness for efficiency — the supervisor bypass incident shows the cost of skipping verification. |
| 12 | **Add comparative analysis instruction for follow-up reviews.** Finding category shift, what remediation fixed, what remains, severity tiering with effort estimates. | The before/after comparison was the most valuable retrospective section. Nothing instructed producing it. Future follow-up reviews would miss the severity trajectory analysis. |
| 13 | **Inject `quality-detection.md` reference into Detector spawn instructions.** | The skill's Agent Team section omits the reference. The orchestrator must cross-reference the code review guide to discover structural detection targets. Structural-target detections produced 13 attributed findings. |
| 14 | **Add detection source tagging reminder to Detector spawn instructions.** | Detection-source breakdown was the primary signal for improvement analysis. Without tagging, the self-improvement pipeline has no data to work with. |

### Code review guide (`code-review-guide.md`) — 6 proposals

| # | Change | Observation |
|---|--------|-------------|
| 15 | **Add dead/disconnected infrastructure check to Detector instructions.** Code constructed, wired, or declared but never invoked in any production path. | 8 findings of dead infrastructure. Existing detection targets don't cover "constructed but never called." Worker pools started but never used, interfaces declared but never implemented, config fields declared but ignored. |
| 16 | **Add explicit nit exclusion instruction.** Count nits separately; include in retrospective but exclude from verified findings list. | Nit/finding separation was implicit convention, not explicit instruction. |
| 17 | **Add structural-target sub-categorization to retrospective fields.** Sub-categorize by which target triggered the sighting (caller re-implementation, multi-responsibility, ambient state, etc.). | Sub-categories revealed which targets are most productive. Enables calibration of detection effort. |
| 18 | **Add origin guidance for codebase-wide reviews.** Default to `pre-existing`; do not use `introduced` when there is no change set. | The guide assumes PR/diff context. Full-codebase reviews have no diff boundary for origin attribution. |
| 19 | **Add `quality-detection.md` reference to no-spec source-of-truth section.** | The source-of-truth decision point mentions only the failure mode checklist, not structural targets. An agent reading only that section could skip structural targets entirely. |
| 20 | **Add comparative analysis as optional retrospective field.** Finding category shift, what remediation fixed, what remains, severity tier breakdown. | Codifies the most analytically valuable output of the review as a repeatable format. |

### Quality detection targets (`quality-detection.md`) — 4 proposals

These expand the detection scope beyond AI-specific patterns to standard engineering review concerns.

| # | Change | Observation |
|---|--------|-------------|
| 21 | **Add "Dead infrastructure" detection target.** Code constructed, initialized, or declared but never invoked in production paths. | 8 findings — the most common single-category finding type. None of the existing 6 targets cover this shape. |
| 22 | **Add "Semantic drift" detection target.** Code where documented/named meaning diverges from actual behavior. | Produced 2 of 3 highest-severity behavioral bugs. Comments promising behavior the code doesn't implement, field names implying semantics the code ignores. |
| 23 | **Add "Silent error and context discard" detection target.** Functions that discard caller context or silently swallow errors. | 5 findings. Context bypass prevents graceful shutdown and deadline propagation. Standard Go review concern, not currently in detection scope. |
| 24 | **Add "String-based type discrimination" detection target.** Code classifying values by string content when typed mechanism exists in the same project. | 14 call sites using string matching on error messages despite a typed error package in the project. Code looks structurally clean; fragility is invisible without explicit targeting. |

### AI failure modes checklist (`ai-failure-modes.md`) — 7 proposals

These expand the Detector's primary source of truth to cover standard engineering concerns alongside AI-specific failure modes.

| # | Change | Observation |
|---|--------|-------------|
| 25 | **Expand "magic numbers" to "bare literals"** (include string property keys, not just numeric literals). | 23+ findings involve string bare literals. Current item covers only numeric literals. String bare literals were the largest subcategory. |
| 26 | **Add item: Dead infrastructure** (constructed but never wired). | 8 findings. Current item #3 only covers dead middleware. Broader shape: dead interfaces, dead fields, dead pools, dead config paths. |
| 27 | **Expand "test name contradictions" to "non-enforcing tests"** (empty gate tests, advisory assertions, unconditional skips). | 4 findings from subtler forms the current item misses. More findings came from these forms than from name-mismatch. |
| 28 | **Add item: Comment-code drift.** Comments describing behavior the code doesn't implement, or stale temporal claims ("currently fails" on passing tests). | 4 findings. Stale comments mislead future agents into wrong assumptions about code behavior. |
| 29 | **Add item: Zero-value sentinel ambiguity.** Zero value used as sentinel "use default" but is also a valid domain value. | Produced a Tier 1 behavioral bug: temperature 0.0 (greedy decoding) silently treated as "unset." None of the existing items catch this class. |
| 30 | **Add item: Context bypass** (using `context.Background()` where caller context should be forwarded). | 3 findings. Prevents graceful shutdown and deadline propagation. Go-specific failure mode not covered by existing items. |
| 31 | **Add item: String-based error classification.** String matching on error messages instead of typed errors. | 14 call sites in the brownfield project. Fragile pattern not covered by any existing item. |

### Existing code review reference (`existing-code-review.md`) — 6 proposals

| # | Change | Observation |
|---|--------|-------------|
| 32 | **Add dual-path verification instruction.** When code has bulk path (rebuild/sync) and incremental path (per-event), verify both populate the same state. | The review's most critical bug: the bulk path worked correctly but the incremental path silently dropped data. Non-obvious verification target; agents won't check unless directed. |
| 33 | **Add sentinel value confusion instruction.** Verify guard conditions distinguish "unset/use-default" from "explicitly set to zero." | Produced a Tier 1 behavioral bug from a guard checking `< 0` when 0.0 was a valid explicit value. Well-known trap not in current instructions. |
| 34 | **Add test-production string alignment instruction.** Verify that test `strings.Contains` assertions reference values that actually exist in the production source they claim to test. | Tests asserting on phantom strings provide no behavioral coverage while appearing to pass. |
| 35 | **Add string-based error classification instruction.** Flag `strings.Contains(err.Error(), ...)` when typed errors exist in the same project. | Same concern as proposals 24/31, applied at the detection instruction level. |
| 36 | **Add dead infrastructure detection instruction.** Verify interfaces, pools, config fields have at least one production caller. | Same concern as proposals 21/26, applied at the detection instruction level. |
| 37 | **Add severity tiering to "When Only Structural Issues Surface" section.** Present behavioral bugs (Tier 1) first; don't bury them in flat structural lists. | Without severity ordering, critical findings are visually indistinguishable from debt findings. |

### Test reviewer agent (`fbk-test-reviewer.md`) — 6 proposals

These address the pipeline's blind spot for test-integrity issues in its own output. 4 of 6 remediation-caused findings were test-integrity issues that the per-phase test reviewer didn't catch.

| # | Change | Observation |
|---|--------|-------------|
| 38 | **Add Tier 1 criterion: Stale failure annotations on passing tests.** Flag comments like "currently fails" on tests that now pass. | Two instances survived two review cycles. No current criterion detects comment-vs-behavior mismatch in tests. |
| 39 | **Add Tier 1 criterion: Empty gate tests** (zero assertions). | Two instances. Current criteria catch error-absence-only assertions but not zero assertions. |
| 40 | **Add Tier 1 criterion: Advisory assertions** (logging output instead of failing output for behavioral checks). | Tests that appear to verify behavior but use non-failing output, so the test passes regardless of the assertion result. |
| 41 | **Add checkpoint check: Unconditionally skipped tests with behavioral names.** | Three instances. Skip directives are a different evasion mechanism than weakened assertions. Tests that claim coverage via their names but skip unconditionally. |
| 42 | **Add checkpoint check: Test assertions referencing values absent from production code.** | Tests asserting on strings that don't exist in the code they claim to test. Same concern as proposal 34, applied at the test reviewer level. |
| 43 | **Add checkpoint check: Build-tag consistency for infrastructure-dependent tests.** | Tests requiring external infrastructure (HTTP servers, databases) that run under default test execution without appropriate build tags. |

### Assessment

The proposals fall into three tiers of impact:

**Highest impact — expanding detection scope (proposals 21-31, 32-37):** These close the gap between AI-specific failure mode detection and general engineering review. The post-remediation review's 33 out-of-scope findings (55%) are predominantly standard engineering issues that the current taxonomy doesn't target. Adding dead infrastructure, semantic drift, context bypass, sentinel confusion, and string-based dispatch to the detection scope would catch many of these without requiring additional review passes.

**High impact — severity and structure (proposals 2-5, 10, 12, 37):** Severity tiering, cross-cutting pattern grouping, and comparative analysis transform the review output from a flat findings list into actionable intelligence. The adjacent observation channel (proposal 5) addresses information loss at the Challenger boundary.

**Moderate impact — operational improvements (proposals 1, 8-9, 11, 13-14, 16-20, 38-43):** Process fixes (stuck-agent recovery, parallel spawning, detection tagging), guide clarifications (nit exclusion, origin guidance for codebase reviews), and test reviewer expansions. Individually small; collectively they reduce friction and close minor detection gaps.
