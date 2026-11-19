"""Tests are written and checked before code: test tasks run in implement, and the test
checkpoint compares their work with the writing-tests baseline, runs every check, and locks
the reviewed tests. Plan validation runs at breakdown close and again at each task start."""

import difflib
import hashlib
import os
import re
import shutil
import stat
from pathlib import Path

from . import evidence, traceability
from .store import (
    ACCEPTED_OUTPUT_FOLDER,
    BASELINE_FOLDER,
    LOCKED_FOLDER,
    WorkflowError,
    confined,
    event,
    ignore_everything,
    now,
    read_json,
    readable,
    record_folder,
    remove_folder,
    remove_record_folder,
    save,
    unclaimed_record_folder,
    unit_dir,
)


def source_files(root, record):
    """Every production file in scope, region-bearing files included, by whole-file fingerprint."""
    declared = evidence.scope(root, record["unit"])
    return evidence.file_hashes(
        root,
        [
            p
            for p in evidence.expand(root, declared["sources"])
            if not evidence.matches(p, declared["tests"])
        ],
    )


def file_mode(path):
    """A file's type and executable bit as Git records them: 120000 for a symbolic link,
    100755 for an executable file, 100644 otherwise; None when it does not exist."""
    try:
        status = os.lstat(path)
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(status.st_mode):
        return "120000"
    return "100755" if status.st_mode & 0o111 else "100644"


def file_modes(root, paths):
    return {relative: file_mode(confined(root, relative)) for relative in sorted(set(paths))}


# A record folder's own top-level .gitignore ignores everything in it, so a project path
# that would land on that name, or on the escape folder itself, is stored under the
# escape folder instead; every other copy sits at its own relative path.
ESCAPE = ".copies"


def copy_path(folder, relative):
    """Where a record folder keeps its copy of a project path."""
    first = Path(relative).parts[0]
    return Path(folder) / (f"{ESCAPE}/{relative}" if first in {".gitignore", ESCAPE} else relative)


def save_copies(root, record, folder, paths):
    """Replace one of the unit's record folders with a copy of each file at its own
    relative path, keeping its executable bit, and return the copies' fingerprints and
    the files' modes."""
    target = record_folder(root, record["unit"], folder)
    shutil.rmtree(target, ignore_errors=True)
    hashes, modes = _write_copies(root, target, paths)
    target.mkdir(parents=True, exist_ok=True)
    ignore_everything(target)
    return hashes, modes


def _write_copies(root, target, paths):
    """Write a copy of each file under target at its own relative path, keeping its
    executable bit, and return the copies' fingerprints and the files' modes."""
    hashes, modes = {}, {}
    for relative in sorted(set(paths)):
        source = confined(root, relative)
        data = source.read_bytes()
        copy = copy_path(target, relative)
        copy.parent.mkdir(parents=True, exist_ok=True)
        copy.write_bytes(data)
        modes[relative] = file_mode(source)
        copy.chmod(0o755 if modes[relative] == "100755" else 0o644)
        hashes[relative] = hashlib.sha256(data).hexdigest()
    return hashes, modes


def keep_accepted_output(root, record):
    """Before a checkpoint run replaces the saved check output, copy the previous accepted
    checkpoint's output into the unit's accepted-output folder, unless the copy there is
    already that output. Output that is neither is left for the reviewer's required
    reading to refuse."""
    target = unit_dir(root, record["unit"]) / ACCEPTED_OUTPUT_FOLDER
    items = _accepted_items(record)
    if not items or all(_matches(target / Path(item["path"]).name, item["sha256"]) for item in items):
        return
    if not all(_matches(confined(root, item["path"]), item["sha256"]) for item in items):
        return
    data = {Path(item["path"]).name: confined(root, item["path"]).read_bytes() for item in items}
    target = record_folder(root, record["unit"], ACCEPTED_OUTPUT_FOLDER)
    shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True)
    ignore_everything(target)
    for name, content in data.items():
        (target / name).write_bytes(content)


def accepted_output_paths(root, record):
    """The previous accepted checkpoint's kept output, as required reading for a later
    checkpoint's reviewer; refused when a copy is missing or no longer its recorded bytes."""
    base = unit_dir(root, record["unit"]).relative_to(Path(root).resolve()).as_posix()
    paths = []
    for item in _accepted_items(record):
        path = f"{base}/{ACCEPTED_OUTPUT_FOLDER}/{Path(item['path']).name}"
        if not _matches(confined(root, path), item["sha256"]):
            raise WorkflowError(
                f"Unit {record['unit']}: the previous accepted checkpoint's saved output {path} is missing or "
                "no longer matches its recorded fingerprint, so the reviewer cannot read the red it carries "
                "forward. Restore it if you kept a copy (its fingerprint is in the unit's state); the folder is "
                "git-ignored, so once its bytes are lost they cannot be recovered: move the unit under "
                ".fbk/archive/ and redo it as a new unit."
            )
        paths.append(path)
    return paths


def _accepted_items(record):
    """Each saved output file of the previous accepted checkpoint, with its fingerprint."""
    from .engine import accepted_checkpoint

    return [item for check in (accepted_checkpoint(record) or {}).get("verification", [])
            for item in check.get("saved_output", {}).values()]


def _matches(path, sha256):
    data = _read(path, f"Saved check output {path.name}")
    return data is not None and hashlib.sha256(data).hexdigest() == sha256


def record_baseline(root, record, session, reason):
    """Record the writing-tests baseline the test checkpoint compares against: a saved copy
    and fingerprint of every scoped test file and every production file in scope. It is
    recorded whenever the unit begins or returns to writing tests; task relaunches,
    cancellations, and checkpoint rejections never re-record it, so an earlier change
    cannot hide. Implementation tasks running at that moment are named, so their later
    verified changes are theirs. The caller saves the record."""
    declared = evidence.scope(root, record["unit"])
    _set_aside_baseline(root, record)
    files, modes = save_copies(root, record, BASELINE_FOLDER,
                               evidence.expand(root, declared["tests"] + declared["sources"]))
    # A region-bearing file is saved whole; its region's fingerprint is recorded apart.
    regions = {path: evidence.test_fingerprint(declared, path, _baseline_copy(root, record, path, files[path]))
               for path in files if evidence.region_start(declared, path) is not None}
    running = {task: run["assignment_id"] for task, run in record.get("task_runs", {}).items()
               if run["status"] == "running" and run.get("stage", "implementation") == "implementation"}
    # A symbolic link's target is recorded apart, as its fingerprint reads through it.
    links = evidence.symlink_targets(root, files)
    extra = {**({"regions": regions} if regions else {}), **({"links": links} if links else {})}
    record["writing_tests_baseline"] = {"at": now(), "reason": reason, "files": files, "modes": modes,
                                        "running": running, **extra}
    event(record, "writing-tests-baseline-recorded", session, reason=reason, files=files, modes=modes,
          running=running, **extra)


