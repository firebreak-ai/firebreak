"""Workflow facts and transitions. Mutating callers hold store.transaction."""

import uuid

from . import evidence as ev
from . import review_plan
from .store import SCHEMA_VERSION, WorkflowError, digest, discover, event, load, now, read_json, save, unit_dir


def initialize(root, unit, kind="feature", parent=None, design=True):
    if kind not in {"project", "feature"}:
        raise WorkflowError("Unit kind must be project or feature.")
    if any(c.isspace() for c in unit):
        raise WorkflowError(
            f"Unit names can't contain spaces: {unit!r}. Use {'-'.join(unit.split())!r}."
        )
    directory = unit_dir(root, unit)
    if (directory / "state.json").exists():
        raise WorkflowError(f"Unit {unit} already exists; use status to resume it.")
    if parent == unit:
        raise WorkflowError("A unit cannot be its own parent.")
    parent_evidence = accepted_parent(root, parent) if parent else None
    record = {
        "schema_version": SCHEMA_VERSION,
        "unit": unit,
        "kind": kind,
        "parent": parent,
        "parent_evidence": parent_evidence,
        "design": True if kind == "project" else design,
        "owner": None,
        "open_phase": None,
        "opened_at": None,
        "locks": {},
        "unlocks": [],
        "grants": [],
        "events": [],
        "observations": [],
        "workers": {},
        "phases": {
            p: {
                "evidence": None,
                "rounds": [],
                "round_limit": 3,
                "pending": None,
                "generation": 0,
            }
            for p in ev.REVIEWS
        },
    }
    record["review_plans"] = review_plan.initialize(root, ev.phases(record))
    event(record, "created", None, unit_kind=kind)
    save(root, record)
    return record


def phase_state(root, record):
    for phase in ev.phases(record):
        accepted = record["phases"][phase]["evidence"]
        if accepted:
            try:
                current = ev.revision(root, record, phase)
            except WorkflowError as exc:
                return phase, "stale", str(exc)
            if current != accepted["revision"] or not ev.supporting_current(
                root, accepted
            ):
                return (
                    phase,
                    "stale",
                    "Accepted inputs changed; reopen this phase with a recorded reason.",
                )
        else:
            return phase, "open" if record["open_phase"] == phase else "ready", ""
    return "closed", "closed", ""


def accepted_parent(root, parent):
    record = load(root, parent)
    accepted = record["phases"]["spec"]["evidence"]
    if not accepted:
        raise WorkflowError(
            f"Parent {parent} needs an accepted spec before this crossing."
        )
    for phase in ev.phases(record):
        evidence = record["phases"][phase]["evidence"]
        if (
            not evidence
            or evidence["revision"] != ev.revision(root, record, phase)
            or not ev.supporting_current(root, evidence)
        ):
            raise WorkflowError(
                f"Parent {parent} has unaccepted or changed {phase}; re-close it first."
            )
        if phase == "spec":
            break
    from .retrospective import require_phase_observations

    require_phase_observations(record)
    return {
        "unit": parent,
        "revision": accepted["revision"],
        "accepted_at": accepted["at"],
    }


def check_parent(root, record):
    if record["parent"]:
        current = accepted_parent(root, record["parent"])
        if current != record["parent_evidence"]:
            raise WorkflowError(
                f"Parent {record['parent']} changed; acknowledge-parent with the operator's reason."
            )


def ownership(record, session):
    if not session:
        raise WorkflowError(
            "A session id is required; pass --session or use Claude Code's session environment."
        )
    if record["owner"] not in {None, session}:
        raise WorkflowError(
            f"Unit {record['unit']} belongs to session {record['owner']}; use takeover with a reason."
        )


def observed_revision(root, record, phase):
    try:
        return ev.revision(root, record, phase)
    except WorkflowError as exc:
        # A missing artifact must still be repairable through an explicit reopen.
        return digest(
            {"unreadable": str(exc), "accepted": record["phases"][phase]["evidence"]}
        )


def grant_target(root, record, crossing, phase, tests=()):
    return digest(
        {
            "crossing": crossing,
            "phase": phase,
            "tests": sorted(tests),
            "revision": observed_revision(root, record, phase),
            "rounds": record["phases"][phase]["rounds"]
            if crossing == "close-over-findings"
            else None,
        }
    )


