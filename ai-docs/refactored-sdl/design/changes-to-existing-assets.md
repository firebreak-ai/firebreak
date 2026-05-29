# Changes to existing assets (refactored-sdl)

Design notes for how already-shipped Firebreak assets change under this SDL cycle. These are *planned* changes captured here in the feature directory. The canonical wiki pages for these assets describe current shipped (0.5.0) state and are updated only when the change actually ships.

One section per affected asset.

**Cross-cutting (applies to every phase below):** each new and reshaped phase appends its section to the feature retrospective, following the existing retrospective guide, so the self-improvement loop ([[fbk-improve]]) sees the new flow. Not repeated per section.

---

## /fbk-spec

Adds two upstream phases ([[fbk-intent]] for the "what" and [[fbk-design]] for capability shape), so /fbk-spec moves from Stage 1 to the spec phase (third) of a six-phase model. Its scope narrows:

- **Inputs:** PRD + behavior inventory (from intent) plus design pages + design manifest (from design). The spec no longer originates intent — it consumes it.
- **Outputs:** A spec file that includes [[slice-shapes]] declarations — one per slice — each declaring its test-discipline mode (new-contract / contract-preserving / contract-evolving / cross-cutting). Slice declarations are the input to breakdown.
- **Test-discipline mode per slice:** the spec must declare a [[slice-shapes]] shape for every slice. Spec gate rejects slices without a declared shape.
- **Schemas-from-design rule:** new schemas come from the design phase, not from spec. Spec consumes schemas as constraints (either from design or, for brownfield-existing schemas, from codebase scan).

**Gate (planned).** Hybrid gate per [[hybrid-gate-pattern]]:

- **Mechanical anchor:** spec file structurally valid; every slice has a declared `test-discipline` field from the [[slice-shapes]] taxonomy; every behavior in the inventory is covered by at least one slice; design pages referenced by the spec exist in the feature directory; grilling log present.
- **Semantic anchor:** [[council-deliberation]] output from [[fbk-spec-review]] — the existing multi-persona spec review, applied at the spec gate. After the phase-skill deduplication step against the grilling log, the reduced council output is what the gate consumes.

Single-persona fresh-eyes is *not* used at the spec gate; the council is. Both rest on the same cold, context-isolated review discipline; the council applies it with multiple specialist personas in parallel.

**Technique skills used (planned):** [[grilling-technique]] (slice scope and test-discipline decisions where the choice is judgment); [[council-deliberation]] via [[fbk-spec-review]] (gate-closure semantic anchor); [[fbk-spec-author]] preserved as the spec phase's drafter under the narrowed scope.

---

## /fbk-breakdown

Reshapes breakdown around **slice-then-pair-per-slice** decomposition:

- **Input:** spec with slice declarations, each carrying a [[slice-shapes]] test-discipline mode.
- **For each slice:** breakdown produces the work units the slice's test-discipline mode calls for (the structure varies by shape):

| Slice shape | Work-unit structure |
|-------------|---------------------|
| new-contract | **Test task** writes new tests against the slice's contract; tests must fail against empty implementation. **Impl task** writes code to turn tests green without modifying them. |
| contract-preserving | The existing **test-review** runs over all tests covering the module — validating them, hash-locking them, and surfacing any coverage gap (resolved by adding tests, staying contract-preserving). **Implementation unit** writes code preserving the existing contract. **Verification** confirms the locked tests still pass and the contract is observably unchanged. |
| contract-evolving | **Test task** writes new tests for new behavior; lists existing tests to retire from the lock manifest with rationale. **Impl task** writes code; retired tests removed, new tests must pass. |
| cross-cutting | **Test task** writes seam-level integration / contract / e2e tests. No paired impl task — the implementation already exists across the other slices; the seam tests must pass against it. |

- **Executability as completeness check:** if a slice's work units come out oversized — too large for a less-familiar agent to execute correctly given the spec they're built from — breakdown bounces the slice back to spec for re-scoping rather than producing oversized tasks. "Less-familiar agent" is a spec-completeness check, not a model-tier constraint. The bounce-back *is* the breakdown gate's semantic check — no separate fresh-eyes pass at breakdown closure.
- **Test review pre-lock gates lock application:** [[test-review-technique]] reviews accepted test tasks before [[test-integrity-locking]] applies its hashes. If the pre-lock verdict is `needs-revision`, tests bounce back to the test-task agent for rework and locks are not applied.
- **Contract-preserving slices** lean on the existing test-review (scoped to all tests covering the module) to validate and lock the existing tests, then run implementation and verification. A coverage gap is resolved by adding tests, staying contract-preserving — no separate "coverage-review unit" is introduced.
- **Progressive disclosure of shape instructions:** once a slice is classified into a shape, breakdown loads only that shape's instruction leaf ([[progressive-disclosure]]), so the agent isn't carrying the other three shapes' rules while building the slice.
- **Hash-lock manifest:** locked test files + slice metadata recorded in `ai-docs/<feature-name>/test-lock-manifest.json`. Ceremony product, deleted at squash-merge.

**Gate (planned).** Hybrid gate per [[hybrid-gate-pattern]]:

- **Mechanical anchor:** every slice's work units match its declared shape (per [[slice-shapes]]); file paths/scope declared for each unit; sizing constraints met; for contract-evolving slices, retired-tests list present with rationale; pre-lock [[test-review-technique]] verdict was `accepted` (verified by manifest presence); operator confirms breakdown ran cleanly.
- **Semantic anchor:** the bounce-back mechanism itself. If breakdown completed without bouncing back, the spec was complete enough.

**Technique skills used (planned):** [[test-review-technique]] invoked pre-lock; verdict gates lock application.

