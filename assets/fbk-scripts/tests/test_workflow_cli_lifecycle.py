"""The shipped dispatcher, driven as a subprocess, completes a feature lifecycle.

Every other workflow test calls engine functions in-process. This one runs
``fbk.py`` the way a skill or hook does, with a fake ``claude`` executable on
PATH that asserts the host invocation contract, and then checks the persisted
record from the outside: file digests, the revision hash, lock and check
evidence, review provenance, and the agreement between close, status, and
report. Breakdown writes tasks only; implement runs the test task, the
``test-checkpoint`` command reviews and locks the tests, then the
implementation task and its refactor task run and implement closes. The fixture artifacts are script-authored; nothing here measures
model authoring quality.
"""

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

DISPATCHER = Path(__file__).resolve().parents[1] / "fbk.py"
UNIT = "cancellation"
SESSION = "cli-lifecycle"
TEST_NAMES = (
    "test_releases_once_and_returns_whether_cancellation_is_new",
    "test_failure_propagates_without_retry",
    "test_reentrant_callback_does_not_release_twice",
    "test_instances_do_not_share_state",
)

FAKE_HOST = f"""#!{sys.executable}
import json, sys
from pathlib import Path
sys.stdin.read()
assert '--safe-mode' in sys.argv and '--restricted' in sys.argv
assert '--bare' not in sys.argv
assert sys.argv[sys.argv.index('--setting-sources') + 1] == ''
schema = json.loads(sys.argv[sys.argv.index('--json-schema') + 1])
assert schema['required'] == [] and 'response' not in schema['properties']
assert not any(key in schema for key in ('anyOf', 'oneOf', 'allOf'))
assert {{'summary', 'findings', 'context', 'investigation'}} == set(schema['properties'])
paths = sorted(p for p in Path('.').rglob('*') if p.is_file())
assert not any(p.name == 'state.json' for p in paths)
for path in paths:
    path.read_bytes()
print(json.dumps({{'subtype': 'success', 'structured_output': {{
    'summary': 'Isolated fake review for dispatcher testing.', 'findings': [],
    'context': {{'status': 'complete', 'inspected_files': [p.as_posix() for p in paths],
                'supporting_files': [], 'missing_context': []}}}}}}))
"""

PRD = """# Cancel a job exactly once
## Commitments
### Cancel exactly once
A caller needs to cancel a job and release its held resource without duplicate releases when cancellation is repeated. Add a small synchronous Python Job object initialized with a callable release function. The first cancel returns True and calls release once; subsequent calls return False without calling release again. The cancelled property starts False and becomes True before release is called. If release raises, propagate that exception; cancellation remains recorded, so another cancel does not retry release. Independent jobs keep independent state.
This bounded validation task is authorized for implementation. Existing architecture is unchanged and a separate design document is unnecessary. No async work, threads, scheduling, retry policy, logging, or third-party dependencies are in scope. There are no unresolved product decisions. Acceptance is observable through callback invocations, return values, state, and exception propagation, with standard-library unittest tests. Document the synchronous contract and its limitations in README.md.
"""

SPEC = """# Synchronous cancellation contract
## Requirements
### Idempotent synchronous cancel
Serves [Cancel exactly once](prd.md#cancel-exactly-once).
`jobs.Job(release)` accepts a callable requiring no arguments; callers supply a callable, and constructor validation is out of scope. `cancelled` is initially False. `cancel()` marks this job cancelled before invoking release. On the first call it invokes release exactly once and returns True when release returns normally. Every subsequent call returns False, without invoking release. A release exception propagates unchanged from the first cancel; cancelled remains True and later calls return False without a retry. Separate jobs have separate cancellation state. Reentrant cancellation from the callback sees the cancelled state and returns False, preventing recursive release. There is no thread-safety or async guarantee.
Acceptance tests use real callbacks recording invocations, inspect the state inside a callback, check both return values over repeated calls, assert identity of a propagated exception and then verify cancelled remains True, a further cancel returns False, and release was called only once, exercise reentrant cancellation, and prove independent instances. A no-op cancel, a callback called twice, cancellation recorded after callback, swallowed exceptions, release retried after an exception, or class-level state must fail these tests. Run `python -m unittest discover -s tests -v` from the repository root. Only jobs.py, tests/test_jobs.py, and README.md are delivery files. No external dependencies or architectural changes are needed.
"""

STUB = (
    "class Job:\n"
    "    def __init__(self, release):\n"
    "        self.cancelled = False\n"
    "        self.release = release\n"
    "    def cancel(self):\n"
    "        return False\n"
)

