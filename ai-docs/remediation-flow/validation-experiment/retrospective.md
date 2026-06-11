# Validation Experiment — Retrospective

**Outcome**: `rewrite-wins-structurally`. Approval to proceed to Feature 2.

## Cycle metadata

- **Module under experiment**: realmind persona/world ingestion (Go; `internal/persona/`, `internal/world/`, session-init slice of `internal/chat/session.go`).
- **Duration**: 2026-05-16 (intent extraction begun) through 2026-05-21 (final review). Real elapsed time well over the ≤16h target — substantial ceremony was added during the experiment as methodology was developed in flight.
- **Sandbox technology**: container with realmind unmounted; in-sandbox `Read` against known realmind paths confirmed "file not found" (`physical-separation-maintained: true`).
- **Pipeline**: intent extraction (host, in realmind tree) → dependency stubs (drafted inside the sandbox from intent rather than transcribed from realmind signatures — methodology adaptation) → rearchitecture (inside sandbox) → spec (cleared-context `/fbk-spec` session, single 1800-line spec) → breakdown → implement → code-review → fix-pass → re-review.

## Architectural-decision retrospective

The rearchitecture produced six modules (`intake`, `enumeration`, `mining`, `resolution`, `ingestion`, plus supporting packages) as the decomposition of the slop persona/world ingestion capability. Each move was the right call:

- `Capability` as the single seam → resolved baseline A4 (bypassed `Importer` interface) and A7 (ingestion not represented as a unit). Single-seam architecture is the design choice that eliminated DIN (dead infrastructure) findings.
- `resolution.Registry` as the canonical entity-resolution primitive → resolved A2 (three near-identical resolve+write pipelines). PPD (parallel-path drift) eliminated.
- Typed `*Input` types at boundaries → eliminated TBB (trust-boundary blindness) by design.
- Cancellation contract (AC-49, 100ms bounded response) → eliminated CTX (context-discard) by design.
- Unified `ingestionerr` error vocabulary (three Kinds) → eliminated SED (silent error discard) by design.

The architecturally-rooted eliminations are the durable wins. They trace back to design decisions during rearchitecture, not to fix-cycle patches that could regress.

## Firebreak-leak retrospective

- **Physical separation maintained**: yes (verified at sandbox standup; re-verified at session starts).
- **In-session slop reads attempted**: zero successful slop reads. Sandbox isolation held throughout.
- **Methodology adaptation**: dependency stubs were drafted inside the firebreak from intent rather than transcribed from realmind signatures on host. Cleaner contamination story (no slop-shape via dep stubs), at the cost of dep stubs being idealized rather than slop-actual. Defensible given realmind is past the remediation-feasibility threshold.

## Move-list accuracy

- Behaviors discovered during rewrite that were missing from the inventory: none material. The two-tier schema captured behaviors at the right grain for the rewrite to honor.
- Behaviors in inventory that turned out to be obsolete: none observed.
- Inventory accuracy: high. Held up to the rewrite without revision.

## Caller-update slop signal

N/A. Single-module experiment; no callers updated. The slop signal would be Feature 7 territory.

## Mental-model contamination check

Four-question protocol, per the parent spec's acknowledgment of operator mental-model contamination as an unmitigated threat.

1. **Intent — did the operator articulate behaviors using slop-shaped abstractions?**
   First-draft intent did exactly this. The agent preserved current architecture detail. Two redirect rounds needed to reach capability-only ("describe what, not how" → "still preserving current shape" → "capability-only"). The instructions-doc fix landed during the experiment and on subsequent artifacts the agent reached capability-level on first draft. **Evidence: yes, played out — but corrected in real-time and the fix propagated to the instructions doc.**

2. **Rearchitecture — did the operator's move-list propose moves that preserved slop boundaries without independent design justification?**
   No. The six-module decomposition emerged from intent + structural principles inside the firebreak. The architectural review meeting pattern surfaced unjustified choices for revision before they landed. **Evidence: no.**

3. **Rewrite review — did the operator catch themselves expecting slop-shaped solutions the agent did not produce?**
   Not observed. The rewrite output looked structurally different from the slop in ways that surprised the operator positively, not negatively. **Evidence: no.**

