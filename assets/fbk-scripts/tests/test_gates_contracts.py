"""Tests for fbk.gates.contracts — four interface-contract gate checks.

Red phase: fbk/gates/contracts.py does not exist yet. Collection succeeds;
every test errors/fails because the import fails. That is the expected state
before task-02 runs.

Shared fixtures MINIMAL_ENTRY and MINIMAL_DESIGN_CONTRACTS are reused by
test_gates_spec.py (task-09).
"""

import pytest

# This import WILL fail at red phase (contracts.py does not exist).
# That is acceptable — the import error is the expected red-phase failure.
from fbk.gates.contracts import (
    check_interface_contracts_structure,
    check_design_anchor,
    check_ac_coverage,
    check_seam_coverage,
    NO_CONTRACTS_SENTENCE,
)


# ---------------------------------------------------------------------------
# Module-level fixture strings
# ---------------------------------------------------------------------------

# A minimal valid single ## Interface contracts entry with all six fields.
# The entry id is IF-D-01; covers one AC that also appears in ## Acceptance
# criteria. design-ref is a path/anchor form. This is the UV-1 real-entry
# fixture, distinct from the no-contracts form.
MINIMAL_ENTRY = """\
## Acceptance criteria
- AC-01: The system validates interface contracts on every spec.

## Interface contracts
- id: IF-D-01
  name: ContractValidator.validate
  signature: validate(spec_text: str) -> List[str]
  invariants: Returns empty list when contracts are valid; non-empty on failure.
  covers: [AC-01]
  design-ref: design/contracts.md#if-d-01
"""

# A ## Interface contracts section whose body is exactly the no-contracts
# sentence. Built by referencing the imported constant so it cannot drift.
NO_CONTRACTS_SECTION = f"## Interface contracts\n{NO_CONTRACTS_SENTENCE}\n"

# A minimal valid no-contracts design/contracts.md text.
# Reuses the imported constant — do not retype the literal.
# Reused by task-09 (test_gates_spec.py).
MINIMAL_DESIGN_CONTRACTS = NO_CONTRACTS_SENTENCE + "\n"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _spec_with_entry(entry_block: str) -> str:
    """Wrap an entry block in a minimal spec with ## Acceptance criteria."""
    return entry_block


def _spec_no_contracts() -> str:
    """Return a spec that carries the no-contracts sentence in the contracts section."""
    return (
        "## Acceptance criteria\n"
        "- AC-01: Some criterion.\n\n"
        + NO_CONTRACTS_SECTION
    )


# ---------------------------------------------------------------------------
# TestStructural — check_interface_contracts_structure (AC-01..AC-07)
# ---------------------------------------------------------------------------