def _previous_baseline(root, record, whole=False):
    """Where the baseline copies a re-record replaces wait until a later re-record, so an
    interrupted one leaves the copies its saved baseline names. They are named by the time
    that baseline was recorded, so once a replacement is saved they are never read; with
    whole, the unit's folder holding every such set."""
    folder = _runtime_folder(root, "writing-tests-baseline-previous", record["unit"])
    if whole:
        return folder
    at = (record.get("writing_tests_baseline") or {}).get("at", "")
    return folder / hashlib.sha256(at.encode()).hexdigest()


def _set_aside_baseline(root, record):
    """Before a re-record replaces the baseline copies, keep the set holding every copy the
    saved baseline names: the current copies, or those set aside by an earlier re-record
    that was interrupted. The other set is deleted."""
    recorded = (record.get("writing_tests_baseline") or {}).get("files", {})
    live = unclaimed_record_folder(root, record["unit"], BASELINE_FOLDER)
    previous = _previous_baseline(root, record)

    def complete(folder):
        return all(_matches_hash(copy_path(folder, path), value) for path, value in recorded.items())

    if recorded and complete(previous):
        return
    remove_folder(root, _previous_baseline(root, record, whole=True))
    if recorded and complete(live):
        previous.parent.mkdir(parents=True, exist_ok=True)
        live.rename(previous)


def _matches_hash(path, value):
    data = _content(path)
    return data is not None and hashlib.sha256(data).hexdigest() == value


# Where an implementation task running when the writing-tests baseline was recorded keeps
# the content of its verified return, inside Firebreak's git-ignored runtime folder.
RETURNS = "verified-returns"


def keep_verified_return(root, record, task_id, run):
    """Keep a copy of each file an implementation task's return records as changed since
    the writing-tests baseline, when that baseline names the assignment as running. A test
    task that later changes a shared file then shows the reviewer only its own change,
    against this content."""
    baseline = record.get("writing_tests_baseline") or {}
    if baseline.get("running", {}).get(task_id) != run["assignment_id"]:
        return
    kept = _runtime_folder(root, RETURNS, record["unit"])
    # The baseline naming this assignment is saved, so copies kept for assignments it does
    # not name belong to a superseded baseline.
    if kept.is_dir():
        for folder in kept.iterdir():
            if folder.name not in baseline["running"].values() or folder.name == run["assignment_id"]:
                remove_folder(root, folder)
    folder = kept / run["assignment_id"]
    changed = {path: value for path, value in run["return"]["files"].items()
               if value is not None and baseline["files"].get(path) != value}
    hashes, _ = _write_copies(root, folder, changed)
    moved = sorted(path for path in changed if hashes[path] != changed[path])
    if moved:
        raise WorkflowError(
            f"Task outputs changed while Firebreak kept a copy of the task's return: {', '.join(moved)}; "
            "inspect changes and retry."
        )
    # Kept with the return, so a later change to a returned file's executable bit shows.
    present = [path for path, value in run["return"]["files"].items() if value is not None]
    run["return"]["modes"] = file_modes(root, present)
    # Always recorded, even empty: a return without it predates link targets, so its
    # links are unknown.
    run["return"]["links"] = evidence.symlink_targets(root, present)


# Stands for a path no qualifying verified return records as changed since the baseline.
NO_RETURN = object()


def _returned_copy(root, record, finished, path):
    """What a qualifying verified return recorded for a path changed since the baseline:
    its kept content, None for a file it deleted, and NO_RETURN otherwise. A kept copy that
    is missing or no longer that content is refused."""
    baseline = record["writing_tests_baseline"]["files"]
    for assignment, result in finished:
        if path not in result.get("files", {}) or result["files"][path] == baseline.get(path):
            continue
        value = result["files"][path]
        if value is None:
            return None
        copy = copy_path(_runtime_folder(root, RETURNS, record["unit"]) / assignment, path)
        if not _matches_hash(copy, value):
            raise WorkflowError(
                f"Unit {record['unit']}: the kept copy of {path} from a verified implementation return "
                f"({copy.relative_to(Path(root).resolve()).as_posix()}) is missing or no longer matches the "
                "return's fingerprint, so the checkpoint cannot show the test tasks' change to it apart from "
                "that return. Restore it to the content the return's fingerprint records, or relaunch the "
                "implementation task, then run test-checkpoint again."
            )
        return copy.read_bytes()
    return NO_RETURN


def _returned_mode(finished, path):
    """The mode a qualifying verified return recorded for a path, or None."""
    return next((result["modes"][path] for _, result in finished if path in result.get("modes", {})), None)


def _returned_link(finished, path):
    """The link target a qualifying verified return recorded for a path it records, None
    when that path was not a link, and NO_RETURN when no such return records it or the
    return predates link targets, so they are unknown."""
    result = next((result for _, result in finished if path in result.get("files", {})), None)
    return NO_RETURN if result is None or "links" not in result else result["links"].get(path)


def retargeted_since(root, accepted, paths):
    """The tests whose symbolic-link target differs from the one recorded when the
    checkpoint accepted them. A fingerprint reads through a link, so a test retargeted
    between equal files is unchanged by content alone. An acceptance from before link
    targets were recorded gives none."""
    captured = (accepted or {}).get("test_links")
    if captured is None:
        return set()
    current = evidence.symlink_targets(root, paths)
    return {path for path in paths if captured.get(path) != current.get(path)}


def scoped_tests(root, record):
    """The scoped tests the lock would cover: whole test files and non-empty test regions."""
    declared = evidence.scope(root, record["unit"])
    return sorted(evidence.held_tests(declared, evidence.test_fingerprints(root, declared)))


def held_in_baseline(root, record):
    """The paths that held a scoped test when the writing-tests baseline was recorded: whole
    test files and region-bearing files whose recorded region was not empty."""
    declared = evidence.scope(root, record["unit"])
    baseline = record["writing_tests_baseline"]
    recorded = {path: baseline.get("regions", {}).get(path, evidence.EMPTY_REGION)
                if evidence.region_start(declared, path) is not None else value
                for path, value in baseline["files"].items()
                if evidence.region_start(declared, path) is not None or evidence.matches(path, declared["tests"])}
    return set(evidence.held_tests(declared, recorded))


def record_outcome(root, record, session):
    """Record, on entering implement with a plan that has no test task, which outcome
    applies: preservation when scoped tests exist, so the checkpoint locks them as they
    are, or no-tests, with the empty test inventory, so a test appearing later is refused.
    A plan with test tasks takes the normal flow and records nothing. The caller saves."""
    tasks = read_json(unit_dir(root, record["unit"]) / "tasks.json")
    if any(task.get("stage") == "tests" for task in tasks):
        return
    tests = scoped_tests(root, record)
    event(record, "test-outcome-recorded", session, outcome="preservation" if tests else "no-tests",
          inventory=tests)


