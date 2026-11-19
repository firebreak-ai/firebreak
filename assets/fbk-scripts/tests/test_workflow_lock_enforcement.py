"""Locked tests are checked at every task boundary (build step 5, plan decision 7).

A worker can change a locked test through the shell, which the write hook never sees.
Task start and task finish compare every locked test file with its lock, including after
task finish has run its checks, except files with an approved unlock outstanding. A
mismatch refuses the finish and any new start, names the files, and records a
lock-violation event naming the finishing task and every task running at the time. When the
checkpoint locks, Firebreak saves a copy of each locked test file in a record folder inside
the unit's folder, following the step 3b record-folder pattern; a violation shows the diff
against the copy, and one command restores a violated file from its copy. The copies are
deleted at implementation close, cleared with the locks by a breakdown-or-earlier reopen,
and saved again on an implement reopen when the files still match their locks.

The tests assume these shapes, leaving names to the implementer where they can:

- **Copies folder.** One new name in ``store.RECORD_FOLDERS``; each copy sits at
  ``test_preparation.copy_path(<unit folder>/<that name>, <relative path>)``.
- **Event.** A record event whose name contains "lock" and "violat"; the files and task ids
  appear among its strings.
- **Diff.** The unified diff against the copy appears in the refusal message or the event.
- **Restore.** The one registered command whose name contains "restore", run as
  ``<command> <unit> --tests <path>...`` (the shape of ``approve unlock-test --tests``).

Lead rulings on points decision 7 leaves open: a refused start also records the event,
naming the starting task and every running task; a refused finish leaves the task running;
an implement reopen checks the locks at the reopen itself, refusing there or saving the
copies again there; restore recreates a deleted locked file; a new scoped test file added
through the shell is not a lock violation.
"""

import hashlib
import os
import stat
import sys

import pytest

from fbk.workflow import COMMANDS, close, engine, handoff, review, store, test_preparation
from .test_workflow_checkpoint_review_inputs import commit_all, ignored, plant_unit, strings
from .test_workflow_commands import call
from .test_workflow_implement_stages import (
    CHECK,
    REFS,
    denied,
    edit_tasks,
    refusal,
    stage,
    start,
)
from .test_workflow_lifecycle import (
    approve_unlock,
    blocking_review,
    clean_review,
    complete_declared_implementation_task,
    declare_module_preparation_task,
    enter_implementation,
    mutate,
    observe_phase,
    prepare_implementation,
    project as workflow_project,
    run_test_tasks,
)
from .test_workflow_test_checkpoint import checkpoint_refusal
from .test_workflow_test_preparation import write_permission
from .test_workflow_unlock_rework_reopen import UTIL_CHECK, finish, reopen
from .refactor_plan import complete_refactor_tasks

project = workflow_project

UNIT = ".fbk/feature"
RELEASE, OTHER = "tests/check.py", "tests/other.py"
KNOWN_FOLDERS = {store.BASELINE_FOLDER, store.OUTPUT_FOLDER, store.ACCEPTED_OUTPUT_FOLDER}
SHELL_EDIT = "assert False, 'shell edit'\n"
CORRECTED = "from pathlib import Path\nassert Path('src/app.py').read_text() == 'release()', 'not released'\n"


# Helpers


def lock_folder():
    """The record folder name holding the saved copies of locked tests."""
    new = [name for name in store.RECORD_FOLDERS if name not in KNOWN_FOLDERS]
    assert len(new) == 1, (
        f"No reserved record folder holds the saved copies of locked tests (record folders: {store.RECORD_FOLDERS}).")
    return new[0]


def copy_of(root, relative):
    """The saved copy of a locked test, or None when there is none."""
    path = test_preparation.copy_path(root / UNIT / lock_folder(), relative)
    return path if path.is_file() else None


def restore_command():
    names = [name for name in COMMANDS if "restore" in name]
    assert len(names) == 1, f"No single command restores a locked test from its saved copy (commands: {COMMANDS})."
    return names[0]


def restore(root, *paths):
    return call(root, restore_command(), "feature", "--tests", *paths)


def restore_refusal(root, *paths):
    command = restore_command()
    return refusal(call, root, command, "feature", "--tests", *paths)


def violations(root):
    return [e for e in store.load(root, "feature")["events"]
            if "lock" in e["event"] and "violat" in e["event"]]


def event_strings(event):
    return set(strings(event))


def with_other_test(root):
    """A second locked test no test task owns, passing and untouched."""
    (root / OTHER).write_text("assert 1 == 1\n")


def with_tidy_task(root):
    """A second implementation task, so two can run at once."""
    (root / "src/util.py").write_text("pass")
    edit_tasks(root, lambda by_id, tasks: tasks.append({
        "id": "tidy", "stage": "implementation", "description": "Tidy the utility module.",
        "files": ["src/util.py"], "depends_on": [], "acceptance_refs": REFS,
        "verification": "The utility module holds util().",
        "check_expectations": [{"argv": UTIL_CHECK, "exit_code": 0}],
    }))


def complete(root, task, changed, argv):
    """Finish a task through the public route: checks run outside the project lock."""
    result = review.run_command(argv, root, 30)
    return handoff.complete_task(
        root, "feature", "s", task, changed_files=changed,
        checks=[{"argv": argv, "exit_code": result["exit_code"],
                 "evidence": (result["stdout"] or result["stderr"] or "The check ran.")[-500:]}],
        unresolved=[], outcome="The task's change is in place.")


def finish_directly(root, task, changed, argv):
    """Finish a task through finish_task, which runs the checks inside the project lock."""
    return mutate(root, handoff.finish_task, "s", task, changed_files=changed,
                  checks=[{"argv": argv, "exit_code": 0, "evidence": "The check ran."}],
                  unresolved=[], outcome="The task's change is in place.")


ROUTES = {"complete_task": complete, "finish_task": finish_directly}


def finish_refusal(root, task, changed, argv, route=complete):
    try:
        returned = route(root, task, changed, argv)
    except store.WorkflowError as exc:
        return str(exc)
    return f"NOT REFUSED: {returned['status']}" if returned["status"] == "completed" else None


def shows_diff(texts):
    lines = {line.strip() for text in texts for line in text.splitlines()}
    return "+" + SHELL_EDIT.strip() in lines and "-from pathlib import Path" in lines


def closed_implementation(root):
    prepare_implementation(root)
    assert start(root, "cancel", "implementer") is None
    (root / "src/app.py").write_text("release()")
    finish(root, "cancel", ["src/app.py"], CHECK)
    complete_refactor_tasks(root)


def closed_and_observed(root):
    closed_implementation(root)
    close.close_phase(root, "feature", "implement", "s", reviewer=clean_review)
    observe_phase(root, "implement")


