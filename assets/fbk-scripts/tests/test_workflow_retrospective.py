"""Retrospectives expose bounded evidence without polluting runtime or authority."""

import copy
import json

import pytest
from fbk.workflow import retrospective as retro
from fbk.workflow import store
from tests import test_workflow_lifecycle as scenarios

project = scenarios.project


@pytest.fixture
def record():
    return {
        "schema_version": 2,
        "unit": "feature",
        "owner": None,
        "phases": {"spec": {"rounds": [], "pending": None}},
        "events": [{"event": "created", "at": "then", "session": "s"}],
    }


def test_read_is_bounded_and_originals_are_opt_in(tmp_path, record):
    record["events"] += [
        {"event": "reviewed", "review": "PRIVATE BODY " * 3000} for _ in range(40)
    ]
    before = copy.deepcopy(record)
    packet = retro.packet(tmp_path, record, max_chars=3000)
    assert len(json.dumps(packet, ensure_ascii=False)) <= 3000
    assert "PRIVATE BODY" not in json.dumps(packet)
    assert packet["sections"]["events"]["omitted"] > 0
    assert record == before
    assert not list(tmp_path.iterdir())
    original = retro.packet(tmp_path, record, section="events", index=1)
    assert original["evidence"] == record["events"][0]
    assert (
        retro.packet(tmp_path, record, section="events", index=original["ref"])[
            "evidence"
        ]
        == original["evidence"]
    )
    large = retro.packet(tmp_path, record, section="events", index=2)
    assert large["omissions"] and "evidence" not in large


def test_observation_persists_event_and_stale_file_binding(tmp_path, record):
    (tmp_path / "decision.md").write_text("Settled decision\nsecond line\n")
    request = {
        "id": "late",
        "observation": "A review found a missed requirement.",
        "evidence": [
            {"path": "decision.md", "start_line": 1, "end_line": 1},
            {"event_index": 0, "sha256": store.digest(record["events"][0])},
        ],
        "suspected_cause": "Earlier inspection may have missed it.",
        "detection_phase": "spec",
    }
    with store.transaction(tmp_path):
        row = retro.record_observation(tmp_path, record, "s", request)
        store.save(tmp_path, record)
    loaded = store.load(tmp_path, "feature")
    assert loaded["events"][-1]["observation"] == loaded["observations"][0] == row
    assert row["epistemic_status"].startswith("agent-reported")
    assert (
        retro.packet(tmp_path, loaded, section="files", index="1")["content"]
        == "Settled decision"
    )
    (tmp_path / "decision.md").write_text("Changed\n")
    with pytest.raises(store.WorkflowError, match="stale"):
        retro.validate_reference(tmp_path, loaded, row["evidence"][0])
    with pytest.raises(store.WorkflowError, match="stale"):
        retro.packet(tmp_path, loaded, section="files", index=1)
    summary = retro.packet(tmp_path, loaded)
    assert "Changed" not in json.dumps(summary)


def test_event_digest_and_paths_fail_closed(tmp_path, record):
    for ref in (
        {"event_index": 0},
        {"event_index": 0, "sha256": "bad"},
        {"event_id": "event:missing"},
        {"path": "../outside"},
        {"path": "/etc/passwd"},
    ):
        with pytest.raises(store.WorkflowError):
            retro.validate_reference(tmp_path, record, ref)
    event_ref = retro.validate_reference(
        tmp_path, record, {"event_id": "event:" + store.digest(record["events"][0])}
    )
    record["events"][0]["at"] = "changed"
    with pytest.raises(store.WorkflowError, match="stale"):
        retro.validate_reference(tmp_path, record, event_ref)


def test_human_question_is_attributed_not_inferred(tmp_path, record):
    request = {
        "id": "question",
        "observation": "Asked again.",
        "evidence": [{"event_id": "event:" + store.digest(record["events"][0])}],
        "human_question": {
            "classification": "already-settled",
            "reason": "The operator recorded this choice.",
            "decision_refs": ["choice"],
        },
    }
    with pytest.raises(store.WorkflowError, match="decision"):
        retro.record_observation(tmp_path, record, "s", request)
    record["decisions"] = [{"id": "choice", "text": "Use A."}]
    row = retro.record_observation(tmp_path, record, "s", request)
    assert row["human_question"]["decisions"][0]["sha256"] == store.digest(
        record["decisions"][0]
    )
    assert "claim" in row["human_question"]["attribution"]
    assert "rates" in retro.packet(tmp_path, record)["observation_summary"]["meaning"]
    with pytest.raises(store.WorkflowError, match="immutable"):
        retro.record_observation(tmp_path, record, "s", request)


