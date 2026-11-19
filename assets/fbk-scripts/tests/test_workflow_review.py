"""Review selection and council execution: exercise state transitions and failed stages."""

import copy

import pytest
from fbk.workflow import close, council, engine, hooks, review, review_plan, store

from tests import test_workflow_lifecycle as scenarios
from tests.council_stub import Council
from tests.test_workflow_commands import call

project = scenarios.project


def choose(root, mode, phase="spec", members=None):
    return call(
        root,
        "review-plan",
        "feature",
        "--phase",
        phase,
        "--mode",
        mode,
        "--reason",
        "The operator selected this review.",
        "--members",
        *(members or []),
    )


def at_spec(root):
    scenarios.accept(root, "intent")
    scenarios.enter(root, "spec")


def native(findings=()):
    return {
        "review": {
            "summary": "Inspected the relevant source.",
            "findings": list(findings),
        },
        "seconds": 1,
        "usage": {"test-model": {"inputTokens": 100}},
    }


def finding():
    return copy.deepcopy(scenarios.blocking_review()["review"]["findings"][0])


def assessor(ids, disposition="supported", canonical=False):
    return {
        "review": {
            "summary": "Checked claims against source.",
            "assessments": [
                {
                    "finding_id": i,
                    "disposition": disposition,
                    "evidence": "src/app.py:1 retains the resource.",
                    **(
                        {"finding": None if disposition == "refuted" else finding()}
                        if canonical
                        else {}
                    ),
                }
                for i in ids
            ],
        },
        "seconds": 1,
        "usage": {"test-model": {"inputTokens": 100}},
    }


def test_unselected_close_never_starts_a_reviewer(project):
    at_spec(project)
    with store.transaction(project):
        record = store.load(project, "feature")
        record["review_plans"]["spec"] = None
        store.save(project, record)
    called = []
    with pytest.raises(store.WorkflowError, match="Choose single or council"):
        close.close_phase(
            project, "feature", "spec", "s", reviewer=lambda *a: called.append(a)
        )
    assert not called
    work = store.load(project, "feature")["phases"]["spec"]
    assert work["pending"] is None and work["rounds"] == []


def test_selection_survives_restart_and_default_changes(project):
    selected = choose(project, "council", members=["guardian", "builder"])
    call(
        project,
        "review-default",
        "--phase",
        "spec",
        "--mode",
        "single",
        "--reason",
        "New default.",
    )
    at_spec(project)
    status = call(project, "status", "feature")[0]
    assert status["review_plans"]["spec"] == selected
    assert "council" in status["review_guidance"]
    assert (
        choose(project, "council", members=["builder", "guardian"])["id"]
        == selected["id"]
    )


def test_unresolved_choice_inherits_new_default_on_entry(project):
    with store.transaction(project):
        record = store.load(project, "feature")
        record["review_plans"]["spec"] = None
        store.save(project, record)
    call(
        project,
        "review-default",
        "--phase",
        "spec",
        "--mode",
        "council",
        "--members",
        "guardian",
        "builder",
        "--reason",
        "Council for future spec decisions.",
    )
    at_spec(project)
    plan = store.load(project, "feature")["review_plans"]["spec"]
    assert plan["mode"] == "council" and plan["source"] == "project"


def test_design_and_spec_choices_are_independent(tmp_path):
    call(tmp_path, "workflow-init")
    call(tmp_path, "unit-init", "feature")
    choose(tmp_path, "council", phase="design", members=["architect", "builder"])
    choose(tmp_path, "single")
    record = store.load(tmp_path, "feature")
    assert record["design"]
    assert record["review_plans"]["design"]["mode"] == "council"
    assert record["review_plans"]["spec"]["mode"] == "single"
    call(
        tmp_path,
        "route",
        "feature",
        "--design",
        "off",
        "--reason",
        "Architecture unchanged.",
    )
    assert store.load(tmp_path, "feature")["review_plans"]["spec"]["mode"] == "single"
    with pytest.raises(store.WorkflowError, match="applicable"):
        choose(tmp_path, "single", phase="design")


def test_changing_review_does_not_invalidate_earlier_intent(project):
    scenarios.accept(project, "intent")
    choose(project, "council", members=["guardian", "builder"])
    assert engine.phase_state(project, store.load(project, "feature"))[:2] == (
        "spec",
        "ready",
    )


def test_accepted_selection_requires_reopen(project):
    scenarios.accept(project, "intent")
    scenarios.accept(project, "spec")
    with pytest.raises(store.WorkflowError, match="Reopen"):
        choose(project, "council", members=["builder", "guardian"])
    assert engine.phase_state(project, store.load(project, "feature"))[:2] == (
        "breakdown",
        "ready",
    )


