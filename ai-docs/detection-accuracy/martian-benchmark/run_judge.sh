#!/usr/bin/env bash
set -euo pipefail

# Martian Benchmark Judge Runner (Consensus Mode)
# Spawns 3 parallel Claude Code sub-agents per PR to judge Firebreak findings
# against golden comments. Each agent evaluates independently with the
# benchmark's judge prompt. Results are aggregated by majority vote.
#
# Usage:
#   ./run_judge.sh [flags]
#   ./run_judge.sh --limit 5 --dry-run
#   ./run_judge.sh --repo sentry

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BATCHES_FILE="$SCRIPT_DIR/results/judge_batches.jsonl"
OUTPUT_FILE="$SCRIPT_DIR/results/judge_consensus.jsonl"
LOGS_DIR="$SCRIPT_DIR/logs"

MODEL="opus"
JUDGES=3
LIMIT=0
REPO_FILTER=""
DELAY=5
MAX_BUDGET=2
DRY_RUN=false
FORCE=false

usage() {
  cat <<'EOF'
Usage: run_judge.sh [flags]

Flags:
  --model <alias>       Judge model (default: opus)
  --judges <N>          Number of parallel judges per PR (default: 3)
  --limit <N>           Stop after N PRs (default: 0 = all)
  --repo <name>         Filter to one source repo
  --delay <N>           Seconds between PR batches (default: 5)
  --max-budget <N>      Per-judge USD cap (default: 2)
  --force               Re-judge PRs that already have results
  --dry-run             Print commands without executing
  -h, --help            Show this help
EOF
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)       MODEL="$2"; shift 2 ;;
    --judges)      JUDGES="$2"; shift 2 ;;
    --limit)       LIMIT="$2"; shift 2 ;;
    --repo)        REPO_FILTER="$2"; shift 2 ;;
    --delay)       DELAY="$2"; shift 2 ;;
    --max-budget)  MAX_BUDGET="$2"; shift 2 ;;
    --force)       FORCE=true; shift ;;
    --dry-run)     DRY_RUN=true; shift ;;
    -h|--help)     usage ;;
    *) echo "Unknown flag: $1"; usage ;;
  esac
done

# ── Validation ───────────────────────────────────────────────

if [[ ! -f "$BATCHES_FILE" ]]; then
  echo "ERROR: judge_batches.jsonl not found at $BATCHES_FILE"
  echo "Run prepare_judge_batches.py first."
  exit 1
fi

if ! command -v claude &>/dev/null; then
  echo "ERROR: claude CLI not found in PATH"
  exit 1
fi

mkdir -p "$LOGS_DIR"

# ── Judge system prompt (benchmark-aligned) ──────────────────

JUDGE_SYSTEM_PROMPT='You are evaluating an AI code review tool against a benchmark.

For each golden comment (the expected issue), determine if ANY candidate finding
describes the SAME underlying issue.

Instructions:
- Determine if the candidate identifies the SAME underlying issue as the golden comment
- Accept semantic matches — different wording is fine if it is the same problem
- Focus on whether they point to the same bug, concern, or code issue
- A candidate that identifies the same code location AND same behavioral consequence
  is a match even if it frames the root cause differently
- Severity disagreements do not prevent matching — a golden "Low" can match a
  candidate "critical" if they describe the same bug
- One golden can match multiple candidates; one candidate can match multiple goldens

For each golden comment, respond with:
- The matching candidate index (1-based), or null if no match
- Brief reasoning for the decision

Output ONLY a valid JSON object in this exact format:
{
  "matches": {
    "1": {"candidate_index": <int or null>, "reasoning": "<brief explanation>"},
    "2": {"candidate_index": <int or null>, "reasoning": "<brief explanation>"}
  }
}

Keys in "matches" are golden comment indices (1-based). Do not include any text
outside the JSON object.'

# ── Count entries ────────────────────────────────────────────

if [[ -n "$REPO_FILTER" ]]; then
  ENTRIES=$(jq -c "select(.source_repo == \"$REPO_FILTER\")" "$BATCHES_FILE")
else
  ENTRIES=$(cat "$BATCHES_FILE")
fi

TOTAL=$(echo "$ENTRIES" | grep -c '{' || true)
COMPLETED=0
SKIPPED=0
FAILED=0
ATTEMPTED=0

echo "═══════════════════════════════════════════════════════════"
echo "  Martian Benchmark Judge Runner (Consensus Mode)"
echo "═══════════════════════════════════════════════════════════"
echo "  Model:      $MODEL"
echo "  Judges:     $JUDGES per PR (majority vote)"
echo "  Entries:    $TOTAL"
if [[ "$LIMIT" -gt 0 ]]; then
  echo "  Limit:      $LIMIT"
