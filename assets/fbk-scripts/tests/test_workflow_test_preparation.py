"""Exercise real placeholders and red/green runs across the phase boundary: breakdown
writes tasks only, test tasks run in implement, and the test checkpoint locks."""

import json
import sys

import pytest

from fbk.workflow import close, engine, evidence, handoff, hooks, review, store
from .test_workflow_commands import call
from .test_workflow_lifecycle import (
    accept,
    blocking_review,
    clean_review,
    enter,
    mutate,
    observe_phase,
    pass_checkpoint,
    project as workflow_project,
)
from .refactor_plan import complete_refactor_tasks, with_refactor

project = workflow_project


def setup_plan(root, extra_check=None, creates=("src/cancellation.py",)):
    refs = [".fbk/feature/prd.md", ".fbk/feature/spec.md", ".fbk/feature/spec.md#cancel-once"]
    command = [sys.executable, "tests/check.py"]
    store.atomic_json(
        root / ".fbk/feature/tasks.json",
        with_refactor([
            {
                "id": "behavior-tests",
                "stage": "tests",
                "description": "Prove cancellation is idempotent.",
                "files": ["tests/check.py", "src/cancellation.py"],
                "acceptance_refs": refs,
                "verification": "Two calls must return true then false; a constant result fails.",
                "check_expectations": [{"argv": command, "exit_code": 1}],
                "depends_on": [],
            },
            {
                "id": "cancel",
                "stage": "implementation",
                "description": "Implement idempotent cancellation.",
                "files": ["src/cancellation.py"],
                "acceptance_refs": refs,
                "input_refs": refs + ["tests/check.py"],
                "verification": "The cancellation behavior check passes unchanged.",
                "check_expectations": [{"argv": [sys.executable, "tests/check.py"], "exit_code": 0}],
                "depends_on": ["behavior-tests"],
            },
        ]),
    )
    if extra_check:
        scope_path = root / ".fbk/feature/scope.json"
        scope = json.loads(scope_path.read_text())
        scope["checks"].append(extra_check)
        store.atomic_json(scope_path, scope)
        tasks_path = root / ".fbk/feature/tasks.json"
        tasks = json.loads(tasks_path.read_text())
        tasks[0]["check_expectations"].append({"argv": extra_check, "exit_code": 0})
        store.atomic_json(tasks_path, tasks)
    # The spec declares the paths the plan's tasks create.
    scope_path = root / ".fbk/feature/scope.json"
    store.atomic_json(scope_path, {**json.loads(scope_path.read_text()), "creates": list(creates)})
    accept(root, "intent")
    accept(root, "spec")
    enter(root, "breakdown")
    return command


def write_preparation(root):
    (root / "src/cancellation.py").write_text(
        "def cancel(resource):\n    return None\n"
    )
    (root / "tests/check.py").write_text(
        "import sys\nfrom pathlib import Path\nsys.path.insert(0, str(Path.cwd() / 'src'))\n"
        "from cancellation import cancel\nresource = {}\n"
        "assert cancel(resource) is True, 'first cancellation must release'\n"
        "assert cancel(resource) is False, 'repeated cancellation must do nothing'\n"
    )


def write_permission(root, path, worker=None):
    return hooks.handle(
        root,
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "session_id": "s",
            "agent_id": worker,
            "tool_input": {"file_path": str(root / path)},
        },
    )


def implement_plan(root, **kwargs):
    """setup_plan, then a plan-only breakdown close and implement entry: writing tests."""
    command = setup_plan(root, **kwargs)
    close.close_phase(root, "feature", "breakdown", "s", reviewer=clean_review)
    observe_phase(root, "breakdown")
    mutate(root, engine.approve, "s", "start-implementation", "implement", "Proceed.")
    enter(root, "implement")
    return command


def finish_behavior_tests(root, command, changed=("src/cancellation.py", "tests/check.py")):
    result = review.run_command(command, root, 10)
    returned = mutate(
        root, handoff.finish_task, "s", "behavior-tests",
        changed_files=list(changed),
        checks=[{"argv": command, "exit_code": result["exit_code"], "evidence": result["stderr"] or "ran"}],
        unresolved=[], outcome="Imports succeed; cancellation is missing.",
    )
    return result, returned


