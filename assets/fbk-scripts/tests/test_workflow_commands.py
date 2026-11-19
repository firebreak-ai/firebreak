"""Exercise the public argument and execution seam, including real test commands."""

import json
import subprocess
import sys

import pytest
from fbk.workflow import cli, review, store

from tests import test_workflow_lifecycle as scenarios
from tests.test_workflow_lifecycle import clean_review

project = scenarios.project


@pytest.mark.parametrize(
    "decision_phase,expected_phase,expected_status,expected_next",
    [
        ("intent", "intent", "stale", "Reopen intent."),
        ("spec", "spec", "ready", "Enter spec."),
    ],
)
def test_recording_decision_reports_current_readiness(
    project, decision_phase, expected_phase, expected_status, expected_next
):
    scenarios.accept(project, "intent")
    source = project / ".fbk/feature/decision.md"
    quote = "Canceling an already canceled task returns false."
    source.write_text(quote)
    request = {
        "id": "repeat-cancel",
        "text": quote,
        "phase": decision_phase, "kind": "governs",
        "source": {"path": ".fbk/feature/decision.md", "quote": quote},
    }
    store.atomic_json(project / ".fbk/request.json", request)

    result = call(project, "decision-record", "feature", "--request", ".fbk/request.json")

    assert result["id"] == request["id"]
    assert result["phase"] == decision_phase
    assert result["source"]["quote"] == quote
    workflow = result["workflow"]
    assert (workflow["phase"], workflow["status"], workflow["next"]) == (
        expected_phase, expected_status, expected_next
    )
    assert workflow == call(project, "status", "feature")[0]


def call(root, command, *arguments):
    args = cli.parser_for(command).parse_args(
        [*arguments, "--root", str(root), "--session", "s"]
    )
    return cli.execute(command, args)


def test_project_init_is_idempotent_and_preserves_operator_settings(tmp_path, project):
    from tests.test_workflow_checkpoint_review_inputs import checkpointed_folders, git, ignored

    # The two folder names come from a real checkpoint; they are the implementer's choice.
    folders = checkpointed_folders(project)[:2]
    call(tmp_path, "workflow-init")
    config = tmp_path / ".fbk/config.json"
    data = json.loads(config.read_text())
    data["reviewer_model"] = "sonnet"
    store.atomic_json(config, data)
    call(tmp_path, "workflow-init")
    assert json.loads(config.read_text())["reviewer_model"] == "sonnet"
    assert "runtime/" in (tmp_path / ".fbk/.gitignore").read_text().splitlines()
    assert git(tmp_path, "init", "-q").returncode == 0
    for folder in folders:
        assert ignored(tmp_path, f"{folder}/saved.txt"), f"A new project does not ignore {folder}."


def test_project_unit_runs_design_and_ends_after_spec(tmp_path, monkeypatch):
    monkeypatch.setattr(review, "review", clean_review)
    call(tmp_path, "workflow-init")
    call(tmp_path, "unit-init", "platform", "--kind", "project")
    for phase in ("design", "spec"):
        call(
            tmp_path,
            "review-plan",
            "platform",
            "--phase",
            phase,
            "--mode",
            "single",
            "--reason",
            "The operator selected single review for this project.",
        )
    base = tmp_path / ".fbk/platform"
    (base / "prd.md").write_text(
        "# Platform\n\n## Commitments\n\n### Cancelable jobs\n\nThe platform supports cancelable jobs.\n"
    )
    (base / "design").mkdir()
    (base / "design/overview.md").write_text(
        "# Overview\n\n## Design choices\n\n### One scheduler\n\n"
        "Keep one scheduler and an explicit job state, serving [Cancelable jobs](../prd.md#cancelable-jobs).\n"
    )
    (base / "spec.md").write_text(
        "# Contract\n\n## Requirements\n\n### Boolean cancel\n\n"
        "Shared job cancellation returns a boolean, from [One scheduler](design/overview.md#one-scheduler).\n"
    )
    store.atomic_json(base / "scope.json", {"sources": [], "tests": [], "checks": []})
    for phase in ("intent", "design", "spec"):
        call(tmp_path, "phase-enter", phase, "platform")
        result = call(tmp_path, "phase-close", phase, "platform")
        scenarios.observe_phase(tmp_path, phase, unit="platform")
    assert result["status"] == "retrospective-required"
    assert call(tmp_path, "status", "platform")[0]["status"] == "closed"
    assert result["accepted_phase"] == "spec"


# The public lock-tests command and its --red-check / --preserve-existing arguments are
# gone: the test checkpoint is the only way to lock (test_workflow_test_checkpoint covers
# its CLI command, red evidence, and preservation).


def test_public_recovery_and_budget_extension_are_audited(project):
    call(project, "phase-enter", "intent", "feature")
    with store.transaction(project):
        record = store.load(project, "feature")
        record["phases"]["intent"]["pending"] = {"id": "abandoned", "at": store.now()}
        store.save(project, record)
    assert call(project, "status", "feature")[0]["status"] == "reviewing"
    call(
        project,
        "recover-close",
        "intent",
        "feature",
        "--reason",
        "Abandoned process was stopped.",
    )
    call(
        project,
        "extend-review",
        "intent",
        "feature",
        "--rounds",
        "1",
        "--reason",
        "One more evidence pass authorized.",
    )
    report = call(project, "workflow-report", "feature", "--history")[0]
    assert {"close-recovered", "review-extended"} <= {
        e["event"] for e in report["events"]
    }
    assert store.load(project, "feature")["phases"]["intent"]["round_limit"] == 4


