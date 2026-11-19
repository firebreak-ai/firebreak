"""Breakdown writes tasks only; implementation runs the test tasks, the test checkpoint
locks the tests, and only then does code get written and implementation close.

Covers step 4a of the test-stage amendment: no task starts while breakdown is open;
breakdown close accepts a plan-only unit and its review asks only plan questions;
``check-tests`` and ``lock-tests`` are gone; implementation close needs a current
accepted checkpoint whose locks it made; a task carrying ``stubs`` is refused.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from fbk.workflow import COMMANDS, close, engine, evidence, handoff, review, store
from .test_workflow_commands import call
from .test_workflow_implement_stages import CHECK, edit_tasks, refusal, start
from .test_workflow_lifecycle import (
    accept,
    clean_review,
    complete_declared_implementation_task,
    enter,
    mutate,
    observe_phase,
    prepare_implementation,
    project as workflow_project,
)
from .test_workflow_test_checkpoint import installed_dispatcher  # noqa: F401 - shared install fixture

project = workflow_project

REPO = Path(__file__).resolve().parents[3]
REMOVED = ("check-tests", "lock-tests")


def open_breakdown(root):
    accept(root, "intent")
    accept(root, "spec")
    enter(root, "breakdown")


def must_not_review(*args):
    raise AssertionError("A reviewer launched for a close that should be refused first.")


# Breakdown writes tasks only


@pytest.mark.parametrize("task", ["prepare-tests", "cancel"])
def test_no_task_starts_while_breakdown_is_open(project, task):
    open_breakdown(project)
    message = start(project, task, "worker")
    assert message is not None, f"{task} started during breakdown."
    assert "implement" in message, message
    record = store.load(project, "feature")
    assert not record.get("task_runs")
    assert not any(e["event"] == "task-started" for e in record["events"])


def test_breakdown_close_accepts_a_plan_with_no_tests_run_checked_or_locked(project):
    open_breakdown(project)
    # Nothing was written, run, or checked: the plan alone is accepted.
    result = close.close_phase(project, "feature", "breakdown", "s", reviewer=clean_review)
    assert result["accepted_phase"] == "breakdown"
    record = store.load(project, "feature")
    accepted = record["phases"]["breakdown"]["evidence"]
    assert accepted and accepted["outcome"] == "pass"
    assert "test_preparation" not in accepted
    assert not record["locks"]
    assert not record.get("lock_origin")
    assert not any(e["event"] in {"tests-prepared", "tests-locked"} for e in record["events"])
    assert not record.get("task_runs")


def test_breakdown_close_still_validates_the_plan(project):
    # Guard (passes now): plan validation stays at breakdown close, apart from tests.
    edit_tasks(project, lambda by_id, tasks: by_id["cancel"].update(files=["tests/check.py"]))
    open_breakdown(project)
    message = refusal(close.close_phase, project, "feature", "breakdown", "s", reviewer=must_not_review)
    assert message is not None and "cancel" in message, message
    assert not store.load(project, "feature")["phases"]["breakdown"]["evidence"]


@pytest.mark.parametrize("task", ["prepare-tests", "cancel"])
def test_a_task_carrying_stubs_is_refused_with_the_files_and_creates_remedy(project, task):
    edit_tasks(project, lambda by_id, tasks: by_id[task].update(stubs=["src/app.py"]))
    open_breakdown(project)
    message = refusal(close.close_phase, project, "feature", "breakdown", "s", reviewer=must_not_review)
    assert message is not None, "A task carrying stubs was accepted."
    assert task in message and "stubs" in message, message
    assert "files" in message and "creates" in message, message
    assert not store.load(project, "feature")["phases"]["breakdown"]["evidence"]


# The breakdown review is plan-only


def breakdown_brief():
    return review.focus_brief("unit", "breakdown", [".fbk/unit/tasks.json"])


def test_breakdown_review_asks_only_plan_questions():
    brief = breakdown_brief()
    text = " ".join([brief["decision"], *brief["acceptance_obligations"]])
    # Tests, placeholders, and red output do not exist yet when breakdown closes.
    for absent in ("stub", "red output", "actual tests", "before tests are locked",
                   "executable tests", "import and invoke"):
        assert absent not in text, f"The breakdown review still asks about {absent!r}: {text}"
    lowered = text.lower()
    for present in ("owned files", "depend", "cover"):
        assert present in lowered, f"The breakdown review no longer asks about {present!r}."
    # A named bug the plan does not show a test failing is a blocker at breakdown.
    assert any("verification" in item and "named bug" in item and "blocker" in item
               for item in brief["acceptance_obligations"]), brief["acceptance_obligations"]
    assert any("each material requirement" in item and "failing assertion" in item
               for item in brief["acceptance_obligations"]), brief["acceptance_obligations"]


# check-tests and lock-tests are gone


def test_the_removed_commands_are_not_registered():
    from fbk import COMMAND_MAP

    for command in REMOVED:
        assert command not in COMMANDS
        assert command not in COMMAND_MAP


@pytest.mark.parametrize("command, arguments", [
    ("check-tests", ["--red-check", json.dumps(CHECK)]),
    ("check-tests", ["--preserve-existing", "--reason", "Keep it."]),
    ("lock-tests", ["--red-check", json.dumps(CHECK)]),
    ("lock-tests", ["--preserve-existing", "--reason", "Keep it."]),
])
def test_the_shipped_dispatcher_refuses_the_removed_commands(project, command, arguments):
    open_breakdown(project)
    result = subprocess.run(
        [sys.executable, str(REPO / "assets/fbk-scripts/fbk.py"), command, "feature", *arguments,
         "--root", str(project), "--session", "s"],
        cwd=project, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode != 0, result.stdout
    # Refused as an unknown command, not by a phase or evidence rule of a live command.
    assert f"unrecognized command '{command}'" in result.stderr, result.stderr
    record = store.load(project, "feature")
    assert not record["locks"]
    assert "checked" not in record.get("test_preparation", {})


def test_the_shipped_dispatcher_does_not_list_the_removed_commands():
    result = subprocess.run([sys.executable, str(REPO / "assets/fbk-scripts/fbk.py"), "--help"],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    listed = result.stdout.replace(",", " ").split()
    assert "test-checkpoint" in listed
    for command in REMOVED:
        assert command not in listed


def test_the_installed_dispatcher_does_not_list_the_removed_commands(installed_dispatcher):  # noqa: F811
    dispatcher, env = installed_dispatcher
    result = subprocess.run([sys.executable, str(dispatcher), "--help"], env=env,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    listed = result.stdout.replace(",", " ").split()
    assert "test-checkpoint" in listed
    for command in REMOVED:
        assert command not in listed


def test_unlock_approval_stays_on_the_command_line(project):
    # approve unlock-test takes the approved rework (per-test expected outcomes and the
    # commands covering them) from a JSON request file, as other request-taking commands do.
    prepare_implementation(project)
    store.atomic_json(project / ".fbk/unlock-request.json", {
        "expected": {"tests/check.py": "fail"},
        "commands": [{"argv": [sys.executable, "tests/check.py"], "tests": ["tests/check.py"]}],
    })
    arguments = ["unlock-test", "--phase", "implement",
                 "--reason", "The cancellation test asserts the wrong call.", "--tests", "tests/check.py",
                 "--request", ".fbk/unlock-request.json"]
    from .test_workflow_test_checkpoint import parses

    assert parses("approve", "feature", *arguments), "approve unlock-test takes no request file."
    call(project, "approve", "feature", *arguments)
    record = store.load(project, "feature")
    assert record["unlocks"] == ["tests/check.py"]
    assert record["grants"][-1]["crossing"] == "unlock-test"
    # The rework run carries the approved command, its exit derived as non-zero.
    packet = mutate(project, handoff.start_task, "s", "prepare-tests", "rework-author")
    assert [item["argv"] for item in packet["check_expectations"]] == [[sys.executable, "tests/check.py"]]
    assert packet["check_expectations"][0]["exit_code"] not in (0, None)


# Implementation close needs a current accepted checkpoint


def code_written(root):
    """Writing code after the checkpoint: the implementation task makes the check pass."""
    prepare_implementation(root)
    (root / "src/app.py").write_text("release()")
    complete_declared_implementation_task(root)


def set_record(root, change):
    with store.transaction(root):
        record = store.load(root, "feature")
        change(record)
        store.save(root, record)


def test_implementation_closes_with_a_current_accepted_checkpoint(project):
    code_written(project)
    record = store.load(project, "feature")
    assert record.get("lock_origin") == evidence.CHECKPOINT
    assert engine.checkpoint_current(project, record)
    result = close.close_phase(project, "feature", "implement", "s", reviewer=clean_review)
    assert result["status"] == "retrospective-required"
    observe_phase(project, "implement")
    assert engine.status_report(project, store.load(project, "feature"))["status"] == "closed"


def stale_checkpoint(record):
    record["phases"]["test-checkpoint"]["evidence"]["revision"] = "0" * 64


def breakdown_locks(record):
    # The locks a pre-amendment breakdown made: no checkpoint acceptance behind them.
    record["phases"]["test-checkpoint"]["evidence"] = None
    record["lock_origin"] = "breakdown"


def origin_less_locks(record):
    record.pop("lock_origin", None)


def no_checkpoint_acceptance(record):
    record["phases"]["test-checkpoint"]["evidence"] = None


@pytest.mark.parametrize("change", [stale_checkpoint, breakdown_locks, origin_less_locks,
                                    no_checkpoint_acceptance])
def test_implementation_close_refuses_without_a_current_checkpoint_lock(project, change):
    code_written(project)
    set_record(project, change)
    locks = store.load(project, "feature")["locks"]
    assert locks and engine.verify_locks(project, store.load(project, "feature")) is None
    message = refusal(close.close_phase, project, "feature", "implement", "s", reviewer=must_not_review)
    assert message is not None, "Implementation closed without a current accepted checkpoint."
    assert "checkpoint" in message.lower(), message
    record = store.load(project, "feature")
    assert record["phases"]["implement"]["evidence"] is None
    assert record["phases"]["implement"]["rounds"] == []


def test_implementation_close_names_the_checkpoint_when_tests_were_never_locked(project):
    accept(project, "intent")
    accept(project, "spec")
    accept(project, "breakdown")
    mutate(project, engine.approve, "s", "start-implementation", "implement", "Proceed.")
    enter(project, "implement")
    message = refusal(close.close_phase, project, "feature", "implement", "s", reviewer=must_not_review)
    assert message is not None
    assert store.load(project, "feature")["phases"]["implement"]["evidence"] is None


# Guides


@pytest.mark.parametrize("guide", ["fbk-docs/workflow/breakdown.md", "fbk-docs/workflow/handoffs.md",
                                   "skills/fbk-breakdown/SKILL.md"])
def test_breakdown_guides_name_no_removed_command(guide):
    text = (REPO / "assets" / guide).read_text(encoding="utf-8")
    for command in REMOVED:
        assert command not in text, f"{guide} still names {command}."