def reopen_implement_refusal(root):
    """Approve and run the implement reopen itself; the reopen's refusal, or None."""
    reason = "Revisit the delivered code."
    mutate(root, engine.approve, "s", "reopen", "implement", reason)
    return refusal(mutate, root, engine.reopen, "implement", "s", reason)


def assert_violation_names(root, *names):
    events = violations(root)
    assert events, "No lock-violation event was recorded."
    found = event_strings(events[-1])
    assert all(any(name in s for s in found) for name in names), (
        f"The lock-violation event does not name {names}: {events[-1]}")
    return found


# Saved copies


def test_the_checkpoint_lock_saves_a_copy_of_each_locked_test(project):
    with_other_test(project)
    prepare_implementation(project)
    locks = store.load(project, "feature")["locks"]
    assert set(locks) == {RELEASE, OTHER}
    for relative in locks:
        copy = copy_of(project, relative)
        assert copy is not None, f"No saved copy of locked test {relative}."
        assert copy.read_bytes() == (project / relative).read_bytes()
    assert (project / UNIT / lock_folder() / ".gitignore").read_text() == "*\n", (
        "The copies folder carries no ignore-everything file of its own.")


def test_a_relock_after_rework_saves_the_reworked_content(project):
    # Catches copies saved at the first lock only: a later restore would undo approved rework.
    prepare_implementation(project)
    approve_unlock(project, {RELEASE: "fail"}, [{"argv": CHECK, "tests": [RELEASE]}],
                   reason="The cancellation test asserts the wrong call.")

    def corrected(root):
        (root / RELEASE).write_text(CORRECTED)
        return [RELEASE]

    run_test_tasks(project, {"prepare-tests": corrected})
    assert checkpoint_refusal(project) is None
    copy = copy_of(project, RELEASE)
    assert copy is not None and copy.read_text() == CORRECTED, "The re-lock kept the earlier copy."


def test_the_write_hook_refuses_the_copies_folder(project):
    prepare_implementation(project)
    folder = f"{UNIT}/{lock_folder()}"
    for path in (f"{folder}/{RELEASE}", f"{folder}/new.txt"):
        assert denied(write_permission(project, path)), f"The lead may write {path}."
        assert denied(write_permission(project, path, "implementer")), f"A worker may write {path}."


def test_a_unit_named_like_the_copies_folder_is_refused(project):
    name = lock_folder()
    for unit in (name, f"feature/{name}"):
        with pytest.raises(store.WorkflowError):
            with store.transaction(project):
                engine.initialize(project, unit, design=False)
        assert not (project / ".fbk" / unit / "state.json").exists()


def test_an_existing_project_gains_the_copies_ignore_entry(project):
    (project / ".fbk/.gitignore").write_text("runtime/\nlocal-notes/\n")
    commit_all(project)
    prepare_implementation(project)
    name = lock_folder()
    lines = (project / ".fbk/.gitignore").read_text().splitlines()
    assert any(name in line for line in lines), f".fbk/.gitignore gained no entry for {name}."
    assert "runtime/" in lines and "local-notes/" in lines, "The existing ignore entries were lost."
    assert ignored(project, f"{UNIT}/{name}/{RELEASE}"), "Git does not ignore the saved copy."
    # Guard: the unit's own records stay tracked.
    assert not ignored(project, f"{UNIT}/state.json")


# Task start


@pytest.mark.parametrize("change", ["edit", "delete"])
def test_an_implementation_task_start_after_a_shell_change_names_the_locked_test(project, change):
    # Catches relying on the stage alone: a stale checkpoint refuses the start without
    # saying which locked test changed.
    # The refused start records the event naming the starting task and every running task.
    with_tidy_task(project)
    prepare_implementation(project)
    assert start(project, "cancel", "implementer") is None
    if change == "edit":
        (project / RELEASE).write_text(SHELL_EDIT)
    else:
        (project / RELEASE).unlink()
    message = start(project, "tidy", "tidy-worker")
    assert message is not None, "The start was allowed over a changed locked test."
    assert RELEASE in message, f"The refusal does not name the changed locked test: {message}"
    assert_violation_names(project, RELEASE, "tidy", "cancel")
    assert "tidy" not in store.load(project, "feature").get("task_runs", {}), "The refused start was recorded as a run."


def test_a_test_task_start_after_a_shell_change_is_refused(project):
    # Catches checking only implementation starts: with the checkpoint stale, the stage lets
    # a test task start and rework a locked test with no unlock.
    prepare_implementation(project)
    (project / RELEASE).write_text(SHELL_EDIT)
    message = start(project, "prepare-tests", "test-author")
    assert message is not None, "A test task started over a locked test changed through the shell."
    assert RELEASE in message
    assert_violation_names(project, RELEASE, "prepare-tests")


# Task finish


def test_a_finish_over_a_shell_change_is_refused_and_recorded_with_every_running_task(project):
    # Catches a finish that checks only the task's own files, and an event that names only
    # the finishing task.
    with_tidy_task(project)
    prepare_implementation(project)
    assert start(project, "cancel", "implementer") is None
    assert start(project, "tidy", "tidy-worker") is None
    (project / RELEASE).write_text(SHELL_EDIT)
    (project / "src/util.py").write_text("util()")
    message = finish_refusal(project, "tidy", ["src/util.py"], UTIL_CHECK)
    assert message is not None and not message.startswith("NOT REFUSED"), (
        f"The finish was accepted over a changed locked test: {message}")
    assert RELEASE in message
    assert store.load(project, "feature")["task_runs"]["tidy"]["status"] == "running", (
        "A refused finish must leave the task running.")
    names = assert_violation_names(project, RELEASE, "tidy", "cancel")
    assert shows_diff([message, *names]), "The violation does not show the diff against the saved copy."


@pytest.mark.parametrize("route", sorted(ROUTES))
def test_a_change_made_while_finish_runs_its_checks_is_caught(project, monkeypatch, route):
    # Catches comparing the locks only before the checks run, on either completion route.
    prepare_implementation(project)
    assert start(project, "cancel", "implementer") is None
    (project / "src/app.py").write_text("release()")
    original = handoff._execute_task_checks

    def checks_then_shell_edit(root, expectations):
        results = original(root, expectations)
        (project / RELEASE).write_text(SHELL_EDIT)
        return results

    monkeypatch.setattr(handoff, "_execute_task_checks", checks_then_shell_edit)
    message = finish_refusal(project, "cancel", ["src/app.py"], CHECK, ROUTES[route])
    assert message is not None and not message.startswith("NOT REFUSED"), (
        f"A locked test changed while the checks ran, and the finish was accepted: {message}")
    assert RELEASE in message
    assert store.load(project, "feature")["task_runs"]["cancel"]["status"] == "running", (
        "A refused finish must leave the task running.")
    assert_violation_names(project, RELEASE, "cancel")


