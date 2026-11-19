"""The test checkpoint: the review gate inside implement that judges the authored
tests and locks them on pass.

Its review record lives beside the phases at ``record["phases"]["test-checkpoint"]``
and goes through the same machinery as a phase close: round budget, reuse of an
unchanged round, escalation, approval over findings, recovery, and dispositions of
its test-remedy suggestions. It is not a phase: no slash command, no phase close,
no phase observation.

Breakdown writes tasks only, so the one route to the checkpoint is the test tasks
running in implement with no locks; the checkpoint is the only way to lock, and it
refuses locks that any other gate made.

The checkpoint's Python entry point is assumed to be
``close.close_checkpoint(root, unit, session, *, reviewer=None)``, mirroring
``close.close_phase``; ``run_checkpoint`` below is the one place that names it.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from fbk.workflow import (
    COMMANDS,
    cli,
    close,
    engine,
    evidence,
    handoff,
    hooks,
    retrospective,
    review,
    store,
)
from .test_workflow_commands import call
from .test_workflow_implement_stages import (
    CHECK,
    accept_breakdown_and_approve,
    edit_scope,
    edit_tasks,
    refusal,
    run_test_task,
    stage,
    start,
)
from .test_workflow_lifecycle import (
    accept,
    approve_unlock,
    blocking_review,
    clean_review,
    enter,
    enter_implementation,
    mutate,
    prepare_implementation,
    project as workflow_project,
    run_test_tasks,
)
from .test_workflow_phase_handoff import session_packet
from .refactor_plan import complete_refactor_tasks

project = workflow_project

CK = "test-checkpoint"
REPO = Path(__file__).resolve().parents[3]


# Helpers


def run_checkpoint(root, reviewer=clean_review, session="s"):
    entry = getattr(close, "close_checkpoint", None)
    assert entry is not None, "The checkpoint has no entry point (close.close_checkpoint) yet."
    return entry(root, "feature", session, reviewer=reviewer)


def checkpoint_refusal(root, reviewer=clean_review):
    """The checkpoint's refusal message, or None when it passes."""
    try:
        run_checkpoint(root, reviewer)
    except store.WorkflowError as exc:
        return str(exc)
    return None


def work(root):
    phases = store.load(root, "feature")["phases"]
    assert CK in phases, "The unit has no checkpoint review record."
    return phases[CK]


def counting(review_fn):
    calls = []

    def reviewer(*args):
        calls.append(args)
        return review_fn()

    return reviewer, calls


def must_not_run(*args):
    raise AssertionError("The recorded checkpoint review should be reused; no reader is spent.")


def ready_for_checkpoint(root):
    """Implement open with no locks and every test task completed: the normal route."""
    enter_implementation(root)
    run_test_task(root, "prepare-tests", "test-author")
    assert stage(root) == "ready-for-checkpoint"


def scoped_test_hashes(root):
    return evidence.file_hashes(root, evidence.expand(root, evidence.scope(root, "feature")["tests"]))


def checkpoint_revision(root):
    """The checkpoint's revision, or None when the revision cannot address the checkpoint."""
    try:
        return evidence.revision(root, store.load(root, "feature"), CK)
    except (ValueError, KeyError, store.WorkflowError):
        return None


def parses(command, *arguments):
    try:
        cli.parser_for(command).parse_args([*arguments, "--root", "/tmp", "--session", "s"])
    except SystemExit:
        return False
    return True


def cli_call(root, command, *arguments):
    assert parses(command, *arguments), f"{command} does not accept {list(arguments)}"
    return call(root, command, *arguments)


def suggestion(**fields):
    return {
        "title": "Cover repeated cancellation with a regression test.",
        "severity": "suggestion",
        "location": "tests/check.py",
        "evidence": "Only the first cancellation is exercised.",
        "remedy": "Add a second-cancel case to the suite.",
        **fields,
    }


def review_with(*findings):
    def reviewer():
        result = clean_review()
        result["review"]["findings"] = [dict(f) for f in findings]
        return result

    return reviewer


def record_disposition(root, finding, choice="defer", owner="test-lead"):
    text = "Defer the second-cancel case to the test lead."
    source = root / ".fbk/feature/decisions/checkpoint-disposition.md"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(text)
    entry = {"finding": handoff.finding_digest(finding), "disposition": choice}
    if choice == "defer":
        entry["owner"] = owner
    store.atomic_json(root / ".fbk/checkpoint-disposition.json", {
        "id": "checkpoint-disposition", "text": text, "phase": "implement", "kind": "process",
        "source": {"path": source.relative_to(root).as_posix(), "quote": text},
        "dispositions": [entry],
    })
    return call(root, "decision-record", "feature", "--request", ".fbk/checkpoint-disposition.json")


# The checkpoint record and state version


def test_initialize_creates_the_checkpoint_record_beside_the_phases(project):
    record = store.load(project, "feature")
    assert record["phases"].get(CK) == {
        "evidence": None, "rounds": [], "round_limit": 3, "pending": None, "generation": 0,
    }
    # Not a phase: no slash command, no phase close, no review-plan choice.
    assert CK not in evidence.PHASES
    assert CK not in evidence.phases(record)
    assert CK not in record.get("review_plans", {})


def test_initialize_writes_state_version_two(project):
    assert store.load(project, "feature")["schema_version"] == 2


def make_older_record(root, unit="feature"):
    path = root / f".fbk/{unit}/state.json"
    record = json.loads(path.read_text())
    record["schema_version"] = 1
    record["phases"].pop(CK, None)
    store.save(root, record)


def test_an_older_record_is_refused_with_the_archive_remedy(project):
    make_older_record(project)
    message = refusal(store.load, project, "feature")
    assert message is not None, "A version 1 record must be refused."
    assert "feature" in message
    assert ".fbk/archive/" in message
    assert "amendment" in message.lower()
    # Every unit is loaded by status with no unit named; the same remedy reaches the reader.
    assert ".fbk/archive/" in (refusal(call, project, "status") or "")


def test_hooks_surface_the_archive_remedy_for_an_older_record(project):
    make_older_record(project)
    edit = hooks.handle(project, {
        "hook_event_name": "PreToolUse", "tool_name": "Write", "session_id": "s",
        "cwd": str(project), "tool_input": {"file_path": str(project / "notes.txt")},
    })
    reason = edit.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")
    assert ".fbk/archive/" in reason, edit
    started = hooks.handle(project, {"hook_event_name": "SessionStart", "session_id": "s",
                                     "cwd": str(project)})
    context = started.get("hookSpecificOutput", {}).get("additionalContext", "")
    assert ".fbk/archive/" in context, started


def test_an_archived_older_unit_is_skipped(project):
    # Guard (passes today): the remedy the refusal names actually works.
    make_older_record(project)
    archive = project / ".fbk/archive"
    archive.mkdir()
    (project / ".fbk/feature").rename(archive / "feature")
    assert store.discover(project) == []
    allowed = hooks.handle(project, {
        "hook_event_name": "PreToolUse", "tool_name": "Write", "session_id": "s",
        "cwd": str(project), "tool_input": {"file_path": str(project / "notes.txt")},
    })
    assert allowed == {}


# The command and where it is registered


def test_the_checkpoint_command_is_registered(project):
    from fbk import COMMAND_MAP

    assert CK in COMMANDS
    assert COMMAND_MAP.get(CK) == "fbk.workflow.cli"


