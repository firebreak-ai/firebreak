"""Suggestions the author sorted before acceptance owe no disposition; an older record's
accepted suggestion, and a test-checkpoint test remedy, wait for the operator's disposition."""

import json

import pytest
from fbk.workflow import close, decisions, engine, handoff, store
from tests import test_workflow_lifecycle as scenarios
from tests.test_workflow_commands import call

project = scenarios.project

ENCODING = {
    "title": "Specify the output encoding.",
    "severity": "suggestion",
    "location": ".fbk/feature/spec.md",
    "evidence": "Persisted text has no declared encoding.",
    "remedy": "State UTF-8 for persisted text.",
}
REGRESSION = {
    "title": "Cover repeated cancellation with a regression test.",
    "severity": "suggestion",
    "location": "tests/check.py",
    "evidence": "Only the first cancellation is exercised.",
    "remedy": "Add a second-cancel case to the suite.",
}


def accept_with(root, phase, findings):
    """Accept a phase whose review carries the given findings: a pass with suggestions holds
    for the author's sort, and the next close accepts on that review."""
    def reviewer(*args):
        result = scenarios.clean_review()
        result["review"]["findings"] = [dict(f) for f in findings]
        return result
    scenarios.enter(root, phase)
    if any(f["severity"] == "suggestion" for f in findings):
        with pytest.raises(store.WorkflowError, match="Review passed with"):
            close.close_phase(root, "feature", phase, "s", reviewer=reviewer)
    close.close_phase(root, "feature", phase, "s", reviewer=reviewer)
    scenarios.observe_phase(root, phase)


def older_record(root, phase):
    """An acceptance recorded before the author's sort existed: its suggestions still wait
    for the operator."""
    with store.transaction(root):
        record = store.load(root, "feature")
        record["phases"][phase]["evidence"].pop("author_sorted")
        record["phases"][phase]["evidence"].pop("unreviewed_changes")
        store.save(root, record)


def tag(root, phase, index, remedy_kind):
    """Set the reviewer's remedy tag on an accepted finding (the reviewer contract adds it upstream)."""
    with store.transaction(root):
        record = store.load(root, "feature")
        record["phases"][phase]["evidence"]["review"]["review"]["findings"][index - 1]["remedy_kind"] = remedy_kind
        store.save(root, record)


def disposition(root, entries, *, decision_id="disposition-1", phase="spec", text="Fix the encoding before this phase closes."):
    """Write the operator's words to a source file and record them as a decision carrying dispositions."""
    source = root / f".fbk/feature/decisions/{decision_id}.md"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(text)
    request = {
        "id": decision_id,
        "text": text,
        "phase": phase, "kind": "process",
        "source": {"path": source.relative_to(root).as_posix(), "quote": text},
        "dispositions": entries,
    }
    store.atomic_json(root / f".fbk/{decision_id}.json", request)
    return call(root, "decision-record", "feature", "--request", f".fbk/{decision_id}.json")


def record_direct(root, entries, **overrides):
    record = store.load(root, "feature")
    (root / "words.md").write_text("The operator's words.")
    request = {
        "id": "direct", "text": "The operator's words.", "phase": "spec", "kind": "process",
        "source": {"path": "words.md", "quote": "The operator's words."},
        "dispositions": entries, **overrides,
    }
    return decisions.record(root, record, "s", request)


# Decision record


def test_valid_dispositions_are_stored_on_the_decision(project):
    scenarios.accept(project, "intent")
    accept_with(project, "spec", [ENCODING, REGRESSION])
    entries = [
        {"finding": handoff.finding_digest(ENCODING), "disposition": "fix-now"},
        {"finding": handoff.finding_digest(REGRESSION), "disposition": "defer", "owner": "test-lead"},
    ]
    result = disposition(project, entries, phase="breakdown")
    assert result["dispositions"] == entries
    stored = store.load(project, "feature")["decisions"][-1]
    assert stored["id"] == "disposition-1" and stored["dispositions"] == entries
    state = {item["title"]: item for item in handoff.suggestion_dispositions(store.load(project, "feature"))}
    assert state[ENCODING["title"]]["disposition"] == "fix-now"
    assert state[ENCODING["title"]]["decision_id"] == "disposition-1"
    assert state[REGRESSION["title"]] == {
        "digest": handoff.finding_digest(REGRESSION), "phase": "spec", "index": 2,
        "title": REGRESSION["title"], "remedy_kind": "artifact",
        "disposition": "defer", "owner": "test-lead", "decision_id": "disposition-1",
    }


