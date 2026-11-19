"""Real baseline bodies, provenance, and separation from current sources."""

import hashlib
import re

import pytest

from fbk.workflow import review_baseline, store


@pytest.fixture
def captured(tmp_path):
    root = tmp_path / "project"
    reader = tmp_path / "reader"
    reader.mkdir()
    round_id = "a" * 32
    stored = root / f".fbk/runtime/review-rounds/{round_id}/sources"
    files = {
        "src/app.py": b"if retry > 2: return False\n",
        "tests/test_app.py": b"assert rejects(3)\n",
        "tests/test_retired.py": b"assert preserves_existing_behavior()\n",
        ".fbk/feature/spec.md": b"Preserve existing behavior.\n",
        "CLAUDE.md": b"Past conventions, available only for comparison.\n",
    }
    for path, body in files.items():
        target = stored / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
    (stored.parent / "record.json").write_text("prior verdict and transcript")
    (stored / "unlisted-history.txt").write_text("earlier opinions")
    current = reader / "src/app.py"
    current.parent.mkdir()
    current.write_text("if retry > 4: return False\n")
    accepted = {
        "revision": "accepted-contract",
        "review": {
            "source_policy": "original-snapshot-v1",
            "investigation_round": round_id,
            "snapshot_files": {p: hashlib.sha256(b).hexdigest() for p, b in files.items()},
            "summary": "prior reviewer opinion",
        },
    }
    return root, reader, stored, accepted, files


def test_exposes_entire_readable_tree_and_preserves_current_sources(captured):
    root, reader, stored, accepted, files = captured
    available = {"src/app.py": "current-hash"}
    provenance = review_baseline.expose(root, reader, accepted, "breakdown", available)
    baseline = reader / provenance["source_root"]
    assert {p.relative_to(baseline).as_posix(): p.read_bytes() for p in baseline.rglob("*") if p.is_file()} == files
    assert (reader / "src/app.py").read_text() == "if retry > 4: return False\n"
    assert provenance["accepted_revision"] == "accepted-contract"
    assert provenance["source_revision"] == store.digest(accepted["review"]["snapshot_files"])
    assert "opinion" not in str(provenance)
    assert available["src/app.py"] == "current-hash"
    assert all(f"{provenance['source_root']}/{p}" in available for p in files)


@pytest.mark.parametrize("failure", ["missing", "modified", "history", "unbound"])
def test_unavailable_or_unsafe_baseline_never_substitutes_current_sources(captured, failure):
    root, reader, stored, accepted, files = captured
    if failure == "missing":
        (stored / "tests/test_retired.py").unlink()
    elif failure == "modified":
        (stored / "tests/test_app.py").write_text("assert True\n")
    elif failure == "history":
        path = ".fbk/feature/state.json"
        (stored / path).write_text("prior findings")
        accepted["review"]["snapshot_files"][path] = hashlib.sha256(b"prior findings").hexdigest()
    else:
        accepted["review"].pop("investigation_round")
    available = {}
    with pytest.raises(store.WorkflowError):
        review_baseline.expose(root, reader, accepted, "breakdown", available)
    assert not (reader / review_baseline.PREFIX).exists()
    assert not available
    assert (reader / "src/app.py").read_text() == "if retry > 4: return False\n"


def test_selection_uses_acceptance_not_failed_attempts_or_other_phase():
    # Fails today: before implement's first acceptance the fallback is breakdown's snapshot;
    # the accepted test checkpoint snapshot, with its saved output, is the test contract now.
    old = {"revision": "old"}
    latest = {"revision": "latest"}
    breakdown = {"revision": "active-breakdown"}
    checkpoint = {"revision": "accepted-checkpoint"}
    record = {"phases": {"implement": {"rounds": [{"result": {"revision": "failed-attempt"}}]},
                         "breakdown": {"evidence": breakdown},
                         "test-checkpoint": {"evidence": checkpoint}},
              "events": [{"event": "closed", "phase": "implement", "evidence": old},
                         {"event": "closed", "phase": "implement", "evidence": latest},
                         {"event": "closed", "phase": "spec", "evidence": {"revision": "other"}}]}
    assert review_baseline.select(record, "implement")[:2] == (latest, "implement")
    record["events"] = []
    assert review_baseline.select(record, "implement")[:2] == (checkpoint, "test-checkpoint")
    # Breakdown's plan-only acceptance is never implement's test contract.
    record["phases"]["test-checkpoint"]["evidence"] = None
    assert review_baseline.select(record, "implement")[0] is None
    record["phases"]["breakdown"]["evidence"] = None
    assert review_baseline.select(record, "implement")[0] is None
    assert review_baseline.select(record, "breakdown")[0] is None


