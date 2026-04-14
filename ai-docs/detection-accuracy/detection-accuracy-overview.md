> **Note (2026-04-09):** This document describes the internal 3-repo evaluation that motivated the detection accuracy work. For the external benchmark baseline (50 PRs, consensus-judged), see `martian-benchmark/results/deviation_analysis.md`.

# Detection Accuracy Improvement — Project Overview

## 1. Vision

The code review pipeline's detection coverage is limited by agent instruction-following, not by methodology coverage. Evaluation of 3 public repos (178 findings) revealed that 78% of missed issues were already covered by the checklist — detectors didn't apply instructions consistently. External research confirms the root cause: detectors receive ~63 discrete instructions (3x the reliable compliance threshold), with backwards prompt ordering and redundant definitions wasting instruction budget.

This project improves detection accuracy through three phases: fixing known instruction presentation issues (v0.3.5), restructuring the detector architecture around research-confirmed agent instruction limits (v0.4.0), and adding cross-cutting detection capability that single-file agents miss (v0.4.0).

## 2. Architecture

Current state:
```
Orchestrator → spawns 3 Detectors (each: 63 instructions + all files in scope)
            → collects sightings
            → spawns Challengers (per sighting batch)
            → iterates until convergence
```

Target state (after Phase 3):
```
Orchestrator
  ├── Intent Extraction (v0.3.5, orchestrator step — reads docs → intent register + Mermaid diagram → user checkpoint)
  ├── AST skeleton extraction (deterministic: imports, exports, signatures)
  ├── Summarizer agents (per-module behavioral annotation, 3-5 sentences each)
  │
  ├── Intent Path Tracer (intent register + entry points + call chains)
  │     └── traces 5-8 main paths against documented intent
  ├── Test Reviewer (test files + production imports + intent register)
  │     └── test-intent alignment + agentic test failure modes
  ├── Tier 1 Detectors (each: 2-4 checklist items + single file/module)
  │     └── 7 groups, forced per-file enumeration
  ├── Tier 2 Detectors (architectural instructions + skeleton + summaries)
  │     └── cross-module patterns, state flow, contract mismatches
  │
  ├── Cross-agent deduplication
  ├── Challengers (per sighting batch, full file access for verification)
  └── Iterate until convergence
```

Key architectural decisions:
- Instruction count per agent stays under 20 (research-confirmed reliable threshold)
- Code content placed at top of prompt, instructions at bottom (Anthropic-recommended, 30% measured improvement)
- Forced enumeration output format prevents satisficing after first match
- Intent extraction is a separate mandatory phase, not an optional step the orchestrator can skip
- Two detector tiers: Tier 1 for per-file exhaustive checklist application, Tier 2 for cross-module pattern detection

## 3. Technology Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Agent model | Same as current (inherits parent) | No evidence that model change is needed; the issue is instruction presentation, not model capability |
| Instruction budget per agent | ≤20 discrete instructions | IFScale research: standard Claude Sonnet shows linear compliance decay; ~20 is the practical reliable threshold |
| Prompt ordering | Data first, instructions last | Anthropic best practices: 30% measured improvement from this ordering |
| Output format | Structured per-file, per-item enumeration | Prevents satisficing; forces explicit "no issues found" entries |
| Tier 2 content format | Deterministic skeleton (AST-extracted imports, exports, signatures) + LLM behavioral summaries (3-5 sentences per module) | Static skeleton prevents summary drift; behavioral annotation enables the judgment calls static analysis can't make. Challenger layer catches false sightings from summary inaccuracy |
| AST tooling | Language-agnostic instruction to install appropriate parser; grep-based fallback | Avoids hardcoding language-specific tools in pipeline instructions |

## 4. Feature Map

| Feature | Spec path | Release | Depends on | Status |
|---------|-----------|---------|------------|--------|
| `instruction-hygiene` | `ai-docs/detection-accuracy/instruction-hygiene/instruction-hygiene-spec.md` | v0.3.5 | None | Complete (`24b8e5a`) |
| `intent-extraction` | Implemented directly in SKILL.md + code-review-guide.md | v0.3.5 | instruction-hygiene | Complete (`977f828`) |
| `detector-decomposition` | `ai-docs/detection-accuracy/detector-decomposition/detector-decomposition-spec.md` | v0.4.0 | instruction-hygiene, intent-extraction | Not started |
| `tiered-detection` | `ai-docs/detection-accuracy/tiered-detection/tiered-detection-spec.md` | v0.4.0 | detector-decomposition | Not started |

