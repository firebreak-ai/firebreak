"""Public handoff commands and acceptance checks across the new subsystem boundaries."""

import json
import sys
from pathlib import Path

import pytest

from fbk.workflow import cli, close, engine, evidence, review, review_context, store
from tests.test_workflow_commands import call
from tests.test_workflow_lifecycle import (
    accept,
    clean_review,
    enter,
    enter_implementation,
    mutate,
    prepare_implementation,
    project as workflow_project,
    run_test_tasks,
)
from tests.refactor_plan import complete_refactor_tasks, with_refactor

project = workflow_project


def snapshot_review(root, unit, phase, files, checks):
    result = clean_review()
    with review_context.snapshot(root, files) as (_, manifest):
        result.update(
            source_policy="original-snapshot-v1",
            snapshot_files=manifest,
            supporting_files={
                p: manifest[p] for p in review_context.convention_paths(manifest)
            },
            required_files=sorted(files),
        )
    return result


def test_public_report_distills_current_work_and_expands_history_explicitly(project):
    enter(project, "intent")
    mutate(
        project, engine.suspend, "s", "Await the already recorded retention correction."
    )
    report = call(project, "workflow-report", "feature")[0]
    assert "events" not in report and "review_rounds" not in report
    assert (
        report["continuation"]["pending"]
        == "Await the already recorded retention correction."
    )
    history = call(project, "workflow-report", "feature", "--history")[0]
    assert history["events"][-1]["event"] == "suspended"
    assert (
        call(project, "continuation", "feature")["pending"]
        == report["continuation"]["pending"]
    )


def test_public_decision_correction_invalidates_prior_acceptance(project):
    accept(project, "intent")
    (project / "human.txt").write_text(
        "Correction: cancellation must never retry release."
    )
    store.atomic_json(
        project / "decision.json",
        {
            "id": "never-retry",
            "text": "Cancellation never retries release.",
            "phase": "intent", "kind": "governs",
            "source": {
                "path": "human.txt",
                "quote": "Correction: cancellation must never retry release.",
            },
        },
    )
    result = call(project, "decision-record", "feature", "--request", "decision.json")
    assert result["text"] == "Cancellation never retries release."
    packet = call(project, "continuation", "feature")
    assert packet["status"] == "stale"
    assert packet["decisions"][0]["quote"] == result["source"]["quote"]
    assert "hash" not in json.dumps(packet["decisions"]) and "supersedes" not in packet["decisions"][0]
    with pytest.raises(store.WorkflowError, match="cannot start"):
        call(project, "phase-enter", "spec", "feature")


def test_context_contract_change_invalidates_spec_but_not_intent(project):
    (project / "conventions.md").write_text("Release must be called once.")
    path = project / ".fbk/feature/scope.json"
    scope = json.loads(path.read_text())
    scope["context"] = ["conventions.md"]
    store.atomic_json(path, scope)
    accept(project, "intent")
    accept(project, "spec")
    (project / "conventions.md").write_text("Release must be idempotent.")
    status = call(project, "status", "feature")[0]
    assert (status["phase"], status["status"]) == ("spec", "stale")


def test_convention_freshness_preserves_expected_source_edits(project):
    (project / "CLAUDE.md").write_text("Use observable behavior tests.")
    enter(project, "intent")
    close.close_phase(project, "feature", "intent", "s", reviewer=snapshot_review)
    (project / "src/app.py").write_text("release()")
    assert call(project, "status", "feature")[0]["phase"] == "spec"
    (project / "CLAUDE.md").write_text("Use integration behavior tests.")
    assert call(project, "status", "feature")[0]["status"] == "stale"


def test_changed_supporting_source_during_review_cannot_accept(project):
    enter(project, "intent")

    def changed(root, *args):
        result = snapshot_review(root, *args)
        (root / "external-contract.md").write_text("A newly relevant shared contract.")
        return result

    with pytest.raises(store.WorkflowError, match="Review sources changed"):
        close.close_phase(project, "feature", "intent", "s", reviewer=changed)
    assert store.load(project, "feature")["phases"]["intent"]["evidence"] is None


