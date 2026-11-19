#!/usr/bin/env python3
"""Run ordinary suites and normalize native pytest JUnit and shell TAP reports."""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import json
import math
import os
from pathlib import Path
import re
import shlex
import signal
import shutil
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
STATUSES = ("passed", "failed", "error", "skipped")
PYTHON_TARGETS = ["tests", "../../tests/reporting"]
# Keep path/group policy here, independent of collection and product code.
PYTHON_FAMILIES = {
    "workflow": ("test_workflow",),
    "installer": ("test_install", "test_uninstall"),
    "review": ("test_cross_review",),
    "dispatcher": ("test_dispatcher",),
    "pipeline": ("test_pipeline",),
}
PLUGIN = '''def pytest_collection_modifyitems(items):
    for item in items:
        item.user_properties.extend([
            ("fbk_nodeid", item.nodeid),
            ("fbk_source", str(item.path)),
        ])
'''


def python_group(source):
    if "tests/reporting/" in source.replace("\\", "/"):
        return "reporting/infrastructure"
    for group, prefixes in PYTHON_FAMILIES.items():
        if Path(source).name.startswith(prefixes):
            return "python/" + group
    return "python/other"


def counts(results):
    observed = Counter(r["status"] for r in results)
    return {status: observed[status] for status in STATUSES}


def rerun(cwd, argv):
    return "cd " + shlex.quote(str(cwd)) + " && " + shlex.join(argv)


def record(context, name, status, diagnostic="", **extra):
    return {**context, "name": name, "status": status,
            "diagnostic": diagnostic, "duration_seconds": 0.0, **extra}


def process(argv, cwd, directory, env=None):
    directory.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    error = ""
    with (directory / "stdout.log").open("w") as stdout, (directory / "stderr.log").open("w") as stderr:
        try:
            child = subprocess.Popen(argv, cwd=cwd, env=env, stdout=stdout, stderr=stderr)
            try:
                rc = child.wait()
            except KeyboardInterrupt:
                child.terminate()
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
                rc = child.returncode
                error = "Runner interrupted during execution"
        except OSError as exc:
            rc = None
            error = f"Unable to start command: {exc}"
        if error:
            stderr.write(error + "\n")
    duration = time.monotonic() - start
    (directory / "command.json").write_text(json.dumps({
        "argv": argv, "cwd": str(cwd), "exit_code": rc,
        "duration_seconds": duration, "rerun": rerun(cwd, argv),
    }, indent=2) + "\n")
    return rc, duration, error


def parse_tap(text, context):
    results, problems, plans, numbers = [], [], [], []
    plan_after_rows = False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("TAP version"):
            continue
        if stripped.lower().startswith("bail out!"):
            problems.append(stripped)
            continue
        plan = re.fullmatch(r"1\.\.(\d+)(?:\s*#\s*(.*))?", stripped)
        if plan:
            plans.append((int(plan[1]), plan[2] or ""))
            plan_after_rows = bool(results)
            continue
        row = re.fullmatch(r"(not ok|ok)(?:\s+(\d+))?(?:\s+-?\s*(.*))?", stripped)
        if row:
            if plan_after_rows:
                problems.append("Assessment row appeared after the closing TAP plan")
            number = int(row[2]) if row[2] else len(numbers) + 1
            numbers.append(number)
            description = row[3] or f"assessment {number}"
            directive = re.search(r"\s*#\s*(SKIP|TODO)\b(.*)$", description, re.I)
            status = "passed" if row[1] == "ok" else "failed"
            diagnostic = ""
            if directive:
                status = "skipped"
                diagnostic = directive[1] + ": " + directive[2].strip()
            results.append(record(context, description, status, diagnostic, tap_number=number))
        elif stripped.startswith("#"):
            if results:
                results[-1]["diagnostic"] += ("\n" if results[-1]["diagnostic"] else "") + stripped[1:].strip()
        else:
            problems.append("Malformed TAP output: " + stripped)
    if len(plans) != 1:
        problems.append(f"Expected one TAP plan, found {len(plans)}")
    else:
        planned, reason = plans[0]
        if planned != len(numbers) or numbers != list(range(1, len(numbers) + 1)):
            problems.append(f"Inconsistent TAP plan: planned {planned}; row numbers {numbers}")
        if planned == 0:
            if re.match(r"SKIP\b", reason, re.I) and not numbers:
                results.append(record(context, "suite skipped", "skipped", reason))
            else:
                problems.append("Zero discovery: TAP plan contains no assessments or explicit skip")
    if problems:
        results.append(record(context, "TAP reporting error", "error", "\n".join(problems)))
    return results