def check_empty_inventory(root, record, refused, failure=None):
    """In the no-tests outcome, refuse while any scoped test exists, naming each: the unit
    recorded none when implement was entered, so a test appearing later was never reviewed.
    A failure that interrupted a task's checks is kept at the head of the message."""
    from .engine import test_outcome

    if test_outcome(root, record) != "no-tests":
        return
    tests = scoped_tests(root, record)
    if tests:
        raise WorkflowError(
            (f"{failure} " if failure else "")
            + f"Unit {record['unit']} had no scoped tests and no test tasks when implement was entered, "
            f"so it has no test checkpoint, but scoped tests now exist: {', '.join(tests)}. {refused} while "
            "they exist: remove them, or reopen breakdown to plan a test task for them."
        )


def baseline_comparison(root, record, *, diffs=False):
    """Compare the current tree with the writing-tests baseline for the test checkpoint.

    Scoped tests that differ from it were changed by test tasks; the rest are untouched. A
    production change outside every test task's declared files is refused, except within
    the owned files of an implementation task that was running when the baseline was
    recorded and has since completed with verified changes; those are listed apart from
    the test tasks' changes. With diffs, each test task's production change comes back as
    a unified diff against its baseline copy."""
    unit = record["unit"]
    baseline = record.get("writing_tests_baseline")
    if not baseline:
        raise WorkflowError(
            f"Unit {unit} entered implement before Firebreak recorded writing-tests baselines, so its "
            "baseline cannot be recovered and the checkpoint cannot tell which tests and production "
            "files changed while tests were written. Move the unit under .fbk/archive/ and redo it as a new unit."
        )
    declared = evidence.scope(root, unit)
    recorded, recorded_modes = baseline["files"], baseline.get("modes", {})
    # Every saved copy must still be the recorded one, or the baseline is incomplete.
    for path in recorded:
        _baseline_copy(root, record, path)
    # A region-bearing file is two things: its region is a scoped test, compared by the
    # region's fingerprint, and the code above it is a production file, compared without
    # the region. Its mode belongs to the production side. A file without a region
    # compares as one with an empty region.
    tests = evidence.test_fingerprints(root, declared)
    regions = {path for path in set(recorded) | set(tests) if evidence.region_start(declared, path) is not None}
    recorded_tests = {path: baseline.get("regions", {}).get(path, evidence.EMPTY_REGION) if path in regions else value
                      for path, value in recorded.items()
                      if path in regions or evidence.matches(path, declared["tests"])}
    modes = file_modes(root, tests)
    current_files = source_files(root, record)
    recorded_links, links = baseline.get("links", {}), evidence.symlink_targets(root, [*tests, *current_files])

    def mode_differs(path):
        return path in recorded_modes and recorded_modes[path] != modes[path]

    def link_differs(path):
        # A link's target, or a change between a link and a regular file. A baseline
        # recorded before link targets were records none, but its mode names a link.
        return (path in recorded_links and recorded_links[path] != links.get(path)
                or path in recorded_modes and (recorded_modes[path] == "120000") != (path in links))

    # A region's tests change with the file's link target too, unlike its mode, which
    # belongs to the code above.
    changed = sorted(path for path, value in tests.items()
                     if recorded_tests.get(path, evidence.EMPTY_REGION if path in regions else None) != value
                     or path not in regions and mode_differs(path) or link_differs(path))
    modes.update(file_modes(root, current_files))
    before = {path: _code_fingerprint(declared, path, _baseline_copy(root, record, path)) if path in regions else value
              for path, value in recorded.items() if not evidence.matches(path, declared["tests"])}
    current = {path: _code_fingerprint(declared, path, confined(root, path).read_bytes()) if path in regions else value
               for path, value in current_files.items()}
    # Code built before the baseline is inside it. An implementation task running when it
    # was recorded may finish afterwards: a change it recorded in that run's verified
    # return, still as it returned it, is that task's; anything else is undeclared.
    runs = record.get("task_runs", {})
    finished = [(assignment, runs[task]["return"]) for task, assignment in baseline.get("running", {}).items()
                if runs.get(task, {}).get("assignment_id") == assignment
                and runs[task]["status"] == "completed" and runs[task]["return"].get("verified_checks")]
    # A production file a return records differently from its current content changed
    # after that return, even when the change brings it back to the baseline.
    returned = {path: value for _, result in finished for path, value in result.get("files", {}).items()
                if evidence.matches(path, declared["sources"]) and not evidence.matches(path, declared["tests"])}
    production = sorted(path for path in set(before) | set(current) | set(returned)
                        if before.get(path) != current.get(path) or path in current and mode_differs(path)
                        or link_differs(path)
                        or path in returned and returned[path] != current_files.get(path)
                        or path in returned and path in modes
                        and _returned_mode(finished, path) not in {None, modes[path]}
                        or path in returned and _returned_link(finished, path) not in {NO_RETURN, links.get(path)})
    tasks = read_json(unit_dir(root, unit) / "tasks.json")
    by_tests = [path for task in tasks if task.get("stage") == "tests" for path in task["files"]]
    # Judged against the baseline, not the task's start: the return fingerprints every
    # owned file, so a file captured mid-change and later restored is the task's too.
    by_code = {
        path
        for _, result in finished
        for path in result.get("files", {})
        if path in production and current_files.get(path) == result["files"][path]
        # A return keeps the mode and link target of each file it records; any other mode
        # or link change is not its.
        and (path not in modes
             or result.get("modes", {}).get(path, recorded_modes.get(path)) in {None, modes[path]})
        and ("links" not in result or result["links"].get(path) == links.get(path))
    }
    undeclared = [path for path in production
                  if not evidence.matches(path, by_tests) and path not in by_code]
    from .engine import test_outcome

    if undeclared and test_outcome(root, record) == "preservation":
        # No test task exists to declare a production change before the tests lock.
        raise WorkflowError(
            f"Unit {unit}: production files changed since implement was entered: {', '.join(undeclared)}. "
            "A preservation checkpoint locks the existing tests before any code is written, and this unit has "
            f"no test task to declare a production change. Revert them to their saved copies in "
            f".fbk/{unit}/{BASELINE_FOLDER}/ (remove files that are new), or reopen breakdown to plan the work, "
            "then run test-checkpoint again."
        )
    if undeclared:
        raise WorkflowError(
            f"Unit {unit}: production files changed outside every test task's declared files since "
            f"writing tests began: {', '.join(undeclared)}. Restore them to their saved copies in "
            f".fbk/{unit}/{BASELINE_FOLDER}/ (remove files that are new), or rework the change through "
            "a test task that declares those files, then run test-checkpoint again."
        )
    result = {
        "changed_by_test_tasks": changed,
        "untouched": sorted(set(tests) - set(changed)),
        "removed_by_test_tasks": sorted(set(recorded_tests) - set(tests)),
        **({"verified_implementation_changes": sorted(by_code)} if by_code else {}),
    }
    if diffs:
        # Each diff is bound to the bytes it was made from; the reviewer's snapshot must
        # hold the same bytes, and the same tests, or no reader launches.
        result["production_diffs"] = {}
        # Bound by whole-file fingerprints, as the snapshot holds region-bearing files whole;
        # the tests' own fingerprints come back apart for the carried-forward comparison.
        result["compared"] = {**evidence.file_hashes(root, tests),
                              **{path: value for path, value in current_files.items()
                                 if evidence.matches(path, by_tests)}}
        result["fingerprints"] = tests
        # The bound inventory: a path these patterns cover that the comparison did not see
        # was added after it.
        result["bound"] = {"tests": declared["tests"] + [p for entry in declared.get("test_regions", [])
                                                         for p in entry["files"]],
                           "sources": declared["sources"], "declared": by_tests}
        # A verified implementation change stays bound above but is not shown as a test
        # task's production change; a test task's later change to the same file is shown
        # against the content that implementation task returned.
        for path in production:
            if evidence.matches(path, by_tests) and path not in by_code:
                link = _returned_link(finished, path)
                result["production_diffs"][path], result["compared"][path] = _baseline_diff(
                    root, record, declared, path, _returned_copy(root, record, finished, path),
                    _returned_mode(finished, path), recorded_links.get(path) if link is NO_RETURN else link)
        # The snapshot must capture each compared file's link target as the diffs saw it.
        result["compared_links"] = {path: links.get(path) for path in result["compared"]}
    return result