class TestStructural:
    """Tests for check_interface_contracts_structure()."""

    def test_missing_section_returns_exact_string(self):
        """Spec with no ## Interface contracts section returns the missing-section message."""
        spec = "## Acceptance criteria\n- AC-01: Something.\n"
        result = check_interface_contracts_structure(spec)
        expected = (
            "Interface contracts section missing — add ## Interface contracts to the spec. "
            "Carry at least one entry or the no-contracts sentence from design/contracts.md."
        )
        assert expected in result

    def test_empty_section_returns_distinct_exact_string(self):
        """Heading present but blank body returns the present-but-empty message (distinct from missing)."""
        spec = "## Interface contracts\n\n## Acceptance criteria\n- AC-01: Something.\n"
        result = check_interface_contracts_structure(spec)
        expected = (
            "Interface contracts section present but empty — add at least one contract entry "
            "or the no-contracts sentence (No new or changed contracts in this feature.)."
        )
        assert expected in result

    def test_no_contracts_sentence_passes(self):
        """Section body containing only the no-contracts sentence returns an empty list."""
        spec = _spec_no_contracts()
        result = check_interface_contracts_structure(spec)
        assert result == []

    def test_minimal_entry_passes(self):
        """Real single IF-D entry with all six fields and a covered AC returns an empty list."""
        result = check_interface_contracts_structure(MINIMAL_ENTRY)
        assert result == []

    @pytest.mark.parametrize("missing_field", [
        "id", "name", "signature", "invariants", "covers", "design-ref",
    ])
    def test_missing_field_returns_exact_string(self, missing_field):
        """Entry missing each required field returns the exact per-field message."""
        # Build an entry that omits the specified field.
        fields = {
            "id": "IF-D-01",
            "name": "ContractValidator.validate",
            "signature": "validate(spec_text: str) -> List[str]",
            "invariants": "Returns empty list on success.",
            "covers": "[AC-01]",
            "design-ref": "design/contracts.md#if-d-01",
        }
        lines = ["## Acceptance criteria", "- AC-01: Something.", "", "## Interface contracts"]
        for field, value in fields.items():
            if field == missing_field:
                continue
            lines.append(f"  {field}: {value}")
        spec = "\n".join(lines) + "\n"

        entry_id = "IF-D-01" if missing_field != "id" else "<unknown>"
        result = check_interface_contracts_structure(spec)
        expected = (
            f"Interface contracts: entry {entry_id} is missing the {missing_field} field. "
            "Every entry needs id, name, signature, invariants, covers, and design-ref."
        )
        assert expected in result

    def test_invalid_id_prefix_returns_exact_string(self):
        """Entry with non-IF-[DS] id prefix returns the invalid-id-format message."""
        spec = (
            "## Acceptance criteria\n- AC-01: Something.\n\n"
            "## Interface contracts\n"
            "- id: IF-X-01\n"
            "  name: Something\n"
            "  signature: foo() -> None\n"
            "  invariants: None.\n"
            "  covers: [AC-01]\n"
            "  design-ref: design/contracts.md#if-x-01\n"
        )
        result = check_interface_contracts_structure(spec)
        expected = (
            "Interface contracts: entry IF-X-01 has an invalid id format. "
            "Expected IF-D-NN (design-originated, carry from design/contracts.md) or "
            "IF-S-NN (spec-originated, minted by the spec author). NN must be at least two digits."
        )
        assert expected in result

    def test_invalid_id_no_if_prefix_returns_exact_string(self):
        """Entry with completely wrong id prefix (e.g. XX-01) returns the invalid-id-format message."""
        spec = (
            "## Acceptance criteria\n- AC-01: Something.\n\n"
            "## Interface contracts\n"
            "- id: XX-01\n"
            "  name: Something\n"
            "  signature: foo() -> None\n"
            "  invariants: None.\n"
            "  covers: [AC-01]\n"
            "  design-ref: design/contracts.md#xx-01\n"
        )
        result = check_interface_contracts_structure(spec)
        expected = (
            "Interface contracts: entry XX-01 has an invalid id format. "
            "Expected IF-D-NN (design-originated, carry from design/contracts.md) or "
            "IF-S-NN (spec-originated, minted by the spec author). NN must be at least two digits."
        )
        assert expected in result

    def test_empty_covers_list_returns_exact_string(self):
        """Entry with an empty covers list returns the empty-covers message."""
        spec = (
            "## Acceptance criteria\n- AC-01: Something.\n\n"
            "## Interface contracts\n"
            "- id: IF-D-01\n"
            "  name: Something\n"
            "  signature: foo() -> None\n"
            "  invariants: None.\n"
            "  covers: []\n"
            "  design-ref: design/contracts.md#if-d-01\n"
        )
        result = check_interface_contracts_structure(spec)
        expected = (
            "Interface contracts: entry IF-D-01 has an empty covers list — "
            "every contract must cover at least one acceptance criterion."
        )
        assert expected in result

    def test_covers_ac_absent_from_acceptance_criteria_returns_exact_string(self):
        """Entry listing an AC not present in ## Acceptance criteria returns the cross-ref message."""
        spec = (
            "## Acceptance criteria\n- AC-01: Something.\n\n"
            "## Interface contracts\n"
            "- id: IF-D-01\n"
            "  name: Something\n"
            "  signature: foo() -> None\n"
            "  invariants: None.\n"
            "  covers: [AC-99]\n"
            "  design-ref: design/contracts.md#if-d-01\n"
        )
        result = check_interface_contracts_structure(spec)
        expected = (
            "Interface contracts: entry IF-D-01 lists AC-99 in covers but AC-99 does not appear "
            "in ## Acceptance criteria. Check the identifier or add the missing criterion."
        )
        assert expected in result

    @pytest.mark.parametrize("design_ref", [
        "design/contracts.md#if-d-01",
        "pre-existing",
        "none",
    ])
    def test_valid_design_ref_forms_pass(self, design_ref):
        """Each of the three valid design-ref forms returns an empty list."""
        spec = (
            "## Acceptance criteria\n- AC-01: Something.\n\n"
            "## Interface contracts\n"
            "- id: IF-D-01\n"
            "  name: Something\n"
            "  signature: foo() -> None\n"
            "  invariants: None.\n"
            "  covers: [AC-01]\n"
            f"  design-ref: {design_ref}\n"
        )
        result = check_interface_contracts_structure(spec)
        assert result == []

    def test_invalid_design_ref_returns_exact_string(self):
        """Entry with an unrecognized design-ref value returns the invalid-design-ref message."""
        spec = (
            "## Acceptance criteria\n- AC-01: Something.\n\n"
            "## Interface contracts\n"
            "- id: IF-D-01\n"
            "  name: Something\n"
            "  signature: foo() -> None\n"
            "  invariants: None.\n"
            "  covers: [AC-01]\n"
            "  design-ref: whatever\n"
        )
        result = check_interface_contracts_structure(spec)
        expected = (
            "Interface contracts: entry IF-D-01 has an invalid design-ref value 'whatever' — "
            "valid values are a path/anchor into design/contracts.md (e.g., design/contracts.md#if-d-01), "
            "the literal 'pre-existing', or the literal 'none'."
        )
        assert expected in result

    def test_excluded_contracts_empty_rationale_returns_exact_string(self):
        """Excluded entry with empty rationale returns the excluded-rationale message."""
        spec = (
            "## Interface contracts\n"
            + NO_CONTRACTS_SENTENCE + "\n\n"
            "## Excluded contracts\n"
            "- id: IF-D-02\n"
            "  rationale:\n"
        )
        result = check_interface_contracts_structure(spec)
        expected = (
            "Excluded contracts: entry IF-D-02 has an empty rationale — "
            "every excluded contract needs a non-empty rationale explaining why it is not carried."
        )
        assert expected in result

    def test_excluded_contracts_non_if_d_id_returns_exact_string(self):
        """Excluded entry with non-IF-D id returns the excluded-id-format message."""
        spec = (
            "## Interface contracts\n"
            + NO_CONTRACTS_SENTENCE + "\n\n"
            "## Excluded contracts\n"
            "- id: IF-S-01\n"
            "  rationale: Not needed because scope changed.\n"
        )
        result = check_interface_contracts_structure(spec)
        expected = (
            "Excluded contracts: entry IF-S-01 has an invalid id format — "
            "excluded entries reference a design-originated contract and must use the IF-D-NN form."
        )
        assert expected in result

    def test_uncovered_ac_empty_rationale_returns_exact_string(self):
        """Uncovered acceptance criteria entry with empty rationale returns the exact message."""
        spec = (
            "## Acceptance criteria\n- AC-01: Something.\n\n"
            "## Interface contracts\n"
            + NO_CONTRACTS_SENTENCE + "\n\n"
            "## Uncovered acceptance criteria\n"
            "- id: AC-01\n"
            "  rationale:\n"
        )
        result = check_interface_contracts_structure(spec)
        expected = (
            "Uncovered acceptance criteria: entry AC-01 has an empty rationale — "
            "every uncovered criterion needs a non-empty rationale explaining why no contract covers it."
        )
        assert expected in result


