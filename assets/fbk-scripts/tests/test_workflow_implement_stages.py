"""Implement derives its stage from recorded facts; task start, the write hook,
plan validation, and continuation follow that stage.

Breakdown writes tasks only, so a unit enters implement writing tests with no
locks; ``prepare_implementation`` runs the test tasks and passes the test
checkpoint, which is the only route to writing code.
"""

import json
import sys

import pytest

from fbk.workflow import close, engine, evidence, handoff, review, store
from .test_workflow_commands import call
from .test_workflow_lifecycle import (
    accept,
    approve_unlock,
    clean_review,
    enter,
    enter_implementation,
    mutate,
    observe_phase,
    pass_checkpoint,
    run_test_tasks,
    prepare_implementation,
    project as workflow_project,
)
from .test_workflow_test_preparation import write_permission
from .refactor_plan import REFACTOR_ID, with_refactor

project = workflow_project

REFS = [".fbk/feature/prd.md", ".fbk/feature/spec.md", ".fbk/feature/spec.md#cancel-once"]
CHECK = [sys.executable, "tests/check.py"]


def refusal(fn, *args, **kwargs):
    """The refusal message, or None when the action is accepted."""
    try:
        fn(*args, **kwargs)
    except store.WorkflowError as exc:
        return str(exc)
    return None


def denied(result):
    return result.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


def edit_tasks(root, change):
    path = root / ".fbk/feature/tasks.json"
    tasks = store.read_json(path)
    change({task["id"]: task for task in tasks}, tasks)
    # The fixture's covering refactor task follows the implementation tasks' new files.
    store.atomic_json(path, with_refactor([task for task in tasks if task["id"] != REFACTOR_ID]))


def edit_scope(root, **fields):
    path = root / ".fbk/feature/scope.json"
    scope = store.read_json(path)
    scope.update(fields)
    store.atomic_json(path, scope)


def stage(root):
    return engine.implement_stage(root, store.load(root, "feature"))


def unlock(root):
    """Unlock tests/check.py; its corrected form still fails on the missing release."""
    approve_unlock(root, {"tests/check.py": "fail"}, [{"argv": CHECK, "tests": ["tests/check.py"]}],
                   reason="The cancellation test asserts the wrong call.")


def start(root, task, worker):
    return refusal(mutate, root, handoff.start_task, "s", task, worker)


def run_test_task(root, task, worker):
    """Launch and finish a test task through the real handoff; nothing is edited."""
    assert start(root, task, worker) is None, f"{task} should start in writing tests"
    result = review.run_command(CHECK, root, 10)
    assert result["exit_code"] == 1
    returned = mutate(root, handoff.finish_task, "s", task, changed_files=[],
                      checks=[{"argv": CHECK, "exit_code": 1, "evidence": result["stderr"]}],
                      unresolved=[], outcome="Cancellation release is still missing.")
    assert returned["status"] == "completed"


def accept_breakdown_and_approve(root):
    for phase in ("intent", "spec", "breakdown"):
        accept(root, phase)
    mutate(root, engine.approve, "s", "start-implementation", "implement",
           "Implement the agreed spec.")


def add_second_test_task(root):
    # The new test file does not exist yet, so the spec declares it.
    edit_scope(root, creates=["tests/release_check.py"])
    edit_tasks(root, lambda by_id, tasks: tasks.insert(1, {
        "id": "release-tests", "stage": "tests",
        "description": "Check release happens exactly once.",
        "files": ["tests/release_check.py"], "depends_on": [],
        "acceptance_refs": REFS,
        "verification": "A double release fails the check.",
        "check_expectations": [{"argv": CHECK, "exit_code": 1}],
    }))


def task_status(root, task):
    packet = handoff.continuation(root, store.load(root, "feature"))
    return next(view["status"] for view in packet["tasks"] if view["task"] == task)


# Derived stage


def test_only_the_checkpoint_moves_a_plan_only_unit_into_writing_code(project):
    # Breakdown writes tasks only: implement opens writing tests with no locks, the test
    # tasks run there, and the checkpoint's pass is what lets code be written.
    enter_implementation(project)
    assert not store.load(project, "feature")["locks"]
    assert stage(project) == "writing-tests"
    run_test_task(project, "prepare-tests", "test-author")
    assert stage(project) == "ready-for-checkpoint"
    assert start(project, "cancel", "implementer") is not None
    pass_checkpoint(project)
    assert stage(project) == "writing-code"
    assert start(project, "cancel", "implementer") is None


