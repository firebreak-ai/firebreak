"""Producer-to-report integration test — the contract the unit fixtures miss.

Every other report test hand-builds event dicts in the shape the report *reads*.
This test instead drives the *real producers* (the task-completed hook through the
dispatch chokepoint, and the code-review gate) into a real events.jsonl, then runs
the real report over it and asserts the headline numbers are correct.

Because no event dict is hand-authored here, the test cannot encode the report's
assumptions on both sides of the producer/consumer contract.  If a producer writes
a key, value, or stage field the report does not read, a row silently reads zero
and the matching assertion below fails.  That is the whole point: this test fails
the moment producer and consumer envelopes drift apart.

It exercises the three cleanly-drivable Theme-A rows:
  - tasks completed   (PIPELINE_COMMAND, command_name "task-completed")
  - gate first-try rate (VERIFICATION_RESULT, attributed to the active stage;
                         also PIPELINE_COMMAND for gate commands in GATE_COMMAND_NAMES)
  - code-review kill rate (CODE_REVIEW_ROUNDS, total_raised / total_survived)
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

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

FBK_PY = Path(__file__).parent.parent / "fbk.py"

_SPEC = "demo-spec"
_STAGE = "IMPLEMENTING"


def _run_fbk(args, project_root, state_dir, stdin_text=None):
    """Run fbk.py with args in project_root, STATE_DIR set to state_dir."""
    env = {**os.environ, "STATE_DIR": str(state_dir)}
    return subprocess.run(
        [sys.executable, str(FBK_PY)] + args,
        input=stdin_text,
        capture_output=True,
        text=True,
        cwd=str(project_root),
        env=env,
        timeout=30,
    )


def _events(project_root):
    """Return parsed event dicts from the project's events.jsonl."""
    path = os.path.join(str(project_root), ".fbk-capture", "events.jsonl")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def _row_value(output, pattern):
    """Return the first regex group captured from the first matching report line."""
    m = re.search(pattern, output)
    return m.group(1) if m else None


