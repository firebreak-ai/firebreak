import pytest
from fbk.pipeline import validate_sighting, VALID_COMBINATIONS, VALID_TYPES, VALID_SEVERITIES

# Red-phase guard: load_lens_matrix and LensVocabulary do not exist yet.
# The new test class is skipped until those callables are present.
try:
    from fbk.pipeline import load_lens_matrix, LensVocabulary
    _parameterized_callables_present = True
except ImportError:
    _parameterized_callables_present = False

# Red-phase guard for validate_against_mode (scan-mode discriminator, task-09).
try:
    from fbk.pipeline import validate_against_mode
    _scan_mode_callable_present = True
except ImportError:
    _scan_mode_callable_present = False


class TestValidateSighting:
    """Unit tests for fbk.pipeline validate_sighting() function."""

    def test_valid_behavioral_critical_passes(self):
        """Valid sighting with type='behavioral', severity='critical' returns None."""
        sighting = {
            "id": "test-001",
            "title": "Valid behavioral finding",
            "location": {"file": "test.py", "start_line": 10},
            "type": "behavioral",
            "severity": "critical",
            "mechanism": "Test mechanism description",
            "consequence": "Test consequence description",
            "evidence": "Test evidence"
        }
        result = validate_sighting(sighting)
        assert result is None

    def test_invalid_behavioral_minor_rejected(self):
        """Invalid sighting with type='behavioral', severity='minor' returns error."""
        sighting = {
            "id": "test-002",
            "title": "Invalid behavioral finding",
            "location": {"file": "test.py", "start_line": 10},
            "type": "behavioral",
            "severity": "minor",
            "mechanism": "Test mechanism description",
            "consequence": "Test consequence description",
            "evidence": "Test evidence"
        }
        result = validate_sighting(sighting)
        assert result is not None
        assert "invalid type-severity" in result

    def test_invalid_structural_critical_rejected(self):
        """Invalid sighting with type='structural', severity='critical' returns error."""
        sighting = {
            "id": "test-003",
            "title": "Invalid structural finding",
            "location": {"file": "test.py", "start_line": 10},
            "type": "structural",
            "severity": "critical",
            "mechanism": "Test mechanism description",
            "consequence": "Test consequence description",
            "evidence": "Test evidence"
        }
        result = validate_sighting(sighting)
        assert result is not None
        assert "invalid type-severity" in result

    def test_missing_title_field_rejected(self):
        """Sighting missing 'title' field returns error."""
        sighting = {
            "id": "test-004",
            "location": {"file": "test.py", "start_line": 10},
            "type": "behavioral",
            "severity": "critical",
            "mechanism": "Test mechanism description",
            "consequence": "Test consequence description",
            "evidence": "Test evidence"
        }
        result = validate_sighting(sighting)
        assert result is not None
        assert "missing field" in result

    def test_title_below_minimum_length_rejected(self):
        """Sighting with title shorter than 10 characters returns error."""
        sighting = {
            "id": "test-005",
            "title": "Short",
            "location": {"file": "test.py", "start_line": 10},
            "type": "behavioral",
            "severity": "critical",
            "mechanism": "Test mechanism description",
            "consequence": "Test consequence description",
            "evidence": "Test evidence"
        }
        result = validate_sighting(sighting)
        assert result is not None
        assert "minimum length" in result

    def test_invalid_type_rejected(self):
        """Sighting with invalid type 'performance' returns error."""
        sighting = {
            "id": "test-006",
            "title": "Invalid type finding",
            "location": {"file": "test.py", "start_line": 10},
            "type": "performance",
            "severity": "critical",
            "mechanism": "Test mechanism description",
            "consequence": "Test consequence description",
            "evidence": "Test evidence"
        }
        result = validate_sighting(sighting)
        assert result is not None
        assert "invalid type 'performance'" in result
        assert "type-severity" not in result


# ---------------------------------------------------------------------------
# Parameterized-validation tests (new in task-02)
# Skipped when load_lens_matrix / LensVocabulary are not yet importable.
# ---------------------------------------------------------------------------

# Pinned lens-matrix fenced block format that load_lens_matrix must parse.
_LENS_MATRIX_CONTENT = """\
```lens-matrix
types: [behavioral, structural]
severities: [critical, major, minor, info]
matrix:
  behavioral: [critical, major]
  structural: [minor, info]
required: [title, location, type, severity, mechanism, consequence, evidence]
```
"""


def _write_lens_fixture(tmp_path):
    """Write the pinned lens-matrix block to a temp file and return its path."""
    lens_file = tmp_path / "test_lens.md"
    lens_file.write_text(_LENS_MATRIX_CONTENT)
    return lens_file


