import pytest
from fbk.pipeline import validate_sighting, VALID_COMBINATIONS, VALID_TYPES, VALID_SEVERITIES


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
        assert "invalid type" in result