# Locked tests are checked at every task boundary. A worker can change one through the
# shell, which the write hook never sees, so task start and task finish compare each locked
# test with its lock; the saved copies show what changed and restore it.


def _runtime_folder(root, kind, unit):
    """One of a unit's folders inside Firebreak's git-ignored runtime folder: the unit name
    made readable, then a short SHA-256 digest of the full name. The name lets an operator
    tell whose folder it is; the digest keeps it unique, and one short segment means a
    nested unit's folder never sits inside its parent's and a long unit name still fits."""
    code = hashlib.sha256(unit.encode()).hexdigest()[:16]
    return confined(root, ".fbk/runtime") / kind / f"{readable(unit)}-{code}"


def _previous_copies(root, record):
    """Where the copies replaced by the latest save, or set aside by a deletion, wait
    until the lock state they belong to is known to be superseded."""
    return _runtime_folder(root, "locked-tests-previous", record["unit"])


def _copies_match(declared, folder, locks):
    """Whether a folder holds a copy matching each lock."""
    return all(_holds(declared, path, copy_path(folder, path), lock) for path, lock in locks.items())


def reconcile_locked_copies(root, record):
    """Settle a copy save that was interrupted before its lock state was saved: when the
    saved copies do not match the recorded locks and the copies they replaced do, put those
    back. The replaced copies are then dropped. Once implementation is accepted, its close
    discarded the copies, so any copies, live or set aside, are deleted."""
    previous = _previous_copies(root, record)
    if record["phases"]["implement"]["evidence"]:
        # An interrupted reopen of implement may have put them back before it was saved.
        remove_record_folder(root, record["unit"], LOCKED_FOLDER)
        remove_folder(root, previous)
        return
    if not previous.is_dir():
        return
    live = unclaimed_record_folder(root, record["unit"], LOCKED_FOLDER)
    declared = evidence.scope(root, record["unit"])
    if not _copies_match(declared, live, record["locks"]) and _copies_match(declared, previous, record["locks"]):
        shutil.rmtree(live, ignore_errors=True)
        previous.rename(live)
    remove_folder(root, previous)


def save_locked_copies(root, record, locks):
    """Replace the unit's saved copies of locked tests with a copy of each file, as these
    lock fingerprints record it; a region-bearing file is copied whole. The copies replaced
    are set aside and put back when the save fails; they stay set aside until the next save
    or recover-close confirms the lock state, so an interrupted save can be undone too."""
    reconcile_locked_copies(root, record)
    declared = evidence.scope(root, record["unit"])
    live = unclaimed_record_folder(root, record["unit"], LOCKED_FOLDER)
    previous = _previous_copies(root, record)
    previous.parent.mkdir(parents=True, exist_ok=True)
    kept = writing = False
    try:
        if live.is_dir():
            live.rename(previous)
            kept = True
        writing = True
        # A region-bearing file deleted with an empty region has nothing to copy.
        save_copies(root, record, LOCKED_FOLDER,
                    [path for path in locks if not _gone_empty(declared, path, confined(root, path), locks[path])])
        if not _copies_match(declared, live, locks):
            raise WorkflowError(
                "Locked tests changed while Firebreak saved their copies, so nothing was locked; leave the "
                "tests alone and retry."
            )
    except (OSError, WorkflowError) as exc:
        # Only copies this save wrote are removed; when setting the earlier copies aside
        # failed, they were never moved and stay as they are.
        if writing:
            shutil.rmtree(live, ignore_errors=True)
        if kept:
            previous.rename(live)
        if isinstance(exc, WorkflowError):
            raise
        raise WorkflowError(
            f"Firebreak could not save the copies of the locked tests ({getattr(exc, 'strerror', None) or exc}), "
            "so nothing was locked; fix the cause, then retry."
        ) from exc


def discard_locked_copies(root, record):
    """Delete the unit's saved copies of locked tests, refusing a unit found living there
    and any deletion that fails, so the caller can retry. A copy of them is set aside first
    and kept until the caller has saved the state that no longer needs them, so recover-close
    can put them back after an interruption; drop_discarded_copies then deletes it."""
    reconcile_locked_copies(root, record)
    live = unclaimed_record_folder(root, record["unit"], LOCKED_FOLDER)
    if not live.is_dir():
        return
    previous = _previous_copies(root, record)
    declared = evidence.scope(root, record["unit"])
    try:
        # Each locked test's copy is copied by itself, so the set-aside copy is always
        # deletable, and checked against the locks before anything live is deleted.
        for path in record["locks"]:
            source = copy_path(live, path)
            if not _gone_empty(declared, path, source, record["locks"][path]):
                copy = copy_path(previous, path)
                copy.parent.mkdir(parents=True, exist_ok=True)
                copy.write_bytes(source.read_bytes())
                shutil.copymode(source, copy)
    except OSError as exc:
        shutil.rmtree(previous, ignore_errors=True)
        raise WorkflowError(
            f"Firebreak could not set aside the copies of the locked tests ({exc.strerror or exc}); "
            "fix the cause, then retry."
        ) from exc
    if not _copies_match(declared, previous, record["locks"]):
        shutil.rmtree(previous, ignore_errors=True)
        raise WorkflowError(
            f"The saved copies of the locked tests in {live.relative_to(Path(root).resolve()).as_posix()} do not "
            "all match their locks, so Firebreak cannot set them aside before deleting them. Give each the "
            "content its lock in the unit's state records, such as from git, then retry."
        )
    # A deletion that fails partway may have removed some copies, so the set-aside copy
    # stays for recover-close or the retry to put back.
    remove_folder(root, live)


