"""A red check is any non-zero exit; a command that cannot be launched is a setup error.

Only pytest separates failed tests from a collection error by exit code, so Firebreak
judges red mechanically as non-zero and leaves "failed for the right reason" to the
reviewer. A test task may declare ``"exit_code": "nonzero"``; integers stay exact.
Breakdown writes tasks only, so red is proven where it now happens: test task finish
in implement and the test checkpoint, which runs every check and locks on pass.
Also covers step 1's carried-over refusals: malformed task inputs, declared directories
under excluded path components, and a reopened spec declaring a pre-existing path.
"""

import json
import os
import re
import sys

import pytest

from fbk.workflow import close, engine, evidence, handoff, review, store
from .test_workflow_implement_stages import (
    CHECK,
    REFS,
    close_breakdown,
    close_spec_with,
    edit_scope,
    edit_tasks,
    plan_refusals,
    refusal,
    start,
)
from .test_workflow_lifecycle import (
    accept,
    clean_review,
    enter,
    enter_implementation,
    mutate,
    observe_phase,
    pass_checkpoint,
    project as workflow_project,
    run_test_tasks,
)
from .refactor_plan import complete_refactor_tasks

project = workflow_project
CK = "test-checkpoint"

# Rust-shaped: cargo test exits 101 when a test fails.
RUST_RED = (
    "import sys\nfrom pathlib import Path\n"
    "if Path('src/app.py').read_text() != 'release()':\n"
    "    sys.stderr.write('assertion failed: release() was not called\\n')\n"
    "    sys.exit(101)\n"
)
COULD_NOT_RUN = re.compile(r"could not (be )?(run|launch|start)", re.IGNORECASE)


def exits(code):
    return f"import sys\nsys.exit({code})\n"


def set_test_expectation(root, exit_code, argv=CHECK):
    edit_tasks(root, lambda by_id, tasks: by_id["prepare-tests"].update(
        check_expectations=[{"argv": list(argv), "exit_code": exit_code}]))


def enter_breakdown(root):
    accept(root, "intent")
    accept(root, "spec")
    enter(root, "breakdown")


def start_test_task_in_implement(root, task="prepare-tests"):
    """Breakdown writes tasks only; a test task starts once implement opens."""
    enter_implementation(root)
    assert start(root, task, "test-author") is None


def checkpoint_refusal(root):
    """The checkpoint's refusal message, or None when it passes and locks."""
    return refusal(pass_checkpoint, root)


def checkpoint_checks(root):
    """Each check the accepted checkpoint ran, by command."""
    accepted = store.load(root, "feature")["phases"][CK]["evidence"]
    assert accepted, "The checkpoint recorded no acceptance."
    return {tuple(c["argv"]): c for c in accepted.get("verification", accepted.get("checks", []))}


def finish_test_task(root, actual, task="prepare-tests", argv=CHECK):
    return mutate(root, handoff.finish_task, "s", task, changed_files=[],
                  checks=[{"argv": list(argv), "exit_code": actual,
                           "evidence": "The check ran and failed on its assertion."}],
                  unresolved=[], outcome="The behavior under test is still missing.")


def any_refusal(fn, *args, **kwargs):
    """The refusal as (exception type, message), or None when accepted; crashes are reported, not raised."""
    try:
        fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001 - a crash is the defect under test
        return type(exc), str(exc)
    return None


# Plan validation


@pytest.mark.parametrize("exit_code", ["nonzero", 2, 101, 8])
def test_plan_accepts_a_nonzero_or_any_exact_red_on_a_test_task(project, exit_code):
    # Catches a plan that still restricts exit codes to 0 or 1, or rejects the string form.
    set_test_expectation(project, exit_code)
    enter_breakdown(project)
    assert plan_refusals(project) == [None]


def test_plan_refuses_nonzero_on_an_implementation_task(project):
    # Guard (passes now): catches accepting nonzero for implementation tasks.
    edit_tasks(project, lambda by_id, tasks: by_id["cancel"].update(
        check_expectations=[{"argv": CHECK, "exit_code": "nonzero"}]))
    enter_breakdown(project)
    for message in plan_refusals(project):
        assert message is not None and "implementation" in message.lower(), message


