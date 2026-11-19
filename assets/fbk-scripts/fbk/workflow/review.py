"""Read-only headless review and real verification commands with bounded execution."""

import copy
import functools
import hashlib
import json
import os
import shutil
import signal
import subprocess
import time
import uuid
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from .evidence import CHECKPOINT
from .review_plan import MEMBERS
from .store import WorkflowError, confined, event, ignore_everything, load, now, project_config, save, transaction
from .review_context import (
    additional_supporting,
    CONTEXT_SCHEMA,
    convention_paths,
    executable_paths,
    incomplete_context,
    captured_symlinks,
    listing_inputs,
    incomplete_message,
    snapshot,
    validate_context,
)

REMEDY_KINDS = ("artifact", "test", "code", "documentation")

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string", "minLength": 1, "maxLength": 1500},
        "findings": {
            "type": "array",
            "maxItems": 8,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    k: {"type": "string", "minLength": 1, "maxLength": limit}
                    for k, limit in {
                        "title": 180,
                        "location": 300,
                        "evidence": 1500,
                        "remedy": 1000,
                    }.items()
                }
                | {
                    "severity": {"enum": ["blocker", "suggestion"]},
                    "remedy_kind": {"enum": list(REMEDY_KINDS)},
                },
                "required": ["title", "location", "evidence", "remedy", "severity"],
            },
        },
    },
    "required": ["summary", "findings"],
}


VERDICTS = ("met", "not met")
ASSESSMENT_LIMITS = {"evidence": 1500, "remedy": 1000}


def assessments_schema(requirements):
    """The requirement_assessments array: one verdict for each review-only requirement."""
    return {
        "type": "array",
        "minItems": len(requirements),
        "maxItems": len(requirements),
        "items": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "requirement": {"enum": list(requirements)},
                "verdict": {"enum": list(VERDICTS)},
                **{k: {"type": "string", "minLength": 1, "maxLength": limit}
                   for k, limit in ASSESSMENT_LIMITS.items()},
            },
            "required": ["requirement", "verdict", "evidence"],
        },
    }


def requirement_contract(requirements):
    """The implementation review's schema when the unit has review-only requirements."""
    schema = copy.deepcopy(SCHEMA)
    schema["properties"]["requirement_assessments"] = assessments_schema(requirements)
    schema["required"] = [*schema["required"], "requirement_assessments"]
    return schema


def validate_assessments(items, requirements):
    """Refuse requirement assessments that miss, repeat or invent a review-only requirement,
    or whose entry is malformed, naming the problem."""
    if not isinstance(items, list):
        # constraint: requirement-assessments-complete
        raise WorkflowError(
            "requirement_assessments must be an array with one assessment for each review-only requirement: "
            + ", ".join(requirements) + "."
        )
    seen = []
    for item in items:
        name = item.get("requirement") if isinstance(item, dict) else None
        label = f"The requirement assessment for {name}" if isinstance(name, str) else "A requirement assessment"
        if not isinstance(name, str) or not name.strip():
            # constraint: requirement-assessment-fields
            raise WorkflowError(f"{label} has no requirement; name the review-only requirement it assesses.")
        if set(item) - {"remedy"} != {"requirement", "verdict", "evidence"}:
            # constraint: requirement-assessment-fields
            raise WorkflowError(
                f"{label} must carry exactly requirement, verdict, and evidence, plus remedy when not met; "
                f"it carries {', '.join(sorted(item))}."
            )
        if item["verdict"] not in VERDICTS:
            # constraint: requirement-assessment-fields
            raise WorkflowError(f"{label} has verdict {item['verdict']!r}; the verdict is met or not met.")
        for field in ("evidence", *(("remedy",) if item["verdict"] == "not met" or "remedy" in item else ())):
            value = item.get(field)
            if not isinstance(value, str) or not value.strip():
                # constraint: requirement-assessment-fields
                raise WorkflowError(
                    f"{label} needs a nonempty {field}"
                    + (" because its verdict is not met." if field == "remedy" else ".")
                )
            if len(value) > ASSESSMENT_LIMITS[field]:
                # constraint: length-budgets
                raise WorkflowError(f"{label} has a {field} over {ASSESSMENT_LIMITS[field]} characters.")
        seen.append(name)
    unknown = sorted({name for name in seen if name not in requirements})
    repeated = sorted({name for name in seen if seen.count(name) > 1})
    missing = [name for name in requirements if name not in seen]
    if unknown or repeated or missing:
        problems = [f"{label}: {', '.join(names)}" for label, names in (
            ("not a review-only requirement of this unit", unknown),
            ("assessed more than once", repeated),
            ("not assessed", missing),
        ) if names]
        # constraint: requirement-assessments-complete
        raise WorkflowError(
            "requirement_assessments must assess each review-only requirement exactly once; "
            + "; ".join(problems) + "."
        )
    return items


# The most findings any review result holds: the council's limit, every proposal that can stand.
RESULT_FINDING_LIMIT = 33


def validate_review(data, requirements=()):
    """A reader's review; with review-only requirements it also carries their assessments."""
    expected = {"summary", "findings", *(("requirement_assessments",) if requirements else ())}
    if not isinstance(data, dict) or set(data) != expected:
        # constraint: response-properties
        raise WorkflowError(
            "Review did not return a complete summary and findings object."
            if not requirements else
            "Review did not return exactly summary, findings, and requirement_assessments, with one "
            "assessment for each review-only requirement."
        )
    if (
        not isinstance(data["summary"], str)
        or not data["summary"].strip()
        or not isinstance(data["findings"], list)
    ):
        # constraint: summary-nonempty
        raise WorkflowError(
            "Review summary must be nonempty and findings must be an array."
        )
    required = {"title", "location", "evidence", "remedy", "severity"}
    for item in data["findings"]:
        if (
            not isinstance(item, dict)
            or set(item) - {"remedy_kind"} != required
            or any(
                not isinstance(v, str) or not v.strip()
                for k, v in item.items()
                if k != "remedy_kind"
            )
            or item["severity"] not in {"blocker", "suggestion"}
        ):
            # constraint: finding-fields
            raise WorkflowError(
                "Review finding needs a severity, location, concrete evidence, and remedy."
            )
        kind = item.get("remedy_kind", "artifact")
        if not isinstance(kind, str) or kind not in REMEDY_KINDS:
            # constraint: remedy-kind
            raise WorkflowError(
                "Review finding remedy_kind must be one of artifact, test, code, or "
                "documentation; omit it for an artifact remedy."
            )
    if (
        len(data["summary"]) > 1500
        or len(data["findings"]) > RESULT_FINDING_LIMIT
        or any(
            len(f[k]) > limit
            for f in data["findings"]
            for k, limit in {
                "title": 180,
                "location": 300,
                "evidence": 1500,
                "remedy": 1000,
            }.items()
        )
    ):
        # constraint: length-budgets
        raise WorkflowError("Review exceeded the bounded finding format.")
    if requirements:
        # constraint: requirement-assessments-complete
        # constraint: requirement-assessment-fields
        validate_assessments(data["requirement_assessments"], requirements)
    return data


def validate_single(data, requirements=()):
    validate_review(data, requirements)
    if len(data["findings"]) > 8:
        # constraint: length-budgets
        raise WorkflowError("Review exceeded the bounded finding format.")
    return data


_COMMAND_CONTEXT = threading.local()
_COMMAND_GROUPS = {}
_COMMAND_LOCK = threading.RLock()


@contextmanager
def command_scope(root):
    previous = getattr(_COMMAND_CONTEXT, "root", None)
    _COMMAND_CONTEXT.root = str(Path(root).resolve())
    try:
        yield
    finally:
        _COMMAND_CONTEXT.root = previous


def outstanding_command_groups(root):
    root = Path(root).resolve()
    with _COMMAND_LOCK:
        return sorted(pid for pid, owner in _COMMAND_GROUPS.items()
                      if Path(owner).is_relative_to(root))