def test_capture_refs_survive_append_and_expose_missing_original(tmp_path, record):
    runtime = tmp_path / ".fbk/runtime"
    runtime.mkdir(parents=True)
    (tmp_path / ".fbk/config.json").write_text('{"schema_version":1}')
    capture = runtime / "events.jsonl"
    original = {
        "event": "context-delivered",
        "unit": "feature",
        "omitted": {"sources": 8},
    }
    capture.write_text(
        json.dumps(original) + "\n" + json.dumps({"event": "host-event"}) + "\n"
    )
    ref = retro.validate_reference(
        tmp_path, record, {"capture_index": 0, "sha256": store.digest(original)}
    )
    with capture.open("a") as stream:
        stream.write(
            json.dumps({"unit": "another", "event": "context-delivered"}) + "\n"
        )
    assert retro.validate_reference(tmp_path, record, ref) == ref
    before = capture.read_bytes()
    store.save(tmp_path, record)
    state = tmp_path / ".fbk/feature/state.json"
    state_before = state.read_bytes()
    packet = retro.packet(tmp_path, record)
    assert packet["capture_health"]["observed_unit_records"] == 1
    assert packet["capture_health"]["unattributed_records"] == 1
    assert '"sources": 8' not in json.dumps(packet)
    assert (
        retro.packet(tmp_path, record, section="capture", index=1)["evidence"]["value"]
        == original
    )
    assert capture.read_bytes() == before
    assert state.read_bytes() == state_before
    assert not (runtime / "capture-health.json").exists()
    capture.unlink()
    with pytest.raises(store.WorkflowError, match="unavailable"):
        retro.validate_reference(tmp_path, record, ref)
    assert ref["snapshot"] == original


def test_mutation_rejects_pending_and_state_file_evidence(tmp_path, record):
    record["phases"]["spec"]["pending"] = {"id": "close"}
    with pytest.raises(store.WorkflowError, match="pending"):
        retro.require_writer(record, "s")
    record["phases"]["spec"]["pending"] = None
    store.save(tmp_path, record)
    with pytest.raises(store.WorkflowError, match="mutable state"):
        retro.validate_reference(tmp_path, record, {"path": ".fbk/feature/state.json"})


def test_observation_reference_checks_underlying_freshness(tmp_path, record):
    source = tmp_path / "result.txt"
    source.write_text("before")
    row = retro.record_observation(
        tmp_path,
        record,
        "s",
        {
            "id": "result",
            "observation": "Observed result",
            "evidence": [{"path": "result.txt"}],
        },
    )
    ref = {"observation_id": row["id"]}
    assert retro.validate_reference(tmp_path, record, ref)["sha256"] == store.digest(
        row
    )
    source.write_text("after")
    with pytest.raises(store.WorkflowError, match="stale"):
        retro.validate_reference(tmp_path, record, ref)


def test_typed_event_references_revalidate_claim_sources(tmp_path, record):
    source = tmp_path / "result.txt"
    source.write_text("initial result")
    row = retro.record_observation(
        tmp_path,
        record,
        "s",
        {
            "id": "result",
            "observation": "Observed result",
            "evidence": [{"path": "result.txt"}],
        },
    )
    observation_event = {"event_id": "event:" + store.digest(record["events"][-1])}
    store.event(
        record,
        "improvement-evaluated",
        "s",
        evaluation={"evidence": [observation_event], "targets": {}},
    )
    evaluation_event = {"event_id": "event:" + store.digest(record["events"][-1])}
    assert retro.validate_reference(tmp_path, record, evaluation_event)
    assert (
        retro.packet(tmp_path, record, section="observations", index=1)["freshness"][
            "status"
        ]
        == "current"
    )
    source.write_text("different result")
    for ref in (observation_event, evaluation_event):
        with pytest.raises(store.WorkflowError, match="stale"):
            retro.validate_reference(tmp_path, record, ref)
    selected = retro.packet(tmp_path, record, section="observations", index=1)
    assert selected["freshness"]["status"] == "stale"
    assert selected["evidence"] == row
    assert (
        retro.packet(tmp_path, record, section="events", index=3)["freshness"]["status"]
        == "stale"
    )
    source.unlink()
    assert (
        retro.packet(tmp_path, record, section="observations", index=1)["freshness"][
            "status"
        ]
        == "unavailable"
    )


def test_observation_event_cycle_fails_without_recursion_error(tmp_path, record):
    # Legacy index references can form a cycle in a manually damaged record.
    cyclic = {
        "event": "observation-recorded",
        "observation": {"evidence": [{"event_index": 1, "sha256": "bad"}]},
    }
    record["events"].append(cyclic)
    with pytest.raises(store.WorkflowError, match="cycle|stale"):
        retro.validate_reference(
            tmp_path, record, {"event_id": "event:" + store.digest(cyclic)}
        )


def test_pointer_retrieves_historical_findings_from_oversized_event(tmp_path, record):
    finding = {"description": "Missed exception path", "a/b": {"~detail": True}}
    record["events"].append(
        {"event": "reviewed", "checks": "x" * 20000, "review": {"findings": [finding]}}
    )
    original = retro.packet(tmp_path, record, section="events", index=2)
    assert "/review" in original["omissions"][0]["pointer_children"]
    selected = retro.packet(
        tmp_path,
        record,
        section="events",
        index=original["ref"],
        pointer="/review/findings/0",
    )
    assert selected["evidence"] == finding
    assert selected["ref"] == original["ref"]
    assert (
        retro.packet(
            tmp_path,
            record,
            section="events",
            index=2,
            pointer="/review/findings/0/a~1b/~0detail",
        )["evidence"]
        is True
    )
    assert (
        len(
            json.dumps(
                retro.packet(
                    tmp_path,
                    record,
                    section="events",
                    index=2,
                    pointer="/checks",
                    max_chars=2000,
                )
            )
        )
        <= 2000
    )
    for pointer in (
        "review",
        "/missing",
        "/review/findings/01",
        "/review/findings/-",
        "/review/findings/9",
        "/review/~2",
    ):
        with pytest.raises(store.WorkflowError, match="Pointer"):
            retro.packet(tmp_path, record, section="events", index=2, pointer=pointer)
    with pytest.raises(store.WorkflowError, match="requires"):
        retro.packet(tmp_path, record, pointer="/review")