@pytest.mark.parametrize(
    "entries,message",
    [
        ([{"finding": "0" * 64, "disposition": "fix-now", "note": "extra"}], "only finding, disposition, and owner"),
        ([{"finding": "not-a-digest", "disposition": "fix-now"}], "64-character digest"),
        ([{"finding": "0" * 64, "disposition": "later"}], "one of fix-now, defer, or decline"),
        ([{"finding": "0" * 64, "disposition": "defer"}], "names its owner"),
        ([{"finding": "0" * 64, "disposition": "decline", "owner": "someone"}], "Only a deferred suggestion carries an owner"),
        ([{"finding": "0" * 64, "disposition": "decline"}], "matches no accepted suggestion"),
        ([], "nonempty list"),
    ],
)
def test_malformed_dispositions_are_rejected_with_the_rule(project, entries, message):
    scenarios.accept(project, "intent")
    accept_with(project, "spec", [ENCODING])
    with pytest.raises(store.WorkflowError, match=message):
        record_direct(project, entries)
    assert not store.load(project, "feature").get("decisions")


def test_disposition_record_cannot_also_supersede_a_decision(project):
    scenarios.accept(project, "intent")
    accept_with(project, "spec", [ENCODING])
    record = store.load(project, "feature")
    (project / "earlier.md").write_text("Retry three times.")
    decisions.record(project, record, "s", {
        "id": "retries", "text": "Retry three times.", "phase": "spec", "kind": "governs",
        "source": {"path": "earlier.md", "quote": "Retry three times."},
    })
    with store.transaction(project):
        store.save(project, record)
    with pytest.raises(store.WorkflowError, match="answers reviewer suggestions only; record the superseding decision separately"):
        record_direct(project, [{"finding": handoff.finding_digest(ENCODING), "disposition": "decline"}], supersedes="retries")
    assert [row["id"] for row in store.load(project, "feature")["decisions"]] == ["retries"]


def test_disposition_digest_must_name_a_suggestion_not_a_blocker(project):
    scenarios.accept(project, "intent")
    accept_with(project, "spec", [ENCODING])
    blocker = scenarios.blocking_review()["review"]["findings"][0]
    with pytest.raises(store.WorkflowError, match="matches no accepted suggestion"):
        record_direct(project, [{"finding": handoff.finding_digest(blocker), "disposition": "decline"}])
    with pytest.raises(store.WorkflowError, match="more than once"):
        record_direct(project, [
            {"finding": handoff.finding_digest(ENCODING), "disposition": "decline"},
            {"finding": handoff.finding_digest(ENCODING), "disposition": "fix-now"},
        ])


def test_newest_recorded_disposition_wins(project):
    scenarios.accept(project, "intent")
    accept_with(project, "spec", [ENCODING])
    digest = handoff.finding_digest(ENCODING)
    disposition(project, [{"finding": digest, "disposition": "defer", "owner": "docs"}], decision_id="first", phase="breakdown")
    disposition(project, [{"finding": digest, "disposition": "fix-now"}], decision_id="second", phase="breakdown",
                text="On reflection, fix it now.")
    state = handoff.suggestion_dispositions(store.load(project, "feature"))
    assert [(s["disposition"], s["owner"], s["decision_id"]) for s in state] == [("fix-now", None, "second")]


# Continuation packet


def test_author_sorted_suggestions_are_not_listed_for_disposition(project):
    scenarios.accept(project, "intent")
    accept_with(project, "spec", [ENCODING, REGRESSION])
    packet = call(project, "continuation", "feature")
    assert packet["undispositioned_suggestions"] == []
    assert [f["disposition"] for f in packet["accepted_reviews"][0]["findings"]] == [None, None]