def test_outstanding_unlock_returns_the_unit_to_writing_tests(project):
    prepare_implementation(project)
    unlock(project)
    assert store.load(project, "feature")["locks"]
    assert stage(project) == "writing-tests"


def test_every_declared_test_task_must_complete_before_checkpoint(project):
    add_second_test_task(project)
    enter_implementation(project)
    assert stage(project) == "writing-tests"
    run_test_task(project, "prepare-tests", "test-author")
    # Every recorded run is complete, but release-tests never started.
    assert set(store.load(project, "feature")["task_runs"]) == {"prepare-tests"}
    assert stage(project) == "writing-tests"
    run_test_task(project, "release-tests", "release-author")
    assert stage(project) == "ready-for-checkpoint"


def test_relaunched_test_task_returns_the_unit_to_writing_tests(project):
    enter_implementation(project)
    run_test_task(project, "prepare-tests", "test-author")
    assert stage(project) == "ready-for-checkpoint"
    assert start(project, "prepare-tests", "rework-author") is None
    assert stage(project) == "writing-tests"


def test_a_completed_test_task_whose_output_changed_is_not_current(project):
    enter_implementation(project)
    run_test_task(project, "prepare-tests", "test-author")
    assert stage(project) == "ready-for-checkpoint"
    # The recorded output changes with no relaunch: the completed run is no longer current.
    (project / "tests/check.py").write_text("assert False, 'edited after completion'\n")
    assert stage(project) == "writing-tests"


# Implement entry


def test_implement_entry_needs_no_locks_but_implementation_close_does(project):
    accept_breakdown_and_approve(project)
    assert refusal(enter, project, "implement") is None
    assert store.load(project, "feature")["open_phase"] == "implement"
    assert stage(project) == "writing-tests"
    with pytest.raises(store.WorkflowError, match="must be locked|checkpoint"):
        close.close_phase(project, "feature", "implement", "s", reviewer=clean_review)


# Task start


def test_task_start_follows_the_stage_not_the_locks(project):
    prepare_implementation(project)
    assert start(project, "prepare-tests", "test-author") is not None
    unlock(project)
    # Locks still exist; only the outstanding unlock moves the stage.
    assert start(project, "cancel", "implementer") is not None
    assert start(project, "prepare-tests", "test-author") is None


@pytest.mark.parametrize("route", ["no-locks", "ready-for-checkpoint"])
def test_implementation_task_waits_for_writing_code(project, route):
    enter_implementation(project)
    if route == "ready-for-checkpoint":
        run_test_task(project, "prepare-tests", "test-author")
        assert stage(project) == "ready-for-checkpoint"
    assert start(project, "cancel", "implementer") is not None


# Write hook


def declare_production_file_on_test_task(root):
    edit_tasks(root, lambda by_id, tasks: by_id["prepare-tests"].update(
        files=["tests/check.py", "src/app.py"]))


def enter_writing_tests(root, route):
    """Writing tests on a first pass (no locks) or after an unlock of a checkpoint lock."""
    if route == "no-locks":
        enter_implementation(root)
    else:
        prepare_implementation(root)
        unlock(root)
    assert stage(root) == "writing-tests"


@pytest.mark.parametrize("route", ["no-locks", "unlock"])
def test_writing_tests_worker_writes_its_declared_test_and_production_files(project, route):
    declare_production_file_on_test_task(project)
    accept(project, "intent")
    accept(project, "spec")
    assert refusal(accept, project, "breakdown") is None, (
        "plan validation should accept a test task's declared production file")
    mutate(project, engine.approve, "s", "start-implementation", "implement", "Proceed.")
    enter(project, "implement")
    if route == "unlock":
        run_test_tasks(project)
        pass_checkpoint(project)
        unlock(project)
    assert start(project, "prepare-tests", "test-author") is None
    assert write_permission(project, "tests/check.py", "test-author") == {}
    assert write_permission(project, "src/app.py", "test-author") == {}
    assert denied(write_permission(project, "src/other.py", "test-author"))


