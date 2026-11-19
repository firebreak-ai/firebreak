"""Tests that share a file with code, as end-of-file test regions (build step 6, plan decision 6).

Some languages keep unit tests at the end of the source file they test: Rust's
``#[cfg(test)] mod tests``, a C ``#ifdef UNIT_TEST`` block. The scope may declare a test region
for matching files: a start-line expression, with the region running to the end of the file. A
region-bearing file is two things at once: its region is a scoped test, and everything above
the region is a production file. Every rule from steps 1-5 applies to each part as it already
applies to that kind of file: write hook by stage, ownership and plan validation, baseline and
checkpoint comparison, checkpoint revision, lock, saved copies, boundary checks, violations,
and restore.

Lead rulings these tests rely on (the plan leaves them open):

1. **Declaration.** ``scope.json`` gains an optional ``test_regions`` list of objects
   ``{"files": [<globs>], "start": "<regular expression>"}``. The globs follow the confinement
   and control-record rules of the other scope fields. A file a region entry matches must also
   be matched by ``sources`` and must not be matched by ``tests``; either conflict is refused at
   scope load with a message naming the file or pattern. A scope may have ``test_regions`` and
   no ``tests``.
2. **Finding the region.** Text matching only. The region starts at the first line where the
   expression matches (``re.search`` on the line without its line ending) and runs to the end
   of the file. A matching file with no start line has an empty region; adding a start line is
   a change to the region. An invalid expression is refused at scope load.
3. **Write hook after-edit computation.** Write: the after-edit file is the new content. Edit:
   the replacement applied exactly as the tool would, including ``replace_all``; when
   ``old_string`` is absent, or not unique without ``replace_all``, when the file cannot be
   read, or when the tool's result cannot be computed (NotebookEdit), the write is refused with
   a message saying the after-edit file cannot be computed. The before and after region and
   code above are compared, and the stage rules apply to each part that changed.
4. **Restore.** ``restore-locked-tests`` on a region-bearing file replaces the current region
   with the copy's region and keeps the current code above byte for byte; when the current
   file has no start line, the copy's region is appended.
5. **Snapshots and diffs** show the region-bearing file whole. Fingerprints and lock entries
   record the region separately from the file, so writing code above the region never makes
   the checkpoint stale or trips a boundary check.
6. **Malformed entries.** A region entry that is not an object with a ``files`` list of globs
   and a string ``start``, or that carries other keys, is refused at scope load.
7. **Overlapping entries.** A file matched by two region entries is refused at scope load,
   with a message naming the file.
8. **Undeclared region changes.** A region change in a file no test task declares is a
   changed test, as a whole test file changed through the shell is, not an undeclared
   production change.

Rulings added after review round 1:

9. **Every plausible Edit result.** The write hook refuses an Edit when any result the Edit
   tool could plausibly produce changes the region: the plain replacement, the tool's deletion
   of the trailing newline when ``new_string`` is empty, and its line-ending normalization (read
   normalized to LF, written back in the file's detected convention).
10. **Unreadable restore target.** Restore on an existing region-bearing file that cannot be
    read refuses and leaves the file unchanged.
11. **Absent and empty regions are equivalent.** A new production file under a region glob
    with no start line leaves the checkpoint current and passes the lock check; a later
    non-empty region in it is still detected.
12. **Empty start expression.** ``start: ""`` is a valid expression whose region starts at line
    one; an unchanged file is not a changed test.
13. **Declared new paths in conflict checks.** A ``creates`` path matched by both a region entry
    and a whole-file test pattern, or by two region entries, is refused at scope load naming
    the path.
14. **Restore that cannot reproduce the lock.** When composing the current code above with the
    copy's region would not reproduce the locked region, restore refuses and leaves the file
    untouched.

Rulings added after review round 2:

15. **Encodings the hook does not model.** The write hook refuses an Edit or Write to a
    region-bearing file as "cannot be computed" when the current file has mixed line endings
    (both CRLF and bare LF) or starts with a UTF-8 byte-order mark; the message names the
    remedy (convert the file to one line ending, no byte-order mark). This replaces exact
    modelling of the Edit tool's line-ending detection and the Write tool's byte-order-mark
    preservation. Single-convention files without a byte-order mark keep ruling 9.
16. **A deleted file with an empty region.** A production file under a region glob that never
    had a start line may be deleted by an implementation task that owns it: task finish and
    implementation close do not treat it as a lock violation or missing evidence. A missing
    file whose locked region was non-empty is still a violation.
17. **Restore keeps the current mode.** A region-bearing file's executable bit belongs to the
    code above, so restore keeps the current file's mode after a valid mode change.

Shapes the tests assume, leaving names to the implementer where they can:

- A region is named by its file's path wherever Firebreak names tests: in a lock-violation
  refusal and event, in ``restore-locked-tests --tests``, in ``approve unlock-test --tests``,
  and in the checkpoint reviewer's changed and untouched lists (an entry containing the path).
- A lock entry's key contains the file's path; its value is not the whole file's fingerprint.
- The saved copy of a region-bearing file sits at ``copy_path(<locked-tests folder>, <path>)``.

Which tests are red and which are guards. Every test that declares ``test_regions`` is red
today at the shared setup, which asserts that Firebreak accepts the declaration (scope load
refuses the unknown field). Each one's own assertion targets a specific wrong implementation,
named in its comment. Tests marked **guard after regions load** pin behavior that the current
code already has for production files and that a plausible wrong region implementation (for
example, locking the whole region-bearing file) would break; they pass once the declaration
loads unless that wrong implementation is built. The guide checks are red on their own
assertions. No test here is a guard today.
"""

import hashlib
import re
import sys
from pathlib import Path

import pytest

from fbk.workflow import close, engine, evidence, handoff, hooks, review, store, test_preparation
from .test_workflow_checkpoint_review_inputs import comparison, native_capture
from .test_workflow_implement_stages import (
    CHECK,
    REFS,
    edit_scope,
    edit_tasks,
    refusal,
    stage,
    start,
    unlock,
)
from .test_workflow_lifecycle import (
    accept,
    approve_unlock,
    clean_review,
    enter_implementation,
    prepare_implementation,
    project as workflow_project,
    run_test_tasks,
)
from .test_workflow_lock_enforcement import (
    ROUTES,
    finish_refusal,
    restore,
    restore_refusal,
    violations,
    with_tidy_task,
)
from .test_workflow_test_checkpoint import checkpoint_refusal
from .test_workflow_unlock_rework_reopen import carried, finish, keys, reenter_implement, reopen
from .refactor_plan import complete_refactor_tasks

