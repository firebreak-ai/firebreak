"""Continuation and worker handoffs preserve current intent across fresh sessions."""

import json
import sys
from pathlib import Path

import pytest
from fbk.workflow import decisions, engine, evidence, handoff, hooks, store
from .test_workflow_lifecycle import (  # noqa: F401
    blocking_review,
    mutate,
    prepare_implementation,
    project as workflow_project,
)

from .refactor_plan import complete_refactor_tasks, with_refactor

project = workflow_project


def launch(project, **kwargs):
    return mutate(
        project,
        handoff.start_task,
        "s",
        "cancel",
        "worker",
        acceptance_refs=[".fbk/feature/spec.md"],
        **kwargs,
    )


def finish(project, **kwargs):
    values = {
        "changed_files": ["src/app.py"],
        "checks": [
            {
                "argv": [sys.executable, "tests/check.py"],
                "exit_code": 0,
                "evidence": "Cancellation releases once.",
            }
        ],
        "unresolved": [],
        "outcome": "Cancellation releases exactly once.",
    }
    values.update(kwargs)
    return mutate(project, handoff.finish_task, "s", "cancel", **values)


def test_resume_preserves_question_and_current_blocker_evidence(project):
    prepare_implementation(project)
    with store.transaction(project):
        record = store.load(project, "feature")
        record["phases"]["implement"]["rounds"].append(
            {
                "revision": evidence.revision(project, record, "implement"),
                "generation": 0,
                "result": blocking_review(),
            }
        )
        engine.suspend(
            project,
            record,
            "s",
            "Should cancellation preserve the existing retry policy?",
        )
    output = hooks.handle(
        project,
        {"hook_event_name": "SessionStart", "session_id": "new", "source": "compact"},
    )
    packet = json.loads(
        output["hookSpecificOutput"]["additionalContext"].split("\n", 1)[1]
    )
    assert (
        packet["pending"] == "Should cancellation preserve the existing retry policy?"
    )
    assert (
        packet["findings"][0]["evidence"]
        == "A canceled task leaves its resource allocated."
    )
    assert packet["remaining_attempts"] == 2
    assert ".fbk/feature/prd.md" in packet["sources"]


def test_changed_sources_do_not_present_old_findings_as_current(project):
    prepare_implementation(project)
    record = store.load(project, "feature")
    record["phases"]["implement"]["rounds"].append(
        {
            "revision": evidence.revision(project, record, "implement"),
            "generation": 0,
            "result": blocking_review(),
        }
    )
    (project / "src/app.py").write_text("release()")
    packet = handoff.continuation(project, record)
    assert not packet["findings_current"]
    assert packet["findings"] == []
    assert packet["findings_revision"]


def test_many_units_preserve_owned_unit_and_emit_valid_bounded_context(project):
    prepare_implementation(project)
    records = []
    with store.transaction(project):
        for number in range(100):
            records.append(
                engine.initialize(
                    project, f"a-long-unrelated-name-{number}", design=False
                )
            )
    records.append(store.load(project, "feature"))
    packet = handoff.session_context(project, records, "s", max_chars=3500)
    assert packet["unit"] == "feature"
    assert len(json.dumps(packet, ensure_ascii=False)) <= 3500
    assert packet["omitted"]["other_units"] > 0
    assert json.loads(json.dumps(packet))["revision"]


def test_launch_requires_acceptance_context_and_blocks_other_worker_writes(project):
    prepare_implementation(project)
    with pytest.raises(store.WorkflowError, match="acceptance_refs"):
        mutate(project, handoff.start_task, "s", "cancel", "worker", acceptance_refs=[])
    packet = launch(project)
    assert set(packet["acceptance_refs"]) == {".fbk/feature/prd.md", ".fbk/feature/spec.md", ".fbk/feature/spec.md#cancel-once"}
    record = store.load(project, "feature")
    handoff.check_task_write(record, "src/app.py", "worker", "s")
    with pytest.raises(store.WorkflowError, match="Assign this worker"):
        handoff.check_task_write(record, "src/app.py", "other", "s")
    with pytest.raises(store.WorkflowError, match="lead does not edit"):
        handoff.check_task_write(record, "src/app.py", None, "s")
    with pytest.raises(store.WorkflowError, match="outside"):
        handoff.check_task_write(record, "src/unowned.py", "worker", "s")