def cancel_command_groups(root):
    # Cancellation requests do not remove registry entries: the executing thread
    # must still reap and confirm termination before its clock can become idle.
    for group in outstanding_command_groups(root):
        try:
            os.killpg(group, signal.SIGKILL)
        except OSError:
            pass


def release_stopped_command_groups(groups):
    for group in groups:
        if not _process_group_running(group):
            with _COMMAND_LOCK:
                _COMMAND_GROUPS.pop(group, None)


def _process_group_running(group):
    try:
        os.killpg(group, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    # Linux can retain orphaned zombie grandchildren until their new parent
    # reaps them. Zombies cannot execute or write and must not be mistaken for
    # live workers. Other platforms conservatively await disappearance.
    proc = Path("/proc")
    if not proc.is_dir():
        return True
    try:
        for path in proc.iterdir():
            if not path.name.isdigit():
                continue
            try:
                fields = (path / "stat").read_text().rsplit(")", 1)[1].split()
                if int(fields[2]) == group and fields[0] not in {"Z", "X"}:
                    return True
            except FileNotFoundError:
                continue
            except (OSError, ValueError, IndexError):
                return True  # Incomplete process inspection is not confirmation.
    except OSError:
        return True
    return False


def _stop_process_group(process):
    """Bounded cancellation and confirmation, including descendants of an exited leader."""
    try:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=2)
        for _ in range(100):
            if not _process_group_running(process.pid):
                return True
            time.sleep(.01)
    except BaseException:  # noqa: BLE001 - an interrupt here is an outcome to report, not to pass on
        # A second interrupt or failed kill must leave reconciliation required.
        return False
    return False


def run_command(argv, root, timeout, prompt=None, save_to=None):
    """Run one command in its own process group. The result keeps the last MiB of each
    stream. save_to, a directory descriptor and a file name per stream, also publishes
    each stream whole there and records the fingerprint of the captured bytes."""
    started = time.monotonic()
    failure = None
    interrupted = None
    timed_out = False
    process = None
    stopped = True
    stdout_file = tempfile.TemporaryFile(mode="w+b")  # noqa: SIM115 - closed in the finally block, after the process is stopped
    stderr_file = tempfile.TemporaryFile(mode="w+b")  # noqa: SIM115 - closed in the finally block, after the process is stopped
    try:
        process = subprocess.Popen(
            argv, cwd=root, stdin=subprocess.PIPE, text=True,
            stdout=stdout_file, stderr=stderr_file, start_new_session=True,
            env={k: v for k, v in os.environ.items() if k != "CLAUDECODE"},
        )
        with _COMMAND_LOCK:
            _COMMAND_GROUPS[process.pid] = (getattr(_COMMAND_CONTEXT, "root", None)
                                            or str(Path(root).resolve()))
        process.communicate(input=prompt, timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
    except OSError as exc:
        # A command that never started is a setup error, never a failing result.
        failure = WorkflowError(
            f"Command {argv[0]} could not be run: {exc}. Check that it is installed, "
            "executable, and named correctly, then retry."
            if process is None else f"Command failed: {argv[0]}: {exc}"
        )
    except BaseException as exc:  # noqa: BLE001 - held until the process group is stopped, then raised again
        interrupted = exc
    finally:
        if process is not None:
            stopped = _stop_process_group(process)
            if stopped:
                with _COMMAND_LOCK:
                    _COMMAND_GROUPS.pop(process.pid, None)
        captured = {}
        for name, stream in (("stdout", stdout_file), ("stderr", stderr_file)):
            if save_to:
                captured.setdefault("saved_sha256", {})[name] = _publish(stream, *save_to, name)
            size = stream.seek(0, 2)
            stream.seek(max(0, size - 1024 * 1024))
            captured[name] = stream.read().decode("utf-8", errors="replace")
            captured[name + "_omitted_bytes"] = max(0, size - 1024 * 1024)
            stream.close()
    result = {"argv": argv, "exit_code": process.returncode if process else None,
              **captured, "seconds": round(time.monotonic() - started, 3),
              "process_group_stopped": stopped}
    if timed_out:
        # constraint: session-time-limit
        failure = WorkflowError(f"Command {argv[0]} exceeded its {timeout}s time limit; " +
                                ("its process group was stopped." if stopped else
                                 "process-group termination could not be confirmed; reconcile before retrying."))
    if not stopped and failure is None:
        failure = WorkflowError("Process-group termination could not be confirmed; reconcile before retrying.")
    if failure or interrupted:
        error = interrupted if interrupted is not None else failure
        # A session time limit is a safety net like the turn ceiling: reaching it is an
        # ordinary failed attempt with its diagnostics, never an exhausted budget.
        error.diagnostics = {**failure_details(result, "timeout" if timed_out else "execution"),
                             "process_group_stopped": stopped,
                             "process_group": process.pid if process else None}
        if timed_out:
            error.diagnostics["timeout_seconds"] = timeout
        if "saved_sha256" in result:
            error.diagnostics["saved_sha256"] = result["saved_sha256"]
        raise error
    return result


def _publish(stream, directory, names, name):
    """Publish one captured stream as a fresh file in a directory Firebreak opened: write a
    new file there, then atomically replace the published name. Nothing a check left at
    that name, such as a link, is followed or written through. Returns the fingerprint of
    the captured bytes themselves."""
    temporary = f".{names[name]}.{uuid.uuid4().hex}.tmp"
    fingerprint = hashlib.sha256()
    stream.seek(0)
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644,
                         dir_fd=directory)
    with os.fdopen(descriptor, "wb") as saved:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            fingerprint.update(chunk)
            saved.write(chunk)
    os.replace(temporary, names[name], src_dir_fd=directory, dst_dir_fd=directory)
    return fingerprint.hexdigest()


def failure_details(result, category):
    """Preserve bounded host evidence rather than only a terminal error label."""
    return {
        "category": category,
        "seconds": result.get("seconds"),
        "exit_code": result.get("exit_code"),
        **{
            key: result.get(key, "")[-limit:]
            for key, limit in (("stdout", 12000), ("stderr", 4000))
        },
        "stdout_omitted_bytes": result.get("stdout_omitted_bytes", 0)
        + len(result.get("stdout", "")[:-12000].encode()),
        "stderr_omitted_bytes": result.get("stderr_omitted_bytes", 0)
        + len(result.get("stderr", "")[:-4000].encode()),
    }


def bounded_number(config, key, default, maximum):
    value = config.get(key, default)
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not 0 < value <= maximum
    ):
        raise WorkflowError(
            f"{key} must be a positive number no larger than {maximum}."
        )
    return value