# Outstanding unlocks are exempt, exactly


def unlocked_release(root):
    with_other_test(root)
    prepare_implementation(root)
    approve_unlock(root, {RELEASE: "fail"}, [{"argv": CHECK, "tests": [RELEASE]}],
                   reason="The cancellation test asserts the wrong call.")


def test_an_unlocked_test_changed_through_the_shell_does_not_block_its_rework(project):
    # Guard (passes now): catches a check that ignores outstanding unlocks.
    unlocked_release(project)
    (project / RELEASE).write_text(CORRECTED)
    assert start(project, "prepare-tests", "rework-author") is None


def test_an_unlock_exempts_only_its_named_tests_at_start(project):
    # Catches an unlock that exempts every locked test.
    unlocked_release(project)
    (project / RELEASE).write_text(CORRECTED)
    (project / OTHER).write_text(SHELL_EDIT)
    message = start(project, "prepare-tests", "rework-author")
    assert message is not None and OTHER in message, (
        f"A locked test outside the unlock changed and the start was allowed: {message}")
    restore(project, OTHER)
    assert start(project, "prepare-tests", "rework-author") is None
    assert (project / RELEASE).read_text() == CORRECTED, "Restoring the other test touched the unlocked one."


def test_an_unlock_exempts_only_its_named_tests_at_finish(project):
    unlocked_release(project)
    assert start(project, "prepare-tests", "rework-author") is None
    (project / RELEASE).write_text(CORRECTED)
    (project / OTHER).write_text(SHELL_EDIT)
    message = finish_refusal(project, "prepare-tests", [RELEASE], CHECK)
    assert message is not None and not message.startswith("NOT REFUSED") and OTHER in message, (
        f"The rework finished over a changed locked test outside the unlock: {message}")
    assert store.load(project, "feature")["task_runs"]["prepare-tests"]["status"] == "running"
    assert_violation_names(project, OTHER, "prepare-tests")


# Restore


LOCKED_BYTES = (b"from pathlib import Path\r\n"
                b"assert Path('src/app.py').read_text() == 'release()'  # caf\xc3\xa9 \t")


def test_restore_reproduces_the_locked_content_exactly(project):
    # Catches text-mode rewriting (line endings, a trailing newline) and a stale copy.
    def write_locked(root):
        (root / RELEASE).write_bytes(LOCKED_BYTES)
        return [RELEASE]

    prepare_implementation(project, {"prepare-tests": write_locked})
    (project / RELEASE).write_text(SHELL_EDIT)
    assert start(project, "cancel", "implementer") is not None
    restore(project, RELEASE)
    assert (project / RELEASE).read_bytes() == LOCKED_BYTES
    assert stage(project) == "writing-code"
    assert start(project, "cancel", "implementer") is None


def test_restore_recreates_a_deleted_locked_test(project):
    # Catches a restore that only overwrites existing files.
    prepare_implementation(project)
    locked = (project / RELEASE).read_bytes()
    (project / RELEASE).unlink()
    restore(project, RELEASE)
    assert (project / RELEASE).read_bytes() == locked
    assert start(project, "cancel", "implementer") is None


def test_restore_refuses_a_test_with_an_outstanding_unlock(project):
    unlocked_release(project)
    (project / RELEASE).write_text(CORRECTED)
    message = restore_refusal(project, RELEASE)
    assert message is not None, "Restore replaced a test the operator unlocked for rework."
    assert (project / RELEASE).read_text() == CORRECTED


@pytest.mark.parametrize("path", [RELEASE, "src/app.py"])
def test_restore_refuses_a_file_whose_lock_is_not_violated(project, path):
    # Catches a restore that rewrites any path it is given.
    prepare_implementation(project)
    before = (project / path).read_bytes()
    message = restore_refusal(project, path)
    assert message is not None, f"Restore accepted {path}, whose lock is not violated."
    assert (project / path).read_bytes() == before


# Lifecycle


def test_copies_are_deleted_at_implementation_close(project):
    closed_implementation(project)
    assert copy_of(project, RELEASE) is not None, "No saved copy before implementation close."
    close.close_phase(project, "feature", "implement", "s", reviewer=clean_review)
    observe_phase(project, "implement")
    assert copy_of(project, RELEASE) is None, "The saved copies outlived implementation close."


@pytest.mark.parametrize("phase", ["spec", "breakdown"])
def test_a_breakdown_or_earlier_reopen_clears_the_copies(project, phase):
    prepare_implementation(project)
    assert copy_of(project, RELEASE) is not None, "No saved copy after the checkpoint locked."
    reopen(project, phase)
    assert copy_of(project, RELEASE) is None, f"Reopening {phase} kept the saved copies."


def test_an_implement_reopen_saves_the_copies_again_from_matching_files(project):
    # The copies are saved at the reopen itself, before implement is entered again.
    closed_and_observed(project)
    locked = (project / RELEASE).read_bytes()
    assert reopen_implement_refusal(project) is None
    copy = copy_of(project, RELEASE)
    assert copy is not None and copy.read_bytes() == locked, "Reopening implement did not save the copies again."


def test_an_implement_reopen_is_refused_when_a_locked_test_no_longer_matches(project):
    # Catches re-saving copies from changed files, which would make the change the new truth.
    # The reopen itself is refused, so the phase keeps its acceptance.
    closed_and_observed(project)
    (project / RELEASE).write_text(SHELL_EDIT)
    message = reopen_implement_refusal(project)
    assert message is not None and RELEASE in message, (
        f"Implement reopened over a locked test that no longer matches its lock: {message}")
    assert store.load(project, "feature")["phases"]["implement"]["evidence"], "The refused reopen cleared the acceptance."
    copy = copy_of(project, RELEASE)
    assert copy is None or copy.read_text() != SHELL_EDIT, "The changed file was saved as the locked copy."


# Review round 1


def copies_snapshot(root):
    """Every file in the copies folder, with its bytes."""
    folder = root / UNIT / lock_folder()
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob("*") if p.is_file()} \
        if folder.is_dir() else {}


def lock_state(root):
    record = store.load(root, "feature")
    return {"locks": record["locks"], "unlocks": record["unlocks"], "lock_origin": record.get("lock_origin")}


def failing_copy_save(monkeypatch, root, failure):
    """Make saving the copies of locked tests fail: either a locked test changes while the
    copies are written, or the save stops partway with an error after clearing the folder."""
    original = test_preparation.save_copies

    def save(save_root, record, folder, paths):
        if folder != lock_folder():
            return original(save_root, record, folder, paths)
        if failure == "changed-source":
            (root / RELEASE).write_text((root / RELEASE).read_text() + "# changed during the copy\n")
            return original(save_root, record, folder, paths)
        import shutil

        shutil.rmtree(root / UNIT / folder, ignore_errors=True)
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(test_preparation, "save_copies", save)