def test_subagent_start_injects_assignment_and_tracks_worker(project):
    prepare_implementation(project)
    launch(project)
    result = hooks.handle(
        project,
        {"hook_event_name": "SubagentStart", "session_id": "s", "agent_id": "worker"},
    )
    packet = json.loads(
        result["hookSpecificOutput"]["additionalContext"].split("\n", 1)[1]
    )
    assert packet["task"] == "cancel"
    # The outcome defaulted to the description, so the packet carries that text once.
    assert packet["description"] == "Implement cancellation and release."
    assert "outcome" not in packet
    guidance = (
        Path(__file__).resolve().parents[2]
        / "fbk-docs/workflow/repository-grounding.md"
    ).read_text(encoding="utf-8")
    assert packet["authoring_guidance"] == guidance
    assert len(json.dumps(packet, ensure_ascii=False)) <= 16000
    assert store.load(project, "feature")["workers"]["worker"]


@pytest.mark.parametrize("contents", [None, "   ", "Inspect the installed project convention."])
def test_worker_guidance_uses_runtime_installation_and_reports_broken_assets(
    project, tmp_path, monkeypatch, contents
):
    prepare_implementation(project)
    launch(project)
    installation = tmp_path / "installation"
    guidance = installation / "fbk-docs/workflow/repository-grounding.md"
    if contents is not None:
        guidance.parent.mkdir(parents=True)
        guidance.write_text(contents, encoding="utf-8")
    monkeypatch.setattr(
        handoff, "__file__", str(installation / "fbk-scripts/fbk/workflow/handoff.py")
    )
    result = hooks.handle(
        project,
        {"hook_event_name": "SubagentStart", "session_id": "s", "agent_id": "worker"},
    )
    context = result["hookSpecificOutput"]["additionalContext"]
    if contents and contents.strip():
        assert json.loads(context.split("\n", 1)[1])["authoring_guidance"] == contents
    else:
        assert str(guidance) in context
        assert "restore the installed file and retry" in context


def test_return_accepts_own_changes_but_rejects_incomplete_change_accounting(project):
    prepare_implementation(project)
    launch(project)
    (project / "src/app.py").write_text("release()")
    with pytest.raises(store.WorkflowError, match="actual owned-file changes"):
        finish(project, changed_files=[])
    result = finish(project)
    assert result["status"] == "completed"
    assert (
        result["files"]["src/app.py"]
        == evidence.file_hashes(project, ["src/app.py"])["src/app.py"]
    )
    complete_refactor_tasks(project)
    handoff.verify_task_runs(project, store.load(project, "feature"))


def test_return_rejects_late_contract_or_supporting_input_changes(project):
    prepare_implementation(project)
    (project / "conventions.md").write_text("Preserve retry behavior.")
    launch(project, input_refs=["conventions.md"])
    (project / "conventions.md").write_text("Change retry behavior.")
    with pytest.raises(store.WorkflowError, match="supporting inputs changed"):
        finish(project, changed_files=[])
    (project / "spec.md").write_text("unrelated")
    (project / ".fbk/feature/spec.md").write_text("Cancel has different behavior.")
    with pytest.raises(store.WorkflowError, match="Task inputs changed"):
        finish(project, changed_files=[])


def test_unresolved_return_blocks_completion_and_is_visible_after_clear(project):
    prepare_implementation(project)
    launch(project)
    result = finish(
        project,
        changed_files=[],
        unresolved=["Retry behavior contradicts the accepted example."],
    )
    assert result["status"] == "needs-attention"
    with pytest.raises(store.WorkflowError, match="resolve their handoffs"):
        handoff.verify_task_runs(project, store.load(project, "feature"))
    packet = handoff.continuation(project, store.load(project, "feature"))
    assert packet["tasks"][0]["unresolved"] == [
        "Retry behavior contradicts the accepted example."
    ]


def test_pending_repair_blocks_task_handoff_and_routes_recovery(project):
    prepare_implementation(project)
    record = store.load(project, "feature")
    record["pending_repair"] = {"operation": "repair"}
    with pytest.raises(store.WorkflowError, match="recover-repair"):
        handoff.start_task(
            project,
            record,
            "s",
            "cancel",
            "worker",
            acceptance_refs=[".fbk/feature/spec.md"],
        )
    assert "recover-repair" in handoff.continuation(project, record)["next"]