TESTS = """import unittest
from jobs import Job

class JobTests(unittest.TestCase):
    def test_releases_once_and_returns_whether_cancellation_is_new(self):
        calls = []
        job = Job(lambda: calls.append(job.cancelled))
        self.assertFalse(job.cancelled)
        self.assertTrue(job.cancel())
        self.assertFalse(job.cancel())
        self.assertTrue(job.cancelled)
        self.assertEqual(calls, [True])

    def test_failure_propagates_without_retry(self):
        error = RuntimeError('release failed')
        calls = []
        def release():
            calls.append(1)
            raise error
        job = Job(release)
        with self.assertRaises(RuntimeError) as raised:
            job.cancel()
        self.assertIs(raised.exception, error)
        self.assertTrue(job.cancelled)
        self.assertFalse(job.cancel())
        self.assertEqual(calls, [1])

    def test_reentrant_callback_does_not_release_twice(self):
        nested = []
        job = Job(lambda: nested.append(job.cancel()))
        self.assertTrue(job.cancel())
        self.assertEqual(nested, [False])

    def test_instances_do_not_share_state(self):
        calls = []
        first = Job(lambda: calls.append('first'))
        second = Job(lambda: calls.append('second'))
        self.assertTrue(first.cancel())
        self.assertFalse(second.cancelled)
        self.assertTrue(second.cancel())
        self.assertEqual(calls, ['first', 'second'])
"""

IMPLEMENTATION = '''"""Synchronous, idempotent job cancellation; no thread-safety guarantee."""

class Job:
    def __init__(self, release):
        self._release = release
        self._cancelled = False

    @property
    def cancelled(self):
        return self._cancelled

    def cancel(self):
        if self._cancelled:
            return False
        self._cancelled = True
        self._release()
        return True
'''

README = """# Job cancellation
Construct `Job(release)` with a no-argument callback. `cancelled` starts false. The first `cancel()` marks the job cancelled, calls release, and returns true. Later calls return false without another release. Release exceptions propagate, but cancellation remains recorded and release is never retried. Reentrant cancellation also returns false. Each job owns its state. This object is synchronous and provides no thread-safety guarantee, scheduling, or async support. Run `python -m unittest discover -s tests -v` to verify the contract.
"""

PHASE_FILES = {
    "intent": [f".fbk/{UNIT}/prd.md"],
    "spec": [f".fbk/{UNIT}/spec.md", f".fbk/{UNIT}/scope.json"],
    "breakdown": [f".fbk/{UNIT}/tasks.json"],
    "implement": ["jobs.py", "tests/test_jobs.py", "README.md"],
}


def digests(root, paths):
    return {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in paths}


def record(root):
    return json.loads((root / f".fbk/{UNIT}/state.json").read_text())


