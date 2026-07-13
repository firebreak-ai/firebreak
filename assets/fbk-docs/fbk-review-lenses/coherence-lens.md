# Coherence Review Lens

This page defines the coherence review lens in full. The coherence review is a new capability with no prior gate contract; this page is its complete specification.

The coherence review checks whether the contracts that the tasks in a breakdown declare and depend on are mutually consistent — that every producer-declared contract matches what its consumer actually expects.

---

## Why this capability exists

When a breakdown fans work out across multiple parallel tasks, each task author may independently decide what an interface looks like, what fields a handoff carries, or what a shared data shape requires. Two tasks can be internally correct — each consistent with the spec's own description — while still being inconsistent with each other at the seam between them. This inconsistency is invisible to any review that looks at one task in isolation. The coherence review is the review that looks at the seams.

This capability is the prerequisite for the breakdown-decomposition feature: fanning a breakdown across more parallel authors raises the risk of contract drift between authors. The coherence review is what makes that safe.

---

## What counts as a "contract" for this review

The coherence reviewer checks only explicitly declared contracts — material that is written down in a design artifact or spec as a named commitment. Implicit assumptions that are nowhere documented are outside scope.

The categories:

- **Declared interface signatures**: a function or method signature specified in `design/contracts.md` or named in the spec's technical approach, including parameter types and return shapes.
- **Named data shapes with required fields**: any data structure documented as having specific required fields, in the design contracts page or in a spec section that pins field names and types.
- **Documented handoff seams**: any cross-module or cross-task interaction declared as an integration seam in the spec, including what one side sends and what the other side expects to receive.
- **Locked type contracts**: any contract from `design/contracts.md` that was carried into the spec's interface-contracts section. Design-originated contracts use the design-origin identifier; spec-originated contracts (minted during spec authoring for blast-radius discoveries) use the spec-origin identifier. When a design contract is carried into the spec, its design-origin identifier is preserved verbatim — the identifier does not change namespace. The coherence researcher checks both the design contracts page and the spec's interface-contracts section as sources of truth; when they conflict on a contract's fields, the spec's version governs (it is downstream, and the carry rule requires it to be consistent).
- **Package-wide obligations**: a behavioral rule stated once in the design's cross-cutting page or a breakdown conventions artifact (when one exists), applying to every task whose scope matches a stated condition — for example, "every method that touches the database logs unexpected errors."

Consumer sets may be many-to-one: one producer may have multiple consumers, and the coherence review checks each consumer's declared expectation against the single producer's declaration.

**Out of scope**: informal comments in task files that say "the caller should do X" without a corresponding contract declaration; naming conventions not documented as contracts; runtime behaviors not specified in any design artifact. These are out of scope for this iteration.

### When the coherence review trivially accepts

The trivial-accept (skip the full detection passes and write a one-line note plus `Verdict: accepted`) applies only when **both** of these hold — if either a contract or a seam is present, the corresponding detection passes run:

1. **No contracts to check**: the spec's interface-contracts section carries only the no-contracts sentence ("No new or changed contracts in this feature.") and the design contracts page has no contract entries. An **absent `design/contracts.md` entirely** satisfies this condition (treated as "no design contract entries"), and routes to trivial-accept — not to a missing-source loud failure.
2. **No seams to verify**: the spec's technical approach declares no integration seams (the producer→consumer seam checklist is empty).

When both hold, the trivial-accept applies; if only one holds, the review runs the detection passes for the dimension that is present. The coherence review is still invoked in every case — its trivial-accept verdict is evidence that the upstream SDL correctly eliminated ambiguity at earlier gates, not a signal that the review was skipped.

**Absent `design/contracts.md` routing:** when `design/contracts.md` does not exist, treat it as "no design contract entries" and route to trivial-accept (assuming the no-seams condition also holds). Do not treat an absent contracts file as a loud failure. The loud failure (IF-S-01) applies only when the *lens file itself* is absent.

**Trivial-accept artifact shape:** write a single one-line note stating that no contracts and no seams were found, followed by the standard verdict line:

```
No contracts or seams declared — trivial-accept applies.
Verdict: accepted
```

---

## Lens identity

This lens reviews the task set of a compiled breakdown to determine whether every producer-declared contract is consistent with what each consumer task declares it depends on. The core question is: if each task were implemented exactly as written, would the tasks' shared seams connect?

```
output_mode: finding
output_contract: verdict-contract
```

---

## Finding types

