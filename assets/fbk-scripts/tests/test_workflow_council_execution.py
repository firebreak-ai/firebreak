"""The mediated council's steps, retries and records, and the external second reader's assessor."""

import copy
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from fbk.workflow import close, council, handoff, review, store

from tests.test_workflow_commands import call
from tests.council_stub import Council
from tests.test_workflow_review import at_spec, choose, finding, native, assessor, project


@pytest.mark.parametrize("change", [None, "source", "settings"])
def test_failed_reader_retry_reuses_peers_only_with_identical_context(project, monkeypatch, change):
    at_spec(project)
    choose(project, "council", members=["builder", "guardian"])
    calls = []
    fail = True

    def reader(root, prompt, config, **kwargs):
        member = "guardian" if "Council member: guardian." in prompt else "builder"
        calls.append(member)
        if member == "guardian" and fail:
            raise store.WorkflowError("Structured output failed")
        return native()

    monkeypatch.setattr(review, "claude_review", reader)
    with pytest.raises(store.WorkflowError):
        call(project, "phase-close", "spec", "feature")
    if change == "source":
        # Even a source outside the required files invalidates reuse.
        (project / "README.md").write_text("New governing context.")
    elif change == "settings":
        config = store.project_config(project)
        store.atomic_json(project / ".fbk/config.json", {**config, "reviewer_model": "different-model"})
    fail = False
    result = call(project, "phase-close", "spec", "feature")
    assert result["accepted_phase"] == "spec"
    assert calls.count("guardian") == 2
    assert calls.count("builder") == (1 if change is None else 2)
    rounds = store.load(project, "feature")["phases"]["spec"]["rounds"]
    assert rounds[0]["result"]["readers"][0]["usage"]
    latest = next(r for r in rounds[1]["result"]["readers"] if r["member"] == "builder")
    if change is None:
        assert latest["reused"] and latest["usage"] is None
        assert latest["seconds"] == 0


def test_completed_peer_progress_is_visible_while_another_reader_runs(project, monkeypatch):
    at_spec(project)
    choose(project, "council", members=["builder", "guardian"])
    release = threading.Event()
    completed = threading.Event()
    original = review._council_progress

    def progress(*args):
        update = original(*args)
        def observe(stage, state, member=None, **details):
            update(stage, state, member, **details)
            if member == "guardian" and state == "completed":
                completed.set()
        return observe

    def reader(root, prompt, config, **kwargs):
        if "Council member: builder." in prompt:
            assert release.wait(10), "Test did not release the reader"
        return native()

    monkeypatch.setattr(review, "_council_progress", progress)
    monkeypatch.setattr(review, "claude_review", reader)
    with ThreadPoolExecutor(max_workers=1) as pool:
        close = pool.submit(call, project, "phase-close", "spec", "feature")
        try:
            assert completed.wait(10), "Completed peer was hidden behind the slow reader"
            pending = call(project, "status", "feature")[0]["close_in_progress"]
            assert pending["stages"]["opening:guardian"]["state"] == "completed"
            assert pending["stages"]["opening:builder"]["state"] == "started"
        finally:
            release.set()
        assert close.result(timeout=10)["accepted_phase"] == "spec"
    packet = call(project, "retrospective", "feature", "--section", "events")
    entry = next(e for e in packet["sections"]["events"]["entries"] if e["event"] == "council-stage")
    detail = call(project, "retrospective", "feature", "--section", "events", "--index", str(entry["index"]))
    assert detail["evidence"]["stage"] == "opening"


def declared(status="complete", missing=()):
    return {"status": status, "inspected_files": [".fbk/feature/spec.md"],
            "supporting_files": [], "missing_context": list(missing)}


def test_refuted_duplicate_reference_validates_and_is_removed():
    _, validate = council.assessment_contract(["architect:1", "guardian:1"], canonical=True)
    data = {"summary": "Checked.", "assessments": [
        {"finding_id": "architect:1", "disposition": "refuted",
         "evidence": "src/app.py:1 releases it.", "finding": None},
        {"finding_id": "guardian:1", "disposition": "refuted", "evidence": "Same claim.",
         "finding": None, "duplicate_of": "architect:1"}]}
    assert validate(data) is data
    assert "duplicate_of" not in data["assessments"][1]
    assert data["assessments"][1]["disposition"] == "refuted"


