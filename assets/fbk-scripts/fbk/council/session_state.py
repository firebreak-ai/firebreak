#!/usr/bin/env python3
"""
Council session state CLI.

Consolidates state-file operations that the /fbk-council orchestrator previously
performed with raw shell commands (cat, echo >, rm -f, inline python3 -c).
Routing all state ops through this module means every call reaches Claude Code
as a `python3 ...fbk.py session-state ...` invocation — matched by the existing
`Bash(python3:*)` allow rule — so the council never triggers a permission prompt
for session bookkeeping.

Subcommands:
    recovery-check              Emit JSON describing prior-session resume state.
    check-abort                 Exit 2 (and clear the abort file) if abort requested, else exit 0.
    checkpoint <phase> [...]    Merge fields into council-state.json atomically.
    cleanup                     Remove council-state.json.
    show                        Print council-state.json (for debugging).
"""

import argparse
import json
import sys
from datetime import datetime
from typing import List, Optional

from fbk.council.session_manager import (
    _get_council_dir,
    atomic_write_json,
    read_json_safe,
)


def _state_file():
    return _get_council_dir() / "council-state.json"


def _abort_file():
    return _get_council_dir() / "council-abort"


def _session_id_file():
    return _get_council_dir() / "council-session-id"


def cmd_recovery_check() -> int:
    """Emit JSON describing whether a prior session is available to resume."""
    state_file = _state_file()
    session_id_file = _session_id_file()

    if not state_file.exists() or not session_id_file.exists():
        print(json.dumps({"recovering": False}))
        return 0

    state = read_json_safe(state_file, {})
    try:
        session_id = session_id_file.read_text().strip() or None
    except OSError:
        session_id = None

    print(json.dumps({
        "recovering": True,
        "session_id": session_id,
        "current_phase": state.get("current_phase"),
        "completed_phases": state.get("completed_phases", []),
        "key_decisions": state.get("key_decisions", []),
        "transcript_summary": state.get("transcript_summary", ""),
    }))
    return 0


def cmd_check_abort() -> int:
    """Exit 2 (and clear) if abort requested, else exit 0."""
    abort_file = _abort_file()
    if not abort_file.exists():
        return 0

    content = abort_file.read_text().strip()
    if content in ("", "{}"):
        return 0

    abort_file.write_text("{}")
    print("abort-requested", file=sys.stderr)
    return 2


def cmd_checkpoint(
    phase: str,
    completed: Optional[List[str]],
    summary: Optional[str],
    decisions: Optional[List[str]],
    session_id: Optional[str],
) -> int:
    """Merge checkpoint fields into council-state.json atomically."""
    council_dir = _get_council_dir()
    council_dir.mkdir(parents=True, exist_ok=True)
    state_file = _state_file()

    state = read_json_safe(state_file, {})
    state["current_phase"] = phase
    state["last_checkpoint"] = datetime.now().isoformat()

    if completed is not None:
        state["completed_phases"] = completed
    if summary is not None:
        state["transcript_summary"] = summary
    if decisions is not None:
        state["key_decisions"] = decisions
    if session_id is not None:
        state["session_id"] = session_id

    atomic_write_json(state_file, state)
    return 0


def cmd_cleanup() -> int:
    """Remove council-state.json. No-op if the file doesn't exist."""
    state_file = _state_file()
    try:
        state_file.unlink()
    except FileNotFoundError:
        pass
    return 0


def cmd_show() -> int:
    """Print council-state.json contents (JSON) for debugging."""
    state = read_json_safe(_state_file(), {})
    print(json.dumps(state, indent=2))
    return 0


def _split_csv(value: Optional[str]) -> Optional[List[str]]:
    if value is None:
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(prog="session-state")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("recovery-check", help="Emit JSON describing resume state")
    sub.add_parser("check-abort", help="Exit 2 if abort requested, else 0")

    cp = sub.add_parser("checkpoint", help="Merge fields into council-state.json")
    cp.add_argument("phase", help="Current phase identifier")
    cp.add_argument("--completed", help="Comma-separated completed phases")
    cp.add_argument("--summary", help="Transcript summary")
    cp.add_argument("--decisions", help="Comma-separated key decisions")
    cp.add_argument("--session-id", help="Session identifier to record in state")

    sub.add_parser("cleanup", help="Remove council-state.json")
    sub.add_parser("show", help="Print council-state.json as JSON")

    args = parser.parse_args()

    if args.command == "recovery-check":
        return cmd_recovery_check()
    if args.command == "check-abort":
        return cmd_check_abort()
    if args.command == "checkpoint":
        return cmd_checkpoint(
            phase=args.phase,
            completed=_split_csv(args.completed),
            summary=args.summary,
            decisions=_split_csv(args.decisions),
            session_id=args.session_id,
        )
    if args.command == "cleanup":
        return cmd_cleanup()
    if args.command == "show":
        return cmd_show()

    parser.print_help(sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
