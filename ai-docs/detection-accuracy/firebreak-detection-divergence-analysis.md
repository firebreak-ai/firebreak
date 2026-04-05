# Firebreak Detection Divergence Analysis

**Context**: Firebreak was run against a TypeScript personal AI agent project ("Project B"). The maintainer independently filed 24 non-feature-request issues using their own AI review process. Firebreak matched 6/24. This analysis traces every hit and miss to specific methodology documents.

**Methodology documents analyzed**:
- `ai-failure-modes.md` — 13-item AI failure mode checklist
- `quality-detection.md` — 11 structural detection targets
- `code-review-guide.md` — behavioral comparison methodology
- `existing-code-review.md` — conversational review flow
- `code-review-detector.md` — detector agent definition
- `code-review-challenger.md` — challenger agent definition

---

## Classification Summary

Of the 18 issues Firebreak missed:

| Category | Count | Issues |
|----------|-------|--------|
| **Methodology gaps** (checklist genuinely doesn't cover) | 4 | #25, #4, #12, #3, #9 |
| **Execution gaps** (methodology covers it, detector missed it) | 14 | #32, #30, #22, #20, #19, #17, #16, #15, #14, #13, #11, #10, #8 |

**The ratio is striking: 78% of misses are execution gaps, not methodology gaps.** The checklist and structural targets already cover most of what was missed — the detectors just didn't apply them consistently.

---

## Methodology Gaps (4 genuine gaps)

| Gap | Missed Issues | Proposed Detection Target |
|-----|--------------|--------------------------|
| Unbounded growth (memory or storage) | #25 (bloom), #4 (notification_log) | "Flag long-lived data structures and persistent tables that grow monotonically with no eviction, rotation, TTL, or size cap." |
| Migration/DDL idempotency | #12 | "Flag schema migrations and one-time initialization code that lacks guards against re-execution." |
| Transaction atomicity for batch writes | #3 | "Flag loops performing multiple independent write operations where partial completion leaves inconsistent state." |
| Intra-function logical redundancy | #9 | "Flag conditional checks within a single execution path that are fully subsumed by earlier checks in the same path." |

---

## Execution Gaps (14 misses the methodology should have caught)

### Pattern: Inconsistent cross-file application

The detector found an instance of a pattern in one location but missed the same pattern elsewhere:

| What was found | What was missed | Shared methodology item |
|---------------|-----------------|------------------------|
| XML injection in install.sh | HTML injection in Telegram messages (#22, #10) | Behavioral comparison: "describe what the code does, compare to what it should do" |
| chatId=0 sentinel, classifier sentinel | undefined property access (#11) | Checklist item 9: zero-value sentinel ambiguity |
| Vacuous test assertions | Missing test scenarios (#15, #14) | Checklist items 4/6: non-enforcing tests |
| lockdownBot docstring inversion | resolveProvider never returns null (#17), scoreAndRoute returns stale data (#8) | quality-detection.md: semantic drift |
| Test re-implements handler logic | Handler duplicates another handler (#32), utility duplication (#19) | quality-detection.md: caller re-implementation |

**Root cause**: Once the detector finds one instance of a pattern, it appears to move on rather than searching the full codebase for other instances. `code-review-guide.md` line 98 instructs "grep the same file and package for all instances" but this applies to **fixing**, not detection. No parallel instruction exists for detection.

### Pattern: Specific checklist items applied selectively

| Checklist item | Applied to | Not applied to |
|---------------|-----------|---------------|
| String-based type discrimination | Comment-code drift variants | Exact string matching in intent parsing (#30), date-as-string comparison (#13) |
| Silent error and context discard | Discarded timer handles | Swallowed errors after retry (#16), unguarded critical calls (#20) |
| Mixed logic and side effects | Config reload mutations | scoreAndRoute returning stale pre-mutation data (#8) |

---

## Methodology Strengths (what the pipeline is specifically good at)

| Strength | Driving methodology | Why it works |
|----------|-------------------|-------------|
| Comment-code drift | Checklist item 8 + behavioral comparison | The "describe what code does, compare to source of truth" framing naturally surfaces doc/code discrepancies |
| Zero-value sentinel ambiguity | Checklist item 9 | Well-specified with concrete detection heuristic ("check for conditional branches that treat zero-like value as 'not provided'") |
| Non-enforcing tests | Checklist items 4+6 + caller re-implementation target | Strong net for test quality — catches both wrong assertions and tests that bypass production code |
| Ambient state / lifecycle | quality-detection.md: ambient state + silent context discard | Catches shared mutable state and detached lifecycle patterns |
| Dual-path state divergence | existing-code-review.md: dual-path verification | Distinctive instruction that caught Docker .env persistence gap |

**Why these succeed**: The checklist items that work best describe both the **pattern** AND the **detection heuristic** ("Check for X"). Items that only describe the pattern without a concrete "how to detect" instruction are applied more inconsistently.

---

## Key Insight

> The detector found 1-3 instances of most patterns but missed additional instances of the same pattern in other files. The methodology covers the class of issue, but the detector's file-by-file traversal doesn't systematically re-apply each checklist item to every file. A detection-phase instruction — "after identifying a pattern, search the full codebase for other instances" — would close several execution gaps.

This single change could have caught 5-6 of the 14 execution-gap misses (#22, #10, #19, #32, #11, #8).
