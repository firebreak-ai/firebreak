"""Tests for fbk.gates.task_reviewer validation logic."""

import json
import os
import sys
from pathlib import Path

import pytest
from fbk.gates.task_reviewer import validate_tasks, parse_frontmatter
import fbk.gates.task_reviewer as _task_reviewer_mod

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


# ---------------------------------------------------------------------------
# Minimal passing fixture helpers (reuses the shapes from TestValidateTasks)
# ---------------------------------------------------------------------------

_TASK_REVIEWER_SPEC = """\
# Feature Specification

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

_TASK_TEST_CONTENT = """\
---
id: task-01
type: test
wave: 1
covers: [AC-01]
completion_gate: tests compile
files_to_create:
  - tests/test_feature.py
---

# Objective
Write tests for the feature.
"""

_TASK_IMPL_CONTENT = """\
---
id: task-02
type: implementation
wave: 2
covers: [AC-01]
completion_gate: code compiles
files_to_modify:
  - src/placeholder.py
test_tasks:
  - task-01
---

# Objective
Implement the feature.
"""


def _make_task_reviewer_fixture(base_dir):
    """Build a minimal project that the task-reviewer gate passes.

    Returns (spec_path, tasks_dir, project_root) as strings.  The
    files_to_modify path (src/placeholder.py) is created so the gate's
    existence check does not flag it.
    """
    root = os.path.join(base_dir, "tr-project")
    os.makedirs(root, exist_ok=True)

    spec_file = os.path.join(root, "sample-spec.md")
    with open(spec_file, "w") as fh:
        fh.write(_TASK_REVIEWER_SPEC)

    tasks_dir = os.path.join(root, "tasks")
    os.makedirs(tasks_dir, exist_ok=True)

    with open(os.path.join(tasks_dir, "task-01.md"), "w") as fh:
        fh.write(_TASK_TEST_CONTENT)
    with open(os.path.join(tasks_dir, "task-02.md"), "w") as fh:
        fh.write(_TASK_IMPL_CONTENT)

    # Create the placeholder file referenced by task-02's files_to_modify.
    src_dir = os.path.join(root, "src")
    os.makedirs(src_dir, exist_ok=True)
    with open(os.path.join(src_dir, "placeholder.py"), "w") as fh:
        fh.write("# placeholder\n")

    return spec_file, tasks_dir, root


# ---------------------------------------------------------------------------
# Envelope write assertions — task-reviewer gate (AC-12)
# ---------------------------------------------------------------------------

# The task-reviewer gate must write NO PIPELINE_COMMAND of its own.  One
# dispatch through fbk.py yields exactly one PIPELINE_COMMAND, written by
# the chokepoint; the chokepoint-side positive assertion lives in
# tests/test_capture_chokepoint_integration.py.  These tests pin the negative
# half: calling the gate directly (bypassing the chokepoint) must leave the
# events file empty.

@pytest.mark.skipif(
    not _EVENT_WRITER_AVAILABLE,
    reason="fbk.capture.event_writer not available",
)
class TestTaskReviewerGateWritesNoEnvelope:
    """Task-reviewer gate writes no PIPELINE_COMMAND of its own on pass or fail (AC-12).

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

    def test_task_reviewer_gate_pass_writes_no_envelope(self, tmp_path, monkeypatch):
        """Task-reviewer gate pass path writes no PIPELINE_COMMAND when called directly."""
        spec_file, tasks_dir, project_root = _make_task_reviewer_fixture(str(tmp_path))

        # Wrap the project in the capture-fixtures project tree so chdir points
        # to an instrumented root.
        instr_root = capture_fixtures.make_project(str(tmp_path), instrumented=True, marked=True)

        # Copy the spec and task files into the instrumented project.
        spec_dest = os.path.join(instr_root, "sample-spec.md")
        with open(spec_file) as fh:
            spec_content = fh.read()
        with open(spec_dest, "w") as fh:
            fh.write(spec_content)

        tasks_dest = os.path.join(instr_root, "tasks")
        os.makedirs(tasks_dest, exist_ok=True)
        for fname in ("task-01.md", "task-02.md"):
            src = os.path.join(tasks_dir, fname)
            dst = os.path.join(tasks_dest, fname)
            with open(src) as fh:
                content = fh.read()
            with open(dst, "w") as fh:
                fh.write(content)

        # The impl task references src/placeholder.py relative to project_root.
        src_dir = os.path.join(instr_root, "src")
        os.makedirs(src_dir, exist_ok=True)
        with open(os.path.join(src_dir, "placeholder.py"), "w") as fh:
            fh.write("# placeholder\n")

        monkeypatch.chdir(instr_root)
        monkeypatch.setattr(
            sys, "argv",
            ["task-reviewer-gate", spec_dest, tasks_dest, "--project-root", instr_root],
        )

        with pytest.raises(SystemExit) as exc_info:
            _task_reviewer_mod.main()
        assert exc_info.value.code == 0

        assert self._read_envelopes(instr_root) == []

    def test_task_reviewer_gate_fail_writes_no_envelope(self, tmp_path, monkeypatch):
        """Task-reviewer gate fail path writes no PIPELINE_COMMAND when called directly."""
        spec_file, tasks_dir, project_root = _make_task_reviewer_fixture(str(tmp_path))

        instr_root = capture_fixtures.make_project(str(tmp_path), instrumented=True, marked=True)

        spec_dest = os.path.join(instr_root, "sample-spec.md")
        with open(spec_file) as fh:
            spec_content = fh.read()
        with open(spec_dest, "w") as fh:
            fh.write(spec_content)

        tasks_dest = os.path.join(instr_root, "tasks")
        os.makedirs(tasks_dest, exist_ok=True)
        for fname in ("task-01.md", "task-02.md"):
            src = os.path.join(tasks_dir, fname)
            dst = os.path.join(tasks_dest, fname)
            with open(src) as fh:
                content = fh.read()
            with open(dst, "w") as fh:
                fh.write(content)

        # Deliberately omit src/placeholder.py so the impl task's files_to_modify
        # path does not exist — this forces a fail result.

        monkeypatch.chdir(instr_root)
        monkeypatch.setattr(
            sys, "argv",
            ["task-reviewer-gate", spec_dest, tasks_dest, "--project-root", instr_root],
        )

        with pytest.raises(SystemExit) as exc_info:
            _task_reviewer_mod.main()
        assert exc_info.value.code == 2

        assert self._read_envelopes(instr_root) == []
