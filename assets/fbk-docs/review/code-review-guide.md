# Code Review Guide

## Behavioral Comparison Methodology

Apply behavioral comparison to every code review: describe what the code does, then compare that behavior against the source of truth. The source of truth is the spec's acceptance criteria (ACs), a failure mode checklist, or the user-stated intent that drove the implementation. Start by observing the code's actual behavior, then test whether that behavior matches the intended design; surface any divergence as a finding. This grounds every finding: a reported mistake traces back to a specific divergence — a failed AC, a failure-mode pattern from the checklist, an architectural mismatch, or a contradiction with user-stated intent.

**Do**: Describe what processOrder() does. Compare that behavior to AC-03.

**Don't**: Find bugs in processOrder().

### AC verification precision

When reviewing against spec acceptance criteria, verify each AC individually. Produce a separate sighting for each AC that the code does not satisfy. Do not batch multiple AC violations into a single sighting — each AC represents a distinct behavioral contract.

## Remediation verification

Assign a material fix to a fresh remediator with the accepted behavior and scope, current source revision, verified finding, reproduction evidence, affected paths and tests, and constraints. Preserve decisions, remaining findings, and evidence references in its durable return before a context reset; the full review transcript is not an implicit assignment. Apply the existing Consistency audit to the same demonstrated mechanism and account for each relevant sibling as fixed, already safe, or outside scope with its reason. Shared syntax alone does not authorize new behavior, architectural changes, or speculative rewrites.

Assign independent verification to someone other than the remediator or its experimental helper. When verifying a material fix, read `remediation-verification.md` for behavioral and regression evidence. Keep unavailable execution unresolved and apply the existing investigation escalation policy.

After the independent checks, review the affected behavior and related paths on a stable post-fix snapshot, not only the changed lines. Expand to the full artifact when changed mechanisms or interfaces have broader consequences, and record why that scope is sufficient. Carry unresolved findings and consumed budgets forward; remediation or a fresh reviewer does not reset them. Use the existing review-round and investigation controls for completion, context isolation, and escalation.

## Sighting Format

Sightings are the Detector's output — observations of potential behavioral misalignments discovered during code inspection. Every code sighting must identify the exact mechanism, its realistic trigger,
and caller impact: who reaches the code, what they expect, and what differs.
Record these facts in `mechanism`, `consequence`, and `evidence`; no additional
schema fields are needed. Structural and fragile sightings identify a concrete
coupling and plausible maintenance change instead of inventing a current runtime
failure. Apply the enumerated detection targets; confirm the relevant mechanism
before emitting. Model preferences and pattern matches alone do not qualify.

Sightings are not user-facing; they feed the verification loop. The Detector produces sightings as a JSON array without IDs; the pipeline assigns sequential `id` values (S-01, S-02...) after filtering.

**Required-or-reject** (parser rejects the sighting if missing or empty):
- `title`: mechanism-first, min 10 characters
- `location`: object with `file` (string) and `start_line` (integer); optional `end_line`
- `type`: one of `behavioral`, `structural`, `test-integrity`, `fragile`
- `severity`: one of `critical`, `major`, `minor`, `info`
- `mechanism`: the exact code expression that misbehaves and what it does wrong, min 10 characters
- `consequence`: downstream impact of the mechanism, min 10 characters
- `evidence`: specific code path, line reference, or test case

**Required-with-defaults** (parser fills a default if missing):
- `origin`: one of `introduced`, `pre-existing`, `unknown` (default: `unknown`)
- `detection_source`: one of `spec-ac`, `checklist`, `structural-target`, `audit-pass`, `intent`, `linter` (default: `intent`)
- `source_of_truth_ref`: the specific reference compared against, e.g., "AC-03", "intent claim 4" (default: `""`)
- `pattern`: cross-cutting pattern label (default: `""`)
- `remediation`: one-line fix direction (default: `""`)

## Finding Format

Findings are sightings that survived Challenger verification. The Challenger returns a verdict for each normalized candidate; the runtime rejoins those verdicts with the retained full sightings.

