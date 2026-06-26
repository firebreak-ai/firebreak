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

Each observation is a **dash-prefixed line** (`- ` prefix) within its category section. No other format is used for observations — prose paragraphs and numbered items are prohibited, including for critical observations. The gate check for the Critical section scans each line and tests whether the stripped line starts with `-`; any dash-prefixed line is treated as an open observation. A prose sentence or a numbered item beginning with a digit genuinely bypasses the check; a dash-prefixed line at any indentation level does not.

The gate check for the Critical section:

- **Gate fails** when `## Critical` contains any dash-prefixed line after dedup.
- **Gate passes** when `## Critical` is empty or contains only prose notes (for example, "No critical observations.").

This gate is enforced by `fbk.gates.intent` and `fbk.gates.design` via `_critical_section_has_content`. The output contract — three headings, dash-prefixed observations, gate-fail on any dash-prefixed critical line — must be preserved verbatim across any migration of the fresh-eyes preset.

The fresh-eyes report is written to:

```
ai-docs/<feature>/fresh-eyes-<artifact>.md
```