@pytest.mark.parametrize("route", ["no-locks", "unlock"])
def test_test_task_changes_a_declared_production_file_and_finishes(project, route):
    declare_production_file_on_test_task(project)
    enter_writing_tests(project, route)
    assert start(project, "prepare-tests", "test-author") is None
    # The smallest interface change plus the test that calls it, written by the worker.
    assert write_permission(project, "src/app.py", "test-author") == {}
    (project / "src/app.py").write_text("def release():\n    pass\n")
    assert write_permission(project, "tests/check.py", "test-author") == {}
    (project / "tests/check.py").write_text(
        "import sys\nsys.path.insert(0, 'src')\nimport app\napp.release()\n"
        "from pathlib import Path\nassert Path('src/app.py').read_text() == 'release()'\n")
    result = review.run_command(CHECK, project, 10)
    assert result["exit_code"] == 1 and "AssertionError" in result["stderr"]
    returned = handoff.complete_task(
        project, "feature", "s", "prepare-tests",
        changed_files=["src/app.py", "tests/check.py"],
        checks=[{"argv": CHECK, "exit_code": 1, "evidence": result["stderr"]}],
        unresolved=[], outcome="release() exists and does nothing; the check fails on it.")
    assert returned["status"] == "completed", returned
    assert returned["verified_checks"][0]["exit_code"] == 1
    # The unlocked test is reworked by its test task, so the checkpoint can run again
    # (until step 4b adds the approval's scoped rework commands).
    assert stage(project) == "ready-for-checkpoint"


def test_breakdown_starts_no_task_so_no_worker_writes_tests_or_source(project):
    # The production-file allowance is used in implement; breakdown runs no task at all.
    declare_production_file_on_test_task(project)
    accept(project, "intent")
    accept(project, "spec")
    enter(project, "breakdown")
    message = start(project, "prepare-tests", "test-author")
    assert message is not None and "implement" in message, message
    assert not store.load(project, "feature").get("task_runs")
    assert denied(write_permission(project, "src/app.py", "test-author"))
    assert denied(write_permission(project, "tests/check.py", "test-author"))


def test_writing_code_refuses_every_scoped_test_path(project):
    # No route leaves a test worker running into writing code (the checkpoint needs a
    # quiet tree), so the state is set by hand: a test worker that owns the whole test
    # folder is still running when the checkpoint's acceptance and locks stand.
    edit_tasks(project, lambda by_id, tasks: by_id["prepare-tests"].update(files=["tests"]))
    prepare_implementation(project)
    accepted = store.load(project, "feature")["phases"]["test-checkpoint"]["evidence"]
    unlock(project)
    assert start(project, "prepare-tests", "test-author") is None
    with store.transaction(project):
        record = store.load(project, "feature")
        record["unlocks"] = []
        record["phases"]["test-checkpoint"]["evidence"] = accepted
        store.save(project, record)
    assert stage(project) == "writing-code"
    assert denied(write_permission(project, "tests/new_check.py", "test-author"))
    assert denied(write_permission(project, "tests/check.py", "test-author"))


def test_running_implementation_worker_keeps_its_ownership_during_an_unlock(project):
    prepare_implementation(project)
    assert start(project, "cancel", "implementer") is None
    unlock(project)
    assert write_permission(project, "src/app.py", "implementer") == {}
    assert denied(write_permission(project, "tests/check.py", "implementer"))


def test_partial_unlock_lets_a_test_worker_edit_only_the_unlocked_test(project):
    (project / "tests/other_check.py").write_text("assert True\n")
    edit_tasks(project, lambda by_id, tasks: by_id["prepare-tests"].update(
        files=["tests/check.py", "tests/other_check.py"]))
    prepare_implementation(project)
    assert {"tests/check.py", "tests/other_check.py"} <= set(store.load(project, "feature")["locks"])
    unlock(project)  # unlocks tests/check.py only
    assert start(project, "prepare-tests", "test-author") is None
    assert write_permission(project, "tests/check.py", "test-author") == {}
    assert denied(write_permission(project, "tests/other_check.py", "test-author"))


# Plan validation


def plan_with_implementation_files(root, files, creates=(), sources=("src", "pkg", "lib"),
                                   tests=("tests", "pkg/**/*_test.go", "src/test_*.py")):
    edit_scope(root, sources=list(sources), tests=list(tests),
               **({"creates": list(creates)} if creates else {}))
    edit_tasks(root, lambda by_id, tasks: by_id["cancel"].update(files=files))
    accept(root, "intent")
    message = refusal(accept, root, "spec")
    assert message is None, f"spec close should accept the declared scope: {message}"
    enter(root, "breakdown")


def close_breakdown(root):
    return close.close_phase(root, "feature", "breakdown", "s", reviewer=clean_review)


def plan_refusals(root):
    """Plan validation's message through breakdown close, the one route that validates
    the whole plan now that breakdown starts no task."""
    return [refusal(close_breakdown, root)]