def test_doctor_reports_unavailable_host_instead_of_traceback(project, monkeypatch):
    import shutil

    seen = []

    def timeout(*args, **kwargs):
        seen.append(args)
        raise subprocess.TimeoutExpired("claude", 10)

    monkeypatch.setattr(shutil, "which", lambda _: "/fake/claude")
    monkeypatch.setattr(subprocess, "run", timeout)
    assert call(project, "doctor")["claude"] is None
    assert seen


def test_failed_verification_output_cannot_claim_success(project, monkeypatch):
    monkeypatch.setattr(
        review,
        "run_command",
        lambda *a: {
            "exit_code": 1,
            "stdout": "ALL TESTS PASSED",
            "stderr": "",
            "argv": ["check"],
            "seconds": 0,
        },
    )
    assert review.verify(project, [["check"]])[0]["exit_code"] == 1


@pytest.mark.parametrize(
    "envelope",
    [
        {
            "is_error": True,
            "structured_output": {"summary": "Looks fine", "findings": []},
        },
        {
            "subtype": "error_max_turns",
            "structured_output": {"summary": "Looks fine", "findings": []},
        },
        {"result": "No findings"},
        {"structured_output": {"summary": "", "findings": []}},
    ],
)
def test_incomplete_headless_envelope_never_becomes_clean_review(
    project, monkeypatch, envelope
):
    monkeypatch.setattr(
        review,
        "run_command",
        lambda *a: {
            "exit_code": 0,
            "stdout": json.dumps(envelope),
            "stderr": "",
            "seconds": 0,
        },
    )
    with pytest.raises(store.WorkflowError):
        review.claude_review(project, "Inspect the contract.", {})


def test_timeout_terminates_child_check_processes(tmp_path):
    import time

    marker = tmp_path / "surviving-child"
    child = (
        'import pathlib,time; time.sleep(0.6); pathlib.Path("surviving-child").touch()'
    )
    parent = (
        "import subprocess,sys,time; "
        f'subprocess.Popen([sys.executable,"-c",{child!r}]); time.sleep(10)'
    )
    with pytest.raises(store.WorkflowError, match="exceeded"):
        review.run_command([sys.executable, "-c", parent], tmp_path, 0.2)
    time.sleep(0.7)
    assert not marker.exists(), (
        "A timed-out check left a child able to mutate the repository"
    )


@pytest.mark.parametrize("pattern", [".fbk", ".claude", "**/*.json"])
def test_scope_cannot_absorb_workflow_control_records(tmp_path, pattern):
    from fbk.workflow import evidence

    call(tmp_path, "workflow-init")
    call(tmp_path, "unit-init", "unit")
    (tmp_path / ".fbk/unit/scope.json").write_text(
        json.dumps({"sources": [pattern], "tests": [], "checks": []})
    )
    with pytest.raises(store.WorkflowError, match="control records"):
        evidence.scope(tmp_path, "unit")


def test_blocked_close_explains_the_defect_and_recovery(project, monkeypatch):
    root = project
    monkeypatch.setattr(review, "review", scenarios.blocking_review)
    call(root, "phase-enter", "intent", "feature")
    with pytest.raises(store.WorkflowError) as error:
        call(root, "phase-close", "intent", "feature")
    message = str(error.value)
    assert "Cancellation does not release the resource" in message
    assert "Release it on cancellation." in message
    assert "retry close" in message
    assert len(store.load(root, "feature")["phases"]["intent"]["rounds"]) == 1


def _fbk_tree(root):
    return sorted(str(p.relative_to(root)) for p in (root / ".fbk").rglob("*"))


@pytest.mark.parametrize(
    "unit,suggested",
    [
        ("word count", "word-count"),
        ("word\tcount", "word-count"),
        ("word\ncount", "word-count"),
        ("  word  count ", "word-count"),
        ("parent/my child", "parent/my-child"),
    ],
    ids=["space", "tab", "newline", "edge-whitespace", "child-segment"],
)
def test_unit_init_refuses_whitespace_and_suggests_the_dashed_name(
    tmp_path, unit, suggested
):
    """Red: unit creation accepts any whitespace today. The ruling says it must
    refuse, name the given name, suggest the dashed name, and create nothing."""
    call(tmp_path, "workflow-init")
    before = _fbk_tree(tmp_path)
    with pytest.raises(store.WorkflowError) as error:
        call(tmp_path, "unit-init", unit)
    message = str(error.value)
    assert unit in message or repr(unit) in message, message
    assert suggested in message, message
    assert _fbk_tree(tmp_path) == before
    assert not (tmp_path / ".fbk" / unit).exists()


def test_unit_init_whitespace_refusal_is_a_clean_cli_error(tmp_path):
    """Red: through the real dispatcher a spaced name creates a unit today. It
    must exit with the workflow's error code and a JSON error, not a traceback."""
    from pathlib import Path

    call(tmp_path, "workflow-init")
    dispatcher = Path(__file__).resolve().parents[1] / "fbk.py"
    result = subprocess.run(
        [sys.executable, str(dispatcher), "unit-init", "word count",
         "--root", str(tmp_path), "--session", "cli"],
        capture_output=True, text=True, check=False,
    )
    print(repr(result))
    assert result.returncode == 2
    assert "Traceback" not in result.stderr
    error = json.loads(result.stderr)
    assert error["command"] == "unit-init"
    assert "word count" in error["error"] and "word-count" in error["error"]
    assert not (tmp_path / ".fbk/word count").exists()


@pytest.mark.parametrize("unit", ["word-count", "parent/child"])
def test_unit_init_still_creates_ordinary_and_nested_names(tmp_path, unit):
    """Guard: the whitespace refusal must not block names without whitespace,
    including a nested parent/child name."""
    call(tmp_path, "workflow-init")
    call(tmp_path, "unit-init", unit)
    assert (tmp_path / ".fbk" / unit / "state.json").exists()
    assert store.load(tmp_path, unit)["unit"] == unit
