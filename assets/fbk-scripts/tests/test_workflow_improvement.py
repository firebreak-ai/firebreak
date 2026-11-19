"""Exercise evidence freshness and the boundary between adoption and evaluation."""

import copy

import pytest

from fbk.workflow import improvement, store


@pytest.fixture
def ledger(tmp_path):
    (tmp_path / "target.md").write_text("Original instruction")
    (tmp_path / "baseline.txt").write_text("Replay failed: required source was missing")
    record = {
        "unit": "example",
        "owner": None,
        "workers": {},
        "phases": {},
        "events": [],
    }
    proposal = {
        "id": "load-source",
        "hypothesis": "Loading the original source prevents the missing requirement.",
        "evidence": [{"path": "baseline.txt"}],
        "targets": ["target.md"],
        "change_kind": "edit",
        "change": "Route to original sources before analysis.",
        "check": {
            "method": "Replay the task with original sources.",
            "success_criterion": "The previously omitted requirement is handled.",
            "baseline": "One omitted requirement in replay.",
        },
    }
    improvement.record_proposal(tmp_path, record, "s", proposal)
    return tmp_path, record, proposal


def adopt(root, record):
    (root / "target.md").write_text("Read the original source")
    return improvement.record_adoption(
        root,
        record,
        "s",
        {"id": "load-source", "reason": "Apply requested scoped change."},
    )


def evaluate(root, record, outcome="improved", stage="check"):
    (root / "result.txt").write_text("Replay handled the missing requirement")
    return improvement.record_evaluation(
        root,
        record,
        "s",
        {
            "id": "load-source",
            "outcome": outcome,
            "evidence": [{"path": "result.txt"}],
            "comparison": "Replay now covers the requirement missing from baseline.",
            "limitations": "One replay; no long-term maintainability evidence.",
            "stage": stage,
        },
    )


def status(root, record):
    return improvement.report(root, record)["items"][0]["status"]


def test_adoption_is_not_demonstrated_improvement_and_survives_serialization(ledger):
    root, record, _ = ledger
    with pytest.raises(store.WorkflowError, match="actual target change"):
        improvement.record_adoption(
            root, record, "s", {"id": "load-source", "reason": "No edits yet"}
        )
    with pytest.raises(store.WorkflowError, match="adoption"):
        evaluate(root, record)
    snapshot = adopt(root, record)
    assert status(root, record) == "implemented-unverified"
    evaluate(root, record)
    assert status(root, record) == "evaluated-improved"
    assert (
        snapshot["targets"]["target.md"]
        != record["improvements"][0]["baseline_targets"]["target.md"]
    )
    record.update(schema_version=2)
    store.save(root, record)
    assert status(root, store.load(root, "example")) == "evaluated-improved"


@pytest.mark.parametrize("changed", ["target.md", "result.txt"])
def test_changed_target_or_evaluated_original_invalidates_result(ledger, changed):
    root, record, _ = ledger
    adopt(root, record)
    evaluate(root, record)
    history = copy.deepcopy(record["improvements"][0]["evaluations"])
    (root / changed).write_text("Changed after evaluation")
    assert status(root, record) == "needs-re-evaluation"
    assert record["improvements"][0]["evaluations"] == history
    if changed == "target.md":
        with pytest.raises(store.WorkflowError, match="new adoption"):
            evaluate(root, record)


def test_re_adoption_requires_new_evaluation_even_when_target_restored(ledger):
    root, record, _ = ledger
    adopt(root, record)
    evaluate(root, record)
    (root / "target.md").write_text("Further change")
    improvement.record_adoption(
        root, record, "s", {"id": "load-source", "reason": "Revision"}
    )
    (root / "target.md").write_text("Read the original source")
    improvement.record_adoption(
        root, record, "s", {"id": "load-source", "reason": "Restore"}
    )
    assert status(root, record) == "needs-re-evaluation"


