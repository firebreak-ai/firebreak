"""Public retrospective commands connect recorded facts to evaluated changes."""

import hashlib
import json

import pytest

from fbk.workflow import evidence, store, telemetry
from tests.test_workflow_commands import call
from tests.test_workflow_lifecycle import project as workflow_project

project = workflow_project


def request(root, command, body):
    path = root / ".fbk/runtime/request.json"
    store.atomic_json(path, body)
    return call(root, command, "feature", "--request", ".fbk/runtime/request.json")


def test_cli_context_emissions_join_retrieval_without_changing_acceptance_inputs(
    project,
):
    record = store.load(project, "feature")
    before = evidence.revision(project, record, "intent")
    packet = call(project, "continuation", "feature")
    call(project, "continuation", "feature", "--section", "sources")
    rows = [
        json.loads(line)
        for line in (project / ".fbk/runtime/events.jsonl").read_text().splitlines()
    ]
    assert rows[0]["unit"] == "feature"
    assert (
        rows[0]["sha256"]
        == hashlib.sha256(
            json.dumps(
                packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode()
        ).hexdigest()
    )
    assert rows[1]["section"] == "sources"
    assert (
        evidence.revision(project, store.load(project, "feature"), "intent") == before
    )
    retro = call(project, "retrospective", "feature", "--section", "capture")
    assert retro["sections"]["capture"]["total"] == 2
    assert retro["capture_health"]["complete"] is False


def test_report_distinguishes_disabled_capture_from_no_observed_activity(project):
    config = store.project_config(project)
    config["capture"] = False
    store.atomic_json(project / ".fbk/config.json", config)
    for args in [(), ("--history",)]:
        report = call(project, "workflow-report", "feature", *args)[0]
        assert report["capture_health"]["state"] == "disabled"
        assert report["capture_health"]["complete"] is False
    call(project, "continuation", "feature")
    assert not (project / ".fbk/runtime/events.jsonl").exists()


def test_public_observation_preserves_revision_and_is_retrievable(project):
    before = evidence.revision(project, store.load(project, "feature"), "intent")
    index = call(project, "retrospective", "feature", "--section", "events")
    reference = index["sections"]["events"]["entries"][0]["ref"]
    request(
        project,
        "observation-record",
        {
            "id": "interrupted-review",
            "observation": "The recorded unit was created before review began.",
            "evidence": [{"event_id": reference}],
            "uncertainty": "No model outcome has been observed.",
        },
    )
    result = call(
        project, "retrospective", "feature", "--section", "observations", "--index", "1"
    )
    assert result["evidence"]["id"] == "interrupted-review"
    assert result["evidence"]["uncertainty"] == "No model outcome has been observed."
    selected = call(
        project,
        "retrospective",
        "feature",
        "--section",
        "observations",
        "--index",
        "1",
        "--pointer",
        "/uncertainty",
    )
    assert selected["evidence"] == "No model outcome has been observed."
    assert selected["ref"] == result["ref"]
    assert (
        evidence.revision(project, store.load(project, "feature"), "intent") == before
    )
    assert "observations" not in call(project, "continuation", "feature")


def test_public_improvement_stays_unverified_until_evaluation_and_stales_after_edit(
    project,
):
    (project / "guide.md").write_text("Before instruction")
    (project / "baseline.txt").write_text(
        "The fixture repeated an already answered question."
    )
    request(
        project,
        "improvement-record",
        {
            "action": "propose",
            "id": "retrieve-first",
            "hypothesis": "Targeted decision retrieval reduces repeated questions.",
            "evidence": [{"path": "baseline.txt"}],
            "targets": ["guide.md"],
            "change_kind": "edit",
            "change": "Read the applicable decision first.",
            "check": {
                "method": "Replay the fixture with an isolated agent.",
                "success_criterion": "No repeated question.",
                "baseline": "One repeated question.",
            },
        },
    )
    (project / "guide.md").write_text("Read the applicable decision first.")
    request(
        project,
        "improvement-record",
        {
            "action": "adopt",
            "id": "retrieve-first",
            "reason": "User authorized this scoped correction.",
        },
    )
    assert (
        call(project, "improvement-report", "feature")["items"][0]["status"]
        == "implemented-unverified"
    )
    (project / "result.txt").write_text(
        "The replay continued using the existing decision; no question."
    )
    request(
        project,
        "improvement-record",
        {
            "action": "evaluate",
            "id": "retrieve-first",
            "outcome": "improved",
            "evidence": [{"path": "result.txt"}],
            "comparison": "One question before, zero in this replay.",
            "limitations": "One synthetic trial, not a general causal claim.",
            "stage": "check",
        },
    )
    assert (
        call(project, "improvement-report", "feature", "--index", "1")["status"]
        == "evaluated-improved"
    )
    (project / "guide.md").write_text("A subsequent different instruction.")
    assert (
        call(project, "improvement-report", "feature")["items"][0]["status"]
        == "needs-re-evaluation"
    )
    request(
        project,
        "improvement-record",
        {
            "action": "decision",
            "id": "retrieve-first",
            "decision": "defer",
            "reason": "Evaluate the subsequent edit separately.",
        },
    )
    assert (project / "guide.md").read_text() == "A subsequent different instruction."


def test_pending_close_prevents_audit_mutation_without_partial_append(project):
    record = store.load(project, "feature")
    record["phases"]["intent"]["pending"] = {"id": "running-close"}
    store.save(project, record)
    before = (project / ".fbk/feature/state.json").read_bytes()
    with pytest.raises(store.WorkflowError, match="pending"):
        request(
            project,
            "observation-record",
            {
                "id": "blocked",
                "observation": "Uncommitted claim",
                "evidence": [{"event_id": "missing"}],
            },
        )
    assert (project / ".fbk/feature/state.json").read_bytes() == before


def test_capture_write_failure_does_not_break_context_reconstruction(
    project, monkeypatch
):
    monkeypatch.setattr(
        telemetry.os,
        "open",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("unavailable")),
    )
    packet = call(project, "continuation", "feature")
    assert packet["unit"] == "feature"


def test_unavailable_capture_preserves_durable_retrospective(project, tmp_path_factory):
    external = tmp_path_factory.mktemp("outside-capture") / "events.jsonl"
    external.write_text('{"unit":"feature","event":"untrusted-outside"}\n')
    runtime = project / ".fbk/runtime"
    runtime.mkdir(exist_ok=True)
    (runtime / "events.jsonl").symlink_to(external)
    packet = call(project, "retrospective", "feature")
    assert packet["capture_health"]["state"] == "unknown"
    assert packet["capture_health"]["read_error"] == "Runtime evidence unavailable."
    assert packet["sections"]["events"]["total"] > 0
    assert packet["sections"]["capture"]["total"] == 0