@pytest.mark.parametrize("exit_code", ["non-zero", "NONZERO", "nonzero ", "fail", None, True, 1.0])
def test_plan_refuses_a_malformed_exit_code_on_a_test_task(project, exit_code):
    # Guard (passes now): catches a loose check such as "any string" or truthiness.
    set_test_expectation(project, exit_code)
    enter_breakdown(project)
    for message in plan_refusals(project):
        assert message is not None and "expectation" in message.lower(), message


# Task finish


@pytest.mark.parametrize("expected, actual, status", [
    ("nonzero", 1, "completed"),
    ("nonzero", 101, "completed"),
    ("nonzero", 2, "completed"),
    ("nonzero", 0, "needs-attention"),
    (101, 101, "completed"),
    (101, 1, "needs-attention"),
])
def test_task_finish_compares_nonzero_as_any_failure_and_integers_exactly(project, expected, actual, status):
    # Catches comparing "nonzero" to the int exit code (never equal), treating any
    # non-zero integer expectation as nonzero, and accepting a pass as red.
    (project / "tests/check.py").write_text(exits(actual))
    set_test_expectation(project, expected)
    start_test_task_in_implement(project)
    returned = finish_test_task(project, actual)
    assert returned["status"] == status
    assert [c["exit_code"] for c in returned["verified_checks"]] == [actual]


def test_task_finish_keeps_an_integer_red_exact(project):
    # Guard (passes now): an exact exit 1 is not widened to any failure.
    (project / "tests/check.py").write_text(exits(101))
    start_test_task_in_implement(project)
    assert finish_test_task(project, 101)["status"] == "needs-attention"


@pytest.mark.parametrize("expected", ["nonzero", 127])
def test_a_process_that_ran_and_exited_127_is_red(project, expected):
    # Exit 127 from a process that ran is a mechanical red, distinct from a spawn failure.
    argv = [sys.executable, "-c", "import sys; sys.exit(127)"]
    set_test_expectation(project, expected, argv)
    start_test_task_in_implement(project)
    returned = finish_test_task(project, 127, argv=argv)
    assert returned["status"] == "completed"
    assert returned["verified_checks"][0]["exit_code"] == 127


def unlaunchable(root, launch):
    if launch == "missing":
        return ["fbk-no-such-test-runner-7f3a"]
    script = root / "tests/run_checks"
    script.write_text("#!/bin/sh\nexit 1\n")
    os.chmod(script, 0o644)
    return ["./tests/run_checks"]


@pytest.mark.parametrize("expected", [1, "nonzero"])
@pytest.mark.parametrize("launch", ["missing", "not-executable"])
def test_task_finish_refuses_a_check_that_cannot_be_launched(project, launch, expected):
    # Catches counting a spawn failure as red (a nonzero expectation would otherwise complete).
    argv = unlaunchable(project, launch)
    set_test_expectation(project, expected, argv)
    start_test_task_in_implement(project)
    message = refusal(finish_test_task, project, 127, argv=argv)
    assert message is not None and COULD_NOT_RUN.search(message) and argv[0] in message, message
    assert store.load(project, "feature")["task_runs"]["prepare-tests"]["status"] != "completed"


# The test checkpoint: every check runs and its red is any non-zero exit
#
# Retired with check-tests: a red that misses its test task's expectation is refused at
# task finish (above), and the checkpoint's own refusal of a wrong exact code is pinned
# by test_workflow_test_checkpoint.test_a_wrong_exact_nonzero_exit_is_refused.


def declare_scope_check(root, argv):
    path = root / ".fbk/feature/scope.json"
    scope = store.read_json(path)
    scope["checks"].append(list(argv))
    store.atomic_json(path, scope)


def test_checkpoint_accepts_any_non_zero_red_no_test_task_declares(project):
    # A declared whole-unit check exiting 2 that no test task names is red evidence;
    # catches the checkpoint still requiring exit 1 of a check no task pins.
    red = [sys.executable, "-c", "import sys; sys.exit(2)"]
    edit_scope(project, checks=[red])
    enter_implementation(project)
    run_test_tasks(project)
    assert checkpoint_refusal(project) is None
    assert checkpoint_checks(project)[tuple(red)]["exit_code"] == 2
    assert store.load(project, "feature")["locks"]


