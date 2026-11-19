"""The three test outcomes (build step 9b, plan decision 9's last bullet).

A unit whose requirements are all review-only has nothing for a test task to write. Its
breakdown may plan no test task, and implement then follows one of two outcomes, decided when
implement is entered (with the writing-tests baseline) and kept until a breakdown-or-earlier
reopen:

- **Preservation**: scoped tests exist at entry. The unit is ready for the test checkpoint at
  once; the checkpoint demands that every declared check passes, refuses a scoped test that
  differs from the writing-tests baseline, asks the reviewer whether the scoped tests protect
  the code the unit will change, and locks every scoped test on pass. Writing code follows as
  in the normal flow.
- **No tests**: no scoped test exists at entry. Implement starts in writing code with no
  checkpoint and no lock. The empty test inventory is recorded, and task start, task finish
  (after its checks run) and implementation close refuse any scoped test that appears later,
  naming it. Implementation close skips the checkpoint and lock requirements for this unit only.

With one or more test tasks the normal flow is unchanged.

Lead rulings these tests rely on (step 9b brief): breakdown close accepts a plan with no test
task only when every requirement of the unit's own spec.md is review-only; "scoped tests" are
what the lock would cover (whole test files and non-empty test regions); a resume or an
implement reopen does not re-decide the outcome, a breakdown-or-earlier reopen clears it and
re-entry decides it again; ``approve unlock-test`` is refused in both no-test-task outcomes with
the reopen-breakdown remedy; status and the implement progress report name the outcome.

Shapes the tests assume, leaving names to the implementer: refusals are ``WorkflowError``s whose
messages name the test paths involved; reason words are matched loosely. The outcome is found
through behavior (stage, task start, checkpoint, close), except two loose checks that some
event recorded at implement entry mentions the outcome.

Red or guard: **red** tests fail today on an assertion about missing behavior (most of them at
breakdown close, which today refuses every plan without a test task; the helper turns that
refusal into an assertion failure); **guard** tests (marked ``# Guard:``) pass today and pin
behavior a plausible wrong implementation would break.
"""

import json
import re
import sys

import pytest

from fbk.workflow import close, engine, handoff, review, review_baseline, store
from tests import test_workflow_lifecycle as scenarios
from tests.test_workflow_commands import call
from tests.test_workflow_constraints import packet_of
from tests.test_workflow_implement_stages import denied, refusal
from tests.test_workflow_lock_enforcement import ROUTES, finish_refusal
from tests.test_workflow_review_only_requirements import Readers
from tests.test_workflow_test_preparation import write_permission

from .refactor_plan import complete_refactor_tasks, with_refactor

UNIT = "feature"
CK = "test-checkpoint"
SPEC_PATH = f".fbk/{UNIT}/spec.md"
PRD_PATH = f".fbk/{UNIT}/prd.md"
PROTECT, OTHER, NEW = "tests/check.py", "tests/other_check.py", "tests/new_check.py"
CHECK = [sys.executable, PROTECT]
PARSE = [sys.executable, "-c", "import ast, pathlib; ast.parse(pathlib.Path('src/app.py').read_text())"]

DOCSTRING_REASON = "the docstring's wording is judged by a reader, not a program."
NAMING_REASON = "naming is a convention no executable check can meaningfully verify."
REVIEW_ONLY_SPEC = f"""\
# Cancellation documentation

## Requirements

### Cancel docstring

Checked by review: {DOCSTRING_REASON}

The cancel function's docstring says it releases the resource once. Serves [Release on cancel](prd.md#release-on-cancel).

### Cancel naming

Checked by review: {NAMING_REASON}

Public cancellation functions start with cancel. Serves [Release on cancel](prd.md#release-on-cancel).
"""
MIXED_SPEC = f"""\
# Cancellation contract

## Requirements

### Cancel once

Cancel returns true once, false when already canceled. Serves [Release on cancel](prd.md#release-on-cancel).

### Cancel docstring

Checked by review: {DOCSTRING_REASON}

The cancel function's docstring says it releases the resource once. Serves [Release on cancel](prd.md#release-on-cancel).
"""
REVIEW_REFS = [PRD_PATH, SPEC_PATH, f"{SPEC_PATH}#cancel-docstring", f"{SPEC_PATH}#cancel-naming"]

ORIGINAL_CODE = "def cancel():\n    return True\n"
DOCUMENTED_CODE = 'def cancel():\n    """Release the resource once."""\n    return True\n'
PROTECTING_TEST = "import sys\nsys.path.insert(0, 'src')\nimport app\nassert app.cancel() is True\n"
PASSING_TEST = "assert 1 == 1\n"
FAILING_TEST = "import sys\nsys.path.insert(0, 'src')\nimport app\nassert app.cancel() is False, 'cancel broke'\n"

REGION_START = r"^# --- tests ---$"
REGION_CODE = ORIGINAL_CODE + "# --- tests ---\nassert cancel() is True\n"


def code_task(refs=REVIEW_REFS):
    return {
        "id": "document", "stage": "implementation",
        "description": "Document the cancel function's release behavior.",
        "files": ["src/app.py"], "depends_on": [], "acceptance_refs": list(refs),
        "verification": "The production module still parses with the new docstring.",
        "check_expectations": [{"argv": PARSE, "exit_code": 0}],
    }


# Fixtures


def review_only_unit(root, tests=(PROTECT, OTHER), regions=False, spec=REVIEW_ONLY_SPEC, tasks=None):
    """The lifecycle fixture rewritten as a unit whose requirements are all review-only, with one
    implementation task and no test task. ``tests`` are the scoped test files present before
    implement is entered: none gives the no-tests outcome. With ``regions`` the scope declares a
    test region in ``src/app.py`` and no whole-file tests; ``tests`` then says whether the region
    holds tests."""
    root.mkdir(parents=True, exist_ok=True)
    scenarios.project.__wrapped__(root)
    unit = root / f".fbk/{UNIT}"
    (unit / "spec.md").write_text(spec)
    store.atomic_json(unit / "tasks.json", with_refactor(tasks if tasks is not None else [code_task()]))
    (root / PROTECT).unlink()
    scope = {"sources": ["src"], "tests": ["tests"], "docs": [], "checks": [PARSE]}
    if regions:
        scope.update(tests=[], test_regions=[{"files": ["src/app.py"], "start": REGION_START}])
        (root / "src/app.py").write_text(REGION_CODE if tests else ORIGINAL_CODE)
    else:
        (root / "src/app.py").write_text(ORIGINAL_CODE)
        for path in tests:
            (root / path).write_text(PROTECTING_TEST if path == PROTECT else PASSING_TEST)
        if PROTECT in tests:
            scope["checks"] = [CHECK]
    store.atomic_json(unit / "scope.json", scope)
    return root


def accept_breakdown(root):
    """Close breakdown for real; a refusal of the plan with no test task fails the test."""
    try:
        scenarios.accept(root, "breakdown")
    except store.WorkflowError as exc:
        pytest.fail("Breakdown close refused a plan with no test task for a unit whose requirements "
                    f"are all review-only: {exc}")


def enter_implement(root, reason="Implement the agreed spec."):
    scenarios.mutate(root, engine.approve, "s", "start-implementation", "implement", reason)
    scenarios.enter(root, "implement")


def implement_entered(root):
    """Accept intent, spec and a breakdown with no test task, then enter implement."""
    scenarios.accept(root, "intent")
    scenarios.accept(root, "spec")
    accept_breakdown(root)
    enter_implement(root)
    return root