def test_oversized_phase_entry_points_at_its_rounds_and_negative_indexes_reach_the_last(
    tmp_path, record
):
    rounds = [{"revision": f"r{n}", "error": f"Round {n} rejected", "result": "x" * 2000} for n in range(10)]
    record["phases"]["spec"]["rounds"] = rounds
    oversized = retro.packet(tmp_path, record, section="phases", index=1)
    omission = oversized["omissions"][0]
    assert "evidence" not in oversized
    assert omission["suggested_pointers"] == ["/value/rounds", "/value/rounds/-1"]
    assert omission["next"] == "retrospective feature --section phases --index 1 --pointer /value/rounds/-1"
    assert (
        retro.packet(tmp_path, record, section="phases", index=1, pointer="/value/rounds/-1")["evidence"]
        == rounds[-1]
    )
    assert (
        retro.packet(tmp_path, record, section="phases", index=1, pointer="/value/rounds/-10")["evidence"]
        == rounds[0]
    )
    rounds_only = retro.packet(tmp_path, record, section="phases", index=1, pointer="/value/rounds", max_chars=2000)
    assert rounds_only["omissions"][0]["suggested_pointers"] == ["/value/rounds/-1"]
    for pointer in ("/value/rounds/-0", "/value/rounds/-01", "/value/rounds/-11", "/value/rounds/-"):
        with pytest.raises(store.WorkflowError, match="Pointer"):
            retro.packet(tmp_path, record, section="phases", index=1, pointer=pointer)


def test_max_chars_is_bounded(tmp_path, record):
    for bound in (1999, 100001, "5000", 5000.0):
        with pytest.raises(store.WorkflowError, match="max_chars"):
            retro.packet(tmp_path, record, max_chars=bound)
    assert len(json.dumps(retro.packet(tmp_path, record, max_chars=2000), ensure_ascii=False)) <= 2000


def test_offset_pages_a_section_index_with_a_next_hint(tmp_path, record):
    record["events"] += [{"event": "reviewed", "phase": "spec", "at": f"t{n}"} for n in range(60)]
    total = len(record["events"])
    seen, offset = [], 0
    while True:
        page = retro.packet(tmp_path, record, section="events", offset=offset, max_chars=3000)
        index = page["sections"]["events"]
        assert index["offset"] == offset and index["total"] == total
        assert index["order"].startswith("oldest-first")
        assert [e["index"] for e in index["entries"]] == list(range(offset + 1, offset + 1 + len(index["entries"])))
        seen += [e["index"] for e in index["entries"]]
        if "next" not in index:
            assert index["omitted"] == 0
            break
        assert index["omitted"] > 0
        assert index["next"] == f"retrospective feature --section events --offset {offset + len(index['entries'])}"
        offset = int(index["next"].rsplit(" ", 1)[1])
    assert seen == list(range(1, total + 1)) and offset > 0
    tail = retro.packet(tmp_path, record, section="events", offset=-3)["sections"]["events"]
    assert [e["index"] for e in tail["entries"]] == [total - 2, total - 1, total]
    assert "next" not in tail and tail["offset"] == total - 3
    empty = retro.packet(tmp_path, record, section="events", offset=total)["sections"]["events"]
    assert empty["entries"] == [] and "next" not in empty
    with pytest.raises(store.WorkflowError, match="exceeds"):
        retro.packet(tmp_path, record, section="events", offset=total + 1)
    for kwargs in ({"offset": 1}, {"section": "events", "index": 1, "offset": 1}, {"section": "events", "offset": "1"}):
        with pytest.raises(store.WorkflowError, match="offset"):
            retro.packet(tmp_path, record, **kwargs)
    assert "offset" not in retro.packet(tmp_path, record)["sections"]["events"]


def test_cli_exposes_max_chars_and_offset(project):
    from tests.test_workflow_commands import call

    bounded = call(project, "retrospective", "feature", "--max-chars", "2500")
    assert len(json.dumps(bounded, ensure_ascii=False)) <= 2500
    with pytest.raises(store.WorkflowError, match="max_chars"):
        call(project, "retrospective", "feature", "--max-chars", "1000")
    paged = call(project, "retrospective", "feature", "--section", "events", "--offset", "-1")
    assert len(paged["sections"]["events"]["entries"]) == 1
    with pytest.raises(store.WorkflowError, match="offset"):
        call(project, "retrospective", "feature", "--section", "events", "--index", "1", "--offset", "1")
