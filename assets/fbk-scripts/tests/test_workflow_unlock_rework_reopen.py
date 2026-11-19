"""Rework and reopen around the test checkpoint (build step 4b).

An unlock approval carries, per named test, whether its corrected form is expected to fail
(behavior not yet built) or pass (preservation), and the rework commands: argument arrays,
each listing the named tests it covers. A command's expected exit is derived (zero when
every covered test is expected to pass, non-zero otherwise), never stated; every named test
is covered; each owning test task's rework run gets the commands covering its own tests, in
place of the commands in ``tasks.json``. Approving the unlock clears the checkpoint's
acceptance. The writing-tests baseline is re-recorded whenever the unit returns to writing
tests (an unlock approval, a governing change that makes an accepted checkpoint stale, and
re-entry into implement after a breakdown-or-earlier reopen); implementation tasks running
at that moment keep their owned-file exemption once they complete with verified changes.
Reopening breakdown or an earlier phase clears the locks and the checkpoint. A test task
whose tests are unchanged since the previous accepted checkpoint completes even when its
check now passes, carrying that checkpoint's red forward. A checkpoint run after an earlier
acceptance makes no mechanical red demand of whole-unit checks; the reviewer judges from
fresh and carried output.

The tests assume these shapes:

- **Approval.** ``engine.approve(..., "unlock-test", "implement", reason, tests=[...],
  rework={"expected": {path: "fail" | "pass"}, "commands": [{"argv": [...], "tests":
  [...]}]})``, through the shared ``approve_unlock`` helper in the lifecycle tests. On the
  command line, ``approve ... unlock-test --tests ... --request <file>`` with the JSON
  ``{"expected": ..., "commands": ...}``.
- **Carried-forward red.** The reviewer's prompt payload names the tests unchanged since
  the previous accepted checkpoint under a key containing "carried" or "unchanged_since"
  (a list of paths, a list of objects with a "path", or a mapping keyed by path), and the
  previous accepted checkpoint's saved output is in its required_files. A carried-forward
  task run is marked by a key containing "carried" in its return or its task-returned event.
- **Governing change.** The re-record happens no later than the first stage derivation
  after the decision is recorded.
"""

import json
import os
import shutil
import sys

import pytest

from fbk.workflow import close, engine, evidence, handoff, review, store
from .test_workflow_checkpoint_review_inputs import (
    PASSING_TEST,
    UNIT,
    comparison,
    native_capture,
    payload,
)
from .test_workflow_commands import call
from .test_workflow_implement_stages import CHECK, REFS, edit_scope, refusal, stage, start
from .test_workflow_lifecycle import (
    accept,
    approve_unlock,
    clean_review,
    enter,
    enter_implementation,
    mutate,
    observe_phase,
    prepare_implementation,
    project as workflow_project,
    run_test_tasks,
)
from .test_workflow_test_checkpoint import (
    CK,
    DECIDED,
    REDECIDED,
    checkpoint_refusal,
    counting,
    parses,
    record_decision,
    required_reading,
    scoped_test_hashes,
    work,
    write_decision_sources,
)
from .refactor_plan import complete_refactor_tasks, with_refactor

project = workflow_project


# A runner that reports each test by name, optionally scoped to the paths it is given, and
# prints a label so each checkpoint run's saved output can be told apart.
RUNNER_SCRIPT = (
    "import pathlib, runpy, sys\n"
    "label = pathlib.Path('run-label')\n"
    "if label.exists():\n"
    "    print('RUN', label.read_text().strip())\n"
    "paths = sys.argv[1:] or sorted(p.as_posix() for p in pathlib.Path('tests').glob('*.py'))\n"
    "failed = False\n"
    "for path in paths:\n"
    "    try:\n"
    "        runpy.run_path(path)\n"
    "        print('PASSED', path)\n"
    "    except Exception as exc:\n"
    "        failed = True\n"
    "        print('FAILED', path, type(exc).__name__, exc)\n"
    "sys.exit(1 if failed else 0)\n"
)
RUNNER = [sys.executable, "-c", RUNNER_SCRIPT]


def runner(*paths):
    return [*RUNNER, *paths]


RELEASE, REPORT, OTHER = "tests/check.py", "tests/report_check.py", "tests/other_check.py"
FIRST_RUN, SECOND_RUN = "FIRST-CHECKPOINT-RUN", "SECOND-CHECKPOINT-RUN"

LOCKED = {
    RELEASE: "from pathlib import Path\nassert Path('src/app.py').read_text() == 'release()', 'release is missing'\n",
    REPORT: "from pathlib import Path\nassert Path('src/report.py').read_text() == 'report(1)', 'report is missing'\n",
    OTHER: "from pathlib import Path\nassert Path('src/other.py').read_text() == 'other()', 'other is missing'\n",
}
CORRECTED = {
    # Expected to pass: the release is already built.
    RELEASE: "from pathlib import Path\nassert Path('src/app.py').read_text().startswith('release('), 'not released'\n",
    # Expected to fail: the report is not built yet.
    REPORT: "from pathlib import Path\nassert Path('src/report.py').read_text() == 'report()', 'no report yet'\n",
}
EXPECTED = {RELEASE: "pass", REPORT: "fail"}
COMMANDS = [
    {"argv": runner(RELEASE), "tests": [RELEASE]},
    {"argv": runner(REPORT), "tests": [REPORT]},
]
UTIL_CHECK = [sys.executable, "-c",
              "from pathlib import Path; assert Path('src/util.py').read_text() == 'util()'"]


# Helpers


def plan_three_tests(root, split=False, report_argv=None, adjust=None):
    """Three tests written by test tasks, three implementation-owned production files, and
    a whole-unit runner that names each test. The test files exist as placeholders the test
    tasks migrate. Split, a second test task owns the report test."""
    for path in (REPORT, OTHER):
        (root / path).write_text(PASSING_TEST)
    for path in ("src/report.py", "src/other.py", "src/util.py"):
        (root / path).write_text("pass")
    edit_scope(root, checks=[RUNNER])

    def task(task_id, stage_name, files, description, verification, argv, code):
        return {"id": task_id, "stage": stage_name, "description": description, "files": files,
                "depends_on": [], "acceptance_refs": REFS, "verification": verification,
                "check_expectations": [{"argv": argv, "exit_code": code}]}

    tests = [task("prepare-tests", "tests", [RELEASE, OTHER] if split else [RELEASE, REPORT, OTHER],
                  "Check release and the other behavior.",
                  "Each test fails until its behavior is built.", RUNNER, "nonzero")]
    if split:
        tests.append(task("report-tests", "tests", [REPORT], "Check reporting.",
                          "The report test fails until reporting is built.", report_argv or runner(REPORT),
                          "nonzero"))
    planned = [
        *tests,
        task("cancel", "implementation", ["src/app.py"], "Implement release.",
             "The release test passes unchanged.", runner(RELEASE), 0),
        task("tidy", "implementation", ["src/util.py"], "Tidy the utility module.",
             "The utility module holds util().", UTIL_CHECK, 0),
    ]
    if adjust:
        adjust({t["id"]: t for t in planned})
    store.atomic_json(root / ".fbk/feature/tasks.json", with_refactor(planned))


def writes(contents):
    def write(root):
        for path, text in contents.items():
            (root / path).write_text(text)
        return sorted(contents)

    return write


def finish(root, task, changed, argv):
    result = review.run_command(argv, root, 30)
    returned = mutate(root, handoff.finish_task, "s", task, changed_files=changed,
                      checks=[{"argv": argv, "exit_code": result["exit_code"],
                               "evidence": (result["stdout"] or result["stderr"] or "The check ran.")[-500:]}],
                      unresolved=[], outcome="The task's change is in place.")
    assert returned["status"] == "completed", returned
    return returned


def code_after_checkpoint(root, app_mode=None, split=False, report_argv=None, adjust=None):
    """The three tests are written and locked by the checkpoint, and the release task
    completes a verified release."""
    plan_three_tests(root, split=split, report_argv=report_argv, adjust=adjust)
    (root / "run-label").write_text(FIRST_RUN)
    enter_implementation(root)
    if split:
        work_by_task = {"prepare-tests": writes({p: LOCKED[p] for p in (RELEASE, OTHER)}),
                        "report-tests": writes({REPORT: LOCKED[REPORT]})}
    else:
        work_by_task = {"prepare-tests": writes(LOCKED)}
    run_test_tasks(root, work_by_task)
    assert checkpoint_refusal(root) is None
    assert stage(root) == "writing-code"
    assert start(root, "cancel", "implementer") is None
    (root / "src/app.py").write_text("release()")
    if app_mode is not None:
        os.chmod(root / "src/app.py", app_mode)
    finish(root, "cancel", ["src/app.py"], runner(RELEASE))


