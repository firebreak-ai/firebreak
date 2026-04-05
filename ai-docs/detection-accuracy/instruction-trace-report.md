# Code Review Pipeline Instruction Trace Report

**Date**: 2026-04-04
**Analyst**: Opus agent (isolated context, no conversation history)
**Scope**: Full instruction set trace for Detector and Challenger agents in the Firebreak code review pipeline

## Key Numbers

| Metric | Detector | Challenger |
|--------|----------|------------|
| Instruction sources | 5 documents | 3 documents |
| Discrete instructions | ~63 | ~39 |
| Instruction tokens | ~3,950 | ~2,350 |
| Instruction:content ratio (small review) | ~1:1 | ~1:2 |
| Instruction:content ratio (large review) | ~1:5 | ~1:8 |

## Critical Issues Found

### 1. Scope Contradiction (ai-failure-modes.md vs orchestrator)
`ai-failure-modes.md` line 1 says: "Use this checklist when reviewing code **without specs**. When specs are available, use quality-detection.md instead."

But the orchestrator (SKILL.md line 40) injects BOTH documents unconditionally.

`quality-detection.md` line 1 says: "Apply these structural detection targets to **all code reviews**, whether or not the spec contains design constraints."

The Detector receives a conflicting scope signal about when the failure mode checklist applies.

### 2. Dead Infrastructure Defined in 4 Places
- `code-review-guide.md` line 17
- `ai-failure-modes.md` item 7
- `quality-detection.md` section
- `existing-code-review.md` lines 51-53

Three of these are in the Detector's context simultaneously with slightly different wording.

### 3. String-Based Classification Defined in 3 Places
- `ai-failure-modes.md` item 11
- `quality-detection.md` section
- `existing-code-review.md` lines 48-49

### 4. Detector Has No Nit Suppression Instruction
The Challenger is told to reject nits. The Detector has no instruction to avoid producing them. Every nit the Detector produces wastes a Challenger verification cycle.

### 5. Pattern Labels Have No Challenger Handling
Detector assigns cross-cutting pattern labels. Challenger has no instruction to preserve, validate, or carry them forward. Labels silently vanish during verification.

### 6. Three Detection Heuristics Trapped in Orchestrator-Only Doc
`existing-code-review.md` contains 3 unique detection patterns not present in any agent-facing document:
- Dual-path verification
- Test-production string alignment
- Dead code after field removal

These never reach Detector agents because existing-code-review.md is loaded by the orchestrator only, not injected into spawn prompts.

## Redundancies

| Concept | Defined in | Agent-facing copies |
|---------|-----------|-------------------|
| Dead infrastructure | code-review-guide, ai-failure-modes, quality-detection, existing-code-review | 3 |
| String-based error classification | ai-failure-modes, quality-detection, existing-code-review | 2 |
| Zero-value sentinel | ai-failure-modes, existing-code-review | 1 (existing-code-review not injected) |
| Context bypass | ai-failure-modes, quality-detection | 2 |
| Behavioral comparison methodology | code-review-guide, detector agent definition | 2 |
| "Describe in behavioral terms" | code-review-guide, detector agent definition | 2 |

## Attention Competition Analysis

**Detector context ordering:**
1. Agent system prompt — HIGH attention (beginning)
2. Orchestrator spawn instructions — HIGH attention
3. code-review-guide.md — MEDIUM attention (middle)
4. quality-detection.md — MEDIUM-LOW (middle)
5. ai-failure-modes.md — LOW attention (deep middle)
6. Linter output — VARIABLE
7. **Target code files — potentially LOW attention position**

**Critical**: The actual code to review may end up at the END of the prompt. Instructions that tell the Detector HOW to analyze are split across beginning and middle with redundancy consuming attention budget.

## Presentation Issues

| Issue | Location | Concern |
|-------|----------|---------|
| Preamble before first instruction | code-review-guide.md lines 4-5 | Methodology description before actionable instruction |
| Compound instruction | ai-failure-modes.md item 12 | Combines domain-inconsistent fixtures + mock permissiveness |
| Abstract detection heuristic | quality-detection.md "Composition opacity" | Requires proving a negative (no test exists) — expensive |
| Abstract detection heuristic | quality-detection.md "Multi-responsibility modules" | Requires hypothetical future-change reasoning |
| Abstract detection heuristic | quality-detection.md "Non-importable behaviors" | Requires reasoning about hypothetical test scenarios |

## Priority-Ordered Recommendations

| # | Change | Impact |
|---|--------|--------|
| 1 | Resolve ai-failure-modes.md scope contradiction — remove "only without specs" since orchestrator injects unconditionally | Eliminates direct contradiction in Detector instructions |
| 2 | Deduplicate dead infrastructure — canonicalize in quality-detection.md, reference from others | Removes ~200 tokens redundancy, eliminates 3 competing wordings |
| 3 | Add nit-avoidance instruction to Detector | Reduces wasted Challenger verification cycles |
| 4 | Add pattern-label handling to Challenger | Prevents silent label loss during verification |
| 5 | Deduplicate string-based classification | Removes ~150 tokens redundancy |
| 6 | Move 3 unique detection heuristics from existing-code-review.md to quality-detection.md | Makes dual-path verification, test-production string alignment, dead code after removal visible to agents |
| 7 | Split ai-failure-modes.md item 12 | Minor clarity improvement |
| 8 | Trim code-review-guide.md preamble | Minor attention savings |

## Cross-Agent Consistency

Generally consistent. Both reference same type/severity taxonomy. Challenger authorized to reclassify (by design). One gap: pattern labels are a Detector output with no Challenger handling.