def test_reject_unknown_reference_and_baseline_recycling(ledger):
    root, record, proposal = ledger
    proposal.update(id="unknown", evidence=[{"event_id": "event:unknown"}])
    with pytest.raises(store.WorkflowError):
        improvement.record_proposal(root, record, "s", proposal)
    assert len(record["improvements"]) == 1
    adopt(root, record)
    with pytest.raises(store.WorkflowError, match="new check"):
        improvement.record_evaluation(
            root,
            record,
            "s",
            {
                "id": "load-source",
                "outcome": "improved",
                "evidence": [{"path": "baseline.txt"}],
                "comparison": "Unchanged baseline",
                "limitations": "No rerun",
                "stage": "check",
            },
        )


@pytest.mark.parametrize("outcome", ["regressed", "inconclusive", "no-change"])
def test_negative_and_followup_results_preserved_and_rollback_is_only_decision(
    ledger, outcome
):
    root, record, _ = ledger
    adopt(root, record)
    evaluate(root, record)
    evaluate(root, record, outcome, "followup")
    assert status(root, record) == "evaluated-" + outcome
    before = (root / "target.md").read_text()
    improvement.record_decision(
        root,
        record,
        "s",
        {
            "id": "load-source",
            "decision": "rollback",
            "reason": "Later evidence does not support retaining this change.",
        },
    )
    assert (root / "target.md").read_text() == before
    assert len(improvement.report(root, record, 1)["evaluations"]) == 2


def test_no_change_can_be_evaluated_without_adoption(ledger):
    root, record, proposal = ledger
    proposal.update(id="no-intervention", targets=[], change_kind="no-change")
    improvement.record_proposal(root, record, "s", proposal)
    improvement.record_evaluation(
        root,
        record,
        "s",
        {
            "id": "no-intervention",
            "outcome": "no-change",
            "evidence": [{"path": "baseline.txt"}],
            "comparison": "Evidence does not isolate an actionable cause.",
            "limitations": "Missing host trace",
            "stage": "check",
        },
    )
    assert improvement.report(root, record, 2)["status"] == "evaluated-no-change"


def test_removed_target_hash_is_absent_and_ownership_is_enforced(ledger):
    root, record, _ = ledger
    (root / "target.md").unlink()
    adoption = improvement.record_adoption(
        root,
        record,
        "s",
        {"id": "load-source", "reason": "Remove redundant instruction"},
    )
    assert adoption["targets"] == {"target.md": None}
    record["owner"] = "other"
    with pytest.raises(store.WorkflowError, match="owns"):
        evaluate(root, record)


def test_historical_baseline_does_not_invalidate_current_evaluation(ledger):
    root, record, _ = ledger
    adopt(root, record)
    evaluate(root, record)
    baseline_binding = copy.deepcopy(record["improvements"][0]["evidence"])
    (root / "baseline.txt").write_text("Later task result")
    assert status(root, record) == "evaluated-improved"
    assert record["improvements"][0]["evidence"] == baseline_binding


def test_no_change_target_change_invalidates_result(ledger):
    root, record, proposal = ledger
    proposal.update(id="observe", change_kind="no-change")
    improvement.record_proposal(root, record, "s", proposal)
    improvement.record_evaluation(
        root,
        record,
        "s",
        {
            "id": "observe",
            "outcome": "no-change",
            "evidence": [{"path": "baseline.txt"}],
            "comparison": "Insufficient evidence",
            "limitations": "One observation",
            "stage": "check",
        },
    )
    (root / "target.md").unlink()
    assert improvement.report(root, record, 2)["status"] == "needs-re-evaluation"


def test_observation_evaluation_tracks_its_original_evidence(ledger):
    from fbk.workflow import retrospective

    root, record, _ = ledger
    adopt(root, record)
    (root / "result.txt").write_text("Follow-up finding")
    retrospective.record_observation(
        root,
        record,
        "s",
        {
            "id": "followup",
            "observation": "Requirement is covered",
            "evidence": [{"path": "result.txt"}],
        },
    )
    improvement.record_evaluation(
        root,
        record,
        "s",
        {
            "id": "load-source",
            "outcome": "improved",
            "evidence": [{"observation_id": "followup"}],
            "comparison": "Previously missed, now covered",
            "limitations": "One task",
            "stage": "followup",
        },
    )
    (root / "result.txt").write_text("Changed original")
    assert status(root, record) == "needs-re-evaluation"
