from fbk.pipeline import validate_sighting, VALID_COMBINATIONS, VALID_TYPES, VALID_SEVERITIES

from fbk.pipeline import load_lens_matrix

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
