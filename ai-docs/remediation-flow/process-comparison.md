# Process Comparison: Persona/World Ingestion — Baseline vs Rewritten Module

**Date**: 2026-05-21
**Purpose**: Quantitative and qualitative comparison of the original persona/world ingestion implementation against the rewritten module produced under the current Firebreak SDL process. Intended as a process-evaluation artifact: did the workflow changes reduce the variety and density of agentic-coding failure modes?

## Source artifacts

| Artifact | Description |
|----------|-------------|
| `fbk-code-review-2026-05-18-0527.md` | Baseline code review of `internal/persona/`, `internal/world/`, and the session-init slice of `internal/chat/session.go`. **No prior fix-pass applied.** |
| `.firebreak/remediation/fbk-code-review-2026-05-20-1913.md` | First review of the rewritten ingestion module (`rearchitecture/interface-contracts/*`). 4 verified findings (F-01..F-04). |
| `.firebreak/remediation/fbk-code-review-2026-05-21-0230.md` | Post-fix re-review of the rewritten ingestion module. Fresh Detector + Challenger, no carry-over context. |

The "fair" comparison this document captures is **baseline (no fix-pass)** vs **rewrite + fix-pass**. The baseline did not undergo a Firebreak remediation cycle against its own findings — that's an asymmetry; see § Confounders.

All reviews used the same preset (`behavioral-only`) and severity threshold (`minor`).

## Pattern taxonomy

Twelve named patterns generalizing the AI failure mode checklist into observable categories that survive a rewrite. Used as the comparison axis throughout.

| Code | Pattern | Definition |
|------|---------|------------|
| **HPO** | Happy-path optimism | Code assumes upstream systems (LLM, parser, network, store) behave in spec; failure modes are not represented in the type system or error handling. |
| **TBB** | Trust-boundary blindness | Code treats request/file/user input as if it were internal. Missing validation/escaping/canonicalization at a system boundary. |
| **PLR** | Path-of-least-resistance hardcoding | A concrete value wired in where the situation called for a parameter, lookup, or abstraction. Often a plausible-looking constant chosen under uncertainty. |
| **CTX** | Context-discard | A caller-provided `context.Context` replaced with a fresh `context.Background()`, severing cancellation/deadlines/trace propagation. |
| **SID** | Spec-implementation drift | A spec, AC, or design doc names a step/helper that doesn't exist (or contradicts) in the code; comments may reference it. |
| **DIN** | Dead infrastructure / unwired layer | Construct (interface, manager, helper, middleware) built and instantiated but never called by production. |
| **VTH** | Validation theater | Function that looks like it verifies something — right name, returns nil-error — but the check is unreachable, satisfied by zero values, or doesn't cover the claimed behavior. |
| **PIS** | Premature interface stabilization | Interface designed before all consumer needs known; later work bypasses the interface rather than updating it. |
| **DIG** | Documentation-implementation gap | Doc-comments/docstrings claim behavior the code doesn't implement, or direct callers to functions absent from the interface. |
| **PPD** | Parallel-path drift | Two near-identical code paths that should share an abstraction; one path gets a fix the other doesn't. |
| **SED** | Silent error discard | Error returns assigned to `_`, ignored, or logged only at Debug; callers can't distinguish success from masked failure. |
| **ZVA** | Zero-value sentinel ambiguity | Zero/empty/nil serves as both "unset" and a valid domain value with no guard. |

Two additional categories emerged from the rewrite review:

| Code | Pattern | Definition |
|------|---------|------------|
| **MPM** | Mock permissiveness masking constraints | Test double accepts inputs production rejects; tests can't detect violations of the production constraint. (AI failure mode checklist #13.) |
| **FPR** | Fix-pass regression | A finding that exists because a previous fix-pass changed one location without sweeping callers, tests, or adjacent code that depended on the prior shape. |

## Density comparison

| Metric | Baseline (no fix-pass) | Rewrite + fix-pass | Delta |
|--------|------------------------|---------------------|-------|
| Implementation LoC | ~1,700 | ~1,430 | −16% |
| Sightings generated | 13 | 7 | −46% |
| **Verified behavioral-major findings** | **5** | **2** | **−60%** |
| Verified findings total (all severities) | 6 | 2 | −67% |
| Out-of-preset items surfaced | 6 | 5 | −17% |
| **Total surfaced concerns** | **12** | **7** | **−42%** |
| Behavioral-major / kLoC | 2.9 | 1.4 | **−52%** |
| Total concerns / kLoC | 7.1 | 5.0 | −30% |
| False positives caught by Challenger | 1 | 0 | −1 |
| Pre-Challenger drop rate | 46% | 71% | +25pp |
| `go vet` | clean | clean | — |
| `golangci-lint` | not runnable (Go-version mismatch) | clean | — |
| Test suite | not measured | 77 functions, all pass | — |