**Challenger verdict fields:**
- `status`: one of `verified`, `verified-pending-execution`, `rejected`, `rejected-as-nit`, `unresolvable`
- `verification_evidence`: required when status is `verified` or `verified-pending-execution`, min 10 characters — the Challenger's own reasoning from the code
- `rejection_reason`: required when status is `rejected`, min 10 characters
- `reclassified_from`: object with `type` and `severity` when the Challenger changed either; empty object `{}` when no reclassification
- `adjacent_observations`: array of strings; empty array `[]` when none observed
- `finding_id`: assigned by orchestrator after verification (F-01, F-02...)

`verified-pending-execution` requires the same independently established mechanism, trigger and consequence as `verified`; execution remains to measure or confirm a stated runtime detail. If execution is necessary to establish whether the defect exists at all, keep the claim `unresolvable` and identify the deciding check. The orchestrator treats it like `verified` with a caveat marker. `rejected-as-nit` indicates the sighting is technically accurate but functionally irrelevant. The orchestrator treats it like `rejected` but counts nit rejections separately.

`unresolvable` means a necessary source or observation is unavailable, or a specific fact remains undecided after inspection. Retain the claim with the missing evidence and deciding check; do not treat it as confirmed or rejected.

## Finding Classification

Classification uses two orthogonal axes. Canonical definitions are here; Detector, Challenger, and the code-review skill reference this section.

### Type axis

Code review is adversarial: compare what the code is supposed to do (the feature's purpose, the caller's assumption, the user-facing promise) against what it will actually do in production. You are looking for mistakes — places where the developer's mental model and the code diverge. AI-generated code adds a second pattern worth watching for: plausible-looking code that doesn't fit the architecture.

Find the mistake first; classify it second. The primary classification test is the ship decision — would you block or request changes on this PR, or would you merge and flag for follow-up?

- `behavioral` — you would not ship. The code does not do what it is supposed to do under conditions it will actually encounter. Always critical or major.

  Includes (illustrative, not exhaustive): wrong/missing output, crash, hang, data loss, broken feature end-to-end, security bypass, state that should update but doesn't, missing guarantees callers depend on, race conditions, silent failures, code paths that cannot execute as designed. "Conditions it will actually encounter" means concurrent execution, database and network errors, resource limits, and attacker-controlled inputs at trust boundaries — these are normal operation, not hypothetical future changes.

- `fragile` — you would ship but flag for follow-up. Correct today; structure invites a future bug. Behavioral takes precedence when both apply. Always major or minor.

- `structural` — demonstrated organization or coupling makes a plausible maintenance change materially error-prone, even when current behavior passes its tests. Request changes before acceptance when the consequence warrants it; minor or info severity does not by itself determine the ship decision. Cite the affected responsibilities and mechanism. Exclude model preferences and arbitrary size thresholds from findings, including suggestions. User-stated preferences recorded as requirements are governing authority. Always minor or info.

- `test-integrity` — a test passes but does not verify what it claims. The test name, docstring, or surrounding context implies coverage that the assertions do not provide. Always critical, major, or minor.

**Disambiguation rules:**
- A naming issue that causes a runtime collision or wrong dispatch is `behavioral` — follow the consequence, not the pattern.
- A bug in a test file's assertion logic is `test-integrity`, not `behavioral`.
- The most common misclassification is downgrading to `fragile` because the trigger is runtime state (DB error, concurrent execution, untested path) rather than a constructible input. Runtime conditions are normal operation — these findings are `behavioral`.

**Type-severity validity matrix:**

|  | critical | major | minor | info |
|--|----------|-------|-------|------|
| **behavioral** | valid | valid | invalid | invalid |
| **structural** | invalid | invalid | valid | valid |
| **test-integrity** | valid | valid | valid | invalid |
| **fragile** | invalid | valid | valid | invalid |

Invalid combinations are rejected by the parser at both Detector and Challenger stages.

### Severity axis

Initial estimate by the Detector, validated or adjusted by the Challenger. Severity is defined by observability.