def drop_discarded_copies(root, record):
    """Delete the copies discard_locked_copies set aside, once the caller's state is saved.
    That state is already saved, so a failed deletion comes back as a note instead of a
    refusal; the next copy save or recover-close settles them, refusing until it can."""
    try:
        remove_folder(root, _previous_copies(root, record))
    except WorkflowError as exc:
        return {"cleanup_failed": (
            f"The change was saved, but the set-aside copies of the locked tests were not deleted: {exc} "
            "They change nothing while they stay; the next copy save or recover-close settles them.")}
    return {}


def _content(path):
    """A file's bytes, or None when it is missing or cannot be read."""
    try:
        return path.read_bytes() if path.is_file() else None
    except OSError:
        return None


def _matches_lock(declared, path, data, lock):
    """Whether a file's bytes match its lock: a whole test file's, or a region's alone."""
    return data is not None and evidence.test_fingerprint(declared, path, data) == lock


def _gone_empty(declared, path, target, lock):
    """Whether a region-bearing file whose locked region is empty does not exist; it holds
    no test, as a file that never existed holds none."""
    return (not target.exists() and not target.is_symlink() and lock == evidence.EMPTY_REGION
            and evidence.region_start(declared, path) is not None)


def _holds(declared, path, target, lock):
    """Whether the file at target matches a lock; an unreadable file never does."""
    return _gone_empty(declared, path, target, lock) or _matches_lock(declared, path, _content(target), lock)


def _locked_copy(root, record, declared, path):
    """The saved copy of a locked test, or None when it is missing or no longer the locked content."""
    data = _content(copy_path(unit_dir(root, record["unit"]) / LOCKED_FOLDER, path))
    return data if _matches_lock(declared, path, data, record["locks"][path]) else None


def violated_locks(root, record):
    """Locked tests that no longer match their locks, missing ones included, except those
    with an approved unlock outstanding. A new test file is not a violation, nor is a change
    above a region."""
    declared = evidence.scope(root, record["unit"])
    return sorted(path for path, lock in record["locks"].items()
                  if path not in record["unlocks"]
                  and not _holds(declared, path, confined(root, path), lock))


def check_locked_tests(root, record, session, task_id, boundary, failure=None):
    """Refuse a task start or finish while a locked test differs from its lock. The refusal
    is recorded as a lock violation naming the task and every task running now, with the
    diff of each changed file against its saved copy; a refused finish leaves the task running.
    A failure that interrupted the task's checks is kept at the head of the message. In the
    no-tests outcome, any scoped test refuses the start or finish instead."""
    check_empty_inventory(root, record, f"Task {task_id} cannot {boundary}", failure)
    violated = violated_locks(root, record)
    if not violated:
        return
    running = sorted({task for task, run in record.get("task_runs", {}).items()
                      if run.get("status") == "running"} | {task_id})
    declared = evidence.scope(root, record["unit"])
    diffs = {}
    for path in violated:
        copy = _locked_copy(root, record, declared, path)
        diffs[path] = (bytes_diff(copy, _content(confined(root, path)), f"locked/{path}", path) if copy is not None
                       else "No saved copy matches this test's lock, so no diff can be shown.")
    event(record, "lock-violation", session, task=task_id, boundary=boundary, files=violated,
          running=running, diffs=diffs)
    save(root, record)
    unit = record["unit"]
    raise WorkflowError(
        (f"{failure} " if failure else "")
        + f"Locked tests changed outside an approved unlock: {', '.join(violated)}. Task {task_id} cannot "
        f"{boundary} until they match their locks; this was recorded as a lock violation naming the tasks "
        f"running now ({', '.join(running)}). Restore them with restore-locked-tests {unit} --tests "
        f"{' '.join(violated)}, or, if a locked test is wrong, ask the operator for an unlock-test approval "
        "and rework it through its test task. Changes against the saved copies:\n"
        + "\n".join(diffs[path] for path in violated)
    )


def restore_locked_tests(root, record, session, paths):
    """Replace each named locked test whose lock is violated with its saved copy, recreating
    a deleted one. A test region is replaced with the copy's region while the current code
    above it is kept byte for byte, and appended when the start line is gone. A test with an
    approved unlock outstanding is reworked through its test task instead, and a file whose
    lock holds is left alone. The caller saves the record."""
    from .engine import ownership

    ownership(record, session)
    unit = record["unit"]
    declared = evidence.scope(root, unit)
    if not paths:
        raise WorkflowError(f"Name the locked tests to restore: restore-locked-tests {unit} --tests <path>...")
    violated = violated_locks(root, record)
    copies = {}
    for path in dict.fromkeys(paths):
        if path not in record["locks"]:
            raise WorkflowError(
                f"{path} is not a locked test; restore-locked-tests restores only locked tests from their saved copies."
            )
        if path in record["unlocks"]:
            raise WorkflowError(
                f"{path} has an approved unlock outstanding; rework it through its test task, and the test "
                "checkpoint locks the corrected test."
            )
        if path not in violated:
            raise WorkflowError(f"{path} still matches its lock; there is nothing to restore.")
        copies[path] = _locked_copy(root, record, declared, path)
        if copies[path] is None:
            raise WorkflowError(
                f"The saved copy of {path} is missing or no longer matches its lock, so Firebreak cannot restore it. "
                "Restore the locked content another way, such as from git, so the file matches the fingerprint "
                "in the unit's locks."
            )
        start = evidence.region_start(declared, path)
        if start is not None:
            # The code above is kept, so a file that exists but cannot be read is refused.
            current = confined(root, path)
            try:
                code = evidence.split_region(current.read_bytes() if current.exists() else b"", start)[0]
            except OSError as exc:
                raise WorkflowError(
                    f"{path} cannot be read ({exc.strerror}), so Firebreak cannot keep the code above its test "
                    "region; make it readable, then restore again."
                ) from exc
            copies[path] = code + evidence.split_region(copies[path], start)[1]
            if not _matches_lock(declared, path, copies[path], record["locks"][path]):
                raise WorkflowError(
                    f"Restoring the test region of {path} after its current code would not reproduce the locked "
                    "region, because the code above it now holds a line that starts a region, or does not end "
                    "its last line. Correct the code above the region, then restore again."
                )
    for path, data in copies.items():
        target = confined(root, path)
        linked = target.is_symlink()
        target.parent.mkdir(parents=True, exist_ok=True)
        if linked:
            # A link whose target's folder was deleted is written through once that folder exists again.
            resolved = target.resolve()
            confined(root, os.path.relpath(resolved, Path(root).resolve())).parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        if not linked and evidence.region_start(declared, path) is None:
            # Through a project symlink the target keeps its own permissions; the copy is flattened.
            # A region-bearing file keeps its own mode, which belongs to the code above.
            copy = copy_path(unit_dir(root, unit) / LOCKED_FOLDER, path)
            target.chmod(0o755 if file_mode(copy) == "100755" else 0o644)
    event(record, "locked-tests-restored", session, files=sorted(copies))
    return {"restored": sorted(copies), "next": "Locked tests match their locks again; start or finish tasks as before."}