@pytest.mark.parametrize("launch", ["missing", "not-executable"])
def test_checkpoint_refuses_a_declared_check_that_cannot_be_launched(project, launch):
    # Catches recording a spawn failure as red evidence at the checkpoint.
    argv = unlaunchable(project, launch)
    declare_scope_check(project, argv)
    enter_implementation(project)
    run_test_tasks(project)
    message = checkpoint_refusal(project)
    assert message is not None and argv[0] in message, message
    record = store.load(project, "feature")
    assert record["phases"][CK]["evidence"] is None
    assert not record["locks"]


@pytest.mark.parametrize("exit_code", [2, 8, 127])
def test_checkpoint_locks_on_any_non_zero_red(project, exit_code):
    # Catches the lock still requiring exit 1: the checkpoint is the only route to locking.
    (project / "tests/check.py").write_text(exits(exit_code))
    set_test_expectation(project, "nonzero")
    enter_implementation(project)
    run_test_tasks(project)
    assert checkpoint_refusal(project) is None
    assert checkpoint_checks(project)[tuple(CHECK)]["exit_code"] == exit_code
    assert store.load(project, "feature")["locks"] == evidence.file_hashes(project, ["tests/check.py"])


@pytest.mark.parametrize("red", [{"exit_code": 0}, {"exit_code": None}, {}])
def test_lock_refuses_a_red_without_a_non_zero_exit(project, red):
    # Guard on the lock the checkpoint calls: catches a "!= 0" test that lets a missing or
    # null exit code through.
    enter_implementation(project)
    message = refusal(mutate, project, engine.lock_tests, "s", red)
    assert message is not None and "failing" in message, message
    assert not store.load(project, "feature")["locks"]


# Proof through the whole route: task finish, the checkpoint, and implementation close


@pytest.mark.parametrize("expected", [101, "nonzero"])
def test_a_rust_shaped_red_completes_finish_checkpoint_and_implementation_close(project, expected):
    (project / "tests/check.py").write_text(RUST_RED)
    set_test_expectation(project, expected)
    enter_breakdown(project)
    # Breakdown runs no task: the test task starts only in implement.
    assert start(project, "prepare-tests", "test-author") is not None
    assert refusal(close_breakdown, project) is None
    observe_phase(project, "breakdown")
    mutate(project, engine.approve, "s", "start-implementation", "implement", "Implement the agreed spec.")
    enter(project, "implement")
    assert start(project, "prepare-tests", "test-author") is None
    result = review.run_command(CHECK, project, 10)
    assert result["exit_code"] == 101 and "release() was not called" in result["stderr"]
    returned = finish_test_task(project, 101)
    assert returned["status"] == "completed"
    assert returned["verified_checks"][0]["exit_code"] == 101
    assert checkpoint_refusal(project) is None
    record = store.load(project, "feature")
    assert record["locks"] == evidence.file_hashes(project, ["tests/check.py"])
    assert checkpoint_checks(project)[tuple(CHECK)]["exit_code"] == 101
    assert record["phases"]["breakdown"]["evidence"].get("test_preparation") is None
    # The implementation task turns the same check green, and implement closes on it.
    assert start(project, "cancel", "implementer") is None
    (project / "src/app.py").write_text("release()")
    returned = mutate(project, handoff.finish_task, "s", "cancel", changed_files=["src/app.py"],
                      checks=[{"argv": CHECK, "exit_code": 0, "evidence": "Release happens."}],
                      unresolved=[], outcome="Cancellation releases its resource.")
    assert returned["status"] == "completed"
    complete_refactor_tasks(project)
    closed = close.close_phase(project, "feature", "implement", "s", reviewer=clean_review)
    assert closed["status"] == "retrospective-required"


# Review obligations


def test_breakdown_review_states_the_non_zero_red_rule_for_planned_checks():
    # Breakdown reviews the plan: the declared expectations, not output that does not exist yet.
    obligations = review.focus_brief("unit", "breakdown", [".fbk/unit/tasks.json"])[
        "acceptance_obligations"]
    sentence = next(o for o in obligations if "check_expectations" in o)
    assert "exit 1" not in sentence, sentence
    assert "non-zero" in sentence or "nonzero" in sentence, sentence
    assert "output" not in sentence, sentence