def unlock_with_tidy_running(root):
    """An accepted checkpoint, written release code, a tidy task running with a partial
    change, then the operator's unlock of two tests: one expected to pass, one to fail."""
    code_after_checkpoint(root)
    assert start(root, "tidy", "tidy-worker") is None
    (root / "src/util.py").write_text("partial")
    approve_unlock(root, EXPECTED, COMMANDS)


def rework(root, contents, commands=COMMANDS, task="prepare-tests", worker="rework-author"):
    """Relaunch a test task, correct its named tests, and finish through the real handoff
    with the given commands reported."""
    packet = mutate(root, handoff.start_task, "s", task, worker)
    for path, text in contents.items():
        (root / path).write_text(text)
    results = [review.run_command(c["argv"], root, 30) for c in commands]
    returned = handoff.complete_task(
        root, "feature", "s", task, changed_files=sorted(contents),
        checks=[{"argv": c["argv"], "exit_code": r["exit_code"],
                 "evidence": (r["stdout"] or r["stderr"] or "The command ran.")[-500:]}
                for c, r in zip(commands, results)],
        unresolved=[], outcome="The named tests are corrected.")
    return packet, returned


def baseline_bytes(root, relative):
    return (root / UNIT / store.BASELINE_FOLDER / relative).read_bytes()


def baseline_files(root):
    return store.load(root, "feature")["writing_tests_baseline"]["files"]


def current_hash(root, relative):
    return evidence.file_hashes(root, [relative])[relative]