# ---------------------------------------------------------------------------
# TestDesignAnchor — check_design_anchor (AC-08, AC-09)
# ---------------------------------------------------------------------------

class TestDesignAnchor:
    """Tests for check_design_anchor()."""

    def test_all_design_contracts_carried_passes(self, tmp_path):
        """Design page whose every IF-D heading is carried in ## Interface contracts passes."""
        design_dir = tmp_path / "design"
        design_dir.mkdir()
        design_page = (
            "# Contracts\n\n"
            "## IF-D-01 ContractValidator.validate\n"
            "Some description.\n"
        )
        (design_dir / "contracts.md").write_text(design_page)
        spec = (
            "## Acceptance criteria\n- AC-01: Something.\n\n"
            "## Interface contracts\n"
            "- id: IF-D-01\n"
            "  name: ContractValidator.validate\n"
            "  signature: validate(spec_text: str) -> List[str]\n"
            "  invariants: Returns empty list on success.\n"
            "  covers: [AC-01]\n"
            "  design-ref: design/contracts.md#if-d-01\n"
        )
        result = check_design_anchor(spec, str(tmp_path))
        assert result == []

    def test_uncarried_contract_returns_exact_string(self, tmp_path):
        """A design contract neither carried nor excluded returns the carry-or-exclude message."""
        design_dir = tmp_path / "design"
        design_dir.mkdir()
        design_page = (
            "# Contracts\n\n"
            "## IF-D-01 ContractValidator.validate\n"
            "Some description.\n"
        )
        (design_dir / "contracts.md").write_text(design_page)
        # Spec carries the no-contracts sentence — so IF-D-01 is neither carried nor excluded.
        spec = _spec_no_contracts()
        result = check_design_anchor(spec, str(tmp_path))
        expected = (
            "Contract IF-D-01 (ContractValidator.validate) is listed in design/contracts.md but is not carried "
            "into ## Interface contracts and has no entry in ## Excluded contracts. "
            "Resolution: (1) add an IF-D-01 entry to ## Interface contracts with all required fields, "
            "or (2) add an ## Excluded contracts entry for IF-D-01 with a non-empty rationale "
            "explaining the scope change."
        )
        assert expected in result

    def test_excluded_contract_passes(self, tmp_path):
        """Design contract carried only in ## Excluded contracts with rationale passes."""
        design_dir = tmp_path / "design"
        design_dir.mkdir()
        design_page = (
            "# Contracts\n\n"
            "## IF-D-01 ContractValidator.validate\n"
            "Some description.\n"
        )
        (design_dir / "contracts.md").write_text(design_page)
        spec = (
            "## Interface contracts\n"
            + NO_CONTRACTS_SENTENCE + "\n\n"
            "## Excluded contracts\n"
            "- id: IF-D-01\n"
            "  rationale: Out of scope for this release.\n"
        )
        result = check_design_anchor(spec, str(tmp_path))
        assert result == []

    def test_missing_design_contracts_page_returns_exact_string_and_does_not_raise(self, tmp_path):
        """Missing design/contracts.md returns the page-not-found message and does not raise."""
        # No design/contracts.md written — verify function returns a list, not an exception.
        spec = _spec_no_contracts()
        expected_path = str(tmp_path / "design" / "contracts.md")
        result = check_design_anchor(spec, str(tmp_path))
        # Must be a list (no exception raised).
        assert isinstance(result, list)
        expected = (
            f"Design contracts page not found at {expected_path} — "
            "run /fbk-design <feature-name> to produce it before running the spec gate."
        )
        assert expected in result

    def test_no_if_d_headings_in_design_page_passes_vacuously(self, tmp_path):
        """Design page with no IF-D headings (no-contracts sentence only) passes vacuously."""
        design_dir = tmp_path / "design"
        design_dir.mkdir()
        (design_dir / "contracts.md").write_text(MINIMAL_DESIGN_CONTRACTS)
        spec = _spec_no_contracts()
        result = check_design_anchor(spec, str(tmp_path))
        assert result == []


