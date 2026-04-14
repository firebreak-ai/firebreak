#!/usr/bin/env bash
set -euo pipefail

# Martian Benchmark Review Runner
# Automates Firebreak code reviews against the Martian Code Review Benchmark
# using Claude Code headless mode (claude -p).
#
# Usage:
#   ./run_reviews.sh [flags]
#   ./run_reviews.sh --model sonnet --limit 5 --repo grafana
#   ./run_reviews.sh --full-pipeline --tool-name firebreak-opus

# ── Configuration ────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
MANIFEST="$SCRIPT_DIR/manifest.json"
REVIEWS_DIR="$SCRIPT_DIR/reviews"
DIFFS_DIR="$SCRIPT_DIR/diffs"
LOGS_DIR="$SCRIPT_DIR/logs"
PROMPT_FILE="$SCRIPT_DIR/benchmark-prompt.md"

MODEL="opus"
LIMIT=0
REPO_FILTER=""
START_FROM=""
DELAY=300     # 5 min between reviews — prevents 529 overload that degrades to inline execution
MAX_RETRIES=2
MAX_BUDGET=15
TOOL_NAME="firebreak"
FULL_PIPELINE=false
DRY_RUN=false

# ── Usage ────────────────────────────────────────────────────────

usage() {
  cat <<'EOF'
Usage: run_reviews.sh [flags]

Flags:
  --model <alias>       Orchestrator model (default: opus)
                        Detector/Challenger stay on sonnet per agent definitions
  --limit <N>           Stop after N reviews (default: 0 = all)
  --repo <name>         Filter to one source repo
                        (cal_dot_com, sentry, grafana, discourse, keycloak)
  --start-from <id>     Skip entries before this instance_id
  --delay <N>           Seconds between reviews (default: 10)
  --max-budget <N>      Per-review USD cap (default: 15)
  --max-retries <N>     Retry attempts per review (default: 2)
  --tool-name <name>    Tool identifier for inject/judge (default: firebreak)
  --full-pipeline       After reviews, run inject_results.py + judge_anthropic.py
  --dry-run             Print commands without executing
  -h, --help            Show this help
EOF
  exit 0
}

# ── Argument parsing ─────────────────────────────────────────────

while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)       MODEL="$2"; shift 2 ;;
    --limit)       LIMIT="$2"; shift 2 ;;
    --repo)        REPO_FILTER="$2"; shift 2 ;;
    --start-from)  START_FROM="$2"; shift 2 ;;
    --delay)       DELAY="$2"; shift 2 ;;
    --max-budget)  MAX_BUDGET="$2"; shift 2 ;;
    --max-retries) MAX_RETRIES="$2"; shift 2 ;;
    --tool-name)   TOOL_NAME="$2"; shift 2 ;;
    --full-pipeline) FULL_PIPELINE=true; shift ;;
    --dry-run)     DRY_RUN=true; shift ;;
    -h|--help)     usage ;;
    *) echo "Unknown flag: $1"; usage ;;
  esac
done

# ── Validation ───────────────────────────────────────────────────

if [[ ! -f "$MANIFEST" ]]; then
  echo "ERROR: manifest.json not found at $MANIFEST"
  echo "Run fetch_pr_diffs.py first."
  exit 1
fi

if [[ ! -f "$PROMPT_FILE" ]]; then
  echo "ERROR: benchmark-prompt.md not found at $PROMPT_FILE"
  exit 1
fi

if ! command -v claude &>/dev/null; then
  echo "ERROR: claude CLI not found in PATH"
  exit 1
fi

if ! command -v jq &>/dev/null; then
  echo "ERROR: jq not found in PATH"
  exit 1
fi

# ── Setup ────────────────────────────────────────────────────────

mkdir -p "$REVIEWS_DIR" "$LOGS_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TOKEN_LOG="$LOGS_DIR/tokens_${MODEL}_${TIMESTAMP}.jsonl"

# ── Build entry list ─────────────────────────────────────────────

ENTRIES=$(jq -c '.[]' "$MANIFEST")

# Filter by repo
if [[ -n "$REPO_FILTER" ]]; then
  ENTRIES=$(echo "$ENTRIES" | jq -c "select(.source_repo == \"$REPO_FILTER\")")
fi

# Skip entries before --start-from
if [[ -n "$START_FROM" ]]; then
  FOUND=false
  FILTERED=""
  while IFS= read -r entry; do
    id=$(echo "$entry" | jq -r '.instance_id')
    if [[ "$id" == "$START_FROM" ]]; then
      FOUND=true
    fi
    if $FOUND; then
      FILTERED+="$entry"$'\n'
    fi
  done <<< "$ENTRIES"
  if ! $FOUND; then
    echo "ERROR: --start-from instance_id '$START_FROM' not found in manifest"
    exit 1
  fi
  ENTRIES="$FILTERED"
