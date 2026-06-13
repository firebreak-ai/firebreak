"""Shared resolver for the active SDL (spec, stage) of a project.

Several producers need to stamp an event with the spec and stage that is
currently running: the dispatch chokepoint, the standalone hook router, and the
task-completed verification hook.  They must agree on one rule — including which
states carry an active working stage — so events from different producers in the
same cycle carry consistent attribution.  Keeping that rule in one place stops
the producers from drifting apart.

The resolver returns a stage only for an active working stage.  Events during
checkpoint, idle, parked, or terminal periods carry no stage.
"""

import json
import os

from fbk.state import NON_ACTIVE_STATES


def resolve_active_stage(cwd: str):
    """Return (spec, stage) for the active run under cwd, or (None, None).

    Reads state files from <cwd>/.claude/automation/state/ and returns the
    spec_name and current_state of the most-recently-modified file whose state
    is an active working stage.  Returns (None, None) on any error, when no
    state files exist, or when every run is in a checkpoint, idle, parked, or
    terminal state.
    """
    try:
        state_dir = os.path.join(cwd, ".claude", "automation", "state")
        if not os.path.isdir(state_dir):
            return None, None

        candidates = []
        for entry in os.listdir(state_dir):
            if not entry.endswith(".json"):
                continue
            path = os.path.join(state_dir, entry)
            if not os.path.isfile(path):
                continue
            try:
                mtime = os.path.getmtime(path)
                candidates.append((mtime, path))
            except OSError:
                continue

        # Try the most recently touched file first.
        candidates.sort(reverse=True)
        for _, path in candidates:
            try:
                with open(path, "r") as fh:
                    state = json.load(fh)
                spec = state.get("spec_name")
                stage = state.get("current_state")
                if spec and stage and stage not in NON_ACTIVE_STATES:
                    return spec, stage
            except Exception:
                continue

        return None, None
    except Exception:
        return None, None