fi
echo "  Max budget: \$$MAX_BUDGET per judge"
echo "  Delay:      ${DELAY}s between PRs"
echo "  Output:     $OUTPUT_FILE"
if $DRY_RUN; then
  echo "  Mode:       DRY RUN"
fi
echo "═══════════════════════════════════════════════════════════"
echo ""

# ── Existing results for skip logic ─────────────────────────

declare -A DONE_IDS
if [[ -f "$OUTPUT_FILE" ]] && ! $FORCE; then
  while IFS= read -r line; do
    id=$(echo "$line" | jq -r '.instance_id // empty')
    [[ -n "$id" ]] && DONE_IDS["$id"]=1
  done < "$OUTPUT_FILE"
fi

# ── Helper: run one judge and extract JSON ───────────────────

run_single_judge() {
  local instance_id="$1"
  local judge_idx="$2"
  local user_prompt="$3"
  local outfile="$4"

  local response
  response=$(claude -p \
    --model "$MODEL" \
    --output-format json \
    --permission-mode bypassPermissions \
    --max-budget-usd "$MAX_BUDGET" \
    --no-session-persistence \
    --allowedTools "" \
    --system-prompt "$JUDGE_SYSTEM_PROMPT" \
    -- "$user_prompt" </dev/null 2>"$LOGS_DIR/judge_${instance_id}_j${judge_idx}.stderr") || true

  local result_text
  result_text=$(echo "$response" | jq -r '.result // empty')

  if [[ -z "$result_text" ]]; then
    echo '{"error": "no_result"}' > "$outfile"
    return
  fi

  # Extract JSON from result
  local judge_json
  judge_json=$(echo "$result_text" | sed -n '/^{/,/^}/p' | head -50)

  if ! echo "$judge_json" | jq -e '.matches' &>/dev/null 2>&1; then
    judge_json=$(echo "$result_text" | sed 's/^```json//;s/^```//' | sed -n '/^{/,/^}/p' | head -50)
  fi

  if echo "$judge_json" | jq -e '.matches' &>/dev/null 2>&1; then
    echo "$judge_json" > "$outfile"
  else
    echo '{"error": "parse_error"}' > "$outfile"
  fi
}

# ── Main loop ────────────────────────────────────────────────

