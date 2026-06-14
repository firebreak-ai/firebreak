"""Interface-contract gate checks — four pure check functions.

Exposes:
  check_interface_contracts_structure(spec_text) -> List[str]
  check_design_anchor(spec_text, feature_dir) -> List[str]
  check_ac_coverage(spec_text) -> List[str]
  check_seam_coverage(spec_text) -> List[str]

Also exports NO_CONTRACTS_SENTENCE and the message constants used by the checks.
"""

import re
import pathlib
from typing import List

from fbk.gates.sections import heading_line, section_body


# ---------------------------------------------------------------------------
# Sentence constant
# ---------------------------------------------------------------------------

NO_CONTRACTS_SENTENCE = "No new or changed contracts in this feature."


# ---------------------------------------------------------------------------
# Message constants (verbatim — do not paraphrase)
# ---------------------------------------------------------------------------

MSG_SECTION_MISSING = (
    "Interface contracts section missing — add ## Interface contracts to the spec. "
    "Carry at least one entry or the no-contracts sentence from design/contracts.md."
)

MSG_SECTION_EMPTY = (
    "Interface contracts section present but empty — add at least one contract entry "
    "or the no-contracts sentence (No new or changed contracts in this feature.)."
)

MSG_MISSING_FIELD = (
    "Interface contracts: entry {id} is missing the {field} field. "
    "Every entry needs id, name, signature, invariants, covers, and design-ref."
)

MSG_INVALID_ID = (
    "Interface contracts: entry {id} has an invalid id format. "
    "Expected IF-D-NN (design-originated, carry from design/contracts.md) or "
    "IF-S-NN (spec-originated, minted by the spec author). NN must be at least two digits."
)

MSG_EMPTY_COVERS = (
    "Interface contracts: entry {id} has an empty covers list — "
    "every contract must cover at least one acceptance criterion."
)

MSG_COVERS_AC_ABSENT = (
    "Interface contracts: entry {id} lists {ac} in covers but {ac} does not appear "
    "in ## Acceptance criteria. Check the identifier or add the missing criterion."
)

MSG_INVALID_DESIGN_REF = (
    "Interface contracts: entry {id} has an invalid design-ref value '{value}' — "
    "valid values are a path/anchor into design/contracts.md (e.g., design/contracts.md#if-d-01), "
    "the literal 'pre-existing', or the literal 'none'."
)

MSG_EXCLUDED_EMPTY_RATIONALE = (
    "Excluded contracts: entry {id} has an empty rationale — "
    "every excluded contract needs a non-empty rationale explaining why it is not carried."
)

MSG_EXCLUDED_INVALID_ID = (
    "Excluded contracts: entry {id} has an invalid id format — "
    "excluded entries reference a design-originated contract and must use the IF-D-NN form."
)

MSG_UNCOVERED_AC_EMPTY_RATIONALE = (
    "Uncovered acceptance criteria: entry {id} has an empty rationale — "
    "every uncovered criterion needs a non-empty rationale explaining why no contract covers it."
)

MSG_DESIGN_PAGE_NOT_FOUND = (
    "Design contracts page not found at {path} — "
    "run /fbk-design <feature-name> to produce it before running the spec gate."
)

MSG_CONTRACT_NOT_CARRIED = (
    "Contract {id} ({name}) is listed in design/contracts.md but is not carried "
    "into ## Interface contracts and has no entry in ## Excluded contracts. "
    "Resolution: (1) add an {id} entry to ## Interface contracts with all required fields, "
    "or (2) add an ## Excluded contracts entry for {id} with a non-empty rationale "
    "explaining the scope change."
)

MSG_AC_NOT_COVERED = (
    "{ac} is not covered by any contract's covers: list and has no entry in "
    "## Uncovered acceptance criteria. "
    "Resolution: (1) add {ac} to some contract's covers: list, "
    "or (2) add an ## Uncovered acceptance criteria entry for {ac} with a non-empty rationale."
)