def parse_junit(path, context, root, python_prefix):
    try:
        tree = ET.parse(path)
    except (OSError, ET.ParseError) as exc:
        return [record(context, "JUnit reporting error", "error", str(exc))]
    results = []
    xmlroot = tree.getroot()
    if xmlroot.tag not in ("testsuite", "testsuites"):
        return [record(context, "JUnit reporting error", "error", f"Unexpected root element: {xmlroot.tag}")]
    cases = list(xmlroot.iter("testcase"))
    for case in cases:
        props = {p.get("name"): p.get("value", "") for p in case.findall("properties/property")}
        source = props.get("fbk_source") or case.get("file") or context["source"]
        if source and Path(source).is_absolute():
            try:
                source = str(Path(source).relative_to(root))
            except ValueError:
                pass
        elif source != context["source"]:
            source = os.path.normpath(str(Path("assets/fbk-scripts") / source))
        nodeid = props.get("fbk_nodeid", "")
        if not nodeid and case.get("name", "").endswith(".py"):
            candidate = Path(context["cwd"]) / case.get("name")
            if candidate.is_file():
                source = os.path.relpath(candidate, root)
                nodeid = case.get("name")
        selector = os.path.relpath(root / source, context["cwd"]) + ("::" + nodeid.split("::", 1)[1] if "::" in nodeid else "")
        argv = [*python_prefix, "-vv", selector] if nodeid else [*python_prefix, "-vv", *PYTHON_TARGETS]
        statuses = [(tag, case.findall(tag)) for tag in ("error", "failure", "skipped")]
        status = "passed"
        diagnostic = []
        for tag, children in statuses:
            if children and status == "passed":
                status = {"failure": "failed", "error": "error", "skipped": "skipped"}[tag]
            for child in children:
                diagnostic.append("\n".join(filter(None, [child.get("message"), child.text])))
        for tag in ("system-out", "system-err"):
            diagnostic.extend(child.text or "" for child in case.findall(tag))
        try:
            duration = float(case.get("time", "0"))
            if not math.isfinite(duration) or duration < 0:
                raise ValueError("Invalid duration")
        except ValueError:
            duration = 0.0
            status = "error"
            diagnostic.append("Invalid JUnit duration")
        if not case.get("name"):
            status = "error"
            diagnostic.append("Malformed JUnit testcase: missing name")
        results.append(record(context, nodeid or case.get("name", "unnamed case"), status,
                              "\n".join(diagnostic), source=source,
                              group=python_group(source), argv=argv,
                              rerun=rerun(context["cwd"], argv), nodeid=nodeid,
                              duration_seconds=duration,
                              native_junit=ET.tostring(case, encoding="unicode")))
    if not cases:
        results.append(record(context, "Python discovery", "error", "Zero discovery: JUnit contains no test cases"))
    for suite in xmlroot.iter("testsuite"):
        native_cases = list(suite.iter("testcase"))
        try:
            # Pytest counts a failed teardown as an additional test in native XML.
            expected = sum(max(1, len(c.findall("error")) + len(c.findall("failure")) + len(c.findall("skipped"))) for c in native_cases)
            if "tests" in suite.attrib and int(suite.get("tests")) != expected:
                raise ValueError(f"JUnit suite declares {suite.get('tests')} tests but contains {expected} outcomes")
            for attr, tag in (("failures", "failure"), ("errors", "error"), ("skipped", "skipped")):
                if attr in suite.attrib and int(suite.get(attr)) != sum(len(c.findall(tag)) for c in native_cases):
                    raise ValueError(f"JUnit {attr} count does not match native outcomes")
        except ValueError as exc:
            results.append(record(context, "JUnit reporting error", "error", str(exc)))
    return results