project = workflow_project

UNIT = ".fbk/feature"
ROOT_DOCS = Path(__file__).resolve().parents[3]

# A Rust-shaped file. The start expression ends in $ so a CRLF file tests "the line without
# its line ending"; it begins with ^ so it is the conventional marker.
RUST_START = r"^#\[cfg\(test\)\]$"
# A C-shaped file. The expression has no ^, so only re.search (not re.match) finds "#ifdef".
C_START = r"ifdef\s+UNIT_TEST"

LIB, TIMER, EMPTY, WIRE, TWICE = "src/lib.rs", "src/timer.c", "src/empty.rs", "src/wire.rs", "src/twice.rs"

LIB_CODE = (
    "pub fn release() -> bool {\n"
    "    false\n"
    "}\n"
    "\n"
    "// helper: not built\n"
    "// helper: not built\n"
    "\n"
)
LIB_BUILT = LIB_CODE.replace("    false\n", "    true\n")
LIB_EMPTY_REGION = "#[cfg(test)]\nmod tests {\n}\n"
LIB_REGION = (
    "#[cfg(test)]\n"
    "mod tests {\n"
    "    use super::*;\n"
    "\n"
    "    #[test]\n"
    "    fn release_reports_success() {\n"
    "        assert!(release());\n"
    "    }\n"
    "}\n"
)
TIMER_CODE = "int timer_expired(int now, int deadline) {\n    return now >= deadline;\n}\n\n"
TIMER_REGION = (
    "#ifdef UNIT_TEST\n"
    "#include <assert.h>\n"
    "int main(void) {\n"
    "    assert(timer_expired(5, 3));\n"
    "    return 0;\n"
    "}\n"
    "#endif\n"
)
EMPTY_CODE = "pub fn helper() -> u32 {\n    1\n}\n"
WIRE_CODE = "pub fn wire() -> u8 {\r\n    0\r\n}\r\n\r\n"
WIRE_REGION = "#[cfg(test)]\r\nmod tests {\r\n    #[test]\r\n    fn wired() { assert_eq!(super::wire(), 1); }\r\n}\r\n"
TWICE_CODE = "pub fn twice() -> u8 {\n    2\n}\n\n"
TWICE_REGION = (
    "#[cfg(test)]\n"
    "mod first {\n"
    "    #[test]\n"
    "    fn doubles() { assert_eq!(super::twice(), 2); }\n"
    "}\n"
    "\n"
    "#[cfg(test)]\n"
    "mod second {\n"
    "}\n"
)

# A stand-in for `cargo test`: fails on an assertion until release() reports success.
RUST_CHECK = [sys.executable, "-c", (
    "from pathlib import Path\n"
    "code, marker, region = Path('src/lib.rs').read_text().partition('#[cfg(test)]')\n"
    "assert 'assert!(release())' in region, 'the region test is missing'\n"
    "assert 'true' in code, 'release() does not report success'\n"
)]

REGIONS = [{"files": ["src/*.rs"], "start": RUST_START}, {"files": ["src/*.c"], "start": C_START}]
SHELL_REGION = LIB_REGION.replace("assert!(release());", "assert!(true); // shell edit")


# Helpers


def established(action, *args, **kwargs):
    """Run a setup step that must succeed once test regions are declared."""
    try:
        return action(*args, **kwargs)
    except store.WorkflowError as exc:
        raise AssertionError(f"Firebreak refused a unit whose scope declares test regions: {exc}") from None


def write_files(root, files):
    for path, text in files.items():
        (root / path).write_bytes(text.encode())


def declare_regions(root, *, tests=("tests",), regions=None, checks=None):
    """Declare the region-bearing files: Rust files with a #[cfg(test)] region and a C file
    with an #ifdef UNIT_TEST region, all in src, owned by both a test task (src/lib.rs only)
    and an implementation task (every one)."""
    write_files(root, {
        LIB: LIB_CODE + LIB_EMPTY_REGION,
        TIMER: TIMER_CODE + TIMER_REGION,
        EMPTY: EMPTY_CODE,
        WIRE: WIRE_CODE + WIRE_REGION,
        TWICE: TWICE_CODE + TWICE_REGION,
    })
    path = root / UNIT / "scope.json"
    scope = store.read_json(path)
    scope.update(sources=["src"], tests=list(tests), test_regions=regions if regions is not None else REGIONS,
                 checks=checks if checks is not None else [CHECK, RUST_CHECK])
    store.atomic_json(path, scope)

    def add(by_id, tasks):
        tasks.append({
            "id": "region-tests", "stage": "tests",
            "description": "Write the release test in the Rust file's test region.",
            "files": [LIB], "depends_on": [], "acceptance_refs": REFS,
            "verification": "A release() that keeps returning false fails the region test.",
            "check_expectations": [{"argv": RUST_CHECK, "exit_code": "nonzero"}],
        })
        tasks.append({
            "id": "release", "stage": "implementation",
            "description": "Make release() report success.",
            "files": [LIB, TIMER, EMPTY, WIRE, TWICE], "depends_on": [], "acceptance_refs": REFS,
            "verification": "The locked region test passes unchanged.",
            "check_expectations": [{"argv": RUST_CHECK, "exit_code": 0}],
        })

    edit_tasks(root, add)


def write_region_test(root):
    (root / LIB).write_text(LIB_CODE + LIB_REGION)
    return [LIB]


def regions_unit(root):
    declare_regions(root)
    return root


def prepared(root):
    """Writing code: the region test is written, the checkpoint has locked it."""
    established(prepare_implementation, root, {"region-tests": write_region_test})
    return root


def writing_tests(root):
    established(enter_implementation, root)
    return root


def hook(root, worker, tool, path, **fields):
    key = "notebook_path" if tool == "NotebookEdit" else "file_path"
    return hooks.handle(root, {
        "hook_event_name": "PreToolUse", "tool_name": tool, "session_id": "s", "agent_id": worker,
        "tool_input": {key: str(root / path), **fields},
    })


def reason(result):
    """The hook's refusal reason, or None when the write is allowed."""
    output = result.get("hookSpecificOutput", {})
    return output.get("permissionDecisionReason") if output.get("permissionDecision") == "deny" else None


def write(root, worker, path, content):
    return reason(hook(root, worker, "Write", path, content=content))


def edit(root, worker, path, old, new, replace_all=False):
    return reason(hook(root, worker, "Edit", path, old_string=old, new_string=new, replace_all=replace_all))


def implementer(root):
    assert start(root, "release", "implementer") is None, "The implementation task should start in writing code."
    return "implementer"


