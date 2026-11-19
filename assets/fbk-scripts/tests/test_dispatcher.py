"""Exercise the shipped dispatcher and its actual command handlers."""

import importlib
import json
import subprocess
import sys
from pathlib import Path

from fbk import COMMAND_MAP

DISPATCHER = Path(__file__).parents[1] / "fbk.py"


def test_commands_resolve():
    for module in set(COMMAND_MAP.values()):
        assert callable(importlib.import_module(module).main)


def test_unrecognized_command():
    result = subprocess.run([sys.executable, str(DISPATCHER), "nonexistent"], capture_output=True)
    assert result.returncode == 2


def test_stdin_reaches_pipeline():
    result = subprocess.run(
        [sys.executable, str(DISPATCHER), "pipeline", "severity-filter", "--min-severity", "major"],
        input=json.dumps([{"severity": "minor"}, {"severity": "critical"}]),
        text=True, capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == [{"severity": "critical"}]