MSG_SEAM_UNCOVERED = (
    "Integration seam '{a} → {b}' is declared in ## Technical approach "
    "but no entry in ## Interface contracts appears to name both components. "
    "This is a heuristic check — if the seam genuinely needs no contract, either add a "
    "contract entry naming both components or revisit the integration-seam declaration. "
    "Resolution: (1) add or update a contract entry that names both {a} and {b}, "
    "or (2) update the integration-seam declaration if this seam is contract-free."
)


# ---------------------------------------------------------------------------
# Internal parse helpers
# ---------------------------------------------------------------------------

_VALID_ID_RE = re.compile(r"^IF-[DS]-[0-9]{2,}$")
# Match entry starts in both formats:
#   - id: IF-D-01        (YAML list item form)
#     id: IF-D-01        (plain indented form, used by some test fixtures)
_ANY_ENTRY_START_RE = re.compile(r"^\s*(?:-\s+)?id:\s+(\S+)", re.MULTILINE)
_FIELD_RE = re.compile(r"^\s+(\S[^:]*?):\s*(.*)", re.MULTILINE)
_COVERS_LIST_RE = re.compile(r"\[([^\]]*)\]")


def _parse_entries(body: str):
    """Parse entry blocks from a contracts/excluded/uncovered section body.

    Returns a list of dicts. Each dict contains at minimum 'id' (the raw value
    from the text) and every other field found under that entry.

    If the body has indented field lines but no id: key, a synthetic entry with
    id='<unknown>' is returned so the missing-id check fires correctly.
    """
    entries = []
    # Find all entry start positions (id: <value>) in both dash and plain forms.
    matches = list(_ANY_ENTRY_START_RE.finditer(body))

    if not matches:
        # No id: line found — check for any indented field content (missing-id case).
        if _FIELD_RE.search(body):
            entry = {"id": "<unknown>"}
            for field_match in _FIELD_RE.finditer(body):
                field_name = field_match.group(1).strip()
                field_value = field_match.group(2).strip()
                entry[field_name] = field_value
            entries.append(entry)
        return entries

    for idx, match in enumerate(matches):
        entry_id = match.group(1)
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(body)
        block = body[start:end]
        entry = {"id": entry_id}
        for field_match in _FIELD_RE.finditer(block):
            field_name = field_match.group(1).strip()
            field_value = field_match.group(2).strip()
            entry[field_name] = field_value
        entries.append(entry)
    return entries


# ---------------------------------------------------------------------------
# check_interface_contracts_structure
# ---------------------------------------------------------------------------

