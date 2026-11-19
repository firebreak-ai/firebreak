"""Prior review judgments must not pollute current-source reviewer prompts."""

import copy
import json

import pytest

from fbk.workflow import council, review, review_context, store
from tests.test_workflow_review import native


@pytest.mark.parametrize("mode", ["single", "council"])
def test_prior_judgments_do_not_change_reviewer_prompt(tmp_path, monkeypatch, mode):
    record = {"events": [], "parent": None,
              "phases": {"spec": {"pending": None, "rounds": []}},
              "review_plans": {"spec": {"mode": mode, "members": ["architect", "guardian"]}}}
    captured = []
    def capture(root, prompt, *args, **kwargs):
        captured.append(prompt)
        return native()
    monkeypatch.setattr(review, "claude_review", capture)
    monkeypatch.setattr(council, "run", capture)
    config = {"_review_decisions": [{"id": "explicit-rule", "text": "Preserve literal paths.",
                "phase": "intent", "source": {"path": "decision.md"}, "supersedes": []}]}
    review._review_sources(tmp_path, "unit", "spec", ["spec.md", "decision.md"], [], config, record)
    record["events"] = [{"event": "reopened", "phase": "spec", "reason": "OLD_REOPEN_NARRATIVE"}]
    record["phases"]["spec"]["rounds"] = [{"revision": "old", "result": {
        "review": {"summary": "OLD_JUDGMENT", "findings": []},
        "candidates": [{"finding": "OLD_CANDIDATE"}],
        "readers": [{"stage": "adjudication", "review": "OLD_REFUTATION"}]}}]
    before = copy.deepcopy(record)
    review._review_sources(tmp_path, "unit", "spec", ["spec.md", "decision.md"], [], config, record)
    assert captured[0] == captured[1]
    assert "OLD_" not in captured[1]
    packet = json.loads(captured[1].splitlines()[-1])
    assert "review_continuity" not in packet
    assert packet["current_decisions"][0]["text"] == "Preserve literal paths."
    assert "supersedes" not in packet["current_decisions"][0]
    assert "files" not in packet and packet["required_files"] == {
        "phase_targets": [], "authoritative_context": ["decision.md", "spec.md"]}
    assert record == before  # The coordinator's durable history remains intact.


def test_missing_inspection_diagnostic_identifies_declarations_and_truthful_action():
    context = {"status": "complete", "inspected_files": ["spec.md"],
               "supporting_files": [], "missing_context": []}
    with pytest.raises(store.WorkflowError) as caught:
        review_context.validate_context(context, ["spec.md", "a.md", "b.md"], ["b.md", "spec.md", "a.md"])
    assert caught.value.inspection_missing_paths == ["a.md", "b.md"]
    assert "a.md, b.md" in str(caught.value)
    assert "actually read" in str(caught.value)
    assert "not proof" in str(caught.value)
    assert context["inspected_files"] == ["spec.md"]


def test_required_path_declared_only_as_supporting_source_validates():
    # Replays a live council declaration: the last required path appeared only in
    # supporting_files, and several paths appeared in both lists.
    required = ["spec.md", "design/overview.md", ".fbk/unit/decisions/refuse-unknown-keys.md"]
    context = {"status": "complete",
               "inspected_files": ["spec.md", "design/overview.md", "src/app.py"],
               "supporting_files": [".fbk/unit/decisions/refuse-unknown-keys.md", "spec.md"],
               "missing_context": []}
    available = [*required, "src/app.py"]
    assert review_context.validate_context(context, available, required) is context
    assert context["inspected_files"] == ["spec.md", "design/overview.md", "src/app.py"]
    assert context["supporting_files"] == [".fbk/unit/decisions/refuse-unknown-keys.md", "spec.md"]


def test_required_path_in_neither_declaration_list_is_missing():
    context = {"status": "complete", "inspected_files": ["spec.md"],
               "supporting_files": ["CLAUDE.md"], "missing_context": []}
    with pytest.raises(store.WorkflowError) as caught:
        review_context.validate_context(
            context, ["spec.md", "CLAUDE.md", "decision.md"], ["spec.md", "decision.md"])
    assert caught.value.inspection_missing_paths == ["decision.md"]
    assert "inspected_files" in str(caught.value)
    assert "supporting_files" in str(caught.value)


def test_supporting_only_path_outside_snapshot_is_rejected():
    context = {"status": "complete", "inspected_files": ["spec.md"],
               "supporting_files": ["../outside.md"], "missing_context": []}
    with pytest.raises(store.WorkflowError, match="outside the controlled snapshot"):
        review_context.validate_context(context, ["spec.md"], ["spec.md"])


def test_unknown_inspection_path_names_entries_and_exact_spelling_rule():
    # A directory, a glob, a ./ prefix, and an absolute path are all misspellings
    # of snapshot entries; the reader gets them back verbatim to correct.
    context = {"status": "complete",
               "inspected_files": ["spec.md", "src/", "./spec.md", "/abs/spec.md"],
               "supporting_files": ["docs/*.md"], "missing_context": []}
    with pytest.raises(store.WorkflowError) as caught:
        review_context.validate_context(
            context, ["spec.md", "src/app.py", "docs/a.md"], ["spec.md"])
    assert caught.value.inspection_unknown_paths == [
        "./spec.md", "/abs/spec.md", "docs/*.md", "src/"]
    message = str(caught.value)
    assert "./spec.md, /abs/spec.md, docs/*.md, src/" in message
    assert "spelled exactly as it appears in required_files or the snapshot listing" in message
    assert "no directories, wildcards, ./ prefixes, or absolute paths" in message
    assert "Correct the declaration and resubmit" in message
    assert not hasattr(caught.value, "inspection_missing_paths")