def says_cannot_compute(message):
    return message is not None and "comput" in message.lower()


def lock_keys(root, path):
    return [key for key in store.load(root, "feature")["locks"] if path in key]


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def region_of(text, start):
    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if re.search(start, line.rstrip("\r\n")):
            return "".join(lines[index:])
    return ""


def implemented(root):
    """The implementation worker writes release() above the region and finishes."""
    worker = implementer(root)
    assert write(root, worker, LIB, LIB_BUILT + LIB_REGION) is None
    (root / LIB).write_text(LIB_BUILT + LIB_REGION)
    return finish(root, "release", [LIB], RUST_CHECK)


# Declaration and scope load


def test_a_scope_declaring_test_regions_loads(project):
    declare_regions(project)
    established(evidence.scope, project, "feature")


@pytest.mark.parametrize("change, named", [
    ({"sources": ["lib"]}, ("src/",)),
    ({"tests": ["tests", "src/lib.rs"]}, ("src/lib.rs", "src/*.rs")),
])
def test_a_region_file_outside_sources_or_inside_the_test_patterns_is_refused(project, change, named):
    # Catches accepting a region-bearing file that is not a production file, or that is also a
    # whole-file test. Red: the valid declaration is accepted first.
    declare_regions(project)
    established(evidence.scope, project, "feature")
    (project / "lib").mkdir(exist_ok=True)
    edit_scope(project, **change)
    message = refusal(evidence.scope, project, "feature")
    assert message is not None, f"Scope load accepted a region file with {change}."
    assert any(name in message for name in named), f"The refusal does not name the file or pattern {named}: {message}"


@pytest.mark.parametrize("start_expression", ["^#[cfg(test", "(unclosed", "[a-"])
def test_an_invalid_start_expression_is_refused_at_scope_load(project, start_expression):
    declare_regions(project)
    established(evidence.scope, project, "feature")
    edit_scope(project, test_regions=[{"files": ["src/*.rs"], "start": start_expression}])
    assert refusal(evidence.scope, project, "feature") is not None, (
        f"Scope load accepted the invalid start expression {start_expression!r}.")


@pytest.mark.parametrize("files", [[".fbk/feature/*.rs"], [".claude/*.rs"], ["../outside/*.rs"]])
def test_region_globs_follow_the_confinement_and_control_record_rules(project, files):
    declare_regions(project)
    established(evidence.scope, project, "feature")
    edit_scope(project, test_regions=[*REGIONS, {"files": files, "start": RUST_START}])
    assert refusal(evidence.scope, project, "feature") is not None, f"Scope load accepted region files {files}."


@pytest.mark.parametrize("entry", [
    "src/*.rs",
    {"files": "src/*.rs", "start": RUST_START},
    {"files": ["src/*.rs"]},
    {"start": RUST_START},
    {"files": ["src/*.rs"], "start": 3},
    {"files": ["src/*.rs"], "start": RUST_START, "end": "^}$"},
])
def test_a_malformed_region_entry_is_refused(project, entry):
    # Catches loading an entry that is not the ruled {"files": [<globs>], "start": "<expression>"}.
    declare_regions(project)
    established(evidence.scope, project, "feature")
    edit_scope(project, test_regions=[entry])
    assert refusal(evidence.scope, project, "feature") is not None, f"Scope load accepted the region entry {entry!r}."


def test_a_file_matched_by_two_region_entries_is_refused(project):
    # Catches silently picking one entry's start expression for a file two entries match.
    declare_regions(project)
    established(evidence.scope, project, "feature")
    edit_scope(project, test_regions=[*REGIONS, {"files": ["src/lib.rs"], "start": r"^mod tests"}])
    message = refusal(evidence.scope, project, "feature")
    assert message is not None, "Scope load accepted a file matched by two region entries."
    assert LIB in message, f"The refusal does not name the file: {message}"


def test_a_regions_only_scope_runs_through_the_checkpoint_and_implementation_close(project):
    # Catches requiring whole-file test patterns: feature scope structure, the lock's "no tests
    # match" refusal, and implementation close's test-set comparison all count regions as tests.
    declare_regions(project, tests=(), checks=[RUST_CHECK])
    edit_tasks(project, lambda by_id, tasks: tasks.__setitem__(
        slice(None), [t for t in tasks if t["id"] not in {"prepare-tests", "cancel"}]))
    prepared(project)
    assert lock_keys(project, LIB), "The checkpoint did not lock the region of src/lib.rs."
    implemented(project)
    complete_refactor_tasks(project)
    established(close.close_phase, project, "feature", "implement", "s", reviewer=clean_review)


# Ownership and plan validation


def test_a_region_bearing_file_owned_by_a_test_task_and_an_implementation_task_is_accepted(project):
    # Catches treating the region-bearing file as a scoped test, which plan validation refuses
    # to an implementation task.
    declare_regions(project)
    established(accept, project, "intent")
    established(accept, project, "spec")
    message = refusal(accept, project, "breakdown")
    assert message is None, f"Breakdown close refused a region-bearing file owned by both stages: {message}"


# Finding the region and the write hook in writing code


@pytest.mark.parametrize("path, old, new", [
    (LIB, "    false\n", "    true\n"),
    (TIMER, "return now >= deadline;", "return now > deadline;"),
    (WIRE, "    0\r\n", "    1\r\n"),
])
def test_an_implementation_edit_above_the_region_is_allowed(project, path, old, new):
    # Guard after regions load: catches locking or refusing the whole region-bearing file.
    regions_unit(project)
    prepared(project)
    worker = implementer(project)
    assert edit(project, worker, path, old, new) is None, f"An edit above the region of {path} was refused."
    text = (project / path).read_bytes().decode()
    assert write(project, worker, path, text.replace(old, new)) is None


@pytest.mark.parametrize("path, old, new", [
    (LIB, "assert!(release());", "assert!(true);"),
    # C-shaped region, found by re.search: re.match would find no region.
    (TIMER, "assert(timer_expired(5, 3));", "assert(1);"),
    # CRLF file: the expression ends in $, so the line is matched without its line ending.
    (WIRE, "assert_eq!(super::wire(), 1);", "assert!(true);"),
    # The region starts at the first matching line, not the last.
    (TWICE, "assert_eq!(super::twice(), 2);", "assert!(true);"),
])
def test_an_implementation_edit_inside_the_region_is_refused(project, path, old, new):
    # Catches a hook that never computes the after-edit file, finds the region with re.match,
    # keeps the line ending when matching, or starts at the last matching line.
    regions_unit(project)
    prepared(project)
    worker = implementer(project)
    assert edit(project, worker, path, old, new) is not None, f"An implementation edit inside the region of {path} was allowed."
    text = (project / path).read_bytes().decode()
    assert write(project, worker, path, text.replace(old, new)) is not None, (
        f"An implementation Write changing the region of {path} was allowed.")