def test_real_producers_drive_nonzero_report_rows(tmp_path):
    """A real verification, task-completion, and code-review round populate the report.

    Drives the actual task-completed hook (through the chokepoint) and the actual
    code-review gate against an instrumented project with an active IMPLEMENTING
    stage, then runs the real report and asserts the three headline rows reflect
    the captured facts rather than reading zero.
    """
    project = capture_fixtures.make_project(
        str(tmp_path), instrumented=True, marked=True
    )
    state_dir = os.path.join(project, ".claude", "automation", "state")
    os.makedirs(state_dir, exist_ok=True)

    # Active state: the IMPLEMENTING working stage is in progress (no parks), so the
    # chokepoint attributes commands to it and the report renders its rows.
    state = capture_fixtures.build_state(
        _SPEC,
        stage_timestamps={
            "QUEUED": "2026-01-01T00:00:00+00:00",
            _STAGE: "2026-01-01T01:00:00+00:00",
        },
        current_state=_STAGE,
    )
    capture_fixtures.write_state(state_dir, state)

    # A task file the hook's task-path regex will match (no declared-files section,
    # so no out-of-scope check fires and the verification passes cleanly).
    feature_dir = os.path.join(project, "ai-docs", _SPEC)
    tasks_dir = os.path.join(feature_dir, "tasks")
    os.makedirs(tasks_dir, exist_ok=True)
    with open(os.path.join(tasks_dir, "task-01.md"), "w") as f:
        f.write("# Task 01\n\nDo the thing.\n")

    # A valid code-review round log: 5 findings raised, 2 survived → kill rate 0.60.
    with open(os.path.join(feature_dir, ".code-review-rounds.json"), "w") as f:
        json.dump({"spec": _SPEC, "rounds": [{"raised": 5, "survived": 2}]}, f)

    # Gate pass artifacts: quality-scan.md (must contain "Severity:") and
    # test-review-final.md (must carry an accepted verdict — the gate blocks on a
    # non-accepted or unreadable verdict).  An absent test-hashes.json manifest
    # yields only non-blocking "missing" findings, so no hash manifest is needed.
    with open(os.path.join(feature_dir, "quality-scan.md"), "w") as f:
        f.write("Severity: minor\n")
    with open(os.path.join(feature_dir, "test-review-final.md"), "w") as f:
        f.write("# Test review — final pass\n\nVerdict: accepted\n")

    # --- Drive the real task-completed hook through the chokepoint ---
    # No test runner or linter is present, so both checks are skipped and the hook
    # exits 0: one PIPELINE_COMMAND (command_name "task-completed", outcome pass)
    # plus one passing VERIFICATION_RESULT.
    payload = json.dumps(
        {
            "task_description": f"Implement ai-docs/{_SPEC}/tasks/task-01.md",
            "cwd": project,
        }
    )
    tc = _run_fbk(["task-completed"], project, state_dir, stdin_text=payload)
    assert tc.returncode == 0, f"task-completed should pass cleanly; stderr={tc.stderr!r}"

    # --- Drive the real code-review gate (emits CODE_REVIEW_ROUNDS as a side effect) ---
    # The gate artifacts written above make it pass deterministically.
    cr = _run_fbk(["code-review-gate", f"ai-docs/{_SPEC}"], project, state_dir)
    assert cr.returncode == 0, (
        f"code-review-gate should pass with quality-scan.md and test-review-final.md present; "
        f"stdout={cr.stdout!r}; stderr={cr.stderr!r}"
    )

    # Sanity: the real producers wrote the three event types we will read back.
    events = _events(project)
    types = {e.get("event_type") for e in events}
    assert {"PIPELINE_COMMAND", "VERIFICATION_RESULT", "CODE_REVIEW_ROUNDS"} <= types, (
        f"expected all three producer events in the stream, got {types}; events={events!r}"
    )

    # Sanity: exactly one code-review-gate PIPELINE_COMMAND with outcome=pass on IMPLEMENTING.
    cr_gate_events = [
        e for e in events
        if e.get("event_type") == "PIPELINE_COMMAND"
        and e.get("data", {}).get("command_name") == "code-review-gate"
        and e.get("stage") == _STAGE
    ]
    assert len(cr_gate_events) == 1, (
        f"expected exactly 1 code-review-gate PIPELINE_COMMAND on {_STAGE}, "
        f"got {len(cr_gate_events)}: {cr_gate_events!r}"
    )
    assert cr_gate_events[0].get("data", {}).get("outcome") == "pass", (
        f"expected code-review-gate outcome=pass, got: {cr_gate_events[0].get('data')!r}"
    )

    # --- Run the real report and read its rows ---
    rep = _run_fbk(["report", _SPEC], project, state_dir)
    assert rep.returncode == 0, f"report failed: {rep.stderr!r}"
    out = rep.stdout

    # 1) Tasks completed: exactly 1 real task-completion on the IMPLEMENTING row.
    completed = _row_value(out, rf"{_STAGE}\s+tasks completed:\s*(\d+)")
    assert completed is not None and int(completed) == 1, (
        f"expected IMPLEMENTING tasks-completed == 1 from a real task-completion, "
        f"got {completed!r}\n--- report ---\n{out}"
    )

    # 2) First-try gate rate: two first-try attempts on IMPLEMENTING — the passing
    #    verification plus the passing code-review-gate dispatch → 2/2 = 1.00.
    rate = _row_value(out, rf"{_STAGE}\s+first-try rate:\s*([\d.]+)")
    assert rate is not None and float(rate) == pytest.approx(1.0), (
        f"expected IMPLEMENTING first-try rate 1.00 (2/2: verification + code-review-gate), "
        f"got {rate!r}\n--- report ---\n{out}"
    )

    # 3) Kill rate: 5 raised, 2 survived → (5-2)/5 = 0.60.
    kr = _row_value(out, r"kill rate:\s*([\d.]+)")
    assert kr is not None and float(kr) == pytest.approx(0.60), (
        f"expected kill rate 0.60 from 5 raised / 2 survived, got {kr!r}\n"
        f"--- report ---\n{out}"
    )