def preservation_unit(tmp_path, **kwargs):
    return implement_entered(review_only_unit(tmp_path / "p", **kwargs))


def no_tests_unit(tmp_path, **kwargs):
    return implement_entered(review_only_unit(tmp_path / "p", tests=(), **kwargs))


def record(root):
    return store.load(root, UNIT)


def stage(root):
    return engine.implement_stage(root, record(root))


def start(root, task="document", worker="implementer"):
    return refusal(scenarios.mutate, root, handoff.start_task, "s", task, worker)


def checkpoint(root, reviewer=scenarios.clean_review):
    return refusal(close.close_checkpoint, root, UNIT, "s", reviewer=reviewer)


def close_implement(root):
    return refusal(close.close_phase, root, UNIT, "implement", "s", reviewer=scenarios.clean_review)


def finish(root, changed=("src/app.py",)):
    """Finish the implementation task through the public route; returns the handoff result."""
    result = review.run_command(PARSE, root, 30)
    return handoff.complete_task(
        root, UNIT, "s", "document", changed_files=list(changed),
        checks=[{"argv": PARSE, "exit_code": result["exit_code"],
                 "evidence": (result["stdout"] or result["stderr"] or "The module parsed.")[-500:]}],
        unresolved=[], outcome="The docstring is in place.")


def build_code(root, code=DOCUMENTED_CODE):
    """Run the implementation task: start it, write the docstring, finish it verified, then run
    the refactor task over it."""
    assert start(root) is None, f"The implementation task did not start: {start(root)}"
    (root / "src/app.py").write_text(code)
    returned = finish(root)
    assert returned["status"] == "completed", returned
    complete_refactor_tasks(root)


def closed_and_observed(root):
    message = close_implement(root)
    assert message is None, f"Implementation close refused: {message}"
    scenarios.observe_phase(root, "implement")


def reopen(root, phase, reason="Revisit the plan."):
    scenarios.mutate(root, engine.approve, "s", "reopen", phase, reason)
    scenarios.mutate(root, engine.reopen, phase, "s", reason)


def names_remedy(message, *paths):
    assert message is not None, "The action was accepted."
    missing = [p for p in paths if p not in message]
    assert not missing, f"The refusal does not name {missing}: {message}"
    lowered = message.lower()
    assert "breakdown" in lowered and "remov" in lowered, (
        f"The refusal does not give the remedy (remove it, or reopen breakdown to plan a test task): {message}")


def events_since_entry(root):
    events = record(root)["events"]
    entered = max(i for i, e in enumerate(events) if e["event"] == "entered" and e.get("phase") == "implement")
    return events[entered:]


def progress(root):
    return engine.status_report(root, record(root))["test_preparation"]


# Breakdown close (ruling 1)


def test_breakdown_accepts_no_test_task_when_every_requirement_is_review_only(tmp_path):
    """Red. A plan with only an implementation task closes when every requirement is
    review-only. Today breakdown close refuses every plan without a test task."""
    root = review_only_unit(tmp_path / "p")
    scenarios.accept(root, "intent")
    scenarios.accept(root, "spec")
    accept_breakdown(root)
    assert record(root)["phases"]["breakdown"]["evidence"]


def test_breakdown_without_a_test_task_is_refused_naming_the_behavioral_requirement(tmp_path):
    # Guard: passes today; protects behavior that must not regress.
    """Guard: with one behavioral and one review-only requirement, both linked by the
    implementation task, a plan with no test task is refused, naming the behavioral requirement
    as lacking a test task and not the review-only one. Catches: accepting a plan with no test
    task whenever any requirement is review-only."""
    refs = [PRD_PATH, SPEC_PATH, f"{SPEC_PATH}#cancel-once", f"{SPEC_PATH}#cancel-docstring"]
    root = review_only_unit(tmp_path / "p", spec=MIXED_SPEC, tasks=[code_task(refs)])
    scenarios.accept(root, "intent")
    scenarios.accept(root, "spec")
    message = refusal(scenarios.accept, root, "breakdown")
    assert message is not None, "Breakdown accepted no test task beside a behavioral requirement."
    lines = [line for line in message.splitlines() if "Cancel once" in line]
    assert lines and re.search(r"test", lines[0], re.I), message
    assert not any("Cancel docstring" in line and re.search(r"test", line, re.I) for line in message.splitlines()), (
        f"The refusal asks for a test for the review-only requirement: {message}")


def test_breakdown_without_a_test_task_is_refused_for_an_all_behavioral_unit(tmp_path):
    # Guard: passes today; the lifecycle unit's one requirement is behavioral.
    """Guard: the lifecycle unit with its test task removed is refused at breakdown close, naming
    its behavioral requirement. Catches: dropping the test-task rule outright."""
    root = tmp_path / "p"
    root.mkdir()
    scenarios.project.__wrapped__(root)
    path = root / f".fbk/{UNIT}/tasks.json"
    store.atomic_json(path, [t for t in store.read_json(path) if t["stage"] != "tests"])
    scenarios.accept(root, "intent")
    scenarios.accept(root, "spec")
    message = refusal(scenarios.accept, root, "breakdown")
    assert message is not None and "Cancel once" in message, message


# Normal flow


def test_normal_flow_runs_to_implementation_close(tmp_path):
    # Guard: passes today; one or more test tasks keep the normal flow.
    """Guard: the lifecycle unit (a test task, a behavioral requirement) runs its test task,
    passes the checkpoint, builds code and closes implement. Catches: an outcome decision that
    treats a unit with test tasks as preservation or no-tests."""
    root = tmp_path / "p"
    root.mkdir()
    scenarios.project.__wrapped__(root)
    scenarios.enter_implementation(root)
    assert stage(root) == "writing-tests"
    scenarios.run_test_tasks(root)
    assert stage(root) == "ready-for-checkpoint"
    scenarios.pass_checkpoint(root)
    assert stage(root) == "writing-code"
    assert start(root, "cancel") is None
    (root / "src/app.py").write_text("release()")
    result = review.run_command(CHECK, root, 30)
    returned = handoff.complete_task(root, UNIT, "s", "cancel", changed_files=["src/app.py"],
                                     checks=[{"argv": CHECK, "exit_code": result["exit_code"],
                                              "evidence": "The release check passed."}],
                                     unresolved=[], outcome="Release is built.")
    assert returned["status"] == "completed", returned
    complete_refactor_tasks(root)
    assert close_implement(root) is None


def test_normal_flow_still_needs_the_checkpoint_to_close_implement(tmp_path):
    # Guard: passes today; the no-tests exemption is for that outcome only.
    """Guard: a unit with a test task that never ran cannot close implement. Catches: skipping
    the checkpoint and lock requirements for every unit."""
    root = tmp_path / "p"
    root.mkdir()
    scenarios.project.__wrapped__(root)
    scenarios.enter_implementation(root)
    message = close_implement(root)
    assert message is not None and re.search(r"checkpoint|lock", message), message


# Preservation (ruling 3)


def test_preservation_is_ready_for_checkpoint_at_entry(tmp_path):
    """Red. With scoped tests and no test task, the unit is ready for the checkpoint on entry,
    and an implementation task cannot start before it passes."""
    root = preservation_unit(tmp_path)
    assert stage(root) == "ready-for-checkpoint"
    message = start(root)
    assert message is not None, "An implementation task started before the preservation checkpoint."


