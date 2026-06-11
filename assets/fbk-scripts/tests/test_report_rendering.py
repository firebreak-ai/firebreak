"""Integration tests for `fbk.py report <spec>` — table rendering and CLI.

Drives the report subcommand via subprocess, asserting on structural row
labels and rendering rules rather than body vocabulary.  All tests skip
when the fbk.report module is absent (red phase before implementation).
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from tests import capture_fixtures

# ---------------------------------------------------------------------------
# Red-phase guard
# ---------------------------------------------------------------------------

try:
    import fbk.report as _report_module
except ImportError:
    _report_module = None

pytestmark = pytest.mark.skipif(
    _report_module is None,
    reason="fbk.report not yet implemented",
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FBK_PY = Path(__file__).parent.parent / "fbk.py"

_SPEC = "sample-feature"

# Sentinel file written by the pruner when locked lines are dropped past ceiling
_RETENTION_WARNING_REL = ".fbk-capture/.retention-warning"

# Events file location relative to project root
_EVENTS_REL = ".fbk-capture/events.jsonl"

# Structural row label substrings the report table must carry.
# Assert on these markers — not body vocabulary — so wording changes don't
# break the tests.
_REQUIRED_ROW_LABELS = [
    "duration",        # per-stage duration
    "first-try",       # first-try gate pass rate
    "after-rework",    # after-rework gate pass rate
    "parks",           # parks per stage
    "tasks completed", # tasks completed count
    "tasks reworked",  # tasks reworked count
    "scope violation", # scope violations
    "detection round", # code-review detection rounds
    "kill rate",       # detection kill rate
    "tokens",          # tokens per stage
    "coarse indicator",       # token attribution caveat label
    "boundary-adjacent turns", # per-stage boundary-adjacency count
]

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

_STAGES_FULL = [
    "VALIDATING",
    "REVIEWING",
    "BREAKING_DOWN",
    "TASK_REVIEWING",
    "TESTING",
    "TEST_REVIEWING",
    "IMPLEMENTING",
    "VERIFYING",
]

_STAGES_EARLY = ["VALIDATING", "REVIEWING"]


def _build_full_events(spec=_SPEC):
    """Return events in the real producer shapes, covering gate attempts, tasks,
    scope violations, and code-review rounds across pipeline stages.

    Every event here matches what an actual producer writes (the verification
    hook's tests_passed/out_of_scope_files, the chokepoint's command_name/
    outcome, the code-review gate's total_raised/total_survived) — not a shape
    only the report's reader expects.  Parks and rework are state-derived, so
    they live in _build_full_state, not here.
    """
    events = []

    # Gate attempts (verification hook shape): VALIDATING passes first try.
    events.append(capture_fixtures.build_event(
        "VERIFICATION_RESULT", "task_completed", spec, "VALIDATING",
        data={"failing_test_count": 0, "lint_error_count": 0,
              "out_of_scope_files": [], "tests_passed": True},
    ))

    # A completed task in IMPLEMENTING (chokepoint dispatch shape).
    events.append(capture_fixtures.build_event(
        "PIPELINE_COMMAND", "chokepoint", spec, "IMPLEMENTING",
        data={"command_name": "task-completed", "args": ["task-01"],
              "outcome": "pass", "exit_code": 0, "duration": 0.1, "output": ""},
    ))

    # A scope violation in IMPLEMENTING: the verification event lists two
    # out-of-scope files (and so reads as a failed verification).
    events.append(capture_fixtures.build_event(
        "VERIFICATION_RESULT", "task_completed", spec, "IMPLEMENTING",
        data={"failing_test_count": 0, "lint_error_count": 0,
              "out_of_scope_files": ["src/extra.py", "src/other.py"],
              "tests_passed": False},
    ))

    # Code-review rounds: 3 raised, 1 survived → kill rate (3-1)/3.
    events.append(capture_fixtures.build_event(
        "CODE_REVIEW_ROUNDS", "code_review", spec, None,
        data={"spec": spec, "rounds": [{"raised": 3, "survived": 1}],
              "total_raised": 3, "total_survived": 1},
    ))

    return events


def _build_full_state(spec=_SPEC):
    """Return a state dict covering all pipeline stages with durations.

    IMPLEMENTING carries one park in error_history so the report renders a park
    reason and a rework count of one (rework is the stage's re-entry count).
    """
    timestamps = {s: "2026-01-01T00:00:00+00:00" for s in _STAGES_FULL}
    timestamps["COMPLETED"] = "2026-01-01T01:00:00+00:00"
    return capture_fixtures.build_state(
        spec=spec,
        stage_timestamps=timestamps,
        error_history=[
            {"stage": "IMPLEMENTING", "error": "blocked on upstream",
             "timestamp": "2026-01-01T00:30:00+00:00"},
        ],
        current_state="COMPLETED",
    )


def _build_full_transcript_turns():
    """Return a list of turns for a complete pipeline transcript."""
    return [
        {
            "timestamp": "2026-01-01T00:10:00+00:00",
            "model": "claude-opus-4-8",
            "input_tokens": 1000,
            "output_tokens": 200,
            "tools": ["Read", "Edit"],
            "sidechain": False,
        },
        {
            "timestamp": "2026-01-01T00:20:00+00:00",
            "model": "claude-opus-4-8",
            "input_tokens": 1500,
            "output_tokens": 300,
            "tools": ["Bash"],
            "sidechain": False,
        },
    ]


def _setup_full_project(tmp_path):
    """Write a complete fixture project tree under tmp_path.

    Returns (project_root, state_dir) as strings.
    """
    project = capture_fixtures.make_project(str(tmp_path), instrumented=True, marked=True)
    state_dir = str(tmp_path / "state")

    events = _build_full_events()
    capture_fixtures.write_events(os.path.join(project, _EVENTS_REL), events)

    state = _build_full_state()
    capture_fixtures.write_state(state_dir, state)

    transcript_path = os.path.join(
        project, ".claude", "projects", _SPEC, "session.jsonl"
    )
    capture_fixtures.write_transcript(transcript_path, _build_full_transcript_turns())

    return project, state_dir


def _run_report(project, state_dir, spec=_SPEC):
    """Run `fbk.py report <spec>` with cwd=project and STATE_DIR=state_dir.

    Returns the CompletedProcess.
    """
    env = {**os.environ, "STATE_DIR": state_dir}
    return subprocess.run(
        [sys.executable, str(FBK_PY), "report", spec],
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_report_renders_all_required_row_kinds(tmp_path):
    """Full fixture cycle: table carries every required row label; exits 0."""
    project, state_dir = _setup_full_project(tmp_path)

    result = _run_report(project, state_dir)

    assert result.returncode == 0, (
        f"report exited {result.returncode}; stderr: {result.stderr}"
    )

    output = result.stdout
    for label in _REQUIRED_ROW_LABELS:
        assert label in output, (
            f"required row label '{label}' not found in report output"
        )


def test_report_renders_real_values_from_producer_shapes(tmp_path):
    """The table shows the captured numbers, not zero, for each producer source.

    Guards against producer/consumer envelope drift: the fixtures use the real
    producer shapes, so a report that read the wrong key/value/stage would print
    zero here and fail.  (Companion to the producer-driven integration test.)
    """
    project, state_dir = _setup_full_project(tmp_path)

    result = _run_report(project, state_dir)
    assert result.returncode == 0, (
        f"report exited {result.returncode}; stderr: {result.stderr}"
    )
    out = result.stdout

    def _row(pattern):
        m = re.search(pattern, out)
        assert m, f"row not found for pattern {pattern!r}\n--- report ---\n{out}"
        return m.group(1)

    # VALIDATING passed its one verification on the first try.
    assert float(_row(r"VALIDATING\s+first-try rate:\s*([\d.]+)")) == pytest.approx(1.0)
    # One passing task-completed dispatch landed in IMPLEMENTING.
    assert int(_row(r"IMPLEMENTING\s+tasks completed:\s*(\d+)")) == 1
    # The IMPLEMENTING verification listed two out-of-scope files.
    assert int(_row(r"IMPLEMENTING\s+scope violation count:\s*(\d+)")) == 2
    # One park in IMPLEMENTING → one re-entry counted as rework.
    assert int(_row(r"IMPLEMENTING\s+tasks completed:\s*\d+\s+tasks reworked:\s*(\d+)")) == 1
    # 3 raised, 1 survived → (3-1)/3 ≈ 0.67.
    assert float(_row(r"kill rate:\s*([\d.]+)")) == pytest.approx(0.67, abs=0.01)


def test_report_runs_mid_cycle_with_partial_rows(tmp_path):
    """Report exits 0 mid-cycle and prints rows for stages that ran, no error on absent later stages."""
    project = capture_fixtures.make_project(str(tmp_path), instrumented=True, marked=True)
    state_dir = str(tmp_path / "state")

    # Only early stages have events and timestamps
    events = [
        capture_fixtures.build_event(
            "VERIFICATION_RESULT", "gate", _SPEC, stage,
            data={"result": "pass", "attempt": 1},
        )
        for stage in _STAGES_EARLY
    ]
    capture_fixtures.write_events(os.path.join(project, _EVENTS_REL), events)

    partial_timestamps = {s: "2026-01-01T00:00:00+00:00" for s in _STAGES_EARLY}
    state = capture_fixtures.build_state(
        spec=_SPEC,
        stage_timestamps=partial_timestamps,
        current_state="REVIEWING",
    )
    capture_fixtures.write_state(state_dir, state)

    result = _run_report(project, state_dir)

    assert result.returncode == 0, (
        f"report exited {result.returncode} mid-cycle; stderr: {result.stderr}"
    )

    output = result.stdout
    # Rows for stages that ran should appear
    for stage in _STAGES_EARLY:
        assert stage.lower() in output or stage in output, (
            f"expected stage '{stage}' row in partial-cycle output"
        )


def test_missing_transcript_renders_literal_unavailable(tmp_path):
    """Missing transcript renders the literal token 'unavailable', not '0'."""
    project, state_dir = _setup_full_project(tmp_path)

    # Remove the transcript so the tokens path is absent
    transcript_path = os.path.join(
        project, ".claude", "projects", _SPEC, "session.jsonl"
    )
    if os.path.exists(transcript_path):
        os.remove(transcript_path)

    result = _run_report(project, state_dir)

    assert result.returncode == 0, (
        f"report exited {result.returncode}; stderr: {result.stderr}"
    )

    output = result.stdout

    # The tokens row must carry the literal string 'unavailable'
    assert "unavailable" in output, (
        "tokens row did not render 'unavailable' when transcript is missing"
    )

    # It must not render a bare '0' in the tokens row as a substitute for 'unavailable'.
    # Find the tokens row and verify it contains 'unavailable', not '0'.
    tokens_row_lines = [line for line in output.splitlines() if "tokens" in line.lower()]
    assert tokens_row_lines, "tokens row not found in report output"

    for line in tokens_row_lines:
        # The report renders an unavailable stage as "tokens: unavailable" and an
        # available stage as "tokens: in=<n> out=<n>". For a missing transcript
        # every stage must take the unavailable path, so each token line must show
        # the literal word and must NOT show the "in=... out=..." count rendering.
        assert "tokens: unavailable" in line, (
            f"tokens row '{line}' does not render 'tokens: unavailable'"
        )
        assert "in=" not in line and "out=" not in line, (
            f"tokens row '{line}' rendered an in=/out= token count instead of 'unavailable'"
        )


def test_zero_parks_renders_present_empty_row(tmp_path):
    """Stage that ran its parks path with zero parks: parks row present and empty, not an error."""
    project = capture_fixtures.make_project(str(tmp_path), instrumented=True, marked=True)
    state_dir = str(tmp_path / "state")

    # BREAKING_DOWN ran (has timestamps) but produced zero parks — no park events
    events = [
        capture_fixtures.build_event(
            "VERIFICATION_RESULT", "gate", _SPEC, "VALIDATING",
            data={"result": "pass", "attempt": 1},
        ),
        # BREAKING_DOWN: no PIPELINE_COMMAND park events — zero parks
        capture_fixtures.build_event(
            "LIFECYCLE", "orchestrator", _SPEC, "BREAKING_DOWN",
            data={"event": "stage_entered"},
        ),
    ]
    capture_fixtures.write_events(os.path.join(project, _EVENTS_REL), events)

    timestamps = {
        "VALIDATING": "2026-01-01T00:00:00+00:00",
        "BREAKING_DOWN": "2026-01-01T00:05:00+00:00",
    }
    state = capture_fixtures.build_state(
        spec=_SPEC,
        stage_timestamps=timestamps,
        current_state="BREAKING_DOWN",
    )
    capture_fixtures.write_state(state_dir, state)

    result = _run_report(project, state_dir)

    assert result.returncode == 0, (
        f"report exited {result.returncode}; stderr: {result.stderr}"
    )

    output = result.stdout

    # The parks row for BREAKING_DOWN must be present (row label appears in output)
    assert "parks" in output.lower(), (
        "parks row not present for a stage that ran its parks path with zero parks"
    )

    # The parks row must not carry an error or be omitted entirely;
    # the stage label must appear paired with the parks row
    bd_lines = [line for line in output.splitlines() if "BREAKING_DOWN" in line or "breaking_down" in line.lower()]
    assert bd_lines, (
        "BREAKING_DOWN stage row not found in output — row should be present and empty"
    )


def test_empty_vs_absent_row_discriminator(tmp_path):
    """Present-and-empty parks row (stage ran, zero parks) vs omitted row (stage never ran).

    A renderer that simply drops all-zero rows does not pass: the zero-parks
    stage row must appear while the never-ran stage row must be absent.
    """
    project = capture_fixtures.make_project(str(tmp_path), instrumented=True, marked=True)
    state_dir = str(tmp_path / "state")

    # BREAKING_DOWN ran — parks-producing step executed, zero parks
    # TASK_REVIEWING never ran — no timestamps, no events
    events = [
        capture_fixtures.build_event(
            "LIFECYCLE", "orchestrator", _SPEC, "BREAKING_DOWN",
            data={"event": "stage_entered"},
        ),
        # Explicitly no TASK_REVIEWING events
    ]
    capture_fixtures.write_events(os.path.join(project, _EVENTS_REL), events)

    # Only BREAKING_DOWN in timestamps — TASK_REVIEWING absent
    timestamps = {
        "BREAKING_DOWN": "2026-01-01T00:05:00+00:00",
    }
    state = capture_fixtures.build_state(
        spec=_SPEC,
        stage_timestamps=timestamps,
        current_state="BREAKING_DOWN",
    )
    capture_fixtures.write_state(state_dir, state)

    result = _run_report(project, state_dir)

    assert result.returncode == 0, (
        f"report exited {result.returncode}; stderr: {result.stderr}"
    )

    output = result.stdout

    # BREAKING_DOWN parks row must be present (stage ran, zero parks → row present)
    bd_present = any(
        "BREAKING_DOWN" in line or "breaking_down" in line.lower()
        for line in output.splitlines()
    )
    assert bd_present, (
        "BREAKING_DOWN parks row absent — expected present-and-empty row for stage that ran"
    )

    # TASK_REVIEWING row must be absent (parks-producing step never executed)
    tr_present = any(
        "TASK_REVIEWING" in line or "task_reviewing" in line.lower()
        for line in output.splitlines()
    )
    assert not tr_present, (
        "TASK_REVIEWING row present — expected row omitted for stage whose parks step never ran"
    )


def test_over_cap_retention_warning_surfaced(tmp_path):
    """Over-cap retention warning rendered in table when sentinel present; absent otherwise."""
    project, state_dir = _setup_full_project(tmp_path)
    warning_path = os.path.join(project, _RETENTION_WARNING_REL)

    # --- case 1: sentinel present → warning must appear in output ---
    os.makedirs(os.path.dirname(warning_path), exist_ok=True)
    with open(warning_path, "w") as f:
        f.write("")  # sentinel content; presence is the signal

    result_with_warning = _run_report(project, state_dir)

    assert result_with_warning.returncode == 0, (
        f"report exited {result_with_warning.returncode} with sentinel; "
        f"stderr: {result_with_warning.stderr}"
    )

    output_with = result_with_warning.stdout
    assert "retention" in output_with.lower() or "over-cap" in output_with.lower() or "locked lines" in output_with.lower(), (
        "over-cap retention warning not rendered in table when sentinel is present"
    )

    # --- case 2: sentinel absent → warning must not appear ---
    os.remove(warning_path)

    result_without_warning = _run_report(project, state_dir)

    assert result_without_warning.returncode == 0, (
        f"report exited {result_without_warning.returncode} without sentinel; "
        f"stderr: {result_without_warning.stderr}"
    )

    output_without = result_without_warning.stdout
    # None of the warning markers should appear
    warning_markers = ["retention warning", "over-cap", "locked lines dropped"]
    for marker in warning_markers:
        assert marker not in output_without.lower(), (
            f"retention warning marker '{marker}' appeared in output when sentinel is absent"
        )