fi

# Note: --limit is applied inside the loop (caps reviews *executed*, not entries iterated)

# Count totals
TOTAL=$(echo "$ENTRIES" | grep -c '{' || true)
SKIPPED=0
COMPLETED=0
FAILED=0
ATTEMPTED=0
TOTAL_COST=0

echo "═══════════════════════════════════════════════════════════"
echo "  Martian Benchmark Review Runner"
echo "═══════════════════════════════════════════════════════════"
echo "  Model:      $MODEL"
echo "  Tool name:  $TOOL_NAME"
echo "  Entries:    $TOTAL"
if [[ "$LIMIT" -gt 0 ]]; then
  echo "  Limit:      $LIMIT reviews"
fi
echo "  Max budget: \$$MAX_BUDGET per review"
echo "  Delay:      ${DELAY}s between reviews"
echo "  Token log:  $TOKEN_LOG"
if $DRY_RUN; then
  echo "  Mode:       DRY RUN"
fi
echo "═══════════════════════════════════════════════════════════"
echo ""

# ── Main loop ────────────────────────────────────────────────────

INDEX=0

while IFS= read -r entry; do
  [[ -z "$entry" ]] && continue

  INDEX=$((INDEX + 1))
  INSTANCE_ID=$(echo "$entry" | jq -r '.instance_id')
  PR_TITLE=$(echo "$entry" | jq -r '.pr_title')
  PR_URL=$(echo "$entry" | jq -r '.pr_url')
  SOURCE_REPO=$(echo "$entry" | jq -r '.source_repo')
  DIFF_PATH="$DIFFS_DIR/${INSTANCE_ID}.diff"
  REVIEW_PATH="$REVIEWS_DIR/${INSTANCE_ID}.md"

  # Resume safety: skip existing reviews
  if [[ -f "$REVIEW_PATH" ]]; then
    SKIPPED=$((SKIPPED + 1))
    echo "[$INDEX/$TOTAL] $INSTANCE_ID  SKIP (exists)"
    continue
  fi

  # Check limit (caps reviews *attempted*, not entries iterated — skips don't count)
  if [[ "$LIMIT" -gt 0 && "$ATTEMPTED" -ge "$LIMIT" ]]; then
    echo "Limit reached ($LIMIT reviews). Stopping."
    break
  fi

  # Verify diff exists
  if [[ ! -f "$DIFF_PATH" ]]; then
    FAILED=$((FAILED + 1))
    echo "[$INDEX/$TOTAL] $INSTANCE_ID  FAIL (diff not found)"
    continue
  fi

  # Build the claude command
  # Note: --allowedTools is variadic and eats subsequent args.
  # Use -- to separate flags from the positional prompt argument.
  CLAUDE_CMD=(
    claude -p
    --model "$MODEL"
    --output-format json
    --permission-mode bypassPermissions
    --append-system-prompt-file "$PROMPT_FILE"
    --max-budget-usd "$MAX_BUDGET"
    --no-session-persistence
    --allowedTools "Skill Read Grep Glob Write Edit Bash Agent"
    --
  )

  USER_PROMPT="Review the PR diff at $DIFF_PATH.
Instance: $INSTANCE_ID | PR: $PR_TITLE ($PR_URL)
Write the review report to: $REVIEW_PATH

