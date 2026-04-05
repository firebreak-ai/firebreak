# Pipeline Retrospective: Evaluation Round (Preliminary)

**Date**: 2026-04-04
**Scope**: Code review of 3 public repos (Project A: JS game, Project B: TS AI agent, Project C: Java+Angular budget app)
**Finding**: Agent instruction-following is the primary bottleneck, not methodology coverage

## Key Metrics

| Metric | Value |
|--------|-------|
| Total verified findings across 3 projects | 178 |
| Findings matching AI failure mode checklist | ~70% |
| Findings matching structural detection targets | ~25% |
| Findings from intent-alignment pass | 24 (13.5%) |
| Methodology gaps (genuine) | 4 classes of issue |
| Execution gaps (methodology covers it, detector missed it) | 14 instances on Project B alone |
| Execution gap ratio | 78% of misses |

## Observation 1: Findings track our checklist because that's what we told agents to find

The AI failure mode checklist is opinionated by design — it targets patterns specific to AI-generated code. This is a strength (focused detection) and a limitation (blind to general software engineering concerns). The 4 methodology gaps are all general engineering issues, not AI-specific:
- Unbounded data structure growth
- Migration/DDL idempotency
- Batch transaction atomicity
- Intra-function logical redundancy

## Observation 2: Agents don't reliably apply instructions they have

This is the critical finding. 78% of misses on Project B were issues the methodology already covers. The pattern:

**Cross-file pattern inconsistency**: Detector finds XML injection in install.sh but doesn't find HTML injection in Telegram messages — same class of issue, different file. Finds vacuous test assertions but doesn't find missing test scenarios. Finds one sentinel ambiguity but misses another.

The code-review-guide.md says "grep the same file and package for all instances" but only for the fix phase. No parallel instruction exists for detection. However, even if it did, the deeper problem is that agents apply checklist items selectively rather than systematically.

## Observation 3: The orchestrator exhibited the same behavior

The orchestrator (me, in conversation) skipped the intent-extraction phase entirely despite the skill instructions clearly specifying it. The user had to call it out. When eventually run, the intent pass produced 24 new findings — 7 major — that the checklist rounds missed entirely.

This is the same pattern at a different level: the instructions were present, the agent didn't follow them, and the gap was only caught by human oversight.

## Observation 4: The iterative loop works but has diminishing returns

Convergence was consistent across all 3 projects:

| Project | R1 Major | R2 Major | R3 Major | R4 Major |
|---------|----------|----------|----------|----------|
| Project A (JS game) | 13 | 10 | 1 | 0 |
| Project B (TS agent) | 9 | 3 | 1 | 0 |
| Project C (Java+Angular) | 15 | 4 | 1 | — |

R1 captures ~60-70% of major findings. R2 captures most of the rest. R3-R4 produce diminishing returns. The adversarial verification loop (Challenger) works well — rejection rates of 7-14% with evidence-based rejections and one R1 rejection overturned in R2.

## Observation 5: The R1 rejection overturn is significant

BackupService SQL injection was rejected in R1 because the Challenger incorrectly stated sanitizeForPath strips single quotes. R2's fresh detector re-examined the regex and the R2 Challenger confirmed the R1 rejection was wrong. This validates the multi-round approach but also shows that Challengers can make the same instruction-following errors as Detectors — the R1 Challenger read the regex and reported seeing a character that wasn't there.

## Observation 6: Intent-driven and checklist-driven reviews find different things

| Pass type | Character | Example findings |
|-----------|-----------|-----------------|
| Checklist-driven | Code-level bugs, dead code, security, structural patterns | SQL injection, vacuous tests, sentinel ambiguity, dead infrastructure |
| Intent-driven | Documentation drift, unimplemented features, business rule violations | Split doesn't delete original, tower health never implemented, token savings claims false |

The two approaches had almost zero overlap in what they found. Neither subsumes the other.

---

## Root Cause Analysis

### Confirmed by research and instruction trace

1. **Instruction overload (confirmed)**: Detectors receive ~63 discrete instructions from 5 documents at ~3,950 tokens. IFScale research shows standard Claude Sonnet exhibits linear compliance decay from instruction 1. Practical reliable threshold is ~20 instructions. We're at 3x.

