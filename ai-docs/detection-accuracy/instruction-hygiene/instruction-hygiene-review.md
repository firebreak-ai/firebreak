Perspectives: Architecture, Quality, Pragmatism

# instruction-hygiene — Spec Review

## Architectural Soundness

### R-01: 6 existing tests will break — spec only identifies 1 test file
**Severity: blocking**

`test-detection-scope.sh` tests 15-19 assert heuristic keywords in `existing-code-review.md` — all 5 fail after removal. `test-code-review-guide-extensions.sh` test 3 asserts "dead infrastructure" in `code-review-guide.md` — fails after subsection removal. The spec's "Existing tests impacted" section mentions only `test-code-review-guide-extensions.sh` with vague language. Must enumerate all 6 test failures with explicit instructions per test.

### R-02: code-review-guide.md has two sections that will contradict the changes
**Severity: important**

Orchestration Protocol (lines 93-101) describes step 1 without the new ordering — diverges from rewritten SKILL.md step 1. Source of Truth Handling (lines 110-112) says "use ai-failure-modes.md, supplement with quality-detection.md" — contradicts the new unconditional scope. Both are injected into agents. The spec must either update these sections or declare SKILL.md as authoritative with code-review-guide.md non-normative for orchestration.

### R-03: Missing integration seam — SKILL.md steps vs code-review-guide.md Orchestration Protocol
**Severity: important**

The spec declares 4 integration seams but misses: SKILL.md steps 1/3 also correspond to code-review-guide.md's Orchestration Protocol section. The rewrite creates an ordering divergence. Declare as 5th seam.

### R-04: Context bypass redundancy not addressed
**Severity: important**

Trace report identifies context bypass as redundant (ai-failure-modes.md item 10 + quality-detection.md "Silent error and context discard"). Spec claims "6 redundant definitions" but doesn't address this one. Either fix the count or add dedup.

## Over-engineering / Pragmatism

### R-05: Dedup approach — consider deletion over summary-with-reference
**Severity: important**

Builder argues for full deletion of items 7 and 11 from ai-failure-modes.md since quality-detection.md is always co-injected. Research says instruction count matters more than token count — removing 2 items (13→11) beats shortening 2 items (13→13). Counter: self-containment principle. But these docs are never loaded independently in the Detector flow.

### R-06: Conversational review path may lose detection heuristics
**Severity: important**

`existing-code-review.md` is loaded for standalone conversational reviews. After removing 6 heuristic sections, the conversational reviewer loses those detection guides. The spec doesn't verify that the conversational path loads `quality-detection.md`. Need to check or add a reference.

### R-07: Acknowledge instruction count still exceeds threshold
**Severity: important**

Combined post-change: ai-failure-modes.md (14 items) + quality-detection.md (14 sections) = 28 detection instructions, still 1.4x the ~20 reliable threshold. Spec should explicitly frame this as incremental improvement, with detector-decomposition as the structural fix.

### R-08: Testing strategy over-engineered for markdown text edits
**Severity: important**

Shell tests that grep for specific strings in markdown break on rewording. Builder recommends keeping only AC-10 (no target lost) and UV steps for the rest. Guardian found AC-07 isn't automatable and AC-08 has no test at all.

## Testing Strategy and Impact

### R-09: AC-08 (token reduction) has no test
**Severity: important**

No shell test or UV step covers per-Detector token volume reduction. Either add word-count proxy test or explicitly mark as verified-by-inspection.

### R-10: AC-10 detection target names not enumerated
**Severity: important**

Test says "grep for each detection target name" but doesn't list them. Implementer must derive the list, risking omissions. Enumerate the exact grep strings.

### R-11: UV-9 success criteria too vague
**Severity: important**

"Significant drops" is undefined. Baseline only gives total and major counts, not category breakdowns. Define concrete threshold and complete baseline.

## Test Strategy Review

**Test strategy review: FAIL** — 11 defects found by the independent test reviewer.

### TR-01: AC-03 sole absence assertion (Criterion 1 violation)
**Severity: blocking**
Test verifies old conditional string is absent but no positive assertion verifies replacement text is present. Add: verify "Apply these detection targets to all code reviews" exists.

### TR-02: AC-06 single grep for two required instructions (Criterion 1 violation)
**Severity: blocking**
One grep for "pattern label" cannot distinguish whether both Challenger instructions (preserve + correction) are present. Add second assertion for correction instruction.

### TR-03: AC-01/AC-02 negative-only "does not contain" clauses (Criterion 1 advisory)
**Severity: important**
The "does not contain full definition" clauses add no regression value. Drop from test descriptions.

### TR-04: AC-04 removal side missing string-based error classification
**Severity: blocking**
Removal test lists 5 sections but spec removes 6. "String-based error classification" absent from the proposed absence check.

### TR-05: AC-07 no test for "no contradicting meta-instruction"
**Severity: important**
Half of AC-07 is untested.

### TR-06: AC-08 no test exists
**Severity: blocking**
Unmitigated AC coverage gap.

