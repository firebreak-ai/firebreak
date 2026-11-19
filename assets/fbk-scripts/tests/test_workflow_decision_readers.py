"""Readers get the current phase's governing decisions and live amendments, nothing else."""

import pytest
from fbk.workflow import decisions, review, store

from tests import test_workflow_lifecycle as scenarios
from tests.test_workflow_commands import call

project = scenarios.project


def record_decision(root, decision_id, phase, kind="governs", **fields):
    quote = f"The operator settled {decision_id}."
    source = root / f".fbk/feature/decisions/{decision_id}.md"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(quote)
    request = {"id": decision_id, "text": quote, "phase": phase,
               "source": {"path": source.relative_to(root).as_posix(), "quote": quote}, **fields}
    if kind is not None:
        request["kind"] = kind
    store.atomic_json(root / ".fbk/request.json", request)
    return call(root, "decision-record", "feature", "--request", ".fbk/request.json")


def shown(root, phase):
    return [row["id"] for row in decisions.for_readers(root, store.load(root, "feature"), phase)]


def test_kind_is_required_and_defined_in_the_refusal(project):
    with pytest.raises(store.WorkflowError, match="governs when the decision constrains the work product"):
        record_decision(project, "no-kind", "intent", kind=None)
    with pytest.raises(store.WorkflowError, match="Decision needs a kind"):
        record_decision(project, "odd-kind", "intent", kind="requirement")


def test_disposition_decisions_must_be_process(project):
    with pytest.raises(store.WorkflowError, match="dispositions is a process decision"):
        record_decision(project, "answers", "intent", dispositions=[])


def test_readers_get_only_the_current_phase_governing_decisions(project):
    record_decision(project, "release-once", "intent")
    record_decision(project, "single-review", "intent", kind="process")
    assert shown(project, "intent") == ["release-once"]
    scenarios.accept(project, "intent")
    record_decision(project, "retry-limit", "spec")
    # The accepted PRD carries the intent decision forward; the spec reader does not get it again.
    assert shown(project, "spec") == ["retry-limit"]


def test_amendment_travels_forward_until_its_phase_is_reaccepted(project):
    scenarios.accept(project, "intent")
    record_decision(project, "push-errors", "spec", amends="intent")
    assert shown(project, "spec") == ["push-errors"]
    assert shown(project, "implement") == ["push-errors"]
    # Reaccepting the amended phase after the amendment means its document absorbed it.
    record = store.load(project, "feature")
    record["phases"]["intent"]["evidence"]["at"] = "9999-01-01T00:00:00.000+00:00"
    assert decisions.for_readers(project, record, "implement") == []


def test_a_cutting_session_gets_every_earlier_governing_decision(project):
    record_decision(project, "release-once", "intent")
    record_decision(project, "single-review", "intent", kind="process")
    record_decision(project, "stdin-only", "intent")
    record_decision(project, "file-or-stdin", "intent", supersedes="stdin-only")
    scenarios.accept(project, "intent")
    record_decision(project, "retry-limit", "spec")
    record = store.load(project, "feature")
    ids = [row["id"] for row in decisions.governing_through(project, record, "spec")]
    assert ids == ["release-once", "file-or-stdin", "retry-limit"]
    assert [row["id"] for row in decisions.governing_through(project, record, "intent")] == [
        "release-once", "file-or-stdin"]


def test_amends_must_name_an_earlier_accepted_phase(project):
    with pytest.raises(store.WorkflowError, match="earlier phase"):
        record_decision(project, "too-late", "intent", amends="spec")
    with pytest.raises(store.WorkflowError, match="not accepted"):
        record_decision(project, "unaccepted", "spec", amends="intent")
    scenarios.accept(project, "intent")
    with pytest.raises(store.WorkflowError, match="its kind is governs"):
        record_decision(project, "process-amend", "spec", kind="process", amends="intent")


