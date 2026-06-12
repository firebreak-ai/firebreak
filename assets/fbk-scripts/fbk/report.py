"""report — aggregates events, state, and token harvester into a metrics table.

Usage: fbk.py report <spec>

Reads:
  - events from .fbk-capture/events.jsonl (relative to cwd)
  - state from fbk.state.get_state_path(spec) (STATE_DIR env or .claude/automation/state)
  - tokens from the token harvester (transcript under .claude/projects/<spec>/)

Prints a human-readable table covering durations, gate rates, parks/rework,
tasks, scope violations, detection rounds, kill rate, and tokens per stage.

Runs at any pipeline point — partial rows are expected mid-cycle.
"""

import datetime
import glob
import json
import os
import sys

import fbk.state as state_module
from fbk.state import NON_ACTIVE_STATES
from fbk.capture import known_agents, token_harvester


# ---------------------------------------------------------------------------
# Pure computation helpers
# ---------------------------------------------------------------------------


def classify_gate_attempts(events, st, stage):
    """Classify VERIFICATION_RESULT events for a stage as first_try or after_rework.

    A "first try" attempt is any gate attempt that occurred before the stage's
    first park.  An "after rework" attempt is any gate attempt from the moment
    the stage was re-entered following a READY transition onward.

    Args:
        events: List of event dicts from the events stream.
        st:     State dict for the spec (with stage_timestamps and error_history).
        stage:  The stage name to classify attempts for.

    Returns:
        List of dicts, each {"phase": "first_try" | "after_rework", "passed": bool}.
    """
    # Collect VERIFICATION_RESULT events for this stage, sorted by timestamp.
    gate_events = [
        e for e in events
        if e.get("event_type") == "VERIFICATION_RESULT"
        and e.get("stage") == stage
    ]
    gate_events.sort(key=lambda e: e.get("timestamp", ""))

    # Determine the first park timestamp for this stage from error_history.
    first_park_ts = None
    for entry in st.get("error_history", []):
        if entry.get("stage") == stage:
            first_park_ts = entry.get("timestamp")
            break

    # Determine re-entry timestamp: READY appears in stage_timestamps when the
    # pipeline returns from a park.  The re-entry point is when READY was recorded.
    reentry_ts = st.get("stage_timestamps", {}).get("READY")

    results = []
    for ev in gate_events:
        ev_ts = ev.get("timestamp", "")
        data = ev.get("data", {})

        # Determine pass/fail from the event data.
        passed = _event_passed(data)

        # Classify the attempt phase.
        if first_park_ts is None:
            # No park recorded — every attempt is first_try.
            phase = "first_try"
        elif reentry_ts is not None and ev_ts >= reentry_ts:
            # After re-entry: after_rework.
            phase = "after_rework"
        elif ev_ts < first_park_ts:
            # Before the park: first_try.
            phase = "first_try"
        else:
            # Between park and re-entry (shouldn't normally happen, but treat as after_rework).
            phase = "after_rework"

        results.append({"phase": phase, "passed": passed})

    return results


def _event_passed(data):
    """Extract a pass/fail bool from a VERIFICATION_RESULT event's data dict.

    The verification hook writes ``tests_passed``; older/other shapes may carry
    ``passed`` or ``result``.  All three are accepted so the report reads the
    real producer field rather than a shape only the test fixtures emit.
    """
    if "tests_passed" in data:
        return bool(data["tests_passed"])
    if "passed" in data:
        return bool(data["passed"])
    result = data.get("result", "")
    return result == "pass"


def first_try_pass_rate(attempts):
    """Compute the first-try gate pass rate.

    Args:
        attempts: List of classified attempt dicts (each with "phase" and "passed").

    Returns:
        float — count of first-try passed / count of first-try attempts.
        Returns 0.0 when there are no first-try attempts (guard divide-by-zero).
    """
    first_try = [a for a in attempts if a["phase"] == "first_try"]
    if not first_try:
        return 0.0
    passed = sum(1 for a in first_try if a["passed"])
    return passed / len(first_try)


def kill_rate(rounds):
    """Compute the detection kill rate across all rounds.

    kill rate = (total_raised - total_survived) / total_raised

    "Survived" findings are the ones that were not killed; the kill rate is the
    fraction of raised findings that did not survive.

    Args:
        rounds: List of dicts, each {"raised": int, "survived": int}.

    Returns:
        float — the kill rate.  Returns 0.0 when total_raised is zero.
    """
    total_raised = sum(r.get("raised", 0) for r in rounds)
    total_survived = sum(r.get("survived", 0) for r in rounds)
    if total_raised == 0:
        return 0.0
    return (total_raised - total_survived) / total_raised