def _read(path, what):
    try:
        return path.read_bytes() if path.is_file() else None
    except OSError as exc:
        raise WorkflowError(f"{what} cannot be read ({exc.strerror}); make it readable, then run test-checkpoint again.") from exc


def _code_fingerprint(declared, path, data):
    """The fingerprint of a region-bearing file's code above its region."""
    return hashlib.sha256(evidence.split_region(data, evidence.region_start(declared, path))[0]).hexdigest()


def _baseline_copy(root, record, path, recorded=None):
    """The saved baseline copy of a recorded file, refused when missing or no longer the
    recorded bytes."""
    unit = record["unit"]
    recorded = recorded or record["writing_tests_baseline"]["files"][path]
    copy = copy_path(unit_dir(root, unit) / BASELINE_FOLDER, path)
    shown = copy.relative_to(Path(root).resolve()).as_posix()
    data = _read(copy, f"The writing-tests baseline copy of {path} ({shown})")
    if data is None or hashlib.sha256(data).hexdigest() != recorded:
        # A re-record interrupted before its record was saved leaves these copies set aside.
        kept = copy_path(_previous_baseline(root, record), path)
        if _matches_hash(kept, recorded):
            data = kept.read_bytes()
    if data is None or hashlib.sha256(data).hexdigest() != recorded:
        raise WorkflowError(
            f"Unit {unit}: the writing-tests baseline copy of {path} is missing or no longer matches "
            f"its recorded fingerprint, so the checkpoint cannot compare against it. Restore "
            f"{shown} to the content its fingerprint in the unit's state records, then run "
            "test-checkpoint again."
        )
    return data


def _baseline_diff(root, record, declared, path, returned=NO_RETURN, returned_mode=None, old_link=None):
    """A unified diff of one production file against its baseline copy, or against the
    content a verified implementation return recorded when given (None for a file it
    deleted), that shows every byte change and any mode change, against the returned mode
    when one is given, and any change of a symbolic link's target from old_link, and the
    fingerprint of the current bytes it was made from. A region-bearing file's diff covers
    the code above its region only."""
    baseline = record["writing_tests_baseline"]
    recorded = baseline["files"].get(path)
    old_mode = returned_mode or baseline.get("modes", {}).get(path)
    if returned is not NO_RETURN:
        recorded, before = (None, b"") if returned is None else (True, returned)
    else:
        before = _baseline_copy(root, record, path) if recorded is not None else b""
    after = _read(confined(root, path), f"The production file {path}")
    whole = after
    start = evidence.region_start(declared, path)
    if start is not None:
        before = evidence.split_region(before, start)[0]
        after = after if after is None else evidence.split_region(after, start)[0]
    new_mode = file_mode(confined(root, path))
    mode = (f"old mode {old_mode}\nnew mode {new_mode}\n"
            if recorded is not None and after is not None and old_mode and old_mode != new_mode else "")
    new_link = evidence.symlink_targets(root, [path]).get(path)
    if old_link != new_link:
        mode += (f"old symlink -> {old_link}\n" if old_link else "") + (f"new symlink -> {new_link}\n" if new_link else "")
    diff = bytes_diff(before if recorded is not None else None, after,
                      f"{'baseline' if returned is NO_RETURN else 'returned'}/{path}", path)
    return (mode + diff).rstrip("\n"), hashlib.sha256(whole).hexdigest() if whole is not None else None


def bytes_diff(before, after, fromfile, tofile):
    """A unified diff of two file contents that shows every byte change; None stands for
    a file that does not exist."""
    # Text that is not plain UTF-8 is shown escaped, so no byte change disappears.
    escaped = not (_plain(before or b"") and _plain(after or b""))
    note = " (escaped: backslashes doubled, other bytes as \\xNN)" if escaped else ""
    return _unified(
        _diff_lines(before or b"", escaped),
        _diff_lines(after or b"", escaped),
        (fromfile if before is not None else "/dev/null") + note,
        (tofile if after is not None else "/dev/null") + note,
        # Creating or deleting even an empty file changes behavior, so it always shows.
        existence_changed=(before is None) != (after is None),
    )


def _plain(data):
    """Whether bytes read as UTF-8 text whose only control characters are tabs and newlines."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return not any((ord(char) < 32 and char not in "\t\n") or ord(char) == 127 for char in text)


def _diff_lines(data, escaped):
    """Lines split at newlines only, each as its text and whether a newline ends it, so a
    missing final newline is compared as a fact, never as text."""
    lines = []
    for line in re.findall(rb"[^\n]*\n|[^\n]+", data):
        ended = line.endswith(b"\n")
        body = line[:-1] if ended else line
        if escaped:
            text = body.replace(b"\\", b"\\\\").decode("utf-8", errors="backslashreplace")
            text = "".join(f"\\x{ord(char):02x}" if ord(char) < 32 and char != "\t" or ord(char) == 127 else char
                           for char in text)
        else:
            text = body.decode("utf-8")
        lines.append((text, ended))
    return lines


def _unified(before, after, fromfile, tofile, *, existence_changed=False):
    """A unified diff of (text, ended) lines; a line without a final newline is followed by
    the conventional marker line, which cannot be mistaken for file text."""
    def span(start, stop):
        length = stop - start
        return f"{start + 1}" if length == 1 else f"{start if length == 0 else start + 1},{length}"

    output = [f"--- {fromfile}", f"+++ {tofile}"]
    for group in difflib.SequenceMatcher(None, before, after, autojunk=False).get_grouped_opcodes(3):
        output.append(f"@@ -{span(group[0][1], group[-1][2])} +{span(group[0][3], group[-1][4])} @@")
        for tag, a1, a2, b1, b2 in group:
            rows = ([(" ", line) for line in before[a1:a2]] if tag == "equal"
                    else [("-", line) for line in before[a1:a2]] + [("+", line) for line in after[b1:b2]])
            for sign, (text, ended) in rows:
                output.append(sign + text)
                if not ended:
                    output.append("\\ No newline at end of file")
    return "\n".join(output) if len(output) > 2 or existence_changed else ""


def path_kind(root, path, kinds):
    """A listed path's kind: its actual kind on disk, else the kind the spec declares.
    A kind is never inferred from a path's name; an undeclared missing path has none."""
    target = confined(root, path)
    if target.exists():
        return "directory" if target.is_dir() else "file"
    return kinds.get(evidence.canonical(path))


