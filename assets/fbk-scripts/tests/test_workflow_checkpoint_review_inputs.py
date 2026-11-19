"""What the test checkpoint's reviewer sees: the writing-tests baseline, the comparison
of the current tree with it, the complete saved check output, and the reviewer's
obligations (build step 3b).

The tests find Firebreak's two new folders by what they hold, so the folder names stay
the implementer's choice. They assume these shapes:

- **Baseline.** On the first entry into implement, Firebreak saves a copy of every scoped
  test file and every production file in scope in one folder directly inside the unit's
  folder, each at its own relative path (``.fbk/<unit>/<baseline folder>/tests/check.py``),
  and records each copy's sha256 fingerprint in the state record or in that folder.
- **Saved output.** The checkpoint writes each check's complete stdout and stderr as raw
  text files in one folder directly inside the unit's folder. Their sha256 fingerprints
  appear in the checkpoint's accepted evidence, and their paths are in the reviewer's
  required_files.
- **Comparison.** The reviewer's prompt payload carries an object with a key naming the
  changed tests (the key contains "changed") and a key naming the untouched tests (the key
  contains "untouched"), each a list of paths, a list of objects with a "path", or a
  mapping keyed by path.
- **Production diffs.** A unified diff of each declared production change against its
  baseline copy appears in the reviewer's prompt payload or snapshot.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from fbk.workflow import engine, handoff, hooks, review, review_context, store
from .test_workflow_commands import call
from .test_workflow_implement_stages import (
    CHECK,
    accept_breakdown_and_approve,
    denied,
    edit_scope,
    edit_tasks,
    stage,
    start,
)
from .test_workflow_lifecycle import (
    accept,
    blocking_review,
    clean_review,
    enter,
    enter_implementation,
    mutate,
    prepare_implementation,
    project as workflow_project,
)
from .test_workflow_test_checkpoint import (
    CK,
    checkpoint_refusal,
    code_done_after_checkpoint,
    make_checkpoint_rerunnable,
    counting,
    ready_for_checkpoint,
    required_reading,
    work,
)
from .test_workflow_test_preparation import write_permission
from .refactor_plan import complete_refactor_tasks

project = workflow_project

UNIT = ".fbk/feature"
UNIT_DOCUMENTS = {"state.json", "prd.md", "spec.md", "scope.json", "tasks.json"}

RED_TEST = (
    "from pathlib import Path\n"
    "assert Path('src/app.py').read_text() == 'release()', 'release is still missing'\n"
)
PASSING_TEST = "assert True\n"
# The record folders this step's tests do not cover (the saved copies of locked tests, from
# build step 5): every reserved record folder except the baseline, saved output, and kept
# accepted output, so those three stay found by what they hold.
OTHER_RECORD_FOLDERS = set(store.RECORD_FOLDERS) - {
    store.BASELINE_FOLDER, store.OUTPUT_FOLDER, store.ACCEPTED_OUTPUT_FOLDER}


# Helpers


def unit_files(root):
    base = root / UNIT
    return {path.relative_to(root).as_posix() for path in base.rglob("*") if path.is_file()}


def baseline_copy(root, relative):
    """The baseline's saved copy of a scoped file: a file inside the unit's folder whose
    path ends with the scoped file's own relative path. None when there is none."""
    base = root / UNIT
    depth = len(Path(relative).parts)
    hits = sorted(
        path for path in base.rglob("*")
        if path.is_file()
        and path.relative_to(base).parts[0] not in OTHER_RECORD_FOLDERS
        and len(path.relative_to(base).parts) > depth
        and path.relative_to(base).as_posix().endswith("/" + relative)
    )
    return hits[0] if hits else None


def baseline_folder(root):
    copy = baseline_copy(root, "tests/check.py")
    assert copy is not None, "No baseline copy of tests/check.py inside the unit's folder."
    return f"{UNIT}/{copy.relative_to(root / UNIT).parts[0]}"


def saved_output(root, before):
    """Files the checkpoint wrote inside the unit's folder, by path, with their bytes, apart
    from the record folders this step's tests do not cover."""
    new = sorted(path for path in unit_files(root) - before - {f"{UNIT}/state.json"}
                 if Path(path).relative_to(UNIT).parts[0] not in OTHER_RECORD_FOLDERS)
    return {path: (root / path).read_bytes() for path in new}


def output_folder(root, saved):
    assert saved, "The checkpoint saved no check output inside the unit's folder."
    folders = {Path(path).relative_to(UNIT).parts[0] for path in saved}
    assert len(folders) == 1, f"The saved output spreads over several folders: {sorted(folders)}"
    return f"{UNIT}/{folders.pop()}"


def native_capture(monkeypatch):
    """Replace only the native reader; record its prompt and every file in its snapshot."""
    seen = []

    def reader(snapshot, prompt, config, **kwargs):
        snapshot = Path(snapshot)
        files = {path.relative_to(snapshot).as_posix(): path.read_bytes()
                 for path in snapshot.rglob("*") if path.is_file()}
        seen.append({"prompt": prompt, "files": files})
        return {"review": {"summary": "Inspected the authored tests.", "findings": []}}

    monkeypatch.setattr(review, "claude_review", reader)
    return seen


def payload(prompt):
    """The structured part of a reader prompt, decoded."""
    return json.loads(prompt[prompt.index("\n{") + 1:])


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def comparison(prompt):
    """The changed and untouched tests the reviewer was given."""
    found = []

    def walk(value):
        if isinstance(value, dict):
            if any("untouched" in key.lower() for key in value):
                found.append(value)
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(payload(prompt))
    assert found, "The reviewer's prompt carries no comparison of changed and untouched tests."

    def paths(value):
        if isinstance(value, dict):
            return set(value)
        if isinstance(value, list):
            return {item if isinstance(item, str) else item.get("path") for item in value}
        return set()

    item = found[0]
    changed = set().union(*[paths(v) for k, v in item.items()
                            if "changed" in k.lower() and "unchanged" not in k.lower()])
    untouched = set().union(*[paths(v) for k, v in item.items() if "untouched" in k.lower()])
    return changed, untouched


def saved_in_snapshot(capture):
    """Snapshot files inside the unit's folder that are not the unit's own documents:
    the saved check output the reviewer received."""
    return {
        path: data for path, data in capture["files"].items()
        if path.startswith(UNIT + "/")
        and Path(path).relative_to(UNIT).parts[0] not in UNIT_DOCUMENTS | {"decisions", "design"}
    }


def review_lines(capture):
    """Every line the reader received, in its prompt payload or its snapshot."""
    texts = list(strings(payload(capture["prompt"])))
    texts += [data.decode("utf-8", errors="replace") for data in capture["files"].values()]
    return {line for text in texts for line in text.splitlines()}


def finish_test_task(root, worker, writes, changed, argv=CHECK):
    """Launch the test task, write its files, and finish it through the real handoff."""
    assert start(root, "prepare-tests", worker) is None, "The test task should start in writing tests."
    for path, text in writes.items():
        (root / path).write_text(text)
    assert review.run_command(argv, root, 30)["exit_code"] != 0
    returned = mutate(root, handoff.finish_task, "s", "prepare-tests", changed_files=changed,
                      checks=[{"argv": argv, "exit_code": 1, "evidence": "Release is still missing."}],
                      unresolved=[], outcome="The tests fail on the missing release.")
    assert returned["status"] == "completed"


def git(root, *arguments):
    return subprocess.run(["git", "-C", str(root), *arguments], capture_output=True, text=True)


def commit_all(root):
    assert git(root, "init", "-q").returncode == 0
    git(root, "add", "-A")
    committed = git(root, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.com",
                    "commit", "-qm", "Fixture baseline")
    assert committed.returncode == 0, committed.stderr


def ignored(root, relative):
    return git(root, "check-ignore", "-q", "--", relative).returncode == 0


def sha256(data):
    return hashlib.sha256(data).hexdigest()


# The writing-tests baseline


def test_first_entry_into_implement_saves_every_scoped_file_with_fingerprints(project):
    (project / "src/extra.py").write_text("EXTRA = 'production content only the baseline fingerprints'\n")
    (project / "tests/existing_check.py").write_text(PASSING_TEST)
    accept_breakdown_and_approve(project)
    assert baseline_copy(project, "tests/check.py") is None, "A baseline was recorded before implement."
    enter(project, "implement")
    folder = baseline_folder(project)
    for relative in ("tests/check.py", "tests/existing_check.py", "src/app.py", "src/extra.py"):
        copy = project / folder / relative
        assert copy.is_file(), f"The baseline has no copy of {relative}."
        assert copy.read_bytes() == (project / relative).read_bytes()
    # Nothing else records this file's fingerprint, so finding it proves the baseline did.
    fingerprint = sha256((project / "src/extra.py").read_bytes())
    recorded = (project / UNIT / "state.json").read_text() + "".join(
        path.read_text(errors="replace") for path in (project / folder).rglob("*") if path.is_file())
    assert fingerprint in recorded, "The baseline recorded no fingerprint for src/extra.py."


@pytest.mark.parametrize("event", ["relaunch", "cancel-and-relaunch", "rejected-checkpoint",
                                   "suspend-and-resume"])
def test_a_test_changed_before_a_later_event_still_counts_as_changed(project, monkeypatch, event):
    (project / "tests/existing_check.py").write_text(PASSING_TEST)
    original = (project / "tests/check.py").read_bytes()
    enter_implementation(project)
    copy = baseline_copy(project, "tests/check.py")
    assert copy is not None, "Entering implement recorded no baseline."
    changed_test = RED_TEST.replace("is still missing", "was never released")
    if event == "cancel-and-relaunch":
        assert start(project, "prepare-tests", "test-author") is None
        (project / "tests/check.py").write_text(changed_test)
        mutate(project, handoff.cancel_task, "s", "prepare-tests", "The worker stopped before finishing.")
    else:
        finish_test_task(project, "test-author", {"tests/check.py": changed_test}, ["tests/check.py"])
    if event == "rejected-checkpoint":
        assert checkpoint_refusal(project, blocking_review) is not None
    if event == "suspend-and-resume":
        call(project, "suspend", "feature", "--reason", "Pausing between test tasks.")
        call(project, "phase-enter", "implement", "feature")
    else:
        # The relaunched task changes nothing; measured per run, the test looks untouched.
        finish_test_task(project, "second-author", {}, [])
    assert stage(project) == "ready-for-checkpoint"
    assert copy.read_bytes() == original, f"The baseline was re-recorded after the {event}."
    seen = native_capture(monkeypatch)
    assert checkpoint_refusal(project, reviewer=None) is None
    changed, untouched = comparison(seen[-1]["prompt"])
    assert "tests/check.py" in changed, f"A test changed before the {event} was not counted as changed."
    assert "tests/check.py" not in untouched
    assert "tests/existing_check.py" in untouched and "tests/existing_check.py" not in changed


# What the checkpoint compares


RUNNER = [sys.executable, "-c", (
    "import pathlib, runpy, sys\n"
    "failed = False\n"
    "for path in sorted(pathlib.Path('tests').glob('*.py')):\n"
    "    try:\n"
    "        runpy.run_path(str(path))\n"
    "        print('PASSED', path.as_posix())\n"
    "    except AssertionError as exc:\n"
    "        failed = True\n"
    "        print('FAILED', path.as_posix(), exc)\n"
    "sys.exit(1 if failed else 0)\n"
)]


def test_the_reviewer_gets_the_split_and_the_output_to_judge_each_test(project, monkeypatch):
    # A new test that already passes, an untouched test that fails, and an untouched test
    # that passes: the mechanical part of "a changed test that unexpectedly passes, or an
    # untouched test that fails, is not accepted". The reviewer judges; it needs both.
    edit_scope(project, checks=[RUNNER], creates=["tests/new_check.py"])
    edit_tasks(project, lambda by_id, tasks: by_id["prepare-tests"].update(
        files=["tests/check.py", "tests/new_check.py"],
        check_expectations=[{"argv": RUNNER, "exit_code": "nonzero"}]))
    (project / "tests/existing_check.py").write_text(PASSING_TEST)
    enter_implementation(project)
    finish_test_task(project, "test-author", {"tests/new_check.py": PASSING_TEST},
                     ["tests/new_check.py"], argv=RUNNER)
    assert stage(project) == "ready-for-checkpoint"
    seen = native_capture(monkeypatch)
    assert checkpoint_refusal(project, reviewer=None) is None
    changed, untouched = comparison(seen[-1]["prompt"])
    # A test absent from the baseline differs from it.
    assert changed == {"tests/new_check.py"}
    assert untouched == {"tests/check.py", "tests/existing_check.py"}
    output = "".join(data.decode("utf-8", errors="replace")
                     for data in saved_in_snapshot(seen[-1]).values())
    assert "PASSED tests/new_check.py" in output, "The saved output does not show the changed test passing."
    assert "FAILED tests/check.py" in output, "The saved output does not show the untouched test failing."


def test_an_undeclared_production_change_is_refused_before_review(project):
    ready_for_checkpoint(project)
    # src/app.py belongs to the implementation task, not to any test task; src/helper.py is new.
    (project / "src/app.py").write_text("def cancel(task):\n    pass\n")
    (project / "src/helper.py").write_text("def helper():\n    return None\n")
    assert review.run_command(CHECK, project, 10)["exit_code"] == 1
    assert stage(project) == "ready-for-checkpoint"
    reviewer, calls = counting(clean_review)
    message = checkpoint_refusal(project, reviewer)
    assert message is not None, "An undeclared production change reached the checkpoint review."
    assert "src/app.py" in message and "src/helper.py" in message
    assert calls == []
    assert work(project)["rounds"] == [] and work(project)["evidence"] is None
    assert not store.load(project, "feature")["locks"]


def test_built_code_is_inside_the_baseline_a_governing_change_rerecords(project):
    # A governing decision that makes the accepted checkpoint stale returns the unit to
    # writing tests, which re-records the baseline (step 4b ruling): code built before it
    # is inside the new baseline, not a change the re-run checkpoint must explain.
    code_done_after_checkpoint(project)
    make_checkpoint_rerunnable(project)
    copy = baseline_copy(project, "src/app.py")
    assert copy is not None and copy.read_bytes() == (project / "src/app.py").read_bytes(), (
        "The governing change did not re-record the baseline over the built code.")
    message = checkpoint_refusal(project)
    assert message is None, message
    record = store.load(project, "feature")
    assert record["phases"][CK]["evidence"]
    assert record["locks"] and record.get("lock_origin") == CK


