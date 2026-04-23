#!/usr/bin/env python3
"""
Ralph + Council integration helper.

Provides commands for managing multi-iteration council sessions:
- status: Show current council state
- abort: Signal graceful abort
- pause: Signal pause for review
- resume: Remove pause signal
- clean: Clean up state files
- stuck: Check if council appears stuck

Usage:
    python3 ralph-council.py status
    python3 ralph-council.py abort
    python3 ralph-council.py pause
    python3 ralph-council.py resume
    python3 ralph-council.py clean
    python3 ralph-council.py stuck
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Paths
CLAUDE_DIR = Path.home() / '.claude'
LOGS_DIR = CLAUDE_DIR / 'council-logs'
STATE_FILE = LOGS_DIR / 'council-state.json'
ABORT_FILE = LOGS_DIR / 'council-abort'
PAUSE_FILE = LOGS_DIR / 'council-pause'
ACTIVE_FILE = LOGS_DIR / 'active-council'


def read_json_safe(file_path: Path, default: dict) -> dict:
    """Safely read JSON file, returning default if empty or corrupted."""
    try:
        if not file_path.exists():
            return default
        content = file_path.read_text().strip()
        if not content:
            return default
        return json.loads(content)
    except (json.JSONDecodeError, IOError):
        return default


def write_json_safe(file_path: Path, data: dict) -> None:
    """Write JSON data to file."""
    file_path.write_text(json.dumps(data, indent=2))


def is_signal_active(file_path: Path) -> bool:
    """Check if a signal file has non-empty content."""
    data = read_json_safe(file_path, {})
    return bool(data and data != {})


def cmd_status(args) -> None:
    """Show current council state."""
    if not STATE_FILE.exists():
        print("No active Ralph + Council session")
        print(f"  State file not found: {STATE_FILE}")
        return

    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error reading state: {e}")
        return

    print("=" * 60)
    print("RALPH + COUNCIL STATUS")
    print("=" * 60)
    print(f"Task: {state.get('task', 'Unknown')}")
    print(f"Iteration: {state.get('iteration', '?')} of {state.get('max_iterations', '?')}")
    print(f"Status: {state.get('status', 'Unknown')}")
    print(f"Current Phase: {state.get('current_phase', 'Unknown')}")
    print(f"Last Updated: {state.get('last_updated', 'Unknown')}")
    print()

    # Completed phases
    completed = state.get('completed_phases', [])
    if completed:
        print("Completed Phases:")
        for phase in completed:
            if isinstance(phase, dict):
                print(f"  - {phase.get('name', '?')} (iteration {phase.get('iteration', '?')})")
            else:
                print(f"  - {phase}")
    print()

    # Key decisions
    decisions = state.get('key_decisions', [])
    if decisions:
        print("Key Decisions (locked):")
        for d in decisions:
            print(f"  - {d}")
    print()

    # Remaining work
    remaining = state.get('remaining_work', [])
    if remaining:
        print("Remaining Work:")
        for r in remaining:
            print(f"  - {r}")
    print()

    # Control signals
    print("Control Signals:")
    print(f"  Abort requested: {'YES' if is_signal_active(ABORT_FILE) else 'no'}")
    print(f"  Pause requested: {'YES' if is_signal_active(PAUSE_FILE) else 'no'}")

    # Check for active sessions
    active_data = read_json_safe(ACTIVE_FILE, {'sessions': {}})
    session_count = len(active_data.get('sessions', {}))
    print(f"  Active sessions: {session_count}")
    print("=" * 60)


def cmd_abort(args) -> None:
    """Signal graceful abort."""
    write_json_safe(ABORT_FILE, {'requested_at': datetime.now().isoformat()})
    print(f"Abort signal set: {ABORT_FILE}")
    print("Council will complete current phase and exit gracefully.")
    print("To cancel: python3 ralph-council.py resume")


def cmd_pause(args) -> None:
    """Signal pause for review."""
    write_json_safe(PAUSE_FILE, {'requested_at': datetime.now().isoformat()})
    print(f"Pause signal set: {PAUSE_FILE}")
    print("Council will pause after current work for human review.")
    print("To resume: python3 ralph-council.py resume")


def cmd_resume(args) -> None:
    """Clear pause/abort signals."""
    removed = []
    if is_signal_active(PAUSE_FILE):
        write_json_safe(PAUSE_FILE, {})
        removed.append("pause")
    if is_signal_active(ABORT_FILE):
        write_json_safe(ABORT_FILE, {})
        removed.append("abort")

    if removed:
        print(f"Cleared signals: {', '.join(removed)}")
        print("Council can now continue.")
    else:
        print("No active signals to clear.")


def cmd_clean(args) -> None:
    """Clean up state and clear signals."""
    cleaned = []

    # Remove state file (not persistent)
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        cleaned.append("council-state.json")

    # Clear signal files (persistent, just reset content)
    if is_signal_active(ABORT_FILE):
        write_json_safe(ABORT_FILE, {})
        cleaned.append("abort signal")

    if is_signal_active(PAUSE_FILE):
        write_json_safe(PAUSE_FILE, {})
        cleaned.append("pause signal")

    # Clear active sessions (persistent, reset content)
    active_data = read_json_safe(ACTIVE_FILE, {'sessions': {}})
    if active_data.get('sessions'):
        write_json_safe(ACTIVE_FILE, {'sessions': {}})
        cleaned.append("active sessions")

    if cleaned:
        print(f"Cleaned up: {', '.join(cleaned)}")
    else:
        print("Nothing to clean.")


def cmd_stuck(args) -> None:
    """Check if council appears stuck."""
    if not STATE_FILE.exists():
        print("No active session to check.")
        return

    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error reading state: {e}")
        return

    # Check iteration without phase progress
    completed_phases = state.get('completed_phases', [])
    iteration = state.get('iteration', 0)

    if iteration > 3 and len(completed_phases) == 0:
        print("WARNING: Possible stuck state detected!")
        print(f"  Iteration {iteration} with no completed phases")
        print("  Consider: python3 ralph-council.py abort")
        return

    # Check for repeated current phase
    if len(completed_phases) >= 2:
        last_iterations = [p.get('iteration', 0) for p in completed_phases[-2:] if isinstance(p, dict)]
        if len(last_iterations) == 2 and last_iterations[1] - last_iterations[0] > 2:
            print("WARNING: Slow progress detected")
            print(f"  Gap between last two phase completions: {last_iterations[1] - last_iterations[0]} iterations")

    # Check last updated time
    last_updated = state.get('last_updated')
    if last_updated:
        try:
            last_time = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
            age_seconds = (datetime.now(last_time.tzinfo) - last_time).total_seconds()
            if age_seconds > 3600:  # More than 1 hour
                print(f"Note: State not updated in {age_seconds / 3600:.1f} hours")
                print("  Session may have terminated unexpectedly.")
        except ValueError:
            pass

    print("No obvious stuck indicators found.")
    print(f"Current: iteration {iteration}, phase '{state.get('current_phase', 'unknown')}'")


def main():
    parser = argparse.ArgumentParser(
        description="Ralph + Council integration helper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  status    Show current council state
  abort     Signal graceful abort (council finishes current phase)
  pause     Signal pause for human review
  resume    Remove pause/abort signals
  clean     Clean up all state files
  stuck     Check if council appears stuck
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    subparsers.add_parser('status', help='Show current council state')
    subparsers.add_parser('abort', help='Signal graceful abort')
    subparsers.add_parser('pause', help='Signal pause for review')
    subparsers.add_parser('resume', help='Remove pause/abort signals')
    subparsers.add_parser('clean', help='Clean up state files')
    subparsers.add_parser('stuck', help='Check if council appears stuck')

    args = parser.parse_args()

    if not args.command:
        # Default to status
        cmd_status(args)
        return

    commands = {
        'status': cmd_status,
        'abort': cmd_abort,
        'pause': cmd_pause,
        'resume': cmd_resume,
        'clean': cmd_clean,
        'stuck': cmd_stuck,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