def approve(root, record, session, crossing, phase, reason, tests=(), rework=None):
    """Record the operator's approval of a crossing. An unlock names locked tests and
    carries their rework: per named test, whether its corrected form is expected to
    "fail" or "pass", and the commands the rework runs, each listing the named tests it
    covers."""
    ownership(record, session)
    if not reason.strip():
        raise WorkflowError("Record the operator's approval words as the reason.")
    if crossing not in {
        "start-implementation",
        "reopen",
        "unlock-test",
        "close-over-findings",
    }:
        raise WorkflowError("Unknown approval crossing.")
    if phase == ev.CHECKPOINT:
        if crossing != "close-over-findings" or "implement" not in ev.phases(record):
            raise WorkflowError(
                "The test checkpoint takes only close-over-findings approval, in a unit that runs implement."
            )
    elif phase not in ev.phases(record):
        raise WorkflowError("Approval names a phase this unit does not run.")
    if crossing == "start-implementation" and phase != "implement":
        raise WorkflowError("Implementation approval must name implement.")
    if crossing == "unlock-test" and test_outcome(root, record) in {"preservation", "no-tests"}:
        raise WorkflowError(
            "This unit's plan has no test task, since every requirement is review-only, so no test task "
            "exists to rework a test after an unlock. Reopen breakdown and plan a test task that owns the "
            "test, then re-enter implement, run that test task, and pass the test checkpoint."
        )
    if crossing == "unlock-test" and (not tests or set(tests) - record["locks"].keys()):
        raise WorkflowError("Unlock approval must name existing locked tests exactly.")
    if crossing != "unlock-test" and rework is not None:
        raise WorkflowError("Only an unlock approval carries rework commands.")
    if crossing == "unlock-test":
        rework = _unlock_rework(root, record, tests, rework)
        _refuse_conflicting_rework(record, tests, rework)
    grant = {
        "id": str(uuid.uuid4()),
        "crossing": crossing,
        "phase": phase,
        "target": grant_target(root, record, crossing, phase, tests),
        "tests": sorted(tests),
        "reason": reason,
        "at": now(),
        "consumed": False,
        **({"rework": rework} if crossing == "unlock-test" else {}),
    }
    record["grants"].append(grant)
    event(record, "approved", session, grant=grant)
    if crossing == "unlock-test":
        record["unlocks"] = sorted(set(record["unlocks"]) | set(tests))
        grant["consumed"] = True
        # The reworked tests need a fresh checkpoint; its rounds, budget, and generation stay.
        checkpoint = record["phases"][ev.CHECKPOINT]
        if checkpoint["evidence"]:
            checkpoint["evidence"] = None
            event(record, "test-checkpoint-cleared", session, grant_id=grant["id"], tests=sorted(tests))
        # The unit returns to writing tests over the code built so far.
        from .test_preparation import record_baseline

        record_baseline(root, record, session, "unlock approval")
    save(root, record)
    return grant


def _unlock_rework(root, record, tests, rework):
    """Validate an unlock's rework: every named test needs a test task that owns it, a
    stated outcome, and at least one command covering it."""
    tasks = read_json(unit_dir(root, record["unit"]) / "tasks.json")
    orphans = [path for path in sorted(tests)
               if not any(t.get("stage") == "tests" and ev.matches(path, t["files"]) for t in tasks)]
    if orphans:
        raise WorkflowError(
            f"No test task owns {', '.join(orphans)}, so nothing could rework it after an unlock. "
            "Reopen breakdown and add a test task that owns it, then re-enter implement, run that test "
            "task, and pass the test checkpoint, which locks the corrected test."
        )
    named = set(tests)
    usage = (
        'An unlock carries its rework as {"expected": {test: "fail" or "pass"}, "commands": '
        '[{"argv": [...], "tests": [...]}]}: name each unlocked test\'s expected outcome, and give '
        "each command the unlocked tests it covers."
    )
    if not isinstance(rework, dict) or set(rework) != {"expected", "commands"}:
        raise WorkflowError(usage)
    expected, commands = rework["expected"], rework["commands"]
    if not isinstance(expected, dict) or set(expected) != named or any(
            not isinstance(value, str) or value not in {"fail", "pass"} for value in expected.values()):
        raise WorkflowError(
            "State, for every unlocked test and no other, whether its corrected form is expected to "
            '"fail" (behavior not yet built) or "pass" (behavior already built). ' + usage
        )
    if not isinstance(commands, list) or not commands or any(
            not isinstance(c, dict) or set(c) != {"argv", "tests"}
            or not isinstance(c["argv"], list) or not c["argv"]
            or any(not isinstance(a, str) or not a.strip() for a in c["argv"])
            or not isinstance(c["tests"], list) or not c["tests"]
            or any(not isinstance(t, str) for t in c["tests"])
            for c in commands):
        raise WorkflowError(
            "Give each rework command only a nonempty argv and the unlocked tests it covers; its expected "
            "exit is derived from those tests' expected outcomes, never stated. " + usage
        )
    if len({tuple(c["argv"]) for c in commands}) != len(commands):
        raise WorkflowError("Each rework command must be distinct; list every test a command covers in one entry.")
    outside = sorted({t for c in commands for t in c["tests"]} - named)
    if outside:
        raise WorkflowError(
            f"Rework commands cover {', '.join(outside)}, which this unlock does not name; a rework command "
            "may cover only unlocked tests. Name those tests in the unlock, or narrow the command."
        )
    uncovered = sorted(named - {t for c in commands for t in c["tests"]})
    if uncovered:
        raise WorkflowError(
            f"No rework command covers {', '.join(uncovered)}; give each unlocked test a command that runs it."
        )
    return {
        "expected": dict(sorted(expected.items())),
        "commands": [{"argv": list(c["argv"]), "tests": sorted(set(c["tests"]))} for c in commands],
    }


