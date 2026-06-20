"""Workflow-run harvest engine for the observability substrate.

Resolves the run directory by glob-matching the run id under the projects
root, joins the workflow journal roster with the filtered event stream and
per-agent transcripts, assembles the durable per-run record to the canonical
schema, redacts free-text at the resolved capture level, and writes the record
atomically to the confined capture path.

Public entry point: harvest(run_id, project_cwd) -> HarvestResult

One record per run, finalized on first write.  A second call against an
already-finalized record is a no-op that preserves the original harvested_at
timestamp.
"""

import datetime
import glob
import json
import os
import uuid

from fbk import attribution, shapes
from fbk.capture import gate_check, schema, token_harvester


# ---------------------------------------------------------------------------
# Public result type
# ---------------------------------------------------------------------------


class HarvestResult:
    """Carries the outcome of one harvest call.

    Attributes
    ----------
    record_path:
        Absolute path to the written record file, or None when no record was
        written (error or off-level no-op).
    unit_count:
        Number of units in the record (equals the roster size).
    units_with_full_attribution:
        Count of units whose attribution_absent is False.
    completeness:
        "clean-complete" or "truncated".
    finalized:
        True when the record was written or already existed finalized.
    error:
        A non-empty string describing the failure, or None on success.
    """

    def __init__(
        self,
        record_path=None,
        unit_count=0,
        units_with_full_attribution=0,
        completeness="truncated",
        finalized=False,
        error=None,
    ):
        self.record_path = record_path
        self.unit_count = unit_count
        self.units_with_full_attribution = units_with_full_attribution
        self.completeness = completeness
        self.finalized = finalized
        self.error = error


# ---------------------------------------------------------------------------
# Clock seam — tests monkeypatch this to control harvested_at
# ---------------------------------------------------------------------------


def _utcnow() -> datetime.datetime:
    """Return the current UTC datetime as a timezone-aware value."""
    return datetime.datetime.now(datetime.timezone.utc)


# ---------------------------------------------------------------------------
# Run-directory resolver
# ---------------------------------------------------------------------------


def _resolve_run_dir(run_id: str) -> str | None:
    """Locate the run directory for run_id under the projects root.

    Reads FBK_PROJECTS_ROOT (defaults to ~/.claude/projects).  Globs the
    two-segment wildcard <project-hash>/<session-uuid> so the run directory
    is found regardless of the undocumented project-hash value.

    Returns the directory path on success, None when not found.
    """
    projects_root = os.environ.get(
        "FBK_PROJECTS_ROOT", os.path.expanduser("~/.claude/projects")
    )
    pattern = os.path.join(
        projects_root, "*", "*", "subagents", "workflows", run_id
    )
    matches = glob.glob(pattern)
    for candidate in matches:
        if os.path.isdir(candidate):
            return candidate
    return None


# ---------------------------------------------------------------------------
# Journal reader
# ---------------------------------------------------------------------------