- `critical` — the next user who exercises the changed code path hits the bug. No special input or timing required. *A human reviewer would block the PR.*
- `major` — a developer can write a test that demonstrates the failure. The triggering input is constructible but not the default path. *A human reviewer would request changes.*
- `minor` — observable only through code reading. No runtime failure can be demonstrated against the current codebase. *A human reviewer might leave a comment.*
- `info` — accurate observation with no recommended action. Excluded from finding count by default. *A human reviewer would not comment.*

### Nit exclusion

Nits (naming, formatting, style, minor inconsistency with no behavioral or maintainability impact) are excluded from findings entirely. They do not receive type or severity classification. The Challenger rejects nit-level sightings from the findings list and counts them separately in the retrospective.

## Orchestration

Use the `fbk-code-review` skill and shared `fbk-review-lenses/review-loop.md` for independent detection and evidence-based challenge. The standalone report records verified findings, unresolved evidence, and actual checks. Managed phase acceptance remains the runtime's responsibility.

## Source of Truth Handling

**Spec available**: Use the spec's acceptance criteria (ACs) and user-visible (UV) steps as the primary comparison target. These define the intended behavior against which the code is measured. When the spec states it carries a contract inherited from a broader project scope verbatim, do not treat the spec's copy as the source of truth for that contract — locate the original and diff the code against it field by field (signature, every invariant, every constant). A review that stays inside the spec cannot catch a transcription divergence: a dropped field, a renamed field, a widened type, or a changed constant looks correct against the spec's own copy.

**No spec available**: Use both the AI failure mode checklist (`fbk-docs/review/ai-failure-modes.md`) and the structural detection targets from `fbk-docs/review/quality-detection.md` for structural issue detection.

**Intent register**: When an intent register has been extracted, include it as an additional comparison target for Detectors alongside specs or the checklist. Challengers verify intent-sourced sightings against the cited claim and the code — reject the sighting if the intent claim itself is inaccurate.

**Post-implementation**: Use the feature spec that drove the implementation as the source of truth. When the spec is finalized after implementation (e.g., during recovery workflows), treat the spec as the authoritative baseline for behavioral comparison.

**Codebase-wide reviews**: When reviewing code that is not tied to a specific change set (e.g., a full codebase audit), default the origin field to `pre-existing` for all sightings. Override to `introduced` only when git history or PR context confirms the issue was created by a recent change.

## Retrospective Fields

Each code review run produces a retrospective capturing these fields:

- **Sighting counts**: total sightings generated, verified findings at termination, rejections, and nit count (raw count, not categorized by type — nits are excluded from the classification system). Include breakdown by detection source (spec-ac, checklist, structural-target, audit-pass, linter). For structural-type findings, include sub-categorization (duplication, dead code, dead infrastructure, bare literals, composition opacity). For audit-pass findings, include sub-categorization by audit (concurrency, logic-inversion, test-integrity, cross-function-api)
- **Verification rounds**: how many detection/verification iterations before convergence; a measure of code opacity or reviewer uncertainty
- **Scope assessment**: code scope reviewed (files, modules, lines of code) relative to context usage (tokens, cache efficiency)
- **Context health**: round count, sightings-per-round trend, rejection rate per round, whether the hard cap (5 rounds) was reached
- **Tool usage**: which project-native tools (grep, file navigation, test runners) were available and used vs. grep/glob fallback
- **Finding quality**: false positive rate (findings the user dismissed), false negative signals (issues the user identified that the Detector missed), breakdown by origin (introduced vs. pre-existing)
- **Intent register**: claims extracted (count and sources), findings attributed to intent comparison (detection source: intent), intent claims invalidated during verification
- **Pass outcomes**: results of the quality scan, final test-review, doc reconcile, and (when run) cross-model review passes — what each surfaced, and any remaining uncertainty

- **Late structural discoveries**: identify the affected responsibility, concrete maintenance risk, detection phase, and correction. Trace a missed prevention opportunity to the accepted design or spec with original source/event references when supported; distinguish an implementation departure from an upstream defect. Record uncertainty when attribution is unavailable. Use the existing observation record for actionable process failures, following `workflow/retrospective.md`; do not create a second ledger.
