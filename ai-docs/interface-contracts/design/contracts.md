# Interface contracts — interface-contracts

This feature's own interface contracts, and the first worked instance of the schema defined in `contracts-standard.md`. Every identifier here is design-originated, so all use the `IF-D-NN` prefix.

## IF-D-01 — check_interface_contracts_structure

- signature: `check_interface_contracts_structure(spec_text: str) -> List[str]` — accepts the full spec file text as a string; returns a list of failure strings (empty list means all structural checks passed). This check reads only the spec text — it does not open the design page, so it takes no feature directory.
- invariants: Pre: `spec_text` is a non-empty string; an empty string is treated as a missing section and produces a failure. Post: each returned string is a self-contained human-readable failure message naming the specific item that failed, the artifact that defines it, and the two resolution paths. Post: an empty return list means every structural sub-check passed. Scope: this check validates three sections — `## Interface contracts` (six fields per entry, id form, non-empty covers, AC existence, valid design-ref), `## Excluded contracts` (each entry has an `IF-D-NN` id and a non-empty rationale), and `## Uncovered acceptance criteria` (each entry has an `AC-NN` id and a non-empty rationale). Error: if `## Interface contracts` is absent, returns exactly the canonical string from `gate-checks.md`: `"Interface contracts section missing — add ## Interface contracts to the spec. Carry at least one entry or the no-contracts sentence from design/contracts.md."` Error: if an entry is present but missing a required field, returns one failure per missing field naming the entry's identifier and the field name. Error: if an `## Excluded contracts` or `## Uncovered acceptance criteria` entry has an empty rationale, returns one failure per offending entry.
- consumed-by: `spec.py` main(), inside the `scope == "feature"` branch alongside the existing `check_slices` call.
- produced-by: `fbk/gates/contracts.py` (new module).

## IF-D-02 — check_design_anchor

- signature: `check_design_anchor(spec_text: str, feature_dir: str) -> List[str]` — accepts spec text and the feature directory path; returns failure strings.
- invariants: Pre: `feature_dir` is a string; if `design/contracts.md` does not exist at that path the function returns a single failure rather than raising. Post: returns one failure per `IF-D-NN` identifier in `design/contracts.md` that is absent from both `## Interface contracts` and `## Excluded contracts` in the spec. Post: empty return means every design-originated identifier is carried or excluded. Error: the canonical string from `gate-checks.md`: `"Design contracts page not found at <path> — run /fbk-design <feature-name> to produce it before running the spec gate."` Error per missing identifier: the canonical "contract listed in design but not carried" string from `gate-checks.md` (names the `IF-D-NN` identifier and its design-heading name, and states the two resolution paths — carry it with all required fields, or excuse it in `## Excluded contracts` with a rationale). The check is one-directional: spec-originated `IF-S-NN` entries that have no matching design identifier are not failures here; that direction belongs to spec review.
- consumed-by: `spec.py` main(), called after IF-D-01.
- produced-by: `fbk/gates/contracts.py`.

## IF-D-03 — check_ac_coverage

- signature: `check_ac_coverage(spec_text: str) -> List[str]` — accepts spec text only; returns failure strings.
- invariants: Pre: `spec_text` non-empty string. Post: returns one failure per `AC-NN` identifier found in `## Acceptance criteria` that appears in neither any contract's `covers:` list nor in `## Uncovered acceptance criteria`. Post: empty return means every acceptance criterion is covered or excused. Error per uncovered criterion: `"AC-NN is not covered by any contract's covers: list and has no entry in ## Uncovered acceptance criteria. Resolution: (1) add AC-NN to some contract's covers: list, or (2) add an ## Uncovered acceptance criteria entry for AC-NN with a non-empty rationale."` If `## Acceptance criteria` is absent, returns empty list — the earlier `check_section` call in `spec.py` main() already reports that failure.
- consumed-by: `spec.py` main(), called after IF-D-02.
- produced-by: `fbk/gates/contracts.py`.

## IF-D-04 — check_seam_coverage

- signature: `check_seam_coverage(spec_text: str) -> List[str]` — accepts spec text; returns failure strings.
- invariants: Pre: `spec_text` non-empty string. Post: if no integration-seam declaration is found in the spec, returns empty list — no seams declared means no check to run. Post: for each component pair extracted from seam declarations, returns one failure if no contract entry in `## Interface contracts` contains both component names as substrings (case-insensitive). Post: empty return means every declared seam has at least one contract entry naming both components. Error per uncovered pair: the canonical seam-coverage string from `gate-checks.md` (names both components, states explicitly that the check is a heuristic, and gives the two resolution paths — name both components in a contract entry, or revise the integration-seam declaration). The error message states the heuristic nature explicitly; the operator is the final judge of whether the check misfired.
- consumed-by: `spec.py` main(), called after IF-D-03.
- produced-by: `fbk/gates/contracts.py`.

## IF-D-05 — contracts.py module public interface

- signature: Module `fbk/gates/contracts.py` exports exactly four names: `check_interface_contracts_structure`, `check_design_anchor`, `check_ac_coverage`, `check_seam_coverage` (the functions defined under IF-D-01 through IF-D-04). `spec.py` imports them as: `from fbk.gates.contracts import (check_interface_contracts_structure, check_design_anchor, check_ac_coverage, check_seam_coverage)`.
- invariants: Pre: all four functions accept only the arguments defined in IF-D-01 through IF-D-04. Post: all four functions return `List[str]` — this return type is the integration contract `spec.py` relies on; any change to the return type is a contract-evolving change requiring a retired-tests entry in the feature that makes the change. Error: `ImportError` from this import fails the gate at startup; `spec.py` does not catch it — the failure surfaces as a Python traceback, consistent with how `fbk.injection` and `fbk.slices` are imported in the existing gate.
- consumed-by: `spec.py` (import at module top level).
- produced-by: `fbk/gates/contracts.py`.
