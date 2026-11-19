"""Behavioral workflow tests: real files/processes, controlled semantic reviewer.

The fake reviewer isolates workflow policy, not model quality. A separate live
Claude experiment validates the host adapter and structured reviewer protocol.
"""

import json
import multiprocessing
import subprocess
import sys
from pathlib import Path

import pytest
from fbk.workflow import close, decisions, engine, evidence, hooks, store

from .refactor_plan import complete_refactor_tasks, with_refactor


def clean_review(*args):
    return {
        "shape": "single",
        "readers": [],
        "review": {
            "summary": "Behavior and declared contracts inspected.",
            "findings": [],
        },
    }


def blocking_review(*args):
    return {
        "shape": "single",
        "readers": [],
        "review": {
            "summary": "A behavior is missing.",
            "findings": [
                {
                    "title": "Cancellation does not release the resource",
                    "severity": "blocker",
                    "location": "src/app.py:1",
                    "evidence": "A canceled task leaves its resource allocated.",
                    "remedy": "Release it on cancellation.",
                }
            ],
        },
    }


@pytest.fixture
def project(tmp_path):
    store.atomic_json(
        tmp_path / ".fbk/config.json",
        {
            "schema_version": 1,
            "review_defaults": {
                p: {
                    "mode": "single",
                    "members": [],
                    "reason": "Fixture operator chooses single review.",
                }
                for p in ("design", "spec")
            },
        },
    )
    with store.transaction(tmp_path):
        engine.initialize(tmp_path, "feature", design=False)
    unit = tmp_path / ".fbk/feature"
    # Each document carries its traceability section: one commitment, and one requirement
    # linking it (the unit skips design).
    (unit / "prd.md").write_text(
        "# Cancellation\n\n## Commitments\n\n### Release on cancel\n\n"
        "A canceled task releases its resource. Existing tasks continue normally.\n"
    )
    (unit / "spec.md").write_text(
        "# Cancellation contract\n\n## Requirements\n\n### Cancel once\n\n"
        "Cancel returns true once, false when already canceled. Release exactly once. "
        "Serves [Release on cancel](prd.md#release-on-cancel).\n"
    )
    store.atomic_json(
        unit / "scope.json",
        {
            "sources": ["src"],
            "tests": ["tests"],
            "docs": [],
            "checks": [[sys.executable, "tests/check.py"]],
        },
    )
    store.atomic_json(
        unit / "tasks.json",
        with_refactor([
            {
                "id": "prepare-tests", "stage": "tests",
                "description": "Check cancellation regression behavior.",
                "files": ["tests/check.py"], "depends_on": [],
                "acceptance_refs": [".fbk/feature/prd.md", ".fbk/feature/spec.md", ".fbk/feature/spec.md#cancel-once"],
                "verification": "The cancellation check fails until release is implemented.",
                "check_expectations": [{"argv": [sys.executable, "tests/check.py"], "exit_code": 1}],
            },
            {
                "id": "cancel",
                "stage": "implementation",
                "description": "Implement cancellation and release.",
                "files": ["src/app.py"],
                "depends_on": [],
                "acceptance_refs": [".fbk/feature/prd.md", ".fbk/feature/spec.md", ".fbk/feature/spec.md#cancel-once"],
                "verification": "The reviewed cancellation test passes unchanged.",
                "check_expectations": [{"argv": [sys.executable, "tests/check.py"], "exit_code": 0}],
            }
        ]),
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "tests/check.py").write_text(
        "from pathlib import Path\nassert Path('src/app.py').read_text() == 'release()'\n"
    )
    (tmp_path / "src/app.py").write_text("pass")
    return tmp_path


def mutate(root, fn, *args, unit="feature", **kwargs):
    with store.transaction(root):
        return fn(root, store.load(root, unit), *args, **kwargs)


def enter(root, phase, session="s"):
    return mutate(root, engine.enter, phase, session)


def observe_phase(root, phase, unit="feature", session="s"):
    """Complete the author's phase account when setting up later-phase tests."""
    from fbk.workflow import retrospective

    with store.transaction(root):
        record = store.load(root, unit)
        pending = next(p for p in retrospective.pending_phases(record) if p["phase"] == phase)
        retrospective.record_observation(root, record, session, {
            "id": f"{phase}-{len(record.get('observations', []))}",
            "detection_phase": phase,
            "observation": "The phase established the cancellation contract; its review accepted the declared behavior.",
            "evidence": [{"event_id": pending["event_id"]}],
        })
        store.save(root, record)


