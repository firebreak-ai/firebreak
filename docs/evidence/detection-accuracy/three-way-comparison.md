# Three-Way Comparison: Pre-Hygiene vs Post-Hygiene vs Repo Issues

**Date**: 2026-04-04
**Purpose**: Determine detection accuracy of both review passes against the 32 filed repo issues as ground truth

## Scope

- **Pre-hygiene review**: 53 findings (F-001 through F-046 + INTENT-F-01 through INTENT-F-07)
- **Post-hygiene review**: 119 findings across 8 units (Core, Config/DB, AI, Notify, Sources, Util, Scripts, Tests)
- **Repo issues**: 31 filed issues (#2-#32), 3 excluded from matching (#7 tracking, #28 feature request, #29 feature request) = **28 matchable issues**

Matching criteria: a finding counts as a match only if it identifies the same behavioral defect described by the repo issue, not merely the same file or general area. Partial matches are noted.

---

## Section 1: Repo Issue Coverage

Each of the 28 matchable repo issues is listed below with its closest findings from each review. Issues are grouped by coverage outcome.

### Exact match — found by BOTH reviews

**#31 — SUBSCRIBE_SIGNALS regex defined but never used — signal prefixes not stripped**
- Pre-hygiene: F-021 (Intent fast path includes verb in keywords)
- Post-hygiene: F-AI (subscribe signal leak in intent fast-path)
- Match quality: **Exact.** Both reviews identify that the intent fast path passes signal verbs (follow, track, etc.) through as part of the keyword instead of stripping them.

### Partial match — found by BOTH reviews

**#5 — Add integration tests for pipeline, classifier, and notifier**
- Pre-hygiene: F-012 (router test asserts expect(true).toBe(true)), F-009 (/import validation test doesn't call handler), F-029 (SimHash pipeline integration test makes no assertion on near-duplicate)
- Post-hygiene: F-TEST (router tautological assertion), F-TEST (pipeline-integration near-dup unasserted), plus ~20 additional test-integrity findings covering hollow tests, missing assertions, spy-never-asserted patterns
- Match quality: **Partial.** Both reviews found weak/missing test coverage, but neither directly says "these modules have zero test coverage." The repo issue is about missing integration tests; the reviews found that existing tests are hollow. Post-hygiene coverage is substantially broader.

**#21 — SSRF via /summary — no URL scheme or private IP restriction**
- Pre-hygiene: F-030 (SSRF protection blocks all 172.x instead of RFC1918)
- Post-hygiene: F-NOT (SSRF over-block 172.x), F2-SRC-05 (OPML file:// URLs pass through to fetch — local file read)
- Match quality: **Partial.** Both reviews identify SSRF-related implementation flaws, but the repo issue is about missing SSRF protection on /summary specifically. F-030 criticizes the existing SSRF check's range, not the missing entry point coverage. The OPML file:// finding is a distinct SSRF vector.

**#24 — Config read-modify-write race in concurrent mutations**
- Pre-hygiene: F-042 (non-atomic config hot-reload)
- Post-hygiene: F-CFG (hot-reload silent discard before getConfig)
- Match quality: **Partial.** Both reviews identify config atomicity problems, but the repo issue is about concurrent write races in addFeed/removeFeed/addInterest (load-modify-save), while both findings focus on the hot-reload path. Related root cause, different manifestation.

### Partial match — found ONLY by post-hygiene

**#8 — scoreAndRoute returns stale scored array without summaries**
- Pre-hygiene: None.
- Post-hygiene: F3-04 (dual pipeline divergence — scoreAndRoute vs triggerOnce are parallel re-implementations). Also related: F-CORE (worthSummary unused — 2 paths), F-CORE (zero-value sentinel pre-filtered vs AI-unscored).
- Match quality: **Weak partial.** The dual pipeline divergence finding identifies structural problems in scoreAndRoute but doesn't specifically call out the stale return value.

**#10 — Telegram sendBreakingAlert does not escape URL in href attribute**
- Pre-hygiene: None (found XML injection in install.sh but missed HTML injection in Telegram).
- Post-hygiene: F2-NOT-06 (HTML injection in Telegram alerts via AI topics)
- Match quality: **Partial.** Same vulnerability class (HTML injection in Telegram), different specific vector (AI topic strings vs URL in href).

**#12 — DB migration ALTER TABLE has no idempotency guard**
- Pre-hygiene: None.
- Post-hygiene: F-CFG (string-based duplicate-column detection)
- Match quality: **Weak partial.** The post-hygiene finding identifies a quality concern in the migration code (string matching for column detection) but doesn't identify the TOCTOU race condition that #12 describes.

**#15 — trends.test.ts does not verify Infinity spike ratio behavior**
- Pre-hygiene: None.
- Post-hygiene: F-SCR (Infinity spikeRatio serializes to null), F-TEST (trends zero-assertion body — two instances)
- Match quality: **Partial.** Post-hygiene found both the Infinity serialization bug and that trends tests have empty assertion bodies. The zero-assertion finding is structurally close to #15's concern.

**#18 — No integration test for scoreAndRoute + summarizer + router pipeline**
- Pre-hygiene: F-012 (router test asserts expect(true).toBe(true)) — identifies a weak router test but not missing integration coverage.
- Post-hygiene: F-TEST (router composition opacity)
- Match quality: **Partial.** The composition opacity finding identifies that router tests don't verify the integration between components, which is #18's concern framed differently.

**#22 — HTML injection in Telegram ack messages for /search, /subscribe, /summary**
- Pre-hygiene: None.
- Post-hygiene: F2-NOT-06 (AI topic strings HTML-injected into Telegram alerts unescaped)
- Match quality: **Partial.** Same vulnerability class (HTML injection in Telegram messages), different injection source (AI topics vs user input in ack messages).

**#32 — /buzz discover duplicates registered /discover handler**
- Pre-hygiene: None.
- Post-hygiene: F-NOT (path-dependent ack behavior), F-NOT (buzz→import dual path bypasses mutex)
- Match quality: **Partial.** Post-hygiene identified /buzz dual-path patterns, which is structurally related to the handler duplication. Not the exact behavioral match (degraded UI, missing auto feature).

### Not matched — found by NEITHER review

**#2 — Sequential feed processing blocks on slow feeds**
- Nearest pre-hygiene: F-008 (sequential per-item mark-read in FreshRSS) — different code, different problem (mark-read API calls vs scheduler feed groups).
- Neither review identified the sequential await in `runFeedGroup()`.

**#3 — No batch transaction for article inserts**
- Nearest pre-hygiene: F-044 (cleanupOldArticles two DELETEs without transaction) — same pattern class, different operation.
- Neither review identified the missing transaction on the insert loop.

**#4 — notification_log table grows unbounded**
- Neither review flagged unbounded table growth. Methodology gap identified in prior divergence analysis.

**#6 — Add per-feed error tracking with circuit breaker**
- Enhancement request for resilience pattern. Outside both reviews' detection scope.

**#9 — trends.ts duplicate detection for new topics is partially redundant**
- Nearest post-hygiene: F-AI (trends named constants disconnected from cutoffs) — about bare literals, not the redundant loop logic.
- Neither review identified the intra-function redundancy.

**#11 — summarizer fallback uses a.reason which may be undefined**
- Nearest: F-006/F-AI (classifier failure synthetic scores) — upstream problem (classifier), not the summarizer's use of reason.
- Neither review traced the fallback path to identify that internal strings leak into user-facing output.

**#13 — trends.ts string comparison for ISO date timestamps is fragile**
- Nearest post-hygiene: F-AI (double Date parse in loop) — about redundant parsing, not string comparison fragility.
- Neither review identified the fragile comparison.

**#14 — summarizer.test.ts missing test for AI returning non-array JSON**
- Nearest post-hygiene: F-TEST (summarizer hardcoded batch count) — about test rigidity, not missing scenarios.
- Neither review identified this specific missing test case.

**#16 — Telegram sendMessage silently swallows errors after all retries**
- Nearest pre-hygiene: F-038 (FreshRSS mark-read CSRF failure silently returns) — same pattern, different location.
- Nearest post-hygiene: F-NOT (duplicated retry in telegram) — structural retry issue, not the swallowed-error behavior.
- Neither review identified the no-throw-after-final-retry defect.

**#17 — resolveProvider never returns null — falls through to ollama**
- Nearest pre-hygiene: F-014 (dead resolveProvider import) — dead import, not the behavioral issue.
- Nearest post-hygiene: F-AI (dead providers Record map) — dead code in providers, not the unreachable null return.
- Neither review identified that the null guard in the caller is unreachable.

**#19 — Summarizer and classifier share identical JSON-stripping logic**
- Nearest: F-046/F-SRC (stripHtml triplicated) — different duplicated code (stripHtml in sources, not JSON-stripping in AI modules).
- Neither review identified this specific duplication.

**#20 — markNotified in router.ts not inside try-catch for breaking alerts**
- Nearest pre-hygiene: F-045 (markNotified per-ID updates without transaction) — about transaction atomicity, not error handling flow.
- Neither review identified the placement relative to sendBreakingAlert's silent failure.

**#23 — /unsubscribe does not remove AI-discovered Reddit feeds**
- Nearest pre-hygiene: INTENT-F-02 (/subscribe creates Reddit feeds as RSS) — about creation format, not unsubscribe cleanup.
- Neither review traced the subscribe-then-unsubscribe workflow to find orphaned feeds.

**#25 — Bloom filter grows unbounded during long-running process**
- Pre-hygiene found F-002 (bloom not updated on rollback); post-hygiene found F-UTL (bloom count inflation corrupts FPR). Both are bloom filter defects but neither identifies the core issue: no rotation or eviction for a long-running process.

**#26 — No input length validation on /buzz, /subscribe, /interests**
- Neither review checked for missing input length bounds.

**#27 — /filter accepts catch-all regex .* without validation**
- Neither review checked for overly permissive regex patterns.

**#30 — /buzz check incorrectly subscribes instead of fetching**
- Nearest post-hygiene: F-AI (subscribe signal leak in intent fast-path) — same module but different defect. #30 is about "check" not matching FETCH_SIGNALS; the finding is about SUBSCRIBE_SIGNALS not being tested.
- Neither review identified the specific FETCH_SIGNALS regex gap.

---

## Section 2: Three-Way Overlap Matrix

Issues #7 (tracking), #28 (feature request), and #29 (feature request) are excluded.

| Issue # | Issue Title (short) | Pre-hygiene? | Post-hygiene? | Match Quality |
|---------|-------------------|--------------|---------------|---------------|
| #2 | Sequential feed processing blocks | N | N | — |
| #3 | No batch transaction for inserts | N | N | — |
| #4 | notification_log grows unbounded | N | N | — |
| #5 | Add integration tests | Partial (F-009, F-012, F-029) | Partial (~23 test findings) | Both found hollow/weak tests but not the missing-coverage gap per se |
| #6 | Per-feed error tracking / circuit breaker | N | N | Enhancement — outside detection scope |
| #8 | scoreAndRoute returns stale array | N | Partial (F3-04 dual pipeline) | Weak — structural divergence noted, not the stale return value |
| #9 | trends.ts redundant duplicate detection | N | N | — |
| #10 | Telegram sendBreakingAlert URL unescaped | N | Partial (F2-NOT-06 HTML injection) | Same vulnerability class, different specific vector |
| #11 | summarizer fallback uses undefined reason | N | N | — |
| #12 | DB migration ALTER TABLE no idempotency | N | Partial (F-CFG string-based column detection) | Related code, different defect (quality vs race condition) |
| #13 | trends.ts fragile string date comparison | N | N | — |
| #14 | summarizer.test.ts missing non-array test | N | N | — |
| #15 | trends.test.ts no Infinity spike test | N | Partial (F-SCR Infinity→null, F-TEST trends zero-assertion) | Post-hygiene found Infinity serialization bug and hollow trends tests |
| #16 | sendMessage swallows errors after retries | N | N | F-NOT retry duplication is structural, not the swallowed-error behavior |
| #17 | resolveProvider never returns null | N | N | F-014 (dead import) and F-AI (dead providers map) are tangential |
| #18 | No scoreAndRoute integration test | N | Partial (F-TEST router composition opacity) | Post-hygiene identified composition not tested, same concern |
| #19 | Shared JSON-stripping logic duplicated | N | N | F-046/stripHtml is different duplicated code |
| #20 | markNotified not in try-catch | N | N | F-045 is about transactions, not error handling flow |
| #21 | SSRF via /summary | Partial (F-030 SSRF 172.x over-block) | Partial (F-NOT SSRF 172.x, F2-SRC-05 OPML file://) | Both found SSRF-related issues but not the /summary entry point |
| #22 | HTML injection in Telegram ack messages | N | Partial (F2-NOT-06 HTML injection via AI topics) | Same class, different injection source |
| #23 | /unsubscribe misses Reddit feeds | N | N | INTENT-F-02 is about creation, not removal |
| #24 | Config read-modify-write race | Partial (F-042 non-atomic hot-reload) | Partial (F-CFG hot-reload silent discard) | Both found config atomicity issues, different manifestation |
| #25 | Bloom filter grows unbounded | N | N | Both found bloom bugs (F-002 rollback, F-UTL count inflation) but not unbounded growth |
| #26 | No input length validation | N | N | — |
| #27 | /filter accepts catch-all regex | N | N | — |
| #30 | /buzz check subscribes instead of fetching | N | N | Different intent-parsing defect than signal leak |
| #31 | SUBSCRIBE_SIGNALS unused, prefixes not stripped | Y (F-021) | Y (F-AI subscribe signal leak) | **Exact match** — both reviews |
| #32 | /buzz discover duplicates /discover handler | N | Partial (F-NOT dual path, path-dependent ack) | Structural overlap, not exact behavioral match |

---

## Section 3: Coverage Metrics

**Matchable issues**: 28 (31 issues #2-#32, minus #7, #28, #29)

### Strict matching (exact behavioral match only)

| Metric | Count | Issues |
|--------|-------|--------|
| Pre-hygiene overlap | **1/28** (3.6%) | #31 |
| Post-hygiene overlap | **1/28** (3.6%) | #31 |
| Found by BOTH | 1 | #31 |
| Found ONLY by pre-hygiene | 0 | — |
| Found ONLY by post-hygiene | 0 | — |
| Found by NEITHER | 27 | All others |

### Lenient matching (includes partial matches where the finding addresses the same vulnerability class, code area, or closely related behavioral concern)

| Metric | Count | Issues |
|--------|-------|--------|
| Pre-hygiene overlap | **4/28** (14.3%) | #5, #21, #24, #31 |
| Post-hygiene overlap | **11/28** (39.3%) | #5, #8, #10, #12, #15, #18, #21, #22, #24, #31, #32 |
| Found by BOTH (at least partial) | 4 | #5, #21, #24, #31 |
| Found ONLY by pre-hygiene | 0 | — |
| Found ONLY by post-hygiene | 7 | #8, #10, #12, #15, #18, #22, #32 |
| Found by NEITHER | 17 | #2, #3, #4, #6, #9, #11, #13, #14, #16, #17, #19, #20, #23, #25, #26, #27, #30 |

### Summary

| Metric | Pre-hygiene | Post-hygiene |
|--------|-------------|--------------|
| Exact matches | 1 (3.6%) | 1 (3.6%) |
| Partial-or-better matches | 4 (14.3%) | 11 (39.3%) |
| Net gain (partial-or-better) | — | +7 issues |

---

## Section 4: What Changed

### New repo issue overlaps gained in post-hygiene

The post-hygiene review picked up partial matches on 7 issues that the pre-hygiene review missed entirely:

| Issue | Post-hygiene finding | Character |
|-------|---------------------|-----------|
| #8 (stale scoreAndRoute return) | Dual pipeline divergence (F3-04) | Structural — identified the parallel re-implementation but not the specific stale return |
| #10 (URL unescaped in Telegram) | HTML injection via AI topics (F2-NOT-06) | Security — same vulnerability class, different vector |
| #12 (migration idempotency) | String-based column detection (F-CFG) | Structural — identified code quality issue in the migration, not the race condition |
| #15 (missing Infinity test) | Infinity→null serialization + zero-assertion trends tests | Test-integrity + behavioral — found both the Infinity serialization bug and hollow trend tests |
| #18 (missing integration test) | Router composition opacity | Test-integrity — identified that composition isn't verified |
| #22 (HTML injection in ack) | HTML injection via AI topics | Security — same class, different entry point |
| #32 (/buzz discover duplication) | Dual path + path-dependent ack | Structural — identified the /buzz dual-path pattern |

Additionally, the post-hygiene review substantially deepened coverage on issues already partially matched by pre-hygiene:
- **#5** (missing integration tests): Pre-hygiene had 3 test-quality findings; post-hygiene produced 23 test-integrity findings, covering far more hollow tests and missing assertions.

### Repo issue overlaps lost

**None.** Every issue matched (exactly or partially) by the pre-hygiene review is also matched by the post-hygiene review. The sole exact match (#31 SUBSCRIBE_SIGNALS) appears in both.

### Character of new findings

The post-hygiene review's gains cluster into three categories:

1. **Test-integrity** (largest gain): The jump from ~3 to 23 test findings meant more hollow tests, missing assertions, and coverage gaps were surfaced. This creates partial overlap with issues #5, #15, and #18.

2. **Security** (moderate gain): HTML injection findings expanded from install.sh-only to Telegram messages, creating partial overlap with #10 and #22.

3. **Structural** (moderate gain): Dual-path divergence, composition opacity, and parallel re-implementation findings created partial overlap with #8, #12, and #32.

### What types of repo issues remain blind spots for BOTH reviews

The 17 issues found by neither review (even leniently) fall into distinct categories:

**Performance / scalability (3 issues: #2, #3, #4)**
Sequential processing, batch transactions, unbounded table growth. These are systems engineering concerns — neither review's checklist targets throughput, I/O patterns, or storage growth.

**Missing validation / input sanitization (3 issues: #26, #27, #30)**
Input length limits, regex validation, intent-parsing edge cases. The reviews check for injection but not for missing input bounds or keyword misrouting.

**Specific behavioral bugs (6 issues: #9, #11, #13, #16, #17, #20)**
Redundant loop logic, undefined property access in fallback, fragile string comparison, swallowed retry errors, unreachable null return, misplaced error handling. These require tracing specific execution paths through the code and reasoning about edge-case inputs. They are individually discoverable but fall through when a detector has 60+ instructions competing for attention.

**Feature/resilience gaps (2 issues: #6, #23)**
Circuit breaker pattern, orphaned feed cleanup on unsubscribe. These are design-level gaps that require understanding the intended user workflow end-to-end.

**Duplicated utility code (1 issue: #19)**
The reviews found stripHtml triplication but missed the JSON-stripping duplication — same pattern class, different instance.

**Unbounded data structure (1 issue: #25)**
Bloom filter growth. Both reviews found bloom filter bugs (rollback, count inflation) but neither identified the core architectural issue of no rotation/eviction.

**Missing test scenarios (1 issue: #14)**
Specific untested edge case (non-array JSON) in summarizer tests. (#15 gets a partial match from post-hygiene via Infinity serialization + zero-assertion findings, so is counted in the lenient overlap.)

### Key takeaway

The post-hygiene review nearly tripled partial coverage (14% to 39%) primarily through expanded test-integrity and security detection. However, exact behavioral matches barely changed — the improvement is in finding adjacent/related issues rather than the precise defects maintainers filed. The persistent blind spots (performance, input validation, specific path-tracing bugs) require fundamentally different detection strategies: performance profiling awareness, input-boundary checking, and deeper per-function path tracing.

---

## Section 5: Baseline Calibration — Repo Issues Are Not Ground Truth

The repo issues are an independent baseline for calibrating detection accuracy. They are not an oracle. The repo's issues were filed by a different agent with its own detection strengths and blind spots (documented in `firebreak-detection-divergence-analysis.md`). Both pipelines have false negatives, and either may have false positives the other doesn't.

### Areas where Firebreak may have the better read

**Challenger rejection of #24 (config race) may be correct.** The Challenger rejected S-CFG-06 twice with technically sound reasoning: synchronous `readFileSync`/`writeFileSync` in Bun's single-threaded event loop executes atomically within a single function call. Issue #24 may have been filed based on pattern intuition ("read-modify-write looks racey") without confirming the actual async scheduling behavior. Further analysis needed: construct a concrete interleaving scenario in Bun's event loop, or confirm the issue is about a different mechanism than the one our Challenger analyzed.

**Multi-round severity correction.** F-NOT-08 (first-contact takeover) was rated critical in R1, then R3 proved the code path is unreachable — the listener never starts without chatId. Our iterative approach produced a more accurate severity assessment than a single-pass review would. If the repo had filed this as a security issue, our reclassification to major/structural (dead code) would be the better read.

**119 findings with no corresponding repo issue.** The repo's agent missed: XML injection in install.sh (our sole critical), dual pipeline divergence (F3-04), Claude CLI subprocess no timeout (F3-03), OPML file:// SSRF (F2-SRC-05), 23 test-integrity findings, and dozens of structural issues. These are real issues the repo's review process didn't catch. Non-overlap does not mean non-issue.

**Rigorous Challenger rejections demonstrate calibration.** The bloom hash independence rejection (confirmed different primes), hexToSimhash double-prefix rejection (no production caller), JS single-thread atomicity analysis — these show the pipeline correctly *not* inflating findings. Precision is as valuable as recall.

### Areas where the repo issues may have the better read

**Specific path-tracing bugs** (#9, #11, #13, #16, #17, #20) require following a single value through a specific call chain — a detection style our broad multi-file behavioral comparison is structurally weak at. The planned v0.4.0 narrow-mandate detector decomposition directly targets this gap.

**Performance/scalability concerns** (#2, #3, #4, #25) are outside our checklist's scope entirely. These are systems engineering issues that require reasoning about throughput and storage growth over time, not behavioral comparison against intent.

**Missing input validation** (#26, #27, #30) represents a detection target class our checklist doesn't include. The checklist targets injection (what happens when bad input gets through) but not missing bounds (what input is accepted at all).

### Areas requiring further analysis

| Area | Question | How to resolve |
|------|----------|----------------|
| #24 config race | Is the Challenger's single-thread rejection correct, or does Bun's async scheduling create a real interleaving window? | Construct a minimal reproduction: two concurrent Telegram commands triggering addFeed simultaneously |
| R2 data loss (9 sightings) | Do any of the 9 unverified R2 AI/Notify sightings correspond to repo issues #16, #17, or #20? | Re-run R2 AI/Notify detection with full detail passthrough to Challenger |
| F-AI-10 vs #13 | Is the trends.ts double Date parse (weakened to info) related to the fragile string date comparison (#13)? | Read both the finding and the issue in detail to determine if they share a root cause |
| Repo issue #25 vs our bloom findings | Both reviews found bloom bugs but neither found unbounded growth. Is unbounded growth the real issue, or are the specific bugs (rollback, count inflation, tracking gap) the actionable problems? | Analyze bloom rotation logic to determine whether the documented two-generation rotation addresses #25, or whether the issue is about the rotation being insufficient |
| Post-hygiene unique findings | Are the 108 findings with no repo issue counterpart all real, or do some reflect overcounting from 8 parallel detectors? | Sample 10-15 findings with no repo match and verify code behavior manually |