# ---------------------------------------------------------------------------
# TestACCoverage — check_ac_coverage (AC-10)
# ---------------------------------------------------------------------------

class TestACCoverage:
    """Tests for check_ac_coverage()."""

    def test_all_acs_covered_passes(self):
        """Every AC in ## Acceptance criteria covered by some covers list passes."""
        spec = (
            "## Acceptance criteria\n"
            "- AC-01: Criterion one.\n"
            "- AC-02: Criterion two.\n\n"
            "## Interface contracts\n"
            "- id: IF-D-01\n"
            "  name: Foo\n"
            "  signature: foo() -> None\n"
            "  invariants: None.\n"
            "  covers: [AC-01, AC-02]\n"
            "  design-ref: design/contracts.md#if-d-01\n"
        )
        result = check_ac_coverage(spec)
        assert result == []

    def test_uncovered_ac_returns_exact_string(self):
        """An AC with no entry in covers lists and no uncovered-AC excuse returns the exact message."""
        spec = (
            "## Acceptance criteria\n"
            "- AC-01: Covered.\n"
            "- AC-02: Uncovered.\n\n"
            "## Interface contracts\n"
            "- id: IF-D-01\n"
            "  name: Foo\n"
            "  signature: foo() -> None\n"
            "  invariants: None.\n"
            "  covers: [AC-01]\n"
            "  design-ref: design/contracts.md#if-d-01\n"
        )
        result = check_ac_coverage(spec)
        expected = (
            "AC-02 is not covered by any contract's covers: list and has no entry in "
            "## Uncovered acceptance criteria. "
            "Resolution: (1) add AC-02 to some contract's covers: list, "
            "or (2) add an ## Uncovered acceptance criteria entry for AC-02 with a non-empty rationale."
        )
        assert expected in result

    def test_ac_excused_in_uncovered_section_passes(self):
        """AC listed in ## Uncovered acceptance criteria passes without a covers entry."""
        spec = (
            "## Acceptance criteria\n"
            "- AC-01: Covered.\n"
            "- AC-02: Excused.\n\n"
            "## Interface contracts\n"
            "- id: IF-D-01\n"
            "  name: Foo\n"
            "  signature: foo() -> None\n"
            "  invariants: None.\n"
            "  covers: [AC-01]\n"
            "  design-ref: design/contracts.md#if-d-01\n\n"
            "## Uncovered acceptance criteria\n"
            "- id: AC-02\n"
            "  rationale: No contract boundary here.\n"
        )
        result = check_ac_coverage(spec)
        assert result == []

    def test_body_scan_trap_ac_in_signature_field_still_uncovered(self):
        """AC appearing only inside a signature/invariants field text (not in covers) is still uncovered.

        This proves coverage is drawn only from covers: lists, never a body-wide text scan.
        """
        # AC-02 appears in the signature text but NOT in any covers: list.
        spec = (
            "## Acceptance criteria\n"
            "- AC-01: Covered.\n"
            "- AC-02: Appears only in body text.\n\n"
            "## Interface contracts\n"
            "- id: IF-D-01\n"
            "  name: Foo\n"
            "  signature: foo(ac_02_context: str) -> None  # handles AC-02 case\n"
            "  invariants: Relates to AC-02 behavior.\n"
            "  covers: [AC-01]\n"
            "  design-ref: design/contracts.md#if-d-01\n"
        )
        result = check_ac_coverage(spec)
        expected = (
            "AC-02 is not covered by any contract's covers: list and has no entry in "
            "## Uncovered acceptance criteria. "
            "Resolution: (1) add AC-02 to some contract's covers: list, "
            "or (2) add an ## Uncovered acceptance criteria entry for AC-02 with a non-empty rationale."
        )
        assert expected in result