def test_red_tests_written_in_implement_lock_at_the_checkpoint_and_code_goes_green(project):
    command = setup_plan(project)
    # Breakdown writes tasks only: it closes with no test written, run, or locked.
    close.close_phase(project, "feature", "breakdown", "s", reviewer=clean_review)
    observe_phase(project, "breakdown")
    assert not store.load(project, "feature")["locks"]
    mutate(project, engine.approve, "s", "start-implementation", "implement", "Proceed.")
    enter(project, "implement")
    packet = mutate(project, handoff.start_task, "s", "behavior-tests", "test-author")
    assert packet["stage"] == "tests"
    assert packet["check_expectations"] == [{"argv": command, "exit_code": 1}]
    assert ".fbk/feature/prd.md" in packet["acceptance_refs"]
    assert write_permission(project, "src/cancellation.py", "test-author") == {}
    write_preparation(project)
    result, returned = finish_behavior_tests(project, command)
    assert result["exit_code"] == 1
    assert "first cancellation must release" in result["stderr"]
    assert returned["status"] == "completed"
    assert not store.load(project, "feature")["locks"]
    pass_checkpoint(project)
    assert store.load(project, "feature")["locks"] == evidence.file_hashes(
        project, ["tests/check.py"]
    )
    mutate(project, handoff.start_task, "s", "cancel", "implementer")
    denied = write_permission(project, "tests/check.py", "implementer")
    assert denied["hookSpecificOutput"]["permissionDecision"] == "deny"
    (project / "src/cancellation.py").write_text(
        "def cancel(resource):\n    if resource.get('released'):\n        return False\n"
        "    resource['released'] = True\n    return True\n"
    )
    assert review.run_command(command, project, 10)["exit_code"] == 0
    mutate(
        project,
        handoff.finish_task,
        "s",
        "cancel",
        changed_files=["src/cancellation.py"],
        checks=[
            {
                "argv": command,
                "exit_code": 0,
                "evidence": "Both cancellation assertions pass.",
            }
        ],
        unresolved=[],
        outcome="Idempotent cancellation delivered.",
    )
    complete_refactor_tasks(project)
    result = close.close_phase(
        project, "feature", "implement", "s", reviewer=clean_review
    )
    assert result["status"] == "retrospective-required"
    observe_phase(project, "implement")
    assert engine.status_report(project, store.load(project, "feature"))["status"] == "closed"


@pytest.mark.parametrize("exit_code", [0, 2])
def test_test_task_requires_its_declared_red_outcome(project, exit_code):
    command = implement_plan(project)
    mutate(project, handoff.start_task, "s", "behavior-tests", "worker")
    returned = mutate(
        project,
        handoff.finish_task,
        "s",
        "behavior-tests",
        changed_files=[],
        checks=[
            {
                "argv": command,
                "exit_code": exit_code,
                "evidence": "Unexpected pass or collection error.",
            }
        ],
        unresolved=[],
        outcome="Preparation is incomplete.",
    )
    assert returned["status"] == "needs-attention"


def test_breakdown_writes_no_source_and_launches_no_task(project):
    setup_plan(project)
    result = write_permission(project, "src/app.py")
    assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
    for task in ("cancel", "behavior-tests"):
        with pytest.raises(store.WorkflowError, match="implement"):
            mutate(project, handoff.start_task, "s", task, "worker")
    assert not store.load(project, "feature").get("task_runs")


def test_breakdown_review_failure_does_not_advance_or_lock(project):
    setup_plan(project)
    with pytest.raises(store.WorkflowError, match="blocking defects"):
        close.close_phase(
            project, "feature", "breakdown", "s", reviewer=blocking_review
        )
    record = store.load(project, "feature")
    assert not record["locks"]
    assert record["open_phase"] == "breakdown"


