"""Semantic reporting regressions using real shell and pytest subprocesses."""
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
from pathlib import Path
import shlex
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

SPEC = importlib.util.spec_from_file_location("fbk_test_runner", Path(__file__).resolve().parents[1] / "run-tests.py")
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def report(parent):
    directory, = parent.iterdir()
    return directory, json.loads((directory / "summary.json").read_text())


def shell(root, name, body, family="installer"):
    path = root / "tests" / family / ("test-" + name + ".sh")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    return path


def test_shell_failure_retains_evidence_and_runs_later_suite(tmp_path):
    root = tmp_path / "checkout with 'quotes'"
    shell(root, "fail", 'mkdir -p "$FBK_REPORT_DIR"\necho evidence > "$FBK_REPORT_DIR/fixture"\nprintf "not ok 1 - behavior\\n# expected: ready\\n# actual: missing\\n1..1\\n"\nexit 1\n')
    shell(root, "pass", 'printf "ok 1 - executed\\n1..1\\n"', "installer")
    parent = tmp_path / "reports"
    assert runner.run(root, ["installer"], parent) == 1
    directory, summary = report(parent)
    assert summary["counts"] == {"passed": 1, "failed": 1, "error": 0, "skipped": 0}
    failure = next(r for r in summary["results"] if r["status"] == "failed")
    assert "actual: missing" in failure["diagnostic"]
    assert failure["exit_code"] == 1
    assert (directory / "scratch/installer/fixture").read_text() == "evidence\n"
    assert all((directory / artifact).exists() for artifact in failure["artifacts"])
    assert shlex.split(failure["rerun"])[1] == str(root)
    retry = subprocess.run(failure["argv"], cwd=failure["cwd"], env={"FBK_REPORT_DIR": str(tmp_path / "retry")}, capture_output=True)
    assert retry.returncode == 1
    assert ET.parse(directory / "junit.xml").find(".//failure") is not None


@pytest.mark.parametrize("body,status", [
    ('printf "ok 1 - works\\n1..1\\n"', 0),
    ('printf "1..0 # SKIP unavailable optional integration\\n"', 0),
    ('printf "ok 1 - optional # SKIP unavailable\\n1..1\\n"', 0),
    ('printf "1..0\\n"', 2),
    ('printf "ok 1 - completed\\n1..2\\n"', 2),
    ('printf "ok 1 - completed\\n"', 2),
    ('printf "ok 1 - completed\\nBail out! fixture broke\\n1..1\\n"', 2),
    ('printf "ok 1 - completed\\n1..1\\n"; echo setup-broke >&2; exit 8', 2),
    ('printf "not ok 1 - rejected\\n1..2\\n"; exit 1', 2),
    ('printf "malformed\\n1..0\\n"', 2),
])
def test_shell_outcomes_and_plan_validation(tmp_path, body, status):
    shell(tmp_path, "case", body)
    parent = tmp_path / "reports"
    assert runner.run(tmp_path, ["installer"], parent) == status
    directory, summary = report(parent)
    if "SKIP" in body:
        assert summary["counts"]["skipped"] == 1
    if "setup-broke" in body:
        error = next(r for r in summary["results"] if r["status"] == "error")
        assert "setup-broke" in error["diagnostic"]
        assert error["exit_code"] == 8
        assert summary["counts"]["passed"] == 1
    assert (directory / "scratch").exists() == (status != 0)


def test_missing_suite_and_tool_are_errors(tmp_path):
    assert runner.run(tmp_path, ["installer"], tmp_path / "empty") == 2
    cwd = tmp_path / "assets/fbk-scripts"
    cwd.mkdir(parents=True)
    assert runner.run(tmp_path, ["python"], tmp_path / "missing", [str(tmp_path / "absent-tool")]) == 2
    _, summary = report(tmp_path / "missing")
    assert any("Unable to start" in r["diagnostic"] for r in summary["results"])


def test_setup_error_after_failed_check_is_not_hidden_by_failure(tmp_path):
    shell(tmp_path, "mixed", 'printf "not ok 1 - wrong result\\n1..1\\n"; echo fixture-failed >&2; exit 2')
    parent = tmp_path / "reports"
    assert runner.run(tmp_path, ["installer"], parent) == 2
    _, summary = report(parent)
    assert summary["counts"] == {"passed": 0, "failed": 1, "error": 1, "skipped": 0}
    assert "fixture-failed" in next(r["diagnostic"] for r in summary["results"] if r["status"] == "error")


def test_native_pytest_results_exact_nodeids_and_setup_errors(tmp_path):
    cwd = tmp_path / "assets/fbk-scripts"
    (cwd / "tests").mkdir(parents=True)
    (tmp_path / "tests/reporting").mkdir(parents=True)
    (cwd / "tests/test_workflow_sample.py").write_text('''import pytest
@pytest.fixture
def broken():
    raise RuntimeError("fixture unavailable")
def test_pass():
    assert True
@pytest.mark.parametrize("value", ["with 'quote' and space"], ids=["odd.id [quoted]"])
def test_failure(value):
    assert value == "expected"
def test_setup(broken):
    pass
@pytest.mark.skip(reason="optional dependency")
def test_skip():
    pass
@pytest.mark.xfail(reason="known issue")
def test_xfail():
    assert False
''')
    prefix = [sys.executable, "-m", "pytest"]
    assert runner.run(tmp_path, ["python"], tmp_path / "reports", prefix) == 2
    directory, summary = report(tmp_path / "reports")
    assert summary["counts"] == {"passed": 1, "failed": 1, "error": 1, "skipped": 2}
    assert summary["groups"][0]["name"] == "python/workflow"
    failure = next(r for r in summary["results"] if r["status"] == "failed")
    assert failure["nodeid"].endswith('test_failure[odd.id [quoted]]')
    assert failure["argv"][-1].split("::", 1)[1] == failure["nodeid"].split("::", 1)[1]
    retry = subprocess.run(failure["argv"], cwd=failure["cwd"], capture_output=True, text=True)
    assert retry.returncode == 1
    assert "1 failed" in retry.stdout
    assert "fixture unavailable" in next(r for r in summary["results"] if r["status"] == "error")["diagnostic"]
    assert (directory / "python/native.xml").exists()
    combined = ET.parse(directory / "junit.xml")
    assert len(combined.findall(".//error")) == 1
    assert len(combined.findall(".//skipped")) == 2


@pytest.mark.parametrize("xml", ["<broken", "<wrong/>", "<testsuite tests='0'/>", "<testsuite tests='2'><testcase name='one'/></testsuite>"])
def test_invalid_native_xml_cannot_pass(tmp_path, xml):
    path = tmp_path / "native.xml"
    path.write_text(xml)
    context = {"source": "assets/fbk-scripts/tests", "cwd": str(tmp_path), "group": "python/other"}
    results = runner.parse_junit(path, context, tmp_path, [sys.executable, "-m", "pytest"])
    assert any(r["status"] == "error" for r in results)


def test_concurrent_runs_never_clear_failed_artifacts(tmp_path):
    shell(tmp_path, "failure", 'printf "not ok 1 - bad\\n1..1\\n"; exit 1')
    parent = tmp_path / "reports"
    with ThreadPoolExecutor(max_workers=2) as executor:
        assert list(executor.map(lambda _: runner.run(tmp_path, ["installer"], parent), range(2))) == [1, 1]
    directories = list(parent.iterdir())
    assert len(directories) == 2
    assert all((p / "summary.json").exists() and (p / "scratch").exists() for p in directories)
    assert all(json.loads((p / "summary.json").read_text())["status"] == "failed" for p in directories)