def _refuse_conflicting_rework(record, tests, rework):
    """Refuse an unlock whose command repeats an outstanding approval's command array when
    the two would expect different exits, so no expectation is dropped silently."""
    pending = {"id": None, "crossing": "unlock-test", "tests": sorted(tests), "rework": rework}
    outcomes, entries = _outstanding_rework([*record["grants"], pending],
                                            set(record["unlocks"]) | set(tests))
    for argv in {tuple(entry["argv"]) for entry in entries}:
        same = [entry for entry in entries if tuple(entry["argv"]) == argv]
        if len({_derived_exit(outcomes, entry["tests"]) for entry in same}) > 1:
            covered = sorted({t for entry in same for t in entry["tests"]})
            raise WorkflowError(
                f"The rework command {' '.join(argv)} is approved to cover {', '.join(covered)} with outcomes "
                f"({', '.join(f'{t}: {outcomes[t]}' for t in covered)}) that no single exit code can meet. "
                "Give this unlock a different command for its tests."
            )


def _derived_exit(outcomes, tests):
    """A rework command's expected exit: zero when every test it covers is expected to
    pass, non-zero otherwise."""
    return 0 if all(outcomes[t] == "pass" for t in tests) else "nonzero"


def _outstanding_rework(grants, unlocks):
    """The effective approved rework for outstanding unlocks: each unlocked test's outcome
    from the latest approval naming it, and every approved command still covering a test
    whose latest approval it belongs to."""
    latest, outcomes = {}, {}
    for grant in grants:
        if grant["crossing"] == "unlock-test" and grant.get("rework"):
            for path in grant["tests"]:
                latest[path], outcomes[path] = grant["id"], grant["rework"]["expected"][path]
    entries = []
    for grant in grants:
        for command in (grant.get("rework") or {}).get("commands", []):
            live = [path for path in command["tests"] if path in unlocks and latest.get(path) == grant["id"]]
            if live:
                entries.append({"argv": command["argv"], "tests": command["tests"], "live": live})
    return outcomes, entries


def approved_rework(record):
    """The outstanding unlocks' effective rework, as the checkpoint reviewer reads it:
    each unlocked test's approved outcome, and each command with the tests it covers and
    its derived exit. None when no unlock with rework is outstanding."""
    outcomes, entries = _outstanding_rework(record["grants"], set(record["unlocks"]))
    if not entries:
        return None
    commands = {}
    for entry in entries:
        merged = commands.setdefault(tuple(entry["argv"]), {"argv": entry["argv"], "tests": set(), "live": set()})
        merged["tests"].update(entry["tests"])
        merged["live"].update(entry["live"])
    return {
        "expected": {path: outcomes[path] for path in sorted(record["unlocks"]) if path in outcomes},
        "commands": [{"argv": c["argv"], "tests": sorted(c["tests"]), "live": sorted(c["live"]),
                      "exit_code": _derived_exit(outcomes, c["tests"])} for c in commands.values()],
    }


def review_binding(record, phase):
    """What a review verdict depends on beyond its revision and sources: for the test
    checkpoint, the outstanding unlocks' approved outcomes and command coverage, which
    the reviewer judges the reworked tests against but which leave the locked revision
    alone. A cached round and a managed review round are reused only under the same one."""
    return approved_rework(record) if phase == ev.CHECKPOINT else None


def rework_commands(record, owned):
    """The approved rework commands covering outstanding unlocked tests that match the
    owned paths, each with the exit derived from the effective outcomes of the tests it
    covers. A test task's run uses them in place of the commands tasks.json declares; None
    when no unlock of an owned test is outstanding."""
    rework = approved_rework(record)
    selected = [c for c in (rework or {}).get("commands", []) if any(ev.matches(p, owned) for p in c["live"])]
    if not selected:
        return None
    return [{"argv": c["argv"], "exit_code": c["exit_code"]} for c in selected]


def consume(root, record, crossing, phase, tests=()):
    target = grant_target(root, record, crossing, phase, tests)
    for grant in reversed(record["grants"]):
        if (
            not grant["consumed"]
            and grant["target"] == target
            and grant["crossing"] == crossing
        ):
            grant["consumed"] = True
            return grant["id"]
    raise WorkflowError(
        f"Unit {record['unit']}, {phase}: approval required for {crossing} at this revision; "
        "record the operator's words with approve.",
        3,
    )