4. **Net judgment — did mental-model contamination plausibly affect the classification outcome?**
   **No.** The threat played out at the intent stage and was caught and corrected. By rearchitecture and rewrite, the structural defenses (sandbox isolation + capability-not-shape framing) carried the load.

**Recommendation for Feature 2**: the curse-of-knowledge / mental-model contamination problem was successfully mitigated by the intent-alignment review pattern (context-clear subagent simulates downstream comprehension). Feature 2's intent extraction skill must include this review step. The skill should not assume operator-first authoring alone is sufficient defense.

## Decisions-revisitable evidence

Per the parent spec's "Decisions revisitable after Feature 1" section.

| Decision | Status | Evidence |
|---|---|---|
| Two-tier behavior inventory schema | **Validated, refined.** The schema field set worked. The audit rules required strengthening: capability-not-shape needs to be its own front-loaded section, not just an audit step. Also: descriptions over identifiers in human-facing communication. |
| Typed-contract requirement | **Validated as viable.** Hand-authoring was tractable when designed from intent (inside firebreak). Required two structural-principles passes to converge on a clean shape. Driver of the architecturally-rooted categorical eliminations. |
| Move-record minimum schema (8 fields) | **Not exercised at scale.** Single-module experiment. Defer to Feature 1.5. |
| Per-module incremental caller-update timing | **Not exercised.** Single-module. Defer. |
| Triple-council deliberation count | **Council not used; experiment succeeded without it.** Operator review + agent dialogue (architectural review meeting pattern) was sufficient at this scope. Council likely justified at higher-stakes design moments but not as default ceremony per stage. |
| Stakes-tier UX | **Not exercised.** Defer. |
| Defense-in-depth restructure (two real defenses + supporting controls) | **Validated.** Sandbox isolation + lexical/structural audits on agent-facing fields were the load-bearing defenses. Supporting controls (correctness gates, retrospective) added value but didn't carry contamination defense. |
| Above-firebreak set composition | **Revised during experiment.** Rearchitecture moved *inside* the firebreak (was above). Intent stays above. Pre-flight stays above. Net: above-firebreak set shrank further than the parent expected. |
| Firebreak coverage enumeration | **Held up.** Sandbox isolation against absolute paths, symlinks, and history access all worked. No escape paths surfaced. |
| Feature 1 commitment-doc structure | **Not formally followed.** Operator chose prototype mode over formal pre-registration. The classification was driven by qualitative pattern-class analysis (12-pattern taxonomy from process-comparison.md) rather than by pre-pinned per-category thresholds. The qualitative result was strong enough to be decisive without numerical threshold-checking, but Feature 1.5 should run with the formal commitment-doc structure to validate that the qualitative finding correlates with quantitative thresholds. |

## New findings the parent spec does not yet account for

These emerged during the experiment and warrant addition to the parent spec.

1. **Wave order as contamination control (not just engineering convenience).** Foundation-first wave order isn't tidy ordering — it's structural. The lowest-layer slop sets the upper bound on cleanliness for everything above it via interface-shape contamination. Parent spec should elevate wave-order from "Tech decisions" to load-bearing architectural commitment.

2. **Interface-shape contamination as a separate vector.** Distinct from body-pattern contamination. The firebreak isolates against bodies; interfaces imported from unrewritten slop neighbors carry slop shape inward. Mitigated in this experiment by drafting dep stubs from intent (capability-driven) rather than transcribing from slop (shape-driven). Parent spec should name this vector and the mitigation.

3. **Curse-of-knowledge gaps as a named failure mode.** Operator's tacit knowledge doesn't externalize automatically; agents pattern-match on operator's confident output as if they were peer-experts. Mitigated by grill-me framing (front-end) + intent-alignment review by context-clear subagent (back-end). Feature 2's skill needs both.

4. **Intent-alignment-review pattern.** Architecturally parallel to `/fbk-spec-review`: context-clear subagent reviews agent-facing intent artifacts for ambiguity gaps; iterate until clean. Feature 2 codification target as `/fbk-intent-review`.