# ---------------------------------------------------------------------------
# TestSeamCoverage — check_seam_coverage (AC-11)
# ---------------------------------------------------------------------------

class TestSeamCoverage:
    """Tests for check_seam_coverage()."""

    def test_seam_with_both_components_in_contracts_passes(self):
        """Seam whose two components both appear in ## Interface contracts body passes."""
        spec = (
            "## Technical approach\n"
            "- [ ] SpecParser → ContractValidator: parses spec for contract entries.\n\n"
            "## Interface contracts\n"
            "- id: IF-D-01\n"
            "  name: SpecParser to ContractValidator handoff\n"
            "  signature: SpecParser.parse(text: str) -> ContractValidator\n"
            "  invariants: None.\n"
            "  covers: [AC-01]\n"
            "  design-ref: design/contracts.md#if-d-01\n"
        )
        result = check_seam_coverage(spec)
        assert result == []

    def test_seam_missing_component_returns_exact_string_with_heuristic(self):
        """Seam where one component is absent from contracts body returns the heuristic message."""
        spec = (
            "## Acceptance criteria\n- AC-01: Something.\n\n"
            "## Technical approach\n"
            "- [ ] ComponentA → ComponentB: integration point.\n\n"
            "## Interface contracts\n"
            "- id: IF-D-01\n"
            "  name: Only ComponentA mentioned\n"
            "  signature: ComponentA.run() -> None\n"
            "  invariants: None.\n"
            "  covers: [AC-01]\n"
            "  design-ref: design/contracts.md#if-d-01\n"
        )
        result = check_seam_coverage(spec)
        expected = (
            "Integration seam 'ComponentA → ComponentB' is declared in ## Technical approach "
            "but no entry in ## Interface contracts appears to name both components. "
            "This is a heuristic check — if the seam genuinely needs no contract, either add a "
            "contract entry naming both components or revisit the integration-seam declaration. "
            "Resolution: (1) add or update a contract entry that names both ComponentA and ComponentB, "
            "or (2) update the integration-seam declaration if this seam is contract-free."
        )
        assert expected in result
        # Proves the heuristic-labelling clause is present.
        assert any("heuristic" in msg for msg in result)

    def test_no_declared_seam_passes(self):
        """Spec with no checklist seam lines in ## Technical approach passes."""
        spec = (
            "## Technical approach\n"
            "Prose describing the approach without any seam declarations.\n\n"
            "## Interface contracts\n"
            + NO_CONTRACTS_SENTENCE + "\n"
        )
        result = check_seam_coverage(spec)
        assert result == []

    def test_arrow_in_prose_line_not_treated_as_seam(self):
        """A → arrow inside a prose line (not a - [ ] item) produces zero seam failures."""
        # The Unicode right arrow (U+2192) in plain prose must not trigger the seam check.
        spec = (
            "## Technical approach\n"
            "The data flows from ComponentA → ComponentB as described in the design.\n\n"
            "## Interface contracts\n"
            + NO_CONTRACTS_SENTENCE + "\n"
        )
        result = check_seam_coverage(spec)
        assert result == []