@pytest.fixture(scope="module")
def lifecycle(tmp_path_factory):
    """Run the whole lifecycle once through the dispatcher; tests inspect the result."""
    base = tmp_path_factory.mktemp("cli-lifecycle")
    host = base / "bin"
    host.mkdir()
    (host / "claude").write_text(FAKE_HOST)
    (host / "claude").chmod(0o755)
    env = dict(os.environ, PATH=str(host) + os.pathsep + os.environ["PATH"])
    root = base / "project"
    root.mkdir()
    (root / ".git").mkdir()
    unit = root / ".fbk" / UNIT
    check = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]
    payloads = {}

    def run(*args):
        result = subprocess.run(
            [sys.executable, str(DISPATCHER), *args, "--root", str(root), "--session", SESSION],
            env=env, text=True, capture_output=True, check=False,
        )
        assert result.returncode == 0, f"{args[0]} failed: {result.stderr or result.stdout}"
        payload = json.loads(result.stdout)
        payloads[args[0]] = payload
        return payload

    def close(phase):
        payload = run("phase-close", phase, UNIT)
        assert payload["accepted_phase"] == phase
        payloads["phase-close:" + phase] = payload
        pending = next(p for p in payload["retrospective"]["pending"] if p["phase"] == phase)
        request = root / ".fbk/runtime/phase-observation.json"
        request.parent.mkdir(parents=True, exist_ok=True)
        request.write_text(json.dumps({
            "id": phase + "-scripted-observation",
            "detection_phase": phase,
            "observation": "Scripted fixture; records dispatcher behavior, not model authoring.",
            "evidence": [{"event_id": pending["event_id"]}],
        }))
        run("observation-record", UNIT, "--request", ".fbk/runtime/phase-observation.json")

    def finish_task(task, changed, *, red):
        result = subprocess.run(check, cwd=root, capture_output=True, text=True, check=False)
        assert result.returncode == (1 if red else 0), result.stderr
        path = f".fbk/runtime/{task}-result.json"
        (root / path).write_text(json.dumps({
            "changed_files": changed,
            "checks": [{"argv": check, "exit_code": result.returncode,
                        "stdout": result.stdout, "stderr": result.stderr,
                        "evidence": result.stdout + result.stderr}],
            "unresolved": [],
            "outcome": "Scripted task result.",
        }))
        run("task-finish", UNIT, task, "--result", path)

    run("workflow-init")
    run("unit-init", UNIT, "--design", "off")
    run("review-plan", UNIT, "--phase", "spec", "--mode", "single",
        "--reason", "The fixture operator chooses one independent spec reviewer.")

    run("phase-enter", "intent", UNIT)
    (unit / "prd.md").write_text(PRD)
    close("intent")

    run("phase-enter", "spec", UNIT)
    (unit / "spec.md").write_text(SPEC)
    (unit / "scope.json").write_text(json.dumps({
        "sources": ["jobs.py"], "tests": ["tests/test_jobs.py"],
        "docs": ["README.md"], "checks": [check],
        "creates": ["jobs.py", "tests/", "tests/test_jobs.py", "README.md"],
    }))
    close("spec")

    run("phase-enter", "breakdown", UNIT)
    refs = [f".fbk/{UNIT}/prd.md", f".fbk/{UNIT}/spec.md", f".fbk/{UNIT}/spec.md#idempotent-synchronous-cancel"]
    (unit / "tasks.json").write_text(json.dumps([
        {"id": "tests", "stage": "tests", "acceptance_refs": refs,
         "verification": "Real callback behavior rejects the no-op placeholder.",
         "check_expectations": [{"argv": check, "exit_code": 1}],
         "description": "Prove the contract with real callbacks against a placeholder Job; the check fails.",
         "files": ["tests/test_jobs.py", "jobs.py"], "depends_on": []},
        {"id": "code", "stage": "implementation", "acceptance_refs": refs,
         "input_refs": ["tests/test_jobs.py", *refs],
         "verification": "All locked tests pass unchanged; documentation matches.",
         "check_expectations": [{"argv": check, "exit_code": 0}],
         "description": "Implement the accepted contract and document it.",
         "files": ["jobs.py", "README.md"], "depends_on": ["tests"]},
        {"id": "refactor", "stage": "implementation", "refactor": True, "acceptance_refs": refs,
         "verification": "The structure improves and every locked test still passes.",
         "check_expectations": [{"argv": check, "exit_code": 0}],
         "description": "Refactor the code the implementation task built.",
         "files": ["jobs.py", "README.md"], "depends_on": ["code"]},
    ]))
    # Breakdown writes the tasks and closes; no test exists yet and nothing locks.
    close("breakdown")
    assert record(root)["locks"] == {}

    run("approve", UNIT, "start-implementation", "--phase", "implement",
        "--reason", "The fixture operator authorizes implementing the isolated fixture.")
    run("phase-enter", "implement", UNIT)
    run("task-start", UNIT, "tests", "--worker", "scripted-test-author")
    (root / "tests").mkdir()
    (root / "jobs.py").write_text(STUB)
    (root / "tests/test_jobs.py").write_text(TESTS)
    finish_task("tests", ["jobs.py", "tests/test_jobs.py"], red=True)
    run("test-checkpoint", UNIT)
    lock_before = record(root)["locks"]
    run("task-start", UNIT, "code", "--worker", "scripted-implementer")
    (root / "jobs.py").write_text(IMPLEMENTATION)
    (root / "README.md").write_text(README)
    finish_task("code", ["jobs.py", "README.md"], red=False)
    run("task-start", UNIT, "refactor", "--worker", "scripted-refactorer")
    finish_task("refactor", [], red=False)
    close("implement")

    run("status", UNIT)
    run("workflow-report", UNIT, "--history")
    return {"root": root, "payloads": payloads, "check": check, "lock_before": lock_before}


def assert_check(check, argv, *, red):
    """The fixture has four tests; anything but four named outcomes is not evidence."""
    assert check["argv"] == argv
    assert type(check["exit_code"]) is int and check["exit_code"] == (1 if red else 0)
    output = check.get("stdout", "") + "\n" + check.get("stderr", "")
    assert re.search(r"Ran 4 tests? in ", output)
    for name in TEST_NAMES:
        assert re.search(
            rf"^{name} \(test_jobs\.JobTests\.{name}\) \.\.\. {'FAIL' if red else 'ok'}$",
            output, re.MULTILINE,
        ), name
    assert re.search(r"^FAILED \(failures=4\)$" if red else r"^OK$", output, re.MULTILINE)


