"""Standalone hook router — the sole write entry point for hook-fired events.

Registered by absolute path on every hook event in .claude/settings.json.
Appends one envelope line to .fbk-capture/events.jsonl under the pinned
working directory (os.getcwd() — never payload['cwd'] or $CLAUDE_PROJECT_DIR).

Design constraints:
- NEVER blocks the harness: every failure path exits 0.
- NEVER writes to stdout: hook stdout can be interpreted as hook output
  (decisions, context injection); this script is a pure observer.
- Working-directory pinning: os.getcwd() is the sole authority for both the
  gate decision and the write destination. payload['cwd'] and
  $CLAUDE_PROJECT_DIR are not silently trusted over it.
- Stage stamp: if a Firebreak-style state file exists under
  <cwd>/.claude/automation/state/, the current pipeline stage of the most
  recently modified spec is stamped onto the event. Fail-silent when absent;
  the event is still written with stage=null when no run is active.
- Fail-silent: any exception (parse error, write failure, etc.) is absorbed;
  exit 0 in all cases.
"""

import glob
import json
import os
import sys

# ---------------------------------------------------------------------------
# sys.path bootstrap — must happen before any fbk.capture.* imports so this
# script resolves modules correctly when invoked by absolute path at runtime.
#
# hook_router.py lives at:  <fbk-scripts>/fbk/capture/hook_router.py
# The fbk-scripts root is therefore two levels up from this file's directory.
# ---------------------------------------------------------------------------

_this_file = os.path.realpath(__file__)
_capture_dir = os.path.dirname(_this_file)      # .../fbk/capture/
_fbk_pkg_dir = os.path.dirname(_capture_dir)    # .../fbk/
_fbk_scripts_root = os.path.dirname(_fbk_pkg_dir)  # .../fbk-scripts/

if _fbk_scripts_root not in sys.path:
    sys.path.insert(1, _fbk_scripts_root)

# Inject the project-local venv's site-packages so third-party deps resolve
# without requiring system-wide installation. Falls through silently if absent.
for _site_pkg in glob.glob(
    os.path.join(_fbk_scripts_root, ".venv", "lib", "python*", "site-packages")
):
    if _site_pkg not in sys.path:
        sys.path.insert(0, _site_pkg)

# Now that sys.path is set up, import fbk.capture modules.
from fbk.capture import event_writer, gate_check, known_agents  # noqa: E402

# ---------------------------------------------------------------------------
# Event-type mapping
# ---------------------------------------------------------------------------

# Maps hook_event_name values to the fixed metrics-plane vocabulary.
_EVENT_TYPE_MAP = {
    "PreToolUse": "TOOL_USE",
    "PostToolUse": "TOOL_USE",
    "PostToolUseFailure": "TOOL_USE",
    "SubagentStart": "SUBAGENT_STOP",
    "SubagentStop": "SUBAGENT_STOP",
    "PrePrompt": "LIFECYCLE",
    "PostPrompt": "LIFECYCLE",
    "Stop": "LIFECYCLE",
    "SessionStart": "LIFECYCLE",
    "SessionEnd": "LIFECYCLE",
}

_DEFAULT_EVENT_TYPE = "LIFECYCLE"


def _map_event_type(hook_event_name):
    """Return the vocabulary event type for the given hook_event_name."""
    return _EVENT_TYPE_MAP.get(hook_event_name, _DEFAULT_EVENT_TYPE)


# ---------------------------------------------------------------------------
# Stage resolution (best-effort)
# ---------------------------------------------------------------------------


def _read_active_stage(cwd):
    """Return (spec, stage) from the most-recently-modified state file under cwd.

    Reads .claude/automation/state/*.json, picks the newest by mtime, and
    returns (spec_name, current_state) from its contents.  Returns (None, None)
    on any failure or when no state files exist.
    """
    try:
        state_pattern = os.path.join(
            cwd, ".claude", "automation", "state", "*.json"
        )
        state_files = glob.glob(state_pattern)
        if not state_files:
            return None, None

        latest = max(state_files, key=os.path.getmtime)
        with open(latest) as f:
            state = json.load(f)

        return state.get("spec_name"), state.get("current_state")
    except Exception:
        return None, None


# ---------------------------------------------------------------------------
# Data assembly
# ---------------------------------------------------------------------------


def _assemble_data(hook_event_name, payload):
    """Build the data dict from the hook payload for the given event type.

    Tool-use events carry tool_name and tool_input (redaction strips tool_input
    at standard level — that happens centrally in event_writer, not here).
    Subagent events carry agent_type (empty identity is preserved, not dropped).
    Lifecycle events carry a minimal set of non-free-text fields.
    """
    event_type = _map_event_type(hook_event_name)

    if event_type == "TOOL_USE":
        data = {"tool_name": payload.get("tool_name")}
        # Include tool_input so the writer can redact or preserve per level.
        if "tool_input" in payload:
            data["tool_input"] = payload["tool_input"]
        return data

    if event_type == "SUBAGENT_STOP":
        # agent_type may be empty string — always preserve it (even empty identity
        # is recorded; the report excludes unknowns from counts, not the router).
        return {
            "agent_type": payload.get("agent_type", ""),
            "is_known_agent": known_agents.is_known_agent(payload.get("agent_type")),
        }

    # LIFECYCLE: carry non-free-text contextual fields only.
    return {
        "hook_event_name": hook_event_name,
        "session_id": payload.get("session_id"),
        "agent_id": payload.get("agent_id"),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    # Wrap everything so the router never raises and always exits 0.
    try:
        # Read stdin once; fail-silent to a parse-error marker.
        try:
            payload = json.load(sys.stdin)
        except Exception:
            payload = {"_parse_error": True}

        # Pinned cwd — os.getcwd() is the sole authority.
        # payload['cwd'] and $CLAUDE_PROJECT_DIR are deliberately ignored.
        cwd = os.getcwd()

        # Gate: uninstrumented or level=off → exit 0, no write, no stdout.
        if not gate_check.project_is_instrumented(cwd):
            sys.exit(0)

        level = gate_check.resolve_capture_level(cwd)
        if level == "off":
            sys.exit(0)

        # Map hook name to vocabulary event type.
        hook_event_name = payload.get("hook_event_name", "")
        event_type = _map_event_type(hook_event_name)

        # Read spec/stage best-effort; pass None/None when no run is active.
        # The writer enforces null-not-absent — None becomes JSON null.
        spec, stage = _read_active_stage(cwd)

        # Assemble the data dict (writer handles redaction by level).
        data = _assemble_data(hook_event_name, payload)

        # Events path is always under the pinned cwd — never any global dir.
        events_path = os.path.join(cwd, ".fbk-capture", "events.jsonl")

        event_writer.write(
            event_type,
            "hook_router",
            data,
            spec,
            stage,
            level,
            events_path,
        )

    except Exception:
        # Fail-silent: absorb everything, never raise, never write stdout.
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
