> **Note (2026-04-09):** Preliminary internal evaluation. Superseded by the Martian benchmark evaluation (50 PRs, consensus-judged) in `martian-benchmark/results/deviation_analysis.md`.

# Pipeline Retrospective: Evaluation Round

**Date**: 2026-04-04
**Scope**: Code review of 3 public repos (Project A: JS game, Project B: TS AI agent, Project C: Java+Angular budget app)
**Finding**: Agent instruction-following is the primary bottleneck, not methodology coverage

## Current State

| Feature | Release | Status | Spec | Commit |
|---------|---------|--------|------|--------|
| `instruction-hygiene` | v0.3.5 | **Complete** — committed, pending push/tag/release | `instruction-hygiene/instruction-hygiene-spec.md` | `24b8e5a` |
| `detector-decomposition` | v0.4.0 | Not started | Needs spec | — |
| `tiered-detection` | v0.4.0 | Not started, depends on detector-decomposition | Needs spec | — |

**Project overview**: `detection-accuracy-overview.md`

### What instruction-hygiene (v0.3.5) addressed
- Deduplicated 3 redundant definitions (dead infrastructure, string-based classification, context bypass/silent error)
- Resolved scope contradiction in ai-failure-modes.md
- Promoted 3 trapped heuristics to quality-detection.md
- Split compound checklist item 12
- Added nit suppression to Detector, pattern-label handling to Challenger
- Restructured prompt ordering (content-first, instructions-last)
- Loaded quality-detection.md in conversational review path
- Aligned code-review-guide.md Orchestration Protocol and Source of Truth Handling

### What instruction-hygiene did NOT address (deferred to v0.4.0)
- Instruction count still ~62 per Detector (~30 detection targets + ~32 format/methodology) — 3x the ~20 reliable threshold
- No forced enumeration — agents can still satisfice after first match
- No intent extraction phase — still depends on orchestrator remembering to do it
- No narrow-mandate agent decomposition — still 1 Detector with all checklist items
- No cross-cutting Tier 2 agents — cross-module patterns still depend on file scope overlap
- No dedicated test reviewer agent — test-integrity items mixed with code checklist
- 4 methodology gaps not addressed: unbounded growth, migration idempotency, batch atomicity, intra-function redundancy

---

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

1. **Instruction overload (confirmed)**: Detectors receive ~62 discrete instructions from 4 documents. IFScale research shows standard Claude Sonnet exhibits linear compliance decay from instruction 1. Practical reliable threshold is ~20 instructions. We're at 3x. **Partially addressed by instruction-hygiene** (reduced redundancy and contradictions); **structurally addressed by detector-decomposition** (3-5 items per agent).

2. **Instruction ordering was backwards (fixed in v0.3.5)**: We put instructions in the middle of the prompt. Anthropic recommends data at top, instructions at bottom, with a measured 30% improvement. **Fixed**: SKILL.md steps 1 and 3 now specify content-first ordering.

3. **Redundancy wasted instruction budget (fixed in v0.3.5)**: Dead infrastructure defined in 4 places, string-based classification in 3 places, context bypass overlapped. **Fixed**: Deduplicated to 1 canonical + 1 summary each.

4. **Scope contradiction (fixed in v0.3.5)**: ai-failure-modes.md said "only without specs" but orchestrator injected unconditionally. **Fixed**: Unconditional scope, quality-detection.md loaded in all paths.

5. **Context competition (confirmed, not yet addressed)**: Cognitive load research shows linear degradation as task content grows relative to instructions. **Addressed by detector-decomposition** (less content per agent via narrow scope).

6. **Satisficing after first match (confirmed, not yet addressed)**: The "find one then move on" pattern is expected with 62 instructions and large code volumes. **Addressed by detector-decomposition** (forced enumeration + narrow mandate).

7. **Three detection heuristics trapped in orchestrator-only doc (fixed in v0.3.5)**: Dual-path verification, test-production string alignment, dead code after field removal. **Fixed**: Promoted to quality-detection.md, quality-detection.md loaded in all paths.

### Not confirmed / still hypothetical

- Whether the R1 Challenger's regex misread was attention-related or a hallucination
- Whether reasoning/thinking mode would materially improve our specific detection task
- Whether the instruction-to-content ratio or instruction count is the dominant factor in our case

---

## Remaining Work: detector-decomposition (v0.4.0)

Absorbs Proposals B + D + F + G from the original analysis:
- 7 narrow-mandate Tier 1 detector groups (3-5 items each)
- Forced per-file enumeration
- Mandatory intent extraction phase + dedicated intent path tracer
- Dedicated test reviewer agent (separated from Tier 1 checklist groups)
- Randomized checklist ordering

Key design decisions already made (see `detection-accuracy-overview.md`):
- 8 agent types: 7 checklist groups + intent path tracer
- Test reviewer as separate dedicated agent with its own context shape
- Intent extractor produces up to 30 structured claims; path tracer traces 5-8 main paths
- Evaluation via fresh repos with existing filed issues (25% overlap baseline to beat)

## Remaining Work: tiered-detection (v0.4.0)

Absorbs Proposal A:
- Tier 2 cross-cutting detectors operating on summarized file context
- Hybrid summary format: deterministic AST skeleton + LLM behavioral annotation
- Language-agnostic AST tooling instruction
- Cross-tier deduplication

Depends on detector-decomposition (Tier 1 infrastructure must be in place first).

---

## Supporting Documents

- `instruction-trace-report.md` — Full trace of instruction sets per agent type (pre-instruction-hygiene baseline)
- `agent-instruction-alignment-research.md` — External research on instruction following
- `firebreak-detection-divergence-analysis.md` — Divergence analysis vs Project B maintainer's findings
- `instruction-hygiene/` — Complete spec, review, tasks, and retrospective for the v0.3.5 feature
- `detection-accuracy-overview.md` — Project overview with all 3 features and resolved design decisions

## Evaluation Artifacts (gitignored, in tmp/firebreak-eval/)

- Code review results for all 3 projects
- Outreach drafts for all 3 projects
- Divergence analysis with specific issue numbers
- Cloned repos for re-evaluation (UV-9)
