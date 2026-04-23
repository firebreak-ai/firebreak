#!/usr/bin/env bash
set -euo pipefail

# FN Retrospective Re-run
# Runs the 21 PRs scoped by the low-through-medium risk buckets in
# results/0.4.0-fullrepo-50pr-fn-retrospective.md to measure recall impact
# of the detection-audits + security-patterns + typechecker-exec changes
# shipped in commit 4596347.
#
# Buckets covered:
#   - Concurrency (7): cal_dot_com PR14943, discourse PR8/PR9, grafana PR79265/PR90939,
#                     keycloak PR40940, sentry PR3
#   - Security (2): discourse PR4, sentry PR3
#   - Compile/typecheck (3): grafana PR79265, keycloak PR36882, cal_dot_com PR11059
#   - Logic inversions (7): cal_dot_com PR8330/PR10967/PR14740/PR22345,
#                          keycloak PR36880, discourse PR3/PR10
#   - Test integrity (3): sentry PR77754/PR93824, discourse PR8
#   - Cross-function API (3): sentry PR5/PR95633, cal_dot_com PR11059
# Unique PRs: 21 (some PRs span multiple buckets)
#
# Usage:
#   ./run_fn_retro_21.sh                    # uses auto-generated timestamp
#   TOOL_NAME=firebreak-v0.4.0-custom ./run_fn_retro_21.sh
#   DRY_RUN=1 ./run_fn_retro_21.sh          # preview only

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Generate default tool-name with timestamp if not overridden
DEFAULT_TS="$(date +%Y%m%d_%H%M%S)"
TOOL_NAME="${TOOL_NAME:-firebreak-v0.4.0-${DEFAULT_TS}}"
DELAY="${DELAY:-300}"
DRY_RUN="${DRY_RUN:-0}"

LOG="$SCRIPT_DIR/logs/fn_retro_21_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$SCRIPT_DIR/logs"

# 21 unique instance_ids covering the FN retrospective low-through-medium buckets
INSTANCES=(
  "cal_dot_com__calcom__cal.com__PR8330"
  "cal_dot_com__calcom__cal.com__PR10967"
  "cal_dot_com__calcom__cal.com__PR11059"
  "cal_dot_com__calcom__cal.com__PR14740"
  "cal_dot_com__calcom__cal.com__PR14943"
  "cal_dot_com__calcom__cal.com__PR22345"
  "discourse__ai-code-review-evaluation__discourse-graphite__PR3"
  "discourse__ai-code-review-evaluation__discourse-graphite__PR4"
  "discourse__ai-code-review-evaluation__discourse-graphite__PR8"
  "discourse__ai-code-review-evaluation__discourse-graphite__PR9"
  "discourse__ai-code-review-evaluation__discourse-graphite__PR10"
  "grafana__grafana__grafana__PR79265"
  "grafana__grafana__grafana__PR90939"
  "keycloak__keycloak__keycloak__PR36880"
  "keycloak__keycloak__keycloak__PR36882"
  "keycloak__keycloak__keycloak__PR40940"
  "sentry__ai-code-review-evaluation__sentry-greptile__PR3"
  "sentry__ai-code-review-evaluation__sentry-greptile__PR5"
  "sentry__getsentry__sentry__PR77754"
  "sentry__getsentry__sentry__PR93824"
  "sentry__getsentry__sentry__PR95633"
)

TOTAL=${#INSTANCES[@]}

{
  echo "═══════════════════════════════════════════════════════════"
  echo "  FN Retrospective Re-run — 21 PRs"
  echo "═══════════════════════════════════════════════════════════"
  echo "  Tool name: $TOOL_NAME"
  echo "  Delay:     ${DELAY}s between PRs"
  echo "  Log:       $LOG"
  echo "  Dry run:   $DRY_RUN"
  echo "  Started:   $(date)"
  echo "═══════════════════════════════════════════════════════════"
  echo ""
} | tee "$LOG"

for i in "${!INSTANCES[@]}"; do
  idx=$((i + 1))
  id="${INSTANCES[$i]}"
  echo "[$idx/$TOTAL] $id" | tee -a "$LOG"

  if [[ "$DRY_RUN" == "1" ]]; then
    echo "    (dry run — would call run_reviews.sh --start-from $id --limit 1)" | tee -a "$LOG"
  else
    # Delegate to run_reviews.sh one-at-a-time so resume-safety, worktree build,
    # token logging, and full-repo / diff-only plumbing stay consistent.
    # --delay 0 inside the child because we sleep in this parent loop.
    "$SCRIPT_DIR/run_reviews.sh" \
      --start-from "$id" \
      --limit 1 \
      --tool-name "$TOOL_NAME" \
      --delay 0 \
      2>&1 | tee -a "$LOG"
  fi

  # Sleep between PRs except after the last one
  if [[ "$idx" -lt "$TOTAL" && "$DRY_RUN" != "1" ]]; then
    echo "    sleeping ${DELAY}s before next PR..." | tee -a "$LOG"
    sleep "$DELAY"
  fi
done

{
  echo ""
  echo "═══════════════════════════════════════════════════════════"
  echo "  Finished: $(date)"
  echo "  Tool name: $TOOL_NAME"
  echo "  Reviews in: $SCRIPT_DIR/reviews/"
  echo "═══════════════════════════════════════════════════════════"
} | tee -a "$LOG"