def test_mode_change_invalidates_cached_review_and_grant_without_resetting_budget(
    project,
):
    at_spec(project)
    with pytest.raises(store.WorkflowError):
        close.close_phase(
            project, "feature", "spec", "s", reviewer=scenarios.blocking_review
        )
    call(
        project,
        "approve",
        "feature",
        "close-over-findings",
        "--phase",
        "spec",
        "--reason",
        "Accept known defect.",
    )
    original = store.load(project, "feature")["review_plans"]["spec"]["id"]
    choose(project, "council", members=["builder", "guardian"])
    choose(project, "single")
    assert store.load(project, "feature")["review_plans"]["spec"]["id"] != original
    called = []

    def blocked(*args):
        called.append(True)
        return scenarios.blocking_review()

    with pytest.raises(store.WorkflowError, match="approval required"):
        close.close_phase(project, "feature", "spec", "s", reviewer=blocked)
    assert called == [True]
    work = store.load(project, "feature")["phases"]["spec"]
    assert len(work["rounds"]) == 2 and work["round_limit"] == 3


def test_running_close_cannot_change_mode(project):
    at_spec(project)

    def inspect(*args):
        with pytest.raises(store.WorkflowError, match="running close"):
            choose(project, "council", members=["builder", "guardian"])
        return scenarios.clean_review()

    assert (
        close.close_phase(project, "feature", "spec", "s", reviewer=inspect)[
            "accepted_phase"
        ]
        == "spec"
    )


def test_out_of_band_mode_change_stales_inflight_result(project):
    at_spec(project)

    def change(*args):
        with store.transaction(project):
            record = store.load(project, "feature")
            record["review_plans"]["spec"]["id"] = "changed-outside-supported-command"
            store.save(project, record)
        return scenarios.clean_review()

    with pytest.raises(store.WorkflowError, match="Inputs changed"):
        close.close_phase(project, "feature", "spec", "s", reviewer=change)
    assert store.load(project, "feature")["phases"]["spec"]["evidence"] is None


def test_single_result_cannot_satisfy_council_choice(project):
    at_spec(project)
    choose(project, "council", members=["builder", "guardian"])
    with pytest.raises(store.WorkflowError, match="does not match"):
        close.close_phase(
            project, "feature", "spec", "s", reviewer=scenarios.clean_review
        )


@pytest.mark.parametrize("event", ["UserPromptExpansion", "PreToolUse"])
def test_entry_hooks_surface_saved_choice(project, event):
    scenarios.accept(project, "intent")
    choose(project, "council", members=["guardian", "builder"])
    payload = {
        "hook_event_name": event,
        "session_id": "s",
        "command_name": "fbk-spec",
        "command_args": "feature",
        "tool_name": "Skill",
        "tool_input": {"skill": "fbk-spec", "args": "feature"},
    }
    output = hooks.handle(project, payload)
    assert (
        "spec: council (builder, guardian)"
        in output["hookSpecificOutput"]["additionalContext"]
    )
    assert store.load(project, "feature")["review_plans"]["spec"]["mode"] == "council"


@pytest.mark.parametrize(
    "members",
    [
        ["guardian"],
        ["guardian", "guardian"],
        ["architect", "guardian", "builder", "security"],
    ],
)
def test_invalid_council_selection_does_not_mutate_state(project, members):
    before = store.load(project, "feature")
    with pytest.raises(store.WorkflowError):
        choose(project, "council", members=members)
    assert store.load(project, "feature") == before


def test_selected_single_ignores_optional_external_reader(project, monkeypatch):
    monkeypatch.setattr(review, "claude_review", lambda *a: native())
    config = store.project_config(project)
    config["second_reader"] = ["must-not-run"]
    store.atomic_json(project / ".fbk/config.json", config)
    monkeypatch.setattr(
        review,
        "run_command",
        lambda *a: pytest.fail("single selection invoked external reader"),
    )
    assert review.review(project, "feature", "spec", {}, [])["shape"] == "single"


def test_council_keeps_a_supported_minority_proposal_and_isolates_the_openings(project):
    minority = {**finding(), "title": "secret-minority-finding"}
    scripted = Council(openings={"guardian": [minority]})
    result = council.run(project, "Inspect cancellation", {}, "spec",
                         ["architect", "guardian", "security"], scripted)
    assert "error" not in result
    assert result["review"]["findings"][0]["title"] == "secret-minority-finding"
    openings = [prompt for step, member, prompt in scripted.prompts if step == "opening"]
    assert openings and not any("secret-minority-finding" in p for p in openings)
    assert "secret-minority-finding" in scripted.prompts[-1][2]


