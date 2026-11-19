"""Claude Code adapters. No model calls, subprocesses, or correctness-critical telemetry."""

import json
import os
import sys
from pathlib import Path

from . import engine, evidence, handoff, review_plan, telemetry
from .store import (
    RECORD_FOLDERS,
    WorkflowError,
    discover,
    enabled,
    load,
    project_config,
    project_root,
    save,
    transaction,
    unit_dir,
)

SKILLS = {f"fbk-{p}": p for p in evidence.PHASES}
SKILLS["fbk-breakdown"] = "breakdown"


def _unit_arg(text):
    parts = (text or "").split(maxsplit=1)
    if not parts:
        raise WorkflowError(
            "Name one unit, for example /fbk-spec account-settings; initialize it first with unit-init."
        )
    return parts[0].removeprefix(".fbk/").rstrip("/")


def record_event(root, payload, decision, unit=None, phase=None):
    """Metadata only; capture cannot influence hook policy."""
    telemetry.record(
        root,
        {
            "event": payload.get("hook_event_name"),
            "session": payload.get("session_id"),
            "agent": payload.get("agent_id", "main"),
            "tool_use_id": payload.get("tool_use_id"),
            "tool": payload.get("tool_name"),
            "unit": unit,
            "phase": phase,
            "decision": decision,
        },
    )