@pytest.mark.parametrize("files, creates", [
    (["pkg/**"], []),
    (["pkg"], ["pkg/"]),
    (["pkg/sub/*.go"], []),
    (["src/*.py"], []),
    (["tests/check.py"], []),
    (["tests/new_check.py"], ["tests/new_check.py"]),
    # A declared new directory is a directory even when its name has a dot.
    (["pkg/v1.2"], ["pkg/", "pkg/v1.2/"]),
    (["pkg/v1.2/"], ["pkg/", "pkg/v1.2/"]),
])
def test_plan_rejects_an_implementation_task_owning_a_scoped_test(project, files, creates):
    plan_with_implementation_files(project, files, creates)
    for message in plan_refusals(project):
        assert message is not None and "cancel" in message, (files, message)


@pytest.mark.parametrize("files, creates", [
    (["pkg/foo.go"], ["pkg/", "pkg/foo.go"]),
    (["src/app.py"], []),
    (["src/app_*.py"], []),
    (["lib"], ["lib/"]),
])
def test_plan_accepts_implementation_files_outside_the_test_patterns(project, files, creates):
    plan_with_implementation_files(project, files, creates)
    assert plan_refusals(project) == [None]


def test_plan_accepts_a_character_class_disjoint_from_the_test_patterns(project):
    plan_with_implementation_files(project, ["src/[a-m]*.py"],
                                   tests=["tests", "src/[n-z]*.py"])
    assert plan_refusals(project) == [None]


@pytest.mark.parametrize("first, second, overlap", [
    ("src/[a-m]*.py", "src/[n-z]*.py", False),
    ("src/[a-m]*.py", "src/[k-z]*.py", True),
    ("src/[abc]*.py", "src/[xyz]*.py", False),
    ("src/[abc]*.py", "src/[cde]*.py", True),
    ("src/[!a-m]*.py", "src/[n-z]*.py", True),
    ("src/[!a-z]*.py", "src/[a-m]*.py", False),
    ("src/[!n-z]*.py", "src/[n-z]*.py", False),
    ("src/[!a]*.py", "src/[!b]*.py", True),
    ("src/[a-m]*.py", "src/?*.py", True),
])
def test_character_classes_overlap_only_when_they_share_a_character(first, second, overlap):
    assert evidence.patterns_overlap(first, second) is overlap
    assert evidence.patterns_overlap(second, first) is overlap


def test_plan_accepts_a_declared_extensionless_file_beside_a_name_pattern(project):
    # A declared new file is a file even without an extension in its name.
    plan_with_implementation_files(project, ["Makefile"], ["Makefile"],
                                   sources=["src", "Makefile"], tests=["tests", "**/*_test.go"])
    assert plan_refusals(project) == [None]


def test_plan_judges_character_classes_as_the_runtime_matcher_does(project):
    # fnmatch reads [b-a!] so that src/a.py matches it as well as src/[a-z]*.py.
    assert evidence.matches("src/a.py", ["src/[b-a!]*.py"])
    assert evidence.matches("src/a.py", ["src/[a-z]*.py"])
    plan_with_implementation_files(project, ["src/[b-a!]*.py"], sources=["src"],
                                   tests=["tests", "src/[a-z]*.py"])
    for message in plan_refusals(project):
        assert message is not None and "cancel" in message, message


# First characters for witness names; overlaps in the cases below show up in one of them.
WITNESS_CHARS = "abcmnxyzAZ019!-]^[_."


@pytest.mark.parametrize("first, second", [
    ("src/[b-a!]*.py", "src/[a-z]*.py"),
    ("src/[b-a!]*.py", "src/[!a-z]*.py"),
    ("src/[z-a]*.py", "src/*.py"),
    ("src/[!z-a]*.py", "src/[a-c]*.py"),
    ("src/[b-a]x.py", "src/?x.py"),
    ("src/[c-a]*.py", "src/[b]*.py"),
    ("src/[a-c-e]*.py", "src/[d]*.py"),
    ("src/[a-]*.py", "src/[-z]*.py"),
    ("src/[]a]*.py", "src/[]z]*.py"),
    ("src/[!]a]*.py", "src/[]a]*.py"),
    ("src/[^a]*.py", "src/[a-c]*.py"),
    ("src/[^a]*.py", "src/[^]*.py"),
])
def test_class_overlap_agrees_with_the_runtime_matcher(first, second):
    witnesses = [f"src/{c}{tail}.py" for c in WITNESS_CHARS for tail in ("", "x")]
    expected = any(evidence.matches(w, [first]) and evidence.matches(w, [second])
                   for w in witnesses)
    assert evidence.patterns_overlap(first, second) is expected, (first, second, expected)
    assert evidence.patterns_overlap(second, first) is expected, (second, first, expected)


