"""Traceability in tasks (build step 8, plan decision 8).

Each task links the requirements it serves through anchored ``acceptance_refs`` entries into
``spec.md``; breakdown close checks that every task links one of its own unit's requirements
and that every requirement is covered by an implementation task and a test task; at launch the
task packet carries each linked requirement's own section, its design choices' sections and
their commitments' sections, bound so a change to any of them makes the task context stale;
a chain or rest of the packet over its own limit is refused at breakdown close and at launch.

Lead rulings these tests rely on (step 8 brief):

1. **Where the link lives.** An ``acceptance_refs`` entry ``<repository path of spec.md>#<anchor>``.
   An anchored entry into the unit's own ``spec.md`` (or a child's parent's accepted
   ``spec.md``) must land on an item of the Requirements section by step 7's parser and anchor
   rules, or it is refused naming the task, the entry and the reason. Whole-file references
   stay allowed; an anchored spec entry satisfies the spec half of the prd/spec rule; anchored
   entries into other documents keep today's rule (any unique heading).
2. **Each task needs one of its own.** Parent requirement links are carried in the context
   but do not count toward the own-requirement rule or coverage.
3. **Coverage at breakdown close** (plan validation, before any review round), naming every
   problem at once: each task with no own-requirement link, and each own requirement not
   linked by an implementation task, a test task, or either (saying which).
4. **Extra links at launch** follow the same landing rule and join the chain.
5. **The chain in the packet**: ``packet["traceability"]`` with ``requirements``,
   ``design_choices``, ``commitments``, each a list of ``{"ref", "name", "text"}``; the text is
   the item's own section, verbatim; no duplicates, first-appearance order; parent links
   followed; links to code, URLs and other documents not followed.
6. **The chain stays current**: every document the chain was read from is bound to the
   assignment.
7. **Oversize refusal** (superseded in part by the 2026-10-25 two-limit ruling, see "the packet
   limits" below): the chain has a 64,000-character limit (raised 2026-11-06) and the rest of the packet a 16,000-character limit. A
   chain refusal names the task, the chain's size and the limit, each linked requirement's
   whole-chain size, and up to five largest linked sections (largest first, by reference and
   character count), states the split-or-tighten remedy, and records no run. Breakdown close
   checks both limits for every task before any review round.

Shapes the tests assume: refusals are ``WorkflowError``. A section's text is compared after
stripping surrounding whitespace (the ruling says "verbatim"; whether the blank line before the
next heading is kept is left to the implementer). Character counts in the oversize refusal are
matched within a few characters for the same reason, and may be written with thousands
separators.

Red or guard: each test's docstring says which. **Red** tests fail today on an assertion about
missing behavior; **guard** tests (marked ``# Guard:``) pass today and pin behavior a plausible
wrong implementation would break.
"""

import json
import re
import sys
from pathlib import Path

import pytest

from fbk.workflow import engine, evidence, handoff, store
from .test_workflow_lifecycle import mutate
from .test_workflow_traceability import (
    DESIGN,
    PARENT_DESIGN,
    PARENT_PRD,
    PARENT_SPEC,
    PRD,
    SPEC,
    SPEC_NO_DESIGN,
    accept,
    feature,
    names_all,
    parent_and_child,
    refused,
)
from .refactor_plan import refactor_task, with_refactor

ROOT_DOCS = Path(__file__).resolve().parents[3]
UNIT = "feature"
BASE = f".fbk/{UNIT}"
PRD_REF, SPEC_REF = f"{BASE}/prd.md", f"{BASE}/spec.md"
DESIGN_REF = f"{BASE}/design/storage.md"
LIMIT = 16000
CHAIN_LIMIT = 64000


def req(anchor, base=BASE):
    return f"{base}/spec.md#{anchor}"


def refs(*anchors, base=BASE):
    return [f"{base}/prd.md", f"{base}/spec.md", *(req(a, base) for a in anchors)]


def task(task_id, stage, files, acceptance_refs):
    """A valid task; each gets its own check command so no two tasks share an expectation."""
    code = 1 if stage == "tests" else 0
    return {
        "id": task_id, "stage": stage, "description": f"Task {task_id} builds its part of backups.",
        "files": files, "depends_on": [], "acceptance_refs": acceptance_refs,
        "verification": "Its check proves the linked requirements; a wrong restore fails it.",
        "check_expectations": [{"argv": [sys.executable, "-c", f"import sys; sys.exit({code})  # {task_id}"],
                                "exit_code": code}],
    }


def default_tasks():
    """A test task and an implementation task, each linking both requirements of SPEC."""
    linked = refs("restore-command", "history-listing")
    return [task("restore-tests", "tests", ["tests/test_restore.py"], linked),
            task("restore-code", "implementation", ["src/backup.py"], linked)]


def project_files(root):
    for path in ("tests/test_restore.py", "tests/test_listing.py", "src/backup.py", "src/listing.py"):
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text("pass\n")


def through_spec(root, *, design=True, prd=PRD, designs=None, spec=None):
    """A unit with intent, (design,) and spec accepted, and its source and test files present."""
    feature(root, design=design, prd=prd, designs=designs, spec=spec)
    project_files(root)
    for phase in ("intent", "design", "spec") if design else ("intent", "spec"):
        accept(root, phase)


def write_tasks(root, tasks, unit=UNIT):
    store.atomic_json(root / f".fbk/{unit}/tasks.json", with_refactor(tasks))


def breakdown_refusal(root, tasks, unit=UNIT):
    """Breakdown close must refuse before any review round; returns the message."""
    write_tasks(root, tasks, unit)
    return refused(root, "breakdown", unit)


def into_implement(root, tasks, unit=UNIT):
    """Accept breakdown with ``tasks`` and enter implement (writing tests, no locks)."""
    write_tasks(root, tasks, unit)
    accept(root, "breakdown", unit)
    mutate(root, engine.approve, "s", "start-implementation", "implement",
           "Implement the agreed spec.", unit=unit)
    mutate(root, engine.enter, "implement", "s", unit=unit)


def launch(root, task_id, unit=UNIT, **kwargs):
    return mutate(root, handoff.start_task, "s", task_id, f"{task_id}-worker", unit=unit, **kwargs)


def launch_refusal(root, task_id, unit=UNIT, **kwargs):
    with pytest.raises(store.WorkflowError) as failure:
        launch(root, task_id, unit, **kwargs)
    record = store.load(root, unit)
    assert task_id not in record.get("task_runs", {}), "A refused launch recorded a run."
    assert not any(e["event"] == "task-started" and e.get("task") == task_id for e in record["events"]), (
        "A refused launch recorded a task-started event.")
    return str(failure.value)


def section_of(doc, heading):
    """Expected item text: from ``heading`` to the next heading at its level or higher."""
    lines = doc.splitlines()
    start = lines.index(heading)
    level = len(heading) - len(heading.lstrip("#"))
    end = next((i for i in range(start + 1, len(lines)) if re.match(rf"#{{1,{level}}} ", lines[i])), len(lines))
    return "\n".join(lines[start:end]).strip()


def entry(ref, doc, heading):
    return {"ref": ref, "name": heading.lstrip("#").strip(), "text": section_of(doc, heading)}


def chain_of(packet):
    chain = packet.get("traceability")
    assert isinstance(chain, dict), f"The task packet carries no traceability chain: {sorted(packet)}"
    return {
        kind: [(e["ref"], e["name"], e["text"].strip()) for e in chain.get(kind, [])]
        for kind in ("requirements", "design_choices", "commitments")
    }


def expected(**kinds):
    return {kind: [(e["ref"], e["name"], e["text"]) for e in kinds.get(kind, [])]
            for kind in ("requirements", "design_choices", "commitments")}


def lines_naming(message, *names):
    return "\n".join(line for line in message.splitlines() if any(n in line for n in names))


# Chain entries of the default documents.
RESTORE = entry(req("restore-command"), SPEC, "### Restore command")
LISTING = entry(req("history-listing"), SPEC, "### History listing")
SNAPSHOT = entry(f"{DESIGN_REF}#snapshot-store", DESIGN, "## Snapshot store")
RETENTION = entry(f"{DESIGN_REF}#retention-log", DESIGN, "## Retention log")
FAST = entry(f"{PRD_REF}#fast-restore", PRD, "### Fast restore")
HISTORY = entry(f"{PRD_REF}#keep-history", PRD, "### Keep history")


# --- breakdown close: where an anchored requirement link may land ---------------------------

AMBIGUOUS_SPEC = SPEC + """
## Notes

### _Restore command_

The command's history, written with emphasis so its anchor matches the requirement's.
"""


@pytest.mark.parametrize("anchor,reason,spec", [
    ("requirements", r"section heading", SPEC),
    ("listing-format", r"inside", SPEC),
    ("checks", r"outside|Requirements", SPEC),
    ("restore-command", r"ambiguous", AMBIGUOUS_SPEC),
], ids=["section-heading", "heading-inside-an-item", "heading-outside-requirements", "ambiguous"])
def test_anchored_spec_link_not_landing_on_a_requirement_is_refused(tmp_path, anchor, reason, spec):
    """Red. An anchored acceptance_refs entry into the unit's spec.md must land on an item of
    Requirements by step 7's rules; the section heading, a heading inside an item, a heading
    outside Requirements, and an anchor two headings produce (with emphasis removed) are
    refused naming the task, the entry and the reason. Today any unique plain heading anchor
    is accepted, and the emphasis form is not counted as a duplicate."""
    through_spec(tmp_path, spec=spec)
    tasks = default_tasks()
    bad = req(anchor)
    tasks[1]["acceptance_refs"] = [*refs("history-listing"), bad] if anchor == "restore-command" else [
        *tasks[1]["acceptance_refs"], bad]
    message = breakdown_refusal(tmp_path, tasks)
    names_all(message, "restore-code", bad)
    assert re.search(reason, message, re.I), f"The refusal gives no reason matching {reason!r}: {message}"


def test_anchored_spec_link_to_a_missing_anchor_is_refused(tmp_path):
    """Guard: today's reference check already refuses an anchor no heading produces, naming the
    task and entry; the requirement landing rule must keep refusing it."""
    through_spec(tmp_path)
    tasks = default_tasks()
    bad = req("no-such-requirement")
    tasks[0]["acceptance_refs"].append(bad)
    message = breakdown_refusal(tmp_path, tasks)
    names_all(message, "restore-tests", bad)
    assert re.search(r"anchor|heading", message, re.I), message


