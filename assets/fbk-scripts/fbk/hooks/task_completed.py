"""TaskCompleted hook: validates per-task prerequisites for SDL workflow tasks."""

import glob
import json
import os
import re
import subprocess
import sys


def detect_test_cmd(directory: str) -> str:
    """Detect the test runner command for a given directory.

    Checks for marker files and returns the appropriate test command string,
    or an empty string if no recognized test runner is found.
    """
    d = directory
    if os.path.isfile(os.path.join(d, "package.json")):
        return "npm test"
    if os.path.isfile(os.path.join(d, "Cargo.toml")):
        return "cargo test"
    if os.path.isfile(os.path.join(d, "go.mod")):
        return "go test ./..."
    if os.path.isfile(os.path.join(d, "pytest.ini")):
        return "python -m pytest"
    pyproject = os.path.join(d, "pyproject.toml")
    if os.path.isfile(pyproject):
        try:
            content = open(pyproject).read()
            if "[tool.pytest" in content:
                return "python -m pytest"
        except OSError:
            pass
    makefile = os.path.join(d, "Makefile")
    if os.path.isfile(makefile):
        try:
            content = open(makefile).read()
            if re.search(r"^test:", content, re.MULTILINE):
                return "make test"
        except OSError:
            pass
    return ""


def detect_lint_cmd(directory: str) -> str:
    """Detect the linter command for a given directory.

    Checks for linter config files and returns the appropriate lint command
    string, or an empty string if no recognized linter is found.
    """
    d = directory
    if glob.glob(os.path.join(d, ".eslintrc*")):
        return "npx eslint ."
    pyproject = os.path.join(d, "pyproject.toml")
    if os.path.isfile(pyproject):
        try:
            content = open(pyproject).read()
            if "[tool.ruff]" in content:
                return "ruff check ."
            if "[tool.flake8]" in content:
                return "flake8 ."
        except OSError:
            pass
    if os.path.isfile(os.path.join(d, "Cargo.toml")):
        return "cargo clippy"
    if os.path.isfile(os.path.join(d, ".golangci.yml")) or os.path.isfile(
        os.path.join(d, ".golangci.yaml")
    ):
        return "golangci-lint run"
    return ""


def _extract_declared_files(task_file_path: str) -> list[str]:
    """Extract declared file paths from the Files to create/modify section."""
    try:
        content = open(task_file_path).read()
    except OSError:
        return []

    declared = []
    in_section = False
    for line in content.splitlines():
        if re.match(r"^#{1,3} Files to.*create.*modify", line, re.IGNORECASE):
            in_section = True
            continue
        if in_section:
            if re.match(r"^#+ ", line):
                break
            matches = re.findall(r"`([^`]+)`", line)
            declared.extend(matches)
    return sorted(set(declared))


TASK_PATH_PATTERN = r"ai-docs/\S+?/\S*tasks/task-\S*\.md"


def count_test_failures(test_cmd: str, output: str) -> int:
    """Return the number of failing tests parsed from a runner's output.

    Keyed on the detected runner so the summary line is parsed in the right
    format.  Always returns at least 1 when called (this is only invoked after a
    non-zero exit), so a real failure is never under-reported as zero even when
    the summary cannot be parsed.
    """
    patterns = {
        "python -m pytest": r"(\d+)\s+failed",
        "npm test": r"(\d+)\s+(?:failing|failed)",
        "cargo test": r";\s*(\d+)\s+failed",
        "make test": r"(\d+)\s+(?:failing|failed)",
    }
    pat = patterns.get(test_cmd)
    if pat:
        matches = re.findall(pat, output)
        if matches:
            return max(int(m) for m in matches)
    if test_cmd == "go test ./...":
        # go prints one "--- FAIL" line per failing test.
        fail_lines = re.findall(r"^--- FAIL", output, re.MULTILINE)
        if fail_lines:
            return len(fail_lines)
    return 1


