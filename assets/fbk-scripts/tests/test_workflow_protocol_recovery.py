"""Malformed reader declarations get one durable correction, without an experiment."""

import pytest

from fbk.workflow import investigations, managed_investigations as managed, store, hooks
from tests.test_workflow_review import project as project


def execution(tmp_path):
    source = tmp_path / "sources"
    source.mkdir(exist_ok=True)
    return managed.open_round(
        tmp_path, source, {"review_round_timeout": 60}, "contract"
    )


def request(**changes):
    return dict(
        id="probe",
        question="Does the runner support this?",
        requirements=["spec.md"],
        mode="direct",
        argv=["python3", "--version"],
        **changes,
    )


def run(tmp_path, active, session):
    return managed.run_reader(
        tmp_path,
        "Inspect spec.md.",
        {"_managed_execution": active, "_review_available_files": {}},
        session,
        schema={},
        validator=lambda x: x,
    )


@pytest.mark.parametrize(
    "changes,match",
    [
        ({"external": {}}, "external requires"),
        ({"external": {"target": "service", "effects": "read"}}, "effects"),
        ({"exploratory": "false"}, "boolean"),
        (
            {"authorization": {"target": "service", "effects": ["read"], "source": {}}},
            "source",
        ),
    ],
)
def test_invalid_request_has_no_experiment_or_reservation(tmp_path, changes, match):
    active = execution(tmp_path)
    with pytest.raises(investigations.InvestigationRequestError, match=match):
        active.investigate(request(**changes), "reader")
    assert investigations._load(tmp_path, active.round_id)["investigations"] == {}
    assert not (tmp_path / ".fbk/runtime/investigations").exists()
    active.finish()


def test_one_correction_retains_usage_and_survives_restart(tmp_path):
    active = execution(tmp_path)
    prompts = []

    def session(root, prompt, config, **kwargs):
        prompts.append(prompt)
        if len(prompts) == 1:
            return {
                "investigation": request(external={}),
                "seconds": 2,
                "usage": {"input_tokens": 7},
            }
        assert "external requires" in prompt
        return {"review": {"findings": []}, "seconds": 3, "usage": {"input_tokens": 9}}

    result = run(tmp_path, active, session)
    assert result["seconds"] == 5
    assert len(result["continuation_usage"]) == 2
    row = investigations._load(tmp_path, active.round_id)
    correction = next(iter(row["reader_corrections"].values()))[0]
    assert correction["request_digest"]
    assert "argv" not in correction
    assert row["investigations"] == {}
    active.finish()
    resumed = execution(tmp_path)
    calls = []

    def invalid(*args, **kwargs):
        calls.append(1)
        return {"investigation": request(external={})}

    with pytest.raises(investigations.InvestigationRequestError) as error:
        run(tmp_path, resumed, invalid)
    assert error.value.diagnostics["protocol_correction_exhausted"]
    assert len(calls) == 1
    resumed.finish()


def test_missing_inspection_uses_same_one_correction(tmp_path):
    active = execution(tmp_path)
    calls = []

    def session(root, prompt, config, **kwargs):
        calls.append(prompt)
        if len(calls) == 1:
            error = store.WorkflowError("Inspect original spec.md before declaring it.")
            error.inspection_missing_paths = ["spec.md"]
            error.diagnostics = {"seconds": 2, "usage": {"input_tokens": 5}}
            raise error
        assert "Do not invent inspected files" in prompt
        return {"investigation": request(external={})}

    with pytest.raises(investigations.InvestigationRequestError) as error:
        run(tmp_path, active, session)
    assert error.value.diagnostics["protocol_correction_exhausted"]
    assert len(calls) == 2
    assert (
        investigations._load(tmp_path, active.round_id)["managed_clock"][
            "worker_seconds"
        ]
        == 2
    )
    active.finish()


