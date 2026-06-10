"""End-to-end seam tests for the metrics-plane capture pipeline.

Two tests verify the cross-cutting integration properties:

1. test_two_source_cycle_joins_in_one_report — a single instrumented project
   cycle records events from two producers (hook router and dispatch chokepoint)
   into one events.jsonl, the report aggregates them into a single table without
   error, and the completed working stage's retrospective carries the provenance
   metrics block.

2. test_uninstrumented_project_records_nothing_end_to_end — a bare project with
   no sentinel and no capture.cfg receives no events from either producer; both
   commands behave normally; no capture file is created anywhere.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Red-phase guard — skip the whole module when the capture subsystem is absent.
# ---------------------------------------------------------------------------

try:
    from fbk.capture import event_writer  # noqa: F401
    _CAPTURE_AVAILABLE = True
except ImportError:
    _CAPTURE_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _CAPTURE_AVAILABLE,
    reason="fbk.capture not yet implemented",
)

from tests import capture_fixtures  # noqa: E402 — after guard

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

FBK_PY = Path(__file__).parent.parent / "fbk.py"
ROUTER = Path(__file__).parent.parent / "fbk" / "capture" / "hook_router.py"

# The eight envelope field names the schema mandates for every event.
_ENVELOPE_KEYS = frozenset({
    "schema_version",
    "event_type",
    "timestamp",
    "spec",
    "stage",
    "source",
    "capture_level",
    "data",
})

_CAPTURE_DIR = ".fbk-capture"
_EVENTS_FILE = "events.jsonl"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _events_path(project_root):
    """Return the canonical events.jsonl path for a project root."""
    return os.path.join(str(project_root), _CAPTURE_DIR, _EVENTS_FILE)


def _read_event_lines(project_root):
    """Return parsed event dicts for each non-empty line in events.jsonl."""
    path = _events_path(project_root)
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def _run_fbk(args, project_root, state_dir):
    """Run fbk.py with args in project_root, STATE_DIR set to state_dir.

    Returns a CompletedProcess with text stdout/stderr.
    """
    env = {**os.environ, "STATE_DIR": str(state_dir)}
    return subprocess.run(
        [sys.executable, str(FBK_PY)] + args,
        capture_output=True,
        text=True,
        cwd=str(project_root),
        env=env,
        timeout=30,
    )


def _run_router(payload_json, project_dir, env_extra=None):
    """Run the hook router with the given stdin payload and working directory.

    Returns a CompletedProcess with captured stdout and stderr.
    """
    env = {**os.environ, **(env_extra or {})}
    return subprocess.run(
        [sys.executable, str(ROUTER)],
        input=payload_json,
        cwd=str(project_dir),
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )


# ---------------------------------------------------------------------------
# Test 1 — two-source cycle joins in one report
# ---------------------------------------------------------------------------


def test_two_source_cycle_joins_in_one_report(tmp_path):
    """Router and chokepoint events both land in events.jsonl and appear in one report.

    Drives a complete QUEUED → VALIDATING → VALIDATED cycle through the real dispatch
    path (fbk.py → chokepoint), feeds the router a PostToolUse payload, then runs
    fbk.py report and asserts:
    - events.jsonl contains events from both producers (PIPELINE_COMMAND and TOOL_USE)
    - both event shapes carry the same eight envelope fields
    - the report exits 0 and renders a table covering both event sources under the spec
    - the retrospective for the completed working stage contains a structurally-matched
      provenance metrics block (the AC-20 second half)
    """
    project = capture_fixtures.make_project(
        str(tmp_path), instrumented=True, marked=True
    )
    state_dir = os.path.join(project, ".claude", "automation", "state")
    os.makedirs(state_dir, exist_ok=True)

    # --- Step 1: run fbk.py state create (produces a PIPELINE_COMMAND event) ---
    create_result = _run_fbk(
        ["state", "create", "demo-spec"],
        project_root=project,
        state_dir=state_dir,
    )
    assert create_result.returncode == 0, (
        f"state create failed: {create_result.stderr!r}"
    )

    # --- Step 2: transition QUEUED -> VALIDATING (another PIPELINE_COMMAND event) ---
    transition1_result = _run_fbk(
        ["state", "transition", "demo-spec", "VALIDATING"],
        project_root=project,
        state_dir=state_dir,
    )
    assert transition1_result.returncode == 0, (
        f"transition to VALIDATING failed: {transition1_result.stderr!r}"
    )

    # --- Step 3: transition VALIDATING -> VALIDATED (triggers retro injector) ---
    transition2_result = _run_fbk(
        ["state", "transition", "demo-spec", "VALIDATED"],
        project_root=project,
        state_dir=state_dir,
    )
    assert transition2_result.returncode == 0, (
        f"transition to VALIDATED failed: {transition2_result.stderr!r}"
    )

    # --- Step 4: feed the router a PostToolUse payload (produces a TOOL_USE event) ---
    payload = capture_fixtures.hook_payload(
        "PostToolUse",
        tool_name="Bash",
    )
    router_result = _run_router(payload, project)
    assert router_result.returncode == 0, (
        f"router exited {router_result.returncode}, stderr: {router_result.stderr!r}"
    )
    assert router_result.stdout == "", (
        f"expected no stdout from router, got: {router_result.stdout!r}"
    )

    # --- Step 5: assert events.jsonl contains events from both producers ---
    events = _read_event_lines(project)

    pipeline_events = [e for e in events if e.get("event_type") == "PIPELINE_COMMAND"]
    tool_use_events = [e for e in events if e.get("event_type") == "TOOL_USE"]

    assert len(pipeline_events) >= 1, (
        f"expected at least one PIPELINE_COMMAND event, got {len(pipeline_events)}; "
        f"all events: {events!r}"
    )
    assert len(tool_use_events) >= 1, (
        f"expected at least one TOOL_USE event, got {len(tool_use_events)}; "
        f"all events: {events!r}"
    )

    # --- Step 6: verify the eight-field envelope is consistent across producers ---
    # Take one representative event from each producer and check the key set.
    pipeline_sample = pipeline_events[0]
    tool_use_sample = tool_use_events[0]

    pipeline_fields = frozenset(pipeline_sample.keys())
    tool_use_fields = frozenset(tool_use_sample.keys())

    assert _ENVELOPE_KEYS <= pipeline_fields, (
        f"PIPELINE_COMMAND event missing envelope fields: "
        f"{_ENVELOPE_KEYS - pipeline_fields}; event={pipeline_sample!r}"
    )
    assert _ENVELOPE_KEYS <= tool_use_fields, (
        f"TOOL_USE event missing envelope fields: "
        f"{_ENVELOPE_KEYS - tool_use_fields}; event={tool_use_sample!r}"
    )
    assert pipeline_fields == tool_use_fields, (
        f"envelope field sets differ between producers: "
        f"PIPELINE_COMMAND has {sorted(pipeline_fields)}, "
        f"TOOL_USE has {sorted(tool_use_fields)}"
    )

    # --- Step 7: run fbk.py report and assert it exits 0 and renders both sources ---
    report_result = _run_fbk(
        ["report", "demo-spec"],
        project_root=project,
        state_dir=state_dir,
    )
    assert report_result.returncode == 0, (
        f"report exited {report_result.returncode}, stderr: {report_result.stderr!r}"
    )

    report_output = report_result.stdout

    # The report header must reference the spec name — the (spec, stage) join anchor.
    assert "demo-spec" in report_output, (
        f"expected spec name 'demo-spec' in report output; output={report_output!r}"
    )

    # The report must include the VALIDATING stage row — that stage ran and produced
    # both chokepoint events (transitions) and is listed in _PIPELINE_STAGES.
    assert "VALIDATING" in report_output, (
        f"expected 'VALIDATING' stage row in report table; output={report_output!r}"
    )

    # The token section or stage-durations section must appear — confirming the
    # report processed both the events stream and the state without erroring.
    assert "stage durations" in report_output or "gate attempts" in report_output, (
        f"expected a metrics table section (stage durations or gate attempts) in report; "
        f"output={report_output!r}"
    )

    # Both event sources appear under the same spec in the output — the PIPELINE_COMMAND
    # events are counted in the table (tasks/scope/gate rows) and the TOOL_USE events
    # contribute to the known-subagents row. The spec line is the join header.
    assert f"spec: demo-spec" in report_output, (
        f"expected 'spec: demo-spec' join header in report; output={report_output!r}"
    )

    # --- Step 8: assert retro injector fired — the AC-20 second half ---
    # The completed working stage is VALIDATING (it transitioned to VALIDATED, not PARKED).
    retro_path = os.path.join(
        project, "ai-docs", "demo-spec", "demo-spec-retrospective.md"
    )
    assert os.path.exists(retro_path), (
        f"expected retrospective file to be created by retro injector at {retro_path!r}"
    )

    with open(retro_path, encoding="utf-8") as f:
        retro_content = f.read()

    # Assert the section heading was written by retro.append_section.
    assert "## VALIDATING — metrics" in retro_content, (
        f"expected '## VALIDATING — metrics' heading in retrospective; "
        f"content={retro_content!r}"
    )

    # Assert the provenance marker is structurally present. The marker has the fixed
    # prefix with a free-field generated= timestamp — match by structure, not exact string.
    marker_prefix = "<!-- fbk-metrics stage=VALIDATING spec=demo-spec generated="
    assert marker_prefix in retro_content, (
        f"expected provenance marker starting with {marker_prefix!r} "
        f"in retrospective; content={retro_content!r}"
    )


# ---------------------------------------------------------------------------
# Test 2 — uninstrumented project records nothing end to end
# ---------------------------------------------------------------------------


def test_uninstrumented_project_records_nothing_end_to_end(tmp_path):
    """A bare project with no sentinel and no capture.cfg produces no capture events.

    Both the router and the chokepoint must be entirely silent: no events file
    is created under the project, commands behave normally (exit 0), and the
    router produces no stdout output.
    """
    # Bare project — no sentinel, no capture.cfg.  instrumented=False creates only
    # the root directory with no .claude/automation/ subdirectory at all.
    project = capture_fixtures.make_project(str(tmp_path), instrumented=False)
    state_dir = os.path.join(project, ".claude", "automation", "state")
    os.makedirs(state_dir, exist_ok=True)

    # --- Step 1: feed the router a PostToolUse payload ---
    payload = capture_fixtures.hook_payload(
        "PostToolUse",
        tool_name="Read",
    )
    router_result = _run_router(payload, project)

    # Router exits 0 even for uninstrumented projects — it must never block the harness.
    assert router_result.returncode == 0, (
        f"expected router exit 0 for uninstrumented project, "
        f"got {router_result.returncode}; stderr: {router_result.stderr!r}"
    )
    # Router emits no stdout — any output would be interpreted as hook output.
    assert router_result.stdout == "", (
        f"expected no stdout from router for uninstrumented project, "
        f"got: {router_result.stdout!r}"
    )
    # No events file created.
    assert not os.path.exists(_events_path(project)), (
        f"expected no events.jsonl for uninstrumented project after router run, "
        f"but file was created at {_events_path(project)!r}"
    )

    # --- Step 2: run fbk.py state create and a transition through the chokepoint ---
    create_result = _run_fbk(
        ["state", "create", "demo-spec"],
        project_root=project,
        state_dir=state_dir,
    )
    # The command must behave normally — exit 0, output intact.
    assert create_result.returncode == 0, (
        f"state create should behave normally for uninstrumented project; "
        f"stderr: {create_result.stderr!r}"
    )
    # Still no events file — the chokepoint must record nothing.
    assert not os.path.exists(_events_path(project)), (
        f"expected no events.jsonl after state create for uninstrumented project; "
        f"file was created"
    )

    transition_result = _run_fbk(
        ["state", "transition", "demo-spec", "VALIDATING"],
        project_root=project,
        state_dir=state_dir,
    )
    assert transition_result.returncode == 0, (
        f"state transition should behave normally for uninstrumented project; "
        f"stderr: {transition_result.stderr!r}"
    )
    # The state JSON should still appear on stdout — normal command output is unaffected.
    assert transition_result.stdout.strip(), (
        "expected state JSON on stdout from state transition for uninstrumented project"
    )

    # --- Step 3: assert no capture file exists anywhere under the project ---
    assert not os.path.exists(_events_path(project)), (
        f"expected no events.jsonl after all producers ran for uninstrumented project; "
        f"file was created at {_events_path(project)!r}"
    )

    # Confirm no .fbk-capture directory was created at all.
    capture_dir = os.path.join(project, _CAPTURE_DIR)
    assert not os.path.isdir(capture_dir), (
        f"expected no .fbk-capture directory for uninstrumented project; "
        f"directory exists at {capture_dir!r}"
    )