def test_inserting_a_start_line_above_the_region_changes_the_region(project):
    # Catches comparing the region by its old line range instead of recomputing it from the
    # after-edit file: the region now starts at the inserted line.
    regions_unit(project)
    prepared(project)
    worker = implementer(project)
    message = edit(project, worker, LIB, "pub fn release() -> bool {",
                   "#[cfg(test)]\nfn probe() {}\n\npub fn release() -> bool {")
    assert message is not None, "An edit that moves the region's start line above was allowed."


def test_replace_all_reaching_into_the_region_is_refused(project):
    # Catches applying only the first occurrence: "release" appears above and inside the region.
    regions_unit(project)
    prepared(project)
    worker = implementer(project)
    assert edit(project, worker, LIB, "release", "free", replace_all=True) is not None, (
        "A replace_all edit that changes the region was allowed.")


def test_replace_all_confined_above_the_region_is_allowed(project):
    # Guard after regions load: catches refusing every replace_all, or treating its repeated
    # occurrences as ambiguous.
    regions_unit(project)
    prepared(project)
    worker = implementer(project)
    assert edit(project, worker, LIB, "not built", "pending", replace_all=True) is None


@pytest.mark.parametrize("old, why", [
    ("no such text", "absent"),
    ("release", "not unique without replace_all"),
])
def test_an_edit_whose_result_cannot_be_computed_is_refused(project, old, why):
    # Catches guessing the result: an absent old_string, or one that is ambiguous without
    # replace_all, leaves the after-edit file unknown.
    regions_unit(project)
    prepared(project)
    worker = implementer(project)
    message = edit(project, worker, LIB, old, "x")
    assert says_cannot_compute(message), f"An edit whose old_string is {why} was not refused as uncomputable: {message}"


def test_a_notebook_edit_of_a_region_bearing_file_is_refused(project):
    regions_unit(project)
    prepared(project)
    worker = implementer(project)
    message = reason(hook(project, worker, "NotebookEdit", LIB, new_source="x", cell_id="c1"))
    assert says_cannot_compute(message), f"A NotebookEdit of a region-bearing file was not refused as uncomputable: {message}"


def test_an_edit_of_an_unreadable_region_bearing_file_is_refused(project):
    regions_unit(project)
    prepared(project)
    worker = implementer(project)
    target = project / LIB
    target.chmod(0o000)
    try:
        message = edit(project, worker, LIB, "    false\n", "    true\n")
    finally:
        target.chmod(0o644)
    assert says_cannot_compute(message), f"An edit of an unreadable region-bearing file was not refused: {message}"


def test_a_file_with_no_start_line_has_an_empty_region_and_adding_one_is_a_region_change(project):
    # Catches treating a file without a start line as having no region to protect.
    regions_unit(project)
    prepared(project)
    worker = implementer(project)
    assert write(project, worker, EMPTY, EMPTY_CODE.replace("1", "2")) is None, (
        "An edit of the code in a file with an empty region was refused.")
    message = write(project, worker, EMPTY, EMPTY_CODE + "\n#[cfg(test)]\nmod tests {}\n")
    assert message is not None, "Adding a start line to a file with an empty region was allowed in writing code."


# The write hook in writing tests


def test_a_test_worker_writes_the_region_and_code_above_of_its_declared_file(project):
    # Guard after regions load: catches refusing a test task its declared region-bearing file.
    regions_unit(project)
    writing_tests(project)
    assert start(project, "region-tests", "test-author") is None
    assert write(project, "test-author", LIB, LIB_CODE + LIB_REGION) is None
    assert edit(project, "test-author", LIB, "// helper: not built\n// helper", "pub fn reset() {}\n// helper") is None


def test_a_test_worker_changing_code_above_in_a_file_it_did_not_declare_is_refused(project):
    # Guard after regions load: src/timer.c is region-bearing but region-tests declares only src/lib.rs.
    regions_unit(project)
    writing_tests(project)
    assert start(project, "region-tests", "test-author") is None
    assert edit(project, "test-author", TIMER, "return now >= deadline;", "return 1;") is not None
    assert edit(project, "test-author", TIMER, "assert(timer_expired(5, 3));", "assert(1);") is not None


def test_a_running_implementation_worker_during_an_unlock_cannot_change_a_region(project):
    # Catches applying "implementation workers never write tests" to whole test files only.
    regions_unit(project)
    prepared(project)
    worker = implementer(project)
    unlock(project)  # unlocks tests/check.py; the unit is writing tests again
    assert stage(project) == "writing-tests"
    assert edit(project, worker, LIB, "    false\n", "    true\n") is None, (
        "A running implementation worker lost its production ownership above the region during an unlock.")
    assert edit(project, worker, LIB, "assert!(release());", "assert!(true);") is not None, (
        "A running implementation worker changed a region during an unlock.")


# Baseline and checkpoint comparison


def test_a_region_change_is_a_changed_test_and_the_reviewer_sees_the_file_whole(project, monkeypatch):
    # Catches comparing the region-bearing file only as production: the region change must be
    # a changed test, the untouched C region an untouched test, and the snapshot holds the file whole.
    regions_unit(project)
    writing_tests(project)
    run_test_tasks(project, {"region-tests": write_region_test})
    seen = native_capture(monkeypatch)
    assert checkpoint_refusal(project, reviewer=None) is None
    changed, untouched = comparison(seen[-1]["prompt"])
    assert any(LIB in str(path) for path in changed), f"The region change is not a changed test: {changed}"
    assert any(TIMER in str(path) for path in untouched), f"The untouched C region is not an untouched test: {untouched}"
    assert seen[-1]["files"].get(LIB) == (project / LIB).read_bytes(), (
        "The reviewer's snapshot does not hold the region-bearing file whole.")


def test_a_region_only_change_is_not_shown_as_a_production_change(project):
    # Catches presenting a region edit to the reviewer as a test task's production diff.
    regions_unit(project)
    writing_tests(project)
    run_test_tasks(project, {"region-tests": write_region_test})
    record = store.load(project, "feature")
    result = test_preparation.baseline_comparison(project, record, diffs=True)
    assert LIB not in result["production_diffs"], "A change confined to the region was shown as a production change."
    assert any(LIB in path for path in result["changed_by_test_tasks"]), result["changed_by_test_tasks"]


