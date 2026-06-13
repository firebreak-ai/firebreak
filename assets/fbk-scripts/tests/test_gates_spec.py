"""Tests for fbk.gates.spec section validation and open-questions logic."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fbk.gates.spec import check_section, check_open_questions
from fbk.gates.contracts import NO_CONTRACTS_SENTENCE
import fbk.gates.spec as _spec_gate_mod

from tests import capture_fixtures

# ---------------------------------------------------------------------------
# event_writer availability guard — red-phase: module present but audit
# call-sites not yet migrated
# ---------------------------------------------------------------------------

try:
    from fbk.capture import event_writer as _event_writer  # noqa: F401
    _EVENT_WRITER_AVAILABLE = True
except ImportError:
    _EVENT_WRITER_AVAILABLE = False


# ---------------------------------------------------------------------------
# Subprocess helpers
# ---------------------------------------------------------------------------

FBK_PY = Path(__file__).parent.parent / "fbk.py"

_MINIMAL_VALID_SECTIONS = (
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

_SLICES_BLOCK = """\
## Slices
- name: slice-alpha
  test-discipline: {discipline}
  covers: [{covers}]
"""


def _make_minimal_spec(extra_sections=""):
    return "# Feature Specification\n\n" + _MINIMAL_VALID_SECTIONS + extra_sections


def make_spec_with_slices(discipline="new-contract", covers="B-001", include_slices=True):
    """Build a minimal valid 8-section feature spec, optionally with a Slices block."""
    base = _make_minimal_spec()
    if include_slices:
        slices_block = _SLICES_BLOCK.format(discipline=discipline, covers=covers)
        base += slices_block
    return base


def run_spec_gate(tmp_path, spec_text, name="sample-spec.md", inventory_ids=None):
    """Write spec to a temp file and run the gate, returning CompletedProcess.

    Unconditionally creates design/contracts.md under tmp_path so the
    design-anchor check (task-10) finds the page and passes for contract-clean
    specs. The file contains the no-contracts sentence, meaning a spec that
    carries the no-contracts ## Interface contracts section satisfies both
    the structural check and the design-anchor check.
    """
    spec_file = tmp_path / name
    spec_file.write_text(spec_text)
    # Create design/contracts.md so the design-anchor check passes for clean specs.
    design_dir = tmp_path / "design"
    design_dir.mkdir(parents=True, exist_ok=True)
    (design_dir / "contracts.md").write_text(NO_CONTRACTS_SENTENCE + "\n")
    if inventory_ids is not None:
        inv_lines = "\n".join(f"- id: {bid}\n  short-handle: x" for bid in inventory_ids)
        (tmp_path / "behavior-inventory.yaml").write_text(inv_lines + "\n")
    return subprocess.run(
        [sys.executable, str(FBK_PY), "spec-gate", str(spec_file)],
        capture_output=True, text=True,
    )


# Module-level constant: slices spec whose testing-strategy has no AC references.
SLICES_SPEC_WITHOUT_TS_AC = (
    "# Feature Specification\n\n"
    "## Problem\nDescribes the issue or gap being addressed.\n\n"
    "## Goals\n- Primary objective of the feature\n\n"
    "## User-facing behavior\nDescribes how end users interact with the feature.\n\n"
    "## Technical approach\nDetails the implementation strategy.\n\n"
    "## Testing strategy\nSome prose with no AC references here.\n\n"
    "## Documentation impact\nExpected changes to user documentation.\n\n"
    "## Acceptance criteria\n- AC-01: Feature works as specified\n\n"
    "## Dependencies\nNone\n\n"
    "## Open questions\nNone\n\n"
    "## Interface contracts\n"
    + NO_CONTRACTS_SENTENCE + "\n\n"
    + "## Slices\n"
    "- name: slice-alpha\n"
    "  test-discipline: new-contract\n"
    "  covers: [B-001]\n"
)


class TestCheckSection:
    """Tests for check_section() behavioral contract."""

    def test_missing_section_produces_failure(self):
        """Spec missing ## Problem section produces failure."""
        spec = "## Overview\nSome content here"
        failures = check_section(spec, "## Problem")
        assert len(failures) > 0
        assert any("Missing section" in f for f in failures)

    def test_empty_section_produces_failure(self):
        """Spec with ## Problem but only whitespace body produces failure."""
        spec = "## Problem\n   \n\n## Overview\nSome content"
        failures = check_section(spec, "## Problem")
        assert len(failures) > 0
        assert any("Empty section" in f for f in failures)

    def test_valid_section_passes(self):
        """Spec with ## Problem and body content produces no failure."""
        spec = "## Problem\nThis is a valid problem statement with content."
        failures = check_section(spec, "## Problem")
        assert len(failures) == 0