def count_lint_errors(lint_cmd: str, output: str) -> int:
    """Return the number of lint errors parsed from a linter's output.

    Always returns at least 1 when called (only invoked after a non-zero exit),
    so a real lint failure is never under-reported as zero when the summary
    cannot be parsed.
    """
    patterns = {
        "ruff check .": r"Found (\d+) error",
        "npx eslint .": r"\d+\s+problems?\s+\((\d+)\s+error",
    }
    pat = patterns.get(lint_cmd)
    if pat:
        m = re.search(pat, output)
        if m:
            return int(m.group(1))
    # Generic fallback: a "(\d+) errors" summary if the linter printed one.
    m = re.search(r"(\d+)\s+errors?\b", output)
    if m:
        return int(m.group(1))
    return 1


def main() -> None:
    data = json.load(sys.stdin)

    task_description = data.get("task_description", "")
    cwd = data.get("cwd", ".")

    match = re.search(TASK_PATH_PATTERN, task_description)
    if not match:
        sys.exit(0)

    task_file = match.group(0)
    if not os.path.isabs(task_file):
        task_file = os.path.join(cwd, task_file)

    failures = []
    failing_test_count = 0
    lint_error_count = 0

    test_cmd = detect_test_cmd(cwd)
    if not test_cmd:
        print("[WARN] No recognized test runner; skipping test suite check.", file=sys.stderr)
    else:
        result = subprocess.run(test_cmd, shell=True, cwd=cwd, capture_output=True, text=True)
        if result.returncode != 0:
            output = (result.stdout + result.stderr).strip()
            failures.append(f"TEST SUITE FAILED:\n{output}")
            failing_test_count = count_test_failures(test_cmd, output)

    lint_cmd = detect_lint_cmd(cwd)
    if not lint_cmd:
        print("[WARN] No recognized linter; skipping lint check.", file=sys.stderr)
    else:
        result = subprocess.run(lint_cmd, shell=True, cwd=cwd, capture_output=True, text=True)
        if result.returncode != 0:
            output = (result.stdout + result.stderr).strip()
            failures.append(f"LINT ERRORS:\n{output}")
            lint_error_count = count_lint_errors(lint_cmd, output)

    out_of_scope_files: list = []
    if os.path.isfile(task_file):
        declared_files = _extract_declared_files(task_file)
        if declared_files:
            git_check = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=cwd,
                capture_output=True,
            )
            if git_check.returncode == 0:
                diff_result = subprocess.run(
                    ["git", "diff", "--name-only", "HEAD"],
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                )
                modified = sorted(diff_result.stdout.splitlines())
                if modified:
                    undeclared = [f for f in modified if f not in declared_files]
                    if undeclared:
                        out_of_scope_files = undeclared
                        task_basename = os.path.basename(task_file)
                        print(
                            f"[WARN] Task {task_basename} modified files outside declared scope:\n"
                            + "\n".join(undeclared),
                            file=sys.stderr,
                        )

    verification_data = {
        "failing_test_count": failing_test_count,
        "lint_error_count": lint_error_count,
        "out_of_scope_files": out_of_scope_files,
        "tests_passed": failing_test_count == 0 and lint_error_count == 0,
    }

    def _write_verification_event():
        try:
            # Imported inside the guard so a broken or absent capture install
            # cannot crash the verification hook — capture is fail-silent.
            from fbk.capture import active_stage, event_writer, gate_check

            level = gate_check.resolve_capture_level(cwd)
            events_path = os.path.join(cwd, ".fbk-capture", "events.jsonl")
            # Stamp the active spec/stage so the report can attribute this
            # gate attempt to the stage that produced it (a null stage row
            # would never match the report's per-stage gate-rate filter).
            spec, stage = active_stage.resolve_active_stage(cwd)
            event_writer.write(
                "VERIFICATION_RESULT",
                "task_completed",
                verification_data,
                spec,
                stage,
                level,
                events_path,
            )
        except Exception:
            pass

    if failures:
        print("TaskCompleted validation failed:\n", file=sys.stderr)
        for f in failures:
            print(f + "\n", file=sys.stderr)
        _write_verification_event()
        sys.exit(2)

    _write_verification_event()
    sys.exit(0)


if __name__ == "__main__":
    main()
