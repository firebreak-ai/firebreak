"""Plan references and completed task runs must not overstate handoff readiness."""

import copy

import pytest

from fbk.workflow import engine, handoff, store, task_graph
from .test_workflow_dependency_lineage import branching, finish, implemented_branch, open_implement
from .test_workflow_lifecycle import mutate, project as project
from .refactor_plan import with_refactor


def row(name, files, *, deps=(), refs=(), consumes=()):
    return {"id": name, "stage": "tests", "files": files,
            "depends_on": list(deps), "input_refs": list(refs), "consumes": list(consumes)}


@pytest.mark.parametrize("ref", ["guide.md#missing", "guide.md:20", "absent.md"])
def test_plan_rejects_unresolved_input_with_task_and_reference(tmp_path, ref):
    (tmp_path / "guide.md").write_text("# Available\n")
    with pytest.raises(store.WorkflowError) as error:
        task_graph.validate(tmp_path, [row("reader", ["result.py"], refs=[ref])])
    assert "reader" in str(error.value)
    assert ref in str(error.value)


def test_future_reference_waits_for_producer_then_resolves_anchor(tmp_path):
    tasks = [row("producer", ["guide.md"]),
             row("reader", ["result.py"], deps=["producer"], refs=["guide.md#contract"])]
    task_graph.validate(tmp_path, tasks)
    with pytest.raises(store.WorkflowError, match="missing"):
        handoff._references(tmp_path, tasks[1]["input_refs"], "input_refs")
    (tmp_path / "guide.md").write_text("# Wrong heading\n")
    task_graph.validate(tmp_path, tasks)
    with pytest.raises(store.WorkflowError, match="anchor"):
        handoff._references(tmp_path, tasks[1]["input_refs"], "input_refs")
    (tmp_path / "guide.md").write_text("# Contract\n")
    task_graph.validate(tmp_path, tasks)
    assert handoff._references(tmp_path, tasks[1]["input_refs"], "input_refs") == ["guide.md"]


@pytest.mark.parametrize("consumes", [["missing.py"], ["missing/*.py"]])
def test_missing_consumption_needs_matching_ordered_producer(tmp_path, consumes):
    tasks = [row("producer", ["unrelated.py"]),
             row("reader", ["result.py"], deps=["producer"], consumes=consumes)]
    with pytest.raises(store.WorkflowError, match="reader.*missing.*producer"):
        task_graph.validate(tmp_path, tasks)
    tasks[0]["files"] = ["missing/file.py"] if "*" in consumes[0] else consumes
    task_graph.validate(tmp_path, tasks)


def test_input_reference_alone_protects_consumer_and_rejects_escape(tmp_path):
    (tmp_path / "guide.md").write_text("# Contract\n")
    tasks = [row("producer", ["guide.md"]), row("reader", ["result.py"], refs=["guide.md"])]
    with pytest.raises(store.WorkflowError, match="order"):
        task_graph.validate(tmp_path, tasks)
    tasks[1]["depends_on"] = ["producer"]
    task_graph.validate(tmp_path, tasks)
    tasks[1]["input_refs"] = ["../outside.md"]
    with pytest.raises(store.WorkflowError):
        task_graph.validate(tmp_path, tasks)


@pytest.mark.parametrize("change", ["plan", "returned-file"])
def test_changed_completed_test_task_blocks_without_restamping(project, change):
    # Writing tests in implement: a completed test task whose plan entry or returned
    # file changed is reported, never silently restamped, and keeps the unit writing tests.
    tasks = implemented_branch(project)
    mutate(project, handoff.start_task, "s", "storage-tests", "author")
    (project / "src/storage.py").write_text("def release():\n    return None\n")
    finish(project, "storage-tests", ["src/storage.py"], 1)
    before = copy.deepcopy(store.load(project, "feature")["task_runs"])
    if change == "plan":
        tasks[0]["description"] += " Updated definition."
        store.atomic_json(project / ".fbk/feature/tasks.json", with_refactor(tasks))
    else:
        (project / "tests/check.py").write_text("assert False, 'required behavior missing'\n")
    record = store.load(project, "feature")
    blockers = [b for b in handoff.task_run_blockers(project, record) if b["task"] == "storage-tests"]
    assert len(blockers) == 1
    blocker = blockers[0]
    assert "task-start" in blocker["next"]
    assert record["task_runs"] == before
    assert engine.implement_stage(project, record) == "writing-tests"
    with pytest.raises(store.WorkflowError, match="storage-tests"):
        handoff.verify_task_runs(project, record)


def test_empty_optional_input_refs_allow_launch(project):
    tasks = branching(project)
    tasks[0]["input_refs"] = []
    store.atomic_json(project / ".fbk/feature/tasks.json", with_refactor(tasks))
    open_implement(project)
    packet = mutate(project, handoff.start_task, "s", "storage-tests", "author")
    assert packet["input_refs"] == []
    assert packet["acceptance_refs"]