@pytest.mark.parametrize("rule", ["chain", "disposition", "operative-finding", "self", "unknown"])
def test_other_duplicate_rules_still_reject_the_assessment(rule):
    ids = ["architect:1", "guardian:1", "security:1"]
    _, validate = council.assessment_contract(ids, canonical=True)
    rows = [{"finding_id": i, "disposition": "supported", "evidence": "src/app.py:1 retains it.",
             "finding": finding()} for i in ids]
    rows[1].update(finding=None, duplicate_of="architect:1")
    if rule == "chain":
        rows[2].update(finding=None, duplicate_of="guardian:1")
    elif rule == "disposition":
        rows[0].update(disposition="refuted", finding=None)
    elif rule == "operative-finding":
        rows[1]["finding"] = finding()
    elif rule == "self":
        rows[1]["duplicate_of"] = "guardian:1"
    elif rule == "unknown":
        rows[1]["duplicate_of"] = "missing:1"
    with pytest.raises(store.WorkflowError, match="direct retained representative"):
        validate({"summary": "Checked.", "assessments": rows})


@pytest.mark.parametrize("with_candidates", [False, True])
def test_the_external_readers_assessor_runs_only_with_candidates(project, with_candidates):
    calls = []

    def reader(root, prompt, config, **kwargs):
        props = kwargs["schema"]["properties"]
        calls.append("adjudication")
        return assessor(["native:1"], canonical=True)

    readers = [
        {**native([finding()] if with_candidates else []), "member": "native"},
        {**native(), "member": "external"},
    ]
    result = council.adjudicate(project, "Inspect", {}, readers, reader, shape="dual")
    assert "challenge" not in result
    assert result["adjudication"] == ("ran" if with_candidates else "skipped-no-candidates")
    assert calls == (["adjudication"] if with_candidates else [])
    assert result["review"] is not None


@pytest.mark.parametrize("restated", [None, "code"])
def test_test_remedy_tag_survives_the_assessor_to_the_merged_review(project, restated):
    tagged = {**finding(), "remedy_kind": "test"}
    assert council.validate_candidates(native([tagged])["review"])["findings"][0]["remedy_kind"] == "test"
    assert council.CANDIDATE_SCHEMA["properties"]["findings"]["items"]["properties"]["remedy_kind"]["enum"] == [
        "artifact", "test", "code", "documentation"
    ]
    stages = []

    def reader(root, prompt, config, **kwargs):
        props = kwargs["schema"]["properties"]
        stages.append("adjudication")
        result = assessor(["native:1"], canonical=True)
        operative = result["review"]["assessments"][0]["finding"]
        assert "remedy_kind" not in operative
        if restated:
            operative["remedy_kind"] = restated
        kwargs["validator"](result["review"])
        return result

    result = council.adjudicate(
        project, "Inspect", {}, [{**native([tagged]), "member": "native"}], reader, shape="dual",
    )
    assert stages == ["adjudication"]
    assert result["candidates"][0]["finding"]["remedy_kind"] == "test"
    assert result["review"]["findings"][0]["remedy_kind"] == (restated or "test")
    assert review.validate_review(result["review"])


def test_council_reader_rejects_an_unknown_remedy_kind():
    with pytest.raises(store.WorkflowError, match="remedy_kind must be one of"):
        council.validate_candidates(native([{**finding(), "remedy_kind": "prose"}])["review"])




