## Entry

Read the spec from `ai-docs/<feature-name>/<feature-name>-spec.md`. Fail fast if the spec gate does not pass — do not proceed to classification without a structurally complete spec.

## Classification process

Analyze the spec and project context to determine which council agents to invoke and how.

**Inputs**:
- Spec content: what the feature does, which systems it touches
- Project context: existing architecture, project-level threat model, complexity signals
- Stage context: what kind of review is needed at this point

**Outputs**:
- Which agents to invoke (subset of 6, or all)
- Invocation mode: solo, discussion, or full council
- Brief rationale for each agent selection — present this to the user before proceeding

Present the classification with rationale and proceed. The user can intervene to adjust, but the default is forward motion. Classification is an operational decision where you have better signal than the user; it does not require an active human decision.

## SDL concerns table

| SDL concern | Primary | Supporting | Review prompt framing |
|-------------|---------|-----------|----------------------|
| Architectural soundness | Architect | Builder | "Evaluate the technical approach for integration risks, performance implications, and conflicts with existing architecture. When the spec describes integrating with or extending existing modules, also verify: (1) Pattern consistency — does the proposed approach follow the existing pattern or introduce a parallel path? (2) Integration point existence — do the integration points referenced actually exist in the code? (3) Convention visibility — are there conventions in existing code that the spec doesn't mention but tasks will need? Flag these for breakdown discovery." |
| Over-engineering / pragmatism | Builder | Advocate | "Identify areas where the design is more complex than the requirements justify" |
| Quality: testing strategy and impact | Guardian | Analyst | "Validate that the testing strategy covers all acceptance criteria at the appropriate level (unit, integration, e2e). Verify that impacted existing tests are identified — search the test suite for coverage of affected files and functions. Flag any acceptance criteria that lack a corresponding test plan." |
| Threat modeling | Security | Architect | "Identify trust boundaries, data flows, entry points, and threats; compare against project threat model" |
| User impact / scope creep | Advocate | Builder | "Evaluate whether each requirement serves the stated user need without unnecessary scope expansion" |
| Measurability | Analyst | Guardian | "Verify that acceptance criteria are quantifiable and that success can be measured, not just asserted" |
| Documentation impact | (deterministic) | — | Verify the spec's documentation impact section is present and specific — not "update docs" but which documents and what changes. Cross-check against the feature's scope to catch missing doc impacts. |

## Architecture Reviewer Brief — Contract Drift

When the feature has a `design/contracts.md`, the architect additionally checks for contract drift between the design and the spec. Report each of the following as an `informational` finding — the reviewer surfaces; the operator decides:

- A spec-added `IF-S-NN` contract that is absent from design (the spec minted an interface the design never enumerated). Report the specific `IF-S-` identifier and note that design has no corresponding entry.
- An `IF-D-NN` entry whose identifier is preserved in the spec but whose name or signature has materially changed from the design's original. Report the `IF-D-` identifier, the design value, and the spec value so the operator can confirm the change is intentional.
- A count or name mismatch between the design page's `IF-D-NN` entries and what the spec carries or excludes. Report the totals on each side and name the entries that appear in one but not the other.

All three conditions are `informational`, not blocking. Record them in the review document under the Architectural soundness concern so they are visible at breakdown.

## Residual ambiguity hunt

A complete spec has driven every requirement down to concrete definitions: every field name, data shape, contract, function or class signature, and the specifics of any observable behavior is pinned down — extracted from the existing code when the feature integrates with it, or decided with the operator when the piece is new.

The reviewing perspectives actively hunt for the opposite: any name, shape, contract, signature, or observable behavior that is still vague, hand-waved, or parked "to be decided later" while the spec claims to be done. The architecture perspective owns the structural side — undefined contracts, signatures, field names, and data shapes. The quality perspective owns the behavioral side — an asserted behavior (a component logs, emits, records, retries, validates) that never says what is recorded or how a test would catch it breaking.

Also hunt for the reverse failure: two acceptance criteria, or an acceptance criterion and a stated design invariant, that are each concrete on their own but assert mutually exclusive behavior for the same operation. A spec can fail this way while every individual item looks fully specified — the gap is between two definitions, not inside either one.

Treat each such gap as a blocking finding, not a nitpick. Name the specific undefined item and what concrete definition would resolve it. A spec carrying this kind of open vagueness has not passed — this is the floor the reviewers carry, and there is no automated check behind it.

## Independent test-review

After the council reaches a clean state and the review document is stabilized, an independent test-review runs against the stabilized spec. It is distinct from the council: it carries no council memory and no council findings, and it reads the spec on its own. For each requirement it asks one question — does its planned test actually prove the behavior, such that the test would fail if that behavior broke? It also checks that every declared integration seam has end-to-end coverage planned. The pass emits a verdict that the gate verifies, so an unproven testing strategy stops the spec from advancing rather than slipping through to breakdown.

## Classification signals