def test_breakdown_review_reads_the_plan_not_tests_placeholders_or_red_output(
    project, monkeypatch
):
    setup_plan(project)
    # Files a test author would write exist on disk, but breakdown does not review them.
    write_preparation(project)
    seen = []

    def reader(root, prompt, config):
        packet = json.loads(prompt.split("\n", 1)[1])
        required = set(config["_review_required_files"])
        assert {".fbk/feature/tasks.json", ".fbk/feature/prd.md", ".fbk/feature/spec.md"} <= required
        assert not {"tests/check.py", "src/cancellation.py"} & required, required
        assert packet["required_files"]["phase_targets"] == [".fbk/feature/tasks.json"]
        assert not (packet.get("test_discipline") or {}).get("red_check"), packet.get("test_discipline")
        seen.append(required)
        return {"review": clean_review()["review"], "context": {"supporting_files": []}}

    monkeypatch.setattr(review, "claude_review", reader)
    close.close_phase(project, "feature", "breakdown", "s")
    assert len(seen) == 1
    assert not store.load(project, "feature")["locks"]


def test_a_contract_change_while_checkpoint_checks_run_is_not_accepted(
    project, monkeypatch
):
    command = implement_plan(project)
    mutate(project, handoff.start_task, "s", "behavior-tests", "test-author")
    write_preparation(project)
    finish_behavior_tests(project, command)
    execute = review.run_command

    def changing_check(*args, **kwargs):
        result = execute(*args, **kwargs)
        (project / ".fbk/feature/spec.md").write_text(
            "The contract changed during execution."
        )
        return result

    monkeypatch.setattr(review, "run_command", changing_check)
    with pytest.raises(store.WorkflowError):
        pass_checkpoint(project)
    record = store.load(project, "feature")
    assert not record["locks"]
    assert not record["phases"]["test-checkpoint"]["evidence"]


def test_preservation_at_the_checkpoint_must_actually_pass_declared_regressions(project):
    extra = [sys.executable, "tests/check_imports.py"]
    (project / "tests/check_imports.py").write_text("raise RuntimeError('regression')\n")
    # The behavior is already built before the unit starts, so the test task's own check passes.
    built = ("def cancel(resource):\n    if resource.get('released'):\n        return False\n"
             "    resource['released'] = True\n    return True\n")
    (project / "src/cancellation.py").write_text(built)
    command = setup_plan(project, extra_check=extra, creates=())
    edit_task(project, "behavior-tests", check_expectations=[{"argv": command, "exit_code": 0}],
              verification="The existing cancellation behavior keeps passing.")
    close.close_phase(project, "feature", "breakdown", "s", reviewer=clean_review)
    observe_phase(project, "breakdown")
    mutate(project, engine.approve, "s", "start-implementation", "implement", "Proceed.")
    enter(project, "implement")
    mutate(project, handoff.start_task, "s", "behavior-tests", "test-author")
    write_preparation(project)
    (project / "src/cancellation.py").write_text(built)
    result, returned = finish_behavior_tests(project, command, changed=("tests/check.py",))
    assert result["exit_code"] == 0 and returned["status"] == "completed", returned
    with pytest.raises(store.WorkflowError, match="regression checks to pass"):
        pass_checkpoint(project)
    assert not store.load(project, "feature")["locks"]


def test_colocated_tests_are_not_production_sources(project):
    # Guard: the checkpoint's production comparison leaves colocated tests out.
    from fbk.workflow import test_preparation

    setup_plan(project)
    scope_path = project / ".fbk/feature/scope.json"
    scope = json.loads(scope_path.read_text())
    scope["tests"] = ["src/test_*.py"]
    store.atomic_json(scope_path, scope)
    (project / "src/test_app.py").write_text("old test")
    record = store.load(project, "feature")
    before = test_preparation.source_files(project, record)
    assert "src/test_app.py" not in before and "src/app.py" in before
    (project / "src/test_app.py").write_text("updated test")
    assert test_preparation.source_files(project, record) == before
    (project / "src/app.py").write_text("changed implementation")
    assert test_preparation.source_files(project, record) != before