class TestCheckOpenQuestions:
    """Tests for check_open_questions() behavioral contract."""

    def test_bare_question_without_rationale_fails(self):
        """Bullet with only '- Why?' and no rationale produces failure."""
        bullets = ["- Why?"]
        failures = check_open_questions(bullets)
        assert len(failures) > 0
        assert any("rationale" in f.lower() for f in failures)

    def test_inline_rationale_passes(self):
        """Bullet with inline rationale '- Why? Because X' produces no failure."""
        bullets = ["- Why? Because X"]
        failures = check_open_questions(bullets)
        assert len(failures) == 0

    def test_indented_continuation_rationale_passes(self):
        """Bullet with indented continuation line produces no failure."""
        bullets = ["- Why?", "  Because the reason is clear"]
        failures = check_open_questions(bullets)
        assert len(failures) == 0


# ---------------------------------------------------------------------------
# Slice-block detection (hinge tests — no inventory file in any of these)
# ---------------------------------------------------------------------------

class TestSliceBlockDetection:
    """Tests for the hinge that activates slice checking only when ## Slices is present."""

    def test_no_slices_block_passes_identically(self, tmp_path):
        """Spec with no ## Slices block passes identically to today (AC-21 regression)."""
        result = run_spec_gate(tmp_path, _make_minimal_spec())
        assert result.returncode == 0

    def test_test_discipline_in_prose_does_not_activate_check(self, tmp_path):
        """Token 'test-discipline' in prose or code fence does not trigger slice checking (AC-21)."""
        prose_contamination = (
            "\nThe test-discipline concept is described here.\n\n"
            "```yaml\ntest-discipline: new-contract\n```\n"
        )
        result = run_spec_gate(tmp_path, _make_minimal_spec(prose_contamination))
        assert result.returncode == 0

    def test_slices_block_with_valid_slice_passes(self, tmp_path):
        """Spec with a well-formed ## Slices block and one complete valid slice passes."""
        result = run_spec_gate(tmp_path, make_spec_with_slices())
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# Slice test-discipline field validation (AC-04)
# ---------------------------------------------------------------------------

class TestSliceDisciplineValidation:
    """Tests for test-discipline field presence and taxonomy enforcement (AC-04)."""

    def test_slice_missing_test_discipline_fails(self, tmp_path):
        """Slice without test-discipline field causes gate failure with slice name in output."""
        spec = (
            _make_minimal_spec()
            + "## Slices\n"
            "- name: slice-alpha\n"
            "  covers: [B-001]\n"
        )
        result = run_spec_gate(tmp_path, spec)
        assert result.returncode == 2
        combined = result.stdout + result.stderr
        assert "slice-alpha" in combined or "test-discipline" in combined

    def test_slice_invalid_test_discipline_fails(self, tmp_path):
        """Slice with out-of-taxonomy test-discipline value causes gate failure."""
        result = run_spec_gate(
            tmp_path, make_spec_with_slices(discipline="unknown-value")
        )
        assert result.returncode == 2
        combined = result.stdout + result.stderr
        assert "unknown-value" in combined or any(
            v in combined for v in ["new-contract", "contract-preserving", "contract-evolving", "cross-cutting"]
        )

    def test_valid_new_contract_discipline_passes(self, tmp_path):
        """Slice with test-discipline: new-contract passes."""
        result = run_spec_gate(tmp_path, make_spec_with_slices(discipline="new-contract"))
        assert result.returncode == 0

    def test_valid_contract_preserving_discipline_passes(self, tmp_path):
        """Slice with test-discipline: contract-preserving passes."""
        result = run_spec_gate(tmp_path, make_spec_with_slices(discipline="contract-preserving"))
        assert result.returncode == 0

    def test_valid_contract_evolving_discipline_passes(self, tmp_path):
        """Slice with test-discipline: contract-evolving passes."""
        result = run_spec_gate(tmp_path, make_spec_with_slices(discipline="contract-evolving"))
        assert result.returncode == 0

    def test_valid_cross_cutting_discipline_passes(self, tmp_path):
        """Slice with test-discipline: cross-cutting passes."""
        result = run_spec_gate(tmp_path, make_spec_with_slices(discipline="cross-cutting"))
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# Vocabulary drift sentinel — guards guide↔gate alignment
# ---------------------------------------------------------------------------