def test_selected_missing_tree_does_not_fall_back_to_older_acceptance(captured):
    root, reader, stored, accepted, files = captured
    missing = {"revision": "selected-but-missing", "review": {}}
    record = {"events": [{"event": "closed", "phase": "spec", "evidence": accepted},
                         {"event": "closed", "phase": "spec", "evidence": missing}]}
    provenance = review_baseline.prepare(root, reader, record, "spec", {})
    assert provenance["status"] == "unavailable"
    assert provenance["accepted_revision"] == "selected-but-missing"
    assert not (reader / review_baseline.PREFIX).exists()


def test_managed_review_loads_readable_baseline_and_ratchets_without_nested_history(captured, monkeypatch):
    from fbk.workflow import decisions, review, review_context

    root, _, _, accepted, _ = captured
    source = root / "src/app.py"
    source.parent.mkdir()
    source.write_text("if retry > 4: return False\n")
    record = {"unit": "feature", "parent": None,
              "phases": {"spec": {"rounds": [], "generation": 1}},
              "review_plans": {"spec": {"mode": "single"}},
              "events": [{"event": "closed", "phase": "spec", "evidence": accepted}]}
    monkeypatch.setattr(review, "project_config", lambda _: {})
    monkeypatch.setattr(review, "load", lambda *_: record)
    monkeypatch.setattr(decisions, "binding", lambda *_: [])
    expected_prior = ["if retry > 2: return False\n", "if retry > 4: return False\n"]
    seen = []

    def reader(snapshot, prompt, config):
        baseline = config["_review_baseline"]
        prior = snapshot / baseline["source_root"]
        assert baseline["status"] == "available"
        assert (prior / "src/app.py").read_text() == expected_prior[len(seen)]
        assert (snapshot / "src/app.py").read_bytes() == source.read_bytes()
        assert not (prior / review_baseline.PREFIX).exists()
        if not seen:
            assert (prior / "tests/test_retired.py").read_text() == "assert preserves_existing_behavior()\n"
        else:
            assert not (prior / "tests/test_retired.py").exists()
        assert "prior reviewer opinion" not in prompt
        assert "comparison_baseline" in prompt
        assert '"available_conventions": []' in prompt
        inspected = ["src/app.py", f"{baseline['source_root']}/src/app.py"]
        context = {"status": "complete", "inspected_files": inspected,
                   "supporting_files": [], "missing_context": []}
        review_context.validate_context(context, config["_review_available_files"], ["src/app.py"])
        seen.append(baseline)
        return {"review": {"summary": "Compared actual source bodies.", "findings": []}, "context": context}

    monkeypatch.setattr(review, "claude_review", reader)
    first = review.review(root, "feature", "spec", ["src/app.py"], [])
    assert review_baseline.reusable(root, record, "spec", first)
    assert not review_baseline.reusable(root, record, "spec", {"investigation_round": "b" * 32})
    assert first["snapshot_files"] == {"src/app.py": hashlib.sha256(source.read_bytes()).hexdigest()}
    record["events"].append({"event": "closed", "phase": "spec",
                             "evidence": {"revision": "next-accepted", "review": first}})
    source.write_text("if retry > 6: return False\n")
    review.review(root, "feature", "spec", ["src/app.py"], [])
    assert [p["accepted_revision"] for p in seen] == ["accepted-contract", "next-accepted"]


