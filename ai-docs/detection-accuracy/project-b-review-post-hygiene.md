# Project B Code Review — Post-Instruction-Hygiene (v0.3.5)

**Date**: 2026-04-05
**Scope**: Full codebase review of Project B (TS AI agent, ~35 source files, 25 test files, 8 scripts)
**Pipeline version**: Post instruction-hygiene (v0.3.5, commit `24b8e5a`)
**Purpose**: Evaluate detection accuracy improvement from v0.3.5 instruction-hygiene changes against the same repo reviewed pre-hygiene

## Retrospective Fields

### Sighting Counts

| Round | Sightings | Verified | Rejected | Weakened | Cannot Verify |
|-------|-----------|----------|----------|----------|---------------|
| R1 | 103 | 86 | 10 | 7 | 0 |
| R2 | 48 | 27 | 12 | 0 | 9 |
| R3 | 17 | 6 | 9 (7 dup) | 0 | 0 |
| R4 | 2 | 0 | 2 (1 dup) | 0 | 0 |
| **Total** | **170** | **119** | **33** | **7** | **9** |

Rejection breakdown:
- False claims (code doesn't do what sighting says): 7
- Duplicates of prior-round findings: 10
- Nits (no behavioral/maintainability impact): 4
- Unreachable code paths: 3
- Insufficient detail to verify: 9

Detection source breakdown (R1 only — R2+ don't reliably tag):
- `checklist`: ~55% of sightings
- `structural-target`: ~35% of sightings
- `linter`: 0% (no linter available)

Structural-type finding sub-categorization:
- Bare literals / policy values: ~20 findings
- Dead infrastructure / dead code: 5
- Duplication (code, logic, stripHtml): 8
- Composition opacity: 3
- Parallel collection coupling: 2

### Verified Findings by Severity

| Severity | R1 | R2 | R3 | Total |
|----------|----|----|-----|-------|
| Critical | 2 | 0 | 0 | 1* |
| Major | 22 | 6 | 3 | 32** |
| Minor | 54 | 20 | 3 | 77 |
| Info | 8 | 1 | 0 | 9 |
| **Total** | **86** | **27** | **6** | **119** |

*F-NOT-08 (first-contact takeover) reclassified from critical to major in R3 — code is unreachable dead infrastructure
**Includes the reclassified F-NOT-08

### Verified Findings by Type

| Type | Count | % |
|------|-------|---|
| Structural | 48 | 40% |
| Behavioral | 30 | 25% |
| Test-integrity | 23 | 19% |
| Fragile | 18 | 15% |

### Verified Findings by Unit

| Unit | Critical | Major | Minor | Info | Total |
|------|----------|-------|-------|------|-------|
| Core (pipeline, scheduler, trigger, events, index) | 0 | 6 | 11 | 1 | 18 |
| Config/DB | 0 | 3 | 7 | 2 | 12 |
| AI module | 0 | 2 | 10 | 2 | 14 |
| Notify (listener, router, telegram) | 0 | 3 | 9 | 2 | 14 |
| Sources | 0 | 3 | 12 | 3 | 18 |
| Util | 0 | 3 | 4 | 0 | 7 |
| Scripts | 1 | 3 | 8 | 1 | 13 |
| Tests | 0 | 9 | 14 | 0 | 23 |
| **Total** | **1** | **32** | **75** | **11** | **119** |

### Critical Finding

**F-SCR-01** (install.sh, XML injection): Unescaped .env values interpolated verbatim into launchd plist XML at `install.sh:57-59`. The inline comment stripper at line 53 (`%%\#*`) truncates any token value containing `#`. Malformed XML silently breaks service installation; crafted values enable XML injection.

### Top Major Findings

| ID | Unit | Description |
|----|------|-------------|
| F-AI-01 | AI | Prefilter claims to skip non-matching articles but sends all to AI |
| F-AI-02 | AI | Classifier failure injects synthetic scores indistinguishable from real |
| F-CORE-06 | Core | Parallel scheduler/scheduleFeed interval maps diverge on rescheduleFeed |
| F-NOT-08 | Notify | First-contact auto-registration (dead code — listener requires chatId to start) |
| F-NOT-06 | Notify | handleCommand bypasses mutex/ack guards |
| F-UTL-04 | Util | fetchJson no error handling on JSON.parse |
| F-UTL-05 | Util | Invalid LOG_LEVEL silently suppresses all logs below error |
| F2-NOT-06 | Notify | AI topic strings HTML-injected into Telegram alerts unescaped |
| F2-SRC-05 | Sources | OPML file:// URLs pass through to fetch — local file read |
| F3-03 | Core | Claude CLI subprocess has no timeout — hangs pipeline forever |
| F3-04 | Core | scoreAndRoute vs triggerOnce are parallel pipeline re-implementations |

### Verification Rounds

4 rounds to convergence: R1 (86) → R2 (27) → R3 (6) → R4 (0).

The decay curve matches the pattern from the preliminary evaluation: R1 captures ~72% of findings, R2 captures ~23%, R3 captures ~5%, R4 converges. This is consistent across both pre- and post-hygiene runs.

### Scope Assessment

- Source files reviewed: 35 (all production code under src/)
- Script files reviewed: 8 (all under scripts/)
- Test files reviewed: 25 (all under tests/)
- Total files: 68
- Estimated lines of code: ~6,000 (source) + ~4,000 (tests)
- Agent invocations: 8 R1 detectors + 8 R1 challengers + 4 R2 detectors + 4 R2 challengers + 2 R3 detectors + 2 R3 challengers + 1 R4 detector + 1 R4 challenger = 30 agent invocations

### Context Health

- Rounds: 4 (converged before hard cap of 5)
- Sightings-per-round trend: 103 → 48 → 17 → 2 (consistent decay)
- Rejection rate per round: 16% → 44% → 65% → 100% (increasing as expected — later rounds find more duplicates)
- R2 had 9 "cannot verify" sightings due to orchestrator error (insufficient detail passed to challenger). This is a process gap, not an agent capability issue.
- No round hit the hard cap

### Tool Usage

- Project-native linters: None available (no eslint config, no TS linter installed)
- Agent tools used: Read, Grep, Glob (standard Detector/Challenger toolset)
- No test execution (review-only, no fixes applied)

### Finding Quality

- False positive rate (user-dismissed findings): TBD — pending user review of findings
- False negative signals: TBD — pending comparison to repo filed issues
- Nit rejection rate: 4 nits excluded across all rounds (low — detectors followed nit exclusion instruction)
- Challenger overturns: 1 severity escalation (F-NOT-08 escalated to critical in R1, then reclassified to major/structural in R3 when dead-code evidence emerged). This multi-round correction validates the iterative approach.
- Adjacent observations: 8 logged by challengers (not promoted to findings but provide context)

---

## Comparison to Pre-Instruction-Hygiene Review

### Detection Yield

| Metric | Pre-hygiene (original) | Post-hygiene (this review) | Delta |
|--------|----------------------|---------------------------|-------|
| R1 total findings | ~14 | 86 | +514% |
| R1 major findings | ~9 | 22 | +144% |
| Total findings (all rounds) | ~50 | 119 | +138% |
| Rounds to converge | 4 | 4 | Same |
| Test-integrity findings | ~3 | 23 | +667% |
| Security-relevant findings | ~2 | 6 | +200% |
| Critical findings | 0 | 1 | New |

### What Changed

The v0.3.5 instruction-hygiene release made the following changes that are likely responsible for the improved yield:

1. **Content-first prompt ordering** (Anthropic-recommended, 30% measured improvement): Detectors receive code content first, instructions last. This keeps detection targets in the recency window where compliance is highest.

2. **quality-detection.md loaded in all paths**: The structural detection targets (composition opacity, caller re-implementation, parallel collection coupling, dual-path verification, etc.) were previously trapped in an orchestrator-only document. Post-hygiene, Detectors receive them directly. This accounts for the majority of the ~35% structural-target sightings.

3. **Deduplication of redundant definitions**: Dead infrastructure, string-based classification, and context bypass had 3-4 redundant definitions each. Consolidation freed instruction budget for other checklist items.

4. **Scope contradiction resolved**: ai-failure-modes.md previously said "only without specs" but the orchestrator injected unconditionally. Fixed to unconditional scope — all detection targets now apply to every review.

5. **Nit suppression for Detectors**: Explicit nit exclusion instruction kept Detectors focused on substantive issues. Only 4 nits reached challengers across 170 sightings.

6. **Forced per-file enumeration**: Requiring Detectors to explicitly state "no issues found" per file reduced satisficing after first match.

### What Didn't Change

- Instruction count remains ~62 per Detector (3x the reliable threshold)
- No forced enumeration output schema (Detectors chose their own format)
- No narrow-mandate agent decomposition
- No intent extraction phase
- No cross-cutting Tier 2 agents

### Caveats

1. **Different review scope**: The original review focused on specific modules; this review covered the full codebase (all 68 files). Direct comparison overstates the improvement because the original review had narrower scope.

2. **No intent extraction**: This review used checklist + structural targets only. The original review's intent-extraction pass produced 24 additional findings (7 major). Adding intent extraction to the post-hygiene pipeline would likely increase yield further.

3. **R2 data loss**: 9 AI/Notify sightings in R2 couldn't be verified due to orchestrator error (insufficient detail passed to challenger). These are uncounted potential findings.

4. **Repo issues are an independent baseline, not ground truth**: The filed issues on the Project B repo were produced by a different agent with different detection strengths. Both pipelines have false negatives, and either may have false positives the other doesn't. The overlap metric measures alignment with an independent reviewer, not correctness. See `three-way-comparison.md` Section 5 for detailed analysis.

---

## Comparison to Post-Intent-Fix Review (Fresh Session)

A third review was run after the intent extraction fix was applied to the pipeline instructions. This review used the updated SKILL.md with the Intent Extraction section, Review Report section, and all cross-file references. It ran in a fresh session against the same Project B codebase.

**Report**: `fbk-code-review-2026-04-05-1200.md` (in project working directory)

### Three-Review Comparison

| Metric | Pre-hygiene (v0.3.4) | Post-hygiene, no intent (v0.3.5) | Post-intent-fix (v0.3.5+intent) |
|--------|---------------------|----------------------------------|----------------------------------|
| Total findings | 53 | 119 | 42 |
| Critical | 0 | 1 | 2 |
| Major | 13 | 32 | 20 |
| Minor | 32 + 7 intent | 77 | 20 |
| Info | 1 | 9 | 0 |
| Major+ ratio | 25% | 29% | 52% |
| Rounds to converge | 4 | 4 | 5 |
| Intent-sourced findings | 7 (separate pass) | 0 (skipped) | 12 (29% of total) |
| Rejection rate | 7.8% | ~16% | 19% |

### Token Usage (Fresh Review)

| Model | Input | Output | Cache Write | Cache Read |
|-------|-------|--------|-------------|------------|
| Opus 4 | 5K | 40K | 1M | 16.8M |
| Sonnet 4 | 19K | 88K | 1.6M | 24.4M |

### What the intent-fix review changed

**1. Intent extraction drives the highest-severity findings.** Both criticals (F-01 auto-reg unreachable, F-03 prefilter no-op) are intent-sourced. These were major/behavioral from the checklist in our review, but the intent register provides the framing "this is a documented core feature that doesn't work" — justifying critical severity. The prefilter no-op is a structural checklist finding but a critical intent finding because the README claims 30-60% token savings that don't happen.

**2. Higher signal density, fewer structural findings.** 42 findings vs 119 — roughly 1/3 the count. But 52% are major+ vs our 29%. The fresh review produced fewer bare-literal/structural findings and more behavioral+test-integrity. Intent extraction focuses detection on "does this feature work as documented?" rather than "does this code have structural issues?"

**3. The config race was verified — our Challenger was wrong.** F-35 in the fresh review: "addFeed/removeFeed read-modify-write collision... Concurrent /subscribe calls can lose each other's writes." Our Challenger rejected this twice (S-CFG-06, S2-CFG-01) with "single-threaded JS means no interleaving." The fresh review's Challenger verified it by tracing the async boundary: two Telegram commands arriving in quick succession create two async chains, each doing load→mutate→save. This resolves the open investigation item on repo issue #24 — the Challenger false negative is confirmed.

**4. New finding type: "tests protecting bug" (F-11).** The prefilter tests assert that non-matching articles go to AI — they validate the broken behavior. If someone fixes the prefilter, these tests fail. This is qualitatively different from "test doesn't assert anything." The intent register enables this detection class: "this test is correct according to the code but wrong according to the documented intent."

**5. Findings our review missed entirely:**
- F-02: Hot-reload doesn't update scheduler interval closures
- F-06: Bloom rotation gated on modulo-1000 (up to 999 items of FPR overshoot)
- F-10: demo.ts re-implements pipeline normalization (caller re-implementation)
- F-11: Tests protecting the prefilter bug
- F-33: Auto-registration .env write failure leaves ephemeral state
- F-36: FreshRSS token cache key excludes password (credential rotation stale for 23h)
- F-37: /unsubscribe primary `subscribedBy` path has zero test coverage
- F-42: Discovery timer first-run delay (t+25h not t+1h as comment states)

**6. Findings our review found that the fresh review didn't:**
The fresh review's 42 findings are a strict subset in terms of finding *types* — it found representatives of every pattern class we found (bare literals, dead infrastructure, string dispatch, HTML injection, mutex bypass, test-integrity). The difference is volume: our review found ~20 bare literal instances individually; the fresh review found 3-4 representative instances. The fresh review is more concise without being less thorough on major+ issues.

### Interpretation

The intent extraction fix didn't just add intent-sourced findings — it changed the character of the entire review. The intent register acts as a severity amplifier: issues that are "structural debt" from a checklist perspective become "documented feature that doesn't work" from an intent perspective, justifying higher severity. It also acts as a detection filter: with limited instruction budget, detectors guided by intent claims focus on behavioral alignment rather than exhaustively enumerating structural patterns.

The reduced total count (42 vs 119) is not a regression — it reflects higher focus. The 119-finding review spent significant detection budget on bare literals and minor structural issues. The 42-finding review spent that budget on behavioral and test-integrity issues that matter more.

### Intent Extraction Analysis: The Instruction Budget Trade-Off

**The instruction budget is zero-sum.** Adding ~25 intent claims + a Mermaid diagram to a Detector already at 3x the reliable instruction threshold (~62 instructions) means structural detection items get displaced. The data shows this clearly:

| What increased | What decreased |
|---|---|
| Intent-sourced findings: 0 → 12 | Total sightings: 170 → 52 |
| Critical findings: 1 → 2 | Minor/structural findings: 77 → 20 |
| Major+ ratio: 29% → 52% | Bare literal findings: ~20 → ~4 |
| New finding types (tests-protecting-bug) | Pattern enumeration depth |

Detectors reallocated attention from exhaustive structural enumeration to behavioral alignment with documented intent. They didn't get worse at structural detection — they got more selective, spending budget on intent-driven findings instead. This is a better allocation: 2 criticals + 20 majors beats 0 criticals + 32 majors.

**This confirms the v0.4.0 detector decomposition case.** With narrow-mandate agents (3-5 items each), intent claims would go to a dedicated intent path tracer — not compete with checklist items in the same Detector context. Decomposition would yield the intent-driven criticals AND the exhaustive structural enumeration. The current architecture forces an either/or trade-off that decomposition eliminates.

### What Intent Extraction Uniquely Enables

**Severity calibration.** The prefilter no-op is the same code defect in both reviews. From the checklist: "code doesn't match its comment" (minor/structural, comment-code drift). From the intent register: "a core documented feature claiming 30-60% token savings is not implemented" (critical/behavioral). The intent register provides the "how much does this matter?" frame that the checklist can't.

**Detection classes the checklist can't produce.** F-11 (tests protecting the bug) is impossible without intent. A test asserting "non-matching articles go to AI" is correct according to the code. Only the intent claim "pre-filter skips irrelevant articles before AI" reveals the test is validating broken behavior. No checklist item catches "test is correct but wrong."

**Challenger accuracy improvement.** The config race (F-35) was verified by the fresh review's Challenger but rejected twice by ours. Possible mechanism: the intent register claims "feeds.json is hot-reloadable," establishing concurrent config mutations as an expected usage pattern. With that context, the Challenger may have been more skeptical of the "single-threaded means safe" argument.

### Open Questions on Intent Dynamics

1. **Is the reduced structural coverage a problem in practice?** The fresh review found 4 bare-literal instances instead of 20. If a remediation spec only needs representative examples to justify "extract constants," 4 is sufficient. If the spec needs an exhaustive list for implementation, 4 is not.

2. **Would sequential passes (intent-only then checklist-only) recover both?** The pre-hygiene review ran intent as a separate pass and got 7 additional findings on top of 46 checklist findings. The fresh review ran them concurrently and got 42 total. Is concurrent worse than sequential for total coverage?

3. **How much of the reduction is session variance vs. intent displacement?** Different sessions produce different detection even with identical instructions. Some of the 119-vs-42 gap may be normal variance, not intent-caused displacement.

4. **Does the intent register improve Challenger accuracy systematically or incidentally?** The F-35 config race verification is one data point. A controlled comparison (same sightings, Challenger with vs without intent register) would isolate the effect.

All four questions resolve structurally under v0.4.0 detector decomposition — dedicated agents don't compete for the same budget, so the trade-off disappears.

### Mermaid Diagram Effectiveness

The fresh review's intent register includes a `graph TD` Mermaid diagram (~60 lines, 4 subgraphs, ~18 labeled edges). Assessment against two goals:

**Token budgeting — diagram is more expensive than prose.** The diagram consumes ~1,200 tokens. The equivalent module relationships expressed as prose would be ~200-300 tokens (8-10 sentences). The diagram is ~4x more expensive in raw tokens. It encodes relationships as structured edges (`PreFilter -->|relevant| AI`) rather than compound sentences, which may be easier for an LLM to use as a lookup table during detection — but all 12 intent-sourced findings in the fresh review cite specific prose claims (e.g., "Source: Intent claim 8"), not the diagram. No finding references the diagram as its detection source.

**User checkpoint — diagram provides real value.** The user opens the review report in VSCode, sees the rendered diagram, and can visually verify module relationships faster than scanning 25 prose claims. Spatial layout surfaces structural assumptions (e.g., "the diagram shows PreFilter sending to AI, but there should be a skip path") that prose buries in sequential text. The diagram earns its cost at the user checkpoint, not in the Detector's context window.

**Potential refinement (not yet actioned — gathering more data).** Include the diagram in the review report file for the user checkpoint but exclude it from the Detector spawn prompt. Prose claims are what Detectors actually cite. This would recover ~900 tokens of instruction budget per Detector spawn — meaningful at 3x the reliable threshold. However, this is a single data point from one review. The diagram may provide detection value that doesn't show up in source citations (e.g., helping the Detector build a mental model of module relationships before reading code). More reviews needed before changing how diagrams are consumed.

---

## Cross-Cutting Patterns

Patterns that appeared across multiple units, assigned during detection and confirmed during verification:

| Pattern | Occurrences | Units |
|---------|-------------|-------|
| `bare-policy-literal` | ~20 | All units |
| `string-error-dispatch` | 3 | Core, Config/DB |
| `silent-null-discard` | 4 | Config (CRUD + hot-reload) |
| `filtered-array-unused` | 2 | Core (pipeline + trigger) |
| `bloom-tracking-gap` | 2 | Core (L0-blocked, null title/URL) |
| `striphtml-triplication` | 3 | Sources (rss, rsshub, freshrss) |
| `lang-default-scatter` | 3 | Sources (rss, v2ex, types) |
| `unvalidated-ai-string` | 2 | Notify (subreddit URL, Telegram HTML) |
| `caller-reimplementation` | 3 | Tests (rss-e2e) |
| `handleCommand-mutex-bypass` | 3 | Notify (direct call, buzz sub-dispatch) |
| `invocation-order-coupling` | 2 | Tests (pipeline-integration) |
| `dual-pipeline-divergence` | 1 | Core (scoreAndRoute vs triggerOnce) |

---

## Open Items

- [x] Compare findings against Project B repo filed issues — see `three-way-comparison.md`
- [x] Investigate Challenger false negative on #24 (config race) — **confirmed**: fresh review F-35 verified the race; our Challenger was wrong
- [x] Run intent-extraction phase — **completed**: fresh review with intent-fix pipeline produced 12 intent-sourced findings (29% of total), both criticals intent-sourced
- [ ] Re-run R2 AI/Notify detection with full detail passthrough to recover 9 lost sightings
- [ ] Investigate whether F-AI-10 (trends double Date parse) shares root cause with repo issue #13
- [ ] Analyze bloom rotation logic against repo issue #25 (unbounded growth)
- [ ] Sample 10-15 findings with no repo counterpart for manual verification (precision check)
- [ ] User review of findings for false positive rate
- [ ] Run three-way comparison of fresh review (42 findings) against repo issues — does intent extraction improve ground-truth overlap?
- [ ] Update pipeline-retrospective-preliminary.md with post-hygiene + post-intent data
- [ ] Update `three-way-comparison.md` with fresh review data (third column)