BEFORE_TESTS = "def cancel():\n    return None  # modified-before-tests\n"
PLACEHOLDER = "def cancel(task):\n    return None  # placeholder-for-new-signature\n"


def test_the_reviewer_sees_declared_production_changes_as_diffs_against_the_baseline(project, monkeypatch):
    commit_all(project)  # The repository's last commit holds the original src/app.py.
    edit_tasks(project, lambda by_id, tasks: by_id["prepare-tests"].update(
        files=["tests/check.py", "src/app.py"]))
    for phase in ("intent", "spec", "breakdown"):
        accept(project, phase)
    # The source was already modified before writing tests began.
    (project / "src/app.py").write_text(BEFORE_TESTS)
    mutate(project, engine.approve, "s", "start-implementation", "implement", "Implement the agreed spec.")
    enter(project, "implement")
    finish_test_task(project, "test-author", {"src/app.py": PLACEHOLDER}, ["src/app.py"])
    assert stage(project) == "ready-for-checkpoint"
    seen = native_capture(monkeypatch)
    assert checkpoint_refusal(project, reviewer=None) is None
    lines = review_lines(seen[-1])
    assert any(line.startswith("-") and "modified-before-tests" in line for line in lines), (
        "The reviewer saw no diff line removing the baseline's content.")
    assert any(line.startswith("+") and "placeholder-for-new-signature" in line for line in lines), (
        "The reviewer saw no diff line adding the test task's change.")
    assert "-pass" not in lines, "The diff compares with the last commit, not the baseline copy."


# Full saved output


def large_output_check():
    script = (
        "import sys\n"
        "sys.stdout.write('DECISIVE: test_release_once failed: AssertionError: the resource is still held\\n')\n"
        "sys.stdout.write('filler stdout line\\n' * 70000)\n"
        "sys.stdout.write('END OF STDOUT\\n')\n"
        "sys.stderr.write('DECISIVE STDERR: collected 2 items, 1 failed\\n')\n"
        "sys.stderr.write('filler stderr line\\n' * 70000)\n"
        "sys.stderr.write('END OF STDERR\\n')\n"
        "raise SystemExit(1)\n"
    )
    return [sys.executable, "-c", script]


def test_the_reviewer_snapshot_holds_the_complete_saved_output(project, monkeypatch):
    big = large_output_check()
    edit_scope(project, checks=[CHECK, big])
    expected = subprocess.run(big, capture_output=True, timeout=60)
    stdout, stderr = expected.stdout.decode(), expected.stderr.decode()
    # The fixture exceeds both old limits, with its decisive evidence at the start.
    for text in (stdout, stderr):
        assert len(text.encode()) > 1024 * 1024 + 12000
        assert text.startswith("DECISIVE")
    ready_for_checkpoint(project)
    before = unit_files(project)
    seen = native_capture(monkeypatch)
    assert checkpoint_refusal(project, reviewer=None) is None
    received = {path: data.decode("utf-8", errors="replace")
                for path, data in saved_in_snapshot(seen[-1]).items()}
    holding = {name: [path for path, text in received.items() if full in text]
               for name, full in (("stdout", stdout), ("stderr", stderr))}
    for name, paths in holding.items():
        assert paths, f"The reviewer's snapshot does not hold the complete {name}."
        assert received[paths[0]].find("DECISIVE") < 1000
        assert paths[0] in required_reading(seen[-1]["prompt"]), (
            f"The saved {name} is not required reading for the reviewer.")
    # The saved files stay in the unit's folder, fingerprinted in the checkpoint evidence.
    saved = saved_output(project, before)
    accepted = json.dumps(work(project)["evidence"])
    for name, paths in holding.items():
        assert paths[0] in saved, f"The saved {name} is not kept inside the unit's folder."
        assert sha256(saved[paths[0]]) in accepted, f"The saved {name}'s fingerprint is not in the evidence."


def test_the_first_implement_review_compares_against_the_checkpoint_snapshot_and_its_output(
        project, monkeypatch):
    # Fails today: before implement's first acceptance, its review baseline is breakdown's
    # accepted snapshot, which holds no checkpoint output.
    from fbk.workflow import close, review_baseline

    ready_for_checkpoint(project)
    before = unit_files(project)
    seen = native_capture(monkeypatch)
    assert checkpoint_refusal(project, reviewer=None) is None
    # The saved check output, not the record folder's own ignore file.
    saved = {path: data for path, data in saved_output(project, before).items()
             if Path(path).name != ".gitignore"}
    assert any(b"release is still missing" in data or b"AssertionError" in data for data in saved.values())
    locked_test = (project / "tests/check.py").read_bytes()
    assert start(project, "cancel", "implementer") is None
    (project / "src/app.py").write_text("release()")
    returned = mutate(project, handoff.finish_task, "s", "cancel", changed_files=["src/app.py"],
                      checks=[{"argv": CHECK, "exit_code": 0, "evidence": "Release happens."}],
                      unresolved=[], outcome="Cancellation releases its resource.")
    assert returned["status"] == "completed"
    record = store.load(project, "feature")
    accepted, phase, _ = review_baseline.select(record, "implement")
    assert phase == CK, f"The implement review's baseline comes from {phase}, not the test checkpoint."
    assert accepted == record["phases"][CK]["evidence"]
    complete_refactor_tasks(project)
    seen.clear()
    close.close_phase(project, "feature", "implement", "s", reviewer=None)
    assert seen, "The native implement reader was not asked."
    prior = {path[len(review_baseline.PREFIX) + 1:]: data for path, data in seen[0]["files"].items()
             if path.startswith(review_baseline.PREFIX + "/")}
    assert prior.get("tests/check.py") == locked_test, "The baseline tree lacks the reviewed tests."
    for path, data in saved.items():
        assert prior.get(path) == data, f"The baseline tree lacks the checkpoint's saved output {path}."


def test_output_with_terminal_color_codes_passes_the_hygiene_scan(project):
    (project / "tests/check.py").write_text(
        "print('\\x1b[31mFAILED\\x1b[0m test_release_once')\n" + RED_TEST)
    ready_for_checkpoint(project)
    before = unit_files(project)
    message = checkpoint_refusal(project)
    assert message is None, message
    saved = saved_output(project, before)
    assert any(b"\x1b[31m" in data for data in saved.values()), (
        "The saved output does not keep the check's color codes.")


