# Grilling log — interface-contracts (intent phase)

Decisions resolved during intent-phase grilling. Each block records the question,
recommendation, operator answer, and a reflect-back confirmation.

### reconciliation-failure-mode-coverage

- Question: The operator already decided that reconciliation between design's
  contract list and the spec happens at spec review. Does spec review structurally
  cover all three failure modes — (1) design says more than spec carries,
  (2) spec says more than design carries (including renames), and (3) drift after
  spec gate has passed or mid-stream realization that design needs to change —
  or does any mode need its own answer?
- Recommendation: Modes 1 and 2 are structurally covered (gate handles 1,
  spec review handles 2). Defer mode 3 as a known limitation, flagged in the PRD,
  rather than building snapshot-hash or breakdown-precondition machinery inside
  this feature.
- Answer: Modes 1 and 2 are covered. Mode 3 is operator-driven: the operator
  sometimes realises mid-stream that the design needs to change. The agent
  elevates drift during spec review; the operator decides the response —
  instruct the agent to update the design to match the spec change, or stop
  and realign if the deviation was unintended. No automatic re-trigger
  mechanism is required.
- Confirmed: Reconciliation responsibility lives at the spec review layer for
  detection. Modes 1 and 2 are mechanically covered (gate + review). Mode 3 is
  operator-handled: spec review's job is to reliably elevate drift; the
  operator chooses the response (update design, re-run spec gate, or revert
  the design change). This feature does not need its own temporal-drift gate
  machinery, but spec review must reliably elevate drift when it sees it.

### deliberately-dropped-contracts

- Question: When a spec author intentionally does not carry a contract from
  design (scope cut after design, design over-enumerated, contract turned out
  not to be needed), the deterministic design-anchor gate check fires on the
  "missing" id. Should the spec author resolve this with a spec-side marker
  (e.g., an `## Excluded contracts` block with rationale) so the gate sees
  the id as accounted for, or by going back and removing the id from
  `design/contracts.md`?
- Recommendation: Spec-side marker. Design represents a prior decision and
  should not be rewritten as scope shifts; the exclusion rationale is itself
  information and belongs near the current decision. Gate becomes:
  every design id is either present in `## Interface contracts` or present
  in `## Excluded contracts` with a non-empty rationale. Free-text rationale
  is enough; gate error message should include two-paths-to-resolve guidance.
- Answer: Shape (a) — spec-side `## Excluded contracts` block with free-text
  rationale. Gate error message should include the two-paths guidance.
  Additional rationale for not back-updating design: design artifacts are
  ephemeral scaffolding under `ai-docs/<feature>/` and are deleted at
  squash-merge, so backward-updating design is churn on something about to
  be removed.
- Confirmed: Drop-handling lives spec-side. Spec authors who intentionally
  exclude a design-enumerated contract write an `## Excluded contracts` entry
  with a free-text rationale; the gate passes when every design id is either
  carried in `## Interface contracts` or accounted for in `## Excluded
  contracts`. The gate's failure message must teach the convention by naming
  the missing id, pointing at its design anchor, and stating the two
  resolution paths. Design pages are not back-updated — they are ephemeral
  spent scaffolding deleted at squash-merge, and the spec is the canonical
  record of what was actually shipped.

### covers-semantics-ac-coverage

- Question: The deterministic gate already requires every contract's `covers:`
  list to be non-empty (every contract covers ≥1 AC). Should the inverse rule
  also be enforced — that every AC must be covered by ≥1 contract — as a
  deterministic gate check, mirroring the existing slice-block rule that
  every behavior in the inventory must appear in some slice's `covers:`?
- Recommendation: Add it as the 8th deterministic gate check. Closes a real
  silent-gap hazard (an AC sits in the spec with no contract responsible for
  delivering it). Mirrors the existing slice→behavior coverage pattern.
  Cheap to implement (regex out AC-NN from acceptance criteria and from each
  contract's covers, compute set difference). The "is the *right* contract
  covering this AC?" question stays in spec review as part of the locked
  mapping-fit judgment.
- Answer: Add the AC coverage check, with free-text rationale for any
  exemptions. Confirmed (on reflect-back) that exemptions live in a sibling
  spec-side block — `## Uncovered acceptance criteria` — parallel to
  `## Excluded contracts`, with the same set-difference + rationale-present
  check shape.
- Confirmed: Add an 8th deterministic gate check — every `AC-NN` from
  `## Acceptance criteria` must be either covered by some contract's
  `covers:` list, or documented in an `## Uncovered acceptance criteria`
  block with a free-text rationale. The gate's failure message follows the
  Q2 pattern: name the specific AC, state two resolution paths — "Add it to
  some contract's `covers:` list, or document it in
  `## Uncovered acceptance criteria` with a rationale." Two spec-side
  escape-hatch sections in the contracts feature, one per direction:
  `## Excluded contracts` covers design→spec drops; `## Uncovered
  acceptance criteria` covers spec ACs that intentionally have no contract.

### design-ref-brownfield-blast-radius

- Question: The spec enumerates all affected contracts on touched modules,
  including pre-existing ones that were not introduced by this feature's
  design. Those entries have no real design-ref to point at, but gate
  check #2 requires the `design-ref:` field be present. Should the spec
  author use a single magic value (`design-ref: none`) for both
  "no design reference and none expected" and "pre-existing brownfield
  contract", or a two-value scheme that distinguishes them?
- Recommendation: Two-value scheme. Use `pre-existing` for blast-radius
  brownfield entries (contracts that existed before this feature) and
  reserve `none` for the genuinely-absent case. Reasoning: the two cases
  mean different things and downstream agents (test reviewer, code review,
  breakdown) can apply different rules — e.g., "test that an existing
  contract still holds" vs "test a brand-new contract." Cost is one extra
  magic value in the convention; benefit is preserved semantic distinction.
  Defer free-text reference values (git SHA, PR link) as a v2 enhancement —
  unproven need.
- Answer: Agree.
- Confirmed: `design-ref:` accepts three value shapes — a path or anchor
  into this feature's `design/contracts.md`, the literal `none` (truly no
  design reference and none expected), or the literal `pre-existing`
  (contract existed before this feature; this entry is a blast-radius
  enumeration so downstream phases can scope tests against it). The
  design-anchor check (#6) walks design's contracts list and verifies each
  design id is accounted for in the spec; pre-existing spec entries cause
  no false positive because the check does not walk spec→design. No
  free-text reference values in v1; revisit if a future feature surfaces
  the need.