| Type | Definition | Ship decision |
|---|---|---|
| `contract-mismatch` | A producer's declared contract and a consumer's expected contract diverge on a specific named field, type, required presence, or behavior. The producer says X; the consumer expects Y. | Block — a task built against a mismatched contract produces a broken seam at integration time. |
| `contract-gap` | A consumer task depends on a contract that no producer task declares. The dependency has no defined source. | Block — building against an undefined contract produces a broken seam. |
| `contract-ambiguity` | A contract is declared but its specification is incomplete or contradictory across two sources. The consumer cannot determine from the declaration which interpretation is correct. | Request changes — an ambiguous contract produces unpredictable integration behavior. |
| `orphan-declaration` | A producer task declares a contract that no consumer task references. Not necessarily wrong, but worth surfacing. | Comment — may be infrastructure shipped ahead of its consumer; trace provenance before flagging as dead. |

---

## Severity levels

| Severity | Observability | Reviewer action |
|---|---|---|
| `critical` | Any task implementing against this mismatch will produce a broken seam on the first integration attempt. No special conditions required. | Block. |
| `major` | The mismatch is real but only manifests under specific conditions (a particular input shape, an optional field being present, a specific call sequence). A developer can demonstrate the failure. | Request changes. |
| `minor` | The divergence is observable through reading but no runtime failure can be demonstrated against the current task descriptions. | Comment. |

---

## Type-severity validity matrix

| | critical | major | minor |
|---|---|---|---|
| `contract-mismatch` | valid | valid | valid |
| `contract-gap` | valid | valid | invalid |
| `contract-ambiguity` | invalid | valid | valid |
| `orphan-declaration` | invalid | invalid | valid |

```lens-matrix
types: [contract-mismatch, contract-gap, contract-ambiguity, orphan-declaration]
severities: [critical, major, minor]
matrix:
  contract-mismatch: [critical, major, minor]
  contract-gap: [critical, major]
  contract-ambiguity: [major, minor]
  orphan-declaration: [minor]
required: [title, location, type, severity, mechanism, consequence, evidence]
```

---

## What to look for (researcher instructions)

The researcher reads the full set of task files, the design contracts document, and the spec's integration seams section cold. The goal is to find every place where two tasks share a boundary and their descriptions of that boundary differ.

### Pass 1 — Contract inventory

Read every task file. For each task, extract:
- Every interface, data shape, or handoff the task declares it will produce (the producer side).
- Every interface, data shape, or handoff the task declares it will consume or depend on (the consumer side).
- Every integration seam the task references, whether or not it provides the contract.

Build a flat inventory: producer declarations and consumer expectations, each tagged with the task that contains them.

### Pass 2 — Seam matching

For each consumer expectation, locate the producer declaration it should match. A match exists when a producer task names the same interface, shape, or seam the consumer depends on.

Flag mismatches: producer says X, consumer expects Y — these are `contract-mismatch` findings.
Flag gaps: consumer depends on something no producer declares — these are `contract-gap` findings.
Flag orphans: producer declares something no consumer references — these are `orphan-declaration` findings, typically minor.

### Pass 3 — Design contracts alignment

Read `design/contracts.md`. For each contract listed there, check whether the task descriptions are consistent with the design contract. A task that describes a contract differently from how the design documents it is a `contract-mismatch` against the authoritative design declaration.

### Pass 4 — Spec seam cross-check

Read the spec's integration seams section. Every declared seam in the spec should have at least one task that covers the producer side and at least one that covers the consumer side. A declared seam with no corresponding task coverage is a `contract-gap`.

### Pass 5 — Prescribed-code parity for declared values

For any value, field, or behavior that the spec, `design/contracts.md`, or a declared seam pins (a specific literal, a validity rule, a required transformation), locate every task whose prescribed code references that same value and compare the code itself — not just each task's prose description of it. A `contract-mismatch` exists when one task's code accepts, produces, or transforms the value in a way another task's code does not expect, even when neither task's prose states the divergence.

### Pass 6 — Package-wide obligation coverage

For every package-wide obligation stated in the design's cross-cutting page or a breakdown conventions artifact (when one exists), identify which task discharges it — either by implementing it directly or by calling a shared helper task that implements it — for every task whose scope matches the stated condition. An obligation with no discharging task is `critical`; an obligation discharged in only some of the matching tasks is `major`. Both are `contract-gap` findings.

### Detection source tags

