#!/usr/bin/env bash
# Wait for a Firebreak turn to end: fbk-wait.sh <turn-output-file>
# An operator starts `fbk-drive.sh turn ... > <file> 2>&1` in the background and calls this until it prints DONE.
# Each call waits at most 170 seconds, so it fits inside an agent's command time limit; it prints DONE and the end of
# the file once the turn's "=== phases of" block is there, and WAITING otherwise (call it again).
f=${1:?usage: fbk-wait.sh <turn-output-file>}
timeout 170 bash -c 'until grep -q "^=== phases of" "$0" 2>/dev/null; do sleep 10; done' "$f" && { echo DONE; tail -13 "$f"; exit 0; }
echo WAITING; exit 1