@pytest.mark.parametrize("phase", list(PHASE_FILES))
def test_each_phase_acceptance_is_bound_to_current_file_digests(lifecycle, phase):
    root = lifecycle["root"]
    state = record(root)
    work = state["phases"][phase]
    accepted = work["evidence"]
    assert accepted["outcome"] == "pass"
    assert not work.get("pending")

    paths, plans = [], {}
    for current, files in PHASE_FILES.items():
        paths.extend(files)
        if state.get("review_plans", {}).get(current):
            plans[current] = state["review_plans"][current]
        if current == phase:
            break
    expected = digests(root, paths)
    assert accepted["files"] == expected
    inputs = {"files": expected, "design": False, "parent": None}
    if plans:
        inputs["review_plans"] = plans
    revision = hashlib.sha256(
        json.dumps(inputs, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    assert accepted["revision"] == revision
    assert not accepted.get("grant_id"), "acceptance must not rest on an override grant"
    assert accepted.get("review_plan") == state.get("review_plans", {}).get(phase)


@pytest.mark.parametrize("phase", list(PHASE_FILES))
def test_each_phase_records_one_successful_single_review_round(lifecycle, phase):
    state = record(lifecycle["root"])
    work = state["phases"][phase]
    accepted = work["evidence"]
    result = accepted["review"]
    review = result["review"]
    assert result["shape"] == "single"
    assert not result.get("error") and not result.get("second_reader_failure")
    assert review["summary"].strip() and review["findings"] == []
    readers = result["readers"]
    assert len(readers) == 1 and readers[0]["review"] == review and not readers[0].get("error")
    rounds = work["rounds"]
    assert rounds[-1]["revision"] == accepted["revision"]
    assert rounds[-1]["result"] == result and not rounds[-1].get("error")

    closed = [e for e in state["events"] if e["event"] == "closed" and e.get("phase") == phase]
    attempts = [e for e in state["events"] if e["event"] == "close-attempt" and e.get("phase") == phase]
    assert closed[-1]["evidence"] == accepted
    assert attempts[-1]["revision"] == accepted["revision"] and not attempts[-1].get("error")
    assert attempts[-1].get("verification") == accepted.get("verification")

    response = lifecycle["payloads"]["phase-close:" + phase]
    assert response["review_shape"] == result["shape"]
    assert response["findings"] == review["findings"]


def test_checkpoint_lock_records_the_failing_behavioral_check(lifecycle):
    root, argv = lifecycle["root"], lifecycle["check"]
    state = record(root)
    expected = digests(root, ["tests/test_jobs.py"])
    assert state["locks"] == expected and state["unlocks"] == []
    assert state["locks"] == lifecycle["lock_before"], "implementation must not touch the lock"
    events = [e for e in state["events"] if e["event"] == "tests-locked"]
    assert len(events) == 1, "only the test checkpoint locks"
    assert events[0]["origin"] == "test-checkpoint"
    assert events[0]["files"] == expected and not events[0].get("preservation_reason")
    assert_check(events[0]["red_check"], argv, red=True)


def test_the_checkpoint_accepted_one_successful_review_with_its_red_check(lifecycle):
    state = record(lifecycle["root"])
    work = state["phases"]["test-checkpoint"]
    accepted = work["evidence"]
    assert accepted and accepted["outcome"] == "pass" and not work.get("pending")
    assert len(work["rounds"]) == 1 and not work["rounds"][-1].get("error")
    assert accepted["review"]["review"]["findings"] == []
    checks = accepted["verification"]
    assert len(checks) == 1
    assert_check(checks[0], lifecycle["check"], red=True)
    payload = lifecycle["payloads"]["test-checkpoint"]
    assert payload["findings"] == []


def test_declared_checks_run_red_at_the_checkpoint_and_green_at_implementation(lifecycle):
    state = record(lifecycle["root"])
    argv = lifecycle["check"]
    for phase in PHASE_FILES:
        checks = state["phases"][phase]["evidence"].get("verification", [])
        # Breakdown writes tasks only, so it runs no check.
        assert len(checks) == (1 if phase == "implement" else 0), phase
        if checks:
            assert_check(checks[0], argv, red=False)


def test_close_status_and_report_agree_on_the_persisted_record(lifecycle):
    root, payloads = lifecycle["root"], lifecycle["payloads"]
    state = record(root)
    assert state["open_phase"] is None and state["owner"] is None
    closed = payloads["phase-close:implement"]
    statuses, reports = payloads["status"], payloads["workflow-report"]
    assert len(statuses) == 1 and len(reports) == 1
    status, report = statuses[0], reports[0]
    assert status["unit"] == UNIT
    assert (status["phase"], status["status"]) == ("closed", "closed")
    assert status["owner"] is None and status["open_phase"] is None
    assert not status.get("close_in_progress") and not status.get("parent_problem")
    assert closed["status"] == "retrospective-required"
    assert not status.get("retrospective", {}).get("pending")
    assert all(closed.get(k) == v for k, v in status.items()
               if k not in {"status", "next", "retrospective"})
    assert report["unit"] == UNIT and report["status"] == status
    assert report["events"] == state["events"]
    assert report["review_rounds"] == {p: w["rounds"] for p, w in state["phases"].items()}