def refused_checkpoint(root):
    try:
        message = checkpoint_refusal(root)
    except OSError as exc:
        message = str(exc)
    assert message is not None, "The checkpoint passed although its copies could not be saved."
    return message


@pytest.mark.parametrize("failure", ["changed-source", "error"])
def test_a_failed_copy_save_at_the_first_lock_changes_no_lock_state(project, monkeypatch, failure):
    # Catches replacing the locks and clearing unlocks before the copies are safely saved.
    enter_implementation(project)
    run_test_tasks(project)
    before = lock_state(project)
    failing_copy_save(monkeypatch, project, failure)
    refused_checkpoint(project)
    assert lock_state(project) == before, "A failed copy save still changed the lock state."
    assert copies_snapshot(project) == {}, "A failed first lock left copies behind."


@pytest.mark.parametrize("failure", ["changed-source", "error"])
def test_a_failed_copy_save_at_a_relock_keeps_the_locks_unlocks_and_previous_copies(project, monkeypatch, failure):
    # Catches deleting the previous copies before their replacement is complete.
    prepare_implementation(project)
    approve_unlock(project, {RELEASE: "fail"}, [{"argv": CHECK, "tests": [RELEASE]}],
                   reason="The cancellation test asserts the wrong call.")

    def corrected(root):
        (root / RELEASE).write_text(CORRECTED)
        return [RELEASE]

    run_test_tasks(project, {"prepare-tests": corrected})
    before, copies = lock_state(project), copies_snapshot(project)
    assert copies, "No previous copies to keep."
    failing_copy_save(monkeypatch, project, failure)
    refused_checkpoint(project)
    assert lock_state(project) == before, "A failed relock still changed the lock state."
    assert copies_snapshot(project) == copies, "A failed relock lost or changed the previous copies."


@pytest.mark.parametrize("route", sorted(ROUTES))
def test_a_change_before_a_check_times_out_is_still_named_with_its_diff(project, monkeypatch, route):
    # Catches skipping the lock comparison when a completion check raises.
    prepare_implementation(project)
    assert start(project, "cancel", "implementer") is None
    (project / "src/app.py").write_text("release()")

    def edit_then_time_out(root, expectations):
        # The task's own check changes the locked test, then exceeds its time limit.
        (project / RELEASE).write_text(SHELL_EDIT)
        raise store.WorkflowError(
            f"Command {expectations[0]['argv'][0]} exceeded its 300s time limit; its process group was stopped.")

    monkeypatch.setattr(handoff, "_execute_task_checks", edit_then_time_out)
    message = finish_refusal(project, "cancel", ["src/app.py"], CHECK, ROUTES[route])
    assert message is not None and not message.startswith("NOT REFUSED")
    assert RELEASE in message, f"The refusal does not name the locked test changed before the timeout: {message}"
    names = assert_violation_names(project, RELEASE, "cancel")
    assert shows_diff([message, *names]), "The violation does not show the diff against the saved copy."
    assert store.load(project, "feature")["task_runs"]["cancel"]["status"] == "running"


def test_restoring_a_symlinked_test_keeps_its_target_executable(project):
    # Catches applying the flattened copy's mode through a project symlink.
    tools = project / "tools"
    tools.mkdir()
    target = tools / "link_check.py"
    target.write_text("#!/usr/bin/env python3\nassert True\n")
    target.chmod(0o755)
    (project / "tests/link_check.py").symlink_to("../tools/link_check.py")
    prepare_implementation(project)
    assert "tests/link_check.py" in store.load(project, "feature")["locks"]
    locked = target.read_bytes()
    target.write_text("#!/usr/bin/env python3\nassert False, 'shell edit'\n")
    restore(project, "tests/link_check.py")
    assert target.read_bytes() == locked
    assert target.stat().st_mode & stat.S_IXUSR, "Restoring through the symlink cleared the target's executable bit."
    assert os.access(target, os.X_OK)


def test_a_new_scoped_test_added_through_the_shell_is_not_a_violation(project):
    # Guard: catches comparing the whole current test inventory with the lock inventory.
    prepare_implementation(project)
    assert start(project, "cancel", "implementer") is None
    (project / "tests/new_check.py").write_text("assert True\n")
    (project / "src/app.py").write_text("release()")
    returned = complete(project, "cancel", ["src/app.py"], CHECK)
    assert returned["status"] == "completed", returned
    assert violations(project) == [], "A new scoped test was recorded as a lock violation."


@pytest.mark.parametrize("refusal_kind", ["failing-verification", "blocking-review"])
def test_a_refused_implementation_close_keeps_the_copies_and_restore_works(project, refusal_kind):
    # Catches deleting the copies before the close is accepted.
    if refusal_kind == "failing-verification":
        declare_module_preparation_task(project)
        prepare_implementation(project)
        complete_declared_implementation_task(project)
        reviewer = clean_review
    else:
        closed_implementation(project)
        reviewer = blocking_review
    locked, copies = (project / RELEASE).read_bytes(), copies_snapshot(project)
    assert copies, "No copies before the close."
    with pytest.raises(store.WorkflowError):
        close.close_phase(project, "feature", "implement", "s", reviewer=reviewer)
    assert not store.load(project, "feature")["phases"]["implement"]["evidence"]
    assert copies_snapshot(project) == copies, "A refused implementation close changed the copies."
    (project / RELEASE).write_text(SHELL_EDIT)
    restore(project, RELEASE)
    assert (project / RELEASE).read_bytes() == locked


# Review round 2


def test_a_failed_set_aside_of_the_previous_copies_keeps_them_and_locks_nothing(project, monkeypatch):
    # Catches deleting the live copies when moving them aside never happened.
    import pathlib

    prepare_implementation(project)
    approve_unlock(project, {RELEASE: "fail"}, [{"argv": CHECK, "tests": [RELEASE]}],
                   reason="The cancellation test asserts the wrong call.")

    def corrected(root):
        (root / RELEASE).write_text(CORRECTED)
        return [RELEASE]

    run_test_tasks(project, {"prepare-tests": corrected})
    before, copies = lock_state(project), copies_snapshot(project)
    assert copies, "No previous copies to keep."
    live = (project / UNIT / lock_folder()).resolve()
    original = pathlib.Path.rename

    def rename(self, target):
        if pathlib.Path(self).resolve() == live:
            raise PermissionError(13, "Permission denied", str(target))
        return original(self, target)

    monkeypatch.setattr(pathlib.Path, "rename", rename)
    refused_checkpoint(project)
    assert copies_snapshot(project) == copies, "A failed set-aside destroyed the previous copies."
    assert lock_state(project) == before, "A failed set-aside still locked the tests."