def test_checkpoint_review_states_the_right_reason_rule():
    # Guard (passes now): the "failed for the right reason" judgment lives at the checkpoint.
    obligations = review.focus_brief("unit", CK, [".fbk/unit/tasks.json"])["acceptance_obligations"]
    sentence = next(o for o in obligations if "saved output" in o)
    assert "exit 1" not in sentence, sentence
    assert "assertion" in sentence and "build" in sentence and "load" in sentence, sentence


# Carried over: malformed task inputs reach graph validation's refusal


@pytest.mark.parametrize("field, value, expected", [
    ("input_refs", [1], "Task input_refs must be an array of nonempty references."),
    ("input_refs", [None], "Task input_refs must be an array of nonempty references."),
    ("input_refs", [{}], "Task input_refs must be an array of nonempty references."),
    ("consumes", [{}], "Task consumes must be an array of repository-relative file paths or patterns."),
    ("consumes", [1], "Task consumes must be an array of repository-relative file paths or patterns."),
    ("consumes", ["src/app.py", {}], "Task consumes must be an array of repository-relative file paths or patterns."),
])
def test_malformed_task_inputs_are_refused_not_crashed(project, field, value, expected):
    # Catches path extraction running on malformed elements before they are checked.
    def change(by_id, tasks):
        by_id["cancel"][field] = (REFS + value) if field == "input_refs" else value

    enter_breakdown(project)
    edit_tasks(project, change)
    # Breakdown close is the plan's validation route now that breakdown starts no task.
    outcome = any_refusal(close_breakdown, project)
    assert outcome == (store.WorkflowError, expected), outcome
    # Status reports the plan's refusal instead of crashing on the malformed element.
    outcome = any_refusal(engine.status_report, project, store.load(project, "feature"))
    assert outcome is None or outcome[0] is store.WorkflowError, outcome


# Carried over: excluded path components are never in scope


@pytest.mark.parametrize("component", ["node_modules", ".venv", "__pycache__", ".pytest_cache", ".git"])
def test_spec_close_refuses_a_declared_directory_under_an_excluded_component(project, component):
    # The runtime matcher never matches inside these, so nothing there is ever in scope.
    message = close_spec_with(project, [f"src/{component}/"])
    assert message is not None and f"src/{component}/" in message and "scope" in message, message


def test_spec_close_accepts_a_directory_whose_name_only_contains_an_excluded_word(project):
    # Guard (passes now): catches a substring check instead of a whole-component check.
    assert close_spec_with(project, ["src/node_modules_shim/"]) is None


# Carried over: a reopened spec may not declare a pre-existing path it never declared


def reopen_spec(root):
    mutate(root, engine.approve, "s", "reopen", "spec", "Clarify the release contract.")
    mutate(root, engine.reopen, "spec", "s", "Clarify the release contract.")


def test_reopened_spec_refuses_a_pre_existing_path_no_earlier_spec_declared(project):
    # Guard (passes now): catches a reopened spec accepting any existing path.
    assert close_spec_with(project, ["src/new.py"]) is None
    reopen_spec(project)
    edit_scope(project, creates=["src/new.py", "src/app.py"])
    message = refusal(accept, project, "spec")
    assert message is not None and "src/app.py" in message and "already exists" in message, message


def test_reopened_spec_refuses_an_earlier_declaration_with_a_different_kind(project):
    # Guard (passes now): catches matching earlier declarations by path alone.
    assert close_spec_with(project, ["src/new.py"]) is None
    (project / "src/new.py").write_text("pass\n")
    reopen_spec(project)
    edit_scope(project, creates=["src/new.py/"])
    message = refusal(accept, project, "spec")
    assert message is not None and "src/new.py" in message and "already exists" in message, message


# Review round 1: shared commands, preservation, independent verification, secondary commands
#
# check-tests is gone; each rule now holds at test task finish and the test checkpoint.

FOCUSED = [sys.executable, "tests/focused.py"]


def focused_script(code, message="focused assertion failed: release() missing"):
    return f"import sys\nsys.stderr.write({message!r} + '\\n')\nsys.exit({code})\n"


