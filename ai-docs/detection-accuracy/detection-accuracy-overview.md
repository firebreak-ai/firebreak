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
  ├── Intent Extractor (reads all docs → intent register, up to 30 claims)
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

| Feature | Spec path | Release | Depends on |
|---------|-----------|---------|------------|
| `instruction-hygiene` | `ai-docs/detection-accuracy/instruction-hygiene/instruction-hygiene-spec.md` | v0.3.5 | None |
| `detector-decomposition` | `ai-docs/detection-accuracy/detector-decomposition/detector-decomposition-spec.md` | v0.4.0 | instruction-hygiene |
| `tiered-detection` | `ai-docs/detection-accuracy/tiered-detection/tiered-detection-spec.md` | v0.4.0 | detector-decomposition |

**instruction-hygiene** (v0.3.5)
Prompt restructuring, deduplication, scope contradiction fix, trapped heuristic promotion, nit suppression for detectors, pattern-label handling for challengers. Lowest cost, no architectural change.

**detector-decomposition** (v0.4.0)
Decompose from 3 detectors with 63 instructions each to 7 Tier 1 groups with 2-4 instructions each, plus dedicated Intent Path Tracer and Test Reviewer agents. Add forced per-file enumeration. Formalize intent extraction as mandatory first phase. Randomize checklist ordering across runs.

**tiered-detection** (v0.4.0)
Add Tier 2 detector agents that operate on deterministic AST skeletons + LLM behavioral summaries, focused on cross-module patterns: dual-path divergence, state flow between components, contract mismatches, architectural intent alignment. Includes AST tooling installation, summarizer agents, and cross-tier deduplication.

## 5. Cross-Cutting Concerns

**Backward compatibility**: Phase 1 changes only instruction content, not the pipeline protocol. Phases 2-3 change the orchestrator's spawn logic and output collection but preserve the Detector→Challenger→Finding pipeline contract. Challenger agents receive the same sighting format regardless of which tier produced them.

**Cost management**: More agents = more API calls. Phase 2 increases detector count from ~3 to ~8-12. Phase 3 adds ~2-3 Tier 2 agents. Total agent invocations per round roughly triples. The intent extraction phase adds 1 agent per review. This is a deliberate cost-for-coverage trade.

**Testing**: Each phase is validated against fresh repos with existing filed issues (not re-runs of previously reviewed repos). The filed issues provide ground truth: the pipeline should at minimum find what humans already found. The initial evaluation (6/24 overlap = 25% issue coverage) is the baseline to beat. Target: ≥50% overlap on comparable repos after Phase 2.

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

3. **Intent extraction depth** (resolved): Two-stage intent analysis with a separate test reviewer.
   - **Intent extractor**: Reads all project docs, produces up to 30 structured behavioral claims (capped for cost). Full extraction — the evaluation showed both major and minor findings were valuable.
   - **Intent path tracer**: Instead of checking each claim against every file, traces the application's main execution paths (5-8 paths typically) and compares what actually happens against the intent register. Path tracing naturally catches architectural mismatches by following real composition — it surfaces both misaligned behaviors (prefilter doesn't filter) and documented behaviors with no entry point (tower health system). Cheaper than brute-force claim-by-claim checking and better at catching cross-module issues.
   - **Test reviewer**: Separate dedicated agent. Receives test files + their production imports + intent register. Focuses on: (a) test-intent alignment — do tests cover what the docs say the application does? (b) agentic test failure modes — name-assertion mismatch, mock permissiveness, fixture coherence, vacuous assertions, coverage gaps. This removes test-integrity items from the Tier 1 checklist groups (group 3 becomes: composition opacity only, merged into another group) and gives test review its own optimized context shape.

4. **Evaluation methodology**: Each phase should be validated against fresh repos — small-medium public projects with existing filed open issues. The open issues serve as ground truth: at minimum, the pipeline should detect what humans have already detected. This is a floor, not a ceiling (there will always be unfiled issues hiding in any code), but it provides an objective, non-overfitting measurement of detection coverage per release. The initial evaluation (6/24 overlap) is the Phase 1 baseline.