def enter(root, record, phase, session):
    ownership(record, session)
    if record.get("pending_repair"):
        raise WorkflowError(
            "A repair is pending; run recover-repair before entering a phase."
        )
    check_parent(root, record)
    current, status, reason = phase_state(root, record)
    if phase != current or status == "stale":
        raise WorkflowError(
            f"Unit {record['unit']}: {phase} cannot start; {current} is {status}. {reason}"
        )
    from .retrospective import require_phase_observations

    require_phase_observations(record)
    for other in discover(root):
        if other == record["unit"]:
            continue
        peer = load(root, other)
        if peer["owner"] == session and peer["open_phase"]:
            raise WorkflowError(
                f"Session already owns {other} {peer['open_phase']}; finish or suspend it first."
            )
    if record["open_phase"] == phase:
        review_plan.inherit(root, record, phase, session)
        record["owner"] = session
        event(record, "resumed", session, phase=phase)
        save(root, record)
        return status_report(root, record)
    if phase == "implement":
        consume(root, record, "start-implementation", phase)
    if phase == "breakdown" and record.get("task_runs"):
        # A new breakdown needs fresh assignments; the earlier ones stay in the task events.
        event(record, "task-assignments-superseded", session, tasks=sorted(record["task_runs"]),
              reason="A new breakdown requires fresh assignments; prior results remain in task events.")
        record["task_runs"] = {}
    review_plan.inherit(root, record, phase, session)
    # Entering implement records the writing-tests baseline the first time, and again
    # after a breakdown-or-earlier reopen, when the unit returns to writing tests over the
    # code built so far. Other entries and resumes never do: a baseline recorded late
    # would hide earlier edits.
    baseline = None
    if phase == "implement":
        if not any(e["event"] == "entered" and e.get("phase") == "implement" for e in record["events"]):
            baseline = "first entry into implement"
        elif _replanned_since_baseline(record):
            baseline = "re-entry into implement after a reopen or repair"
    record["owner"], record["open_phase"], record["opened_at"] = session, phase, now()
    event(record, "entered", session, phase=phase)
    if baseline:
        from .test_preparation import record_baseline

        record_baseline(root, record, session, baseline)
        from .test_preparation import record_outcome

        # A plan with no test task decides its outcome here, with the baseline.
        record_outcome(root, record, session)
    save(root, record)
    return status_report(root, record)


def test_outcome(root, record):
    """How implement treats the unit's tests: the outcome recorded when implement was
    entered with a plan that has no test task, "preservation" when scoped tests existed then
    and "no-tests" when none did; otherwise "tests" when tasks.json has a test task, and None
    before either. A recorded outcome wins over tasks.json, so editing the plan without
    reopening breakdown cannot change it; a breakdown-or-earlier reopen clears it, and
    re-entry decides it again."""
    outcome = None
    for row in record["events"]:
        if row["event"] == "test-outcome-recorded":
            outcome = row["outcome"]
        elif replanning(row):
            outcome = None
    if outcome:
        return outcome
    try:
        tasks = read_json(unit_dir(root, record["unit"]) / "tasks.json")
    except WorkflowError:
        return None
    return "tests" if any(task.get("stage") == "tests" for task in tasks) else None


def replanning(row):
    """Whether an event replans the unit: a reopen of breakdown or an earlier phase, or a
    contradiction repair that invalidated breakdown. Either clears the recorded test outcome
    and makes the next implement entry record the writing-tests baseline again."""
    if row["event"] == "reopened":
        return row.get("phase") in ev.PHASES[: ev.PHASES.index("breakdown") + 1]
    return (row["event"] == "repair-prepared" and row.get("repair_kind") == "contradiction"
            and "breakdown" in row.get("invalidated", []))


def _replanned_since_baseline(record):
    """Whether the unit was replanned after the latest writing-tests baseline was recorded."""
    latest = {"replanned": -1, "recorded": -1}
    for index, row in enumerate(record["events"]):
        if row["event"] == "writing-tests-baseline-recorded":
            latest["recorded"] = index
        elif replanning(row):
            latest["replanned"] = index
    return latest["replanned"] > latest["recorded"]