def _deny(event, reason):
    if event == "PreToolUse":
        return {
            "hookSpecificOutput": {
                "hookEventName": event,
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
    return {"decision": "block", "reason": reason}


def _context(event, text):
    return {"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}}


def _after_edit(payload, path):
    """The file's bytes before the tool's change and every result the tool could plausibly
    give, or a refusal when no result can be computed. An Edit reads the file with line
    endings normalized to LF and writes it back in the file's own line ending; a file with
    mixed line endings or a byte-order mark is refused, since the tools rewrite those."""
    tool, tool_input = payload.get("tool_name"), payload.get("tool_input", {})
    cannot = (f"Firebreak cannot compute {path.name} as it would be after this {tool}, so it cannot tell "
              "whether the change touches the file's test region")
    try:
        before = path.read_bytes() if path.exists() else None
    except OSError as exc:
        raise WorkflowError(f"{cannot}: the file cannot be read ({exc.strerror}).") from exc
    if before is not None and (before.startswith(b"\xef\xbb\xbf")
                               or b"\r\n" in before and b"\n" in before.replace(b"\r\n", b"")):
        raise WorkflowError(
            f"{cannot}: it has mixed line endings or starts with a byte-order mark. Convert it to one line "
            "ending with no byte-order mark, through a task that owns it, then retry."
        )
    if tool == "Write" and isinstance(tool_input.get("content"), str):
        return before or b"", [tool_input["content"].encode("utf-8")]
    if tool != "Edit":
        raise WorkflowError(f"{cannot}; change it with Edit or Write.")
    old, new = tool_input.get("old_string"), tool_input.get("new_string")
    try:
        text = before.decode("utf-8") if before is not None else None
    except UnicodeDecodeError:
        text = None
    if text is None or not isinstance(old, str) or not old or not isinstance(new, str):
        raise WorkflowError(f"{cannot}: the file is missing or is not UTF-8 text, or the edit is incomplete.")
    ending = "\r\n" if "\r\n" in text else "\n"
    content, old, new = (value.replace("\r\n", "\n") for value in (text, old, new))
    count = content.count(old)
    if count == 0:
        raise WorkflowError(f"{cannot}: the text to replace is absent.")
    if count > 1 and not tool_input.get("replace_all"):
        raise WorkflowError(f"{cannot}: the text to replace is not unique; give more surrounding text or set replace_all.")
    # The plain replacement, and, when new_string is empty, the tool's deletion of the
    # newline after the deleted text.
    targets = [old] + ([old + "\n"] if not new and not old.endswith("\n") and old + "\n" in content else [])
    results = [content.replace(target, new) if tool_input.get("replace_all") else content.replace(target, new, 1)
               for target in targets]
    return before, [result.replace("\n", ending).encode("utf-8") for result in results]


def _region_change(root, record, relative, path, payload):
    """For a region-bearing file in implement, whether the change touches its test region;
    None for any other file. A change to the code above is a production write."""
    if record["open_phase"] != "implement":
        return None
    declared = evidence.scope(root, record["unit"])
    start = evidence.region_start(declared, relative)
    if start is None:
        return None
    before, results = _after_edit(payload, path)
    region = evidence.split_region(before, start)[1]
    return any(evidence.split_region(after, start)[1] != region for after in results)


def _write_check(root, payload, records):
    session = payload.get("session_id")
    if not isinstance(session, str) or not session:
        raise WorkflowError(
            "File action is missing its session identity; retry through the host."
        )
    tool_input = payload.get("tool_input", {})
    value = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not isinstance(value, str) or not value:
        raise WorkflowError(
            "File tool omitted its target path; retry with a concrete file path."
        )
    path = Path(value)
    if not path.is_absolute():
        path = Path(payload.get("cwd") or root) / path
    path = path.resolve()
    active = [r for r in records if r["owner"] == session and r["open_phase"]]
    if not path.is_relative_to(root):
        if active:
            raise WorkflowError(
                "Active Firebreak work writes inside its repository; suspend it before unrelated edits."
            )
        return
    relative = path.relative_to(root).as_posix()
    if (
        relative == ".fbk/config.json"
        or relative.endswith("/state.json")
        and relative.startswith(".fbk/")
    ):
        raise WorkflowError(
            "Use Firebreak commands to change workflow records; restore damaged records from git."
        )
    for record in records:
        directory = unit_dir(root, record["unit"]).resolve()
        inside = path.relative_to(directory).parts if path.is_relative_to(directory) else ()
        if inside and inside[0] in RECORD_FOLDERS:
            raise WorkflowError(
                "Firebreak writes the writing-tests baseline, the saved check output, current and accepted, "
                "and the saved copies of locked tests itself; "
                "leave these folders to Firebreak commands."
            )
    owners = []
    for record in records:
        directory = unit_dir(root, record["unit"]).resolve()
        if path.is_relative_to(directory):
            owners.append(record)
        elif record["open_phase"] in {"breakdown", "implement"}:
            declared = evidence.scope(root, record["unit"])
            if evidence.matches(
                relative, declared["sources"] + declared["tests"] + declared["docs"]
            ):
                owners.append(record)
    if len(owners) > 1:
        # Nested unit documents belong to their deepest unit, shared source has no implicit winner.
        nested = [
            r
            for r in owners
            if path.is_relative_to(unit_dir(root, r["unit"]).resolve())
        ]
        if nested:
            owners = [max(nested, key=lambda r: len(Path(r["unit"]).parts))]
        else:
            raise WorkflowError(
                "Multiple open units claim this file; suspend conflicting work before writing."
            )
    owner = owners[0] if owners else (active[0] if active else None)
    if not owner:
        return
    if not owner["open_phase"] or owner["owner"] != session:
        raise WorkflowError(
            f"Unit {owner['unit']} has no phase owned by this session; enter or take over its phase first."
        )
    if owner.get("pending_repair"):
        raise WorkflowError("Finish or recover-repair before editing this unit.")
    if any(p["pending"] for p in owner["phases"].values()):
        raise WorkflowError(
            "A close is reviewing this unit; finish or recover it before edits."
        )
    inside = path.is_relative_to(unit_dir(root, owner["unit"]).resolve())
    # A region-bearing file is two things: its region is a scoped test and the code above
    # it a production file, so each rule below applies to the part the change touches.
    change = None if inside else _region_change(root, owner, relative, path, payload)
    # Accepted artifacts are edited only after an explicit reopen, irrespective of active phase.
    # The checkpoint accepted a region-bearing file's region only.
    for name, work in owner["phases"].items():
        if work["evidence"] and relative in work["evidence"]["files"] and not (
                name == evidence.CHECKPOINT and change is False):
            raise WorkflowError(
                "This artifact is accepted evidence; reopen its phase before changing it."
            )
    if inside:
        return
    if owner["open_phase"] != "implement":
        # Breakdown writes tasks only; tests and code are written by task workers in implement.
        raise WorkflowError(
            "Write phase artifacts now; enter implementation before editing repository source."
        )
    declared = evidence.scope(root, owner["unit"])
    if not evidence.matches(
        relative, declared["sources"] + declared["tests"] + declared["docs"]
    ):
        raise WorkflowError(
            "File is outside this unit's declared scope; revise the spec before expanding the work."
        )
    is_test = evidence.matches(relative, declared["tests"]) if change is None else change
    outcome = engine.test_outcome(root, owner)
    no_tests = outcome == "no-tests"
    if is_test and no_tests:
        # Before ownership, so every worker learns why a test cannot be written here.
        raise WorkflowError(
            f"{relative} would hold a scoped test, and this unit has no tests and no test tasks. Write it without "
            "the test or test region, or reopen breakdown to plan a test task for it."
        )
    handoff.check_task_write(owner, relative, payload.get("agent_id"), session)
    if relative in owner["locks"] and relative not in owner["unlocks"] and (change is None or is_test):
        raise WorkflowError(
            "Test is locked; obtain a scoped unlock before changing it."
        )
    if engine.implement_stage(root, owner) == "writing-code":
        if is_test and outcome == "preservation":
            # The preserved tests are locked, and no test task exists to add or rework one.
            raise WorkflowError(
                f"{relative} would hold a scoped test, and this unit's plan has no test task. Write it without "
                "the test or test region, or reopen breakdown to plan a test task for it."
            )
        if is_test:
            raise WorkflowError(
                "Tests are locked while code is written; obtain an unlock-test approval and rework the test through its test task."
            )
        # With no tests and no test tasks there is nothing to lock.
        if not no_tests:
            engine.verify_locks(root, owner)
        return
    # Writing tests: a test task's worker writes its declared tests and production
    # files. An implementation task still running from writing code keeps its
    # production ownership only during an approved unlock, and never writes tests.
    stages = {
        run.get("stage", "implementation")
        for run in owner.get("task_runs", {}).values()
        if run["status"] == "running" and run["worker_id"] == payload.get("agent_id")
    }
    if is_test and stages != {"tests"}:
        raise WorkflowError(
            "Implementation workers do not write tests; a test task writes them while the unit is writing tests."
        )
    if "tests" not in stages and not owner["unlocks"]:
        raise WorkflowError(
            "The tests are no longer accepted for writing code; run test-checkpoint and let it pass again "
            "before implementation workers write code."
        )


def handle(root, payload):
    if not enabled(root):
        return {}
    event_name = payload.get("hook_event_name")
    unit, phase = None, None
    try:
        project_config(root)
        tool = payload.get("tool_name")
        tool_input = payload.get("tool_input") or {}
        name = (
            payload.get("command_name", "")
            if event_name == "UserPromptExpansion"
            else tool_input.get("skill", "")
        )
        skill = name.rsplit(":", 1)[-1] if isinstance(name, str) else ""
        if skill in SKILLS and (
            event_name == "UserPromptExpansion"
            or event_name == "PreToolUse"
            and tool == "Skill"
        ):
            text = (
                payload.get("command_args")
                if event_name == "UserPromptExpansion"
                else tool_input.get("args")
            )
            unit, phase = _unit_arg(text), SKILLS[skill]
            if payload.get("agent_id"):
                raise WorkflowError(
                    "Workers inherit the current phase; the lead session enters phases."
                )
            if phase == "intent" and not (unit_dir(root, unit) / "state.json").exists():
                return _context(
                    event_name,
                    "Confirm the unit kind and parent, then run unit-init and phase-enter intent before authoring.",
                )
            with transaction(root):
                record = load(root, unit)
                try:
                    engine.enter(root, record, phase, payload.get("session_id"))
                except WorkflowError as exc:
                    if event_name != "UserPromptExpansion":
                        raise
                    record_event(root, payload, "recovery: " + str(exc), unit, phase)
                    return _context(
                        event_name,
                        f"Firebreak could not open {phase} for {unit}: {exc} "
                        f"Read continuation {unit}, resolve the reported prerequisite, "
                        f"then run phase-enter {phase} {unit} with this session identity. "
                        "The phase has not opened and this message grants no write authority. "
                        "Use existing operator authorization where applicable; phase observations "
                        "are the model's responsibility and need no opt-in.",
                    )
            output = _context(
                event_name,
                f"Firebreak 0.6.0: {unit}, {phase} is open. Use the state-driven workflow guide; close with phase-close. "
                + review_plan.context(record),
            )
        else:
            records = [load(root, u) for u in discover(root)]
            active = [
                r
                for r in records
                if r["owner"] == payload.get("session_id") and r["open_phase"]
            ]
            attributed = active
            if payload.get("agent_id"):
                matches = [
                    r
                    for r in active
                    if payload["agent_id"] in r["workers"]
                    or any(
                        run.get("worker_id") == payload["agent_id"]
                        and run.get("status") == "running"
                        for run in r.get("task_runs", {}).values()
                    )
                ]
                if matches:
                    attributed = matches
            if len(attributed) == 1:
                unit, phase = attributed[0]["unit"], attributed[0]["open_phase"]
            output = {}
            if (
                event_name in {"SubagentStart", "SubagentStop"}
                and unit is not None
                and payload.get("agent_id")
            ):
                with transaction(root):
                    record = load(root, unit)
                    record["workers"][payload["agent_id"]] = (
                        event_name == "SubagentStart"
                    )
                    save(root, record)
                if event_name == "SubagentStart":
                    assignment = next(
                        (
                            key
                            for key, run in record.get("task_runs", {}).items()
                            if run.get("worker_id") == payload["agent_id"]
                            and run.get("status") == "running"
                        ),
                        None,
                    )
                    packet = (
                        handoff.task_packet(root, record, assignment)
                        if assignment
                        else {
                            "unit": unit,
                            "phase": phase,
                            "next": f"Read continuation {unit}. Before implementation writes, obtain a task-start assignment with this worker identity: {payload['agent_id']}.",
                            "worker_id": payload["agent_id"],
                        }
                    )
                    telemetry.record_context(
                        root,
                        kind="hook-task" if assignment else "hook-worker",
                        packet=packet,
                        session=payload.get("session_id"),
                        unit=unit,
                        task=assignment,
                        worker=payload["agent_id"],
                    )
                    output = _context(
                        event_name,
                        "Firebreak worker context:\n"
                        + json.dumps(packet, ensure_ascii=False),
                    )
            elif (
                event_name == "PreToolUse" and tool in {"Agent", "Workflow"} and active
            ):
                if active[0].get("pending_repair"):
                    raise WorkflowError(
                        "Finish or recover-repair before starting workers."
                    )
                if any(p["pending"] for p in active[0]["phases"].values()):
                    raise WorkflowError(
                        "Finish or recover this close before starting more workers."
                    )
            elif event_name == "PreToolUse" and tool in {
                "Edit",
                "Write",
                "NotebookEdit",
            }:
                _write_check(root, payload, records)
            elif event_name == "Stop" and not payload.get("stop_hook_active"):
                from .retrospective import pending_phases, require_phase_observations

                session = payload.get("session_id")
                for record in records:
                    pending_observations = pending_phases(record)
                    if session and record.get("owner") in (None, session) and any(
                        item["session"] == session or record.get("owner") == session
                        for item in pending_observations
                    ):
                        unit, phase = record["unit"], pending_observations[0]["phase"]
                        require_phase_observations(record)
                if not active:
                    record_event(root, payload, "allow", unit, phase)
                    return {}
                status = engine.status_report(root, active[0])
                if status["human_review"]:
                    raise WorkflowError(status["next"] + " Suspend with a reason while awaiting the human.")
                raise WorkflowError(
                    f"Unit {unit}, {phase} remains open. Close it when verified; if waiting on the human, "
                    "state the question and suspend with a reason. Work stays recoverable."
                )
            elif event_name == "SessionStart":
                packet = handoff.session_context(
                    root, records, payload.get("session_id")
                )
                if packet:
                    telemetry.record_context(
                        root,
                        kind="hook-continuation",
                        packet=packet,
                        session=payload.get("session_id"),
                        unit=packet.get("unit"),
                    )
                    output = _context(
                        event_name,
                        "Firebreak continuation:\n"
                        + json.dumps(packet, ensure_ascii=False),
                    )
        record_event(root, payload, "allow", unit, phase)
        return output
    except (WorkflowError, OSError, ValueError, TypeError, KeyError) as exc:
        record_event(root, payload, "deny: " + str(exc), unit, phase)
        if event_name in {"PreToolUse", "UserPromptExpansion", "Stop"}:
            if event_name == "Stop" and payload.get("stop_hook_active"):
                return {}
            return _deny(event_name, str(exc))
        return (
            _context(event_name, "Firebreak needs attention: " + str(exc))
            if event_name in {"SessionStart", "SubagentStart"}
            else {}
        )


def main():
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise TypeError("expected a hook object")
        root = project_root(
            os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or Path.cwd()
        )
        result = handle(root, payload)
        if result:
            print(json.dumps(result))
        return 0
    except (ValueError, TypeError, OSError, WorkflowError) as exc:
        print(f"Firebreak hook input failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