@pytest.mark.parametrize("outcome", ["raise", "incomplete"])
def test_the_assessors_outcome_is_recorded_where_it_is_known(project, outcome):
    missing = "The verification log the candidate cites is not in the snapshot"

    def reader(root, prompt, config, **kwargs):
        if outcome == "raise":
            raise store.WorkflowError("Structured output failed")
        return {**assessor(["native:1", "external:1"], canonical=True),
                "context": declared("incomplete", [missing])}

    readers = [
        {**native([finding()]), "member": "native", "context": declared()},
        {**native([finding()]), "member": "external", "context": declared()},
    ]
    result = council.adjudicate(project, "Inspect", {}, readers, reader, shape="dual")
    assert result["review"] is None
    if outcome == "raise":
        assert result["adjudication"] == "failed"
        assert result["failure"] == {"stage": "adjudication", "diagnostics": None}
    else:
        assert result["adjudication"] == "incomplete"
        assert result["incomplete_context"] == [
            {"member": None, "stage": "adjudication", "missing_context": [missing]}]


# The mediated council.

THREE = ["architect", "guardian", "security"]
CHOSEN = ["architect", "builder", "guardian"]


def proposal_finding(title, severity="suggestion", **extra):
    return {**finding(), "title": title, "severity": severity, **extra}


def run_council(project, scripted, members=THREE, first_speaker=0):
    return council.run(project, PACKET, {}, "spec", members, scripted, unit="feature",
                       first_speaker=first_speaker)


PACKET = "\n" + '{"reading_priority": {}, "rules": {}}'


def test_a_round_with_no_proposals_runs_only_the_openings(project, monkeypatch):
    at_spec(project)
    choose(project, "council", members=CHOSEN)
    scripted = Council()
    monkeypatch.setattr(review, "claude_review", scripted)
    accepted = call(project, "phase-close", "spec", "feature")
    assert accepted["accepted_phase"] == "spec"
    assert [step for step, _ in scripted.calls] == ["opening"] * 3
    result = store.load(project, "feature")["phases"]["spec"]["rounds"][-1]["result"]
    assert result["review"]["findings"] == []
    assert result["discussion"]["proposals"] == [] and result["discussion"]["turns"] == []


def test_a_full_round_runs_each_step_once_per_member_and_records_the_discussion(project):
    scripted = Council(
        openings={"architect": [proposal_finding("Split the store")],
                  "guardian": [proposal_finding("Cover the partial write", "blocker")]},
        stance=lambda member, pid, record: "contest" if pid == "architect:1" and member != "architect" else "support",
    )
    result = run_council(project, scripted)
    assert not result.get("error")
    assert [step for step, _ in scripted.calls] == ["opening"] * 3 + ["turn"] * 3 + ["stance"] * 3 + ["final"]
    assert [r["stage"] for r in result["readers"]][-1] == "final"
    assert [f["title"] for f in result["review"]["findings"]] == ["Cover the partial write"]
    assert result["review"]["findings"][0]["severity"] == "blocker"
    discussion = result["discussion"]
    assert [p["id"] for p in discussion["proposals"]] == ["architect:1", "guardian:1"]
    assert [d["id"] for d in discussion["count"]["dropped"]] == ["architect:1"]
    assert discussion["dropped"] == [{"proposal": "architect:1", "reason": "Dropped: contested."}]
    assert discussion["consensus"] == ["The members agreed on the standing corrections."]
    assert set(discussion["stances"]) == set(THREE)


def test_the_first_speaker_rotates_with_the_round(project):
    scripted = Council(openings={"architect": [proposal_finding("Split the store")]})
    result = run_council(project, scripted, first_speaker=1)
    assert [m for step, m in scripted.calls if step == "turn"] == ["guardian", "security", "architect"]
    assert result["discussion"]["first_speaker"] == "guardian"