def test_saved_output_is_a_review_source_live_and_in_a_stored_snapshot(project, tmp_path_factory):
    ready_for_checkpoint(project)
    before = unit_files(project)
    assert checkpoint_refusal(project) is None
    saved = sorted(saved_output(project, before))
    output_folder(project, saved)
    # Live tree: the unit's folder holds its state record.
    assert set(saved) <= set(review_context.source_paths(project, saved))
    # Stored snapshot: the same paths in a copied tree with no state record.
    stored = tmp_path_factory.mktemp("stored-snapshot")
    for path in saved:
        (stored / path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(project / path, stored / path)
    assert set(saved) <= set(review_context.source_paths(stored, saved))
    # Guard (passes today): workflow records stay out of review.
    for root in (project, stored):
        with pytest.raises(store.WorkflowError):
            review_context.source_paths(root, [f"{UNIT}/state.json"])


# Git-ignored and refused to the write hook


def checkpointed_folders(root):
    ready_for_checkpoint(root)
    before = unit_files(root)
    assert checkpoint_refusal(root) is None
    saved = saved_output(root, before)
    return baseline_folder(root), output_folder(root, saved), sorted(saved)


def test_the_write_hook_refuses_both_folders(project):
    baseline, output, saved = checkpointed_folders(project)
    for path in (f"{baseline}/tests/check.py", f"{baseline}/new.txt", saved[0], f"{output}/new.txt"):
        assert denied(write_permission(project, path)), f"The write hook allowed {path}."
        assert denied(write_permission(project, path, "test-author")), f"A worker may write {path}."
    # Guard (passes today): the lead still writes the unit's own documents.
    assert write_permission(project, f"{UNIT}/decisions/note.md") == {}


def test_an_existing_project_gains_the_ignore_entries(project):
    (project / ".fbk/.gitignore").write_text("runtime/\nlocal-notes/\n")
    commit_all(project)
    baseline, output, saved = checkpointed_folders(project)
    for path in (f"{baseline}/tests/check.py", *saved):
        assert ignored(project, path), f"Git does not ignore {path}."
    lines = (project / ".fbk/.gitignore").read_text().splitlines()
    assert "runtime/" in lines and "local-notes/" in lines, "The existing ignore entries were lost."
    # Guard: the unit's own records stay tracked.
    for path in (f"{UNIT}/state.json", f"{UNIT}/spec.md"):
        assert not ignored(project, path)


def test_a_new_project_ignores_both_folders(project, tmp_path_factory):
    baseline, output, _ = checkpointed_folders(project)
    fresh = tmp_path_factory.mktemp("fresh-project")
    call(fresh, "workflow-init")
    assert git(fresh, "init", "-q").returncode == 0
    for folder in (baseline, output):
        assert ignored(fresh, f"{folder}/saved.txt"), f"A new project does not ignore {folder}."
    assert ignored(fresh, ".fbk/runtime/project.lock")


# The reviewer's obligations


def checkpoint_obligations():
    brief = review.focus_brief("feature", CK, ["tests/check.py", "src/app.py"])
    return " ".join([brief["decision"], *brief["acceptance_obligations"]]).lower()


OBLIGATIONS = {
    "read the saved output": [r"saved output"],
    "each changed test failed on an assertion about missing behavior": [
        r"changed test[^.]*assertion about missing behavio"],
    "each untouched scoped test passed": [r"untouched[^.]*pass"],
    # Guard (passes today): step 3a already names build and load failures.
    "a build or load failure is a blocker": [r"build or load"],
    "a skipped test is a blocker": [r"skipped[^.]*blocker|blocker[^.]*skipped"],
    "a test missing from the output is a blocker": [r"(missing|absent) from the (saved )?output"],
    "a declared production diff that adds behavior is a blocker": [r"diff", r"adds? (meaningful )?behavio"],
    "each named plausible bug in a test task's verification is caught": [
        r"verification", r"named", r"plausible bug"],
    "a wrong implementation is tried in a disposable workspace": [
        r"disposable workspace", r"investigation", r"wrong implementation"],
}


@pytest.mark.parametrize("point", sorted(OBLIGATIONS))
def test_checkpoint_obligations_name_each_point(point):
    text = checkpoint_obligations()
    for pattern in OBLIGATIONS[point]:
        assert re.search(pattern, text), f"The checkpoint obligations do not say: {point} ({pattern})"


# Review round 1 findings
#
# Each test follows a witness from the step 3b review, under the lead's rulings.


def write_decision_and_record(root, decision_id="release-once"):
    from .test_workflow_test_checkpoint import DECIDED, record_decision, write_decision_sources

    write_decision_sources(root)
    record_decision(root, decision_id, DECIDED)


def probe_check(root, name="probe-check-ran"):
    marker = root / name
    return marker, [sys.executable, "-c", f"open({str(marker)!r}, 'a').write('ran')"]


# Major 1: saved output cannot change between its fingerprint and the reviewer


FIRST_OUTPUT = "FIRST CHECK DECISIVE: the release assertion failed\n"


def test_a_later_check_overwriting_earlier_saved_output_never_reaches_the_reviewer(project, monkeypatch):
    first = [sys.executable, "-c",
             f"import sys; sys.stdout.write({FIRST_OUTPUT!r}); sys.stdout.write('first filler\\n' * 100); "
             "raise SystemExit(1)"]
    # The second check rewrites every file in the unit's folder that holds the first
    # check's output, changing only its opening lines.
    second = [sys.executable, "-c", (
        "import pathlib\n"
        f"marker = {FIRST_OUTPUT!r}\n"
        "for path in pathlib.Path('.fbk/feature').rglob('*'):\n"
        "    if path.is_file() and path.name != 'state.json':\n"
        "        text = path.read_text(errors='replace')\n"
        "        if text.startswith(marker):\n"
        "            path.write_text('TAMPERED: the release assertion passed\\n' + text[len(marker):])\n"
    )]
    edit_scope(project, checks=[CHECK, first, second])
    ready_for_checkpoint(project)
    seen = native_capture(monkeypatch)
    message = checkpoint_refusal(project, reviewer=None)
    received = b"".join(b for capture in seen for b in saved_in_snapshot(capture).values())
    assert b"TAMPERED" not in received, "The reviewer received saved output altered after its fingerprint."
    assert message is not None, "A checkpoint whose saved output no longer matches its fingerprints passed."
    assert seen == [], "A reader was launched on saved output that no longer matches its fingerprints."
    assert work(project)["evidence"] is None
    assert not store.load(project, "feature")["locks"]


# Major 2: the implementation exemption covers only verified, unchanged task changes


def code_done_with_owned_folder(root):
    """An accepted checkpoint; the implementation task owns all of src/ and completes a
    verified change to src/app.py and a new src/helper.py; src/untouched.py it never changes."""
    (root / "src/untouched.py").write_text("UNTOUCHED = 1\n")
    code_done_after_checkpoint(root, owned=["src"],
                               writes={"src/app.py": "release()", "src/helper.py": "HELPER = 1\n"})


def test_verified_implementation_changes_alone_pass_a_rerun_checkpoint(project):
    # Guard: a task owning a whole folder; its verified changes predate the governing
    # change, so the re-recorded baseline holds them.
    code_done_with_owned_folder(project)
    make_checkpoint_rerunnable(project)
    assert checkpoint_refusal(project) is None


@pytest.mark.parametrize("change", ["new-file", "untouched-owned-file", "post-completion-edit"])
def test_unverified_changes_in_implementation_owned_files_are_refused(project, change):
    # After the governing change re-records the baseline, no task is running, so any
    # change inside an implementation task's files is undeclared.
    code_done_with_owned_folder(project)
    make_checkpoint_rerunnable(project)
    path = {"new-file": "src/extra.py", "untouched-owned-file": "src/untouched.py",
            "post-completion-edit": "src/helper.py"}[change]
    (project / path).write_text("CHANGED_OUTSIDE_ANY_TASK = 2\n")
    assert review.run_command(CHECK, project, 10)["exit_code"] == 0
    reviewer, calls = counting(clean_review)
    message = checkpoint_refusal(project, reviewer)
    assert message is not None, f"A {change} inside an implementation task's files was exempted."
    assert path in message
    assert calls == [] and work(project)["evidence"] is None


# Major 3: production diffs show every byte change


@pytest.mark.parametrize("before, after", [
    (b'# -*- coding: latin-1 -*-\nVALUE = "\xe9"\n', b'# -*- coding: latin-1 -*-\nVALUE = "\xf6"\n'),
    (b'TEXT = """first\x0bsecond"""\n', b'TEXT = """first\nsecond"""\n'),
    # Round 2: literal text equal to a missing-newline annotation must not hide the change.
    (b"VALUE := old", b"VALUE := old  (no newline at end of file)\n"),
], ids=["latin-1-literal", "vertical-tab-to-newline", "no-newline-marker-collision"])
def test_a_byte_level_production_change_produces_a_visible_diff(project, monkeypatch, before, after):
    edit_tasks(project, lambda by_id, tasks: by_id["prepare-tests"].update(
        files=["tests/check.py", "src/app.py"]))
    (project / "src/app.py").write_bytes(before)
    enter_implementation(project)
    assert start(project, "prepare-tests", "test-author") is None
    (project / "src/app.py").write_bytes(after)
    assert review.run_command(CHECK, project, 10)["exit_code"] != 0
    returned = mutate(project, handoff.finish_task, "s", "prepare-tests", changed_files=["src/app.py"],
                      checks=[{"argv": CHECK, "exit_code": 1, "evidence": "Release is still missing."}],
                      unresolved=[], outcome="The placeholder changed.")
    assert returned["status"] == "completed"
    seen = native_capture(monkeypatch)
    assert checkpoint_refusal(project, reviewer=None) is None
    diff = production_diff(seen[-1], "src/app.py")
    removed = [line for line in diff.splitlines() if line.startswith("-") and not line.startswith("---")]
    added = [line for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")]
    assert removed and added and removed != added, f"The byte change produced no visible diff: {diff!r}"


def production_diff(capture, path):
    """The diff the reviewer received for one production file, from the prompt payload or,
    when the diffs moved to a snapshot file, from that file."""
    texts = []

    def walk(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if "diff" in key.lower() and isinstance(item, dict) and isinstance(item.get(path), str):
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
        # A diffs file may map each path to its diff at the top level.
        if isinstance(loaded, dict) and isinstance(loaded.get(path), str):
            texts.append(loaded[path])
        walk(loaded)
    assert texts, f"The reviewer received no diff for {path}."
    return texts[0]


# Major 4: a preflight refusal after an earlier acceptance withdraws it


def test_an_undeclared_change_refused_after_a_stale_acceptance_withdraws_it(project):
    ready_for_checkpoint(project)
    assert checkpoint_refusal(project) is None
    write_decision_and_record(project)
    assert stage(project) != "writing-code"
    (project / "src/helper.py").write_text("UNDECLARED = 1\n")
    message = checkpoint_refusal(project)
    assert message is not None and "src/helper.py" in message
    assert work(project)["evidence"] is None, "The refusal kept the obsolete checkpoint acceptance."
    assert stage(project) != "writing-code"


def test_a_damaged_baseline_refused_after_a_stale_acceptance_withdraws_it(project):
    edit_tasks(project, lambda by_id, tasks: by_id["prepare-tests"].update(
        files=["tests/check.py", "src/app.py"]))
    ready_for_checkpoint(project)
    assert checkpoint_refusal(project) is None
    write_decision_and_record(project)
    # The relaunched test task makes the declared production change.
    finish_test_task(project, "second-author", {"src/app.py": PLACEHOLDER}, ["src/app.py"])
    assert stage(project) == "ready-for-checkpoint"
    copy = baseline_copy(project, "src/app.py")
    assert copy is not None
    copy.write_text("damaged baseline copy\n")
    message = checkpoint_refusal(project)
    assert message is not None and "src/app.py" in message
    assert work(project)["evidence"] is None, "The refusal kept the obsolete checkpoint acceptance."


def test_refusing_a_current_checkpoint_over_an_undeclared_change_keeps_its_acceptance(project):
    # Guard (passes today): production code is outside the revision, so the acceptance is
    # still current and its refusal changes nothing.
    ready_for_checkpoint(project)
    assert checkpoint_refusal(project) is None
    accepted = work(project)["evidence"]
    (project / "src/helper.py").write_text("UNDECLARED = 1\n")
    assert checkpoint_refusal(project) is not None
    assert work(project)["evidence"] == accepted
    assert stage(project) == "writing-code"


# Major 5: a unit that entered implement before its baseline existed is refused


def drop_baseline(root):
    """A unit that entered implement under step 3a: no baseline in its record or folder."""
    folder = baseline_folder(root)
    shutil.rmtree(root / folder)
    with store.transaction(root):
        record = store.load(root, "feature")
        for key in [key for key in record if "baseline" in key]:
            del record[key]
        record["events"] = [e for e in record["events"] if "baseline" not in e["event"]]
        store.save(root, record)


def test_a_unit_entered_before_its_baseline_existed_is_refused_not_recorded_late(project):
    enter_implementation(project)
    drop_baseline(project)
    # The edits a late baseline would hide.
    (project / "tests/check.py").write_text(RED_TEST.replace("is still missing", "was never released"))
    (project / "src/helper.py").write_text("UNDECLARED = 1\n")
    resumed = None
    try:
        call(project, "phase-enter", "implement", "feature")
    except store.WorkflowError as exc:
        resumed = str(exc)
    assert baseline_copy(project, "tests/check.py") is None, "Resuming recorded the baseline late."
    if resumed is None:
        finish_test_task(project, "test-author", {}, [])
    reviewer, calls = counting(clean_review)
    message = resumed or checkpoint_refusal(project, reviewer)
    assert message is not None
    assert re.search(r"baseline", message, re.I) and re.search(r"cannot be recovered", message, re.I), message
    assert "phase-enter implement" not in message, "The refusal points to a resume that records a late baseline."
    assert calls == [] and work(project)["evidence"] is None


# Major 6: unit names equal to the record folders are refused


def record_folder_names(root):
    baseline, output, _ = checkpointed_folders(root)
    return [Path(baseline).name, Path(output).name]


def test_a_unit_named_like_a_record_folder_is_refused_at_creation(project, tmp_path_factory):
    names = record_folder_names(project)
    fresh = tmp_path_factory.mktemp("collision")
    call(fresh, "workflow-init")
    for name in names:
        for unit in (name, f"feature/{name}"):
            with pytest.raises(store.WorkflowError):
                with store.transaction(fresh):
                    from fbk.workflow import engine as workflow_engine

                    workflow_engine.initialize(fresh, unit, design=False)
            assert not (fresh / ".fbk" / unit / "state.json").exists()


def plant_unit(root, unit):
    """An existing unit record at a colliding path, as created before the reservation."""
    record = json.loads((root / UNIT / "state.json").read_text())
    record.update(unit=unit, parent=None, owner=None, open_phase=None, opened_at=None)
    target = root / ".fbk" / unit / "state.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(record))
    return target


def test_an_existing_top_level_unit_with_a_record_folder_name_is_refused(project):
    names = record_folder_names(project)
    for name in names:
        plant_unit(project, name)
        message = None
        try:
            call(project, "status")
        except store.WorkflowError as exc:
            message = str(exc)
        assert message is not None and name in message, f"A unit named {name} was silently skipped."
        shutil.rmtree(project / ".fbk" / name)


def test_an_existing_nested_colliding_unit_is_refused_before_its_folder_is_replaced(project):
    ready_for_checkpoint(project)
    before = unit_files(project)
    assert checkpoint_refusal(project, blocking_review) is not None
    output = Path(output_folder(project, saved_output(project, before))).name
    shutil.rmtree(project / UNIT / output)
    planted = plant_unit(project, f"feature/{output}")
    reviewer, calls = counting(clean_review)
    message = checkpoint_refusal(project, reviewer)
    assert planted.is_file(), "The checkpoint replaced a colliding unit's folder."
    assert message is not None and output in message
    assert calls == []


# Major 7: the second reader must read large production diffs


def test_a_second_reader_omitting_the_large_diff_file_is_not_accepted(project, monkeypatch, tmp_path_factory):
    edit_tasks(project, lambda by_id, tasks: by_id["prepare-tests"].update(
        files=["tests/check.py", "src/app.py"]))
    enter_implementation(project)
    # A placeholder change large enough that its diff moves out of the brief.
    large = "".join(f"def placeholder_{n}(task):\n    return None\n" for n in range(1500))
    assert len(large) > 40000
    finish_test_task(project, "test-author", {"src/app.py": large}, ["src/app.py"])
    outside = tmp_path_factory.mktemp("second-reader")
    capture = outside / "prompt.txt"
    script = outside / "second_reader.py"
    # The external reader declares every required path that exists in the repository,
    # leaving out anything Firebreak placed only in the reviewer's snapshot.
    script.write_text(
        "import json, os, re, sys\n"
        "prompt = sys.stdin.read()\n"
        f"open({str(capture)!r}, 'w').write(prompt)\n"
        "decoder = json.JSONDecoder()\n"
        "required = []\n"
        "for match in re.finditer(r'\"required_files\": ', prompt):\n"
        "    value, _ = decoder.raw_decode(prompt, match.end())\n"
        "    if isinstance(value, dict):\n"
        "        required = [path for paths in value.values() for path in paths]\n"
        "        break\n"
        f"declared = [p for p in required if os.path.exists(os.path.join({str(project)!r}, p))]\n"
        "print(json.dumps({'summary': 'Read the tests.', 'findings': [],\n"
        "    'context': {'status': 'complete', 'inspected_files': declared,\n"
        "                'supporting_files': [], 'missing_context': []}}))\n"
    )
    config = store.project_config(project)
    store.atomic_json(project / ".fbk/config.json", {**config, "second_reader": [sys.executable, str(script)]})

    def native_reader(root, prompt, config, **kwargs):
        if kwargs.get("schema") and "assessments" in json.dumps(kwargs["schema"]):
            return {"review": {"summary": "Nothing to verify.", "assessments": []}}
        return {"review": {"summary": "Inspected the authored tests.", "findings": []}}

    monkeypatch.setattr(review, "claude_review", native_reader)
    message = checkpoint_refusal(project, reviewer=None)
    assert capture.exists(), "The configured second reader was not asked."
    omitted = set(required_reading(capture.read_text())) - {
        p for p in required_reading(capture.read_text()) if (project / p).exists()}
    assert omitted, "The large diffs did not move to a snapshot file; the fixture proves nothing."
    assert message is not None, "A second reader that never read the large diff file was accepted."
    assert work(project)["evidence"] is None


# Minor 8: a damaged or missing baseline copy is refused before checks or review


@pytest.mark.parametrize("damage", ["corrupted", "removed"])
def test_a_damaged_baseline_copy_is_refused_before_checks_or_review(project, damage):
    marker, probe = probe_check(project)
    edit_scope(project, checks=[CHECK, probe])
    edit_tasks(project, lambda by_id, tasks: by_id["prepare-tests"].update(
        files=["tests/check.py", "src/app.py"]))
    enter_implementation(project)
    finish_test_task(project, "test-author", {"src/app.py": PLACEHOLDER}, ["src/app.py"])
    copy = baseline_copy(project, "src/app.py")
    assert copy is not None
    if damage == "corrupted":
        copy.write_text("def cancel():\n    return 'not the recorded baseline'\n")
    else:
        copy.unlink()
    marker.unlink(missing_ok=True)
    reviewer, calls = counting(clean_review)
    message = checkpoint_refusal(project, reviewer)
    assert message is not None, f"A {damage} baseline copy reached review."
    assert "src/app.py" in message
    assert not marker.exists(), "Checks ran against a damaged baseline."
    assert calls == [] and work(project)["rounds"] == []


# Minor 9: output is saved whole when a check times out


def test_a_timed_out_check_keeps_its_complete_output(project):
    stdout = "DECISIVE TIMEOUT STDOUT\n" + "timeout stdout filler\n" * 60000
    stderr = "DECISIVE TIMEOUT STDERR\n" + "timeout stderr filler\n" * 60000
    slow = [sys.executable, "-c", (
        "import sys, time\n"
        "sys.stdout.write('DECISIVE TIMEOUT STDOUT\\n' + 'timeout stdout filler\\n' * 60000)\n"
        "sys.stdout.flush()\n"
        "sys.stderr.write('DECISIVE TIMEOUT STDERR\\n' + 'timeout stderr filler\\n' * 60000)\n"
        "sys.stderr.flush()\n"
        "time.sleep(30)\n"
    )]
    marker, after = probe_check(project, "after-timeout-ran")
    edit_scope(project, checks=[CHECK, slow, after])
    ready_for_checkpoint(project)
    config = store.project_config(project)
    store.atomic_json(project / ".fbk/config.json", {**config, "check_timeout": 3})
    before = unit_files(project)
    assert checkpoint_refusal(project) is not None, "A checkpoint with a timed-out check was accepted."
    assert marker.exists(), "The check after the timed-out check never ran."
    saved = saved_output(project, before)
    for name, full in (("stdout", stdout), ("stderr", stderr)):
        assert len(full.encode()) > 1024 * 1024 + 12000
        holding = [path for path, data in saved.items() if data.decode(errors="replace") == full]
        assert holding, (f"The timed-out check's complete {name} was not saved: "
                         + repr({path: len(data) for path, data in saved.items()}))
        events = json.dumps(store.load(project, "feature")["events"])
        assert sha256(saved[holding[0]]) in events, f"The timed-out check's {name} fingerprint was not recorded."


# Review round 2 findings


def declared_production_task(root):
    edit_tasks(root, lambda by_id, tasks: by_id["prepare-tests"].update(
        files=["tests/check.py", "src/app.py"]))


def checkpoint_outcome(root, reviewer=clean_review):
    """The checkpoint's refusal message, None on a pass; any other exception is a failure
    to refuse actionably, reported as an assertion."""
    from .test_workflow_test_checkpoint import run_checkpoint

    try:
        run_checkpoint(root, reviewer)
    except store.WorkflowError as exc:
        return str(exc)
    except Exception as exc:  # noqa: BLE001 - the contract is an actionable refusal
        raise AssertionError(f"The checkpoint failed with a traceback, not a refusal: {exc!r}") from exc
    return None


# Major 2: every new preflight refusal after a stale acceptance withdraws it


def test_a_reserved_folder_collision_after_a_stale_acceptance_withdraws_it(project):
    ready_for_checkpoint(project)
    before = unit_files(project)
    assert checkpoint_refusal(project) is None
    output = output_folder(project, saved_output(project, before))
    write_decision_and_record(project)
    assert stage(project) != "writing-code"
    planted = plant_unit(project, f"feature/{Path(output).name}")
    message = checkpoint_outcome(project)
    assert message is not None and Path(output).name in message
    assert planted.is_file()
    assert work(project)["evidence"] is None, "The collision refusal kept the obsolete acceptance."


def test_an_unreadable_baseline_copy_after_a_stale_acceptance_is_refused_and_withdraws_it(project):
    if os.geteuid() == 0:
        pytest.skip("File permissions do not stop the superuser from reading.")
    declared_production_task(project)
    ready_for_checkpoint(project)
    assert checkpoint_refusal(project) is None
    write_decision_and_record(project)
    finish_test_task(project, "second-author", {"src/app.py": PLACEHOLDER}, ["src/app.py"])
    copy = baseline_copy(project, "src/app.py")
    assert copy is not None
    copy.chmod(0)
    try:
        message = checkpoint_outcome(project)
    finally:
        copy.chmod(0o644)
    assert message is not None and "src/app.py" in message
    assert work(project)["evidence"] is None, "The unreadable-copy refusal kept the obsolete acceptance."


# Major 3: a check cannot alias its own saved output destinations


ALIAS_STDOUT = b"ALIAS DECISIVE STDOUT: the release assertion failed\n"
ALIAS_STDERR = b"ALIAS DECISIVE STDERR: collected 1 item\n"
ALIAS = [sys.executable, "-c", (
    "import json, os, pathlib, sys\n"
    "plan = pathlib.Path('alias-plan.json')\n"
    "if plan.exists():\n"
    "    plan = json.loads(plan.read_text())\n"
    "    for name in ('stdout', 'stderr'):\n"
    "        destination = pathlib.Path(plan[name])\n"
    "        destination.unlink(missing_ok=True)\n"
    "        if plan['mode'] == 'symlink':\n"
    "            destination.symlink_to(pathlib.Path(plan['target']).resolve())\n"
    "        else:\n"
    "            os.link(plan['target'], destination)\n"
    f"sys.stdout.buffer.write({ALIAS_STDOUT!r})\n"
    f"sys.stderr.buffer.write({ALIAS_STDERR!r})\n"
    "raise SystemExit(1)\n"
)]


def fingerprint_records(value):
    """Every {path, sha256} pair inside a recorded value."""
    found = {}
    if isinstance(value, dict):
        if isinstance(value.get("path"), str) and isinstance(value.get("sha256"), str):
            found[value["path"]] = value["sha256"]
        for item in value.values():
            found.update(fingerprint_records(item))
    elif isinstance(value, list):
        for item in value:
            found.update(fingerprint_records(item))
    return found


@pytest.mark.parametrize("mode", ["symlink", "hardlink"])
def test_a_check_aliasing_its_saved_output_cannot_change_what_is_saved(project, mode):
    tracked = project / "notes/tracked.txt"
    tracked.parent.mkdir()
    tracked.write_bytes(b"ORIGINAL TRACKED CONTENT\n")
    edit_scope(project, checks=[CHECK, ALIAS])
    ready_for_checkpoint(project)
    # A first, rejected run shows where each stream of the aliasing check is saved.
    before = unit_files(project)
    assert checkpoint_refusal(project, blocking_review) is not None
    saved = saved_output(project, before)
    destinations = {name: next((path for path, data in saved.items() if data == expected), None)
                    for name, expected in (("stdout", ALIAS_STDOUT), ("stderr", ALIAS_STDERR))}
    assert all(destinations.values()), f"The aliasing check's streams were not saved apart: {sorted(saved)}"
    store.atomic_json(project / "alias-plan.json", {**destinations, "mode": mode,
                                                    "target": "notes/tracked.txt"})
    checkpoint_outcome(project)
    assert tracked.read_bytes() == b"ORIGINAL TRACKED CONTENT\n", "Saved output was written through a link."
    recorded = fingerprint_records(next(e for e in reversed(store.load(project, "feature")["events"])
                                        if e["event"] == "close-attempt").get("verification"))
    for name, expected in (("stdout", ALIAS_STDOUT), ("stderr", ALIAS_STDERR)):
        path = destinations[name]
        assert (project / path).read_bytes() == expected, f"The saved {name} lost the captured bytes."
        assert recorded.get(path) == sha256(expected), f"The {name} fingerprint is not of the captured bytes."


# Major 4: the diff the reviewer reads matches the snapshot it reads


def test_a_production_edit_between_comparison_and_snapshot_is_never_shown_inconsistently(project, monkeypatch):
    declared_production_task(project)
    enter_implementation(project)
    finish_test_task(project, "test-author", {"src/app.py": PLACEHOLDER}, ["src/app.py"])
    late = PLACEHOLDER + "def release():\n    return 'late-edit adds behavior'\n"
    original_snapshot = review.snapshot
    edited = []

    def edit_then_capture(root, required):
        if not edited:
            (project / "src/app.py").write_text(late)
            edited.append(True)
        return original_snapshot(root, required)

    monkeypatch.setattr(review, "snapshot", edit_then_capture)
    seen = native_capture(monkeypatch)
    message = checkpoint_outcome(project, reviewer=None)
    assert edited, "The witness seam before snapshot capture never ran."
    for capture in seen:
        if "late-edit" in capture["files"].get("src/app.py", b"").decode(errors="replace"):
            assert "late-edit" in production_diff(capture, "src/app.py"), (
                "The reviewer read a snapshot whose production change its diff does not show.")
    if not seen:
        assert message is not None


# Minor 5: a production change before a cancellation stays in the comparison


@pytest.mark.parametrize("change", ["declared", "undeclared"])
def test_a_production_change_before_cancellation_survives_the_relaunch(project, monkeypatch, change):
    declared_production_task(project)
    enter_implementation(project)
    assert start(project, "prepare-tests", "test-author") is None
    if change == "declared":
        (project / "src/app.py").write_text(PLACEHOLDER)
    else:
        (project / "src/helper.py").write_text("UNDECLARED = 1\n")
    mutate(project, handoff.cancel_task, "s", "prepare-tests", "The worker stopped before finishing.")
    finish_test_task(project, "second-author", {}, [])
    assert stage(project) == "ready-for-checkpoint"
    seen = native_capture(monkeypatch)
    message = checkpoint_outcome(project, reviewer=None)
    if change == "undeclared":
        assert message is not None and "src/helper.py" in message, "The earlier undeclared change was hidden."
        assert seen == []
        return
    assert message is None, message
    diff = production_diff(seen[-1], "src/app.py")
    assert any(line.startswith("+") and "placeholder-for-new-signature" in line for line in diff.splitlines()), (
        "The production change made before the cancellation is missing from the diff.")


# Minor 6: saved output is kept byte for byte


RAW_STDOUT = b"OUT \xff\xfe not utf-8\r\nwindows line\rold mac line\nunix line\n\x80 trailing"
RAW_STDERR = b"ERR \xc3\x28 invalid\r\n\r\nmixed\n\xfe\xff end"


def test_saved_output_keeps_every_byte_in_the_tree_and_the_snapshot(project, monkeypatch):
    raw = [sys.executable, "-c", (
        "import sys\n"
        f"sys.stdout.buffer.write({RAW_STDOUT!r})\n"
        f"sys.stderr.buffer.write({RAW_STDERR!r})\n"
        "raise SystemExit(1)\n"
    )]
    edit_scope(project, checks=[CHECK, raw])
    ready_for_checkpoint(project)
    before = unit_files(project)
    seen = native_capture(monkeypatch)
    assert checkpoint_outcome(project, reviewer=None) is None
    saved = saved_output(project, before)
    received = saved_in_snapshot(seen[-1])
    for name, expected in (("stdout", RAW_STDOUT), ("stderr", RAW_STDERR)):
        paths = [path for path, data in saved.items() if data == expected]
        assert paths, f"No saved file holds the check's {name} byte for byte."
        assert received.get(paths[0]) == expected, f"The reviewer's snapshot changed the saved {name}."


# Review round 3 findings (3 and 4 await the operator's decision and are not pinned)


# Major 1: a declared production file unchanged at comparison is bound too


def test_an_unchanged_declared_production_file_edited_before_capture_is_refused(project, monkeypatch):
    declared_production_task(project)
    enter_implementation(project)
    # The test task changes only its test; its declared production file matches the baseline.
    finish_test_task(project, "test-author",
                     {"tests/check.py": RED_TEST.replace("is still missing", "was never released")},
                     ["tests/check.py"])
    original_snapshot = review.snapshot
    edited = []

    def edit_then_capture(root, required):
        if not edited:
            (project / "src/app.py").write_text("def release():\n    return 'late-edit adds behavior'\n")
            edited.append(True)
        return original_snapshot(root, required)

    monkeypatch.setattr(review, "snapshot", edit_then_capture)
    seen = native_capture(monkeypatch)
    message = checkpoint_outcome(project, reviewer=None)
    assert edited, "The witness seam before snapshot capture never ran."
    assert seen == [], "A reader saw production changed after the comparison, with no diff for it."
    assert message is not None
    assert work(project)["evidence"] is None


# Major 2: an unreadable ignore file after a stale acceptance


def test_an_unreadable_ignore_file_after_a_stale_acceptance_is_refused_and_withdraws_it(project):
    if os.geteuid() == 0:
        pytest.skip("File permissions do not stop the superuser from reading.")
    ready_for_checkpoint(project)
    assert checkpoint_refusal(project) is None
    write_decision_and_record(project)
    assert stage(project) != "writing-code"
    ignore = project / ".fbk/.gitignore"
    assert ignore.is_file()
    ignore.chmod(0)
    try:
        message = checkpoint_outcome(project)
    finally:
        ignore.chmod(0o644)
    assert message is not None and ".gitignore" in message
    assert work(project)["evidence"] is None, "The ignore-file refusal kept the obsolete acceptance."


# Major 5: a verified implementation change survives a no-edit relaunch


@pytest.mark.parametrize("after", ["no-edit", "edit-after-relaunch"])
def test_a_verified_implementation_change_survives_a_no_edit_relaunch(project, after):
    code_done_with_owned_folder(project)
    assert start(project, "cancel", "implementer-2") is None
    returned = mutate(project, handoff.finish_task, "s", "cancel", changed_files=[],
                      checks=[{"argv": CHECK, "exit_code": 0, "evidence": "Release still happens."}],
                      unresolved=[], outcome="Nothing further to change.")
    assert returned["status"] == "completed"
    make_checkpoint_rerunnable(project)
    if after == "edit-after-relaunch":
        (project / "src/helper.py").write_text("HELPER = 'edited after the relaunch'\n")
        message = checkpoint_refusal(project)
        assert message is not None and "src/helper.py" in message, "An edit after the relaunch was exempted."
        return
    message = checkpoint_refusal(project)
    assert message is None, f"The earlier verified change was refused after a no-edit relaunch: {message}"


# Major 6: the large-diff artifact never replaces a repository file


def test_a_repository_file_at_the_diff_artifact_path_keeps_its_content(project, monkeypatch):
    existing = ".review-verification-diffs/production-diffs.json"
    original = b"original repository content at the old diff path\n"
    (project / existing).parent.mkdir()
    (project / existing).write_bytes(original)
    declared_production_task(project)
    enter_implementation(project)
    large = "".join(f"def placeholder_{n}(task):\n    return None\n" for n in range(1500))
    finish_test_task(project, "test-author", {"src/app.py": large}, ["src/app.py"])
    seen = native_capture(monkeypatch)
    assert checkpoint_outcome(project, reviewer=None) is None
    capture = seen[-1]
    assert capture["files"].get(existing) == original, "The diff artifact replaced a repository file."
    diff = production_diff(capture, "src/app.py")
    assert "placeholder_1499" in diff, "The large diff did not reach the reviewer."


# Minor 7: a successful check's output is saved too


def test_a_successful_checks_output_is_saved_whole_beside_a_failing_check(project, monkeypatch):
    ok = [sys.executable, "-c", (
        "import sys\n"
        "sys.stdout.write('PASSING CHECK STDOUT: test_existing_behavior PASSED\\n' + 'pass detail\\n' * 2000)\n"
        "sys.stderr.write('PASSING CHECK STDERR: 1 passed in 0.01s\\n' + 'pass note\\n' * 2000)\n"
    )]
    expected = subprocess.run(ok, capture_output=True, timeout=30)
    assert expected.returncode == 0
    assert len(expected.stdout) > 12000 and len(expected.stderr) > 12000
    edit_scope(project, checks=[CHECK, ok])
    ready_for_checkpoint(project)
    before = unit_files(project)
    seen = native_capture(monkeypatch)
    assert checkpoint_outcome(project, reviewer=None) is None
    saved = saved_output(project, before)
    received = saved_in_snapshot(seen[-1])
    accepted = json.dumps(work(project)["evidence"])
    reading = required_reading(seen[-1]["prompt"])
    for name, data in (("stdout", expected.stdout), ("stderr", expected.stderr)):
        paths = [path for path, content in saved.items() if content == data]
        assert paths, f"The successful check's {name} was not saved byte for byte."
        assert sha256(data) in accepted, f"The successful check's {name} fingerprint is not in the evidence."
        assert received.get(paths[0]) == data, f"The reviewer's snapshot lacks the successful check's {name}."
        assert paths[0] in reading, f"The successful check's {name} is not required reading."


# Review round 4 findings


# Major: a file added under a declared production directory before capture is refused


def test_a_new_file_under_a_declared_production_directory_before_capture_is_refused(project, monkeypatch):
    edit_tasks(project, lambda by_id, tasks: by_id["prepare-tests"].update(files=["tests/check.py", "src"]))
    enter_implementation(project)
    finish_test_task(project, "test-author", {"src/app.py": PLACEHOLDER}, ["src/app.py"])
    original_snapshot = review.snapshot
    added = []

    def add_then_capture(root, required):
        if not added:
            (project / "src/late.py").write_text("def release():\n    return 'late addition adds behavior'\n")
            added.append(True)
        return original_snapshot(root, required)

    monkeypatch.setattr(review, "snapshot", add_then_capture)
    seen = native_capture(monkeypatch)
    message = checkpoint_outcome(project, reviewer=None)
    assert added, "The witness seam before snapshot capture never ran."
    assert seen == [], "A reader saw a production file added after the comparison, with no diff for it."
    assert message is not None
    assert work(project)["evidence"] is None


# Minor: production deletions


EXTRA = "def existing_behavior():\n    return 'kept by the baseline'\n\nVALUE = 42\n"


def test_an_undeclared_production_deletion_is_refused_before_checks_or_review(project):
    marker, probe = probe_check(project)
    edit_scope(project, checks=[CHECK, probe])
    (project / "src/extra.py").write_text(EXTRA)
    ready_for_checkpoint(project)
    (project / "src/extra.py").unlink()
    marker.unlink(missing_ok=True)
    reviewer, calls = counting(clean_review)
    message = checkpoint_outcome(project, reviewer)
    assert message is not None and "src/extra.py" in message, "An undeclared deletion reached the checkpoint."
    assert not marker.exists(), "Checks ran despite an undeclared deletion."
    assert calls == [] and work(project)["rounds"] == []


def test_a_declared_production_deletion_reaches_the_reviewer_as_a_complete_diff(project, monkeypatch):
    edit_tasks(project, lambda by_id, tasks: by_id["prepare-tests"].update(
        files=["tests/check.py", "src/extra.py"]))
    (project / "src/extra.py").write_text(EXTRA)
    enter_implementation(project)
    assert start(project, "prepare-tests", "test-author") is None
    (project / "src/extra.py").unlink()
    returned = mutate(project, handoff.finish_task, "s", "prepare-tests", changed_files=["src/extra.py"],
                      checks=[{"argv": CHECK, "exit_code": 1, "evidence": "Release is still missing."}],
                      unresolved=[], outcome="The obsolete module is removed.")
    assert returned["status"] == "completed"
    seen = native_capture(monkeypatch)
    assert checkpoint_outcome(project, reviewer=None) is None
    diff = production_diff(seen[-1], "src/extra.py")
    lines = diff.splitlines()
    assert any(line.startswith("+++") and "/dev/null" in line for line in lines), diff
    removed = [line[1:] for line in lines if line.startswith("-") and not line.startswith("---")]
    assert removed == EXTRA.splitlines(), f"The deletion diff does not remove every baseline line: {diff!r}"
    assert not any(line.startswith("+") and not line.startswith("+++") for line in lines)


# Review round 5 findings


# Major 1 (lead ruling): the checkpoint refuses while any task is running


@pytest.mark.parametrize("running", ["test-task", "implementation-task"])
def test_the_checkpoint_refuses_while_a_task_is_running(project, running):
    marker, probe = probe_check(project)
    edit_scope(project, checks=[CHECK, probe])
    if running == "test-task":
        ready_for_checkpoint(project)
        task = "prepare-tests"
        assert start(project, task, "rework-author") is None
    else:
        # A governing decision while code is being written: the checkpoint could otherwise
        # run again while an implementation task is still changing code.
        prepare_implementation(project)
        task = "cancel"
        assert start(project, task, "implementer") is None
        write_decision_and_record(project)
        assert stage(project) == "ready-for-checkpoint"
    rounds = len(work(project)["rounds"])
    marker.unlink(missing_ok=True)
    reviewer, calls = counting(clean_review)
    message = checkpoint_outcome(project, reviewer)
    assert message is not None, f"The checkpoint ran while {task} was running."
    assert task in message, f"The refusal does not name the running task {task}: {message}"
    assert not marker.exists(), "Checks ran while a task was running."
    assert calls == [] and len(work(project)["rounds"]) == rounds and work(project)["evidence"] is None


# Major 2: ignore entries made ineffective by a later line are made effective again


def record_folder_files(root):
    """Every file in the unit's baseline and output folders: actual copies and saved output."""
    # The unit's only folders besides its own documents are Firebreak's record folders; the
    # two this covers are the ones other than the record folders this step's tests do not cover.
    folders = {f"{UNIT}/{path.name}" for path in (root / UNIT).iterdir()
               if path.is_dir() and path.name not in {"decisions", "design", *OTHER_RECORD_FOLDERS}}
    assert baseline_folder(root) in folders
    files = sorted(path.relative_to(root).as_posix() for folder in folders
                   for path in (root / folder).rglob("*") if path.is_file())
    assert len(folders) == 2 and files, f"The record folders were not found: {sorted(folders)}"
    return files


@pytest.mark.parametrize("trigger", ["workflow-init", "checkpoint"])
def test_ignore_entries_overridden_by_a_later_negation_are_made_effective_again(project, trigger):
    assert git(project, "init", "-q").returncode == 0
    ready_for_checkpoint(project)
    before = unit_files(project)
    # A rejected run creates the output folder, so both folder names are known.
    assert checkpoint_refusal(project, blocking_review) is not None
    paths = [f"{baseline_folder(project)}/tests/check.py",
             sorted(saved_output(project, before))[0]]
    assert all(ignored(project, path) for path in paths)
    ignore = project / ".fbk/.gitignore"
    ignore.write_text(ignore.read_text() + "# project line\n!**/\n")
    if trigger == "workflow-init":
        call(project, "workflow-init")
    else:
        # Reworked tests need a fresh review, which passes.
        finish_test_task(project, "rework-author",
                         {"tests/check.py": RED_TEST.replace("is still missing", "was never released")},
                         ["tests/check.py"])
        assert checkpoint_refusal(project) is None
    for path in record_folder_files(project):
        assert ignored(project, path), f"After {trigger}, git does not ignore {path}."
    lines = ignore.read_text().splitlines()
    assert "# project line" in lines and "!**/" in lines, "The project's own lines were lost."


# Minor 3: an empty production file's creation or deletion is a visible diff


@pytest.mark.parametrize("change", ["create", "delete"])
def test_an_empty_production_file_created_or_deleted_shows_a_diff(project, monkeypatch, change):
    path = "src/__init__.py"
    if change == "create":
        edit_scope(project, creates=[path])
    else:
        (project / path).write_bytes(b"")
    edit_tasks(project, lambda by_id, tasks: by_id["prepare-tests"].update(files=["tests/check.py", path]))
    enter_implementation(project)
    assert start(project, "prepare-tests", "test-author") is None
    if change == "create":
        (project / path).write_bytes(b"")
    else:
        (project / path).unlink()
    returned = mutate(project, handoff.finish_task, "s", "prepare-tests", changed_files=[path],
                      checks=[{"argv": CHECK, "exit_code": 1, "evidence": "Release is still missing."}],
                      unresolved=[], outcome=f"The empty package marker is {change}d.")
    assert returned["status"] == "completed"
    seen = native_capture(monkeypatch)
    assert checkpoint_outcome(project, reviewer=None) is None
    diff = production_diff(seen[-1], path)
    header = "---" if change == "create" else "+++"
    assert any(line.startswith(header) and "/dev/null" in line for line in diff.splitlines()), (
        f"The empty file's {change} produced no creation or deletion header: {diff!r}")


# Minor 4: a scoped test deleted by a test task is identified as removed


def test_a_deleted_scoped_test_is_identified_as_removed(project, monkeypatch):
    (project / "tests/old_check.py").write_text(PASSING_TEST)
    edit_tasks(project, lambda by_id, tasks: by_id["prepare-tests"].update(
        files=["tests/check.py", "tests/old_check.py"]))
    enter_implementation(project)
    assert start(project, "prepare-tests", "test-author") is None
    (project / "tests/old_check.py").unlink()
    returned = mutate(project, handoff.finish_task, "s", "prepare-tests", changed_files=["tests/old_check.py"],
                      checks=[{"argv": CHECK, "exit_code": 1, "evidence": "Release is still missing."}],
                      unresolved=[], outcome="The obsolete test is removed.")
    assert returned["status"] == "completed"
    seen = native_capture(monkeypatch)
    assert checkpoint_outcome(project, reviewer=None) is None
    changed, untouched = comparison(seen[-1]["prompt"])
    assert "tests/old_check.py" not in untouched
    found = []

    def walk(value):
        if isinstance(value, dict):
            if any("untouched" in key.lower() for key in value):
                found.extend(item for key, item in value.items()
                             if "remov" in key.lower() or "delet" in key.lower())
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(payload(seen[-1]["prompt"]))
    assert any("tests/old_check.py" in json.dumps(item) for item in found), (
        "The reviewer's comparison does not identify the deleted test as removed.")


# Review round 6 findings


# Major 1: negations naming the real unit's folders are caught too


@pytest.mark.parametrize("trigger", ["workflow-init", "checkpoint"])
def test_unit_specific_negations_of_the_record_folders_are_caught(project, trigger):
    assert git(project, "init", "-q").returncode == 0
    ready_for_checkpoint(project)
    before = unit_files(project)
    assert checkpoint_refusal(project, blocking_review) is not None
    paths = [f"{baseline_folder(project)}/tests/check.py", sorted(saved_output(project, before))[0]]
    assert all(ignored(project, path) for path in paths)
    rules = [f"!feature/{Path(path).relative_to(UNIT).parts[0]}/" for path in paths]
    ignore = project / ".fbk/.gitignore"
    ignore.write_text(ignore.read_text() + "".join(f"{rule}\n" for rule in rules))
    message = None
    try:
        if trigger == "workflow-init":
            call(project, "workflow-init")
        else:
            finish_test_task(project, "rework-author",
                             {"tests/check.py": RED_TEST.replace("is still missing", "was never released")},
                             ["tests/check.py"])
            message = checkpoint_refusal(project)
    except store.WorkflowError as exc:
        message = str(exc)
    if message is not None:
        assert any(rule in message for rule in rules), (
            f"The refusal does not name the rule that re-includes the folders: {message}")
    for path in record_folder_files(project):
        assert ignored(project, path), f"After {trigger}, git does not ignore {path}."


# Major 2: the running-task refusal withdraws a stale acceptance


def test_a_running_task_refusal_withdraws_a_stale_acceptance(project):
    ready_for_checkpoint(project)
    assert checkpoint_refusal(project) is None
    assert start(project, "cancel", "implementer") is None
    accepted_revision = work(project)["evidence"]["revision"]
    before = store.load(project, "feature").get("decisions", [])
    write_decision_and_record(project)
    assert stage(project) != "writing-code"
    reviewer, calls = counting(clean_review)
    message = checkpoint_outcome(project, reviewer)
    assert message is not None and "cancel" in message, message
    assert calls == []
    assert work(project)["evidence"] is None, "The running-task refusal kept the obsolete acceptance."
    # Restoring the earlier revision does not revive it.
    with store.transaction(project):
        record = store.load(project, "feature")
        record["decisions"] = before
        store.save(project, record)
    from .test_workflow_test_checkpoint import checkpoint_revision

    assert checkpoint_revision(project) == accepted_revision, "The witness did not restore the revision."
    assert work(project)["evidence"] is None
    assert stage(project) != "writing-code", "Restoring the revision revived the withdrawn acceptance."


# Review round 7 findings


def restore_decisions(root, decisions):
    with store.transaction(root):
        record = store.load(root, "feature")
        record["decisions"] = decisions
        store.save(root, record)


# Major 1: every remaining checkpoint refusal after a stale acceptance withdraws it


def test_an_active_worker_refusal_withdraws_a_stale_acceptance(project):
    from .test_workflow_test_checkpoint import checkpoint_revision

    ready_for_checkpoint(project)
    assert checkpoint_refusal(project) is None
    accepted_revision = work(project)["evidence"]["revision"]
    decisions = store.load(project, "feature").get("decisions", [])
    # A real running task: its run and its active worker entry. Decisions cannot be recorded
    # while a worker is active, so the decision lands between the launch and the worker start.
    assert start(project, "cancel", "implementer") is None
    write_decision_and_record(project)
    hooks.handle(project, {"hook_event_name": "SubagentStart", "session_id": "s",
                           "agent_id": "implementer", "cwd": str(project)})
    assert any(store.load(project, "feature")["workers"].values()), "The worker was not recorded as active."
    reviewer, calls = counting(clean_review)
    assert checkpoint_outcome(project, reviewer) is not None
    assert calls == []
    assert work(project)["evidence"] is None, "The active-worker refusal kept the obsolete acceptance."
    restore_decisions(project, decisions)
    assert checkpoint_revision(project) == accepted_revision, "The witness did not restore the revision."
    assert work(project)["evidence"] is None
    assert stage(project) != "writing-code", "Restoring the revision revived the withdrawn acceptance."


def test_an_exhausted_round_refusal_withdraws_a_stale_acceptance(project):
    from .test_workflow_test_checkpoint import checkpoint_revision

    ready_for_checkpoint(project)
    # Two rejected rounds, each followed by rework, then a pass on the final round.
    for cycle in (1, 2):
        assert checkpoint_refusal(project, blocking_review) is not None
        finish_test_task(project, f"rework-author-{cycle}",
                         {"tests/check.py": RED_TEST.replace("is still missing", f"rework {cycle}")},
                         ["tests/check.py"])
    assert checkpoint_refusal(project) is None
    assert engine.spent_rounds(work(project)) == work(project)["round_limit"] == 3
    accepted_revision = work(project)["evidence"]["revision"]
    decisions = store.load(project, "feature").get("decisions", [])
    write_decision_and_record(project)
    reviewer, calls = counting(clean_review)
    assert checkpoint_outcome(project, reviewer) is not None
    assert calls == []
    assert work(project)["evidence"] is None, "The exhausted-round refusal kept the obsolete acceptance."
    restore_decisions(project, decisions)
    assert checkpoint_revision(project) == accepted_revision, "The witness did not restore the revision."
    assert work(project)["evidence"] is None
    assert stage(project) != "writing-code", "Restoring the revision revived the withdrawn acceptance."


# Major 2: runtime copies of saved output stay ignored


def blocking_reader(snapshot, prompt, config, **kwargs):
    return {"review": blocking_review()["review"]}


@pytest.mark.parametrize("trigger", ["workflow-init", "checkpoint"])
def test_a_runtime_negation_does_not_expose_copied_output(project, monkeypatch, trigger):
    assert git(project, "init", "-q").returncode == 0
    ready_for_checkpoint(project)
    before = unit_files(project)
    monkeypatch.setattr(review, "claude_review", blocking_reader)
    assert checkpoint_refusal(project, reviewer=None) is not None
    saved = set(saved_output(project, before).values())
    runtime = project / ".fbk/runtime"
    copies = sorted(path.relative_to(project).as_posix() for path in runtime.rglob("*")
                    if path.is_file() and path.read_bytes() in saved and path.read_bytes())
    assert copies, "The native review left no runtime copy of the saved output; the fixture proves nothing."
    assert all(ignored(project, path) for path in copies)
    ignore = project / ".fbk/.gitignore"
    # Git cannot re-include files inside an excluded folder, so "!runtime/**" alone leaves
    # the copies ignored; "!runtime/" with it exposes them.
    rules = ["!runtime/", "!runtime/**"]
    ignore.write_text(ignore.read_text() + "# project line\n" + "".join(f"{rule}\n" for rule in rules))
    message = None
    try:
        if trigger == "workflow-init":
            call(project, "workflow-init")
        else:
            finish_test_task(project, "rework-author",
                             {"tests/check.py": RED_TEST.replace("is still missing", "was never released")},
                             ["tests/check.py"])
            message = checkpoint_refusal(project)
    except store.WorkflowError as exc:
        message = str(exc)
    if message is not None:
        assert any(rule in message for rule in rules), (
            f"The refusal does not name the rule that re-includes runtime copies: {message}")
    for path in [*copies, *record_folder_files(project)]:
        assert ignored(project, path), f"After {trigger}, git does not ignore {path}."
    lines = ignore.read_text().splitlines()
    assert "# project line" in lines, "The project's own lines were lost."


# Major 3: executable-bit changes are compared, shown, and kept


def executable(path):
    return bool(path.stat().st_mode & 0o111)


def test_an_undeclared_executable_bit_change_is_refused_before_review(project):
    ready_for_checkpoint(project)
    (project / "src/app.py").chmod(0o755)
    reviewer, calls = counting(clean_review)
    message = checkpoint_outcome(project, reviewer)
    assert message is not None and "src/app.py" in message, "An undeclared mode change reached review."
    assert calls == [] and work(project)["rounds"] == []


def test_a_declared_executable_bit_change_is_shown_and_modes_are_kept(project, monkeypatch):
    declared_production_task(project)
    (project / "src/run.sh").write_text("#!/bin/sh\necho run\n")
    (project / "src/run.sh").chmod(0o755)
    (project / "src/app.py").chmod(0o644)
    enter_implementation(project)
    assert executable(baseline_copy(project, "src/run.sh")), "The baseline copy lost the executable bit."
    assert not executable(baseline_copy(project, "src/app.py"))
    assert start(project, "prepare-tests", "test-author") is None
    (project / "src/app.py").chmod(0o755)
    returned = mutate(project, handoff.finish_task, "s", "prepare-tests", changed_files=[],
                      checks=[{"argv": CHECK, "exit_code": 1, "evidence": "Release is still missing."}],
                      unresolved=[], outcome="The module becomes executable.")
    assert returned["status"] == "completed"
    modes = []

    def reader(snapshot, prompt, config, **kwargs):
        snapshot = Path(snapshot)
        modes.append({name: executable(snapshot / name) for name in ("src/app.py", "src/run.sh")})
        return {"review": {"summary": "Inspected the authored tests.", "findings": []}}

    seen = native_capture(monkeypatch)
    capture_reader = review.claude_review
    monkeypatch.setattr(review, "claude_review", lambda *a, **k: (reader(*a, **k), capture_reader(*a, **k))[1])
    assert checkpoint_outcome(project, reviewer=None) is None
    diff = production_diff(seen[-1], "src/app.py")
    assert re.search(r"mode", diff, re.I) and "755" in diff, f"The mode change is not in the diff: {diff!r}"
    assert modes[-1] == {"src/app.py": True, "src/run.sh": True}, f"The snapshot lost file modes: {modes[-1]}"
    assert not executable(baseline_copy(project, "src/app.py")), "The baseline copy took the later mode."


# Minor 4: every baseline copy is verified at preflight


@pytest.mark.parametrize("damage", ["corrupted", "removed"])
@pytest.mark.parametrize("path", ["tests/check.py", "src/app.py"])
def test_a_damaged_copy_of_an_unchanged_file_is_refused_at_preflight(project, path, damage):
    marker, probe = probe_check(project)
    edit_scope(project, checks=[CHECK, probe])
    ready_for_checkpoint(project)
    copy = baseline_copy(project, path)
    assert copy is not None
    if damage == "corrupted":
        copy.write_text("not the recorded baseline\n")
    else:
        copy.unlink()
    marker.unlink(missing_ok=True)
    reviewer, calls = counting(clean_review)
    message = checkpoint_outcome(project, reviewer)
    assert message is not None and path in message, f"A {damage} baseline copy of {path} was accepted."
    assert not marker.exists() and calls == [] and work(project)["rounds"] == []


# Minor 5: a verified implementation deletion is exempt


def test_a_verified_implementation_deletion_is_accepted_by_a_rerun_checkpoint(project):
    (project / "src/obsolete.py").write_text("OBSOLETE = True\n")
    code_done_after_checkpoint(project, owned=["src"], removes=["src/obsolete.py"])
    make_checkpoint_rerunnable(project)
    message = checkpoint_refusal(project)
    assert message is None, f"A verified implementation deletion was refused: {message}"


# Minor 6: the native reader must declare the large-diff file


def test_a_native_reader_omitting_the_large_diff_file_is_rejected(project, monkeypatch):
    declared_production_task(project)
    enter_implementation(project)
    large = "".join(f"def placeholder_{n}(task):\n    return None\n" for n in range(1500))
    finish_test_task(project, "test-author", {"src/app.py": large}, ["src/app.py"])
    real_run = review.run_command
    prompts = []

    def host(argv, root, timeout, prompt=None, **kwargs):
        if argv[0] != "claude":
            return real_run(argv, root, timeout, prompt, **kwargs)
        prompts.append(prompt)
        # The host declares every required path that exists in the repository, leaving
        # out anything Firebreak placed only in the reviewer's snapshot.
        declared = [p for p in required_reading(prompt) if (project / p).exists()]
        data = {"summary": "Inspected the authored tests.", "findings": [],
                "context": {"status": "complete", "inspected_files": declared,
                            "supporting_files": [], "missing_context": []}}
        envelope = {"subtype": "success", "is_error": False, "structured_output": data}
        return {"argv": argv, "exit_code": 0, "seconds": 0.01, "stdout": json.dumps(envelope), "stderr": ""}

    monkeypatch.setattr(review, "run_command", host)
    message = checkpoint_outcome(project, reviewer=None)
    assert prompts, "The native host was not asked."
    omitted = [p for p in required_reading(prompts[0]) if not (project / p).exists()]
    assert omitted, "The large diffs did not move to a snapshot file; the fixture proves nothing."
    assert message is not None, "A native reader that never read the large diff file was accepted."
    assert work(project)["evidence"] is None


# Review round 8 findings (minor 4 is not pinned: council never runs for the checkpoint)


# Major 1: a mode-only change after a review awaiting disposition forces a fresh review


def test_a_mode_only_change_after_a_disposition_wait_forces_a_fresh_review(project, monkeypatch):
    from .test_workflow_test_checkpoint import record_disposition, suggestion

    declared_production_task(project)
    (project / "src/app.py").chmod(0o644)
    enter_implementation(project)
    finish_test_task(project, "test-author", {"src/app.py": PLACEHOLDER}, ["src/app.py"])
    finding = suggestion(remedy_kind="test")
    monkeypatch.setattr(review, "claude_review", lambda *a, **k: {
        "review": {"summary": "Inspected the authored tests.", "findings": [dict(finding)]}})
    message = checkpoint_outcome(project, reviewer=None)
    assert message is not None and finding["title"] in message, "The review did not wait for a disposition."
    assert refusal_free(record_disposition, project, finding)
    (project / "src/app.py").chmod(0o755)
    seen = native_capture(monkeypatch)
    checkpoint_outcome(project, reviewer=None)
    assert seen, "The retry reused the earlier review instead of reviewing the mode change."
    diff = production_diff(seen[-1], "src/app.py")
    assert re.search(r"mode", diff, re.I) and "755" in diff, f"The fresh review does not see the mode change: {diff!r}"


def refusal_free(fn, *args):
    try:
        fn(*args)
    except store.WorkflowError as exc:
        raise AssertionError(f"Setup step refused: {exc}") from exc
    return True


# Major 2 (lead ruling): record folders and runtime carry their own ignore-everything file


def test_selective_negations_cannot_expose_saved_output(project):
    assert git(project, "init", "-q").returncode == 0
    ready_for_checkpoint(project)
    before = unit_files(project)
    assert checkpoint_refusal(project, blocking_review) is not None
    output = Path(output_folder(project, saved_output(project, before))).name
    ignore = project / ".fbk/.gitignore"
    ignore.write_text(ignore.read_text() + (
        f"!feature/{output}/\nfeature/{output}/*\n!feature/{output}/check-*.stdout.txt\n"))
    finish_test_task(project, "rework-author",
                     {"tests/check.py": RED_TEST.replace("is still missing", "was never released")},
                     ["tests/check.py"])
    before = unit_files(project)
    message = checkpoint_refusal(project)
    assert message is None, message
    saved = sorted(path for path in unit_files(project) if path.startswith(f"{UNIT}/{output}/"))
    assert saved, "The checkpoint saved no output."
    for path in saved:
        assert ignored(project, path), f"Git does not ignore the saved output {path}."
    # The structure the lead ruled: each record folder and the runtime folder ignore everything.
    for folder in (baseline_folder(project), f"{UNIT}/{output}", ".fbk/runtime"):
        own = project / folder / ".gitignore"
        assert own.is_file() and "*" in own.read_text().splitlines(), f"{folder} has no ignore-everything file."


# Major 3: an implementation exemption never covers a later mode change


def test_a_mode_change_after_a_verified_implementation_edit_is_refused(project):
    (project / "src/app.py").chmod(0o644)
    code_done_after_checkpoint(project)
    make_checkpoint_rerunnable(project)
    # Made after the re-recorded baseline, by no running task.
    (project / "src/app.py").chmod(0o755)
    reviewer, calls = counting(clean_review)
    message = checkpoint_outcome(project, reviewer)
    assert message is not None and "src/app.py" in message, "A mode change after the verified edit was exempted."
    assert calls == [] and work(project)["evidence"] is None



# Implementer's known gap: a scoped root .gitignore beside the baseline folder's own


def test_a_scoped_root_ignore_file_round_trips_through_the_baseline(project):
    assert git(project, "init", "-q").returncode == 0
    original = b"build/\n# the project's own root ignore file\n"
    (project / ".gitignore").write_bytes(original)
    edit_scope(project, sources=["src", ".gitignore"])
    ready_for_checkpoint(project)
    copy = baseline_copy(project, ".gitignore")
    assert copy is not None and copy.read_bytes() == original, (
        "The baseline copy of the root .gitignore collides with the baseline folder's own ignore file.")
    assert checkpoint_refusal(project) is None, "Baseline verification failed for the root .gitignore copy."
    assert ignored(project, f"{baseline_folder(project)}/tests/check.py"), "The baseline folder is no longer ignored."


# Review round 9 findings


# Major 1: the retry's investigation workspace carries the changed mode


def test_a_retry_after_a_mode_only_change_gives_investigations_the_new_mode(project, monkeypatch):
    from .test_workflow_test_checkpoint import record_disposition, suggestion

    declared_production_task(project)
    (project / "src/app.py").chmod(0o644)
    enter_implementation(project)
    finish_test_task(project, "test-author", {"src/app.py": PLACEHOLDER}, ["src/app.py"])
    finding = suggestion(remedy_kind="test")
    monkeypatch.setattr(review, "claude_review", lambda *a, **k: {
        "review": {"summary": "Inspected the authored tests.", "findings": [dict(finding)]}})
    assert checkpoint_outcome(project, reviewer=None) is not None
    assert refusal_free(record_disposition, project, finding)
    (project / "src/app.py").chmod(0o755)
    native_capture(monkeypatch)
    checkpoint_outcome(project, reviewer=None)
    round_id = (work(project)["rounds"][-1].get("result") or {}).get("investigation_round")
    assert round_id, "The retry recorded no investigation round."
    workspace = project / ".fbk/runtime/review-rounds" / round_id / "sources/src/app.py"
    assert workspace.is_file(), "The retry's investigation workspace has no copy of src/app.py."
    assert executable(workspace), "Investigations would copy the old mode, not the reviewed one."


# Major 2: retargeting a scoped symlink between equal-content files


def link_project(root):
    (root / "src/a.py").write_text("CONFIG = 'same content'\n")
    (root / "src/b.py").write_text("CONFIG = 'same content'\n")
    os.symlink("a.py", root / "src/launcher.py")


def retarget(root):
    (root / "src/launcher.py").unlink()
    os.symlink("b.py", root / "src/launcher.py")


def test_an_undeclared_symlink_retarget_is_refused_before_review(project):
    link_project(project)
    ready_for_checkpoint(project)
    retarget(project)
    reviewer, calls = counting(clean_review)
    message = checkpoint_outcome(project, reviewer)
    assert message is not None and "src/launcher.py" in message, "An undeclared link retarget reached review."
    assert calls == [] and work(project)["rounds"] == []


def test_a_declared_symlink_retarget_is_shown_and_snapshotted(project, monkeypatch):
    link_project(project)
    edit_tasks(project, lambda by_id, tasks: by_id["prepare-tests"].update(
        files=["tests/check.py", "src/launcher.py"]))
    enter_implementation(project)
    assert start(project, "prepare-tests", "test-author") is None
    retarget(project)
    returned = mutate(project, handoff.finish_task, "s", "prepare-tests", changed_files=[],
                      checks=[{"argv": CHECK, "exit_code": 1, "evidence": "Release is still missing."}],
                      unresolved=[], outcome="The launcher now points at b.py.")
    assert returned["status"] == "completed"
    links = []

    def reader(snapshot, prompt, config, **kwargs):
        target = Path(snapshot) / "src/launcher.py"
        links.append(os.readlink(target) if target.is_symlink() else None)
        return {"review": {"summary": "Inspected the authored tests.", "findings": []}}

    seen = native_capture(monkeypatch)
    capture_reader = review.claude_review
    monkeypatch.setattr(review, "claude_review", lambda *a, **k: (reader(*a, **k), capture_reader(*a, **k))[1])
    message = checkpoint_outcome(project, reviewer=None)
    assert seen, f"No reader ran: {message}"
    diff = production_diff(seen[-1], "src/launcher.py")
    assert "a.py" in diff and "b.py" in diff, f"The diff does not show the link-target change: {diff!r}"
    represented = links[-1] is not None and links[-1].endswith("b.py") or any(
        b"src/launcher.py" in data and b"b.py" in data
        for path, data in seen[-1]["files"].items()
        if path != "src/launcher.py" and "diff" not in path.lower())
    assert represented, "The reviewer's snapshot does not represent the link's target."


# Follow-up group B, review round 1


def link_maps(value):
    """Every target a structure maps src/launcher.py to, wherever it appears."""
    found = []
    if isinstance(value, dict):
        if isinstance(value.get("src/launcher.py"), str):
            found.append(value["src/launcher.py"])
        for item in value.values():
            found += link_maps(item)
    elif isinstance(value, list):
        for item in value:
            found += link_maps(item)
    return found


def link_targets_in(folder, relative="src/launcher.py"):
    """The targets a stored tree gives a link: the link itself, or any JSON listing in it."""
    folder = Path(folder)
    found = [os.readlink(folder / relative)] if (folder / relative).is_symlink() else []
    for path in folder.rglob("*.json"):
        try:
            found += link_maps(json.loads(path.read_text()))
        except (OSError, ValueError):
            continue
    return found


def declared_link_task(root):
    link_project(root)
    edit_tasks(root, lambda by_id, tasks: by_id["prepare-tests"].update(
        files=["tests/check.py", "src/app.py", "src/launcher.py"]))


def test_a_standalone_round_over_a_symlink_keeps_its_snapshot_intact(tmp_path):
    # Catches writing the link listing into a snapshot whose manifest omits it: the
    # untouched snapshot then reads as damaged and contributors are refused.
    from fbk.workflow import review_rounds

    (tmp_path / "a.py").write_text("x = 1\n")
    os.symlink("a.py", tmp_path / "link.py")
    record = review_rounds.begin(tmp_path, ["detector"], "Review behavior", {})
    assert review_rounds.status(tmp_path, record["id"])["snapshot_intact"], (
        "An untouched standalone snapshot over a symlink reads as damaged.")


@pytest.mark.parametrize("occupant", ["listing-file", "plain-file"])
def test_a_project_file_where_the_link_listing_goes_is_kept(project, occupant):
    # Catches writing the link listing over a project file of the same name, or failing
    # the capture when a plain file holds the listing's folder name.
    link_project(project)
    original = b'{"the project": "its own file"}\n'
    if occupant == "listing-file":
        (project / ".review-symlinks").mkdir()
        relative = ".review-symlinks/symlinks.json"
    else:
        relative = ".review-symlinks"
    (project / relative).write_bytes(original)
    try:
        with review_context.snapshot(project, []) as (target, manifest):
            kept = (Path(target) / relative).read_bytes()
            listed = manifest.get(relative)
    except (OSError, store.WorkflowError) as exc:
        pytest.fail(f"Capturing a snapshot failed over the project's own {relative}: {exc!r}")
    assert kept == original, f"The snapshot replaced the project's own {relative}."
    assert listed == hashlib.sha256(original).hexdigest()


def test_a_link_retargeted_just_after_capture_is_recorded_as_captured(project, monkeypatch):
    # Catches reading link targets from the live tree after the snapshot is taken: the
    # round would record the new target while the reader's snapshot shows the old one.
    from contextlib import contextmanager

    declared_link_task(project)
    enter_implementation(project)
    finish_test_task(project, "test-author", {"src/app.py": PLACEHOLDER}, ["src/app.py"])
    original = review.snapshot
    moved = []

    @contextmanager
    def capture_then_retarget(root, required):
        with original(root, required) as captured:
            if not moved:
                retarget(project)
                moved.append(True)
            yield captured

    monkeypatch.setattr(review, "snapshot", capture_then_retarget)
    seen = native_capture(monkeypatch)
    message = checkpoint_outcome(project, reviewer=None)
    assert moved, "The witness seam after snapshot capture never ran."
    if message is not None and "src/launcher.py" in message:
        return  # Refused: the retarget after capture was caught.
    assert seen, f"No reader ran: {message}"
    shown = link_maps([json.loads(data) for path, data in seen[-1]["files"].items() if path.endswith(".json")])
    result = work(project)["rounds"][-1].get("result") or {}
    recorded = link_maps(result.get("snapshot_symlinks", {}))
    assert shown and all(t.endswith("a.py") for t in shown), f"The snapshot does not show the captured link: {shown}"
    assert recorded and all(t.endswith("a.py") for t in recorded), (
        f"The round recorded the link as retargeted after capture, not as the reader saw it: {recorded}")


def test_a_second_equal_content_retarget_before_capture_is_refused(project, monkeypatch):
    # Catches binding only content fingerprints to the snapshot: the diff says b.py while
    # the reader's snapshot points at c.py.
    link_project(project)
    (project / "src/c.py").write_text("CONFIG = 'same content'\n")
    edit_tasks(project, lambda by_id, tasks: by_id["prepare-tests"].update(
        files=["tests/check.py", "src/launcher.py"]))
    enter_implementation(project)
    assert start(project, "prepare-tests", "test-author") is None
    retarget(project)
    returned = mutate(project, handoff.finish_task, "s", "prepare-tests", changed_files=[],
                      checks=[{"argv": CHECK, "exit_code": 1, "evidence": "Release is still missing."}],
                      unresolved=[], outcome="The launcher now points at b.py.")
    assert returned["status"] == "completed"
    original = review.snapshot
    moved = []

    def retarget_then_capture(root, required):
        if not moved:
            (project / "src/launcher.py").unlink()
            os.symlink("c.py", project / "src/launcher.py")
            moved.append(True)
        return original(root, required)

    monkeypatch.setattr(review, "snapshot", retarget_then_capture)
    seen = native_capture(monkeypatch)
    message = checkpoint_outcome(project, reviewer=None)
    assert moved, "The witness seam before snapshot capture never ran."
    assert message is not None and "src/launcher.py" in message, (
        f"A retarget after the comparison reached the reader: {message}")
    assert seen == []


def test_the_implementation_review_baseline_keeps_the_checkpoints_link_target(project, monkeypatch):
    # Catches carrying only content into the implementation review's baseline: an
    # equal-content retarget since the checkpoint is then invisible to the reader.
    from fbk.workflow import close, review_baseline

    link_project(project)
    edit_tasks(project, lambda by_id, tasks: by_id["cancel"].update(files=["src/app.py", "src/launcher.py"]))
    ready_for_checkpoint(project)
    native_capture(monkeypatch)
    assert checkpoint_refusal(project, reviewer=None) is None
    assert start(project, "cancel", "implementer") is None
    (project / "src/app.py").write_text("release()")
    retarget(project)
    returned = mutate(project, handoff.finish_task, "s", "cancel", changed_files=["src/app.py"],
                      checks=[{"argv": CHECK, "exit_code": 0, "evidence": "Release happens."}],
                      unresolved=[], outcome="Cancellation releases its resource.")
    assert returned["status"] == "completed"
    baselines = []

    def reader(snapshot, prompt, config, **kwargs):
        baselines.append(link_targets_in(Path(snapshot) / review_baseline.PREFIX)
                         + link_maps(payload(prompt).get("baseline", payload(prompt))))
        return {"review": {"summary": "Inspected the implementation.", "findings": []}}

    monkeypatch.setattr(review, "claude_review", reader)
    complete_refactor_tasks(project)
    close.close_phase(project, "feature", "implement", "s", reviewer=None)
    assert baselines, "The native implement reader was not asked."
    assert any(t.endswith("a.py") for t in baselines[0]), (
        f"The implementation review's baseline does not carry the checkpoint's link target: {baselines[0]}")


def test_a_verified_return_recorded_before_link_targets_keeps_its_exemption(project):
    # Catches reading a return without link targets as one recording a plain file: an
    # owned, unchanged link then counts as a production change no test task declared.
    from .test_workflow_unlock_rework_reopen import (
        COMMANDS, CORRECTED, RELEASE, UTIL_CHECK, approve_unlock, code_after_checkpoint, finish, rework)

    link_project(project)
    code_after_checkpoint(project, adjust=lambda tasks: tasks["tidy"].update(
        files=["src/util.py", "src/launcher.py"]))
    assert start(project, "tidy", "tidy-worker") is None
    approve_unlock(project, {RELEASE: "pass"}, [COMMANDS[0]])
    (project / "src/util.py").write_text("util()")
    finish(project, "tidy", ["src/util.py"], UTIL_CHECK)
    # As recorded before link targets were kept: neither the baseline nor the return has them.
    with store.transaction(project):
        record = store.load(project, "feature")
        record["writing_tests_baseline"].pop("links", None)
        record["task_runs"]["tidy"]["return"].pop("links", None)
        store.save(project, record)
    _, returned = rework(project, {RELEASE: CORRECTED[RELEASE]}, commands=[COMMANDS[0]])
    assert returned["status"] == "completed", returned
    message = checkpoint_refusal(project)
    assert message is None, f"An unchanged owned link in an earlier verified return was refused: {message}"


def test_a_retry_after_an_equal_content_retarget_reviews_afresh_with_the_new_target(project, monkeypatch):
    # Guard: catches leaving link targets out of the round's identity or the freshness check.
    from .test_workflow_test_checkpoint import record_disposition, suggestion

    declared_link_task(project)
    enter_implementation(project)
    finish_test_task(project, "test-author", {"src/app.py": PLACEHOLDER}, ["src/app.py"])
    finding = suggestion(remedy_kind="test")
    monkeypatch.setattr(review, "claude_review", lambda *a, **k: {
        "review": {"summary": "Inspected the authored tests.", "findings": [dict(finding)]}})
    assert checkpoint_outcome(project, reviewer=None) is not None
    assert refusal_free(record_disposition, project, finding)
    first = (work(project)["rounds"][-1].get("result") or {}).get("investigation_round")
    retarget(project)
    seen = native_capture(monkeypatch)
    checkpoint_outcome(project, reviewer=None)
    assert seen, "The retry reused the earlier review instead of reviewing the retarget."
    round_id = (work(project)["rounds"][-1].get("result") or {}).get("investigation_round")
    assert round_id and round_id != first, "The retry reused the earlier investigation round."
    workspace = project / ".fbk/runtime/review-rounds" / round_id / "sources"
    targets = link_targets_in(workspace)
    assert targets and all(t.endswith("b.py") for t in targets), (
        f"The retry's investigation workspace does not carry the new link target: {targets}")


# Follow-up group B, review round 2


def comparison_lists(prompt):
    """The comparison object in a reader prompt: the dict naming changed tests."""
    found = []

    def walk(value):
        if isinstance(value, dict):
            if "changed_by_test_tasks" in value:
                found.append(value)
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(payload(prompt))
    assert found, "The reader prompt carries no test comparison."
    return found[0]


def test_the_checkpoint_reader_must_read_the_link_listing(project, monkeypatch):
    # Catches making the link listing available without naming it as required reading: a
    # reader can then complete the review having seen only flattened content.
    declared_link_task(project)
    enter_implementation(project)
    finish_test_task(project, "test-author", {"src/app.py": PLACEHOLDER}, ["src/app.py"])
    seen = native_capture(monkeypatch)
    message = checkpoint_outcome(project, reviewer=None)
    assert seen, f"No reader ran: {message}"
    required = required_reading(seen[-1]["prompt"])
    assert review_context.SYMLINKS_FILE in required, (
        f"The link listing {review_context.SYMLINKS_FILE} is not required reading: {required}")


def test_a_test_retargeted_since_the_accepted_checkpoint_is_not_carried_forward(project, monkeypatch):
    # Catches judging "unchanged since the accepted checkpoint" by content alone: a test
    # retargeted between equal files is listed both as changed and as carrying the old red.
    test = project / "tests/check.py"
    content = test.read_bytes()
    (project / "fixtures").mkdir()
    (project / "fixtures/a.py").write_bytes(content)
    (project / "fixtures/b.py").write_bytes(content)
    test.unlink()
    os.symlink("../fixtures/a.py", test)
    ready_for_checkpoint(project)
    assert checkpoint_refusal(project) is None
    make_checkpoint_rerunnable(project)
    test.unlink()
    os.symlink("../fixtures/b.py", test)
    seen = native_capture(monkeypatch)
    message = checkpoint_outcome(project, reviewer=None)
    assert seen, f"No reader ran: {message}"
    lists = comparison_lists(seen[-1]["prompt"])
    changed = lists.get("changed_by_test_tasks", [])
    carried = lists.get("unchanged_since_accepted_checkpoint", [])
    assert "tests/check.py" in changed, f"The retargeted test is not listed as changed: {lists}"
    assert "tests/check.py" not in carried, (
        f"The retargeted test is listed as unchanged since the accepted checkpoint: {lists}")


def test_a_standalone_contributor_may_declare_the_link_listing(tmp_path, monkeypatch):
    # Catches leaving the snapshot's link listing out of a standalone contributor's
    # available files: declaring it as read is refused as outside the snapshot.
    from fbk.workflow import review_contributors, review_rounds

    (tmp_path / "a.py").write_text("x = 1\n")
    os.symlink("a.py", tmp_path / "link.py")
    record = review_rounds.begin(tmp_path, ["reader"], "Review behavior", {})
    offered = []

    def session(root, prompt, config, **kwargs):
        offered.append((Path(root), dict(config.get("_review_available_files", {}))))
        return {"review": {"result": []}, "seconds": 0}

    monkeypatch.setattr(review, "_claude_session", session)
    review_contributors.run(tmp_path, record["id"], ["reader"])
    assert offered, "The contributor was not launched."
    workspace, available = offered[0]
    assert (workspace / review_context.SYMLINKS_FILE).is_file(), "The contributor's copy has no link listing."
    try:
        review_context.validate_context(
            {"status": "complete", "inspected_files": [review_context.SYMLINKS_FILE, "a.py", "link.py"],
             "supporting_files": [], "missing_context": []}, available)
    except store.WorkflowError as exc:
        pytest.fail(f"A contributor declaring the link listing it was given is refused: {exc}")


LINK_COUNT = 2000


def test_an_implementation_review_over_many_links_still_launches(project, monkeypatch):
    # Catches inlining every baseline link target into the reader prompt: a project with
    # many ordinary links outgrows the prompt limit and implement can never close.
    from fbk.workflow import close

    vendor = project / "vendor"
    vendor.mkdir()
    (vendor / "shared_module_with_a_reasonably_descriptive_name.py").write_text("VALUE = 1\n")
    for index in range(LINK_COUNT):
        os.symlink("shared_module_with_a_reasonably_descriptive_name.py",
                   vendor / f"compatibility_alias_for_the_shared_module_number_{index:05d}.py")
    ready_for_checkpoint(project)
    native_capture(monkeypatch)
    assert checkpoint_refusal(project, reviewer=None) is None
    assert start(project, "cancel", "implementer") is None
    (project / "src/app.py").write_text("release()")
    returned = mutate(project, handoff.finish_task, "s", "cancel", changed_files=["src/app.py"],
                      checks=[{"argv": CHECK, "exit_code": 0, "evidence": "Release happens."}],
                      unresolved=[], outcome="Cancellation releases its resource.")
    assert returned["status"] == "completed"
    complete_refactor_tasks(project)
    seen = native_capture(monkeypatch)
    message = refusal_or_none(lambda: close.close_phase(project, "feature", "implement", "s", reviewer=None))
    assert seen, f"The implementation reader never launched over {LINK_COUNT} links: {message}"
    # The session adds its own guidance before refusing a brief over 160,000 characters.
    assert len(seen[-1]["prompt"]) < 150000, (
        f"The implementation brief over {LINK_COUNT} links is {len(seen[-1]['prompt']):,} characters, "
        "past what the reader session accepts.")


def refusal_or_none(action):
    try:
        action()
    except store.WorkflowError as exc:
        return str(exc)
    return None


@pytest.mark.parametrize("change", ["declared", "undeclared"])
def test_a_reset_of_a_verified_retarget_is_judged_against_the_return(project, monkeypatch, change):
    # Catches dropping the link targets a verified return records: a test task's reset of
    # an implementer's equal-content retarget would then be invisible.
    from .test_workflow_unlock_rework_reopen import (
        COMMANDS, CORRECTED, RELEASE, approve_unlock, code_after_checkpoint, finish, rework)

    link_project(project)
    check = [sys.executable, "-c", "import os; assert os.readlink('src/launcher.py') == 'b.py'"]

    def own(tasks):
        tasks["tidy"].update(files=["src/util.py", "src/launcher.py"],
                             check_expectations=[{"argv": check, "exit_code": 0}])
        if change == "declared":
            tasks["prepare-tests"]["files"] = [*tasks["prepare-tests"]["files"], "src/launcher.py"]

    code_after_checkpoint(project, adjust=own)
    assert start(project, "tidy", "tidy-worker") is None
    approve_unlock(project, {RELEASE: "pass"}, [COMMANDS[0]])
    retarget(project)
    finish(project, "tidy", [], check)
    # Back to the baseline's target, after the verified return.
    (project / "src/launcher.py").unlink()
    os.symlink("a.py", project / "src/launcher.py")
    _, returned = rework(project, {RELEASE: CORRECTED[RELEASE]}, commands=[COMMANDS[0]])
    assert returned["status"] == "completed", returned
    seen = native_capture(monkeypatch)
    message = checkpoint_outcome(project, reviewer=None)
    if change == "undeclared":
        assert message is not None and "src/launcher.py" in message, (
            f"An undeclared reset of a verified retarget was not refused: {message}")
        assert seen == []
        return
    assert seen, f"No reader ran: {message}"
    diff = production_diff(seen[-1], "src/launcher.py")
    assert "b.py" in diff and "a.py" in diff, f"The reset is not shown against the returned target: {diff!r}"


def test_the_no_tests_entry_baseline_carries_link_targets(tmp_path):
    # Guard: catches dropping link targets from the writing-tests baseline a no-tests
    # unit's implementation review compares against.
    from fbk.workflow import review_baseline
    from .test_workflow_test_outcomes import implement_entered, review_only_unit

    root = review_only_unit(tmp_path / "p", tests=())
    (root / "src/a.py").write_text("CONFIG = 'same content'\n")
    os.symlink("a.py", root / "src/launcher.py")
    implement_entered(root)
    reader = tmp_path / "reader"
    reader.mkdir()
    provenance = review_baseline.prepare(root, reader, store.load(root, "feature"), "implement", {})
    assert provenance["status"] == "available", provenance
    assert "a.py" in link_maps(provenance), f"The entry baseline does not carry the link target: {provenance}"


def test_a_retained_implementation_acceptance_carries_link_targets(project, monkeypatch):
    # Guard: catches retaining only content when an implementation acceptance is
    # superseded by a reopen, so the next review's baseline loses the old link targets.
    from fbk.workflow import close, review_baseline
    from .test_workflow_lifecycle import observe_phase

    link_project(project)
    ready_for_checkpoint(project)
    native_capture(monkeypatch)
    assert checkpoint_refusal(project, reviewer=None) is None
    assert start(project, "cancel", "implementer") is None
    (project / "src/app.py").write_text("release()")
    returned = mutate(project, handoff.finish_task, "s", "cancel", changed_files=["src/app.py"],
                      checks=[{"argv": CHECK, "exit_code": 0, "evidence": "Release happens."}],
                      unresolved=[], outcome="Cancellation releases its resource.")
    assert returned["status"] == "completed"
    complete_refactor_tasks(project)
    close.close_phase(project, "feature", "implement", "s", reviewer=None)
    observe_phase(project, "implement")
    reason = "Revisit the delivered code."
    mutate(project, engine.approve, "s", "reopen", "implement", reason)
    mutate(project, engine.reopen, "implement", "s", reason)
    record = store.load(project, "feature")
    _, phase, _ = review_baseline.select(record, "implement")
    assert phase == "implement", f"The baseline after the reopen is not the retained acceptance: {phase}"
    reader = project.parent / "retained-reader"
    reader.mkdir()
    provenance = review_baseline.prepare(project, reader, record, "implement", {})
    assert provenance["status"] == "available", provenance
    assert "a.py" in link_maps(provenance), f"The retained acceptance lost the link target: {provenance}"


# Follow-up group B, review round 3


def test_a_repair_reader_is_told_to_read_the_link_listing_it_must_declare(project, monkeypatch):
    # Catches requiring the link listing from a repair reader without naming it in the
    # prompt's required files: a reader following its prompt is rejected.
    from fbk.workflow import repair
    from .test_workflow_repair_clears_locks import SPEC_REPAIR, locked

    link_project(project)
    locked(project)
    prompts = []

    def reader(snapshot, prompt, config, **kwargs):
        prompts.append((prompt, list(config.get("_review_required_files", []))))
        return {"review": {"status": "equivalent", "evidence": "The quoted source settles it."}}

    monkeypatch.setattr(review, "claude_review", reader)
    repair.apply(project, "feature", "s", dict(SPEC_REPAIR))
    assert prompts, "The repair reader was not asked."
    prompt, enforced = prompts[-1]
    told = required_reading(prompt)
    assert review_context.SYMLINKS_FILE in enforced, "The setup no longer requires the link listing."
    assert set(enforced) <= set(told), (
        f"The repair reader must declare {sorted(set(enforced) - set(told))}, which its prompt never names.")


def test_a_declared_retarget_of_a_region_bearing_file_marks_its_test_changed(project, monkeypatch):
    # Catches letting a test region's mode exemption hide a link retarget: the region's
    # tests can resolve fixtures relative to the new target, so they are not untouched.
    region = "src/mod.py"
    code = "def cancel():\n    return True\n# --- tests ---\nassert cancel() is True\n"
    (project / "shared").mkdir()
    (project / "shared/mod_a.py").write_text(code)
    (project / "shared/mod_b.py").write_text(code)
    os.symlink("../shared/mod_a.py", project / region)
    edit_scope(project, test_regions=[{"files": [region], "start": r"^# --- tests ---$"}])
    edit_tasks(project, lambda by_id, tasks: by_id["prepare-tests"].update(files=["tests/check.py", region]))
    enter_implementation(project)
    assert start(project, "prepare-tests", "test-author") is None
    (project / region).unlink()
    os.symlink("../shared/mod_b.py", project / region)
    returned = mutate(project, handoff.finish_task, "s", "prepare-tests", changed_files=[],
                      checks=[{"argv": CHECK, "exit_code": 1, "evidence": "Release is still missing."}],
                      unresolved=[], outcome="The module now points at mod_b.py.")
    assert returned["status"] == "completed"
    seen = native_capture(monkeypatch)
    message = checkpoint_outcome(project, reviewer=None)
    assert seen, f"No reader ran: {message}"
    lists = comparison_lists(seen[-1]["prompt"])
    assert region in lists.get("changed_by_test_tasks", []) and region not in lists.get("untouched", []), (
        f"The retargeted region-bearing file's tests are not marked changed: {lists}")


def cached_review_after_a_disposition(root, monkeypatch):
    """A checkpoint review waiting on a disposition, the disposition recorded, and the
    cached result's link targets removed, as recorded before link targets were kept."""
    from .test_workflow_test_checkpoint import record_disposition, suggestion

    enter_implementation(root)
    finish_test_task(root, "test-author", {"src/app.py": PLACEHOLDER}, ["src/app.py"])
    finding = suggestion(remedy_kind="test")
    monkeypatch.setattr(review, "claude_review", lambda *a, **k: {
        "review": {"summary": "Inspected the authored tests.", "findings": [dict(finding)]}})
    assert checkpoint_outcome(root, reviewer=None) is not None
    assert refusal_free(record_disposition, root, finding)
    with store.transaction(root):
        record = store.load(root, "feature")
        result = record["phases"][CK]["rounds"][-1]["result"]
        result.pop("snapshot_symlinks", None)
        store.save(root, record)


def test_a_cached_review_without_link_targets_is_stale_after_a_retarget(project, monkeypatch):
    # Catches reading a cached review with no recorded link targets as matching the live
    # ones: an equal-content retarget during the wait then reuses the old verdict.
    declared_link_task(project)
    cached_review_after_a_disposition(project, monkeypatch)
    retarget(project)
    seen = native_capture(monkeypatch)
    checkpoint_outcome(project, reviewer=None)
    assert seen, "A cached review without link targets was reused after the link was retargeted."


def test_a_cached_review_without_link_targets_stays_fresh_when_there_are_no_links(project, monkeypatch):
    # Guard: an upgrade must not invalidate every cached review; with no links in the
    # project, a cached review recorded before link targets were kept is still reused.
    declared_production_task(project)
    cached_review_after_a_disposition(project, monkeypatch)
    seen = native_capture(monkeypatch)
    message = checkpoint_outcome(project, reviewer=None)
    assert seen == [], f"A cached review in a project with no links was not reused: {message}"
    assert message is None and work(project)["evidence"], f"The reused review did not accept the checkpoint: {message}"


def test_a_relaunched_test_task_after_a_retarget_carries_no_earlier_red(project):
    # Guard: catches carrying the accepted checkpoint's red forward for a test retargeted
    # between equal files since; the task's now-passing check must not complete it.
    from .test_workflow_unlock_rework_reopen import finish_unchanged_or_changed, keys, reopened_with_release_built

    test = project / "tests/check.py"
    content = test.read_bytes()
    (project / "fixtures").mkdir()
    (project / "fixtures/a.py").write_bytes(content)
    (project / "fixtures/b.py").write_bytes(content)
    test.unlink()
    os.symlink("../fixtures/a.py", test)
    reopened_with_release_built(project)
    test.unlink()
    os.symlink("../fixtures/b.py", test)
    returned = finish_unchanged_or_changed(project, {})
    assert not any(isinstance(k, str) and "carried" in k.lower() for k in keys(returned)), (
        f"The retargeted test task carried the earlier red forward: {returned}")
    assert returned["status"] != "completed", f"The retargeted test task completed on a passing check: {returned}"


# Follow-up group B, review round 4


@pytest.mark.xfail(strict=True, reason="Follow-up: a standalone review round does not notice an equal-content link "
                   "retarget after capture, so contributors resume against the old link listing.")
def test_a_standalone_round_notices_an_equal_content_retarget_after_capture(tmp_path):
    from fbk.workflow import review_rounds

    (tmp_path / "a.py").write_text("x = 1\n")
    (tmp_path / "b.py").write_text("x = 1\n")
    os.symlink("a.py", tmp_path / "link.py")
    record = review_rounds.begin(tmp_path, ["reader"], "Review behavior", {})
    (tmp_path / "link.py").unlink()
    os.symlink("b.py", tmp_path / "link.py")
    status = review_rounds.status(tmp_path, record["id"])
    assert status["historical"] or not status["snapshot_intact"], (
        "A standalone round did not notice its captured link was retargeted.")


REGION_MODULE = "src/mod.py"
REGION_BODY = "def cancel():\n    return True\n# --- tests ---\nassert cancel() is True\n"


def region_type_change_is_marked(root, monkeypatch, before, after, legacy=False):
    """A region-bearing file the test task declares changes between a regular file and a
    link with the same content; its tests must be listed as changed."""
    (root / "shared").mkdir()
    (root / "shared/mod_a.py").write_text(REGION_BODY)
    before(root)
    edit_scope(root, test_regions=[{"files": [REGION_MODULE], "start": r"^# --- tests ---$"}])
    edit_tasks(root, lambda by_id, tasks: by_id["prepare-tests"].update(files=["tests/check.py", REGION_MODULE]))
    enter_implementation(root)
    if legacy:
        # As recorded before link targets were kept: the baseline's mode alone names the link.
        with store.transaction(root):
            record = store.load(root, "feature")
            record["writing_tests_baseline"].pop("links", None)
            store.save(root, record)
        assert store.load(root, "feature")["writing_tests_baseline"]["modes"][REGION_MODULE] == "120000"
    assert start(root, "prepare-tests", "test-author") is None
    (root / REGION_MODULE).unlink()
    after(root)
    returned = mutate(root, handoff.finish_task, "s", "prepare-tests", changed_files=[],
                      checks=[{"argv": CHECK, "exit_code": 1, "evidence": "Release is still missing."}],
                      unresolved=[], outcome="The module changed type, keeping its content.")
    assert returned["status"] == "completed"
    seen = native_capture(monkeypatch)
    message = checkpoint_outcome(root, reviewer=None)
    assert seen, f"No reader ran: {message}"
    lists = comparison_lists(seen[-1]["prompt"])
    changed, untouched = lists.get("changed_by_test_tasks", []), lists.get("untouched", [])
    assert REGION_MODULE in changed and REGION_MODULE not in untouched, (
        f"The region-bearing file's type change left its tests untouched: {lists}")


def _regular_region(root):
    (root / REGION_MODULE).write_text(REGION_BODY)


def _linked_region(root):
    os.symlink("../shared/mod_a.py", root / REGION_MODULE)


def test_a_region_bearing_file_turned_into_an_equal_content_link_marks_its_test_changed(project, monkeypatch):
    # Guard: catches judging a region's tests by link targets alone, which a regular file
    # turned into a link never records.
    region_type_change_is_marked(project, monkeypatch, _regular_region, _linked_region)


def test_a_legacy_baseline_link_turned_into_a_regular_file_marks_its_test_changed(project, monkeypatch):
    # Guard: catches ignoring the baseline's recorded link mode when it predates link targets.
    region_type_change_is_marked(project, monkeypatch, _linked_region, _regular_region, legacy=True)
