"""Exhaustion requests human judgment on the last attempt, not the next retry."""

import pytest
from fbk.workflow import hooks, review, store
from tests import test_workflow_lifecycle as scenarios
from tests.test_workflow_commands import call
from tests.test_workflow_phase_handoff import session_packet

project = scenarios.project


@pytest.mark.parametrize("failure_kind", ["host", "findings"])
def test_last_failed_attempt_escalates_and_survives_context_reset(project, monkeypatch, failure_kind):
    calls = []
    def reader(*args):
        calls.append(args)
        if failure_kind == "host":
            raise store.WorkflowError("Host failed to return a review")
        return scenarios.blocking_review()
    monkeypatch.setattr(review, "review", reader)
    call(project, "phase-enter", "intent", "feature")
    for attempt in range(3):
        with pytest.raises(store.WorkflowError) as error:
            call(project, "phase-close", "intent", "feature")
        status = call(project, "status", "feature")[0]
        if attempt < 2:
            assert status["human_review"] is None
        else:
            assert "Human help is required" in str(error.value)
            assert status["status"] == "human-review-required"
            assert status["human_review"]["rounds_used"] == 3
    stopped = hooks.handle(project, {"hook_event_name": "Stop", "session_id": "s", "cwd": str(project)})
    assert stopped["decision"] == "block" and "Human help" in stopped["reason"]
    call(project, "suspend", "feature", "--reason", "Awaiting human judgment on the failed attempts.")
    incoming = session_packet(project, "fresh-session")
    assert incoming["status"] == "human-review-required"
    assert incoming["human_review"]["rounds_used"] == 3
    with pytest.raises(store.WorkflowError):
        call(project, "phase-enter", "intent", "feature")
        call(project, "phase-close", "intent", "feature")
    assert len(calls) == 3
    events = store.load(project, "feature")["events"]
    assert sum(e["event"] == "human-review-required" for e in events) == 1
    call(project, "extend-review", "intent", "feature", "--rounds", "1", "--reason", "The operator authorized one retry after reviewing the failures.")
    assert call(project, "status", "feature")[0]["human_review"] is None
    assert len(store.load(project, "feature")["phases"]["intent"]["rounds"]) == 3


def test_acceptance_on_last_attempt_does_not_request_human_review(project, monkeypatch):
    attempts = 0
    def reader(*args):
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise store.WorkflowError("Temporary host failure")
        return scenarios.clean_review()
    monkeypatch.setattr(review, "review", reader)
    call(project, "phase-enter", "intent", "feature")
    for _ in range(2):
        with pytest.raises(store.WorkflowError):
            call(project, "phase-close", "intent", "feature")
    result = call(project, "phase-close", "intent", "feature")
    assert result["accepted_phase"] == "intent" and result["human_review"] is None
    assert not any(e["event"] == "human-review-required" for e in store.load(project, "feature")["events"])


def exhaust(project, monkeypatch, rounds=3):
    monkeypatch.setattr(review, "review", lambda *args: scenarios.blocking_review())
    call(project, "phase-enter", "intent", "feature")
    for _ in range(rounds):
        with pytest.raises(store.WorkflowError):
            call(project, "phase-close", "intent", "feature")


def test_suspend_note_after_exhaustion_leads_the_next_action(project, monkeypatch):
    exhaust(project, monkeypatch)
    note = "The fix is written to prd.md; only authorization for one more review round is needed. " + "x" * 400
    call(project, "suspend", "feature", "--reason", note)
    status = call(project, "status", "feature")[0]
    assert status["status"] == "human-review-required"
    assert status["human_review"]["suspend_note"]["note"] == note
    assert status["human_review"]["history"].endswith("--section phases --index 1 --pointer /value/rounds")
    assert status["human_review"]["latest_round"].endswith("--pointer /value/rounds/-1")
    assert note[:400] + "..." in status["next"]
    assert note[:420] not in status["next"]
    assert "authorization for another review round" in status["next"]
    assert 'extend-review intent feature --rounds 1 --reason' in status["next"]
    assert "Present failed stages" not in status["next"]
    incoming = session_packet(project, "fresh-session")
    assert incoming["next"] == status["next"] and incoming["pending"] == note
    call(project, "extend-review", "intent", "feature", "--rounds", "1", "--reason", "The operator authorized one retry.")
    assert call(project, "status", "feature")[0]["human_review"] is None


def test_suspend_note_before_exhaustion_keeps_the_presentation_text(project, monkeypatch):
    exhaust(project, monkeypatch, rounds=2)
    call(project, "suspend", "feature", "--reason", "Waiting on the human's answer to the naming question.")
    call(project, "phase-enter", "intent", "feature")
    with pytest.raises(store.WorkflowError):
        call(project, "phase-close", "intent", "feature")
    status = call(project, "status", "feature")[0]
    assert status["status"] == "human-review-required"
    assert status["human_review"]["suspend_note"] is None
    assert "Present failed stages, unresolved candidates" in status["next"]
    assert "naming question" not in status["next"]
    assert session_packet(project, "fresh-session")["next"] == status["next"]


def test_suspend_note_after_exhaustion_leads_the_close_time_escalation(project, monkeypatch):
    exhaust(project, monkeypatch)
    note = "The fix is written to prd.md; only authorization for one more review round is needed."
    call(project, "suspend", "feature", "--reason", note)
    call(project, "phase-enter", "intent", "feature")
    with pytest.raises(store.WorkflowError) as error:
        call(project, "phase-close", "intent", "feature")
    message = str(error.value)
    assert note in message
    assert "authorization for another review round" in message
    assert "extend-review intent feature --rounds 1 --reason" in message
    assert "Present failed stages" not in message
    assert message == call(project, "status", "feature")[0]["next"] or message.endswith(call(project, "status", "feature")[0]["next"])