@pytest.mark.skipif(
    not _parameterized_callables_present,
    reason="load_lens_matrix and LensVocabulary not yet implemented",
)
class TestParameterizedValidation:
    """Unit tests for load_lens_matrix() and the per-lens validate_sighting(finding, vocab) path."""

    def test_load_lens_matrix_parses_vocabulary(self, tmp_path):
        """load_lens_matrix returns a LensVocabulary with types, severities, matrix, and required parsed from the fenced block."""
        lens_path = _write_lens_fixture(tmp_path)
        vocab = load_lens_matrix(lens_path)

        assert vocab.types == {"behavioral", "structural"}
        assert vocab.severities == {"critical", "major", "minor", "info"}
        assert vocab.matrix["behavioral"] == {"critical", "major"}
        assert vocab.matrix["structural"] == {"minor", "info"}
        # The researcher-candidate required set excludes 'id' but includes 'title'.
        assert "id" not in vocab.required
        assert "title" in vocab.required

    def test_finding_valid_for_loaded_lens_passes(self, tmp_path):
        """A finding with type='structural', severity='minor' (valid for the loaded lens) is accepted."""
        lens_path = _write_lens_fixture(tmp_path)
        vocab = load_lens_matrix(lens_path)
        finding = {
            "title": "Structural minor finding",
            "location": {"file": "test.py", "start_line": 1},
            "type": "structural",
            "severity": "minor",
            "mechanism": "Test mechanism description",
            "consequence": "Test consequence description",
            "evidence": "Test evidence",
        }
        result = validate_sighting(finding, vocab=vocab)
        assert result is None

    def test_finding_invalid_for_loaded_lens_rejected(self, tmp_path):
        """A finding with type='structural', severity='critical' (invalid for the loaded lens matrix) is rejected with a type-severity error."""
        lens_path = _write_lens_fixture(tmp_path)
        vocab = load_lens_matrix(lens_path)
        finding = {
            "title": "Structural critical finding",
            "location": {"file": "test.py", "start_line": 1},
            "type": "structural",
            "severity": "critical",
            "mechanism": "Test mechanism description",
            "consequence": "Test consequence description",
            "evidence": "Test evidence",
        }
        result = validate_sighting(finding, vocab=vocab)
        assert result is not None
        assert "type-severity" in result

    def test_id_free_candidate_passes_against_lens_required(self, tmp_path):
        """A researcher candidate omitting 'id' passes when validated against a vocab whose required set excludes 'id'."""
        lens_path = _write_lens_fixture(tmp_path)
        vocab = load_lens_matrix(lens_path)
        # No 'id' key — this is a pre-assignment researcher candidate.
        finding = {
            "title": "Researcher candidate without id",
            "location": {"file": "test.py", "start_line": 1},
            "type": "behavioral",
            "severity": "critical",
            "mechanism": "Test mechanism description",
            "consequence": "Test consequence description",
            "evidence": "Test evidence",
        }
        result = validate_sighting(finding, vocab=vocab)
        assert result is None


# ---------------------------------------------------------------------------
# Scan-mode bypass tests (task-09, AC-18)
# Skipped until validate_against_mode is importable.
# ---------------------------------------------------------------------------

_DOC_RECONCILE_RECORD = {
    "class": "drift",
    "doc": "design.md",
    "doc_says": "X",
    "code_shows": "Y",
    "rationale": "Z",
}


@pytest.mark.skipif(
    not _scan_mode_callable_present,
    reason="validate_against_mode not yet implemented — red-phase skip",
)
class TestScanModeBypass:
    """Proves the scan-mode validation bypass is real, not vacuous.

    Uses a doc-reconcile record (no severity/type/mechanism/location) that the
    finding-validator rejects under the code-review vocabulary.  The negative
    confirms the validator would reject it; the positive confirms the scan-mode
    path accepts the same record.
    """

    def test_finding_validator_would_reject_doc_reconcile_record(self):
        """validate_sighting(record) with default vocabulary returns a non-None error for a doc-reconcile record.

        The record has no severity, type, mechanism, or location — all required by
        the code-review vocabulary.  This is the negative that makes the positive
        (scan-mode accepts) non-vacuous.
        """
        result = validate_sighting(_DOC_RECONCILE_RECORD)
        assert result is not None, (
            "Expected validate_sighting to reject the doc-reconcile record under the "
            "default code-review vocabulary (missing required finding fields), got None"
        )

    def test_scan_mode_accepts_the_rejected_record(self):
        """validate_against_mode(record, vocab=None, output_mode='scan') returns None for the same doc-reconcile record.

        The scan path skips finding-validation entirely, so a record the finding-validator
        rejects is accepted when routed through the scan-mode discriminator.
        """
        result = validate_against_mode(_DOC_RECONCILE_RECORD, vocab=None, output_mode="scan")
        assert result is None, (
            "Expected scan-mode to accept the doc-reconcile record (bypass finding-validation), "
            f"got: {result!r}"
        )

    def test_finding_mode_still_routes_through_validator(self):
        """validate_against_mode(record, vocab=None, output_mode='finding') returns the same error as validate_sighting.

        Proves the bypass is mode-gated: finding-mode still validates, so the
        difference in scan vs finding mode is observable.
        """
        expected = validate_sighting(_DOC_RECONCILE_RECORD)
        result = validate_against_mode(_DOC_RECONCILE_RECORD, vocab=None, output_mode="finding")
        assert result == expected, (
            f"Expected finding-mode to return the same rejection as validate_sighting "
            f"({expected!r}), got: {result!r}"
        )
