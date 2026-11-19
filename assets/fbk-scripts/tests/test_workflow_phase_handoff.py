"""A new session must receive and enforce readiness after post-close changes."""

import json

import pytest
from fbk.workflow import hooks, review, store

from tests import test_workflow_lifecycle as scenarios
from tests.test_workflow_parent_recovery import call

project = scenarios.project


def session_packet(root, session):
    result = hooks.handle(
        root,
        {"hook_event_name": "SessionStart", "session_id": session, "cwd": str(root)},
    )
    context = result["hookSpecificOutput"]["additionalContext"]
    return json.loads(context[context.index("{"):])


@pytest.mark.parametrize("change", ["decision", "artifact"])
def test_changed_intent_handoff_requires_reacceptance_before_design(
    project, monkeypatch, change
):
    monkeypatch.setattr(review, "review", scenarios.clean_review)
    call(project, "route", "feature", "--design", "on", "--reason", "Review the architecture.")
    call(project, "phase-enter", "intent", "feature")
    accepted = call(project, "phase-close", "intent", "feature")
    assert (accepted["phase"], accepted["status"]) == ("design", "ready")
    scenarios.observe_phase(project, "intent")

    quote = "Repeated cancellation succeeds without releasing the resource again."
    if change == "decision":
        source = project / ".fbk/feature/repeat-cancellation.md"
        source.write_text(quote)
        store.atomic_json(project / ".fbk/request.json", {
            "id": "repeat-cancellation", "text": quote, "phase": "intent", "kind": "governs",
            "source": {"path": ".fbk/feature/repeat-cancellation.md", "quote": quote},
        })
        recorded = call(project, "decision-record", "feature", "--request", ".fbk/request.json")
        assert (recorded["workflow"]["phase"], recorded["workflow"]["status"]) == ("intent", "stale")
    else:
        # Model an external edit after close: no write hook supplies advance notice.
        prd = project / ".fbk/feature/prd.md"
        prd.write_text(prd.read_text() + "\n" + quote)

    outgoing = call(project, "status", "feature")[0]
    continuation = call(project, "continuation", "feature", session="fresh-session")
    incoming = session_packet(project, "fresh-session")
    for packet in (outgoing, continuation, incoming):
        assert (packet["phase"], packet["status"]) == ("intent", "stale")
        assert packet["next"] == outgoing["next"]

    with pytest.raises(store.WorkflowError):
        call(project, "phase-enter", "design", "feature", session="fresh-session")
    for payload in (
        {"hook_event_name": "UserPromptExpansion", "command_name": "fbk-design", "command_args": "feature"},
        {"hook_event_name": "PreToolUse", "tool_name": "Skill", "tool_input": {"skill": "fbk-design", "args": "feature"}},
    ):
        result = hooks.handle(project, {**payload, "session_id": "fresh-session", "cwd": str(project)})
        if payload["hook_event_name"] == "PreToolUse":
            assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
        else:
            assert "decision" not in result
            assert "could not open design" in result["hookSpecificOutput"]["additionalContext"]
            assert "stale" in result["hookSpecificOutput"]["additionalContext"]
    assert call(project, "status", "feature")[0]["status"] == "stale"

    reason = "Revalidate intent after the post-close clarification."
    call(project, "approve", "feature", "reopen", "--phase", "intent", "--reason", reason, session="fresh-session")
    call(project, "phase-close", "intent", "feature", "--reopen", "--reason", reason, session="fresh-session")
    call(project, "phase-enter", "intent", "feature", session="fresh-session")
    reaccepted = call(project, "phase-close", "intent", "feature", session="fresh-session")
    assert (reaccepted["phase"], reaccepted["status"]) == ("design", "ready")
    scenarios.observe_phase(project, "intent", session="fresh-session")

    next_session = session_packet(project, "design-session")
    assert (next_session["phase"], next_session["status"]) == ("design", "ready")
    if change == "decision":
        # The reaccepted PRD now carries the intent decision; design does not get it separately.
        assert not any(row["id"] == "repeat-cancellation" for row in next_session["decisions"])
    hooks.handle(project, {
        "hook_event_name": "UserPromptExpansion", "command_name": "fbk-design",
        "command_args": "feature", "session_id": "design-session", "cwd": str(project),
    })
    # Confirm actual entry, not merely absence of a denial in the hook response.
    entered = call(project, "status", "feature")[0]
    assert (entered["phase"], entered["status"], entered["owner"]) == ("design", "open", "design-session")
