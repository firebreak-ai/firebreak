"""Failed reviewer stages retain bounded evidence needed to diagnose the host."""

import json
import sys

import pytest
from fbk.workflow import council, review, store
from tests.test_workflow_review import finding


def test_turn_failure_retains_structured_host_error_and_completed_readers(tmp_path, monkeypatch):
    host_error = {"subtype": "error_max_structured_output_retries", "errors": ["turn comment exceeds the schema limit"], "num_turns": 7}
    def command(argv, root, timeout, prompt):
        schema = json.loads(argv[argv.index("--json-schema") + 1])
        if "comment" in schema["properties"]:
            return {"exit_code": 1, "stdout": json.dumps(host_error), "stderr": "x" * 5000, "seconds": 299}
        data = {"summary": "Inspected", "findings": [finding()],
                "context": {"status": "complete", "inspected_files": [], "supporting_files": [], "missing_context": []}}
        return {"exit_code": 0, "stdout": json.dumps({"subtype": "success", "structured_output": data}), "stderr": "", "seconds": 2}
    monkeypatch.setattr(review, "run_command", command)
    result = council.run(tmp_path, "Inspect originals", {}, "spec", ["architect", "guardian"], review.claude_review)
    assert result["review"] is None and result.get("error")
    assert len(result["readers"]) == 2
    assert result["failure"]["stage"] == "turn" and result["failure"]["member"] == "architect"
    diagnostic = result["failure"]["diagnostics"]
    assert json.loads(diagnostic["stdout"])["errors"] == host_error["errors"]
    assert diagnostic["seconds"] == 299
    assert len(diagnostic["stderr"]) == 4000 and diagnostic["stderr_omitted_bytes"] == 1000


def test_timeout_preserves_output_produced_before_process_was_stopped(tmp_path):
    with pytest.raises(store.WorkflowError) as failed:
        review.run_command([sys.executable, "-c", "import time; print('reader reached source inspection', flush=True); time.sleep(30)"], tmp_path, 1)
    diagnostic = failed.value.diagnostics
    assert "reader reached source inspection" in diagnostic["stdout"]
    assert diagnostic["exit_code"] != 0
    assert diagnostic["category"] == "timeout"
    assert diagnostic["timeout_seconds"] == 1
    assert "budget_exhausted" not in diagnostic