def accept(root, phase):
    """Enter and close a phase with a clean review. Breakdown writes tasks only, so its
    close runs no test task, red check, or lock."""
    enter(root, phase)
    result = close.close_phase(root, "feature", phase, "s", reviewer=clean_review)
    observe_phase(root, phase)
    return {**result, **engine.status_report(root, store.load(root, "feature"))}


def enter_implementation(root):
    """Accept intent, spec, and a plan-only breakdown, then enter implement: the unit is
    writing tests, with no locks."""
    for phase in ("intent", "spec", "breakdown"):
        accept(root, phase)
    mutate(
        root,
        engine.approve,
        "s",
        "start-implementation",
        "implement",
        "Implement the agreed spec.",
    )
    enter(root, "implement")


def ordered_test_tasks(root):
    """Every declared test task, each after the test tasks it depends on."""
    tasks = [t for t in store.read_json(root / ".fbk/feature/tasks.json") if t.get("stage") == "tests"]
    ordered, done = [], set()
    while len(ordered) < len(tasks):
        ready = [t for t in tasks if t["id"] not in done and set(t.get("depends_on", [])) <= done]
        assert ready, "The fixture's test tasks cannot be ordered."
        for task in ready:
            ordered.append(task)
            done.add(task["id"])
    return ordered


def run_test_tasks(root, work=None, session="s"):
    """Run every declared test task through the real handoff: start it for its own
    worker, let ``work[task_id]`` (a function of root returning the changed files) write
    its tests, then finish it with its declared checks executed for real."""
    from fbk.workflow import handoff, review

    work = work or {}
    for task in ordered_test_tasks(root):
        mutate(root, handoff.start_task, session, task["id"], f"{task['id']}-author")
        changed = work[task["id"]](root) if task["id"] in work else []
        checks = [review.run_command(item["argv"], root, 10) for item in task["check_expectations"]]
        returned = handoff.complete_task(
            root, "feature", session, task["id"], changed_files=list(changed),
            checks=[{"argv": item["argv"], "exit_code": c["exit_code"],
                     "evidence": (c["stderr"] or c["stdout"] or "The declared check ran.")[-500:]}
                    for item, c in zip(task["check_expectations"], checks)],
            unresolved=[], outcome="The tests are written and fail on the missing behavior.")
        assert returned["status"] == "completed", returned


def approve_unlock(root, expected, commands, tests=None, reason="The operator found the named tests wrong."):
    """Approve an unlock with the rework the operator approved: per named test, whether its
    corrected form is expected to "fail" (behavior not yet built) or "pass" (preservation),
    and the rework commands, each an argv with the named tests it covers. A command's
    expected exit is derived from its tests, never stated."""
    import inspect

    assert "rework" in inspect.signature(engine.approve).parameters, (
        "An unlock approval cannot carry per-test expectations and rework commands yet "
        "(engine.approve takes no rework).")
    tests = sorted(expected) if tests is None else list(tests)
    return mutate(root, engine.approve, "s", "unlock-test", "implement", reason, tests=tests,
                  rework={"expected": dict(expected), "commands": [dict(c) for c in commands]})


def pass_checkpoint(root, reviewer=clean_review, session="s"):
    """Run the test checkpoint; on pass it reviews and locks the tests."""
    return close.close_checkpoint(root, "feature", session, reviewer=reviewer)


def prepare_implementation(root, work=None):
    """The route to writing code: a plan-only breakdown, then in implement every test
    task runs through the real handoff, and the test checkpoint passes and locks."""
    enter_implementation(root)
    run_test_tasks(root, work)
    pass_checkpoint(root)
    assert engine.implement_stage(root, store.load(root, "feature")) == "writing-code"