def colliding_unit_refusal(root, action):
    """Plant a pre-step-5 unit at feature/<copies folder>, run the action, and return its
    refusal; the planted record must survive unchanged."""
    planted = plant_unit(root, f"feature/{lock_folder()}")
    data = planted.read_bytes()
    message = refusal(action)
    assert planted.is_file() and planted.read_bytes() == data, "The colliding unit's record was moved or deleted."
    assert message is not None, "A unit living in the copies folder was not refused."
    assert lock_folder() in message, f"The refusal does not name the colliding unit: {message}"
    return message


def test_a_colliding_unit_is_refused_at_a_checkpoint_lock(project):
    enter_implementation(project)
    run_test_tasks(project)
    colliding_unit_refusal(project, lambda: close.close_checkpoint(project, "feature", "s", reviewer=clean_review))


def test_a_colliding_unit_is_refused_at_an_implement_reopen(project):
    closed_and_observed(project)
    colliding_unit_refusal(project, lambda: _reopen_raising(project))


def _reopen_raising(root):
    reason = "Revisit the delivered code."
    mutate(root, engine.approve, "s", "reopen", "implement", reason)
    mutate(root, engine.reopen, "implement", "s", reason)


def test_a_colliding_unit_is_refused_at_implementation_close(project):
    closed_implementation(project)
    colliding_unit_refusal(
        project, lambda: close.close_phase(project, "feature", "implement", "s", reviewer=clean_review))


def test_a_colliding_unit_is_refused_at_a_breakdown_reopen(project):
    prepare_implementation(project)
    colliding_unit_refusal(project, lambda: reopen(project, "breakdown"))


@pytest.mark.parametrize("route", sorted(ROUTES))
def test_a_lock_already_differing_at_finish_runs_no_completion_check(project, monkeypatch, route):
    # Catches comparing the locks only after the checks have run.
    prepare_implementation(project)
    assert start(project, "cancel", "implementer") is None
    (project / "src/app.py").write_text("release()")
    (project / RELEASE).write_text(SHELL_EDIT)
    calls = []
    original = handoff._execute_task_checks

    def spy(root, expectations):
        calls.append(expectations)
        return original(root, expectations)

    monkeypatch.setattr(handoff, "_execute_task_checks", spy)
    message = finish_refusal(project, "cancel", ["src/app.py"], CHECK, ROUTES[route])
    assert message is not None and not message.startswith("NOT REFUSED") and RELEASE in message
    assert calls == [], "Completion checks ran although a locked test already differed."


OTHER_EDIT = "assert False, 'other shell edit'\n"


def names_both(texts):
    lines = {line.strip() for text in texts for line in text.splitlines()}
    return all(any(path in text for text in texts) for path in (RELEASE, OTHER)) and shows_diff(texts) \
        and "+" + OTHER_EDIT.strip() in lines and "-assert 1 == 1" in lines


def test_two_changed_locked_tests_are_both_named_with_diffs_at_start_and_finish(project):
    # Catches reporting only the first mismatch.
    with_other_test(project)
    with_tidy_task(project)
    prepare_implementation(project)
    assert start(project, "cancel", "implementer") is None
    (project / RELEASE).write_text(SHELL_EDIT)
    (project / OTHER).write_text(OTHER_EDIT)
    message = start(project, "tidy", "tidy-worker")
    assert message is not None
    found = assert_violation_names(project, RELEASE, OTHER, "tidy", "cancel")
    assert names_both([message, *found]), f"The start refusal does not show both files and diffs: {message}"
    (project / "src/app.py").write_text("release()")
    message = finish_refusal(project, "cancel", ["src/app.py"], CHECK)
    assert message is not None and not message.startswith("NOT REFUSED")
    found = assert_violation_names(project, RELEASE, OTHER, "cancel")
    assert names_both([message, *found]), f"The finish refusal does not show both files and diffs: {message}"


# Review round 3


def _relock_killed_midway(root):
    """In a forked process, run the re-lock checkpoint and kill the process (no handlers
    run) on the second write of a locked test's bytes, wherever Firebreak writes it."""
    import pathlib

    contents = {(root / path).read_bytes() for path in (RELEASE, OTHER)}
    original = pathlib.Path.write_bytes
    writes = []

    def write_bytes(self, data):
        if bytes(data) in contents:
            writes.append(str(self))
            if len(writes) == 2:
                os._exit(9)
        return original(self, data)

    pathlib.Path.write_bytes = write_bytes
    try:
        close.close_checkpoint(root, "feature", "s", reviewer=clean_review)
    finally:
        pathlib.Path.write_bytes = original
    os._exit(0)


def test_a_relock_killed_while_writing_copies_leaves_every_lock_a_usable_copy_after_recovery(project):
    # Catches moving every previous copy away before the new ones exist, with nothing in
    # recovery to put them back: an unaffected locked test would lose its copy.
    import hashlib
    import multiprocessing

    with_other_test(project)
    prepare_implementation(project)
    approve_unlock(project, {RELEASE: "fail"}, [{"argv": CHECK, "tests": [RELEASE]}],
                   reason="The cancellation test asserts the wrong call.")

    def corrected(root):
        (root / RELEASE).write_text(CORRECTED)
        return [RELEASE]

    run_test_tasks(project, {"prepare-tests": corrected})
    process = multiprocessing.get_context("fork").Process(target=_relock_killed_midway, args=(project,))
    process.start()
    process.join(60)
    assert process.exitcode == 9, (
        f"The simulated kill did not interrupt the copy writing (exit {process.exitcode}); "
        "the test's interruption point needs adjusting to how copies are written.")
    record = store.load(project, "feature")
    if record["phases"]["test-checkpoint"]["pending"]:
        mutate(project, close.recover, "test-checkpoint", "s", "The checkpoint process was killed.")
    record = store.load(project, "feature")
    for path, lock in record["locks"].items():
        copy = copy_of(project, path)
        assert copy is not None and hashlib.sha256(copy.read_bytes()).hexdigest() == lock, (
            f"After recovery, locked test {path} has no usable copy matching its lock.")
    # A later accidental edit of the unaffected test gets its diff and restore works.
    locked_other = (project / OTHER).read_bytes()
    (project / OTHER).write_text(OTHER_EDIT)
    message = start(project, "prepare-tests", "rework-author-2")
    assert message is not None and OTHER in message
    events = violations(project)
    lines = {line.strip() for text in [message, *event_strings(events[-1])] for line in text.splitlines()}
    assert "+" + OTHER_EDIT.strip() in lines and "-assert 1 == 1" in lines, "No diff against a usable copy."
    restore(project, OTHER)
    assert (project / OTHER).read_bytes() == locked_other


