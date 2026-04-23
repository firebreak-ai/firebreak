"""Tests for fbk.hooks.task_completed detection functions."""

import re

import pytest
from fbk.hooks.task_completed import detect_test_cmd, detect_lint_cmd

TASK_PATH_PATTERN = r"ai-docs/\S+?/\S*tasks/task-\S*\.md"


class TestTaskPathRegex:
    """Tests for the task-description path regex that scopes the hook to SDL tasks."""

    def test_matches_feature_suffixed_tasks_dir(self):
        """Current breakdown convention: ai-docs/<feature>/<feature>-tasks/task-NN.md."""
        desc = "Task file: ai-docs/agent-personas/agent-personas-tasks/task-06-impl-council-architect.md\nRead that file..."
        match = re.search(TASK_PATH_PATTERN, desc)
        assert match is not None
        assert match.group(0) == "ai-docs/agent-personas/agent-personas-tasks/task-06-impl-council-architect.md"

    def test_matches_plain_tasks_dir(self):
        """Legacy convention: ai-docs/<feature>/tasks/task-NN.md."""
        desc = "Task file: ai-docs/myfeature/tasks/task-01-setup.md\nExecute it."
        match = re.search(TASK_PATH_PATTERN, desc)
        assert match is not None
        assert match.group(0) == "ai-docs/myfeature/tasks/task-01-setup.md"

    def test_non_sdl_task_description_does_not_match(self):
        """A task description with no SDL task path should not match."""
        desc = "Refactor the login component to use the new auth hook."
        match = re.search(TASK_PATH_PATTERN, desc)
        assert match is None

    def test_path_without_ai_docs_prefix_does_not_match(self):
        """A task.md path outside ai-docs/ should not match."""
        desc = "Review tasks/task-foo.md under specs/"
        match = re.search(TASK_PATH_PATTERN, desc)
        assert match is None

    def test_matches_absolute_path(self):
        """Absolute paths should still match (regex searches for substring)."""
        desc = "Task file: /home/user/proj/ai-docs/feat/feat-tasks/task-01-bootstrap.md"
        match = re.search(TASK_PATH_PATTERN, desc)
        assert match is not None
        assert match.group(0) == "ai-docs/feat/feat-tasks/task-01-bootstrap.md"


class TestDetectTestCmd:
    """Tests for detect_test_cmd function."""

    def test_npm_project_detected(self, tmp_path):
        """Test npm project (package.json) returns 'npm test'."""
        (tmp_path / "package.json").write_text("{}")
        result = detect_test_cmd(str(tmp_path))
        assert result == "npm test"

    def test_cargo_project_detected(self, tmp_path):
        """Test Rust project (Cargo.toml) returns 'cargo test'."""
        (tmp_path / "Cargo.toml").write_text("")
        result = detect_test_cmd(str(tmp_path))
        assert result == "cargo test"

    def test_go_project_detected(self, tmp_path):
        """Test Go project (go.mod) returns 'go test ./...'."""
        (tmp_path / "go.mod").write_text("")
        result = detect_test_cmd(str(tmp_path))
        assert result == "go test ./..."

    def test_pytest_project_detected(self, tmp_path):
        """Test pytest project (pyproject.toml with [tool.pytest]) returns 'python -m pytest'."""
        (tmp_path / "pyproject.toml").write_text("[tool.pytest]\n")
        result = detect_test_cmd(str(tmp_path))
        assert result == "python -m pytest"

    def test_makefile_test_target_detected(self, tmp_path):
        """Test Makefile with test target returns 'make test'."""
        (tmp_path / "Makefile").write_text("test:\n\techo 'testing'\n")
        result = detect_test_cmd(str(tmp_path))
        assert result == "make test"

    def test_empty_directory_returns_empty_string(self, tmp_path):
        """Test empty directory returns empty string."""
        result = detect_test_cmd(str(tmp_path))
        assert result == ""


class TestDetectLintCmd:
    """Tests for detect_lint_cmd function."""

    def test_eslint_detected(self, tmp_path):
        """Test eslint detection (.eslintrc.json) returns string containing 'eslint'."""
        (tmp_path / ".eslintrc.json").write_text("{}")
        result = detect_lint_cmd(str(tmp_path))
        assert "eslint" in result

    def test_ruff_detected(self, tmp_path):
        """Test ruff detection (pyproject.toml with [tool.ruff]) returns string containing 'ruff'."""
        (tmp_path / "pyproject.toml").write_text("[tool.ruff]\n")
        result = detect_lint_cmd(str(tmp_path))
        assert "ruff" in result

    def test_empty_directory_returns_empty_string(self, tmp_path):
        """Test empty directory returns empty string."""
        result = detect_lint_cmd(str(tmp_path))
        assert result == ""