def declare_module_preparation_task(root):
    """Give the closure fixture a real focused prerequisite, separate from release integration."""
    path = root / ".fbk/feature/tasks.json"
    tasks = store.read_json(path)
    task = next(task for task in tasks if task["id"] == "cancel")
    task["description"] = "Prepare a syntactically valid cancellation module for release integration."
    task["verification"] = "The production module parses as Python; the independent unit check still verifies release behavior."
    task["check_expectations"] = [{"argv": [sys.executable, "-c",
        "import ast; from pathlib import Path; ast.parse(Path('src/app.py').read_text())"], "exit_code": 0}]
    store.atomic_json(path, tasks)


def complete_declared_implementation_task(root):
    """Exercise real start/finish and runtime checks, without fabricated task state."""
    from fbk.workflow import handoff, review
    task = next(task for task in store.read_json(root / ".fbk/feature/tasks.json") if task["id"] == "cancel")
    mutate(root, handoff.start_task, "s", "cancel", "implementation-worker")
    checks = [review.run_command(item["argv"], root, 10) for item in task["check_expectations"]]
    result = handoff.complete_task(root, "feature", "s", "cancel", changed_files=[],
        checks=[{**check, "evidence": "The reviewed task command executed successfully."} for check in checks],
        unresolved=[], outcome="The reviewed task definition of done is satisfied.")
    assert result["status"] == "completed"
    complete_refactor_tasks(root)


