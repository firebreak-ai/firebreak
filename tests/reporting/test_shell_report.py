"""The reporting helper preserves evidence without changing command semantics."""

import os
import importlib.util
from pathlib import Path
import subprocess


HELPER = Path(__file__).resolve().parents[1] / "lib/test-report.sh"


def run_suite(tmp_path, body):
    suite = tmp_path / "suite.sh"
    suite.write_text(
        'set -uo pipefail\nsource "$1"\nfbk_test_init "$0"\n' + body
    )
    return subprocess.run(
        ["bash", str(suite), str(HELPER)],
        env={**os.environ, "FBK_REPORT_DIR": str(tmp_path / "reports")},
        capture_output=True,
        text=True,
    )


def test_failing_command_keeps_streams_status_and_fixture(tmp_path):
    result = run_suite(tmp_path, '''
echo fixture > "$TMPDIR/fixture.txt"
fbk_run "negative command" bash -c 'echo actual; echo reason >&2; exit 7'
exit "$?"
''')
    assert result.returncode == 7
    assert result.stdout == "actual\n"
    assert "reason" in result.stderr
    scratch, = (tmp_path / "reports").iterdir()
    command, = (scratch / "commands").iterdir()
    assert (command / "exit-code.txt").read_text() == "7\n"
    assert (command / "stdout.txt").read_text() == "actual\n"
    assert (command / "stderr.txt").read_text() == "reason\n"
    assert (scratch / "tmp/fixture.txt").read_text() == "fixture\n"


def test_expected_negative_command_does_not_fail_suite(tmp_path):
    result = run_suite(tmp_path, '''
if fbk_run "expected rejection" bash -c 'exit 3'; then exit 1; fi
exit 0
''')
    assert result.returncode == 0, result.stderr
    assert list((tmp_path / "reports").iterdir()) == []


def test_failed_assertion_cannot_exit_successfully(tmp_path):
    result = run_suite(tmp_path, 'FAIL=1\necho fixture > "$TMPDIR/evidence"\nexit 0\n')
    assert result.returncode == 1
    scratch, = (tmp_path / "reports").iterdir()
    assert (scratch / "tmp/evidence").read_text() == "fixture\n"


def test_concurrent_suites_keep_distinct_artifacts(tmp_path):
    suite = tmp_path / "suite.sh"
    suite.write_text('''set -uo pipefail
source "$1"
fbk_test_init "$0"
fbk_run "write evidence" echo "$2"
echo "$2" > "$TMPDIR/evidence"
exit 1
''')
    children = [
        subprocess.Popen(
            ["bash", str(suite), str(HELPER), label],
            env={**os.environ, "FBK_REPORT_DIR": str(tmp_path / "reports")},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for label in ("first", "second")
    ]
    for child in children:
        child.communicate(timeout=10)
        assert child.returncode == 1
    assert sorted(
        p.read_text() for p in (tmp_path / "reports").glob("*/tmp/evidence")
    ) == ["first\n", "second\n"]


def test_multiline_failure_diagnostics_remain_valid_tap(tmp_path):
    result = run_suite(tmp_path, '''
echo 'TAP version 13'
echo 'not ok 1 - returned unexpected records'
fbk_diag $'wrong output\\nsecond line' 'one record' $'two records\\nwith details'
echo '1..1'
FAIL=1
exit 1
''')
    spec = importlib.util.spec_from_file_location("report_runner", HELPER.parents[1] / "run-tests.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    records = runner.parse_tap(result.stdout, {})
    assert result.returncode == 1
    assert [r["status"] for r in records] == ["failed"]
    assert "with details" in records[0]["diagnostic"]
