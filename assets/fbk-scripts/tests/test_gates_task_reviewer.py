"""Tests for fbk.gates.task_reviewer validation logic."""

import pytest
from fbk.gates.task_reviewer import validate_tasks, parse_frontmatter


class TestParseFormatter:
    """Tests for parse_frontmatter() helper."""

    def test_valid_frontmatter(self):
        """Valid YAML frontmatter is parsed correctly."""
        content = """---
id: task-01
type: test
wave: 1
---
Body content here"""
        fm = parse_frontmatter(content)
        assert fm.get('id') == 'task-01'
        assert fm.get('type') == 'test'
        assert fm.get('wave') == 1

    def test_missing_frontmatter(self):
        """Content without frontmatter returns empty dict."""
        content = "Just body content"
        fm = parse_frontmatter(content)
        assert fm == {}

    def test_unclosed_frontmatter(self):
        """Unclosed frontmatter returns empty dict."""
        content = """---
id: task-01
type: test
Body content here"""
        fm = parse_frontmatter(content)
        assert fm == {}


class TestValidateTasks:
    """Tests for validate_tasks() behavioral contract."""

    def test_missing_required_field(self):
        """Task file missing 'id' field produces failure with descriptive message."""
        tasks = {
            "task-01.md": {
                "type": "test",
                "wave": 1,
                "covers": ["AC-01"],
                "completion_gate": "tests compile",
                "files_to_create": ["test.py"]
            }
        }
        spec_acs = {"AC-01"}
        failures = validate_tasks(tasks, spec_acs)
        assert len(failures) > 0
        assert any("missing required field" in f for f in failures)
        assert any("id" in f for f in failures)

    def test_invalid_type_enum(self):
        """Task file with invalid type produces failure with type constraints."""
        tasks = {
            "task-01.md": {
                "id": "task-01",
                "type": "unknown",
                "wave": 1,
                "covers": ["AC-01"],
                "completion_gate": "tests compile",
                "files_to_create": ["test.py"]
            }
        }
        spec_acs = {"AC-01"}
        failures = validate_tasks(tasks, spec_acs)
        assert len(failures) > 0
        assert any("type must be" in f for f in failures)

    def test_implementation_missing_test_tasks(self):
        """Implementation task without test_tasks produces failure."""
        tasks = {
            "task-02.md": {
                "id": "task-02",
                "type": "implementation",
                "wave": 2,
                "covers": ["AC-01"],
                "completion_gate": "code compiles",
                "files_to_modify": ["src/main.py"]
            }
        }
        spec_acs = {"AC-01"}
        failures = validate_tasks(tasks, spec_acs)
        assert len(failures) > 0
        assert any("missing 'test_tasks'" in f for f in failures)

    def test_file_scope_conflict_same_wave(self):
        """Two tasks in same wave claiming same file produces File scope conflict."""
        tasks = {
            "task-01.md": {
                "id": "task-01",
                "type": "test",
                "wave": 1,
                "covers": ["AC-01"],
                "completion_gate": "tests compile",
                "files_to_create": ["shared.py"]
            },
            "task-02.md": {
                "id": "task-02",
                "type": "test",
                "wave": 1,
                "covers": ["AC-02"],
                "completion_gate": "tests compile",
                "files_to_create": ["shared.py"]
            }
        }
        spec_acs = {"AC-01", "AC-02"}
        failures = validate_tasks(tasks, spec_acs)
        assert len(failures) > 0
        assert any("File scope conflict" in f for f in failures)

    def test_valid_task_set_passes(self):
        """Valid task set covering all spec ACs produces no failures."""
        tasks = {
            "task-01.md": {
                "id": "task-01",
                "type": "test",
                "wave": 1,
                "covers": ["AC-01", "AC-02"],
                "completion_gate": "tests compile",
                "files_to_create": ["tests/test_feature.py"]
            },
            "task-02.md": {
                "id": "task-02",
                "type": "implementation",
                "wave": 2,
                "covers": ["AC-01", "AC-02"],
                "completion_gate": "code compiles",
                "files_to_modify": ["src/main.py"],
                "test_tasks": ["task-01"]
            }
        }
        spec_acs = {"AC-01", "AC-02"}
        failures = validate_tasks(tasks, spec_acs)
        assert len(failures) == 0

    def test_missing_files_to_create_or_modify(self):
        """Task with neither files_to_create nor files_to_modify produces failure."""
        tasks = {
            "task-01.md": {
                "id": "task-01",
                "type": "test",
                "wave": 1,
                "covers": ["AC-01"],
                "completion_gate": "tests compile"
            }
        }
        spec_acs = {"AC-01"}
        failures = validate_tasks(tasks, spec_acs)
        assert len(failures) > 0
        assert any("must have files_to_create or files_to_modify" in f for f in failures)

    def test_invalid_ac_identifier_format(self):
        """Task with invalid AC identifier format produces failure."""
        tasks = {
            "task-01.md": {
                "id": "task-01",
                "type": "test",
                "wave": 1,
                "covers": ["INVALID-01"],
                "completion_gate": "tests compile",
                "files_to_create": ["test.py"]
            }
        }
        spec_acs = {"AC-01"}
        failures = validate_tasks(tasks, spec_acs)
        assert len(failures) > 0
        assert any("invalid AC identifier" in f for f in failures)

    def test_ac_coverage_test_task_missing(self):
        """AC not covered by any test task produces failure."""
        tasks = {
            "task-01.md": {
                "id": "task-01",
                "type": "implementation",
                "wave": 1,
                "covers": ["AC-01"],
                "completion_gate": "code compiles",
                "files_to_modify": ["src/main.py"],
                "test_tasks": []
            }
        }
        spec_acs = {"AC-01"}
        failures = validate_tasks(tasks, spec_acs)
        assert len(failures) > 0
        assert any("AC-01" in f and "not covered by any test task" in f for f in failures)

    def test_ac_coverage_impl_task_missing(self):
        """AC not covered by any implementation task produces failure."""
        tasks = {
            "task-01.md": {
                "id": "task-01",
                "type": "test",
                "wave": 1,
                "covers": ["AC-01"],
                "completion_gate": "tests compile",
                "files_to_create": ["test.py"]
            }
        }
        spec_acs = {"AC-01"}
        failures = validate_tasks(tasks, spec_acs)
        assert len(failures) > 0
        assert any("AC-01" in f and "not covered by any implementation task" in f for f in failures)

    def test_test_tasks_reference_validation(self):
        """Implementation task referencing non-existent test task produces failure."""
        tasks = {
            "task-02.md": {
                "id": "task-02",
                "type": "implementation",
                "wave": 2,
                "covers": ["AC-01"],
                "completion_gate": "code compiles",
                "files_to_modify": ["src/main.py"],
                "test_tasks": ["task-01"]
            }
        }
        spec_acs = {"AC-01"}
        failures = validate_tasks(tasks, spec_acs)
        assert len(failures) > 0
        assert any("test_tasks reference" in f and "does not match any task id" in f for f in failures)

    def test_corrective_category_allows_test_only_ac(self):
        """Corrective category allows AC covered only by test task."""
        tasks = {
            "task-01.md": {
                "id": "task-01",
                "type": "test",
                "wave": 1,
                "covers": ["AC-01"],
                "completion_gate": "tests compile",
                "files_to_create": ["test.py"]
            }
        }
        spec_acs = {"AC-01"}
        failures = validate_tasks(tasks, spec_acs, category="corrective")
        assert len(failures) == 0

    def test_testing_infrastructure_category_allows_test_only_ac(self):
        """Testing-infrastructure category allows AC covered only by test task."""
        tasks = {
            "task-01.md": {
                "id": "task-01",
                "type": "test",
                "wave": 1,
                "covers": ["AC-01"],
                "completion_gate": "tests compile",
                "files_to_create": ["test.py"]
            }
        }
        spec_acs = {"AC-01"}
        failures = validate_tasks(tasks, spec_acs, category="testing-infrastructure")
        assert len(failures) == 0