Tag each finding with its detection source:
- `contract-inventory`: finding from pass 1 or 2, comparing task declarations to each other.
- `design-contracts-alignment`: finding from pass 3, comparing a task to the design contracts document.
- `spec-seam-crosscheck`: finding from pass 4, comparing task coverage to declared seams.
- `prescribed-code-diff`: finding from pass 5, comparing actual prescribed code across tasks that reference the same declared value.
- `obligation-coverage`: finding from pass 6, tracing a stated package-wide obligation to its discharging tasks.

---

## Source-of-truth handling

The source of truth for this review, in priority order:

1. `design/contracts.md` — the locked and declared contracts. When a task description conflicts with this document, the document wins; the task is wrong.
2. The spec's integration seams section — the declared seam set. When a task claims a seam that the spec does not declare, that is a new seam that was not reviewed during spec review.
3. The task files themselves — for consumer-vs-producer comparisons where neither the contracts document nor the spec specifies the exact shape.
4. The design's cross-cutting page and a breakdown conventions artifact (when one exists) — the sources for package-wide obligations checked by pass 6.

When the spec states a contract is inherited from a broader project scope verbatim, the researcher must locate the original contract document and compare the task's description against it field by field, not against the spec's copy.

The spec's interface-contracts section is the authoritative source for contracts at coherence-review time. Design contracts that were carried into the spec appear there with their original (design-origin) identifiers. A contract that appears in the design contracts page but is absent from the spec's interface-contracts section — and is not listed in the spec's excluded-contracts section — is a contract the spec gate should have caught as an error. If the coherence reviewer encounters such a case, surface it as a contract-gap finding: the producer's design intent was never ratified into the spec.

---

## Challenger instructions

### Provenance for orphan-declaration findings

For any finding tagged `orphan-declaration`, the challenger traces whether the declared contract has a known future consumer — in a planned downstream feature, in an existing calling module outside this task set, or in a spec section that describes a second phase. If the trace finds a consumer, reject the finding. If the trace is ambiguous (infrastructure shipped ahead of its consumer), surface the finding with the ambiguity noted rather than rejecting it.

### Reclassification guidance

- A mismatch that only affects an optional field is major, not critical, unless the consumer treats that field as required.
- A gap in an explicitly declared seam is critical. The coherence review does not surface gaps in informally implied interfaces — those are outside scope (only explicitly declared contracts are reviewed). If the researcher surfaces a candidate based on an informal assumption rather than a declared contract, the challenger rejects it on scope grounds: "this dependency is not declared in any design artifact or spec section and is therefore out of scope for this review."
- `contract-ambiguity` is always major or minor; it cannot be critical because an ambiguous contract might resolve correctly.

---

## Verdict contract

**Artifact path:** `ai-docs/<feature>/coherence-review.md`

**Passing condition:** no confirmed contract mismatches, contract gaps, or contract ambiguities. Orphan declarations at minor severity do not block.

**Failing condition:** any confirmed `contract-mismatch` or `contract-gap` finding at any severity; any confirmed `contract-ambiguity` at major severity.

**Verdict line format:**
```
Verdict: accepted
```
or
```
Verdict: needs-revision
```

The verdict line is the final line of the artifact. The gate locates it by its `Verdict:` prefix. Any trailing whitespace or line ending variation that makes the prefix unlocatable is a gate failure.

---

## SDL placement

Post-breakdown, pre-implementation. The breakdown skill assembles the task manifest, runs the pre-lock test-review, runs the task-review checkpoint, then invokes the coherence review. The implementation phase gate requires `Verdict: accepted` from `coherence-review.md` before implementation begins.

A new gate step must be added to the breakdown-to-implementation transition to check this artifact. The gate logic:

1. Check that `ai-docs/<feature>/coherence-review.md` exists.
2. Locate the `Verdict:` line.
3. Require `Verdict: accepted`. Anything else — file absent, verdict line absent, verdict value other than `accepted` — is a gate failure.

---

## Future extension

The contract universe defined here (explicit declared contracts only) is the first iteration. A future iteration may extend the coherence review to cover:

- Informal caller assumptions documented as code comments rather than design artifacts.
- Runtime behavioral contracts (retry behavior, timeout handling) that are not stated as a package-wide obligation anywhere — pass 6 covers obligations stated in the design's cross-cutting page or a conventions artifact, but not undocumented runtime behavior.
- Cross-feature contract dependencies when a feature reuses a contract from an adjacent feature.

Each of these extensions adds a new detection pass to this lens without changing the loop.