Use the fbk-code-review skill to perform this review."

  ATTEMPTED=$((ATTEMPTED + 1))

  if $DRY_RUN; then
    echo "[$INDEX/$TOTAL] $INSTANCE_ID  DRY RUN"
    echo "  cmd: ${CLAUDE_CMD[*]} \"<prompt>\""
    echo "  diff: $DIFF_PATH"
    echo "  out:  $REVIEW_PATH"
    echo ""
    continue
  fi

  # Execute with retry
  START_TIME=$(date +%s)
  touch "$LOGS_DIR/.review_start_$$"
  echo -n "[$INDEX/$TOTAL] $INSTANCE_ID  "

  RESPONSE=""
  SUCCESS=false

  for attempt in $(seq 1 "$MAX_RETRIES"); do
    RESPONSE=$("${CLAUDE_CMD[@]}" "$USER_PROMPT" </dev/null 2>"$LOGS_DIR/${INSTANCE_ID}.stderr") || true

    # Validate response is valid JSON with a result
    if echo "$RESPONSE" | jq -e '.result' &>/dev/null; then
      SUCCESS=true
      break
    fi

    echo -n "retry($attempt) "
    sleep $((DELAY * attempt))
  done

  END_TIME=$(date +%s)
  DURATION=$((END_TIME - START_TIME))

  if ! $SUCCESS; then
    FAILED=$((FAILED + 1))
    echo "FAIL (no valid response after $MAX_RETRIES attempts)  ${DURATION}s"
    # Log the failed response if we got one
    if [[ -n "$RESPONSE" ]]; then
      echo "$RESPONSE" | jq -c --arg id "$INSTANCE_ID" --arg repo "$SOURCE_REPO" \
        '. + {instance_id: $id, source_repo: $repo, benchmark_status: "failed"}' \
        >> "$TOKEN_LOG" 2>/dev/null || true
    fi
    continue
  fi

  # Locate the review file — skill may write to a different path than requested
  if [[ ! -f "$REVIEW_PATH" ]]; then
    # Find any new .md files the skill created in reviews/ during this run
    NEW_FILE=$(find "$REVIEWS_DIR" -name "*.md" -newer "$LOGS_DIR/.review_start_$$" 2>/dev/null \
      | grep -v "$(basename "$REVIEW_PATH")" | head -1)
    if [[ -n "$NEW_FILE" ]]; then
      mv "$NEW_FILE" "$REVIEW_PATH"
    else
      # No file found anywhere — extract from JSON result as last resort
      echo "$RESPONSE" | jq -r '.result' > "$REVIEW_PATH"
    fi
  fi

  # Also check project root for fbk-code-review-*.md files the skill may have created
  for stray in "$PROJECT_DIR"/fbk-code-review-*.md; do
    [[ -f "$stray" ]] && mv "$stray" "$REVIEW_PATH" && break
  done

  FINDINGS=$(grep -c '^### F-' "$REVIEW_PATH" 2>/dev/null) || FINDINGS=0

  # Extract cost from response
  COST=$(echo "$RESPONSE" | jq -r '.total_cost_usd // 0')
  TOTAL_COST=$(awk "BEGIN {printf \"%.6f\", $TOTAL_COST + $COST}")

  # Log token data to JSONL (augmented with metadata)
  echo "$RESPONSE" | jq -c --arg id "$INSTANCE_ID" --arg repo "$SOURCE_REPO" \
    --argjson findings "$FINDINGS" \
    '. + {instance_id: $id, source_repo: $repo, findings_count: $findings, benchmark_status: "ok"}' \
    >> "$TOKEN_LOG"

  COMPLETED=$((COMPLETED + 1))
  printf "OK  %2d findings  \$%.2f  %ds\n" "$FINDINGS" "$COST" "$DURATION"

  # Delay between reviews (skip after last)
  if [[ "$INDEX" -lt "$TOTAL" ]]; then
    sleep "$DELAY"
  fi

done <<< "$ENTRIES"

# ── Summary ──────────────────────────────────────────────────────

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  Run Complete"
echo "═══════════════════════════════════════════════════════════"
echo "  Model:     $MODEL"
echo "  Completed: $COMPLETED"
echo "  Skipped:   $SKIPPED (existing reviews)"
echo "  Failed:    $FAILED"

if [[ "$COMPLETED" -gt 0 ]]; then
  AVG_COST=$(awk "BEGIN {printf \"%.2f\", $TOTAL_COST / $COMPLETED}")
  printf "  Total cost: \$%.2f  (avg \$%s/review)\n" "$TOTAL_COST" "$AVG_COST"
fi

echo "  Token log: $TOKEN_LOG"
echo "═══════════════════════════════════════════════════════════"

# ── Post-run validation: detect inline execution ─────────────────

INVALID=()
for review_file in "$REVIEWS_DIR"/*.md; do
  if grep -qP '(performed inline|agent spawning unavailable|inline by the orchestrator)' "$review_file" 2>/dev/null; then
    INVALID+=("$(basename "$review_file" .md)")
  fi
done

if [[ ${#INVALID[@]} -gt 0 ]]; then
  echo ""
  echo "WARNING: ${#INVALID[@]} review(s) fell back to inline execution (invalid):"
  for inv in "${INVALID[@]}"; do
    echo "  $inv"
  done
  echo ""
  echo "These reviews ran without adversarial agents (Detector/Challenger)"
  echo "and should be deleted and re-run:"
  echo "  rm ${INVALID[*]/#/$REVIEWS_DIR/}"
  echo "  then re-run: ./run_reviews.sh"
fi

# ── Post-run pipeline ────────────────────────────────────────────

if $FULL_PIPELINE; then
  echo ""
  echo "Running post-review pipeline..."

  echo "  Step 3: inject_results.py --tool-name $TOOL_NAME --min-severity minor"
  python3 "$SCRIPT_DIR/inject_results.py" --tool-name "$TOOL_NAME" --min-severity minor

  echo "  Step 4: judge_anthropic.py --tool $TOOL_NAME"
  python3 "$SCRIPT_DIR/judge_anthropic.py" --tool "$TOOL_NAME"

  echo ""
  echo "Pipeline complete. Results in: $SCRIPT_DIR/results/"
fi
