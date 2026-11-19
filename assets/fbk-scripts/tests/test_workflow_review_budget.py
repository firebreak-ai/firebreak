"""Native session limits are explicit: the turn ceiling and the per-session time limit are
safety nets whose breach is an ordinary failed round; only the shared managed round clock
still requires human intervention."""

import json
import subprocess

import pytest
from fbk.workflow import review, store
from tests import test_workflow_lifecycle as scenarios
from tests.test_workflow_commands import call
from tests.test_workflow_phase_handoff import session_packet

project = scenarios.project


def success():
    return {"exit_code": 0, "seconds": 1, "stderr": "", "stdout": json.dumps({
        "subtype": "success", "structured_output": {
            "summary": "Inspected sources", "findings": [],
            "context": {"status": "complete", "inspected_files": [],
                        "supporting_files": [], "missing_context": []},
        }})}


@pytest.mark.parametrize("config, expected", [({}, 100), ({"reviewer_max_turns": 24}, 24)])
def test_native_session_uses_configured_turn_budget(tmp_path, monkeypatch, config, expected):
    calls = []
    def command(argv, root, timeout, prompt):
        calls.append((argv, timeout))
        return success()
    monkeypatch.setattr(review, "run_command", command)
    review.claude_review(tmp_path, "Inspect", config)
    assert len(calls) == 1
    argv, timeout = calls[0]
    assert argv[argv.index("--max-turns") + 1] == str(expected)
    assert timeout == 1200


@pytest.mark.parametrize("config, expected", [({}, 1200), ({"review_timeout": 600}, 600)])
def test_native_session_time_limit_is_passed_to_the_command_and_stated_in_the_prompt(
    tmp_path, monkeypatch, config, expected
):
    calls = []
    def command(argv, root, timeout, prompt):
        calls.append((timeout, prompt))
        return success()
    monkeypatch.setattr(review, "run_command", command)
    review.claude_review(tmp_path, "Inspect", config)
    [(timeout, prompt)] = calls
    assert timeout == expected
    # The sentence is rendered by the constraint registry from the same configured value
    # and placed in the packet by the assembler (tests/test_workflow_constraints.py).
    from fbk.workflow import constraints

    [rule] = [r for r in constraints.rules(constraints.render("review", config, review.SCHEMA))
              if r["id"] == "session-time-limit"]
    assert rule["rule"] == (
        f"This session is stopped after {expected} seconds (the configured review_timeout) "
        "and the attempt is then recorded as failed, so return the complete review within that time; "
        "when the whole round's clock has less time left, this session is stopped at that shorter limit instead."
    )


@pytest.mark.parametrize("value", [True, 0, -1, 1.5, 12.0, "24", None])
def test_invalid_turn_budget_is_rejected_before_launch(tmp_path, monkeypatch, value):
    def command(*args):
        pytest.fail("An invalid review budget must not launch a paid session")
    monkeypatch.setattr(review, "run_command", command)
    with pytest.raises(store.WorkflowError, match="reviewer_max_turns"):
        review.claude_review(tmp_path, "Inspect", {"reviewer_max_turns": value})


@pytest.mark.parametrize("exit_code", [0, 1])
def test_host_turn_ceiling_fails_with_diagnostics_but_no_budget_marker(tmp_path, monkeypatch, exit_code):
    envelope = {"subtype": "error_max_turns", "is_error": True, "num_turns": 24}
    monkeypatch.setattr(review, "run_command", lambda *args: {
        "exit_code": exit_code, "seconds": 90, "stdout": json.dumps(envelope),
        "stderr": "unrelated host warning",
    })
    with pytest.raises(store.WorkflowError, match="24 turn ceiling") as failed:
        review.claude_review(tmp_path, "Inspect", {"reviewer_max_turns": 24})
    diagnostic = failed.value.diagnostics
    assert "budget_exhausted" not in diagnostic
    assert diagnostic["category"] == "host"
    assert diagnostic["exit_code"] == exit_code
    assert diagnostic["reviewer_max_turns"] == 24
    assert diagnostic["review_timeout"] == 1200
    assert diagnostic["num_turns"] == 24
    assert json.loads(diagnostic["stdout"]) == envelope