def test_preservation_entry_records_its_outcome(tmp_path):
    """Red. Entering implement with no test task and scoped tests records that the preservation
    outcome applies (some event from entry on names it)."""
    root = preservation_unit(tmp_path)
    assert any("preservation" in json.dumps(e).lower() for e in events_since_entry(root)), (
        "No event recorded at implement entry names the preservation outcome.")


def test_preservation_checkpoint_passes_locks_every_scoped_test_and_code_follows(tmp_path):
    """Red. The checkpoint runs the declared check, saves its output, passes, and locks every
    scoped test, including one no check runs; then the implementation task runs and implement
    closes on the current checkpoint."""
    root = preservation_unit(tmp_path)
    message = checkpoint(root)
    assert message is None, f"The preservation checkpoint refused: {message}"
    state = record(root)
    assert set(state["locks"]) == {PROTECT, OTHER}, state["locks"]
    assert state.get("lock_origin") == CK
    assert state["phases"][CK]["evidence"]
    output = root / f".fbk/{UNIT}" / store.OUTPUT_FOLDER
    assert output.is_dir() and any(p.is_file() for p in output.rglob("*")), "No check output was saved."
    assert stage(root) == "writing-code"
    build_code(root)
    closed_and_observed(root)
    assert record(root)["phases"]["implement"]["evidence"]


def test_preservation_checkpoint_refuses_a_failing_declared_check(tmp_path):
    """Red. A preservation checkpoint needs every scoped test to pass: a failing declared check
    refuses it, saying so and naming the remedy, and locks nothing. Catches: demanding red as the
    normal first checkpoint does, which a failing check would satisfy."""
    root = review_only_unit(tmp_path / "p")
    (root / PROTECT).write_text(FAILING_TEST)
    implement_entered(root)
    message = checkpoint(root)
    assert message is not None, "A preservation checkpoint passed with a failing declared check."
    lowered = message.lower()
    assert "preservation" in lowered and "pass" in lowered, message
    assert "breakdown" in lowered, f"The refusal does not name reopening breakdown to plan test tasks: {message}"
    assert record(root)["locks"] == {}
    assert stage(root) != "writing-code"


@pytest.mark.parametrize("change", ["edited", "added", "removed"])
def test_preservation_checkpoint_refuses_a_scoped_test_changed_since_the_baseline(tmp_path, change):
    """Red. No test task could have changed a scoped test, so one that differs from the
    writing-tests baseline (edited, added or removed through the shell; the declared check still
    passes) is refused at the checkpoint, naming it. Catches: deciding preservation from the
    current tree, and passing whatever tests exist at checkpoint time."""
    root = preservation_unit(tmp_path)
    if change == "edited":
        path = OTHER
        (root / OTHER).write_text("assert 2 == 2\n")
    elif change == "added":
        path = NEW
        (root / NEW).write_text(PASSING_TEST)
    else:
        path = OTHER
        (root / OTHER).unlink()
    message = checkpoint(root)
    assert message is not None, f"The checkpoint passed over a scoped test {change} since the baseline."
    assert path in message, f"The refusal does not name {path}: {message}"
    assert record(root)["locks"] == {}


def test_preservation_outcome_is_kept_when_every_scoped_test_is_removed_after_entry(tmp_path):
    """Red. The outcome is the one recorded at entry: removing every scoped test afterwards does
    not turn the unit into writing code without a checkpoint. Catches: deciding the outcome from
    the current tree at every call."""
    root = preservation_unit(tmp_path)
    (root / PROTECT).unlink()
    (root / OTHER).unlink()
    assert stage(root) != "writing-code"
    assert start(root) is not None, "An implementation task started after the scoped tests were removed."
    message = close_implement(root)
    assert message is not None, "Implement closed with no checkpoint after the scoped tests were removed."


def test_preservation_reviewer_is_asked_whether_the_scoped_tests_protect_the_change(tmp_path, monkeypatch):
    """Red. The checkpoint reviewer is told this is a preservation checkpoint for a unit whose
    requirements are all review-only and asked whether the scoped tests protect the code the
    unit will change; the red demand for new tests is not among its obligations."""
    root = preservation_unit(tmp_path)
    readers = Readers(monkeypatch, native={})
    message = refusal(close.close_checkpoint, root, UNIT, "s")
    assert readers.prompts.get("native"), f"The checkpoint reviewer never ran: {message}"
    prompt = readers.prompts["native"][0]
    assert re.search(r"preservation checkpoint", prompt, re.I), "The prompt does not name a preservation checkpoint."
    priority = packet_of(prompt)["reading_priority"]
    stated = [priority.get("decision", ""), *priority["acceptance_obligations"]]
    assert any(re.search(r"review-only", s, re.I) and re.search(r"preservation", s, re.I) for s in stated), (
        "No decision or obligation says the unit's requirements are all review-only.")
    assert any(re.search(r"protect", s, re.I) and re.search(r"preservation|scoped test", s, re.I)
               and re.search(r"will change|changes?", s, re.I) for s in stated), (
        "No decision or obligation asks whether the scoped tests protect the code the unit will change.")
    red = [s for s in stated if re.search(r"assertion about missing behavior", s, re.I)]
    assert not red, f"The red obligation for new tests is still stated: {red}"


def test_preservation_checkpoint_approval_over_findings_locks(tmp_path):
    """Red. A preservation checkpoint with a blocker needs the operator's approval over findings,
    as any checkpoint does, then locks."""
    root = preservation_unit(tmp_path)
    message = checkpoint(root, scenarios.blocking_review)
    assert message is not None and "approval required" in message, message
    scenarios.mutate(root, engine.approve, "s", "close-over-findings", CK, "Accept the documented residual.")
    assert checkpoint(root, scenarios.blocking_review) is None
    assert set(record(root)["locks"]) == {PROTECT, OTHER}


def test_preservation_by_test_region_is_ready_for_checkpoint_and_locks_the_region(tmp_path):
    """Red. A non-empty test region is a scoped test: a regions-only unit whose region holds
    tests at entry takes the preservation outcome and locks the region."""
    root = preservation_unit(tmp_path, regions=True)
    assert stage(root) == "ready-for-checkpoint"
    assert checkpoint(root) is None
    assert set(record(root)["locks"]) == {"src/app.py"}


# No tests at all (ruling 4)


def test_no_tests_unit_writes_code_from_entry_and_records_the_empty_inventory(tmp_path):
    """Red. With no test task and no scoped test, implement starts in writing code with no
    locks, and an event recorded from entry on names the empty test inventory."""
    root = no_tests_unit(tmp_path)
    assert stage(root) == "writing-code"
    assert record(root)["locks"] == {}
    marks = ("inventory", "no-tests", "no tests", "no_tests", "empty")
    assert any(any(m in json.dumps(e).lower() for m in marks) for e in events_since_entry(root)), (
        "No event recorded at implement entry names the empty test inventory.")


def test_no_tests_unit_runs_to_implementation_close_without_checkpoint_or_lock(tmp_path):
    """Red. The implementation task runs, its worker may write production code through the write
    hook, and implement closes with no checkpoint acceptance and no locks."""
    root = no_tests_unit(tmp_path)
    assert start(root) is None
    assert write_permission(root, "src/app.py", "implementer") == {}, (
        "The write hook refused production code in the no-tests outcome.")
    (root / "src/app.py").write_text(DOCUMENTED_CODE)
    assert finish(root)["status"] == "completed"
    complete_refactor_tasks(root)
    closed_and_observed(root)
    state = record(root)
    assert state["phases"]["implement"]["evidence"]
    assert state["locks"] == {} and not state["phases"][CK]["evidence"]