def test_the_shipped_dispatcher_lists_the_checkpoint_command():
    result = subprocess.run([sys.executable, str(REPO / "assets/fbk-scripts/fbk.py"), "--help"],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert CK in result.stdout.split()


@pytest.fixture(scope="module")
def installed_dispatcher(tmp_path_factory):
    sandbox = tmp_path_factory.mktemp("checkpoint-install")
    home, target_project = sandbox / "home", sandbox / "project"
    home.mkdir()
    target_project.mkdir()
    env = {**os.environ, "HOME": str(home), "CLAUDE_PROJECT_DIR": str(target_project)}
    env.setdefault("UV_CACHE_DIR", str(Path.home() / ".cache/uv"))
    env.pop("PYTHONPATH", None)
    env.pop("VIRTUAL_ENV", None)
    target = target_project / ".claude"
    result = subprocess.run(
        ["bash", str(REPO / "installer/install.sh"), "--source", str(REPO / "assets"),
         "--target", str(target)],
        cwd=target_project, env=env, capture_output=True, text=True, timeout=180,
    )
    assert result.returncode == 0, f"Install failed:\n{result.stdout}\n{result.stderr}"
    return target / "fbk-scripts/fbk.py", env


def test_the_installed_dispatcher_lists_the_checkpoint_command(installed_dispatcher):
    dispatcher, env = installed_dispatcher
    result = subprocess.run([sys.executable, str(dispatcher), "--help"], env=env,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert CK in result.stdout.split()


@pytest.mark.parametrize("command, arguments", [
    ("recover-close", [CK, "feature", "--reason", "The old checkpoint process stopped."]),
    ("extend-review", [CK, "feature", "--reason", "The operator authorized one more round."]),
    ("approve", ["feature", "close-over-findings", "--phase", CK, "--reason", "Accept the residual."]),
])
def test_review_escalation_commands_accept_the_checkpoint(command, arguments):
    assert parses(command, *arguments), f"{command} refuses the checkpoint"


@pytest.mark.parametrize("command", ["phase-enter", "phase-close"])
def test_the_checkpoint_is_not_a_phase_on_the_command_line(command):
    # Guard (passes today): the checkpoint has no phase entry or phase close.
    assert not parses(command, CK, "feature")
    assert f"fbk-{CK}" not in hooks.SKILLS


def test_the_cli_command_runs_the_checkpoint_and_locks(project, monkeypatch):
    ready_for_checkpoint(project)
    assert CK in COMMANDS, "test-checkpoint is not a registered command"
    monkeypatch.setattr(review, "review", clean_review)
    call(project, CK, "feature")
    record = store.load(project, "feature")
    assert record["phases"].get(CK, {}).get("evidence"), "The command did not record an accepted checkpoint."
    assert record["locks"] == scoped_test_hashes(project)


# When the checkpoint may run


def test_checkpoint_refuses_while_tests_are_still_being_written(project):
    enter_implementation(project)
    assert stage(project) == "writing-tests"
    reviewer, calls = counting(clean_review)
    message = checkpoint_refusal(project, reviewer)
    assert message is not None, "The checkpoint ran before every test task completed."
    assert calls == []
    assert work(project)["rounds"] == []
    assert not store.load(project, "feature")["locks"]


def test_checkpoint_refuses_outside_implement(project):
    accept(project, "intent")
    accept(project, "spec")
    enter(project, "breakdown")
    reviewer, calls = counting(clean_review)
    message = checkpoint_refusal(project, reviewer)
    assert message is not None, "The checkpoint ran during breakdown."
    assert calls == []
    assert work(project)["rounds"] == []


def lock_by_another_gate(root, origin):
    """Hand-made locks no checkpoint made: breakdown's old locks, or locks with no origin."""
    with store.transaction(root):
        record = store.load(root, "feature")
        record["locks"] = scoped_test_hashes(root)
        record["unlocks"] = []
        if origin is None:
            record.pop("lock_origin", None)
        else:
            record["lock_origin"] = origin
        store.save(root, record)


@pytest.mark.parametrize("origin", ["breakdown", None])
def test_checkpoint_refuses_locks_another_gate_made(project, origin):
    # Fails today: the checkpoint still runs on breakdown-origin or origin-less locks.
    ready_for_checkpoint(project)
    lock_by_another_gate(project, origin)
    reviewer, calls = counting(clean_review)
    message = checkpoint_refusal(project, reviewer)
    assert message is not None, f"The checkpoint ran on locks with origin {origin!r}."
    assert calls == []
    assert work(project)["rounds"] == [] and work(project)["evidence"] is None
    record = store.load(project, "feature")
    assert record.get("lock_origin") == origin, "The refused checkpoint re-stamped the locks."


@pytest.mark.parametrize("origin", ["breakdown", None])
def test_locks_another_gate_made_never_authorize_code(project, origin):
    # Fails today: breakdown-origin and origin-less locks still derive writing code.
    ready_for_checkpoint(project)
    lock_by_another_gate(project, origin)
    assert stage(project) != "writing-code", f"Locks with origin {origin!r} authorized code."
    assert start(project, "cancel", "implementer") is not None


# What a pass does


def test_pass_records_evidence_locks_tests_and_derives_writing_code(project):
    ready_for_checkpoint(project)
    assert not store.load(project, "feature")["locks"]
    assert checkpoint_refusal(project) is None
    record = store.load(project, "feature")
    accepted = record["phases"][CK]["evidence"]
    assert accepted, "A pass records accepted checkpoint evidence."
    assert accepted["revision"] == checkpoint_revision(project)
    assert accepted["review"]["review"]["findings"] == []
    checks = accepted.get("verification", accepted.get("checks"))
    assert checks and any(check["exit_code"] for check in checks), "The pass keeps its red evidence."
    assert record["locks"] == scoped_test_hashes(project)
    assert record["unlocks"] == []
    assert stage(project) == "writing-code"
    assert start(project, "cancel", "implementer") is None


def test_pass_records_its_own_event_and_needs_no_phase_observation(project):
    ready_for_checkpoint(project)
    assert checkpoint_refusal(project) is None
    record = store.load(project, "feature")
    assert not any(e["event"] == "closed" and e.get("phase") == CK for e in record["events"])
    assert any("checkpoint" in e["event"] for e in record["events"]), "The pass has no event of its own."
    assert retrospective.pending_phases(record) == []
    status = engine.status_report(project, record)
    assert status["retrospective"]["pending"] == []
    assert status["phase"] == "implement" and status["status"] == "open"
    # Nothing asks for an observation before implementation work starts.
    assert start(project, "cancel", "implementer") is None


def test_every_declared_check_runs_after_an_earlier_one_fails(project):
    marker = project / "second-check-ran"
    second = [sys.executable, "-c", f"open({str(marker)!r}, 'w').write('ran')"]
    edit_scope(project, checks=[CHECK, second])
    ready_for_checkpoint(project)
    assert not marker.exists()
    assert checkpoint_refusal(project) is None
    assert marker.exists(), "The checkpoint stopped at the first failing check."
    accepted = work(project)["evidence"]
    ran = [check["argv"] for check in accepted.get("verification", accepted.get("checks", []))]
    assert CHECK in ran and second in ran


def test_checkpoint_requires_red_when_test_tasks_expect_failure(project):
    ready_for_checkpoint(project)
    # The production change lands outside every task: every declared check now passes.
    (project / "src/app.py").write_text("release()")
    assert review.run_command(CHECK, project, 10)["exit_code"] == 0
    assert stage(project) == "ready-for-checkpoint"
    message = checkpoint_refusal(project)
    assert message is not None, "A checkpoint whose test tasks expect failure passed with no red check."
    assert work(project)["evidence"] is None
    assert work(project)["rounds"] == []
    assert not store.load(project, "feature")["locks"]


def test_checkpoint_accepts_preservation_when_every_test_task_expects_success(project):
    edit_tasks(project, lambda by_id, tasks: by_id["prepare-tests"].update(
        check_expectations=[{"argv": CHECK, "exit_code": 0}],
        verification="The existing cancellation check keeps passing."))
    for phase in ("intent", "spec", "breakdown"):
        accept(project, phase)
    # The behavior is already built before writing tests begins, so it sits in the baseline.
    (project / "src/app.py").write_text("release()")
    mutate(project, engine.approve, "s", "start-implementation", "implement", "Implement the agreed spec.")
    enter(project, "implement")
    assert start(project, "prepare-tests", "test-author") is None
    result = review.run_command(CHECK, project, 10)
    assert result["exit_code"] == 0
    returned = mutate(project, handoff.finish_task, "s", "prepare-tests", changed_files=[],
                      checks=[{"argv": CHECK, "exit_code": 0, "evidence": "Cancellation already releases."}],
                      unresolved=[], outcome="The existing check preserves the behavior.")
    assert returned["status"] == "completed"
    assert stage(project) == "ready-for-checkpoint"
    assert checkpoint_refusal(project) is None
    assert store.load(project, "feature")["locks"] == scoped_test_hashes(project)


# Revision: tests in, production code out


def test_revision_follows_tests_and_ignores_production_code(project):
    ready_for_checkpoint(project)
    before = checkpoint_revision(project)
    assert before is not None, "The checkpoint has no revision."
    (project / "src/app.py").write_text("def release():\n    return None\n")
    assert checkpoint_revision(project) == before
    (project / "tests/check.py").write_text("assert False, 'a different test'\n")
    assert checkpoint_revision(project) != before


def test_writing_code_keeps_the_accepted_checkpoint_current(project):
    ready_for_checkpoint(project)
    assert checkpoint_refusal(project) is None
    accepted = work(project)["evidence"]["revision"]
    assert start(project, "cancel", "implementer") is None
    (project / "src/app.py").write_text("release()")
    result = review.run_command(CHECK, project, 10)
    assert result["exit_code"] == 0
    returned = mutate(project, handoff.finish_task, "s", "cancel", changed_files=["src/app.py"],
                      checks=[{"argv": CHECK, "exit_code": 0, "evidence": "Release happens."}],
                      unresolved=[], outcome="Cancellation releases its resource.")
    assert returned["status"] == "completed"
    assert checkpoint_revision(project) == accepted
    assert stage(project) == "writing-code"
    complete_refactor_tasks(project)
    closed = close.close_phase(project, "feature", "implement", "s", reviewer=clean_review)
    assert closed["status"] == "retrospective-required"
    # Only implement asks for an observation; the checkpoint never does.
    pending = retrospective.pending_phases(store.load(project, "feature"))
    assert [row["phase"] for row in pending] == ["implement"]


# Blocking review and rework


def test_blocking_review_leaves_tests_unlocked_and_rework_returns_to_writing_tests(project):
    ready_for_checkpoint(project)
    message = checkpoint_refusal(project, blocking_review)
    assert message is not None and "Cancellation does not release the resource" in message
    record = store.load(project, "feature")
    assert record["phases"][CK]["evidence"] is None
    assert len(record["phases"][CK]["rounds"]) == 1
    assert not record["locks"]
    assert stage(project) in {"writing-tests", "ready-for-checkpoint"}
    assert start(project, "cancel", "implementer") is not None
    # The lead reworks through the test task, which returns the unit to writing tests.
    assert start(project, "prepare-tests", "rework-author") is None
    assert stage(project) == "writing-tests"


# Escalation: approval over findings, dispositions, recovery, budget


def test_approval_over_findings_reuses_the_checkpoint_review_and_locks(project):
    ready_for_checkpoint(project)
    reviewer, calls = counting(blocking_review)
    message = checkpoint_refusal(project, reviewer)
    assert message is not None and "approval required" in message
    assert refusal(mutate, project, engine.approve, "s", "close-over-findings", CK,
                   "Accept the documented cancellation residual.") is None
    assert checkpoint_refusal(project, must_not_run) is None
    record = store.load(project, "feature")
    assert len(calls) == 1
    assert record["phases"][CK]["evidence"]["outcome"] == "approved-over-findings"
    assert record["grants"][-1]["consumed"]
    assert record["locks"] == scoped_test_hashes(project)


def test_test_remedy_suggestion_is_dispositioned_before_the_lock(project):
    finding = suggestion(remedy_kind="test")
    ready_for_checkpoint(project)
    reviewer, calls = counting(review_with(finding))
    message = checkpoint_refusal(project, reviewer)
    assert message is not None and finding["title"] in message
    assert "decision-record feature --request <file> carrying dispositions" in message
    assert not store.load(project, "feature")["locks"]
    assert work(project)["evidence"] is None
    # The operator's disposition names the checkpoint's own suggestion.
    assert refusal(record_disposition, project, finding) is None
    assert checkpoint_refusal(project, must_not_run) is None
    assert len(calls) == 1
    assert store.load(project, "feature")["locks"] == scoped_test_hashes(project)


def test_artifact_remedy_suggestion_does_not_hold_the_lock(project):
    ready_for_checkpoint(project)
    assert checkpoint_refusal(project, counting(review_with(suggestion(remedy_kind="artifact")))[0]) is None
    assert store.load(project, "feature")["locks"] == scoped_test_hashes(project)


class Interrupted(BaseException):
    """The checkpoint process is killed mid-review; no handler runs."""


def test_an_interrupted_checkpoint_recovers(project):
    ready_for_checkpoint(project)

    def killed(*args):
        raise Interrupted()

    with pytest.raises(Interrupted):
        run_checkpoint(project, killed)
    assert work(project)["pending"], "The interrupted checkpoint left no pending reservation."
    status = engine.status_report(project, store.load(project, "feature"))
    assert status["status"] == "reviewing"
    # Pending-operation guards see the running checkpoint.
    assert refusal(mutate, project, engine.suspend, "s", "Pausing.") is not None
    assert refusal(mutate, project, handoff.start_task, "s", "prepare-tests", "other-author") is not None
    assert checkpoint_refusal(project) is not None
    cli_call(project, "recover-close", CK, "feature", "--reason", "The old checkpoint process stopped.")
    recovered = work(project)
    assert recovered["pending"] is None
    assert recovered["rounds"][-1]["error"].startswith("Interrupted review recovered")
    assert checkpoint_refusal(project) is None
    assert store.load(project, "feature")["locks"] == scoped_test_hashes(project)


def exhaust_checkpoint(root, monkeypatch):
    monkeypatch.setattr(review, "review", lambda *args: blocking_review())
    assert CK in COMMANDS, "test-checkpoint is not a registered command"
    for _ in range(3):
        with pytest.raises(store.WorkflowError):
            call(root, CK, "feature")


def test_budget_is_independent_and_exhaustion_escalates_through_resume(project, monkeypatch):
    ready_for_checkpoint(project)
    exhaust_checkpoint(project, monkeypatch)
    record = store.load(project, "feature")
    assert engine.spent_rounds(record["phases"][CK]) == 3
    assert record["phases"]["implement"]["rounds"] == []
    status = call(project, "status", "feature")[0]
    assert status["remaining_attempts"]["implement"] == 3
    assert status["remaining_attempts"].get(CK) == 0
    assert status["status"] == "human-review-required"
    assert status["human_review"]["phase"] == CK
    assert status["human_review"]["rounds_used"] == 3
    assert any(e["event"] == "human-review-required" and e.get("phase") == CK for e in record["events"])
    # The history pointer leads to the checkpoint's own rounds.
    index = re.search(r"--index (\d+)", status["human_review"]["history"]).group(1)
    entry = retrospective.packet(project, record, section="phases", index=index)
    assert entry["evidence"]["name"] == CK
    packet = handoff.continuation(project, record)
    assert packet["status"] == "human-review-required"
    assert packet["human_review"]["phase"] == CK
    stopped = hooks.handle(project, {"hook_event_name": "Stop", "session_id": "s", "cwd": str(project)})
    assert stopped.get("decision") == "block" and "Human help" in stopped["reason"]
    assert CK in stopped["reason"]
    # A fourth attempt spends nothing.
    reviewer, calls = counting(clean_review)
    assert checkpoint_refusal(project, reviewer) is not None
    assert calls == []
    # Resume in a fresh session: the escalation survives.
    call(project, "suspend", "feature", "--reason", "Awaiting the operator's call on the checkpoint findings.")
    incoming = session_packet(project, "fresh-session")
    assert incoming["status"] == "human-review-required"
    assert incoming["human_review"]["phase"] == CK
    call(project, "phase-enter", "implement", "feature")
    resumed = call(project, "status", "feature")[0]
    assert resumed["status"] == "human-review-required"
    assert f"extend-review {CK} feature --rounds 1" in resumed["next"]
    cli_call(project, "extend-review", CK, "feature", "--rounds", "1",
             "--reason", "The operator authorized one more checkpoint round.")
    extended = call(project, "status", "feature")[0]
    assert extended["human_review"] is None
    assert extended["remaining_attempts"][CK] == 1
    assert extended["remaining_attempts"]["implement"] == 3
    monkeypatch.setattr(review, "review", clean_review)
    call(project, CK, "feature")
    assert work(project)["evidence"]
    assert store.load(project, "feature")["locks"] == scoped_test_hashes(project)


# Status and continuation before tests run and after rejection


def test_status_and_continuation_report_the_checkpoint_before_tests_run(project):
    enter_implementation(project)
    status = call(project, "status", "feature")[0]
    assert status["review_rounds"].get(CK) == 0
    assert status["remaining_attempts"].get(CK) == 3
    assert (status["phase"], status["status"], status["human_review"]) == ("implement", "open", None)
    packet = handoff.continuation(project, store.load(project, "feature"))
    assert packet["status"] == "open" and packet["human_review"] is None


def test_status_after_a_rejected_checkpoint_spends_only_its_own_budget(project):
    ready_for_checkpoint(project)
    assert checkpoint_refusal(project, blocking_review) is not None
    status = call(project, "status", "feature")[0]
    assert status["review_rounds"].get(CK) == 1
    assert status["remaining_attempts"].get(CK) == 2
    assert status["remaining_attempts"]["implement"] == 3
    assert (status["status"], status["human_review"]) == ("open", None)
    packet = handoff.continuation(project, store.load(project, "feature"))
    assert packet["status"] == "open" and packet["human_review"] is None


# What the checkpoint reviewer is asked


def checkpoint_brief(files):
    try:
        return review.focus_brief("feature", CK, files)
    except KeyError:
        return None


def test_checkpoint_review_obligations_ask_whether_the_tests_are_useful():
    brief = checkpoint_brief(["tests/check.py", "src/app.py", ".fbk/feature/spec.md"])
    assert brief is not None, "The review brief has no checkpoint objectives."
    text = " ".join([brief["decision"], *brief["acceptance_obligations"]]).lower()
    for phrase in ("useful", "vacuous", "blocker", "assertion", "missing behavior", "build", "load"):
        assert phrase in text, phrase
    # The obligations differ from implement's, which judges delivered code.
    assert brief["decision"] != review.focus_brief("feature", "implement", [])["decision"]


def test_native_checkpoint_review_reads_the_tests_with_checkpoint_obligations(project, monkeypatch):
    ready_for_checkpoint(project)
    quote = "Cancellation must release the resource exactly once."
    source = project / ".fbk/feature/decisions/release-once.md"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(quote)
    store.atomic_json(project / ".fbk/release-once.json", {
        "id": "release-once", "text": quote, "phase": "implement", "kind": "governs",
        "source": {"path": source.relative_to(project).as_posix(), "quote": quote},
    })
    call(project, "decision-record", "feature", "--request", ".fbk/release-once.json")
    assert stage(project) == "ready-for-checkpoint"
    prompts = []

    def reader(snapshot, prompt, config):
        prompts.append(prompt)
        return {"review": {"summary": "Inspected the authored tests.", "findings": []}}

    monkeypatch.setattr(review, "claude_review", reader)
    assert checkpoint_refusal(project, reviewer=None) is None
    assert prompts, "The native reader was not asked."
    assert "vacuous" in prompts[0].lower()
    assert "tests/check.py" in prompts[0]
    assert quote in prompts[0]
    assert store.load(project, "feature")["locks"] == scoped_test_hashes(project)


# Review round 1 findings
#
# Each test below follows a witness case from the step 3a review.


SECOND_TEST_TASK = {
    "id": "release-tests", "stage": "tests",
    "description": "Check release happens exactly once.",
    "files": ["tests/release_check.py"], "depends_on": [],
    "acceptance_refs": [".fbk/feature/prd.md", ".fbk/feature/spec.md", ".fbk/feature/spec.md#cancel-once"],
    "verification": "A double release fails the check.",
}


def set_expectations(root, expectations, task="prepare-tests"):
    edit_tasks(root, lambda by_id, tasks: by_id[task].update(check_expectations=expectations))


def record_decision(root, decision_id, quote, *, kind="governs", supersedes=None, path="decision-sources.md"):
    """Record a decision under implement whose source file may already exist."""
    request = {
        "id": decision_id, "text": quote, "phase": "implement", "kind": kind,
        "source": {"path": path, "quote": quote},
    }
    if supersedes:
        request["supersedes"] = supersedes
    store.atomic_json(root / f".fbk/{decision_id}.json", request)
    return call(root, "decision-record", "feature", "--request", f".fbk/{decision_id}.json")


DECIDED = "Cancellation releases the resource exactly once."
REDECIDED = "Cancellation releases the resource once and reports the release."
PROCESS = "The lead runs the checkpoint after every test task completes."


def write_decision_sources(root):
    (root / "decision-sources.md").write_text(f"{DECIDED}\n{REDECIDED}\n{PROCESS}\n")


PASSES = [sys.executable, "-c", "raise SystemExit(0)"]


def code_done_after_checkpoint(root, owned=None, writes=None, removes=()):
    """The route to code with a checkpoint that can run again over it: the test task
    preserves a check that always passes, the checkpoint accepts and locks, and the
    implementation task then completes verified changes (by default src/app.py)."""
    edit_scope(root, checks=[PASSES])
    set_expectations(root, [{"argv": PASSES, "exit_code": 0}])
    if owned:
        edit_tasks(root, lambda by_id, tasks: by_id["cancel"].update(files=list(owned)))
    prepare_implementation(root)
    assert stage(root) == "writing-code"
    assert start(root, "cancel", "implementer") is None
    writes = {"src/app.py": "release()"} if writes is None else writes
    for path, text in writes.items():
        (root / path).write_text(text)
    for path in removes:
        (root / path).unlink()
    returned = mutate(root, handoff.finish_task, "s", "cancel", changed_files=sorted([*writes, *removes]),
                      checks=[{"argv": CHECK, "exit_code": 0, "evidence": "Release happens."}],
                      unresolved=[], outcome="Cancellation releases its resource.")
    assert returned["status"] == "completed"


def make_checkpoint_rerunnable(root):
    """A new governing decision makes the accepted checkpoint not current, so it runs again
    over code written since the writing-tests baseline."""
    write_decision_sources(root)
    record_decision(root, "release-once", DECIDED)
    assert stage(root) == "ready-for-checkpoint"


# Major: the lock binds the reviewed test inventory


def test_a_test_added_just_before_locking_is_never_locked(project, monkeypatch):
    ready_for_checkpoint(project)
    late = "tests/late_check.py"
    original = handoff.undispositioned_in
    fired = []

    def add_test_then_continue(*args, **kwargs):
        # Runs after the final snapshot check and immediately before the lock.
        if not fired:
            (project / late).write_text("assert True\n")
            fired.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(handoff, "undispositioned_in", add_test_then_continue)
    message = checkpoint_refusal(project)
    assert fired, "The witness seam before the lock never ran."
    record = store.load(project, "feature")
    assert late not in record["locks"], "An unreviewed test was locked."
    assert bool(record["locks"]) == bool(record["phases"][CK]["evidence"]), message


# Major: locks and acceptance commit together


def test_interruption_between_locking_and_acceptance_leaves_no_locks(project, monkeypatch):
    ready_for_checkpoint(project)
    original = close.event
    fired = []

    def killed_after_lock(record, kind, session, **fields):
        if (kind == "close-attempt" and fields.get("phase") == CK
                and fields.get("outcome") in {"pass", "approved-over-findings"}):
            fired.append(kind)
            raise Interrupted()
        return original(record, kind, session, **fields)

    monkeypatch.setattr(close, "event", killed_after_lock)
    with pytest.raises(Interrupted):
        run_checkpoint(project)
    assert fired, "The witness seam after locking never ran."
    record = store.load(project, "feature")
    assert record["phases"][CK]["evidence"] is None
    assert record["locks"] == {}, "Locks survived without checkpoint acceptance."
    assert stage(project) != "writing-code"


# Major: governing decisions bind the checkpoint's review


def test_checkpoint_revision_follows_governing_decisions_only(project):
    write_decision_sources(project)
    finding = suggestion(remedy_kind="test")
    ready_for_checkpoint(project)
    assert checkpoint_refusal(project, counting(review_with(finding))[0]) is not None
    before = checkpoint_revision(project)
    assert before is not None
    record_disposition(project, finding)
    assert checkpoint_revision(project) == before, "A disposition changed the checkpoint revision."
    record_decision(project, "checkpoint-routine", PROCESS, kind="process")
    assert checkpoint_revision(project) == before, "A process decision changed the checkpoint revision."
    (project / "src/app.py").write_text("def release():\n    return None\n")
    assert checkpoint_revision(project) == before
    # The source file already existed: only the recorded decision is new.
    record_decision(project, "release-once", DECIDED)
    governed = checkpoint_revision(project)
    assert governed != before, "A governing decision left the checkpoint revision unchanged."
    record_decision(project, "release-reported", REDECIDED, supersedes="release-once")
    assert checkpoint_revision(project) not in {before, governed}, (
        "Superseding a governing decision left the checkpoint revision unchanged.")


def test_a_new_governing_decision_voids_reuse_and_approval(project):
    write_decision_sources(project)
    ready_for_checkpoint(project)
    reviewer, calls = counting(blocking_review)
    assert checkpoint_refusal(project, reviewer) is not None
    assert refusal(mutate, project, engine.approve, "s", "close-over-findings", CK,
                   "Accept the documented cancellation residual.") is None
    record_decision(project, "release-once", DECIDED)
    message = checkpoint_refusal(project, reviewer)
    assert len(calls) == 2, "The review recorded before the decision was reused."
    assert message is not None, "The approval granted before the decision still applied."
    assert work(project)["evidence"] is None
    assert not store.load(project, "feature")["locks"]


# Major: the checkpoint and implement close never run at once


def test_implement_close_waits_for_a_running_checkpoint(project):
    # Guard: implement close also needs a current checkpoint, which a running rerun is not.
    code_done_after_checkpoint(project)
    make_checkpoint_rerunnable(project)
    implement_reviewer, implement_calls = counting(clean_review)
    attempts = []

    def checkpoint_reviewer(*args):
        attempts.append(refusal(close.close_phase, project, "feature", "implement", "s",
                                reviewer=implement_reviewer))
        return clean_review()

    outcome = checkpoint_refusal(project, checkpoint_reviewer)
    assert attempts and attempts[0] is not None, "Implement closed while the checkpoint was running."
    assert implement_calls == []
    assert outcome is None
    record = store.load(project, "feature")
    assert record["phases"]["implement"]["evidence"] is None
    assert record["phases"]["implement"]["rounds"] == []
    assert record["phases"][CK]["evidence"]


def test_the_checkpoint_waits_for_a_running_implement_close(project):
    # Guard: implement close needs a current checkpoint, which refuses to run again anyway.
    code_done_after_checkpoint(project)
    complete_refactor_tasks(project)
    before = work(project)
    checkpoint_reviewer, checkpoint_calls = counting(clean_review)
    attempts = []

    def implement_reviewer(*args):
        attempts.append(checkpoint_refusal(project, checkpoint_reviewer))
        return clean_review()

    closed = close.close_phase(project, "feature", "implement", "s", reviewer=implement_reviewer)
    assert closed["status"] == "retrospective-required"
    assert attempts and attempts[0] is not None, "The checkpoint ran while implement was closing."
    assert checkpoint_calls == []
    record = store.load(project, "feature")
    assert record["phases"][CK]["rounds"] == before["rounds"]
    assert record["phases"][CK]["evidence"] == before["evidence"]


# Major: continuation carries the checkpoint's review


def test_continuation_after_checkpoint_exhaustion_reports_its_review(project, monkeypatch):
    ready_for_checkpoint(project)
    exhaust_checkpoint(project, monkeypatch)
    packet = handoff.continuation(project, store.load(project, "feature"), max_chars=float("inf"))
    assert packet["remaining_attempts"] == 0, "Continuation reports implement's budget."
    titles = [finding["title"] for finding in packet["findings"]]
    assert "Cancellation does not release the resource" in titles
    assert "No review has run" not in str(packet.get("review_summary"))
    assert CK in packet["next"]


def test_accepted_review_handoffs_include_the_checkpoint(project):
    ready_for_checkpoint(project)
    assert checkpoint_refusal(project, blocking_review) is not None
    mutate(project, engine.approve, "s", "close-over-findings", CK, "Accept the documented residual.")
    assert checkpoint_refusal(project, must_not_run) is None
    reviews = handoff.accepted_reviews(project, store.load(project, "feature"))
    checkpoint = [item for item in reviews if item["phase"] == CK]
    assert checkpoint, "Accepted-review handoffs leave out the checkpoint."
    assert [f["title"] for f in checkpoint[0]["findings"]] == ["Cancellation does not release the resource"]


# Major: a contradiction repair resets the checkpoint's allowance


def test_contradiction_repair_resets_an_exhausted_checkpoint_budget(project, monkeypatch):
    from fbk.workflow import repair
    from .test_workflow_repairs import authorize

    authorize(project)
    ready_for_checkpoint(project)
    locked = store.load(project, "feature")["locks"]
    exhaust_checkpoint(project, monkeypatch)
    assert engine.review_budget_exhausted(work(project))
    repair.apply(project, "feature", "s", {
        "kind": "contradiction", "path": ".fbk/feature/spec.md",
        "before": "Release exactly once.", "after": "Release exactly once. Cancel returns true once.",
        "decision_id": "cancel-return",
    }, verifier=lambda *a: {"status": "equivalent", "evidence": "The quoted source settles it."})
    record = store.load(project, "feature")
    checkpoint = record["phases"][CK]
    assert checkpoint["generation"] == 1
    assert not engine.review_budget_exhausted(checkpoint), "The repaired checkpoint starts exhausted."
    assert "budget_exhausted" not in checkpoint
    assert checkpoint["round_limit"] == engine.spent_rounds(checkpoint) + 3
    # Existing phase behavior and the deliberately kept locks stay as they were.
    assert record["phases"]["implement"]["round_limit"] == 3
    assert record["locks"] == locked


def test_contradiction_repair_after_a_pass_clears_acceptance_and_clears_checkpoint_locks(project):
    # From an accepted checkpoint: the repair affects breakdown, so the checkpoint's
    # acceptance clears, its generation and allowance reset, and its locks clear as a
    # breakdown reopen clears them.
    from fbk.workflow import repair
    from .test_workflow_repairs import authorize

    authorize(project)
    ready_for_checkpoint(project)
    assert checkpoint_refusal(project) is None
    before = store.load(project, "feature")
    locks = before["locks"]
    assert locks and before.get("lock_origin") == CK
    spent = engine.spent_rounds(before["phases"][CK])
    assert spent == 1 and before["phases"][CK]["round_limit"] == 3
    repair.apply(project, "feature", "s", {
        "kind": "contradiction", "path": ".fbk/feature/spec.md",
        "before": "Release exactly once.", "after": "Release exactly once. Cancel returns true once.",
        "decision_id": "cancel-return",
    }, verifier=lambda *a: {"status": "equivalent", "evidence": "The quoted source settles it."})
    record = store.load(project, "feature")
    checkpoint = record["phases"][CK]
    assert checkpoint["evidence"] is None, "The repair left the checkpoint's acceptance in place."
    assert checkpoint["generation"] == 1
    assert checkpoint["round_limit"] == spent + 3
    assert not engine.review_budget_exhausted(checkpoint)
    assert record["locks"] == {} and not record.get("lock_origin")


# Minor: each command meets its own expectations


SUCCEEDS = [sys.executable, "-c", "raise SystemExit(0)"]
FAILS = [sys.executable, "-c", "raise SystemExit(1)"]


def flip(code_before, code_after, marker="flipped"):
    """A command whose exit changes once the marker exists, outside every task's files, so
    a test task can complete before the checkpoint sees a different outcome."""
    return [sys.executable, "-c",
            f"import os, sys; sys.exit({code_after} if os.path.exists({marker!r}) else {code_before})"]


def test_a_red_check_cannot_cover_another_commands_unmet_expectation(project):
    flipping = flip(0, 1)
    set_expectations(project, [{"argv": CHECK, "exit_code": "nonzero"}, {"argv": flipping, "exit_code": 0}])
    enter_implementation(project)
    run_test_tasks(project)
    (project / "flipped").write_text("")
    assert stage(project) == "ready-for-checkpoint"
    reviewer, calls = counting(clean_review)
    assert checkpoint_refusal(project, reviewer) is not None
    assert calls == [] and work(project)["evidence"] is None


def test_a_task_only_command_runs_and_meets_its_expectation(project):
    marker = project / "task-command-ran"
    task_only = [sys.executable, "-c", f"open({str(marker)!r}, 'w').write('ran')"]
    set_expectations(project, [{"argv": CHECK, "exit_code": "nonzero"}, {"argv": task_only, "exit_code": 0}])
    enter_implementation(project)
    run_test_tasks(project)
    marker.unlink()
    assert checkpoint_refusal(project) is None
    assert marker.exists(), "A command named only in a test task's expectations never ran."
    accepted = work(project)["evidence"]
    assert task_only in [c["argv"] for c in accepted.get("verification", accepted.get("checks", []))]


def test_a_wrong_exact_nonzero_exit_is_refused(project):
    flipping = flip(2, 1)
    set_expectations(project, [{"argv": flipping, "exit_code": 2}])
    enter_implementation(project)
    run_test_tasks(project)
    (project / "flipped").write_text("")
    assert review.run_command(flipping, project, 10)["exit_code"] == 1
    reviewer, calls = counting(clean_review)
    assert checkpoint_refusal(project, reviewer) is not None
    assert calls == [] and work(project)["evidence"] is None


def run_test_task_with(root, task, argv, code):
    assert start(root, task, f"{task}-author") is None
    returned = mutate(root, handoff.finish_task, "s", task, changed_files=[],
                      checks=[{"argv": argv, "exit_code": code, "evidence": "The declared check ran."}],
                      unresolved=[], outcome="The tests are written.")
    assert returned["status"] == "completed", returned


def test_conflicting_shared_expectations_are_refused(project):
    # Each test task completes against its own outcome; only the checkpoint holds both.
    flipping = flip(1, 0)
    set_expectations(project, [{"argv": flipping, "exit_code": 1}])
    edit_scope(project, creates=["tests/release_check.py"])
    edit_tasks(project, lambda by_id, tasks: tasks.insert(1, {
        **SECOND_TEST_TASK, "check_expectations": [{"argv": flipping, "exit_code": 0}]}))
    enter_implementation(project)
    run_test_task_with(project, "prepare-tests", flipping, 1)
    (project / "flipped").write_text("")
    run_test_task_with(project, "release-tests", flipping, 0)
    assert stage(project) == "ready-for-checkpoint"
    reviewer, calls = counting(clean_review)
    message = checkpoint_refusal(project, reviewer)
    assert message is not None and "disagree" in message
    assert calls == [] and work(project)["rounds"] == []


# Minor: the native pipeline reads declared production files and uses the second reader


def test_dual_reader_checkpoint_reads_declared_production_files(project, monkeypatch, tmp_path_factory):
    edit_tasks(project, lambda by_id, tasks: by_id["prepare-tests"].update(
        files=["tests/check.py", "src/app.py"]))
    ready_for_checkpoint(project)
    # The external reader lives outside the reviewed repository.
    outside = tmp_path_factory.mktemp("second-reader")
    capture = outside / "prompt.txt"
    script = outside / "second_reader.py"
    second = suggestion(title="Name the release in the cancellation assertion.",
                        location="tests/check.py:2", remedy_kind="artifact")
    script.write_text(
        "import json, re, sys\n"
        "prompt = sys.stdin.read()\n"
        f"open({str(capture)!r}, 'w').write(prompt)\n"
        "decoder = json.JSONDecoder()\n"
        "required = []\n"
        "for match in re.finditer(r'\"required_files\": ', prompt):\n"
        "    value, _ = decoder.raw_decode(prompt, match.end())\n"
        "    if isinstance(value, dict):\n"
        "        required = [path for paths in value.values() for path in paths]\n"
        "        break\n"
        f"print(json.dumps({{'summary': 'Read the tests.', 'findings': [{json.dumps(second)}],\n"
        "    'context': {'status': 'complete', 'inspected_files': required,\n"
        "                'supporting_files': [], 'missing_context': []}}))\n"
    )
    config = store.project_config(project)
    store.atomic_json(project / ".fbk/config.json",
                      {**config, "second_reader": [sys.executable, str(script)]})
    prompts = []

    def native_reader(root, prompt, config, **kwargs):
        prompts.append(prompt)
        if kwargs.get("schema") and "assessments" in json.dumps(kwargs["schema"]):
            return {"review": {"summary": "Verified the candidate.", "assessments": [
                {"finding_id": "external:1", "disposition": "supported",
                 "evidence": "tests/check.py:2 asserts on the file text.", "finding": second}]}}
        return {"review": {"summary": "Inspected the authored tests.", "findings": []}}

    monkeypatch.setattr(review, "claude_review", native_reader)
    outcome = checkpoint_refusal(project, reviewer=None)
    assert capture.exists(), "The configured second reader was not asked."
    assert outcome is None, (outcome, work(project)["rounds"][-1]["result"].get("second_reader_failure"))
    external = capture.read_text()
    assert "vacuous" in external.lower()
    for prompt in (prompts[0], external):
        assert "src/app.py" in prompt, "A declared production file is missing from required reading."
        # The traceback in the check output names src/app.py too; required reading is what counts.
        assert "src/app.py" in required_reading(prompt), (
            "A declared production file is missing from the reader's required_files.")
    result = work(project)["evidence"]["review"]
    assert result["shape"] == "dual"
    assert result["adjudication"] == "ran"
    assert [f["title"] for f in result["review"]["findings"]] == [second["title"]]


# Minor: the revision follows the accepted breakdown


def test_a_reaccepted_breakdown_with_identical_tests_changes_the_revision(project):
    prepare_implementation(project)
    before = checkpoint_revision(project)
    tests = scoped_test_hashes(project)
    mutate(project, engine.approve, "s", "reopen", "breakdown", "Clarify the cancellation task.")
    mutate(project, engine.reopen, "breakdown", "s", "Clarify the cancellation task.")
    edit_tasks(project, lambda by_id, tasks: by_id["cancel"].update(
        description="Implement cancellation and release, exactly once."))
    accept(project, "breakdown")
    mutate(project, engine.approve, "s", "start-implementation", "implement", "Proceed.")
    enter(project, "implement")
    assert scoped_test_hashes(project) == tests
    assert checkpoint_revision(project) != before


# Minor: accepted-checkpoint lifecycle


def test_unlock_clears_acceptance_and_keeps_rounds_generation_and_budget(project):
    ready_for_checkpoint(project)
    assert checkpoint_refusal(project, blocking_review) is not None
    mutate(project, engine.approve, "s", "close-over-findings", CK, "Accept the residual.")
    assert checkpoint_refusal(project, must_not_run) is None
    kept = {k: work(project)[k] for k in ("rounds", "generation", "round_limit")}
    approve_unlock(project, {"tests/check.py": "fail"}, [{"argv": CHECK, "tests": ["tests/check.py"]}],
                   reason="The cancellation test asserts the wrong call.")
    after = work(project)
    assert after["evidence"] is None
    assert {k: after[k] for k in kept} == kept


def test_implement_reopen_keeps_checkpoint_acceptance(project):
    from .test_workflow_lifecycle import observe_phase

    ready_for_checkpoint(project)
    assert checkpoint_refusal(project) is None
    assert start(project, "cancel", "implementer") is None
    (project / "src/app.py").write_text("release()")
    mutate(project, handoff.finish_task, "s", "cancel", changed_files=["src/app.py"],
           checks=[{"argv": CHECK, "exit_code": 0, "evidence": "Release happens."}],
           unresolved=[], outcome="Cancellation releases its resource.")
    complete_refactor_tasks(project)
    close.close_phase(project, "feature", "implement", "s", reviewer=clean_review)
    observe_phase(project, "implement")
    kept = work(project)
    mutate(project, engine.approve, "s", "reopen", "implement", "Revisit the delivered code.")
    mutate(project, engine.reopen, "implement", "s", "Revisit the delivered code.")
    after = work(project)
    assert after["evidence"] == kept["evidence"] and after["evidence"]
    assert after["generation"] == kept["generation"]


def test_breakdown_reopen_clears_acceptance_and_resets_generation(project):
    ready_for_checkpoint(project)
    assert checkpoint_refusal(project, blocking_review) is not None
    mutate(project, engine.approve, "s", "close-over-findings", CK, "Accept the residual.")
    assert checkpoint_refusal(project, must_not_run) is None
    mutate(project, engine.approve, "s", "reopen", "breakdown", "Replan the cancellation work.")
    mutate(project, engine.reopen, "breakdown", "s", "Replan the cancellation work.")
    after = work(project)
    assert after["evidence"] is None
    assert after["generation"] == 1
    assert after["round_limit"] == engine.spent_rounds(after) + 3


def test_breakdown_reopen_resets_an_exhausted_checkpoint_allowance(project, monkeypatch):
    ready_for_checkpoint(project)
    exhaust_checkpoint(project, monkeypatch)
    assert engine.review_budget_exhausted(work(project))
    mutate(project, engine.approve, "s", "reopen", "breakdown", "Replan the cancellation work.")
    mutate(project, engine.reopen, "breakdown", "s", "Replan the cancellation work.")
    after = work(project)
    assert not engine.review_budget_exhausted(after)
    assert after["generation"] == 1
    assert after["round_limit"] == engine.spent_rounds(after) + 3


# Review round 2 findings


def required_reading(prompt):
    """Every path in a reader prompt's required_files, parsed rather than searched."""
    decoder = json.JSONDecoder()
    for match in re.finditer(r'"required_files": ', prompt):
        value, _ = decoder.raw_decode(prompt, match.end())
        if isinstance(value, dict):
            return [path for paths in value.values() for path in paths]
        if isinstance(value, list):
            return value
    raise AssertionError("The reader prompt carries no required_files.")


# Major: a stale checkpoint acceptance does not authorize writing code


def test_a_new_governing_decision_after_a_pass_stops_writing_code(project):
    write_decision_sources(project)
    ready_for_checkpoint(project)
    assert checkpoint_refusal(project) is None
    assert stage(project) == "writing-code"
    record_decision(project, "release-once", DECIDED)
    assert work(project)["evidence"]["revision"] != checkpoint_revision(project)
    assert stage(project) != "writing-code", "A stale checkpoint acceptance still authorizes writing code."
    assert start(project, "cancel", "implementer") is not None


# Major: continuation and current-findings keep the checkpoint's unresolved review


BLOCKER = "Cancellation does not release the resource"


def assert_reports_checkpoint_review(root, remaining):
    packet = handoff.continuation(root, store.load(root, "feature"), max_chars=float("inf"))
    assert packet["remaining_attempts"] == remaining, "Continuation reports implement's budget."
    assert BLOCKER in [f["title"] for f in packet["findings"]], "Continuation hides the checkpoint's findings."
    assert "No review has run" not in str(packet.get("review_summary"))
    findings = call(root, "current-findings", "feature")
    assert findings["phase"] == CK, "Default current-findings reads implement's review."
    assert BLOCKER in [f["title"] for f in findings["findings"]]
    assert findings["remaining_attempts"] == remaining


def test_an_ordinary_rejection_stays_in_continuation_and_current_findings(project):
    ready_for_checkpoint(project)
    assert checkpoint_refusal(project, blocking_review) is not None
    assert_reports_checkpoint_review(project, 2)


def test_a_rejection_survives_suspend_and_resume(project):
    ready_for_checkpoint(project)
    assert checkpoint_refusal(project, blocking_review) is not None
    call(project, "suspend", "feature", "--reason", "Awaiting the operator on the checkpoint findings.")
    call(project, "phase-enter", "implement", "feature")
    assert_reports_checkpoint_review(project, 2)


def test_an_extended_checkpoint_keeps_its_unresolved_review_in_focus(project, monkeypatch):
    ready_for_checkpoint(project)
    exhaust_checkpoint(project, monkeypatch)
    cli_call(project, "extend-review", CK, "feature", "--rounds", "1",
             "--reason", "The operator authorized one more checkpoint round.")
    assert_reports_checkpoint_review(project, 1)


# Major: a checkpoint test remedy is dispositioned through the documented retrieval route


def test_a_checkpoint_test_remedy_is_dispositioned_from_the_listed_digest(project):
    finding = suggestion(remedy_kind="test")
    ready_for_checkpoint(project)
    reviewer, calls = counting(review_with(finding))
    assert checkpoint_refusal(project, reviewer) is not None
    listed = call(project, "continuation", "feature", "--section", "undispositioned_suggestions")
    items = [item for item in listed.get("undispositioned_suggestions") or []
             if item["title"] == finding["title"]]
    assert items, "continuation --section undispositioned_suggestions leaves out the checkpoint's suggestion."
    assert items[0]["phase"] == CK and items[0]["remedy_kind"] == "test"
    digest = items[0]["digest"]
    explicit = cli_call(project, "current-findings", "feature", "--phase", CK)
    shown = [f for f in explicit["findings"] if f["title"] == finding["title"]]
    assert shown and shown[0].get("digest") == digest, "current-findings gives no digest for the suggestion."
    text = "Defer the second-cancel case to the test lead."
    source = project / ".fbk/feature/decisions/listed-disposition.md"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(text)
    store.atomic_json(project / ".fbk/listed-disposition.json", {
        "id": "listed-disposition", "text": text, "phase": "implement", "kind": "process",
        "source": {"path": source.relative_to(project).as_posix(), "quote": text},
        "dispositions": [{"finding": digest, "disposition": "defer", "owner": "test-lead"}],
    })
    call(project, "decision-record", "feature", "--request", ".fbk/listed-disposition.json")
    assert checkpoint_refusal(project, must_not_run) is None
    assert len(calls) == 1
    assert store.load(project, "feature")["locks"] == scoped_test_hashes(project)


# Minor: red is any non-zero exit, not exit 1


RED_101 = [sys.executable, "-c", "raise SystemExit(101)"]


@pytest.mark.parametrize("expected", [101, "nonzero"])
def test_a_checkpoint_accepts_red_exit_101(project, expected):
    edit_scope(project, checks=[RED_101])
    set_expectations(project, [{"argv": RED_101, "exit_code": expected}])
    enter_implementation(project)
    assert start(project, "prepare-tests", "test-author") is None
    result = review.run_command(RED_101, project, 10)
    assert result["exit_code"] == 101
    returned = mutate(project, handoff.finish_task, "s", "prepare-tests", changed_files=[],
                      checks=[{"argv": RED_101, "exit_code": 101, "evidence": "Release is still missing."}],
                      unresolved=[], outcome="The check fails with exit 101.")
    assert returned["status"] == "completed"
    assert stage(project) == "ready-for-checkpoint"
    assert checkpoint_refusal(project) is None
    accepted = work(project)["evidence"]
    assert accepted
    assert [c["exit_code"] for c in accepted.get("verification", accepted.get("checks", []))] == [101]
    assert store.load(project, "feature")["locks"] == scoped_test_hashes(project)


# Review round 3 findings


# Major: re-locking reworked checkpoint tests does not skip the checkpoint


def test_every_owner_of_an_unlocked_test_reworks_it_after_the_latest_approval(project):
    # Guard: two ordered test tasks own tests/check.py. Readiness needs a completed run of
    # each owner after the latest unlock of that test; any one owner, or a run after an
    # earlier approval only, is not enough.
    edit_tasks(project, lambda by_id, tasks: tasks.insert(1, {
        "id": "release-tests", "stage": "tests",
        "description": "Extend the cancellation check with release-once cases.",
        "files": ["tests/check.py"], "depends_on": ["prepare-tests"],
        "acceptance_refs": [".fbk/feature/prd.md", ".fbk/feature/spec.md", ".fbk/feature/spec.md#cancel-once"],
        "verification": "A double release fails the check.",
        "check_expectations": [{"argv": CHECK, "exit_code": 1}],
    }))
    enter_implementation(project)
    run_test_tasks(project)
    assert checkpoint_refusal(project) is None

    def unlock_check(reason):
        approve_unlock(project, {"tests/check.py": "fail"}, [{"argv": CHECK, "tests": ["tests/check.py"]}],
                       reason=reason)

    def refused_without_review():
        reviewer, calls = counting(clean_review)
        assert checkpoint_refusal(project, reviewer) is not None
        assert calls == []

    unlock_check("The cancellation test asserts the wrong call.")
    run_test_task(project, "prepare-tests", "first-owner")
    assert stage(project) == "writing-tests", "One owner's rework settled the unlock."
    refused_without_review()
    run_test_task(project, "release-tests", "second-owner")
    assert stage(project) == "ready-for-checkpoint"

    # A later approval of the same test needs both owners again.
    unlock_check("The release-once case asserts the wrong count.")
    assert stage(project) == "writing-tests", "Runs after the earlier approval settled the later one."
    run_test_task(project, "prepare-tests", "first-owner-again")
    assert stage(project) == "writing-tests"
    refused_without_review()
    run_test_task(project, "release-tests", "second-owner-again")
    assert stage(project) == "ready-for-checkpoint"
    assert checkpoint_refusal(project) is None
    record = store.load(project, "feature")
    assert record["unlocks"] == [] and record.get("lock_origin") == CK


def test_unlock_rework_through_the_test_task_reruns_the_checkpoint_and_relocks(project):
    # Fails today: an outstanding unlock keeps the unit writing tests even after the rework
    # test task completes, and only the removed lock-tests command settled it.
    ready_for_checkpoint(project)
    assert checkpoint_refusal(project) is None
    approve_unlock(project, {"tests/check.py": "fail"}, [{"argv": CHECK, "tests": ["tests/check.py"]}],
                   reason="The cancellation test asserts the wrong call.")
    assert work(project)["evidence"] is None
    # The test task reworks the unlocked test; it still fails on the missing release.
    assert start(project, "prepare-tests", "rework-author") is None
    (project / "tests/check.py").write_text(
        "from pathlib import Path\nassert Path('src/app.py').read_text() == 'release()', 'not released'\n")
    result = review.run_command(CHECK, project, 10)
    assert result["exit_code"] == 1
    returned = mutate(project, handoff.finish_task, "s", "prepare-tests", changed_files=["tests/check.py"],
                      checks=[{"argv": CHECK, "exit_code": 1, "evidence": result["stderr"]}],
                      unresolved=[], outcome="The reworked test still fails on the missing release.")
    assert returned["status"] == "completed"
    record = store.load(project, "feature")
    assert record["phases"][CK]["evidence"] is None
    assert stage(project) == "ready-for-checkpoint", (
        "The completed rework does not let the checkpoint run again.")
    assert start(project, "cancel", "implementer") is not None
    assert checkpoint_refusal(project) is None
    record = store.load(project, "feature")
    assert record["locks"] == scoped_test_hashes(project) and record["unlocks"] == []
    assert record.get("lock_origin") == CK
    assert stage(project) == "writing-code"
    assert start(project, "cancel", "implementer") is None


# Major: a stale acceptance does not hide a later rejection or exhaustion


def test_rejection_and_exhaustion_after_a_stale_acceptance_stay_in_focus(project, monkeypatch):
    write_decision_sources(project)
    ready_for_checkpoint(project)
    assert checkpoint_refusal(project) is None
    record_decision(project, "release-once", DECIDED)
    monkeypatch.setattr(review, "review", lambda *args: blocking_review())
    with pytest.raises(store.WorkflowError):
        call(project, CK, "feature")
    # One round passed, one rejected: one attempt left.
    assert_reports_checkpoint_review(project, 1)
    with pytest.raises(store.WorkflowError):
        call(project, CK, "feature")
    status = call(project, "status", "feature")[0]
    assert status["status"] == "human-review-required", "A stale acceptance hides the checkpoint's exhaustion."
    assert status["human_review"]["phase"] == CK
    stopped = hooks.handle(project, {"hook_event_name": "Stop", "session_id": "s", "cwd": str(project)})
    assert stopped.get("decision") == "block" and CK in stopped["reason"]
    packet = handoff.continuation(project, store.load(project, "feature"), max_chars=float("inf"))
    assert packet["status"] == "human-review-required"
    assert packet["human_review"]["phase"] == CK
    assert BLOCKER in [f["title"] for f in packet["findings"]]


# Major: a reused review covers only the check output it assessed


def test_changed_red_output_after_a_disposition_needs_a_fresh_review(project, tmp_path_factory):
    # The check imports a helper from outside the repository, so its output can change
    # with no repository source change.
    outside = tmp_path_factory.mktemp("check-helper")
    (outside / "release_helper.py").write_text("def released():\n    return False\n")
    (project / "tests/check.py").write_text(
        f"import sys\nsys.path.insert(0, {str(outside)!r})\nimport release_helper\n"
        "assert release_helper.released(), 'the resource was not released'\n")
    finding = suggestion(remedy_kind="test")
    ready_for_checkpoint(project)
    assert "AssertionError" in review.run_command(CHECK, project, 10)["stderr"]
    reviewer, calls = counting(review_with(finding))
    assert checkpoint_refusal(project, reviewer) is not None
    record_disposition(project, finding)
    (outside / "release_helper.py").unlink()
    changed = review.run_command(CHECK, project, 10)
    assert changed["exit_code"] == 1 and "ModuleNotFoundError" in changed["stderr"]
    assert stage(project) == "ready-for-checkpoint"
    checkpoint_refusal(project, reviewer)
    record = store.load(project, "feature")
    assert len(calls) == 2, "The review of the assertion failure was reused for the import failure."
    if record["locks"]:
        accepted = record["phases"][CK]["evidence"]
        output = " ".join(c["stderr"] for c in accepted.get("verification", accepted.get("checks", [])))
        assert "ModuleNotFoundError" in output


# Review round 4 findings


def external_helper_check(root, outside):
    """A check whose output depends on a helper outside the repository."""
    (outside / "release_helper.py").write_text("def released():\n    return False\n")
    (root / "tests/check.py").write_text(
        f"import sys\nsys.path.insert(0, {str(outside)!r})\nimport release_helper\n"
        "assert release_helper.released(), 'the resource was not released'\n")


# Major: with a current acceptance, a changed check output does not reopen the checkpoint.
# Lead ruling (round 8): the checkpoint runs again only after an unlock, a reopen, or a
# governing change makes it not current.


def test_changed_output_alone_does_not_rerun_a_current_checkpoint(project, tmp_path_factory):
    outside = tmp_path_factory.mktemp("check-helper")
    external_helper_check(project, outside)
    ready_for_checkpoint(project)
    assert checkpoint_refusal(project) is None
    record = store.load(project, "feature")
    accepted, locks = record["phases"][CK]["evidence"], record["locks"]
    (outside / "release_helper.py").unlink()
    assert "ModuleNotFoundError" in review.run_command(CHECK, project, 10)["stderr"]
    reviewer, calls = counting(blocking_review)
    assert_rerun_refused(project, reviewer, calls, accepted, locks)


# Minor: a timed-out check does not stop the checks after it


def test_a_timed_out_check_is_followed_by_the_next_check_and_blocks_acceptance(project):
    slow = [sys.executable, "-c", "import time; time.sleep(3); raise SystemExit(1)"]
    marker = project / "after-timeout-ran"
    after = [sys.executable, "-c", f"open({str(marker)!r}, 'w').write('ran')"]
    edit_scope(project, checks=[slow, after])
    ready_for_checkpoint(project)
    config = store.project_config(project)
    store.atomic_json(project / ".fbk/config.json", {**config, "check_timeout": 1})
    reviewer, calls = counting(clean_review)
    message = checkpoint_refusal(project, reviewer)
    assert marker.exists(), "The check after a timed-out check never ran."
    assert message is not None, "A checkpoint with a timed-out check was accepted."
    assert work(project)["evidence"] is None


# Review round 5 findings: a running implementation worker writes only while the
# checkpoint's acceptance is current, or during an outstanding unlock


def production_write(root, worker):
    from .test_workflow_test_preparation import write_permission

    return write_permission(root, "src/app.py", worker)


def write_denied(result):
    return result.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


def test_a_running_implementer_is_stopped_before_reworked_tests_pass_the_checkpoint(project):
    # Fails today: the completed rework does not make the checkpoint runnable (see the
    # unlock rework test); the running implementer itself keeps writing during the unlock.
    ready_for_checkpoint(project)
    assert checkpoint_refusal(project) is None
    assert start(project, "cancel", "implementer") is None
    assert production_write(project, "implementer") == {}
    approve_unlock(project, {"tests/check.py": "fail"}, [{"argv": CHECK, "tests": ["tests/check.py"]}],
                   reason="The cancellation test asserts the wrong call.")
    # Existing guard: during the outstanding unlock the running worker keeps its files.
    assert production_write(project, "implementer") == {}
    assert start(project, "prepare-tests", "rework-author") is None
    (project / "tests/check.py").write_text(
        "from pathlib import Path\nassert Path('src/app.py').read_text() == 'release()', 'not released'\n")
    result = review.run_command(CHECK, project, 10)
    assert result["exit_code"] == 1
    returned = mutate(project, handoff.finish_task, "s", "prepare-tests", changed_files=["tests/check.py"],
                      checks=[{"argv": CHECK, "exit_code": 1, "evidence": result["stderr"]}],
                      unresolved=[], outcome="The reworked test still fails on the missing release.")
    assert returned["status"] == "completed"
    assert stage(project) != "writing-code"
    # The checkpoint refuses while any task runs, so the running implementer is cancelled first.
    reviewer, calls = counting(clean_review)
    message = checkpoint_refusal(project, reviewer)
    assert message is not None and "cancel" in message and calls == []
    mutate(project, handoff.cancel_task, "s", "cancel", "Stopped until the reworked tests pass the checkpoint.")
    assert checkpoint_refusal(project) is None
    assert start(project, "cancel", "implementer-2") is None
    assert production_write(project, "implementer-2") == {}


def test_a_running_implementer_stops_writing_after_a_new_governing_decision(project):
    write_decision_sources(project)
    ready_for_checkpoint(project)
    assert checkpoint_refusal(project) is None
    assert start(project, "cancel", "implementer") is None
    assert production_write(project, "implementer") == {}
    record_decision(project, "release-once", DECIDED)
    assert stage(project) != "writing-code"
    assert write_denied(production_write(project, "implementer")), (
        "A running implementer writes production code under a stale checkpoint acceptance.")


def test_a_test_worker_still_writes_its_declared_production_file_while_writing_tests(project):
    # Guard (passes today): the restriction applies to implementation workers only.
    edit_tasks(project, lambda by_id, tasks: by_id["prepare-tests"].update(
        files=["tests/check.py", "src/app.py"]))
    enter_implementation(project)
    assert start(project, "prepare-tests", "test-author") is None
    assert stage(project) == "writing-tests"
    assert production_write(project, "test-author") == {}


# Review round 6 findings


def blocker_with_incomplete_context(*args):
    """A valid single-reader verdict that names a blocker and also reports missing evidence."""
    reader = {
        "review": blocking_review()["review"],
        "context": {"status": "incomplete", "inspected_files": ["tests/check.py"],
                    "supporting_files": [], "missing_context": ["The helper module the check imports."]},
    }
    result = review._single_result(reader)
    assert result.get("error") and result.get("incomplete_context")
    return result


# Major: a blocker reported with incomplete context, after a legitimate return to the
# test stages, leaves code unauthorized and escalates


def test_a_blocker_with_incomplete_context_keeps_code_unauthorized_and_escalates(project):
    write_decision_sources(project)
    ready_for_checkpoint(project)
    assert checkpoint_refusal(project) is None
    locks = store.load(project, "feature")["locks"]
    record_decision(project, "release-once", DECIDED)
    assert stage(project) != "writing-code"
    assert checkpoint_refusal(project, blocker_with_incomplete_context) is not None
    assert stage(project) != "writing-code", "A blocker with incomplete context authorized code."
    assert start(project, "cancel", "implementer") is not None
    assert checkpoint_refusal(project, blocker_with_incomplete_context) is not None
    record = store.load(project, "feature")
    assert engine.spent_rounds(record["phases"][CK]) == 3
    assert record["locks"] == locks and record.get("lock_origin") == CK
    status = engine.status_report(project, record)
    assert status["status"] == "human-review-required"
    assert status["human_review"] and status["human_review"]["phase"] == CK
    assert start(project, "cancel", "implementer") is not None


# Minor: rework through test tasks never replenishes the allowance


def test_rework_cycles_spend_the_checkpoint_allowance(project):
    ready_for_checkpoint(project)
    reviewer, calls = counting(blocking_review)
    for cycle in range(1, 4):
        assert checkpoint_refusal(project, reviewer) is not None
        kept = {k: work(project)[k] for k in ("generation", "round_limit")}
        spent = engine.spent_rounds(work(project))
        assert spent == cycle
        assert start(project, "prepare-tests", f"rework-author-{cycle}") is None
        after = work(project)
        assert {k: after[k] for k in kept} == kept and engine.spent_rounds(after) == spent, (
            "Relaunching a test task changed the checkpoint's rounds, generation, or allowance.")
        (project / "tests/check.py").write_text(
            "from pathlib import Path\n"
            f"assert Path('src/app.py').read_text() == 'release()', 'rework {cycle}'\n")
        result = review.run_command(CHECK, project, 10)
        assert result["exit_code"] == 1
        returned = mutate(project, handoff.finish_task, "s", "prepare-tests", changed_files=["tests/check.py"],
                          checks=[{"argv": CHECK, "exit_code": 1, "evidence": result["stderr"]}],
                          unresolved=[], outcome=f"Rework {cycle} still fails on the missing release.")
        assert returned["status"] == "completed"
        assert stage(project) == "ready-for-checkpoint"
    assert len(calls) == 3
    assert checkpoint_refusal(project, reviewer) is not None, "A fourth checkpoint review started."
    assert len(calls) == 3
    assert engine.spent_rounds(work(project)) == 3


# Minor: the checkpoint refuses while an unlock is outstanding


def test_checkpoint_refuses_during_an_outstanding_unlock(project):
    ready_for_checkpoint(project)
    assert checkpoint_refusal(project) is None
    approve_unlock(project, {"tests/check.py": "fail"}, [{"argv": CHECK, "tests": ["tests/check.py"]}],
                   reason="The cancellation test asserts the wrong call.")
    rounds = len(work(project)["rounds"])
    reviewer, calls = counting(clean_review)
    assert checkpoint_refusal(project, reviewer) is not None, "The checkpoint ran during an outstanding unlock."
    assert calls == []
    assert len(work(project)["rounds"]) == rounds
    assert store.load(project, "feature")["unlocks"] == ["tests/check.py"]


# Review round 7 findings. Lead ruling: once the checkpoint has an acceptance, an attempt
# that cannot reuse the accepted review withdraws it unless that attempt passes, whatever
# the failure. Locks, lock origin and budget are kept.


def dual_incomplete_with_blocker(*args):
    """A dual review whose native reader reports a blocker with incomplete context."""
    from fbk.workflow import council

    readers = [
        {"member": "native", "review": blocking_review()["review"],
         "context": {"status": "incomplete", "inspected_files": ["tests/check.py"],
                     "supporting_files": [], "missing_context": ["The helper module the check imports."]}},
        {"member": "external", "review": {"summary": "Read the tests.", "findings": []}},
    ]
    result = council.adjudicate(None, "prompt", {}, readers, None, challenge=False, shape="dual")
    assert result.get("error") and result.get("review") is None
    return result


def dual_failed_adjudication(*args):
    """A dual review whose readers both report the blocker and whose adjudication fails."""
    from fbk.workflow import council

    def adjudicator(*a, **k):
        raise store.WorkflowError("The adjudicating reader did not return.")

    readers = [{"member": member, "review": blocking_review()["review"]} for member in ("native", "external")]
    result = council.adjudicate(None, "prompt", {}, readers, adjudicator, challenge=False, shape="dual")
    assert result.get("error") and result.get("adjudication") == "failed"
    return result


def host_error(*args):
    raise store.WorkflowError("Host failed to return a review.")


# A whole-unit check that passes after the governing change is not a failure: a checkpoint
# run after an earlier acceptance makes no mechanical red demand of whole-unit checks
# (step 4b ruling), pinned in test_workflow_unlock_rework_reopen.py.
@pytest.mark.parametrize("failure", ["dual-incomplete", "failed-adjudication", "host-error"])
def test_any_failed_attempt_after_a_governing_change_keeps_code_unauthorized(project, tmp_path_factory, failure):
    outside = tmp_path_factory.mktemp("check-helper")
    external_helper_check(project, outside)
    write_decision_sources(project)
    ready_for_checkpoint(project)
    assert checkpoint_refusal(project) is None
    assert start(project, "cancel", "implementer") is None
    assert production_write(project, "implementer") == {}
    # The checkpoint refuses while any task runs; the running-implementer denial after a
    # governing decision is pinned by test_a_running_implementer_stops_writing_after_a_new_governing_decision.
    mutate(project, handoff.cancel_task, "s", "cancel", "Stopped for the governing change.")
    locks = store.load(project, "feature")["locks"]
    # The legitimate return to the test stages: a new governing decision.
    record_decision(project, "release-once", DECIDED)
    assert stage(project) == "ready-for-checkpoint"
    (outside / "release_helper.py").unlink()
    assert "ModuleNotFoundError" in review.run_command(CHECK, project, 10)["stderr"]
    reviewer, calls = counting({"dual-incomplete": dual_incomplete_with_blocker,
                                "failed-adjudication": dual_failed_adjudication,
                                "host-error": host_error}[failure])
    assert checkpoint_refusal(project, reviewer) is not None
    assert stage(project) != "writing-code", f"A {failure} attempt authorized code."
    assert start(project, "cancel", "second-implementer") is not None
    record = store.load(project, "feature")
    assert record["locks"] == locks and record.get("lock_origin") == CK
    assert checkpoint_refusal(project, reviewer) is not None
    record = store.load(project, "feature")
    assert engine.spent_rounds(record["phases"][CK]) == 3
    status = engine.status_report(project, record)
    assert status["status"] == "human-review-required"
    assert status["human_review"] and status["human_review"]["phase"] == CK
    assert stage(project) != "writing-code"


def assert_rerun_refused(root, reviewer, calls, accepted, locks, marker=None):
    """A current checkpoint refuses a rerun: no checks, no reviewer, no round, nothing changed.
    With a marker, the declared probe check that writes it must not run."""
    rounds = len(work(root)["rounds"])
    if marker is not None:
        marker.unlink(missing_ok=True)
    message = checkpoint_refusal(root, reviewer)
    assert message is not None, "A current checkpoint ran again."
    if marker is not None:
        assert not marker.exists(), "A refused rerun ran the declared checks."
    assert "unlock" in message and "reopen" in message
    assert calls == []
    record = store.load(root, "feature")
    assert len(record["phases"][CK]["rounds"]) == rounds
    assert record["phases"][CK]["evidence"] == accepted
    assert record["locks"] == locks and record.get("lock_origin") == CK
    assert stage(root) == "writing-code"


@pytest.mark.parametrize("reader", ["injected", "native"])
def test_a_current_checkpoint_refuses_a_rerun(project, monkeypatch, reader):
    # A declared check with an observable side effect proves the refused rerun skips checks.
    marker = project / "probe-check-ran"
    probe = [sys.executable, "-c", f"open({str(marker)!r}, 'a').write('ran')"]
    edit_scope(project, checks=[CHECK, probe])
    ready_for_checkpoint(project)
    assert checkpoint_refusal(project) is None
    assert marker.exists(), "The probe check did not run at the accepted checkpoint."
    assert start(project, "cancel", "implementer") is None
    record = store.load(project, "feature")
    accepted, locks = record["phases"][CK]["evidence"], record["locks"]
    if reader == "native":
        # Only the reader is mocked; the rerun goes through review.review.
        reads = []
        monkeypatch.setattr(review, "claude_review", lambda *a, **k: reads.append(a) or {
            "review": {"summary": "Inspected the authored tests.", "findings": []}})
        assert_rerun_refused(project, None, reads, accepted, locks, marker)
    else:
        reviewer, calls = counting(clean_review)
        assert_rerun_refused(project, reviewer, calls, accepted, locks, marker)
    assert production_write(project, "implementer") == {}


# Round 8 minor: an interrupted rerun commits nothing


def test_an_interrupted_rerun_after_a_governing_change_commits_nothing(project):
    write_decision_sources(project)
    ready_for_checkpoint(project)
    assert checkpoint_refusal(project) is None
    record_decision(project, "release-once", DECIDED)
    before = store.load(project, "feature")
    accepted, locks = before["phases"][CK]["evidence"], before["locks"]

    def killed(*args):
        raise Interrupted()

    with pytest.raises(Interrupted):
        run_checkpoint(project, killed)
    cli_call(project, "recover-close", CK, "feature", "--reason", "The old checkpoint process stopped.")
    after = store.load(project, "feature")
    assert after["phases"][CK]["evidence"] == accepted, "An interrupted rerun changed the acceptance record."
    assert after["locks"] == locks and after.get("lock_origin") == before.get("lock_origin")
    assert stage(project) != "writing-code"