def test_a_declared_change_above_the_region_reaches_the_reviewer_as_a_production_diff(project, monkeypatch):
    # Catches folding the whole region-bearing file into the test side, hiding a placeholder
    # change above the region from the production diffs.
    regions_unit(project)
    writing_tests(project)

    def placeholder_and_test(root):
        (root / LIB).write_text(LIB_CODE.replace("// helper: not built\n", "pub fn reset() {}\n", 1) + LIB_REGION)
        return [LIB]

    run_test_tasks(project, {"region-tests": placeholder_and_test})
    result = test_preparation.baseline_comparison(project, store.load(project, "feature"), diffs=True)
    diff = result["production_diffs"].get(LIB, "")
    assert "+pub fn reset() {}" in diff, f"The change above the region is not shown as a production diff: {diff!r}"
    assert "+        assert!(release());" not in diff, (
        "The production diff presents the region's new test as production code.")


def test_an_undeclared_change_above_a_region_is_refused_at_the_checkpoint(project):
    # Guard after regions load: catches treating the whole region-bearing file as a test, which
    # would let code above change with no test task declaring it.
    regions_unit(project)
    writing_tests(project)
    run_test_tasks(project, {"region-tests": write_region_test})
    (project / TIMER).write_text(TIMER_CODE.replace(">=", ">") + TIMER_REGION)
    message = checkpoint_refusal(project)
    assert message is not None and TIMER in message, f"An undeclared change above a region passed the checkpoint: {message}"


def test_a_region_change_in_a_file_no_test_task_declares_is_a_changed_test_not_undeclared_production(project, monkeypatch):
    # Catches refusing a region change as an undeclared production change; a changed region is
    # a changed test, as a changed whole test file is.
    regions_unit(project)
    writing_tests(project)
    run_test_tasks(project, {"region-tests": write_region_test})
    (project / TIMER).write_text(TIMER_CODE + TIMER_REGION.replace("5, 3", "6, 3"))
    seen = native_capture(monkeypatch)
    message = checkpoint_refusal(project, reviewer=None)
    assert message is None, f"A changed region was refused as an undeclared production change: {message}"
    changed, _ = comparison(seen[-1]["prompt"])
    assert any(TIMER in str(path) for path in changed), changed


# Lock, checkpoint revision, saved copies


def test_the_lock_and_copies_record_each_region_separately_from_its_file(project):
    # Catches locking the whole region-bearing file (its code above would freeze) or saving no
    # copy of it.
    regions_unit(project)
    prepared(project)
    locks = store.load(project, "feature")["locks"]
    for path in (LIB, TIMER, EMPTY, WIRE, TWICE):
        keys = lock_keys(project, path)
        assert keys, f"No lock entry records the region of {path}: {sorted(locks)}"
        whole = sha256((project / path).read_bytes())
        assert all(locks[key] != whole for key in keys), f"The lock of {path} is the whole file's fingerprint."
    copy = test_preparation.copy_path(project / UNIT / store.LOCKED_FOLDER, LIB)
    assert copy.is_file(), "No saved copy of the region-bearing file src/lib.rs."
    assert region_of(copy.read_text(), RUST_START) == LIB_REGION, "The saved copy does not hold the locked region."


def test_code_written_above_the_region_never_makes_the_checkpoint_stale(project):
    # Guard after regions load: catches digesting the whole region-bearing file into the
    # checkpoint revision.
    regions_unit(project)
    prepared(project)
    (project / LIB).write_text(LIB_BUILT + LIB_REGION)
    (project / TIMER).write_text(TIMER_CODE.replace(">=", ">") + TIMER_REGION)
    record = store.load(project, "feature")
    assert engine.checkpoint_current(project, record), "Writing code above a region made the checkpoint stale."
    assert stage(project) == "writing-code"


def test_a_region_changed_through_the_shell_makes_the_checkpoint_not_current(project):
    # Catches leaving regions out of the checkpoint revision.
    regions_unit(project)
    prepared(project)
    (project / LIB).write_text(LIB_CODE + SHELL_REGION)
    assert not engine.checkpoint_current(project, store.load(project, "feature")), (
        "A changed region left the checkpoint current.")


# Boundary checks


def test_a_shell_change_inside_a_region_is_caught_at_the_next_task_start(project):
    # Catches boundary checks that compare whole locked files only.
    regions_unit(project)
    with_tidy_task(project)
    prepared(project)
    implementer(project)
    (project / LIB).write_text(LIB_CODE + SHELL_REGION)
    message = start(project, "tidy", "tidy-worker")
    assert message is not None and LIB in message, f"A shell change inside a region was not caught at task start: {message}"
    assert violations(project), "No lock-violation event was recorded."
    assert any(LIB in str(event) for event in violations(project)[-1].values())


def test_a_shell_change_adding_a_start_line_to_an_empty_region_is_caught(project):
    regions_unit(project)
    with_tidy_task(project)
    prepared(project)
    (project / EMPTY).write_text(EMPTY_CODE + "\n#[cfg(test)]\nmod tests {}\n")
    message = start(project, "tidy", "tidy-worker")
    assert message is not None and EMPTY in message, f"A start line added through the shell was not caught: {message}"


def test_code_above_the_region_written_through_the_shell_trips_no_boundary_check(project):
    # Guard after regions load: catches comparing the whole region-bearing file with its copy.
    regions_unit(project)
    with_tidy_task(project)
    prepared(project)
    (project / TIMER).write_text(TIMER_CODE.replace(">=", ">") + TIMER_REGION)
    assert start(project, "tidy", "tidy-worker") is None
    assert violations(project) == []


def test_the_rust_flow_builds_code_above_the_locked_region_and_closes(project):
    # The Regions item of "Done means": after the checkpoint, the implementation edit above
    # the region is allowed, its finish passes the boundary check, and implementation closes.
    regions_unit(project)
    prepared(project)
    returned = implemented(project)
    assert returned["status"] == "completed"
    assert start(project, "cancel", "cancel-worker") is None
    (project / "src/app.py").write_text("release()")
    finish(project, "cancel", ["src/app.py"], CHECK)
    complete_refactor_tasks(project)
    established(close.close_phase, project, "feature", "implement", "s", reviewer=clean_review)


# Restore


def test_restore_replaces_the_region_and_keeps_a_valid_edit_above(project):
    # Catches restoring the whole file from its copy, which would undo built code.
    regions_unit(project)
    with_tidy_task(project)
    prepared(project)
    implementer(project)
    (project / LIB).write_text(LIB_BUILT + SHELL_REGION)
    assert start(project, "tidy", "tidy-worker") is not None
    established(restore, project, LIB)
    assert (project / LIB).read_text() == LIB_BUILT + LIB_REGION, "Restore did not keep the code above byte for byte."
    assert start(project, "tidy", "tidy-worker") is None