def derive_parks(st, stage):
    """Derive park entries for a stage from the state's error_history.

    An empty-reason park is kept as a present entry (not dropped) so the
    renderer can surface "(no reason recorded)".

    Args:
        st:    State dict.
        stage: Stage name to filter parks for.

    Returns:
        List of dicts, each {"reason": str | None}.
    """
    parks = []
    for entry in st.get("error_history", []):
        if entry.get("stage") == stage:
            reason = entry.get("error")
            # Keep the entry even when reason is empty or None.
            parks.append({"reason": reason if reason else None})
    return parks


def derive_rework(st, stage):
    """Derive the re-entry count for a stage.

    A stage that has any entry in error_history (indicating it was parked and
    re-entered at least once) gets a count of >= 1.

    Args:
        st:    State dict.
        stage: Stage name to derive re-entry count for.

    Returns:
        int — number of times the stage was re-entered (>= 0).
    """
    return sum(1 for entry in st.get("error_history", []) if entry.get("stage") == stage)


def count_known_subagents(events):
    """Count SUBAGENT_STOP events whose agent identity is a known Firebreak agent.

    The hook router writes SUBAGENT_STOP envelopes where the envelope's source
    field is always the writer's provenance name ("hook_router") and the agent
    identity lives in the event's data["agent_type"] field.  This function reads
    the identity from data, not the envelope source.  Events with empty or
    unrecognised identities are excluded from the count.

    Args:
        events: List of event dicts from the events stream.

    Returns:
        int — count of SUBAGENT_STOP events with a known agent identity.
    """
    count = 0
    for ev in events:
        if ev.get("event_type") != "SUBAGENT_STOP":
            continue
        identity = ev.get("data", {}).get("agent_type") or ""
        if known_agents.is_known_agent(identity):
            count += 1
    return count


# ---------------------------------------------------------------------------
# Per-stage summary block
# ---------------------------------------------------------------------------


