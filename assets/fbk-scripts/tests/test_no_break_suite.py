"""Meta-test: AC-11 no-regression guard.

Runs the existing gate and telemetry test modules as a subprocess and
asserts they pass with zero failures. This is a characterization test —
the suites are green today and the migration must keep them green.

This file is intentionally excluded from its own subprocess run via an
explicit module list (not a directory glob), so there is no recursion risk.
"""

import sys
from pathlib import Path

import pytest

# Resolved relative to this file: assets/fbk-scripts/
FBK_SCRIPTS = Path(__file__).parent.parent

# Modules that must pass unchanged through the migration.
# Paths are relative to FBK_SCRIPTS so subprocess cwd matches.
UNCHANGED_MODULES = [
    "tests/test_gates_intent.py",
    "tests/test_gates_design.py",
    "tests/test_gates_spec.py",
    "tests/test_gates_breakdown.py",
    "tests/test_gates_task_reviewer.py",
    "tests/test_gates_test_hash.py",
    "tests/test_gates_review.py",
    "tests/test_gates_code_review.py",
    "tests/test_capture_report_integration.py",
]

# Modules whose assertions were sanctioned to change (new agent names,
# coherence-gate command count). They must be green after their updates.
CHANGED_MODULES = [
    "tests/test_shapes.py",
    "tests/test_dispatcher.py",
    "tests/test_capture_known_agents.py",
]


def _run_pytest(modules: list[str]) -> tuple[int, str]:
    """Run pytest over *modules* (relative paths) in the fbk-scripts directory."""
    import subprocess

    result = subprocess.run(
        [sys.executable, "-m", "pytest", *modules, "-q"],
        cwd=str(FBK_SCRIPTS),
        capture_output=True,
        text=True,
    )
    combined = result.stdout + result.stderr
    return result.returncode, combined


def test_unchanged_gate_and_telemetry_suites_pass():
    """Every gate and telemetry suite that must not change passes with zero failures."""
    returncode, output = _run_pytest(UNCHANGED_MODULES)
    assert returncode == 0, (
        "One or more unchanged gate/telemetry suites failed.\n"
        f"pytest output (last 2000 chars):\n{output[-2000:]}"
    )
    # Lower-bound: the run actually collected and passed tests (not vacuously empty).
    assert "passed" in output, (
        f"pytest ran but reported no passing tests — possible collection error.\n{output[-2000:]}"
    )
    assert "no tests ran" not in output, (
        f"pytest collected nothing — module list or cwd is wrong.\n{output[-2000:]}"
    )


def test_code_review_trust_boundary_module_runs_green():
    """The code-review gate module stays green, pinning the round-log allowlist.

    Specifically: the severity_breakdown field must remain stripped from round
    log projections. This gate is untouched by the migration, so this test
    confirms no accidental side-effect broke it.
    """
    returncode, output = _run_pytest(["tests/test_gates_code_review.py"])
    assert returncode == 0, (
        "test_gates_code_review.py failed — round-log allowlist may have changed.\n"
        f"pytest output (last 2000 chars):\n{output[-2000:]}"
    )
    assert "passed" in output, (
        f"pytest ran but reported no passing tests.\n{output[-2000:]}"
    )
    assert "no tests ran" not in output, (
        f"pytest collected nothing from test_gates_code_review.py.\n{output[-2000:]}"
    )


def test_updated_telemetry_and_dispatcher_suites_pass():
    """Suites with sanctioned assertion changes (new agent names, coherence-gate count) are green.

    Covers the telemetry half of AC-11: test_shapes.py (new agent names),
    test_dispatcher.py (coherence-gate command entry set to 22), and
    test_capture_known_agents.py (new agent names).
    """
    returncode, output = _run_pytest(CHANGED_MODULES)
    assert returncode == 0, (
        "One or more updated telemetry/dispatcher suites failed.\n"
        f"pytest output (last 2000 chars):\n{output[-2000:]}"
    )
    assert "passed" in output, (
        f"pytest ran but reported no passing tests — possible collection error.\n{output[-2000:]}"
    )
    assert "no tests ran" not in output, (
        f"pytest collected nothing — module list or cwd is wrong.\n{output[-2000:]}"
    )
