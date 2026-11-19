"""Capture is optional; attempt history records final decisions."""

import json
import pytest
from fbk.workflow import close, engine, hooks, store, telemetry
from tests.test_workflow_lifecycle import (
    clean_review,
    blocking_review,
    enter,
    mutate,
    project as workflow_project,
)

project = workflow_project


def attempts(root):
    return [
        e
        for e in store.load(root, "feature")["events"]
        if e["event"] == "close-attempt"
    ]


def test_capture_health_and_private_context(project, monkeypatch):
    assert telemetry.capture_health(project)["state"] == "not-observed"
    telemetry.record_context(
        project,
        kind="continuation",
        packet={"secret": "raw content", "omitted": {"tasks": 2}},
        session="s",
        unit="feature",
    )
    path = project / ".fbk/runtime/events.jsonl"
    row = json.loads(path.read_text())
    assert "raw content" not in path.read_text()
    assert row["omitted"] == {"tasks": 2} and len(row["sha256"]) == 64
    assert telemetry.capture_health(project)["state"] == "recording"
    monkeypatch.setattr(telemetry, "CAP_BYTES", path.stat().st_size + 1)
    telemetry.record(project, {"event": "test"})
    assert telemetry.capture_health(project)["state"] == "capped"
    assert not telemetry.capture_health(project)["complete"]
    config = store.project_config(project)
    config["capture"] = False
    store.atomic_json(project / ".fbk/config.json", config)
    assert telemetry.capture_health(project)["state"] == "disabled"


def test_capture_failure_does_not_change_policy(project, monkeypatch):
    enter(project, "intent")
    monkeypatch.setattr(
        telemetry.os, "write", lambda *a: (_ for _ in ()).throw(OSError("failure"))
    )
    assert (
        hooks.handle(project, {"hook_event_name": "Stop", "session_id": "s"})[
            "decision"
        ]
        == "block"
    )
    assert telemetry.capture_health(project)["state"] == "degraded"
    assert (
        hooks.handle(project, {"hook_event_name": "PostToolUse", "session_id": "s"})
        == {}
    )


@pytest.mark.parametrize(
    "mode", ["pass", "blocker", "review-error", "stale", "source-stale", "recovered"]
)
def test_close_records_final_outcome(project, mode):
    enter(project, "intent")

    def reviewer(root, *args):
        if mode == "blocker":
            return blocking_review()
        if mode == "review-error":
            raise RuntimeError("review failed")
        if mode == "stale":
            (root / ".fbk/feature/prd.md").write_text("Changed intent.")
        if mode == "source-stale":
            return {**clean_review(), "snapshot_files": {"missing.md": "bad"}}
        if mode == "recovered":
            mutate(root, close.recover, "intent", "s", "Old process stopped.")
        return clean_review()

    if mode == "pass":
        close.close_phase(project, "feature", "intent", "s", reviewer=reviewer)
    else:
        with pytest.raises(Exception):
            close.close_phase(project, "feature", "intent", "s", reviewer=reviewer)
    event = attempts(project)[-1]
    assert (
        event["operation"]
        == store.load(project, "feature")["phases"]["intent"]["rounds"][-1]["operation"]
    )
    assert event["outcome"] == ("pass" if mode == "pass" else "failed")
    assert bool(event["error"]) == (mode != "pass")
    if mode == "stale":
        assert "stale" in event["reason"]
    if mode == "blocker":
        assert "blocking defects" in event["reason"]


def test_preflight_is_audited_without_spending_review(project):
    with pytest.raises(store.WorkflowError):
        close.close_phase(project, "feature", "intent", "s", reviewer=clean_review)
    assert attempts(project)[-1]["outcome"] == "failed"
    assert store.load(project, "feature")["phases"]["intent"]["rounds"] == []


def test_ambiguous_hook_has_no_invented_unit(project):
    enter(project, "intent")
    with store.transaction(project):
        record = engine.initialize(project, "other", design=False)
        record.update(owner="s", open_phase="intent", opened_at=store.now())
        store.save(project, record)
    hooks.handle(
        project,
        {
            "hook_event_name": "SubagentStart",
            "session_id": "s",
            "agent_id": "unassigned",
        },
    )
    row = json.loads(
        (project / ".fbk/runtime/events.jsonl").read_text().splitlines()[-1]
    )
    assert row["unit"] is None and row["phase"] is None
    assert "unassigned" not in store.load(project, "feature")["workers"]
    assert "unassigned" not in store.load(project, "other")["workers"]


def test_session_hook_packet_metadata(project):
    assert hooks.handle(project, {"hook_event_name": "SessionStart", "session_id": "s"})
    rows = [
        json.loads(line)
        for line in (project / ".fbk/runtime/events.jsonl").read_text().splitlines()
    ]
    event = next(row for row in rows if row["event"] == "context-delivered")
    assert event["unit"] == "feature" and event["session"] == "s"
    assert "objective" not in event and "packet" not in event


def test_approval_reuse_has_distinct_attempt_and_original_round(project):
    enter(project, "intent")
    with pytest.raises(store.WorkflowError):
        close.close_phase(project, "feature", "intent", "s", reviewer=blocking_review)
    prior = attempts(project)[-1]
    mutate(
        project,
        engine.approve,
        "s",
        "close-over-findings",
        "intent",
        "Accept residual.",
    )
    close.close_phase(project, "feature", "intent", "s", reviewer=clean_review)
    current = attempts(project)[-1]
    assert current["outcome"] == "approved-over-findings"
    assert current["operation"] != prior["operation"]
    assert current["round_operation"] == prior["operation"]
    assert current["reused"]
    assert len(store.load(project, "feature")["phases"]["intent"]["rounds"]) == 1


def test_verification_failure_is_final_without_spending_review(project):
    from tests.test_workflow_lifecycle import prepare_implementation, declare_module_preparation_task, complete_declared_implementation_task

    declare_module_preparation_task(project)
    prepare_implementation(project)
    complete_declared_implementation_task(project)
    with pytest.raises(store.WorkflowError, match="Verification failed"):
        close.close_phase(
            project,
            "feature",
            "implement",
            "s",
            reviewer=clean_review,
            verifier=lambda *a: [{"exit_code": 1}],
        )
    event = attempts(project)[-1]
    assert event["outcome"] == "failed" and "Verification failed" in event["reason"]
    assert store.load(project, "feature")["phases"]["implement"]["rounds"] == []
