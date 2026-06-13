"""Tests for fbk.hooks.task_completed detection functions and verification-event emission."""

import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path

import pytest
from fbk.hooks.task_completed import (
    count_lint_errors,
    count_test_failures,
    detect_lint_cmd,
    detect_test_cmd,
)

try:
    from fbk.capture import event_writer as _event_writer_mod
except ImportError:
    _event_writer_mod = None

from tests import capture_fixtures

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FBK_PY = Path(__file__).parent.parent / "fbk.py"

TASK_PATH_PATTERN = r"ai-docs/\S+?/\S*tasks/task-\S*\.md"


class TestFailureCountParsing:
    """The verification event must record the real number of failures, not a 0/1 flag.

    A flag (always 1) makes 1 failing test and 50 failing tests indistinguishable.
    These assert exact counts greater than one so a reversion to the flag fails.
    """

    def test_pytest_summary_counts_each_failure(self):
        output = "=== 5 failed, 3 passed in 0.21s ==="
        assert count_test_failures("python -m pytest", output) == 5

    def test_go_counts_each_fail_line(self):
        output = "--- FAIL: TestA\n--- FAIL: TestB\n--- FAIL: TestC\nFAIL\n"
        assert count_test_failures("go test ./...", output) == 3

    def test_unparseable_test_output_reports_at_least_one(self):
        # A bare non-zero exit with no summary must never read as zero.
        assert count_test_failures("make test", "Makefile:2: recipe failed") == 1

    def test_ruff_summary_counts_each_error(self):
        assert count_lint_errors("ruff check .", "Found 7 errors.") == 7

    def test_eslint_summary_counts_errors_not_warnings(self):
        output = "✖ 10 problems (8 errors, 2 warnings)"
        assert count_lint_errors("npx eslint .", output) == 8

    def test_unparseable_lint_output_reports_at_least_one(self):
        assert count_lint_errors("cargo clippy", "error: could not compile") == 1


class TestTaskPathRegex:
    """Tests for the task-description path regex that scopes the hook to SDL tasks."""

    def test_matches_feature_suffixed_tasks_dir(self):
        """Current breakdown convention: ai-docs/<feature>/<feature>-tasks/task-NN.md."""
        desc = "Task file: ai-docs/agent-personas/agent-personas-tasks/task-06-impl-council-architect.md\nRead that file..."
        match = re.search(TASK_PATH_PATTERN, desc)
        assert match is not None
        assert match.group(0) == "ai-docs/agent-personas/agent-personas-tasks/task-06-impl-council-architect.md"

    def test_matches_plain_tasks_dir(self):
        """Legacy convention: ai-docs/<feature>/tasks/task-NN.md."""
        desc = "Task file: ai-docs/myfeature/tasks/task-01-setup.md\nExecute it."
        match = re.search(TASK_PATH_PATTERN, desc)
        assert match is not None
        assert match.group(0) == "ai-docs/myfeature/tasks/task-01-setup.md"

    def test_non_sdl_task_description_does_not_match(self):
        """A task description with no SDL task path should not match."""
        desc = "Refactor the login component to use the new auth hook."
        match = re.search(TASK_PATH_PATTERN, desc)
        assert match is None

    def test_path_without_ai_docs_prefix_does_not_match(self):
        """A task.md path outside ai-docs/ should not match."""
        desc = "Review tasks/task-foo.md under specs/"
        match = re.search(TASK_PATH_PATTERN, desc)
        assert match is None

    def test_matches_absolute_path(self):
        """Absolute paths should still match (regex searches for substring)."""
        desc = "Task file: /home/user/proj/ai-docs/feat/feat-tasks/task-01-bootstrap.md"
        match = re.search(TASK_PATH_PATTERN, desc)
        assert match is not None
        assert match.group(0) == "ai-docs/feat/feat-tasks/task-01-bootstrap.md"