def unknown_path_response(inspected):
    """Run the real declaration validator so the reader sees the real error."""
    from fbk.workflow import review_context

    return review_context.validate_context(
        {"status": "complete", "inspected_files": inspected,
         "supporting_files": [], "missing_context": []},
        {"spec.md": "digest", "src/app.py": "digest"},
        ["spec.md"],
    )


def test_unknown_inspection_path_gets_one_correction_then_review_lands(tmp_path):
    active = execution(tmp_path)
    prompts = []

    def session(root, prompt, config, **kwargs):
        prompts.append(prompt)
        if len(prompts) == 1:
            try:
                unknown_path_response(["spec.md", "src/"])
            except store.WorkflowError as exc:
                exc.diagnostics = {"seconds": 2, "usage": {"input_tokens": 5}}
                raise
        assert "Protocol correction" in prompt
        assert "outside the controlled snapshot: src/" in prompt
        assert "spelled exactly as it appears in required_files" in prompt
        assert "Do not invent inspected files" in prompt
        return {"review": {"findings": []}, "seconds": 3, "usage": {"input_tokens": 9}}

    result = run(tmp_path, active, session)
    assert result["review"] == {"findings": []}
    assert result["seconds"] == 5
    assert len(prompts) == 2
    row = investigations._load(tmp_path, active.round_id)
    (corrections,) = row["reader_corrections"].values()
    (correction,) = corrections
    assert correction["category"] == "inspection-declaration-validation"
    assert correction["unknown_inspection_paths"] == ["src/"]
    assert "missing_inspection_paths" not in correction
    assert "src/" in correction["message"]
    active.finish()


def test_second_unknown_inspection_path_failure_exhausts_the_correction(tmp_path):
    active = execution(tmp_path)
    calls = []

    def session(root, prompt, config, **kwargs):
        calls.append(prompt)
        try:
            unknown_path_response(["spec.md", "./spec.md"])
        except store.WorkflowError as exc:
            exc.diagnostics = {"seconds": 1}
            raise

    with pytest.raises(store.WorkflowError) as error:
        run(tmp_path, active, session)
    assert error.value.inspection_unknown_paths == ["./spec.md"]
    assert error.value.diagnostics["protocol_correction_exhausted"]
    assert error.value.diagnostics["unknown_inspection_paths"] == ["./spec.md"]
    assert "already been used" in str(error.value)
    assert len(calls) == 2
    active.finish()


@pytest.mark.parametrize(
    "message", ["Review timed out", "Maximum turns reached", "Invalid JSON"]
)
def test_host_and_generic_errors_are_not_retried(tmp_path, message):
    active = execution(tmp_path)
    calls = []

    def session(*args, **kwargs):
        calls.append(1)
        raise store.WorkflowError(message)

    with pytest.raises(store.WorkflowError, match=message):
        run(tmp_path, active, session)
    assert calls == [1]
    assert "reader_corrections" not in investigations._load(tmp_path, active.round_id)
    active.finish()


UNAUTHORIZED = {"target": "service", "effects": ["read"]}


def forbid_launch(monkeypatch):
    monkeypatch.setattr(
        investigations,
        "run_command",
        lambda *a, **k: pytest.fail("Unauthorized command launched"),
    )


def test_valid_external_request_still_requires_real_authorization(
    tmp_path, monkeypatch
):
    """Refusal is evidence: nothing runs, no correction is spent, the reader finishes."""
    active = execution(tmp_path)
    prompts = []
    forbid_launch(monkeypatch)

    def session(root, prompt, config, **kwargs):
        prompts.append(prompt)
        if len(prompts) == 1:
            return {"investigation": request(external=UNAUTHORIZED), "seconds": 2}
        assert "existing explicit authorization" in prompt
        assert "no command was run" in prompt
        assert "Does the runner support this?" in prompt
        return {"review": {"findings": []}, "seconds": 3}

    result = run(tmp_path, active, session)
    assert result["review"] == {"findings": []}
    assert len(prompts) == 2
    assert not (tmp_path / ".fbk/runtime/investigations").exists()
    row = investigations._load(tmp_path, active.round_id)
    assert "reader_corrections" not in row
    (entry,) = row["investigations"].values()
    assert [a["status"] for a in entry["attempts"]] == ["refused"]
    refused = entry["attempts"][0]
    assert "workspace" not in refused
    assert refused["result"]["seconds"] == 0
    assert "existing explicit authorization" in refused["result"]["error"]
    assert entry["spent_seconds"] == 0
    assert "human_review" not in entry
    assert entry["resolution"]["attempts"] == [1]
    events = [e["type"] for e in row["events"]]
    assert "investigation-refused" in events
    assert "investigation-assignment-started" not in events
    managed.require_resolved(active)
    active.finish()