def holds_tests(root, owned, tests, kinds):
    """Owned paths that are or can contain a scoped test. A file is checked as a
    file, so pkg/foo.go beside pkg/**/*_test.go is not a test; a directory or
    wildcard is checked for overlap with the test patterns, including files that
    do not exist yet."""
    held = []
    for path in owned:
        if any(c in path for c in "*?["):
            pattern = path
        elif path_kind(root, path, kinds) == "file":
            if evidence.matches(path, tests):
                held.append(path)
            continue
        else:
            pattern = f"{path.rstrip('/')}/**"
        if any(evidence.patterns_overlap(pattern, test) for test in tests):
            held.append(path)
    return held


def check_listed_paths(root, task, declared, kinds):
    """Judge a task's listed paths against the current tree and the spec's declarations.
    Plan validation and every task start run it, since an accepted plan does not bind
    what kind of thing each path is on disk. Owned, consumed, and input-reference paths
    must exist or be declared; an implementation task must not own a scoped test."""
    from .task_graph import check_input_shapes, consumed_patterns

    check_input_shapes(task)
    for path in dict.fromkeys([*task["files"], *consumed_patterns(task)]):
        if not any(c in path for c in "*?[") and path_kind(root, path, kinds) is None:
            raise WorkflowError(
                f"Task {task['id']} lists {path}, which does not exist and the spec does not declare in scope.json creates; "
                "correct the path, or reopen spec to declare it."
            )
    held = holds_tests(root, task["files"], declared["tests"], kinds) if task.get("stage") == "implementation" else []
    if held:
        raise WorkflowError(
            f"Implementation task {task['id']} owns paths that can hold scoped tests: {', '.join(held)}. "
            "Give test files to test tasks, and list the implementation task's production files or folders without them."
        )


def plan(root, record):
    """Validate the breakdown's tasks as a plan: stage, listed paths, references,
    verification, ownership, check expectations, requirement links and coverage, ordering,
    the task graph, and each task's context size. Returns
    the tasks; breakdown close runs it, and nothing in it runs a test. A plan may have no
    test task only when every requirement is review-only, which the coverage check ensures."""
    from .handoff import _references

    evidence.structural(root, record, "breakdown")
    tasks = read_json(unit_dir(root, record["unit"]) / "tasks.json")
    declared = evidence.scope(root, record["unit"])
    base = unit_dir(root, record["unit"]).relative_to(root).as_posix()
    kinds = evidence.declared_kinds(declared)
    specs = traceability.requirement_specs(root, record)
    for task in tasks:
        stage = task.get("stage")
        if stage not in {"tests", "implementation"}:
            raise WorkflowError("Each task needs stage tests or implementation.")
        if "refactor" in task and (task["refactor"] is not True or stage != "implementation"):
            raise WorkflowError(
                f"Task {task['id']} sets refactor, which only an implementation task may set, and only to true."
            )
        if "stubs" in task:
            raise WorkflowError(
                f"Task {task['id']} declares stubs, which are no longer used: list every production file the task "
                "creates or changes in its files, and declare each new path in the spec's scope.json creates."
            )
        check_listed_paths(root, task, declared, kinds)
        try:
            refs = _references(root, task.get("acceptance_refs"), "acceptance_refs", specs)
        except WorkflowError as exc:
            raise WorkflowError(f"Task {task['id']}: {exc}") from exc
        if not {f"{base}/prd.md", f"{base}/spec.md"} <= set(refs):
            raise WorkflowError(
                f"Task {task['id']} must reference applicable intent and specification in acceptance_refs."
            )
        if (
            not isinstance(task.get("verification"), str)
            or not task["verification"].strip()
        ):
            raise WorkflowError(
                "Each task needs verification describing observable checks and plausible bugs they detect."
            )
        if stage == "tests" and any(
            not evidence.matches(p, declared["tests"] + declared["sources"])
            for p in task["files"]
        ):
            raise WorkflowError(
                f"Test task {task['id']} owns files outside the declared tests and sources; "
                "list only the tests it writes and the production files its interface changes touch."
            )
        expectations = task.get("check_expectations", [])
        if (
            not isinstance(expectations, list)
            or not expectations
            or any(
                not isinstance(c, dict)
                or not isinstance(c.get("argv"), list)
                or not c["argv"]
                or any(not isinstance(a, str) or not a.strip() for a in c["argv"])
                or (
                    c.get("exit_code") != "nonzero" and type(c.get("exit_code")) is not int
                    if stage == "tests"
                    else type(c.get("exit_code")) is not int or c["exit_code"] != 0
                )
                for c in expectations
            )
            or len({tuple(c["argv"]) for c in expectations}) != len(expectations)
        ):
            raise WorkflowError(
                "Check expectations require unique nonempty command arrays for every task; implementation checks must pass (exit 0), "
                'and a test task declares an exact exit code or "nonzero" for a check expected to fail with any non-zero exit.'
            )
    traceability.task_coverage(root, record, tasks)
    refactor_coverage(tasks)
    by_id = {t["id"]: t for t in tasks}
    if any(
        t["stage"] == "tests"
        and any(by_id[d]["stage"] != "tests" for d in t.get("depends_on", []))
        for t in tasks
    ):
        raise WorkflowError("Test tasks cannot depend on implementation tasks.")
    from .task_graph import validate

    validate(root, tasks)
    from .handoff import planned_oversize

    # Each task's context is checked against both limits now, so an oversized task is split
    # before any review round rather than refused at launch.
    oversized = planned_oversize(root, record, tasks)
    if oversized:
        raise WorkflowError(oversized)
    return tasks


def refactor_coverage(tasks):
    """Every production path an implementation task owns is also owned by a refactor task
    that depends on it, directly or through other tasks, so each wave's code is refactored.
    A refactor task covers a path it lists, or a path inside a folder it lists. Every
    problem is named at once."""
    from .task_graph import follows

    refactors = [t for t in tasks if t.get("refactor")]
    problems = [
        f"- Task {task['id']}: {entry}"
        for task in tasks
        if task["stage"] == "implementation" and not task.get("refactor")
        for entry in task["files"]
        if not any(
            follows(tasks, r["id"], task["id"])
            and (entry in r["files"] or evidence.matches(entry, [f for f in r["files"] if not any(c in f for c in "*?[")]))
            for r in refactors
        )
    ]
    if problems:
        raise WorkflowError(
            "Every production path an implementation task owns needs a refactor task that depends on that "
            "task and owns the path or a folder holding it (an implementation task with \"refactor\": true). "
            "Plan one refactor task after each wave of implementation tasks. Uncovered:\n" + "\n".join(problems)
        )


