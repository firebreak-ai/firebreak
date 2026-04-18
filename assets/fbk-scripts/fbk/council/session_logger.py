#!/usr/bin/env python3
"""
Council Session Logger

Tracks phase timing, agent contributions, tool usage, token metrics, permissions, and outcomes.
Writes session logs to ~/.claude/council-logs/<session-id>.json

Usage:
    # Initialize session
    python session-logger.py init <session-id> [--tier quick|full] [--task "description"]

    # Log phase start/end
    python session-logger.py phase-start <session-id> <phase-name>
    python session-logger.py phase-end <session-id> <phase-name>

    # Log agent contribution (with full content via stdin)
    echo "Full discussion content" | python session-logger.py contribution <session-id> <agent-name> <phase> [--input-tokens N] [--output-tokens N]

    # Log agent contribution (legacy mode - char count only)
    python session-logger.py contribution <session-id> <agent-name> <phase> --chars <count>

    # Log tool usage
    python session-logger.py tool-use <session-id> <agent-name> <tool-name> [--target "path/or/description"] [--success] [--duration-ms N]

    # Log permission request (called from permissions hook)
    python session-logger.py permission-request <tool-name> --decision <auto_approved|user_approved|user_denied|ask> [--context "path/cmd"] [--rule "rule_name"]

    # Log outcome
    python session-logger.py outcome <session-id> --protocol <voting|consensus> --result "description" [--dissent]

    # Finalize session (merges permission logs into timeline)
    python session-logger.py finalize <session-id>

    # Show session data
    python session-logger.py show <session-id> [--timeline] [--agent NAME] [--type TYPE]
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Schema version for backward compatibility
SCHEMA_VERSION = 2

LOG_DIR = Path.home() / '.claude' / 'council-logs'
PERMISSIONS_LOG = Path.home() / '.claude' / 'council-logs' / 'council-permissions.jsonl'


def get_log_path(session_id: str) -> Path:
    """Get the log file path for a session."""
    return LOG_DIR / f"{session_id}.json"


def load_session(session_id: str) -> dict:
    """Load existing session data or return empty dict."""
    log_path = get_log_path(session_id)
    if log_path.exists():
        with open(log_path, 'r') as f:
            return json.load(f)
    return {}


def save_session(session_id: str, data: dict) -> None:
    """Save session data to log file with restrictive permissions."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = get_log_path(session_id)

    # Write to temp file first, then rename for atomicity
    temp_path = log_path.with_suffix('.tmp')
    with open(temp_path, 'w') as f:
        json.dump(data, f, indent=2)

    # Set restrictive permissions (owner read/write only)
    os.chmod(temp_path, 0o600)

    # Atomic rename
    temp_path.rename(log_path)


def add_timeline_event(data: dict, event: dict) -> None:
    """Add an event to the chronological timeline."""
    if "timeline" not in data:
        data["timeline"] = []

    event["timestamp"] = datetime.now().isoformat()
    data["timeline"].append(event)


def update_token_summary(data: dict, agent: str, input_tokens: int, output_tokens: int) -> None:
    """Update the running token totals."""
    if "token_summary" not in data:
        data["token_summary"] = {
            "by_agent": {},
            "total_input": 0,
            "total_output": 0
        }

    summary = data["token_summary"]

    if agent not in summary["by_agent"]:
        summary["by_agent"][agent] = {"input": 0, "output": 0}

    summary["by_agent"][agent]["input"] += input_tokens
    summary["by_agent"][agent]["output"] += output_tokens
    summary["total_input"] += input_tokens
    summary["total_output"] += output_tokens


def cmd_init(args) -> None:
    """Initialize a new session."""
    session_data = {
        "schema_version": SCHEMA_VERSION,
        "session_id": args.session_id,
        "started_at": datetime.now().isoformat(),
        "tier": args.tier or "full",
        "task_summary": args.task or "",
        "task_type": None,
        "decision_protocol": None,
        "phases": [],
        "timeline": [],
        "agents": {},
        "token_summary": {
            "by_agent": {},
            "total_input": 0,
            "total_output": 0
        },
        "outcome": None,
        "completed_at": None
    }
    save_session(args.session_id, session_data)
    print(json.dumps({"status": "initialized", "session_id": args.session_id}))