# Tied to the canonical four shapes the gate accepts. If the gate's
# TEST_DISCIPLINES tuple changes, this list must change with it and the spec
# guide (feature-spec-guide.md, Slices Declaration Format) must be updated to
# match. Drift between guide vocabulary and gate vocabulary previously caused
# specs that followed the guide to fail the gate; this class is the regression
# guard.

CANONICAL_DISCIPLINES = (
    "new-contract",
    "contract-preserving",
    "contract-evolving",
    "cross-cutting",
)

# The pre-hygiene vocabulary that used to appear in the guide. These values
# must continue to fail the gate — a passing result here means the guide and
# gate have drifted apart again.
RETIRED_DISCIPLINES = ("unit", "integration", "e2e", "contract")


class TestSliceVocabularyDriftSentinel:
    """Regression guard: canonical four pass, retired four fail."""

    @pytest.mark.parametrize("discipline", CANONICAL_DISCIPLINES)
    def test_canonical_discipline_passes(self, tmp_path, discipline):
        """Each canonical test-discipline value documented in the spec guide passes the gate."""
        result = run_spec_gate(tmp_path, make_spec_with_slices(discipline=discipline))
        assert result.returncode == 0, (
            f"Canonical value {discipline!r} must pass the gate. "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )

    @pytest.mark.parametrize("discipline", RETIRED_DISCIPLINES)
    def test_retired_discipline_fails(self, tmp_path, discipline):
        """Each pre-hygiene vocabulary value (unit/integration/e2e/contract) is rejected by the gate.

        A passing result for any of these means the guide and gate have drifted apart
        again — re-run the hygiene fix.
        """
        result = run_spec_gate(tmp_path, make_spec_with_slices(discipline=discipline))
        assert result.returncode == 2, (
            f"Retired value {discipline!r} must fail the gate. "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )


# ---------------------------------------------------------------------------
# Inventory coverage enforcement (AC-04)
# ---------------------------------------------------------------------------

class TestInventoryCoverage:
    """Tests for behavior-inventory coverage enforcement (AC-04)."""

    def test_behavior_not_covered_by_any_slice_fails(self, tmp_path):
        """Inventory entry with no slice covering it causes gate failure (B-001 uncovered)."""
        spec = make_spec_with_slices(covers="B-002")
        result = run_spec_gate(tmp_path, spec, inventory_ids=["B-001", "B-002"])
        assert result.returncode == 2
        combined = result.stdout + result.stderr
        assert "B-001" in combined or "not covered" in combined

    def test_all_behaviors_covered_passes(self, tmp_path):
        """All inventory ids covered by slices causes gate to pass."""
        result = run_spec_gate(
            tmp_path, make_spec_with_slices(covers="B-001"), inventory_ids=["B-001"]
        )
        assert result.returncode == 0

    def test_empty_inventory_passes(self, tmp_path):
        """Empty inventory file (zero ids to cover) causes gate to pass."""
        result = run_spec_gate(tmp_path, make_spec_with_slices(), inventory_ids=[])
        assert result.returncode == 0

    def test_no_inventory_file_skips_coverage_check(self, tmp_path):
        """Absence of behavior-inventory.yaml skips coverage check (backward compat)."""
        result = run_spec_gate(tmp_path, make_spec_with_slices())
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# Testing-strategy AC traceability retained for slices-bearing specs (AC-04/AC-21)
# ---------------------------------------------------------------------------

class TestTestingStrategyRetainedForSliceSpecs:
    """Existing testing-strategy AC traceability check still fires for slices-bearing specs."""

    def test_slices_spec_without_ac_in_testing_strategy_fails(self, tmp_path):
        """Slices-bearing spec with testing-strategy section lacking AC-NN references fails."""
        result = run_spec_gate(tmp_path, SLICES_SPEC_WITHOUT_TS_AC)
        assert result.returncode == 2
        assert "Testing strategy" in (result.stdout + result.stderr)


