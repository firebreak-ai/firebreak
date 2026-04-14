#!/usr/bin/env bash
set -euo pipefail

# Usage: confidence.sh <self_score> <agent_count> <challenger_verdict>
#   self_score:         1-10 (detector's self-assessed confidence)
#   agent_count:        1+  (number of independent agents that reported this sighting)
#   challenger_verdict: confirmed | weakened
#
# Output: <final_score> <pass|fail>
#   final_score: 1.0-10.0 (one decimal place)
#   pass/fail:   pass if >= 6.0, fail otherwise

SELF_SCORE="${1:?Usage: confidence.sh <self_score> <agent_count> <challenger_verdict>}"
AGENT_COUNT="${2:?Usage: confidence.sh <self_score> <agent_count> <challenger_verdict>}"
VERDICT="${3:?Usage: confidence.sh <self_score> <agent_count> <challenger_verdict>}"

awk -v s="$SELF_SCORE" -v a="$AGENT_COUNT" -v v="$VERDICT" 'BEGIN {
  score = s
  for (i = 1; i < a; i++) score *= 1.2
  if (v == "confirmed") score *= 1.2
  else if (v == "weakened") score *= 0.8
  if (score > 10) score = 10
  printf "%.1f %s\n", score, (score >= 8.0 ? "pass" : "fail")
}'