class TimedOutProcess:
    """A subprocess that never answers before its time limit."""
    pid = 123
    returncode = -9

    def communicate(self, input=None, timeout=None):
        if timeout is not None:
            raise subprocess.TimeoutExpired("claude", timeout)

    def wait(self, timeout=None):
        return self.returncode


def simulate_timeout(monkeypatch):
    monkeypatch.setattr(review.subprocess, "Popen", lambda *a, **kw: TimedOutProcess())
    monkeypatch.setattr(review.os, "killpg", lambda *a: None)
    monkeypatch.setattr(review, "_process_group_running", lambda group: False)


def test_session_timeout_fails_with_diagnostics_but_no_budget_marker(tmp_path, monkeypatch):
    simulate_timeout(monkeypatch)
    with pytest.raises(store.WorkflowError, match="exceeded its 600s time limit") as failed:
        review.claude_review(tmp_path, "Inspect", {"review_timeout": 600, "reviewer_max_turns": 24})
    diagnostic = failed.value.diagnostics
    assert "budget_exhausted" not in diagnostic
    assert diagnostic["category"] == "timeout"
    assert diagnostic["timeout_seconds"] == 600
    assert diagnostic["review_timeout"] == 600
    assert diagnostic["reviewer_max_turns"] == 24
    assert isinstance(diagnostic["seconds"], (int, float))
    assert "stdout" in diagnostic and "stderr" in diagnostic


@pytest.mark.parametrize("mode", ["single", "council"])
def test_session_timeout_is_an_ordinary_failed_round_governed_by_the_round_limit(project, monkeypatch, mode):
    scenarios.accept(project, "intent")
    if mode == "council":
        call(project, "review-plan", "feature", "--phase", "spec", "--mode", "council",
             "--members", "guardian", "builder", "--reason", "Independent perspectives")
    config = store.project_config(project)
    store.atomic_json(project / ".fbk/config.json", {**config, "review_timeout": 600})
    launches = []
    real_popen = subprocess.Popen

    def popen(argv, *args, **kwargs):
        # Only the reviewer sessions hang; the runtime's own git commands run for real.
        if argv[0] != "claude":
            return real_popen(argv, *args, **kwargs)
        launches.append(argv)
        return TimedOutProcess()

    simulate_timeout(monkeypatch)
    monkeypatch.setattr(review.subprocess, "Popen", popen)
    call(project, "phase-enter", "spec", "feature")
    with pytest.raises(store.WorkflowError) as failed:
        call(project, "phase-close", "spec", "feature")
    assert "Human help is required" not in str(failed.value)
    assert "exceeded its 600s time limit" in str(failed.value)
    count = len(launches)
    assert count > 0
    work = store.load(project, "feature")["phases"]["spec"]
    assert len(work["rounds"]) == 1
    assert "budget_exhausted" not in work
    assert work["rounds"][-1]["error"]
    diagnostics = [work["rounds"][-1].get("failure_diagnostics")]
    result = work["rounds"][-1].get("result") or {}
    diagnostics.append((result.get("failure") or {}).get("diagnostics"))
    diagnostics.extend(item.get("diagnostics") for item in result.get("failures", []))
    retained = [item for item in diagnostics if item]
    assert retained and all("budget_exhausted" not in item for item in retained)
    assert all(item["category"] == "timeout" and item["timeout_seconds"] == 600
               and item["review_timeout"] == 600 for item in retained)
    if mode == "council":
        # A timed-out reader is a failed member like any other reader failure.
        assert {item["member"] for item in result["failures"]} == {"guardian", "builder"}
    status = call(project, "status", "feature")[0]
    assert status["status"] != "human-review-required"
    assert status["human_review"] is None
    assert not any(e["event"] == "human-review-required"
                   for e in store.load(project, "feature")["events"])
    # The next close attempt runs the reviewer again without extend-review.
    with pytest.raises(store.WorkflowError) as failed:
        call(project, "phase-close", "spec", "feature")
    assert "Human help is required" not in str(failed.value)
    assert len(launches) > count
    assert len(store.load(project, "feature")["phases"]["spec"]["rounds"]) == 2


