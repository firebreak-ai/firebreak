"""Planned references can target future contents; task launch requires real contents."""

import pytest

from fbk.workflow import handoff, store, task_graph
from .test_workflow_dependency_lineage import branching, finish, open_implement
from .test_workflow_lifecycle import mutate, project as project
from .refactor_plan import with_refactor


def graph(ref, *, producer_files=("guide.md",), dependency=True):
    return [
        {"id": "producer", "files": list(producer_files), "depends_on": []},
        {"id": "reader", "files": ["result.py"],
         "depends_on": ["producer"] if dependency else [], "input_refs": [ref]},
    ]


@pytest.mark.parametrize("ref", ["guide.md#new-contract", "guide.md:3"])
@pytest.mark.parametrize("ownership", [["guide.md"], ["*.md"]])
def test_existing_file_can_receive_future_reference_target(tmp_path, ref, ownership):
    (tmp_path / "guide.md").write_text("# Existing contract\n")
    task_graph.validate(tmp_path, graph(ref, producer_files=ownership))


@pytest.mark.parametrize("ref", ["guide.md#typo", "guide.md:30", "typo.md#contract"])
@pytest.mark.parametrize("producer", [[], ["unrelated.md"]])
def test_unresolved_reference_without_matching_producer_rejected(tmp_path, ref, producer):
    (tmp_path / "guide.md").write_text("# Existing contract\n")
    with pytest.raises(store.WorkflowError) as error:
        task_graph.validate(tmp_path, graph(ref, producer_files=producer))
    assert "reader" in str(error.value)
    assert ref in str(error.value)


@pytest.mark.parametrize("ref", ["guide.md#new-contract", "guide.md:3", "guide.md"])
def test_writer_must_precede_reader(tmp_path, ref):
    (tmp_path / "guide.md").write_text("# Existing contract\n")
    with pytest.raises(store.WorkflowError):
        task_graph.validate(tmp_path, graph(ref, dependency=False))
    tasks = graph(ref, dependency=False)
    tasks[0]["depends_on"] = ["reader"]
    if ref != "guide.md":
        with pytest.raises(store.WorkflowError):
            task_graph.validate(tmp_path, tasks)
    else:
        task_graph.validate(tmp_path, tasks)


def test_transitive_predecessor_can_supply_future_contents(tmp_path):
    (tmp_path / "guide.md").write_text("# Existing contract\n")
    tasks = graph("guide.md#new-contract")
    tasks.append({"id": "middle", "files": ["middle.py"], "depends_on": ["producer"]})
    tasks[1]["depends_on"] = ["middle"]
    task_graph.validate(tmp_path, tasks)


def test_own_output_cannot_supply_missing_launch_input(tmp_path):
    (tmp_path / "guide.md").write_text("# Existing contract\n")
    tasks = graph("guide.md#new-contract", producer_files=[])
    tasks[1]["files"] = ["guide.md"]
    with pytest.raises(store.WorkflowError, match="reader.*anchor"):
        task_graph.validate(tmp_path, tasks)


def test_future_reference_still_confines_producer_owned_path(tmp_path):
    with pytest.raises(store.WorkflowError):
        task_graph.validate(tmp_path, graph("../guide.md#future", producer_files=["../guide.md"]))


@pytest.mark.parametrize("ref,error", [("tests/guide.md#new-contract", "anchor"),
                                       ("tests/guide.md:3", "line")])
def test_consumer_launch_requires_resolved_predecessor_output(project, ref, error):
    guide = project / "tests/guide.md"
    guide.write_text("# Existing contract\n")
    tasks = branching(project)
    tasks[0]["files"].append("tests/guide.md")
    tasks[1]["input_refs"] = [ref]
    store.atomic_json(project / ".fbk/feature/tasks.json", with_refactor(tasks))
    task_graph.validate(project, tasks)
    open_implement(project)

    mutate(project, handoff.start_task, "s", "storage-tests", "author")
    (project / "src/storage.py").write_text("def release():\n    return None\n")
    finish(project, "storage-tests", ["src/storage.py"], 1)
    with pytest.raises(store.WorkflowError, match=error):
        mutate(project, handoff.start_task, "s", "cli-tests", "reader")
    assert "cli-tests" not in store.load(project, "feature")["task_runs"]

    mutate(project, handoff.start_task, "s", "storage-tests", "author")
    guide.write_text("# Existing contract\n\n# New contract\n")
    finish(project, "storage-tests", ["tests/guide.md"], 1)
    packet = mutate(project, handoff.start_task, "s", "cli-tests", "reader")
    assert packet["input_refs"] == [ref]
    returned = store.load(project, "feature")["task_runs"]["storage-tests"]["return"]
    assert packet["consumed_files"]["tests/guide.md"] == returned["files"]["tests/guide.md"]