def test_breakdown_prompt_carries_no_execution_or_lineage_from_an_earlier_acceptance(tmp_path, monkeypatch):
    # Breakdown reviews a plan: even a record whose earlier breakdown acceptance kept red
    # output and preparation history gives its prompt no execution records or lineage.
    from fbk.workflow import review

    baseline = {"revision": "selected", "test_preparation": {
        "red_check": {"argv": ["pytest"], "exit_code": 1, "stdout": "selected assertion failed"}}}
    record = {"parent": None, "events": [{"event": "closed", "phase": "breakdown", "evidence": baseline}],
              "test_preparation": {"checked": {"historical_evidence": {
                  "applicable": [{"accepted_source": "older-history-pointer", "sources": {"retired-old-revision": "hash"},
                                  "red_check": {"stdout": "older-revision-execution"}}]}}}}
    prompts = []
    monkeypatch.setattr(review, "claude_review", lambda root, prompt, config:
                        prompts.append(prompt) or {"review": {"summary": "Inspected the plan", "findings": []}})
    review._review_sources(tmp_path, "feature", "breakdown", [], [], {}, record)
    for value in ["selected assertion failed", "older-history-pointer", "retired-old-revision",
                  "older-revision-execution", "baseline_execution", "lineage_review",
                  "Baseline execution records", "preservation evidence"]:
        assert value not in prompts[0], value


@pytest.mark.parametrize("missing_capture", [False, True])
def test_managed_current_only_review_names_unavailable_comparison(captured, monkeypatch, missing_capture):
    from fbk.workflow import decisions, review

    root, _, stored, accepted, _ = captured
    source = root / "src/app.py"
    source.parent.mkdir()
    source.write_text("current body\n")
    (stored / "tests/test_retired.py").unlink()
    record = {"unit": "feature", "parent": None,
              "phases": {"spec": {"rounds": [], "generation": 1}},
              "events": [{"event": "closed", "phase": "spec", "evidence": accepted}] if missing_capture else []}
    monkeypatch.setattr(review, "project_config", lambda _: {})
    monkeypatch.setattr(review, "load", lambda *_: record)
    monkeypatch.setattr(decisions, "binding", lambda *_: [])

    def reader(snapshot, prompt, config):
        baseline = config["_review_baseline"]
        assert baseline["status"] == "unavailable"
        assert not (snapshot / review_baseline.PREFIX).exists()
        assert all(not p.startswith(review_baseline.PREFIX) for p in config["_review_available_files"])
        assert (snapshot / "src/app.py").read_text() == "current body\n"
        assert "missing_context" in prompt
        if missing_capture:
            assert "tests/test_retired.py" in baseline["reason"]
        else:
            assert "No applicable accepted" in baseline["reason"]
        return {"review": {"summary": "Inspected current source; no change comparison claimed.", "findings": []}}

    monkeypatch.setattr(review, "claude_review", reader)
    review.review(root, "feature", "spec", ["src/app.py"], [])
    assert source.read_text() == "current body\n"


def test_unavailable_baseline_grant_retry_reuses_the_completed_native_review(tmp_path, monkeypatch):
    from fbk.workflow import close, engine, review
    from tests import test_workflow_lifecycle as scenarios
    from tests.test_workflow_commands import call

    root = scenarios.project.__wrapped__(tmp_path)
    scenarios.accept(root, "intent")
    scenarios.accept(root, "spec")  # An older acceptance without a captured source tree.
    call(root, "approve", "feature", "reopen", "--phase", "spec", "--reason", "Revise spec")
    scenarios.mutate(root, engine.reopen, "spec", "s", "Revise spec")
    scenarios.enter(root, "spec")
    calls = []

    def reader(snapshot, prompt, config):
        calls.append(config["_review_baseline"])
        return scenarios.blocking_review()

    monkeypatch.setattr(review, "claude_review", reader)
    with pytest.raises(store.WorkflowError, match="Review found blocking defects"):
        close.close_phase(root, "feature", "spec", "s")
    record = store.load(root, "feature")
    rounds = len(record["phases"]["spec"]["rounds"])
    assert calls[0]["status"] == "unavailable"
    call(root, "approve", "feature", "close-over-findings", "--phase", "spec",
         "--reason", "Accept the demonstrated limitation")
    close.close_phase(root, "feature", "spec", "s")
    record = store.load(root, "feature")
    assert len(calls) == 1
    assert len(record["phases"]["spec"]["rounds"]) == rounds
    assert record["phases"]["spec"]["evidence"]["outcome"] == "approved-over-findings"