class TestDetectTestCmd:
    """Tests for detect_test_cmd function."""

    def test_npm_project_detected(self, tmp_path):
        """Test npm project (package.json) returns 'npm test'."""
        (tmp_path / "package.json").write_text("{}")
        result = detect_test_cmd(str(tmp_path))
        assert result == "npm test"

    def test_cargo_project_detected(self, tmp_path):
        """Test Rust project (Cargo.toml) returns 'cargo test'."""
        (tmp_path / "Cargo.toml").write_text("")
        result = detect_test_cmd(str(tmp_path))
        assert result == "cargo test"

    def test_go_project_detected(self, tmp_path):
        """Test Go project (go.mod) returns 'go test ./...'."""
        (tmp_path / "go.mod").write_text("")
        result = detect_test_cmd(str(tmp_path))
        assert result == "go test ./..."

    def test_pytest_project_detected(self, tmp_path):
        """Test pytest project (pyproject.toml with [tool.pytest]) returns 'python -m pytest'."""
        (tmp_path / "pyproject.toml").write_text("[tool.pytest]\n")
        result = detect_test_cmd(str(tmp_path))
        assert result == "python -m pytest"

    def test_makefile_test_target_detected(self, tmp_path):
        """Test Makefile with test target returns 'make test'."""
        (tmp_path / "Makefile").write_text("test:\n\techo 'testing'\n")
        result = detect_test_cmd(str(tmp_path))
        assert result == "make test"

    def test_empty_directory_returns_empty_string(self, tmp_path):
        """Test empty directory returns empty string."""
        result = detect_test_cmd(str(tmp_path))
        assert result == ""


class TestDetectLintCmd:
    """Tests for detect_lint_cmd function."""

    def test_eslint_detected(self, tmp_path):
        """Test eslint detection (.eslintrc.json) returns string containing 'eslint'."""
        (tmp_path / ".eslintrc.json").write_text("{}")
        result = detect_lint_cmd(str(tmp_path))
        assert "eslint" in result

    def test_ruff_detected(self, tmp_path):
        """Test ruff detection (pyproject.toml with [tool.ruff]) returns string containing 'ruff'."""
        (tmp_path / "pyproject.toml").write_text("[tool.ruff]\n")
        result = detect_lint_cmd(str(tmp_path))
        assert "ruff" in result

    def test_empty_directory_returns_empty_string(self, tmp_path):
        """Test empty directory returns empty string."""
        result = detect_lint_cmd(str(tmp_path))
        assert result == ""


# ---------------------------------------------------------------------------
# Helpers shared by TestVerificationResultEvent
# ---------------------------------------------------------------------------


def _run_hook(project_root, task_description, extra_env=None):
    """Run fbk.py task-completed with the given task_description payload.

    cwd is set to project_root so the hook resolves relative paths there and
    event_writer creates .fbk-capture/events.jsonl under that root.
    """
    env = {**os.environ}
    if extra_env:
        env.update(extra_env)

    payload = json.dumps({"task_description": task_description, "cwd": str(project_root)})

    return subprocess.run(
        [sys.executable, str(FBK_PY), "task-completed"],
        input=payload,
        cwd=str(project_root),
        capture_output=True,
        text=True,
        env=env,
    )


def _read_verification_events(project_root):
    """Return all VERIFICATION_RESULT events from <project_root>/.fbk-capture/events.jsonl."""
    events_path = os.path.join(str(project_root), ".fbk-capture", "events.jsonl")
    if not os.path.exists(events_path):
        return []
    events = []
    with open(events_path) as f:
        for line in f:
            line = line.strip()
            if line:
                obj = json.loads(line)
                if obj.get("event_type") == "VERIFICATION_RESULT":
                    events.append(obj)
    return events


def _build_failing_project(tmp_path):
    """Build a project fixture that forces a deterministic failing verification.

    Layout:
      - .fbk-capture/capture.cfg with capture_level=full
      - Makefile whose test: target exits 1
      - git init (so out-of-scope diff is computable)
      - Task file declaring a narrow scope (just one file)
      - An extra file modified outside that declared scope

    Returns (project_root, task_description_string).
    """
    project = capture_fixtures.make_project(tmp_path, instrumented=True, capture_cfg="full")

    # Makefile with failing test target.
    (Path(project) / "Makefile").write_text("test:\n\t@exit 1\n")

    # git init so the hook can compute out-of-scope diffs.
    subprocess.run(["git", "init"], cwd=project, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=project, capture_output=True, check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=project, capture_output=True, check=True,
    )

    # Task file declaring a narrow scope.
    feature = "myfeature"
    tasks_dir = Path(project) / "ai-docs" / feature / f"{feature}-tasks"
    tasks_dir.mkdir(parents=True)
    task_file = tasks_dir / "task-01-bootstrap.md"
    task_file.write_text(
        "---\nid: task-01\n---\n"
        "# Objective\nBootstrap.\n"
        "# Files to create/modify\n"
        "- `ai-docs/myfeature/myfeature-tasks/task-01-bootstrap.md`\n"
        "# Test requirements\nNone.\n"
    )

    # Initial commit so HEAD exists (required for git diff HEAD to work).
    subprocess.run(["git", "add", "."], cwd=project, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=project, capture_output=True, check=True,
    )

    # Modify a file outside the declared scope after the initial commit.
    out_of_scope = Path(project) / "out-of-scope.txt"
    out_of_scope.write_text("changed\n")
    subprocess.run(["git", "add", "out-of-scope.txt"], cwd=project, capture_output=True, check=True)

    task_description = (
        f"Task file: ai-docs/{feature}/{feature}-tasks/task-01-bootstrap.md\n"
        "Execute it."
    )
    return project, task_description