def reopen(root, record, phase, session, reason):
    ownership(record, session)
    if record.get("pending_repair"):
        raise WorkflowError("A repair is pending; run recover-repair before reopening.")
    if not reason.strip() or phase not in ev.phases(record):
        raise WorkflowError("Reopen needs a valid phase and a reason.")
    if not record["phases"][phase]["evidence"]:
        raise WorkflowError(
            f"{phase} has no accepted close to reopen; enter or resume it instead."
        )
    if any(p["pending"] for p in record["phases"].values()):
        raise WorkflowError(
            "A close is in progress; wait or use recover-close after stopping its process."
        )
    if any(record["workers"].values()):
        raise WorkflowError(
            "Workers are still active; stop or finish them before reopening."
        )
    from .test_preparation import save_locked_copies, violated_locks

    if phase == "implement" and record["locks"]:
        # Implementation close deleted the saved copies; they are saved again only from
        # tests that still match their locks, so a change is never made the locked truth.
        violated = violated_locks(root, record)
        if violated:
            raise WorkflowError(
                f"Locked tests no longer match their locks: {', '.join(violated)}. Restore their locked content, "
                "such as from git, so each matches the fingerprint in the unit's locks, then reopen implement."
            )
    grant = consume(root, record, "reopen", phase)
    later = ev.phases(record)[ev.phases(record).index(phase) :]
    if "breakdown" in later:
        # The checkpoint judged tests against the reopened plan; reopening implement alone keeps it.
        later.append(ev.CHECKPOINT)
    from .review_baseline import retained

    superseded = {name: retained(record["phases"][name]["evidence"])
                  for name in later if record["phases"][name]["evidence"]}
    for name in later:
        record["phases"][name]["evidence"] = None
        record["phases"][name]["generation"] += 1
        record["phases"][name].pop("budget_exhausted", None)
        record["phases"][name]["round_limit"] = (
            spent_rounds(record["phases"][name]) + 3
        )
    cleared = {}
    if ev.CHECKPOINT in later:
        # The checkpoint locks again on the replanned tests; reopening implement alone keeps the locks.
        cleared = clear_locks(root, record)
    elif phase == "implement" and record["locks"]:
        save_locked_copies(root, record, record["locks"])
    record["open_phase"], record["owner"] = None, None
    event(record, "reopened", session, phase=phase, reason=reason, grant_id=grant,
          superseded_evidence=superseded, **cleared)
    save(root, record)
    from .test_preparation import drop_discarded_copies

    return {**status_report(root, record), **(drop_discarded_copies(root, record) if cleared else {})}


def clear_locks(root, record):
    """Clear the test locks, unlocks, lock origin and saved copies when the unit is
    replanned, returning the cleared values for the replanning event. The caller saves,
    then deletes the set-aside copies with drop_discarded_copies."""
    from .test_preparation import discard_locked_copies

    # Set aside against the locks the saved state still holds, before they are cleared.
    discard_locked_copies(root, record)
    cleared = {"cleared_locks": record["locks"], "cleared_unlocks": record["unlocks"],
               "cleared_lock_origin": record.pop("lock_origin", None)}
    record["locks"], record["unlocks"] = {}, []
    return cleared


def takeover(root, record, session, reason):
    if not session or not reason.strip():
        raise WorkflowError("Takeover requires a session and a reason.")
    for unit in discover(root):
        if unit != record["unit"]:
            other = load(root, unit)
            if other["owner"] == session and other["open_phase"]:
                raise WorkflowError(
                    f"Session already owns {unit}; finish or suspend it before takeover."
                )
    event(record, "takeover", session, previous_owner=record["owner"], reason=reason)
    record["owner"] = session
    record["workers"] = {}
    save(root, record)


def suspend(root, record, session, reason):
    ownership(record, session)
    if (
        not reason.strip()
        or any(p["pending"] for p in record["phases"].values())
        or any(record["workers"].values())
    ):
        raise WorkflowError("Suspend needs a reason and no running close or workers.")
    event(record, "suspended", session, phase=record["open_phase"], reason=reason)
    record["owner"] = None
    save(root, record)


def lock_tests(root, record, session, red_result=None, preservation_reason=None, expected_files=None,
               persist=True):
    """The test checkpoint's lock of the scoped tests it reviewed; a caller passing
    persist=False saves the record with its own changes. Locking clears every unlock, and
    a locked test may change only when an unlock covers it."""
    ownership(record, session)
    if record["open_phase"] != "implement":
        raise WorkflowError("Enter implement before locking tests; the test checkpoint locks them.")
    declared = ev.scope(root, record["unit"])
    paths = ev.test_files(root, declared)
    if not paths:
        raise WorkflowError(
            "No tests match scope.json; write the behavior tests before locking."
        )
    # A region-bearing file's lock is its region's fingerprint, so its code above stays editable.
    updated = ev.test_fingerprints(root, declared, paths)
    if expected_files is not None and updated != expected_files:
        raise WorkflowError("Tests changed after review; review the current tests before locking.")
    if not preservation_reason and not ev.is_red(red_result):
        raise WorkflowError(
            "Show a failing behavioral check (a non-zero exit), or explain why these existing tests preserve behavior."
        )
    from .handoff import disposition_blockers, undispositioned

    # No later phase can add a test, so a test remedy is dispositioned before the suite locks.
    blocked = disposition_blockers(
        record, record["unit"], undispositioned(record, remedy_kind="test"),
        "Accepted suggestions whose remedy is a test have no recorded disposition",
    )
    if blocked:
        raise WorkflowError(blocked)
    # An empty region compares as a file that does not exist.
    held, previously = ev.held_tests(declared, updated), ev.held_tests(declared, record["locks"])
    for path in record["locks"]:
        if held.get(path) != previously.get(path) and path not in record["unlocks"]:
            raise WorkflowError(
                f"Locked test changed without approval: {path}; obtain an unlock first."
            )
    # A copy of each locked test, so a later change can be shown and restored; saved
    # before any lock state changes, so a failed save leaves the locks as they were.
    from .test_preparation import save_locked_copies

    save_locked_copies(root, record, updated)
    record["locks"] = updated
    record["unlocks"] = []
    record["lock_origin"] = ev.CHECKPOINT
    event(
        record,
        "tests-locked",
        session,
        origin=ev.CHECKPOINT,
        files=updated,
        red_check=red_result,
        preservation_reason=preservation_reason,
    )
    if persist:
        save(root, record)
    return {"locked": paths}