def test_continuation_lists_an_older_records_suggestions_until_one_is_recorded(project):
    scenarios.accept(project, "intent")
    accept_with(project, "spec", [ENCODING, REGRESSION])
    older_record(project, "spec")
    packet = call(project, "continuation", "feature")
    assert packet["phase"] == "breakdown"
    assert packet["undispositioned_suggestions"] == [
        {"digest": handoff.finding_digest(ENCODING), "phase": "spec", "index": 1,
         "title": ENCODING["title"], "remedy_kind": "artifact"},
        {"digest": handoff.finding_digest(REGRESSION), "phase": "spec", "index": 2,
         "title": REGRESSION["title"], "remedy_kind": "artifact"},
    ]
    assert packet["undispositioned_suggestions_next"] == (
        "Group these by what they are about, put each group to the operator, write the operator's "
        "words to a source file, and record them with decision-record --request <file> carrying dispositions."
    )
    carried = packet["accepted_reviews"][0]["findings"]
    assert [f["digest"] for f in carried] == [handoff.finding_digest(ENCODING), handoff.finding_digest(REGRESSION)]
    assert [f["disposition"] for f in carried] == [None, None]
    disposition(project, [{"finding": handoff.finding_digest(ENCODING), "disposition": "decline"}], phase="breakdown",
                text="The operator declines: the storage layer already fixes UTF-8.")
    packet = call(project, "continuation", "feature")
    assert [s["title"] for s in packet["undispositioned_suggestions"]] == [REGRESSION["title"]]
    assert [f["disposition"] for f in packet["accepted_reviews"][0]["findings"]] == ["decline", None]
    section = call(project, "continuation", "feature", "--section", "undispositioned_suggestions")
    assert section["undispositioned_suggestions"] == packet["undispositioned_suggestions"]


def test_bounded_packet_trims_the_disposition_list_and_reports_the_omission(project):
    scenarios.accept(project, "intent")
    accept_with(project, "spec", [dict(ENCODING, title=f"Suggestion {n}") for n in range(8)])
    older_record(project, "spec")
    record = store.load(project, "feature")
    packet = handoff.continuation(project, record, max_chars=2600)
    assert len(json.dumps(packet, ensure_ascii=False)) <= 2600
    assert packet["omitted"].get("undispositioned_suggestions") or packet["omitted"].get("detail")
    full = handoff.continuation(project, record, max_chars=float("inf"))
    assert len(full["undispositioned_suggestions"]) == 8


# Close gate


def test_an_older_records_undispositioned_spec_suggestion_blocks_breakdown_close_until_recorded(project):
    scenarios.accept(project, "intent")
    accept_with(project, "spec", [ENCODING])
    older_record(project, "spec")
    scenarios.enter(project, "breakdown")
    status = call(project, "status", "feature")[0]
    assert status["undispositioned_suggestions"] == 1
    with pytest.raises(store.WorkflowError) as error:
        close.close_phase(project, "feature", "breakdown", "s", reviewer=scenarios.clean_review)
    message = str(error.value)
    assert message.startswith(
        "Accepted suggestions from earlier phases have no recorded disposition: spec#1 Specify the output encoding."
    )
    assert "decision-record feature --request <file> carrying dispositions (fix-now, defer with an owner, or decline)" in message
    assert store.load(project, "feature")["phases"]["breakdown"]["rounds"] == []
    disposition(project, [{"finding": handoff.finding_digest(ENCODING), "disposition": "fix-now"}], phase="breakdown")
    assert call(project, "status", "feature")[0]["undispositioned_suggestions"] == 0
    result = close.close_phase(project, "feature", "breakdown", "s", reviewer=scenarios.clean_review)
    assert result["accepted_phase"] == "breakdown"


def test_a_phase_closes_over_its_own_sorted_suggestions_and_owes_no_disposition(project):
    scenarios.accept(project, "intent")
    accept_with(project, "spec", [ENCODING, REGRESSION])
    record = store.load(project, "feature")
    assert record["phases"]["spec"]["evidence"]["outcome"] == "pass"
    assert engine.status_report(project, record)["undispositioned_suggestions"] == 0
    scenarios.enter(project, "breakdown")
    assert close.close_phase(project, "feature", "breakdown", "s", reviewer=scenarios.clean_review)["accepted_phase"] == "breakdown"