def deletion_refused_or_done(root, action):
    """Run an action that deletes the copies folder while part of it cannot be deleted;
    it must be refused, or the folder must really be gone."""
    folder = root / UNIT / lock_folder()
    blocked = folder / "tests"
    assert blocked.is_dir(), "No copies to delete."
    blocked.chmod(0o555)
    try:
        refused = refusal(action)
    finally:
        if blocked.exists():
            blocked.chmod(0o755)
    assert refused is not None or not folder.exists(), (
        "Deleting the copies failed, yet the operation reported success with the copies still in place.")


def test_a_failed_copies_deletion_at_implementation_close_is_surfaced(project):
    closed_implementation(project)
    deletion_refused_or_done(
        project, lambda: close.close_phase(project, "feature", "implement", "s", reviewer=clean_review))


def test_a_failed_copies_deletion_at_a_breakdown_reopen_is_surfaced(project):
    prepare_implementation(project)
    deletion_refused_or_done(project, lambda: reopen(project, "breakdown"))


def test_restore_recreates_a_symlinked_test_whose_target_folder_was_deleted(project):
    # Catches writing through a dangling link without recreating its target's folder.
    import shutil

    shared = project / "shared"
    shared.mkdir()
    (shared / "link_check.py").write_text("assert True\n")
    (project / "tests/link_check.py").symlink_to("../shared/link_check.py")
    prepare_implementation(project)
    assert "tests/link_check.py" in store.load(project, "feature")["locks"]
    locked = (shared / "link_check.py").read_bytes()
    shutil.rmtree(shared)
    try:
        restore(project, "tests/link_check.py")
    except OSError as exc:
        pytest.fail(f"Restore could not recreate the test through its link: {exc}")
    assert (shared / "link_check.py").read_bytes() == locked
    assert (project / "tests/link_check.py").read_bytes() == locked


ESCAPED = ".copies/escaped_check.py"


def test_a_test_whose_copy_path_is_escaped_gets_its_diff_and_exact_restore(project):
    # Guard: catches joining the copies folder and the path without copy_path's escaping.
    from .test_workflow_implement_stages import edit_scope

    edit_scope(project, tests=["tests", ".copies"])
    (project / ".copies").mkdir()
    locked = b"assert True  # escaped\n"
    (project / ESCAPED).write_bytes(locked)
    prepare_implementation(project)
    assert ESCAPED in store.load(project, "feature")["locks"]
    escaped_copy = test_preparation.copy_path(project / UNIT / lock_folder(), ESCAPED)
    assert escaped_copy.relative_to(project / UNIT / lock_folder()).parts[:2] == (".copies", ".copies")
    assert escaped_copy.read_bytes() == locked
    (project / ESCAPED).write_text(SHELL_EDIT)
    message = start(project, "cancel", "implementer")
    assert message is not None and ESCAPED in message
    lines = {line.strip() for text in [message, *event_strings(violations(project)[-1])]
             for line in text.splitlines()}
    assert "+" + SHELL_EDIT.strip() in lines and "-assert True  # escaped" in lines, "No diff for the escaped path."
    restore(project, ESCAPED)
    assert (project / ESCAPED).read_bytes() == locked


# Follow-ups from review round 4 (logged at the review cap; each fails loudly once fixed)


def _run_killed(target, *args):
    import multiprocessing

    process = multiprocessing.get_context("fork").Process(target=target, args=args)
    process.start()
    process.join(60)
    assert process.exitcode == 9, f"The simulated kill did not happen (exit {process.exitcode})."


def _close_killed_after_deleting_copies(root):
    original = test_preparation.discard_locked_copies

    def discard_then_die(*args, **kwargs):
        original(*args, **kwargs)
        os._exit(9)

    test_preparation.discard_locked_copies = discard_then_die
    close.close_phase(root, "feature", "implement", "s", reviewer=clean_review)
    os._exit(0)


def assert_usable_copies(root, unit="feature"):
    import hashlib

    record = store.load(root, unit)
    assert record["locks"], "No locks to check."
    folder = root / ".fbk" / unit / lock_folder()
    for path, lock in record["locks"].items():
        copy = test_preparation.copy_path(folder, path)
        assert copy.is_file() and hashlib.sha256(copy.read_bytes()).hexdigest() == lock, (
            f"Unit {unit}: locked test {path} has no usable copy matching its lock.")


def test_followup_a_close_killed_after_deleting_copies_recovers_them(project):
    closed_implementation(project)
    _run_killed(_close_killed_after_deleting_copies, project)
    if store.load(project, "feature")["phases"]["implement"]["pending"]:
        mutate(project, close.recover, "implement", "s", "The close process was killed.")
    record = store.load(project, "feature")
    assert record["phases"]["implement"]["evidence"] is None and record["open_phase"] == "implement", (
        "The killed close was accepted.")
    assert_usable_copies(project)
    locked = (project / RELEASE).read_bytes()
    (project / RELEASE).write_text(SHELL_EDIT)
    restore(project, RELEASE)
    assert (project / RELEASE).read_bytes() == locked


def _sub_relock_killed(root, sub):
    import pathlib

    record = store.load(root, sub)
    contents = {(root / path).read_bytes() for path in record["locks"]}
    original = pathlib.Path.write_bytes
    writes = []

    def write_bytes(self, data):
        if bytes(data) in contents:
            writes.append(str(self))
            if len(writes) == 2:
                os._exit(9)
        return original(self, data)

    pathlib.Path.write_bytes = write_bytes
    with store.transaction(root):
        test_preparation.save_locked_copies(root, store.load(root, sub), record["locks"])
    os._exit(0)


def nested_unit_with_copies(root, sub="feature/sub"):
    """A second unit nested under feature, holding the same locks and their copies, as a
    nested unit that reached writing code would."""
    import json
    import shutil

    target = root / ".fbk" / sub
    target.mkdir(parents=True)
    for name in ("prd.md", "spec.md", "scope.json", "tasks.json"):
        shutil.copy2(root / UNIT / name, target / name)
    record = json.loads((root / UNIT / "state.json").read_text())
    record["unit"] = sub
    store.save(root, record)
    shutil.copytree(root / UNIT / lock_folder(), target / lock_folder())
    assert_usable_copies(root, sub)
    return sub


@pytest.mark.parametrize("cleanup", ["implementation-close", "breakdown-reopen"])
def test_followup_a_parent_cleanup_keeps_a_nested_units_set_aside_copies(project, cleanup):
    with_other_test(project)
    if cleanup == "implementation-close":
        closed_implementation(project)
    else:
        prepare_implementation(project)
    sub = nested_unit_with_copies(project)
    _run_killed(_sub_relock_killed, project, sub)
    if cleanup == "implementation-close":
        close.close_phase(project, "feature", "implement", "s", reviewer=clean_review)
    else:
        reopen(project, "breakdown")
    mutate(project, close.recover, "test-checkpoint", "s", "The nested unit's checkpoint was killed.", unit=sub)
    assert_usable_copies(project, sub)