5. **Architectural review meeting pattern.** Real-time co-author-and-defend mode for design phases. Distinct from spec-review and intent-review. Feature 4 codification target.

6. **Spec-redundancy finding.** Intent + rearchitecture artifacts cover ~80–90% of what `/fbk-spec` produces. `/fbk-spec` becomes a redundant synthesis step in the remediation pipeline. Possible restructure: intent + rearchitecture outputs become spec-format directly; `/fbk-spec` degrades to light assembly. Feature 2/4/parent codification target.

7. **Fix-pass regression (FPR) as a measurable failure mode.** 40% rate this iteration. Invisible in baseline because baseline had no fix-pass. Feature 7 (caller-update tightening) should design to drive this rate down.

8. **Mock permissiveness (MPM) as a measurable failure mode.** Emerged from rewrite's explicit test-infrastructure scope. Test doubles more permissive than production let assertions pass when production would fail. Worth tracking as a separate metric in future cycles.

9. **Pattern-class breadth as a measurable instrument.** 9 pattern classes in baseline → 4 in rewrite. Categorical-elimination rate is a sharper signal than density alone. Feature 8's progress gate should use this alongside per-capita density.

10. **Spec-AC detection-source mix as a spec-quality indicator.** Rewrite review's detection sources shifted toward `spec-ac` (sound spec) and away from `intent` / `checklist` (under-specified spec). High `spec-ac` percentage is both a code-quality signal and a spec-quality signal.

11. **Detection-source mix and test-to-production LoC ratio as measurement-validity instruments.** 3.3× test surface is what made test-integrity findings detectable. Lower ratios would absorb the same issues silently. Worth tracking.

## Methodology gaps surfaced for Feature 1.5 / repeat

1. **Fair comparison**: baseline + fix-pass vs rewrite + fix-pass, not pre-fix-pass baseline vs post-fix-pass rewrite. The current numerical claim is inflated by comparison asymmetry. Feature 1.5 should run the symmetric comparison.

2. **Spec size pressure on breakdown.** The 1800-line consolidated spec was at the upper edge of breakdown's attention budget. Either: (a) tighten the spec by removing redundancy with rearchitecture artifacts (per the spec-redundancy finding), or (b) restructure pipeline so intent + rearch outputs are consumed directly by breakdown without a synthesis pass.

3. **`/fbk-spec` scope-recognition heuristic is incomplete.** Defaults to project-shape when it sees multiple modules. Better heuristic: (module count + module independence + bottleneck count + downstream-agent attention budget) → scope decision. Solo operator + tightly-related modules + spec-attention-budget-sensitive → feature shape. Solo operator + independent modules + large total spec size → project shape.

4. **Pattern taxonomy applied to rewrite was built from baseline.** Confirmation-bias risk. Feature 1.5 should ideally use an independently-derived taxonomy, or have a third independent review producing one.

5. **Test-infrastructure scope asymmetry.** Rewrite reviews include `internal/testsupport/`; baseline didn't. Feature 1.5 should normalize scope explicitly (include or exclude test infrastructure consistently across both sides).

6. **Operator-time budget was not respected.** ≤16h target was substantially exceeded as methodology was developed in flight. Now that methodology is captured in the instructions docs, Feature 1.5 should hit closer to the original budget. If it doesn't, the methodology itself is too heavy and needs simplification.

## Outcome and approval-to-proceed

**Final classification**: `rewrite-wins-structurally`.

**Approval status**: proceed to Feature 2 (Intent Extraction & Behavior Inventory Skill) per the parent spec's approval rules.

**Strong recommendation**: also commit to Feature 1.5 (merge-case validation) with the fair comparison (baseline + fix-pass vs rewrite + fix-pass) before considering the firebreak hypothesis fully validated. The current result is strong enough to commit to building, not yet strong enough to commit to broader market positioning.

**Net read**: the firebreak technique works on this codebase, with this rigor, on this module. The qualitative finding (8 pattern classes eliminated, pattern signature qualitatively changed) is durable across the confounders. The numerical claims are weaker but still positive. Continue.