def verify(root, checks, *, keep_going=False, save_output=None):
    """Run checks in order; stop at the first failure unless keep_going, as the test
    checkpoint needs, since it expects red and every check's outcome is evidence. With
    keep_going, a check that timed out or could not start, once its processes are
    stopped, is kept as a result with no exit code and its diagnostics.

    save_output, a repository-relative folder, receives each check's complete stdout and
    stderr, replacing what an earlier run left there; each result names its saved files
    and their fingerprints."""
    config = project_config(root)
    timeout = bounded_number(config, "check_timeout", 300, 3600)
    directory = None
    if save_output:
        # A fresh directory Firebreak creates and holds open, so a check that swaps the
        # path for a link cannot redirect where its output is published.
        folder = confined(root, save_output)
        if folder.is_symlink() or folder.is_file():
            folder.unlink()
        shutil.rmtree(folder, ignore_errors=True)
        folder.mkdir()
        ignore_everything(folder)
        directory = os.open(folder, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        return _run_checks(root, checks, timeout, keep_going, save_output, directory)
    finally:
        if directory is not None:
            os.close(directory)


def _run_checks(root, checks, timeout, keep_going, save_output, directory):
    results = []
    for number, argv in enumerate(checks, 1):
        names = {name: f"check-{number}.{name}.txt" for name in ("stdout", "stderr")}
        try:
            keep = {"save_to": (directory, names)} if directory is not None else {}
            result = run_command(argv, root, timeout, **keep)
        except WorkflowError as exc:
            diagnostics = getattr(exc, "diagnostics", None) or {}
            if not keep_going or not diagnostics.get("process_group_stopped"):
                raise
            result = {"argv": argv, "exit_code": None, "error": str(exc),
                      "stdout": diagnostics.get("stdout", ""), "stderr": diagnostics.get("stderr", ""),
                      "seconds": diagnostics.get("seconds"),
                      **({"saved_sha256": diagnostics["saved_sha256"]} if "saved_sha256" in diagnostics else {})}
        if directory is not None:
            hashes = result.pop("saved_sha256", {})
            result["saved_output"] = {
                name: {"path": f"{save_output}/{names[name]}", "sha256": hashes[name]} for name in hashes
            }
        # Keep bounded evidence; the exit code is the authority, not text containing PASS.
        for stream in ("stdout", "stderr"):
            omitted = max(0, len(result[stream]) - 12000)
            result[stream] = result[stream][-12000:]
            result[stream + "_omitted_chars"] = omitted
        results.append(result)
        if result["exit_code"] and not keep_going:
            break
    return results


def saved_output_intact(root, checks, manifest=None):
    """Refuse saved check output that is incomplete or no longer matches its fingerprints.
    With a snapshot manifest, compare the bytes the reviewer will read instead of the tree."""
    if not any("saved_output" in check for check in checks):
        return
    for number, check in enumerate(checks, 1):
        saved = check.get("saved_output", {})
        for name in ("stdout", "stderr"):
            item = saved.get(name)
            if item is None:
                raise WorkflowError(
                    f"Check {number} has no saved {name}; run test-checkpoint again so every check's output is saved."
                )
            path = confined(root, item["path"])
            actual = manifest.get(item["path"]) if manifest is not None else (
                hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None)
            if actual != item["sha256"]:
                raise WorkflowError(
                    f"The saved {name} of check {number} ({item['path']}) changed after it was saved, so the "
                    "reviewer cannot read what the check printed. Make sure no check writes inside the unit's "
                    "folder, then run test-checkpoint again."
                )


def claude_review(root, prompt, config, *, schema=SCHEMA, validator=validate_single):
    if config.get("_managed_project_root"):
        from .managed_investigations import run_reader
        return run_reader(root, prompt, config, _claude_session, schema=schema, validator=validator)
    return _claude_session(root, prompt, config, schema=schema, validator=validator)


def wire_contract(schema, *, managed):
    """The JSON schema handed to the host: one flat object with no top-level union.

    The host validates structured output itself and retries with its validator's
    error text. A union of complete branches made one over-long summary report the
    failures of every branch at once, which the model never recovered from. A flat
    object yields one clear error per property; Firebreak enforces the
    review-or-investigation choice after parsing.
    """
    wire = copy.deepcopy(schema)
    wire["properties"]["context"] = CONTEXT_SCHEMA
    wire["required"] = [*wire["required"], "context"]
    if managed:
        from .managed_investigations import REQUEST_SCHEMA

        wire["properties"]["investigation"] = REQUEST_SCHEMA
        wire["required"] = []
    return wire


def length_budgets(schema):
    """State the schema's own size limits so the prompt cannot drift from the validator."""
    parts = []

    def walk(node, name):
        if not isinstance(node, dict):
            return
        if "maxLength" in node:
            parts.append(f"{name} at most {node['maxLength']} characters")
        if "maxItems" in node:
            parts.append(f"{name} at most {node['maxItems']} items")
        for key, child in node.get("properties", {}).items():
            walk(child, f"{name}.{key}" if name else key)
        walk(node.get("items"), f"{name}[]")
        for branch in node.get("anyOf", []):
            walk(branch, name)

    walk(schema, "")
    if not parts:
        return ""
    return (
        "The response schema enforces these length budgets, counted in characters of each "
        "string value; a longer value is rejected, so condense rather than exceed them: "
        + "; ".join(parts) + "."
    )


def brief_parts(prompt):
    """Size each top-level packet field and the surrounding text, largest first."""
    sizes, rest = {}, 0
    for line in prompt.splitlines():
        try:
            packet = json.loads(line) if line.startswith("{") else None
        except ValueError:
            packet = None
        if isinstance(packet, dict) and not sizes:
            sizes = {key: len(json.dumps(value, ensure_ascii=False)) for key, value in packet.items()}
        else:
            rest += len(line) + 1
    sizes["instructions and stage material"] = rest
    return sorted(sizes.items(), key=lambda item: -item[1])


def _claude_session(root, prompt, config, *, schema=SCHEMA, validator=validate_single):
    timeout = bounded_number(config, "review_timeout", 1200, 86400)
    max_turns = config.get("reviewer_max_turns", 100)
    if isinstance(max_turns, bool) or not isinstance(max_turns, int) or max_turns <= 0:
        # constraint: n/a configuration error, not model output
        raise WorkflowError("reviewer_max_turns must be a positive integer.")
    model = config.get("reviewer_model", "opus")
    effort = config.get("reviewer_effort", "medium")
    if not isinstance(effort, str) or effort not in {
        "low",
        "medium",
        "high",
        "xhigh",
        "max",
    }:
        # constraint: n/a configuration error, not model output
        raise WorkflowError("reviewer_effort must be low, medium, high, xhigh, or max.")
    if not isinstance(model, str) or not model or model.startswith("-"):
        # constraint: n/a configuration error, not model output
        raise WorkflowError("reviewer_model must name a Claude Code model.")
    wire_schema = wire_contract(schema, managed=bool(config.get("_managed_project_root")))
    if config.get("_managed_project_root"):
        # Guidance only: every enforced rule on the request and the response shape is
        # rendered from the constraint registry into the prompt's rules block.
        prompt += (
            "\nIf a consequential factual or runtime question can be checked, request an investigation "
            "instead of guessing, in the request shape the rules block states: a stable id, a concrete "
            "question, requirements references, and mode=direct with argv for one bounded check or "
            "mode=delegated with a prompt for exploratory or code-changing experiments. Declare "
            "exploratory, modifies_code, and external target and effects truthfully; external "
            "authenticated, shared, or state-changing checks need sourced existing authorization. "
            "The runtime executes against a disposable snapshot and returns evidence; you retain "
            "responsibility for the final review."
        )
    argv = [
        "claude",
        "-p",
        "--safe-mode",
        "--restricted",
        "--model",
        model,
        "--effort",
        effort,
        "--output-format",
        "json",
        "--json-schema",
        json.dumps(wire_schema),
        "--tools",
        "Read,Glob,Grep",
        "--allowedTools",
        "Read,Glob,Grep",
        "--strict-mcp-config",
        "--mcp-config",
        '{"mcpServers":{}}',
        "--permission-mode",
        "dontAsk",
        "--settings",
        '{"disableAllHooks":true}',
        "--setting-sources",
        "",
        "--max-turns",
        str(max_turns),
        "--no-session-persistence",
    ]
    # Guidance on classifying context; the declaration's enforced rules (required
    # paths, snapshot spelling, status shape, the incomplete verdict), the session
    # limits, and the length budgets come from the constraint registry's rules block.
    prompt += (
        "\nReport context completeness for the CURRENT review decision. Return complete after "
        "inspecting the required inputs and dependencies needed for that decision. "
        "List repository-relative inspected_files for all sources read. "
        "Use supporting_files only for governing authority documents and shared contracts materially "
        "relied on, not background implementation under development. "
        "Return incomplete only for unavailable evidence needed to decide this task. "
        "Artifacts belonging to a later phase are not missing prerequisites. A new repository may "
        "have no optional convention files; their absence alone does not make context incomplete. "
        "A completeness report is a claim, not proof of correctness. Read source evidence before deciding."
    )
    if len(prompt) > 160000:
        # A tripwire for the assembler inlining content it should cite; the reviewer reads
        # sources itself, so an oversize brief is never the unit's or the agent's fault.
        error = WorkflowError(
            f"Review brief is {len(prompt):,} characters, over the 160,000 limit. This is a Firebreak "
            f"defect in how the brief is built, not a problem with the unit: largest parts are "
            f"{', '.join(f'{name} ({size:,})' for name, size in brief_parts(prompt)[:3])}. "
            "This attempt does not count against the review round limit. Do not retry or change "
            "the unit; report this message to the operator."
        )
        error.diagnostics = {"round_unspent": True, "brief_characters": len(prompt),
                             "brief_parts": dict(brief_parts(prompt))}
        # constraint: n/a handoff size is the assembler's fault, not the model's output
        raise error
    budgets = {"review_timeout": timeout, "reviewer_max_turns": max_turns}
    try:
        with command_scope(config.get("_managed_project_root") or root):
            result = run_command(argv, root, timeout, prompt)
    except WorkflowError as exc:
        exc.diagnostics = {**getattr(exc, "diagnostics", {}), **budgets}
        raise
    try:
        host_result = json.loads(result["stdout"])
    except (ValueError, TypeError):
        host_result = None
    if isinstance(host_result, dict) and host_result.get("subtype") == "error_max_turns":
        host_detail = str(host_result.get("result") or host_result.get("error") or host_result["subtype"])
        # The turn ceiling is a safety net against a looping session, not a budget:
        # reaching it is an ordinary failed attempt that the phase round limit governs.
        error = WorkflowError(
            f"Claude review reached its {max_turns} turn ceiling without a complete verdict "
            f"(exit {result['exit_code']}): {host_detail[-2000:]}"
        )
        error.diagnostics = {
            **failure_details(result, "host"), **budgets,
            "num_turns": host_result.get("num_turns"),
        }
        # constraint: turn-ceiling
        raise error
    if result["exit_code"]:
        diagnostic = result["stderr"].strip() or result["stdout"].strip()
        try:
            failure = json.loads(diagnostic)
            if isinstance(failure, dict):
                diagnostic = str(
                    failure.get("result")
                    or failure.get("error")
                    or failure.get("subtype")
                    or diagnostic
                )
        except (ValueError, TypeError):
            pass
        error = WorkflowError(
            f"Claude review failed (exit {result['exit_code']}): "
            + diagnostic[-2000:]
            + (
                " Use a host supporting --safe-mode and --restricted with normal Claude authentication."
                if "unknown option" in diagnostic or "unrecognized" in diagnostic
                else ""
            )
        )
        error.diagnostics = {**failure_details(result, "host"), **budgets}
        # constraint: n/a host process failure, not model output
        raise error
    try:
        if result.get("stdout_omitted_bytes") or len(result["stdout"]) > 1024 * 1024:
            # constraint: n/a transport bound, unreachable under the schema's length budgets
            raise ValueError("Review response exceeded 1 MiB")
        envelope = json.loads(result["stdout"])
        if envelope.get("is_error") or envelope.get("subtype") not in {None, "success"}:
            # constraint: n/a host envelope status, not model output
            raise ValueError(f"Incomplete review: {envelope.get('subtype')}")
        data = envelope.get("structured_output")
        if data is None:
            data = json.loads(envelope["result"])
        if not isinstance(data, dict):
            # constraint: n/a the host schema already enforces the object type
            raise ValueError("Native structured output must be a JSON object")
        data = data.copy()
        ignored_investigation = None
        mixed_error = None
        if config.get("_managed_project_root"):
            # The flat wire schema admits both shapes; exactly one is acceptable here.
            mixed = sorted(set(data) - {"investigation"})
            if "investigation" in data and mixed:
                # A review that validates on its own is final: a model that re-sends a
                # satisfied request alongside it has still delivered the review that was
                # paid for. The request is dropped, recorded, and never run. Only when
                # the review fields do not validate does the mixing itself fail the response.
                request = data.pop("investigation")
                ignored_investigation = {
                    "id": request.get("id") if isinstance(request, dict) else None,
                    "reason": "response combined a completed review with an investigation "
                    "request; the review was accepted and the request was not run",
                }
                mixed_error = ValueError(
                    "Response mixed an investigation request with review fields "
                    f"({', '.join(mixed)}); return either the investigation alone or the complete review"
                )
            elif "investigation" in data:
                return {"investigation": data["investigation"], "seconds": result["seconds"],
                        "usage": envelope.get("modelUsage", envelope.get("usage")),
                        "reported_cost_usd": envelope.get("total_cost_usd")}
            elif not data:
                # constraint: managed-response-shape
                raise ValueError(
                    "Response was an empty object: neither an investigation request nor a complete "
                    f"review with {', '.join([*schema['required'], 'context'])}"
                )
        try:
            context = validate_context(
                data.pop("context", None),
                config.get("_review_available_files"),
                config.get("_review_required_files", ()),
            )
            validator(data)
        except (WorkflowError, ValueError, KeyError, TypeError, AttributeError) as exc:
            if mixed_error is not None:
                if hasattr(exc, "inspection_missing_paths"):
                    # The review branch failed only on its inspection declaration, so the
                    # reader keeps its ordinary one-shot correction for the missing paths.
                    mixed_error.inspection_missing_paths = exc.inspection_missing_paths
                    mixed_error.args = (f"{mixed_error} {exc}",)
                elif hasattr(exc, "inspection_unknown_paths"):
                    mixed_error.inspection_unknown_paths = exc.inspection_unknown_paths
                    mixed_error.args = (f"{mixed_error} {exc}",)
                # constraint: managed-response-shape
                raise mixed_error from exc
            raise
    except (WorkflowError, ValueError, KeyError, TypeError, AttributeError) as exc:
        error = WorkflowError(
            f"Claude returned incomplete or invalid review JSON: {exc}"
        )
        error.diagnostics = {**failure_details(result, "response-validation"), **budgets}
        if hasattr(exc, "inspection_missing_paths"):
            error.inspection_missing_paths = exc.inspection_missing_paths
            error.diagnostics["missing_inspection_paths"] = exc.inspection_missing_paths
        if hasattr(exc, "inspection_unknown_paths"):
            error.inspection_unknown_paths = exc.inspection_unknown_paths
            error.diagnostics["unknown_inspection_paths"] = exc.inspection_unknown_paths
        # constraint: n/a wraps the validator's own annotated rejection with diagnostics
        raise error from exc
    return {
        "review": data,
        "context": context,
        "seconds": result["seconds"],
        "usage": envelope.get("modelUsage", envelope.get("usage")),
        "reported_cost_usd": envelope.get("total_cost_usd"),
        **({"ignored_investigation": ignored_investigation} if ignored_investigation else {}),
    }


DETECTION_GUIDES = (
    "review/ai-failure-modes.md",
    "review/detection-audits.md",
    "review/quality-detection.md",
    "review/security-patterns.md",
    "fbk-review-lenses/shared-detection.md",
    "review/test-integrity.md",
    "review/remediation-verification.md",
)


def implementation_guidance():
    return _detection_guidance(DETECTION_GUIDES)


def test_guidance():
    return _detection_guidance(("review/test-integrity.md",))


def remediation_guidance():
    return _detection_guidance(("review/remediation-verification.md",))


def _detection_guidance(paths):
    """Load shipped criteria, never a reviewed project's lookalike files."""
    directory = Path(__file__).resolve().parents[3] / "fbk-docs"
    guides = {}
    for relative in paths:
        try:
            text = (directory / relative).read_text()
        except OSError as exc:
            raise WorkflowError(
                f"Review guidance is unavailable: {relative}. "
                "Restore the Firebreak installation's fbk-docs before retrying."
            ) from exc
        if not text.strip():
            raise WorkflowError(f"Review guidance is empty: {relative}. Restore the installed guide.")
        guides[relative] = text
    return guides


REVIEWER_BRIEF = "review/reviewer-brief.md"
PHASE_BRIEFS = {
    "intent": "review/phase-intent.md",
    "design": "review/phase-design.md",
    "spec": "review/phase-spec.md",
    "breakdown": "review/phase-breakdown.md",
    CHECKPOINT: "review/phase-checkpoint.md",
    "implement": "review/phase-implement.md",
}
# Used when no test was written: every requirement is review-only and the plan has no test task.
PRESERVATION_BRIEF = "review/phase-checkpoint-preservation.md"
COUNCIL_BRIEF = "review/council/council-brief.md"
PERSONAS = {member: f"review/council/{member}.md" for member in MEMBERS}
PERSONA_SECTIONS = ("Identity", "Quality bars", "Default you resist", "Duty")
REVIEW_BRIEFS = (REVIEWER_BRIEF, *PHASE_BRIEFS.values(), PRESERVATION_BRIEF,
                 COUNCIL_BRIEF, *PERSONAS.values())


def _brief_sections(relative, required):
    """The named ``## `` sections of a shipped review brief, each as its nonblank lines."""
    sections, current = {}, None
    for line in _detection_guidance((relative,))[relative].splitlines():
        if line.startswith("## "):
            current = sections.setdefault(line[3:].strip(), [])
        elif current is not None and line.strip():
            current.append(line.strip())
    missing = [name for name in required if name not in sections]
    if missing:
        raise WorkflowError(
            f"Review guidance {relative} is missing its {', '.join(missing)} section. Restore the installed guide."
        )
    return sections


BRIEF_SECTIONS = ("Role", "Evidence", "Reporting", "Findings")


def reviewer_brief(phase, unit, sections=BRIEF_SECTIONS):
    """The named sections of the shared reviewer brief, in file order, one sentence per line.

    Single reviewers get every section; council openings skip Role, which the council brief
    gives them; turns also skip Reporting, since they add only replacements; closing stances
    get Evidence only."""
    found = _brief_sections(REVIEWER_BRIEF, BRIEF_SECTIONS)
    lines = [line for name in BRIEF_SECTIONS if name in sections for line in found[name]]
    return " ".join(lines).replace("{phase}", phase).replace("{unit}", unit) + " "


def phase_brief(phase, preservation=False):
    """The phase review's decision question, what it checks, and the work left to later phases."""
    relative = PRESERVATION_BRIEF if preservation and phase == CHECKPOINT else PHASE_BRIEFS[phase]
    sections = _brief_sections(relative, ("Decision", "Check", "Later deliverables"))

    def items(name):
        return [line[2:].strip() if line.startswith("- ") else line for line in sections[name]]

    return {
        "decision": " ".join(sections["Decision"]),
        "acceptance_obligations": items("Check"),
        "later_deliverables": items("Later deliverables"),
    }


def council_brief(step, phase, unit):
    """What every council session shares, then what this step produces."""
    sections = _brief_sections(COUNCIL_BRIEF, ("Council", step))
    lines = sections["Council"] + sections[step]
    return " ".join(lines).replace("{phase}", phase).replace("{unit}", unit) + " "


def persona(member, phase):
    """A council member's role, and what it looks for in this phase."""
    focus = phase.capitalize()
    sections = _brief_sections(PERSONAS[member], (*PERSONA_SECTIONS[:3], focus))
    parts = [f"Council member: {member}."]
    for name in (*PERSONA_SECTIONS, focus):
        if name in sections:
            label = f"{focus} focus" if name == focus else name
            parts.append(f"{label}: " + " ".join(sections[name]))
    return " ".join(parts) + " "


def review_brief_digests():
    """A changed brief must start a fresh review, as a changed review module does."""
    from .store import digest

    return {name: digest(text) for name, text in _detection_guidance(REVIEW_BRIEFS).items()}


def review(root, unit, phase, files, checks):
    config = project_config(root)
    if phase == "implement":
        config["_review_detection_guidance"] = implementation_guidance()
    elif phase in {"breakdown", CHECKPOINT}:
        config["_review_detection_guidance"] = test_guidance()
    record = load(root, unit)
    if phase in {"spec", "breakdown", CHECKPOINT, "implement"}:
        from .traceability import review_only

        # The spec review judges each review-only marker; the test reviews need no test for
        # one; the implementation review assesses each, since no test checks it.
        config["_review_only_requirements"] = review_only(root, record)
    from .decisions import for_readers

    # Readers get the phase's own governing decisions and live amendments; staleness
    # still digests every active decision through evidence.revision_inputs.
    decisions = for_readers(root, record, phase)
    required = set(files)
    required.update(d["source"]["path"] for d in decisions)
    if record["parent"]:
        required.add(f".fbk/{record['parent']}/spec.md")
    targets = None
    if phase == "breakdown":
        # Breakdown reviews the plan; tests are written and reviewed in implement.
        targets = [f".fbk/{unit}/tasks.json"]
    if phase == CHECKPOINT:
        from . import evidence
        from .store import read_json, unit_dir

        # The tests, and the production files test tasks declared for interface changes.
        declared = evidence.scope(root, unit)
        tests = evidence.test_files(root, declared)
        owned = [
            path
            for task in read_json(unit_dir(root, unit) / "tasks.json")
            if task.get("stage") == "tests"
            for path in evidence.expand(root, task["files"])
            if evidence.matches(path, declared["sources"]) and path not in tests
        ]
        required.update(tests, owned)
        targets = sorted({*tests, *owned})
        from .engine import test_outcome

        if test_outcome(root, record) == "preservation":
            # A preservation checkpoint judges whether the scoped tests protect the code the
            # unit will change, so that code, as the implementation tasks own it, is read too.
            config["_review_preservation"] = True
            required.update(
                path
                for task in read_json(unit_dir(root, unit) / "tasks.json")
                if task.get("stage") == "implementation"
                for path in evidence.expand(root, task["files"])
                if evidence.matches(path, declared["sources"])
            )
        # Each check's complete saved output is required reading, and the comparison with
        # the writing-tests baseline says which tests changed and how production changed.
        required.update(item["path"] for check in checks for item in check.get("saved_output", {}).values())
        from .test_preparation import baseline_comparison

        config["_review_test_comparison"] = baseline_comparison(root, record, diffs=True)
        compared = config["_review_test_comparison"].pop("compared")
        compared_links = config["_review_test_comparison"].pop("compared_links")
        bound = config["_review_test_comparison"].pop("bound")
        fingerprints = config["_review_test_comparison"].pop("fingerprints")
        # After an earlier acceptance, tests unchanged since it carry its red forward, and
        # the output that showed that red is required reading too.
        from .engine import accepted_checkpoint
        from .test_preparation import accepted_output_paths

        from .engine import approved_rework

        # An outstanding unlock's approved outcome for each reworked test, and which tests
        # each rework command covers: its exit alone cannot show a reversed result.
        rework = approved_rework(record)
        if rework:
            config["_review_test_comparison"]["approved_rework"] = rework
        from .test_preparation import retargeted_since

        accepted_tests = (accepted_checkpoint(record) or {}).get("tests")
        if accepted_tests:
            retargeted = retargeted_since(root, accepted_checkpoint(record), tests)
            config["_review_test_comparison"]["unchanged_since_accepted_checkpoint"] = sorted(
                path for path in tests if fingerprints.get(path) == accepted_tests.get(path)
                and path not in retargeted)
            config["_review_test_comparison"]["accepted_checkpoint_output"] = accepted_output_paths(root, record)
            required.update(config["_review_test_comparison"]["accepted_checkpoint_output"])
    if phase == "implement":
        from . import evidence

        declared = evidence.scope(root, unit)
        targets = evidence.expand(
            root, declared["sources"] + declared["tests"] + declared["docs"]
        )
    with snapshot(root, required) as (sources, manifest):
        from . import review_baseline

        # No reader launches on saved check output other than the fingerprinted bytes.
        if phase == CHECKPOINT:
            saved_output_intact(root, checks, manifest)
            # Nor on a snapshot whose tests or production files differ from the bytes the
            # changed-versus-untouched split and the production diffs were made from.
            from .evidence import matches

            # Link targets too: a fingerprint reads through a link, so a retarget between
            # equal files after the comparison changes no content.
            captured = captured_symlinks(sources)
            moved = sorted(path for path, value in compared.items()
                           if manifest.get(path) != value or captured.get(path) != compared_links.get(path))
            moved += sorted(
                path for path in manifest
                if path not in compared and (
                    matches(path, bound["tests"])
                    or matches(path, bound["sources"]) and matches(path, bound["declared"])
                )
            )
            if moved:
                raise WorkflowError(
                    f"{', '.join(moved)} changed while the checkpoint prepared its review, so the "
                    "reviewer would read files its comparison does not describe. Let running work "
                    "finish, then run test-checkpoint again."
                )

        available = {**manifest, **listing_inputs(sources)}
        links = captured_symlinks(sources)
        baseline = review_baseline.prepare(root, sources, record, phase, available)
        config = {
            **config,
            "_managed_project_root": str(root),
            "_managed_unit": unit,
            "_managed_phase": phase,
            "_review_required_files": sorted(required),
            "_review_available_files": available,
            "_review_baseline": baseline,
            "_review_decisions": decisions,
            "_review_phase_targets": targets,
        }
        work = record["phases"][phase]
        pending = work.get("pending")
        if pending:
            config["_council_progress"] = _council_progress(root, unit, phase, pending["id"])
        previous = work["rounds"][-2] if len(work["rounds"]) > 1 else None
        prior_result = (previous or {}).get("result") or {}
        if (
            pending and previous and previous.get("error") and prior_result.get("error")
            and previous["revision"] == pending["revision"]
            and previous["generation"] == work["generation"]
            and prior_result.get("source_policy") == "original-snapshot-v1"
            and prior_result.get("snapshot_files") == manifest
            and prior_result.get("required_files") == sorted(required)
        ):
            config["_council_previous"] = prior_result
            config["_council_previous_operation"] = previous["operation"]
        if pending:
            with transaction(root):
                latest = load(root, unit)
                latest_work = latest["phases"][phase]
                if latest_work.get("pending", {}).get("id") == pending["id"] and latest_work["rounds"]:
                    latest_work["rounds"][-1]["result"] = {
                        "readers": [], "error": "Review interrupted before completion.",
                        "source_policy": "original-snapshot-v1", "snapshot_files": manifest,
                        "required_files": sorted(required),
                    }
                    save(root, latest)
        from .engine import review_binding
        from .managed_investigations import managed_round_id, open_round
        from .store import digest
        # A mode or link change alone leaves the manifest as it was, yet investigations
        # copy the snapshot, so each is part of the round's identity.
        executables = executable_paths(sources, manifest)
        identity = digest({"unit": unit, "phase": phase, "sources": manifest,
                           **({"executables": executables} if executables else {}),
                           **({"symlinks": links} if links else {}),
                           "baseline": baseline,
                           "required": sorted(required), "generation": work["generation"],
                           **({"binding": binding} if (binding := review_binding(record, phase)) else {}),
                           "configuration": {k: v for k, v in config.items() if not k.startswith("_")},
                           "selection": record.get("review_plans", {}).get(phase),
                           "detection_guidance": {name: digest(text) for name, text in config.get("_review_detection_guidance", {}).items()},
                           "review_briefs": review_brief_digests(),
                           "review_implementation": {name: digest(Path(__file__).with_name(name).read_text())
                                                     for name in ("review.py", "review_baseline.py", "council.py", "managed_investigations.py", "review_execution.py", "investigations.py")}})
        if prior_result.get("investigation_round") != managed_round_id(unit, phase, identity):
            config.pop("_council_previous", None)
            config.pop("_council_previous_operation", None)
        execution = open_round(root, sources, config, identity, unit, phase)
        review_baseline.remember(root, execution.round_id, baseline)
        config["_managed_execution"] = execution
        if pending:
            with transaction(root):
                latest = load(root, unit)
                active = latest["phases"][phase]
                if active.get("pending", {}).get("id") == pending["id"] and active["rounds"]:
                    active["rounds"][-1].setdefault("result", {})["investigation_round"] = execution.round_id
                    save(root, latest)
        try:
            result = _review_sources(sources, unit, phase, required, checks, config, record)
            if phase == "implement":
                result = requirement_blockers(result, config["_review_only_requirements"])
            if not result.get("error"):
                from .managed_investigations import require_resolved
                require_resolved(execution)
            result["investigation_round"] = execution.round_id
        finally:
            execution.finish()
        result["supporting_files"] = {
            p: manifest[p] for p in convention_paths(manifest)
        }
        result["additional_supporting_files"] = additional_supporting(
            root, unit, phase, required, result, manifest
        )
        if phase in {"breakdown", "implement", CHECKPOINT}:
            result["detection_guidance"] = {name: digest(text) for name, text in config["_review_detection_guidance"].items()}
        result["snapshot_files"] = manifest
        # A mode-only change must also make the snapshot stale, so it gets a fresh review.
        result["snapshot_executables"] = executable_paths(sources, manifest)
        result["snapshot_symlinks"] = links
        result["source_policy"] = "original-snapshot-v1"
        result["required_files"] = sorted(required)
        from .review_rounds import _manifest
        from .store import digest

        try:
            current = _manifest(root, required)
        except (OSError, WorkflowError) as exc:
            current = {"unavailable": str(exc)}
        if current != manifest:
            drift = {
                "paths": sorted(p for p in set(current) | set(manifest)
                                if current.get(p) != manifest.get(p)),
                "detected_at": now(), "original_revision": digest(manifest),
                "current_revision": digest(current),
            }
            result["source_drift"] = drift
            with transaction(root):
                latest = load(root, unit)
                event(latest, "review-source-drift", (pending or {}).get("session", "review"),
                      phase=phase, **drift)
                save(root, latest)
        return result


def _council_progress(root, unit, phase, operation):
    def update(stage, state, member=None, **details):
        # Progress is diagnostic; it cannot revive an abandoned reservation or
        # turn a successful review into a failure when reporting is unavailable.
        try:
            with transaction(root):
                record = load(root, unit)
                pending = record["phases"][phase].get("pending")
                if not pending or pending["id"] != operation:
                    return
                key = f"{stage}:{member}" if member else stage
                stages = pending.setdefault("stages", {})
                row = stages.setdefault(key, {"stage": stage, "member": member})
                row.update(state=state, **details)
                row["started_at" if state == "started" else "finished_at"] = now()
                event(record, "council-contract" if stage == "contract" else "council-stage", pending["session"], phase=phase,
                      operation=operation, stage=stage, state=state, member=member, **details)
                rounds = record["phases"][phase]["rounds"]
                if rounds and rounds[-1].get("operation") == operation:
                    retained = rounds[-1].setdefault("result", {})
                    if details.get("reader_context"):
                        retained["reader_context"] = details["reader_context"]
                    if state in {"completed", "reused"} and details.get("response"):
                        retained.setdefault("readers", []).append(
                            {**details["response"], "stage": stage, **({"member": member} if member else {})}
                        )
                save(root, record)
        except Exception:  # noqa: BLE001 - progress notes are best effort; a failed note leaves the review running
            pass
    return update


def bounded_checks(checks, root=None, available=None):
    """Keep executable outcomes and bounded excerpts, with explicit omission counts."""
    output = []
    for check in checks:
        item = {k: check[k] for k in ("argv", "exit_code", "seconds") if k in check}
        for stream in ("stdout", "stderr"):
            value = check.get(stream, "")
            item[stream] = value[-2000:]
            item[stream + "_omitted_chars"] = check.get(
                stream + "_omitted_chars", 0
            ) + max(0, len(value) - 2000)
            item[stream + "_omitted_bytes"] = check.get(stream + "_omitted_bytes", 0)
        output.append(item)
    if root is not None and checks:
        directory = Path(tempfile.mkdtemp(prefix=".review-verification-", dir=root))
        target = directory / "checks.json"
        relative = target.relative_to(root).as_posix()
        target.write_text(json.dumps(checks, ensure_ascii=False))
        if available is not None:
            available[relative] = "runtime-execution-evidence"
        if len(json.dumps(output)) > 32000:
            # All executable outcomes remain reachable; no directive to shrink real verification.
            return {
                "checks": len(checks),
                "failed": sum(bool(c.get("exit_code")) for c in checks),
                "evidence_file": relative,
                "instruction": "Read exact commands, outcomes, and captured diagnostics here before assessing verification.",
            }
        return {"outcomes": output, "evidence_file": relative}
    if len(json.dumps(output)) > 32000:
        raise WorkflowError(
            "Verification context needs a snapshot evidence file for progressive retrieval."
        )
    return output


def comparison_brief(root, comparison, required, available=None):
    """The checkpoint's comparison with the writing-tests baseline. Large production diffs
    move to a snapshot file the reviewer must read, so the brief does not grow with them."""
    diffs = comparison.get("production_diffs", {})
    if len(json.dumps(diffs, ensure_ascii=False)) <= 32000:
        return comparison, required
    # A freshly allocated folder, so the file never replaces a captured repository file.
    directory = Path(tempfile.mkdtemp(prefix=".review-verification-diffs-", dir=root))
    target = directory / "production-diffs.json"
    target.write_text(json.dumps(diffs, ensure_ascii=False))
    relative = target.relative_to(root).as_posix()
    if isinstance(available, dict):
        available[relative] = "runtime-baseline-diff"
    return {
        **comparison,
        "production_diffs": {
            "count": len(diffs),
            "diffs_file": relative,
            "instruction": "Read every diff in this file; each shows a declared production change "
            "against its copy in the writing-tests baseline.",
        },
    }, sorted({*required, relative})


DECISIONS_FILE = ".review-decisions/current-decisions.json"


def current_decisions(root, rows, required, available=None):
    """Hand the reviewer each latest applicable decision, not the store's bookkeeping.

    Replaced decisions are already excluded; their pointers and the source
    fingerprints serve Firebreak's own checks. A large set moves to a snapshot
    file the reviewer must declare reading, so the brief does not grow with it.
    """
    from .decisions import lean

    decisions = [lean(d) for d in rows]
    text = json.dumps(decisions, ensure_ascii=False)
    if len(text) <= 32000:
        return decisions, required
    target = Path(root) / DECISIONS_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)
    if isinstance(available, dict):
        available[DECISIONS_FILE] = "runtime-decision-record"
    return {
        "count": len(decisions),
        "decisions_file": DECISIONS_FILE,
        "instruction": "Read every decision in this file before deciding; each is the latest "
        "applicable decision, with its source path and exact quote.",
    }, sorted({*required, DECISIONS_FILE})


