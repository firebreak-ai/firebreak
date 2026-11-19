"""pytest plugin for testq.py: writes each test's outcome to the file named by TESTQ_OUT (JSON).
{"tests": {nodeid: "passed" | exception type of the failure}, "collect": {file or node that failed to collect: exception type}}"""
import json, os

_out = {"tests": {}, "collect": {}}


def _kind(report):
    crash = getattr(getattr(report, "longrepr", None), "reprcrash", None)
    return (crash.message.split(":")[0].split(".")[-1].strip() if crash and crash.message else "") or "failed"


def pytest_collectreport(report):
    if report.failed:
        _out["collect"][report.nodeid] = _kind(report)


def pytest_runtest_logreport(report):
    if report.failed:
        _out["tests"][report.nodeid] = _kind(report)
    elif report.when == "call" and report.passed:
        _out["tests"].setdefault(report.nodeid, "passed")
    elif report.skipped:
        _out["tests"].setdefault(report.nodeid, "skipped")


def pytest_sessionfinish(session):
    if os.environ.get("TESTQ_OUT"):
        with open(os.environ["TESTQ_OUT"], "w") as f:
            json.dump(_out, f)