# ---------------------------------------------------------------------------
# TestModuleInterface (AC-12)
# ---------------------------------------------------------------------------

class TestModuleInterface:
    """Tests for the module interface contract — callability and return-type discipline."""

    def test_all_four_functions_are_callable(self):
        """The four gate-check names imported at module level are all callable."""
        assert callable(check_interface_contracts_structure)
        assert callable(check_design_anchor)
        assert callable(check_ac_coverage)
        assert callable(check_seam_coverage)

    def test_check_interface_contracts_structure_returns_list_of_str(self):
        """check_interface_contracts_structure returns list[str]; element type checked on real failure."""
        # Use a spec that produces at least one failure so the element assertion is exercised.
        spec = "## Acceptance criteria\n- AC-01: Something.\n"  # missing contracts section
        result = check_interface_contracts_structure(spec)
        assert isinstance(result, list)
        assert all(isinstance(x, str) for x in result)
        assert len(result) > 0  # confirm non-empty so element check is meaningful

    def test_check_design_anchor_returns_list_of_str(self, tmp_path):
        """check_design_anchor returns list[str]; element type checked on real failure (missing page)."""
        spec = _spec_no_contracts()
        result = check_design_anchor(spec, str(tmp_path))
        assert isinstance(result, list)
        assert all(isinstance(x, str) for x in result)
        assert len(result) > 0

    def test_check_ac_coverage_returns_list_of_str(self):
        """check_ac_coverage returns list[str]; element type checked on real failure.

        Uses a spec that declares a real contract (so AC coverage is enforced) with
        one uncovered AC. The no-contracts form is deliberately NOT used here: a
        no-contracts spec passes vacuously (UV-4), so it would produce no failure.
        """
        spec = (
            "## Acceptance criteria\n"
            "- AC-01: Covered criterion.\n"
            "- AC-02: Uncovered criterion.\n\n"
            "## Interface contracts\n"
            "- id: IF-D-01\n"
            "  name: Foo\n"
            "  signature: foo() -> None\n"
            "  invariants: None.\n"
            "  covers: [AC-01]\n"
            "  design-ref: design/contracts.md#if-d-01\n"
        )
        result = check_ac_coverage(spec)
        assert isinstance(result, list)
        assert all(isinstance(x, str) for x in result)
        assert len(result) > 0

    def test_check_seam_coverage_returns_list_of_str(self):
        """check_seam_coverage returns list[str]; element type checked on real failure."""
        spec = (
            "## Technical approach\n"
            "- [ ] Alpha → Beta: integration.\n\n"
            "## Interface contracts\n"
            + NO_CONTRACTS_SENTENCE + "\n"
        )
        result = check_seam_coverage(spec)
        assert isinstance(result, list)
        assert all(isinstance(x, str) for x in result)
        assert len(result) > 0


