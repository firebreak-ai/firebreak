"""Human and agent entry points share the same engine as the hook adapter."""

import argparse
import json
import os
import sys
from pathlib import Path

from . import COMMANDS, close, engine, evidence, handoff, review_plan
from .store import (
    WorkflowError,
    atomic_json,
    confined,
    discover,
    enabled,
    ensure_ignored,
    load,
    project_config,
    project_root,
    read_json,
    save,
    transaction,
)


def parser_for(command):
    parser = argparse.ArgumentParser(prog=f"fbk.py {command}")
    parser.add_argument(
        "--root", default=None, help="Repository root (otherwise discovered from cwd)"
    )
    parser.add_argument(
        "--session",
        default=os.environ.get("CLAUDE_CODE_SESSION_ID")
        or os.environ.get("FBK_SESSION_ID", "terminal"),
    )
    if command not in {"workflow-init", "workflow-hook", "doctor", "review-default"}:
        if command in {"phase-enter", "phase-close"}:
            parser.add_argument("phase", choices=evidence.PHASES)
        if command in {"recover-close", "extend-review"}:
            # A review's budget and reservation: a phase's, or the test checkpoint's.
            parser.add_argument("phase", choices=evidence.REVIEWS)
        parser.add_argument(
            "unit", nargs="?" if command in {"status", "workflow-report"} else None
        )
    if command == "unit-init":
        parser.add_argument("--kind", choices=["project", "feature"], default="feature")
        parser.add_argument("--parent")
        parser.add_argument("--design", choices=["on", "off"], default="on")
    if command in {
        "approve",
        "route",
        "phase-close",
        "takeover",
        "suspend",
        "acknowledge-parent",
        "recover-close",
        "extend-review",
        "review-plan",
        "review-default",
        "recover-repair",
        "task-cancel",
    }:
        parser.add_argument("--reason", default="")
    if command in {"review-plan", "review-default"}:
        parser.add_argument("--phase", required=True, choices=review_plan.PHASES)
        parser.add_argument("--mode", required=True, choices=["single", "council"])
        parser.add_argument(
            "--members", nargs="*", default=[], choices=review_plan.MEMBERS
        )
    if command == "phase-close":
        parser.add_argument("--reopen", action="store_true")
    if command == "workflow-report":
        parser.add_argument(
            "--history",
            action="store_true",
            help="Expand all audit events and review attempts",
        )
    if command == "continuation":
        parser.add_argument(
            "--section",
            choices=["decisions", "tasks", "sources", "pending", "accepted_reviews", "undispositioned_suggestions"],
            help="Retrieve one complete omitted context section",
        )
    if command == "retrospective":
        parser.add_argument(
            "--section",
            choices=[
                "events",
                "phases",
                "observations",
                "decisions",
                "grants",
                "tasks",
                "review_plans",
                "files",
                "capture",
            ],
        )
        parser.add_argument(
            "--index", help="One entry, numbered from 1, or its exact reference"
        )
        parser.add_argument(
            "--pointer",
            help="JSON Pointer into the selected historical entry, such as /value/rounds/0/result/review/findings/0; a negative list index such as /value/rounds/-1 counts from the end",
        )
        parser.add_argument(
            "--offset",
            type=int,
            help="Page a section index: skip this many entries, or with a negative value start this many entries before the end",
        )
        parser.add_argument(
            "--max-chars",
            type=int,
            default=12000,
            help="Output bound in characters, 2000 to 100000 (default 12000)",
        )
    if command == "improvement-report":
        parser.add_argument("--index", type=int, help="One proposal, numbered from 1")
    if command in {"current-findings", "workflow-report"}:
        parser.add_argument("--phase", choices=evidence.REVIEWS)
    if command == "current-findings":
        parser.add_argument(
            "--index",
            type=int,
            help="One finding, numbered from 1 in the current attempt",
        )
    if command in {"task-start", "task-finish", "task-context", "task-cancel"}:
        parser.add_argument("task")
    if command == "task-start":
        parser.add_argument("--worker", required=True)
        parser.add_argument("--outcome")
        parser.add_argument("--acceptance-refs", nargs="+")
        parser.add_argument("--input-refs", nargs="+")
    if command == "task-finish":
        parser.add_argument(
            "--result",
            required=True,
            help="Repository-relative JSON handoff result file",
        )
    if command in {
        "decision-record",
        "decision-annotate",
        "repair-policy",
        "repair",
        "observation-record",
        "improvement-record",
    }:
        parser.add_argument(
            "--request", required=True, help="Repository-relative JSON request file"
        )
    if command == "approve":
        parser.add_argument(
            "crossing",
            choices=[
                "start-implementation",
                "reopen",
                "unlock-test",
                "close-over-findings",
            ],
        )
        parser.add_argument("--phase", required=True, choices=evidence.REVIEWS)
        parser.add_argument("--tests", nargs="*", default=[])
        parser.add_argument(
            "--request",
            help="Repository-relative JSON file with an unlock's rework: "
            '{"expected": {test: "fail" or "pass"}, "commands": [{"argv": [...], "tests": [...]}]}',
        )
    if command == "restore-locked-tests":
        parser.add_argument("--tests", nargs="+", required=True,
                            help="Locked tests to replace with their saved copies")
    if command == "route":
        parser.add_argument("--design", required=True, choices=["on", "off"])
    if command == "extend-review":
        parser.add_argument("--rounds", type=int, default=1)
    return parser