def _build_passing_project(tmp_path):
    """Build a project fixture where tests pass and all touched files are in scope.

    Returns (project_root, task_description_string).
    """
    project = capture_fixtures.make_project(tmp_path, instrumented=True, capture_cfg="full")

    # Makefile with passing test target.
    (Path(project) / "Makefile").write_text("test:\n\t@exit 0\n")

    # git init.
    subprocess.run(["git", "init"], cwd=project, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=project, capture_output=True, check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=project, capture_output=True, check=True,
    )

    feature = "myfeature"
    tasks_dir = Path(project) / "ai-docs" / feature / f"{feature}-tasks"
    tasks_dir.mkdir(parents=True)

    # The declared in-scope file (the task file itself and one source file).
    in_scope_file = Path(project) / "in-scope.txt"
    in_scope_file.write_text("original\n")

    task_file = tasks_dir / "task-01-bootstrap.md"
    task_file.write_text(
        "---\nid: task-01\n---\n"
        "# Objective\nBootstrap.\n"
        "# Files to create/modify\n"
        "- `ai-docs/myfeature/myfeature-tasks/task-01-bootstrap.md`\n"
        "- `in-scope.txt`\n"
        "# Test requirements\nNone.\n"
    )

    # Initial commit.
    subprocess.run(["git", "add", "."], cwd=project, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=project, capture_output=True, check=True,
    )

    # Modify only the declared in-scope file.
    in_scope_file.write_text("changed\n")
    subprocess.run(["git", "add", "in-scope.txt"], cwd=project, capture_output=True, check=True)

    task_description = (
        f"Task file: ai-docs/{feature}/{feature}-tasks/task-01-bootstrap.md\n"
        "Execute it."
    )
    return project, task_description


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    _event_writer_mod is None,
    reason="fbk.capture.event_writer not importable",
)
class TestVerificationResultEvent:
    """Verifies that task_completed writes a VERIFICATION_RESULT event as a
    fail-silent side effect before its existing exit.

    These tests fail in the red phase because the hook's main() does not yet
    write the event, and pass once the side-effect write is implemented.
    """

    def test_verification_event_written_on_failure(self, tmp_path):
        """Failing tests and an out-of-scope file produce a VERIFICATION_RESULT event;
        hook still exits 2 and the event carries a failing-test count >= 1 and the
        out-of-scope file path (present because the project runs at full level).
        """
        project, task_description = _build_failing_project(tmp_path)

        result = _run_hook(
            project,
            task_description,
            extra_env={"FBK_CAPTURE_LEVEL": "full"},
        )

        # Exit code is unchanged: failing tests → 2.
        assert result.returncode == 2, (
            f"expected hook to exit 2 on test failure, got {result.returncode}; "
            f"stderr: {result.stderr!r}"
        )

        events = _read_verification_events(project)
        assert len(events) >= 1, (
            "expected at least one VERIFICATION_RESULT event written to events.jsonl, "
            f"got {len(events)}"
        )

        event = events[0]
        data = event.get("data", {})

        # Failing-test count must be >= 1.
        failing_count = data.get("failing_test_count")
        assert failing_count is not None, (
            f"expected 'failing_test_count' key in event data, got: {data!r}"
        )
        assert failing_count >= 1, (
            f"expected failing_test_count >= 1, got {failing_count!r}"
        )

        # Lint-error count field must be present (value may be 0).
        assert "lint_error_count" in data, (
            f"expected 'lint_error_count' key in event data, got: {data!r}"
        )

        # Out-of-scope file list must be present and contain the touched-but-undeclared file.
        out_of_scope = data.get("out_of_scope_files")
        assert out_of_scope is not None, (
            f"expected 'out_of_scope_files' key in event data at full level, got: {data!r}"
        )
        assert isinstance(out_of_scope, list), (
            f"expected 'out_of_scope_files' to be a list, got {type(out_of_scope)!r}"
        )
        assert any("out-of-scope.txt" in f for f in out_of_scope), (
            f"expected 'out-of-scope.txt' in out_of_scope_files, got {out_of_scope!r}"
        )

    def test_verification_event_records_zero_failures_on_pass(self, tmp_path):
        """Passing tests and all touched files in declared scope produce a
        VERIFICATION_RESULT event with failing_test_count == 0 and an empty
        (present, not absent) out-of-scope list; hook exits 0.
        """
        project, task_description = _build_passing_project(tmp_path)

        result = _run_hook(
            project,
            task_description,
            extra_env={"FBK_CAPTURE_LEVEL": "full"},
        )

        # Exit code is unchanged: passing tests → 0.
        assert result.returncode == 0, (
            f"expected hook to exit 0 on passing tests, got {result.returncode}; "
            f"stderr: {result.stderr!r}"
        )

        events = _read_verification_events(project)
        assert len(events) >= 1, (
            "expected at least one VERIFICATION_RESULT event written to events.jsonl, "
            f"got {len(events)}"
        )

        event = events[0]
        data = event.get("data", {})

        # Failing-test count must be exactly 0.
        failing_count = data.get("failing_test_count")
        assert failing_count is not None, (
            f"expected 'failing_test_count' key in event data, got: {data!r}"
        )
        assert failing_count == 0, (
            f"expected failing_test_count == 0 on passing run, got {failing_count!r}"
        )

        # Out-of-scope list must be present and empty (not absent).
        assert "out_of_scope_files" in data, (
            f"expected 'out_of_scope_files' key present (empty list) in event data, got: {data!r}"
        )
        out_of_scope = data["out_of_scope_files"]
        assert isinstance(out_of_scope, list), (
            f"expected 'out_of_scope_files' to be a list, got {type(out_of_scope)!r}"
        )
        assert len(out_of_scope) == 0, (
            f"expected empty out_of_scope_files on in-scope-only run, got {out_of_scope!r}"
        )

        # Producer source-literal pin: task_completed must stamp exactly this name.
        assert event["source"] == "task_completed", (
            f"expected source == 'task_completed' (exact literal), got {event.get('source')!r}"
        )

    def test_verification_write_failure_is_silent(self, tmp_path):
        """An unwritable events path leaves the hook's exit code unchanged and
        produces no traceback in stderr — the write failure is swallowed.
        """
        # Build a passing project so exit-code comparison is against 0.
        project, task_description = _build_passing_project(tmp_path)

        # Make the capture dir an unwritable regular file so any write attempt fails.
        capture_dir = os.path.join(str(project), ".fbk-capture")
        # Remove the dir created by make_project (instrumented=True creates .claude/automation/).
        # make_project with capture_cfg writes .fbk-capture/capture.cfg; clear it.
        import shutil
        if os.path.isdir(capture_dir):
            shutil.rmtree(capture_dir)
        # Place a regular file where the capture dir would be so opens fail.
        with open(capture_dir, "w") as f:
            f.write("not a directory\n")
        os.chmod(capture_dir, 0o444)

        result_with_bad_path = _run_hook(
            project,
            task_description,
            extra_env={"FBK_CAPTURE_LEVEL": "full"},
        )

        # Also run a reference pass with a clean project to get the baseline exit code.
        project_ref, task_description_ref = _build_passing_project(
            tmp_path / "ref"
        )
        result_ref = _run_hook(
            project_ref,
            task_description_ref,
            extra_env={"FBK_CAPTURE_LEVEL": "full"},
        )

        # Exit code must match the no-capture run.
        assert result_with_bad_path.returncode == result_ref.returncode, (
            f"expected exit code {result_ref.returncode} with unwritable events path, "
            f"got {result_with_bad_path.returncode}"
        )

        # No Python traceback in stderr.
        assert "Traceback" not in result_with_bad_path.stderr, (
            f"expected no traceback in stderr on write failure, got: {result_with_bad_path.stderr!r}"
        )