def share_check_with_second_test_task(root, order):
    """prepare-tests expects CHECK nonzero; release-tests expects the same CHECK to exit exactly 101."""
    edit_scope(root, creates=["tests/release_check.py"])
    second = {
        "id": "release-tests", "stage": "tests",
        "description": "Check release happens exactly once.",
        "files": ["tests/release_check.py"], "depends_on": [],
        "acceptance_refs": REFS,
        "verification": "A double release fails the check.",
        "check_expectations": [{"argv": CHECK, "exit_code": 101}],
    }

    def change(by_id, tasks):
        by_id["prepare-tests"]["check_expectations"] = [{"argv": CHECK, "exit_code": "nonzero"}]
        tasks.insert(0 if order == "exact-first" else len(tasks), second)

    edit_tasks(root, change)


def finish_in_implement(root, task, argv=CHECK):
    """Start a test task in implement and return it with its check executed for real."""
    assert start(root, task, f"{task}-author") is None
    actual = review.run_command(list(argv), root, 10)["exit_code"]
    return finish_test_task(root, actual, task=task, argv=argv)


@pytest.mark.parametrize("order", ["nonzero-first", "exact-first"])
def test_checkpoint_accepts_compatible_shared_expectations(project, order):
    # Catches refusing nonzero and 101 on one command as a disagreement before running it.
    (project / "tests/check.py").write_text(RUST_RED)
    share_check_with_second_test_task(project, order)
    enter_implementation(project)
    run_test_tasks(project)
    assert checkpoint_refusal(project) is None
    assert checkpoint_checks(project)[tuple(CHECK)]["exit_code"] == 101


@pytest.mark.parametrize("order", ["nonzero-first", "exact-first"])
def test_a_shared_command_missing_its_exact_code_keeps_the_checkpoint_closed(project, order):
    # Guard: exit 1 satisfies nonzero but not the other task's exact 101. Both tasks complete
    # on 101, then a marker outside every task's files flips the command to 1 without
    # touching any recorded file, so the checkpoint itself must compare every expectation;
    # keeping only the first or the looser one would accept.
    marker = project / "flip-to-exit-1"
    (project / "tests/check.py").write_text(
        "import sys\nfrom pathlib import Path\n"
        f"sys.stderr.write('assertion failed: release() missing\\n')\n"
        f"sys.exit(1 if Path({str(marker)!r}).exists() else 101)\n")
    share_check_with_second_test_task(project, order)
    enter_implementation(project)
    run_test_tasks(project)
    assert engine.implement_stage(project, store.load(project, "feature")) == "ready-for-checkpoint"
    marker.write_text("flip")
    assert review.run_command(CHECK, project, 10)["exit_code"] == 1
    assert engine.implement_stage(project, store.load(project, "feature")) == "ready-for-checkpoint", "The flip must not invalidate the completed runs."
    reviewed = []
    message = refusal(pass_checkpoint, project, lambda *a: reviewed.append(a) or clean_review())
    # The refusal is about the unmet expectation, not a disagreement between compatible ones.
    assert message is not None and "disagree" not in message, message
    assert "expected outcome" in message, message
    assert reviewed == []
    assert not store.load(project, "feature")["locks"]


def preservation_plan(root, check_expected, focused_expected, focused_exit):
    (root / "tests/check.py").write_text(exits(0))
    (root / "tests/focused.py").write_text(focused_script(focused_exit))
    edit_tasks(root, lambda by_id, tasks: by_id["prepare-tests"].update(check_expectations=[
        {"argv": CHECK, "exit_code": check_expected},
        {"argv": FOCUSED, "exit_code": focused_expected},
    ]))
    enter_implementation(root)


def finish_both_checks(root):
    """Finish prepare-tests with both of its checks executed for real."""
    assert start(root, "prepare-tests", "test-author") is None
    checks = [{"argv": argv, "exit_code": review.run_command(argv, root, 10)["exit_code"],
               "evidence": "The check ran."} for argv in (CHECK, FOCUSED)]
    return mutate(root, handoff.finish_task, "s", "prepare-tests", changed_files=[],
                  checks=checks, unresolved=[], outcome="The checks ran.")