def test_unknown_inspection_paths_are_capped_with_a_remainder_count():
    unknown = [f"ghost/{index:03d}.md" for index in range(30)]
    context = {"status": "complete", "inspected_files": ["spec.md", *unknown],
               "supporting_files": [], "missing_context": []}
    with pytest.raises(store.WorkflowError) as caught:
        review_context.validate_context(context, ["spec.md"], ["spec.md"])
    assert caught.value.inspection_unknown_paths == unknown
    assert "ghost/024.md (and 5 more)" in str(caught.value)
    assert "ghost/025.md" not in str(caught.value)


def test_missing_required_paths_take_precedence_over_unknown_paths():
    context = {"status": "complete", "inspected_files": ["spec.md", "src/"],
               "supporting_files": [], "missing_context": []}
    with pytest.raises(store.WorkflowError) as caught:
        review_context.validate_context(
            context, ["spec.md", "decision.md", "src/app.py"], ["spec.md", "decision.md"])
    assert caught.value.inspection_missing_paths == ["decision.md"]
    assert not hasattr(caught.value, "inspection_unknown_paths")
    assert "outside the controlled snapshot" not in str(caught.value)


def test_host_validation_preserves_typed_unknown_paths_for_bounded_correction(tmp_path, monkeypatch):
    data = {"summary": "Inspected", "findings": [],
            "context": {"status": "complete", "inspected_files": ["spec.md", "src/"],
                        "supporting_files": [], "missing_context": []}}
    monkeypatch.setattr(review, "run_command", lambda *args: {
        "exit_code": 0, "stdout": json.dumps({"subtype": "success", "structured_output": data}),
        "stderr": "", "seconds": 1,
    })
    with pytest.raises(store.WorkflowError) as caught:
        review._claude_session(tmp_path, "Inspect originals", {
            "_review_required_files": ["spec.md"],
            "_review_available_files": {"spec.md": "x", "src/app.py": "y"}})
    assert caught.value.inspection_unknown_paths == ["src/"]
    assert caught.value.diagnostics["unknown_inspection_paths"] == ["src/"]
    assert "missing_inspection_paths" not in caught.value.diagnostics


def test_incomplete_declaration_naming_missing_items_validates():
    context = {"status": "incomplete", "inspected_files": ["spec.md"],
               "supporting_files": [],
               "missing_context": ["design/cache.md cited by spec.md is not in the snapshot"]}
    assert review_context.validate_context(context, ["spec.md"], ["spec.md"]) is context
    assert context["status"] == "incomplete"


@pytest.mark.parametrize("status, missing, expected", [
    ("complete", ["A decision record is unavailable"],
     "status complete requires an empty missing_context"),
    ("incomplete", [], "status incomplete requires missing_context to name each unavailable item"),
])
def test_contradictory_status_and_missing_items_is_a_malformed_declaration(status, missing, expected):
    context = {"status": status, "inspected_files": ["spec.md"],
               "supporting_files": [], "missing_context": missing}
    with pytest.raises(store.WorkflowError, match=expected):
        review_context.validate_context(context, ["spec.md"], ["spec.md"])


def test_incomplete_declaration_still_names_the_required_paths_it_read():
    context = {"status": "incomplete", "inspected_files": [], "supporting_files": [],
               "missing_context": ["design/cache.md is absent"]}
    with pytest.raises(store.WorkflowError) as caught:
        review_context.validate_context(context, ["spec.md"], ["spec.md"])
    assert caught.value.inspection_missing_paths == ["spec.md"]


def test_host_session_returns_an_incomplete_declaration_as_the_reader_verdict(tmp_path, monkeypatch):
    data = {"summary": "The cited cache design is not in the snapshot; no decision possible.",
            "findings": [],
            "context": {"status": "incomplete", "inspected_files": ["spec.md"],
                        "supporting_files": [],
                        "missing_context": ["design/cache.md cited by spec.md is absent"]}}
    monkeypatch.setattr(review, "run_command", lambda *args: {
        "exit_code": 0, "stdout": json.dumps({"subtype": "success", "structured_output": data}),
        "stderr": "", "seconds": 1,
    })
    result = review._claude_session(tmp_path, "Inspect originals", {
        "_review_required_files": ["spec.md"], "_review_available_files": {"spec.md": "x"}})
    assert result["context"]["status"] == "incomplete"
    assert result["context"]["missing_context"] == ["design/cache.md cited by spec.md is absent"]
    assert result["review"]["summary"] == data["summary"]


def test_host_validation_preserves_typed_missing_paths_for_bounded_correction(tmp_path, monkeypatch):
    data = {"summary": "Inspected", "findings": [],
            "context": {"status": "complete", "inspected_files": [],
                        "supporting_files": [], "missing_context": []}}
    monkeypatch.setattr(review, "run_command", lambda *args: {
        "exit_code": 0, "stdout": json.dumps({"subtype": "success", "structured_output": data}),
        "stderr": "", "seconds": 1,
    })
    with pytest.raises(store.WorkflowError) as caught:
        review._claude_session(tmp_path, "Inspect originals", {"_review_required_files": ["decision.md"]})
    assert caught.value.inspection_missing_paths == ["decision.md"]
    assert caught.value.diagnostics["missing_inspection_paths"] == ["decision.md"]
