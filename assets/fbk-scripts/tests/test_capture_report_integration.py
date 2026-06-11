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
  - gate first-try rate (VERIFICATION_RESULT, attributed to the active stage)
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
    _run_fbk(["code-review-gate", f"ai-docs/{_SPEC}"], project, state_dir)

    # Sanity: the real producers wrote the three event types we will read back.
    events = _events(project)
    types = {e.get("event_type") for e in events}
    assert {"PIPELINE_COMMAND", "VERIFICATION_RESULT", "CODE_REVIEW_ROUNDS"} <= types, (
        f"expected all three producer events in the stream, got {types}; events={events!r}"
    )

    # --- Run the real report and read its rows ---
    rep = _run_fbk(["report", _SPEC], project, state_dir)
    assert rep.returncode == 0, f"report failed: {rep.stderr!r}"
    out = rep.stdout

    # 1) Tasks completed: the real task-completion must register on the IMPLEMENTING row.
    completed = _row_value(out, rf"{_STAGE}\s+tasks completed:\s*(\d+)")
    assert completed is not None and int(completed) >= 1, (
        f"expected IMPLEMENTING tasks-completed >= 1 from a real task-completion, "
        f"got {completed!r}\n--- report ---\n{out}"
    )

    # 2) First-try gate rate: one passing verification on the active stage → 1.00.
    rate = _row_value(out, rf"{_STAGE}\s+first-try rate:\s*([\d.]+)")
    assert rate is not None and float(rate) == pytest.approx(1.0), (
        f"expected IMPLEMENTING first-try rate 1.00 from a passing verification, "
        f"got {rate!r}\n--- report ---\n{out}"
    )

    # 3) Kill rate: 5 raised, 2 survived → (5-2)/5 = 0.60.
    kr = _row_value(out, r"kill rate:\s*([\d.]+)")
    assert kr is not None and float(kr) == pytest.approx(0.60), (
        f"expected kill rate 0.60 from 5 raised / 2 survived, got {kr!r}\n"
        f"--- report ---\n{out}"
    )