def check_interface_contracts_structure(spec_text: str) -> List[str]:
    """Check that ## Interface contracts is present, well-formed, and cross-references are valid.

    Returns a list of failure strings; empty list means the section passes.
    """
    failures: List[str] = []

    # Locate the section.
    ln = heading_line(spec_text, "## Interface contracts")
    if ln is None:
        return [MSG_SECTION_MISSING]

    body = section_body(spec_text, ln)
    if not body.strip():
        return [MSG_SECTION_EMPTY]

    # No-contracts sentence path — skip entry parsing.
    if NO_CONTRACTS_SENTENCE in body.strip():
        # Still validate escape-hatch sections below.
        pass
    else:
        # Collect AC ids from ## Acceptance criteria for cross-reference.
        ac_ln = heading_line(spec_text, "## Acceptance criteria")
        if ac_ln is not None:
            ac_body = section_body(spec_text, ac_ln)
            ac_ids = set(re.findall(r"\bAC-[0-9]+\b", ac_body))
        else:
            ac_ids = set()

        # Parse entries.
        entries = _parse_entries(body)
        for entry in entries:
            entry_id = entry.get("id", "<unknown>")

            # Validate id field presence and format.
            if entry_id == "<unknown>":
                # id key was not found at all — emit missing-field message.
                failures.append(MSG_MISSING_FIELD.format(id="<unknown>", field="id"))
            elif not _VALID_ID_RE.match(entry_id):
                failures.append(MSG_INVALID_ID.format(id=entry_id))
                # Still check other fields using the raw id (even if invalid).

            # Check all six required fields.
            required_fields = ["id", "name", "signature", "invariants", "covers", "design-ref"]
            for field in required_fields:
                if field == "id":
                    # id presence/validity already handled above
                    continue
                value = entry.get(field, "")
                if not value:
                    failures.append(MSG_MISSING_FIELD.format(id=entry_id, field=field))
                    continue

                # Additional per-field checks for non-empty values.
                if field == "covers":
                    m = _COVERS_LIST_RE.search(value)
                    if m:
                        raw_items = [x.strip() for x in m.group(1).split(",") if x.strip()]
                    else:
                        raw_items = []

                    if not raw_items:
                        failures.append(MSG_EMPTY_COVERS.format(id=entry_id))
                    else:
                        for ac in raw_items:
                            if ac not in ac_ids:
                                failures.append(
                                    MSG_COVERS_AC_ABSENT.format(id=entry_id, ac=ac)
                                )

                elif field == "design-ref":
                    valid = (
                        value in ("pre-existing", "none")
                        or ("/" in value)
                        or ("#" in value)
                    )
                    if not valid:
                        failures.append(MSG_INVALID_DESIGN_REF.format(id=entry_id, value=value))

    # Validate ## Excluded contracts (if present).
    exc_ln = heading_line(spec_text, "## Excluded contracts")
    if exc_ln is not None:
        exc_body = section_body(spec_text, exc_ln)
        exc_entries = _parse_entries(exc_body)
        _if_d_re = re.compile(r"^IF-D-[0-9]{2,}$")
        for entry in exc_entries:
            entry_id = entry.get("id", "<unknown>")
            if not _if_d_re.match(entry_id):
                failures.append(MSG_EXCLUDED_INVALID_ID.format(id=entry_id))
            rationale = entry.get("rationale", "")
            if not rationale:
                failures.append(MSG_EXCLUDED_EMPTY_RATIONALE.format(id=entry_id))

    # Validate ## Uncovered acceptance criteria (if present).
    uca_ln = heading_line(spec_text, "## Uncovered acceptance criteria")
    if uca_ln is not None:
        uca_body = section_body(spec_text, uca_ln)
        uca_entries = _parse_entries(uca_body)
        for entry in uca_entries:
            entry_id = entry.get("id", "<unknown>")
            rationale = entry.get("rationale", "")
            if not rationale:
                failures.append(MSG_UNCOVERED_AC_EMPTY_RATIONALE.format(id=entry_id))

    return failures


# ---------------------------------------------------------------------------
# check_design_anchor
# ---------------------------------------------------------------------------

def check_design_anchor(spec_text: str, feature_dir: str) -> List[str]:
    """Check that every IF-D contract in design/contracts.md is carried or excluded.

    Returns a list of failure strings; empty list means the check passes.
    """
    failures: List[str] = []

    design_path = pathlib.Path(feature_dir) / "design" / "contracts.md"
    if not design_path.exists():
        return [MSG_DESIGN_PAGE_NOT_FOUND.format(path=str(design_path))]

    design_text = design_path.read_text()

    # Extract design IF-D ids and names.
    design_id_re = re.compile(r"^## (IF-D-[0-9]{2,})(.*)", re.MULTILINE)
    design_ids = []
    design_names = {}
    for m in design_id_re.finditer(design_text):
        did = m.group(1)
        rest = m.group(2)
        design_ids.append(did)
        # Name is text after ' — ' separator in the heading.
        if " — " in rest:
            name = rest.split(" — ", 1)[1].strip()
        elif " — " in rest:
            name = rest.split(" — ", 1)[1].strip()
        else:
            # Try a plain space separator (e.g. "## IF-D-01 ContractValidator.validate").
            stripped = rest.strip()
            name = stripped if stripped else "unnamed"
        design_names[did] = name if name else "unnamed"

    if not design_ids:
        return []

    # Extract carried IF-D ids from ## Interface contracts.
    contracts_ln = heading_line(spec_text, "## Interface contracts")
    carried: set = set()
    if contracts_ln is not None:
        contracts_body = section_body(spec_text, contracts_ln)
        carried = set(re.findall(r"\bid:\s*(IF-D-[0-9]{2,})", contracts_body))

    # Extract excluded IF-D ids from ## Excluded contracts.
    exc_ln = heading_line(spec_text, "## Excluded contracts")
    excluded: set = set()
    if exc_ln is not None:
        exc_body = section_body(spec_text, exc_ln)
        excluded = set(re.findall(r"\bid:\s*(IF-D-[0-9]{2,})", exc_body))

    missing = set(design_ids) - (carried | excluded)
    for did in sorted(missing):
        name = design_names.get(did, "unnamed")
        failures.append(MSG_CONTRACT_NOT_CARRIED.format(id=did, name=name))

    return failures