def test_preservation_executes_a_focused_task_command_outside_scope(project):
    # Catches preservation at the checkpoint running only the spec's whole-unit checks.
    preservation_plan(project, 0, 0, 0)
    assert finish_both_checks(project)["status"] == "completed"
    assert checkpoint_refusal(project) is None
    recorded = checkpoint_checks(project)
    assert tuple(FOCUSED) in recorded, sorted(recorded)
    assert recorded[tuple(FOCUSED)]["exit_code"] == 0
    red = store.load(project, "feature")["phases"][CK]["evidence"]["red_evidence"]
    assert red["red_check"] is None and red["preservation_reason"]


@pytest.mark.parametrize("check_expected, focused_expected, focused_exit", [
    ("nonzero", 0, 0),   # the whole-unit check passes but its task expects a failure
    (101, 0, 0),
    (0, 0, 1),           # the focused task command fails its exact 0
    (0, "nonzero", 0),   # the focused task command passes but its task expects a failure
])
def test_preservation_refuses_a_task_expectation_it_does_not_meet(
    project, check_expected, focused_expected, focused_exit
):
    # Catches skipping the collection and comparison of task expectations: the task does not
    # complete, and the checkpoint does not run or lock.
    preservation_plan(project, check_expected, focused_expected, focused_exit)
    assert finish_both_checks(project)["status"] == "needs-attention"
    assert checkpoint_refusal(project) is not None
    assert not store.load(project, "feature")["locks"]


@pytest.mark.parametrize("reported, actual", [(101, 0), (0, 101)])
def test_task_finish_decides_from_independent_execution(project, reported, actual):
    # Catches a nonzero branch that trusts the worker's report over the runtime's own run.
    (project / "tests/check.py").write_text(exits(actual))
    set_test_expectation(project, "nonzero")
    start_test_task_in_implement(project)
    returned = finish_test_task(project, reported)
    assert returned["status"] == "needs-attention"
    assert [c["exit_code"] for c in returned["verified_checks"]] == [actual]


def secondary_plan(root, focused_expected, focused_exit):
    (root / "tests/check.py").write_text(RUST_RED)
    (root / "tests/focused.py").write_text(focused_script(focused_exit))
    edit_tasks(root, lambda by_id, tasks: by_id["prepare-tests"].update(check_expectations=[
        {"argv": CHECK, "exit_code": "nonzero"},
        {"argv": FOCUSED, "exit_code": focused_expected},
    ]))
    enter_implementation(root)


@pytest.mark.parametrize("focused_expected", ["nonzero", 8])
def test_checkpoint_accepts_a_secondary_command_meeting_its_expectation(project, focused_expected):
    # Catches applying the comparison only to one command, and dropping a secondary command's output.
    secondary_plan(project, focused_expected, 8)
    assert finish_both_checks(project)["status"] == "completed"
    assert checkpoint_refusal(project) is None
    focused = checkpoint_checks(project)[tuple(FOCUSED)]
    assert focused["exit_code"] == 8


@pytest.mark.parametrize("focused_expected, focused_exit", [("nonzero", 0), (8, 2), (8, 0)])
def test_a_secondary_command_missing_its_expectation_keeps_the_checkpoint_closed(
    project, focused_expected, focused_exit
):
    # Catches a pass counted as red, and an exact code widened to any failure, off the main check.
    secondary_plan(project, focused_expected, focused_exit)
    assert finish_both_checks(project)["status"] == "needs-attention"
    assert checkpoint_refusal(project) is not None
    assert not store.load(project, "feature")["locks"]


@pytest.mark.parametrize("focused_expected", ["nonzero", 101])
def test_checkpoint_accepts_a_focused_red_command_beside_passing_whole_unit_checks(project, focused_expected):
    # Catches folding focused task commands into the whole-unit list that must pass.
    preservation_plan(project, 0, focused_expected, 101)
    scope_path = project / ".fbk/feature/scope.json"
    before = scope_path.read_bytes()
    assert finish_both_checks(project)["status"] == "completed"
    assert checkpoint_refusal(project) is None
    recorded = checkpoint_checks(project)
    assert tuple(FOCUSED) in recorded, sorted(recorded)
    assert recorded[tuple(FOCUSED)]["exit_code"] == 101
    assert recorded[tuple(CHECK)]["exit_code"] == 0
    # The checkpoint reads the spec's checks; it never rewrites them.
    assert scope_path.read_bytes() == before
    assert evidence.scope(project, "feature")["checks"] == [CHECK]