def test_each_turn_sees_the_earlier_turns_and_can_replace_or_withdraw(project):
    seen = []

    def turn(member, record):
        seen.append((member, [t["member"] for t in record["turns"]], [p["id"] for p in record["proposals"]]))
        if member == "architect":
            return {"comment": "I take mine back.", "proposals": [],
                    "responses": [{"proposal": "architect:1", "action": "withdraw", "reason": "Guardian is right."}]}
        if member == "guardian":
            return {"comment": "A narrower fix.", "responses": [], "proposals": [
                {**proposal_finding("Retry only the write"), "replaces": ["guardian:1"]},
                {**proposal_finding("A fresh concern"), "replaces": []}]}
        return {"comment": "Nothing to add.", "responses": [], "proposals": []}

    scripted = Council(openings={"architect": [proposal_finding("Split the store")],
                                 "guardian": [proposal_finding("Retry everything")]}, turn=turn)
    result = run_council(project, scripted)
    assert seen == [
        ("architect", [], ["architect:1", "guardian:1"]),
        ("guardian", ["architect"], ["guardian:1"]),
        ("security", ["architect", "guardian"], ["guardian:1", "guardian:r1"]),
    ]
    assert [f["title"] for f in result["review"]["findings"]] == ["Retry only the write"]
    assert [u["finding"]["title"] for u in result["discussion"]["unanchored"]] == ["A fresh concern"]
    assert [(d["id"], d["why"]) for d in result["discussion"]["count"]["dropped"]] == [("guardian:1", "replaced")]


def test_a_tied_blocker_goes_to_a_rotating_second_round_and_stays_a_suggestion_if_still_tied(project):
    second_seen = []

    def second(member, pid, record):
        second_seen.append((member, [s["member"] for s in record["second_round"]]))
        return "support" if member == "architect" else "contest"

    scripted = Council(
        openings={"architect": [proposal_finding("Cover the partial write", "blocker")]},
        stance=lambda member, pid, record: "support" if member == "architect" else "contest",
        second=second,
    )
    result = run_council(project, scripted, members=["architect", "builder"])
    assert scripted.count("second-round") == 2
    assert second_seen == [("architect", []), ("builder", ["architect"])]
    [kept] = result["review"]["findings"]
    assert kept["severity"] == "suggestion"
    assert result["discussion"]["findings"][0]["tied"] is True


def test_when_every_proposal_drops_no_final_session_runs(project):
    scripted = Council(openings={"architect": [proposal_finding("Split the store")]},
                       stance=lambda member, pid, record: "contest")
    result = run_council(project, scripted)
    assert scripted.count("final") == 0
    assert result["review"]["findings"] == []
    assert result["discussion"]["count"]["dropped"][0]["why"] == "contested"


def test_each_session_gets_only_its_part_of_the_reviewer_brief(project):
    scripted = Council(openings={"architect": [proposal_finding("Split the store")]})
    run_council(project, scripted)
    prompts = {(step, member): prompt for step, member, prompt in scripted.prompts}
    opening, turn = prompts[("opening", "architect")], prompts[("turn", "architect")]
    stance, final = prompts[("stance", "architect")], prompts[("final", None)]
    assert "Report every blocker" in opening and "Report every blocker" not in turn
    for text in (opening, turn):
        assert "Do not infer a defect" in text and "Prefer the smallest repair" in text
    assert "Do not infer a defect" in stance and "Report every blocker" not in stance
    assert "Do not infer a defect" not in final and "Council member:" not in final
    assert not any("Independently review" in p for p in (opening, turn, stance, final))
    assert "Read the work alone" in opening and "Read the openings and earlier turns" in turn
    assert "Give support or contest on every proposal" in stance
    assert "Write each standing proposal as a finding" in final


def test_a_test_remedy_tag_survives_the_final_session(project):
    scripted = Council(openings={"guardian": [proposal_finding("Add the retry test", remedy_kind="test")]})

    def final_drops_the_tag(root, prompt, config, **kwargs):
        response = scripted(root, prompt, config, **kwargs)
        if "consensus" in response["review"]:
            for item in response["review"]["findings"]:
                item["finding"].pop("remedy_kind", None)
        return response

    result = council.run(project, PACKET, {}, "spec", THREE, final_drops_the_tag, unit="feature")
    assert result["review"]["findings"][0]["remedy_kind"] == "test"