# Lock gate: the test checkpoint is the only lock, so a test remedy is dispositioned before it
#
# Retired: a spec suggestion whose remedy is a test blocking a breakdown-time lock. Breakdown
# no longer locks, and its close already refuses an older record's undispositioned earlier
# suggestion, so no lock can meet one; breakdown's own test remedy is the case left, pinned below.


def checkpoint_ready_after_breakdown_review(root, findings, remedy_kind):
    """Breakdown's review raises the findings; implement opens and every test task finishes."""
    scenarios.accept(root, "intent")
    scenarios.accept(root, "spec")
    accept_with(root, "breakdown", findings)
    tag(root, "breakdown", 1, remedy_kind)
    scenarios.mutate(root, engine.approve, "s", "start-implementation", "implement", "Implement the agreed spec.")
    scenarios.enter(root, "implement")
    scenarios.run_test_tasks(root)


def test_breakdowns_author_sorted_test_remedy_does_not_hold_the_checkpoint_lock(project):
    checkpoint_ready_after_breakdown_review(project, [REGRESSION], "test")
    scenarios.pass_checkpoint(project)
    assert store.load(project, "feature")["locks"]


def test_an_older_records_breakdown_test_remedy_blocks_the_checkpoint_lock(project):
    checkpoint_ready_after_breakdown_review(project, [REGRESSION], "test")
    older_record(project, "breakdown")
    with pytest.raises(store.WorkflowError, match="breakdown#1 Cover repeated cancellation"):
        scenarios.pass_checkpoint(project)
    assert not store.load(project, "feature")["locks"]
    disposition(project, [{"finding": handoff.finding_digest(REGRESSION), "disposition": "decline"}],
                phase="implement", text="The operator declines: the suite already covers a second cancel.")
    scenarios.pass_checkpoint(project)
    assert store.load(project, "feature")["locks"]


# Retired: an artifact remedy not holding a breakdown-time lock. Every earlier phase's
# suggestion, artifact or test, must be dispositioned before the checkpoint runs, and the
# checkpoint's own artifact remedy not holding its lock is pinned by
# test_workflow_test_checkpoint.test_artifact_remedy_suggestion_does_not_hold_the_lock.


# Breakdown close: its own suggestions, test remedies included, hold for the author's sort; it never locks


TEST_REMEDY = dict(REGRESSION, remedy_kind="test")


def counting_reviewer(findings):
    """A reviewer that returns the given findings and counts how often it is asked."""
    calls = []

    def reviewer(*args):
        calls.append(args)
        result = scenarios.clean_review()
        result["review"]["findings"] = [dict(f) for f in findings]
        return result

    return reviewer, calls


def prepare_breakdown(root):
    scenarios.accept(root, "intent")
    scenarios.accept(root, "spec")
    scenarios.enter(root, "breakdown")


def test_breakdown_suggestions_hold_for_the_authors_sort_and_accept_on_the_same_review(project):
    prepare_breakdown(project)
    reviewer, calls = counting_reviewer([TEST_REMEDY, dict(ENCODING, remedy_kind="artifact")])
    with pytest.raises(store.WorkflowError, match="Review passed with 2 suggestion"):
        close.close_phase(project, "feature", "breakdown", "s", reviewer=reviewer)
    record = store.load(project, "feature")
    assert record["phases"]["breakdown"]["evidence"] is None
    assert record["open_phase"] == "breakdown"

    def must_not_run(*args):
        raise AssertionError("the recorded review is reused; no reader call is spent")

    result = close.close_phase(project, "feature", "breakdown", "s", reviewer=must_not_run)
    assert result["accepted_phase"] == "breakdown"
    assert len(calls) == 1
    record = store.load(project, "feature")
    # Breakdown writes tasks only; the test checkpoint locks.
    assert not record["locks"]
    assert len(record["phases"]["breakdown"]["rounds"]) == 1
    assert engine.status_report(project, record)["undispositioned_suggestions"] == 0
