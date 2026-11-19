# Fresh-Eyes Lens

## 1. Lens identity

This lens runs an adversarial read-only pass on any document or artifact. The reviewer treats the author as unreliable and surfaces what the author missed, grouped by severity. The core question is: what would a cold reader, without authoring context, notice that the author did not?

```
output_mode: scan
output_contract: observation-format
```

This is a scan-mode lens. It carries no `lens-matrix` block and bypasses `validate_sighting()`. Observations are checked only against the structural output schema defined in the observation-format section below.

---

## 2. Finding types

Not applicable. This is a scan-mode lens. Observations are categorized by severity (Critical / Substantive / Minor), not by finding type. No type field is emitted.

---

## 3. Severity levels

Three severity levels apply to fresh-eyes observations:

| Level | Definition | Action |
|---|---|---|
| Critical | A flaw that, if unaddressed, would cause the artifact to fail its stated purpose or violate an explicit contract it declares. | Gate fails; author must address before proceeding. |
| Substantive | A real problem that degrades quality or correctness but does not make the artifact entirely wrong. | Reported; author decides whether to address. |
| Minor | A wording, consistency, or clarity issue with no behavioral consequence. | Reported for awareness. |

---

## 4. Type-severity validity matrix

Not applicable. This is a scan-mode lens. Scan-mode lenses carry no `lens-matrix` block. The observation severity levels above define the full vocabulary; observations are emitted under the appropriate `## Critical`, `## Substantive`, or `## Minor` heading.

---

## 5. What to look for

The researcher reads the artifact without authoring context. Approach:

- **Contradiction detection**: find places where two sections of the same document make incompatible claims — where the overview says one thing and the implementation or error-handling sections say another.
- **Contract-vs-behavior mismatch**: identify where the artifact declares a guarantee (invariant, return contract, error contract) and then describes behavior that violates it.
- **Silent assumption surfacing**: identify assumptions the author made that are not stated and that a caller or implementer could reasonably get wrong.
- **Missing constraint identification**: find cases where the artifact omits a constraint or edge-case that the described behavior clearly requires.
- **Ambiguous specification**: identify places where a phrase or requirement is interpretable in more than one way, such that two implementers could produce incompatible results without either being wrong.

Each observation names the specific location and mechanism. "Section X says Y, but Section Z says the opposite" is an observation. A general statement of concern without a specific location is not.

---

## 6. Source-of-truth handling

The researcher has no prior authoring context. The artifact itself is the primary source. The researcher compares the artifact's stated invariants, contracts, and guarantees against the behaviors the artifact describes — internal consistency is the main check.

When the invoker provides cross-cutting convention files alongside the artifact (a shared interface definition, a naming registry, a conventions document), the researcher compares the artifact against those documents as reference material. Convention files are comparison anchors, not a record of the author's reasoning.

When the artifact proposes a change to existing code or documentation, assess the
future state it specifies against its own guarantees and current governing
requirements. An authorized contract change can supersede the pre-change state;
ordinary planned implementation differences are not defects. A self-consistent
proposal can still violate compatibility or another obligation that remains in
force. Establish the authority for the change from supplied original sources;
identify missing deciding evidence rather than treating the proposal as its own
authorization.

Treat a deferral as valid later-phase scope when it preserves current obligations
and leaves the current phase decision supportable. Surface a concrete contradiction,
or a deferred decision required now to satisfy a governing constraint or make the
artifact usable for its stated phase. Ordinary later deliverables and private
implementation choices need not be settled early. Explain why a questioned deferral
prevents the current decision; an author's deferral note alone neither proves a gap
nor waives an existing obligation.

When no cross-cutting files are provided, the researcher works from the artifact alone.

---

## 7. Challenger instructions

Not applicable. Fresh-eyes is a zero-challenger preset (degenerate cardinality). No challenger is spawned. The researcher's observations are the loop's final output.

---

## 8. Observation format (`output_contract: observation-format`)

Fresh-eyes observations are grouped under three section headings, in this order:

```
## Critical
## Substantive
## Minor
```

Write each observation as a bullet under its severity heading. If a category has no observations, state that explicitly. Save the report under the project's review directory, default `reviews/fresh-eyes-<artifact-name>.md`. The report is advisory; it does not provide managed phase acceptance.