while IFS= read -r batch; do
  [[ -z "$batch" ]] && continue

  INSTANCE_ID=$(echo "$batch" | jq -r '.instance_id')
  PR_TITLE=$(echo "$batch" | jq -r '.pr_title')
  GOLDEN_COUNT=$(echo "$batch" | jq -r '.golden_count')
  CANDIDATE_COUNT=$(echo "$batch" | jq -r '.candidate_count')

  # Skip if already judged
  if [[ -n "${DONE_IDS[$INSTANCE_ID]+x}" ]]; then
    SKIPPED=$((SKIPPED + 1))
    echo "[$((SKIPPED + COMPLETED + FAILED))/$TOTAL] $INSTANCE_ID  SKIP (exists)"
    continue
  fi

  # Check limit
  if [[ "$LIMIT" -gt 0 && "$ATTEMPTED" -ge "$LIMIT" ]]; then
    echo "Limit reached ($LIMIT). Stopping."
    break
  fi

  # Skip PRs with no candidates
  if [[ "$CANDIDATE_COUNT" -eq 0 ]]; then
    jq -n -c \
      --arg id "$INSTANCE_ID" \
      --argjson gc "$GOLDEN_COUNT" \
      '{instance_id: $id, golden_count: $gc, candidate_count: 0, status: "no_candidates", votes: [], consensus: {}}' \
      >> "$OUTPUT_FILE"
    COMPLETED=$((COMPLETED + 1))
    echo "[$((SKIPPED + COMPLETED + FAILED))/$TOTAL] $INSTANCE_ID  OK (no candidates)"
    continue
  fi

  ATTEMPTED=$((ATTEMPTED + 1))

  # Build user prompt
  GOLDEN_SECTION=$(echo "$batch" | jq -r '
    .golden_comments[] |
    "Golden \(.index) (\(.severity)):\n\(.comment)\n"
  ')

  CANDIDATE_SECTION=$(echo "$batch" | jq -r '
    .candidates[] |
    "Candidate \(.index) [\(.id)] (\(.type)/\(.severity)):\n\(.description)\n\(.detail)\n---\n"
  ')

  USER_PROMPT="Judge the following PR review results.

PR: $PR_TITLE
Instance: $INSTANCE_ID

=== GOLDEN COMMENTS ($GOLDEN_COUNT) ===

$GOLDEN_SECTION

=== CANDIDATE FINDINGS ($CANDIDATE_COUNT) ===

$CANDIDATE_SECTION

For each golden comment, find the best matching candidate (or null if no match).
Output ONLY the JSON object."

  if $DRY_RUN; then
    echo "[$((SKIPPED + COMPLETED + FAILED + 1))/$TOTAL] $INSTANCE_ID  DRY RUN  (${GOLDEN_COUNT}g × ${CANDIDATE_COUNT}c × ${JUDGES} judges)"
    continue
  fi

  echo -n "[$((SKIPPED + COMPLETED + FAILED + 1))/$TOTAL] $INSTANCE_ID  "

  START_TIME=$(date +%s)

  # Spawn N judges in parallel
  TMPDIR=$(mktemp -d)
  for j in $(seq 1 "$JUDGES"); do
    run_single_judge "$INSTANCE_ID" "$j" "$USER_PROMPT" "$TMPDIR/judge_${j}.json" &
  done
  wait

  END_TIME=$(date +%s)
  DURATION=$((END_TIME - START_TIME))

  # Collect votes
  VOTES="["
  ERRORS=0
  for j in $(seq 1 "$JUDGES"); do
    result_file="$TMPDIR/judge_${j}.json"
    if [[ -f "$result_file" ]] && jq -e '.matches' "$result_file" &>/dev/null 2>&1; then
      [[ "$VOTES" != "[" ]] && VOTES+=","
      VOTES+=$(cat "$result_file")
    else
      ERRORS=$((ERRORS + 1))
    fi
  done
  VOTES+="]"

  rm -rf "$TMPDIR"

  SUCCESSFUL_VOTES=$((JUDGES - ERRORS))

  if [[ "$SUCCESSFUL_VOTES" -eq 0 ]]; then
    FAILED=$((FAILED + 1))
    echo "FAIL (all $JUDGES judges failed)  ${DURATION}s"
    continue
  fi

  # Build consensus via majority vote (done in jq)
  # For each golden index, count how many judges matched vs null,
  # and which candidate_index got the most votes
  CONSENSUS=$(echo "$VOTES" | jq -c --argjson gc "$GOLDEN_COUNT" '
    . as $votes |
    [range(1; $gc + 1) | tostring] |
    map(. as $gi |
      {
        key: $gi,
        value: (
          [$votes[].matches[$gi].candidate_index] |
          # Count occurrences of each value
          group_by(.) |
          sort_by(-length) |
          .[0][0] as $winner |
          [$votes[].matches[$gi].candidate_index] as $all_votes |
          {
            candidate_index: $winner,
            vote_count: ([$all_votes[] | select(. == $winner)] | length),
            total_votes: ($all_votes | length),
            all_votes: $all_votes
          }
        )
      }
    ) | from_entries
  ')

  # Write full record with all votes and consensus
  jq -n -c \
    --arg id "$INSTANCE_ID" \
    --argjson gc "$GOLDEN_COUNT" \
    --argjson cc "$CANDIDATE_COUNT" \
    --argjson votes "$VOTES" \
    --argjson consensus "$CONSENSUS" \
    --argjson judges "$JUDGES" \
    --argjson errors "$ERRORS" \
    '{
      instance_id: $id,
      golden_count: $gc,
      candidate_count: $cc,
      judges: $judges,
      successful_votes: ($judges - $errors),
      errors: $errors,
      status: "ok",
      consensus: $consensus,
      votes: $votes
    }' >> "$OUTPUT_FILE"

  COMPLETED=$((COMPLETED + 1))

  # Count consensus matches
  MATCH_COUNT=$(echo "$CONSENSUS" | jq -r '[to_entries[] | select(.value.candidate_index != null)] | length' | head -1)
  UNANIMOUS=$(echo "$CONSENSUS" | jq -r '[to_entries[] | select(.value.vote_count == .value.total_votes)] | length' | head -1)

  echo "OK  ${MATCH_COUNT:-?}/${GOLDEN_COUNT} matched  (${UNANIMOUS:-?} unanimous)  ${DURATION}s"

  # Delay between PRs
  if [[ "$DELAY" -gt 0 ]]; then
    sleep "$DELAY"
  fi

done <<< "$ENTRIES"

# ── Summary ──────────────────────────────────────────────────

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  Judge Run Complete (Consensus Mode)"
echo "═══════════════════════════════════════════════════════════"
echo "  Model:     $MODEL"
echo "  Judges:    $JUDGES per PR"
echo "  Completed: $COMPLETED"
echo "  Skipped:   $SKIPPED (existing results)"
echo "  Failed:    $FAILED"
echo "  Output:    $OUTPUT_FILE"
echo "═══════════════════════════════════════════════════════════"