def test_restore_keeps_crlf_code_above_byte_for_byte(project):
    # Catches text-mode rewriting of the code kept above the region.
    regions_unit(project)
    prepared(project)
    built = WIRE_CODE.replace("    0\r\n", "    1\r\n")
    (project / WIRE).write_bytes((built + WIRE_REGION.replace("1); }", "2); }")).encode())
    established(restore, project, WIRE)
    assert (project / WIRE).read_bytes() == (built + WIRE_REGION).encode()


def test_restore_appends_the_region_when_the_start_line_is_gone(project):
    # Catches a restore that finds no region to replace and gives up, or rewrites the whole file.
    regions_unit(project)
    prepared(project)
    (project / LIB).write_text(LIB_BUILT)
    established(restore, project, LIB)
    assert (project / LIB).read_text() == LIB_BUILT + LIB_REGION


def test_restore_refuses_a_region_that_still_matches_its_lock(project):
    # Guard after regions load: catches comparing the whole file with its copy, which would
    # make built code above look like a violation and restore would undo it.
    regions_unit(project)
    prepared(project)
    (project / LIB).write_text(LIB_BUILT + LIB_REGION)
    assert restore_refusal(project, LIB) is not None
    assert (project / LIB).read_text() == LIB_BUILT + LIB_REGION


# Unlock rework of a region


def test_an_unlocked_region_is_reworked_by_its_test_task_and_relocked(project):
    # Catches an unlock that does not recognize a region as a locked test, and a relock that
    # keeps the earlier region's copy.
    regions_unit(project)
    prepared(project)
    established(approve_unlock, project, {LIB: "fail"}, [{"argv": RUST_CHECK, "tests": [LIB]}],
                reason="The region test asserts the wrong call.")
    reworked = LIB_REGION.replace("fn release_reports_success", "fn release_succeeds")

    def rework(root):
        (root / LIB).write_text(LIB_CODE + reworked)
        return [LIB]

    run_test_tasks(project, {"region-tests": rework})
    assert checkpoint_refusal(project) is None
    copy = test_preparation.copy_path(project / UNIT / store.LOCKED_FOLDER, LIB)
    assert region_of(copy.read_text(), RUST_START) == reworked, "The relock kept the earlier region's copy."
    assert stage(project) == "writing-code"


# Guides, overview, glossary


def guide(name):
    return (ROOT_DOCS / "assets/fbk-docs/workflow" / name).read_text()


def test_the_test_regions_guide_illustrates_start_markers_per_language():
    assert (ROOT_DOCS / "assets/fbk-docs/workflow/test-regions.md").is_file(), "test-regions.md does not exist."
    text = guide("test-regions.md")
    assert "#[cfg(test)]" in text and "UNIT_TEST" in text, "The test-regions guide gives no example start markers."
    assert re.search(r"region", text, re.I), "The test-regions guide does not describe test regions."


# Region guidance travels only with test tasks in a scope that declares regions (operator,
# 2026-10-23): test-regions.md is its own guide, carried as test_region_guidance.

REGION_GUIDE = ROOT_DOCS / "assets/fbk-docs/workflow/test-regions.md"


def launched(root, task, worker):
    from .test_workflow_lifecycle import mutate

    return mutate(root, handoff.start_task, "s", task, worker)


def test_a_test_task_in_a_scope_with_regions_carries_the_region_guide(project):
    # Red: the region guide does not exist yet and the packet has no test_region_guidance.
    regions_unit(project)
    writing_tests(project)
    packet = launched(project, "region-tests", "test-author")
    assert REGION_GUIDE.is_file(), "assets/fbk-docs/workflow/test-regions.md does not exist."
    assert packet.get("test_region_guidance") == REGION_GUIDE.read_text(), (
        "A test task in a scope declaring test_regions does not carry the region guide.")


def test_a_test_task_in_a_scope_without_regions_does_not_carry_the_region_guide(project):
    # Guard: passes today (no such key); catches sending the region guide to every test task.
    writing_tests(project)
    packet = launched(project, "prepare-tests", "test-author")
    assert "test_region_guidance" not in packet
    assert "test_authoring_guidance" in packet


def test_an_implementation_task_never_carries_the_region_guide(project):
    # Guard: passes today (no such key); catches sending it to implementation tasks of a
    # region-declaring scope.
    regions_unit(project)
    prepared(project)
    packet = launched(project, "release", "implementer")
    assert packet["stage"] == "implementation"
    assert "test_region_guidance" not in packet


def test_the_test_authoring_guide_no_longer_carries_the_region_paragraph():
    # Red: the region paragraph is still in test-authoring.md.
    text = guide("test-authoring.md")
    assert not re.search(r"test region", text, re.I) and "#[cfg(test)]" not in text and "UNIT_TEST" not in text, (
        "test-authoring.md still describes test regions; that guidance belongs in test-regions.md.")


def test_the_spec_guide_states_interleaved_in_file_tests_are_unsupported():
    text = guide("spec.md")
    assert re.search(r"interleav", text, re.I) and "Zig" in text, (
        "The spec guide does not state that tests interleaved through a file are unsupported.")
    assert "test_regions" in text, "The spec guide does not name the scope's test_regions declaration."


def test_the_spec_review_flags_an_interleaved_test_layout():
    obligations = review.focus_brief("unit", "spec", [".fbk/unit/spec.md", ".fbk/unit/scope.json"])[
        "acceptance_obligations"]
    assert any(re.search(r"interleav", o, re.I) for o in obligations), obligations


def test_the_overview_and_glossary_define_test_region():
    assert re.search(r"^### test region$", (ROOT_DOCS / "GLOSSARY.md").read_text(), re.M | re.I), (
        "The glossary has no test region entry.")
    assert re.search(r"test region", (ROOT_DOCS / "docs/architecture-overview.md").read_text(), re.I)


# Review round 1


def test_deleting_text_just_above_the_start_line_is_refused_when_the_tool_also_drops_the_newline(project):
    # Catches modelling only the plain replacement: with an empty new_string the Edit tool also
    # deletes the newline after the deleted text, merging the comment into the start line.
    regions_unit(project)
    prepared(project)
    worker = implementer(project)
    (project / LIB).write_text("// remove me\n" + LIB_REGION)
    message = edit(project, worker, LIB, "remove me", "")
    assert message is not None, "An edit whose plausible result removes the region's start line was allowed."