def test_anchored_entries_into_other_documents_keep_todays_rule(tmp_path):
    """Guard: an anchored entry into a design file may name any unique heading, here a heading
    inside a design choice; only spec.md entries must land on a requirement. An implementation
    applying the requirement rule to every anchored entry would refuse this plan."""
    through_spec(tmp_path)
    tasks = default_tasks()
    for each in tasks:
        each["acceptance_refs"].append(f"{DESIGN_REF}#store-layout")
    write_tasks(tmp_path, tasks)
    accept(tmp_path, "breakdown")


def test_anchored_spec_entry_satisfies_the_spec_half_of_the_reference_rule(tmp_path):
    """Guard: a task referencing prd.md and only anchored spec.md entries (no whole spec.md)
    satisfies the rule that acceptance_refs cover both intent and specification."""
    through_spec(tmp_path)
    tasks = default_tasks()
    for each in tasks:
        each["acceptance_refs"] = [PRD_REF, req("restore-command"), req("history-listing")]
    write_tasks(tmp_path, tasks)
    accept(tmp_path, "breakdown")


# --- breakdown close: own-requirement links and coverage -----------------------------------


def test_task_without_a_requirement_link_is_refused_naming_it(tmp_path):
    """Red. A task referencing only whole files links no requirement; breakdown close refuses
    it by name before any review round. Today whole-file references satisfy plan validation."""
    through_spec(tmp_path)
    tasks = default_tasks() + [task("wiring", "implementation", ["src/listing.py"], refs())]
    message = breakdown_refusal(tmp_path, tasks)
    assert "wiring" in lines_naming(message, "wiring"), message
    assert re.search(r"requirement", lines_naming(message, "wiring"), re.I), message


COVERAGE_SPEC = """\
# Backup behavior

## Requirements

### Restore command

Restores, from [Snapshot store](design/storage.md#snapshot-store).

### History listing

Lists, from [Retention log](design/storage.md#retention-log).

### Restore progress

Shows progress, from [Snapshot store](design/storage.md#snapshot-store).

### Listing order

Newest first, from [Retention log](design/storage.md#retention-log).
"""


def test_breakdown_close_names_every_coverage_problem_at_once(tmp_path):
    """Red. One refusal names the task with no requirement link, the requirement no test task
    links, the requirement no implementation task links, and the requirement neither links,
    saying which kind of task is missing for each. Today plan validation checks no coverage."""
    through_spec(tmp_path, spec=COVERAGE_SPEC)
    tasks = [
        task("core-tests", "tests", ["tests/test_restore.py"], refs("restore-command", "restore-progress")),
        task("core-code", "implementation", ["src/backup.py"], refs("restore-command", "history-listing")),
        task("docs-only", "implementation", ["src/listing.py"], refs()),
    ]
    message = breakdown_refusal(tmp_path, tasks)
    assert "docs-only" in message, f"The task without a requirement link is not named: {message}"
    no_test = lines_naming(message, "History listing", "history-listing")
    no_code = lines_naming(message, "Restore progress", "restore-progress")
    neither = lines_naming(message, "Listing order", "listing-order")
    assert no_test and re.search(r"test", no_test, re.I), (
        f"History listing should be named as lacking a test task: {message}")
    assert no_code and re.search(r"implementation", no_code, re.I), (
        f"Restore progress should be named as lacking an implementation task: {message}")
    assert neither and re.search(r"implementation", neither, re.I) and re.search(r"test", neither, re.I), (
        f"Listing order should be named as lacking both: {message}")
    assert "Restore command" not in message, f"A covered requirement is named as a problem: {message}"


def test_requirement_covered_only_by_a_test_task_is_refused(tmp_path):
    """Red. With design skipped: a requirement linked only by a test task is refused for want of
    an implementation task. Today breakdown closes."""
    through_spec(tmp_path, design=False)
    tasks = [task("restore-tests", "tests", ["tests/test_restore.py"], refs("restore-command", "history-listing")),
             task("restore-code", "implementation", ["src/backup.py"], refs("restore-command"))]
    message = breakdown_refusal(tmp_path, tasks)
    names_all(message, "History listing")
    assert re.search(r"implementation", lines_naming(message, "History listing"), re.I), message


# --- child units ---------------------------------------------------------------------------

CHILD = ".fbk/child"
PARENT = ".fbk/platform"


def child_through_spec(root):
    parent_and_child(root)
    project_files(root)
    for phase in ("intent", "design", "spec"):
        accept(root, phase, unit="child")


def child_tasks(extra=()):
    linked = refs("button-cancels", "scheduler-reuse", base=CHILD) + list(extra)
    return [task("child-tests", "tests", ["tests/test_restore.py"], linked),
            task("child-code", "implementation", ["src/backup.py"], linked)]


def test_child_task_linking_only_a_parent_requirement_is_refused(tmp_path):
    """Red. A parent requirement link is carried but does not count toward the own-requirement
    rule; a child task whose only requirement link is the parent's is refused by name."""
    child_through_spec(tmp_path)
    tasks = child_tasks() + [task("parent-only", "implementation", ["src/listing.py"],
                                  [*refs(base=CHILD), req("cancel-api", PARENT)])]
    message = breakdown_refusal(tmp_path, tasks, unit="child")
    assert "parent-only" in message, message


def test_child_link_to_the_parent_requirements_heading_is_refused(tmp_path):
    """Red. An anchored entry into the parent's accepted spec.md follows the same landing rule:
    the Requirements section heading is not a requirement. Today it is a unique heading."""
    child_through_spec(tmp_path)
    bad = req("requirements", PARENT)
    message = breakdown_refusal(tmp_path, child_tasks([bad]), unit="child")
    names_all(message, "child-tests", bad)


def test_child_packet_follows_links_into_the_parent_and_needs_no_parent_coverage(tmp_path):
    """Red. A child whose tasks cover only its own requirements closes breakdown (the parent's
    Scheduler API needs no child coverage), and a task that also links the parent's Cancel API
    carries its chain: requirements in link order, the child's and the parent's design choices,
    and commitments in both units, each once in first-appearance order. Today the packet has no
    chain."""
    child_through_spec(tmp_path)
    child = store.load(tmp_path, "child")
    assert child["parent"] == "platform"
    into_implement(tmp_path, child_tasks([req("cancel-api", PARENT)]), unit="child")
    packet = launch(tmp_path, "child-tests", unit="child")
    from .test_workflow_traceability import CHILD_DESIGN, CHILD_PRD, CHILD_SPEC

    assert chain_of(packet) == expected(
        requirements=[entry(req("button-cancels", CHILD), CHILD_SPEC, "### Button cancels"),
                      entry(req("scheduler-reuse", CHILD), CHILD_SPEC, "### Scheduler reuse"),
                      entry(req("cancel-api", PARENT), PARENT_SPEC, "### Cancel API")],
        design_choices=[entry(f"{CHILD}/design/console.md#console-button", CHILD_DESIGN, "### Console button"),
                        entry(f"{PARENT}/design/overview.md#job-state-machine", PARENT_DESIGN, "### Job state machine"),
                        entry(f"{CHILD}/design/console.md#reuse-scheduler", CHILD_DESIGN, "### Reuse scheduler")],
        commitments=[entry(f"{CHILD}/prd.md#cancel-from-the-console", CHILD_PRD, "### Cancel from the console"),
                     entry(f"{PARENT}/prd.md#cancel-jobs", PARENT_PRD, "### Cancel jobs"),
                     entry(f"{PARENT}/prd.md#shared-scheduler", PARENT_PRD, "### Shared scheduler")],
    )


@pytest.mark.parametrize("path,old,new", [
    (f"{PARENT}/design/overview.md", "Explicit job states serve", "Explicit, documented job states serve"),
    (f"{PARENT}/prd.md", "Any job can be cancelled.", "Any job can be cancelled at any time."),
])
def test_a_changed_parent_chain_source_makes_the_child_task_context_stale(tmp_path, path, old, new):
    """Red. The chain read the parent's design file and prd.md; neither is bound to the
    child's assignment today, so after either changes the task context is still served. Every
    document the chain was read from must bind the assignment."""
    child_through_spec(tmp_path)
    into_implement(tmp_path, child_tasks(), unit="child")
    launch(tmp_path, "child-tests", unit="child")
    source = tmp_path / path
    assert old in source.read_text()
    source.write_text(source.read_text().replace(old, new))
    with pytest.raises(store.WorkflowError, match=r"(?i)changed|stale|refresh"):
        handoff.task_packet(tmp_path, store.load(tmp_path, "child"), "child-tests")


def test_a_changed_own_chain_source_makes_the_task_context_stale(tmp_path):
    """Guard: the unit's own design file is already bound through the accepted breakdown's
    plan binding; a chain implementation must not loosen that."""
    through_spec(tmp_path)
    into_implement(tmp_path, default_tasks())
    launch(tmp_path, "restore-tests")
    design = tmp_path / DESIGN_REF
    design.write_text(design.read_text().replace("One folder per day", "One folder per hour"))
    with pytest.raises(store.WorkflowError, match=r"(?i)changed|stale|refresh"):
        handoff.task_packet(tmp_path, store.load(tmp_path, UNIT), "restore-tests")


# --- the chain in the packet ---------------------------------------------------------------


def test_packet_carries_each_linked_requirements_chain_with_design(tmp_path):
    """Red. A task linking both requirements carries each requirement's own section (a
    deeper heading inside it included, the next section excluded), the design choices they link
    (with the heading inside the item), and those choices' commitments. Today the packet has
    no traceability entry."""
    through_spec(tmp_path)
    into_implement(tmp_path, default_tasks())
    packet = launch(tmp_path, "restore-tests")
    assert chain_of(packet) == expected(requirements=[RESTORE, LISTING], design_choices=[SNAPSHOT, RETENTION],
                                        commitments=[FAST, HISTORY])
    assert "## Checks" not in LISTING["text"] and "#### Listing format" in LISTING["text"]


SHARED_SPEC = """\
# Backup behavior

## Requirements

### Restore command

Restores from [Retention log](design/storage.md#retention-log) and
[Snapshot store](design/storage.md#snapshot-store), and again [Snapshot store](design/storage.md#snapshot-store).
See [the module](../../src/backup.py), [restic](https://example.com/restic#restore) and [notes](notes.md#restore).

### History listing

Lists dates from [Snapshot store](design/storage.md#snapshot-store).

## Checks

Run the unit tests.
"""


def test_packet_chain_has_no_duplicates_keeps_first_appearance_and_ignores_other_links(tmp_path):
    """Red. Requirements follow the task's link order; a design choice two requirements share
    (and one links twice) appears once where first reached; commitments follow; links to code,
    a URL and another document inside a requirement are not followed."""
    through_spec(tmp_path, spec=SHARED_SPEC)
    linked = refs("history-listing", "restore-command")
    into_implement(tmp_path, [task("restore-tests", "tests", ["tests/test_restore.py"], linked),
                              task("restore-code", "implementation", ["src/backup.py"], linked)])
    packet = launch(tmp_path, "restore-tests")
    assert chain_of(packet) == expected(
        requirements=[entry(req("history-listing"), SHARED_SPEC, "### History listing"),
                      entry(req("restore-command"), SHARED_SPEC, "### Restore command")],
        design_choices=[SNAPSHOT, RETENTION],
        commitments=[FAST, HISTORY],
    )