def test_no_tests_write_hook_refuses_a_scoped_test_path(tmp_path):
    """Red. In writing code the write hook still refuses every scoped test path, so an
    implementer cannot add a test through Write."""
    root = no_tests_unit(tmp_path)
    assert start(root) is None
    assert denied(write_permission(root, NEW, "implementer")), "The write hook let an implementer write a test."


def test_no_tests_checkpoint_is_refused_saying_no_checkpoint_applies(tmp_path):
    """Red. test-checkpoint refuses in the no-tests outcome, saying the unit has no tests and no
    test tasks, and spends no checkpoint round."""
    root = no_tests_unit(tmp_path)
    message = checkpoint(root)
    assert message is not None, "The checkpoint ran in the no-tests outcome."
    assert re.search(r"no (scoped )?tests", message, re.I) and re.search(r"no test tasks?", message, re.I), message
    assert record(root)["phases"][CK]["rounds"] == []
    assert record(root)["locks"] == {}


def test_no_tests_task_start_refuses_a_test_created_through_the_shell(tmp_path):
    """Red. A scoped test created through the shell after entry is refused at the next task
    start, naming it with the remedy; the refused start is not recorded as a run. Catches:
    re-deciding the outcome from the current tree, which would quietly make it preservation."""
    root = no_tests_unit(tmp_path)
    (root / NEW).write_text(PASSING_TEST)
    message = start(root)
    names_remedy(message, NEW)
    assert "document" not in record(root).get("task_runs", {}), "The refused start was recorded as a run."


def test_no_tests_resume_does_not_re_decide_the_outcome(tmp_path):
    """Red. Resuming implement after a scoped test appears keeps the no-tests outcome: the stage
    stays writing code and the next task start is still refused naming the test."""
    root = no_tests_unit(tmp_path)
    (root / NEW).write_text(PASSING_TEST)
    scenarios.enter(root, "implement")
    assert stage(root) == "writing-code"
    names_remedy(start(root), NEW)


def test_no_tests_task_start_refuses_a_test_region_created_through_the_shell(tmp_path):
    """Red. In a regions-only scope whose region file held no tests at entry, a region added
    through the shell is a scoped test and refuses the next task start, naming the file."""
    root = no_tests_unit(tmp_path, regions=True)
    assert stage(root) == "writing-code"
    (root / "src/app.py").write_text(REGION_CODE)
    names_remedy(start(root), "src/app.py")


def test_no_tests_finish_refuses_a_test_created_while_the_task_ran(tmp_path):
    """Red. A scoped test created through the shell while the task ran refuses its finish,
    naming it; the task stays running."""
    root = no_tests_unit(tmp_path)
    assert start(root) is None
    (root / "src/app.py").write_text(DOCUMENTED_CODE)
    (root / NEW).write_text(PASSING_TEST)
    message = finish_refusal(root, "document", ["src/app.py"], PARSE)
    assert message is not None and not message.startswith("NOT REFUSED"), (
        f"The finish was accepted over a test created through the shell: {message}")
    names_remedy(message, NEW)
    assert record(root)["task_runs"]["document"]["status"] == "running"


@pytest.mark.parametrize("route", sorted(ROUTES))
def test_no_tests_finish_refuses_a_test_created_while_its_checks_ran(tmp_path, monkeypatch, route):
    """Red. A scoped test created while finish runs the task's checks is caught after they
    run, on either completion route; the task stays running. Catches: checking only before
    the checks."""
    root = no_tests_unit(tmp_path)
    assert start(root) is None
    (root / "src/app.py").write_text(DOCUMENTED_CODE)
    original = handoff._execute_task_checks

    def checks_then_new_test(where, expectations):
        results = original(where, expectations)
        (root / NEW).write_text(PASSING_TEST)
        return results

    monkeypatch.setattr(handoff, "_execute_task_checks", checks_then_new_test)
    message = finish_refusal(root, "document", ["src/app.py"], PARSE, ROUTES[route])
    assert message is not None and not message.startswith("NOT REFUSED"), (
        f"A test created while the checks ran was accepted: {message}")
    names_remedy(message, NEW)
    assert record(root)["task_runs"]["document"]["status"] == "running"


def test_no_tests_implementation_close_refuses_a_scoped_test_and_closes_once_removed(tmp_path):
    """Red. A scoped test present at implementation close refuses it, naming the test with the
    remedy; once it is removed, implement closes."""
    root = no_tests_unit(tmp_path)
    build_code(root)
    (root / NEW).write_text(PASSING_TEST)
    names_remedy(close_implement(root), NEW)
    assert not record(root)["phases"]["implement"]["evidence"]
    (root / NEW).unlink()
    assert close_implement(root) is None


def test_no_tests_implement_review_baseline_is_the_entry_baseline_or_named_unavailable(tmp_path):
    """Red. With no accepted checkpoint snapshot, the implement review compares against the
    writing-tests baseline recorded at entry, or marks the comparison unavailable with a reason
    naming the no-tests outcome."""
    root = no_tests_unit(tmp_path)
    build_code(root)
    reader = tmp_path / "reader"
    reader.mkdir()
    available = {}
    provenance = review_baseline.prepare(root, reader, record(root), "implement", available)
    if provenance["status"] == "available":
        assert any(path.endswith("src/app.py") for path in available), provenance
    else:
        assert re.search(r"no tests|no test tasks?|no scoped tests?", provenance.get("reason", ""), re.I), (
            f"The unavailable comparison does not name the no-tests outcome: {provenance}")


# Reopen (ruling 6)


def test_reopening_breakdown_re_decides_a_no_tests_unit_as_preservation(tmp_path):
    """Red. A breakdown reopen clears the no-tests outcome; a scoped test added before re-entry
    makes the unit preservation, so it waits for the checkpoint, which locks the test. Catches:
    keeping the empty-inventory exemption past a breakdown reopen."""
    root = no_tests_unit(tmp_path)
    reopen(root, "breakdown")
    (root / PROTECT).write_text(PROTECTING_TEST)
    accept_breakdown(root)
    enter_implement(root, "Proceed with the replanned work.")
    assert stage(root) == "ready-for-checkpoint"
    assert start(root) is not None
    message = close_implement(root)
    assert message is not None, "Implement closed without the preservation checkpoint after the reopen."
    assert checkpoint(root) is None
    assert set(record(root)["locks"]) == {PROTECT}


def test_reopening_breakdown_re_decides_a_preservation_unit_as_no_tests(tmp_path):
    """Red. After the preservation checkpoint locked the tests, a breakdown reopen clears the
    locks and the outcome; with every scoped test removed before re-entry the unit writes code
    with no checkpoint."""
    root = preservation_unit(tmp_path, tests=(OTHER,))
    assert checkpoint(root) is None
    reopen(root, "breakdown")
    assert record(root)["locks"] == {}
    (root / OTHER).unlink()
    accept_breakdown(root)
    enter_implement(root, "Proceed with the replanned work.")
    assert stage(root) == "writing-code"
    assert re.search(r"no (scoped )?tests", checkpoint(root) or "", re.I)
    build_code(root)
    assert close_implement(root) is None


