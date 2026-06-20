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

    def test_command_map_contains_all_20_commands(self):
        """COMMAND_MAP contains exactly all 20 commands from spec."""
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
            "session-state",
            "ralph",
            "intent-gate",
            "design-gate",
            "code-review-gate",
            "report",
            "run-retro",
        }

        actual_commands = set(fbk.COMMAND_MAP.keys())
        assert actual_commands == expected_commands, (
            f"COMMAND_MAP mismatch — extra: {actual_commands - expected_commands}, "
            f"missing: {expected_commands - actual_commands}"
        )
        assert fbk.COMMAND_MAP["report"] == "fbk.report"
        assert fbk.COMMAND_MAP["run-retro"] == "fbk.run_retro"

    def test_intent_gate_maps_to_exact_module(self):
        """COMMAND_MAP["intent-gate"] == "fbk.gates.intent"."""
        try:
            import fbk
        except ImportError:
            pytest.skip("fbk module not yet implemented")
        assert "intent-gate" in fbk.COMMAND_MAP, \
            "intent-gate missing from COMMAND_MAP"
        assert fbk.COMMAND_MAP["intent-gate"] == "fbk.gates.intent", \
            f"Expected 'fbk.gates.intent', got '{fbk.COMMAND_MAP.get('intent-gate')}'"

    def test_design_gate_maps_to_exact_module(self):
        """COMMAND_MAP["design-gate"] == "fbk.gates.design"."""
        try:
            import fbk
        except ImportError:
            pytest.skip("fbk module not yet implemented")
        assert "design-gate" in fbk.COMMAND_MAP, \
            "design-gate missing from COMMAND_MAP"
        assert fbk.COMMAND_MAP["design-gate"] == "fbk.gates.design", \
            f"Expected 'fbk.gates.design', got '{fbk.COMMAND_MAP.get('design-gate')}'"

    def test_code_review_gate_maps_to_exact_module(self):
        """COMMAND_MAP["code-review-gate"] == "fbk.gates.code_review" (underscore)."""
        try:
            import fbk
        except ImportError:
            pytest.skip("fbk module not yet implemented")
        assert "code-review-gate" in fbk.COMMAND_MAP, \
            "code-review-gate missing from COMMAND_MAP"
        assert fbk.COMMAND_MAP["code-review-gate"] == "fbk.gates.code_review", \
            f"Expected 'fbk.gates.code_review', got '{fbk.COMMAND_MAP.get('code-review-gate')}'"


class TestDispatcherModuleResolution:
    """Tests for command-to-module resolution (AC-04)."""

    def test_each_command_resolves_to_importable_module(self):
        """Each command in COMMAND_MAP resolves to an importable module.

        Note: This test now also covers run-retro by iteration; it requires
        fbk.run_retro to be importable and will fail until the reader module
        is registered in COMMAND_MAP and the module is implemented.
        """
        try:
            import fbk
        except ImportError:
            pytest.skip("fbk module not yet implemented")

        for command, module_path in fbk.COMMAND_MAP.items():
            importlib.import_module(module_path)

    def test_run_retro_module_importable_with_main(self):
        """fbk.run_retro is importable and exposes a callable main function."""
        try:
            import fbk.run_retro
        except ImportError:
            pytest.skip("fbk.run_retro module not yet implemented")

        assert callable(fbk.run_retro.main), \
            "fbk.run_retro.main must be callable"


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
        """stdin JSON is passed through to the task-completed module and parsed.

        Uses a task_description containing a valid SDL task path so the module
        moves past the early-exit guard and attempts test/lint detection.  The
        resulting WARN lines on stderr are the only observable signal that the
        module actually consumed the stdin payload.
        """
        test_input = json.dumps({
            "task_description": "Implement ai-docs/myfeature/tasks/task-01-setup.md",
            # Use a directory with no test runner / linter so the hook returns
            # quickly without spawning an actual test suite.
            "cwd": "/tmp",
        })

        result = subprocess.run(
            [sys.executable, str(dispatcher_path), "task-completed"],
            input=test_input,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, (
            f"task-completed exited {result.returncode}; stderr: {result.stderr}"
        )
        # The module emits this WARN when it parsed a task path but found no test
        # runner in cwd.  Its presence proves stdin was read, JSON-decoded, and the
        # task_description field was actually used by the hook logic.
        assert "No recognized test runner" in result.stderr, (
            "Expected WARN about missing test runner on stderr — "
            "this proves stdin was received and parsed by the module. "
            f"Got stderr: {result.stderr!r}"
        )