def split_tasks():
    return [task("restore-tests", "tests", ["tests/test_restore.py"], refs("restore-command")),
            task("listing-tests", "tests", ["tests/test_listing.py"], refs("history-listing")),
            task("backup-code", "implementation", ["src/backup.py"], refs("restore-command", "history-listing"))]


def test_packet_without_design_links_requirements_straight_to_commitments(tmp_path):
    """Red. In a unit without design the chain has no design choices; the commitments are the
    ones the requirement links. Only the task's own requirement is carried."""
    through_spec(tmp_path, design=False)
    into_implement(tmp_path, split_tasks())
    packet = launch(tmp_path, "restore-tests")
    assert chain_of(packet) == expected(
        requirements=[entry(req("restore-command"), SPEC_NO_DESIGN, "### Restore command")],
        design_choices=[], commitments=[FAST])


def test_requirement_link_added_at_launch_joins_the_chain(tmp_path):
    """Red. A requirement link added through --acceptance-refs at launch is carried with its
    design choices and commitments after the task's own."""
    through_spec(tmp_path)
    into_implement(tmp_path, split_tasks())
    packet = launch(tmp_path, "restore-tests", acceptance_refs=[req("history-listing")])
    assert chain_of(packet) == expected(requirements=[RESTORE, LISTING], design_choices=[SNAPSHOT, RETENTION],
                                        commitments=[FAST, HISTORY])


@pytest.mark.parametrize("anchor", ["requirements", "listing-format", "checks"])
def test_requirement_link_added_at_launch_follows_the_landing_rule(tmp_path, anchor):
    """Red. An extra anchored spec.md entry at launch that misses a requirement item is refused
    naming the task and the entry, and no run is recorded. Today any unique heading is
    accepted."""
    through_spec(tmp_path)
    into_implement(tmp_path, split_tasks())
    message = launch_refusal(tmp_path, "restore-tests", acceptance_refs=[req(anchor)])
    names_all(message, "restore-tests", req(anchor))


# --- the packet limits ---------------------------------------------------------------------
#
# Lead ruling (operator, 2026-10-25, superseding step 8's single limit): a task's context has
# two limits, each checked on its own. The chain (``packet["traceability"]``) may be at most
# 16,000 serialized characters, and so may the rest of the packet (the packet without its
# ``traceability`` key). Breakdown close checks every task's context, built from tasks.json the
# way launch builds it, before any review round, and names every oversized task in one refusal;
# launch keeps its own check. A chain refusal reports the task, the chain's size and limit, each
# linked requirement's whole-chain size, the five largest linked sections and the split-or-
# tighten remedy; a rest refusal reports the task, the rest's size and limit, its largest fields
# (up to five, largest first, by serialized size) and the shorten-or-split remedy; a task over
# both gets one refusal reporting both. Sizes are ``len(json.dumps(..., ensure_ascii=False))``.
# At breakdown the worker id is a 36-character placeholder (round 1 ruling 2), so a rest size
# reported at breakdown close is up to 16 more than at launch with these tests' 20-character
# worker ids; it is matched within a few dozen characters. A field's size is matched
# within the length of its key plus quoting, since "by serialized size" may or may not count it.