# ---------------------------------------------------------------------------
# Wiring-proof tests — prove spec.py calls the four contract checks (AC-13)
# ---------------------------------------------------------------------------

# RED PHASE: These tests WILL FAIL before task-10 wires the gate (i.e. before
# spec.py imports and calls the four contract checks from fbk.gates.contracts).
# They are intentionally failing here to establish the red phase of the
# test-driven build. After task-10 lands, the full suite should be green.


class TestContractCheckWiring:
    """Prove that spec.py calls the four contract checks after check_slices (AC-13).

    RED PHASE — all three tests below that expect contract failures WILL FAIL
    before task-10 wires the gate. This is expected and correct: the gate does
    not yet call the contract checks, so missing-section and accumulation
    failures are not surfaced yet.
    """

    def test_no_contracts_spec_passes(self, tmp_path):
        """Spec with no-contracts section and matching design/contracts.md passes (exit 0).

        Uses the migrated make_spec_with_slices() + run_spec_gate(), which
        produce the ## Interface contracts section (no-contracts sentence) and
        the design/contracts.md page unconditionally — so this test passes even
        before task-10 wires the gate, because the gate simply ignores the
        checks for now.
        """
        result = run_spec_gate(tmp_path, make_spec_with_slices())
        assert result.returncode == 0, (
            f"Contract-clean spec must pass the gate. "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )

    def test_missing_interface_contracts_section_fails(self, tmp_path):
        """Spec with ## Interface contracts section absent exits 2; stderr names missing section.

        Constructs a spec directly from the base sections WITHOUT the
        ## Interface contracts section (does not use the migrated helpers).
        Expects exit 2 and the exact structural-failure message in stderr.

        RED PHASE — will fail before task-10 wires the gate.
        """
        # Build a spec that has no ## Interface contracts section at all.
        spec_without_contracts_section = (
            "# Feature Specification\n\n"
            "## Problem\nDescribes the issue or gap being addressed.\n\n"
            "## Goals\n- Primary objective of the feature\n\n"
            "## User-facing behavior\nDescribes how end users interact with the feature.\n\n"
            "## Technical approach\nDetails the implementation strategy.\n\n"
            "## Testing strategy\n- AC-01: Test criterion 1\n\n"
            "## Documentation impact\nExpected changes to user documentation.\n\n"
            "## Acceptance criteria\n- AC-01: Feature works as specified\n\n"
            "## Dependencies\nNone\n\n"
            "## Open questions\nNone\n\n"
            "## Slices\n"
            "- name: slice-alpha\n"
            "  test-discipline: new-contract\n"
            "  covers: [B-001]\n"
        )
        result = run_spec_gate(tmp_path, spec_without_contracts_section)
        assert result.returncode == 2, (
            f"Spec missing ## Interface contracts must fail the gate. "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
        assert (
            "Interface contracts section missing — add ## Interface contracts to the spec. "
            "Carry at least one entry or the no-contracts sentence from design/contracts.md."
        ) in result.stderr, (
            f"Expected structural-failure message in stderr. stderr={result.stderr!r}"
        )

    def test_combined_failure_accumulates_without_short_circuit(self, tmp_path):
        """Spec failing both a slice check and the contracts structural check shows both errors.

        Feeds a spec with an out-of-taxonomy test-discipline value (slice check
        will reject it) AND no ## Interface contracts section (structural check
        will flag it). Asserts stderr contains BOTH the slice-failure signal AND
        the contracts structural-failure string — proving the gate accumulates
        failures without short-circuiting.

        RED PHASE — will fail before task-10 wires the gate.
        """
        # Spec has invalid discipline AND no ## Interface contracts section.
        spec_dual_failure = (
            "# Feature Specification\n\n"
            "## Problem\nDescribes the issue or gap being addressed.\n\n"
            "## Goals\n- Primary objective of the feature\n\n"
            "## User-facing behavior\nDescribes how end users interact with the feature.\n\n"
            "## Technical approach\nDetails the implementation strategy.\n\n"
            "## Testing strategy\n- AC-01: Test criterion 1\n\n"
            "## Documentation impact\nExpected changes to user documentation.\n\n"
            "## Acceptance criteria\n- AC-01: Feature works as specified\n\n"
            "## Dependencies\nNone\n\n"
            "## Open questions\nNone\n\n"
            "## Slices\n"
            "- name: slice-alpha\n"
            "  test-discipline: unit\n"  # out-of-taxonomy (retired vocabulary)
            "  covers: [B-001]\n"
            # No ## Interface contracts section — structural check should flag this too.
        )
        result = run_spec_gate(tmp_path, spec_dual_failure)
        assert result.returncode == 2, (
            f"Dual-failure spec must exit 2. "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
        combined = result.stdout + result.stderr
        # Slice-check failure signal: the out-of-taxonomy discipline value appears.
        assert "unit" in combined, (
            f"Expected slice-check failure signal ('unit') in output. combined={combined!r}"
        )
        # Contracts structural-failure signal.
        assert (
            "Interface contracts section missing — add ## Interface contracts to the spec. "
            "Carry at least one entry or the no-contracts sentence from design/contracts.md."
        ) in combined, (
            f"Expected contracts structural-failure message in output. combined={combined!r}"
        )


# ---------------------------------------------------------------------------
# Envelope write assertions — spec gate (AC-12)
# ---------------------------------------------------------------------------

# The spec gate must write NO PIPELINE_COMMAND of its own.  One dispatch
# through fbk.py yields exactly one PIPELINE_COMMAND, written by the
# chokepoint; the chokepoint-side positive assertion lives in
# tests/test_capture_chokepoint_integration.py.  These tests pin the negative
# half: calling the gate directly (bypassing the chokepoint) must leave the
# events file empty.

@pytest.mark.skipif(
    not _EVENT_WRITER_AVAILABLE,
    reason="fbk.capture.event_writer not available",
)
class TestSpecGateWritesNoEnvelope:
    """Spec gate writes no PIPELINE_COMMAND of its own on pass or fail (AC-12).

    One dispatch yields exactly one PIPELINE_COMMAND, written by the
    chokepoint; the chokepoint-side positive assertion lives in
    tests/test_capture_chokepoint_integration.py.
    """

    def _events_path(self, project_root):
        return os.path.join(project_root, ".fbk-capture", "events.jsonl")

    def _read_envelopes(self, project_root):
        path = self._events_path(project_root)
        if not os.path.exists(path):
            return []
        with open(path) as fh:
            return [json.loads(line) for line in fh if line.strip()]

    def test_spec_gate_pass_writes_no_envelope(self, tmp_path, monkeypatch):
        """Spec-gate pass path writes no PIPELINE_COMMAND when called directly."""
        project_root = capture_fixtures.make_project(str(tmp_path), instrumented=True, marked=True)

        spec_file = Path(project_root) / "sample-spec.md"
        spec_file.write_text(_make_minimal_spec())

        # The merged spec gate runs the contract design-anchor check, which
        # requires a design/contracts.md page beside the spec.  Create it with
        # the no-contracts sentence so the contract-clean minimal spec passes.
        design_dir = Path(project_root) / "design"
        design_dir.mkdir(parents=True, exist_ok=True)
        (design_dir / "contracts.md").write_text(NO_CONTRACTS_SENTENCE + "\n")

        monkeypatch.chdir(project_root)
        monkeypatch.setattr(sys, "argv", ["spec-gate", str(spec_file)])

        # Pass path returns normally (no sys.exit) — call directly.  Invoked
        # without fbk.py, the gate is the only possible writer, so the events
        # file must hold zero envelopes.
        _spec_gate_mod.main()

        assert self._read_envelopes(project_root) == []

    def test_spec_gate_fail_writes_no_envelope(self, tmp_path, monkeypatch):
        """Spec-gate fail path writes no PIPELINE_COMMAND when called directly."""
        project_root = capture_fixtures.make_project(str(tmp_path), instrumented=True, marked=True)

        # A spec missing required sections — will fail structural validation.
        spec_file = Path(project_root) / "broken-spec.md"
        spec_file.write_text("# Feature Specification\n\n## Problem\nOnly one section present.\n")

        monkeypatch.chdir(project_root)
        monkeypatch.setattr(sys, "argv", ["spec-gate", str(spec_file)])

        with pytest.raises(SystemExit) as exc_info:
            _spec_gate_mod.main()
        assert exc_info.value.code == 2

        assert self._read_envelopes(project_root) == []