def test_repeated_unauthorized_request_exhausts_attempts_and_review_lands(
    tmp_path, monkeypatch
):
    """Exhausting a question is a caveat: the reader is told and finishes without it."""
    active = execution(tmp_path)
    prompts = []
    forbid_launch(monkeypatch)

    def session(root, prompt, config, **kwargs):
        prompts.append(prompt)
        if len(prompts) <= 3:
            assert '"exhausted"' not in prompt
            return {"investigation": request(external=UNAUTHORIZED), "seconds": 1}
        assert '"limit": "attempts"' in prompt
        assert "no further attempts are possible in this round" in prompt
        assert "report the question as unresolved in your review" in prompt
        if len(prompts) == 4:
            # Asking again returns the same evidence without spending anything.
            return {"investigation": request(external=UNAUTHORIZED), "seconds": 1}
        return {"review": {"findings": []}, "seconds": 3}

    result = run(tmp_path, active, session)
    assert result["review"] == {"findings": []}
    assert len(prompts) == 5
    assert prompts[3] == prompts[4]
    row = investigations._load(tmp_path, active.round_id)
    assert "reader_corrections" not in row
    (entry,) = row["investigations"].values()
    assert [a["status"] for a in entry["attempts"]] == ["refused"] * 3
    assert entry["human_review"]["limit"] == "attempts"
    assert entry["human_review"]["evidence"] == []
    assert entry["resolution"]["attempts"] == [1, 2, 3]
    assert row["investigation_human_review"]["limit"] == "attempts"
    assert "investigation-human-review-required" in [e["type"] for e in row["events"]]
    managed.require_resolved(active)
    active.finish()
    clock = investigations._load(tmp_path, active.round_id)["managed_clock"]
    assert "budget_exhausted" not in clock
    # The round stays usable for a later stage; only a stop for this question needs a human.
    execution(tmp_path).finish()


def test_reader_that_ignores_the_exhausted_note_twice_is_stopped(
    tmp_path, monkeypatch
):
    active = execution(tmp_path)
    prompts = []
    forbid_launch(monkeypatch)

    def session(root, prompt, config, **kwargs):
        prompts.append(prompt)
        return {"investigation": request(external=UNAUTHORIZED), "seconds": 1}

    with pytest.raises(store.WorkflowError, match="twice") as error:
        run(tmp_path, active, session)
    assert len(prompts) == 5
    diagnostics = error.value.diagnostics
    assert diagnostics["exhausted_question_repeated"].endswith("-probe")
    assert "budget_exhausted" not in diagnostics
    assert diagnostics["reader_responses"]["count"] == 5
    (entry,) = investigations._load(tmp_path, active.round_id)["investigations"].values()
    assert len(entry["attempts"]) == 3
    active.finish()