def execute(command, args):
    root = Path(args.root).resolve() if args.root else project_root(Path.cwd())
    if command == "workflow-hook":
        from .hooks import main as hook_main

        return hook_main()
    if command == "workflow-init":
        with transaction(root):
            path = confined(root, ".fbk/config.json")
            if not path.exists():
                atomic_json(
                    path,
                    {
                        "schema_version": 1,
                        "reviewer_model": "opus",
                        "reviewer_max_turns": 100,
                        "review_timeout": 1200,
                        "reviewer_effort": "medium",
                        "check_timeout": 300,
                    },
                )
            # An existing project gains entries added since it was initialized.
            ensure_ignored(root)
        return {
            "root": str(root),
            "workflow": "0.6.0",
            "next": "Create a unit with unit-init.",
        }
    if command == "doctor":
        import shutil
        import subprocess

        binary = shutil.which("claude")
        try:
            version = (
                subprocess.run(
                    [binary, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=True,
                ).stdout.strip()
                if binary
                else None
            )
        except (OSError, subprocess.SubprocessError):
            version = None
        return {
            "root": str(root),
            "enabled": enabled(root),
            "claude": version,
            "runtime": sys.version.split()[0],
            "workflow": "0.6.0",
            "notes": [
                "Direct slash-command entry uses UserPromptExpansion; verify on the installed host.",
                "Command-hook timeouts and shell/external writes are prevention gaps.",
            ],
        }
    project_config(root)
    if command == "review-default":
        selected = review_plan.choice(args.mode, args.members, args.reason, "project")
        with transaction(root):
            config = project_config(root)
            review_plan.defaults(root)
            config.setdefault("review_defaults", {})[args.phase] = {
                k: selected[k] for k in ("mode", "members", "reason")
            }
            atomic_json(confined(root, ".fbk/config.json"), config)
        return {
            "phase": args.phase,
            "default": config["review_defaults"][args.phase],
            "next": "Applies to new units and unresolved choices at phase entry; existing selections stay unchanged.",
        }
    if command in {
        "status",
        "workflow-report",
        "continuation",
        "current-findings",
        "task-context",
        "retrospective",
        "improvement-report",
    }:
        # Atomic record replacement gives readers a complete snapshot without
        # queuing behind (or delaying) a correctness-critical commit.
        units = [args.unit] if args.unit else discover(root)
        records = [load(root, u) for u in units]
        from . import telemetry

        if command == "status":
            return [engine.status_report(root, r) for r in records]
        if command == "retrospective":
            from . import retrospective

            return retrospective.packet(
                root,
                records[0],
                section=args.section,
                index=args.index,
                pointer=args.pointer,
                max_chars=args.max_chars,
                offset=args.offset,
            )
        if command == "improvement-report":
            from . import improvement

            return improvement.report(root, records[0], index=args.index)
        if command == "continuation":
            if args.section:
                view = handoff.continuation(root, records[0], max_chars=float("inf"))
                packet = {
                    "unit": records[0]["unit"],
                    "phase": view["phase"],
                    args.section: view.get(args.section),
                }
            else:
                packet = handoff.continuation(root, records[0])
            telemetry.record_context(
                root,
                kind="continuation",
                packet=packet,
                session=args.session,
                unit=args.unit,
                section=args.section,
            )
            return packet
        if command == "task-context":
            packet = handoff.task_packet(root, records[0], args.task)
            telemetry.record_context(
                root,
                kind="task-context",
                packet=packet,
                session=args.session,
                unit=args.unit,
                task=args.task,
            )
            return packet
        if command == "current-findings":
            packet = _findings(root, records[0], args.phase, args.index)
            telemetry.record_context(
                root,
                kind="current-findings",
                packet=packet,
                session=args.session,
                unit=args.unit,
                section=str(args.index) if args.index is not None else None,
            )
            return packet
        if not args.history:
            return [
                {
                    "unit": r["unit"],
                    "status": engine.status_report(root, r),
                    "continuation": handoff.continuation(root, r),
                    "current_findings": f"current-findings {r['unit']}"
                    + (f" --phase {args.phase}" if args.phase else ""),
                    "history": f"workflow-report {r['unit']} --history",
                    "usage_boundary": "Headless review usage only; authoring-session usage is not measured.",
                    "capture_health": telemetry.capture_health(root),
                    "retrospective": f"retrospective {r['unit']}",
                    "improvements": f"improvement-report {r['unit']}",
                }
                for r in records
            ]
        return [
            {
                "unit": r["unit"],
                "status": engine.status_report(root, r),
                "events": r["events"],
                "review_rounds": {
                    p: v["rounds"]
                    for p, v in r["phases"].items()
                    if not args.phase or p == args.phase
                },
                "usage_boundary": "Headless review usage only; authoring-session usage is not measured.",
                "capture_health": telemetry.capture_health(root),
            }
            for r in records
        ]
    if command == "phase-close" and not args.reopen:
        result = close.close_phase(root, args.unit, args.phase, args.session)
        if result.get("status") in {"closed", "retrospective-required"}:
            result["improvements"] = f"improvement-report {args.unit}"
        return result
    if command == "test-checkpoint":
        return close.close_checkpoint(root, args.unit, args.session)
    if command in {"repair", "recover-repair"}:
        from . import repair

        if command == "repair":
            return repair.apply(
                root, args.unit, args.session, _request(root, args.request)
            )
        return repair.recover(root, args.unit, args.session, args.reason)
    if command == "task-finish":
        result = _request(root, args.result)
        if set(result) != {"changed_files", "checks", "unresolved", "outcome"}:
            raise WorkflowError(
                "Task result needs changed_files, checks, unresolved, and outcome."
            )
        return handoff.complete_task(root, args.unit, args.session, args.task, **result)
    with transaction(root):
        if command == "unit-init":
            record = engine.initialize(
                root, args.unit, args.kind, args.parent, args.design == "on"
            )
            return engine.status_report(root, record)
        record = load(root, args.unit)
        if command in {"observation-record", "improvement-record"}:
            from . import retrospective

            retrospective.require_writer(record, args.session)
            if record.get("pending_repair") or any(
                p.get("pending") for p in record["phases"].values()
            ):
                raise WorkflowError(
                    "Finish or recover the pending operation before recording retrospective work."
                )
            request = _request(root, args.request)
            if command == "observation-record":
                result = retrospective.record_observation(
                    root, record, args.session, request
                )
            else:
                from . import improvement

                action = request.pop("action", None)
                operations = {
                    "propose": improvement.record_proposal,
                    "adopt": improvement.record_adoption,
                    "evaluate": improvement.record_evaluation,
                    "decision": improvement.record_decision,
                }
                if action not in operations:
                    raise WorkflowError(
                        "Improvement action must be propose, adopt, evaluate, or decision."
                    )
                result = operations[action](root, record, args.session, request)
            save(root, record)
            return result
        if record.get("pending_repair") and command != "takeover":
            raise WorkflowError(
                "A repair is pending; use recover-repair before changing this unit."
            )
        if command in {"decision-record", "decision-annotate", "repair-policy"}:
            from . import decisions

            operation = {"decision-record": decisions.record,
                         "decision-annotate": decisions.annotate,
                         "repair-policy": decisions.policy}[command]
            result = operation(root, record, args.session, _request(root, args.request))
            save(root, record)
            if command == "decision-record":
                return {**result, "workflow": engine.status_report(root, record)}
            return result
        if command == "task-start":
            packet = handoff.start_task(
                root,
                record,
                args.session,
                args.task,
                args.worker,
                outcome=args.outcome,
                acceptance_refs=args.acceptance_refs,
                input_refs=args.input_refs,
            )
            from . import telemetry

            telemetry.record_context(
                root,
                kind="task-start",
                packet=packet,
                session=args.session,
                unit=args.unit,
                task=args.task,
                worker=args.worker,
            )
            return packet
        if command == "restore-locked-tests":
            from .test_preparation import restore_locked_tests

            result = restore_locked_tests(root, record, args.session, args.tests)
            save(root, record)
            return result
        if command == "task-cancel":
            return handoff.cancel_task(
                root, record, args.session, args.task, args.reason
            )
        if command == "review-plan":
            return review_plan.select(
                root,
                record,
                args.phase,
                args.mode,
                args.members,
                args.reason,
                args.session,
            )
        if command == "phase-enter":
            return engine.enter(root, record, args.phase, args.session)
        if command == "phase-close":
            return engine.reopen(root, record, args.phase, args.session, args.reason)
        if command == "approve":
            return engine.approve(
                root,
                record,
                args.session,
                args.crossing,
                args.phase,
                args.reason,
                args.tests,
                _request(root, args.request) if args.request else None,
            )
        if command == "route":
            engine.route(root, record, args.session, args.design == "on", args.reason)
        elif command == "takeover":
            engine.takeover(root, record, args.session, args.reason)
        elif command == "suspend":
            engine.suspend(root, record, args.session, args.reason)
        elif command == "acknowledge-parent":
            engine.acknowledge_parent(root, record, args.session, args.reason)
        elif command == "recover-close":
            close.recover(root, record, args.phase, args.session, args.reason)
        elif command == "extend-review":
            close.extend_review(
                root, record, args.phase, args.session, args.reason, args.rounds
            )
        return engine.status_report(root, record)


def _request(root, path):
    request = read_json(confined(root, path))
    if not isinstance(request, dict):
        raise WorkflowError("Request must be a JSON object.")
    return request


def _findings(root, record, phase=None, index=None):
    if not phase and record.get("open_phase"):
        phase = engine.review_in_focus(root, record, record["open_phase"])
    phase = phase or engine.phase_state(root, record)[0]
    if phase == "closed":
        phase = evidence.phases(record)[-1]
    result = handoff.current_findings(record, phase)
    result["current"] = handoff.findings_are_current(root, record, phase, result)
    if index is not None:
        if not 1 <= index <= len(result["findings"]):
            raise WorkflowError(
                "Finding index is outside the current attempt's findings."
            )
        result["findings"] = [result["findings"][index - 1]]
    else:
        result["finding_count"] = len(result["findings"])
        selected = []
        for finding in result["findings"]:
            if (
                selected
                and len(json.dumps([*selected, finding], ensure_ascii=False)) > 10000
            ):
                break
            selected.append(finding)
        result["findings"] = selected
        if len(selected) < result["finding_count"]:
            result["omitted_findings"] = result["finding_count"] - len(selected)
            result["next"] = (
                f"current-findings {record['unit']} --phase {phase} --index {len(selected) + 1}"
            )
    return result


def main():
    command = Path(sys.argv[0]).name
    argv = sys.argv[1:]
    if command not in COMMANDS:
        if not argv or argv[0] not in COMMANDS:
            print("Commands: " + ", ".join(COMMANDS), file=sys.stderr)
            return 2
        command, argv = argv[0], argv[1:]
    args = parser_for(command).parse_args(argv)
    try:
        result = execute(command, args)
        if command != "workflow-hook":
            print(json.dumps(result, indent=2, ensure_ascii=False))
        return result if command == "workflow-hook" else 0
    except (WorkflowError, OSError) as exc:
        print(
            json.dumps({"error": str(exc), "command": command}, ensure_ascii=False),
            file=sys.stderr,
        )
        return getattr(exc, "code", 2)


if __name__ == "__main__":
    sys.exit(main())