2. **Instruction ordering is backwards (confirmed)**: We put instructions in the middle of the prompt (between agent system prompt and code files). Anthropic explicitly recommends data at top, instructions at bottom, with a measured 30% improvement. We're doing the opposite.

3. **Redundancy wastes instruction budget (confirmed)**: Dead infrastructure defined in 4 places, string-based classification in 3 places. Each redundant definition counts against the ~20-instruction reliable budget while adding no detection value.

4. **Scope contradiction (confirmed)**: ai-failure-modes.md says "only without specs" but the orchestrator injects it unconditionally alongside quality-detection.md. Detector receives conflicting scope signals.

5. **Context competition (confirmed)**: Cognitive load research shows linear degradation as task content grows relative to instructions. Code files are "distractor interference" from the instruction-following perspective.

6. **Satisficing after first match (confirmed)**: The "find one then move on" pattern is expected behavior when agents have 63 instructions and large code volumes. Finding one instance produces a plausible completion. Research recommends forced enumeration to prevent this.

7. **Three detection heuristics trapped in orchestrator-only doc (new finding)**: Dual-path verification, test-production string alignment, and dead code after field removal exist in existing-code-review.md but are never injected into agent spawn prompts. Agents never see them.

### Not confirmed / still hypothetical

- Whether the R1 Challenger's regex misread was attention-related or a hallucination
- Whether reasoning/thinking mode would materially improve our specific detection task
- Whether the instruction-to-content ratio or instruction count is the dominant factor in our case

---

## Improvement Proposals

### Proposal A: Two-Tier Detector Architecture

Split detection into two agent tiers per round, optimized for different detection goals.

**Tier 1: Focused detectors** (per-file or small module)
- 3-5 checklist items per agent
- Full file contents but minimal instructions
- Forced per-file, per-item enumeration ("no issues found" entries required)
- Targets: edge cases, null safety, error handling, specific pattern instances

**Tier 2: Cross-cutting detectors** (broader scope, lighter content)
- File summaries/signatures instead of full contents (exports, function names, types, call graphs)
- Architectural instructions: dual-path verification, caller re-implementation across modules, state flow, API contract mismatches
- Targets: cross-module interactions, composition opacity, state divergence

**Trade-offs**: More agents = more cost and coordination. Tier 2 depends on quality of file summaries. Overlap between tiers needs deduplication.

### Proposal B: Instruction Decomposition (Many Narrow Agents)

Instead of 3 detectors with 63 instructions each, spawn 8-12 detectors each with 3-5 related checklist items and the same file scope.

Example groupings:
- Agent 1: Bare literals + hardcoded coupling + string-based discrimination
- Agent 2: Dead infrastructure + dead conditional guards + middleware never connected
- Agent 3: Non-enforcing tests + test-integrity variants + composition opacity
- Agent 4: Zero-value sentinel + context bypass + silent error discard
- Agent 5: Comment-code drift + semantic drift
- Agent 6: Mixed logic/side effects + ambient state + non-importable behaviors
- Agent 7: Caller re-implementation + parallel collection coupling + multi-responsibility

**Trade-offs**: Higher agent count = higher cost. Each agent still scans all files but with a narrow detection mandate. Doesn't solve cross-module detection on its own.

### Proposal C: Prompt Restructuring (Cheapest Change)

Keep current agent topology but fix the instruction presentation:

1. **Reverse prompt order**: Code files first (top), instructions last (bottom). 30% measured improvement.
2. **Deduplicate**: Remove 6 identified redundancies (~350 tokens, ~8 instruction slots freed).
3. **Resolve scope contradiction**: Remove "only without specs" from ai-failure-modes.md.
4. **Move trapped heuristics**: Promote dual-path verification, test-production string alignment, dead code after removal from existing-code-review.md to quality-detection.md.
5. **Add nit suppression to Detector**: Reduce wasted Challenger cycles.
6. **Add pattern-label handling to Challenger**: Prevent silent label loss.

**Trade-offs**: Lowest cost, lowest disruption. Doesn't address the fundamental instruction count problem (~63 → ~55 after dedup, still well above ~20 threshold). Quick win that buys marginal improvement.

### Proposal D: Forced Enumeration

Require each detector to produce structured output accounting for every file against every assigned checklist item:

```
File: src/pipeline.ts
  - Bare literals: No issues found
  - Dead infrastructure: S-01 (bloom filter pool declared, never used)
  - Silent error discard: S-02 (catch block swallows with log only)
```

**Trade-offs**: Significantly increases output token usage. May slow detection. But directly prevents the "find one then move on" satisficing pattern. Works with any agent topology.

### Proposal E: Self-Verification Pass

After the initial detection pass, run a second pass where the detector reviews its own output:

> "Before you finish, verify that you have applied every checklist item to every file. For any checklist item with zero findings across all files, re-examine the files specifically for that pattern."

**Trade-offs**: Doubles the detection phase time. But targets the specific failure mode (silent omission of checklist items) with minimal architectural change.

### Proposal F: Intent Pass as Standard Phase

Formalize intent extraction as a mandatory first phase rather than an optional/skippable step:

1. Extract testable behavioral claims from project docs
2. Present intent register to orchestrator for scope confirmation
3. Run intent-alignment detection as a separate agent wave alongside (not after) checklist detection

**Trade-offs**: Adds time to every review. But the evaluation showed intent findings are qualitatively different from checklist findings — neither subsumes the other. Making it mandatory prevents the orchestrator from skipping it.

### Proposal G: Randomized Checklist Ordering

Randomize the order of checklist items across detection rounds. Items at the beginning get more attention (primacy effect); randomizing ensures no item is consistently disadvantaged.

**Trade-offs**: Trivial to implement. Small marginal improvement. Only helps with position-dependent attention, not instruction count.

---

## Compatibility Matrix

| | A (Two-Tier) | B (Narrow Agents) | C (Prompt Fix) | D (Forced Enum) | E (Self-Verify) | F (Intent Phase) | G (Random Order) |
|---|---|---|---|---|---|---|---|
| **A** | — | Partially exclusive (both reshape topology) | Complementary | Complementary | Complementary | Complementary | Complementary |
| **B** | Partially exclusive | — | Complementary | Complementary | Less needed (narrow scope reduces satisficing) | Complementary | Less needed (fewer items per agent) |
| **C** | Complementary | Complementary | — | Complementary | Complementary | Complementary | Complementary |
| **D** | Complementary | Complementary | Complementary | — | Partially redundant (both target omissions) | Complementary | Complementary |
| **E** | Complementary | Less needed | Complementary | Partially redundant | — | Complementary | Complementary |
| **F** | Complementary | Complementary | Complementary | Complementary | Complementary | — | Complementary |
| **G** | Complementary | Less needed | Complementary | Complementary | Complementary | Complementary | — |

**Key relationships:**
- **A and B are partially exclusive** — both reshape the detector topology. Pick one approach to agent decomposition.
- **D and E are partially redundant** — both target the "silent omission" problem. D prevents it structurally; E catches it after the fact. D is more reliable but costlier.
- **C is complementary with everything** — it's a low-cost structural fix that improves any configuration.
- **F is complementary with everything** — it's an orthogonal detection dimension.
- **B makes E and G less needed** — narrow agents with 3-5 instructions have less satisficing and less position bias.

---

## Recommended Implementation Path

### Phase 1: Quick wins (Proposal C + G)
- Prompt restructuring, deduplication, scope fix, trapped heuristic promotion
- Randomized checklist ordering
- Lowest cost, no architectural change, immediate improvement
- Estimated impact: 10-20% improvement in instruction compliance

### Phase 2: Structural improvement (Proposal B + D + F)
- Decompose to narrow-mandate agents (3-5 items each)
- Add forced enumeration to each narrow agent
- Formalize intent extraction as mandatory phase
- Higher cost, significant architectural change, addresses root causes
- Estimated impact: 40-60% improvement in detection coverage

### Phase 3: Architectural evolution (Proposal A)
- Two-tier detector architecture (focused + cross-cutting)
- Requires Phase 2's narrow-agent infrastructure as the Tier 1 foundation
- Adds Tier 2 cross-cutting agents with summarized file context
- Estimated impact: catches the cross-module interaction class that narrow agents miss

---

## Supporting Documents

- `instruction-trace-report.md` — Full trace of instruction sets per agent type
- `agent-instruction-alignment-research.md` — External research on instruction following
- `firebreak-detection-divergence-analysis.md` — Divergence analysis vs Project B maintainer's findings
