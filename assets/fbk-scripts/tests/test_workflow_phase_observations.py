"""Phase observations survive boundaries and cannot be replaced by a clean review."""

import copy
import json

import pytest
from fbk.workflow import close, engine, handoff, hooks, retrospective, store
from tests import test_workflow_lifecycle as scenario
from tests.test_workflow_commands import call

project = scenario.project


def close_intent(root):
    scenario.enter(root, "intent")
    return close.close_phase(root, "feature", "intent", "s", reviewer=scenario.clean_review)


def record_pending(root, phase, identifier="phase-account", session="s"):
    state = store.load(root, "feature")
    pending = next(p for p in retrospective.pending_phases(state) if p["phase"] == phase)
    request = {
        "id": identifier,
        "observation": "The behavior examples made the cancellation contract clear; review passed without findings.",
        "detection_phase": phase,
        "evidence": [{"event_id": pending["event_id"]}],
    }
    path = root / ".fbk/runtime/phase-observation.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(request))
    return call(root, "observation-record", "feature", "--request", ".fbk/runtime/phase-observation.json", "--session", session)


def test_clean_phase_needs_model_observation_before_next_phase(project):
    assert store.load(project, "feature")["observations"] == []
    result = close_intent(project)
    state = store.load(project, "feature")
    assert state["phases"]["intent"]["evidence"]
    acceptance = copy.deepcopy(state["phases"]["intent"]["evidence"])
    assert state["observations"] == []  # The runtime cannot author the model's account.
    assert result["retrospective"]["pending"][0]["phase"] == "intent"
    with pytest.raises(store.WorkflowError, match="retrospective observations for intent"):
        scenario.enter(project, "spec")
    # Both hook entry paths share the same crossing check.
    for payload in (
        {"hook_event_name": "UserPromptExpansion", "command_name": "fbk-spec", "command_args": "feature"},
        {"hook_event_name": "PreToolUse", "tool_name": "Skill", "tool_input": {"skill": "fbk-spec", "args": "feature"}},
    ):
        response = hooks.handle(project, {**payload, "session_id": "s"})
        assert "retrospective observations" in json.dumps(response)
    row = record_pending(project, "intent")
    state = store.load(project, "feature")
    assert state["observations"] == [row]
    assert state["phases"]["intent"]["evidence"] == acceptance
    assert len(state["phases"]["intent"]["rounds"]) == 1
    assert retrospective.pending_phases(state) == []
    scenario.enter(project, "spec")


def test_wrong_phase_or_earlier_event_does_not_cover_acceptance(project):
    close_intent(project)
    with store.transaction(project):
        state = store.load(project, "feature")
        acceptance = retrospective.pending_phases(state)[0]["event_id"]
        for identifier, phase, ref in (
            ("early", "intent", "event:" + store.digest(state["events"][0])),
            ("wrong-phase", "spec", acceptance),
        ):
            retrospective.record_observation(project, state, "s", {
                "id": identifier, "detection_phase": phase,
                "observation": "A source was inspected.", "evidence": [{"event_id": ref}],
            })
        store.save(project, state)
    with pytest.raises(store.WorkflowError, match="retrospective observations"):
        scenario.enter(project, "spec")
    record_pending(project, "intent")
    original = copy.deepcopy(store.load(project, "feature")["observations"])
    scenario.mutate(project, engine.approve, "s", "reopen", "intent", "Clarify accepted intent.")
    scenario.mutate(project, engine.reopen, "intent", "s", "Clarify accepted intent.")
    scenario.enter(project, "intent")
    close.close_phase(project, "feature", "intent", "s", reviewer=scenario.clean_review)
    assert retrospective.pending_phases(store.load(project, "feature"))
    record_pending(project, "intent", "reopened-account")
    assert store.load(project, "feature")["observations"][:-1] == original


def test_resumption_and_stop_preserve_pending_observation_after_owner_clears(project):
    close_intent(project)
    state = store.load(project, "feature")
    assert state["owner"] is None and state["open_phase"] is None
    packet = handoff.session_context(project, [state], "new-session")
    assert packet["retrospective"]["pending"][0]["phase"] == "intent"
    stop = {"hook_event_name": "Stop", "session_id": "s"}
    assert hooks.handle(project, stop)["decision"] == "block"
    assert hooks.handle(project, {**stop, "stop_hook_active": True}) == {}
    record_pending(project, "intent", session="new-session")
    assert hooks.handle(project, stop) == {}


def test_existing_run_requires_backfill_and_close_cannot_skip_it(project):
    close_intent(project)
    with store.transaction(project):
        state = store.load(project, "feature")
        del state["observations"]  # An existing installation has no initialized ledger.
        state["owner"], state["open_phase"] = "s", "spec"
        store.save(project, state)
    with pytest.raises(store.WorkflowError, match="retrospective observations"):
        close.close_phase(project, "feature", "spec", "s", reviewer=scenario.clean_review)
    assert store.load(project, "feature")["phases"]["spec"]["rounds"] == []
    record_pending(project, "intent")
    close.close_phase(project, "feature", "spec", "s", reviewer=scenario.clean_review)
    assert [p["phase"] for p in retrospective.pending_phases(store.load(project, "feature"))] == ["spec"]


def test_final_phase_is_not_complete_until_observation_is_recorded(project):
    scenario.prepare_implementation(project)
    (project / "src/app.py").write_text("release()")
    scenario.complete_declared_implementation_task(project)
    result = close.close_phase(project, "feature", "implement", "s", reviewer=scenario.clean_review)
    assert result["status"] == "retrospective-required"
    assert handoff.session_context(project, [store.load(project, "feature")], "new-session")
    assert hooks.handle(project, {"hook_event_name": "Stop", "session_id": "s"})["decision"] == "block"
    record_pending(project, "implement")
    assert call(project, "status", "feature")[0]["status"] == "closed"
    assert handoff.session_context(project, [store.load(project, "feature")], "new-session") == {}


def test_child_cannot_bypass_parent_phase_observations(project):
    scenario.accept(project, "intent")
    scenario.enter(project, "spec")
    close.close_phase(project, "feature", "spec", "s", reviewer=scenario.clean_review)
    with store.transaction(project):
        with pytest.raises(store.WorkflowError, match="retrospective observations for spec"):
            engine.initialize(project, "child", parent="feature", design=False)
    record_pending(project, "spec")
    with store.transaction(project):
        child = engine.initialize(project, "child", parent="feature", design=False)
    assert child["parent"] == "feature"
