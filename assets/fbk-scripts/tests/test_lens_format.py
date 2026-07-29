"""Structural conformance tests for review lens files.

Each of the seven review lens documents must contain every section that
lens-format.md requires.  The required section list is read from
lens-format.md itself — not hardcoded here — so the check tracks the format
contract.

The conditional output-contract section is resolved by reading each lens's
declared ``output_contract`` field:

- ``verdict-contract``     → heading containing "Verdict"
- ``findings-artifact``    → heading containing "Findings", "Artifact", or
                             ".code-review-rounds.json"
- ``observation-format``   → heading containing "Output" or "Observation"

The test reads each lens's own declaration rather than maintaining a
per-lens allowlist, so neither the code-review lens nor the scan-mode lenses
false-fail.
"""

import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Module-level paths
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parents[3]
LENS_DIR = _REPO_ROOT / "assets" / "fbk-docs" / "fbk-review-lenses"
LENS_FORMAT = LENS_DIR / "lens-format.md"

LENS_FILENAMES = [
    "code-lens.md",
    "test-lens.md",
    "fresh-eyes-lens.md",
    "coherence-lens.md",
    "task-lens.md",
    "quality-lens.md",
    "doc-reconcile-lens.md",
]

# Valid values for each declared field.
VALID_OUTPUT_MODES = {"finding", "scan"}
VALID_OUTPUT_CONTRACTS = {"verdict-contract", "findings-artifact", "observation-format"}

# ---------------------------------------------------------------------------
# Helpers — structural parsers anchored on document markers, not vocabulary
# ---------------------------------------------------------------------------

_OUTPUT_MODE_RE = re.compile(r"^output_mode:\s*(finding|scan)", re.MULTILINE)
_OUTPUT_CONTRACT_RE = re.compile(
    r"^output_contract:\s*(verdict-contract|findings-artifact|observation-format)",
    re.MULTILINE,
)


def read_output_mode(text: str) -> str | None:
    """Extract the declared ``output_mode`` value from a lens document.

    Matches the line ``output_mode: finding|scan`` wherever it appears —
    in a fenced block or in the lens-identity body — and returns the value,
    or None when no such line exists.
    """
    match = _OUTPUT_MODE_RE.search(text)
    return match.group(1) if match else None


def read_output_contract(text: str) -> str | None:
    """Extract the declared ``output_contract`` value from a lens document.

    Matches ``output_contract: <kind>`` wherever it appears and returns the
    value, or None when absent.
    """
    match = _OUTPUT_CONTRACT_RE.search(text)
    return match.group(1) if match else None


def _extract_headings(text: str) -> list[str]:
    """Return the text portion of every ## or ### heading in *text*.

    Strips leading ``#`` markers and whitespace; does not strip trailing
    content (e.g. parenthetical qualifications like
    "What to look for (researcher instructions)").
    """
    lines = text.splitlines()
    headings = []
    for line in lines:
        if line.startswith("## ") or line.startswith("### "):
            heading_text = line.lstrip("#").strip()
            headings.append(heading_text)
    return headings


def _heading_contains(headings: list[str], substring: str) -> bool:
    """Return True when any heading contains *substring* (case-insensitive)."""
    lower = substring.lower()
    return any(lower in h.lower() for h in headings)


# ---------------------------------------------------------------------------
# Universal required section names — read from lens-format.md
# ---------------------------------------------------------------------------

def _load_universal_required_sections() -> list[str]:
    """Parse the universal required section names from lens-format.md.

    Reads the numbered list under the "Universal sections" marker in the
    "Required sections" block.  Returns the bare section names (without
    numbering) so they can be matched as substrings against lens headings.

    If lens-format.md does not exist the caller receives an empty list and
    the per-lens assertions will fail with a clear missing-file error before
    reaching the section check.
    """
    if not LENS_FORMAT.exists():
        return []

    text = LENS_FORMAT.read_text(encoding="utf-8")

    # Isolate the "Universal sections" numbered list. The list follows the
    # line "**Universal sections** (all lenses, all modes):" and ends at the
    # next blank line after the last numbered item.
    universal_block_re = re.compile(
        r"\*\*Universal sections\*\*.*?\n((?:\d+\. .+\n?)+)",
        re.DOTALL,
    )
    match = universal_block_re.search(text)
    if not match:
        return []

    block = match.group(1)
    # Each line looks like "1. Lens identity" — extract the name after ". "
    sections = []
    for line in block.splitlines():
        line = line.strip()
        item_match = re.match(r"^\d+\.\s+(.+)$", line)
        if item_match:
            sections.append(item_match.group(1).strip())
    return sections