def test_council_failure_is_persisted_without_fallback(project, monkeypatch):
    at_spec(project)
    choose(project, "council", members=["builder", "guardian"])

    def reader(root, prompt, config, **kwargs):
        if "Council member: guardian." in prompt:
            raise store.WorkflowError("review host timed out")
        return native()

    monkeypatch.setattr(review, "claude_review", reader)
    with pytest.raises(store.WorkflowError, match="no single-reviewer fallback"):
        call(project, "phase-close", "spec", "feature")
    work = store.load(project, "feature")["phases"]["spec"]
    assert work["pending"] is None and work["evidence"] is None
    assert work["rounds"][0]["result"]["readers"][0]["usage"]


def test_council_cannot_drop_a_proposal_by_leaving_it_out_of_the_stances(project):
    scripted = Council(openings={"guardian": [finding()]})

    def omits(root, prompt, config, **kwargs):
        response = scripted(root, prompt, config, **kwargs)
        if "stances" in response["review"]:
            response["review"]["stances"] = []
        return response

    result = council.run(project, "Inspect", {}, "spec", ["architect", "guardian"], omits)
    assert "every listed proposal" in result["error"]
    assert result["review"] is None


def test_a_supported_blocker_stops_the_close(project, monkeypatch):
    at_spec(project)
    choose(project, "council", members=["builder", "guardian"])
    monkeypatch.setattr(review, "claude_review", Council(openings={"guardian": [finding()]}))
    with pytest.raises(store.WorkflowError, match="blocking defects"):
        call(project, "phase-close", "spec", "feature")
    assert store.load(project, "feature")["phases"]["spec"]["evidence"] is None


def test_council_clean_result_closes_and_retains_selection(project, monkeypatch):
    at_spec(project)
    selected = choose(project, "council", members=["builder", "guardian"])
    monkeypatch.setattr(review, "claude_review", lambda *a, **k: native())
    result = call(project, "phase-close", "spec", "feature")
    assert result["review_shape"] == "council"
    accepted = store.load(project, "feature")["phases"]["spec"]["evidence"]
    assert accepted["review_plan"] == selected
    assert len(accepted["review"]["readers"]) == 2


def test_council_rejects_unbounded_output(project):
    result = council.run(
        project,
        "Inspect",
        {},
        "design",
        ["architect", "guardian"],
        lambda *a, **k: native([finding()] * 9),
    )
    assert "bounded finding format" in result["error"]
    assert result["review"] is None


def test_council_openings_skip_the_single_reviewer_role_line(project, monkeypatch):
    at_spec(project)
    prompts = []

    def reader(root, prompt, config, **kwargs):
        prompts.append(prompt)
        return native([])

    monkeypatch.setattr(review, "claude_review", reader)
    review.review(project, "feature", "spec", {}, [])
    assert prompts[0].startswith("Independently review the spec work")
    choose(project, "council", members=["builder", "guardian"])
    prompts.clear()
    review.review(project, "feature", "spec", {}, [])
    openings = [p for p in prompts if "Council member: " in p]
    assert len(openings) == 2
    assert not any("Independently review" in p for p in openings)
    assert all("You are one member of a review council" in p for p in openings)


def test_every_council_includes_the_builder(project):
    before = store.load(project, "feature")
    with pytest.raises(store.WorkflowError, match="Every council includes the builder"):
        choose(project, "council", members=["architect", "guardian"])
    assert store.load(project, "feature") == before


def test_intent_and_breakdown_close_with_a_single_reviewer_when_no_plan_is_recorded(project):
    record = store.load(project, "feature")
    record["review_plans"]["spec"] = None
    assert record["review_plans"].get("intent") is None
    assert review_plan.require(record, "intent") is None
    assert review_plan.require(record, "breakdown") is None
    with pytest.raises(store.WorkflowError, match="Choose single or council review for spec"):
        review_plan.require(record, "spec")
    assert "intent" not in review_plan.context(record) and "breakdown" not in review_plan.context(record)


def test_the_council_is_available_for_intent(project, monkeypatch):
    scenarios.enter(project, "intent")
    choose(project, "council", phase="intent", members=["builder", "advocate"])
    scripted = Council()
    monkeypatch.setattr(review, "claude_review", scripted)
    accepted = call(project, "phase-close", "intent", "feature")
    assert accepted["accepted_phase"] == "intent" and accepted["review_shape"] == "council"
    [opening, _] = [p for step, _, p in scripted.prompts if step == "opening"]
    assert "Intent focus:" in opening