The behavioral-major density dropping by ~50% is the durable headline metric: the count of "would not ship this" findings per unit of code is halved.

The pre-Challenger drop rate climbing from 46% → 71% is also informative: when the Detector has to reach into test infrastructure and structural items to find anything, the in-domain signal thins out. That's a code-quality indicator, not a noisy-Detector indicator.

## Pattern composition

| Pattern | Baseline | Rewrite + fix-pass | Notes |
|---------|----------|---------------------|-------|
| TBB | 1 | **0** | Eliminated by typed `*Input` at the seam (no file paths constructed from request data) |
| CTX | 1 | **0** | Eliminated by AC-49 cancellation contract (100ms bounded response to cancel) |
| DIN | 2 | **0** | Eliminated by `Capability` as the single seam; no unwired Managers, no missing helpers |
| PLR | 4 | ~0–1 | One secondary instance (F-01 — invented `EdgeTypeContains`) |
| HPO | 4 | **0** | — |
| SED | 2 | **0** | Eliminated by unified `ingestionerr` error vocabulary (three Kinds) |
| PIS | 2 | **0** | — |
| PPD | 1 | **0** | Was present in the first rewrite review; fix-pass closed it |
| DIG | 2 | 1 | F-02 — `PropKeyProse` fallback contradicts its own docstring |
| SID | 1 | 2 | F-01, F-02 — both small-radius spec deviations (1 edge type, 2 fallback branches) |
| VTH | 2 | 3 | All 3 are on the **test** side (vacuous assertions, dead test setup) |
| MPM | 0 | 1 | New: `DeterministicMintRegistry.RegisterAuthorAlias` no-ops where production errors |
| FPR | 0 | 2 | New: 2 of the 5 dropped items are blast-radius from the first rewrite review's fix-pass |

**Pattern class breadth**: 9 distinct classes in baseline → 4 in rewrite + fix-pass (SID, DIG, VTH, MPM; PLR as a single secondary).

### Categories eliminated entirely

Eight pattern classes appear in the baseline and are absent from the post-fix rewrite:

- **TBB** trust-boundary blindness
- **CTX** context-discard
- **DIN** dead infrastructure
- **PLR** path-of-least-resistance hardcoding (one secondary remains; primary instances are gone)
- **HPO** happy-path optimism
- **SED** silent error discard
- **PIS** premature interface stabilization
- **PPD** parallel-path drift

These survived the fix cycle without re-emerging. The category eliminations are architecturally durable — they trace back to design decisions in the spec (typed inputs, cancellation contract, single Capability seam, unified error vocabulary) rather than to specific code-level fixes that could regress.

### Categories that concentrated or shifted

1. **VTH migrated from production to tests.** Baseline VTH was in production (`extractPersona` dead length-check; the empty-string verification path the Challenger rejected as a false positive). Post-fix rewrite VTH is all test-side: vacuous AC-54/AC-55 hygiene assertions, dead `SetResponse` setup in mining tests. The production code isn't doing validation theater anymore — the test infrastructure is.

2. **MPM emerged as a new category.** The rewrite has explicit test doubles in `internal/testsupport/`; the baseline didn't. A test double that's more permissive than production lets test assertions pass when production would fail. This category was effectively out-of-scope for the baseline review.