def verify_locks(root, record):
    if not record["locks"] or record["unlocks"]:
        raise WorkflowError(
            "Tests must be locked, with every unlock re-locked by the test checkpoint, before implementation closes."
        )
    declared = ev.scope(root, record["unit"])
    actual = ev.test_fingerprints(root, declared, record["locks"])
    if actual != record["locks"]:
        raise WorkflowError(
            "Locked tests changed; restore them, or obtain a scoped unlock and rework them through their test task."
        )
    if set(ev.held_tests(declared, ev.test_fingerprints(root, declared))) != set(ev.held_tests(declared, record["locks"])):
        raise WorkflowError(
            "The test set changed; review and lock the complete declared test set again."
        )


def checkpoint_locked(root, record):
    """Whether the tests are locked by a test checkpoint whose acceptance is current."""
    return bool(record["locks"] and record.get("lock_origin") == ev.CHECKPOINT
                and checkpoint_current(root, record))


def implement_stage(root, record):
    """Implement's stage, derived from recorded facts: writing-tests,
    ready-for-checkpoint, or writing-code. Writing code needs tests the test checkpoint
    locked, with no outstanding unlock and a current acceptance. An outstanding unlock
    keeps the unit writing tests until each test task owning an unlocked test has
    completed a run since that unlock was approved. Completeness walks every declared
    test task, not task_runs. A unit with no tests and no test tasks writes code from the
    start; one preserving existing tests is ready for the checkpoint from the start."""
    outcome = test_outcome(root, record)
    if outcome == "no-tests":
        return "writing-code"
    if not record["unlocks"] and checkpoint_locked(root, record):
        return "writing-code"
    if outcome == "preservation":
        # The recorded outcome has no test task to wait for, whatever tasks.json now lists.
        return "ready-for-checkpoint"
    from .handoff import _verify_completed

    runs = record.get("task_runs", {})
    tasks = read_json(unit_dir(root, record["unit"]) / "tasks.json")
    if record["unlocks"] and not _unlock_reworked(record, tasks):
        return "writing-tests"
    for task in tasks:
        if task.get("stage") != "tests":
            continue
        if runs.get(task["id"], {}).get("status") != "completed":
            return "writing-tests"
        try:
            _verify_completed(root, record, task["id"])
        except WorkflowError:
            return "writing-tests"
    return "ready-for-checkpoint"


def _unlock_reworked(record, tasks):
    """Whether every test task owning an unlocked test has returned a completed run after
    the latest approval that unlocked that test."""
    events = record["events"]
    for path in record["unlocks"]:
        approved = max((index for index, row in enumerate(events)
                        if row["event"] == "approved" and row["grant"]["crossing"] == "unlock-test"
                        and path in row["grant"]["tests"]), default=-1)
        for task in tasks:
            if task.get("stage") != "tests" or not ev.matches(path, task["files"]):
                continue
            returned = max((index for index, row in enumerate(events)
                            if row["event"] == "task-returned" and row.get("task") == task["id"]
                            and row.get("status") == "completed"), default=-1)
            if returned < approved:
                return False
    return True


def unrecorded_return(root, record):
    """Whether the unit still stands on the latest checkpoint pass with no baseline recorded
    since: that pass's locks, no outstanding unlock, and every scoped test matching its lock."""
    events = record["events"]
    passed, recorded = (max((i for i, row in enumerate(events) if row["event"] == name), default=-1)
                        for name in ("test-checkpoint-passed", "writing-tests-baseline-recorded"))
    if passed < recorded or not record["locks"] or record["unlocks"] or record.get("lock_origin") != ev.CHECKPOINT:
        return False
    try:
        declared = ev.scope(root, record["unit"])
        return ev.held_tests(declared, ev.test_fingerprints(root, declared)) == ev.held_tests(declared, record["locks"])
    except WorkflowError:
        return False


def accepted_checkpoint(record):
    """The latest test checkpoint acceptance the unit recorded, kept after an unlock, a
    reopen, or a governing change withdraws it; None before the first."""
    return next((row["evidence"] for row in reversed(record["events"])
                 if row["event"] == "test-checkpoint-passed"), None)


def checkpoint_current(root, record):
    """Whether the test checkpoint's acceptance matches its current revision; None when
    it has no acceptance."""
    accepted = record["phases"].get(ev.CHECKPOINT, {}).get("evidence")
    if not accepted:
        return None
    try:
        return accepted["revision"] == ev.revision(root, record, ev.CHECKPOINT)
    except WorkflowError:
        return False


def spent_rounds(work):
    """Rounds that count against the limit; a refused oversize brief is Firebreak's defect."""
    return sum(1 for r in work.get("rounds", []) if not r.get("unspent"))


