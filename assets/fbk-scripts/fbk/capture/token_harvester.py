"""Post-hoc stage token harvester — attributes transcript turns to SDL stages.

Reads Claude Code session transcripts (JSONL) and attributes each assistant
turn to the SDL stage active at its timestamp, using a hard split on the state
engine's transition timestamps.  Aggregates across multiple transcripts for
one cycle into a single per-stage total set.

Unavailable-vs-zero distinction: a missing or unreadable transcript marks its
contributed stages available=False and omits token totals entirely, so a
report renderer can show 'unavailable' rather than a misleading zero.

This module is a pure reader: it never writes events or modifies any file.
"""

import datetime
import json


# ---------------------------------------------------------------------------
# Timestamp parsing
# ---------------------------------------------------------------------------


def _parse_ts(s):
    """Parse an ISO-8601 timestamp string; return a timezone-aware datetime or None."""
    if not s:
        return None
    try:
        return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Per-file parsing (ported from prototype harvest_file)
# ---------------------------------------------------------------------------


def _parse_transcript(path):
    """Parse one transcript JSONL and return a list of per-turn dicts.

    Each turn dict carries:
        timestamp       (datetime, tz-aware)
        input_tokens    (int)
        output_tokens   (int)
        cache_read_input_tokens     (int)
        cache_creation_input_tokens (int)
        model           (str)
        tool_calls      (int)
        tool_errors     (int)

    Returns None when the file cannot be opened (missing or permission error),
    so the caller can distinguish unavailable from an empty-but-readable file.
    """
    try:
        f = open(path, encoding="utf-8", errors="replace")
    except OSError:
        return None

    turns = []
    tool_names_by_id = {}

    with f:
        for line in f:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue

            rtype = rec.get("type", "")
            msg = rec.get("message")

            if rtype == "assistant" and isinstance(msg, dict):
                ts = _parse_ts(rec.get("timestamp", ""))
                if ts is None:
                    continue

                usage = msg.get("usage") or {}
                model = msg.get("model", "unknown")

                input_tokens = usage.get("input_tokens") or 0
                output_tokens = usage.get("output_tokens") or 0
                cache_read = usage.get("cache_read_input_tokens") or 0
                cache_creation = usage.get("cache_creation_input_tokens") or 0

                tool_call_count = 0
                content = msg.get("content")
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            tool_call_count += 1
                            if block.get("id"):
                                tool_names_by_id[block["id"]] = block.get("name", "?")

                turns.append({
                    "timestamp": ts,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cache_read_input_tokens": cache_read,
                    "cache_creation_input_tokens": cache_creation,
                    "model": model,
                    "tool_calls": tool_call_count,
                    "tool_errors": 0,  # errors come from user records; accumulated below
                    "_tool_result_pending": False,
                })

            elif rtype == "user" and isinstance(msg, dict):
                content = msg.get("content")
                if isinstance(content, list):
                    for block in content:
                        if (
                            isinstance(block, dict)
                            and block.get("type") == "tool_result"
                            and block.get("is_error")
                        ):
                            # Attribute the error to the most-recent turn that used that tool.
                            # For simplicity, increment the last turn's tool_errors.
                            if turns:
                                turns[-1]["tool_errors"] += 1

    return turns


# ---------------------------------------------------------------------------
# Stage-boundary helpers
# ---------------------------------------------------------------------------


def _build_stage_boundaries(transitions):
    """Convert ordered transitions list to a list of (stage, start_ts, interval_seconds).

    Each entry carries:
        stage          (str)
        start_ts       (datetime, tz-aware)
        interval_s     (float or None)  — seconds to the next stage start;
                                          None for the last stage

    Entries with an unparseable timestamp are skipped.
    """
    parsed = []
    for entry in transitions:
        ts = _parse_ts(entry.get("timestamp", ""))
        if ts is not None:
            parsed.append((entry["stage"], ts))

    boundaries = []
    for i, (stage, start_ts) in enumerate(parsed):
        if i + 1 < len(parsed):
            next_ts = parsed[i + 1][1]
            interval_s = (next_ts - start_ts).total_seconds()
        else:
            interval_s = None
        boundaries.append({"stage": stage, "start_ts": start_ts, "interval_s": interval_s})
    return boundaries


def _attribute_turn(turn_ts, boundaries):
    """Return the index into boundaries of the stage that owns turn_ts.

    Hard split: a turn strictly before a boundary's start belongs to the
    preceding stage; a turn at-or-after belongs to that stage.
    The first stage captures anything before its own start (edge case: turns
    before any boundary go to the first stage).
    """
    # Walk from last boundary backwards; the first one whose start_ts <= turn_ts wins.
    for i in range(len(boundaries) - 1, -1, -1):
        if turn_ts >= boundaries[i]["start_ts"]:
            return i
    # turn_ts is before all boundaries — assign to the first stage
    return 0


