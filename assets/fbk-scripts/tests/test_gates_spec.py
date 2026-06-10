"""Tests for fbk.gates.spec section validation and open-questions logic."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fbk.gates.spec import check_section, check_open_questions
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

_MINIMAL_VALID_SECTIONS = """\
## Problem
Describes the issue or gap being addressed.

## Goals
- Primary objective of the feature

## User-facing behavior
Describes how end users interact with the feature.

## Technical approach
Details the implementation strategy.

## Testing strategy
- AC-01: Test criterion 1

## Documentation impact
Expected changes to user documentation.

## Acceptance criteria
- AC-01: Feature works as specified

## Dependencies
None

## Open questions
None
"""

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
    """Write spec to a temp file and run the gate, returning CompletedProcess."""
    spec_file = tmp_path / name
    spec_file.write_text(spec_text)
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
    "## Slices\n"
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
# Envelope write assertions — spec gate (AC-03, AC-11)
# ---------------------------------------------------------------------------

# Red phase: the migrated event-writer call sites in fbk/gates/spec.py do not
# exist yet.  Each test drives main() in-process (monkeypatched argv + chdir)
# and asserts the post-migration envelope behaviour.  They will fail until the
# call-site swap lands.

@pytest.mark.skipif(
    not _EVENT_WRITER_AVAILABLE,
    reason="fbk.capture.event_writer not available",
)
class TestSpecGateWritesEnvelope:
    """Spec gate writes a PIPELINE_COMMAND envelope on both pass and fail paths (AC-03, AC-11)."""

    def _events_path(self, project_root):
        return os.path.join(project_root, ".fbk-capture", "events.jsonl")

    def _read_envelopes(self, project_root):
        path = self._events_path(project_root)
        if not os.path.exists(path):
            return []
        with open(path) as fh:
            return [json.loads(line) for line in fh if line.strip()]

    def test_spec_gate_pass_writes_envelope(self, tmp_path, monkeypatch):
        """Spec-gate pass path writes a PIPELINE_COMMAND envelope recording the pass result."""
        project_root = capture_fixtures.make_project(str(tmp_path), instrumented=True, marked=True)

        spec_file = Path(project_root) / "sample-spec.md"
        spec_file.write_text(_make_minimal_spec())

        monkeypatch.chdir(project_root)
        monkeypatch.setattr(sys, "argv", ["spec-gate", str(spec_file)])

        # The spec gate pass path returns normally (no sys.exit) — call directly.
        _spec_gate_mod.main()

        envelopes = self._read_envelopes(project_root)
        assert len(envelopes) >= 1, "No envelope written; migration not yet applied"
        env = envelopes[-1]
        assert env.get("event_type") == "PIPELINE_COMMAND"
        assert env.get("data", {}).get("result") == "pass"
        assert "spec" in env
        assert "stage" in env

    def test_spec_gate_fail_writes_envelope(self, tmp_path, monkeypatch):
        """Spec-gate fail path writes a PIPELINE_COMMAND envelope recording the fail result."""
        project_root = capture_fixtures.make_project(str(tmp_path), instrumented=True, marked=True)

        # A spec missing required sections — will fail structural validation.
        spec_file = Path(project_root) / "broken-spec.md"
        spec_file.write_text("# Feature Specification\n\n## Problem\nOnly one section present.\n")

        monkeypatch.chdir(project_root)
        monkeypatch.setattr(sys, "argv", ["spec-gate", str(spec_file)])

        with pytest.raises(SystemExit) as exc_info:
            _spec_gate_mod.main()
        assert exc_info.value.code == 2

        envelopes = self._read_envelopes(project_root)
        assert len(envelopes) >= 1, "No envelope written; migration not yet applied"
        env = envelopes[-1]
        assert env.get("event_type") == "PIPELINE_COMMAND"
        assert env.get("data", {}).get("result") == "fail"

    def test_spec_gate_write_failure_is_silent(self, tmp_path, monkeypatch):
        """Spec gate continues normally when the events path is unwritable (AC-11)."""
        project_root = capture_fixtures.make_project(str(tmp_path), instrumented=True, marked=True)

        # Block writes by creating .fbk-capture/ as a plain file rather than a dir.
        capture_dir = os.path.join(project_root, ".fbk-capture")
        with open(capture_dir, "w") as fh:
            fh.write("not-a-directory")

        spec_file = Path(project_root) / "sample-spec.md"
        spec_file.write_text(_make_minimal_spec())

        monkeypatch.chdir(project_root)
        monkeypatch.setattr(sys, "argv", ["spec-gate", str(spec_file)])

        # Gate must complete its own pass/fail logic regardless of the write failure.
        # The pass path returns normally (no sys.exit) — call directly.
        _spec_gate_mod.main()