def test_new_unlocked_test_blocks_further_production_writes(project):
    from .test_workflow_lifecycle import prepare_implementation

    prepare_implementation(project)
    (project / "tests/new_regression.py").write_text("assert False\n")
    result = write_permission(project, "src/app.py")
    assert result["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_resume_can_reconstruct_the_implement_stage_and_tests(project):
    command = implement_plan(project)
    mutate(project, handoff.start_task, "s", "behavior-tests", "test-author")
    write_preparation(project)
    finish_behavior_tests(project, command)
    mutate(project, engine.suspend, "s", "Ready for the test checkpoint.")
    packet = handoff.continuation(project, store.load(project, "feature"))
    assert packet["test_preparation"]["stage"] == "ready-for-checkpoint"
    assert "tests/check.py" in packet["sources"]
    assert packet["tasks"][0]["verification"]


def test_partial_task_plan_does_not_break_status(project):
    setup_plan(project)
    store.atomic_json(project / ".fbk/feature/tasks.json", {"draft": True})
    status = engine.status_report(project, store.load(project, "feature"))
    assert status["phase"] == "breakdown"


def test_reopened_breakdown_replaces_obsolete_assignments_but_retains_their_evidence(
    project,
):
    from .test_workflow_lifecycle import prepare_implementation

    prepare_implementation(project)
    mutate(project, handoff.start_task, "s", "cancel", "worker")
    mutate(
        project,
        handoff.finish_task,
        "s",
        "cancel",
        changed_files=[],
        checks=[
            {
                "argv": ["inspect"],
                "exit_code": 0,
                "evidence": "Existing interface inspected.",
            }
        ],
        unresolved=[],
        outcome="Existing implementation inspected.",
    )
    mutate(
        project, engine.approve, "s", "reopen", "breakdown", "Revise the assignments."
    )
    mutate(project, engine.reopen, "breakdown", "s", "Revise the assignments.")
    enter(project, "breakdown")
    record = store.load(project, "feature")
    assert not record["task_runs"]
    assert any(
        e["event"] == "task-returned" and e["task"] == "cancel"
        for e in record["events"]
    )
    assert not record["locks"]


def edit_task(root, task_id, **fields):
    path = root / ".fbk/feature/tasks.json"
    tasks = store.read_json(path)
    task = next(task for task in tasks if task["id"] == task_id)
    task.update(fields)
    store.atomic_json(path, tasks)


def test_unrelated_task_edit_leaves_a_started_assignment_valid(project):
    """Assignment validity binds the task's own plan entry and its related entries, not the whole file."""
    command = implement_plan(project)
    mutate(project, handoff.start_task, "s", "behavior-tests", "test-author")
    # The implementation task neither depends on nor supplies the test task; its check is irrelevant to it.
    edit_task(project, "cancel", check_expectations=[
        {"argv": [sys.executable, "tests/check.py", "--verbose"], "exit_code": 0}])
    record = store.load(project, "feature")
    # The unstarted implementation task is reported too; only the test task's entry matters here.
    assert [b for b in handoff.task_run_blockers(project, record) if b["task"] not in ("cancel", "refactor")] == [
        {"task": "behavior-tests",
         "reason": "Finish assigned tasks and resolve their handoffs before closing.",
         "next": "Finish the current task and submit task-finish with its required checks."}
    ]
    write_preparation(project)
    _, returned = finish_behavior_tests(project, command)
    assert returned["status"] == "completed"


def test_own_task_edit_invalidates_the_assignment(project):
    implement_plan(project)
    mutate(project, handoff.start_task, "s", "behavior-tests", "test-author")
    edit_task(project, "behavior-tests", verification="A constant result must fail; so must a raised error.")
    blockers = handoff.task_run_blockers(project, store.load(project, "feature"))
    assert [b["reason"] for b in blockers if b["task"] not in ("cancel", "refactor")] == [
        "Task inputs changed; launch the task again against the current accepted breakdown."
    ]


def test_dependency_task_edit_invalidates_the_dependent_assignment(project):
    refs = [".fbk/feature/prd.md", ".fbk/feature/spec.md", ".fbk/feature/spec.md#cancel-once"]
    command = [sys.executable, "tests/check.py"]
    # The plan is complete before breakdown closes: a fixture task the behavior tests consume.
    def plan_with_fixture(root):
        tasks = store.read_json(root / ".fbk/feature/tasks.json")
        tasks.insert(0, {
            "id": "fixtures", "stage": "tests",
            "description": "Provide the shared cancellation fixture.",
            "files": ["tests/fixtures.py"], "depends_on": [], "acceptance_refs": refs,
            "verification": "The fixture module exists; the behavior check still fails without cancellation.",
            "check_expectations": [{"argv": command, "exit_code": 1}],
        })
        tasks[1]["depends_on"] = ["fixtures"]
        tasks[1]["consumes"] = ["tests/fixtures.py"]
        store.atomic_json(root / ".fbk/feature/tasks.json", tasks)

    setup_plan(project, creates=("src/cancellation.py", "tests/fixtures.py"))
    plan_with_fixture(project)
    close.close_phase(project, "feature", "breakdown", "s", reviewer=clean_review)
    observe_phase(project, "breakdown")
    mutate(project, engine.approve, "s", "start-implementation", "implement", "Proceed.")
    enter(project, "implement")
    mutate(project, handoff.start_task, "s", "fixtures", "fixture-author")
    (project / "tests/fixtures.py").write_text("resource = {}\n")
    result = review.run_command(command, project, 10)
    returned = mutate(
        project, handoff.finish_task, "s", "fixtures", changed_files=["tests/fixtures.py"],
        checks=[{"argv": command, "exit_code": 1, "evidence": result["stderr"]}],
        unresolved=[], outcome="Fixture provided.",
    )
    assert returned["status"] == "completed"
    mutate(project, handoff.start_task, "s", "behavior-tests", "test-author")
    edit_task(project, "fixtures", description="Provide a different shared fixture shape.")
    blockers = [b for b in handoff.task_run_blockers(project, store.load(project, "feature"))
                if b["task"] not in ("cancel", "refactor")]
    assert {b["task"] for b in blockers} == {"fixtures", "behavior-tests"}
    assert all(b["reason"].startswith("Task inputs changed") for b in blockers)


def test_a_task_carrying_stubs_is_refused_with_the_files_and_creates_remedy(project):
    setup_plan(project)
    edit_task(project, "behavior-tests", stubs=["src/cancellation.py"])
    with pytest.raises(store.WorkflowError) as raised:
        close.close_phase(project, "feature", "breakdown", "s", reviewer=clean_review)
    message = str(raised.value)
    assert "behavior-tests" in message and "stubs" in message, message
    assert "files" in message and "creates" in message, message
    assert not store.load(project, "feature")["phases"]["breakdown"]["evidence"]


def test_changed_files_rejection_names_its_snapshot_window(project):
    implement_plan(project)
    (project / "tests/check.py").write_text("edited before the assignment was launched\n")
    mutate(project, handoff.start_task, "s", "behavior-tests", "test-author")
    started_at = store.load(project, "feature")["task_runs"]["behavior-tests"]["started_at"]
    (project / "src/cancellation.py").write_text("def cancel(resource):\n    return None\n")
    with pytest.raises(store.WorkflowError) as raised:
        mutate(
            project, handoff.finish_task, "s", "behavior-tests", changed_files=["tests/check.py"],
            checks=[{"argv": ["true"], "exit_code": 0, "evidence": "n/a"}],
            unresolved=[], outcome="Declared the pre-launch edit.",
        )
    message = str(raised.value)
    assert f"task-start snapshot taken at {started_at}" in message
    assert "Declared but unchanged since that snapshot: tests/check.py." in message
    assert "Changed since that snapshot but not declared: src/cancellation.py." in message
    assert "Edits made before task-start" in message