def review_accepted(root, record, name):
    """Whether a review record holds acceptance that still counts. A checkpoint acceptance
    whose revision has moved is kept for history but no longer counts."""
    if name == ev.CHECKPOINT:
        return bool(checkpoint_current(root, record))
    return bool(record["phases"].get(name, {}).get("evidence"))


def review_budget_exhausted(work, accepted=None):
    """Whether a review is out of rounds; accepted overrides whether its evidence counts."""
    accepted = bool(work.get("evidence")) if accepted is None and work else accepted
    latest = (work.get("rounds") or [None])[-1] if work else None
    # A pass held for the author's sort is accepted by the next close without a round.
    held = bool(latest and latest.get("held_for_author") and not latest.get("error"))
    return bool(work and not accepted and not held and not work.get("pending")
                and (work.get("budget_exhausted")
                     or spent_rounds(work) >= work["round_limit"]))


def _spec_trim_line(record):
    """While the spec is open, what the trim did to its current draft."""
    work = record["phases"].get("spec") or {}
    trim = work.get("trim")
    if record.get("open_phase") != "spec" or not trim or trim["generation"] != work.get("generation"):
        return None
    from .spec_trim import summary

    return summary(trim)


def status_report(root, record):
    from .acceptance_drift import report as drift_report
    from .close import review_stages
    from .retrospective import phase_progress

    phase, state, reason = phase_state(root, record)
    parent_problem = ""
    try:
        check_parent(root, record)
    except WorkflowError as exc:
        parent_problem = str(exc)
    reviewed = review_in_focus(root, record, phase)
    work = record["phases"].get(reviewed, {})
    pending = work.get("pending")
    repair = record.get("pending_repair")
    exhausted = review_budget_exhausted(work, review_accepted(root, record, reviewed) if work else None)
    # The retrospective's phases section numbers every stored review record.
    position = list(record["phases"]).index(reviewed) + 1 if reviewed in record["phases"] else None
    retrospective = phase_progress(record)
    human_review = {
        "phase": reviewed,
        "rounds_used": spent_rounds(work),
        "round_limit": work["round_limit"],
        "budget_exhausted": work.get("budget_exhausted"),
        "latest_failure": str(work["rounds"][-1].get("error") or "Review did not establish acceptance.")[:1500],
        "suspend_note": suspend_note_after_escalation(record, reviewed),
        "history": f"retrospective {record['unit']} --section phases --index {position} --pointer /value/rounds",
        "latest_round": f"retrospective {record['unit']} --section phases --index {position} --pointer /value/rounds/-1",
    } if exhausted else None
    preparation = {}
    if record.get("open_phase") == "implement":
        from .test_preparation import progress

        preparation = {"test_preparation": progress(root, record)}
    from .handoff import undispositioned

    return {
        **preparation,
        # Accepted suggestions from earlier phases still awaiting a disposition; they block this phase's close.
        "undispositioned_suggestions": len(
            undispositioned(record, before=phase if phase in ev.PHASES else None)
        ),
        "acceptance_drift": drift_report(root, record),
        "unit": record["unit"],
        "retrospective": retrospective,
        "phase": phase,
        "status": "repairing"
        if repair
        else "reviewing"
        if pending
        else "stale"
        if parent_problem
        else "human-review-required"
        if exhausted
        else "retrospective-required"
        if state == "closed" and retrospective["pending"]
        else state,
        "reason": reason,
        "owner": record["owner"],
        "open_phase": record["open_phase"],
        "parent_problem": parent_problem,
        "close_in_progress": pending,
        "human_review": human_review,
        "next": "A repair is pending; use recover-repair to reconcile its recorded patch."
        if repair
        else "Wait for the running close; recover-close only after stopping it."
        if pending
        else parent_problem
        if parent_problem
        else review_escalation(record["unit"], reviewed, record)
        if exhausted
        else "Record your phase observations with " + retrospective["record"] + ". " + retrospective["guidance"]
        if retrospective["pending"]
        else "Work accepted."
        if phase == "closed"
        else f"{'Reopen' if state == 'stale' else 'Resume' if state == 'open' else 'Enter'} {phase}.",
        # Files each accepted phase changed after its passing review, accepted unreviewed.
        "unreviewed_changes": {
            p: v["evidence"]["unreviewed_changes"]
            for p, v in record["phases"].items()
            if (v.get("evidence") or {}).get("unreviewed_changes")
        },
        "review_rounds": {p: len(v["rounds"]) for p, v in record["phases"].items()},
        **({"spec_trim": spec_trim_line} if (spec_trim_line := _spec_trim_line(record)) else {}),
        # Each phase's latest round: what each council step or the external assessor did.
        "review_stages": {
            p: stages
            for p, v in record["phases"].items()
            if v["rounds"]
            and (stages := review_stages(v["rounds"][-1].get("result"))) is not None
        },
        "review_plans": record.get("review_plans", {}),
        "review_guidance": review_plan.context(record),
        "remaining_attempts": {
            p: max(0, v["round_limit"] - spent_rounds(v))
            for p, v in record["phases"].items()
        },
    }