def _read_journal(run_dir: str) -> tuple[list[str], dict] | None:
    """Parse journal.jsonl into a roster list and a per-agent result map.

    Returns (roster, results_by_agent_id) where:
        roster              – ordered list of agentIds with a "started" line
        results_by_agent_id – dict mapping agentId → result dict for each
                              agent that has a "result" line

    Returns None when journal.jsonl is absent.
    """
    journal_path = os.path.join(run_dir, "journal.jsonl")
    if not os.path.exists(journal_path):
        return None

    roster: list[str] = []
    results: dict = {}

    with open(journal_path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            entry_type = entry.get("type", "")
            agent_id = entry.get("agentId")

            if entry_type == "started" and agent_id:
                roster.append(agent_id)
            elif entry_type == "result" and agent_id:
                results[agent_id] = entry.get("result")

    return roster, results


# ---------------------------------------------------------------------------
# Event stream reader
# ---------------------------------------------------------------------------


def _read_events(project_cwd: str) -> list[dict] | None:
    """Read events.jsonl from the project capture directory.

    Returns a list of parsed event dicts when the file is readable (empty
    list when the file does not exist — no events is a valid empty state).
    Returns None when the file exists but cannot be read (e.g. permission
    denied), which signals the error path per IF-D-03.
    """
    events_path = os.path.join(project_cwd, ".fbk-capture", "events.jsonl")

    if not os.path.exists(events_path):
        # Missing events file: no events recorded yet (not an error).
        return []

    try:
        with open(events_path, encoding="utf-8", errors="replace") as fh:
            events = []
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            return events
    except OSError:
        return None


def _filter_events_by_roster(
    events: list[dict], roster: list[str]
) -> dict[str, dict]:
    """Return per-agent dicts of event data for roster agents only.

    Keys are agent_ids from the roster.  The value for each agent is a dict
    containing:
        stop_event_data   – data from the SUBAGENT_STOP event (or None)
        start_timestamps  – list of timestamps from LIFECYCLE events
        stop_timestamps   – list of timestamps from SUBAGENT_STOP events

    Off-roster events are silently excluded.
    """
    roster_set = set(roster)
    per_agent: dict[str, dict] = {
        agent_id: {
            "stop_event_data": None,
            "start_timestamps": [],
            "stop_timestamps": [],
        }
        for agent_id in roster
    }

    for event in events:
        data = event.get("data") or {}
        event_agent_id = data.get("agent_id")

        if event_agent_id not in roster_set:
            continue

        event_type = event.get("event_type", "")
        timestamp = event.get("timestamp")

        if event_type == "SUBAGENT_STOP":
            per_agent[event_agent_id]["stop_event_data"] = data
            if timestamp:
                per_agent[event_agent_id]["stop_timestamps"].append(timestamp)

        elif event_type == "LIFECYCLE":
            if timestamp:
                per_agent[event_agent_id]["start_timestamps"].append(timestamp)

    return per_agent


# ---------------------------------------------------------------------------
# First-message extractor
# ---------------------------------------------------------------------------


def _read_first_message_text(run_dir: str, agent_id: str) -> str | None:
    """Return the text of the first message from the agent's transcript.

    The transcript JSONL is opened and the first user-type record's first
    text content block is returned.  Returns None when the transcript is
    absent, unreadable, or contains no user record with text content.
    """
    transcript_path = os.path.join(run_dir, f"agent-{agent_id}.jsonl")
    try:
        with open(transcript_path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if record.get("type") != "user":
                    continue

                msg = record.get("message") or {}
                content = msg.get("content") or []
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            return block.get("text", "")
                elif isinstance(content, str):
                    return content
    except OSError:
        pass

    return None


# ---------------------------------------------------------------------------
# Timing helpers
# ---------------------------------------------------------------------------


def _earliest_ts_str(timestamps: list[str]) -> str | None:
    """Return the ISO string corresponding to the earliest parseable timestamp."""
    best_dt = None
    best_str = None
    for ts in timestamps:
        dt = token_harvester._parse_ts(ts)
        if dt is None:
            continue
        if best_dt is None or dt < best_dt:
            best_dt = dt
            best_str = ts
    return best_str


def _latest_ts_str(timestamps: list[str]) -> str | None:
    """Return the ISO string corresponding to the latest parseable timestamp."""
    best_dt = None
    best_str = None
    for ts in timestamps:
        dt = token_harvester._parse_ts(ts)
        if dt is None:
            continue
        if best_dt is None or dt > best_dt:
            best_dt = dt
            best_str = ts
    return best_str


def _duration_seconds(started_str: str | None, stopped_str: str | None) -> float | None:
    """Return the duration in seconds between started and stopped ISO strings.

    Returns None when either string is absent or unparseable.
    """
    if not started_str or not stopped_str:
        return None
    started_dt = token_harvester._parse_ts(started_str)
    stopped_dt = token_harvester._parse_ts(stopped_str)
    if started_dt is None or stopped_dt is None:
        return None
    return (stopped_dt - started_dt).total_seconds()


# ---------------------------------------------------------------------------
# Per-agent unit builder
# ---------------------------------------------------------------------------


def _build_unit(
    agent_id: str,
    run_dir: str,
    event_data: dict,
    journal_result: dict | None,
    journal_result_present: bool,
) -> dict:
    """Build the canonical per-unit dict for one roster agent.

    Parameters
    ----------
    agent_id:
        The agent's identifier.
    run_dir:
        Path to the workflow run directory (used to locate the transcript).
    event_data:
        Dict from _filter_events_by_roster for this agent, containing
        stop_event_data, start_timestamps, and stop_timestamps.
    journal_result:
        The structured result from the journal, or None.
    journal_result_present:
        Whether a result line existed in the journal for this agent.
    """
    # --- Attribution: descriptor parse from first message only ---
    first_message_text = _read_first_message_text(run_dir, agent_id)
    if first_message_text is not None:
        descriptor = attribution.parse_attribution(first_message_text)
    else:
        descriptor = {"cardinality": None, "stance": None, "attribution_absent": True}

    attribution_absent = descriptor.get("attribution_absent", True)
    cardinality = descriptor.get("cardinality")
    stance = descriptor.get("stance")

    # asset_bundle from descriptor; fall back to empty when absent
    raw_asset_bundle = descriptor.get("asset_bundle") or {}
    persona_from_descriptor = raw_asset_bundle.get("persona")

    # --- Shape: prefer descriptor persona, fall back to SubagentStop agent_type ---
    stop_data = event_data.get("stop_event_data") or {}
    agent_type_from_event = stop_data.get("agent_type")

    persona_for_shape = persona_from_descriptor if persona_from_descriptor else agent_type_from_event
    shape = shapes.resolve_shape(persona_for_shape)

    # --- Timing: earliest start, latest stop ---
    started_at = _earliest_ts_str(event_data.get("start_timestamps") or [])
    stopped_at = _latest_ts_str(event_data.get("stop_timestamps") or [])
    duration_s = _duration_seconds(started_at, stopped_at)

    # --- Tokens: from transcript ---
    transcript_path = os.path.join(run_dir, f"agent-{agent_id}.jsonl")
    token_result = token_harvester.transcript_token_totals(transcript_path)
    tokens_available = token_result["available"]
    if tokens_available:
        tokens = token_result["tokens"]
    else:
        tokens = {
            "input_tokens": None,
            "output_tokens": None,
            "cache_read_input_tokens": None,
            "cache_creation_input_tokens": None,
        }

    # gate_outcome: look for a VERIFICATION_RESULT event for this agent
    # (not available in this slice — null per schema)
    gate_outcome = None

    return {
        "agent_id": agent_id,
        "label": None,
        "phase": None,
        "shape": shape,
        "topology": {
            "cardinality": cardinality,
            "stance": stance,
        },
        "asset_bundle": {
            "instructions": None,
            "persona": persona_from_descriptor,
            "decision_tree": None,
        },
        "attribution_absent": attribution_absent,
        "started_at": started_at,
        "stopped_at": stopped_at,
        "duration_s": duration_s,
        "tokens": tokens,
        "tokens_available": tokens_available,
        "gate_outcome": gate_outcome,
        "journal_result_present": journal_result_present,
        "journal_result": journal_result,
    }


# ---------------------------------------------------------------------------
# Record assembler
# ---------------------------------------------------------------------------


def _assemble_record(
    run_id: str,
    units: list[dict],
    harvested_at: str,
    completeness: str,
) -> dict:
    """Build the top-level durable record dict from the assembled units.

    Field names are copied verbatim from the canonical schema.
    """
    return {
        "schema_version": "1.0",
        "run_id": run_id,
        "harvested_at": harvested_at,
        "workflow_name": None,
        "finalized": True,
        "completeness": completeness,
        "units": units,
        "phases": [],
        "ceremony_metrics": None,
    }


# ---------------------------------------------------------------------------
# Redaction: apply schema.redact to the free-text fields in the record
# ---------------------------------------------------------------------------


def _redact_record(record: dict, level: str) -> dict:
    """Return a copy of the record with free-text fields redacted at level.

    Applies schema.redact to journal_result (per unit) and any other
    descriptor-derived dict fields that may carry free-text keys.
    The structural fields (agent_id, shape, topology, tokens, etc.) are
    never in FREETEXT_KEYS and survive unchanged.
    """
    if level == "full":
        return record

    redacted_units = []
    for unit in record.get("units", []):
        redacted_unit = dict(unit)

        # Redact journal_result (may contain free-text keys like "output")
        if unit.get("journal_result") is not None:
            redacted_unit["journal_result"] = schema.redact(
                unit["journal_result"], level
            )

        # Redact asset_bundle (may carry free-text keys from the descriptor)
        if unit.get("asset_bundle") is not None:
            redacted_unit["asset_bundle"] = schema.redact(
                unit["asset_bundle"], level
            )

        redacted_units.append(redacted_unit)

    result = dict(record)
    result["units"] = redacted_units
    return result


# ---------------------------------------------------------------------------
# Confined atomic write
# ---------------------------------------------------------------------------


def _confined_write(
    project_cwd: str, run_id: str, record: dict
) -> tuple[str | None, str | None]:
    """Write the record atomically to the confined runs/ directory.

    Resolves the real capture dir via gate_check._real_capture_dir.  Refuses
    to write when:
    - _real_capture_dir returns None
    - runs/ is a symlink
    - runs/ realpath escapes the confined capture dir

    Uses a unique pid/uuid temp name, then os.replace to the final path.

    Returns (record_path, error_message).  On success error_message is None.
    On failure record_path is None and error_message describes the problem.
    """
    real_capture_dir = gate_check._real_capture_dir(project_cwd)
    if real_capture_dir is None:
        return None, "capture dir absent or unsafe"

    runs_dir = os.path.join(real_capture_dir, "runs")

    # Refuse a symlinked runs/
    if os.path.exists(runs_dir) and os.path.islink(runs_dir):
        return None, "runs/ is a symlink — write refused"

    # Create runs/ when it doesn't yet exist
    os.makedirs(runs_dir, exist_ok=True)

    # Refuse if runs/ realpath escapes the capture dir
    real_runs = os.path.realpath(runs_dir)
    if not real_runs.startswith(real_capture_dir + os.sep) and real_runs != real_capture_dir:
        return None, "runs/ realpath escapes the confined capture dir"

    final_path = os.path.join(runs_dir, f"{run_id}.json")
    pid = os.getpid()
    unique_id = str(uuid.uuid4())
    temp_name = f".harvest-{pid}-{unique_id}.tmp"
    temp_path = os.path.join(runs_dir, temp_name)

    try:
        with open(temp_path, "w", encoding="utf-8") as fh:
            json.dump(record, fh, indent=2)
        os.replace(temp_path, final_path)
    except OSError as exc:
        # Clean up temp on failure if it exists
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        return None, f"write failed: {exc}"

    return final_path, None


# ---------------------------------------------------------------------------
# Main public entry point
# ---------------------------------------------------------------------------


def harvest(run_id: str, project_cwd: str) -> HarvestResult:
    """Harvest the durable run record for run_id.

    Resolves the run directory, joins the journal roster with the event stream
    and per-agent transcripts, assembles the canonical record, redacts
    free-text at the project's capture level, and writes the record atomically.

    Always writes finalized=True.  When a finalized record already exists,
    returns immediately without re-reading the run directory (no-op that
    preserves the original harvested_at).

    At capture level "off", writes no record and returns a result with no
    record_path set.

    Parameters
    ----------
    run_id:
        The workflow run directory name used to locate the run.
    project_cwd:
        The project root path, used to resolve the capture dir and events.

    Returns
    -------
    HarvestResult with record_path, unit_count, units_with_full_attribution,
    completeness, finalized, and error set.
    """
    # --- Resolve capture level ---
    capture_level = gate_check.resolve_capture_level(project_cwd)

    # At "off" level: write no free-text record.
    if capture_level == "off":
        return HarvestResult(
            completeness="truncated",
            finalized=False,
            error=None,
        )

    # --- Resolve runs/ directory for idempotency check ---
    real_capture_dir = gate_check._real_capture_dir(project_cwd)
    if real_capture_dir is not None:
        record_path_candidate = os.path.join(
            real_capture_dir, "runs", f"{run_id}.json"
        )
    else:
        record_path_candidate = None

    # --- Idempotency: if a finalized record already exists, no-op ---
    if record_path_candidate and os.path.isfile(record_path_candidate):
        try:
            with open(record_path_candidate, encoding="utf-8") as fh:
                existing = json.load(fh)
            if existing.get("finalized") is True:
                return HarvestResult(
                    record_path=record_path_candidate,
                    unit_count=len(existing.get("units", [])),
                    units_with_full_attribution=sum(
                        1 for u in existing.get("units", [])
                        if not u.get("attribution_absent", True)
                    ),
                    completeness=existing.get("completeness", "truncated"),
                    finalized=True,
                    error=None,
                )
        except (OSError, json.JSONDecodeError):
            pass  # Fall through to re-harvest if we can't read the existing record

    # --- Resolve run directory ---
    run_dir = _resolve_run_dir(run_id)
    if run_dir is None:
        return HarvestResult(error=f"run directory not found for run_id={run_id!r}")

    # --- Read events (error path: unreadable events → error, no write) ---
    events = _read_events(project_cwd)
    if events is None:
        return HarvestResult(error="events.jsonl could not be read")

    # --- Read journal (error path: absent journal → truncated with zero units) ---
    journal_result = _read_journal(run_dir)
    if journal_result is None:
        # Missing journal: produce truncated record with empty units
        harvested_at = _utcnow().isoformat()
        record = _assemble_record(
            run_id=run_id,
            units=[],
            harvested_at=harvested_at,
            completeness="truncated",
        )
        redacted = _redact_record(record, capture_level)
        record_path, write_error = _confined_write(project_cwd, run_id, redacted)
        if write_error:
            return HarvestResult(error=write_error)
        return HarvestResult(
            record_path=record_path,
            unit_count=0,
            units_with_full_attribution=0,
            completeness="truncated",
            finalized=True,
            error=None,
        )

    roster, results_by_agent = journal_result

    # --- Filter events to the roster ---
    per_agent_events = _filter_events_by_roster(events, roster)

    # --- Build units for each roster agent ---
    units = []
    for agent_id in roster:
        event_data = per_agent_events[agent_id]
        agent_result = results_by_agent.get(agent_id)
        result_present = agent_id in results_by_agent

        unit = _build_unit(
            agent_id=agent_id,
            run_dir=run_dir,
            event_data=event_data,
            journal_result=agent_result,
            journal_result_present=result_present,
        )
        units.append(unit)

    # --- Determine completeness ---
    all_have_results = all(agent_id in results_by_agent for agent_id in roster)
    completeness = "clean-complete" if all_have_results else "truncated"

    # --- harvested_at: wall-clock time of this harvest ---
    harvested_at = _utcnow().isoformat()

    # --- Assemble record ---
    record = _assemble_record(
        run_id=run_id,
        units=units,
        harvested_at=harvested_at,
        completeness=completeness,
    )

    # --- Redact free-text ---
    redacted = _redact_record(record, capture_level)

    # --- Atomic confined write ---
    record_path, write_error = _confined_write(project_cwd, run_id, redacted)
    if write_error:
        return HarvestResult(error=write_error)

    units_with_full_attribution = sum(
        1 for u in units if not u.get("attribution_absent", True)
    )

    return HarvestResult(
        record_path=record_path,
        unit_count=len(roster),
        units_with_full_attribution=units_with_full_attribution,
        completeness=completeness,
        finalized=True,
        error=None,
    )