---

## /fbk-code-review

Becomes the sixth phase of the pipeline. Its existing bug-finding machinery — intent extraction followed by the detector/challenger detection loop — is preserved unchanged; the new passes are additive on top:

- **[[test-review-technique]] final pass.** Re-validates by reading that locked tests still exercise the behavior they claimed to cover given the implementation's final shape. Catches drift introduced during implementation.
- **[[quality-scan-technique]] top-five.** Pocock-style top-five quality findings on the change set, severity-tagged (critical / substantive / minor). Scan-only — the operator decides what to do with each finding (address inline, spin up a follow-up feature via [[fbk-design]], or defer).

**Gate (planned).** Hybrid gate per [[hybrid-gate-pattern]]:

- **Mechanical anchor:** project tests pass; [[test-integrity-locking]] hash check passes; quality-scan artifact present with severity field populated; test-review final-pass artifact present.
- **Semantic anchor:** test-review final-pass verdict (accepted / needs-revision), with any drift surfaced as findings; quality-scan top-five findings (severity-tagged). Even critical-severity findings surface for operator decision rather than halting the pipeline.

**Technique skills used (planned):** [[test-review-technique]] final pass; [[quality-scan-technique]] top-five; the existing [[adversarial-code-review]] detection layer (intent extraction + detector/challenger) remains unchanged ahead of them.

---

## fbk-test-reviewer (agent)

The agent persona is preserved. What changes is its conceptual role: from a single-purpose agent invoked at fixed points to the embodiment of the [[test-review-technique]] capability invoked at multiple checkpoints by multiple phase skills. Its review scope also widens: at each checkpoint it reviews the full set of tests covering the changed module(s), not only the new or modified tests.

Checkpoints:

- **Pre-lock (breakdown phase). Verdict gates lock application.** Reviews newly-written test tasks before [[test-integrity-locking]] applies hashes. The substantive review — catches failure modes when they're still cheap to fix. If the verdict is `needs-revision`, tests bounce back and the lock manifest is not populated.
- **Final (code-review phase). Verdict feeds the code-review gate.** Re-reviews locked tests against the final implementation. Catches drift. One of two semantic anchors at the code-review gate (alongside [[quality-scan-technique]] findings).

Gains awareness of the four [[slice-shapes]]:

- For contract-preserving slices, the pre-lock review runs over all tests covering the module (not presumed already-reviewed) — validating them, locking them, and surfacing any coverage gap (resolved by adding tests, staying contract-preserving); the final checkpoint applies normally.
- For contract-evolving slices, the agent checks both directions of the retirement list — retired tests should not cover behavior still in scope; new tests should cover only behavior actually new.

**Out-of-ceremony invocation:** via `/test-review`, operators can invoke it to audit existing or third-party tests outside the SDL flow.

---

## /fbk-implement

Formally recognized as the fifth phase in the six-phase model (intent → design → spec → breakdown → **implementation** → code-review). Existing responsibilities are unchanged at this layer of detail:

- Executes the compiled task breakdown with parallel agent teams.
- Per-task verification via the `TaskCompleted` Claude Code hook (the only shipped hook today, wired in `settings.json`).
- Per-wave verification gates fire between waves.
- [[test-integrity-locking]] hashes verified unchanged per task; any modification of a locked test invalidates the hash and trips the gate.

What changes is the *framing*: implementation is named as a phase with its own input/output contract (input: task breakdown + test-lock manifest from breakdown; output: implementation code with passing per-task verification, ready for code-review). The phase's "semantic anchor" is effectively the locked tests themselves — the contract was established upstream, and implementation succeeds when the contract holds. The skill itself does not change behaviorally.

---

## /fbk-spec-review

Preserved as the **mechanism that produces the spec gate's semantic anchor** — not a standalone phase with its own gate. Spec-review is part of the spec phase's gate-closure work.

The [[council-deliberation]] pattern is the existing multi-persona spec review — cold, context-isolated review producing structured observations, applied with multiple specialist personas in parallel and then synthesized. It is related to [[fresh-eyes-technique]] (same discipline) but is not rebuilt or reframed as a "variant" of it.

The spec gate's mechanical anchor verifies the council ran and produced a structured review document. The semantic anchor is the council's synthesized findings, after the spec phase's deduplication step against the grilling log. The existing council roster, threat-modeling pathway, and structural review-gate are all preserved. What changes is the framing.

---

## Test integrity locking (concept)

Hash-locking is an **existing, shipped** Firebreak feature — this design does not introduce it, it preserves it. The shipped mechanism is unchanged: tests are SHA-256 locked by the test reviewer before implementation, any modification trips the verification gate, and the locks are recorded in the feature-directory test-lock manifest. A future cycle intends to wire the lock to hooks so enforcement becomes more "real" and deterministic — today the check runs as part of a gate script. That hook work is explicitly out of scope for this cycle; here we only preserve the current function.

This design's only additions on top of the preserved mechanism:

- **Test-lock manifest gains slice metadata.** Each accepted test file records, in addition to its path and SHA-256 hash, the slice declaration it belongs to and the slice's test-discipline mode (one of the four [[slice-shapes]]).
- **Contract-preserving slices lock pre-existing tests.** For slices that rely on existing tests rather than newly-written ones, those existing tests are also hashed at acceptance and added to the manifest. The manifest becomes "tests the implementation must not modify," not just "tests written this feature."
- **Catching power is judged by reading.** Hash-locking prevents modification but doesn't prove tests catch what they claim; the [[test-review-technique]] checkpoint judges catching power by reading the tests. (Programmatic mutation sampling as an empirical proof was considered and deferred — see the decision spine.)
