#!/usr/bin/env python3
"""dispatch_status.py — Read pipeline state and format human-readable output"""

import argparse
import json
import os
import sys


def format_status(state_dict):
    """Format pipeline state as human-readable text.

    Args:
        state_dict: Parsed JSON state dictionary

    Returns:
        Formatted string with feature name, status, timestamps, stage history,
        PARKED info (if applicable), and error history (if present).
    """
    spec = state_dict.get("spec_name", "unknown")
    current = state_dict.get("current_state", "UNKNOWN")
    timestamps = state_dict.get("stage_timestamps", {})
    parked_info = state_dict.get("parked_info", {})
    error_history = state_dict.get("error_history", [])

    # Sort stages by timestamp
    sorted_stages = sorted(timestamps.items(), key=lambda x: x[1])
    last_ts = sorted_stages[-1][1] if sorted_stages else "N/A"

    lines = []
    lines.append(f"Feature: {spec}")
    lines.append(f"Status: {current}")
    lines.append(f"Last transition: {last_ts}")
    lines.append("")
    lines.append("Stage history:")
    for stage_name, ts in sorted_stages:
        lines.append(f"  {stage_name:<20} {ts}")

    if current == "PARKED" and parked_info:
        lines.append("")
        lines.append(f"PARKED at: {parked_info.get('failed_stage', 'unknown')}")
        lines.append(f"Reason: {parked_info.get('reason', 'unknown')}")

    if error_history:
        lines.append("")
        lines.append("Errors:")
        for entry in error_history:
            stage = entry.get("stage", "?")
            error = entry.get("error", "?")
            ts = entry.get("timestamp", "?")
            lines.append(f"  [{stage}] {error} ({ts})")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Read pipeline state and format human-readable output"
    )
    parser.add_argument("spec_name", help="Name of the spec/pipeline")
    args = parser.parse_args()

    state_dir = os.environ.get("STATE_DIR", ".claude/automation/state")
    state_file = os.path.join(state_dir, f"{args.spec_name}.json")

    if not os.path.isfile(state_file):
        print(f"No pipeline state found for '{args.spec_name}'", file=sys.stderr)
        sys.exit(1)

    with open(state_file) as f:
        state_dict = json.load(f)

    output = format_status(state_dict)
    print(output)

    # Log to audit logger (skip if not found)
    try:
        from fbk.audit import log_event
        log_event(
            args.spec_name,
            "status_query",
            {"queried_state": state_dict.get("current_state", "UNKNOWN")}
        )
    except (ImportError, Exception):
        pass


if __name__ == "__main__":
    main()