def cmd_phase_start(args) -> None:
    """Log the start of a phase."""
    data = load_session(args.session_id)
    if not data:
        print(json.dumps({"error": "Session not found"}), file=sys.stderr)
        sys.exit(1)

    # Check if phase already exists and is incomplete
    for phase in data.get("phases", []):
        if phase["name"] == args.phase_name and phase.get("ended_at") is None:
            print(json.dumps({"status": "already_started", "phase": args.phase_name}))
            return

    phase_data = {
        "name": args.phase_name,
        "started_at": datetime.now().isoformat(),
        "ended_at": None,
        "duration_seconds": None
    }
    data.setdefault("phases", []).append(phase_data)

    # Also add to timeline
    add_timeline_event(data, {
        "type": "phase_start",
        "phase": args.phase_name
    })

    save_session(args.session_id, data)
    print(json.dumps({"status": "phase_started", "phase": args.phase_name}))


def cmd_phase_end(args) -> None:
    """Log the end of a phase."""
    data = load_session(args.session_id)
    if not data:
        print(json.dumps({"error": "Session not found"}), file=sys.stderr)
        sys.exit(1)

    for phase in data.get("phases", []):
        if phase["name"] == args.phase_name and phase.get("ended_at") is None:
            phase["ended_at"] = datetime.now().isoformat()
            start = datetime.fromisoformat(phase["started_at"])
            end = datetime.fromisoformat(phase["ended_at"])
            phase["duration_seconds"] = round((end - start).total_seconds(), 2)

            # Also add to timeline
            add_timeline_event(data, {
                "type": "phase_end",
                "phase": args.phase_name,
                "duration_seconds": phase["duration_seconds"]
            })

            save_session(args.session_id, data)
            print(json.dumps({
                "status": "phase_ended",
                "phase": args.phase_name,
                "duration_seconds": phase["duration_seconds"]
            }))
            return

    print(json.dumps({"error": "Phase not found or already ended"}), file=sys.stderr)


def cmd_contribution(args) -> None:
    """Log an agent contribution with optional full content."""
    data = load_session(args.session_id)
    if not data:
        print(json.dumps({"error": "Session not found"}), file=sys.stderr)
        sys.exit(1)

    # Get content from stdin if available, otherwise use legacy char_count mode
    content = None
    char_count = args.chars or 0

    if not sys.stdin.isatty():
        content = sys.stdin.read()
        char_count = len(content)

    # Update agent aggregates (backward compatible)
    agents = data.setdefault("agents", {})
    agent = agents.setdefault(args.agent_name, {
        "total_contributions": 0,
        "total_characters": 0,
        "by_phase": {}
    })

    agent["total_contributions"] += 1
    agent["total_characters"] += char_count
    phase_contributions = agent["by_phase"].setdefault(args.phase, 0)
    agent["by_phase"][args.phase] = phase_contributions + 1

    # Build timeline event
    event = {
        "type": "contribution",
        "agent": args.agent_name,
        "phase": args.phase,
        "char_count": char_count
    }

    if content is not None:
        event["content"] = content

    if args.input_tokens:
        event["input_tokens"] = args.input_tokens
    if args.output_tokens:
        event["output_tokens"] = args.output_tokens

    # Update token summary if tokens provided
    input_tokens = args.input_tokens or 0
    output_tokens = args.output_tokens or 0
    if input_tokens or output_tokens:
        update_token_summary(data, args.agent_name, input_tokens, output_tokens)

    add_timeline_event(data, event)
    save_session(args.session_id, data)

    print(json.dumps({
        "status": "contribution_logged",
        "agent": args.agent_name,
        "phase": args.phase,
        "char_count": char_count,
        "has_content": content is not None,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens
    }))


def cmd_tool_use(args) -> None:
    """Log an agent's tool usage."""
    data = load_session(args.session_id)
    if not data:
        print(json.dumps({"error": "Session not found"}), file=sys.stderr)
        sys.exit(1)

    event = {
        "type": "tool_use",
        "agent": args.agent_name,
        "tool": args.tool_name,
        "success": args.success
    }

    if args.target:
        event["target"] = args.target
    if args.duration_ms:
        event["duration_ms"] = args.duration_ms

    add_timeline_event(data, event)
    save_session(args.session_id, data)

    print(json.dumps({
        "status": "tool_use_logged",
        "agent": args.agent_name,
        "tool": args.tool_name,
        "success": args.success
    }))