@pytest.mark.parametrize("unit, readable, other", [
    ("feature", "feature", "feature-x"),
    ("parent/child", "parent-child", "parent-child"),
    ("billing/" + "refunds-" * 40, ("billing/" + "refunds-" * 40).replace("/", "-")[:48],
     "billing/" + "refunds-" * 41),
    ("退款", "--", "退货"),
    (" team", "-team", "?team"),
])
def test_a_units_runtime_folder_starts_with_its_name_and_stays_one_short_segment(
        project, unit, readable, other):
    """An operator correlates a runtime folder with its unit by name, so the folder starts
    with the unit name (unsafe characters as hyphens, cut to 48); 16 hex characters of the
    full name's digest keep it unique and one segment of at most 65 characters."""
    folder = test_preparation._runtime_folder(project, "locked-tests-previous", unit)
    assert folder.parent == project / ".fbk/runtime/locked-tests-previous"
    assert folder.name == f"{readable}-{hashlib.sha256(unit.encode()).hexdigest()[:16]}"
    assert len(folder.name) <= 65
    assert folder != test_preparation._runtime_folder(project, "locked-tests-previous", other)


def relocked(root):
    """A relock after rework, so the copies it replaced are still set aside."""
    prepare_implementation(root)
    approve_unlock(root, {RELEASE: "fail"}, [{"argv": CHECK, "tests": [RELEASE]}],
                   reason="The cancellation test asserts the wrong call.")

    def corrected(r):
        (r / RELEASE).write_text(CORRECTED)
        return [RELEASE]

    run_test_tasks(root, {"prepare-tests": corrected})
    assert checkpoint_refusal(root) is None


@pytest.mark.parametrize("cleanup", ["implementation-close", "breakdown-reopen"])
def test_followup_a_failed_deletion_of_the_previous_copies_is_surfaced(project, cleanup):
    relocked(project)
    if cleanup == "implementation-close":
        assert start(project, "cancel", "implementer") is None
        (project / "src/app.py").write_text("release()")
        finish(project, "cancel", ["src/app.py"], CHECK)
        complete_refactor_tasks(project)
        action = lambda: close.close_phase(project, "feature", "implement", "s", reviewer=clean_review)  # noqa: E731
    else:
        action = lambda: reopen(project, "breakdown")  # noqa: E731
    previous = test_preparation._previous_copies(project, store.load(project, "feature"))
    if not previous.is_dir():
        return  # Nothing set aside to fail deleting: the follow-up is resolved another way.
    blocked = next(p for p in previous.rglob("*") if p.is_dir())
    blocked.chmod(0o555)
    try:
        refused = refusal(action)
    finally:
        if blocked.exists():
            blocked.chmod(0o755)
    assert refused is not None or not previous.exists(), (
        "Deleting the set-aside copies failed, yet the operation reported success with them still in place.")


# Follow-up group A, review round 1


def test_a_close_whose_copies_deletion_fails_partway_keeps_them_recoverable(project, monkeypatch):
    # Catches dropping the set-aside copy when deleting the live copies fails after
    # removing some of them: the locks stay, and recover-close has nothing to put back.
    import pathlib

    with_other_test(project)
    closed_implementation(project)
    live = (project / UNIT / lock_folder()).resolve()
    original = test_preparation.remove_folder

    def remove_one_then_fail(root, path):
        if pathlib.Path(path).resolve() != live:
            return original(root, path)
        test_preparation.copy_path(live, RELEASE).unlink()
        raise store.WorkflowError(f"Firebreak could not delete {path} (Permission denied); make it deletable.")

    with monkeypatch.context() as patched:
        patched.setattr(test_preparation, "remove_folder", remove_one_then_fail)
        message = refusal(lambda: close.close_phase(project, "feature", "implement", "s", reviewer=clean_review))
    assert message is not None, "The close was accepted although deleting the copies failed."
    mutate(project, close.recover, "implement", "s", "The copies deletion failed partway.")
    assert_usable_copies(project)


def _close_killed_after_saving_acceptance(root):
    def die(*args, **kwargs):
        os._exit(9)

    test_preparation.drop_discarded_copies = die
    close.close_phase(root, "feature", "implement", "s", reviewer=clean_review)
    os._exit(0)


def test_recovery_after_an_accepted_close_deletes_its_set_aside_copies(project):
    # Catches recover-close putting the set-aside copies back into an accepted close.
    closed_implementation(project)
    _run_killed(_close_killed_after_saving_acceptance, project)
    assert store.load(project, "feature")["phases"]["implement"]["evidence"], "The close was not accepted."
    mutate(project, close.recover, "implement", "s", "The close process was killed during cleanup.")
    assert copy_of(project, RELEASE) is None, "Recovery restored the copies of an accepted implementation close."
    assert not test_preparation._previous_copies(project, store.load(project, "feature")).exists(), (
        "Recovery kept the set-aside copies of an accepted implementation close.")


def test_a_nested_unit_with_long_segment_names_can_save_copies_and_record_a_baseline(project):
    # Catches escaping the whole unit name into one folder name, which exceeds the
    # file-name length limit (255 bytes) for a valid unit whose segments are each short.
    prepare_implementation(project)
    sub = nested_unit_with_copies(project, "feature/" + "a" * 125 + "/" + "b" * 125)
    try:
        with store.transaction(project):
            record = store.load(project, sub)
            test_preparation.save_locked_copies(project, record, record["locks"])
            test_preparation.record_baseline(project, record, "s", "unlock approval")
    except (OSError, store.WorkflowError) as exc:
        pytest.fail(f"A valid nested unit name could not use its runtime folders: {exc}")


# Follow-up group A, review round 2


def test_a_breakdown_reopen_retried_after_partial_copies_deletions_keeps_them_recoverable(project, monkeypatch):
    # Catches reconciling against the already-cleared locks on a retry: every set-aside
    # copy then looks superseded and is dropped, although the saved state still locks both.
    import pathlib

    with_other_test(project)
    prepare_implementation(project)
    live = (project / UNIT / lock_folder()).resolve()
    original = test_preparation.remove_folder
    attempts = []

    def fail_partway(root, path):
        if pathlib.Path(path).resolve() != live:
            return original(root, path)
        attempts.append(path)
        if len(attempts) == 1:
            test_preparation.copy_path(live, RELEASE).unlink()
        raise store.WorkflowError(f"Firebreak could not delete {path} (Permission denied); make it deletable.")

    with monkeypatch.context() as patched:
        patched.setattr(test_preparation, "remove_folder", fail_partway)
        for _ in range(2):
            assert refusal(lambda: reopen(project, "breakdown")) is not None, "The reopen was not refused."
    assert len(attempts) == 2, "The retried reopen never tried to delete the copies again."
    mutate(project, close.recover, "implement", "s", "The copies deletion failed twice.")
    assert_usable_copies(project)