REVIEW_ONLY_INSTRUCTIONS = {
    "spec": "Each requirement listed here carries a Checked by review marker with its reason, so "
    "breakdown plans no test for it and the implementation review assesses it by reading. Judge "
    "each marker against its requirement's text: a marker on a requirement that names observable "
    "behavior an executable check could verify is a blocker, because it drops that behavior's test.",
    "breakdown": "Each requirement listed here is review-only: it carries a Checked by review marker "
    "and needs no test task and no test, since the implementation review assesses it by reading. It "
    "still needs an implementation task. A missing test for one is not a defect.",
    CHECKPOINT: "Each requirement listed here is review-only: it carries a Checked by review marker "
    "and needs no test, since the implementation review assesses it by reading. A missing test for "
    "one is not a defect.",
    "implement": "No test checks the review-only requirements listed here; this review is their "
    "verification. Read the delivered code and documents and return one entry in "
    "requirement_assessments for each, naming it by its requirement reference: verdict met or not "
    "met, evidence citing what you read, and a remedy when it is not met.",
}


REFACTOR_REVIEW_INSTRUCTION = (
    "Each refactor task returned the review listed here for the files it owns. Check each against the "
    "delivered code: a change it claims that the code does not show, or a believable boundary between "
    "independently changing policies that it neither tried nor explained, is a finding."
)