def cmd_permission_request(args) -> None:
    """Log a permission request (called from permissions hook)."""
    # This command appends to a separate JSONL file for atomic writes
    # The finalize command merges these into the session timeline
    event = {
        "type": "permission_request",
        "timestamp": datetime.now().isoformat(),
        "tool_name": args.tool_name,
        "decision": args.decision,
        "rule_matched": args.rule or "unknown"
    }

    if args.context:
        # Truncate context to 200 chars for readability
        event["context"] = args.context[:200] if len(args.context) > 200 else args.context

    try:
        # Append to JSONL file (one JSON object per line)
        with open(PERMISSIONS_LOG, 'a') as f:
            f.write(json.dumps(event) + '\n')
        print(json.dumps({"status": "permission_logged", "tool": args.tool_name, "decision": args.decision}))
    except Exception as e:
        # Logging should never fail the permission decision
        print(json.dumps({"status": "logging_failed", "error": str(e)}), file=sys.stderr)


def cmd_outcome(args) -> None:
    """Log the session outcome."""
    data = load_session(args.session_id)
    if not data:
        print(json.dumps({"error": "Session not found"}), file=sys.stderr)
        sys.exit(1)

    data["decision_protocol"] = args.protocol
    data["outcome"] = {
        "result": args.result,
        "had_dissent": args.dissent
    }

    add_timeline_event(data, {
        "type": "outcome",
        "protocol": args.protocol,
        "result": args.result,
        "had_dissent": args.dissent
    })

    save_session(args.session_id, data)
    print(json.dumps({
        "status": "outcome_logged",
        "protocol": args.protocol,
        "had_dissent": args.dissent
    }))


def cmd_self_eval(args) -> None:
    """Log council self-evaluation with optional improvement proposals."""
    data = load_session(args.session_id)
    if not data:
        print(json.dumps({"error": "Session not found"}), file=sys.stderr)
        sys.exit(1)

    # Parse worked and friction items (can be comma-separated or multiple flags)
    worked_items = []
    friction_items = []

    if args.worked:
        for item in args.worked:
            worked_items.extend([x.strip() for x in item.split(',') if x.strip()])

    if args.friction:
        for item in args.friction:
            friction_items.extend([x.strip() for x in item.split(',') if x.strip()])

    # Build self-evaluation structure
    self_eval = {
        "what_worked": worked_items,
        "friction_points": friction_items,
        "confidence": args.confidence or 0.5,
        "proposals": []
    }

    # Handle proposals
    if args.proposal:
        for i, prop_text in enumerate(args.proposal):
            proposal = {
                "id": f"{args.session_id}-prop-{i+1}",
                "description": prop_text,
                "risk_level": args.risk or "SAFE",
                "target_file": args.target or None,
                "blocked_by_immutable_core": args.blocked_by_immutable_core or False
            }
            self_eval["proposals"].append(proposal)

    # Store in session data
    data["self_evaluation"] = self_eval

    # Add to timeline
    add_timeline_event(data, {
        "type": "self_evaluation",
        "worked_count": len(worked_items),
        "friction_count": len(friction_items),
        "proposal_count": len(self_eval["proposals"]),
        "confidence": self_eval["confidence"],
        "has_actionable_proposals": len(self_eval["proposals"]) > 0 and self_eval["confidence"] >= 0.7
    })

    save_session(args.session_id, data)

    # Determine if proposals should be surfaced
    should_surface = (
        len(self_eval["proposals"]) > 0 and
        self_eval["confidence"] >= 0.7 and
        not any(p.get("blocked_by_immutable_core") for p in self_eval["proposals"])
    )

    print(json.dumps({
        "status": "self_eval_logged",
        "worked_count": len(worked_items),
        "friction_count": len(friction_items),
        "proposal_count": len(self_eval["proposals"]),
        "confidence": self_eval["confidence"],
        "should_surface_to_user": should_surface
    }))