def test_managed_round_clock_exhaustion_still_pauses_for_human_help(tmp_path, monkeypatch):
    """The per-round wall clock is the safety net that still needs a human: a session cut
    short by that clock is recorded as the clock's exhaustion, not as a session timeout."""
    from fbk.workflow import managed_investigations as managed, review_execution
    source = tmp_path / "snapshot"
    source.mkdir()
    ticks = [0.0]
    monkeypatch.setattr(review_execution.time, "monotonic", lambda: ticks[0])
    execution = managed.open_round(tmp_path, source, {"review_round_timeout": 10}, "contract")
    launched = []

    def session(root, prompt, config, **kwargs):
        launched.append(config["review_timeout"])
        ticks[0] += config["review_timeout"]
        error = store.WorkflowError(f"Command claude exceeded its {config['review_timeout']}s time limit")
        error.diagnostics = {"category": "timeout", "timeout_seconds": config["review_timeout"],
                             "seconds": config["review_timeout"], "stdout": "", "stderr": ""}
        raise error

    config = {"review_timeout": 600, "review_round_timeout": 10,
              "_managed_project_root": str(tmp_path), "_managed_execution": execution}
    with pytest.raises(store.WorkflowError, match="human help is required") as failed:
        managed.run_reader(tmp_path, "Inspect", config, session,
                           schema=review.SCHEMA, validator=review.validate_single)
    assert launched == [10]
    assert failed.value.diagnostics["budget_exhausted"] == "review-round-time"
    assert failed.value.diagnostics["investigation_round"] == execution.round_id
    execution.finish()
    with pytest.raises(store.WorkflowError, match="human"):
        managed.open_round(tmp_path, source, {"review_round_timeout": 10}, "contract")


def test_incomplete_context_is_a_recorded_verdict_not_a_harness_failure(project, monkeypatch):
    scenarios.accept(project, "intent")
    missing = "design/cache.md cited by spec.md is not in the snapshot"
    retained = {"title": "Spec cites an absent cache design", "severity": "suggestion",
                "location": ".fbk/feature/spec.md:1", "evidence": "The reference resolves to nothing.",
                "remedy": "Add the design or drop the reference."}
    calls = []

    def command(argv, root, timeout, prompt):
        calls.append(prompt)
        inspected = sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())
        first = len(calls) == 1
        return {"exit_code": 0, "seconds": 3, "stderr": "", "stdout": json.dumps({
            "subtype": "success", "structured_output": {
                "summary": "Could not decide: the cited cache design is absent." if first
                else "Inspected sources.",
                "findings": [retained] if first else [],
                "context": {"status": "incomplete" if first else "complete",
                            "inspected_files": inspected, "supporting_files": [],
                            "missing_context": [missing] if first else []}}})}

    monkeypatch.setattr(review, "run_command", command)
    call(project, "phase-enter", "spec", "feature")
    with pytest.raises(store.WorkflowError) as failed:
        call(project, "phase-close", "spec", "feature")
    assert str(failed.value).startswith("Review incomplete; missing context: " + missing)
    assert "Human help is required" not in str(failed.value)
    assert len(calls) == 1
    work = store.load(project, "feature")["phases"]["spec"]
    assert len(work["rounds"]) == 1
    round_record = work["rounds"][0]
    assert round_record["error"] == "Review incomplete; missing context: " + missing
    assert "failure_diagnostics" not in round_record
    assert "budget_exhausted" not in work
    result = round_record["result"]
    assert result["incomplete_context"] == [
        {"member": None, "stage": "independent", "missing_context": [missing]}]
    assert result["error"] == round_record["error"]
    assert result["readers"][0]["review"]["findings"] == [retained]
    assert result["readers"][0]["review"]["summary"].startswith("Could not decide")
    assert result["readers"][0]["context"]["status"] == "incomplete"
    status = call(project, "status", "feature")[0]
    assert status["status"] != "human-review-required"
    assert status["human_review"] is None
    events = store.load(project, "feature")["events"]
    assert not any(e["event"] == "human-review-required" for e in events)
    # The next close attempt runs the reviewer again rather than reusing the incomplete verdict.
    accepted = call(project, "phase-close", "spec", "feature")
    assert accepted["accepted_phase"] == "spec"
    assert len(calls) == 2
    assert len(store.load(project, "feature")["phases"]["spec"]["rounds"]) == 2