def stage_summary(spec, stage):
    """Return a markdown metrics block body for one stage.

    Opens with the provenance marker line and includes the stage's gate/park/
    rework metrics.  Tokens are excluded from the per-stage injected block.

    Args:
        spec:  The spec name.
        stage: The stage name.

    Returns:
        str — markdown block starting with the provenance marker.
    """
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    marker = f"<!-- fbk-metrics stage={stage} spec={spec} generated={now} -->"
    lines = [marker]
    lines.append(f"stage: {stage}")
    lines.append(f"spec: {spec}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Event loading helpers
# ---------------------------------------------------------------------------


def _load_events(cwd):
    """Load events from .fbk-capture/events.jsonl under cwd.

    Returns an empty list when the file is absent or unreadable.
    """
    path = os.path.join(cwd, ".fbk-capture", "events.jsonl")
    if not os.path.exists(path):
        return []
    events = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return events


def _load_state(spec):
    """Load the state dict for spec.  Returns an empty state dict on failure."""
    path = state_module.get_state_path(spec)
    if not os.path.exists(path):
        return {
            "spec_name": spec,
            "current_state": "QUEUED",
            "stage_timestamps": {},
            "error_history": [],
            "parked_info": {},
        }
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _find_transcript_paths(spec, cwd):
    """Locate transcript JSONL files for spec under .claude/projects/<spec>/."""
    projects_dir = os.path.join(cwd, ".claude", "projects", spec)
    pattern = os.path.join(projects_dir, "*.jsonl")
    return sorted(glob.glob(pattern))


def _parse_ts(s):
    """Parse an ISO-8601 string into a datetime or return None."""
    if not s:
        return None
    try:
        return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Duration helpers
# ---------------------------------------------------------------------------


def _stage_duration_s(stage, stage_timestamps):
    """Compute the duration in seconds for a stage, or None when still running."""
    start = _parse_ts(stage_timestamps.get(stage))
    if start is None:
        return None

    # Find the timestamp of the entry that follows this one in chronological order.
    all_entries = [(k, _parse_ts(v)) for k, v in stage_timestamps.items() if _parse_ts(v)]
    all_entries.sort(key=lambda x: x[1])

    idx = next((i for i, (k, _) in enumerate(all_entries) if k == stage), None)
    if idx is None or idx + 1 >= len(all_entries):
        return None
    return (all_entries[idx + 1][1] - all_entries[idx][1]).total_seconds()


# ---------------------------------------------------------------------------
# Ordered pipeline stages (used to determine render order)
# ---------------------------------------------------------------------------

_PIPELINE_STAGES = [
    "VALIDATING",
    "REVIEWING",
    "BREAKING_DOWN",
    "TASK_REVIEWING",
    "TESTING",
    "TEST_REVIEWING",
    "IMPLEMENTING",
    "VERIFYING",
]


# ---------------------------------------------------------------------------
# Table rendering
# ---------------------------------------------------------------------------


def _fmt_duration(seconds):
    """Format seconds as a human-readable duration string."""
    if seconds is None:
        return "(in progress)"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


def _print_warnings(cwd):
    """Print any active warning lines to stdout."""
    # Over-cap retention warning.
    retention_sentinel = os.path.join(cwd, ".fbk-capture", ".retention-warning")
    if os.path.exists(retention_sentinel):
        print("WARNING: over-cap retention — locked lines dropped past ceiling (events may be incomplete)")

    # Stale-fallback warning from known_agents.
    if known_agents.STALE_FALLBACK:
        print("WARNING: stale agent fallback — known-agent set derived from hardcoded list, not installed personas")


def _render_table(spec, events, st, token_data, cwd):
    """Print the full metrics table to stdout.

    Columns: stage, metric, value.

    Empty-vs-absent discriminator:
    - A stage that ran (appears in stage_timestamps) renders ALL rows for that
      stage, even when counts are zero.
    - A stage that never ran (absent from stage_timestamps) is entirely omitted.
    """
    stage_timestamps = st.get("stage_timestamps", {})

    # Determine which pipeline stages actually ran.
    ran_stages = [s for s in _PIPELINE_STAGES if s in stage_timestamps]

    # Also include any non-standard stages present in timestamps (not in _PIPELINE_STAGES).
    extra_ran = [
        k for k in stage_timestamps
        if k not in _PIPELINE_STAGES
        and k not in NON_ACTIVE_STATES
    ]
    ran_stages = ran_stages + extra_ran

    print(f"fbk report — spec: {spec}")
    print(f"current state: {st.get('current_state', '?')}")
    print()

    # Refresh the known-agent scan once, unconditionally, before warnings read
    # the stale-fallback flag. count_known_subagents only triggers the scan as a
    # side effect of checking SUBAGENT_STOP events, so a session with zero such
    # events would leave known_agents.STALE_FALLBACK at its stale import-time
    # value and wrongly suppress the warning. Deriving here keeps the flag
    # current regardless of event content.
    scan_root = os.environ.get(
        "FBK_AGENTS_DIR", os.path.expanduser("~/.claude/agents")
    )
    _, known_agents.STALE_FALLBACK = known_agents.derive_known_agents(scan_root)

    # Count known subagents (value is reused at the end of the table where the
    # "known subagents" line is printed). is_known_agent re-derives per event,
    # which keeps the flag current when events do exist.
    known_count = count_known_subagents(events)

    # Print warnings before the table body.
    _print_warnings(cwd)

    # Aggregate events by stage and type for quick lookup.
    events_by_stage = {}
    for ev in events:
        s = ev.get("stage", "")
        if s not in events_by_stage:
            events_by_stage[s] = []
        events_by_stage[s].append(ev)

    # Collect CODE_REVIEW_ROUNDS data (spec-level, not per-stage).
    review_rounds = []
    for ev in events:
        if ev.get("event_type") == "CODE_REVIEW_ROUNDS":
            data = ev.get("data", {})
            # The code-review gate writes total_raised/total_survived plus a
            # rounds *list*; read those, deriving the round count from the list.
            rounds_list = data.get("rounds", [])
            round_count = len(rounds_list) if isinstance(rounds_list, list) else rounds_list
            review_rounds.append({
                "raised": data.get("total_raised", 0),
                "survived": data.get("total_survived", 0),
                "rounds": round_count,
            })

    # --- Duration rows ---
    print("=== stage durations ===")
    for s in ran_stages:
        dur = _stage_duration_s(s, stage_timestamps)
        print(f"  {s:<20} duration: {_fmt_duration(dur)}")
    print()

    # --- Gate attempt rows (first-try and after-rework) ---
    print("=== gate attempts ===")
    for s in ran_stages:
        stage_evs = events_by_stage.get(s, [])
        attempts = classify_gate_attempts(stage_evs, st, s)
        ftr = first_try_pass_rate(attempts)
        after_rework_attempts = [a for a in attempts if a["phase"] == "after_rework"]
        after_rework_rate = (
            sum(1 for a in after_rework_attempts if a["passed"]) / len(after_rework_attempts)
            if after_rework_attempts else 0.0
        )
        print(f"  {s:<20} first-try rate: {ftr:.2f}  after-rework rate: {after_rework_rate:.2f}")
    print()

    # --- Parks rows (present-and-empty for stages that ran) ---
    print("=== parks ===")
    for s in ran_stages:
        parks = derive_parks(st, s)
        if parks:
            for p in parks:
                reason = p["reason"] or "(no reason recorded)"
                print(f"  {s:<20} parks: {reason}")
        else:
            # Stage ran but had zero parks — present-and-empty row.
            print(f"  {s:<20} parks: (none)")
    print()

    # --- Tasks completed and reworked ---
    print("=== tasks ===")
    for s in ran_stages:
        stage_evs = events_by_stage.get(s, [])
        # A completed task is a passing task-completed dispatch the chokepoint
        # recorded under this stage (command_name, hyphenated, with outcome).
        completed = sum(
            1 for ev in stage_evs
            if ev.get("event_type") == "PIPELINE_COMMAND"
            and ev.get("data", {}).get("command_name") == "task-completed"
            and ev.get("data", {}).get("outcome") == "pass"
        )
        # There is no task-reworked event; rework is the stage's re-entry count,
        # derived from the parks recorded in error_history.
        reworked = derive_rework(st, s)
        print(f"  {s:<20} tasks completed: {completed}  tasks reworked: {reworked}")
    print()

    # --- Scope violations ---
    print("=== scope violations ===")
    for s in ran_stages:
        stage_evs = events_by_stage.get(s, [])
        # Out-of-scope files are recorded on the verification event, not as a
        # separate command; sum them across this stage's verification results.
        violations = sum(
            len(ev.get("data", {}).get("out_of_scope_files", []))
            for ev in stage_evs
            if ev.get("event_type") == "VERIFICATION_RESULT"
        )
        print(f"  {s:<20} scope violation count: {violations}")
    print()

    # --- Detection rounds and kill rate ---
    print("=== detection rounds ===")
    if review_rounds:
        for i, r in enumerate(review_rounds, 1):
            print(f"  detection round {i}: raised={r['raised']}  survived={r['survived']}")
        kr = kill_rate(review_rounds)
        print(f"  kill rate: {kr:.2f} (note: survivors are findings not killed; true positives may inflate kill rate)")
    else:
        # No rounds yet — still print the section header row so the label appears.
        print("  detection round: (none yet)")
        print("  kill rate: n/a (note: survivors are findings not killed; true positives may inflate kill rate)")
    print()

    # --- Tokens per stage ---
    # The "coarse indicator" label is an explicit AC-06 requirement: stage
    # attribution is a hard split by timestamp, so per-stage token counts are
    # approximate and should not be over-trusted across cycles.
    print("=== per-stage token usage (coarse indicator — stage attribution is approximate) ===")
    for s in ran_stages:
        token_entry = token_data.get(s) if token_data else None
        if token_entry is None or not token_entry.get("available", False):
            print(f"  {s:<20} tokens: unavailable")
        else:
            by_type = token_entry.get("tokens_by_type", {})
            total_in = by_type.get("input_tokens", 0)
            total_out = by_type.get("output_tokens", 0)
            # Turns near a stage boundary may be mis-attributed; surfacing the
            # count tells the operator how coarse this stage's figure is.
            boundary = token_entry.get("boundary_adjacent_turns")
            boundary = boundary if boundary is not None else 0
            print(
                f"  {s:<20} tokens: in={total_in} out={total_out}"
                f"  boundary-adjacent turns: {boundary}"
            )
    print()

    # Subagent count (session-level) — computed early so the stale-fallback
    # warning can read the flag the scan sets.
    print(f"known subagents: {known_count}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main():
    """CLI main: read spec from argv, load data, print the report table."""
    if len(sys.argv) < 2:
        print("Usage: fbk.py report <spec>", file=sys.stderr)
        return 2

    spec = sys.argv[1]
    cwd = os.getcwd()

    # Load events.
    events = _load_events(cwd)

    # Load state.
    st = _load_state(spec)

    # Harvest tokens.
    transcript_paths = _find_transcript_paths(spec, cwd)
    stage_timestamps = st.get("stage_timestamps", {})
    transitions = [
        {"stage": k, "timestamp": v}
        for k, v in sorted(
            stage_timestamps.items(),
            key=lambda item: item[1] or "",
        )
    ]
    if transcript_paths and transitions:
        token_data = token_harvester.harvest(transcript_paths, transitions)
    elif transitions:
        # No transcripts — mark all stages as unavailable.
        token_data = {
            k: {"available": False, "tokens_by_type": {}, "tokens_by_model": {},
                "tool_calls": None, "tool_errors": None, "boundary_adjacent_turns": None}
            for k in stage_timestamps
        }
    else:
        token_data = {}

    _render_table(spec, events, st, token_data, cwd)
    return 0