def refactor_returns(record):
    """Each completed refactor task's review, as its return's outcome, with its files."""
    return [
        {"task": task_id, "files": run["files"], "changed_files": run["return"].get("changed_files", []),
         "review": run["return"].get("outcome")}
        for task_id, run in record.get("task_runs", {}).items()
        if run.get("refactor") and run.get("status") == "completed" and run.get("return")
    ]


def focus_brief(unit, phase, files, target_files=None, review_only=False, preservation=False):
    base = f".fbk/{unit}/"
    names = {
        "intent": ("prd.md",),
        "design": ("design/",),
        "spec": ("spec.md", "scope.json"),
        "breakdown": ("tasks.json",),
        "implement": (),
        CHECKPOINT: (),
    }
    targets = [
        p
        for p in sorted(files)
        if (
            not p.startswith(".fbk/")
            if phase in {"implement", CHECKPOINT}
            else any(
                p == base + n or (n.endswith("/") and p.startswith(base + n))
                for n in names[phase]
            )
        )
    ]
    if target_files is not None:
        targets = sorted(set(target_files) & set(files))
    brief = phase_brief(phase, preservation)
    obligations = brief["acceptance_obligations"]
    if review_only and phase in {"breakdown", CHECKPOINT}:
        # Review-only requirements need no test, so the per-requirement test demands apply to
        # behavioral requirements alone.
        obligations[:] = [o.replace("material requirement", "material behavioral requirement") for o in obligations]
        obligations.append(
            "A review-only requirement, listed in review_only_requirements, needs no test; hold only "
            "behavioral requirements to the test obligations above."
        )
    obligations.append(
        "A current decision that amends an earlier phase overrides that phase's accepted "
        "document where they differ; the difference is not a defect."
    )
    if phase not in {"implement", CHECKPOINT}:
        obligations.append(
            f"Later phases receive this phase's decisions only through the accepted {phase} "
            f"document: each current decision of the {phase} phase, and each amendment of "
            f"{phase}, must be stated there in substance. A missing or contradicted decision is a blocker."
        )
    return {
        "phase_targets": targets,
        **brief,
        "coverage": "Inspect every path in required_files, both its phase_targets and its authoritative_context, and any dependency needed for the current decision. authoritative_context governs how the targets are judged; it is not work under review. Later deliverables are future work, not prerequisites for this review. Consult existing relevant conventions; a new repository may have none.",
    }