CRLF_CODE = "".join(f"// line {i}\r\n" for i in range(12)) + "pub fn release() -> bool {\r\n    false\r\n}\r\n\r\n"


def test_a_code_edit_on_a_mostly_crlf_file_with_an_lf_region_is_refused(project):
    # Catches ignoring the Edit tool's line-ending normalization: it writes the file back in
    # its detected convention (CRLF here), which rewrites the LF region.
    regions_unit(project)
    prepared(project)
    worker = implementer(project)
    (project / LIB).write_bytes((CRLF_CODE + LIB_REGION).encode())
    message = edit(project, worker, LIB, "    false", "    true")
    assert message is not None, "A code edit whose normalized result rewrites the LF region as CRLF was allowed."


def test_restore_refuses_an_unreadable_region_bearing_file_and_leaves_it_unchanged(project):
    # Catches treating an unreadable file as having no code above, which truncates it to the region.
    regions_unit(project)
    prepared(project)
    target = project / LIB
    current = (LIB_BUILT + SHELL_REGION).encode()
    target.write_bytes(current)
    target.chmod(0o200)
    try:
        message = refusal(restore, project, LIB)
    finally:
        target.chmod(0o644)
    assert message is not None, "Restore wrote over a region-bearing file it could not read."
    assert target.read_bytes() == current, "Restore changed a region-bearing file it could not read."


NEW = "src/new.rs"


def test_a_new_production_file_with_no_start_line_keeps_the_checkpoint_current(project):
    # Catches counting an absent region and an empty one as different tests: the new file must
    # not make the checkpoint stale or the test set differ from the locks.
    regions_unit(project)
    edit_scope(project, creates=[NEW])
    edit_tasks(project, lambda by_id, tasks: by_id["release"]["files"].append(NEW))
    prepared(project)
    worker = implementer(project)
    assert write(project, worker, NEW, "pub fn fresh() {}\n") is None
    (project / NEW).write_text("pub fn fresh() {}\n")
    assert engine.checkpoint_current(project, store.load(project, "feature")), (
        "A new production file with no start line made the checkpoint stale.")
    assert refusal(engine.verify_locks, project, store.load(project, "feature")) is None, (
        "A new production file with no start line failed the lock check.")
    assert write(project, worker, LIB, LIB_BUILT + LIB_REGION) is None
    (project / LIB).write_text(LIB_BUILT + LIB_REGION)
    finish(project, "release", [LIB, NEW], RUST_CHECK)
    # Guard: a later non-empty region in the new file is still detected.
    (project / NEW).write_text("pub fn fresh() {}\n\n#[cfg(test)]\nmod tests {}\n")
    assert not engine.checkpoint_current(project, store.load(project, "feature")), (
        "A non-empty region added to the new file left the checkpoint current.")


TABLE = "src/table.inc"
WHOLE_REGION = {"files": ["src/*.inc"], "start": ""}


def with_whole_file_region(root):
    regions_unit(root)
    (root / TABLE).write_text("1 2 3\n4 5 6\n")
    edit_scope(root, test_regions=[*REGIONS, WHOLE_REGION])
    established(evidence.scope, root, "feature")


def test_an_empty_start_expression_makes_an_unchanged_file_an_untouched_test(project):
    # Catches truthiness checks that read start "" as no region.
    with_whole_file_region(project)
    writing_tests(project)
    run_test_tasks(project, {"region-tests": write_region_test})
    result = test_preparation.baseline_comparison(project, store.load(project, "feature"))
    assert TABLE not in result["changed_by_test_tasks"], "An unchanged file with start \"\" was a changed test."
    assert TABLE in result["untouched"], result


def test_an_empty_start_expression_makes_a_change_a_changed_test_not_undeclared_production(project, monkeypatch):
    # The region starts at line one, so the whole file is the region and no code sits above it.
    with_whole_file_region(project)
    writing_tests(project)
    run_test_tasks(project, {"region-tests": write_region_test})
    (project / TABLE).write_text("1 2 3\n4 5 7\n")
    seen = native_capture(monkeypatch)
    message = checkpoint_refusal(project, reviewer=None)
    assert message is None, f"A change to a whole-file region was refused as undeclared production: {message}"
    changed, _ = comparison(seen[-1]["prompt"])
    assert any(TABLE in str(path) for path in changed), changed


@pytest.mark.parametrize("change", [
    {"tests": ["tests", "src/*_test.rs"], "creates": ["src/new_test.rs"]},
    {"test_regions": [*REGIONS, {"files": ["src/new.rs"], "start": "^mod tests"}], "creates": ["src/new.rs"]},
])
def test_a_declared_new_path_in_a_region_conflict_is_refused_at_scope_load(project, change):
    # Catches checking conflicts against existing files only.
    regions_unit(project)
    established(evidence.scope, project, "feature")
    edit_scope(project, **change)
    named = change["creates"][0]
    message = refusal(evidence.scope, project, "feature")
    assert message is not None, f"Scope load accepted the declared new path {named} in a region conflict."
    assert named in message, f"The refusal does not name {named}: {message}"


def test_a_region_corrupted_before_finish_is_refused_with_the_task_left_running(project):
    # Catches checking regions at task start only.
    regions_unit(project)
    prepared(project)
    implementer(project)
    (project / LIB).write_text(LIB_BUILT + SHELL_REGION)
    message = finish_refusal(project, "release", [LIB], RUST_CHECK)
    assert message is not None and not message.startswith("NOT REFUSED") and LIB in message, message
    assert store.load(project, "feature")["task_runs"]["release"]["status"] == "running"
    event = violations(project)[-1]
    assert event.get("task") == "release" and LIB in event.get("files", []), event


@pytest.mark.parametrize("route", sorted(ROUTES))
def test_a_region_corrupted_while_finish_runs_its_checks_is_caught(project, monkeypatch, route):
    regions_unit(project)
    prepared(project)
    implementer(project)
    (project / LIB).write_text(LIB_BUILT + LIB_REGION)
    original = handoff._execute_task_checks

    def checks_then_corrupt(root, expectations):
        results = original(root, expectations)
        (project / LIB).write_text(LIB_BUILT + SHELL_REGION)
        return results

    monkeypatch.setattr(handoff, "_execute_task_checks", checks_then_corrupt)
    message = finish_refusal(project, "release", [LIB], RUST_CHECK, ROUTES[route])
    assert message is not None and not message.startswith("NOT REFUSED") and LIB in message, message
    assert store.load(project, "feature")["task_runs"]["release"]["status"] == "running"
    assert "release" in str(violations(project)[-1])