def filler(size, word):
    """One plain-text line of exactly ``size`` characters."""
    text = (f"Detail about {word} for the operator. " * (size // 20 + 2))[:size]
    return text[:-1] + "." if size else ""


def padded(doc, heading, size, word):
    """``doc`` with a filler paragraph appended to the item under ``heading``."""
    lines = doc.splitlines()
    start = lines.index(heading)
    level = len(heading) - len(heading.lstrip("#"))
    end = next((i for i in range(start + 1, len(lines)) if re.match(rf"#{{1,{level}}} ", lines[i])), len(lines))
    while end > start + 1 and not lines[end - 1].strip():
        end -= 1
    return "\n".join([*lines[:end], "", filler(size, word), *lines[end:]]) + "\n"


def sized_at(message, ref, size, tolerance=4):
    """Positions where ``ref`` is followed on its line by a count within ``tolerance`` of ``size``."""
    found = []
    for match in re.finditer(re.escape(ref), message):
        rest = message[match.end():match.end() + 120].split("\n", 1)[0]
        if any(abs(int(n.replace(",", "")) - size) <= tolerance for n in re.findall(r"\d[\d,]*", rest)):
            found.append(match.start())
    return found


def states_size(message, size, tolerance=4):
    """Whether the message states a count within ``tolerance`` of ``size`` anywhere."""
    return any(abs(int(n.replace(",", "")) - size) <= tolerance for n in re.findall(r"\d[\d,]*", message))


FIELD_TOLERANCE = 32


def field_at(message, field, size, tolerance=FIELD_TOLERANCE):
    """Positions where packet field ``field`` (underscores or spaces) is followed on its line by a
    count within ``tolerance`` of ``size``. ``authoring_guidance`` does not match inside
    ``test_authoring_guidance``."""
    pattern = r"(?<![\w-])" + field.replace("_", "[_ ]") + r"(?!\w)"
    found = []
    for match in re.finditer(pattern, message):
        rest = message[match.end():match.end() + 120].split("\n", 1)[0]
        if any(abs(int(n.replace(",", "")) - size) <= tolerance for n in re.findall(r"\d[\d,]*", rest)):
            found.append(match.start())
    return found


def in_order(message, finder, items):
    """``items`` (each ``(name, size)``) are each listed by ``finder`` and appear in that order."""
    positions = []
    for name, size in items:
        found = finder(message, name, size)
        assert found, f"The refusal does not list {name} with its size (~{size}): {message}"
        positions.append(found[0] if not positions else next((p for p in found if p > positions[-1]), -1))
    assert positions == sorted(positions) and -1 not in positions, (
        f"The refusal does not list {[n for n, _ in items]} largest first: {message}")


def dumped(value):
    return len(json.dumps(value, ensure_ascii=False))


def split_sizes(packet):
    """The serialized size of the packet's chain and of the rest of the packet."""
    return dumped(packet["traceability"]), dumped({k: v for k, v in packet.items() if k != "traceability"})


def launched(root, task_id, **kwargs):
    """Launch a task expected to be within both limits; a refusal fails as an assertion."""
    try:
        return launch(root, task_id, **kwargs)
    except store.WorkflowError as exc:
        pytest.fail(f"Launch of {task_id} was refused though its chain and rest are each within their limits: {exc}")


def guidance_text(name="repository-grounding.md"):
    return (ROOT_DOCS / "assets/fbk-docs/workflow" / name).read_text(encoding="utf-8")


def four_tasks():
    """A test task, an implementation task and a refactor task for each requirement, each linking
    only its own, so no planned chain carries both requirements."""
    restore = task("restore-code", "implementation", ["src/backup.py"], refs("restore-command"))
    listing = task("listing-code", "implementation", ["src/listing.py"], refs("history-listing"))
    return [task("restore-tests", "tests", ["tests/test_restore.py"], refs("restore-command")),
            task("listing-tests", "tests", ["tests/test_listing.py"], refs("history-listing")),
            restore, listing,
            refactor_task([restore], "restore-refactor"), refactor_task([listing], "listing-refactor")]


def sized_plan(tmp_path, *, chain=None, rest=None, tasks=default_tasks, task_id="restore-tests", **launch_kwargs):
    """Spec text and tasks that give test task ``task_id``'s context, launched with
    ``launch_kwargs``, a chain of exactly ``chain`` and a rest of exactly ``rest`` characters
    (either left as is when None). A probe unit with the restore requirement padded by one
    character gives the base sizes; padding that requirement grows only the chain and the task's
    verification grows only the rest, one for one (plain text, nothing escaped)."""
    probe = tmp_path / "probe"
    probe.mkdir()
    through_spec(probe, spec=padded(SPEC, "### Restore command", 1, "restore"))
    into_implement(probe, tasks())
    base_chain, base_rest = split_sizes(launch(probe, task_id, **launch_kwargs))
    spec = padded(SPEC, "### Restore command", 1 + (chain - base_chain if chain else 0), "restore")
    planned = tasks()
    if rest:
        target = next(t for t in planned if t["id"] == task_id)
        target["verification"] = filler(len(target["verification"]) + rest - base_rest, "checks")
    return spec, planned


def sized_unit(tmp_path, spec, tasks, *, accept_plan=True):
    root = tmp_path / "unit"
    root.mkdir()
    through_spec(root, spec=spec)
    if accept_plan:
        into_implement(root, tasks)
    return root


def chain_sizes(spec):
    """Each requirement's whole-chain size (its section, design choice and commitment texts)."""
    restore = entry(req("restore-command"), spec, "### Restore command")
    return {restore["ref"]: sum(len(e["text"]) for e in (restore, SNAPSHOT, FAST)),
            LISTING["ref"]: sum(len(e["text"]) for e in (LISTING, RETENTION, HISTORY))}


def test_oversize_chain_refuses_launch_naming_the_task_chains_and_largest_sections(tmp_path):
    """Red. The chain has its own 64,000-character limit, and launch checks it. Each planned task
    links one requirement, so every planned chain is under the limit and breakdown closes; adding
    the history listing at launch through --acceptance-refs pushes the restore test task's chain
    past it. The refusal names the task, the chain's size (not the whole packet's) and the limit,
    each linked requirement's whole-chain size, and the five largest linked sections largest first
    with their character counts (the sixth, smallest, is not listed), and states the remedy. No
    run is recorded. Today the refusal states the whole packet's size."""
    prd = padded(PRD, "### Fast restore", 12800, "fast restore")
    design = padded(padded(DESIGN, "## Snapshot store", 18000, "snapshots"), "## Retention log", 6000, "retention")
    spec = padded(padded(SPEC, "### Restore command", 24000, "restore"), "### History listing", 8800, "listing")
    through_spec(tmp_path, prd=prd, designs={"storage.md": design}, spec=spec)
    into_implement(tmp_path, four_tasks())
    message = launch_refusal(tmp_path, "restore-tests", acceptance_refs=[req("history-listing")])
    sections = [entry(req("restore-command"), spec, "### Restore command"),
                entry(f"{DESIGN_REF}#snapshot-store", design, "## Snapshot store"),
                entry(f"{PRD_REF}#fast-restore", prd, "### Fast restore"),
                entry(req("history-listing"), spec, "### History listing"),
                entry(f"{DESIGN_REF}#retention-log", design, "## Retention log")]
    smallest = entry(f"{PRD_REF}#keep-history", prd, "### Keep history")
    sizes = [len(s["text"]) for s in sections]
    assert sizes == sorted(sizes, reverse=True) and sizes[-1] > len(smallest["text"]), sizes
    chain = dumped({"requirements": [sections[0], sections[3]], "design_choices": [sections[1], sections[4]],
                    "commitments": [sections[2], smallest]})
    assert chain > CHAIN_LIMIT and dumped({"requirements": sections[:1], "design_choices": sections[1:2],
                                           "commitments": sections[2:3]}) < CHAIN_LIMIT
    assert "restore-tests" in message, message
    assert re.search(r"64,?000", message), f"The refusal does not state the limit: {message}"
    assert states_size(message, chain, tolerance=12), (
        f"The refusal does not state the chain's size (~{chain}): {message}")
    for requirement, whole in [(sections[0], sizes[0] + sizes[1] + sizes[2]),
                               (sections[3], sizes[3] + sizes[4] + len(smallest["text"]))]:
        assert sized_at(message, requirement["ref"], whole, tolerance=12), (
            f"The refusal does not give {requirement['ref']}'s whole-chain size (~{whole}): {message}")
    in_order(message, sized_at, [(s["ref"], n) for s, n in zip(sections, sizes)])
    assert smallest["ref"] not in message, f"More than five sections are listed: {message}"
    assert re.search(r"split", message, re.I) and re.search(r"tighten|shorten|trim", message, re.I), (
        f"The refusal does not state the remedy: {message}")


@pytest.mark.parametrize("margin", [-60, 60], ids=["just-under", "just-over"])
def test_chain_limit_counts_only_the_chain(tmp_path, margin):
    """Red. The chain limit counts the chain alone. The restore requirement is padded so the
    restore test task's chain, with the history listing added at launch, lands 60 characters
    under or over 16,000 while its whole packet is thousands over. Under launches carrying that
    chain; over is refused naming the task and the chain's size, with no run. Today the limit
    counts the whole packet, so under is refused too."""
    added = {"acceptance_refs": [req("history-listing")]}
    spec, tasks = sized_plan(tmp_path, chain=CHAIN_LIMIT + margin, tasks=four_tasks, **added)
    root = sized_unit(tmp_path, spec, tasks)
    if margin < 0:
        packet = launched(root, "restore-tests", **added)
        assert chain_of(packet)["requirements"][0][2] == section_of(spec, "### Restore command")
        assert split_sizes(packet)[0] == CHAIN_LIMIT + margin
        assert dumped(packet) > CHAIN_LIMIT + 4000, dumped(packet)
    else:
        message = launch_refusal(root, "restore-tests", **added)
        assert "restore-tests" in message, message
        assert states_size(message, CHAIN_LIMIT + margin), (
            f"The refusal does not state the chain's size ({CHAIN_LIMIT + margin}): {message}")


def test_breakdown_close_refuses_a_task_whose_own_fields_push_the_rest_past_the_limit(tmp_path):
    """Red. The rest of the packet has its own 16,000-character limit, and breakdown close checks
    it. The restore test task's long verification puts the rest 400 over while its chain is small.
    Breakdown close refuses before any review round, naming the task, the rest's size and the
    limit, its largest fields largest first by serialized size (verification, then the worker
    authoring guidance and the test authoring guidance, larger first), and the shorten-or-split remedy; the
    other task, within both limits, is not named. Today breakdown close does not check size."""
    spec, tasks = sized_plan(tmp_path, rest=LIMIT + 400)
    root = sized_unit(tmp_path, spec, tasks, accept_plan=False)
    message = breakdown_refusal(root, tasks)
    assert "restore-tests" in message and "restore-code" not in message, message
    assert re.search(r"16,?000", message), f"The refusal does not state the limit: {message}"
    assert states_size(message, LIMIT + 400, tolerance=60), (
        f"The refusal does not state the rest's size (~{LIMIT + 400}): {message}")
    verification = next(t["verification"] for t in tasks if t["id"] == "restore-tests")
    guides = sorted([("authoring_guidance", dumped(guidance_text())),
                     ("test_authoring_guidance", dumped(guidance_text("test-authoring.md")))],
                    key=lambda field: field[1], reverse=True)
    in_order(message, field_at, [("verification", dumped(verification))] + guides)
    assert re.search(r"shorten|tighten|trim", message, re.I) and re.search(r"split", message, re.I), (
        f"The refusal does not state the remedy: {message}")


def test_launch_refuses_a_rest_grown_after_breakdown_naming_its_largest_fields(tmp_path, monkeypatch):
    """Red. Launch keeps its own check of the rest. The realistic way the rest grows after
    breakdown close accepted it is an installation update: the installed worker authoring
    guidance changes between close and launch. The test points ``handoff.__file__`` at a copied
    installation whose repository-grounding guidance is about 12,000 characters longer, as the
    guidance tests in test_workflow_handoff do, which pushes the rest past 16,000 with a small
    chain. (Launch-time --input-refs would need hundreds of extra references to grow the rest that
    far, so it is not the realistic route.) The refusal names the task, the rest's size and the
    limit, and the guidance as the largest field, before the test authoring guidance; no run is
    recorded. Today the refusal names no fields."""
    probe = tmp_path / "probe"
    probe.mkdir()
    through_spec(probe)
    into_implement(probe, default_tasks())
    base_rest = split_sizes(launch(probe, "restore-tests"))[1]
    root = sized_unit(tmp_path, SPEC, default_tasks())
    installation = tmp_path / "installation"
    docs = installation / "fbk-docs/workflow"
    docs.mkdir(parents=True)
    for name in ("test-authoring.md", "test-regions.md"):
        (docs / name).write_text(guidance_text(name), encoding="utf-8")
    original = guidance_text()
    bloated = original + "\n" + filler(12000, "grounding") + "\n"
    (docs / "repository-grounding.md").write_text(bloated, encoding="utf-8")
    monkeypatch.setattr(handoff, "__file__", str(installation / "fbk-scripts/fbk/workflow/handoff.py"))
    rest = base_rest + dumped(bloated) - dumped(original)
    assert rest > LIMIT
    message = launch_refusal(root, "restore-tests")
    assert "restore-tests" in message, message
    assert re.search(r"16,?000", message), f"The refusal does not state the limit: {message}"
    assert states_size(message, rest), f"The refusal does not state the rest's size ({rest}): {message}"
    in_order(message, field_at, [("authoring_guidance", dumped(bloated)),
                                 ("test_authoring_guidance", dumped(guidance_text("test-authoring.md")))])


def test_breakdown_close_names_every_oversized_task_in_one_refusal_and_accepts_nothing(tmp_path):
    """Red. Two tasks each over the rest limit: breakdown close refuses once, before any reviewer
    launches or review round is spent, naming both tasks, and the breakdown is not accepted.
    Today breakdown close accepts the plan."""
    through_spec(tmp_path)
    tasks = default_tasks()
    for planned, size in zip(tasks, (17000, 18000)):
        planned["verification"] = filler(size, planned["id"])
    message = breakdown_refusal(tmp_path, tasks)
    names_all(message, "restore-tests", "restore-code")
    assert re.search(r"16,?000", message), f"The refusal does not state the limit: {message}"
    assert not store.load(tmp_path, UNIT)["phases"]["breakdown"].get("evidence"), (
        "Breakdown was accepted with oversized tasks.")


def test_plan_just_under_both_limits_closes_and_launches(tmp_path):
    """Red. The restore test task's chain and rest are each 100 characters under 16,000, so its
    whole packet is near 32,000: breakdown close accepts the plan and the task launches with
    both parts at those sizes. Today the launch is refused because the whole packet is over."""
    spec, tasks = sized_plan(tmp_path, chain=CHAIN_LIMIT - 100, rest=LIMIT - 100)
    root = sized_unit(tmp_path, spec, tasks)
    assert split_sizes(launched(root, "restore-tests")) == (CHAIN_LIMIT - 100, LIMIT - 100)


def test_task_over_both_limits_gets_one_refusal_reporting_both(tmp_path):
    """Red. The restore test task's chain is 200 over and its rest 300 over. Breakdown close
    refuses once, reporting for it both the chain (its size, each linked requirement's whole-chain
    size, the largest sections) and the rest (its size and its largest field, the verification).
    Today breakdown close does not check size."""
    spec, tasks = sized_plan(tmp_path, chain=CHAIN_LIMIT + 200, rest=LIMIT + 300)
    root = sized_unit(tmp_path, spec, tasks, accept_plan=False)
    message = breakdown_refusal(root, tasks)
    assert "restore-tests" in message, message
    assert states_size(message, CHAIN_LIMIT + 200, tolerance=12), (
        f"The refusal does not state the chain's size (~{CHAIN_LIMIT + 200}): {message}")
    assert states_size(message, LIMIT + 300, tolerance=60), (
        f"The refusal does not state the rest's size (~{LIMIT + 300}): {message}")
    for ref, whole in chain_sizes(spec).items():
        assert sized_at(message, ref, whole, tolerance=12), (
            f"The refusal does not give {ref}'s whole-chain size (~{whole}): {message}")
    verification = next(t["verification"] for t in tasks if t["id"] == "restore-tests")
    assert field_at(message, "verification", dumped(verification)), (
        f"The refusal does not list the verification field with its size: {message}")


def test_end_to_end_shape_with_a_moderate_chain_and_rest_launches(tmp_path):
    """Red. The shape the end-to-end run hit: a chain of about 11,000 characters and a rest of
    about 13,000, about 24,000 in all. Each is within its own limit, so breakdown closes and the
    task launches with both parts at those sizes. Today the launch is refused, as in that run."""
    spec, tasks = sized_plan(tmp_path, chain=11000, rest=13000)
    root = sized_unit(tmp_path, spec, tasks)
    assert split_sizes(launched(root, "restore-tests")) == (11000, 13000)


# --- review round 1 of the two limits ------------------------------------------------------
#
# Lead rulings (2026-10-25, after review round 1):
# 1. Each input reference is judged on its own at breakdown close: one that does not resolve yet
#    (a future input with an ordered producer) does not drop the others' derived consumed paths;
#    only files that do not exist go without a hash.
# 2. The planned worker placeholder is 36 characters, a standard id's length, so close is the
#    stricter check: a plan that passes close never fails launch over a worker id up to 36.
# 3. A context that cannot be built at close (missing or empty guidance, a chain link launch
#    would refuse) is refused before any review round, naming the task and the reason.

ID_LENGTH = 36


def helper_tasks():
    """A producer test task writing a new helper, and the restore test task ordered after it whose
    input references hold an existing source file and that future helper."""
    linked = refs("restore-command", "history-listing")
    producer = task("helper-tests", "tests", ["tests/helpers.py"], linked)
    consumer = task("restore-tests", "tests", ["tests/test_restore.py"], linked)
    consumer["depends_on"] = ["helper-tests"]
    consumer["input_refs"] = ["src/listing.py", "tests/helpers.py"]
    return [producer, consumer, task("restore-code", "implementation", ["src/backup.py"], linked)]


def test_breakdown_close_counts_an_existing_input_beside_a_future_one(tmp_path):
    """Red (round 1 ruling 1). The restore test task's input references hold an existing file
    (src/listing.py) and a future one (tests/helpers.py, written by an ordered producer). Launch
    would carry both as consumed paths and the existing file's hash. Its verification is sized so
    that context's rest, counted with a 36-character worker id, is 10 over 16,000, and about 130
    under without the two consumed paths and the hash. Breakdown close must count them and refuse
    naming the task. Today the future reference makes close drop every input path, so it
    accepts."""
    probe = tmp_path / "probe"
    probe.mkdir()
    through_spec(probe)
    into_implement(probe, default_tasks())
    rest = {k: v for k, v in launch(probe, "restore-tests").items() if k != "traceability"}
    # The same context as launch would build it for the planned task, field by field.
    rest.update(worker_id="w" * ID_LENGTH, input_refs=["src/listing.py", "tests/helpers.py"],
                consumes=["src/listing.py", "tests/helpers.py"],
                consumed_files={"src/listing.py": evidence.file_hashes(probe, ["src/listing.py"])["src/listing.py"]},
                dependencies={"helper-tests": {}})
    tasks = helper_tasks()
    consumer = tasks[1]
    consumer["verification"] = filler(len(rest["verification"]) + LIMIT + 10 - dumped(rest), "checks")
    rest["verification"] = consumer["verification"]
    assert dumped(rest) == LIMIT + 10
    dropped = {**rest, "consumes": [], "consumed_files": {}}
    assert dumped(dropped) < LIMIT - 100, dumped(dropped)
    root = tmp_path / "unit"
    root.mkdir()
    feature(root)
    project_files(root)
    scope = root / f"{BASE}/scope.json"
    store.atomic_json(scope, {**store.read_json(scope), "creates": ["tests/helpers.py"]})
    for phase in ("intent", "design", "spec"):
        accept(root, phase)
    message = breakdown_refusal(root, tasks)
    assert "restore-tests" in message, message
    assert states_size(message, LIMIT + 10), f"The refusal does not state the rest's size ({LIMIT + 10}): {message}"


def test_breakdown_close_counts_the_worker_id_at_a_standard_ids_length(tmp_path):
    """Red (round 1 ruling 2). The restore test task's rest is 8 over 16,000 with a 36-character
    worker id and 8 under with the 20-character one the tests launch with, so a 20-character
    placeholder would let a plan through that a standard-length worker id then fails at launch.
    Breakdown close must refuse it, stating the 36-character size. Today the placeholder is 20
    characters long, so close accepts."""
    spec, tasks = sized_plan(tmp_path, rest=LIMIT + 8 - (ID_LENGTH - len("restore-tests-worker")))
    root = sized_unit(tmp_path, spec, tasks, accept_plan=False)
    message = breakdown_refusal(root, tasks)
    assert "restore-tests" in message, message
    assert states_size(message, LIMIT + 8, tolerance=0), (
        f"The refusal does not state the rest with a 36-character worker id ({LIMIT + 8}): {message}")


def test_a_plan_passing_close_launches_with_a_standard_length_worker_id(tmp_path):
    """Guard (round 1 ruling 2). A rest 8 under 16,000 with a 36-character worker id passes
    breakdown close, and the task launches with a 36-character worker id at exactly that size: the
    placeholder must not overcount either."""
    spec, tasks = sized_plan(tmp_path, rest=LIMIT - 8 - (ID_LENGTH - len("restore-tests-worker")))
    root = sized_unit(tmp_path, spec, tasks)
    worker = "a" * ID_LENGTH
    packet = mutate(root, handoff.start_task, "s", "restore-tests", worker, unit=UNIT)
    assert split_sizes(packet)[1] == LIMIT - 8


@pytest.mark.parametrize("contents", [None, "  \n"], ids=["missing", "empty"])
def test_breakdown_close_refuses_when_installed_guidance_cannot_be_read(tmp_path, monkeypatch, contents):
    """Red (round 1 ruling 3). With the installed worker authoring guidance missing or empty
    (``handoff.__file__`` pointed at a copied installation, as test_workflow_handoff's guidance
    test does), no task's context can be built. Breakdown close must refuse before any reviewer
    launches or review round is spent, naming a task and the guidance file, and accept nothing.
    Today the size check skips a task whose context cannot be built, so close accepts."""
    through_spec(tmp_path)
    installation = tmp_path / "installation"
    docs = installation / "fbk-docs/workflow"
    docs.mkdir(parents=True)
    for name in ("test-authoring.md", "test-regions.md"):
        (docs / name).write_text(guidance_text(name), encoding="utf-8")
    if contents is not None:
        (docs / "repository-grounding.md").write_text(contents, encoding="utf-8")
    monkeypatch.setattr(handoff, "__file__", str(installation / "fbk-scripts/fbk/workflow/handoff.py"))
    message = breakdown_refusal(tmp_path, default_tasks())
    assert "restore-tests" in message or "restore-code" in message, message
    assert "repository-grounding.md" in message, message
    assert not store.load(tmp_path, UNIT)["phases"]["breakdown"].get("evidence"), (
        "Breakdown was accepted though a task's context could not be built.")


# --- guides --------------------------------------------------------------------------------


def guide(name):
    return (ROOT_DOCS / "assets/fbk-docs/workflow" / name).read_text()


def test_breakdown_guide_states_anchored_requirement_links_and_coverage():
    """Red. The breakdown guide shows a task linking a requirement by anchor and states that
    every requirement needs an implementation task and a test task."""
    text = guide("breakdown.md")
    assert "spec.md#" in text, "The breakdown guide shows no anchored requirement link."
    assert re.search(r"every requirement", text, re.I), "The breakdown guide states no requirement coverage rule."


def test_handoffs_guide_describes_the_chain_and_the_oversize_refusal():
    """Red. The handoffs guide, which describes the task packet, names the traceability chain
    and what an oversize packet's refusal reports."""
    text = guide("handoffs.md")
    assert "traceability" in text, "The handoffs guide does not describe the packet's traceability chain."
    assert re.search(r"commitment", text, re.I) and re.search(r"design choice", text, re.I), text[:200]
    assert re.search(r"largest", text, re.I), "The handoffs guide does not describe the oversize refusal."


def sentences(text):
    return re.split(r"(?<=[.;])\s+", text)


def test_handoffs_guide_states_both_context_limits():
    """Red. The handoffs guide states the two limits: one sentence puts 16,000 on the chain, and
    one puts it on the rest of the packet (its other fields or guidance). Today it states a single
    limit on the whole packet."""
    said = [s for s in sentences(guide("handoffs.md")) if re.search(r"16,?000", s)]
    assert any(re.search(r"chain|traceability", s, re.I) for s in said), (
        f"The handoffs guide does not put the limit on the chain: {said}")
    assert any(re.search(r"\brest\b|remainder|other fields|everything else|guidance", s, re.I) for s in said), (
        f"The handoffs guide does not put the limit on the rest of the packet: {said}")


def test_breakdown_guide_says_breakdown_close_checks_the_context_size():
    """Red. The breakdown guide says closing breakdown checks each task's context size. Today it
    only says to split oversized packets."""
    said = [s for s in sentences(guide("breakdown.md")) if re.search(r"\bclos(e|es|ing)\b", s, re.I)]
    assert any(re.search(r"size|16,?000|oversiz|too large|limit", s, re.I) for s in said), (
        "The breakdown guide does not say breakdown close checks the task context size.")


def test_architecture_overview_describes_task_traceability():
    """Red. The architecture overview says breakdown close checks requirement coverage by tasks
    and that the task context carries the chain."""
    text = (ROOT_DOCS / "docs/architecture-overview.md").read_text()
    assert re.search(r"breakdown close[^.]*requirement", text, re.I), (
        "The architecture overview does not describe breakdown's requirement coverage.")
    assert re.search(r"task[^.]*(design choices|commitments)", text, re.I), (
        "The architecture overview does not say tasks carry design choices and commitments.")


# --- review round 1 findings ---------------------------------------------------------------
#
# Lead rulings (2026-10-23) on the cross-model review of the first build:
# 1. At launch, a chain link from an included requirement or design choice that lands in an
#    upstream document but misses an item of the correct section is refused, naming the task,
#    the document, the link and the reason; every document read while following the chain binds
#    the run.
# 2. An acceptance_refs entry into a spec file with both a line number and an anchor
#    (spec.md:1#x) is refused at breakdown close and at launch, naming the task and entry.
# 3. Following an ancestor's links, only that ancestor's own upstream documents and its own
#    ancestors' count; a link from a parent item into a child's document is not followed.
# 4. A literal duplicate requirement heading joins the single aggregate refusal.
# 5. A percent-encoded anchor resolving to a Requirements item is accepted.
# 6. A launch refusal for a missing anchor added at launch names the task.
# 7. An implementation task linking one of several requirements gets exactly its own chain.


def test_renamed_parent_design_choice_refuses_child_launch_and_restoring_it_launches_bound(tmp_path):
    """Red. After the child enters implement, the parent's linked design choice is renamed.
    Launch is refused naming the task, the document, the link as written and the reason; today
    the choice is silently dropped and launch succeeds. Restoring the heading lets launch
    succeed with the choice in the chain and its design file bound to the run, so a later
    change to that file makes the context stale."""
    child_through_spec(tmp_path)
    into_implement(tmp_path, child_tasks(), unit="child")
    overview = tmp_path / PARENT / "design/overview.md"
    original = overview.read_text()
    overview.write_text(original.replace("### Job state machine", "### Job states"))
    message = launch_refusal(tmp_path, "child-tests", unit="child")
    link = "../platform/design/overview.md#job-state-machine"
    names_all(message, "child-tests", link)
    assert f"{CHILD}/spec.md" in message or f"{PARENT}/design/overview.md" in message, (
        f"The refusal does not name the document: {message}")
    assert re.search(r"anchor|heading", message, re.I), message
    overview.write_text(original)
    packet = launch(tmp_path, "child-tests", unit="child")
    refs_in_chain = [ref for ref, _, _ in chain_of(packet)["design_choices"]]
    assert f"{PARENT}/design/overview.md#job-state-machine" in refs_in_chain, refs_in_chain
    run = store.load(tmp_path, "child")["task_runs"]["child-tests"]
    assert f"{PARENT}/design/overview.md" in run["inputs"], sorted(run["inputs"])
    overview.write_text(original.replace("Explicit job states serve", "Explicit, documented job states serve"))
    with pytest.raises(store.WorkflowError, match=r"(?i)changed|stale|refresh"):
        handoff.task_packet(tmp_path, store.load(tmp_path, "child"), "child-tests")


@pytest.mark.parametrize("anchor", ["history-listing", "checks"])
def test_line_and_anchor_spec_entry_is_refused_at_breakdown_close(tmp_path, anchor):
    """Red. spec.md:1#<anchor> combines a line number and an anchor; it is refused naming the
    task and entry. Today the line is stripped by the reference check while the requirement
    check skips the entry, so breakdown closes."""
    through_spec(tmp_path)
    tasks = default_tasks()
    bad = f"{SPEC_REF}:1#{anchor}"
    tasks[0]["acceptance_refs"].append(bad)
    message = breakdown_refusal(tmp_path, tasks)
    names_all(message, "restore-tests", bad)


@pytest.mark.parametrize("anchor", ["history-listing", "checks"])
def test_line_and_anchor_spec_entry_is_refused_at_launch(tmp_path, anchor):
    """Red. The same entry added at launch is refused naming the task and entry, with no run
    recorded. Today launch succeeds and the requirement silently leaves the chain."""
    through_spec(tmp_path)
    into_implement(tmp_path, split_tasks())
    bad = f"{SPEC_REF}:1#{anchor}"
    message = launch_refusal(tmp_path, "restore-tests", acceptance_refs=[bad])
    names_all(message, "restore-tests", bad)


STRAY_PARENT_DESIGN = PARENT_DESIGN.replace(
    "Explicit job states serve [Cancel jobs](../prd.md#cancel-jobs).",
    "Explicit job states serve [Cancel jobs](../prd.md#cancel-jobs); the console unit uses them for\n"
    "[Cancel from the console](../../child/prd.md#cancel-from-the-console).",
)


def test_parent_design_choice_link_into_the_child_is_not_followed(tmp_path):
    """Red. The parent's Job state machine mentions the child's commitment (an unrelated
    document to the parent, so its spec close ignores it). A child task linking its own
    Scheduler reuse and the parent's Cancel API carries the parent's commitments only; today
    the child's Cancel from the console joins the chain."""
    from .test_workflow_traceability import CHILD_DESIGN, CHILD_PRD, CHILD_SPEC, make_unit, write

    base = make_unit(tmp_path, "platform", kind="project")
    write(base, "prd.md", PARENT_PRD)
    write(base, "design/overview.md", STRAY_PARENT_DESIGN)
    write(base, "spec.md", PARENT_SPEC)
    for phase in ("intent", "design", "spec"):
        accept(tmp_path, phase, unit="platform")
    child = make_unit(tmp_path, "child", parent="platform")
    write(child, "prd.md", CHILD_PRD)
    write(child, "design/console.md", CHILD_DESIGN)
    write(child, "spec.md", CHILD_SPEC)
    project_files(tmp_path)
    for phase in ("intent", "design", "spec"):
        accept(tmp_path, phase, unit="child")
    into_implement(tmp_path, [
        task("child-tests", "tests", ["tests/test_restore.py"],
             [*refs("scheduler-reuse", base=CHILD), req("cancel-api", PARENT)]),
        task("button-tests", "tests", ["tests/test_listing.py"], refs("button-cancels", base=CHILD)),
        task("child-code", "implementation", ["src/backup.py"], refs("button-cancels", "scheduler-reuse", base=CHILD)),
    ], unit="child")
    packet = launch(tmp_path, "child-tests", unit="child")
    commitments = [ref for ref, _, _ in chain_of(packet)["commitments"]]
    assert commitments == [f"{PARENT}/prd.md#shared-scheduler", f"{PARENT}/prd.md#cancel-jobs"], (
        f"A parent item's link into the child was followed: {commitments}")
    assert chain_of(packet) == expected(
        requirements=[entry(req("scheduler-reuse", CHILD), CHILD_SPEC, "### Scheduler reuse"),
                      entry(req("cancel-api", PARENT), PARENT_SPEC, "### Cancel API")],
        design_choices=[entry(f"{CHILD}/design/console.md#reuse-scheduler", CHILD_DESIGN, "### Reuse scheduler"),
                        entry(f"{PARENT}/design/overview.md#job-state-machine", STRAY_PARENT_DESIGN,
                              "### Job state machine")],
        commitments=[entry(f"{PARENT}/prd.md#shared-scheduler", PARENT_PRD, "### Shared scheduler"),
                     entry(f"{PARENT}/prd.md#cancel-jobs", PARENT_PRD, "### Cancel jobs")],
    )


DUPLICATE_SPEC = COVERAGE_SPEC + """
## Notes

### Restore command

The command's history, under a heading that repeats the requirement's name.
"""


def test_literal_duplicate_requirement_heading_joins_the_aggregate_refusal(tmp_path):
    """Red. A literal duplicate of the Restore command heading makes its entries ambiguous; the
    one breakdown refusal names that entry as ambiguous together with the task without a
    requirement link and every uncovered requirement. Today the older unique-heading check
    refuses first and reports only the ambiguous reference."""
    through_spec(tmp_path, spec=DUPLICATE_SPEC)
    tasks = [
        task("core-tests", "tests", ["tests/test_restore.py"], refs("restore-command", "restore-progress")),
        task("core-code", "implementation", ["src/backup.py"], refs("restore-command", "history-listing")),
        task("docs-only", "implementation", ["src/listing.py"], refs()),
    ]
    message = breakdown_refusal(tmp_path, tasks)
    names_all(message, req("restore-command"), "docs-only")
    assert re.search(r"ambiguous", message, re.I), message
    for name, anchor in [("History listing", "history-listing"), ("Restore progress", "restore-progress"),
                         ("Listing order", "listing-order")]:
        assert lines_naming(message, name, anchor), f"{name} is not named: {message}"


ENCODED = f"{SPEC_REF}#history%2Dlisting"


def test_percent_encoded_requirement_anchor_is_accepted_at_breakdown_close(tmp_path):
    """Red. #history%2Dlisting decodes to History listing, a requirement; breakdown closes with
    it covering that requirement. Today the raw fragment fails the unique-heading check."""
    through_spec(tmp_path)
    tasks = default_tasks()
    for each in tasks:
        each["acceptance_refs"] = [*refs("restore-command"), ENCODED]
    write_tasks(tmp_path, tasks)
    accept(tmp_path, "breakdown")


def test_percent_encoded_requirement_anchor_added_at_launch_joins_the_chain(tmp_path):
    """Red. The encoded entry added at launch is accepted and History listing joins the chain.
    Today launch refuses the raw fragment."""
    through_spec(tmp_path)
    into_implement(tmp_path, split_tasks())
    packet = launch(tmp_path, "restore-tests", acceptance_refs=[ENCODED])
    assert chain_of(packet) == expected(requirements=[RESTORE, LISTING], design_choices=[SNAPSHOT, RETENTION],
                                        commitments=[FAST, HISTORY])


def test_missing_anchor_added_at_launch_is_refused_naming_the_task(tmp_path):
    """Red. An extra entry whose anchor no heading produces is refused naming the task and the
    entry, with no run recorded. Today the generic reference error omits the task."""
    through_spec(tmp_path)
    into_implement(tmp_path, split_tasks())
    bad = req("no-such-requirement")
    message = launch_refusal(tmp_path, "restore-tests", acceptance_refs=[bad])
    names_all(message, "restore-tests", bad)


def test_implementation_task_carries_only_its_own_requirements_chain(tmp_path):
    # Guard: the review found this untested, not broken; it passes on the step 8 build.
    """Guard. After checkpoint acceptance, an implementation task linking
    History listing alone carries that requirement, Retention log and Keep history, and none of
    the other three requirements, Snapshot store or Fast restore. Pins chains for
    implementation tasks and selection by linked requirement."""
    from .test_workflow_lifecycle import pass_checkpoint, run_test_tasks

    through_spec(tmp_path, spec=COVERAGE_SPEC)
    into_implement(tmp_path, [
        task("all-tests", "tests", ["tests/test_restore.py"],
             refs("restore-command", "history-listing", "restore-progress", "listing-order")),
        task("restore-code", "implementation", ["src/backup.py"],
             refs("restore-command", "restore-progress", "listing-order")),
        task("listing-code", "implementation", ["src/listing.py"], refs("history-listing")),
    ])
    run_test_tasks(tmp_path)
    pass_checkpoint(tmp_path)
    assert engine.implement_stage(tmp_path, store.load(tmp_path, UNIT)) == "writing-code"
    packet = launch(tmp_path, "listing-code")
    assert packet["stage"] == "implementation"
    assert chain_of(packet) == expected(
        requirements=[entry(req("history-listing"), COVERAGE_SPEC, "### History listing")],
        design_choices=[RETENTION], commitments=[HISTORY])


# --- review round 2 findings ---------------------------------------------------------------
#
# Lead rulings (2026-10-23):
# 1. A followed chain link resolving to an ancestor's upstream document (prd.md or a file under
#    its design folder) that no longer exists is refused at launch, naming the task, the link
#    and the reason.
# 2. Spec-anchor validation is deferred only for acceptance_refs; input_refs keep the older line
#    and heading checks.
# 4. Chains through a parent with design from a child without design, and through a
#    grandparent, are pinned exactly; a changed grandparent source makes the context stale.


def test_renamed_parent_design_file_refuses_child_launch_and_restoring_it_launches_bound(tmp_path):
    """Red. After the child enters implement, the parent's design/overview.md is renamed. The
    child requirement's link into it is refused at launch, naming the task, the link and that
    the document is missing; today the link is silently skipped and launch succeeds. After the
    file is restored, launch succeeds with the parent's design choice in the chain and the file
    bound to the run."""
    child_through_spec(tmp_path)
    into_implement(tmp_path, child_tasks(), unit="child")
    overview = tmp_path / PARENT / "design/overview.md"
    renamed = overview.with_name("renamed.md")
    overview.rename(renamed)
    message = launch_refusal(tmp_path, "child-tests", unit="child")
    names_all(message, "child-tests", "../platform/design/overview.md#job-state-machine")
    assert re.search(r"missing|exist|not found|no longer|cannot read", message, re.I), message
    renamed.rename(overview)
    packet = launch(tmp_path, "child-tests", unit="child")
    refs_in_chain = [ref for ref, _, _ in chain_of(packet)["design_choices"]]
    assert f"{PARENT}/design/overview.md#job-state-machine" in refs_in_chain, refs_in_chain
    run = store.load(tmp_path, "child")["task_runs"]["child-tests"]
    assert f"{PARENT}/design/overview.md" in run["inputs"], sorted(run["inputs"])


def test_input_ref_into_spec_with_a_bad_line_and_anchor_is_refused(tmp_path):
    """Red. input_refs keep the older line and heading checks: a spec.md reference whose line
    does not exist and whose anchor names no heading is refused at launch, with no run
    recorded. Today the spec-anchor exemption lets it through."""
    child_through_spec(tmp_path)
    into_implement(tmp_path, child_tasks(), unit="child")
    bad = f"{CHILD}/spec.md:999999#no-such-heading"
    message = launch_refusal(tmp_path, "child-tests", unit="child", input_refs=[bad])
    assert bad in message or "999999" in message, message


def test_encoded_anchor_inherited_in_acceptance_refs_still_launches(tmp_path):
    # Guard: the task's own acceptance_refs carry #history%2Dlisting, and with no input_refs
    # declared they also become its input_refs; keeping the older checks for input_refs must
    # not refuse this valid encoded requirement link.
    """Guard. A task whose accepted acceptance_refs hold the encoded History listing anchor
    launches and carries that requirement's chain."""
    through_spec(tmp_path)
    linked = [*refs("restore-command"), ENCODED]
    into_implement(tmp_path, [task("restore-tests", "tests", ["tests/test_restore.py"], linked),
                              task("restore-code", "implementation", ["src/backup.py"], linked)])
    packet = launch(tmp_path, "restore-tests")
    assert chain_of(packet) == expected(requirements=[RESTORE, LISTING], design_choices=[SNAPSHOT, RETENTION],
                                        commitments=[FAST, HISTORY])


CHILD_SPEC_NO_DESIGN = """\
# Console contract

## Requirements

### Button cancels

For [Cancel from the console](prd.md#cancel-from-the-console).
"""


def test_child_without_design_carries_a_designed_parent_requirements_design_choices(tmp_path):
    # Guard: the review found this untested, not broken; it passes on the current build.
    """Guard. A child without design links its own requirement (to its commitment) and the parent's
    Cancel API. The parent has design, so Cancel API's chain runs through the parent's Job state
    machine to Cancel jobs. Pins that the parent requirement's own unit decides whether design
    choices are followed, not the child's."""
    from .test_workflow_traceability import CHILD_PRD

    parent_and_child(tmp_path, child_spec=CHILD_SPEC_NO_DESIGN, child_has_design=False)
    project_files(tmp_path)
    for phase in ("intent", "spec"):
        accept(tmp_path, phase, unit="child")
    linked = [*refs("button-cancels", base=CHILD), req("cancel-api", PARENT)]
    into_implement(tmp_path, [task("child-tests", "tests", ["tests/test_restore.py"], linked),
                              task("child-code", "implementation", ["src/backup.py"], linked)], unit="child")
    packet = launch(tmp_path, "child-tests", unit="child")
    assert chain_of(packet) == expected(
        requirements=[entry(req("button-cancels", CHILD), CHILD_SPEC_NO_DESIGN, "### Button cancels"),
                      entry(req("cancel-api", PARENT), PARENT_SPEC, "### Cancel API")],
        design_choices=[entry(f"{PARENT}/design/overview.md#job-state-machine", PARENT_DESIGN,
                              "### Job state machine")],
        commitments=[entry(f"{CHILD}/prd.md#cancel-from-the-console", CHILD_PRD, "### Cancel from the console"),
                     entry(f"{PARENT}/prd.md#cancel-jobs", PARENT_PRD, "### Cancel jobs")],
    )


COMPANY = ".fbk/company"
COMPANY_PRD = """\
# Company platform

## Commitments

### Shared platform

Every team builds on one platform.
"""
COMPANY_DESIGN = """\
# Company design

## Design choices

### Platform program

A platform program serves [Shared platform](../prd.md#shared-platform).
"""
COMPANY_SPEC = """\
# Company contract

## Requirements

### Program charter

From [Platform program](design/overview.md#platform-program).
"""
MIDDLE_PRD = """\
# Job platform

## Commitments

### Cancel jobs

Any job can be cancelled.
"""
MIDDLE_DESIGN = """\
# Platform design

## Design choices

### Job state machine

Explicit job states serve [Cancel jobs](../prd.md#cancel-jobs) and the company's
[Shared platform](../../company/prd.md#shared-platform).
"""
MIDDLE_SPEC = """\
# Platform contract

## Requirements

### Cancel API

From [Job state machine](design/overview.md#job-state-machine).
"""
GRANDCHILD_PRD = """\
# Console cancel

## Commitments

### Cancel from the console

An operator cancels a job from the console.
"""
GRANDCHILD_DESIGN = """\
# Console design

## Design choices

### Console button

A button serves [Cancel from the console](../prd.md#cancel-from-the-console).
"""
GRANDCHILD_SPEC = """\
# Console contract

## Requirements

### Button cancels

From [Console button](design/console.md#console-button) and the parent's
[Job state machine](../platform/design/overview.md#job-state-machine).
"""


def three_generations(root):
    """company (project) > platform (project) > child (feature), each with design; the child
    in implement with a test task and an implementation task linking Button cancels."""
    from .test_workflow_traceability import make_unit, write

    for unit, parent, kind, documents in [
        ("company", None, "project", (COMPANY_PRD, COMPANY_DESIGN, COMPANY_SPEC, "overview.md")),
        ("platform", "company", "project", (MIDDLE_PRD, MIDDLE_DESIGN, MIDDLE_SPEC, "overview.md")),
        ("child", "platform", "feature", (GRANDCHILD_PRD, GRANDCHILD_DESIGN, GRANDCHILD_SPEC, "console.md")),
    ]:
        base = make_unit(root, unit, kind=kind, parent=parent)
        prd, design, spec, design_name = documents
        write(base, "prd.md", prd)
        write(base, f"design/{design_name}", design)
        write(base, "spec.md", spec)
        for phase in ("intent", "design", "spec"):
            accept(root, phase, unit=unit)
    project_files(root)
    linked = refs("button-cancels", base=CHILD)
    into_implement(root, [task("child-tests", "tests", ["tests/test_restore.py"], linked),
                          task("child-code", "implementation", ["src/backup.py"], linked)], unit="child")


def test_chain_reaches_a_grandparent_commitment(tmp_path):
    # Guard: the review found this untested, not broken; it passes on the current build.
    """Guard. The child's requirement links its own design choice and the parent's Job state machine,
    which links the grandparent's Shared platform; the chain carries all three units' items in
    first-appearance order."""
    three_generations(tmp_path)
    packet = launch(tmp_path, "child-tests", unit="child")
    assert chain_of(packet) == expected(
        requirements=[entry(req("button-cancels", CHILD), GRANDCHILD_SPEC, "### Button cancels")],
        design_choices=[entry(f"{CHILD}/design/console.md#console-button", GRANDCHILD_DESIGN, "### Console button"),
                        entry(f"{PARENT}/design/overview.md#job-state-machine", MIDDLE_DESIGN,
                              "### Job state machine")],
        commitments=[entry(f"{CHILD}/prd.md#cancel-from-the-console", GRANDCHILD_PRD, "### Cancel from the console"),
                     entry(f"{PARENT}/prd.md#cancel-jobs", MIDDLE_PRD, "### Cancel jobs"),
                     entry(f"{COMPANY}/prd.md#shared-platform", COMPANY_PRD, "### Shared platform")],
    )


def test_a_changed_grandparent_chain_source_makes_the_task_context_stale(tmp_path):
    # Guard: the review found this untested, not broken; it passes on the current build.
    """Guard. The grandparent's prd.md was read for the chain, so it is bound to the run; changing it
    makes the task context stale."""
    three_generations(tmp_path)
    launch(tmp_path, "child-tests", unit="child")
    assert f"{COMPANY}/prd.md" in store.load(tmp_path, "child")["task_runs"]["child-tests"]["inputs"]
    source = tmp_path / COMPANY / "prd.md"
    source.write_text(source.read_text().replace("Every team builds", "Every product team builds"))
    with pytest.raises(store.WorkflowError, match=r"(?i)changed|stale|refresh"):
        handoff.task_packet(tmp_path, store.load(tmp_path, "child"), "child-tests")


# --- review round 3 findings ---------------------------------------------------------------
#
# Lead rulings (2026-10-23):
# 1. A document read while following the chain whose parse reports unreadable lines (at
#    document level, or inside an item whose links are followed) refuses launch, naming the
#    task, the document and the line, before any of its links are used.
# 2. The routing the traversal used (each ancestor's design flag, and the lineage) is bound to
#    the run; a change makes task-context refuse as stale.
# 3. A missing or unreadable linked ancestor prd.md refuses launch, naming the task, the linking
#    item and the link.
# 4. An item's packet text keeps fenced examples (with heading-looking lines) and blockquotes.

PARENT_OVERVIEW = f"{PARENT}/design/overview.md"


@pytest.mark.parametrize("broken", [
    "Explicit job states serve [Cancel\njobs](../prd.md#cancel-jobs).",
    'Explicit job states serve [Cancel jobs](../prd.md#cancel-jobs "the parent commitment").',
], ids=["link-wrapped-across-lines", "link-with-a-title"])
def test_unreadable_link_in_a_followed_parent_design_choice_refuses_launch(tmp_path, broken):
    """Red. After the child enters implement, the parent's Job state machine (which the child's
    requirement links) has its commitment link rewritten outside the Markdown subset. Launch is
    refused naming the task, the parent design file and the line; today the parse report is
    ignored, the commitment is silently dropped and launch succeeds."""
    child_through_spec(tmp_path)
    into_implement(tmp_path, child_tasks(), unit="child")
    overview = tmp_path / PARENT_OVERVIEW
    text = overview.read_text()
    old = "Explicit job states serve [Cancel jobs](../prd.md#cancel-jobs)."
    assert old in text
    overview.write_text(text.replace(old, broken))
    line = overview.read_text().splitlines().index(broken.splitlines()[0]) + 1
    message = launch_refusal(tmp_path, "child-tests", unit="child")
    names_all(message, "child-tests", PARENT_OVERVIEW)
    lines = {line, line + 1} if "\n" in broken else {line}
    assert any(re.search(rf"\bline {n}\b", message) for n in lines), (
        f"The refusal does not name line {sorted(lines)} of {PARENT_OVERVIEW}: {message}")


def feature_parent_and_child(root):
    """A feature parent with design (so its routing can change), accepted through spec, and a
    child with design accepted through spec."""
    from .test_workflow_traceability import CHILD_DESIGN, CHILD_PRD, CHILD_SPEC, make_unit, write

    base = make_unit(root, "platform", kind="feature")
    write(base, "prd.md", PARENT_PRD)
    write(base, "design/overview.md", PARENT_DESIGN)
    write(base, "spec.md", PARENT_SPEC)
    for phase in ("intent", "design", "spec"):
        accept(root, phase, unit="platform")
    child = make_unit(root, "child", parent="platform")
    write(child, "prd.md", CHILD_PRD)
    write(child, "design/console.md", CHILD_DESIGN)
    write(child, "spec.md", CHILD_SPEC)
    project_files(root)
    for phase in ("intent", "design", "spec"):
        accept(root, phase, unit="child")


def test_a_parent_routed_to_skip_design_after_launch_makes_the_task_context_stale(tmp_path):
    """Red. The child task's chain went through the parent's design choice because the parent
    had design. The parent's design is reopened and its routing changed to skip design, with no
    document edited. The chain the traversal would now build differs, so task-context refuses as
    stale; today it silently drops the parent's design choice and serves the packet."""
    feature_parent_and_child(tmp_path)
    into_implement(tmp_path, child_tasks(), unit="child")
    packet = launch(tmp_path, "child-tests", unit="child")
    assert f"{PARENT_OVERVIEW}#job-state-machine" in [ref for ref, _, _ in chain_of(packet)["design_choices"]]
    reason = "The operator decided the platform needs no design."
    mutate(tmp_path, engine.approve, "s", "reopen", "design", reason, unit="platform")
    mutate(tmp_path, engine.reopen, "design", "s", reason, unit="platform")
    mutate(tmp_path, engine.route, "s", False, reason, unit="platform")
    assert store.load(tmp_path, "platform")["design"] is False
    with pytest.raises(store.WorkflowError, match=r"(?i)changed|stale|refresh"):
        handoff.task_packet(tmp_path, store.load(tmp_path, "child"), "child-tests")


def test_missing_parent_prd_refuses_launch_naming_the_task_item_and_link(tmp_path):
    """Red. After the child enters implement, the parent's prd.md is removed. Launch is refused
    naming the task, the item whose link reached it and that link; today the refusal is the
    bare "Cannot read ... for the traceability check"."""
    child_through_spec(tmp_path)
    into_implement(tmp_path, child_tasks(), unit="child")
    (tmp_path / PARENT / "prd.md").unlink()
    message = launch_refusal(tmp_path, "child-tests", unit="child")
    assert "child-tests" in message, f"The refusal does not name the task: {message}"
    pairs = [("Console button", "../../platform/prd.md#cancel-jobs"),
             ("Reuse scheduler", "../../platform/prd.md#shared-scheduler"),
             ("Job state machine", "../prd.md#cancel-jobs")]
    assert any(item in message and link in message for item, link in pairs), (
        f"The refusal does not name the linking item and its link: {message}")


FENCED_SPEC = """\
# Backup behavior

## Requirements

### Restore command

`backup restore <date>` restores the files, from [Snapshot store](design/storage.md#snapshot-store).

An example session:

```text
$ backup restore 2026-10-01
## Restored 2026-10-01
# 412 files
```

> Restores never overwrite a newer file.
> Not a heading either, just quoted text

The command exits non-zero when the date has no snapshot.

### History listing

`backup list` shows thirty days, from [Retention log](design/storage.md#retention-log).
"""

# Written out literally: a heading-aware helper would stop at the fenced "## Restored" line.
FENCED_RESTORE_TEXT = """\
### Restore command

`backup restore <date>` restores the files, from [Snapshot store](design/storage.md#snapshot-store).

An example session:

```text
$ backup restore 2026-10-01
## Restored 2026-10-01
# 412 files
```

> Restores never overwrite a newer file.
> Not a heading either, just quoted text

The command exits non-zero when the date has no snapshot."""


def test_packet_text_keeps_a_fenced_example_and_a_blockquote_inside_an_item(tmp_path):
    # Guard: the review found this untested, not broken; it passes on the current build.
    """Guard. The Restore command item holds a fenced example with heading-looking lines and a
    blockquote; the packet carries the item's whole text, verbatim, up to History
    listing."""
    through_spec(tmp_path, spec=FENCED_SPEC)
    into_implement(tmp_path, default_tasks())
    packet = launch(tmp_path, "restore-tests")
    requirements = packet["traceability"]["requirements"]
    assert [r["ref"] for r in requirements] == [req("restore-command"), req("history-listing")]
    assert requirements[0]["text"].strip() == FENCED_RESTORE_TEXT


# --- review round 4 follow-up --------------------------------------------------------------


def test_followup_launch_after_parent_routed_to_skip_design_is_refused(tmp_path):
    """After the child enters implement, the parent's design is reopened and routed to skip
    design before the child task launches. The child's requirement still links the parent's Job
    state machine, so launch is refused naming the task and that design choice."""
    feature_parent_and_child(tmp_path)
    into_implement(tmp_path, child_tasks(), unit="child")
    reason = "The operator decided the platform needs no design."
    mutate(tmp_path, engine.approve, "s", "reopen", "design", reason, unit="platform")
    mutate(tmp_path, engine.reopen, "design", "s", reason, unit="platform")
    mutate(tmp_path, engine.route, "s", False, reason, unit="platform")
    assert store.load(tmp_path, "platform")["design"] is False
    message = launch_refusal(tmp_path, "child-tests", unit="child")
    assert "child-tests" in message and re.search(r"job-state-machine|Job state machine", message), message


# --- Follow-up group C, review round 1 -----------------------------------------------------


def test_followup_c_parent_requirement_link_after_parent_routed_to_skip_design_is_refused(tmp_path):
    """Red (round 1 finding 1). The child's own requirements link only the child's design; the
    task also links the parent's Cancel API, which links the parent's Job state machine. After
    the parent is routed to skip design, launch is refused naming the task and that design
    choice, instead of carrying Cancel API with its design choice and commitments dropped."""
    from .test_workflow_traceability import CHILD_DESIGN, CHILD_PRD, CHILD_SPEC, make_unit, write

    own_only = CHILD_SPEC.replace(
        " and the parent's\n[Job state machine](../platform/design/overview.md#job-state-machine).", ".")
    assert own_only != CHILD_SPEC
    base = make_unit(tmp_path, "platform", kind="feature")
    write(base, "prd.md", PARENT_PRD)
    write(base, "design/overview.md", PARENT_DESIGN)
    write(base, "spec.md", PARENT_SPEC)
    for phase in ("intent", "design", "spec"):
        accept(tmp_path, phase, unit="platform")
    child = make_unit(tmp_path, "child", parent="platform")
    write(child, "prd.md", CHILD_PRD)
    write(child, "design/console.md", CHILD_DESIGN)
    write(child, "spec.md", own_only)
    project_files(tmp_path)
    for phase in ("intent", "design", "spec"):
        accept(tmp_path, phase, unit="child")
    into_implement(tmp_path, child_tasks([req("cancel-api", PARENT)]), unit="child")
    reason = "The operator decided the platform needs no design."
    mutate(tmp_path, engine.approve, "s", "reopen", "design", reason, unit="platform")
    mutate(tmp_path, engine.reopen, "design", "s", reason, unit="platform")
    mutate(tmp_path, engine.route, "s", False, reason, unit="platform")
    assert store.load(tmp_path, "platform")["design"] is False
    message = launch_refusal(tmp_path, "child-tests", unit="child")
    assert "child-tests" in message and re.search(r"job-state-machine|Job state machine", message), message


PARENT_SPEC_NO_DESIGN = """\
# Platform contract

## Requirements

### Scheduler API

For [Shared scheduler](prd.md#shared-scheduler).

### Cancel API

For [Cancel jobs](prd.md#cancel-jobs).
"""


def test_followup_c_link_to_a_supporting_file_in_a_no_design_parents_design_folder_launches(tmp_path):
    """Red (round 1 finding 9). The parent never had design but keeps a diagram in its design
    folder. A child requirement links its design choice and that diagram; spec close accepts it,
    and launch must too, since a diagram is not a design choice."""
    from .test_workflow_traceability import CHILD_DESIGN, CHILD_PRD, CHILD_SPEC, make_unit, write

    base = make_unit(tmp_path, "platform", kind="feature", design=False)
    write(base, "prd.md", PARENT_PRD)
    write(base, "spec.md", PARENT_SPEC_NO_DESIGN)
    write(base, "design/diagram.svg", "<svg xmlns='http://www.w3.org/2000/svg'/>\n")
    for phase in ("intent", "spec"):
        accept(tmp_path, phase, unit="platform")
    spec = CHILD_SPEC.replace("[Job state machine](../platform/design/overview.md#job-state-machine)",
                              "[diagram](../platform/design/diagram.svg)")
    assert spec != CHILD_SPEC
    child = make_unit(tmp_path, "child", parent="platform")
    write(child, "prd.md", CHILD_PRD)
    write(child, "design/console.md", CHILD_DESIGN)
    write(child, "spec.md", spec)
    project_files(tmp_path)
    for phase in ("intent", "design", "spec"):
        accept(tmp_path, phase, unit="child")
    into_implement(tmp_path, child_tasks(), unit="child")
    packet = launch(tmp_path, "child-tests", unit="child")
    assert f"{CHILD}/design/console.md#console-button" in [ref for ref, _, _ in chain_of(packet)["design_choices"]]


# --- Follow-up group C, review round 3 -----------------------------------------------------


def test_followup_c3_refused_shape_in_an_unlinked_sibling_of_a_followed_document_refuses_launch(tmp_path):
    """Red (round 3 finding 7). After the child enters implement, the parent's One scheduler,
    which the child's chain does not link, gains a tab-indented line. The parent design file is
    followed through Job state machine, so launch is refused naming the task, the file, the
    line and One scheduler, and no run is recorded."""
    child_through_spec(tmp_path)
    into_implement(tmp_path, child_tasks(), unit="child")
    overview = tmp_path / PARENT_OVERVIEW
    old = "A single scheduler serves [Shared scheduler](../prd.md#shared-scheduler)."
    text = overview.read_text()
    assert old in text
    overview.write_text(text.replace(old, old + "\n\tIndented with a tab."))
    line = overview.read_text().splitlines().index("\tIndented with a tab.") + 1
    message = launch_refusal(tmp_path, "child-tests", unit="child")
    names_all(message, "child-tests", PARENT_OVERVIEW, "One scheduler")
    assert re.search(rf"\bline {line}\b", message), f"The refusal does not name line {line}: {message}"