def test_public_worker_result_blocks_close_until_handoff_matches_files(project):
    prepare_implementation(project)
    packet = call(
        project,
        "task-start",
        "feature",
        "cancel",
        "--worker",
        "worker",
        "--acceptance-refs",
        ".fbk/feature/spec.md",
    )
    context = call(project, "task-context", "feature", "cancel")
    assert context["revision"] == packet["revision"]
    guidance = (
        Path(__file__).resolve().parents[2]
        / "fbk-docs/workflow/repository-grounding.md"
    ).read_text(encoding="utf-8")
    assert context["authoring_guidance"] == packet["authoring_guidance"] == guidance
    with pytest.raises(store.WorkflowError, match="Finish assigned tasks"):
        close.close_phase(project, "feature", "implement", "s", reviewer=clean_review)
    (project / "src/app.py").write_text("release()")
    result = {
        "changed_files": [],
        "outcome": "Release once.",
        "checks": [
            {"argv": [sys.executable, "tests/check.py"], "exit_code": 0, "evidence": "Release observed."}
        ],
        "unresolved": [],
    }
    store.atomic_json(project / ".fbk/runtime/worker-result.json", result)
    with pytest.raises(store.WorkflowError, match="actual owned-file changes"):
        call(
            project,
            "task-finish",
            "feature",
            "cancel",
            "--result",
            ".fbk/runtime/worker-result.json",
        )
    result["changed_files"] = ["src/app.py"]
    store.atomic_json(project / ".fbk/runtime/worker-result.json", result)
    assert (
        call(
            project,
            "task-finish",
            "feature",
            "cancel",
            "--result",
            ".fbk/runtime/worker-result.json",
        )["status"]
        == "completed"
    )
    complete_refactor_tasks(project)
    assert (
        close.close_phase(project, "feature", "implement", "s", reviewer=clean_review)[
            "status"
        ]
        == "retrospective-required"
    )


def test_pending_repair_prevents_checkpoint_execution_before_cli_mutation_guard(
    project, monkeypatch
):
    # The checkpoint replaced lock-tests as the command that runs checks before it locks.
    enter_implementation(project)
    run_test_tasks(project)
    record = store.load(project, "feature")
    record["pending_repair"] = {"path": ".fbk/feature/spec.md"}
    store.save(project, record)
    calls = []
    monkeypatch.setattr(review, "run_command", lambda *a, **k: calls.append(a))
    with pytest.raises(store.WorkflowError, match="repair is pending|recover-repair"):
        call(project, "test-checkpoint", "feature")
    assert calls == []
    assert not store.load(project, "feature")["locks"]


def test_blocker_handoff_contains_evidence_and_not_just_remedy(project):
    from tests.test_workflow_lifecycle import blocking_review

    enter(project, "intent")
    with pytest.raises(store.WorkflowError) as error:
        close.close_phase(project, "feature", "intent", "s", reviewer=blocking_review)
    assert "A canceled task leaves its resource allocated." in str(error.value)
    current = call(project, "current-findings", "feature", "--index", "1")
    assert current["current"] and current["findings"][0]["severity"] == "blocker"
    (project / ".fbk/feature/prd.md").write_text("Changed requirement.")
    assert call(project, "current-findings", "feature")["current"] is False


def test_worker_cannot_launch_with_nonexistent_acceptance_line(project):
    prepare_implementation(project)
    with pytest.raises(store.WorkflowError, match="line does not exist"):
        call(
            project,
            "task-start",
            "feature",
            "cancel",
            "--worker",
            "worker",
            "--acceptance-refs",
            ".fbk/feature/spec.md:999",
        )
    assert "cancel" not in store.load(project, "feature").get("task_runs", {})


def test_new_owned_file_after_worker_return_is_not_accepted_as_reviewed(project):
    from fbk.workflow import handoff

    tasks = project / ".fbk/feature/tasks.json"
    rows = [row for row in json.loads(tasks.read_text()) if not row.get("refactor")]
    next(row for row in rows if row["id"] == "cancel")["files"] = ["src"]
    store.atomic_json(tasks, with_refactor(rows))
    prepare_implementation(project)
    call(
        project,
        "task-start",
        "feature",
        "cancel",
        "--worker",
        "worker",
        "--acceptance-refs",
        ".fbk/feature/spec.md",
    )
    (project / "src/app.py").write_text("release()")
    mutate(
        project,
        handoff.finish_task,
        "s",
        "cancel",
        changed_files=["src/app.py"],
        checks=[
            {"argv": [sys.executable, "tests/check.py"], "exit_code": 0, "evidence": "Release observed."}
        ],
        unresolved=[],
        outcome="Release once.",
    )
    complete_refactor_tasks(project)
    handoff.verify_task_runs(project, store.load(project, "feature"))
    (project / "src/unreviewed.py").write_text("unexpected = True")
    with pytest.raises(store.WorkflowError, match="changed after completion"):
        close.close_phase(project, "feature", "implement", "s", reviewer=clean_review)


