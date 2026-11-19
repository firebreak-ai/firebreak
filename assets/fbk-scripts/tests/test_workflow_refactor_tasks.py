"""Refactor tasks: an implementation task marked ``"refactor": true`` restructures code earlier
implementation tasks built, under the locked tests.

Breakdown close refuses a plan unless every path an implementation task owns is also owned by a
refactor task depending on it, by the same path or a folder holding it. A refactor task's links
do not count toward the rule that an implementation task links every requirement. Its packet
carries the refactor method, it may create files inside a folder it owns, and the implementation
review receives its returned review.
"""

import sys

import pytest

from fbk.workflow import close, handoff, review, store
from tests import test_workflow_lifecycle as scenarios
from tests.test_workflow_constraints import complete_context, stage_of
from tests.test_workflow_managed_investigations import host
from tests.test_workflow_traceability import refused

from .refactor_plan import complete_refactor_tasks

UNIT = "feature"
TASKS = f".fbk/{UNIT}/tasks.json"
METHOD_LINE = "Judge the code against the four rules of simple design, in priority order:"


@pytest.fixture
def project(tmp_path):
    return scenarios.project.__wrapped__(tmp_path)


def edit_plan(root, change):
    tasks = store.read_json(root / TASKS)
    change({t["id"]: t for t in tasks}, tasks)
    store.atomic_json(root / TASKS, tasks)


def breakdown_refusal(root):
    scenarios.accept(root, "intent")
    scenarios.accept(root, "spec")
    return refused(root, "breakdown")


def test_plan_without_a_refactor_task_is_refused_naming_each_uncovered_path(project):
    edit_plan(project, lambda by_id, tasks: tasks.remove(by_id["refactor"]))
    message = breakdown_refusal(project)
    assert "refactor task" in message and "Task cancel: src/app.py" in message, message


def test_refactor_task_that_does_not_depend_on_the_builder_leaves_its_path_uncovered(project):
    def change(by_id, tasks):
        by_id["refactor"]["depends_on"] = []
    edit_plan(project, change)
    assert "Task cancel: src/app.py" in breakdown_refusal(project)


def test_refactor_task_owning_the_folder_covers_the_path_and_may_create_files_there(project):
    """A folder covers the paths inside it, and a boundary trial may add a file to that folder
    without the spec declaring it."""
    def change(by_id, tasks):
        by_id["refactor"]["files"] = ["src"]
    edit_plan(project, change)
    scenarios.prepare_implementation(project)
    (project / "src/app.py").write_text("release()")
    scenarios.complete_declared_implementation_task(project)
    scenarios.mutate(project, handoff.start_task, "s", "refactor", "refactor-worker")
    (project / "src/policy.py").write_text("RELEASE = 'release()'\n")
    task = next(t for t in store.read_json(project / TASKS) if t["id"] == "refactor")
    checks = [review.run_command(item["argv"], project, 10) for item in task["check_expectations"]]
    result = handoff.complete_task(
        project, UNIT, "s", "refactor", changed_files=["src/policy.py"],
        checks=[{**c, "evidence": "The refactor task's check ran."} for c in checks],
        unresolved=[], outcome="Extracted the release policy into src/policy.py.")
    assert result["status"] == "completed", result


@pytest.mark.parametrize("stage, value", [("tests", True), ("implementation", "yes")])
def test_refactor_marker_only_true_and_only_on_an_implementation_task(project, stage, value):
    def change(by_id, tasks):
        target = by_id["prepare-tests"] if stage == "tests" else by_id["refactor"]
        target["refactor"] = value
    edit_plan(project, change)
    message = breakdown_refusal(project)
    assert "sets refactor" in message, message


def test_requirement_linked_only_by_a_refactor_task_still_needs_an_implementation_task(project):
    spec = project / f".fbk/{UNIT}/spec.md"
    spec.write_text(spec.read_text() + (
        "\n### Cancel logging\n\nCancel logs each cancellation once. "
        "Serves [Release on cancel](prd.md#release-on-cancel).\n"))
    logging = f".fbk/{UNIT}/spec.md#cancel-logging"

    def change(by_id, tasks):
        by_id["prepare-tests"]["acceptance_refs"].append(logging)
        by_id["refactor"]["acceptance_refs"].append(logging)
    edit_plan(project, change)
    message = breakdown_refusal(project)
    assert 'requirement "Cancel logging": no implementation task links it' in message, message


def test_refactor_packet_carries_the_method_and_a_builder_packet_does_not(project):
    scenarios.prepare_implementation(project)
    builder = scenarios.mutate(project, handoff.start_task, "s", "cancel", "cancel-worker")
    assert "refactor_guidance" not in builder
    (project / "src/app.py").write_text("release()")
    task = next(t for t in store.read_json(project / TASKS) if t["id"] == "cancel")
    checks = [review.run_command(item["argv"], project, 10) for item in task["check_expectations"]]
    handoff.complete_task(project, UNIT, "s", "cancel", changed_files=["src/app.py"],
                          checks=[{**c, "evidence": "ran"} for c in checks], unresolved=[],
                          outcome="Cancellation releases once.")
    packet = scenarios.mutate(project, handoff.start_task, "s", "refactor", "refactor-worker")
    assert packet["refactor"] is True
    assert METHOD_LINE in packet["refactor_guidance"]
    # It links no requirement; the worker reads the accepted spec whole.
    assert not [r for r in packet["acceptance_refs"] if "#" in r]
    assert packet["rules_sources"] == [f".fbk/{UNIT}/spec.md"]
    assert "review" in packet["return_contract"]


def test_implementation_review_receives_each_refactor_review(project, monkeypatch):
    prompts = []

    def reviewer(argv, cwd, timeout, prompt=None, **kwargs):
        if argv[:1] != ["claude"]:
            return real(argv, cwd, timeout, prompt, **kwargs)
        stage_of(argv)
        prompts.append(prompt)
        return host({"summary": "Inspected the delivered code.", "findings": [],
                     "context": complete_context(cwd)})

    real = review.run_command
    scenarios.prepare_implementation(project)
    (project / "src/app.py").write_text("release()")
    scenarios.complete_declared_implementation_task(project)
    monkeypatch.setattr(review, "run_command", reviewer)
    close.close_phase(project, UNIT, "implement", "s")
    assert prompts, "No implementation reviewer launched."
    assert '"refactor_reviews"' in prompts[0]
    assert "No improvement: the code is one cohesive decision." in prompts[0]