@pytest.mark.parametrize("mode", ["single", "council"])
def test_turn_ceiling_is_an_ordinary_failed_round_governed_by_the_round_limit(project, monkeypatch, mode):
    scenarios.accept(project, "intent")
    if mode == "council":
        call(project, "review-plan", "feature", "--phase", "spec", "--mode", "council",
             "--members", "guardian", "builder", "--reason", "Independent perspectives")
    calls = []
    def command(*args):
        calls.append(args)
        return {"exit_code": 1, "seconds": 10, "stderr": "", "stdout": json.dumps({
            "subtype": "error_max_turns", "is_error": True, "num_turns": 100})}
    monkeypatch.setattr(review, "run_command", command)
    call(project, "phase-enter", "spec", "feature")
    with pytest.raises(store.WorkflowError) as failed:
        call(project, "phase-close", "spec", "feature")
    assert "Human help is required" not in str(failed.value)
    count = len(calls)
    assert count > 0
    work = store.load(project, "feature")["phases"]["spec"]
    assert len(work["rounds"]) == 1
    assert "budget_exhausted" not in work
    assert work["rounds"][-1]["error"]
    diagnostics = [work["rounds"][-1].get("failure_diagnostics")]
    result = work["rounds"][-1].get("result") or {}
    diagnostics.append((result.get("failure") or {}).get("diagnostics"))
    diagnostics.extend(item.get("diagnostics") for item in result.get("failures", []))
    retained = [item for item in diagnostics if item]
    assert retained and all("budget_exhausted" not in item for item in retained)
    assert any(item.get("num_turns") == 100 for item in retained)
    status = call(project, "status", "feature")[0]
    assert status["status"] != "human-review-required"
    assert status["human_review"] is None
    call(project, "suspend", "feature", "--reason", "Pause between review attempts")
    assert session_packet(project, "fresh-session")["human_review"] is None
    call(project, "phase-enter", "spec", "feature")
    with pytest.raises(store.WorkflowError) as failed:
        call(project, "phase-close", "spec", "feature")
    assert "Human help is required" not in str(failed.value)
    assert len(calls) > count
    assert len(store.load(project, "feature")["phases"]["spec"]["rounds"]) == 2
    events = store.load(project, "feature")["events"]
    assert not any(e["event"] == "human-review-required" for e in events)
    # The phase round limit, not the turn ceiling, is what finally asks for human help.
    with pytest.raises(store.WorkflowError, match="Human help is required"):
        call(project, "phase-close", "spec", "feature")
    work = store.load(project, "feature")["phases"]["spec"]
    assert len(work["rounds"]) == work["round_limit"] == 3
    assert call(project, "status", "feature")[0]["status"] == "human-review-required"


@pytest.mark.parametrize("mode", ["single", "council"])
def test_oversize_brief_is_refused_before_launch_without_spending_a_round(project, monkeypatch, mode):
    from fbk.workflow import engine

    scenarios.accept(project, "intent")
    if mode == "council":
        call(project, "review-plan", "feature", "--phase", "spec", "--mode", "council",
             "--members", "guardian", "builder", "--reason", "Independent perspectives")
    real_focus = review.focus_brief
    monkeypatch.setattr(review, "focus_brief",
                        lambda *a, **kw: {**real_focus(*a, **kw), "coverage": "x" * 170000})
    launches = []
    real_popen = subprocess.Popen

    def popen(argv, *args, **kwargs):
        if argv[0] == "claude":
            launches.append(argv)
        return real_popen(argv, *args, **kwargs)

    monkeypatch.setattr(review.subprocess, "Popen", popen)
    call(project, "phase-enter", "spec", "feature")
    # More attempts than the round limit: none is spent, so none escalates to a human.
    for _ in range(4):
        with pytest.raises(store.WorkflowError) as failed:
            call(project, "phase-close", "spec", "feature")
        assert "Human help is required" not in str(failed.value)
        assert "Firebreak defect" in str(failed.value)
        assert "reading_priority" in str(failed.value)
        assert "split the review unit" not in str(failed.value)
    assert launches == []
    work = store.load(project, "feature")["phases"]["spec"]
    assert len(work["rounds"]) == 4 and all(r["unspent"] and r["error"] for r in work["rounds"])
    assert engine.spent_rounds(work) == 0
    assert call(project, "status", "feature")[0]["human_review"] is None
