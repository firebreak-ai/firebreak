"""Every test-authoring and implementation task runs in a subagent, never in the lead session."""

from pathlib import Path

import pytest

from fbk.workflow import handoff, hooks, store
from tests.test_workflow_lifecycle import mutate, prepare_implementation, project as project
from tests.test_workflow_dependency_lineage import open_implement
from tests.test_workflow_test_preparation import setup_plan

ASSETS = Path(__file__).resolve().parents[2]


def open_phase(project, stage):
    if stage == "tests":
        # Test tasks run in implement, while tests are being written.
        setup_plan(project)
        open_implement(project)
        return "behavior-tests"
    prepare_implementation(project)
    return "cancel"


def write_decision(project, path):
    return hooks.handle(project, {
        "hook_event_name": "PreToolUse", "session_id": "s", "tool_name": "Write",
        "cwd": str(project), "tool_input": {"file_path": path},
    })


@pytest.mark.parametrize("stage", ["tests", "implementation"])
def test_lead_cannot_assign_a_task_to_itself(project, stage):
    task = open_phase(project, stage)
    with pytest.raises(store.WorkflowError, match="subagent"):
        mutate(project, handoff.start_task, "s", task, "s")
    assert task not in store.load(project, "feature").get("task_runs", {})


@pytest.mark.parametrize("stage", ["tests", "implementation"])
def test_lead_cannot_write_project_files_but_keeps_unit_artifacts(project, stage):
    open_phase(project, stage)
    denied = write_decision(project, "src/app.py")["hookSpecificOutput"]
    assert denied["permissionDecision"] == "deny"
    assert "lead does not edit" in denied["permissionDecisionReason"]
    assert write_decision(project, ".fbk/feature/notes.md") == {}


def test_close_rejects_a_task_recorded_under_the_lead_session(project):
    prepare_implementation(project)
    # A run recorded before the fix, when the lead could name itself as the worker.
    with store.transaction(project):
        record = store.load(project, "feature")
        record["task_runs"] = {"cancel": {"status": "completed", "worker_id": "s"}}
        store.save(project, record)
    problems = handoff.task_run_blockers(project, store.load(project, "feature"))
    # The planned refactor task has not run yet, so it is reported as unassigned beside it.
    assert [(p["task"], p["reason"]) for p in problems] == [
        ("refactor", "Implementation task is unassigned."),
        ("cancel", "Task ran in the lead session instead of a subagent."),
    ]


def test_workflow_docs_state_the_subagent_rule():
    skill = (ASSETS / "skills/fbk-implement/SKILL.md").read_text(encoding="utf-8")
    assert "subagent" in skill
    for guide in ("handoffs.md", "breakdown.md"):
        text = (ASSETS / "fbk-docs/workflow" / guide).read_text(encoding="utf-8")
        assert "--worker <session-id>" not in text
        assert "session id as the worker" not in text