def test_gate_outcomes_drive_exact_first_try_fraction(tmp_path):
    """Gate PIPELINE_COMMAND events on spec/task-reviewer/code-review gates count in the rate.

    Drives the real gate-fail → park → recover cycle via capture_fixtures.drive_gate_fail_park_recover,
    then runs the real report and pins VALIDATING first-try rate to exactly 0.50.

    Red mechanics: the pre-fix classify_gate_attempts ignores PIPELINE_COMMAND events
    entirely — it reads only VERIFICATION_RESULT.  With only the one passing verification
    visible, it reports first-try rate 1.00, not 0.50, so this test fails at the pre-fix
    commit when the 0.50 pin is checked.
    """
    project = capture_fixtures.make_project(str(tmp_path), instrumented=True, marked=True)
    state_dir = os.path.join(project, ".claude", "automation", "state")

    # drive_gate_fail_park_recover creates the state from scratch via state-create and
    # state-transition; it does not need a pre-written state file.
    events = capture_fixtures.drive_gate_fail_park_recover(project, state_dir, _SPEC)

    # Sanity: the fixture produced the expected event mix for VALIDATING.
    # The chokepoint writes one PIPELINE_COMMAND per spec-gate call with the real
    # stage; spec.py also writes one with stage=None.  Filtering by stage=VALIDATING
    # isolates the two chokepoint-written events (one fail before park, one pass after).
    spec_gate_events = [
        e for e in events
        if e.get("event_type") == "PIPELINE_COMMAND"
        and e.get("data", {}).get("command_name") == "spec-gate"
        and e.get("stage") == "VALIDATING"
    ]
    assert len(spec_gate_events) == 2, (
        f"expected exactly 2 spec-gate PIPELINE_COMMAND events on VALIDATING, "
        f"got {len(spec_gate_events)}: {spec_gate_events!r}"
    )

    passing_verifications = [
        e for e in events
        if e.get("event_type") == "VERIFICATION_RESULT"
        and e.get("stage") == "VALIDATING"
        and (
            e.get("data", {}).get("tests_passed")
            or e.get("data", {}).get("passed")
            or e.get("data", {}).get("result") == "pass"
        )
    ]
    assert len(passing_verifications) == 1, (
        f"expected exactly 1 passing VERIFICATION_RESULT on VALIDATING, "
        f"got {len(passing_verifications)}: {passing_verifications!r}"
    )

    # Run the real report and read the VALIDATING rows.
    rep = _run_fbk(["report", _SPEC], project, state_dir)
    assert rep.returncode == 0, f"report failed: {rep.stderr!r}"
    out = rep.stdout

    # First-try rate for VALIDATING:
    #   - Before the park: passing verification (attempt 1, pass) + spec-gate fail (attempt 2, fail) → 1/2 = 0.50
    #   - After the park (after-rework): spec-gate pass → 1/1 = 1.00
    ftr = _row_value(out, r"VALIDATING\s+first-try rate:\s*([\d.]+)")
    assert ftr is not None and float(ftr) == pytest.approx(0.50), (
        f"expected VALIDATING first-try rate 0.50 "
        f"(1 passing verification + 1 spec-gate fail before park = 1/2), "
        f"got {ftr!r}\n--- report ---\n{out}"
    )

    # After-rework rate: spec-gate pass is the sole after-rework attempt → 1/1 = 1.00.
    arr = _row_value(out, r"VALIDATING\s+first-try rate:.*?after-rework rate:\s*([\d.]+)")
    assert arr is not None and float(arr) == pytest.approx(1.00), (
        f"expected VALIDATING after-rework rate 1.00 (spec-gate pass after re-entry), "
        f"got {arr!r}\n--- report ---\n{out}"
    )

    # Tasks reworked: one park-driven re-entry of VALIDATING.
    reworked = _row_value(out, r"VALIDATING\s+tasks completed:.*?tasks reworked:\s*(\d+)")
    assert reworked is not None and int(reworked) == 1, (
        f"expected VALIDATING tasks reworked == 1 (one park-driven re-entry), "
        f"got {reworked!r}\n--- report ---\n{out}"
    )
