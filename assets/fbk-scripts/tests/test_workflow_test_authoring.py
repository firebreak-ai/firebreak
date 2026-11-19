"""Fresh test workers receive canonical guidance from the active installation."""

import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from fbk.workflow import handoff, store
from tests.test_workflow_lifecycle import mutate, prepare_implementation, project as project
from tests.test_workflow_dependency_lineage import open_implement
from tests.test_workflow_test_preparation import setup_plan


@pytest.mark.parametrize("installation_scope", ["project", "global"])
@pytest.mark.parametrize("stage", ["tests", "implementation"])
def test_fresh_worker_receives_stage_guidance_from_runtime_installation(
    project, tmp_path, installation_scope, stage
):
    if stage == "tests":
        # Test tasks run in implement, after a plan-only breakdown.
        setup_plan(project)
        open_implement(project)
        task = "behavior-tests"
    else:
        prepare_implementation(project)
        task = "cancel"
    mutate(project, handoff.start_task, "s", task, "fresh-worker")

    # Reproduce the shipped directory layout without installing into a live project.
    assets = Path(__file__).resolve().parents[2]
    target = (project if installation_scope == "project" else tmp_path / "home") / ".claude"
    scripts = target / "fbk-scripts"
    scripts.mkdir(parents=True)
    shutil.copy2(assets / "fbk-scripts/fbk.py", scripts / "fbk.py")
    shutil.copytree(assets / "fbk-scripts/fbk", scripts / "fbk", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(assets / "fbk-docs/workflow", target / "fbk-docs/workflow")
    # A current-working-directory lookalike must not replace installed methodology.
    lookalike = project / "fbk-docs/workflow/test-authoring.md"
    lookalike.parent.mkdir(parents=True)
    lookalike.write_text("PROJECT_LOOKALIKE")

    def run(*args, payload=None):
        result = subprocess.run(
            [sys.executable, "-I", str(scripts / "fbk.py"), *args], cwd=project,
            input=json.dumps(payload) if payload else None,
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    context = run("task-context", "feature", task, "--root", str(project), "--session", "s")
    hook = run("workflow-hook", payload={
        "hook_event_name": "SubagentStart", "session_id": "s", "agent_id": "fresh-worker",
        "cwd": str(project),
    })
    spawned = json.loads(hook["hookSpecificOutput"]["additionalContext"].split("\n", 1)[1])
    assert spawned == context
    assert context["authoring_guidance"] == (target / "fbk-docs/workflow/repository-grounding.md").read_text()
    assert set(context["acceptance_refs"]) == {".fbk/feature/prd.md", ".fbk/feature/spec.md", ".fbk/feature/spec.md#cancel-once"}
    if stage == "tests":
        assert context["test_authoring_guidance"] == (target / "fbk-docs/workflow/test-authoring.md").read_text()
        assert "PROJECT_LOOKALIKE" not in json.dumps(context)
    else:
        assert "test_authoring_guidance" not in context


@pytest.mark.parametrize("contents", [None, " \n"])
def test_missing_test_guidance_reports_installed_path_before_assignment(
    project, tmp_path, monkeypatch, contents
):
    setup_plan(project)
    open_implement(project)
    installation = tmp_path / "installation"
    docs = installation / "fbk-docs/workflow"
    docs.mkdir(parents=True)
    (docs / "repository-grounding.md").write_text("Inspect relevant project sources.")
    path = docs / "test-authoring.md"
    if contents is not None:
        path.write_text(contents)
    monkeypatch.setattr(handoff, "__file__", str(installation / "fbk-scripts/fbk/workflow/handoff.py"))
    with pytest.raises(store.WorkflowError, match="restore the installed file and retry") as failure:
        mutate(project, handoff.start_task, "s", "behavior-tests", "fresh-worker")
    assert str(path) in str(failure.value)
    assert not store.load(project, "feature").get("task_runs")