def _single_result(reader):
    """A reader that reported missing evidence gives a verdict the round fails on, not a crash."""
    result = {"shape": "single", "readers": [reader], "review": reader["review"]}
    incomplete = incomplete_context(result["readers"])
    if incomplete:
        result["incomplete_context"] = incomplete
        result["error"] = incomplete_message(incomplete)
    elif "requirement_assessments" in reader["review"]:
        # A single reader's assessments are operative.
        result["review"] = {k: v for k, v in reader["review"].items() if k != "requirement_assessments"}
        result["requirement_assessments"] = reader["review"]["requirement_assessments"]
    return result


def requirement_blockers(result, requirements):
    """Store the operative assessments with the round and add one blocker finding to the
    operative findings for each review-only requirement assessed as not met. These blockers
    are Firebreak's, not the reader's, so they are counted to keep them out of the reader's
    output limits (``reader_review``)."""
    if not requirements or result.get("error") or not result.get("review"):
        return result
    names = {item["requirement"]: item["name"] for item in requirements}
    findings = list(result["review"]["findings"])
    before = len(findings)
    for item in result["requirement_assessments"]:
        if item["verdict"] == "not met":
            # constraint: requirement-not-met-blocker
            findings.append({
                "title": f'Review-only requirement "{names[item["requirement"]]}" is not met'[:180],
                "location": item["requirement"],
                "evidence": item["evidence"],
                "remedy": item["remedy"],
                "severity": "blocker",
            })
    result["review"] = {**result["review"], "findings": findings}
    result["requirement_blockers"] = len(findings) - before
    return result