def test_resume_prioritizes_earliest_stale_authority_over_open_implementation(project):
    prepare_implementation(project)
    (project / ".fbk/feature/prd.md").write_text("Changed cancellation intent.")
    packet = call(project, "continuation", "feature")
    assert packet["phase"] == "intent" and packet["status"] == "stale"
    assert packet["tasks"] == []
    assert packet["sources"] == [".fbk/feature/prd.md"]


def test_omitted_decisions_have_a_complete_targeted_retrieval_path(project):
    enter(project, "intent")
    for i in range(6):
        statement = f"Constraint {i}: " + "Preserve the observed behavior. " * 90
        (project / f"decision-source-{i}.md").write_text(statement)
        store.atomic_json(
            project / "decision.json",
            {
                "id": str(i),
                "text": statement,
                "phase": "intent", "kind": "governs",
                "source": {"path": f"decision-source-{i}.md", "quote": statement},
            },
        )
        call(project, "decision-record", "feature", "--request", "decision.json")
    compact = call(project, "continuation", "feature")
    assert compact["omitted"]["decisions"] > 0
    assert len(json.dumps(compact, ensure_ascii=False)) <= 10000
    detailed = call(project, "continuation", "feature", "--section", "decisions")
    assert len(detailed["decisions"]) == 6
    assert {d["id"] for d in detailed["decisions"]} == {str(i) for i in range(6)}


def test_nested_unit_sources_are_available_without_parent_review_history(project):
    with store.transaction(project):
        record = engine.initialize(project, "parent/child", design=False)
    path = project / ".fbk/parent/child/prd.md"
    path.write_text("Nested feature intent.")
    paths = [".fbk/parent/child/prd.md"]
    with review_context.snapshot(project, paths) as (sources, manifest):
        assert (sources / paths[0]).read_text() == "Nested feature intent."
        assert ".fbk/parent/child/state.json" not in manifest
    with pytest.raises(store.WorkflowError, match="history"):
        with review_context.snapshot(project, [".fbk/parent/child/state.json"]):
            pass
    assert record["unit"] == "parent/child"


def test_oversized_worker_return_cannot_pollute_durable_handoff(project):
    from fbk.workflow import handoff

    prepare_implementation(project)
    call(
        project,
        "task-start",
        "feature",
        "cancel",
        "--worker",
        "worker",
        "--acceptance-refs",
        ".fbk/feature/spec.md",
    )
    with pytest.raises(store.WorkflowError, match="16,000"):
        mutate(
            project,
            handoff.finish_task,
            "s",
            "cancel",
            changed_files=[],
            checks=[
                {
                    "argv": ["check"],
                    "exit_code": 0,
                    "evidence": "Repeated diagnostic. " * 2000,
                }
            ],
            unresolved=[],
            outcome="Unchanged behavior.",
        )
    run = store.load(project, "feature")["task_runs"]["cancel"]
    assert run["status"] == "running" and "return" not in run


def test_implementation_reading_priority_keeps_governing_sources_out_of_edit_targets():
    from fbk.workflow import review

    packet = review.focus_brief("feature", "implement", ["src/app.py", "human-decision.md", "shared-contract.md", ".fbk/feature/spec.md"], target_files=["src/app.py"])
    assert packet["phase_targets"] == ["src/app.py"]
    # Every required path outside the targets is authority; the brief does not list them twice.
    assert "authoritative_context" not in packet


