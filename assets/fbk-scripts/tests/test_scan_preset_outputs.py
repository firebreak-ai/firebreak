"""Spec-contract conformance tests for scan-only preset output shapes.

Pins the structural contracts that the quality-scan and doc-reconcile
scan-only migration must preserve (AC-17 / IF-S-10):

- quality-scan: at most five ranked sightings, each with a ``Severity:``
  field whose value is one of ``critical`` / ``substantive`` / ``minor``.
- doc-reconcile: a JSON array of records, each carrying the five fields
  ``class`` / ``doc`` / ``doc_says`` / ``code_shows`` / ``rationale``,
  with drift items listed before notes.

Fixtures are authored to the spec's output contracts, not read from a live
run.  The live re-run confirming the real emitted shape is the UV-8
source-of-truth gate (out of scope here).
"""

import json
import re
from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "scan_outputs"
QUALITY_SCAN_FIXTURE = FIXTURE_DIR / "quality-scan.md"
DOC_RECONCILE_FIXTURE = FIXTURE_DIR / "doc-reconcile.json"

# Regex that matches a Severity: line carrying the scan vocabulary.
# Anchored to the scan preset vocabulary (critical / substantive / minor),
# which is distinct from the finding-validator's severities.
_SEVERITY_LINE_RE = re.compile(
    r"^\s*[-*]?\s*\**Severity\**:\s*(critical|substantive|minor)",
    re.IGNORECASE | re.MULTILINE,
)

_SCAN_SEVERITY_VOCABULARY = {"critical", "substantive", "minor"}
_DOC_RECONCILE_CLASS_VOCABULARY = {"drift", "note"}
_DOC_RECONCILE_REQUIRED_FIELDS = {"class", "doc", "doc_says", "code_shows", "rationale"}


# ---------------------------------------------------------------------------
# quality-scan output shape
# ---------------------------------------------------------------------------


class TestQualityScanOutputShape:
    """quality-scan report carries at most five severity-tagged sightings."""

    def test_quality_scan_has_at_most_five_severity_tagged_sightings(self):
        """Severity-tagged sightings are >= 1 (present) and <= 5 (upper bound),
        each value within the scan vocabulary critical/substantive/minor."""
        text = QUALITY_SCAN_FIXTURE.read_text(encoding="utf-8")
        matches = _SEVERITY_LINE_RE.findall(text)

        assert len(matches) >= 1, (
            "quality-scan fixture carries no Severity: lines — fixture does not "
            "represent the spec's required output"
        )
        assert len(matches) <= 5, (
            f"quality-scan fixture has {len(matches)} severity-tagged sightings; "
            "the contract allows at most five"
        )

        bad_values = {v.lower() for v in matches} - _SCAN_SEVERITY_VOCABULARY
        assert not bad_values, (
            f"Severity values outside scan vocabulary found: {bad_values!r}. "
            "Allowed: critical / substantive / minor."
        )


# ---------------------------------------------------------------------------
# doc-reconcile output shape
# ---------------------------------------------------------------------------


class TestDocReconcileOutputShape:
    """doc-reconcile JSON array carries all five required fields per record."""

    @pytest.fixture(autouse=True)
    def load_fixture(self):
        """Load the doc-reconcile JSON fixture once per test."""
        self.records = json.loads(DOC_RECONCILE_FIXTURE.read_text(encoding="utf-8"))

    def test_doc_reconcile_records_carry_all_five_fields(self):
        """Every record in the JSON array has class/doc/doc_says/code_shows/rationale,
        and class is one of drift/note."""
        assert isinstance(self.records, list) and len(self.records) >= 1, (
            "doc-reconcile fixture must be a non-empty JSON array"
        )

        for idx, record in enumerate(self.records):
            missing = _DOC_RECONCILE_REQUIRED_FIELDS - set(record.keys())
            assert not missing, (
                f"Record at index {idx} is missing fields: {missing!r}"
            )
            assert record["class"] in _DOC_RECONCILE_CLASS_VOCABULARY, (
                f"Record at index {idx} has unrecognised class {record['class']!r}; "
                "allowed: drift / note"
            )

    def test_doc_reconcile_drift_listed_before_notes(self):
        """All drift records appear before all note records in the JSON array."""
        assert isinstance(self.records, list) and len(self.records) >= 1, (
            "doc-reconcile fixture must be a non-empty JSON array"
        )

        drift_indices = [i for i, r in enumerate(self.records) if r.get("class") == "drift"]
        note_indices = [i for i, r in enumerate(self.records) if r.get("class") == "note"]

        if not drift_indices or not note_indices:
            pytest.skip(
                "drift-before-notes ordering requires at least one drift and one note "
                "record; fixture must carry both classes"
            )

        last_drift = max(drift_indices)
        first_note = min(note_indices)

        assert first_note > last_drift, (
            f"doc-reconcile ordering violated: first note at index {first_note} "
            f"is not after last drift at index {last_drift}"
        )