| Agent | Invoke when... |
|-------|---------------|
| Architect | New system boundaries, data flow changes, integration with existing systems |
| Builder | Complex technical approach, scope that could be simplified, aggressive sizing |
| Guardian | Behavioral changes needing test coverage, failure-sensitive code paths |
| Security | Auth/authz, data storage, external APIs, trust boundary changes |
| Advocate | User-facing behavior changes, scope that may exceed stated user need |
| Analyst | Quantifiable success conditions, claims requiring evidence, metrics |

## Invocation modes

- **Solo**: One perspective clearly dominates (e.g., pure security concern → Security agent alone).
- **Discussion**: Concerns cross boundaries (e.g., security vs. usability → Security + Advocate). 2–3 agents review the spec, share findings, and build toward consensus on blocking issues before synthesis.
- **Full council**: Multiple classification signals fire or the feature is high-stakes.

One thorough pass beats multiple fast passes. Give each agent a detailed, stage-specific prompt — not a brief generic one. Prefer 2–3 agents with thorough instructions over 6 agents quickly.

## Invoking the council

Route all council invocations through the existing `/fbk-council` skill. Do not reimplement council infrastructure.

In each agent's review prompt, include:
- The SDL concern the agent owns (from the table above)
- The exact prompt framing from the SDL concerns table
- Relevant spec sections scoped to that agent's focus area

Frame prompts with SDL context. Generic "review this spec" prompts do not produce actionable SDL findings.

## Threat model determination

Every feature requires an active decision — not a passive default in either direction.

1. Summarize the feature's security-relevant characteristics: data touched, trust boundaries crossed, new entry points, auth/access control changes.
2. Ask the user: "Does this feature need a threat model?" Present the security summary as context.
3. Record the decision and rationale in the review document regardless of the answer.

**If yes**: Read project threat model (`ai-docs/threat-model.md`) if it exists. Load `fbk-sdl-workflow/threat-modeling.md` for the detailed process. Produce `<feature-name>-threat-model.md` containing:
- Assets, threat actors, trust boundaries
- Identified threats (STRIDE or equivalent) with mitigations and residual risks
- "Proposed project model updates" section: specific additions, removals, or modifications to the project-level threat model, with rationale for each change

The user reviews and approves proposed project model updates before the project model is modified.

**If no**: Record in the review document: decision + rationale (e.g., "No new trust boundaries, no data handling changes, no external API interaction"). Security concerns still surface through normal review if the Security agent is invoked — the skip applies only to the structured threat model artifact.

## Review document structure

Begin the review document with a metadata line listing the perspectives that were invoked:

```
Perspectives: Security, Architecture, Quality
```

Organize findings by SDL concern, not by agent.

When titling a finding-grouping section with an SDL concern name, use the exact concern name from the table above. Do not paraphrase or shorten it to a form that begins with the word "Testing" — the gate parser reserves `## Test*` headings for the canonical testing-strategy section.

Each finding includes:
- **Severity**: `blocking` (must resolve before breakdown), `important` (should address), or `informational` (note for awareness)
- **Category**: which SDL concern from the table above
- **Description**: actionable and specific — not generic observations

Generic observations ("consider adding more tests") do not constitute findings. Each finding must name the specific gap and what resolution looks like.

## On re-run

When the user revises a spec and re-runs the spec review, replace the review document entirely. Do not append to or merge with the prior review. The review reflects the current spec state — stale findings create confusion. Previous reviews are recoverable from git history.

## Verification gate

**Structural prerequisites** (check deterministically):
- Review document contains findings from all classified (or user-selected) perspectives
- Each finding has severity classification (blocking / important / informational)
- Threat model determination recorded: decision + rationale
- If threat model requested: document exists with required sections (assets, threat actors, trust boundaries, threats)
- Testing strategy coverage entries for all three categories (new tests, impacted tests, infrastructure) — empty categories have explicit "none" with justification
- Independent test-review reached an `accepted` verdict — `test-review-spec.md` is present in the feature folder and its verdict is accepted

**Semantic evaluation** (human decides):
- Blocking findings genuinely resolved — addressed in spec revision or accepted with documented rationale and risk owner
- Findings are actionable and specific, not generic observations
- No residual ambiguity remains — every name, shape, contract, signature, and observable-behavior specific is concrete, with any leftover vagueness raised as a blocking finding (see the residual ambiguity hunt above)

## Transition

After presenting findings:
1. Run structural prerequisites.
2. If blocking findings exist: "There are N blocking findings. Would you like to revise the spec to address them, or accept with documented rationale?"
3. If the user accepts blocking findings: record the rationale and risk owner in the review document before advancing.
4. If all resolved: "The review is structurally complete. Would you like to proceed to task breakdown?"
5. Before invoking `/fbk-breakdown`: confirm all artifacts are written to disk; summarize (feature name, number of findings by severity, threat model decision, gate result); compact context.
6. If agreed: invoke `/fbk-breakdown <feature-name>`.