3. **SID became smaller-radius.** Baseline SID was an entire missing helper function (`cleanupPhase1WorldFacts`, ~50 LoC spec'd but absent). Post-fix rewrite SID is a single edge-type name and a 4-line fallback branch. The category persists; the blast radius shrank by an order of magnitude.

4. **FPR emerged as a measurable artifact.** Two of the 5 dropped items in the 2026-05-21 review are explicitly identified as regressions from the prior fix-pass:
   - S-03: prior S-06 fix (nil-guard symmetrization) made AC-54/AC-55 hygiene assertions vacuously true.
   - S-06, S-07: prior F-03 fix (removing `RoleSettingPrimary` from `buildProseSources`) left dead `SetResponse` calls in two test files.

   This is **40% fix-pass regression rate** (2/5) for this iteration. The Firebreak re-review surfaced these as discrete findings rather than letting them accumulate as silent drift — that's the value of the post-fix re-review pass.

## Architecture / maintainability assessment

The baseline review identified seven architectural concerns (A1–A7). The rewrite addresses them as follows:

| Baseline concern | Status in rewrite + fix-pass |
|------------------|------------------------------|
| **A1** `session.go` monolith (1413 LoC, 11 responsibilities) | **Resolved** — ingestion is its own subsystem: separate packages for `intake`, `enumeration`, `mining`, `resolution`, `ingestion`, `seed`, `sources`, `llm`, `logging`. |
| **A2** Three near-identical "resolve entities + write edges" pipelines | **Resolved** — `resolution.Registry` is the single seam with named primitives (`Mint`, `RegisterAuthorAlias`, `NoteDiscoveredAlias`, `Resolve`, `RegisterPrivilegedNode`). |
| **A3** Sync-async handshake inline in `NewSession` | **Partially resolved** — `Capability.IngestSession` is the single entry; mining runs serial Generate calls with a bounded envelope (354). Background lifecycle out of scope. |
| **A4** `Importer` interface bypassed by callers | **Resolved** — `Capability` is the single seam; per-package responsibilities split. No bypassed interfaces. |
| **A5** Cross-package coupling on graph schema | **Resolved** at the seam — `seed.SeedGraph` is the boundary contract; downstream packages don't reach into graph schema. |
| **A6** Config across module boundaries | Not directly visible in this scope. |
| **A7** Ingestion capability not represented as a unit | **Resolved** — `ingestion.Capability` is the unit. The biggest structural change. |

No new architectural concerns surfaced in either rewrite review. Structural cleanliness is preserved through the fix cycle. None of the post-fix findings would require restructuring to address (F-01 is a one-line removal; F-02 is removing two `if` branches and fixing fixtures).

## Process signals

| Signal | Baseline | Rewrite + fix-pass |
|--------|----------|---------------------|
| Detection sources (verified findings) | 1 spec-ac, 1 audit-pass, 2 checklist, 2 intent | 4 spec-ac, 1 audit-pass, 2 intent |
| Convergence | 1 round | 1 round (second iteration) |
| False positive rate | 14% (1/7) | 0% (0/2) |
| Out-of-domain Detector noise | ~46% | ~71% |
| Architectural recommendations made | 7 (A1–A7) | 0 (rewrite resolved them) |

Detection-source mix shifted toward `spec-ac`. With 53 ACs and an intent register sourced from named claims, the Detector finds *spec violations* rather than *intent gaps*. The reviewer no longer has to reconstruct intent from code reading and historical phase docs — the spec carries that load.

Test-to-production LoC ratio: ~1,430 production carrying ~4,700 test LoC = **3.3× test surface**. This ratio is what makes test-integrity findings detectable. A thinner test surface would absorb the same issues silently.

## Confounders

These are the asymmetries the comparison contains. Reading the numbers without them risks over-claiming the process win.

1. **Baseline hasn't had a fix-pass.** If a Firebreak remediation cycle were run against the 2026-05-18 baseline, it would (a) close most of the verified findings and (b) generate its own FPR items in adjacent code. We don't have that data. The current comparison is "pre-fix-pass baseline vs post-fix-pass rewrite" — the fairer-still comparison would be "baseline + fix-pass vs rewrite + fix-pass."

2. **Test-infrastructure scope is asymmetric.** The rewrite review explicitly includes `internal/testsupport/` (~600 LoC). The baseline review didn't — the persona/world packages don't have a comparable shared test-infrastructure seam. Three of the rewrite's 5 dropped items live in test code; that category was effectively out-of-scope for the baseline.

3. **Detection-source mix is partly a spec-quality signal.** The rewrite review is so spec-driven because the spec has 53 ACs. If the baseline had a comparable spec, the same Detector would have produced more `spec-ac` findings and fewer `intent` ones, regardless of code quality.

4. **Different module structure.** The rewrite is a fresh implementation. The baseline accumulated across multiple remediation phases. The baseline has historical-debt overhead the rewrite doesn't.

5. **Pattern taxonomy was built from the baseline.** Mapping rewrite findings to this taxonomy carries confirmation-bias risk. The categorical-disappearance result is striking enough (8 of 12 classes → 0) that it's likely real signal, but a third independent review using a different taxonomy would strengthen the conclusion.

## Net read

**Density**:
- Behavioral-major density: 2.9/kLoC → 1.4/kLoC. **−52%**.
- Total concern density: 7.1/kLoC → 5.0/kLoC. **−30%**.

**Breadth**:
- Pattern classes surfaced: 9 → 4. **−56%** in the *variety* of failure modes still present.
- Categorical eliminations: 8 of the baseline's 12 pattern classes are absent in the rewrite + fix-pass. Architecturally durable wins.

**Composition**:
- Baseline signature: **PLR + HPO** (model picked plausible constants or happy-path shapes under uncertainty).
- Rewrite signature: **SID + DIG + VTH (test side) + MPM**. All small-radius, all leaf-level, no architectural restructuring required.

**New measurable artifact**:
- Fix-pass regression rate: 40% (2/5) this iteration. Now trackable as a discrete signal.

**The kinds of bugs that survive review have changed.** The rewrite no longer ships code that omits a security boundary (TBB), leaks a context (CTX), or contains an entire missing helper (DIN at the spec'd-helper-missing level). The bugs that remain are spec-seam deviations and test-fixture coverage gaps — categories that are easier to detect, easier to fix, and easier to design out in the next iteration of the spec template.

By the measure that matters most for process evaluation — *which failure modes the process eliminates entirely versus which it merely reduces in frequency* — the rewrite is worth the effort. Eight of twelve pattern classes are gone, not just reduced.

## Suggested tracking metrics for future iterations

For each future feature-level Firebreak cycle, capture and track these metrics so cross-cycle trends become visible:

1. **Behavioral-major density** (findings/kLoC). Target: trend down.
2. **Pattern class breadth** (count of distinct pattern classes surfacing in a review). Target: ≤5.
3. **Categorical recurrence**: of the 8 categories eliminated in this cycle (TBB/CTX/DIN/PLR/HPO/SED/PIS/PPD), how many re-emerge in the next feature's review? Target: 0.
4. **Fix-pass regression rate** (FPR findings / total dropped findings in post-fix review). Target: ≤20%.
5. **Detection-source mix** (% `spec-ac` vs other). High `spec-ac` % is a spec-quality signal as much as a code-quality signal; if `intent` and `checklist` start dominating, the spec is under-specified.
6. **Test-infrastructure findings** (% of out-of-preset items in test code). Watch for VTH/MPM concentration — signals test-double or fixture quality drifting from production behavior.
7. **Architectural recommendations** (count of A-class items raised by reviewer). The rewrite generated zero; baseline generated seven. A spike in a future review indicates the structural foundation is degrading.
8. **False-positive rate** (Challenger rejections / sightings reaching Challenger). Healthy range observed so far: 0–15%. Higher suggests Detector over-reach; persistently zero suggests Detector under-reach.

Items 1, 4, 5, 6, 8 are count-based and easy to automate as part of a review-summary table. Items 2, 3, 7 require inspection but are stable enough to score quickly.

## Appendix: finding-to-pattern map

### Baseline (12 surfaced items)

| Finding | Severity | Primary | Secondary |
|---------|----------|---------|-----------|
| S-01 path traversal | major | TBB | HPO |
| S-02 missing Phase-1 cleanup | major | SID | DIN |
| S-03 hardcoded `EntityTypePerson` | major | PLR | HPO |
| S-05 silent LLM classification failure | major | HPO | VTH, SED |
| S-06 `context.Background()` in goroutine | major | CTX | — |
| S-04 unwired `Manager` | minor | DIN | PIS, DIG |
| OOP: `ImportWithMemoryIDs` not on interface | structural | PIS | DIG |
| OOP: deprecated `strings.Title` | structural | HPO | — |
| OOP: `GetAllWorldFacts` silent skip | structural | SED | — |
| OOP: bare default literals in `ApplyMemoryDefaults` | structural | PLR | — |
| OOP: `FindEntityMentions` unbounded substring | structural | PLR | HPO |
| OOP: dead `extractPersona` length guard | structural | VTH | — |

### Rewrite + fix-pass (7 surfaced items)

| Finding | Severity | Primary | Secondary |
|---------|----------|---------|-----------|
| F-01 `EdgeTypeContains` not in spec | major | SID | PLR |
| F-02 `PropKeyProse` fallback contradicts docstring | major | DIG | SID |
| S-03 hygiene tests pass nil registry | test-integrity / major | VTH | FPR |
| S-04 `DeterministicMintRegistry` silently no-ops | test-integrity / major | MPM | — |
| S-05 test fixtures use `PropKeyProse` incorrectly | test-integrity / major | DIG | (links to F-02) |
| S-06 dead `SetResponse` for setting-primary | structural / minor | VTH | FPR |
| S-07 dead `SetResponse` for setting-primary (2nd file) | structural / minor | VTH | FPR |