def test_a_widened_fix_from_the_final_session_leaves_the_voted_text_in_the_record(project):
    voted = proposal_finding("Retry the write once", remedy="Retry the failed write once.")
    scripted = Council(openings={"guardian": [voted]})

    def final_widens_the_fix(root, prompt, config, **kwargs):
        response = scripted(root, prompt, config, **kwargs)
        if "consensus" in response["review"]:
            for item in response["review"]["findings"]:
                item["finding"]["remedy"] = "Rewrite the storage layer with a retry queue."
        return response

    result = council.run(project, PACKET, {}, "spec", THREE, final_widens_the_fix, unit="feature")
    assert result["review"]["findings"][0]["remedy"] == "Rewrite the storage layer with a retry queue."
    listed = {p["id"]: p["finding"] for p in result["discussion"]["proposals"]}
    written = result["discussion"]["findings"][0]
    assert listed[written["proposal"]]["remedy"] == "Retry the failed write once."


@pytest.mark.parametrize("outcome", ["raise", "incomplete"])
def test_a_failed_or_incomplete_stance_ends_the_round(project, outcome):
    missing = "The decision record the proposal cites is not in the snapshot"

    def fail(step, member):
        if outcome == "raise" and (step, member) == ("stance", "guardian"):
            raise store.WorkflowError("Structured output failed")

    scripted = Council(
        openings={"architect": [proposal_finding("Split the store")]}, fail=fail,
        context=lambda step, member: declared("incomplete", [missing])
        if outcome == "incomplete" and (step, member) == ("stance", "guardian") else None,
    )
    result = run_council(project, scripted)
    assert scripted.count("final") == 0
    assert result["review"] is None
    if outcome == "raise":
        assert result["error"] == "Structured output failed"
        assert result["failure"] == {"stage": "stance", "member": "guardian", "diagnostics": None}
    else:
        assert result["error"] == "Review incomplete; missing context: guardian: " + missing
        assert result["incomplete_context"] == [
            {"member": "guardian", "stage": "stance", "missing_context": [missing]}]


def test_an_incomplete_opening_stops_the_council_and_a_retry_reuses_finished_openings(project, monkeypatch):
    at_spec(project)
    choose(project, "council", members=CHOSEN)
    missing = "design/cache.md cited by spec.md is not in the snapshot"
    incomplete = {"on": True}
    scripted = Council(
        openings={"architect": [proposal_finding("Split the store")]},
        context=lambda step, member: declared("incomplete", [missing])
        if incomplete["on"] and (step, member) == ("opening", "guardian") else None,
    )
    monkeypatch.setattr(review, "claude_review", scripted)
    with pytest.raises(store.WorkflowError) as failed:
        call(project, "phase-close", "spec", "feature")
    assert str(failed.value) == "Review incomplete; missing context: guardian: " + missing
    assert [step for step, _ in scripted.calls] == ["opening"] * 3
    result = store.load(project, "feature")["phases"]["spec"]["rounds"][0]["result"]
    assert result["incomplete_context"] == [
        {"member": "guardian", "stage": "opening", "missing_context": [missing]}]
    assert result["review"] is None
    incomplete["on"] = False
    scripted.calls.clear()
    with pytest.raises(store.WorkflowError, match="Review passed with"):
        call(project, "phase-close", "spec", "feature")
    assert [c for c in scripted.calls if c[0] == "opening"] == [("opening", "guardian")]
    assert scripted.count("turn") == 3 and scripted.count("final") == 1


def test_a_failed_turn_fails_the_close_and_the_retry_starts_the_discussion_over(project, monkeypatch):
    at_spec(project)
    choose(project, "council", members=CHOSEN)
    broken = {"on": True}

    def fail(step, member):
        if broken["on"] and (step, member) == ("turn", "guardian"):
            raise store.WorkflowError("Structured output failed")

    scripted = Council(openings={"architect": [proposal_finding("Split the store")]}, fail=fail)
    monkeypatch.setattr(review, "claude_review", scripted)
    with pytest.raises(store.WorkflowError, match="Structured output failed"):
        call(project, "phase-close", "spec", "feature")
    record = store.load(project, "feature")
    result = record["phases"]["spec"]["rounds"][-1]["result"]
    assert result["failure"] == {"stage": "turn", "member": "guardian", "diagnostics": None}
    attempt = next(e for e in reversed(record["events"]) if e["event"] == "close-attempt")
    assert attempt["outcome"] == "failed"
    broken["on"] = False
    scripted.calls.clear()
    with pytest.raises(store.WorkflowError, match="Review passed with"):
        call(project, "phase-close", "spec", "feature")
    assert scripted.count("opening") == 0
    assert scripted.count("turn") == 3


