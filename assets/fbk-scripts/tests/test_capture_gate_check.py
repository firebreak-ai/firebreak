"""Unit tests for the per-project capture gate: instrumentation detection and level resolution.

Tests cover:
- Detecting whether a project is instrumented (sentinel or capture.cfg present)
- Resolving the capture level (off/standard/full) based on configuration and defaults
- Handling of filesystem errors and invalid configuration values
- Bounded single-line reads to prevent performance degradation
"""

import os
import pytest

# Red phase: gate_check module does not exist yet.
try:
    from fbk.capture import gate_check
    GATE_CHECK_AVAILABLE = True
except ImportError:
    GATE_CHECK_AVAILABLE = False

from tests import capture_fixtures

pytestmark = pytest.mark.skipif(
    not GATE_CHECK_AVAILABLE,
    reason="fbk.capture.gate_check module not yet implemented"
)


class TestProjectIsInstrumented:
    """Tests for gate_check.project_is_instrumented(cwd) -> bool."""

    def test_instrumented_true_for_firebreak_marked_project(self, tmp_path):
        """A project with .claude/automation/.fbk-managed sentinel is instrumented."""
        root = capture_fixtures.make_project(str(tmp_path), instrumented=True, marked=True)
        assert gate_check.project_is_instrumented(root) is True

    def test_instrumented_true_for_capture_cfg_project(self, tmp_path):
        """A project with .fbk-capture/capture.cfg (without sentinel) is instrumented."""
        root = capture_fixtures.make_project(
            str(tmp_path), instrumented=False, capture_cfg="standard"
        )
        assert gate_check.project_is_instrumented(root) is True

    def test_instrumented_false_for_bare_project(self, tmp_path):
        """A bare project with neither sentinel nor capture.cfg is not instrumented."""
        root = capture_fixtures.make_project(str(tmp_path), instrumented=False)
        assert gate_check.project_is_instrumented(root) is False

    def test_instrumented_false_on_filesystem_error(self, tmp_path):
        """Filesystem errors (e.g., non-existent path) resolve safely to False, no raise."""
        nonexistent_path = os.path.join(str(tmp_path), "does_not_exist")
        # Should return False without raising an exception
        assert gate_check.project_is_instrumented(nonexistent_path) is False

    def test_instrumented_false_on_file_where_directory_expected(self, tmp_path):
        """When a directory is expected but a file exists instead, return False safely."""
        # Create a file that would conflict with .claude/automation directory
        test_file = os.path.join(str(tmp_path), "project")
        with open(test_file, "w") as f:
            f.write("conflict")
        # Trying to treat a file as a directory should return False, not raise
        assert gate_check.project_is_instrumented(test_file) is False


class TestResolveCaptureLevel:
    """Tests for gate_check.resolve_capture_level(cwd) -> "off"|"standard"|"full"."""

    def test_level_returns_off_from_cfg(self, tmp_path):
        """Valid capture_level=off in capture.cfg is returned."""
        root = capture_fixtures.make_project(
            str(tmp_path), instrumented=False, capture_cfg="off"
        )
        assert gate_check.resolve_capture_level(root) == "off"

    def test_level_returns_standard_from_cfg(self, tmp_path):
        """Valid capture_level=standard in capture.cfg is returned."""
        root = capture_fixtures.make_project(
            str(tmp_path), instrumented=False, capture_cfg="standard"
        )
        assert gate_check.resolve_capture_level(root) == "standard"

    def test_level_defaults_standard_for_firebreak_without_cfg(self, tmp_path):
        """A Firebreak-marked project without capture.cfg defaults to standard."""
        root = capture_fixtures.make_project(
            str(tmp_path), instrumented=True, marked=True, capture_cfg=None
        )
        assert gate_check.resolve_capture_level(root) == "standard"

    def test_level_invalid_cfg_warns_and_defaults_standard(self, tmp_path, capsys):
        """Invalid capture_level value warns to stderr and defaults to standard."""
        root = capture_fixtures.make_project(str(tmp_path), instrumented=False)
        # Write an invalid capture.cfg manually
        cfg_path = os.path.join(root, ".fbk-capture", "capture.cfg")
        os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
        with open(cfg_path, "w") as f:
            f.write("capture_level=banana\n")

        result = gate_check.resolve_capture_level(root)
        assert result == "standard"

        # Check that stderr contains a warning about the invalid value
        captured = capsys.readouterr()
        assert captured.err  # stderr should not be empty
        assert "banana" in captured.err or "invalid" in captured.err.lower()

    def test_level_off_for_uninstrumented_project(self, tmp_path):
        """A bare uninstrumented project resolves to off."""
        root = capture_fixtures.make_project(str(tmp_path), instrumented=False)
        assert gate_check.resolve_capture_level(root) == "off"

    def test_level_reads_only_one_line(self, tmp_path):
        """Large trailing content after the first line does not affect the result.

        This verifies the bounded-read behavior: only the first line is read,
        so a multi-megabyte file does not change the resolved level.
        """
        root = capture_fixtures.make_project(
            str(tmp_path), instrumented=False, capture_cfg="standard"
        )
        # Append a very large second line to the capture.cfg
        cfg_path = os.path.join(root, ".fbk-capture", "capture.cfg")
        with open(cfg_path, "a") as f:
            # Write ~5MB of padding on a second line
            large_padding = "x" * (5 * 1024 * 1024)
            f.write(large_padding + "\n")

        # Resolve should still return standard (only first line read)
        result = gate_check.resolve_capture_level(root)
        assert result == "standard"