def _is_boundary_adjacent(turn_ts, stage_idx, boundaries):
    """Return True when turn_ts is within one transition-interval of any boundary of its stage.

    A stage's boundaries are:
        - its own start_ts  (start boundary)
        - the next stage's start_ts  (end boundary, equal to start_ts + interval_s)

    The interval used is the stage's own interval_s (gap to next stage).  When
    there is no next stage (last stage), use the preceding stage's interval if
    available; if the stage is also the first (single-stage run), every turn is
    considered adjacent.
    """
    b = boundaries[stage_idx]
    interval_s = b["interval_s"]

    if interval_s is None:
        # Last stage: derive the comparison interval from the preceding stage.
        if stage_idx > 0:
            interval_s = boundaries[stage_idx - 1]["interval_s"]
        if interval_s is None:
            # Only one stage — every turn is adjacent by definition.
            return True
        # Only start boundary applies for the last stage.
        start_delta = abs((turn_ts - b["start_ts"]).total_seconds())
        return start_delta <= interval_s

    # Non-last stage: adjacent if within interval_s of start or end boundary.
    start_delta = abs((turn_ts - b["start_ts"]).total_seconds())
    end_ts = b["start_ts"] + datetime.timedelta(seconds=interval_s)
    end_delta = abs((turn_ts - end_ts).total_seconds())
    return start_delta <= interval_s or end_delta <= interval_s


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def transcript_token_totals(transcript_path: str) -> dict:
    """Sum token usage across all turns in one transcript.

    Args:
        transcript_path: Path to a transcript JSONL file.

    Returns:
        dict with keys:
            available (bool): True if the transcript is readable; False if missing or unreadable.
            tokens (dict): When available is True, a dict with four keys:
                    input_tokens, output_tokens, cache_read_input_tokens, cache_creation_input_tokens
                    (each int, summed across all turns).
                When available is False, an empty dict.

    The function preserves the project's "available-vs-zero" semantics: an
    unreadable or missing transcript is marked available=False with empty tokens,
    never as zero. A readable-but-empty transcript yields available=True with
    all four token fields summed to 0.
    """
    turns = _parse_transcript(transcript_path)
    if turns is None:
        # Unreadable or missing — mark unavailable with empty tokens.
        return {"available": False, "tokens": {}}

    # Readable transcript (possibly empty) — sum all four token fields.
    totals = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_input_tokens": 0,
        "cache_creation_input_tokens": 0,
    }
    for turn in turns:
        totals["input_tokens"] += turn["input_tokens"]
        totals["output_tokens"] += turn["output_tokens"]
        totals["cache_read_input_tokens"] += turn["cache_read_input_tokens"]
        totals["cache_creation_input_tokens"] += turn["cache_creation_input_tokens"]

    return {"available": True, "tokens": totals}


def harvest(transcript_paths, transitions):
    """Attribute transcript turns to SDL stages and aggregate across all transcripts.

    Args:
        transcript_paths: Ordered list of transcript JSONL file paths for one cycle.
        transitions:      Ordered list of dicts, each {"stage": str, "timestamp": ISO-8601}.

    Returns:
        dict mapping stage name → stage entry dict.  Each stage entry has:
            available               (bool)
            tokens_by_type          (dict: input_tokens/output_tokens/
                                          cache_read_input_tokens/
                                          cache_creation_input_tokens → int)
                                    omitted (empty dict) when available is False
            tokens_by_model         (dict: model → token dict)
            tool_calls              (int)
            tool_errors             (int)
            boundary_adjacent_turns (int)

    A stage is available True only when at least one turn is attributed to it
    from a readable transcript; its token totals are then real counts.  When a
    stage's turns lived only in unreadable or missing transcripts (or it had no
    attributed turns at all), available is False and its totals are absent — so
    "no readable data" stays distinct from "zero tokens".
    """
    boundaries = _build_stage_boundaries(transitions)
    if not boundaries:
        return {}

    stage_names = [b["stage"] for b in boundaries]

    # Track per-stage accumulated state.
    # readable_counts: how many readable transcripts contributed to a stage.
    readable_counts = {name: 0 for name in stage_names}
    # Token sums and counters — only accumulated while the transcript is readable.
    stage_totals = {
        name: {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 0,
        }
        for name in stage_names
    }
    stage_by_model = {name: {} for name in stage_names}
    stage_tool_calls = {name: 0 for name in stage_names}
    stage_tool_errors = {name: 0 for name in stage_names}
    stage_boundary_adjacent = {name: 0 for name in stage_names}

    for path in transcript_paths:
        turns = _parse_transcript(path)
        if turns is None:
            # Unreadable — do not contribute to any stage.
            continue

        for turn in turns:
            idx = _attribute_turn(turn["timestamp"], boundaries)
            stage = boundaries[idx]["stage"]

            # A turn attributed from this readable transcript makes the stage
            # available — so a stage whose turns lived only in an unreadable
            # transcript stays unavailable rather than reading as zero.
            readable_counts[stage] += 1

            # Accumulate token totals.
            for key in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
                stage_totals[stage][key] += turn[key]

            # Accumulate per-model token totals.
            model = turn["model"]
            if model not in stage_by_model[stage]:
                stage_by_model[stage][model] = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_read_input_tokens": 0,
                    "cache_creation_input_tokens": 0,
                }
            for key in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
                stage_by_model[stage][model][key] += turn[key]

            # Accumulate tool counts.
            stage_tool_calls[stage] += turn["tool_calls"]
            stage_tool_errors[stage] += turn["tool_errors"]

            # Boundary-adjacency.
            if _is_boundary_adjacent(turn["timestamp"], idx, boundaries):
                stage_boundary_adjacent[stage] += 1

    # Build result.
    result = {}
    for name in stage_names:
        available = readable_counts[name] > 0
        if available:
            result[name] = {
                "available": True,
                "tokens_by_type": dict(stage_totals[name]),
                "tokens_by_model": stage_by_model[name],
                "tool_calls": stage_tool_calls[name],
                "tool_errors": stage_tool_errors[name],
                "boundary_adjacent_turns": stage_boundary_adjacent[name],
            }
        else:
            result[name] = {
                "available": False,
                "tokens_by_type": {},
                "tokens_by_model": {},
                "tool_calls": None,
                "tool_errors": None,
                "boundary_adjacent_turns": None,
            }

    return result