**instruction-hygiene** (v0.3.5) — Complete
Prompt restructuring, deduplication, scope contradiction fix, trapped heuristic promotion, nit suppression for detectors, pattern-label handling for challengers. Lowest cost, no architectural change.

**intent-extraction** (v0.3.5) — Complete
Mandatory intent extraction phase with user checkpoint, review report file, Mermaid diagram generation. Added to SKILL.md, code-review-guide.md, and existing-code-review.md. Validated against Project B: 12 intent-sourced findings (29% of total), both critical findings intent-sourced, new finding type "tests protecting bug" uniquely enabled by intent.

**detector-decomposition** (v0.4.0) — Updated based on v0.3.5 evaluation data
Decompose from 3 detectors with 63 instructions each to 7 Tier 1 groups with 2-4 instructions each, plus dedicated Intent Path Tracer and Test Reviewer agents. Randomize checklist ordering across runs.

Updates from v0.3.5 evaluation:
- Intent extraction is already implemented — the Intent Path Tracer agent consumes the existing intent register format (prose claims + Mermaid diagram) rather than designing a new extraction step. The Mermaid diagram may be path-tracer-specific context (excluded from general Detector prompts to save ~900 tokens) pending further data.
- Test Reviewer adds "tests protecting bug" as a named detection target — tests that validate broken behavior against documented intent. This finding type was uniquely enabled by intent extraction in the v0.3.5 evaluation.
- Forced per-file enumeration schema: consider making strict schema optional. Informal enumeration instructions ("state what you checked per file") achieved compliance in all three v0.3.5 evaluations without a rigid format.

**tiered-detection** (v0.4.0) — Updated based on v0.3.5 evaluation data
Add Tier 2 detector agents that operate on deterministic AST skeletons + LLM behavioral summaries, focused on cross-module patterns: dual-path divergence, state flow between components, contract mismatches, architectural intent alignment.

