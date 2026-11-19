"""Executable task graphs preserve red provenance through interface-placeholder replacement.

Breakdown writes tasks only; the test tasks run in implement, the test checkpoint
locks their tests, and the implementation tasks follow."""

import json
import re
import sys

import pytest

from fbk.workflow import close, engine, handoff, store
from .test_workflow_implement_stages import plan_refusals
from .test_workflow_lifecycle import (
    accept, clean_review, enter, mutate, observe_phase, pass_checkpoint, project as project,
)
from .refactor_plan import REFACTOR_ID, complete_refactor_tasks, with_refactor


def task(name, stage, files, deps=(), consumes=()):
    return {
        "id": name, "stage": stage, "description": name,
        "files": files, "depends_on": list(deps), "consumes": list(consumes),
        "acceptance_refs": [".fbk/feature/prd.md", ".fbk/feature/spec.md", ".fbk/feature/spec.md#cancel-once"],
        "verification": "An observable release is required, not a no-op.",
        "check_expectations": [{"argv": [sys.executable, "tests/check.py"],
                                "exit_code": 1 if stage == "tests" else 0}],
    }


def write_tasks(root, tasks):
    """Write the plan with one refactor task covering its current implementation tasks."""
    store.atomic_json(root / ".fbk/feature/tasks.json",
                      with_refactor([t for t in tasks if t["id"] != REFACTOR_ID]))


def branching(root, creates=("src/storage.py", "tests/cli.py")):
    tasks = [
        task("storage-tests", "tests", ["tests/check.py", "src/storage.py"]),
        task("cli-tests", "tests", ["tests/cli.py"], ["storage-tests"], ["src/storage.py"]),
        task("storage-implementation", "implementation", ["src/storage.py"], ["storage-tests"], ["tests/check.py"]),
        task("cli-implementation", "implementation", ["src/app.py"], ["cli-tests", "storage-implementation"], ["src/storage.py", "tests/cli.py"]),
    ]
    write_tasks(root, tasks)
    (root / "tests/check.py").write_text(
        "import runpy\nassert runpy.run_path('src/storage.py')['release']() == 'released'\n"
    )
    # The spec declares the paths the plan's tasks create.
    scope_path = root / ".fbk/feature/scope.json"
    store.atomic_json(scope_path, {**store.read_json(scope_path), "creates": list(creates)})
    accept(root, "intent")
    accept(root, "spec")
    enter(root, "breakdown")
    return tasks


def open_implement(root):
    """Close the open breakdown with tasks only, approve, and enter implement: writing tests."""
    close.close_phase(root, "feature", "breakdown", "s", reviewer=clean_review)
    observe_phase(root, "breakdown")
    mutate(root, engine.approve, "s", "start-implementation", "implement", "Approved checks and graph.")
    enter(root, "implement")


def implemented_branch(root, creates=("src/storage.py", "tests/cli.py")):
    """branching, then implement entered: the test tasks have not run."""
    tasks = branching(root, creates)
    open_implement(root)
    return tasks


def finish(root, name, changed, code):
    return mutate(root, handoff.finish_task, "s", name, changed_files=changed,
                  checks=[{"argv": [sys.executable, "tests/check.py"], "exit_code": code,
                           "evidence": "Actual storage release assertion executed."}],
                  unresolved=[], outcome="Prepared or implemented release behavior.")


def run_branch_tests(root):
    """Both test tasks run in implement, then the checkpoint locks their tests."""
    mutate(root, handoff.start_task, "s", "storage-tests", "storage-author")
    (root / "src/storage.py").write_text("def release():\n    return None\n")
    finish(root, "storage-tests", ["src/storage.py"], 1)
    packet = mutate(root, handoff.start_task, "s", "cli-tests", "cli-author")
    (root / "tests/cli.py").write_text("# CLI acceptance cases consume the storage interface.\n")
    finish(root, "cli-tests", ["tests/cli.py"], 1)
    pass_checkpoint(root)
    return packet


def prepare_branch(root):
    implemented_branch(root)
    return run_branch_tests(root)


def test_branching_stub_replacement_preserves_completed_test_consumers(project):
    packet = prepare_branch(project)
    assert packet["consumes"] == ["src/storage.py"]
    mutate(project, handoff.start_task, "s", "storage-implementation", "storage-worker")
    (project / "src/storage.py").write_text("def release():\n    return 'released'\n")
    finish(project, "storage-implementation", ["src/storage.py"], 0)
    packet = mutate(project, handoff.start_task, "s", "cli-implementation", "cli-worker")
    assert packet["consumed_files"]["src/storage.py"] == store.load(project, "feature")["task_runs"]["storage-implementation"]["return"]["files"]["src/storage.py"]
    (project / "src/app.py").write_text("from storage import release\n")
    finish(project, "cli-implementation", ["src/app.py"], 0)
    complete_refactor_tasks(project)
    handoff.verify_task_runs(project, store.load(project, "feature"))
    assert store.load(project, "feature")["task_runs"]["cli-tests"]["return"]["verified_checks"][0]["exit_code"] == 1
    (project / "src/storage.py").write_text("def release():\n    return 'external change'\n")
    with pytest.raises(store.WorkflowError, match="[Uu]nexpected interference"):
        handoff.verify_task_runs(project, store.load(project, "feature"))


