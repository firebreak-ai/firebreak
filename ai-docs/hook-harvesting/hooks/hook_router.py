#!/usr/bin/env python3
"""Universal hook router — capture-everything observability tap.

Registered on every hook event in .claude/settings.json. Appends the full
stdin payload (plus a small derived envelope) as one JSON line to
.fbk-capture/events.jsonl under the project root.

Design constraints:
- NEVER blocks the harness: every failure path exits 0.
- NEVER writes to stdout: hook stdout can be interpreted as hook output
  (decisions, context injection); this script is a pure observer.
- Stage stamp: if a Firebreak-style state file exists under
  <cwd>/.claude/automation/state/, the current pipeline stage of the most
  recently modified spec is stamped onto the event. Fail-silent when absent,
  so the router works identically in non-Firebreak projects.
- Large string fields are truncated (tool outputs can be hundreds of KB);
  byte sizes are preserved before truncation so size metrics survive.
"""

import datetime
import glob
import json
import os
import sys

TRUNCATE_AT = 20_000  # chars per string field
CAPTURE_DIR_NAME = ".fbk-capture"


def project_root():
    return os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


def truncate_strings(obj, limit=TRUNCATE_AT):
    if isinstance(obj, str):
        if len(obj) > limit:
            return obj[:limit] + f"…[truncated {len(obj) - limit} chars]"
        return obj
    if isinstance(obj, dict):
        return {k: truncate_strings(v, limit) for k, v in obj.items()}
    if isinstance(obj, list):
        return [truncate_strings(v, limit) for v in obj]
    return obj


def current_stage(cwd):
    """Best-effort read of the Firebreak pipeline stage for the active spec."""
    try:
        state_files = glob.glob(os.path.join(cwd, ".claude", "automation", "state", "*.json"))
        if not state_files:
            return None
        latest = max(state_files, key=os.path.getmtime)
        with open(latest) as f:
            state = json.load(f)
        return {
            "spec": state.get("spec_name"),
            "stage": state.get("current_state"),
        }
    except Exception:
        return None


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {"_parse_error": True}

    try:
        cwd = payload.get("cwd") or os.getcwd()
        event = {
            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "event": payload.get("hook_event_name", "unknown"),
            "session_id": payload.get("session_id"),
            "agent_id": payload.get("agent_id"),
            "agent_type": payload.get("agent_type"),
            "fbk": current_stage(cwd),
            "payload": truncate_strings(payload),
        }
        capture_dir = os.path.join(project_root(), CAPTURE_DIR_NAME)
        os.makedirs(capture_dir, exist_ok=True)
        with open(os.path.join(capture_dir, "events.jsonl"), "a") as f:
            f.write(json.dumps(event, default=str) + "\n")
    except Exception:
        pass  # observer must never break the harness

    sys.exit(0)


if __name__ == "__main__":
    main()