### TR-07: UV-3 standard format not verified
**Severity: important**
"Detect this when..." format requirement has no test. Add grep for "Detect this when" near promoted section names.

### TR-08: UV-8 count test doesn't verify item content
**Severity: important**
Count of 14 would pass even if original item 12 wasn't actually split. Add content check for items 12 and 13.

### TR-09: Seam 4 Detector end untested
**Severity: important**
Detector's pattern-label assignment instruction has no test. Add grep for "cross-cutting pattern label" in Detector definition.

### TR-10: test-code-review-guide-extensions.sh Test 3 breakage misidentified
**Severity: blocking**
Spec says check "existing-code-review.md content" but the actual failing test asserts on code-review-guide.md content.

### TR-11: test-detection-scope.sh Tests 15-19 not acknowledged
**Severity: blocking**
Five tests will break. Not mentioned anywhere in the spec.

## Threat Model Determination

**Security-relevant characteristics**: No data touched, no trust boundaries crossed, no new entry points, no auth/access control changes. Changes are to instruction documents (markdown files) used by the code review pipeline internally.

**Decision**: No. No new trust boundaries, no data handling changes, no external interaction. Changes are to internal instruction documents only.

## Testing

### New tests needed
Covered in spec testing strategy — 12 shell tests covering AC-01 through AC-13. Reviewed and corrected by council (simplified from content-matching to structural tests). See TR-01 through TR-11 for specific corrections applied.

### Existing tests impacted
8 tests identified and enumerated with specific actions. See R-01 resolution. Tests span test-detection-scope.sh (tests 1, 15-19), test-code-review-guide-extensions.sh (test 3), and test-code-review-structural.sh (test 23).

### Test infrastructure changes
None — existing shell test infrastructure is sufficient.

## Resolution Status

All blocking and important findings have been addressed through spec revisions:

| Finding | Status | Resolution |
|---------|--------|------------|
| R-01 (6 tests break) | **Resolved** | All 8 impacted tests enumerated with specific actions |
| R-02 (code-review-guide.md contradictions) | **Resolved** | Added change 11: align Orchestration Protocol + Source of Truth Handling (AC-13) |
| R-03 (missing integration seam) | **Resolved** | Added 5th seam to declaration |
| R-04 (context bypass redundancy) | **Resolved** | Added change: dedup and split context bypass / silent error discard (AC-11) |
| R-05 (deletion vs summary) | **Resolved** | Kept summaries — ai-failure-modes.md has consumers beyond the Detector (orchestrator in conversational mode) where quality-detection.md may not be co-loaded. Added change to ensure quality-detection.md IS loaded in conversational path (AC-12) |
| R-06 (conversational path loses heuristics) | **Resolved** | Fixed by AC-12 — conversational path now explicitly loads quality-detection.md |
| R-07 (count still exceeds threshold) | **Resolved** | Added explicit acknowledgment in Goals section linking to detector-decomposition |
| R-08 (testing over-engineered) | **Resolved** | Simplified to structural tests; content correctness via UV steps |
| R-09/TR-06 (AC-08 no test) | **Resolved** | AC-08 rewritten as verified-by-inspection; token reduction is consequence of structural changes |
| R-10 (AC-10 names not enumerated) | **Resolved** | Full detection target grep list added to test description |
| R-11 (UV-9 too vague) | **Resolved** | Concrete baseline, threshold (>25% drop), and 2-run protocol defined |
| TR-01 (AC-03 absence-only) | **Resolved** | Added positive assertion for replacement text |
| TR-02 (AC-06 single grep) | **Resolved** | Added second assertion for correction instruction |
| TR-03 (AC-01/02 negative clauses) | **Resolved** | Dropped content-matching tests; structural tests only |
| TR-04 (AC-04 missing 6th section) | **Resolved** | All 6 sections listed in removal check |
| TR-05 (AC-07 meta-instruction half) | **Resolved** | Changed to structural shell test on SKILL.md step definitions |
| TR-07 (UV-3 format not verified) | **Resolved** | AC-04 test includes "Detect this when" format check |
| TR-08 (UV-8 count without content) | **Resolved** | AC-09 test checks item 12/13 content keywords |
| TR-09 (seam 4 Detector end) | **Resolved** | AC-05 test also checks "cross-cutting pattern label" in Detector definition |
| TR-10 (Test 3 misidentified) | **Resolved** | Correctly identified as code-review-guide.md assertion |
| TR-11 (tests 15-19 not acknowledged) | **Resolved** | All 5 tests enumerated with actions |

**Threat model**: Not needed. No trust boundaries, no data handling, no external interaction.

## Original Summary (pre-resolution)

| Category | Blocking | Important | Informational |
|----------|----------|-----------|---------------|
| Architecture | 1 | 3 | 0 |
| Pragmatism | 0 | 4 | 0 |
| Testing | 0 | 3 | 0 |
| Test Strategy Review | 6 | 5 | 0 |
| **Total** | **7** | **15** | **0** |

All findings resolved. Spec is ready for task breakdown.