def expected_outcomes(tasks, commands):
    """Each command's expected exit codes, one per test task that names it; a command a
    test task expects an outcome from is added to the commands run. Every expectation is
    kept, so a shared command must meet each one."""
    expected = {}
    for task in tasks:
        if task["stage"] != "tests":
            continue
        for item in task.get("check_expectations", []):
            expected.setdefault(tuple(item["argv"]), []).append(item["exit_code"])
            if item["argv"] not in commands:
                commands.append(item["argv"])
    for codes in expected.values():
        exact = {code for code in codes if code != "nonzero"}
        if len(exact) > 1 or 0 in exact and "nonzero" in codes:
            raise WorkflowError("Test tasks disagree on the expected outcome of a shared check; "
                                "no exit code can meet all of them, so correct the tasks' check_expectations.")
    return expected


def unmet(results, expected):
    """Whether any result misses an exit code a test task expects of its command."""
    return any(
        not evidence.exit_matches(code, result["exit_code"])
        for result in results
        for code in expected.get(tuple(result["argv"]), [])
    )


def checkpoint_commands(root, record):
    """The commands the test checkpoint runs, their expected exits, and whether it demands
    red. Every run executes the declared whole-unit checks and each test task's commands,
    and saves their output. The first checkpoint holds the test tasks' commands to their
    declared exits and demands red. After an earlier acceptance Firebreak cannot know which
    tests a check covers, so it holds no declared exit and leaves red to the reviewer, who
    reads fresh and carried-forward output; a test task owning an outstanding unlocked test
    runs the approved rework commands instead, held to their derived exits."""
    from .engine import accepted_checkpoint, rework_commands

    commands = [list(argv) for argv in evidence.scope(root, record["unit"])["checks"]]
    tasks = read_json(unit_dir(root, record["unit"]) / "tasks.json")
    if accepted_checkpoint(record) is None:
        return commands, expected_outcomes(tasks, commands), True
    expected = {}
    for task in tasks:
        if task["stage"] != "tests":
            continue
        rework = rework_commands(record, task["files"])
        for item in rework if rework is not None else task.get("check_expectations", []):
            if rework is not None:
                expected.setdefault(tuple(item["argv"]), []).append(item["exit_code"])
            if item["argv"] not in commands:
                commands.append(item["argv"])
    return commands, expected, False


def red_evidence(checks, expected, declared, demand_red=True, preservation=False):
    """The checkpoint's red evidence: every check meets its expected exits, and, when red is
    demanded, a check fails unless every test task expects its checks to pass
    (preservation), in which case every declared check must pass instead. A preservation
    checkpoint, for a plan with no test task, needs every check to pass. A check that did
    not finish is never evidence."""
    unfinished = [check for check in checks if check.get("exit_code") is None]
    if unfinished:
        raise WorkflowError(
            "Some checks did not finish: " + "; ".join(check.get("error", " ".join(check["argv"])) for check in unfinished)
            + " Make them finish within check_timeout, then run test-checkpoint again."
        )
    if preservation:
        failed = [check for check in checks if check["exit_code"]]
        if failed:
            raise WorkflowError(
                "A preservation checkpoint needs every scoped test to pass: the unit's requirements are all "
                "review-only and it has no test tasks, so the checkpoint locks the existing tests as they "
                "are. These checks failed: "
                + "; ".join(f"{' '.join(check['argv'])} (exit {check['exit_code']})" for check in failed)
                + ". Read their saved output and fix the cause, or reopen breakdown to plan test tasks for "
                "the behavior they check."
            )
        return {"red_check": None, "preservation_reason": (
            "A preservation checkpoint: every requirement is review-only, the plan has no test task, and "
            "every declared check passes.")}
    if unmet(checks, expected):
        raise WorkflowError(
            "The checkpoint's checks did not meet their expected outcomes (the test tasks' declared ones, "
            "or an unlock's approved rework commands); read each check's output, rework the tests through "
            "their test tasks, and run test-checkpoint again."
        )
    if not demand_red:
        red = next((check for check in checks if evidence.is_red(check)), None)
        return {"red_check": red, "preservation_reason": None if red else (
            "A checkpoint after an earlier acceptance: the reviewer judged red from fresh and carried-forward output.")}
    if expected and all(code == 0 for codes in expected.values() for code in codes):
        if any(check["exit_code"] for check in checks if check["argv"] in declared):
            raise WorkflowError("Preservation requires the declared regression checks to pass.")
        return {"red_check": None,
                "preservation_reason": "Every test task expects its checks to pass, and every declared check passes."}
    red = next((check for check in checks if evidence.is_red(check)), None)
    if red is None:
        raise WorkflowError(
            "No check failed, but the test tasks expect red. A test for behavior not yet built must fail "
            "on an assertion about it; rework the tests through their test tasks, or declare exit 0 "
            "for a test that preserves behavior already built."
        )
    return {"red_check": red, "preservation_reason": None}


def progress(root, record):
    """Implement's stage as a compact handoff; tests and check output remain on disk."""
    from .engine import implement_stage, test_outcome

    result = {
        "evidence": f".fbk/{record['unit']}/state.json#/phases/test-checkpoint",
        "locked_test_count": len(record["locks"]),
    }
    try:
        stage = implement_stage(root, record)
    except WorkflowError as exc:
        return {**result, "stage": "unknown", "next": str(exc)}
    outcome = test_outcome(root, record)
    if outcome == "no-tests":
        return {**result, "stage": stage, "next": (
            "The unit has no scoped tests and no test tasks, so no test checkpoint applies and it is writing "
            "code; read implementation assignments before production work. A scoped test that appears is "
            "refused at every task boundary and at implementation close.")}
    if outcome == "preservation" and stage == "ready-for-checkpoint":
        return {**result, "stage": stage, "next": (
            f"Run test-checkpoint {record['unit']}: a preservation checkpoint, since every requirement is "
            "review-only and the plan has no test tasks. Every scoped test must pass; the reviewer judges "
            "whether they protect the code the unit will change, and they lock on pass.")}
    return {**result, "stage": stage, "next": {
        "writing-tests": "Run the test tasks; each needs a completed, current run before the test checkpoint.",
        "ready-for-checkpoint": f"Run test-checkpoint {record['unit']} to review and lock the tests.",
        "writing-code": "Read implementation assignments and locked tests before production work.",
    }[stage]}