class TestFieldParsingLineAnchoring:
    """The field regex must not span newlines — a colon-less continuation line
    under one field must not swallow the next field's key (realmind2 affect
    spec-phase gate defect: every entry reported 'missing covers')."""

    def test_colonless_continuation_line_does_not_swallow_covers(self):
        spec = (
            "## Acceptance criteria\n- AC-01: Something.\n\n"
            "## Interface contracts\n"
            "- id: IF-D-01\n"
            "  name: Decay.floor\n"
            "  signature: DecayedSignificance(raw float64) float64\n"
            "  invariants: significance decays toward an arousal-anchored floor\n"
            "  - the floor is never reached for nonzero inputs\n"
            "  covers: [AC-01]\n"
            "  design-ref: design/contracts.md#if-d-01\n"
        )
        result = check_interface_contracts_structure(spec)
        assert result == []


class TestDesignAnchorNonstandardScheme:
    """A design contracts page numbered with a non-IF-D prefix must fail loudly
    instead of silently skipping carry verification (realmind2 affect design
    used IF-A-NN and the check provided no verification value)."""

    def test_nonstandard_prefix_returns_loud_failure(self, tmp_path):
        design_dir = tmp_path / "design"
        design_dir.mkdir()
        (design_dir / "contracts.md").write_text(
            "# Contracts\n\n## IF-A-01 — Affect.Assign\nSome description.\n"
        )
        spec = (
            "## Interface contracts\n"
            + NO_CONTRACTS_SENTENCE + "\n"
        )
        result = check_design_anchor(spec, str(tmp_path))
        assert result, "non-IF-D scheme must not pass silently"
        assert any("IF-A-01" in f and "IF-D" in f for f in result)

    def test_long_prefix_returns_loud_failure(self, tmp_path):
        """A multi-letter capability prefix (IF-AFFECT-01) must also fail loudly."""
        design_dir = tmp_path / "design"
        design_dir.mkdir()
        (design_dir / "contracts.md").write_text(
            "# Contracts\n\n## IF-AFFECT-01 — Affect.Assign\nSome description.\n"
        )
        spec = "## Interface contracts\n" + NO_CONTRACTS_SENTENCE + "\n"
        result = check_design_anchor(spec, str(tmp_path))
        assert any("IF-AFFECT-01" in f for f in result)

    def test_mixed_scheme_flags_nonstandard_ids(self, tmp_path):
        design_dir = tmp_path / "design"
        design_dir.mkdir()
        (design_dir / "contracts.md").write_text(
            "# Contracts\n\n"
            "## IF-D-01 ContractValidator.validate\nDescription.\n\n"
            "## IF-A-02 — Affect.Assign\nDescription.\n"
        )
        spec = (
            "## Acceptance criteria\n- AC-01: Something.\n\n"
            "## Interface contracts\n"
            "- id: IF-D-01\n"
            "  name: ContractValidator.validate\n"
            "  signature: validate(spec_text: str) -> List[str]\n"
            "  invariants: Returns empty list on success.\n"
            "  covers: [AC-01]\n"
            "  design-ref: design/contracts.md#if-d-01\n"
        )
        result = check_design_anchor(spec, str(tmp_path))
        assert any("IF-A-02" in f for f in result)
