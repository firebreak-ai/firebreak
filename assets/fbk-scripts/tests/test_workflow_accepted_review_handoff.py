"""Accepted advice remains discoverable after the workflow advances."""

import copy
import json

import pytest

from fbk.workflow import handoff, review, store
from tests import test_workflow_lifecycle as scenarios
from tests.test_workflow_commands import call
from tests.test_workflow_phase_handoff import session_packet

project = scenarios.project


def original_fields(findings):
    """Carried findings add a digest and disposition state; the rest is the durable original."""
    return [{k: v for k, v in f.items() if k not in {"digest", "disposition"}} for f in findings]


def accept_with_suggestion(root, monkeypatch, text="Specify the output encoding.", count=1):
    finding = {
        "title": text, "severity": "suggestion", "location": ".fbk/feature/prd.md",
        "evidence": "The next phase must choose an encoding for persisted text.",
        "remedy": "Consider explicit UTF-8 when specifying persistence.",
    }
    def reviewer(*args):
        result = scenarios.clean_review()
        result["review"]["findings"] = [finding] * count
        return result
    monkeypatch.setattr(review, "review", reviewer)
    call(root, "phase-enter", "intent", "feature")
    # The suggestion holds the pass; the author sorts it and closes again on the same review.
    with pytest.raises(store.WorkflowError, match="Review passed with"):
        call(root, "phase-close", "intent", "feature")
    call(root, "phase-close", "intent", "feature")
    scenarios.observe_phase(root, "intent")
    return finding


def test_fresh_phase_receives_accepted_advice_and_durable_selected_followup(project, monkeypatch):
    finding = accept_with_suggestion(project, monkeypatch)
    reason = "During spec, resolve the encoding suggestion from intent's accepted review in .fbk/feature/state.json."
    call(project, "suspend", "feature", "--reason", reason)
    before = copy.deepcopy(store.load(project, "feature"))
    for packet in (call(project, "continuation", "feature"), session_packet(project, "new-session")):
        assert (packet["phase"], packet["status"]) == ("spec", "ready")
        assert packet["findings"] == []
        prior = packet["accepted_reviews"][0]
        assert prior["phase"] == "intent" and prior["source_current"]
        assert original_fields(prior["findings"]) == [finding]
        assert prior["findings"][0]["digest"] == handoff.finding_digest(finding)
        assert prior["findings"][0]["disposition"] is None
        assert packet["pending"] == reason
        # The pointer must lead to the durable original, not an invented summary.
        original = json.loads((project / prior["source"]).read_text())
        for part in prior["pointer"].strip("/").split("/"):
            original = original[part]
        assert original["findings"] == original_fields(prior["findings"])
    assert store.load(project, "feature") == before


def test_oversized_prior_review_has_complete_targeted_retrieval(project, monkeypatch):
    finding = accept_with_suggestion(project, monkeypatch, count=8)
    packet = handoff.continuation(project, store.load(project, "feature"), max_chars=3000)
    assert len(json.dumps(packet, ensure_ascii=False)) <= 3000
    assert packet["omitted"].get("accepted_reviews") or packet["omitted"].get("detail")
    assert packet["accepted_review_index"][0] == {"phase": "intent", "finding_count": 8, "source_current": True}
    full = call(project, "continuation", "feature", "--section", "accepted_reviews")
    assert original_fields(full["accepted_reviews"][0]["findings"]) == [finding] * 8


def test_changed_accepted_sources_keep_historical_advice_but_mark_it_stale(project, monkeypatch):
    finding = accept_with_suggestion(project, monkeypatch)
    (project / ".fbk/feature/prd.md").write_text("The human changed the intended behavior.")
    packet = call(project, "continuation", "feature")
    assert packet["status"] == "stale"
    assert original_fields(packet["accepted_reviews"][0]["findings"]) == [finding]
    assert packet["accepted_reviews"][0]["source_current"] is False


def test_bounded_handoff_prioritizes_the_most_recent_accepted_phase(project, monkeypatch):
    finding = accept_with_suggestion(project, monkeypatch, count=8)
    call(project, "phase-enter", "spec", "feature")
    # The author sorted intent's suggestion before intent accepted, so spec closes without a
    # disposition; spec's own review holds once for the same sort.
    with pytest.raises(store.WorkflowError, match="Review passed with"):
        call(project, "phase-close", "spec", "feature")
    call(project, "phase-close", "spec", "feature")
    scenarios.observe_phase(project, "spec")
    # Each carried finding also names its digest and disposition, so one eight-finding review needs about 6000 characters.
    packet = handoff.continuation(project, store.load(project, "feature"), max_chars=6000)
    assert len(json.dumps(packet, ensure_ascii=False)) <= 6000
    assert packet["phase"] == "breakdown"
    assert [r["phase"] for r in packet["accepted_reviews"]] == ["spec"]
    assert original_fields(packet["accepted_reviews"][0]["findings"]) == [finding] * 8
    assert packet["omitted"]["accepted_reviews"] == 1
    full = call(project, "continuation", "feature", "--section", "accepted_reviews")
    assert {r["phase"] for r in full["accepted_reviews"]} == {"intent", "spec"}