def test_prerequisite_cannot_be_skipped_by_cli_or_either_hook_entry(project):
    with pytest.raises(store.WorkflowError, match="intent"):
        enter(project, "spec")
    common = {"session_id": "s", "cwd": str(project)}
    for payload in [
        dict(
            common,
            hook_event_name="PreToolUse",
            tool_name="Skill",
            tool_input={"skill": "fbk-spec", "args": "feature"},
        ),
        dict(
            common,
            hook_event_name="UserPromptExpansion",
            command_name="fbk-spec",
            command_args="feature",
        ),
    ]:
        result = hooks.handle(project, payload)
        if payload["hook_event_name"] == "UserPromptExpansion":
            assert "decision" not in result
            context = result["hookSpecificOutput"]["additionalContext"]
            assert "could not open spec" in context
            assert "continuation feature" in context
        else:
            assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
            assert result["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
            assert "decision" not in result
    assert store.load(project, "feature")["open_phase"] is None


def test_direct_entry_and_explicit_fallback_are_idempotent(project):
    result = hooks.handle(
        project,
        {
            "hook_event_name": "UserPromptExpansion",
            "session_id": "s",
            "command_name": "fbk-intent",
            "command_args": "feature",
        },
    )
    assert "open" in result["hookSpecificOutput"]["additionalContext"]
    enter(project, "intent")
    assert store.load(project, "feature")["open_phase"] == "intent"


def test_accepted_artifact_edit_invalidates_readiness_after_reload(project):
    accept(project, "intent")
    accept(project, "spec")
    (project / ".fbk/feature/spec.md").write_text(
        "Cancellation now waits for pending I/O."
    )
    status = engine.status_report(project, store.load(project, "feature"))
    assert (status["phase"], status["status"]) == ("spec", "stale")
    with pytest.raises(store.WorkflowError, match="stale"):
        enter(project, "breakdown")


def test_implementation_requires_real_passing_check_and_unchanged_tests(project):
    declare_module_preparation_task(project)
    prepare_implementation(project)
    complete_declared_implementation_task(project)
    # The checkpoint locked the tests; the whole-unit check still fails at close.
    with pytest.raises(store.WorkflowError, match="Verification failed"):
        close.close_phase(project, "feature", "implement", "s", reviewer=clean_review)
    assert not store.load(project, "feature")["phases"]["implement"]["evidence"]
    (project / "src/app.py").write_text("release()")
    complete_declared_implementation_task(project)
    assert (
        close.close_phase(project, "feature", "implement", "s", reviewer=clean_review)[
            "status"
        ]
        == "retrospective-required"
    )
    observe_phase(project, "implement")
    assert engine.status_report(project, store.load(project, "feature"))["status"] == "closed"


def test_lock_requires_red_evidence_or_preservation_reason(project):
    # The lock the checkpoint applies keeps refusing a lock without red or a reason.
    enter_implementation(project)
    with pytest.raises(store.WorkflowError, match="failing"):
        mutate(project, engine.lock_tests, "s", {"exit_code": 0})
    with pytest.raises(store.WorkflowError, match="failing"):
        mutate(project, engine.lock_tests, "s", {"exit_code": None})
    with pytest.raises(store.WorkflowError, match="failing"):
        mutate(project, engine.lock_tests, "s", {})


def test_unlock_cannot_cover_another_test_and_relock_is_required(project):
    (project / "tests/other.py").write_text("assert 1 == 1")
    prepare_implementation(project)
    assert "tests/other.py" in store.load(project, "feature")["locks"]
    approve_unlock(project, {"tests/check.py": "fail"},
                   [{"argv": [sys.executable, "tests/check.py"], "tests": ["tests/check.py"]}],
                   reason="Update cancellation test.")
    (project / "tests/other.py").write_text("assert True")
    # The unlocked test is reworked through its test task, but the locked test the unlock
    # does not cover changed through the shell, so the rework task's start is refused.
    with pytest.raises(store.WorkflowError, match="tests/other.py"):
        run_test_tasks(project)
    assert store.load(project, "feature")["unlocks"] == ["tests/check.py"]
    with pytest.raises(store.WorkflowError, match="re-locked"):
        engine.verify_locks(project, store.load(project, "feature"))


def test_approval_cannot_authorize_a_changed_revision(project):
    accept(project, "intent")
    mutate(
        project,
        engine.approve,
        "s",
        "reopen",
        "intent",
        "Change cancellation semantics.",
    )
    (project / ".fbk/feature/prd.md").write_text(
        "A different requirement than the approved change."
    )
    with pytest.raises(store.WorkflowError, match="approval required"):
        mutate(project, engine.reopen, "intent", "s", "New requirements.")


def test_reopen_supersedes_later_open_phase_and_clears_locks(project):
    prepare_implementation(project)
    assert store.load(project, "feature")["locks"]
    mutate(
        project, engine.approve, "s", "reopen", "spec", "Clarify cancellation boundary."
    )
    mutate(project, engine.reopen, "spec", "s", "Clarify cancellation boundary.")
    record = store.load(project, "feature")
    assert engine.phase_state(project, record)[:2] == ("spec", "ready")
    # Reopening spec (breakdown or earlier) clears the locks; the checkpoint locks again.
    assert record["locks"] == {} and not record.get("lock_origin")
    enter(project, "spec")


def test_review_budget_survives_fixes_and_restart(project):
    enter(project, "intent")
    for i in range(3):
        (project / ".fbk/feature/prd.md").write_text(
            f"Cancel task and release resources. Revision {i}."
        )
        with pytest.raises(store.WorkflowError, match="approval required"):
            close.close_phase(
                project, "feature", "intent", "s", reviewer=blocking_review
            )
    (project / ".fbk/feature/prd.md").write_text("Fourth attempted revision.")
    with pytest.raises(store.WorkflowError, match="budget exhausted"):
        close.close_phase(project, "feature", "intent", "s", reviewer=clean_review)
    assert len(store.load(project, "feature")["phases"]["intent"]["rounds"]) == 3


def test_close_over_findings_reuses_review_and_consumes_scoped_grant(project):
    enter(project, "intent")
    with pytest.raises(store.WorkflowError):
        close.close_phase(project, "feature", "intent", "s", reviewer=blocking_review)
    mutate(
        project,
        engine.approve,
        "s",
        "close-over-findings",
        "intent",
        "Accept this documented residual.",
    )

    def must_not_run(*args):
        raise AssertionError("Review of identical accepted residual repeated")

    close.close_phase(project, "feature", "intent", "s", reviewer=must_not_run)
    record = store.load(project, "feature")
    assert record["phases"]["intent"]["evidence"]["outcome"] == "approved-over-findings"
    assert record["grants"][-1]["consumed"]


def test_suggestions_do_not_force_repair_cycles(project):
    """A pass with suggestions holds for the author's sort; the next close accepts the fixed
    revision on that review, spends no round, and names the files no reviewer read."""
    calls = []

    def suggestions(*args):
        calls.append(args)
        result = blocking_review()
        result["review"]["findings"][0]["severity"] = "suggestion"
        return result

    enter(project, "intent")
    with pytest.raises(store.WorkflowError, match="Review passed with 1 suggestion"):
        close.close_phase(project, "feature", "intent", "s", reviewer=suggestions)
    work = store.load(project, "feature")["phases"]["intent"]
    assert work["evidence"] is None and len(work["rounds"]) == 1
    (project / ".fbk/feature/prd.md").write_text("The author's fix for the suggestion.")
    result = close.close_phase(project, "feature", "intent", "s", reviewer=suggestions)
    assert result["phase"] == "spec"
    assert len(calls) == 1
    assert result["unreviewed_changes"] == {"intent": [".fbk/feature/prd.md"]}
    record = store.load(project, "feature")
    assert len(record["phases"]["intent"]["rounds"]) == 1
    assert record["phases"]["intent"]["evidence"]["author_sorted"] is True
    assert engine.status_report(project, record)["unreviewed_changes"] == {"intent": [".fbk/feature/prd.md"]}


def test_a_clean_pass_accepts_at_once(project):
    enter(project, "intent")
    result = close.close_phase(project, "feature", "intent", "s", reviewer=clean_review)
    assert result["phase"] == "spec"
    assert result["unreviewed_changes"] == {}


def test_a_decision_governing_the_phase_after_a_held_pass_needs_a_fresh_review(project):
    calls = []

    def suggestions(*args):
        calls.append(args)
        result = blocking_review()
        result["review"]["findings"][0]["severity"] = "suggestion"
        return result

    enter(project, "intent")
    with pytest.raises(store.WorkflowError, match="Review passed with"):
        close.close_phase(project, "feature", "intent", "s", reviewer=suggestions)
    (project / "answer.md").write_text("Add the retry the reviewer suggested.")
    with store.transaction(project):
        record = store.load(project, "feature")
        decisions.record(project, record, "s", {
            "id": "add-retry", "text": "Add the retry the reviewer suggested.", "phase": "intent",
            "kind": "governs", "source": {"path": "answer.md", "quote": "Add the retry the reviewer suggested."},
        })
        store.save(project, record)
    close.close_phase(project, "feature", "intent", "s", reviewer=clean_review)
    assert len(calls) == 1
    assert len(store.load(project, "feature")["phases"]["intent"]["rounds"]) == 2


def test_changed_artifact_while_review_running_cannot_close(project):
    def intervening_edit(*args):
        (project / ".fbk/feature/prd.md").write_text("Changed while reader ran.")
        return clean_review()

    enter(project, "intent")
    with pytest.raises(store.WorkflowError, match="stale"):
        close.close_phase(project, "feature", "intent", "s", reviewer=intervening_edit)
    assert not store.load(project, "feature")["phases"]["intent"]["evidence"]


def test_recovered_old_close_cannot_commit(project):
    def recover_during_review(*args):
        mutate(project, close.recover, "intent", "s", "Old process stopped.")
        return clean_review()

    enter(project, "intent")
    with pytest.raises(store.WorkflowError, match="reservation"):
        close.close_phase(
            project, "feature", "intent", "s", reviewer=recover_during_review
        )
    assert not store.load(project, "feature")["phases"]["intent"]["evidence"]


def test_incomplete_review_never_counts_as_clean(project):
    enter(project, "intent")
    with pytest.raises(store.WorkflowError):
        close.close_phase(
            project,
            "feature",
            "intent",
            "s",
            reviewer=lambda *a: {"review": {"findings": []}},
        )
    record = store.load(project, "feature")
    assert record["phases"]["intent"]["evidence"] is None
    assert record["phases"]["intent"]["pending"] is None


def test_other_session_requires_takeover_and_suspension_preserves_work(project):
    enter(project, "intent")
    with pytest.raises(store.WorkflowError, match="belongs"):
        enter(project, "intent", "other")
    mutate(project, engine.takeover, "other", "Previous terminal exited.")
    enter(project, "intent", "other")
    mutate(project, engine.suspend, "other", "Waiting for user clarification.")
    enter(project, "intent", "third")
    assert store.load(project, "feature")["owner"] == "third"


def test_stop_is_bounded_and_suspension_allows_human_handoff(project):
    enter(project, "intent")
    payload = {"hook_event_name": "Stop", "session_id": "s", "stop_hook_active": False}
    assert hooks.handle(project, payload)["decision"] == "block"
    assert hooks.handle(project, dict(payload, stop_hook_active=True)) == {}
    mutate(project, engine.suspend, "s", "Awaiting cancellation policy decision.")
    assert hooks.handle(project, payload) == {}


def test_write_gate_protects_scope_and_lock(project):
    prepare_implementation(project)
    payload = {
        "hook_event_name": "PreToolUse",
        "session_id": "s",
        "tool_name": "Write",
        "cwd": str(project),
    }

    def decision(path):
        return hooks.handle(project, dict(payload, tool_input={"file_path": path}))

    # Implementation starts with the reviewed tests already locked.
    assert (
        decision("src/app.py")["hookSpecificOutput"]["permissionDecision"] == "deny"
    )
    assert (
        decision("tests/check.py")["hookSpecificOutput"]["permissionDecision"] == "deny"
    )
    assert (
        decision("unrelated.py")["hookSpecificOutput"]["permissionDecision"] == "deny"
    )


def test_unconfigured_project_hook_is_silent_and_has_no_side_effect(tmp_path):
    assert (
        hooks.handle(tmp_path, {"hook_event_name": "PreToolUse", "tool_name": "Write"})
        == {}
    )
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("name", ["../escape", "/absolute", "runtime/unit"])
def test_unit_paths_cannot_escape_or_overlap_runtime(project, name):
    with pytest.raises(store.WorkflowError):
        engine.initialize(project, name)


def test_symlink_record_cannot_read_or_write_outside_repository(project, tmp_path):
    outside = project.parent / (project.name + "-outside.json")
    outside.write_text("external data")
    path = project / ".fbk/feature/state.json"
    path.unlink()
    path.symlink_to(outside)
    with pytest.raises(store.WorkflowError, match="escapes"):
        store.load(project, "feature")
    assert outside.read_text() == "external data"


def test_interrupted_replace_retains_previous_valid_record(project, monkeypatch):
    previous = store.load(project, "feature")

    def interrupted(*args):
        raise OSError("simulated interruption before commit")

    with monkeypatch.context() as patch:
        patch.setattr(store.os, "replace", interrupted)
        with pytest.raises(OSError):
            mutate(project, engine.enter, "intent", "s")
    assert store.load(project, "feature") == previous


def _append_in_process(root, index):
    with store.transaction(root, timeout=10):
        record = store.load(root, "feature")
        store.event(record, "worker-result", str(index), result=index)
        store.save(root, record)


def test_concurrent_processes_do_not_lose_updates(project):
    context = multiprocessing.get_context("fork")
    processes = [
        context.Process(target=_append_in_process, args=(project, i)) for i in range(8)
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join(10)
        assert process.exitcode == 0
    results = [
        e["result"]
        for e in store.load(project, "feature")["events"]
        if e["event"] == "worker-result"
    ]
    assert sorted(results) == list(range(8))


def test_task_dependency_cycle_blocks_breakdown(project):
    accept(project, "intent")
    accept(project, "spec")
    enter(project, "breakdown")
    store.atomic_json(
        project / ".fbk/feature/tasks.json",
        [
            {"id": "a", "description": "A", "files": ["src/a.py"], "depends_on": ["b"]},
            {"id": "b", "description": "B", "files": ["src/b.py"], "depends_on": ["a"]},
        ],
    )
    with pytest.raises(store.WorkflowError, match="cycle"):
        close.close_phase(project, "feature", "breakdown", "s", reviewer=clean_review)


def test_child_cannot_enter_against_changed_parent(project):
    accept(project, "intent")
    accept(project, "spec")
    with store.transaction(project):
        engine.initialize(project, "child", parent="feature", design=False)
    (project / ".fbk/feature/spec.md").write_text("Parent changed without review.")
    with pytest.raises(store.WorkflowError, match="Parent"):
        mutate(project, engine.enter, "intent", "s", unit="child")


def test_cli_works_from_nested_directory_and_reports_missing_prerequisites(project):
    dispatcher = Path(__file__).resolve().parents[1] / "fbk.py"
    result = subprocess.run(
        [
            sys.executable,
            str(dispatcher),
            "phase-enter",
            "spec",
            "feature",
            "--session",
            "cli",
        ],
        cwd=project / "src",
        capture_output=True,
        text=True,
        check=False,
    )
    # Pytest retains this command context on failure without changing mutation anchors.
    print(f"cwd={project / 'src'}\n{result!r}")
    assert result.returncode == 2
    assert "intent" in json.loads(result.stderr)["error"]


def test_reopen_forces_new_review_even_when_artifacts_are_identical(project):
    accept(project, "intent")
    mutate(
        project,
        engine.approve,
        "s",
        "reopen",
        "intent",
        "Reconsider the prior acceptance.",
    )
    mutate(project, engine.reopen, "intent", "s", "Reconsider the prior acceptance.")
    enter(project, "intent")
    with pytest.raises(store.WorkflowError, match="approval required"):
        close.close_phase(project, "feature", "intent", "s", reviewer=blocking_review)
    assert len(store.load(project, "feature")["phases"]["intent"]["rounds"]) == 2


def test_missing_session_cannot_inherit_suspended_write_authority(project):
    prepare_implementation(project)
    mutate(project, engine.suspend, "s", "Awaiting user.")
    result = hooks.handle(
        project,
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "cwd": str(project),
            "tool_input": {"file_path": "src/app.py"},
        },
    )
    assert result["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_backup_directory_does_not_block_real_units(project):
    store.atomic_json(project / ".fbk/.backup/state.json", {})
    enter(project, "intent")
    assert store.discover(project) == ["feature"]


def test_invalid_review_can_retry_without_editing_artifacts(project):
    enter(project, "intent")
    with pytest.raises(store.WorkflowError):
        close.close_phase(
            project,
            "feature",
            "intent",
            "s",
            reviewer=lambda *a: {"review": {"findings": []}},
        )
    assert (
        close.close_phase(project, "feature", "intent", "s", reviewer=clean_review)[
            "phase"
        ]
        == "spec"
    )


def test_worker_lifecycle_prevents_close_until_worker_finishes(project):
    enter(project, "intent")
    payload = {"session_id": "s", "agent_id": "worker-1"}
    hooks.handle(project, dict(payload, hook_event_name="SubagentStart"))
    with pytest.raises(store.WorkflowError, match="Workers"):
        close.close_phase(project, "feature", "intent", "s", reviewer=clean_review)
    hooks.handle(project, dict(payload, hook_event_name="SubagentStop"))
    assert (
        close.close_phase(project, "feature", "intent", "s", reviewer=clean_review)[
            "phase"
        ]
        == "spec"
    )


def test_invisible_character_in_spec_fails_close_before_any_reviewer_and_spends_no_round(project):
    accept(project, "intent")
    enter(project, "spec")
    spec = project / ".fbk/feature/spec.md"
    spec.write_text(
        "# Requirements\nThe vertical tab \x0b ends a record. Release exactly once.\n"
        "## Line boundaries\nServes [Release on cancel](prd.md#release-on-cancel).\n"
    )

    def reviewer(*args):
        pytest.fail("A reviewer must not launch while the artifact carries invisible characters")

    with pytest.raises(store.WorkflowError) as failure:
        close.close_phase(project, "feature", "spec", "s", reviewer=reviewer)
    message = str(failure.value)
    assert ".fbk/feature/spec.md:2:18 U+000B LINE TABULATION" in message
    assert "Write each character as an escape" in message and "then close again" in message
    record = store.load(project, "feature")
    assert record["phases"]["spec"]["rounds"] == []
    assert record["phases"]["spec"]["pending"] is None
    attempt = [e for e in record["events"] if e["event"] == "close-attempt" and e["phase"] == "spec"][-1]
    assert attempt["outcome"] == "failed"
    assert attempt["artifact_hygiene"]["outcome"] == "findings"
    assert attempt["artifact_hygiene"]["findings"][0]["codepoint"] == "U+000B"
    # Only the unit's own artifacts are scanned, never code, tests, or context.
    assert all(path.startswith(".fbk/feature/") for path in attempt["artifact_hygiene"]["scanned"])

    spec.write_text(spec.read_text().replace("\x0b", "\\v"))
    assert close.close_phase(project, "feature", "spec", "s", reviewer=clean_review)["accepted_phase"] == "spec"
    record = store.load(project, "feature")
    assert len(record["phases"]["spec"]["rounds"]) == 1
    attempt = [e for e in record["events"] if e["event"] == "close-attempt" and e["phase"] == "spec"][-1]
    assert attempt["outcome"] == "pass"
    assert attempt["artifact_hygiene"]["outcome"] == "clean"
    assert ".fbk/feature/spec.md" in attempt["artifact_hygiene"]["scanned"]


def held_intent(root, *, snapshot=False):
    """Intent's review passes with one suggestion and is held for the author's sort.
    With snapshot, the review records every source it read, as a native review does."""
    calls = []

    def suggestions(*args):
        calls.append(args)
        result = blocking_review()
        result["review"]["findings"][0]["severity"] = "suggestion"
        if snapshot:
            import hashlib
            from fbk.workflow.review_context import source_paths

            result["source_policy"] = "original-snapshot-v1"
            result["required_files"] = []
            result["snapshot_files"] = {
                p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in source_paths(root, [])
            }
        return result

    enter(root, "intent")
    with pytest.raises(store.WorkflowError, match="Review passed with"):
        close.close_phase(root, "feature", "intent", "s", reviewer=suggestions)
    return calls


def decide(root, request):
    (root / f"{request['id']}.md").write_text(request["text"])
    request = {**request, "source": {"path": f"{request['id']}.md", "quote": request["text"]}}
    with store.transaction(root):
        record = store.load(root, "feature")
        decisions.record(root, record, "s", request)
        store.save(root, record)


def test_a_decision_governing_the_phase_superseded_after_the_hold_still_needs_a_fresh_review(project):
    held_intent(project)
    decide(project, {"id": "add-retry", "text": "Add the retry.", "phase": "intent", "kind": "governs"})
    decide(project, {"id": "no-retry", "text": "Leave the retry out after all.", "phase": "intent",
                     "kind": "process", "supersedes": "add-retry"})
    close.close_phase(project, "feature", "intent", "s", reviewer=clean_review)
    assert len(store.load(project, "feature")["phases"]["intent"]["rounds"]) == 2


def test_an_amendment_of_the_phase_after_the_hold_needs_a_fresh_review(project):
    with store.transaction(project):
        record = store.load(project, "feature")
        record["decisions"] = [{"id": "late", "text": "Amend intent.", "phase": "spec", "kind": "governs",
                                "amends": "intent", "source": {}, "supersedes": None, "at": "9999-01-01T00:00:00+00:00"}]
        store.save(project, record)
    with store.transaction(project):
        record = store.load(project, "feature")
        assert close._governing_after(record, "intent", "2026-10-31T00:00:00+00:00")
        assert not close._governing_after(record, "design", "2026-10-31T00:00:00+00:00")


def test_a_sorted_close_refuses_when_a_source_outside_the_phase_changed(project):
    held_intent(project, snapshot=True)
    (project / "CLAUDE.md").write_text("A convention changed after the review.")
    with pytest.raises(store.WorkflowError, match="Review sources changed"):
        close.close_phase(project, "feature", "intent", "s", reviewer=clean_review)
    assert store.load(project, "feature")["phases"]["intent"]["evidence"] is None


def test_a_sorted_close_accepts_changes_to_the_phase_own_files_with_a_full_snapshot(project):
    held_intent(project, snapshot=True)
    (project / ".fbk/feature/prd.md").write_text("The author's fix.")
    result = close.close_phase(project, "feature", "intent", "s", reviewer=clean_review)
    assert result["unreviewed_changes"] == {"intent": [".fbk/feature/prd.md"]}


def test_a_hold_on_the_last_round_is_not_an_exhausted_budget(project):
    enter(project, "intent")
    with store.transaction(project):
        record = store.load(project, "feature")
        record["phases"]["intent"]["round_limit"] = 1
        store.save(project, record)
    calls = held_intent(project)
    record = store.load(project, "feature")
    assert engine.status_report(project, record)["status"] != "human-review-required"
    assert not [e for e in record["events"] if e["event"] == "human-review-required"]
    close.close_phase(project, "feature", "intent", "s", reviewer=clean_review)
    assert len(calls) == 1