UNIVERSAL_REQUIRED_SECTIONS = _load_universal_required_sections()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("filename", LENS_FILENAMES)
class TestLensFormatConformance:
    """Each of the seven lenses must conform to lens-format.md."""

    def _read(self, filename: str) -> tuple[Path, str]:
        """Return (path, text) for *filename*, failing if the file is absent."""
        path = LENS_DIR / filename
        assert path.exists(), (
            f"Lens file not found: {path}\n"
            "The lens directory or this file has not been authored yet. "
            "Create all seven lens files to make this test pass."
        )
        return path, path.read_text(encoding="utf-8")

    def test_lens_declares_output_mode(self, filename: str) -> None:
        """The lens file exists and declares output_mode as 'finding' or 'scan'."""
        _, text = self._read(filename)
        mode = read_output_mode(text)
        assert mode in VALID_OUTPUT_MODES, (
            f"{filename}: output_mode declaration missing or invalid.\n"
            f"  found: {mode!r}\n"
            f"  expected one of: {sorted(VALID_OUTPUT_MODES)}\n"
            "Add a line 'output_mode: finding' or 'output_mode: scan' to the lens-identity section."
        )

    def test_lens_has_universal_required_sections(self, filename: str) -> None:
        """The lens contains every universal required section from lens-format.md."""
        _, text = self._read(filename)
        assert LENS_FORMAT.exists(), (
            f"lens-format.md not found at {LENS_FORMAT}. "
            "Author lens-format.md before authoring lenses."
        )
        assert UNIVERSAL_REQUIRED_SECTIONS, (
            "Could not parse universal required sections from lens-format.md. "
            "Check that the 'Universal sections' numbered list is present."
        )
        headings = _extract_headings(text)
        for section_name in UNIVERSAL_REQUIRED_SECTIONS:
            assert _heading_contains(headings, section_name), (
                f"{filename}: missing universal required section '{section_name}'.\n"
                f"  Headings found: {headings}\n"
                "Add a ## heading whose text contains the section name."
            )

    def test_lens_declares_output_contract(self, filename: str) -> None:
        """The lens declares output_contract as one of the three valid kinds.

        Additionally enforces the consistency rule:
        - scan mode  → must declare observation-format
        - finding mode → must declare verdict-contract or findings-artifact
        """
        _, text = self._read(filename)
        contract = read_output_contract(text)
        assert contract in VALID_OUTPUT_CONTRACTS, (
            f"{filename}: output_contract declaration missing or invalid.\n"
            f"  found: {contract!r}\n"
            f"  expected one of: {sorted(VALID_OUTPUT_CONTRACTS)}\n"
            "Add 'output_contract: <kind>' to the lens-identity section."
        )

        mode = read_output_mode(text)
        if mode == "scan":
            assert contract == "observation-format", (
                f"{filename}: scan-mode lens declares output_contract: {contract!r} "
                "but must declare 'observation-format'. "
                "Fix the output_contract to match the output_mode."
            )
        elif mode == "finding":
            assert contract in {"verdict-contract", "findings-artifact"}, (
                f"{filename}: finding-mode lens declares output_contract: {contract!r} "
                "but must declare 'verdict-contract' or 'findings-artifact'. "
                "Fix the output_contract to match the output_mode."
            )

    def test_lens_carries_its_declared_output_contract_section(self, filename: str) -> None:
        """The lens carries the section matching its declared output_contract kind.

        - verdict-contract   → a heading containing 'Verdict'
        - findings-artifact  → a heading containing 'Findings', 'Artifact', or
                               '.code-review-rounds.json'
        - observation-format → a heading containing 'Output' or 'Observation' or
                               'format'

        The check reads the lens's own declaration, so the code-review lens
        (findings-artifact) and the scan-mode lenses (observation-format) are
        not required to carry a Verdict section and do not false-fail.
        """
        _, text = self._read(filename)
        contract = read_output_contract(text)
        headings = _extract_headings(text)

        if contract == "verdict-contract":
            assert _heading_contains(headings, "Verdict"), (
                f"{filename} declares output_contract: verdict-contract "
                "but carries no heading containing 'Verdict'.\n"
                f"  Headings found: {headings}\n"
                "Add a '## Verdict contract' (or similar) section."
            )
        elif contract == "findings-artifact":
            has_section = (
                _heading_contains(headings, "Findings")
                or _heading_contains(headings, "Artifact")
                or _heading_contains(headings, ".code-review-rounds.json")
            )
            assert has_section, (
                f"{filename} declares output_contract: findings-artifact "
                "but carries no heading containing 'Findings', 'Artifact', or "
                "'.code-review-rounds.json'.\n"
                f"  Headings found: {headings}\n"
                "Add a '## Findings artifact' section."
            )
        elif contract == "observation-format":
            has_section = (
                _heading_contains(headings, "Output")
                or _heading_contains(headings, "Observation")
                or _heading_contains(headings, "format")
            )
            assert has_section, (
                f"{filename} declares output_contract: observation-format "
                "but carries no heading containing 'Output', 'Observation', or 'format'.\n"
                f"  Headings found: {headings}\n"
                "Add an '## Observation format' section."
            )
        else:
            pytest.fail(
                f"{filename}: output_contract is {contract!r}, which is not a recognized kind. "
                "This test cannot determine which section to require."
            )