def test_reopening_implement_keeps_the_no_tests_outcome(tmp_path):
    """Red. An implement reopen keeps the recorded outcome: a scoped test added before
    re-entering is refused at the next task start rather than making the unit preservation."""
    root = no_tests_unit(tmp_path)
    build_code(root)
    closed_and_observed(root)
    reopen(root, "implement", "Revisit the delivered documentation.")
    (root / NEW).write_text(PASSING_TEST)
    enter_implement(root, "Continue the delivered documentation.")
    assert stage(root) == "writing-code"
    names_remedy(start(root), NEW)


# Unlock (ruling 7)


def unlock_message(root, tests):
    return refusal(scenarios.approve_unlock, root, {path: "pass" for path in tests},
                   [{"argv": CHECK, "tests": list(tests)}])


def test_unlock_is_refused_after_a_preservation_checkpoint(tmp_path):
    """Red. No test task exists to rework a locked test, so an unlock is refused with the
    remedy to reopen breakdown and plan a test task; nothing is unlocked."""
    root = preservation_unit(tmp_path)
    assert checkpoint(root) is None
    grants = record(root)["grants"]
    message = unlock_message(root, [PROTECT])
    assert message is not None, "An unlock was approved with no test task to rework it."
    lowered = message.lower()
    assert "test task" in lowered and "reopen" in lowered and "breakdown" in lowered, message
    assert record(root)["unlocks"] == [] and record(root)["grants"] == grants
    assert stage(root) == "writing-code"


def test_unlock_is_refused_in_the_no_tests_outcome(tmp_path):
    """Red. In the no-tests outcome an unlock is refused, through the command line too, saying
    no test task exists and naming the reopen-breakdown remedy."""
    root = no_tests_unit(tmp_path)
    message = unlock_message(root, [NEW])
    assert message is not None
    lowered = message.lower()
    assert "test task" in lowered and "reopen" in lowered and "breakdown" in lowered, message
    store.atomic_json(root / ".fbk/unlock-request.json",
                      {"expected": {NEW: "pass"}, "commands": [{"argv": CHECK, "tests": [NEW]}]})
    cli_message = refusal(call, root, "approve", UNIT, "unlock-test", "--phase", "implement",
                          "--reason", "The operator found the test wrong.", "--tests", NEW,
                          "--request", ".fbk/unlock-request.json")
    assert cli_message is not None and "breakdown" in cli_message.lower(), cli_message
    assert record(root)["unlocks"] == []


# Status and continuation (ruling 8)


def test_status_and_continuation_name_the_preservation_checkpoint(tmp_path):
    """Red. Status and the continuation's implement progress say the next step is the
    preservation checkpoint."""
    root = preservation_unit(tmp_path)
    packet = handoff.continuation(root, record(root))
    for report in (progress(root), packet["test_preparation"]):
        assert report["stage"] == "ready-for-checkpoint"
        assert re.search(r"preservation", report["next"], re.I) and "test-checkpoint" in report["next"], report


def test_status_and_continuation_say_the_unit_has_no_tests(tmp_path):
    """Red. Status and the continuation's implement progress say the unit has no tests and is
    writing code."""
    root = no_tests_unit(tmp_path)
    packet = handoff.continuation(root, record(root))
    for report in (progress(root), packet["test_preparation"]):
        assert report["stage"] == "writing-code"
        assert re.search(r"no (scoped )?tests", report["next"], re.I), report


# Review round 1 findings


def add_unreviewed_test_task(root, files):
    """Add a test task to tasks.json without reopening breakdown: the accepted plan is unchanged."""
    path = root / f".fbk/{UNIT}/tasks.json"
    tasks = store.read_json(path)
    tasks.insert(0, {
        "id": "late-tests", "stage": "tests", "description": "Add tests the accepted plan never had.",
        "files": list(files), "depends_on": [], "acceptance_refs": REVIEW_REFS,
        "verification": "The late tests pass against the built code.",
        "check_expectations": [{"argv": CHECK, "exit_code": 0}],
    })
    store.atomic_json(path, tasks)


def test_an_unreviewed_test_task_does_not_change_a_recorded_preservation_outcome(tmp_path):
    """Red (finding 1). After a preservation checkpoint, a test task added to tasks.json without
    reopening breakdown leaves the outcome as recorded: the stage stays writing code, and an
    unlock of a locked test is refused with the reopen-breakdown remedy. Catches: reading the
    outcome from the live tasks.json before the recorded outcome, which let the unlock through."""
    root = preservation_unit(tmp_path)
    assert checkpoint(root) is None
    assert stage(root) == "writing-code"
    add_unreviewed_test_task(root, [PROTECT])
    grants = record(root)["grants"]
    message = unlock_message(root, [PROTECT])
    assert message is not None, "An unlock was approved on a test task the accepted plan never had."
    assert "breakdown" in message.lower(), message
    assert record(root)["unlocks"] == [] and record(root)["grants"] == grants
    # Any tasks.json edit makes breakdown stale, so the checkpoint, whose revision covers the
    # accepted breakdown, is no longer current; preservation ignores the live test task, so the
    # unit is ready for the checkpoint again, not writing tests.
    assert stage(root) == "ready-for-checkpoint", "An unreviewed test task changed the recorded outcome's stage."


def test_an_unreviewed_test_task_does_not_change_a_recorded_no_tests_outcome(tmp_path):
    """Red (finding 1). In the no-tests outcome, a test task added to tasks.json without
    reopening breakdown leaves the unit writing code; the checkpoint is still refused as having
    no tests, and an unlock is refused with the reopen-breakdown remedy."""
    root = no_tests_unit(tmp_path)
    build_code(root)
    add_unreviewed_test_task(root, [NEW])
    assert stage(root) == "writing-code", "An unreviewed test task changed the recorded outcome's stage."
    message = unlock_message(root, [NEW])
    assert message is not None and "breakdown" in message.lower(), message
    assert record(root)["unlocks"] == []


def find_key(value, key):
    """Every value stored under ``key`` anywhere in a JSON structure."""
    found = []
    if isinstance(value, dict):
        for name, item in value.items():
            if name == key:
                found.append(item)
            found += find_key(item, key)
    elif isinstance(value, list):
        for item in value:
            found += find_key(item, key)
    return found


def test_no_tests_reviewer_packet_carries_no_superseded_lock_discipline(tmp_path, monkeypatch):
    """Red (finding 2). After a preservation checkpoint, a breakdown reopen and a no-tests
    re-entry, the implementation reviewer's actual packet presents no locked files: the lock it
    would describe was cleared with the reopen."""
    from tests.test_workflow_review_only_requirements import assess

    root = preservation_unit(tmp_path, tests=(OTHER,))
    assert checkpoint(root) is None
    reopen(root, "breakdown")
    (root / OTHER).unlink()
    accept_breakdown(root)
    enter_implement(root, "Proceed with the replanned work.")
    assert stage(root) == "writing-code"
    build_code(root)
    readers = Readers(monkeypatch, native={"assessments": [
        assess(f"{SPEC_PATH}#cancel-docstring"), assess(f"{SPEC_PATH}#cancel-naming")]})
    message = refusal(close.close_phase, root, UNIT, "implement", "s")
    assert readers.prompts.get("native"), f"The implementation reviewer never ran: {message}"
    packet = packet_of(readers.prompts["native"][0])
    stale = [item for item in find_key(packet, "test_discipline") if item]
    stale += [item for item in find_key(packet, "locked_files") if item]
    assert not stale, f"The no-tests reviewer packet carries the superseded lock: {stale}"