def test_plan_judges_an_existing_directory_as_a_directory(project):
    # The directory exists, so the spec does not declare it; its dotted name does not make it a file.
    (project / "pkg/v1.2").mkdir(parents=True)
    plan_with_implementation_files(project, ["pkg/v1.2"])
    for message in plan_refusals(project):
        assert message is not None and "cancel" in message, message


def test_implementation_start_rechecks_ownership_against_the_current_tree(project):
    # Declared a file, the path is accepted at breakdown; it then appears as a directory.
    edit_scope(project, sources=["src", "pkg"], tests=["tests", "pkg/**/*_test.go"],
               creates=["pkg/", "pkg/v1.2"])
    edit_tasks(project, lambda by_id, tasks: by_id["cancel"].update(files=["pkg/v1.2"]))
    prepare_implementation(project)
    assert stage(project) == "writing-code"
    (project / "pkg/v1.2").mkdir(parents=True)
    message = start(project, "cancel", "implementer")
    assert message is not None and "cancel" in message, message


def test_test_task_start_in_implement_rechecks_listed_paths_against_the_current_tree(project):
    # An existing, undeclared production file listed at breakdown is gone when the task starts.
    (project / "src/extra.py").write_text("pass\n")
    edit_tasks(project, lambda by_id, tasks: by_id["prepare-tests"].update(
        files=["tests/check.py", "src/extra.py"]))
    enter_implementation(project)
    (project / "src/extra.py").unlink()
    message = start(project, "prepare-tests", "test-author")
    assert message is not None and "src/extra.py" in message, message


def plan_with_a_consumer(root, creates, consumes=(), input_refs=()):
    """A producer owning the declared new folder pkg, and the implementation task reading from it."""
    edit_scope(root, sources=["src", "pkg"], tests=["tests"], creates=list(creates))

    def change(by_id, tasks):
        tasks.append({
            "id": "producer", "stage": "implementation",
            "description": "Create the pkg module.", "files": ["pkg"], "depends_on": [],
            "acceptance_refs": REFS, "verification": "The module imports.",
            "check_expectations": [{"argv": CHECK, "exit_code": 0}],
        })
        by_id["cancel"].update(depends_on=["producer"], consumes=list(consumes))
        if input_refs:
            by_id["cancel"]["input_refs"] = REFS + list(input_refs)

    edit_tasks(root, change)
    accept(root, "intent")
    message = refusal(accept, root, "spec")
    assert message is None, f"spec close should accept the declared scope: {message}"
    enter(root, "breakdown")


@pytest.mark.parametrize("route", ["consumes", "input_refs"])
def test_plan_refuses_a_consumed_missing_path_the_spec_does_not_declare(project, route):
    plan_with_a_consumer(project, ["pkg/"], **{route: ["pkg/undeclared.py"]})
    for message in plan_refusals(project):
        assert message is not None and "pkg/undeclared.py" in message, message
        assert "declare" in message.lower(), message


@pytest.mark.parametrize("route", ["consumes", "input_refs"])
def test_plan_accepts_a_consumed_path_the_spec_declares(project, route):
    plan_with_a_consumer(project, ["pkg/", "pkg/declared.py"], **{route: ["pkg/declared.py"]})
    assert plan_refusals(project) == [None]


@pytest.mark.parametrize("task, path", [
    ("cancel", "src/new_module.py"),
    ("prepare-tests", "tests/new_check.py"),
])
def test_plan_refuses_a_missing_path_the_spec_does_not_declare(project, task, path):
    edit_tasks(project, lambda by_id, tasks: by_id[task]["files"].append(path))
    accept(project, "intent")
    accept(project, "spec")
    enter(project, "breakdown")
    for message in plan_refusals(project):
        assert message is not None and path in message, message
        assert "spec" in message and "declare" in message.lower(), message


def test_plan_accepts_declared_production_files_on_a_test_task(project):
    declare_production_file_on_test_task(project)
    accept(project, "intent")
    accept(project, "spec")
    enter(project, "breakdown")
    assert plan_refusals(project) == [None]
    observe_phase(project, "breakdown")
    mutate(project, engine.approve, "s", "start-implementation", "implement", "Proceed.")
    enter(project, "implement")
    assert start(project, "prepare-tests", "test-author") is None