def finish_process(results, context, rc, error, directory, kind):
    # pytest exit 1 represents test failures; 2..5 are execution/collection errors.
    if kind == "python":
        unexpected = rc not in (0, 1) or (rc == 1 and not any(r["status"] in ("failed", "error") for r in results))
    else:
        unexpected = rc not in (0, 1) or (rc == 1 and not any(r["status"] == "failed" for r in results))
    if error or unexpected:
        output = (directory / "stderr.log").read_text(errors="replace")[-12000:]
        if not output.strip():
            output = (directory / "stdout.log").read_text(errors="replace")[-12000:]
        results.append(record(context, "suite execution", "error", f"{error or 'Process exited unexpectedly'}; exit status {rc}\n{output}"))
    return results


def write_reports(directory, results, duration):
    groups = []
    for name in sorted({r["group"] for r in results}):
        members = [r for r in results if r["group"] == name]
        elapsed = sum(r["duration_seconds"] for r in members)
        if name.startswith("shell/"):
            # TAP does not measure individual rows. Count each suite's actual
            # wall time once instead of inventing equal durations for its rows.
            elapsed = sum(max(r.get("suite_duration_seconds", 0.0) for r in members if r["source"] == source)
                          for source in {r["source"] for r in members})
        groups.append({"name": name, "count_unit": "assessment_rows" if name.startswith("shell/") else "python_cases",
                       "counts": counts(members), "duration_seconds": elapsed})
    total = counts(results)
    code = 2 if total["error"] else 1 if total["failed"] else 0
    status = "error" if code == 2 else "failed" if code else "passed"
    xml = ET.Element("testsuites", tests=str(len(results)), failures=str(total["failed"]), errors=str(total["error"]), skipped=str(total["skipped"]), time=str(duration))
    for group in groups:
        tally = group["counts"]
        suite = ET.SubElement(xml, "testsuite", name=group["name"], tests=str(sum(tally.values())), failures=str(tally["failed"]), errors=str(tally["error"]), skipped=str(tally["skipped"]), time=str(group["duration_seconds"]))
        for result in (r for r in results if r["group"] == group["name"]):
            case = ET.SubElement(suite, "testcase", name=result["name"], classname=group["name"], file=result["source"], time=str(result["duration_seconds"]))
            if result.get("native_junit"):
                native = ET.fromstring(result["native_junit"])
                for child in native:
                    case.append(deepcopy(child))
            tag = {"failed": "failure", "error": "error", "skipped": "skipped"}.get(result["status"])
            if tag and case.find(tag) is None:
                ET.SubElement(case, tag, message=result["diagnostic"].split("\n")[0]).text = result["diagnostic"]
    ET.indent(xml)
    ET.ElementTree(xml).write(directory / "junit.xml", encoding="utf-8", xml_declaration=True)
    summary = {"schema_version": 1, "status": status, "duration_seconds": duration, "counts": total, "groups": groups,
               "results": [{k: v for k, v in r.items() if k != "native_junit"} for r in results],
               "scratch_directory": str(directory / "scratch") if code else None}
    (directory / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    markdown = [f"# Test result: {status}", "", "| Subsystem | Passed | Failed | Error | Skipped | Seconds |",
                "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for group in groups:
        markdown.append("| " + group["name"] + " | " + " | ".join(str(group["counts"][s]) for s in STATUSES)
                        + f" | {group['duration_seconds']:.2f} |")
    markdown += ["", "Python totals count cases; shell totals count assessment rows. Execution/reporting errors are additional records.",
                 "", f"Reports: `{directory}`. Detailed outcomes: `summary.json`; native logs and `junit.xml` are retained."]
    for result in results:
        if result["status"] in ("failed", "error"):
            markdown += ["", f"## {result['status']}: {result['source']} — {result['name']}", "",
                         "    " + result["diagnostic"][:2000].replace("\n", "\n    "), "",
                         "Rerun:", "", "    " + result["rerun"], "",
                         "Artifacts: " + ", ".join(result["artifacts"])]
    rendered = "\n".join(markdown) + "\n"
    (directory / "summary.md").write_text(rendered)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as stream:
            stream.write(rendered)
    for group in groups:
        print(f"{group['name']} ({group['count_unit']}): " + ", ".join(f"{s}={n}" for s, n in group["counts"].items()) + f"; {group['duration_seconds']:.2f}s")
    for result in results:
        if result["status"] in ("failed", "error"):
            print(f"\n{result['status'].upper()}: {result['source']} :: {result['name']}\n{result['diagnostic']}\nArtifacts: " + ", ".join(str(directory / a) for a in result["artifacts"]) + f"\nRerun: {result['rerun']}")
    print(f"\nOverall: {status}; reports: {directory}")
    return code


def run(root, suites, output_parent, python_prefix=None):
    root = Path(root).resolve()
    output_parent = Path(output_parent).resolve()
    output_parent.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="run-", dir=output_parent))
    scratch = directory / "scratch"
    scratch.mkdir()
    results = []
    start = time.monotonic()
    python_prefix = python_prefix or ["uv", "run", "python", "-m", "pytest"]
    for kind in suites:
        if kind == "python":
            jobs = [("python/other", "assets/fbk-scripts/tests", root / "assets/fbk-scripts", [*python_prefix, "-q", *PYTHON_TARGETS])]
        else:
            jobs = [("shell/" + kind, str(p.relative_to(root)), root, ["bash", str(p.relative_to(root))]) for p in sorted((root / "tests" / kind).glob("test-*.sh"))]
        if not jobs:
            argv = ["python3", str(ROOT / "tests/run-tests.py"), "--suite", kind]
            context = {"group": "shell/" + kind, "source": f"tests/{kind}", "cwd": str(root), "argv": argv,
                       "rerun": rerun(root, argv), "exit_code": None, "artifacts": []}
            results.append(record(context, "suite discovery", "error", "Zero discovery: no test-*.sh files found"))
        for group, source, cwd, argv in jobs:
            logdir = directory / ("python" if kind == "python" else f"shell/{kind}/{Path(source).stem}")
            env = dict(os.environ)
            env["FBK_REPORT_DIR"] = str(scratch / kind)
            if kind == "python":
                logdir.mkdir(parents=True, exist_ok=True)
                (logdir / "fbk_report_nodeids.py").write_text(PLUGIN)
                env["PYTHONPATH"] = str(logdir) + os.pathsep + env.get("PYTHONPATH", "")
                argv += ["--junitxml", str(logdir / "native.xml"), "-o", "junit_family=xunit1", "--basetemp", str(scratch / "pytest"), "-p", "fbk_report_nodeids"]
            rc, duration, error = process(argv, cwd, logdir, env)
            rerun_argv = [*python_prefix, "-vv", *PYTHON_TARGETS] if kind == "python" else argv
            context = {"group": group, "source": source, "cwd": str(cwd), "argv": rerun_argv,
                       "rerun": rerun(cwd, rerun_argv), "exit_code": rc,
                       "artifacts": [str(p.relative_to(directory)) for p in sorted(logdir.iterdir()) if p.is_file()] + ["scratch"]}
            if kind == "python":
                parsed = parse_junit(logdir / "native.xml", context, root, python_prefix)
            else:
                parsed = parse_tap((logdir / "stdout.log").read_text(errors="replace"), context)
                for result in parsed:
                    result["suite_duration_seconds"] = duration
            results.extend(finish_process(parsed, context, rc, error, logdir, kind))
    if not any(r["status"] in ("failed", "error") for r in results):
        shutil.rmtree(scratch)
        for result in results:
            result["artifacts"] = [p for p in result["artifacts"] if p != "scratch"]
    return write_reports(directory, results, time.monotonic() - start)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", action="append", choices=("python", "installer", "lint"))
    parser.add_argument("--output-dir", type=Path, default=ROOT / "test-results")
    args = parser.parse_args()
    def interrupted(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    return run(ROOT, list(dict.fromkeys(args.suite or ["python", "installer", "lint"])), args.output_dir)


if __name__ == "__main__":
    raise SystemExit(main())