@pytest.mark.parametrize("shared_file_exists", [False, True])
def test_parallel_task_launch_rejects_intersecting_globs_before_writes(
    project, shared_file_exists
):
    from fbk.workflow import handoff

    first, second = ["src/*/foo.py"], ["src/bar/*.py"]
    assert handoff.ownership_overlaps(first, second)
    assert not handoff.ownership_overlaps(first, ["tests/*.py"])
    store.atomic_json(
        project / ".fbk/feature/tasks.json",
        with_refactor([
            {
                "id": task, "stage": "implementation",
                "acceptance_refs": [".fbk/feature/prd.md", ".fbk/feature/spec.md", ".fbk/feature/spec.md#cancel-once"],
                "verification": "Cancellation behavior satisfies the reviewed tests.",
                "check_expectations": [{"argv": [sys.executable, "tests/check.py"], "exit_code": 0}],
                "description": "Implement assigned cancellation behavior.",
                "files": files,
                "depends_on": ["first"] if task == "second" else [],
            }
            for task, files in [("first", first), ("second", second)]
        ] + [json.loads((project / ".fbk/feature/tasks.json").read_text())[0]]),
    )
    if shared_file_exists:
        (project / "src/bar").mkdir()
        (project / "src/bar/foo.py").write_text("pass")
    prepare_implementation(project)
    call(
        project, "task-start", "feature", "first", "--worker", "worker-one",
        "--acceptance-refs", ".fbk/feature/spec.md",
    )
    with pytest.raises(store.WorkflowError, match="nonoverlapping"):
        call(
            project, "task-start", "feature", "second", "--worker", "worker-two",
            "--acceptance-refs", ".fbk/feature/spec.md",
        )
    runs = store.load(project, "feature")["task_runs"]
    # The test task ran before the checkpoint; of the implementation tasks only first runs.
    assert {task for task, run in runs.items() if run["stage"] == "implementation"} == {"first"}
    assert runs["first"]["status"] == "running"


@pytest.mark.parametrize(
    "protected",
    [
        ".claude/projects/prior.jsonl",
        ".claude/sessions/prior.jsonl",
        ".claude/memory/prior.md",
        ".claude/settings.json",
        ".claude/settings.local.json",
        ".claude/.credentials.json",
    ],
)
def test_explicit_and_glob_context_cannot_reintroduce_host_history(project, protected):
    path = project / protected
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("Host-only historical material.")
    convention = project / ".claude/rules/testing.md"
    convention.parent.mkdir(parents=True, exist_ok=True)
    convention.write_text("Verify observable behavior.")
    scope_path = project / ".fbk/feature/scope.json"
    declared = json.loads(scope_path.read_text())
    for context in [[protected], [".claude/**"]]:
        store.atomic_json(scope_path, {**declared, "context": context})
        with pytest.raises(store.WorkflowError, match="host history"):
            evidence.scope(project, "feature")
    with pytest.raises(store.WorkflowError, match="Invalid required review source"):
        with review_context.snapshot(project, [protected]):
            pytest.fail("Explicit source restored excluded host material")
    store.atomic_json(scope_path, {**declared, "context": [".claude/rules/*.md"]})
    assert evidence.scope(project, "feature")["context"] == [".claude/rules/*.md"]
    with review_context.snapshot(project, [".claude/rules/testing.md"]) as (root, manifest):
        assert protected not in manifest
        assert (root / ".claude/rules/testing.md").read_text() == "Verify observable behavior."


@pytest.mark.parametrize("change", ["convention", "implementation", "new-source"])
def test_source_snapshot_changes_remove_findings_from_active_continuation(project, change):
    from tests.test_workflow_lifecycle import blocking_review

    (project / "CLAUDE.md").write_text("Use observable behavior tests.")
    enter(project, "intent")

    def blocker(root, *args):
        result = snapshot_review(root, *args)
        result["review"] = blocking_review()["review"]
        return result

    with pytest.raises(store.WorkflowError, match="blocking defects"):
        close.close_phase(project, "feature", "intent", "s", reviewer=blocker)
    before = call(project, "continuation", "feature")
    assert before["findings_current"] and before["findings"]
    assert call(project, "current-findings", "feature")["current"]
    path = {
        "convention": "CLAUDE.md",
        "implementation": "src/app.py",
        "new-source": "new-contract.md",
    }[change]
    (project / path).write_text("Changed source evidence.")
    after = call(project, "continuation", "feature")
    assert after["revision"] == before["revision"]
    assert not after["findings_current"] and after["findings"] == []
    current = call(project, "current-findings", "feature")
    assert not current["current"]
    assert current["findings"] == before["findings"]  # Still retrievable as stale evidence.
