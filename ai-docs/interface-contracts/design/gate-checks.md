# Gate checks — the four new spec-gate algorithms

The four new check algorithms in enough detail to implement, with parse rules, set logic, and teaching error message formats. All four live in `fbk/gates/contracts.py` and are called by `fbk/gates/spec.py`. The spec-side shapes they read are defined in `spec-sections.md`; the design page shape they read is defined in `contracts-standard.md`.

**This page is the single source of truth for every teaching-error string.** Where any other artifact (the design contracts page, the spec's contract invariants, the tests) quotes a gate failure message, it copies the wording here verbatim. The implementation defines each message as a module constant in `contracts.py`, and the tests assert against the exact string — so a message and its test cannot drift.

## Check 1: Structural completeness of `## Interface contracts`

**Function**: `check_interface_contracts_structure(spec_text)`. This check reads only the spec text — it validates the three spec-side sections and never opens the design page, so it takes no feature directory.

**Parse rule for `## Interface contracts`**:
1. Locate `## Interface contracts` using the existing `heading_line` helper (case-insensitive).
2. Extract the section body using `section_body`.
3. If body is empty: one failure — section present but empty.
4. If body contains the no-contracts sentence (`No new or changed contracts in this feature.`, stripped): the contracts section is valid; skip entry parsing and proceed to the escape-hatch sections below.
5. Otherwise parse entries. Entry boundary: `^\s*-\s+id:\s+(IF-[DS]-[0-9]{2,})`. Each match opens a new entry. Parse the subsequent indented lines for the remaining fields (`name`, `signature`, `invariants`, `covers`, `design-ref`) using `^\s+<field>:\s+(.+)`.
6. For `covers:`, extract the inline YAML list: `\[([^\]]*)\]`, split on commas.

**Set logic for `## Interface contracts`**:
- For each entry: verify all six fields (`id`, `name`, `signature`, `invariants`, `covers`, `design-ref`) are present and non-empty.
- Verify each `id` matches `^IF-[DS]-[0-9]{2,}$` (accepts both `IF-D-NN` and `IF-S-NN`; any other prefix is a failure).
- Verify each `covers` list is non-empty.
- Verify each `AC-NN` in every `covers` list appears in the acceptance criteria section. Extract AC identifiers from that section using `re.findall(r"\bAC-[0-9]+\b", ac_body)`.
- Verify each `design-ref` value is one of: the literal `pre-existing`, the literal `none`, or a path/anchor form. A value is recognized as a path/anchor form when it contains a `/` or a `#` (the gate treats the path form as shape-only and does not resolve or follow it). A bare token that is neither a reserved literal nor a path/anchor (for example, `whatever`) is invalid. Concretely: `valid = value in ("pre-existing", "none") or ("/" in value) or ("#" in value)`.

**Escape-hatch sections** (validated by this same function so the empty-rationale rule the PRD requires is enforced):
- `## Excluded contracts`: if present, parse entries with boundary `^\s*-\s+id:\s+(IF-D-[0-9]{2,})` and a `rationale:` field. Each entry's `id` must match `^IF-D-[0-9]{2,}$` (excluded entries are always design-originated) and its `rationale` must be non-empty.
- `## Uncovered acceptance criteria`: if present, parse entries with boundary `^\s*-\s+id:\s+(AC-[0-9]+)` and a `rationale:` field. Each entry's `id` must match `^AC-[0-9]+$` and its `rationale` must be non-empty.

**Teaching error messages**:
- `"Interface contracts section missing — add ## Interface contracts to the spec. Carry at least one entry or the no-contracts sentence from design/contracts.md."`
- `"Interface contracts section present but empty — add at least one contract entry or the no-contracts sentence (No new or changed contracts in this feature.)."`
- `"Interface contracts: entry <id> is missing the <field> field. Every entry needs id, name, signature, invariants, covers, and design-ref."`
- `"Interface contracts: entry <id> has an invalid id format. Expected IF-D-NN (design-originated, carry from design/contracts.md) or IF-S-NN (spec-originated, minted by the spec author). NN must be at least two digits."`
- `"Interface contracts: entry <id> has an empty covers list — every contract must cover at least one acceptance criterion."`
- `"Interface contracts: entry <id> lists <AC-NN> in covers but <AC-NN> does not appear in ## Acceptance criteria. Check the identifier or add the missing criterion."`
- `"Interface contracts: entry <id> has an invalid design-ref value '<value>' — valid values are a path/anchor into design/contracts.md (e.g., design/contracts.md#if-d-01), the literal 'pre-existing', or the literal 'none'."`
- `"Excluded contracts: entry <id> has an empty rationale — every excluded contract needs a non-empty rationale explaining why it is not carried."`
- `"Excluded contracts: entry <id> has an invalid id format — excluded entries reference a design-originated contract and must use the IF-D-NN form."`
- `"Uncovered acceptance criteria: entry <id> has an empty rationale — every uncovered criterion needs a non-empty rationale explaining why no contract covers it."`

(The `design/contracts.md#if-d-01` anchor in the design-ref message is illustrative of the path form an author writes; the gate stores and shape-checks `design-ref` but does not resolve or follow the anchor.)

## Check 2: Design-anchor walk

**Function**: `check_design_anchor(spec_text, feature_dir)`

**Parse rule**:
1. Derive the design contracts path as `Path(feature_dir) / "design" / "contracts.md"`.
2. If the file does not exist: return one failure naming the path and instructing the operator to run the design phase.
3. Read the file. Extract design identifiers: `re.findall(r"^## (IF-D-[0-9]{2,})", design_text, re.MULTILINE)`. The `IF-D-` prefix is required — design pages only ever carry `IF-D-NN` identifiers. Prose mentions of identifiers do not match because `^##` anchors to line start.
4. If no identifiers found: no-contracts form. Return empty failures (vacuous pass).
5. Extract carried identifiers from `## Interface contracts` in the spec: all `id:` field values matching `IF-D-[0-9]{2,}`. Spec-originated `IF-S-NN` entries are ignored by this check — they are never design-originated and cannot satisfy a design-anchor requirement.
6. Extract excluded identifiers from `## Excluded contracts` in the spec: all `id:` field values matching `IF-D-[0-9]{2,}`.
7. Compute: `missing = design_ids - (carried_ids | excluded_ids)`.

**Set logic**:
- One failure string per identifier in `missing`.
- The check is one-directional: `IF-S-NN` entries in the spec that have no matching design identifier are not failures here. Detecting spec-adds absent from design is spec review's job.

**Name extraction**: The design page heading form is `## IF-D-NN — <name>`. Extract the name as the text after `— ` in the heading line. If the heading has no ` — ` separator, use "unnamed" in the failure message.

**Teaching error messages**:
- `"Design contracts page not found at <path> — run /fbk-design <feature-name> to produce it before running the spec gate."`
- `"Contract IF-D-NN (<name>) is listed in design/contracts.md but is not carried into ## Interface contracts and has no entry in ## Excluded contracts. Resolution: (1) add an IF-D-NN entry to ## Interface contracts with all required fields, or (2) add an ## Excluded contracts entry for IF-D-NN with a non-empty rationale explaining the scope change."`

## Check 3: AC-coverage

**Function**: `check_ac_coverage(spec_text)`

**Parse rule**:
1. Locate `## Acceptance criteria` and extract body using `heading_line` + `section_body`.
2. Extract all AC identifiers from the body: `re.findall(r"\bAC-[0-9]+\b", ac_body)`. Word-boundary anchors prevent partial matches.
3. Locate `## Interface contracts` and extract body. Parse entries (boundary `^\s*-\s+id:\s+IF-[DS]-[0-9]{2,}`) and, for each entry, read the `covers:` inline list with `\[([^\]]*)\]`. The covered-AC set is the union of identifiers drawn **only from those `covers:` lists** — not a body-wide scan. (A body-wide `AC-NN` scan would wrongly count an AC merely mentioned in a `signature` or `invariants` field as covered; coverage must come from the explicit `covers:` list.)
4. Locate `## Uncovered acceptance criteria` and extract body. Collect excused ACs: `re.findall(r"^\s*-\s+id:\s+(AC-[0-9]+)", uca_body, re.MULTILINE)`.
5. Compute: `uncovered = set(ac_ids) - (set(covered_ids) | set(excused_ids))`.

**Set logic**:
- One failure per identifier in `uncovered`.
- ACs appearing in both `covers:` lists and in `## Uncovered acceptance criteria` are not failures — redundancy is allowed.
- If `## Acceptance criteria` is absent: return empty list (the existing `check_section` call in `spec.py` main() already reports that failure; this function does not double-report).

**Teaching error messages**:
- `"AC-NN is not covered by any contract's covers: list and has no entry in ## Uncovered acceptance criteria. Resolution: (1) add AC-NN to some contract's covers: list, or (2) add an ## Uncovered acceptance criteria entry for AC-NN with a non-empty rationale."`

## Check 4: Light seam-coverage

**Function**: `check_seam_coverage(spec_text)`

**Parse rule**:
1. Locate `## Technical approach` using `heading_line` + `section_body`.
2. Extract component pairs from integration-seam declarations. The seam format (from `feature-spec-guide.md`) is a checklist item: `- [ ] ComponentA → ComponentB: <interface>: <convention>` where `→` is Unicode U+2192. Extraction regex (anchored to line start so a seam written mid-prose is not matched): `re.findall(r"^\s*-\s*\[[ x]\]\s*([^→\n]+?)\s*→\s*([^:\n]+?):", technical_body, re.MULTILINE)`. Group 1 is the left component name, group 2 is the right component name; strip whitespace from both.
3. If no pairs found: return empty failures.
4. Extract the full body of `## Interface contracts`.
5. For each pair `(A, B)`: check whether both `A` and `B` appear as substrings in the contracts body (case-insensitive, using `re.search(re.escape(name), contracts_body, re.IGNORECASE)`).

**Set logic**:
- One failure per pair where either component name is absent from the contracts body.
- This is a heuristic substring scan, not a structural reference check. The gate failure message states so explicitly.

**Teaching error messages**:
- `"Integration seam 'ComponentA → ComponentB' is declared in ## Technical approach but no entry in ## Interface contracts appears to name both components. This is a heuristic check — if the seam genuinely needs no contract, either add a contract entry naming both components or revisit the integration-seam declaration. Resolution: (1) add or update a contract entry that names both ComponentA and ComponentB, or (2) update the integration-seam declaration if this seam is contract-free."`

## Integration into `spec.py` main()

The four checks are called inside the `if scope == "feature":` branch, after the existing `check_slices` call. The `feature_dir` value is already available as `pathlib.Path(spec_path).parent`. The import is at module top level.

```python
from fbk.gates.contracts import (
    check_interface_contracts_structure,
    check_design_anchor,
    check_ac_coverage,
    check_seam_coverage,
)
```

Addition to the feature-scope block in `main()`:

```python
fails.extend(check_interface_contracts_structure(spec_text))
fails.extend(check_design_anchor(spec_text, str(feature_dir)))
fails.extend(check_ac_coverage(spec_text))
fails.extend(check_seam_coverage(spec_text))
```

Call order is intentional: structural completeness runs first because the downstream checks depend on the section being parseable. All four calls accumulate into the shared `fails` list, consistent with how the existing gate accumulates failures across checks rather than short-circuiting. Only the design-anchor check needs `feature_dir` (to locate `design/contracts.md`); the other three read the spec text alone.

**Seam at the `spec.py` / `contracts.py` boundary**: `spec.py` is the caller; `contracts.py` is the implementer. Data crossing inbound: `spec_text: str` for all four checks, plus `feature_dir: str` for the design-anchor check. Data crossing outbound: `List[str]`. Failure mode if `contracts.py` is absent: `ImportError` at startup, surfacing as a Python traceback — consistent with how `fbk.injection` and `fbk.slices` behave in the existing gate, and with the module-interface contract in `contracts.md`.