def merge_permissions_log(data: dict) -> int:
    """Merge permission events from JSONL into session timeline. Returns count merged."""
    if not PERMISSIONS_LOG.exists():
        return 0

    permissions = []
    try:
        with open(PERMISSIONS_LOG, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    permissions.append(json.loads(line))
    except Exception:
        return 0

    if not permissions:
        return 0

    # Get session time bounds
    started_at = data.get("started_at")
    if not started_at:
        return 0

    session_start = datetime.fromisoformat(started_at)
    session_end = datetime.now()

    # Filter permissions to those within this session's timeframe
    session_permissions = []
    for perm in permissions:
        try:
            perm_time = datetime.fromisoformat(perm["timestamp"])
            if session_start <= perm_time <= session_end:
                session_permissions.append(perm)
        except (KeyError, ValueError):
            continue

    # Add to timeline
    timeline = data.setdefault("timeline", [])
    timeline.extend(session_permissions)

    # Sort timeline by timestamp
    timeline.sort(key=lambda e: e.get("timestamp", ""))

    # Build permissions summary
    if session_permissions:
        perm_summary = {"by_decision": {}, "by_tool": {}, "total": len(session_permissions)}
        for perm in session_permissions:
            decision = perm.get("decision", "unknown")
            tool = perm.get("tool_name", "unknown")
            perm_summary["by_decision"][decision] = perm_summary["by_decision"].get(decision, 0) + 1
            perm_summary["by_tool"][tool] = perm_summary["by_tool"].get(tool, 0) + 1
        data["permissions_summary"] = perm_summary

    return len(session_permissions)


def cmd_finalize(args) -> None:
    """Finalize and close the session."""
    data = load_session(args.session_id)
    if not data:
        print(json.dumps({"error": "Session not found"}), file=sys.stderr)
        sys.exit(1)

    data["completed_at"] = datetime.now().isoformat()

    # Merge permission events from the separate JSONL log
    permissions_merged = merge_permissions_log(data)

    # Calculate total duration
    if data.get("started_at"):
        start = datetime.fromisoformat(data["started_at"])
        end = datetime.fromisoformat(data["completed_at"])
        data["total_duration_seconds"] = round((end - start).total_seconds(), 2)

    add_timeline_event(data, {
        "type": "session_finalized",
        "total_duration_seconds": data.get("total_duration_seconds"),
        "permissions_merged": permissions_merged
    })

    save_session(args.session_id, data)

    # Clear the permissions log after successful merge
    if permissions_merged > 0:
        try:
            PERMISSIONS_LOG.unlink()
        except Exception:
            pass

    print(json.dumps({
        "status": "finalized",
        "session_id": args.session_id,
        "total_duration_seconds": data.get("total_duration_seconds"),
        "permissions_merged": permissions_merged
    }))


def cmd_show(args) -> None:
    """Display session data with optional filtering."""
    data = load_session(args.session_id)
    if not data:
        print(json.dumps({"error": "Session not found"}), file=sys.stderr)
        sys.exit(1)

    # If timeline view requested, filter and format
    if args.timeline:
        timeline = data.get("timeline", [])

        # Filter by agent if specified
        if args.agent:
            timeline = [e for e in timeline if e.get("agent") == args.agent]

        # Filter by event type if specified
        if args.type:
            timeline = [e for e in timeline if e.get("type") == args.type]

        print(json.dumps(timeline, indent=2))
    else:
        print(json.dumps(data, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Council Session Logger")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # init
    init_parser = subparsers.add_parser("init", help="Initialize a new session")
    init_parser.add_argument("session_id", help="Unique session identifier")
    init_parser.add_argument("--tier", choices=["quick", "full"], help="Council tier")
    init_parser.add_argument("--task", help="Task description")
    init_parser.set_defaults(func=cmd_init)

    # phase-start
    ps_parser = subparsers.add_parser("phase-start", help="Log phase start")
    ps_parser.add_argument("session_id", help="Session identifier")
    ps_parser.add_argument("phase_name", help="Phase name")
    ps_parser.set_defaults(func=cmd_phase_start)

    # phase-end
    pe_parser = subparsers.add_parser("phase-end", help="Log phase end")
    pe_parser.add_argument("session_id", help="Session identifier")
    pe_parser.add_argument("phase_name", help="Phase name")
    pe_parser.set_defaults(func=cmd_phase_end)

    # contribution (enhanced)
    contrib_parser = subparsers.add_parser("contribution", help="Log agent contribution")
    contrib_parser.add_argument("session_id", help="Session identifier")
    contrib_parser.add_argument("agent_name", help="Agent name")
    contrib_parser.add_argument("phase", help="Phase name")
    contrib_parser.add_argument("--chars", type=int, help="Character count (legacy mode)")
    contrib_parser.add_argument("--input-tokens", type=int, help="Input tokens used")
    contrib_parser.add_argument("--output-tokens", type=int, help="Output tokens generated")
    contrib_parser.set_defaults(func=cmd_contribution)

    # tool-use (new)
    tool_parser = subparsers.add_parser("tool-use", help="Log agent tool usage")
    tool_parser.add_argument("session_id", help="Session identifier")
    tool_parser.add_argument("agent_name", help="Agent name")
    tool_parser.add_argument("tool_name", help="Tool name (e.g., Read, Grep, Bash)")
    tool_parser.add_argument("--target", help="Tool target (file path, search query, etc.)")
    tool_parser.add_argument("--success", action="store_true", default=True, help="Tool call succeeded")
    tool_parser.add_argument("--failed", action="store_true", help="Tool call failed")
    tool_parser.add_argument("--duration-ms", type=int, help="Tool execution duration in ms")
    tool_parser.set_defaults(func=lambda a: cmd_tool_use(argparse.Namespace(
        session_id=a.session_id,
        agent_name=a.agent_name,
        tool_name=a.tool_name,
        target=a.target,
        success=not a.failed,
        duration_ms=a.duration_ms
    )))

    # permission-request (for hook integration)
    perm_parser = subparsers.add_parser("permission-request", help="Log permission request")
    perm_parser.add_argument("tool_name", help="Tool that triggered the permission request")
    perm_parser.add_argument("--decision", required=True,
                             choices=["auto_approved", "user_approved", "user_denied", "ask"],
                             help="Permission decision")
    perm_parser.add_argument("--context", help="Context (file path, command, etc.)")
    perm_parser.add_argument("--rule", help="Rule that matched (e.g., council_research, safe_path)")
    perm_parser.set_defaults(func=cmd_permission_request)

    # outcome
    outcome_parser = subparsers.add_parser("outcome", help="Log session outcome")
    outcome_parser.add_argument("session_id", help="Session identifier")
    outcome_parser.add_argument("--protocol", required=True, choices=["voting", "consensus", "unanimous"],
                                help="Decision protocol used")
    outcome_parser.add_argument("--result", required=True, help="Outcome description")
    outcome_parser.add_argument("--dissent", action="store_true", help="Had dissenting views")
    outcome_parser.set_defaults(func=cmd_outcome)

    # self-eval (council self-evaluation)
    selfeval_parser = subparsers.add_parser("self-eval", help="Log council self-evaluation")
    selfeval_parser.add_argument("session_id", help="Session identifier")
    selfeval_parser.add_argument("--worked", action="append", help="What worked well (can be repeated)")
    selfeval_parser.add_argument("--friction", action="append", help="Friction points encountered (can be repeated)")
    selfeval_parser.add_argument("--proposal", action="append", help="Improvement proposal description (can be repeated)")
    selfeval_parser.add_argument("--confidence", type=float, help="Confidence in evaluation (0.0-1.0)")
    selfeval_parser.add_argument("--risk", choices=["SAFE", "MODERATE", "ELEVATED"],
                                 help="Risk level for proposals")
    selfeval_parser.add_argument("--target", help="Target file for proposal")
    selfeval_parser.add_argument("--blocked-by-immutable-core", action="store_true",
                                 help="Proposal blocked by immutable core")
    selfeval_parser.set_defaults(func=cmd_self_eval)

    # finalize
    fin_parser = subparsers.add_parser("finalize", help="Finalize session")
    fin_parser.add_argument("session_id", help="Session identifier")
    fin_parser.set_defaults(func=cmd_finalize)

    # show (enhanced)
    show_parser = subparsers.add_parser("show", help="Show session data")
    show_parser.add_argument("session_id", help="Session identifier")
    show_parser.add_argument("--timeline", action="store_true", help="Show chronological timeline only")
    show_parser.add_argument("--agent", help="Filter timeline by agent name")
    show_parser.add_argument("--type", help="Filter timeline by event type")
    show_parser.set_defaults(func=cmd_show)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == '__main__':
    main()