def review_in_focus(root, record, phase):
    """The review a status speaks for: the current phase's, or the test checkpoint's while
    implement is open and the checkpoint is running or its latest review is unresolved
    (rejected or out of rounds), unless implement's own review is running, out of
    rounds, or more recent."""
    if phase == "implement":
        work, checkpoint = record["phases"]["implement"], record["phases"].get(ev.CHECKPOINT)
        if not checkpoint:
            return phase
        if checkpoint["pending"]:
            return ev.CHECKPOINT
        unresolved = bool(checkpoint["rounds"]) and not review_accepted(root, record, ev.CHECKPOINT)
        later = unresolved and (
            not work["rounds"]
            or checkpoint["rounds"][-1].get("at", "") >= work["rounds"][-1].get("at", "")
        )
        if later and not work["pending"] and not review_budget_exhausted(work):
            return ev.CHECKPOINT
    return phase


def suspend_note_after_escalation(record, phase):
    """The latest suspend note recorded after this phase's most recent human-review-required event.

    Returns None when the phase was never escalated or every suspend note predates
    the escalation; those notes described an earlier state of the work.
    """
    events = record.get("events", [])
    escalated = max(
        (
            i
            for i, e in enumerate(events)
            if e.get("event") == "human-review-required" and e.get("phase") == phase
        ),
        default=None,
    )
    if escalated is None:
        return None
    return next(
        (
            {"at": e.get("at"), "note": str(e.get("reason"))}
            for e in reversed(events[escalated + 1 :])
            if e.get("event") == "suspended" and str(e.get("reason") or "").strip()
        ),
        None,
    )


def review_escalation(unit, phase, record=None):
    """Next action for an exhausted review budget.

    With a record whose latest suspend note postdates the escalation, the note is
    the current state: lead with it and name the human's authorization as the open
    item. Without such a note the failure still has to be presented.
    """
    note = suspend_note_after_escalation(record, phase) if record else None
    if note:
        quoted = note["note"][:400] + ("..." if len(note["note"]) > 400 else "")
        return (
            f"Unit {unit}, {phase}: review budget exhausted. Human help is required. "
            f"The suspend note recorded after the exhaustion ({note['at']}) says: \"{quoted}\" "
            "Lead with that note; the open item is the human's authorization for another review round. "
            f"Once the human authorizes it, run extend-review {phase} {unit} --rounds 1 --reason \"<human's authorization>\". "
            "Incomplete reviews are not acceptance verdicts; present the failed stages again only if the human asks."
        )
    return (
        f"Unit {unit}, {phase}: review budget exhausted. Human help is required. "
        "Present failed stages, unresolved candidates, and any proposed scope changes for human review; "
        "incomplete reviews are not acceptance verdicts. Pause before more review rounds. "
        "Use extend-review only after the human authorizes another attempt."
    )


def route(root, record, session, design, reason):
    ownership(record, session)
    if not reason.strip() or record["open_phase"]:
        raise WorkflowError(
            "Change routing between phases and record the operator's reason."
        )
    if record["kind"] == "project" and not design:
        raise WorkflowError(
            "A project unit needs design to define its children's shared contracts."
        )
    if any(
        record["phases"][p]["evidence"]
        for p in ("design", "spec", "breakdown", "implement")
    ):
        raise WorkflowError(
            "Reopen design (or spec when design was skipped) before changing routing."
        )
    if phase_state(root, record)[1] == "stale":
        raise WorkflowError(
            "Accepted intent changed; reopen it before changing routing."
        )
    record["design"] = design
    event(record, "route-changed", session, design=design, reason=reason)
    # Routing is a dependency of all phase digests; an accepted intent remains
    # valid because routing changes do not change its subject or parent evidence.
    intent = record["phases"]["intent"]["evidence"]
    if intent:
        intent["revision"] = ev.revision(root, record, "intent")
    save(root, record)


def acknowledge_parent(root, record, session, reason):
    ownership(record, session)
    if not record["parent"] or not reason.strip():
        raise WorkflowError(
            "Parent acknowledgement requires a parent and the operator's reason."
        )
    if (
        (record["open_phase"] and record["owner"] is not None)
        or any(p["pending"] for p in record["phases"].values())
        or any(record["workers"].values())
        or record.get("pending_repair")
    ):
        raise WorkflowError(
            "Finish or recover running work and suspend the active phase before acknowledging the parent."
        )
    # Suspension keeps the draft phase and review history but releases ownership.
    # Updating this dependency leaves accepted child evidence stale; it must still
    # be explicitly reopened before work can resume.
    record["parent_evidence"] = accepted_parent(root, record["parent"])
    event(
        record,
        "parent-acknowledged",
        session,
        parent=record["parent_evidence"],
        reason=reason,
    )
    save(root, record)