# ---------------------------------------------------------------------------
# check_ac_coverage
# ---------------------------------------------------------------------------

def check_ac_coverage(spec_text: str) -> List[str]:
    """Check that every AC in ## Acceptance criteria is covered or excused.

    Returns a list of failure strings; empty list means the check passes.
    """
    failures: List[str] = []

    # Collect AC ids.
    ac_ln = heading_line(spec_text, "## Acceptance criteria")
    if ac_ln is None:
        return []
    ac_body = section_body(spec_text, ac_ln)
    ac_ids = set(re.findall(r"\bAC-[0-9]+\b", ac_body))

    # Collect covered ids strictly from covers: lists.
    covered: set = set()
    contracts_ln = heading_line(spec_text, "## Interface contracts")
    if contracts_ln is not None:
        contracts_body = section_body(spec_text, contracts_ln)
        # No-contracts form: the feature declares no contracts, so coverage-by-
        # contract is vacuously satisfied — a no-contracts spec passes (UV-4).
        if NO_CONTRACTS_SENTENCE in contracts_body.strip():
            return []
        # Parse entries and read only their covers: fields.
        entries = _parse_entries(contracts_body)
        for entry in entries:
            covers_value = entry.get("covers", "")
            if covers_value:
                m = _COVERS_LIST_RE.search(covers_value)
                if m:
                    for item in m.group(1).split(","):
                        item = item.strip()
                        if item:
                            covered.add(item)

    # Collect excused ids from ## Uncovered acceptance criteria.
    excused: set = set()
    uca_ln = heading_line(spec_text, "## Uncovered acceptance criteria")
    if uca_ln is not None:
        uca_body = section_body(spec_text, uca_ln)
        excused = set(re.findall(r"^\s*-\s+id:\s+(AC-[0-9]+)", uca_body, re.MULTILINE))

    uncovered = ac_ids - (covered | excused)
    for ac in sorted(uncovered):
        failures.append(MSG_AC_NOT_COVERED.format(ac=ac))

    return failures


# ---------------------------------------------------------------------------
# check_seam_coverage
# ---------------------------------------------------------------------------

def check_seam_coverage(spec_text: str) -> List[str]:
    """Check that integration seams in ## Technical approach are reflected in ## Interface contracts.

    Returns a list of failure strings; empty list means the check passes.
    This is a heuristic check — it looks for component names as substrings.
    """
    failures: List[str] = []

    tech_ln = heading_line(spec_text, "## Technical approach")
    if tech_ln is None:
        return []
    technical_body = section_body(spec_text, tech_ln)

    # Extract seam pairs from checklist lines only (- [ ] or - [x]).
    pairs = re.findall(
        r"^\s*-\s*\[[ x]\]\s*([^→\n]+?)\s*→\s*([^:\n]+?):",
        technical_body,
        re.MULTILINE,
    )
    if not pairs:
        return []

    # Get the contracts body for the heuristic name search.
    contracts_ln = heading_line(spec_text, "## Interface contracts")
    contracts_body = ""
    if contracts_ln is not None:
        contracts_body = section_body(spec_text, contracts_ln)

    for left, right in pairs:
        a = left.strip()
        b = right.strip()
        a_found = bool(re.search(re.escape(a), contracts_body, re.IGNORECASE))
        b_found = bool(re.search(re.escape(b), contracts_body, re.IGNORECASE))
        if not (a_found and b_found):
            failures.append(MSG_SEAM_UNCOVERED.format(a=a, b=b))

    return failures
