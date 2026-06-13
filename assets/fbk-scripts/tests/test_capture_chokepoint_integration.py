"""Real-producer integration tests for fbk.capture.chokepoint.

Drives `fbk.py state transition` through the real dispatch path (subprocess)
to exercise the chokepoint normal-return path: multi-line indented JSON is
re-emitted byte-for-byte, integer exit codes propagate, and one
PIPELINE_COMMAND event is written per invocation.

The fbk.py dispatch wrap (task-35) is absent in the red phase, so the event
assertions fail until that wrap is added.  All tests collect cleanly and the
subprocess-only assertions (exit code, stdout shape) demonstrate the state
engine already works correctly.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

try:
    from fbk.capture import chokepoint as _chokepoint_module  # noqa: F401
    _CHOKEPOINT_AVAILABLE = True
except ImportError:
    _CHOKEPOINT_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _CHOKEPOINT_AVAILABLE,
    reason="fbk.capture.chokepoint not yet implemented",
)

from tests import capture_fixtures  # noqa: E402 — after guard


FBK_PY = Path(__file__).parent.parent / "fbk.py"

_CAPTURE_DIR = ".fbk-capture"
_EVENTS_FILE = "events.jsonl"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _events_path(project_root):
    """Return the canonical events.jsonl path for a project root string."""
    return os.path.join(project_root, _CAPTURE_DIR, _EVENTS_FILE)


def _read_event_lines(project_root):
    """Return parsed JSON objects for each non-empty line in events.jsonl."""
    path = _events_path(project_root)
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def _clear_events(project_root):
    """Remove the events log so a later assertion measures only the
    invocation under test. The `state create` setup step runs through the same
    wrapped dispatch and records its own PIPELINE_COMMAND event; clearing the
    log after setup isolates the measured `state transition` call.
    """
    path = _events_path(project_root)
    if os.path.exists(path):
        os.remove(path)


def _run_fbk(args, project_root, state_dir):
    """Run fbk.py with args in project_root, with STATE_DIR set to state_dir.

    Returns a CompletedProcess with text stdout/stderr.
    """
    env = {**os.environ, "STATE_DIR": str(state_dir)}
    return subprocess.run(
        [sys.executable, str(FBK_PY)] + args,
        capture_output=True,
        text=True,
        cwd=str(project_root),
        env=env,
        timeout=15,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRealStateTransitionChokepoint:
    """End-to-end tests driving fbk.py state transition through the chokepoint."""

    def test_real_state_transition_reemits_multiline_json_and_propagates_exit(
        self, tmp_path
    ):
        """state transition to VALIDATING: multi-line JSON re-emitted, exit 0 propagated, one PIPELINE_COMMAND event written."""
        project = capture_fixtures.make_project(
            str(tmp_path), instrumented=True, marked=True
        )
        state_dir = os.path.join(project, ".claude", "automation", "state")
        os.makedirs(state_dir, exist_ok=True)

        # Create the spec state so a valid transition is possible.
        create_result = _run_fbk(
            ["state", "create", "demo-spec"],
            project_root=project,
            state_dir=state_dir,
        )
        assert create_result.returncode == 0, (
            f"state create failed: {create_result.stderr!r}"
        )
        _clear_events(project)

        # Run the valid transition QUEUED -> VALIDATING through the full fbk.py dispatch.
        result = _run_fbk(
            ["state", "transition", "demo-spec", "VALIDATING"],
            project_root=project,
            state_dir=state_dir,
        )

        # The integer exit code 0 propagates — not masked to a SystemExit artifact.
        assert result.returncode == 0, (
            f"expected exit code 0 from successful transition, got {result.returncode}; "
            f"stderr: {result.stderr!r}"
        )

        # The state JSON is printed as multi-line indented output.
        stdout = result.stdout
        lines = stdout.strip().splitlines()
        assert len(lines) > 1, (
            f"expected multi-line indented JSON on stdout, got single line: {stdout!r}"
        )

        # The stdout, once stripped, parses as a single clean JSON object with no
        # stray injector output before or after.
        try:
            state_obj = json.loads(stdout.strip())
        except json.JSONDecodeError as exc:
            pytest.fail(
                f"stdout does not parse as JSON (stray lines from injector?): {exc}; "
                f"stdout={stdout!r}"
            )

        # The parsed state reflects the new current_state.
        assert state_obj.get("current_state") == "VALIDATING", (
            f"expected current_state 'VALIDATING', got {state_obj.get('current_state')!r}"
        )

        # Exactly one PIPELINE_COMMAND event was written for the state command.
        events = _read_event_lines(project)
        pipeline_events = [
            e for e in events if e.get("event_type") == "PIPELINE_COMMAND"
        ]
        assert len(pipeline_events) == 1, (
            f"expected exactly one PIPELINE_COMMAND event, got {len(pipeline_events)}: "
            f"{pipeline_events!r}"
        )

        recorded = pipeline_events[0]
        data = recorded.get("data", {})

        # The recorded command name is "state".
        assert data.get("command_name") == "state", (
            f"expected command_name 'state' in event data, got {data.get('command_name')!r}; "
            f"data={data!r}"
        )

        # The outcome field is present and reflects success.
        assert "outcome" in data, (
            f"expected 'outcome' key in PIPELINE_COMMAND event data; data={data!r}"
        )
        assert data["outcome"] == "pass", (
            f"expected outcome 'pass' for exit code 0, got {data['outcome']!r}"
        )

    def test_real_transition_invalid_propagates_nonzero_and_records(
        self, tmp_path
    ):
        """Invalid transition from QUEUED: exit 1 propagated, one PIPELINE_COMMAND event recorded."""
        project = capture_fixtures.make_project(
            str(tmp_path), instrumented=True, marked=True
        )
        state_dir = os.path.join(project, ".claude", "automation", "state")
        os.makedirs(state_dir, exist_ok=True)

        # Create the spec state (initial state is QUEUED).
        create_result = _run_fbk(
            ["state", "create", "demo-spec"],
            project_root=project,
            state_dir=state_dir,
        )
        assert create_result.returncode == 0, (
            f"state create failed: {create_result.stderr!r}"
        )
        _clear_events(project)

        # Attempt an invalid transition QUEUED -> REVIEWED; should return 1.
        result = _run_fbk(
            ["state", "transition", "demo-spec", "REVIEWED"],
            project_root=project,
            state_dir=state_dir,
        )

        # The non-zero exit code is propagated — not masked.
        assert result.returncode == 1, (
            f"expected exit code 1 from invalid transition, got {result.returncode}; "
            f"stderr: {result.stderr!r}"
        )

        # Exactly one PIPELINE_COMMAND event was recorded for the failed attempt.
        events = _read_event_lines(project)
        pipeline_events = [
            e for e in events if e.get("event_type") == "PIPELINE_COMMAND"
        ]
        assert len(pipeline_events) == 1, (
            f"expected exactly one PIPELINE_COMMAND event for invalid transition, "
            f"got {len(pipeline_events)}: {pipeline_events!r}"
        )

        recorded = pipeline_events[0]
        data = recorded.get("data", {})

        # The recorded command name is "state".
        assert data.get("command_name") == "state", (
            f"expected command_name 'state' in event data, got {data.get('command_name')!r}"
        )

        # The outcome reflects failure.
        assert "outcome" in data, (
            f"expected 'outcome' key in PIPELINE_COMMAND event data; data={data!r}"
        )
        assert data["outcome"] == "fail", (
            f"expected outcome 'fail' for exit code 1, got {data['outcome']!r}"
        )


# ---------------------------------------------------------------------------
# Spec-gate single-writer tests (AC-12)
# ---------------------------------------------------------------------------
#
# One real fbk.py spec-gate dispatch must yield exactly one PIPELINE_COMMAND
# event, written by the chokepoint with source="chokepoint".  Pre-fix, two
# events were written per dispatch: the chokepoint's (correct) and the gate's
# own duplicate (mislabelled source="chokepoint", carrying "result" but no
# "outcome") — double-counting attempts and poisoning the rate arithmetic.
#
# Minimal valid spec content is copied from _make_minimal_spec() in
# tests/test_gates_spec.py, which is the canonical source of truth.
_MINIMAL_VALID_SPEC = """\
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

