"""Canonical feature-spec fixtures shared across the test suite.

This module is the single source of truth for "a minimal feature spec that
passes the spec gate". Several test files run a spec through the gate (directly,
through the dispatcher, or in-process) and previously each carried its own
verbatim copy of the same spec text. When the spec gate's required sections
changed, those copies drifted out of sync silently. Keeping one definition here
means a gate-contract change is reflected everywhere by editing one place.

The canonical spec carries the no-contracts ## Interface contracts section, so
it satisfies the contract structural check and the AC-coverage check (which is
vacuously satisfied for a no-contracts feature). Tests that run the gate must
also create the design contracts page beside the spec — use
write_design_contracts_page() for that.
"""

import os

from fbk.gates.contracts import NO_CONTRACTS_SENTENCE

# The required sections of a minimal gate-passing spec, without the title line.
MINIMAL_VALID_SECTIONS = (
    "## Problem\n"
    "Describes the issue or gap being addressed.\n\n"
    "## Goals\n"
    "- Primary objective of the feature\n\n"
    "## User-facing behavior\n"
    "Describes how end users interact with the feature.\n\n"
    "## Technical approach\n"
    "Details the implementation strategy.\n\n"
    "## Testing strategy\n"
    "- AC-01: Test criterion 1\n\n"
    "## Documentation impact\n"
    "Expected changes to user documentation.\n\n"
    "## Acceptance criteria\n"
    "- AC-01: Feature works as specified\n\n"
    "## Dependencies\n"
    "None\n\n"
    "## Open questions\n"
    "None\n\n"
    "## Interface contracts\n"
    + NO_CONTRACTS_SENTENCE + "\n"
)

# A complete minimal gate-passing spec, title included.
MINIMAL_VALID_SPEC = "# Feature Specification\n\n" + MINIMAL_VALID_SECTIONS

SLICES_BLOCK = """\
## Slices
- name: slice-alpha
  test-discipline: {discipline}
  covers: [{covers}]
"""


def make_minimal_spec(extra_sections=""):
    """Return the canonical minimal spec, optionally with extra sections appended."""
    return MINIMAL_VALID_SPEC + extra_sections


def make_spec_with_slices(discipline="new-contract", covers="B-001", include_slices=True):
    """Build the minimal valid spec, optionally with a Slices block appended."""
    base = make_minimal_spec()
    if include_slices:
        base += SLICES_BLOCK.format(discipline=discipline, covers=covers)
    return base


def write_design_contracts_page(directory, body=None):
    """Create <directory>/design/contracts.md so the design-anchor check passes.

    The default body is the no-contracts sentence, which pairs with the
    no-contracts ## Interface contracts section in the canonical spec. Accepts
    a str or os.PathLike directory and returns the path written.
    """
    design_dir = os.path.join(os.fspath(directory), "design")
    os.makedirs(design_dir, exist_ok=True)
    page = os.path.join(design_dir, "contracts.md")
    with open(page, "w") as fh:
        fh.write((NO_CONTRACTS_SENTENCE if body is None else body) + "\n")
    return page
