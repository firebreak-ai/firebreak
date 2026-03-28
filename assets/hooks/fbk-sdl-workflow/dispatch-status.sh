#!/usr/bin/env bash
# dispatch-status.sh — Read pipeline state and format human-readable output
# chmod +x dispatch-status.sh
set -uo pipefail

SPEC_NAME="${1:-}"

[[ -z "$SPEC_NAME" ]] && { echo "Usage: dispatch-status.sh <spec-name>" >&2; exit 2; }

STATE_DIR="${STATE_DIR:-.claude/automation/state}"
STATE_FILE="$STATE_DIR/$SPEC_NAME.json"

if [[ ! -f "$STATE_FILE" ]]; then
  echo "No pipeline state found for '$SPEC_NAME'" >&2
  exit 1
fi

python3 - "$STATE_FILE" <<'PYEOF'
import json, sys

state_file = sys.argv[1]
with open(state_file) as f:
    state = json.load(f)

spec = state.get("spec_name", "unknown")
current = state.get("current_state", "UNKNOWN")
timestamps = state.get("stage_timestamps", {})
parked_info = state.get("parked_info", {})
error_history = state.get("error_history", [])

# Sort stages by timestamp
sorted_stages = sorted(timestamps.items(), key=lambda x: x[1])
last_ts = sorted_stages[-1][1] if sorted_stages else "N/A"

print(f"Feature: {spec}")
print(f"Status: {current}")
print(f"Last transition: {last_ts}")
print()
print("Stage history:")
for stage_name, ts in sorted_stages:
    print(f"  {stage_name:<20} {ts}")

if current == "PARKED" and parked_info:
    print()
    print(f"PARKED at: {parked_info.get('failed_stage', 'unknown')}")
    print(f"Reason: {parked_info.get('reason', 'unknown')}")

if error_history:
    print()
    print("Errors:")
    for entry in error_history:
        stage = entry.get("stage", "?")
        error = entry.get("error", "?")
        ts = entry.get("timestamp", "?")
        print(f"  [{stage}] {error} ({ts})")
PYEOF

# Log to audit logger (skip if not found)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOGGER="$SCRIPT_DIR/audit-logger.py"
if [[ -f "$LOGGER" ]]; then
  CURRENT=$(python3 -c "import json; print(json.load(open('$STATE_FILE'))['current_state'])" 2>/dev/null)
  python3 "$LOGGER" log "$SPEC_NAME" status_query "{\"queried_state\":\"$CURRENT\"}" 2>/dev/null || true
fi
