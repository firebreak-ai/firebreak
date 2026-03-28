#!/usr/bin/env python3
"""Pipeline state engine — manages per-spec JSON state with transition enforcement."""

import argparse
import datetime
import json
import os
import sys

VALID_TRANSITIONS = {
    "QUEUED": ["VALIDATING"],
    "VALIDATING": ["VALIDATED", "PARKED"],
    "VALIDATED": ["REVIEWING"],
    "REVIEWING": ["REVIEWED", "PARKED"],
    "REVIEWED": ["BREAKING_DOWN"],
    "BREAKING_DOWN": ["BROKEN_DOWN", "PARKED"],
    "BROKEN_DOWN": ["TASK_REVIEWING"],
    "TASK_REVIEWING": ["TASKS_READY", "PARKED"],
    "TASKS_READY": ["TESTING"],
    "TESTING": ["TESTS_WRITTEN", "PARKED"],
    "TESTS_WRITTEN": ["TEST_REVIEWING"],
    "TEST_REVIEWING": ["TESTS_READY", "PARKED"],
    "TESTS_READY": ["IMPLEMENTING"],
    "IMPLEMENTING": ["IMPLEMENTED", "PARKED"],
    "IMPLEMENTED": ["VERIFYING"],
    "VERIFYING": ["COMPLETED", "PARKED"],
    "COMPLETED": [],
    "PARKED": ["READY"],
    "READY": [],  # dynamic — resolved at runtime from parked_info.failed_stage
}

ALL_STATES = set(VALID_TRANSITIONS.keys())


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def get_state_dir():
    return os.environ.get("STATE_DIR", ".claude/automation/state")


def get_state_path(spec_name):
    return os.path.join(get_state_dir(), f"{spec_name}.json")


def load_state(spec_name):
    path = get_state_path(spec_name)
    if not os.path.exists(path):
        print(f"Error: no state file for '{spec_name}'", file=sys.stderr)
        sys.exit(1)
    with open(path) as f:
        return json.load(f)


def save_state(spec_name, state):
    path = get_state_path(spec_name)
    with open(path, "w") as f:
        json.dump(state, f, indent=2)


def get_valid_for_state(state):
    current = state["current_state"]
    if current == "READY":
        parked_info = state.get("parked_info", {})
        failed_stage = parked_info.get("failed_stage")
        if not failed_stage:
            print("Error: READY state but no parked_info.failed_stage", file=sys.stderr)
            sys.exit(1)
        return [failed_stage]
    return VALID_TRANSITIONS.get(current, [])


def create_state(spec_name):
    path = get_state_path(spec_name)
    if os.path.exists(path):
        print(f"Error: state already exists for '{spec_name}'", file=sys.stderr)
        return 1
    os.makedirs(get_state_dir(), exist_ok=True)
    state = {
        "spec_name": spec_name,
        "current_state": "QUEUED",
        "stage_timestamps": {"QUEUED": now_iso()},
        "agent_ids": [],
        "verification_results": {},
        "error_history": [],
        "parked_info": {},
    }
    save_state(spec_name, state)
    print(json.dumps(state, indent=2))
    return 0


def read_state(spec_name):
    state = load_state(spec_name)
    print(json.dumps(state, indent=2))
    return 0


def transition_state(spec_name, new_state, reason=None):
    state = load_state(spec_name)
    current = state["current_state"]
    valid = get_valid_for_state(state)

    if new_state not in valid:
        print(
            f"Error: invalid transition {current} -> {new_state}. "
            f"Valid transitions: {valid}",
            file=sys.stderr,
        )
        return 1

    prev_state = current
    state["current_state"] = new_state
    state["stage_timestamps"][new_state] = now_iso()

    if new_state == "PARKED":
        state["parked_info"] = {
            "failed_stage": prev_state,
            "reason": reason or "",
        }
        state["error_history"].append({
            "stage": prev_state,
            "error": reason or "",
            "timestamp": now_iso(),
        })
    elif prev_state == "READY":
        state["parked_info"] = {}

    save_state(spec_name, state)
    print(json.dumps(state, indent=2))
    return 0


def get_valid_transitions(spec_name):
    state = load_state(spec_name)
    valid = get_valid_for_state(state)
    print(json.dumps(valid, indent=2))
    return 0


def main():
    parser = argparse.ArgumentParser(description="Pipeline state engine")
    sub = parser.add_subparsers(dest="command")

    p_create = sub.add_parser("create")
    p_create.add_argument("spec_name")

    p_transition = sub.add_parser("transition")
    p_transition.add_argument("spec_name")
    p_transition.add_argument("new_state")
    p_transition.add_argument("--reason", default=None)

    p_read = sub.add_parser("read")
    p_read.add_argument("spec_name")

    p_valid = sub.add_parser("get-valid-transitions")
    p_valid.add_argument("spec_name")

    args = parser.parse_args()

    if args.command == "create":
        sys.exit(create_state(args.spec_name))
    elif args.command == "transition":
        sys.exit(transition_state(args.spec_name, args.new_state, args.reason))
    elif args.command == "read":
        sys.exit(read_state(args.spec_name))
    elif args.command == "get-valid-transitions":
        sys.exit(get_valid_transitions(args.spec_name))
    else:
        parser.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()