# What status, close events and the author's findings show of a council round.


def test_status_reports_each_council_step(project, monkeypatch):
    at_spec(project)
    choose(project, "council", members=CHOSEN)
    monkeypatch.setattr(review, "claude_review", Council(
        openings={"architect": [proposal_finding("Split the store")]}))
    with pytest.raises(store.WorkflowError, match="Review passed with"):
        call(project, "phase-close", "spec", "feature")
    expected = {"opening": "ran", "turn": "ran", "stance": "ran", "second-round": "skipped", "final": "ran"}
    assert call(project, "status", "feature")[0]["review_stages"]["spec"] == expected
    record = store.load(project, "feature")
    attempt = next(e for e in reversed(record["events"]) if e["event"] == "close-attempt")
    assert attempt["review_stages"] == expected


@pytest.mark.parametrize("result, expected", [
    ({"shape": "council", "readers": [{"stage": "opening"}] * 3},
     {"opening": "ran", "turn": "skipped", "stance": "skipped", "second-round": "skipped", "final": "skipped"}),
    ({"shape": "council", "readers": [{"stage": "opening"}, {"stage": "turn"}],
      "failure": {"stage": "turn", "member": "guardian", "diagnostics": None}},
     {"opening": "ran", "turn": "failed", "stance": "not-reached", "second-round": "not-reached",
      "final": "not-reached"}),
    ({"shape": "council", "readers": [{"stage": "opening"}], "failures": [{"stage": "opening"}]},
     {"opening": "failed", "turn": "not-reached", "stance": "not-reached", "second-round": "not-reached",
      "final": "not-reached"}),
    ({"shape": "council", "readers": [{"stage": "opening"}, {"stage": "turn"}, {"stage": "stance"}],
      "incomplete_context": [{"member": "guardian", "stage": "stance", "missing_context": ["x"]}]},
     {"opening": "ran", "turn": "ran", "stance": "incomplete", "second-round": "not-reached",
      "final": "not-reached"}),
    ({"shape": "dual", "adjudication": "ran"}, {"adjudication": "ran"}),
    ({"shape": "single"}, None),
])
def test_review_stages_name_where_a_round_stopped(result, expected):
    assert close.review_stages(result) == expected


def test_the_authors_findings_carry_council_dissent_and_alternatives(project):
    def turn(member, record):
        if member == "guardian":
            return {"comment": "Two ways to fix it.", "responses": [], "proposals": [
                {**proposal_finding("Retry only the write"), "replaces": ["architect:1"]},
                {**proposal_finding("Queue the write"), "replaces": ["architect:1"]}]}
        return {"comment": "Nothing to add.", "responses": [], "proposals": []}

    scripted = Council(
        openings={"architect": [proposal_finding("Retry everything")]}, turn=turn,
        stance=lambda member, pid, record: "contest" if member == "security" and pid == "guardian:r1" else "support",
    )
    result = run_council(project, scripted)
    record = {"phases": {"spec": {"rounds": [{"result": result, "generation": 1}], "generation": 1}}}
    findings = handoff.current_findings(record, "spec")["findings"]
    assert [f["title"] for f in findings] == ["Retry only the write", "Queue the write"]
    assert findings[0]["council"] == {"dissent": "security contests guardian:r1.", "tied": False,
                                      "alternative_to": [2]}
    assert findings[1]["council"]["alternative_to"] == [1]
    assert findings[0]["digest"] == handoff.finding_digest(result["review"]["findings"][0])