def test_stale_task_can_be_canceled_and_relaunched_with_refreshed_input(project):
    prepare_implementation(project)
    (project / "conventions.md").write_text("Preserve retry behavior.")
    launch(project, input_refs=["conventions.md"])
    (project / "conventions.md").write_text("Preserve retry behavior and document it.")
    mutate(
        project,
        handoff.cancel_task,
        "s",
        "cancel",
        "worker stopped; refresh changed conventions",
    )
    packet = launch(project, input_refs=["conventions.md"])
    assert packet["status"] == "running"
    finish(project, changed_files=[])


def test_continuation_shows_only_sourced_current_decision_after_late_correction(
    project,
):
    record = store.load(project, "feature")
    (project / "answers.md").write_text(
        "Use five retries.\nCorrection: use three retries."
    )
    decisions.record(
        project,
        record,
        "s",
        {
            "id": "initial",
            "text": "Use five retries.",
            "phase": "intent", "kind": "governs",
            "source": {"path": "answers.md", "quote": "Use five retries."},
        },
    )
    decisions.record(
        project,
        record,
        "s",
        {
            "id": "corrected",
            "text": "Use three retries.",
            "phase": "intent", "kind": "governs",
            "source": {"path": "answers.md", "quote": "Correction: use three retries."},
            "supersedes": "initial",
        },
    )
    packet = handoff.continuation(project, record)
    assert [row["text"] for row in packet["decisions"]] == ["Use three retries."]
    (project / "answers.md").write_text("Use something else.")
    degraded = handoff.continuation(project, record)
    assert degraded["decisions"] == []
    assert degraded["authority_problem"]
    assert "answers.md" in degraded["sources"]


def test_sequential_task_can_supersede_owned_output_but_unattributed_edit_is_rejected(
    project,
):
    # Comments do not alter the accepted single release call.
    (project / "tests/check.py").write_text(
        "import ast\nfrom pathlib import Path\n"
        "actual = ast.parse(Path('src/app.py').read_text())\n"
        "expected = ast.parse('release()')\n"
        "assert ast.dump(actual) == ast.dump(expected)\n"
    )
    tasks_path = project / ".fbk/feature/tasks.json"
    tasks = [task for task in json.loads(tasks_path.read_text()) if not task.get("refactor")]
    tasks.append(
        {
            "id": "document", "stage": "implementation",
            "acceptance_refs": [".fbk/feature/prd.md", ".fbk/feature/spec.md", ".fbk/feature/spec.md#cancel-once"],
            "verification": "Cancellation behavior remains unchanged.",
            "check_expectations": [{"argv": [sys.executable, "tests/check.py"], "exit_code": 0}],
            "description": "Clarify release behavior in source.",
            "files": ["src/app.py"],
            "depends_on": ["cancel"],
        }
    )
    tasks_path.write_text(json.dumps(with_refactor(tasks)))
    prepare_implementation(project)
    launch(project)
    (project / "src/app.py").write_text("release()")
    finish(project)
    mutate(
        project,
        handoff.start_task,
        "s",
        "document",
        "second",
        acceptance_refs=[".fbk/feature/spec.md"],
    )
    (project / "src/app.py").write_text("release()  # exactly once")
    mutate(
        project,
        handoff.finish_task,
        "s",
        "document",
        changed_files=["src/app.py"],
        checks=[
            {
                "argv": [sys.executable, "tests/check.py"],
                "exit_code": 0,
                "evidence": "Preserved release behavior.",
            }
        ],
        unresolved=[],
        outcome="Documented release behavior.",
    )
    complete_refactor_tasks(project)
    handoff.verify_task_runs(project, store.load(project, "feature"))
    (project / "src/app.py").write_text("release_twice()")
    with pytest.raises(store.WorkflowError, match="without a completed dependent task"):
        handoff.verify_task_runs(project, store.load(project, "feature"))


def test_a_distinct_launch_outcome_stays_in_the_packet(project):
    prepare_implementation(project)
    launch(project, outcome="Cancel twice and see one release.")
    packet = handoff.task_packet(project, store.load(project, "feature"), "cancel")
    assert packet["outcome"] == "Cancel twice and see one release."
    assert packet["description"] == "Implement cancellation and release."
