"""Hook-invoked finalization trigger over the harvest engine.

Exposes finalize_runs(hook_event_name, cwd, payload=None) as the sole public
entry point.  The router calls this after every event write; the event-name
gate here (decision D-16) reduces the call to exactly two real triggers:

  PostToolUse  — targeted single-run finalize via run id parsed from the
                 Workflow tool response; no sweep.
  SessionStart — recovery sweep of the newest closed-unfinalized run under
                 the current project's subtree only (never other projects').

Every other event is a no-op.  This function never raises into the router.
"""

import glob
import json
import os
import re

from fbk import harvest


# ---------------------------------------------------------------------------
# Run-id parser
# ---------------------------------------------------------------------------


def _parse_run_id_from_payload(payload: dict | None) -> str | None:
    """Extract the run id from a Workflow tool response inside payload.

    The Workflow tool response contains the line:
        Transcript dir: …/subagents/workflows/<run-id>

    payload may carry the response under 'tool_response' as:
      - a plain string
      - a dict with a 'content' list of text blocks

    The parser serialises the full payload to a string and searches for the
    canonical substring so it handles any nesting depth without special-casing
    each possible shape.

    Returns the run id string when found, None otherwise.
    """
    if payload is None:
        return None

    # Serialise the payload to a string so one regex covers all shapes.
    try:
        payload_str = json.dumps(payload)
    except (TypeError, ValueError):
        try:
            payload_str = str(payload)
        except Exception:
            return None

    match = re.search(r"subagents/workflows/([^\s/\"\\]+)", payload_str)
    if match:
        return match.group(1)
    return None


# ---------------------------------------------------------------------------
# SessionStart sweep helpers
# ---------------------------------------------------------------------------