def test_per_question_time_exhaustion_is_a_caveat(tmp_path, monkeypatch):
    source = tmp_path / "sources"
    source.mkdir(exist_ok=True)
    active = managed.open_round(
        tmp_path,
        source,
        {"review_round_timeout": 60, "investigation_timeout": 10},
        "contract",
    )
    launches = []

    def worker(argv, cwd, timeout, prompt=None):
        launches.append(timeout)
        return {"exit_code": 0, "seconds": timeout, "stdout": "slow", "stderr": ""}

    monkeypatch.setattr(investigations, "run_command", worker)
    prompts = []

    def session(root, prompt, config, **kwargs):
        prompts.append(prompt)
        if len(prompts) == 1:
            return {"investigation": request(), "seconds": 1}
        assert '"limit": "time"' in prompt
        assert "no further attempts are possible in this round" in prompt
        assert "slow" in prompt
        return {"review": {"findings": []}, "seconds": 1}

    result = run(tmp_path, active, session)
    assert result["review"] == {"findings": []}
    assert launches == [10]
    (entry,) = investigations._load(tmp_path, active.round_id)["investigations"].values()
    assert entry["human_review"]["limit"] == "time"
    assert entry["spent_seconds"] == 10
    assert entry["resolution"]["attempts"] == [1]
    managed.require_resolved(active)
    active.finish()


def test_review_time_exhaustion_still_stops_the_reader(tmp_path, monkeypatch):
    """The whole review's clock is the session safety net and stays fatal."""
    active = execution(tmp_path)
    monkeypatch.setattr(
        investigations,
        "run_command",
        lambda argv, cwd, timeout, prompt=None: {
            "exit_code": 0, "seconds": timeout, "stdout": "", "stderr": ""
        },
    )

    def session(root, prompt, config, **kwargs):
        return {"investigation": request(), "seconds": 1}

    with pytest.raises(store.WorkflowError, match="review-time budget") as error:
        run(tmp_path, active, session)
    assert error.value.diagnostics["budget_exhausted"] == "investigation-review-time"
    row = investigations._load(tmp_path, active.round_id)
    (entry,) = row["investigations"].values()
    assert entry["human_review"]["limit"] == "review-time"
    with pytest.raises(store.WorkflowError, match="Unresolved investigation"):
        managed.require_resolved(active)
    active.finish()


def test_investigate_failure_keeps_reader_diagnostics(tmp_path, monkeypatch):
    active = execution(tmp_path)
    recorded = []
    record_worker = active.record_worker
    monkeypatch.setattr(
        active, "record_worker", lambda r: (recorded.append(r), record_worker(r))
    )

    def broken(request, reader_key):
        raise store.WorkflowError("Experiment snapshot contains symlinks")

    monkeypatch.setattr(active, "investigate", broken)

    def session(root, prompt, config, **kwargs):
        return {
            "investigation": request(),
            "seconds": 4,
            "usage": {"input_tokens": 11},
        }

    with pytest.raises(store.WorkflowError, match="symlinks") as error:
        run(tmp_path, active, session)
    diagnostics = error.value.diagnostics
    assert diagnostics["investigation_round"] == active.round_id
    summary = diagnostics["reader_responses"]
    assert summary["count"] == 1
    assert summary["seconds"] == 4
    assert summary["usage"] == [{"input_tokens": 11}]
    assert summary["last_investigation_request_digest"] == store.digest(request())
    assert "argv" in summary["last_investigation_request_fields"]
    assert recorded[-1] is diagnostics
    clock = investigations._load(tmp_path, active.round_id)["managed_clock"]
    assert clock["worker_seconds"] == 4  # the response is charged once, not twice
    assert clock["worker_usage"] == [{"input_tokens": 11}]
    active.finish()


def test_slash_recovery_keeps_state_unchanged_and_corruption_denied(project):
    before = store.load(project, "feature")
    payload = {
        "hook_event_name": "UserPromptExpansion",
        "session_id": "s",
        "command_name": "fbk-spec",
        "command_args": "feature",
    }
    result = hooks.handle(project, payload)
    assert "could not open spec" in result["hookSpecificOutput"]["additionalContext"]
    assert store.load(project, "feature") == before
    path = project / ".fbk/feature/state.json"
    path.write_text("{}")
    assert hooks.handle(project, payload)["decision"] == "block"