@pytest.mark.parametrize("consumer_first", [True, False])
def test_unordered_writer_consumer_graph_rejected_before_tasks_start(project, consumer_first):
    tasks = branching(project, creates=("src/storage.py", "tests/cli.py", "tests/shared.py", "tests/consumer.py"))
    writer = task("fixtures", "tests", ["tests/shared.py"])
    reader = task("consumer", "tests", ["tests/consumer.py"], consumes=["tests/shared.py"])
    tasks.extend([reader, writer] if consumer_first else [writer, reader])
    write_tasks(project, tasks)
    [message] = plan_refusals(project)
    assert message is not None and re.search("order|depend", message), message


def test_hook_protects_running_consumer_from_coordinator_write(project):
    implemented_branch(project)
    mutate(project, handoff.start_task, "s", "storage-tests", "storage-author")
    (project / "src/storage.py").write_text("def release():\n    return None\n")
    finish(project, "storage-tests", ["src/storage.py"], 1)
    mutate(project, handoff.start_task, "s", "cli-tests", "cli-author")
    with pytest.raises(store.WorkflowError, match="lead does not edit"):
        handoff.check_task_write(store.load(project, "feature"), "src/storage.py", None, "s")


def test_external_edit_to_running_consumed_input_is_flagged(project):
    implemented_branch(project)
    mutate(project, handoff.start_task, "s", "storage-tests", "storage-author")
    (project / "src/storage.py").write_text("def release():\n    return None\n")
    finish(project, "storage-tests", ["src/storage.py"], 1)
    mutate(project, handoff.start_task, "s", "cli-tests", "cli-author")
    (project / "src/storage.py").write_text("# changed outside Firebreak\n")
    with pytest.raises(store.WorkflowError, match="[Uu]nexpected interference.*refresh"):
        handoff.task_packet(project, store.load(project, "feature"), "cli-tests")


def test_runtime_added_context_cannot_race_a_running_writer(project):
    tasks = branching(project, creates=("src/storage.py", "tests/cli.py", "tests/extra.py"))
    tasks.append(task("independent-tests", "tests", ["tests/extra.py"]))
    write_tasks(project, tasks)
    open_implement(project)
    mutate(project, handoff.start_task, "s", "storage-tests", "storage-author")
    (project / "src/storage.py").write_text("def release():\n    return None\n")
    with pytest.raises(store.WorkflowError, match="writer.*consumer|consumer.*writer"):
        mutate(project, handoff.start_task, "s", "independent-tests", "other-author", input_refs=["src/storage.py"])


def test_running_consumer_detects_added_file_in_consumed_directory(project):
    tasks = branching(project)
    tasks[1]["consumes"] = ["src"]
    write_tasks(project, tasks)
    open_implement(project)
    mutate(project, handoff.start_task, "s", "storage-tests", "storage-author")
    (project / "src/storage.py").write_text("def release():\n    return None\n")
    finish(project, "storage-tests", ["src/storage.py"], 1)
    mutate(project, handoff.start_task, "s", "cli-tests", "cli-author")
    (project / "src/unexpected.py").write_text("# External module added during review\n")
    with pytest.raises(store.WorkflowError, match="[Uu]nexpected interference"):
        handoff.task_packet(project, store.load(project, "feature"), "cli-tests")


def test_ordering_dependency_does_not_freeze_unconsumed_sibling_output(project):
    # Two implementation branches read different outputs of one preparation task.
    branching(project, creates=("src/storage.py", "tests/cli.py", "src/notes.py"))
    tasks_path = project / '.fbk/feature/tasks.json'
    tasks = json.loads(tasks_path.read_text())
    tasks.append(task('notes', 'implementation', ['src/notes.py'], ['storage-tests'], ['tests/check.py']))
    write_tasks(project, tasks)
    open_implement(project)
    run_branch_tests(project)
    mutate(project, handoff.start_task, 's', 'storage-implementation', 'storage-worker')
    (project / 'src/storage.py').write_text("def release():\n    return 'released'\n")
    packet = mutate(project, handoff.start_task, 's', 'notes', 'notes-worker')
    assert set(packet['consumed_files']) == {'tests/check.py'}


def test_plan_rejects_task_that_freezes_its_own_writes(project):
    tasks = branching(project)
    tasks[2]['consumes'].append('src/storage.py')
    write_tasks(project, tasks)
    [message] = plan_refusals(project)
    assert message is not None and re.search('own|read.only', message), message


def test_transitive_dependency_cannot_hide_modified_consumed_output(project):
    branching(project, creates=("src/storage.py", "tests/cli.py", "src/notes.py"))
    path = project / '.fbk/feature/tasks.json'
    tasks = json.loads(path.read_text())
    # notes reaches storage-tests' output only through cli-tests.
    tasks.append(task('notes', 'implementation', ['src/notes.py'], ['cli-tests'], ['src/storage.py']))
    # The later writer of the consumed interface waits for its reader.
    next(t for t in tasks if t['id'] == 'storage-implementation')['depends_on'].append('notes')
    write_tasks(project, tasks)
    open_implement(project)
    run_branch_tests(project)
    # A production output (not a locked test, which would void the checkpoint and stop
    # every implementation task by stage) changes outside any task.
    (project / 'src/storage.py').write_text('# unauthorized replacement of the interface\n')
    with pytest.raises(store.WorkflowError, match='[Uu]nexpected interference'):
        mutate(project, handoff.start_task, 's', 'notes', 'notes-worker')