def _is_finalized(project_cwd: str, run_id: str) -> bool:
    """Return True when a finalized record already exists for run_id.

    Checks only the 'finalized' flag in the record JSON; skips full re-parse.
    Returns False when the file is absent, unreadable, or flag is not true.
    """
    record_path = os.path.join(project_cwd, ".fbk-capture", "runs", f"{run_id}.json")
    if not os.path.isfile(record_path):
        return False
    try:
        with open(record_path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data.get("finalized") is True
    except (OSError, json.JSONDecodeError, ValueError):
        return False


def _projects_root() -> str:
    """Return the projects root (FBK_PROJECTS_ROOT, default ~/.claude/projects)."""
    return os.environ.get(
        "FBK_PROJECTS_ROOT", os.path.expanduser("~/.claude/projects")
    )


def _resolve_project_dir(cwd: str, payload: dict | None) -> str | None:
    """Resolve the current project's folder under the projects root.

    Claude Code stores each project's sessions and runs under a folder named
    after the project's working directory with path separators replaced by '-'.
    The recovery sweep is scoped to that single folder so a session never
    finalizes another project's runs — a real hazard when several sandboxed
    projects share one global Firebreak install.

    Resolution order:
      1. cwd — the design's source of truth (the router's os.getcwd(), never
         payload['cwd']). The project folder is cwd with '/' replaced by '-'.
         This is preferred because the folder always exists (prior sessions)
         even when the current session's own folder has not been written yet.
      2. session id — the folder that physically holds this session's files,
         used only when the cwd-derived name is not present (e.g. a path the
         naming scheme rewrites differently).
      3. neither resolves — return None so the caller sweeps nothing rather
         than risk finalizing another project's runs.
    """
    projects_root = _projects_root()

    candidate = os.path.join(projects_root, cwd.replace("/", "-"))
    if os.path.isdir(candidate):
        return candidate

    session_id = payload.get("session_id") if payload else None
    if session_id:
        for hit in (
            glob.glob(os.path.join(projects_root, "*", session_id))
            + glob.glob(os.path.join(projects_root, "*", f"{session_id}.jsonl"))
        ):
            parent = os.path.dirname(hit)
            if os.path.isdir(parent):
                return parent

    return None


def _glob_run_dirs(project_dir: str) -> list[str]:
    """Return run-directory paths under one project's subtree only."""
    pattern = os.path.join(project_dir, "*", "subagents", "workflows", "*")
    return [p for p in glob.glob(pattern) if os.path.isdir(p)]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def finalize_runs(
    hook_event_name: str,
    cwd: str,
    payload: dict | None = None,
) -> None:
    """Trigger finalization for closed workflow runs based on the hook event.

    Gates on hook_event_name first (decision D-16):
      - PostToolUse: parse the run id from the Workflow tool response in
        payload and finalize only that run; no sweep.
      - SessionStart: sweep FBK_PROJECTS_ROOT for the newest closed-unfinalized
        run and finalize it (at most one per call).
      - Any other event: return immediately without doing any work.

    Never raises; every error is absorbed silently so the router stays exit 0.
    """
    try:
        # D-16: event-name gate — must be first action.
        if hook_event_name == "PostToolUse":
            _finalize_post_tool_use(cwd, payload)
        elif hook_event_name == "SessionStart":
            _finalize_session_start(cwd, payload)
        # All other events: no-op.
    except Exception:
        pass


# ---------------------------------------------------------------------------
# PostToolUse path — targeted finalize, no sweep
# ---------------------------------------------------------------------------


def _finalize_post_tool_use(cwd: str, payload: dict | None) -> None:
    """Finalize the specific run named in the Workflow tool response.

    Parses the run id from payload.  When found, calls harvest for only that
    run.  When absent or unparseable, returns without sweeping — a mid-session
    sweep could touch still-live concurrent runs.
    """
    # Gate on the Workflow tool: only a returned Workflow call proves a run is
    # closed. Any other tool whose response merely mentions a workflow path
    # must not trigger finalization of a possibly-live run (AC-06/AC-07).
    if payload is None or payload.get("tool_name") != "Workflow":
        return
    run_id = _parse_run_id_from_payload(payload)
    if run_id is None:
        return
    # Absorb any harvest error; a missed run is caught on the next SessionStart.
    try:
        harvest.harvest(run_id, cwd)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# SessionStart path — bounded recovery sweep
# ---------------------------------------------------------------------------


def _finalize_session_start(cwd: str, payload: dict | None) -> None:
    """Sweep for the newest closed-unfinalized run and finalize it.

    Reads the run directories under the CURRENT project's subtree only,
    filters to those without a finalized record, picks the newest by directory
    modification time, and calls harvest for only that one run.  A second
    SessionStart catches the next-newest (catch-up).

    Project scoping matters: several sandboxed projects can share one global
    Firebreak install under a single projects root, so an unscoped sweep would
    finalize another project's runs into this project's capture dir.  When the
    current project's folder cannot be resolved, the sweep does nothing rather
    than risk that contamination.

    The closed-forever invariant makes the sweep safe at session start: no live
    process can extend an on-disk run directory once a new session begins
    (single-session-per-project sandbox).
    """
    project_dir = _resolve_project_dir(cwd, payload)
    if project_dir is None:
        return

    run_dirs = _glob_run_dirs(project_dir)

    # Filter to unfinalized runs; collect (mtime, run_id, run_dir) tuples.
    unfinalized = []
    for run_dir in run_dirs:
        run_id = os.path.basename(run_dir)
        if not _is_finalized(cwd, run_id):
            try:
                mtime = os.path.getmtime(run_dir)
            except OSError:
                mtime = 0.0
            unfinalized.append((mtime, run_id))

    if not unfinalized:
        return

    # Pick the newest by mtime.
    unfinalized.sort(key=lambda t: t[0], reverse=True)
    _newest_mtime, newest_run_id = unfinalized[0]

    try:
        harvest.harvest(newest_run_id, cwd)
    except Exception:
        pass