DEEP = "tests/deep/deep_check.py"


def test_a_close_whose_copies_cannot_all_be_listed_keeps_every_copy(project, monkeypatch):
    # Catches a set-aside copy that silently misses an unlistable folder: deleting the live
    # copies then leaves no folder holding every locked copy.
    import pathlib

    (project / "tests/deep").mkdir()
    (project / DEEP).write_text("assert 2 == 2\n")
    closed_implementation(project)
    assert DEEP in store.load(project, "feature")["locks"], "The nested test was not locked."
    live = (project / UNIT / lock_folder()).resolve()
    unlistable = test_preparation.copy_path(live, DEEP).parent
    original = test_preparation.remove_folder

    def remove_one_then_fail(root, path):
        if pathlib.Path(path).resolve() != live:
            return original(root, path)
        test_preparation.copy_path(live, RELEASE).unlink()
        raise store.WorkflowError(f"Firebreak could not delete {path} (Permission denied); make it deletable.")

    unlistable.chmod(0o000)
    try:
        with monkeypatch.context() as patched:
            patched.setattr(test_preparation, "remove_folder", remove_one_then_fail)
            message = refusal(lambda: close.close_phase(project, "feature", "implement", "s", reviewer=clean_review))
    finally:
        unlistable.chmod(0o755)
    assert message is not None, "The close was accepted although its copies could not all be set aside."
    mutate(project, close.recover, "implement", "s", "The copies could not all be listed.")
    assert_usable_copies(project)


# Follow-up group A, review round 3


def _set_aside_copies_undeletable(monkeypatch):
    """After the copies are set aside, make their folder undeletable, so the deletion after
    the durable save fails; returns a function that makes it deletable again."""
    blocked = []
    original = test_preparation.discard_locked_copies

    def discard_then_block(root, record):
        original(root, record)
        folder = test_preparation.copy_path(test_preparation._previous_copies(root, record), RELEASE).parent
        folder.chmod(0o555)
        blocked.append(folder)

    monkeypatch.setattr(test_preparation, "discard_locked_copies", discard_then_block)

    def unblock():
        monkeypatch.undo()
        for folder in blocked:
            folder.chmod(0o755)
        assert blocked, "The copies were never set aside."

    return unblock


def assert_cleanup_failed_then_settled(root, result, phase="implement"):
    """The operation committed and said its cleanup failed; recover-close then deletes the
    leftover set-aside copies without bringing any copy back."""
    assert "cleanup_failed" in result, f"A failed cleanup after the save was not reported: {sorted(result)}"
    previous = test_preparation._previous_copies(root, store.load(root, "feature"))
    assert previous.is_dir(), "The set-aside copies were deleted although their deletion was made to fail."
    assert copy_of(root, RELEASE) is None, "The live copies outlived the committed operation."
    mutate(root, close.recover, phase, "s", "Settle the leftover set-aside copies.")
    assert not previous.exists(), "recover-close did not delete the leftover set-aside copies."
    assert copy_of(root, RELEASE) is None, "recover-close brought obsolete copies back."


def test_a_cleanup_failure_after_an_accepted_implementation_close_is_reported_and_settled(project, monkeypatch):
    closed_implementation(project)
    unblock = _set_aside_copies_undeletable(monkeypatch)
    try:
        result = close.close_phase(project, "feature", "implement", "s", reviewer=clean_review)
    finally:
        unblock()
    assert store.load(project, "feature")["phases"]["implement"]["evidence"], "The close was not committed."
    assert_cleanup_failed_then_settled(project, result)


def test_a_cleanup_failure_after_a_breakdown_reopen_is_reported_and_settled(project, monkeypatch):
    prepare_implementation(project)
    reason = "Revisit the plan."
    mutate(project, engine.approve, "s", "reopen", "breakdown", reason)
    unblock = _set_aside_copies_undeletable(monkeypatch)
    try:
        result = mutate(project, engine.reopen, "breakdown", "s", reason)
    finally:
        unblock()
    record = store.load(project, "feature")
    assert record["locks"] == {} and not record["phases"]["breakdown"]["evidence"], "The reopen was not committed."
    assert_cleanup_failed_then_settled(project, result, "breakdown")


def test_a_cleanup_failure_after_a_breakdown_invalidating_repair_is_reported_and_settled(project, monkeypatch):
    from .test_workflow_repair_clears_locks import assert_cleared, locked, repair_spec

    locked(project, built=True)
    unblock = _set_aside_copies_undeletable(monkeypatch)
    try:
        result = repair_spec(project)
    finally:
        unblock()
    assert_cleared(project)
    assert not store.load(project, "feature")["phases"]["breakdown"]["evidence"], "The repair was not committed."
    assert_cleanup_failed_then_settled(project, result, "breakdown")


def _implement_reopen_killed_after_reconciling(root):
    original = test_preparation.reconcile_locked_copies

    def reconcile_then_die(*args, **kwargs):
        original(*args, **kwargs)
        os._exit(9)

    test_preparation.reconcile_locked_copies = reconcile_then_die
    mutate(root, engine.reopen, "implement", "s", "Revisit the delivered code.")
    os._exit(0)


def test_recovery_after_an_interrupted_implement_reopen_removes_the_revived_copies(project, monkeypatch):
    # Catches an implement reopen reviving an accepted close's leftover set-aside copies as
    # live copies before it is saved: killed there, recovery finds nothing set aside and
    # leaves live copies in a closed unit, which restore can write over later edits.
    closed_implementation(project)
    unblock = _set_aside_copies_undeletable(monkeypatch)
    try:
        result = close.close_phase(project, "feature", "implement", "s", reviewer=clean_review)
    finally:
        unblock()
    assert "cleanup_failed" in result
    observe_phase(project, "implement")
    mutate(project, engine.approve, "s", "reopen", "implement", "Revisit the delivered code.")
    _run_killed(_implement_reopen_killed_after_reconciling, project)
    assert store.load(project, "feature")["phases"]["implement"]["evidence"], "The killed reopen was saved."
    mutate(project, close.recover, "implement", "s", "The reopen process was killed.")
    assert copy_of(project, RELEASE) is None, "Recovery left live copies in an accepted implementation."
    assert not test_preparation._previous_copies(project, store.load(project, "feature")).exists()