def test_an_unchanged_region_carries_its_red_after_the_code_above_is_built(project, monkeypatch):
    # Catches carrying red forward by whole-file fingerprint: the code above changed, the region did not.
    declare_regions(project, tests=(), checks=[RUST_CHECK])
    edit_tasks(project, lambda by_id, tasks: tasks.__setitem__(
        slice(None), [t for t in tasks if t["id"] not in {"prepare-tests", "cancel"}]))
    prepared(project)
    implemented(project)
    reopen(project, "breakdown")
    reenter_implement(project, "breakdown")
    assert review.run_command(RUST_CHECK, project, 10)["exit_code"] == 0
    assert start(project, "region-tests", "carry-author") is None
    result = review.run_command(RUST_CHECK, project, 10)
    returned = handoff.complete_task(
        project, "feature", "s", "region-tests", changed_files=[],
        checks=[{"argv": RUST_CHECK, "exit_code": result["exit_code"], "evidence": "The region check ran."}],
        unresolved=[], outcome="The region test is unchanged.")
    assert returned["status"] == "completed", f"An unchanged region did not carry its earlier red: {returned}"
    assert any(isinstance(k, str) and "carried" in k.lower() for k in keys(returned))
    seen = native_capture(monkeypatch)
    assert checkpoint_refusal(project, reviewer=None) is None
    changed, untouched = comparison(seen[-1]["prompt"])
    assert not any(LIB in str(p) for p in changed) and any(LIB in str(p) for p in untouched), (changed, untouched)
    assert any(LIB in str(p) for p in carried(seen[-1]["prompt"])), "The reviewer was not told the region carries red."


def test_restore_refuses_when_composition_cannot_reproduce_the_locked_region(project):
    # Catches dropping restore's final fingerprint check: appending the region to an
    # unterminated last line merges the start marker into production code.
    regions_unit(project)
    prepared(project)
    current = LIB_BUILT.rstrip("\n").encode()
    (project / LIB).write_bytes(current)
    message = refusal(restore, project, LIB)
    assert message is not None, "Restore wrote a file whose region does not match its lock."
    assert (project / LIB).read_bytes() == current, "A refused restore changed the file."


# Review round 2


def says_remedy(message, *words):
    return says_cannot_compute(message) and all(word in message.lower() for word in words)


@pytest.mark.parametrize("code", [
    # One CRLF line in an LF file.
    "pub fn release() -> bool {\r\n    false\n}\n\n",
    # The reviewer's shape: the first line ends in LF, CRLF leads in the first lines, LF leads overall.
    "// start\n" + "".join(f"// crlf {i}\r\n" for i in range(3)) + "pub fn release() -> bool {\n    false\n}\n\n",
])
def test_a_code_edit_on_a_mixed_line_ending_file_is_refused_as_not_computable(project, code):
    # Catches guessing which line-ending convention the Edit tool will write back.
    regions_unit(project)
    prepared(project)
    worker = implementer(project)
    (project / LIB).write_bytes((code + LIB_REGION).encode())
    message = edit(project, worker, LIB, "    false", "    true")
    assert says_remedy(message, "line ending"), (
        f"A code edit on a mixed line-ending file was not refused as uncomputable with the remedy: {message}")


@pytest.mark.parametrize("tool", ["Write", "Edit"])
def test_a_write_or_edit_to_a_file_with_a_byte_order_mark_is_refused_as_not_computable(project, tool):
    # Catches omitting the byte-order mark the Write tool preserves, which can move the start line.
    regions_unit(project)
    prepared(project)
    worker = implementer(project)
    (project / LIB).write_bytes(b"\xef\xbb\xbf" + (LIB_CODE + LIB_REGION).encode())
    message = (write(project, worker, LIB, LIB_REGION) if tool == "Write"
               else edit(project, worker, LIB, "    false", "    true"))
    assert says_remedy(message, "byte-order mark"), (
        f"A {tool} to a file with a byte-order mark was not refused as uncomputable with the remedy: {message}")


def test_an_implementation_task_owning_the_folder_deletes_a_file_with_no_start_line(project):
    # Catches comparing an empty-region lock with a missing file as a violation or missing evidence.
    regions_unit(project)
    def own_folder(by_id, tasks):
        by_id["release"]["files"] = ["src"]
        by_id["cancel"]["depends_on"] = ["release"]  # src/app.py is inside the folder

    edit_tasks(project, own_folder)
    prepared(project)
    worker = implementer(project)
    assert write(project, worker, LIB, LIB_BUILT + LIB_REGION) is None
    (project / LIB).write_text(LIB_BUILT + LIB_REGION)
    (project / EMPTY).unlink()
    message = finish_refusal(project, "release", [LIB, EMPTY], RUST_CHECK)
    assert message == "NOT REFUSED: completed", f"Deleting a production file with an empty region refused the finish: {message}"
    assert violations(project) == [], "Deleting a production file with an empty region was recorded as a lock violation."
    assert start(project, "cancel", "cancel-worker") is None
    (project / "src/app.py").write_text("release()")
    finish(project, "cancel", ["src/app.py"], CHECK)
    complete_refactor_tasks(project)
    message = refusal(close.close_phase, project, "feature", "implement", "s", reviewer=clean_review)
    assert message is None, f"Implementation close refused after a production file with an empty region was deleted: {message}"


def test_a_missing_file_whose_locked_region_was_not_empty_is_still_a_violation(project):
    # Guard: catches treating every missing region-bearing file as an empty region.
    regions_unit(project)
    with_tidy_task(project)
    prepared(project)
    (project / TIMER).unlink()
    message = start(project, "tidy", "tidy-worker")
    assert message is not None and TIMER in message, f"A deleted file with a locked region was not a violation: {message}"
    assert violations(project)


@pytest.mark.parametrize("locked_mode, current_mode", [(0o644, 0o755), (0o755, 0o644)])
def test_restore_keeps_the_current_executable_bit_after_a_valid_mode_change(project, locked_mode, current_mode):
    # Guard: catches applying the saved copy's mode, which undoes a valid production mode change.
    regions_unit(project)
    (project / LIB).chmod(locked_mode)
    prepared(project)
    (project / LIB).write_text(LIB_BUILT + SHELL_REGION)
    (project / LIB).chmod(current_mode)
    established(restore, project, LIB)
    assert (project / LIB).read_text() == LIB_BUILT + LIB_REGION
    assert (project / LIB).stat().st_mode & 0o777 == current_mode, "Restore undid the file's valid mode change."