def test_replacing_an_earlier_phase_decision_is_an_amendment(project):
    record_decision(project, "release-once", "intent")
    scenarios.accept(project, "intent")
    with pytest.raises(store.WorkflowError, match="amends intent"):
        record_decision(project, "wrong-target", "spec", supersedes="release-once", amends="spec")
    row = record_decision(project, "release-twice", "spec", supersedes="release-once")
    assert row["amends"] == "intent"
    assert "release-once" not in shown(project, "implement")
    assert "release-twice" in shown(project, "implement")


def test_informal_new_version_of_an_active_decision_is_refused(project):
    record_decision(project, "push-errors", "intent")
    with pytest.raises(store.WorkflowError, match='looks like a new version of active decision push-errors'):
        record_decision(project, "push-errors-v2", "intent")
    record_decision(project, "push-errors-v2", "intent", supersedes="push-errors")
    with pytest.raises(store.WorkflowError, match="active decision push-errors-v2"):
        record_decision(project, "push-errors-v3", "intent")
    # Numbered siblings are not versions.
    record_decision(project, "step-1", "intent")
    record_decision(project, "step-2", "intent")


def annotate(root, **request):
    store.atomic_json(root / ".fbk/annotate.json", request)
    return call(root, "decision-annotate", "feature", "--request", ".fbk/annotate.json")


def test_earlier_records_are_annotated_once_with_a_reason(project):
    scenarios.accept(project, "intent")
    record_decision(project, "legacy-override", "spec")
    record = store.load(project, "feature")
    for key in ("kind", "amends"):
        record["decisions"][0].pop(key, None)
    with store.transaction(project):
        store.save(project, record)
    # A record from before kinds existed counts as governing for its own phase.
    assert shown(project, "spec") == ["legacy-override"]
    assert shown(project, "implement") == []
    with pytest.raises(store.WorkflowError, match="operator's reason"):
        annotate(project, id="legacy-override", kind="governs", amends="intent")
    annotate(project, id="legacy-override", kind="governs", amends="intent", reason="Overrides a PRD line.")
    assert shown(project, "implement") == ["legacy-override"]
    events = [e for e in store.load(project, "feature")["events"] if e["event"] == "decision-annotated"]
    assert events[-1]["reason"] == "Overrides a PRD line." and events[-1]["amends"] == "intent"
    with pytest.raises(store.WorkflowError, match="already has a kind"):
        annotate(project, id="legacy-override", kind="process", reason="Second thoughts.")


def test_review_requires_only_the_shown_decisions_sources(project, monkeypatch):
    record_decision(project, "release-once", "intent")
    scenarios.accept(project, "intent")
    record_decision(project, "retry-limit", "spec")
    record_decision(project, "review-mode", "spec", kind="process")
    captured = {}

    def sources(root, unit, phase, required, checks, config, record):
        captured.update(required=set(required), decisions=config["_review_decisions"])
        return {"error": "captured", "readers": []}

    monkeypatch.setattr(review, "_review_sources", sources)
    call(project, "phase-enter", "spec", "feature")
    review.review(project, "feature", "spec", [".fbk/feature/spec.md"], [])
    assert [d["id"] for d in captured["decisions"]] == ["retry-limit"]
    assert ".fbk/feature/decisions/retry-limit.md" in captured["required"]
    assert ".fbk/feature/decisions/release-once.md" not in captured["required"]
    assert ".fbk/feature/decisions/review-mode.md" not in captured["required"]


@pytest.mark.parametrize("phase", ["intent", "spec", "breakdown"])
def test_phase_review_must_find_its_decisions_in_its_document(phase):
    obligations = review.focus_brief("unit", phase, [])["acceptance_obligations"]
    assert any(f"only through the accepted {phase} document" in o and "blocker" in o for o in obligations)
    assert any("overrides that phase's accepted document" in o for o in obligations)


def test_implement_review_has_no_later_phase_to_carry_decisions_to():
    obligations = review.focus_brief("unit", "implement", [])["acceptance_obligations"]
    assert not any("only through the accepted" in o for o in obligations)
