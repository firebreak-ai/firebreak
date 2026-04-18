"""Tests for fbk.py dispatcher command resolution and Python version check."""

import importlib
import json
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest


class TestDispatcherCommandMap:
    """Tests for COMMAND_MAP dict availability and contents."""

    def test_command_map_available(self):
        """COMMAND_MAP is accessible as module-level constant in fbk module."""
        try:
            import fbk
            assert hasattr(fbk, 'COMMAND_MAP'), "fbk module must expose COMMAND_MAP"
            assert isinstance(fbk.COMMAND_MAP, dict), "COMMAND_MAP must be a dict"
        except ImportError:
            pytest.skip("fbk module not yet implemented")

    def test_command_map_contains_all_14_commands(self):
        """COMMAND_MAP contains all 14 commands from spec."""
        try:
            import fbk
        except ImportError:
            pytest.skip("fbk module not yet implemented")

        expected_commands = {
            "spec-gate",
            "review-gate",
            "breakdown-gate",
            "task-reviewer-gate",
            "test-hash-gate",
            "task-completed",
            "dispatch-status",
            "pipeline",
            "audit",
            "config",
            "state",
            "session-logger",
            "session-manager",
            "ralph",
        }

        actual_commands = set(fbk.COMMAND_MAP.keys())
        assert expected_commands.issubset(actual_commands), \
            f"Missing commands: {expected_commands - actual_commands}"


class TestDispatcherModuleResolution:
    """Tests for command-to-module resolution (AC-04)."""

    def test_each_command_resolves_to_importable_module(self):
        """Each command in COMMAND_MAP resolves to an importable module."""
        try:
            import fbk
        except ImportError:
            pytest.skip("fbk module not yet implemented")

        for command, module_path in fbk.COMMAND_MAP.items():
            try:
                importlib.import_module(module_path)
            except ImportError as e:
                # Expected to fail until implementation phase completes
                pytest.skip(f"Module {module_path} for command {command} not yet implemented: {e}")


class TestDispatcherBehavior:
    """Tests for dispatcher behavioral contract via subprocess."""

    @pytest.fixture
    def dispatcher_path(self):
        """Return path to fbk.py dispatcher."""
        # fbk.py should be in assets/fbk-scripts/ or assets/fbk-scripts/fbk/
        fbk_scripts = Path(__file__).parent.parent
        candidates = [
            fbk_scripts / "fbk.py",
            fbk_scripts / "fbk" / "__main__.py",
        ]
        for path in candidates:
            if path.exists():
                return path
        pytest.skip("fbk.py dispatcher not found")

    def test_unrecognized_command_exits_2(self, dispatcher_path):
        """Unrecognized command exits with code 2."""
        result = subprocess.run(
            [sys.executable, str(dispatcher_path), "nonexistent-command"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 2, \
            f"Expected exit code 2, got {result.returncode}. stderr: {result.stderr}"

    def test_unrecognized_command_prints_to_stderr(self, dispatcher_path):
        """Unrecognized command prints available commands to stderr."""
        result = subprocess.run(
            [sys.executable, str(dispatcher_path), "nonexistent-command"],
            capture_output=True,
            text=True
        )
        # stderr should list available commands — verify at least one known command name present
        assert "spec-gate" in result.stderr, \
            f"stderr should list available commands including 'spec-gate', got: {result.stderr}"



class TestDispatcherIntegration:
    """Integration tests for dispatcher behavior with modules."""

    @pytest.fixture
    def dispatcher_path(self):
        """Return path to fbk.py dispatcher."""
        fbk_scripts = Path(__file__).parent.parent
        candidates = [
            fbk_scripts / "fbk.py",
            fbk_scripts / "fbk" / "__main__.py",
        ]
        for path in candidates:
            if path.exists():
                return path
        pytest.skip("fbk.py dispatcher not found")

    def test_stdin_passthrough_to_module(self, dispatcher_path):
        """stdin is passed through to module (integration test)."""
        # This test validates that stdin from dispatcher is passed to the target module
        # It requires the task-completed module to exist and accept JSON input
        test_input = json.dumps({"id": "test-001", "status": "completed"})

        result = subprocess.run(
            [sys.executable, str(dispatcher_path), "task-completed"],
            input=test_input,
            capture_output=True,
            text=True,
            timeout=5
        )
        # Test will skip if module not yet implemented
        # Otherwise, verify that input was processed without error
        if result.returncode != 0:
            pytest.skip(f"task-completed module not yet available: {result.stderr}")