Updates from v0.3.5 evaluation:
- Add two detection targets: **workflow completeness** (does an operation's inverse undo all effects — repo issue #23 /unsubscribe doesn't remove Reddit feeds) and **concurrent path interaction** (do concurrent invocations of the same path interfere — repo issue #24, fresh review F-34/F-35).
- Three of four original methodology gaps confirmed as still undetected: unbounded data structure growth (#4, #25), batch transaction atomicity (#3), intra-function logical redundancy (#9). Add to Tier 2 or checklist detection targets.
- Cross-tier deduplication keys on existing pattern label field in sighting format — Tier 2 finding with same pattern label as Tier 1 findings subsumes the Tier 1 instances.

Includes AST tooling installation, summarizer agents, and cross-tier deduplication.

## 5. Cross-Cutting Concerns

**Backward compatibility**: Phase 1 changes only instruction content, not the pipeline protocol. Phases 2-3 change the orchestrator's spawn logic and output collection but preserve the Detector→Challenger→Finding pipeline contract. Challenger agents receive the same sighting format regardless of which tier produced them.

**Cost management**: More agents = more API calls. Phase 2 increases detector count from ~3 to ~8-12. Phase 3 adds ~2-3 Tier 2 agents. Total agent invocations per round roughly triples. The intent extraction phase adds 1 agent per review. This is a deliberate cost-for-coverage trade.

**Testing**: Each phase is validated against fresh repos with existing filed issues (not re-runs of previously reviewed repos). The filed issues are an independent baseline for calibrating detection accuracy, not ground truth — the issue-filing agent has its own blind spots. Current baselines on Project B: v0.3.4 14.3% partial overlap, v0.3.5 39.3%. Target: ≥50% partial overlap on comparable repos after Phase 2.

**Evaluation data**: The 3 public repo reviews, divergence analysis, and instruction trace are the evidence base. All stored in `tmp/firebreak-eval/`.

## 6. Open Questions

1. **Tier 2 file summary format** (resolved): Hybrid approach — deterministic skeleton + LLM behavioral annotation. The orchestrator detects the project's language(s) and installs appropriate AST tooling to extract import graphs and function signatures (language-agnostic instruction: "install and use an AST parser appropriate for this project's language; fall back to grep-based extraction if unavailable"). A lightweight summarizer agent then reads each file and produces a 3-5 sentence behavioral description (what the module does, what it depends on, what it assumes about callers). Tier 2 agents receive both: the skeleton as factual guardrail, the behavioral annotations for semantic reasoning about cross-module patterns. Static analysis alone catches static analysis problems — the AI's value is specifically the judgment calls that static tools miss (undocumented contracts, state assumptions, intent-behavior misalignment across modules). False sightings from summary inaccuracy are caught by the existing Challenger verification layer.

2. **Checklist item grouping for narrow agents** (resolved): Group by detection similarity (related patterns together) for reasoning coherence, with empirical refinement over time. 8 agent types:
   Tier 1 checklist groups (7 groups, test items removed to dedicated Test Reviewer):
   1. Bare literals + hardcoded coupling + string-based discrimination
   2. Dead infrastructure + dead conditional guards + middleware never connected
   3. Zero-value sentinel + context bypass + silent error discard
   4. Comment-code drift + semantic drift
   5. Mixed logic/side effects + ambient state + non-importable behaviors
   6. Caller re-implementation + parallel collection coupling + multi-responsibility
   7. Composition opacity + surface-level fixes + semantically incoherent fixtures

   Specialized agents (outside Tier 1 numbering):
   - **Intent Path Tracer**: Traces main execution paths against intent register. Catches architectural mismatches, documented behaviors with no entry point, and module-level intent drift.
   - **Test Reviewer**: Dedicated agent for test quality. Test-intent alignment (do tests cover documented paths?) + agentic test failure modes (name-assertion mismatch, mock permissiveness, vacuous assertions, fixture coherence, coverage gaps). Receives test files + production imports + intent register.

3. **Intent extraction depth** (resolved, partially implemented in v0.3.5): Two-stage intent analysis with a separate test reviewer.
   - **Intent extractor**: Implemented in v0.3.5 as orchestrator-level instructions in SKILL.md. Reads all project docs, produces up to 30 structured behavioral claims + Mermaid diagram, gated by user checkpoint. Validated: 25 claims extracted from Project B, 12 findings sourced from intent (29% of total), both criticals intent-sourced.
   - **Intent path tracer**: v0.4.0 agent. Consumes the existing intent register format (not a separate extraction). Traces 5-8 main execution paths against intent claims. Path tracing catches architectural mismatches by following real composition — the v0.3.5 evaluation confirmed this: F-01 (auto-reg unreachable) and F-03 (prefilter no-op) are path-tracing findings produced by general Detectors that a dedicated agent would find more reliably without displacing structural detection.
   - **Test reviewer**: Separate dedicated agent. Receives test files + their production imports + intent register. Focuses on: (a) test-intent alignment — do tests cover what the docs say the application does? (b) **tests protecting bugs** — tests that validate broken behavior against documented intent (new finding type from v0.3.5 evaluation: F-11 prefilter tests assert all articles go to AI, which is correct per code but wrong per intent). (c) agentic test failure modes — name-assertion mismatch, mock permissiveness, fixture coherence, vacuous assertions, coverage gaps. This removes test-integrity items from the Tier 1 checklist groups and gives test review its own optimized context shape.

4. **Evaluation methodology**: Each phase should be validated against fresh repos — small-medium public projects with existing filed open issues. The open issues serve as an independent baseline for calibrating detection accuracy — not ground truth, as the issue-filing agent has its own blind spots. Overlap measures alignment with an independent reviewer, not correctness. See `three-way-comparison.md` Section 5 for detailed analysis.

   Current baselines (Project B, 28 matchable issues):
   - Pre-hygiene (v0.3.4): 4/28 partial overlap (14.3%)
   - Post-hygiene no intent (v0.3.5): 11/28 partial overlap (39.3%)
   - Post-hygiene with intent (v0.3.5+intent): pending comparison (42 findings, TBD overlap)
   
   v0.4.0 target: ≥50% partial overlap on comparable repos after detector-decomposition.
