"""Tests for fbk.hooks.task_completed detection functions."""

import pytest
from fbk.hooks.task_completed import detect_test_cmd, detect_lint_cmd


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