# Declared new paths


def close_spec_with(root, creates, sources=("src", "pkg")):
    accept(root, "intent")
    edit_scope(root, sources=list(sources), creates=creates)
    return refusal(accept, root, "spec")


@pytest.mark.parametrize("creates, named", [
    (["src/app.py"], "src/app.py"),           # already exists
    (["tests/"], "tests/"),                   # existing directory
    (["docs/guide.md"], "docs/guide.md"),     # outside the sources and tests
    (["pkg/new.go"], "pkg/new.go"),           # under a missing, undeclared directory
    (["pkg/", "pkg/sub/new.go"], "pkg/sub/new.go"),
])
def test_spec_close_refuses_an_invalid_creates_entry(project, creates, named):
    message = close_spec_with(project, creates)
    assert message is not None and named in message, message


def test_spec_close_accepts_declared_new_paths(project):
    creates = ["pkg/", "pkg/v1.2/", "pkg/v1.2/api.go", "src/new.py", "tests/new_check.py"]
    assert close_spec_with(project, creates) is None
    assert store.load(project, "feature")["phases"]["spec"]["evidence"]


def test_spec_close_accepts_a_declared_directory_under_glob_scoped_paths(project):
    accept(project, "intent")
    edit_scope(project, sources=["pkg/**/*.go"], tests=["tests", "pkg/**/*_test.go"],
               creates=["pkg/", "pkg/sub/", "pkg/sub/api.go"])
    assert refusal(accept, project, "spec") is None


@pytest.mark.parametrize("creates, named", [
    (["pkg/", "pkg/sub/"], "pkg/sub/"),  # pkg/*.go cannot match anything inside pkg/sub/
    (["other/"], "other/"),
])
def test_spec_close_refuses_a_declared_directory_no_scope_pattern_reaches(project, creates, named):
    accept(project, "intent")
    edit_scope(project, sources=["pkg/*.go"], tests=["tests", "pkg/*_test.go"], creates=creates)
    message = refusal(accept, project, "spec")
    assert message is not None and named in message and "scope" in message, message


@pytest.mark.parametrize("creates", [
    ["pkg/", "pkg/v1.2/", "pkg/v1.2"],
    ["pkg/", "pkg/v1.2", "pkg/v1.2/"],
    ["pkg/", "./pkg/v1.2", "pkg/v1.2/"],
    ["pkg/", "pkg/v1.2/", "./pkg/v1.2"],
])
def test_spec_close_refuses_a_path_declared_as_both_a_file_and_a_directory(project, creates):
    message = close_spec_with(project, creates, sources=("pkg",))
    assert message is not None and "pkg/v1.2" in message, message
    assert "file" in message and "directory" in message, message


def test_spec_close_accepts_declarations_spelled_from_the_current_directory(project):
    assert close_spec_with(project, ["./pkg/", "./pkg/new.go"], sources=("pkg",)) is None


@pytest.mark.parametrize("declared, listed", [
    ("./src/new.py", "src/new.py"),
    ("src/new.py", "./src/new.py"),
    ("./lib/", "lib"),
])
def test_a_declaration_covers_an_equivalent_task_path_spelling(project, declared, listed):
    # Task paths may start with ./ today (an existing ./src/app.py is accepted).
    plan_with_implementation_files(project, [listed], creates=[declared])
    assert plan_refusals(project) == [None]


def test_spec_close_refuses_a_directory_named_like_a_scoped_file(project):
    # pkg/generated.go matches pkg/*.go, but nothing inside the directory can.
    accept(project, "intent")
    edit_scope(project, sources=["pkg/*.go"], tests=["tests"],
               creates=["pkg/", "pkg/generated.go/"])
    message = refusal(accept, project, "spec")
    assert message is not None and "pkg/generated.go" in message and "scope" in message, message


def test_spec_review_checks_every_creates_entry_against_the_design():
    obligations = review.focus_brief("unit", "spec", [".fbk/unit/spec.md", ".fbk/unit/scope.json"])[
        "acceptance_obligations"]
    creates = [o for o in obligations if "creates" in o]
    assert len(creates) == 1, obligations
    assert "design" in creates[0] and "parallel" in creates[0] and "blocker" in creates[0]


# Continuation


def test_continuation_reports_a_test_task_from_its_actual_run(project):
    enter_implementation(project)
    assert task_status(project, "prepare-tests") == "unassigned"
    assert start(project, "prepare-tests", "test-author") is None
    assert task_status(project, "prepare-tests") == "running"