def test_unavailable_reuse_requires_supplied_provenance_and_invalidates_on_capture_return(captured, monkeypatch):
    from fbk.workflow import decisions, review

    root, _, stored, accepted, files = captured
    source = root / "src/app.py"
    source.parent.mkdir()
    source.write_text("current source\n")
    missing = stored / "tests/test_retired.py"
    missing.unlink()
    record = {"unit": "feature", "parent": None,
              "phases": {"spec": {"rounds": [], "generation": 1}},
              "events": [{"event": "closed", "phase": "spec", "evidence": accepted}]}
    monkeypatch.setattr(review, "project_config", lambda _: {})
    monkeypatch.setattr(review, "load", lambda *_: record)
    monkeypatch.setattr(decisions, "binding", lambda *_: [])
    monkeypatch.setattr(review, "claude_review", lambda *args:
                        {"review": {"summary": "Inspected current source.", "findings": []}})
    result = review.review(root, "feature", "spec", ["src/app.py"], [])
    assert re.fullmatch(r"feature-spec-[a-f0-9]{32}", result["investigation_round"])
    assert review_baseline.reusable(root, record, "spec", result)
    provenance = root / f".fbk/runtime/review-rounds/{result['investigation_round']}/baseline.json"
    supplied = provenance.read_bytes()
    provenance.unlink()
    assert not review_baseline.reusable(root, record, "spec", result)
    provenance.write_bytes(supplied)
    accepted["revision"] = "different-acceptance"
    assert not review_baseline.reusable(root, record, "spec", result)
    accepted["revision"] = "accepted-contract"
    missing.write_bytes(files["tests/test_retired.py"])
    assert not review_baseline.reusable(root, record, "spec", result)


def test_repaired_acceptance_survives_reopen_without_falling_back_to_old_tree(tmp_path, monkeypatch):
    from fbk.workflow import close, engine, repair, review
    from tests import test_workflow_lifecycle as scenarios
    from tests.test_workflow_commands import call
    from tests.test_workflow_repairs import authorize, reference

    root = scenarios.project.__wrapped__(tmp_path)
    authorize(root)
    request = reference(root)
    scenarios.enter(root, "intent")
    monkeypatch.setattr(review, "claude_review", lambda *args: scenarios.clean_review())
    close.close_phase(root, "feature", "intent", "s")
    scenarios.observe_phase(root, "intent")
    original = store.load(root, "feature")["phases"]["intent"]["evidence"]["revision"]
    repair.apply(root, "feature", "s", request)
    latest = store.load(root, "feature")["phases"]["intent"]["evidence"]["revision"]
    assert latest != original
    call(root, "approve", "feature", "reopen", "--phase", "intent", "--reason", "Revise intent")
    scenarios.mutate(root, engine.reopen, "intent", "s", "Revise intent")
    record = store.load(root, "feature")
    selected, phase, _ = review_baseline.select(record, "intent")
    assert selected["revision"] == latest
    assert phase == "intent"
    assert "summary" not in str(record["events"][-1]["superseded_evidence"])
    reader = root / "reader"
    reader.mkdir()
    baseline = review_baseline.prepare(root, reader, record, "intent", {})
    assert baseline["accepted_revision"] == latest
    assert baseline["status"] == "unavailable"
    assert not (reader / review_baseline.PREFIX).exists()


def test_a_baseline_in_a_round_named_with_its_unit_and_phase_is_read(captured, tmp_path):
    """A round folder starts with its unit and phase so an operator can match it; a baseline
    stored under that name is read like one under the older bare digest."""
    root, reader, stored, accepted, files = captured
    named = "feature-spec-" + "a" * 32
    stored.parent.rename(stored.parent.with_name(named))
    accepted["review"]["investigation_round"] = named
    provenance = review_baseline.expose(root, reader, accepted, "breakdown", {})
    baseline = reader / provenance["source_root"]
    assert {p.relative_to(baseline).as_posix(): p.read_bytes() for p in baseline.rglob("*") if p.is_file()} == files