def test_no_tests_write_hook_refusal_of_a_new_region_names_the_file_and_the_remedy(tmp_path):
    """Red (finding 3). In a regions-only no-tests unit, the write hook refuses an implementation
    worker adding a test region to its own file, naming the file and directing it to omit the
    region or reopen breakdown; it says nothing of locks or unlock-test, which this outcome has
    none of."""
    from tests.test_workflow_test_regions import write

    root = no_tests_unit(tmp_path, regions=True)
    assert start(root) is None
    message = write(root, "implementer", "src/app.py", REGION_CODE)
    assert message is not None, "The write hook let an implementer add a test region."
    lowered = message.lower()
    assert "src/app.py" in message, f"The refusal does not name the file: {message}"
    assert "breakdown" in lowered and re.search(r"omit|without|remove|leave out", lowered), message
    assert "unlock" not in lowered and "locked" not in lowered, f"The refusal speaks of locks: {message}"


def entry_comparison(root, tmp_path):
    reader = tmp_path / "reader"
    reader.mkdir()
    available = {}
    provenance = review_baseline.prepare(root, reader, record(root), "implement", available)
    return provenance, reader


def test_no_tests_comparison_tree_holds_the_entry_code_not_the_built_code(tmp_path):
    # Guard: passes with the step 9b build; pins its choice of the entry baseline.
    """Guard (finding 6). The comparison tree the implement reviewer gets in the no-tests
    outcome holds the code as it was at implement entry, not the code the task built. Catches:
    copying the current tree, which hides the whole change from comparison."""
    root = no_tests_unit(tmp_path)
    build_code(root)
    provenance, reader = entry_comparison(root, tmp_path)
    assert provenance["status"] == "available", provenance
    copied = (reader / review_baseline.PREFIX / "src/app.py").read_text()
    assert copied == ORIGINAL_CODE and copied != DOCUMENTED_CODE


def test_no_tests_missing_baseline_copy_marks_the_comparison_unavailable_without_the_checkpoint_remedy(tmp_path):
    """Red (findings 4 and 6). With the entry baseline's copy of src/app.py missing, the
    comparison is unavailable with a reason naming the no-tests outcome and the missing copy,
    and no instruction to run test-checkpoint, which this outcome refuses."""
    from fbk.workflow import test_preparation

    root = no_tests_unit(tmp_path)
    build_code(root)
    test_preparation.copy_path(root / f".fbk/{UNIT}" / store.BASELINE_FOLDER, "src/app.py").unlink()
    provenance, _ = entry_comparison(root, tmp_path)
    assert provenance["status"] == "unavailable", provenance
    reason = provenance.get("reason", "")
    assert re.search(r"no (scoped )?tests|no test tasks?", reason, re.I), f"The reason does not name the outcome: {reason}"
    assert "src/app.py" in reason, f"The reason does not name the missing copy: {reason}"
    assert "test-checkpoint" not in reason and "checkpoint cannot" not in reason, (
        f"The reason gives the checkpoint's remedy: {reason}")


def preservation_packet(root, monkeypatch):
    readers = Readers(monkeypatch, native={})
    message = refusal(close.close_checkpoint, root, UNIT, "s")
    assert readers.prompts.get("native"), f"The checkpoint reviewer never ran: {message}"
    return packet_of(readers.prompts["native"][0])


def test_preservation_reviewer_must_confirm_every_scoped_test_ran_and_passed(tmp_path, monkeypatch):
    # Guard: passes with the step 9b build; pins obligations the first prompt test did not.
    """Guard (finding 5). The preservation reviewer is told to confirm from the saved output that
    every scoped test ran and passed, with a missing, skipped or failing test a blocker, and the
    production files the implementation tasks own are required reading."""
    root = preservation_unit(tmp_path)
    packet = preservation_packet(root, monkeypatch)
    obligations = packet["reading_priority"]["acceptance_obligations"]
    confirm = [o for o in obligations if re.search(r"saved output", o, re.I)
               and re.search(r"every scoped test", o, re.I) and re.search(r"pass", o, re.I)]
    assert confirm, f"No obligation demands every scoped test ran and passed: {obligations}"
    assert all(re.search(word, confirm[0], re.I) for word in (r"missing", r"skipped", r"failing", r"blocker")), confirm[0]
    required = [path for group in packet["required_files"].values() for path in group]
    assert any(str(path).endswith("src/app.py") for path in required), (
        f"The implementation task's production file is not required reading: {required}")


def test_an_all_review_only_unit_with_a_test_task_follows_the_normal_flow(tmp_path):
    # Guard: passes with the step 9b build; the outcome follows the plan, not the requirements.
    """Guard (finding 7). An all-review-only unit whose accepted plan has a test task starts in
    writing tests, needs that task's completed run, then the checkpoint and its locks before code
    and implementation close. Catches: choosing preservation or no-tests because every
    requirement is review-only."""
    test_task = {
        "id": "keep-tests", "stage": "tests", "description": "Keep the cancel behavior protected.",
        "files": [PROTECT], "depends_on": [], "acceptance_refs": REVIEW_REFS,
        "verification": "A cancel that stops returning true fails the check.",
        "check_expectations": [{"argv": CHECK, "exit_code": 0}],
    }
    root = implement_entered(review_only_unit(tmp_path / "p", tasks=[test_task, code_task()]))
    assert stage(root) == "writing-tests"
    assert start(root) is not None, "An implementation task started before the test task ran."
    assert close_implement(root) is not None, "Implement closed before the test task and checkpoint."
    scenarios.run_test_tasks(root)
    assert stage(root) == "ready-for-checkpoint"
    assert close_implement(root) is not None, "Implement closed before the checkpoint."
    assert checkpoint(root) is None
    assert set(record(root)["locks"]) == {PROTECT, OTHER}
    build_code(root)
    assert close_implement(root) is None


def test_preservation_production_change_through_the_shell_gets_a_remedy_without_test_tasks(tmp_path):
    """Red (finding 8, intent check). In the preservation outcome a production file changed
    through the shell between implement entry and the checkpoint is refused, naming it, with a
    remedy that fits a unit with no test task (revert it, or reopen breakdown), never reworking
    it through a test task."""
    root = preservation_unit(tmp_path)
    (root / "src/app.py").write_text(DOCUMENTED_CODE)
    message = checkpoint(root)
    assert message is not None, "The checkpoint accepted an undeclared production change."
    assert "src/app.py" in message, message
    lowered = message.lower()
    assert "breakdown" in lowered or re.search(r"restore|revert", lowered), message
    assert not re.search(r"through a test task|test task that declares", lowered), (
        f"The remedy sends a unit with no test task to a test task: {message}")
    assert record(root)["locks"] == {}


# Review round 2 findings


EXTRA = "src/extra.py"


def held_locks(root):
    """Locked paths holding a test; an empty region's lock entry holds none."""
    from fbk.workflow import evidence

    return {path for path, value in record(root)["locks"].items() if value != evidence.EMPTY_REGION}


