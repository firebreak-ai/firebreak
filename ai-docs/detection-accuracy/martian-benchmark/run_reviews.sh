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
WORKTREES_DIR="$SCRIPT_DIR/worktrees"
CLONE_SCRIPT="$SCRIPT_DIR/clone_repos.py"

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
MODE="full-repo"   # full-repo (cwd = per-PR worktree) | diff-only (cwd = empty sandbox)
SANDBOX_DIR="/tmp/firebreak-benchmark-sandbox"   # cwd when mode=diff-only; empty dir isolates from project's ai-docs/

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
  --mode <mode>         full-repo (default): cwd = per-PR worktree with diff
                        applied. Loads benchmark-prompt-fullrepo.md.
                        diff-only: cwd = empty sandbox; reviewer sees only
                        the diff file. Loads benchmark-prompt-diff.md.
  --sandbox-dir <path>  Working dir when --mode diff-only
                        (default: /tmp/firebreak-benchmark-sandbox)
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
    --mode)        MODE="$2"; shift 2 ;;
    --sandbox-dir) SANDBOX_DIR="$2"; shift 2 ;;
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

case "$MODE" in
  full-repo) PROMPT_FILE="$SCRIPT_DIR/benchmark-prompt-fullrepo.md" ;;
  diff-only) PROMPT_FILE="$SCRIPT_DIR/benchmark-prompt-diff.md" ;;
  *) echo "ERROR: --mode must be 'full-repo' or 'diff-only' (got '$MODE')"; exit 1 ;;
esac

if [[ ! -f "$PROMPT_FILE" ]]; then
  echo "ERROR: prompt file not found at $PROMPT_FILE"
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

mkdir -p "$REVIEWS_DIR" "$LOGS_DIR" "$SANDBOX_DIR"

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
echo "  Mode:       $MODE"
if [[ "$MODE" == "diff-only" ]]; then
  echo "  Sandbox:    $SANDBOX_DIR"
else
  echo "  Worktrees:  $WORKTREES_DIR/<instance_id>"
fi
echo "  Prompt:     $(basename "$PROMPT_FILE")"
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
  OWNER=$(echo "$entry" | jq -r '.owner')
  REPO=$(echo "$entry" | jq -r '.repo')
  PR_NUMBER=$(echo "$entry" | jq -r '.pr_number')
  BASE_SHA=$(echo "$entry" | jq -r '.base_sha // ""')
  DIFF_PATH="$DIFFS_DIR/${INSTANCE_ID}.diff"
  REVIEW_PATH="$REVIEWS_DIR/${INSTANCE_ID}.md"
  WORKTREE_DIR="$WORKTREES_DIR/${INSTANCE_ID}"

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

  # Resolve working directory based on mode
  WORK_DIR="$SANDBOX_DIR"
  WORKTREE_STATUS=""
  if [[ "$MODE" == "full-repo" ]]; then
    if [[ ! -d "$WORKTREE_DIR" || ! -f "$WORKTREE_DIR/.fbk-benchmark-status" ]]; then
      # Worktree missing — invoke clone_repos.py to build it
      if ! python3 "$CLONE_SCRIPT" --instance "$INSTANCE_ID" >>"$LOGS_DIR/${INSTANCE_ID}.clone.log" 2>&1; then
        echo "[$INDEX/$TOTAL] $INSTANCE_ID  WARN worktree build failed — falling back to diff-only"
      fi
    fi
    if [[ -f "$WORKTREE_DIR/.fbk-benchmark-status" ]]; then
      WORKTREE_STATUS=$(cat "$WORKTREE_DIR/.fbk-benchmark-status")
    fi
    # apply:failed-fallback-head means diff didn't apply but head_sha is checked out
    # — the worktree IS usable for full-repo review. Only reject true failures
    # (bare "apply:failed" or "apply:failed:<reason>"), not the fallback-head case.
    if [[ -d "$WORKTREE_DIR" && "$WORKTREE_STATUS" != "apply:failed" && "$WORKTREE_STATUS" != apply:failed:* ]]; then
      WORK_DIR="$WORKTREE_DIR"
    else
      # Fallback: use sandbox, log it
      echo "[$INDEX/$TOTAL] $INSTANCE_ID  NOTE worktree unavailable ($WORKTREE_STATUS) — using sandbox"
    fi
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

  if [[ "$MODE" == "full-repo" && "$WORK_DIR" == "$WORKTREE_DIR" ]]; then
    USER_PROMPT="Benchmark code review — full-repo mode.

You are in a checkout of ${OWNER}/${REPO} at base ${BASE_SHA} with PR #${PR_NUMBER} applied to the working tree. The PR's changes are already in place — read files directly. The PR diff is available at $DIFF_PATH for quick reference to what changed.

Instance: $INSTANCE_ID | PR: $PR_TITLE ($PR_URL)
Output review report: $REVIEW_PATH

Browse the repo freely: trace callers of changed functions, inspect sibling modules, discover and run project-native linters (eslint, golangci-lint, pylint, rubocop, etc.), read existing tests. Treat this as a real PR review — ground findings in what the code actually does. Use the fbk-code-review skill with the benchmark-prompt-fullrepo overrides (in your system prompt): skip user checkpoint, skip post-implementation routing, take the standalone review path. Focus findings on the PR's changes; do not produce findings unrelated to the PR."
  else
    USER_PROMPT="Benchmark code review — diff-only mode.

Target diff: $DIFF_PATH
Instance: $INSTANCE_ID | PR: $PR_TITLE ($PR_URL)
Output review report: $REVIEW_PATH

Read the diff file with the Read tool. Do NOT search the working directory
for specs or documentation — this is an isolated diff with no project
context. Use the fbk-code-review skill but follow the benchmark-prompt
overrides (in your system prompt): skip Source of Truth Handling discovery,
skip post-implementation routing, take the standalone review path with the
AI failure mode checklist as source of truth."
  fi

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
    # Run claude from WORK_DIR. In full-repo mode this is the per-PR worktree
    # (checkout at base_sha with PR diff applied). In diff-only mode this is
    # the empty sandbox, which isolates the orchestrator from project ai-docs/
    # discovery that would mis-route the review.
    RESPONSE=$(cd "$WORK_DIR" && "${CLAUDE_CMD[@]}" "$USER_PROMPT" </dev/null 2>"$LOGS_DIR/${INSTANCE_ID}.stderr") || true

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

  # Also check worktree + sandbox + project root for fbk-code-review-*.md files the skill may have created
  for stray in "$WORK_DIR"/fbk-code-review-*.md "$SANDBOX_DIR"/fbk-code-review-*.md "$PROJECT_DIR"/fbk-code-review-*.md; do
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

  echo "  Step 3: inject_results.py --tool-name $TOOL_NAME --min-severity minor (via uv run fbk-pipeline.py)"
  uv run "$SCRIPT_DIR/inject_results.py" --tool-name "$TOOL_NAME" --min-severity minor

  echo "  Step 4: judge_anthropic.py --tool $TOOL_NAME"
  python3 "$SCRIPT_DIR/judge_anthropic.py" --tool "$TOOL_NAME"

  echo ""
  echo "Pipeline complete. Results in: $SCRIPT_DIR/results/"
fi
