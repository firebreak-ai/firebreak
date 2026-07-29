#!/usr/bin/env bash
set -euo pipefail

# Run 4 reviews per repo across all 5 repos = 20 balanced PRs
# Used for v0.4.0-single-detector candidate evaluation

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOL_NAME="${TOOL_NAME:-firebreak-v0.4.0-single-detector}"
LOG="$SCRIPT_DIR/logs/balanced20_$(date +%Y%m%d_%H%M%S).log"

echo "Tool name: $TOOL_NAME" | tee "$LOG"
echo "Log:       $LOG" | tee -a "$LOG"
echo "Started:   $(date)" | tee -a "$LOG"
echo "" | tee -a "$LOG"

for repo in cal_dot_com discourse grafana keycloak sentry; do
  echo "═══ Repo: $repo (4 reviews) ═══" | tee -a "$LOG"
  "$SCRIPT_DIR/run_reviews.sh" \
    --repo "$repo" \
    --limit 4 \
    --tool-name "$TOOL_NAME" \
    --delay 300 \
    2>&1 | tee -a "$LOG"
  echo "" | tee -a "$LOG"
done

echo "Finished: $(date)" | tee -a "$LOG"
echo "Reviews in: $SCRIPT_DIR/reviews/" | tee -a "$LOG"