def test_a_verified_deletion_of_an_empty_region_file_is_not_a_removed_scoped_test(tmp_path):
    """Red (round 2, finding 1). A preservation unit whose region-bearing source file holds no
    test region at entry passes its checkpoint; a governing decision then makes the checkpoint
    stale and re-records the baseline while the implementation task that owns that file runs;
    the task deletes the file and finishes verified. The re-run checkpoint accepts: an empty
    region removed is no scoped test removed, and the deletion is the running task's verified
    change. Catches: counting every path missing from the baseline's region list as a removed
    test."""
    from tests.test_workflow_test_checkpoint import DECIDED, record_decision, write_decision_sources

    root = review_only_unit(tmp_path / "p", tasks=[{**code_task(), "files": ["src/app.py", EXTRA]}])
    path = root / f".fbk/{UNIT}/scope.json"
    store.atomic_json(path, {**store.read_json(path),
                             "test_regions": [{"files": [EXTRA], "start": REGION_START}]})
    (root / EXTRA).write_text("def extra():\n    return 1\n")
    implement_entered(root)
    assert checkpoint(root) is None
    assert held_locks(root) == {PROTECT, OTHER}
    assert start(root) is None
    write_decision_sources(root)
    record_decision(root, "release-once", DECIDED)
    assert stage(root) != "writing-code", "The governing decision did not make the checkpoint stale."
    reasons = [e.get("reason") for e in record(root)["events"] if e["event"] == "writing-tests-baseline-recorded"]
    assert len(reasons) == 2, f"The governing decision did not re-record the baseline: {reasons}"
    (root / EXTRA).unlink()
    returned = finish(root, changed=(EXTRA,))
    assert returned["status"] == "completed", returned
    assert stage(root) == "ready-for-checkpoint"
    message = checkpoint(root)
    assert message is None, f"The re-run checkpoint refused the verified deletion of an empty-region file: {message}"
    assert held_locks(root) == {PROTECT, OTHER}


def test_no_tests_write_hook_refusal_of_a_new_test_file_names_the_file_and_the_remedy(tmp_path):
    """Red (round 2, finding 2). In the no-tests outcome, an assigned implementation worker
    writing a new whole-file scoped test gets the no-tests refusal naming the file, with the
    remedy to leave it out or reopen breakdown, not only the ownership message."""
    from tests.test_workflow_test_regions import write

    root = no_tests_unit(tmp_path)
    assert start(root) is None
    message = write(root, "implementer", NEW, PASSING_TEST)
    assert message is not None, "The write hook let an implementer write a test file."
    lowered = message.lower()
    assert NEW in message, f"The refusal does not name the file: {message}"
    assert "breakdown" in lowered and re.search(r"omit|without|remove|leave (it )?out", lowered), message
    assert "unlock" not in lowered and "locked" not in lowered, f"The refusal speaks of locks: {message}"


def test_preservation_with_one_failing_check_of_two_runs_both_and_names_the_failure(tmp_path):
    # Guard: passes with the step 9b build; pins that every declared check must pass.
    """Guard (round 2, finding 3). Two declared checks, the first failing and the second
    passing: both run with saved output, the refusal names the failing one, and neither
    acceptance nor locks are recorded. Catches: accepting preservation when any check passes."""
    failing = [sys.executable, OTHER]
    root = review_only_unit(tmp_path / "p")
    (root / OTHER).write_text("assert False, 'other broke'\n")
    path = root / f".fbk/{UNIT}/scope.json"
    store.atomic_json(path, {**store.read_json(path), "checks": [failing, CHECK]})
    implement_entered(root)
    message = checkpoint(root)
    assert message is not None, "A preservation checkpoint passed with one of two checks failing."
    assert OTHER in message, f"The refusal does not name the failing check: {message}"
    attempt = [e for e in record(root)["events"] if e["event"] == "close-attempt" and e.get("phase") == CK][-1]
    ran = {tuple(c["argv"]): c for c in attempt.get("verification") or []}
    assert set(ran) == {tuple(failing), tuple(CHECK)}, f"Not every declared check ran: {sorted(ran)}"
    assert ran[tuple(failing)]["exit_code"] != 0 and ran[tuple(CHECK)]["exit_code"] == 0
    assert all(c.get("saved_output") for c in ran.values()), "A check's output was not saved."
    state = record(root)
    assert state["locks"] == {} and not state["phases"][CK]["evidence"]


# Review round 3 findings


EXTRA_CODE = "def extra():\n    return 1\n"
EXTRA_REGION = EXTRA_CODE + "# --- tests ---\nassert extra() == 1\n"


def edit_scope(root, **fields):
    path = root / f".fbk/{UNIT}/scope.json"
    store.atomic_json(path, {**store.read_json(path), **fields})


def with_extra_region(root, holds_tests):
    """Declare src/extra.py a region-bearing source file owned by the implementation task;
    its region holds a test at entry only when ``holds_tests``. With ``holds_tests`` None the
    file does not exist yet, and the spec declares it in creates."""
    edit_scope(root, test_regions=[{"files": [EXTRA], "start": REGION_START}])
    if holds_tests is None:
        edit_scope(root, creates=[EXTRA])
    else:
        (root / EXTRA).write_text(EXTRA_REGION if holds_tests else EXTRA_CODE)
    store.atomic_json(root / f".fbk/{UNIT}/tasks.json", with_refactor([{**code_task(), "files": ["src/app.py", EXTRA]}]))
    return root


KEEP_TESTS = {
    "id": "keep-tests", "stage": "tests", "description": "Protect the cancel behavior with a test.",
    "files": [PROTECT], "depends_on": [], "acceptance_refs": REVIEW_REFS,
    "verification": "A cancel that stops returning true fails the check.",
    "check_expectations": [{"argv": CHECK, "exit_code": 0}],
}


def plan_with_test_task(root):
    store.atomic_json(root / f".fbk/{UNIT}/tasks.json", with_refactor([KEEP_TESTS, code_task()]))


def write_protecting_test(root):
    (root / PROTECT).write_text(PROTECTING_TEST)
    return [PROTECT]


def baseline_events(root):
    return [i for i, e in enumerate(record(root)["events"]) if e["event"] == "writing-tests-baseline-recorded"]


def assert_normal_flow_after_replan(root, entered_at, code=DOCUMENTED_CODE):
    """After re-entering implement on a plan with a test task: writing tests, a baseline
    recorded at this entry, implementation refused until the test task completes and the
    checkpoint locks, and implementation close needing the checkpoint."""
    assert stage(root) == "writing-tests", "The re-entered unit kept the earlier no-tests outcome."
    assert any(i > entered_at for i in baseline_events(root)), "No writing-tests baseline was recorded at re-entry."
    assert start(root) is not None, "An implementation task started before the test task ran."
    assert close_implement(root) is not None, "Implement closed before the test task and checkpoint."
    scenarios.run_test_tasks(root, {"keep-tests": write_protecting_test})
    assert stage(root) == "ready-for-checkpoint"
    assert start(root) is not None, "An implementation task started before the checkpoint."
    assert close_implement(root) is not None, "Implement closed before the checkpoint."
    assert checkpoint(root) is None
    assert set(record(root)["locks"]) == {PROTECT} and record(root).get("lock_origin") == CK
    assert stage(root) == "writing-code"
    build_code(root, code)
    assert close_implement(root) is None


def no_tests_unit_declaring_a_future_test(tmp_path):
    """A no-tests unit whose spec already declares tests/check.py in creates, so a later plan
    can give a test task that file without changing the spec."""
    root = review_only_unit(tmp_path / "p", tests=())
    edit_scope(root, creates=[PROTECT])
    return implement_entered(root)