def keys(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from keys(item)


def carried(prompt):
    """The tests the reviewer is told are unchanged since the previous accepted checkpoint."""
    found = []

    def walk(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if isinstance(key, str) and ("carried" in key.lower() or "unchanged_since" in key.lower()):
                    found.append(item)
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(payload(prompt))
    assert found, "The reviewer is not told which tests are unchanged since the previous accepted checkpoint."

    def paths(value):
        if isinstance(value, dict):
            return set(value)
        if isinstance(value, list):
            return {item if isinstance(item, str) else item.get("path") for item in value}
        return set()

    return set().union(*[paths(item) for item in found])


def required_output(capture):
    """The bytes of every required file the reader received."""
    return [capture["files"].get(path, b"") for path in required_reading(capture["prompt"])]


def governing_change(root):
    """Record a governing decision that makes the accepted checkpoint stale; deriving the
    stage afterwards sees the return to the test stages."""
    write_decision_sources(root)
    record_decision(root, "release-once", DECIDED)
    assert stage(root) != "writing-code"


# Unlock approval: what it carries and what it does


def test_unlock_approval_clears_acceptance_and_rerecords_the_baseline(project):
    code_after_checkpoint(project)
    assert start(project, "tidy", "tidy-worker") is None
    (project / "src/util.py").write_text("partial")
    kept = {k: work(project)[k] for k in ("rounds", "generation", "round_limit")}
    assert baseline_bytes(project, "src/app.py") == b"pass"
    approved_at = len(store.load(project, "feature")["events"])
    approve_unlock(project, EXPECTED, COMMANDS)
    record = store.load(project, "feature")
    # The acceptance clears; rounds, generation, and budget stay.
    assert work(project)["evidence"] is None
    assert {k: work(project)[k] for k in kept} == kept
    assert record["unlocks"] == sorted(EXPECTED)
    assert stage(project) == "writing-tests"
    # The baseline is the tree at the approval: built code, the running task's partial
    # change, and the locked tests.
    assert any(e["event"] == "writing-tests-baseline-recorded" for e in record["events"][approved_at:]), (
        "The unlock approval recorded no writing-tests baseline.")
    files = baseline_files(project)
    for path in ("src/app.py", "src/util.py", RELEASE, REPORT, OTHER):
        assert files[path] == current_hash(project, path), f"The unlock baseline does not hold {path} as approved."
    assert baseline_bytes(project, "src/app.py") == b"release()"
    assert baseline_bytes(project, "src/util.py") == b"partial"
    assert baseline_bytes(project, OTHER) == LOCKED[OTHER].encode()


def test_the_rework_run_uses_the_approval_commands_and_finishes_despite_differing_from_the_lock(project):
    unlock_with_tidy_running(project)
    tasks_before = (project / ".fbk/feature/tasks.json").read_bytes()
    packet, returned = rework(project, CORRECTED)
    # The worker is told the approval's commands, with exits derived from their tests.
    expectations = packet["check_expectations"]
    assert [item["argv"] for item in expectations] == [c["argv"] for c in COMMANDS], expectations
    assert expectations[0]["exit_code"] == 0, "A command covering only pass-expected tests must expect exit 0."
    assert expectations[1]["exit_code"] not in (0, None), "A command covering a fail-expected test must expect non-zero."
    assert returned["status"] == "completed", returned
    assert [c["argv"] for c in returned["verified_checks"]] == [c["argv"] for c in COMMANDS]
    assert returned["verified_checks"][0]["exit_code"] == 0
    assert returned["verified_checks"][1]["exit_code"] != 0
    record = store.load(project, "feature")
    assert record["locks"][RELEASE] != current_hash(project, RELEASE), "The reworked test still matches its lock."
    # tasks.json is untouched, so breakdown's acceptance stands.
    assert (project / ".fbk/feature/tasks.json").read_bytes() == tasks_before
    accepted = record["phases"]["breakdown"]["evidence"]
    assert accepted and accepted["revision"] == evidence.revision(project, record, "breakdown")
    assert stage(project) == "ready-for-checkpoint"


@pytest.mark.parametrize("miss", ["pass-expected-fails", "fail-expected-passes"])
def test_a_rework_command_that_misses_its_derived_expectation_does_not_complete(project, miss):
    unlock_with_tidy_running(project)
    contents = dict(CORRECTED)
    if miss == "pass-expected-fails":
        contents[RELEASE] = "from pathlib import Path\nassert Path('src/app.py').read_text() == 'released()'\n"
    else:
        contents[REPORT] = PASSING_TEST
    _, returned = rework(project, contents)
    assert returned["status"] != "completed", f"A rework run whose {miss} completed."
    assert stage(project) == "writing-tests"


def test_each_owning_test_task_gets_only_the_commands_covering_its_tests(project):
    code_after_checkpoint(project, split=True)
    approve_unlock(project, EXPECTED, COMMANDS)
    first = mutate(project, handoff.start_task, "s", "prepare-tests", "release-author")
    second = mutate(project, handoff.start_task, "s", "report-tests", "report-author")
    assert [item["argv"] for item in first["check_expectations"]] == [runner(RELEASE)]
    assert [item["argv"] for item in second["check_expectations"]] == [runner(REPORT)]
    assert first["check_expectations"][0]["exit_code"] == 0
    assert second["check_expectations"][0]["exit_code"] not in (0, None)


def test_the_rerun_checkpoint_accepts_the_running_implementers_changes_and_relocks(project):
    unlock_with_tidy_running(project)
    _, returned = rework(project, CORRECTED)
    assert returned["status"] == "completed", returned
    # The task running at the approval finishes its owned-file change after it.
    (project / "src/util.py").write_text("util()")
    finish(project, "tidy", ["src/util.py"], UTIL_CHECK)
    assert stage(project) == "ready-for-checkpoint"
    (project / "run-label").write_text(SECOND_RUN)
    message = checkpoint_refusal(project)
    assert message is None, message
    record = store.load(project, "feature")
    assert record["phases"][CK]["evidence"]
    assert record["locks"] == scoped_test_hashes(project)
    assert record["unlocks"] == [] and record.get("lock_origin") == CK
    assert stage(project) == "writing-code"
    # Correct code was kept, not undone to recreate red.
    assert (project / "src/app.py").read_text() == "release()"
    assert (project / "src/util.py").read_text() == "util()"


def test_the_rerun_reviewer_sees_the_split_against_the_unlock_baseline_and_carried_red(project, monkeypatch):
    unlock_with_tidy_running(project)
    rework(project, CORRECTED)
    (project / "src/util.py").write_text("util()")
    finish(project, "tidy", ["src/util.py"], UTIL_CHECK)
    (project / "run-label").write_text(SECOND_RUN)
    seen = native_capture(monkeypatch)
    message = checkpoint_refusal(project, reviewer=None)
    assert message is None, message
    prompt = seen[-1]["prompt"]
    # Measured from the unlock's baseline, only the reworked tests changed.
    changed, untouched = comparison(prompt)
    assert changed == {RELEASE, REPORT}
    assert untouched == {OTHER}
    # The test for unbuilt behavior keeps its earlier red, which the reviewer reads.
    assert carried(prompt) == {OTHER}
    outputs = required_output(seen[-1])
    assert any(f"RUN {FIRST_RUN}".encode() in data and f"FAILED {OTHER}".encode() in data for data in outputs), (
        "The previous accepted checkpoint's saved output is not required reading.")
    assert any(f"RUN {SECOND_RUN}".encode() in data for data in outputs)


def test_a_corrected_test_expected_to_pass_against_built_code_reaches_acceptance(project):
    # tasks.json still expects tests/check.py's check to fail; the approval expects it to pass.
    prepare_implementation(project)
    assert start(project, "cancel", "implementer") is None
    (project / "src/app.py").write_text("release()")
    finish(project, "cancel", ["src/app.py"], CHECK)
    commands = [{"argv": CHECK, "tests": [RELEASE]}]
    approve_unlock(project, {RELEASE: "pass"}, commands)
    corrected = ("from pathlib import Path\n"
                 "assert Path('src/app.py').read_text() == 'release()', 'the resource was not released'\n")
    _, returned = rework(project, {RELEASE: corrected}, commands=commands)
    assert returned["status"] == "completed", returned
    assert stage(project) == "ready-for-checkpoint"
    message = checkpoint_refusal(project)
    assert message is None, f"A preserved test against built code was refused: {message}"
    record = store.load(project, "feature")
    assert record["locks"] == scoped_test_hashes(project) and record.get("lock_origin") == CK
    assert (project / "src/app.py").read_text() == "release()"
    assert stage(project) == "writing-code"


def test_the_command_line_unlock_takes_the_rework_from_a_request_file(project):
    code_after_checkpoint(project)
    store.atomic_json(project / ".fbk/unlock-request.json",
                      {"expected": EXPECTED, "commands": COMMANDS})
    arguments = ["unlock-test", "--phase", "implement", "--reason", "The operator found the named tests wrong.",
                 "--tests", RELEASE, REPORT, "--request", ".fbk/unlock-request.json"]
    assert parses("approve", "feature", *arguments), "approve unlock-test takes no request file."
    call(project, "approve", "feature", *arguments)
    assert store.load(project, "feature")["unlocks"] == sorted(EXPECTED)
    packet = mutate(project, handoff.start_task, "s", "prepare-tests", "rework-author")
    assert [item["argv"] for item in packet["check_expectations"]] == [c["argv"] for c in COMMANDS]


# Unlock approval refusals


def test_an_unlock_naming_a_test_no_test_task_owns_is_refused_with_the_reopen_remedy(project):
    orphan = "tests/orphan_check.py"
    (project / orphan).write_text(PASSING_TEST)
    prepare_implementation(project)
    assert orphan in store.load(project, "feature")["locks"]
    before = store.load(project, "feature")
    message = refusal(approve_unlock, project, {orphan: "pass"},
                      [{"argv": [sys.executable, orphan], "tests": [orphan]}])
    assert message is not None, "An unlock of a test no test task owns was approved."
    assert orphan in message
    assert "reopen" in message.lower() and "breakdown" in message.lower()
    # A followable route: reopening clears every lock, so the new owner's test is locked
    # by the checkpoint after its run, never by a later unlock.
    lowered = message.lower()
    assert "test task" in lowered and "implement" in lowered and "checkpoint" in lowered, message
    assert "then unlock it" not in lowered, message
    record = store.load(project, "feature")
    assert record["grants"] == before["grants"] and record["unlocks"] == []
    assert record["phases"][CK]["evidence"] == before["phases"][CK]["evidence"]
    assert stage(project) == "writing-code"


@pytest.mark.parametrize("flaw", ["missing-expectation", "command-for-an-unnamed-test",
                                  "uncovered-named-test", "stated-inconsistent-exit"])
def test_an_unlock_with_a_flawed_rework_is_refused(project, flaw):
    code_after_checkpoint(project)
    before = store.load(project, "feature")
    attempt = {
        # Two tests named, one outcome stated.
        "missing-expectation": lambda: approve_unlock(project, {RELEASE: "pass"}, COMMANDS,
                                                      tests=[RELEASE, REPORT]),
        # A command covers a locked test the unlock does not name.
        "command-for-an-unnamed-test": lambda: approve_unlock(
            project, {RELEASE: "pass"}, [{"argv": runner(RELEASE, OTHER), "tests": [RELEASE, OTHER]}]),
        # A named test no command covers.
        "uncovered-named-test": lambda: approve_unlock(project, EXPECTED, [COMMANDS[0]]),
        # The exit is derived; a stated one contradicting the covered test is refused.
        "stated-inconsistent-exit": lambda: approve_unlock(
            project, {RELEASE: "pass"}, [{**COMMANDS[0], "exit_code": "nonzero"}]),
    }[flaw]
    assert refusal(attempt) is not None, f"An unlock with a {flaw} was approved."
    record = store.load(project, "feature")
    assert record["grants"] == before["grants"] and record["unlocks"] == []
    assert record["phases"][CK]["evidence"] == before["phases"][CK]["evidence"]


# What the re-run checkpoint exempts


@pytest.mark.parametrize("route", ["running-task-cancelled", "edit-after-the-unlock"])
def test_production_changes_no_task_running_at_the_unlock_completed_are_refused(project, route):
    # Guard of the exemption's edge: only a task running at the approval that has since
    # completed with verified changes is exempt.
    if route == "running-task-cancelled":
        unlock_with_tidy_running(project)
        (project / "src/util.py").write_text("util()")
        mutate(project, handoff.cancel_task, "s", "tidy", "Stopped before finishing.")
        path = "src/util.py"
    else:
        code_after_checkpoint(project)
        approve_unlock(project, EXPECTED, COMMANDS)
        (project / "src/app.py").write_text("release()  # edited after the unlock\n")
        path = "src/app.py"
    rework(project, CORRECTED)
    reviewer, calls = counting(lambda: pytest.fail("unreachable"))
    message = checkpoint_refusal(project, reviewer)
    assert message is not None and path in message, f"A {route} change was exempted: {message}"
    assert calls == []


def test_an_earlier_verified_mode_change_is_inside_the_unlock_baseline(project):
    # The implementation task's executable-bit change predates the unlock, so the re-run
    # checkpoint compares against a baseline that already holds it.
    (project / "src/app.py").chmod(0o644)
    code_after_checkpoint(project, app_mode=0o755)
    approve_unlock(project, {RELEASE: "pass"}, [COMMANDS[0]])
    _, returned = rework(project, {RELEASE: CORRECTED[RELEASE]}, commands=[COMMANDS[0]])
    assert returned["status"] == "completed", returned
    message = checkpoint_refusal(project)
    assert message is None, f"A change inside the unlock baseline was refused: {message}"


# A governing change that makes the accepted checkpoint stale


def test_a_governing_change_rerecords_the_baseline_and_exempts_the_running_task(project):
    code_after_checkpoint(project)
    assert start(project, "tidy", "tidy-worker") is None
    (project / "src/util.py").write_text("partial")
    governing_change(project)
    # The return to the test stages re-recorded the baseline over the built code and the
    # running task's partial change.
    assert baseline_bytes(project, "src/app.py") == b"release()", "The governing change kept the old baseline."
    assert baseline_bytes(project, "src/util.py") == b"partial"
    # The running task's later verified change is exempt at the re-run.
    (project / "src/util.py").write_text("util()")
    finish(project, "tidy", ["src/util.py"], UTIL_CHECK)
    assert stage(project) == "ready-for-checkpoint"
    message = checkpoint_refusal(project)
    assert message is None, message
    record = store.load(project, "feature")
    assert record["locks"] == scoped_test_hashes(project) and record.get("lock_origin") == CK
    assert (project / "src/app.py").read_text() == "release()"


def test_an_edit_by_no_running_task_after_a_governing_change_is_refused(project):
    # Guard (passes now): an edit after the re-record that no running task made.
    code_after_checkpoint(project)
    governing_change(project)
    (project / "src/app.py").write_text("release()  # edited after the governing change\n")
    reviewer, calls = counting(clean_review)
    message = checkpoint_refusal(project, reviewer)
    assert message is not None and "src/app.py" in message
    assert calls == []


def test_a_rerun_after_acceptance_makes_no_red_demand_of_whole_unit_checks(project):
    # tasks.json expects the whole-unit check to fail; once release is built it passes. The
    # re-run reaches the reviewer, who judges from fresh and carried output.
    prepare_implementation(project)
    assert start(project, "cancel", "implementer") is None
    (project / "src/app.py").write_text("release()")
    finish(project, "cancel", ["src/app.py"], CHECK)
    governing_change(project)
    assert stage(project) == "ready-for-checkpoint"
    assert review.run_command(CHECK, project, 10)["exit_code"] == 0
    reviewer, calls = counting(clean_review)
    message = checkpoint_refusal(project, reviewer)
    assert message is None, f"A re-run demanded red of a whole-unit check: {message}"
    assert len(calls) == 1
    record = store.load(project, "feature")
    assert record["phases"][CK]["evidence"]
    assert record["locks"] == scoped_test_hashes(project) and record.get("lock_origin") == CK
    assert (project / "src/app.py").read_text() == "release()"


# Reopening


def reopen(root, phase, reason="Revisit the plan after code exists."):
    mutate(root, engine.approve, "s", "reopen", phase, reason)
    mutate(root, engine.reopen, phase, "s", reason)


def reenter_implement(root, phase):
    for name in ("spec", "breakdown")[("spec", "breakdown").index(phase):]:
        accept(root, name)
    mutate(root, engine.approve, "s", "start-implementation", "implement", "Proceed with the replanned work.")
    enter(root, "implement")


@pytest.mark.parametrize("phase", ["spec", "breakdown"])
def test_reopening_spec_or_breakdown_after_code_clears_locks_and_resets_the_checkpoint(project, phase):
    code_after_checkpoint(project)
    before = store.load(project, "feature")
    spent = engine.spent_rounds(before["phases"][CK])
    assert before["locks"] and before.get("lock_origin") == CK
    reopen(project, phase)
    record = store.load(project, "feature")
    reopened = max(i for i, e in enumerate(record["events"]) if e["event"] == "reopened")
    checkpoint = record["phases"][CK]
    assert record["locks"] == {}, f"Reopening {phase} kept the locks."
    assert not record.get("lock_origin"), f"Reopening {phase} kept the lock origin."
    assert record["unlocks"] == []
    assert checkpoint["evidence"] is None
    assert checkpoint["generation"] == before["phases"][CK]["generation"] + 1
    assert checkpoint["round_limit"] == spent + 3
    assert any("lock" in e["event"] or any("lock" in key for key in e)
               for e in record["events"][reopened:]), "No event records the cleared locks."


@pytest.mark.parametrize("phase", ["spec", "breakdown"])
def test_reentering_implement_after_a_reopen_rerecords_the_baseline_and_carries_unchanged_red(
        project, monkeypatch, phase):
    code_after_checkpoint(project)
    reopen(project, phase)
    reenter_implement(project, phase)
    # Writing tests again, with the baseline holding the code written before the reopen.
    assert stage(project) == "writing-tests"
    assert baseline_bytes(project, "src/app.py") == b"release()", "Re-entering implement kept the first baseline."
    assert baseline_files(project)["src/app.py"] == current_hash(project, "src/app.py")
    # The test task re-runs without changing any test, and the checkpoint runs again.
    run_test_tasks(project)
    (project / "run-label").write_text(SECOND_RUN)
    seen = native_capture(monkeypatch)
    message = checkpoint_refusal(project, reviewer=None)
    assert message is None, message
    prompt = seen[-1]["prompt"]
    changed, untouched = comparison(prompt)
    assert changed == set() and untouched == {RELEASE, REPORT, OTHER}
    assert carried(prompt) == {RELEASE, REPORT, OTHER}
    outputs = required_output(seen[-1])
    assert any(f"RUN {FIRST_RUN}".encode() in data and f"FAILED {OTHER}".encode() in data for data in outputs), (
        "The previous accepted checkpoint's saved output is not required reading after the reopen.")
    record = store.load(project, "feature")
    assert record["locks"] == scoped_test_hashes(project) and record.get("lock_origin") == CK
    assert (project / "src/app.py").read_text() == "release()"


def reopened_with_release_built(root):
    """The single-test fixture: the checkpoint locks a red release test, release is built so
    the declared check now passes, and breakdown is reopened and implement re-entered."""
    prepare_implementation(root)
    assert start(root, "cancel", "implementer") is None
    (root / "src/app.py").write_text("release()")
    finish(root, "cancel", ["src/app.py"], CHECK)
    reopen(root, "breakdown")
    reenter_implement(root, "breakdown")
    assert review.run_command(CHECK, root, 10)["exit_code"] == 0


def finish_unchanged_or_changed(root, contents):
    assert start(root, "prepare-tests", "carry-author") is None
    for path, text in contents.items():
        (root / path).write_text(text)
    result = review.run_command(CHECK, root, 10)
    return handoff.complete_task(
        root, "feature", "s", "prepare-tests", changed_files=sorted(contents),
        checks=[{"argv": CHECK, "exit_code": result["exit_code"], "evidence": "The release check ran."}],
        unresolved=[], outcome="The release test is in place.")


def test_an_unchanged_test_task_completes_after_a_reopen_carrying_its_earlier_red(project):
    reopened_with_release_built(project)
    returned = finish_unchanged_or_changed(project, {})
    assert returned["status"] == "completed", (
        f"A test task whose tests are unchanged since the accepted checkpoint did not complete: {returned}")
    events = [e for e in store.load(project, "feature")["events"]
              if e["event"] == "task-returned" and e.get("task") == "prepare-tests"]
    marked = [*keys(returned), *keys(events[-1])]
    assert any(isinstance(k, str) and "carried" in k.lower() for k in marked), (
        "The run is not recorded as carrying forward the earlier red.")
    assert stage(project) == "ready-for-checkpoint"
    assert checkpoint_refusal(project) is None
    assert (project / "src/app.py").read_text() == "release()"


def test_a_changed_test_that_passes_against_expected_red_does_not_complete(project):
    # Guard (passes now): carrying forward covers unchanged tests only.
    reopened_with_release_built(project)
    returned = finish_unchanged_or_changed(project, {RELEASE: "assert True  # rewritten\n"})
    assert returned["status"] != "completed", returned


def test_reopening_implement_keeps_locks_acceptance_and_the_baseline(project):
    # Guard (passes now): only a breakdown-or-earlier reopen clears locks or re-records.
    prepare_implementation(project)
    assert start(project, "cancel", "implementer") is None
    (project / "src/app.py").write_text("release()")
    finish(project, "cancel", ["src/app.py"], CHECK)
    complete_refactor_tasks(project)
    close.close_phase(project, "feature", "implement", "s", reviewer=clean_review)
    observe_phase(project, "implement")
    before = store.load(project, "feature")
    reopen(project, "implement", "Revisit the delivered code.")
    mutate(project, engine.approve, "s", "start-implementation", "implement", "Continue the delivered code.")
    enter(project, "implement")
    record = store.load(project, "feature")
    assert record["locks"] == before["locks"] and record.get("lock_origin") == CK
    assert record["phases"][CK]["evidence"] == before["phases"][CK]["evidence"]
    assert record["writing_tests_baseline"] == before["writing_tests_baseline"]
    assert stage(project) == "writing-code"


# Review round 1 and intent-check findings


def approved_outcomes(prompt):
    """Each test's approved outcome ("pass" or "fail") found anywhere in the reviewer's
    payload: a mapping keyed by test path, or an object naming the test under "path" or
    "test"."""
    found = {}

    def walk(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if isinstance(key, str) and key.startswith("tests/") and item in ("pass", "fail"):
                    found[key] = item
            named = value.get("path") or value.get("test")
            if isinstance(named, str):
                for item in value.values():
                    if item in ("pass", "fail"):
                        found[named] = item
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(payload(prompt))
    return found


def command_coverage(prompt):
    """Every (argv, covered tests) pair the reviewer's payload describes."""
    found = set()

    def walk(value):
        if isinstance(value, dict):
            if isinstance(value.get("argv"), list) and isinstance(value.get("tests"), list):
                found.add((tuple(value["argv"]), tuple(sorted(value["tests"]))))
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(payload(prompt))
    return found


def test_the_reviewer_sees_each_approved_outcome_and_command_coverage(project, monkeypatch):
    # One command covers a pass-expected and a fail-expected test, so its derived exit is
    # non-zero. Reversed results (the pass-expected test fails, the fail-expected one
    # passes) still exit non-zero; only the reviewer, told the approval, can see it.
    code_after_checkpoint(project)
    both = runner(RELEASE, REPORT)
    approve_unlock(project, EXPECTED, [{"argv": both, "tests": [RELEASE, REPORT]}])
    reversed_tests = {
        RELEASE: "from pathlib import Path\nassert Path('src/app.py').read_text() == 'released()', 'reversed'\n",
        REPORT: "assert True  # passes although its behavior is not built\n",
    }
    _, returned = rework(project, reversed_tests, commands=[{"argv": both, "tests": [RELEASE, REPORT]}])
    assert returned["status"] == "completed", returned
    seen = native_capture(monkeypatch)
    checkpoint_refusal(project, reviewer=None)
    assert seen, "The reviewer never ran on the reworked tests."
    prompt = seen[-1]["prompt"]
    outcomes = approved_outcomes(prompt)
    assert outcomes.get(RELEASE) == "pass" and outcomes.get(REPORT) == "fail", (
        f"The reviewer is not told each unlocked test's approved outcome: {outcomes}")
    assert (tuple(both), (RELEASE, REPORT)) in command_coverage(prompt), (
        "The reviewer is not told which unlocked tests the rework command covers.")
    outputs = required_output(seen[-1])
    assert any(f"FAILED {RELEASE}".encode() in data and f"PASSED {REPORT}".encode() in data
               for data in outputs), "The reversal is not in the reviewer's required output."


REPORT_DECLARED = [sys.executable, "-c", (
    "import os, sys\n"
    "print('REPORT-DECLARED-RAN')\n"
    "sys.exit(0 if os.path.exists('report-flipped') else 1)\n"
)]


def ran(root):
    """Each command the latest accepted checkpoint ran, with its exit and saved output."""
    accepted = work(root)["evidence"]
    assert accepted, "The checkpoint has no acceptance."
    return {tuple(c["argv"]): c for c in accepted.get("verification", accepted.get("checks", []))}


def saved_text(root, check):
    return b"".join((root / item["path"]).read_bytes() for item in check.get("saved_output", {}).values())


def test_a_rerun_runs_declared_test_task_commands_without_expectations_and_rework_commands(project):
    # The report task is not reworked: its declared command runs and is saved, now exiting
    # 0 where it declared red, with no expectation held. The unlocked release test's
    # approved rework command runs too.
    code_after_checkpoint(project, split=True, report_argv=REPORT_DECLARED)
    approve_unlock(project, {RELEASE: "pass"}, [COMMANDS[0]])
    _, returned = rework(project, {RELEASE: CORRECTED[RELEASE]}, commands=[COMMANDS[0]])
    assert returned["status"] == "completed", returned
    (project / "report-flipped").write_text("")
    assert stage(project) == "ready-for-checkpoint"
    message = checkpoint_refusal(project)
    assert message is None, message
    checks = ran(project)
    assert tuple(REPORT_DECLARED) in checks, "A re-run dropped a test task's declared command."
    assert checks[tuple(REPORT_DECLARED)]["exit_code"] == 0
    assert b"REPORT-DECLARED-RAN" in saved_text(project, checks[tuple(REPORT_DECLARED)]), (
        "The declared command's output was not saved.")
    assert tuple(runner(RELEASE)) in checks and checks[tuple(runner(RELEASE))]["exit_code"] == 0


EXTRA = "tests/extra_check.py"
EXTRA_DECLARED = [sys.executable, "-c", (
    "import runpy\n"
    "print('EXTRA-DECLARED-RAN')\n"
    f"runpy.run_path({EXTRA!r})\n"
)]


def test_a_rerun_after_a_breakdown_reopen_runs_a_new_test_tasks_declared_command(project):
    code_after_checkpoint(project)
    reopen(project, "breakdown")
    (project / EXTRA).write_text(PASSING_TEST)
    tasks = store.read_json(project / ".fbk/feature/tasks.json")
    tasks.insert(1, {"id": "extra-tests", "stage": "tests", "description": "Check the extra behavior.",
                     "files": [EXTRA], "depends_on": [], "acceptance_refs": REFS,
                     "verification": "The extra test fails until the extra behavior is built.",
                     "check_expectations": [{"argv": EXTRA_DECLARED, "exit_code": "nonzero"}]})
    store.atomic_json(project / ".fbk/feature/tasks.json", tasks)
    reenter_implement(project, "breakdown")
    run_test_tasks(project, {"extra-tests": writes({EXTRA: "assert False, 'the extra behavior is missing'\n"})})
    assert stage(project) == "ready-for-checkpoint"
    message = checkpoint_refusal(project)
    assert message is None, message
    checks = ran(project)
    assert tuple(EXTRA_DECLARED) in checks, "The new test task's declared command did not run at the re-run."
    assert b"EXTRA-DECLARED-RAN" in saved_text(project, checks[tuple(EXTRA_DECLARED)])


def test_carrying_red_forward_never_lets_an_unchanged_preservation_check_fail(project):
    # The test task preserves built behavior (exit 0). After a reopen the code is broken,
    # its unchanged check exits 1, and carried-forward red does not excuse that.
    from .test_workflow_implement_stages import edit_tasks

    edit_tasks(project, lambda by_id, tasks: by_id["prepare-tests"].update(
        check_expectations=[{"argv": CHECK, "exit_code": 0}],
        verification="The existing cancellation check keeps passing."))
    for phase in ("intent", "spec", "breakdown"):
        accept(project, phase)
    (project / "src/app.py").write_text("release()")
    mutate(project, engine.approve, "s", "start-implementation", "implement", "Implement the agreed spec.")
    enter(project, "implement")
    run_test_tasks(project)
    assert checkpoint_refusal(project) is None
    reopen(project, "breakdown")
    (project / "src/app.py").write_text("pass")
    reenter_implement(project, "breakdown")
    assert review.run_command(CHECK, project, 10)["exit_code"] == 1
    returned = finish_unchanged_or_changed(project, {})
    assert returned["status"] != "completed", (
        f"An unchanged preservation check that now fails completed as carried-forward red: {returned}")


def test_overlapping_unlocks_derive_exits_from_the_effective_outcomes(project):
    # The first approval expects the release test to fail and the report test to pass under
    # one command; the second re-approves the release test as pass with a focused command.
    # Both tests are now expected to pass, so the shared command expects exit 0.
    code_after_checkpoint(project)
    both = runner(RELEASE, REPORT)
    approve_unlock(project, {RELEASE: "fail", REPORT: "pass"}, [{"argv": both, "tests": [RELEASE, REPORT]}])
    approve_unlock(project, {RELEASE: "pass"}, [COMMANDS[0]])
    assert store.load(project, "feature")["unlocks"] == sorted([RELEASE, REPORT])
    report_passes = "from pathlib import Path\nassert Path('src/report.py').exists(), 'no report module'\n"
    commands = [{"argv": both, "tests": [RELEASE, REPORT]}, COMMANDS[0]]
    packet, returned = rework(project, {RELEASE: CORRECTED[RELEASE], REPORT: report_passes}, commands=commands)
    exits = {tuple(item["argv"]): item["exit_code"] for item in packet["check_expectations"]}
    assert exits == {tuple(both): 0, tuple(runner(RELEASE)): 0}, (
        f"The rework run kept an expectation the later approval superseded: {exits}")
    assert returned["status"] == "completed", returned


def test_identical_rework_commands_with_conflicting_exits_are_refused(project):
    # Two outstanding approvals give the same argv: covering a fail-expected test in one and
    # a pass-expected test in the other. No expectation is dropped silently: the second
    # approval is refused, naming both tests.
    code_after_checkpoint(project)
    shared = runner(RELEASE, REPORT)
    approve_unlock(project, {RELEASE: "fail"}, [{"argv": shared, "tests": [RELEASE]}])
    before = store.load(project, "feature")
    message = refusal(approve_unlock, project, {REPORT: "pass"}, [{"argv": shared, "tests": [REPORT]}])
    assert message is not None, "A rework command conflicting with an outstanding approval's was accepted."
    assert RELEASE in message and REPORT in message, message
    record = store.load(project, "feature")
    assert record["unlocks"] == [RELEASE] and record["grants"] == before["grants"]


def test_a_governing_decision_after_an_edited_decision_source_still_rerecords_the_baseline(project):
    # The checkpoint is already not current because a decision's source changed after
    # acceptance; recording the superseding decision still returns the unit to writing
    # tests over the built code, which is never reported as undeclared.
    write_decision_sources(project)
    enter_implementation(project)
    run_test_tasks(project)
    record_decision(project, "release-once", DECIDED)
    assert checkpoint_refusal(project) is None
    assert start(project, "cancel", "implementer") is None
    (project / "src/app.py").write_text("release()")
    finish(project, "cancel", ["src/app.py"], CHECK)
    sources = project / "decision-sources.md"
    sources.write_text(sources.read_text().replace(DECIDED + "\n", ""))
    assert stage(project) != "writing-code"
    record_decision(project, "release-reported", REDECIDED, supersedes="release-once")
    assert baseline_bytes(project, "src/app.py") == b"release()", (
        "The superseding decision did not re-record the baseline over the built code.")
    assert stage(project) == "ready-for-checkpoint"
    message = checkpoint_refusal(project)
    assert message is None or "src/app.py" not in message, message
    assert message is None, message


def test_lost_accepted_output_is_refused_with_the_archive_remedy(project, monkeypatch):
    # The saved output folders are git-ignored; a clean checkout loses them. The earlier
    # bytes cannot be restored, so the remedy is the archive route.
    prepare_implementation(project)
    assert start(project, "cancel", "implementer") is None
    (project / "src/app.py").write_text("release()")
    finish(project, "cancel", ["src/app.py"], CHECK)
    governing_change(project)
    for folder in (store.OUTPUT_FOLDER, store.ACCEPTED_OUTPUT_FOLDER):
        shutil.rmtree(project / UNIT / folder, ignore_errors=True)
    seen = native_capture(monkeypatch)
    message = checkpoint_refusal(project, reviewer=None)
    assert message is not None, "A checkpoint ran without the carried-forward output."
    assert ".fbk/archive/" in message, f"The refusal's remedy needs the lost bytes: {message}"
    assert seen == []


# Review round 2 finding: a verdict is bound to the approval it reviewed


@pytest.mark.parametrize("reader", ["injected", "native"])
def test_changing_only_the_approval_forces_a_fresh_checkpoint_review(project, monkeypatch, reader):
    # A round reviews the release test approved to pass and the report test to fail under
    # one combined command. A new approval reverses both outcomes with the same command;
    # the tests, source, and output stay identical. The earlier verdict judged the other
    # approval, so the reviewer must run again.
    code_after_checkpoint(project)
    both = runner(RELEASE, REPORT)
    combined = [{"argv": both, "tests": [RELEASE, REPORT]}]
    approve_unlock(project, {RELEASE: "pass", REPORT: "fail"}, combined)
    _, returned = rework(project, CORRECTED, commands=combined)
    assert returned["status"] == "completed", returned
    calls = []
    if reader == "native":
        def native(snapshot, prompt, config, **kwargs):
            calls.append(prompt)
            return {"review": {"summary": "Inspected the reworked tests.", "findings": []}}

        monkeypatch.setattr(review, "claude_review", native)
        reviewer = None
    else:
        reviewer, calls = counting(clean_review)
    assert checkpoint_refusal(project, reviewer) is None
    assert len(calls) == 1
    approve_unlock(project, {RELEASE: "fail", REPORT: "pass"}, combined)
    # The owner reworks after the latest approval, leaving every test as it was.
    _, returned = rework(project, {}, commands=combined, worker="second-rework-author")
    assert returned["status"] == "completed", returned
    assert stage(project) == "ready-for-checkpoint"
    rounds = len(work(project)["rounds"])
    checkpoint_refusal(project, reviewer)
    assert len(calls) == 2, "The verdict on the earlier approval was reused for the reversed one."
    assert len(work(project)["rounds"]) == rounds + 1


# Review round 3 findings: the running-implementation exemption


def authored_diffs(capture, path):
    """Diffs of one production file the reviewer received as test-authored: under any key
    naming diffs that does not name implementation work, in the payload or a snapshot file."""
    texts = []

    def walk(value):
        if isinstance(value, dict):
            for key, item in value.items():
                lowered = str(key).lower()
                if ("diff" in lowered and "implement" not in lowered and isinstance(item, dict)
                        and isinstance(item.get(path), str)):
                    texts.append(item[path])
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(payload(capture["prompt"]))
    for data in capture["files"].values():
        try:
            loaded = json.loads(data)
        except (ValueError, UnicodeDecodeError):
            continue
        walk(loaded)
    return texts


def shared_util_after_running_tidy(root):
    """The test task also owns src/util.py; tidy, which owns it too, is running at the
    unlock and completes a verified change to it afterwards; the release test is reworked."""
    def share(tasks):
        tasks["prepare-tests"]["files"] = [*tasks["prepare-tests"]["files"], "src/util.py"]

    code_after_checkpoint(root, adjust=share)
    assert start(root, "tidy", "tidy-worker") is None
    (root / "src/util.py").write_text("partial")
    approve_unlock(root, {RELEASE: "pass"}, [COMMANDS[0]])
    (root / "src/util.py").write_text("util()")
    finish(root, "tidy", ["src/util.py"], UTIL_CHECK)
    _, returned = rework(root, {RELEASE: CORRECTED[RELEASE]}, commands=[COMMANDS[0]])
    assert returned["status"] == "completed", returned
    assert stage(root) == "ready-for-checkpoint"


def test_a_running_implementers_change_to_a_shared_file_is_not_shown_as_test_authored(project, monkeypatch):
    shared_util_after_running_tidy(project)
    seen = native_capture(monkeypatch)
    message = checkpoint_refusal(project, reviewer=None)
    assert seen, f"No reviewer ran: {message}"
    assert message is None, message
    assert not authored_diffs(seen[-1], "src/util.py"), (
        "The implementation task's verified change was presented as a test task's production change.")


def test_a_shared_file_edited_before_capture_is_still_refused(project, monkeypatch):
    # Guard (passes now): leaving the exempt change out of the test-authored diffs keeps
    # the file bound to the bytes compared, so an edit before capture is refused.
    shared_util_after_running_tidy(project)
    original_snapshot = review.snapshot
    edited = []

    def edit_then_capture(root, required):
        if not edited:
            (project / "src/util.py").write_text("util()  # edited before capture\n")
            edited.append(True)
        return original_snapshot(root, required)

    monkeypatch.setattr(review, "snapshot", edit_then_capture)
    seen = native_capture(monkeypatch)
    message = checkpoint_refusal(project, reviewer=None)
    assert edited, "The witness seam before snapshot capture never ran."
    assert message is not None and "src/util.py" in message, message
    assert seen == []


def test_a_running_implementer_restoring_a_file_captured_mid_change_is_not_undeclared(project):
    # tidy owns src/util.py and src/helper.py. It changes util, the unlock captures that
    # interim content, then it restores util to its task-start content, changes helper,
    # and completes verified. Its verified return fingerprints both files, so util is its.
    (project / "src").mkdir(exist_ok=True)
    (project / "src/helper.py").write_text("pass")
    check = [sys.executable, "-c",
             "from pathlib import Path; assert Path('src/helper.py').read_text() == 'helper()'"]

    def own_two(tasks):
        tasks["tidy"].update(files=["src/util.py", "src/helper.py"],
                             check_expectations=[{"argv": check, "exit_code": 0}])

    code_after_checkpoint(project, adjust=own_two)
    assert start(project, "tidy", "tidy-worker") is None
    (project / "src/util.py").write_text("interim")
    approve_unlock(project, {RELEASE: "pass"}, [COMMANDS[0]])
    assert baseline_bytes(project, "src/util.py") == b"interim"
    (project / "src/util.py").write_text("pass")
    (project / "src/helper.py").write_text("helper()")
    finish(project, "tidy", ["src/helper.py"], check)
    _, returned = rework(project, {RELEASE: CORRECTED[RELEASE]}, commands=[COMMANDS[0]])
    assert returned["status"] == "completed", returned
    message = checkpoint_refusal(project)
    assert message is None, f"The restored file was refused as undeclared: {message}"


# Review round 4 findings, left as logged follow-ups at the review cap


def test_both_workers_editing_a_shared_file_keep_the_implementation_change_apart(project, monkeypatch):
    # tidy, running at the unlock, adds built behavior to the shared file and completes
    # verified; the reworking test task then adds a permitted signature change to it.
    built = "def util():\n    return 'built-behavior'\n"
    check = [sys.executable, "-c",
             "from pathlib import Path; assert 'built-behavior' in Path('src/util.py').read_text()"]

    def share(tasks):
        tasks["prepare-tests"]["files"] = [*tasks["prepare-tests"]["files"], "src/util.py"]
        tasks["tidy"]["check_expectations"] = [{"argv": check, "exit_code": 0}]

    code_after_checkpoint(project, adjust=share)
    assert start(project, "tidy", "tidy-worker") is None
    (project / "src/util.py").write_text("partial")
    approve_unlock(project, {RELEASE: "pass"}, [COMMANDS[0]])
    (project / "src/util.py").write_text(built)
    finish(project, "tidy", ["src/util.py"], check)
    signature = built + "\ndef util_with(option):\n    return None  # signature-placeholder\n"
    _, returned = rework(project, {RELEASE: CORRECTED[RELEASE], "src/util.py": signature},
                         commands=[COMMANDS[0]])
    assert returned["status"] == "completed", returned
    seen = native_capture(monkeypatch)
    message = checkpoint_refusal(project, reviewer=None)
    assert seen, f"No reviewer ran: {message}"
    diffs = authored_diffs(seen[-1], "src/util.py")
    assert any("signature-placeholder" in diff for diff in diffs), "The test task's change is not shown."
    assert not any(line.startswith("+") and "built-behavior" in line
                   for diff in diffs for line in diff.splitlines()), (
        "The implementation task's verified change was presented as test-authored.")


def test_a_file_created_and_discarded_across_the_unlock_baseline_is_not_undeclared(project):
    (project / "src/pkg").mkdir(parents=True, exist_ok=True)
    (project / "src/pkg/__init__.py").write_text("pass")
    check = [sys.executable, "-c",
             "from pathlib import Path; assert Path('src/pkg/__init__.py').read_text() == 'built()'"]

    def own_folder(tasks):
        tasks["tidy"].update(files=["src/pkg/"], check_expectations=[{"argv": check, "exit_code": 0}])

    code_after_checkpoint(project, adjust=own_folder)
    assert start(project, "tidy", "tidy-worker") is None
    (project / "src/pkg/new_module.py").write_text("DRAFT = True\n")
    approve_unlock(project, {RELEASE: "pass"}, [COMMANDS[0]])
    assert baseline_bytes(project, "src/pkg/new_module.py") == b"DRAFT = True\n"
    (project / "src/pkg/new_module.py").unlink()
    (project / "src/pkg/__init__.py").write_text("built()")
    finish(project, "tidy", ["src/pkg/__init__.py"], check)
    _, returned = rework(project, {RELEASE: CORRECTED[RELEASE]}, commands=[COMMANDS[0]])
    assert returned["status"] == "completed", returned
    message = checkpoint_refusal(project)
    assert message is None, f"The discarded file's deletion was refused as undeclared: {message}"


def test_a_non_string_unlock_outcome_is_refused_not_a_crash(project):
    code_after_checkpoint(project)
    before = store.load(project, "feature")
    try:
        approve_unlock(project, {RELEASE: ["pass"]}, [COMMANDS[0]])
    except store.WorkflowError as exc:
        message = str(exc)
    except Exception as exc:  # noqa: BLE001 - the contract is a validation refusal
        pytest.fail(f"A non-string outcome crashed unlock validation: {exc!r}")
    else:
        message = None
    assert message is not None and '"fail"' in message and '"pass"' in message, message
    record = store.load(project, "feature")
    assert record["grants"] == before["grants"] and record["unlocks"] == []


# Follow-up group A, review round 1


BUILT = "def util():\n    return 'built-behavior'\n"


def tidy_returns_running_at_the_unlock(root, change, check):
    """tidy, running at the unlock, changes the shared src/util.py, which the reworking test
    task also owns, and completes verified."""
    def share(tasks):
        tasks["prepare-tests"]["files"] = [*tasks["prepare-tests"]["files"], "src/util.py"]
        tasks["tidy"]["check_expectations"] = [{"argv": check, "exit_code": 0}]

    code_after_checkpoint(root, adjust=share)
    assert start(root, "tidy", "tidy-worker") is None
    (root / "src/util.py").write_text("partial")
    approve_unlock(root, {RELEASE: "pass"}, [COMMANDS[0]])
    change(root / "src/util.py")
    finish(root, "tidy", ["src/util.py"], check)


def reviewed_util_diffs(root, monkeypatch, contents):
    _, returned = rework(root, {RELEASE: CORRECTED[RELEASE], **contents}, commands=[COMMANDS[0]])
    assert returned["status"] == "completed", returned
    seen = native_capture(monkeypatch)
    message = checkpoint_refusal(root, reviewer=None)
    assert seen, f"No reviewer ran: {message}"
    return authored_diffs(seen[-1], "src/util.py")


def test_a_test_task_reverting_a_verified_implementation_change_to_the_baseline_is_shown(project, monkeypatch):
    # Catches choosing the test-authored diffs only among files differing from the
    # baseline: undoing tidy's verified change back to the baseline content hides it.
    check = [sys.executable, "-c",
             "from pathlib import Path; assert 'built-behavior' in Path('src/util.py').read_text()"]
    tidy_returns_running_at_the_unlock(project, lambda path: path.write_text(BUILT), check)
    diffs = reviewed_util_diffs(project, monkeypatch, {"src/util.py": "partial"})
    assert any(line.startswith("-") and "built-behavior" in line for diff in diffs for line in diff.splitlines()), (
        f"The test task's reversal of the verified implementation change is not shown: {diffs}")


def test_a_test_task_recreating_a_file_a_verified_return_deleted_is_shown_as_an_addition(project, monkeypatch):
    # Catches treating a verified deletion as no return: the recreated file is then
    # diffed against its baseline content instead of against its absence.
    module = "src/pkg/mod.py"
    (project / "src/pkg").mkdir(parents=True, exist_ok=True)
    (project / "src/pkg/__init__.py").write_text("pass")
    (project / module).write_text("pass")
    check = [sys.executable, "-c", f"from pathlib import Path; assert not Path({module!r}).exists()"]

    def own(tasks):
        tasks["prepare-tests"]["files"] = [*tasks["prepare-tests"]["files"], "src/pkg/"]
        tasks["tidy"].update(files=[module], check_expectations=[{"argv": check, "exit_code": 0}])

    code_after_checkpoint(project, adjust=own)
    assert start(project, "tidy", "tidy-worker") is None
    (project / module).write_text("partial")
    approve_unlock(project, {RELEASE: "pass"}, [COMMANDS[0]])
    (project / module).unlink()
    finish(project, "tidy", [module], check)
    _, returned = rework(project, {RELEASE: CORRECTED[RELEASE], module: "recreated()\n"}, commands=[COMMANDS[0]])
    assert returned["status"] == "completed", returned
    seen = native_capture(monkeypatch)
    message = checkpoint_refusal(project, reviewer=None)
    assert seen, f"No reviewer ran: {message}"
    diffs = authored_diffs(seen[-1], module)
    assert any("+recreated()" in diff.splitlines() for diff in diffs), f"The recreated file is not shown: {diffs}"
    assert not any("-partial" in diff.splitlines() for diff in diffs), (
        f"The recreated file was diffed against its baseline, hiding the verified deletion: {diffs}")


def _second_unlock_killed_while_recording(root):
    from fbk.workflow import test_preparation

    def die(*args, **kwargs):
        os._exit(9)

    test_preparation.save_copies = die
    approve_unlock(root, {RELEASE: "pass"}, [COMMANDS[0]], reason="A second look at the release test.")
    os._exit(0)


def test_an_interrupted_baseline_rerecord_keeps_the_previous_verified_returns(project, monkeypatch):
    # Catches deleting the verified-return copies before the replacement baseline is
    # saved: the old baseline stays in force without the content its diffs compare against.
    import multiprocessing

    check = [sys.executable, "-c",
             "from pathlib import Path; assert 'built-behavior' in Path('src/util.py').read_text()"]
    tidy_returns_running_at_the_unlock(project, lambda path: path.write_text(BUILT), check)
    before = store.load(project, "feature")["writing_tests_baseline"]
    process = multiprocessing.get_context("fork").Process(target=_second_unlock_killed_while_recording, args=(project,))
    process.start()
    process.join(60)
    assert process.exitcode == 9, f"The simulated kill did not happen (exit {process.exitcode})."
    assert store.load(project, "feature")["writing_tests_baseline"] == before, "The killed approval was saved."
    signature = BUILT + "\ndef util_with(option):\n    return None  # signature-placeholder\n"
    diffs = reviewed_util_diffs(project, monkeypatch, {"src/util.py": signature})
    assert any("signature-placeholder" in diff for diff in diffs), "The test task's change is not shown."
    assert not any(line.startswith("+") and "built-behavior" in line for diff in diffs for line in diff.splitlines()), (
        "After the interrupted re-record, the verified implementation change was presented as test-authored.")


# Follow-up group A, review round 2


def test_a_verified_return_whose_kept_copy_differs_is_not_silently_dropped(project, monkeypatch):
    # Catches ignoring the kept copy's fingerprint: a worker edit just before the copy is
    # kept leaves mismatched evidence, the diff falls back to the baseline, and a test
    # task's reversal of the verified change to the baseline content shows as nothing.
    from fbk.workflow import test_preparation

    check = [sys.executable, "-c",
             "from pathlib import Path; assert 'built-behavior' in Path('src/util.py').read_text()"]
    original = test_preparation.keep_verified_return

    def edit_then_keep(root, record, task_id, run):
        if task_id == "tidy":
            (root / "src/util.py").write_text(BUILT + "# edited while the return was kept\n")
        return original(root, record, task_id, run)

    def change(path):
        path.write_text(BUILT)

    with monkeypatch.context() as patched:
        patched.setattr(test_preparation, "keep_verified_return", edit_then_keep)
        try:
            tidy_returns_running_at_the_unlock(project, change, check)
        except store.WorkflowError as exc:
            assert "src/util.py" in str(exc) or "changed" in str(exc), exc
            return  # The mismatched evidence was refused at completion.
    _, returned = rework(project, {RELEASE: CORRECTED[RELEASE], "src/util.py": "partial"}, commands=[COMMANDS[0]])
    assert returned["status"] == "completed", returned
    seen = native_capture(monkeypatch)
    message = checkpoint_refusal(project, reviewer=None)
    if message is not None:
        assert "src/util.py" in message, message
        return  # The mismatched evidence was refused at the checkpoint.
    diffs = authored_diffs(seen[-1], "src/util.py")
    assert any(line.startswith("-") and "built-behavior" in line for diff in diffs for line in diff.splitlines()), (
        f"The verified return's mismatched kept copy was dropped, hiding the test task's reversal: {diffs}")


def _second_unlock_killed_after_saving_baseline_copies(root):
    from fbk.workflow import test_preparation

    original = test_preparation.save_copies

    def save_then_die(save_root, record, folder, paths):
        result = original(save_root, record, folder, paths)
        if folder == store.BASELINE_FOLDER:
            os._exit(9)
        return result

    test_preparation.save_copies = save_then_die
    approve_unlock(root, {RELEASE: "pass"}, [COMMANDS[0]], reason="A second look at the release test.")
    os._exit(0)


def test_an_unlock_killed_after_replacing_the_baseline_copies_leaves_a_usable_baseline(project):
    # Catches overwriting the saved baseline copies before the replacement record is saved:
    # the saved fingerprints then point at new bytes and the checkpoint cannot compare.
    import multiprocessing

    check = [sys.executable, "-c",
             "from pathlib import Path; assert 'built-behavior' in Path('src/util.py').read_text()"]
    tidy_returns_running_at_the_unlock(project, lambda path: path.write_text(BUILT), check)
    before = store.load(project, "feature")["writing_tests_baseline"]
    process = multiprocessing.get_context("fork").Process(
        target=_second_unlock_killed_after_saving_baseline_copies, args=(project,))
    process.start()
    process.join(60)
    assert process.exitcode == 9, f"The simulated kill did not happen (exit {process.exitcode})."
    assert store.load(project, "feature")["writing_tests_baseline"] == before, "The killed approval was saved."
    _, returned = rework(project, {RELEASE: CORRECTED[RELEASE]}, commands=[COMMANDS[0]])
    assert returned["status"] == "completed", returned
    message = checkpoint_refusal(project)
    assert message is None, f"The interrupted unlock left the saved baseline unusable: {message}"


def test_a_test_task_clearing_the_executable_bit_of_a_verified_new_file_is_shown(project, monkeypatch):
    # Catches exempting a file a verified return created by its bytes alone: with no
    # baseline mode to compare, a later mode change by the test task is hidden.
    tool = "src/pkg/tool.py"
    (project / "src/pkg").mkdir(parents=True, exist_ok=True)
    (project / "src/pkg/__init__.py").write_text("pass")
    check = [sys.executable, "-c", f"import os; assert os.access({tool!r}, os.X_OK)"]

    def own(tasks):
        tasks["prepare-tests"]["files"] = [*tasks["prepare-tests"]["files"], "src/pkg/"]
        tasks["tidy"].update(files=["src/pkg/"], check_expectations=[{"argv": check, "exit_code": 0}])

    code_after_checkpoint(project, adjust=own)
    assert start(project, "tidy", "tidy-worker") is None
    (project / "src/pkg/__init__.py").write_text("partial")
    approve_unlock(project, {RELEASE: "pass"}, [COMMANDS[0]])
    (project / tool).write_text("print('tool')\n")
    os.chmod(project / tool, 0o755)
    finish(project, "tidy", ["src/pkg/__init__.py", tool], check)
    # Inside the test task's declared files, the executable bit is cleared, bytes unchanged.
    os.chmod(project / tool, 0o644)
    _, returned = rework(project, {RELEASE: CORRECTED[RELEASE]}, commands=[COMMANDS[0]])
    assert returned["status"] == "completed", returned
    seen = native_capture(monkeypatch)
    message = checkpoint_refusal(project, reviewer=None)
    assert seen, f"No reviewer ran: {message}"
    diffs = authored_diffs(seen[-1], tool)
    assert any("100755" in diff and "100644" in diff for diff in diffs), (
        f"The test task's mode change to the verified new file is not shown: {diffs}")


# Follow-up group A, review round 3


def test_a_test_task_resetting_a_verified_mode_only_change_is_shown(project, monkeypatch):
    # Catches keeping a verified return's modes only for files whose bytes changed: tidy's
    # verified chmod of an existing shared file, reset by the test task, then shows nothing.
    check = [sys.executable, "-c", "import os; assert os.access('src/util.py', os.X_OK)"]

    def share(tasks):
        tasks["prepare-tests"]["files"] = [*tasks["prepare-tests"]["files"], "src/util.py"]
        tasks["tidy"]["check_expectations"] = [{"argv": check, "exit_code": 0}]

    code_after_checkpoint(project, adjust=share)
    os.chmod(project / "src/util.py", 0o644)
    assert start(project, "tidy", "tidy-worker") is None
    approve_unlock(project, {RELEASE: "pass"}, [COMMANDS[0]])
    assert store.load(project, "feature")["writing_tests_baseline"]["modes"]["src/util.py"] == "100644"
    os.chmod(project / "src/util.py", 0o755)
    finish(project, "tidy", [], check)
    # Inside the test task's declared files, the executable bit is reset, bytes unchanged.
    os.chmod(project / "src/util.py", 0o644)
    _, returned = rework(project, {RELEASE: CORRECTED[RELEASE]}, commands=[COMMANDS[0]])
    assert returned["status"] == "completed", returned
    seen = native_capture(monkeypatch)
    message = checkpoint_refusal(project, reviewer=None)
    assert seen, f"No reviewer ran: {message}"
    diffs = authored_diffs(seen[-1], "src/util.py")
    assert any("100755" in diff and "100644" in diff for diff in diffs), (
        f"The test task's reset of the verified mode change is not shown: {diffs}")


# Follow-up group A, review round 4


def test_a_test_task_deleting_a_file_a_verified_return_created_is_shown_against_the_return(project, monkeypatch):
    # Guard: catches leaving the verified returns' paths out of the production inventory; a
    # file absent from the baseline and from the tree would then hide the test task's deletion.
    created = "src/pkg/created.py"
    (project / "src/pkg").mkdir(parents=True, exist_ok=True)
    (project / "src/pkg/__init__.py").write_text("pass")
    check = [sys.executable, "-c", f"from pathlib import Path; assert Path({created!r}).exists()"]

    def own(tasks):
        tasks["prepare-tests"]["files"] = [*tasks["prepare-tests"]["files"], "src/pkg/"]
        tasks["tidy"].update(files=["src/pkg/"], check_expectations=[{"argv": check, "exit_code": 0}])

    code_after_checkpoint(project, adjust=own)
    assert start(project, "tidy", "tidy-worker") is None
    approve_unlock(project, {RELEASE: "pass"}, [COMMANDS[0]])
    assert created not in baseline_files(project)
    (project / created).write_text("def created():\n    return 'returned-content'\n")
    finish(project, "tidy", [created], check)
    mutate(project, handoff.start_task, "s", "prepare-tests", "rework-author")
    (project / RELEASE).write_text(CORRECTED[RELEASE])
    (project / created).unlink()
    result = review.run_command(COMMANDS[0]["argv"], project, 30)
    returned = handoff.complete_task(
        project, "feature", "s", "prepare-tests", changed_files=sorted([RELEASE, created]),
        checks=[{"argv": COMMANDS[0]["argv"], "exit_code": result["exit_code"],
                 "evidence": (result["stdout"] or result["stderr"] or "The command ran.")[-500:]}],
        unresolved=[], outcome="The named test is corrected and the created module removed.")
    assert returned["status"] == "completed", returned
    seen = native_capture(monkeypatch)
    message = checkpoint_refusal(project, reviewer=None)
    assert seen, f"No reviewer ran: {message}"
    diffs = authored_diffs(seen[-1], created)
    lines = [line for diff in diffs for line in diff.splitlines()]
    assert any(line.startswith("---") and "returned/" in line for line in lines), (
        f"The test task's deletion is not shown against the kept return: {diffs}")
    assert any(line.startswith("+++") and "/dev/null" in line for line in lines), f"Not shown as a deletion: {diffs}"
    assert "-    return 'returned-content'" in lines, f"The deletion diff omits the removed content: {diffs}"
