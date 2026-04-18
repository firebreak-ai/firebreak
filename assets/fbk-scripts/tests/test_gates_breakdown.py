"""Tests for fbk.gates.breakdown validation logic."""

import json
import pytest
from fbk.gates.breakdown import validate_breakdown


class TestBreakdownGateValidation:
    """Tests for breakdown gate validation."""

    def test_uncovered_ac_detected(self):
        """AC in spec not covered by any task produces 'AC coverage' failure."""
        spec = """## Acceptance criteria
- AC-01: First requirement
- AC-02: Second requirement
"""
        manifest = {
            "category": "feature",
            "tasks": [
                {
                    "id": "task-01",
                    "title": "Test AC-01",
                    "file": "task-01-test-ac01.md",
                    "type": "test",
                    "wave_id": 1,
                    "dependencies": [],
                    "covers": ["AC-01"],
                    "model": "Haiku",
                    "status": "pending"
                },
                {
                    "id": "task-02",
                    "title": "Implement AC-01",
                    "file": "task-02-impl-ac01.md",
                    "type": "implementation",
                    "wave_id": 2,
                    "dependencies": ["task-01"],
                    "covers": ["AC-01"],
                    "model": "Haiku",
                    "status": "pending"
                }
            ]
        }
        tfiles = {
            "task-01-test-ac01.md": "## Files to create\n- `test.py`",
            "task-02-impl-ac01.md": "## Files to create\n- `impl.py`"
        }
        result = validate_breakdown(spec, manifest, tfiles)
        assert result["result"] == "fail"
        assert any("AC coverage" in f for f in result["failures"])

    def test_circular_dependency_detected(self):
        """Circular dependency (task-01 -> task-02 -> task-01) produces 'cycle' failure."""
        spec = """## Acceptance criteria
- AC-01: Requirement 1
"""
        manifest = {
            "category": "feature",
            "tasks": [
                {
                    "id": "task-01",
                    "title": "Test AC-01",
                    "file": "task-01.md",
                    "type": "test",
                    "wave_id": 1,
                    "dependencies": ["task-02"],
                    "covers": ["AC-01"],
                    "model": "Haiku",
                    "status": "pending"
                },
                {
                    "id": "task-02",
                    "title": "Implement AC-01",
                    "file": "task-02.md",
                    "type": "implementation",
                    "wave_id": 1,
                    "dependencies": ["task-01"],
                    "covers": ["AC-01"],
                    "model": "Haiku",
                    "status": "pending"
                }
            ]
        }
        tfiles = {
            "task-01.md": "## Files to create\n- `test.py`",
            "task-02.md": "## Files to create\n- `impl.py`"
        }
        result = validate_breakdown(spec, manifest, tfiles)
        assert result["result"] == "fail"
        assert any("cycle" in f.lower() for f in result["failures"])

    def test_wave_ordering_violation_detected(self):
        """Dependency in later wave than dependent produces 'Wave ordering' failure."""
        spec = """## Acceptance criteria
- AC-01: Requirement 1
"""
        manifest = {
            "category": "feature",
            "tasks": [
                {
                    "id": "task-01",
                    "title": "Test AC-01",
                    "file": "task-01.md",
                    "type": "test",
                    "wave_id": 2,
                    "dependencies": ["task-02"],
                    "covers": ["AC-01"],
                    "model": "Haiku",
                    "status": "pending"
                },
                {
                    "id": "task-02",
                    "title": "Implement AC-01",
                    "file": "task-02.md",
                    "type": "implementation",
                    "wave_id": 3,
                    "dependencies": [],
                    "covers": ["AC-01"],
                    "model": "Haiku",
                    "status": "pending"
                }
            ]
        }
        tfiles = {
            "task-01.md": "## Files to create\n- `test.py`",
            "task-02.md": "## Files to create\n- `impl.py`"
        }
        result = validate_breakdown(spec, manifest, tfiles)
        assert result["result"] == "fail"
        assert any("Wave ordering" in f for f in result["failures"])

    def test_file_conflict_detected(self):
        """Two tasks in same wave touching same file produces 'File conflict' failure."""
        spec = """## Acceptance criteria
- AC-01: Requirement 1
- AC-02: Requirement 2
"""
        manifest = {
            "category": "feature",
            "tasks": [
                {
                    "id": "task-01",
                    "title": "Test AC-01",
                    "file": "task-01.md",
                    "type": "test",
                    "wave_id": 1,
                    "dependencies": [],
                    "covers": ["AC-01"],
                    "model": "Haiku",
                    "status": "pending"
                },
                {
                    "id": "task-02",
                    "title": "Test AC-02",
                    "file": "task-02.md",
                    "type": "test",
                    "wave_id": 1,
                    "dependencies": [],
                    "covers": ["AC-02"],
                    "model": "Haiku",
                    "status": "pending"
                },
                {
                    "id": "task-03",
                    "title": "Implement AC-01",
                    "file": "task-03.md",
                    "type": "implementation",
                    "wave_id": 2,
                    "dependencies": ["task-01"],
                    "covers": ["AC-01"],
                    "model": "Haiku",
                    "status": "pending"
                },
                {
                    "id": "task-04",
                    "title": "Implement AC-02",
                    "file": "task-04.md",
                    "type": "implementation",
                    "wave_id": 2,
                    "dependencies": ["task-02"],
                    "covers": ["AC-02"],
                    "model": "Haiku",
                    "status": "pending"
                }
            ]
        }
        tfiles = {
            "task-01.md": "## Files to create\n- `test.py`",
            "task-02.md": "## Files to create\n- `test2.py`",
            "task-03.md": "## Files to create\n- `impl.py`\n- `shared.py`",
            "task-04.md": "## Files to create\n- `shared.py`"
        }
        result = validate_breakdown(spec, manifest, tfiles)
        assert result["result"] == "fail"
        assert any("File conflict" in f for f in result["failures"])

    def test_test_ordering_violation_detected(self):
        """Implementation task before test task in same wave produces 'Test ordering' failure."""
        spec = """## Acceptance criteria
- AC-01: Requirement 1
"""
        manifest = {
            "category": "feature",
            "tasks": [
                {
                    "id": "task-01",
                    "title": "Implement AC-01",
                    "file": "task-01.md",
                    "type": "implementation",
                    "wave_id": 1,
                    "dependencies": [],
                    "covers": ["AC-01"],
                    "model": "Haiku",
                    "status": "pending"
                },
                {
                    "id": "task-02",
                    "title": "Test AC-01",
                    "file": "task-02.md",
                    "type": "test",
                    "wave_id": 1,
                    "dependencies": [],
                    "covers": ["AC-01"],
                    "model": "Haiku",
                    "status": "pending"
                }
            ]
        }
        tfiles = {
            "task-01.md": "## Files to create\n- `impl.py`",
            "task-02.md": "## Files to create\n- `test.py`"
        }
        result = validate_breakdown(spec, manifest, tfiles)
        assert result["result"] == "fail"
        assert any("Test ordering" in f for f in result["failures"])

    def test_valid_breakdown_passes(self):
        """Valid breakdown with all ACs covered, no cycles, correct ordering, test-before-impl passes."""
        spec = """## Acceptance criteria
- AC-01: First requirement
- AC-02: Second requirement
"""
        manifest = {
            "category": "feature",
            "tasks": [
                {
                    "id": "task-01",
                    "title": "Test AC-01",
                    "file": "task-01.md",
                    "type": "test",
                    "wave_id": 1,
                    "dependencies": [],
                    "covers": ["AC-01"],
                    "model": "Haiku",
                    "status": "pending"
                },
                {
                    "id": "task-02",
                    "title": "Test AC-02",
                    "file": "task-02.md",
                    "type": "test",
                    "wave_id": 1,
                    "dependencies": [],
                    "covers": ["AC-02"],
                    "model": "Haiku",
                    "status": "pending"
                },
                {
                    "id": "task-03",
                    "title": "Implement AC-01",
                    "file": "task-03.md",
                    "type": "implementation",
                    "wave_id": 2,
                    "dependencies": ["task-01"],
                    "covers": ["AC-01"],
                    "model": "Haiku",
                    "status": "pending"
                },
                {
                    "id": "task-04",
                    "title": "Implement AC-02",
                    "file": "task-04.md",
                    "type": "implementation",
                    "wave_id": 2,
                    "dependencies": ["task-02"],
                    "covers": ["AC-02"],
                    "model": "Haiku",
                    "status": "pending"
                }
            ]
        }
        tfiles = {
            "task-01.md": "## Files to create\n- `test1.py`",
            "task-02.md": "## Files to create\n- `test2.py`",
            "task-03.md": "## Files to create\n- `impl1.py`",
            "task-04.md": "## Files to create\n- `impl2.py`"
        }
        result = validate_breakdown(spec, manifest, tfiles)
        assert result["result"] == "pass"
        assert len(result.get("failures", [])) == 0