@pytest.mark.parametrize("built", [False, True], ids=["before-code", "after-code"])
def test_a_spec_contradiction_repair_re_decides_a_no_tests_unit(tmp_path, built):
    """Red (round 3, finding 1). A contradiction repair of spec invalidates breakdown and
    implement; with breakdown re-closed on a plan that has a test task, re-entering implement
    takes the normal flow and records a new writing-tests baseline. Lead ruling: such a repair
    counts as replanning, as a breakdown-or-earlier reopen does. Catches: keeping the no-tests
    exemption because no reopen event was recorded."""
    from fbk.workflow import repair
    from tests.test_workflow_repairs import authorize

    root = no_tests_unit_declaring_a_future_test(tmp_path)
    if built:
        build_code(root)
    authorize(root)
    repair.apply(root, UNIT, "s", {
        "kind": "contradiction", "path": SPEC_PATH,
        "before": "Public cancellation functions start with cancel.",
        "after": "Public cancellation functions start with cancel. Cancel returns true once.",
        "decision_id": "cancel-return",
    }, verifier=lambda *a: {"status": "equivalent", "evidence": "The quoted source settles it."})
    state = record(root)
    assert not state["phases"]["breakdown"]["evidence"] and not state["phases"]["implement"]["evidence"]
    scenarios.accept(root, "spec")
    plan_with_test_task(root)
    accept_breakdown(root)
    enter_implement(root, "Proceed with the repaired plan.")
    entered = max(i for i, e in enumerate(record(root)["events"])
                  if e["event"] == "entered" and e.get("phase") == "implement")
    # After code was built, the rebuild writes different content so its finish sees a change.
    rebuilt = DOCUMENTED_CODE.replace("once.", "exactly once.") if built else DOCUMENTED_CODE
    assert_normal_flow_after_replan(root, entered - 1, rebuilt)


def test_reopening_breakdown_onto_a_plan_with_a_test_task_leaves_the_no_tests_outcome(tmp_path):
    # Guard: passes with the step 9b build; pins what round 3 found untested.
    """Guard (round 3, finding 3). No-tests, then a breakdown reopen and an accepted plan
    with a test task: re-entry writes no replacement outcome, and the earlier exemption must not
    survive. The unit writes tests, needs the task's completion, the checkpoint's acceptance and
    its locks before implementation proceeds. Catches: an outcome reader that ignores reopens."""
    root = no_tests_unit_declaring_a_future_test(tmp_path)
    reopen(root, "breakdown")
    plan_with_test_task(root)
    accept_breakdown(root)
    enter_implement(root, "Proceed with the replanned work.")
    entered = max(i for i, e in enumerate(record(root)["events"])
                  if e["event"] == "entered" and e.get("phase") == "implement")
    assert_normal_flow_after_replan(root, entered - 1)


def test_preservation_write_hook_refusal_of_a_new_region_names_the_file_and_the_remedy(tmp_path):
    """Red (round 3, finding 2). After a preservation checkpoint, an implementation worker
    creating its owned production file with a test region is refused, naming the file and saying
    to leave the test out or reopen breakdown; no unlock wording, since this outcome refuses
    unlocks and has no test task."""
    from tests.test_workflow_test_regions import write

    root = implement_entered(with_extra_region(review_only_unit(tmp_path / "p"), holds_tests=None))
    assert checkpoint(root) is None
    assert start(root) is None
    message = write(root, "implementer", EXTRA, EXTRA_REGION)
    assert message is not None, "The write hook let an implementer add a test region."
    lowered = message.lower()
    assert EXTRA in message, f"The refusal does not name the file: {message}"
    assert "breakdown" in lowered and re.search(r"omit|without|remove|leave (the test |it )?out", lowered), message
    assert "unlock" not in lowered, f"The refusal sends the worker to an unlock: {message}"


def test_preservation_checkpoint_refuses_a_removed_test_region(tmp_path):
    # Guard: passes with the step 9b build; pins what round 3 found untested.
    """Guard (round 3, finding 4). A preservation unit whose region-bearing file held a
    test region at entry has that region removed (the code above kept) before the checkpoint:
    the checkpoint refuses, naming the file, and records no acceptance or locks. Catches: a
    preservation refusal that compares whole-file tests only."""
    root = implement_entered(with_extra_region(review_only_unit(tmp_path / "p"), holds_tests=True))
    assert stage(root) == "ready-for-checkpoint"
    (root / EXTRA).write_text(EXTRA_CODE)
    message = checkpoint(root)
    assert message is not None, "The checkpoint accepted a removed test region."
    assert EXTRA in message, f"The refusal does not name the region-bearing file: {message}"
    state = record(root)
    assert state["locks"] == {} and not state["phases"][CK]["evidence"]


# Review round 4 finding, fixed when a breakdown-invalidating repair began clearing the locks


def test_followup_a_decision_between_a_repair_and_re_entry_keeps_the_preservation_outcome(tmp_path):
    """A preservation checkpoint passes; a contradiction repair of spec replans the unit; another
    governing decision is recorded before implement is re-entered. The repair clears the locks,
    so that decision records no baseline that would hide the replan. Re-entry must still record the preservation outcome,
    and the next checkpoint must refuse a failing declared check instead of taking it as red."""
    from fbk.workflow import decisions, repair
    from tests.test_workflow_test_checkpoint import DECIDED, record_decision, write_decision_sources

    root = preservation_unit(tmp_path)
    # The repair's authority is recorded before the pass, so no baseline follows the pass yet.
    # Its decision governs implement, so recording it leaves the accepted spec current.
    (root / "authority.md").write_text(
        "The operator authorizes routine reference and contradiction repairs.\nCancel returns true once.")
    with store.transaction(root):
        state = store.load(root, UNIT)
        decisions.policy(root, state, "s", {"classes": ["reference", "contradiction"], "source": {
            "path": "authority.md",
            "quote": "The operator authorizes routine reference and contradiction repairs."}})
        store.save(root, state)
    record_decision(root, "cancel-return", "Cancel returns true once.", path="authority.md")
    assert checkpoint(root) is None
    repair.apply(root, UNIT, "s", {
        "kind": "contradiction", "path": SPEC_PATH,
        "before": "Public cancellation functions start with cancel.",
        "after": "Public cancellation functions start with cancel. Cancel returns true once.",
        "decision_id": "cancel-return",
    }, verifier=lambda *a: {"status": "equivalent", "evidence": "The quoted source settles it."})
    write_decision_sources(root)
    record_decision(root, "release-once", DECIDED)
    # Built before re-entry, so the entry baseline holds it: the unchanged protecting test now fails.
    (root / "src/app.py").write_text("def cancel():\n    return False\n")
    scenarios.accept(root, "spec")
    accept_breakdown(root)
    enter_implement(root, "Proceed with the repaired plan.")
    assert engine.test_outcome(root, record(root)) == "preservation", (
        "Re-entering implement after the repair did not record the preservation outcome.")
    locked = [e for e in record(root)["events"] if e["event"] == "tests-locked"]
    message = checkpoint(root)
    assert message is not None and "preservation" in message.lower(), (
        f"The checkpoint took a failing check as red instead of refusing it: {message}")
    state = record(root)
    assert not state["phases"][CK]["evidence"]
    assert [e for e in state["events"] if e["event"] == "tests-locked"] == locked