def reader_review(result):
    """The operative review as the readers gave it, without the requirement blockers Firebreak
    added, so the reader's output limits apply to the reader's findings alone."""
    added = result.get("requirement_blockers", 0)
    review = result["review"]
    if not added or not isinstance(review, dict) or not isinstance(review.get("findings"), list):
        return review
    return {**review, "findings": review["findings"][:-added]}


def _review_sources(root, unit, phase, files, checks, config, record):
    from .review_baseline import PREFIX

    # Lock discipline comes only from locks the record holds now; a reopen that cleared
    # them leaves no test contract to describe.
    locks = (
        [e for e in record["events"] if e["event"] == "tests-locked"]
        if phase in {"implement", CHECKPOINT} and record.get("locks")
        else []
    )
    discipline = None
    if locks:
        lock = locks[-1]
        discipline = {
            "locked_files": sorted(lock.get("files", {})),
            "preservation_reason": lock.get("preservation_reason"),
            "red_check": bounded_checks(
                [lock["red_check"]], root, config.get("_review_available_files")
            )
            if lock.get("red_check")
            else None,
        }
    detection = {}
    if phase in {"breakdown", "implement", CHECKPOINT}:
        detection = config.get("_review_detection_guidance")
        if detection is None:
            detection = implementation_guidance() if phase == "implement" else test_guidance()
    stage = {
        "breakdown": "breakdown inspects the planned test tasks and the plausible bugs each names",
        CHECKPOINT: "the test checkpoint inspects executable tests and meaningful red or preservation evidence",
        "implement": "implementation inspects delivered behavior, regressions and actual outcomes",
    }.get(phase)
    test_evidence = (
        f"For test review, apply the current stage: {stage}. "
        "Summarize material test coverage and limitations concisely in the existing summary; put defects "
        "and their deciding evidence in findings, inspected sources in inspected_files/supporting_files, "
        "and unavailable necessary inputs in missing_context with incomplete context status. Distinguish "
        "planned, source-inspected and executed evidence, including when there are no findings. "
    ) if phase in {"breakdown", "implement", CHECKPOINT} else ""
    decisions, required = current_decisions(
        root, config.get("_review_decisions", []),
        list(config.get("_review_required_files", sorted(files))),
        config.get("_review_available_files"),
    )
    comparison = None
    if config.get("_review_test_comparison") is not None:
        comparison, required = comparison_brief(
            root, config["_review_test_comparison"], required, config.get("_review_available_files"))
    # The snapshot flattens symbolic links, so its listing of their targets is required reading.
    required = sorted({*required, *listing_inputs(root)})
    config = {**config, "_review_required_files": required}
    # Each required path is listed once, under the role it plays in this review.
    priority = focus_brief(unit, phase, files, config.get("_review_phase_targets"),
                           bool(config.get("_review_only_requirements")), bool(config.get("_review_preservation")))
    targets = priority.pop("phase_targets")
    # The rules block states every enforced rule once, from the constraint registry,
    # for the kind of reader this round launches; council stage passes render their own.
    from .constraints import render

    selection = record.get("review_plans", {}).get(phase)
    review_only = config.get("_review_only_requirements") or []
    # Only the implementation review assesses review-only requirements; the spec review is
    # told about them so it can judge each marker.
    assessed = [item["requirement"] for item in review_only] if phase == "implement" else []
    refactor_reviews = refactor_returns(record) if phase == "implement" else []
    contract = {"schema": requirement_contract(assessed),
                "validator": functools.partial(validate_single, requirements=assessed)} if assessed else {}
    if selection and selection["mode"] == "council":
        from .council import CANDIDATE_SCHEMA

        rules = render("council-member", config, CANDIDATE_SCHEMA)
    else:
        rules = render("review", config, contract.get("schema", SCHEMA))
    council = bool(selection and selection["mode"] == "council")
    # A council composes each session's brief itself; its sessions need different sections.
    prompt = (
        ("" if council else reviewer_brief(phase, unit))
        + test_evidence
        + "\n"
        + json.dumps(
            {
                "comparison_baseline": config.get("_review_baseline", {
                    "status": "unavailable", "reason": "No baseline source tree was supplied to this review."
                }),
                **({"implementation_detection" if phase == "implement" else "test_detection": detection} if detection else {}),
                "reading_priority": priority,
                "required_files": {
                    "phase_targets": targets,
                    "authoritative_context": sorted(set(required) - set(targets)),
                },
                "rules": rules,
                "available_conventions": convention_paths(
                    p for p in config.get("_review_available_files", {})
                    if not p.startswith(PREFIX + "/")
                ),
                "current_decisions": decisions,
                **(
                    {
                        "verification": bounded_checks(
                            checks, root, config.get("_review_available_files")
                        ),
                        "test_discipline": discipline,
                    }
                    if phase in {"breakdown", "implement", CHECKPOINT}
                    else {}
                ),
                **({"test_comparison": comparison} if comparison is not None else {}),
                **({"review_only_requirements": {
                    "instruction": REVIEW_ONLY_INSTRUCTIONS[phase], "requirements": review_only,
                }} if review_only and phase in REVIEW_ONLY_INSTRUCTIONS else {}),
                **({"refactor_reviews": {
                    "instruction": REFACTOR_REVIEW_INSTRUCTION, "reviews": refactor_reviews,
                }} if refactor_reviews else {}),
                "parent_spec": f".fbk/{record['parent']}/spec.md"
                if record["parent"]
                else None,
            },
            ensure_ascii=False,
        )
    )
    if selection:
        if selection["mode"] == "council":
            from .council import run

            return run(root, prompt, config, phase, selection["members"], claude_review, unit=unit,
                       first_speaker=max(len(record["phases"][phase]["rounds"]) - 1, 0))
        return _single_result(claude_review(root, prompt, config))
    secondary = config.get("second_reader")
    if secondary is not None and (
        not isinstance(secondary, list)
        or not secondary
        or any(not isinstance(a, str) or not a for a in secondary)
    ):
        raise WorkflowError(
            "second_reader must be an executable argument array reading the prompt from stdin."
        )
    if not secondary:
        return _single_result(claude_review(root, prompt, config, **contract))
    # Optional external reader returns the same bare review object, not a host-specific envelope.
    with ThreadPoolExecutor(max_workers=2) as pool:
        native = pool.submit(claude_review, root, prompt, config, **contract)
        external = pool.submit(
            run_command,
            secondary,
            root,
            bounded_number(config, "review_timeout", 1200, 86400),
            prompt,
        )
        first = native.result()
        try:
            raw = external.result()
            if raw["exit_code"]:
                raise WorkflowError("Second reader exited unsuccessfully.")
            if raw.get("stdout_omitted_bytes") or len(raw["stdout"]) > 1024 * 1024:
                raise WorkflowError("Second reader exceeded bounded output.")
            second_data = json.loads(raw["stdout"])
            second_context = validate_context(
                second_data.pop("context", None),
                config["_review_available_files"],
                required,
            )
            second = contract.get("validator", validate_single)(second_data)
        except (WorkflowError, ValueError, TypeError, AttributeError) as exc:
            return {
                "shape": "single",
                "readers": [first],
                "review": first["review"],
                "second_reader_failure": str(exc),
                "error": "Assigned second reader did not complete; recover it or obtain human disposition.",
            }
    from .council import adjudicate

    return adjudicate(
        root,
        prompt,
        config,
        [
            {**first, "member": "native"},
            {
                "review": second,
                "seconds": raw["seconds"],
                "usage": None,
                "member": "external",
                "context": second_context,
            },
        ],
        claude_review,
        shape="dual",
        requirements=assessed,
    )
