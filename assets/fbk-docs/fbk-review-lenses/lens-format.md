# Review Lens Format

A review lens is a markdown document that carries all the type-specific knowledge a review type needs. The researcher and challenger receive it at spawn; nothing in their generic personas changes when the lens changes. Swapping the lens is what produces a different review type.

This page defines what a lens must contain so the researcher and challenger can use it predictably, and where lenses live.

---

## Location

All review lens documents live at:

```
fbk-docs/fbk-review-lenses/<type>-lens.md
```

Where `<type>` is the review type name: `code`, `test`, `task`, `coherence`. (`test-plan` is a deferred review type — no `test-plan-lens.md` ships yet.)

The shared detection document lives at:

```
fbk-docs/fbk-review-lenses/shared-detection.md
```

A lens that uses shared detection passes includes this document by reference: "Read `shared-detection.md` for the [named passes] this lens uses." It never copies the content into itself.

---

## Required sections

Every lens document must contain these sections in this order. A lens that omits a required section is incomplete and must not be used.

**Universal sections** (all lenses, all modes):

1. Lens identity
2. Finding types
3. Severity levels
4. Type-severity validity matrix
5. What to look for
6. Source-of-truth handling
7. Challenger instructions

**Conditional output-contract section** (one of the following, keyed off the lens's declared `output_contract`):

- `verdict-contract` — required when `output_contract: verdict-contract` (verdict-bearing lenses: test, coherence, task)
- `findings-artifact` — required when `output_contract: findings-artifact` (code review)
- `observation-format` — required when `output_contract: observation-format` (scan-mode lenses: fresh-eyes, quality, doc-reconcile)

The conformance check reads the `output_contract` declared in the lens-identity section to determine which output-contract section the lens must carry. A lens that carries the wrong output-contract section, or omits its declared one, fails the conformance check.

### 1. Lens identity

A one-sentence statement of what this lens is for: which artifact type it reviews, from what perspective, and what the core question is.

Example: "This lens reviews test code to determine whether each test would actually fail if the behavior it claims to cover were broken."

This section also declares two required fields:

**`output_mode`**: `finding` or `scan`.

- `finding` — candidates are finding-shaped and route through `validate_sighting()` with the lens's machine-readable matrix below. Lenses: code, test, task, coherence (and test-plan once it ships — currently deferred).
- `scan` — a non-finding output schema that bypasses `validate_sighting()` and is checked only against this lens's structural output schema. Lenses: fresh-eyes, quality, doc-reconcile.

**`output_contract`**: the kind of output-contract section this lens carries. Valid values:

- `verdict-contract` — the lens's output includes a `Verdict:` line. Use for verdict-bearing finding-mode lenses (test, coherence, task).
- `findings-artifact` — the lens's output is a findings report plus a supporting artifact (no `Verdict:` line). Use for code review.
- `observation-format` — the lens's output is a structured observation report. Use for all scan-mode lenses (fresh-eyes, quality, doc-reconcile).

`finding` mode alone does not imply a verdict. Code review is `finding` mode but its preserved output is a findings report plus `.code-review-rounds.json`, not a `Verdict:` line — so it declares `output_contract: findings-artifact`. The conformance check reads `output_contract`, not `output_mode`, to select the required output-contract section.

A `scan`-mode lens must declare `output_contract: observation-format`. A `finding`-mode lens declares either `verdict-contract` or `findings-artifact`. Declaring a mismatch (for example, `scan` mode with `verdict-contract`) is a lens defect.

The `output_mode` and `output_contract` declarations appear in the lens-identity section as a labeled block, for example:

```
output_mode: finding
output_contract: verdict-contract
```

### 2. Finding types

A table of finding types valid for this lens. Each entry carries:

- Type name (the value the researcher emits in the `type` field).
- Plain-language definition: what this type means for this artifact kind.
- Ship decision: would you block, request changes, or merge-and-flag on a finding of this type?

The finding types must be consistent with the generic type definitions in `review-loop.md`. If the lens refines a generic type (for example, test review refines the generic "test-integrity" type), it states the refinement explicitly.

### 3. Severity levels

A table of severity levels valid for this lens. Each entry carries:

- Severity label.
- Observability definition: who can observe this problem and how.
- Reviewer action: block, request changes, comment, or no comment.

### 4. Type-severity validity matrix

A matrix showing which type-severity combinations are valid. The researcher and challenger both validate their output against this matrix before emitting. Invalid combinations are rejected.

For `finding`-mode lenses this matrix is carried in a **machine-readable block** (a `lens-matrix` fenced block) that `pipeline.load_lens_matrix()` parses into a `LensVocabulary` (`types`, `severities`, `matrix`, `required`). The human-readable table and the machine-readable block must agree. The `required` field is the candidate-validation required-field set and **excludes `id`** — the researcher does not emit `id`; the pipeline assigns sighting IDs after schema validation. `scan`-mode lenses carry no `lens-matrix` block (they bypass `validate_sighting()`); instead they declare a structural output schema for the conformance check.

### 5. What to look for (researcher instructions)

The knowledge the researcher uses to surface candidate findings. This is the primary domain-knowledge section.

Structure this as named, enumerable passes or checklists so the researcher can execute them systematically and tag each finding with its detection source. A finding tagged "lens-checklist" traces back to a specific item in this section; a finding tagged "lens-detection-pass" traces back to a specific named pass.

Each detection pass or checklist item is a concrete, actionable criterion — not a general principle. "Check that every test would fail if the behavior it claims to cover were broken" is too general. "Flag any test whose sole assertion is error-absence with no positive behavioral assertion" is actionable.

If the lens uses shared detection passes, include this at the start of this section:

> Read `shared-detection.md` for [list of shared pass names] used by this lens.

Never copy shared pass content into the lens. The reference is the inclusion.

### 6. Source-of-truth handling

What the researcher should compare the artifact against:

- When a spec is available: which sections, which criteria identifiers.
- When no spec is available: which fallback sources (AI failure-mode checklist, lens-defined general criteria, existing code patterns).
- When the artifact carries an inherited contract verbatim: the researcher must locate the original and compare field by field, not accept the artifact's copy as the source of truth.

### 7. Challenger instructions

The additional verification knowledge the challenger uses beyond the generic disciplines in `review-loop.md`. This section may be short or empty if the generic disciplines are sufficient.

Specifically document:

- Any reclassification rules specific to this lens (conditions under which the challenger may reclassify type or severity, and which combinations are reachable).
- Any type-specific definition of "provenance" for the dead-code trace discipline (what provenance chain means for this artifact kind).
- Any type-specific definition of "cited source" for the cited-source reading discipline (what kinds of documents a finding in this type commonly cites, so the challenger knows what to look for).
- Any type-specific verification thresholds (for example, test-review's requirement to trace a call path to confirm behavioral findings is generic; a lens may tighten this).

### 8. Verdict contract (`output_contract: verdict-contract`)

**Conditional — include only when the lens declares `output_contract: verdict-contract`.**

If this lens is loaded by a preset that produces a verdict artifact, describe:

- The artifact filename (canonical path the preset writes).
- The verdict line format (must be exactly `Verdict: accepted` or `Verdict: needs-revision`).
- The passing condition in plain language: what the artifact must contain for the verdict to be accepted.
- The failing condition: what specific defects trigger a needs-revision verdict.

### 9. Findings artifact (`output_contract: findings-artifact`)

**Conditional — include only when the lens declares `output_contract: findings-artifact`.**

For lenses whose output is a findings report plus a supporting artifact (no `Verdict:` line):

- The findings report filename (canonical path the preset writes).
- The supporting artifact filename and format (for example, `.code-review-rounds.json`).
- The structure of the findings report: sections, heading format, finding-entry format.
- The gate check this output feeds: which artifact is read, and what the passing condition is.

### 10. Observation format (`output_contract: observation-format`)

**Conditional — include only when the lens declares `output_contract: observation-format`.**

For lenses loaded by read-only presets that do not produce a verdict (fresh-eyes is the only current example):

- The observation categories (Critical, Substantive, Minor for fresh-eyes).
- The format: each observation is a bullet-list item (`- ` prefix) within its category section.
- The gate check this output feeds: which section is checked, and what the passing condition is.

The gate check for fresh-eyes is enforced by Python code in `fbk/gates/intent.py` and `fbk/gates/design.py`: the gate scans each line in the `## Critical` section and tests whether `line.strip().startswith("-")`. Any line — at any indentation level — whose stripped form starts with a dash is treated as an open observation. The gate fails when any such line exists. **The lens must specify that critical observations are written as lines starting with a dash (`-`), and that no other format (prose, numbered list, or any non-dash-prefixed form) is used for critical observations.** Prose paragraphs and numbered items genuinely bypass the check; indented dashes do not.

---

## Extension rule

Adding a new review type requires writing one new lens document at the location above. Nothing else in the shape changes. The new lens must follow this format exactly. A new lens that omits any required section is a defect, not a draft.

---

## Shared detection document

`shared-detection.md` contains detection passes that are valid across multiple review types. The rules for this document:

- A pass lives here if and only if it is referenced by two or more lenses. A pass used by only one lens belongs in that lens.
- The format of each pass in this document follows the same structure as a named detection pass in a lens's "what to look for" section.
- Lenses reference this document by pass name, not by copying content.
- When a shared pass is updated, all lenses that reference it inherit the update automatically — they reference by name, and the name resolves to the current content.

The shared-detection document is not a complete lens. It cannot be used as a standalone lens; it is a referenced knowledge unit.

Currently expected shared passes (at migration time):

- The test-integrity audit (currently in `detection-audits.md`) is relevant to both code review (where the researcher tags findings as test-integrity type) and test review (where the full pass is the primary detection work). This pass migrates to `shared-detection.md` and both lenses reference it.
- The consistency audit and cross-function API trace (also in `detection-audits.md`) are code-review-specific and remain in the code lens only.
