#!/usr/bin/env python3
"""
Council session management utilities.

Provides atomic operations for managing concurrent council sessions using
persistent marker files with content modification (not create/delete).

This enables:
- Multiple parallel council sessions across different Claude Code instances
- Graceful handling of session crashes (stale session detection)
- Atomic operations to prevent file corruption from concurrent writes
"""

import json
import os
import sys
import fcntl
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

COUNCIL_LOGS_DIR = Path.home() / '.claude' / 'council-logs'
ACTIVE_COUNCIL_FILE = COUNCIL_LOGS_DIR / 'active-council'
SESSION_ID_FILE = COUNCIL_LOGS_DIR / 'council-session-id'
ABORT_FILE = COUNCIL_LOGS_DIR / 'council-abort'
PAUSE_FILE = COUNCIL_LOGS_DIR / 'council-pause'


def atomic_write_json(file_path: Path, data: Dict[str, Any]) -> None:
    """
    Atomically write JSON data to a file using temp+rename pattern.

    This prevents corruption from concurrent writes and partial reads.
    Based on session-logger.py:62-70 implementation.
    """
    tmp_path = file_path.with_suffix('.tmp')

    with open(tmp_path, 'w') as f:
        json.dump(data, f, indent=2)
        f.flush()
        os.fsync(f.fileno())

    # Explicitly set permissions before replace to prevent umask inheritance
    os.chmod(tmp_path, 0o600)
    os.replace(tmp_path, file_path)


def read_json_safe(file_path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    """
    Safely read JSON file, returning default if file is empty, missing, or corrupted.
    """
    try:
        if not file_path.exists():
            return default

        content = file_path.read_text().strip()
        if not content:
            return default

        return json.loads(content)
    except (json.JSONDecodeError, IOError):
        return default


def is_process_alive(pid: int) -> bool:
    """Check if a process with given PID is still running."""
    try:
        os.kill(pid, 0)  # Signal 0 doesn't kill, just checks existence
        return True
    except (OSError, ProcessLookupError):
        return False


def register_session(session_id: str, tier: str) -> None:
    """
    Register a new council session in the active-council file.

    Adds session to JSON tracking concurrent sessions with metadata:
    - started: ISO timestamp
    - tier: quick/full
    - pid: process ID for stale detection
    """
    # Use file locking to prevent concurrent writes
    with open(ACTIVE_COUNCIL_FILE, 'r+') as f:
        fcntl.flock(f, fcntl.LOCK_EX)

        try:
            data = read_json_safe(ACTIVE_COUNCIL_FILE, {'sessions': {}})

            # Clean stale sessions before adding new one
            sessions = data.get('sessions', {})
            active_sessions = {}
            for sid, info in sessions.items():
                pid = info.get('pid')
                if pid and is_process_alive(pid):
                    active_sessions[sid] = info

            # Add new session
            active_sessions[session_id] = {
                'started': datetime.now().isoformat(),
                'tier': tier,
                'pid': os.getpid()
            }

            data['sessions'] = active_sessions

            # Write atomically
            atomic_write_json(ACTIVE_COUNCIL_FILE, data)

        finally:
            fcntl.flock(f, fcntl.LOCK_UN)

    # Also write session ID to separate file for compaction recovery
    SESSION_ID_FILE.write_text(session_id)
    print(f"Registered session: {session_id}")


def unregister_session(session_id: str) -> None:
    """
    Remove a session from the active-council file.

    Called when a session completes normally.
    """
    with open(ACTIVE_COUNCIL_FILE, 'r+') as f:
        fcntl.flock(f, fcntl.LOCK_EX)

        try:
            data = read_json_safe(ACTIVE_COUNCIL_FILE, {'sessions': {}})
            sessions = data.get('sessions', {})

            if session_id in sessions:
                del sessions[session_id]

            data['sessions'] = sessions
            atomic_write_json(ACTIVE_COUNCIL_FILE, data)

        finally:
            fcntl.flock(f, fcntl.LOCK_UN)

    print(f"Unregistered session: {session_id}")


def is_any_session_active() -> bool:
    """
    Check if any council sessions are currently active.

    Used by post-tool-hook.py to determine if auto-approval should be enabled.
    Returns True if at least one live session exists (stale sessions ignored).
    """
    data = read_json_safe(ACTIVE_COUNCIL_FILE, {'sessions': {}})
    sessions = data.get('sessions', {})

    # Check if any sessions have live PIDs
    for session_id, info in sessions.items():
        pid = info.get('pid')
        if pid and is_process_alive(pid):
            return True

    return False


def get_active_sessions() -> Dict[str, Dict[str, Any]]:
    """Get all active sessions with stale session filtering."""
    data = read_json_safe(ACTIVE_COUNCIL_FILE, {'sessions': {}})
    sessions = data.get('sessions', {})

    active = {}
    for session_id, info in sessions.items():
        pid = info.get('pid')
        if pid and is_process_alive(pid):
            active[session_id] = info

    return active


def main():
    """CLI interface for session management."""
    if len(sys.argv) < 2:
        print("Usage: session-manager.py <command> [args]")
        print("Commands:")
        print("  register <session-id> <tier>  - Register a new session")
        print("  unregister <session-id>       - Unregister a session")
        print("  is-active                     - Check if any sessions active")
        print("  list                          - List active sessions")
        sys.exit(1)

    command = sys.argv[1]

    if command == 'register':
        if len(sys.argv) != 4:
            print("Usage: session-manager.py register <session-id> <tier>")
            sys.exit(1)
        session_id = sys.argv[2]
        tier = sys.argv[3]
        register_session(session_id, tier)

    elif command == 'unregister':
        if len(sys.argv) != 3:
            print("Usage: session-manager.py unregister <session-id>")
            sys.exit(1)
        session_id = sys.argv[2]
        unregister_session(session_id)

    elif command == 'is-active':
        if is_any_session_active():
            print("Active sessions exist")
            sys.exit(0)
        else:
            print("No active sessions")
            sys.exit(1)

    elif command == 'list':
        sessions = get_active_sessions()
        if not sessions:
            print("No active sessions")
        else:
            print(f"Active sessions ({len(sessions)}):")
            for session_id, info in sessions.items():
                print(f"  {session_id}")
                print(f"    Tier: {info.get('tier')}")
                print(f"    Started: {info.get('started')}")
                print(f"    PID: {info.get('pid')}")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()