## Interface contracts
No new or changed contracts in this feature.
"""

_BROKEN_SPEC = "# Feature Specification\n\n## Problem\nOnly one section present.\n"


def _write_state_file(state_dir, spec_name, current_state, stage_timestamps):
    """Write a state JSON file under state_dir and return its path."""
    os.makedirs(state_dir, exist_ok=True)
    state = {
        "spec_name": spec_name,
        "current_state": current_state,
        "stage_timestamps": stage_timestamps,
        "agent_ids": [],
        "verification_results": {},
        "error_history": [],
        "parked_info": {},
    }
    path = os.path.join(state_dir, f"{spec_name}.json")
    with open(path, "w") as fh:
        json.dump(state, fh, indent=2)
    return path


class TestSpecGateSingleWriter:
    """One fbk.py spec-gate dispatch yields exactly one PIPELINE_COMMAND (AC-12)."""

    def test_one_gate_dispatch_yields_exactly_one_pipeline_command(self, tmp_path):
        """Passing spec-gate: exactly one PIPELINE_COMMAND with source='chokepoint',
        outcome='pass', exit_code=0, spec='demo-spec', stage='VALIDATING'."""
        project = capture_fixtures.make_project(
            str(tmp_path), instrumented=True, marked=True
        )
        state_dir = os.path.join(project, ".claude", "automation", "state")

        # Pre-populate a state in VALIDATING so the resolver attributes the event.
        # stage_timestamps matches the shape active_stage.resolve_active_stage reads.
        _write_state_file(
            state_dir,
            spec_name="demo-spec",
            current_state="VALIDATING",
            stage_timestamps={"QUEUED": "2026-01-01T00:00:00+00:00", "VALIDATING": "2026-01-01T00:01:00+00:00"},
        )

        # Write a gate-passing spec.  Content is copied verbatim from
        # _make_minimal_spec() in tests/test_gates_spec.py — that function is
        # the canonical source of truth for what the gate accepts.
        spec_path = os.path.join(project, "sample-spec.md")
        with open(spec_path, "w") as fh:
            fh.write(_MINIMAL_VALID_SPEC)

        # The gate's contract design-anchor check requires design/contracts.md
        # beside the spec; the no-contracts sentence makes the clean spec pass.
        design_dir = os.path.join(project, "design")
        os.makedirs(design_dir, exist_ok=True)
        with open(os.path.join(design_dir, "contracts.md"), "w") as fh:
            fh.write("No new or changed contracts in this feature.\n")

        result = _run_fbk(["spec-gate", "sample-spec.md"], project, state_dir)
        assert result.returncode == 0, (
            f"expected spec-gate pass (rc 0), got rc {result.returncode}; "
            f"stderr: {result.stderr!r}"
        )

        events = _read_event_lines(project)
        gate_events = [
            e for e in events
            if e.get("event_type") == "PIPELINE_COMMAND"
            and e.get("data", {}).get("command_name") == "spec-gate"
        ]

        assert len(gate_events) == 1, (
            f"expected exactly one spec-gate PIPELINE_COMMAND, got {len(gate_events)}: "
            f"{gate_events!r}"
        )

        ev = gate_events[0]
        data = ev.get("data", {})

        assert ev.get("source") == "chokepoint", (
            f"expected source='chokepoint', got {ev.get('source')!r}"
        )
        assert data.get("outcome") == "pass", (
            f"expected outcome='pass', got {data.get('outcome')!r}; data={data!r}"
        )
        assert data.get("exit_code") == 0, (
            f"expected exit_code=0, got {data.get('exit_code')!r}; data={data!r}"
        )
        assert ev.get("spec") == "demo-spec", (
            f"expected spec='demo-spec', got {ev.get('spec')!r}"
        )
        assert ev.get("stage") == "VALIDATING", (
            f"expected stage='VALIDATING', got {ev.get('stage')!r}"
        )

    def test_failing_gate_dispatch_also_yields_exactly_one_event(self, tmp_path):
        """Failing spec-gate: exactly one PIPELINE_COMMAND with outcome='fail',
        exit_code=2, source='chokepoint'."""
        project = capture_fixtures.make_project(
            str(tmp_path), instrumented=True, marked=True
        )
        state_dir = os.path.join(project, ".claude", "automation", "state")

        _write_state_file(
            state_dir,
            spec_name="demo-spec",
            current_state="VALIDATING",
            stage_timestamps={"QUEUED": "2026-01-01T00:00:00+00:00", "VALIDATING": "2026-01-01T00:01:00+00:00"},
        )

        # A spec with only one section — the gate rejects it with exit code 2.
        broken_path = os.path.join(project, "broken-spec.md")
        with open(broken_path, "w") as fh:
            fh.write(_BROKEN_SPEC)

        result = _run_fbk(["spec-gate", "broken-spec.md"], project, state_dir)
        assert result.returncode == 2, (
            f"expected spec-gate fail (rc 2), got rc {result.returncode}; "
            f"stderr: {result.stderr!r}"
        )

        events = _read_event_lines(project)
        gate_events = [
            e for e in events
            if e.get("event_type") == "PIPELINE_COMMAND"
            and e.get("data", {}).get("command_name") == "spec-gate"
        ]

        assert len(gate_events) == 1, (
            f"expected exactly one spec-gate PIPELINE_COMMAND for failing dispatch, "
            f"got {len(gate_events)}: {gate_events!r}"
        )

        ev = gate_events[0]
        data = ev.get("data", {})

        assert ev.get("source") == "chokepoint", (
            f"expected source='chokepoint', got {ev.get('source')!r}"
        )
        assert data.get("outcome") == "fail", (
            f"expected outcome='fail', got {data.get('outcome')!r}; data={data!r}"
        )
        assert data.get("exit_code") == 2, (
            f"expected exit_code=2, got {data.get('exit_code')!r}; data={data!r}"
        )


class TestDirectNormalReturnChokepoint:
    """Direct record_dispatch tests for the normal-return branch.

    The subprocess tests above drive commands through fbk.py, but every command
    those tests reach raises SystemExit. Commands like `report` instead return
    an int from main() without calling sys.exit, taking the normal-return branch
    of record_dispatch (result = run_fn(); exit_code = result; ... return
    exit_code). These tests call record_dispatch directly with a run_fn that
    RETURNS an int — never raising SystemExit — in an instrumented project, so
    the normal-return path is exercised and the returned value is observable.
    """

    def test_normal_return_zero_returns_value_records_pass_and_flushes(
        self, tmp_path, capsys
    ):
        """run_fn returns 0: record_dispatch returns 0, records outcome 'pass' with exit_code 0, flushes stdout."""
        project = capture_fixtures.make_project(
            str(tmp_path), instrumented=True, marked=True
        )

        stub_output = json.dumps({"report": "stub", "result": "ok"})

        def run_fn():
            print(stub_output)
            return 0

        result = _chokepoint_module.record_dispatch(
            "report", ["--summary"], run_fn, project
        )

        # The exact int run_fn returned is returned by record_dispatch — no
        # SystemExit artifact, no coercion.
        assert result == 0, (
            f"expected record_dispatch to return 0 (run_fn's return value), got {result!r}"
        )

        # The buffered stdout is flushed to real stdout on the normal-return path.
        captured = capsys.readouterr()
        assert stub_output in captured.out, (
            f"expected run_fn stdout flushed to real stdout on normal return, got: {captured.out!r}"
        )

        # Exactly one PIPELINE_COMMAND event was written.
        events = _read_event_lines(project)
        pipeline_events = [
            e for e in events if e.get("event_type") == "PIPELINE_COMMAND"
        ]
        assert len(pipeline_events) == 1, (
            f"expected exactly one PIPELINE_COMMAND event, got {len(pipeline_events)}: "
            f"{pipeline_events!r}"
        )

        data = pipeline_events[0].get("data", {})

        # The outcome reflects the zero exit code and the recorded exit_code matches.
        assert data.get("outcome") == "pass", (
            f"expected outcome 'pass' for return value 0, got {data.get('outcome')!r}; data={data!r}"
        )
        assert data.get("exit_code") == 0, (
            f"expected exit_code 0 in recorded event, got {data.get('exit_code')!r}; data={data!r}"
        )

    def test_normal_return_nonzero_returns_same_value_records_fail(
        self, tmp_path, capsys
    ):
        """run_fn returns 3: record_dispatch returns 3, records outcome 'fail' with exit_code 3."""
        project = capture_fixtures.make_project(
            str(tmp_path), instrumented=True, marked=True
        )

        def run_fn():
            return 3

        result = _chokepoint_module.record_dispatch(
            "report", [], run_fn, project
        )

        # The exact non-zero int is propagated unchanged.
        assert result == 3, (
            f"expected record_dispatch to return 3 (run_fn's return value), got {result!r}"
        )

        # Exactly one PIPELINE_COMMAND event was written.
        events = _read_event_lines(project)
        pipeline_events = [
            e for e in events if e.get("event_type") == "PIPELINE_COMMAND"
        ]
        assert len(pipeline_events) == 1, (
            f"expected exactly one PIPELINE_COMMAND event, got {len(pipeline_events)}: "
            f"{pipeline_events!r}"
        )

        data = pipeline_events[0].get("data", {})

        # The outcome reflects the non-zero exit code and the exit_code matches.
        assert data.get("outcome") == "fail", (
            f"expected outcome 'fail' for return value 3, got {data.get('outcome')!r}; data={data!r}"
        )
        assert data.get("exit_code") == 3, (
            f"expected exit_code 3 in recorded event, got {data.get('exit_code')!r}; data={data!r}"
        )
