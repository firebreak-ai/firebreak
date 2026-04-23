#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BENCHMARK_DIR="$PROJECT_ROOT/ai-docs/detection-accuracy/martian-benchmark"

ok() {
  TOTAL=$((TOTAL + 1))
  PASS=$((PASS + 1))
  echo "ok $TOTAL - $1"
}

not_ok() {
  TOTAL=$((TOTAL + 1))
  FAIL=$((FAIL + 1))
  echo "not ok $TOTAL - $1"
  [ -n "${2:-}" ] && echo "# $2"
}

echo "TAP version 13"

# --- Test 1: Benchmark directory exists ---
if [ -d "$BENCHMARK_DIR" ]; then
  ok "Benchmark directory exists"
else
  not_ok "Benchmark directory exists" "dir: $BENCHMARK_DIR"
fi

# --- Test 2: run_reviews.sh exists and is executable ---
if [ -x "$BENCHMARK_DIR/run_reviews.sh" ]; then
  ok "run_reviews.sh exists and is executable"
else
  not_ok "run_reviews.sh exists and is executable" "file: $BENCHMARK_DIR/run_reviews.sh"
fi

# --- Test 3: inject_results.py exists and is non-empty ---
if [ -s "$BENCHMARK_DIR/inject_results.py" ]; then
  ok "inject_results.py exists and is non-empty"
else
  not_ok "inject_results.py exists and is non-empty" "file: $BENCHMARK_DIR/inject_results.py"
fi

# --- Test 4: judge_anthropic.py exists and is non-empty ---
if [ -s "$BENCHMARK_DIR/judge_anthropic.py" ]; then
  ok "judge_anthropic.py exists and is non-empty"
else
  not_ok "judge_anthropic.py exists and is non-empty" "file: $BENCHMARK_DIR/judge_anthropic.py"
fi

# --- Test 5: manifest.json exists and is valid JSON ---
if [ -s "$BENCHMARK_DIR/manifest.json" ] && python3 -c "import json,sys; json.load(sys.stdin)" < "$BENCHMARK_DIR/manifest.json" 2>/dev/null; then
  ok "manifest.json exists and is valid JSON"
else
  not_ok "manifest.json exists and is valid JSON" "file: $BENCHMARK_DIR/manifest.json"
fi

# --- Test 6: manifest.json contains 50 PR entries ---
if python3 -c "import json,sys; d=json.load(sys.stdin); assert len(d)==50, f'expected 50, got {len(d)}'" < "$BENCHMARK_DIR/manifest.json" 2>/dev/null; then
  ok "manifest.json contains 50 PR entries"
else
  count=$(python3 -c "import json,sys; print(len(json.load(sys.stdin)))" < "$BENCHMARK_DIR/manifest.json" 2>/dev/null || echo "error")
  not_ok "manifest.json contains 50 PR entries" "count=$count"
fi

# --- Test 7: diffs directory exists and contains diff files ---
if [ -d "$BENCHMARK_DIR/diffs" ] && [ "$(ls "$BENCHMARK_DIR/diffs/" 2>/dev/null | wc -l)" -gt 0 ]; then
  ok "diffs directory exists and contains diff files"
else
  diff_count=$(ls "$BENCHMARK_DIR/diffs/" 2>/dev/null | wc -l || echo "0")
  not_ok "diffs directory exists and contains diff files" "diffs_count=$diff_count dir: $BENCHMARK_DIR/diffs"
fi

# --- Test 8: benchmark prompt files (full-repo + diff-only) exist and are non-empty ---
if [ -s "$BENCHMARK_DIR/benchmark-prompt-fullrepo.md" ] && [ -s "$BENCHMARK_DIR/benchmark-prompt-diff.md" ]; then
  ok "benchmark-prompt-fullrepo.md and benchmark-prompt-diff.md exist and are non-empty"
else
  not_ok "benchmark-prompt-fullrepo.md and benchmark-prompt-diff.md exist and are non-empty" "files: $BENCHMARK_DIR/benchmark-prompt-{fullrepo,diff}.md"
fi

# --- Test 9: results directory exists or can be created ---
[ -d "$BENCHMARK_DIR/results" ] || mkdir -p "$BENCHMARK_DIR/results"
if [ -d "$BENCHMARK_DIR/results" ]; then
  ok "results directory exists or was created"
else
  not_ok "results directory exists or was created" "dir: $BENCHMARK_DIR/results"
fi

# --- Test 10: inject_results.py does not contain old regex-based markdown parsing ---
if ! grep -qE 're\.compile.*severity|re\.compile.*location|_is_metadata_line|parse_findings_flat' "$BENCHMARK_DIR/inject_results.py" 2>/dev/null; then
  ok "inject_results.py does not contain old regex-based markdown parsing"
else
  not_ok "inject_results.py does not contain old regex-based markdown parsing" "old regex patterns found in inject_results.py"
fi

# --- Test 11: inject_results.py references JSON consumption ---
if grep -qi 'json' "$BENCHMARK_DIR/inject_results.py" 2>/dev/null; then
  ok "inject_results.py references JSON consumption"
else
  not_ok "inject_results.py references JSON consumption" "file: $BENCHMARK_DIR/inject_results.py"
fi

# --- Test 12: run_reviews.sh references fbk-pipeline.py or uv run ---
if grep -qE 'pipeline\.py|uv run' "$BENCHMARK_DIR/run_reviews.sh" 2>/dev/null; then
  ok "run_reviews.sh references fbk-pipeline.py or uv run"
else
  not_ok "run_reviews.sh references fbk-pipeline.py or uv run" "file: $BENCHMARK_DIR/run_reviews.sh"
fi

# --- Summary ---
echo ""
echo "1..$TOTAL"
echo "# $PASS/$TOTAL tests passed"
if [ "$FAIL" -gt 0 ]; then
  echo "# FAIL $FAIL"
  exit 1
fi
exit 0
