#!/usr/bin/env python3
"""Audit logger — appends structured JSON lines to per-spec log files."""

import argparse
import datetime
import json
import os
import sys


def get_log_dir():
    return os.environ.get("LOG_DIR", ".claude/automation/logs")


def get_log_path(spec_name):
    return os.path.join(get_log_dir(), f"{spec_name}.log")


def log_event(spec_name, event_type, json_data_str):
    try:
        data = json.loads(json_data_str)
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON data: {e}", file=sys.stderr)
        sys.exit(1)

    entry = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "spec": spec_name,
        "event_type": event_type,
        "data": data,
    }

    log_dir = get_log_dir()
    os.makedirs(log_dir, exist_ok=True)

    with open(get_log_path(spec_name), "a") as f:
        f.write(json.dumps(entry) + "\n")


def read_log(spec_name):
    path = get_log_path(spec_name)
    if not os.path.exists(path):
        print(f"Error: no log file for '{spec_name}'", file=sys.stderr)
        sys.exit(1)
    with open(path) as f:
        print(f.read(), end="")


def main():
    parser = argparse.ArgumentParser(description="Audit logger")
    sub = parser.add_subparsers(dest="command")

    p_log = sub.add_parser("log")
    p_log.add_argument("spec_name")
    p_log.add_argument("event_type")
    p_log.add_argument("json_data")

    p_read = sub.add_parser("read")
    p_read.add_argument("spec_name")

    args = parser.parse_args()

    if args.command == "log":
        log_event(args.spec_name, args.event_type, args.json_data)
    elif args.command == "read":
        read_log(args.spec_name)
    else:
        parser.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()
