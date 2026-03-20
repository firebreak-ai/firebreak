#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
LOGGER="$PROJECT_ROOT/home/dot-claude/hooks/sdl-workflow/audit-logger.py"

TMPDIR_BASE="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_BASE"' EXIT

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

# --- Test 1: single log event produces valid JSON with correct fields ---
test_dir="$TMPDIR_BASE/t1"
mkdir -p "$test_dir"
LOG_DIR="$test_dir" python3 "$LOGGER" log myspec start '{"key":"val"}'
line=$(cat "$test_dir/myspec.log" 2>/dev/null)
if echo "$line" | python3 -c "
import sys, json
d = json.loads(sys.stdin.read().strip())
assert 'timestamp' in d
assert d['spec'] == 'myspec'
assert d['event_type'] == 'start'
assert d['data'] == {'key': 'val'}
" 2>/dev/null; then
  ok "single log event produces valid JSON with correct fields"
else
  not_ok "single log event produces valid JSON with correct fields" "got: $line"
fi

# --- Test 2: multiple sequential log calls produce independent JSON lines ---
test_dir="$TMPDIR_BASE/t2"
mkdir -p "$test_dir"
LOG_DIR="$test_dir" python3 "$LOGGER" log multi ev1 '{"n":1}'
LOG_DIR="$test_dir" python3 "$LOGGER" log multi ev2 '{"n":2}'
LOG_DIR="$test_dir" python3 "$LOGGER" log multi ev3 '{"n":3}'
count=$(wc -l < "$test_dir/multi.log")
valid=true
while IFS= read -r l; do
  echo "$l" | python3 -c "import sys,json; json.loads(sys.stdin.read().strip())" 2>/dev/null || valid=false
done < "$test_dir/multi.log"
if [ "$count" -eq 3 ] && $valid; then
  ok "multiple sequential log calls produce independent JSON lines"
else
  not_ok "multiple sequential log calls produce independent JSON lines" "count=$count valid=$valid"
fi

# --- Test 3: existing entries preserved when appending ---
test_dir="$TMPDIR_BASE/t3"
mkdir -p "$test_dir"
echo '{"timestamp":"pre","spec":"preserve","event_type":"seed","data":{}}' > "$test_dir/preserve.log"
LOG_DIR="$test_dir" python3 "$LOGGER" log preserve append '{"x":1}'
line1=$(sed -n '1p' "$test_dir/preserve.log")
line2=$(sed -n '2p' "$test_dir/preserve.log")
total=$(wc -l < "$test_dir/preserve.log")
if [ "$total" -eq 2 ] && echo "$line1" | python3 -c "import sys,json; assert json.loads(sys.stdin.read().strip())['event_type']=='seed'" 2>/dev/null && \
   echo "$line2" | python3 -c "import sys,json; assert json.loads(sys.stdin.read().strip())['event_type']=='append'" 2>/dev/null; then
  ok "existing entries preserved when appending"
else
  not_ok "existing entries preserved when appending" "total=$total"
fi

# --- Test 4: log file created if it doesn't exist ---
test_dir="$TMPDIR_BASE/t4"
mkdir -p "$test_dir"
[ ! -f "$test_dir/newfile.log" ] || { not_ok "log file created if it doesn't exist" "file pre-existed"; false; }
LOG_DIR="$test_dir" python3 "$LOGGER" log newfile init '{}'
if [ -f "$test_dir/newfile.log" ]; then
  ok "log file created if it doesn't exist"
else
  not_ok "log file created if it doesn't exist"
fi

# --- Test 5: log directory created if it doesn't exist ---
test_dir="$TMPDIR_BASE/t5/nested/deep"
[ ! -d "$test_dir" ] || { not_ok "log directory created if it doesn't exist" "dir pre-existed"; false; }
LOG_DIR="$test_dir" python3 "$LOGGER" log dirtest init '{}'
if [ -f "$test_dir/dirtest.log" ]; then
  ok "log directory created if it doesn't exist"
else
  not_ok "log directory created if it doesn't exist"
fi

# --- Test 6: read returns all events as parseable JSON lines ---
test_dir="$TMPDIR_BASE/t6"
mkdir -p "$test_dir"
LOG_DIR="$test_dir" python3 "$LOGGER" log readtest a '{"v":1}'
LOG_DIR="$test_dir" python3 "$LOGGER" log readtest b '{"v":2}'
output=$(LOG_DIR="$test_dir" python3 "$LOGGER" read readtest)
read_count=$(echo "$output" | wc -l)
read_valid=true
echo "$output" | while IFS= read -r l; do
  echo "$l" | python3 -c "import sys,json; json.loads(sys.stdin.read().strip())" 2>/dev/null || { read_valid=false; break; }
done
if [ "$read_count" -eq 2 ]; then
  ok "read returns all events as parseable JSON lines"
else
  not_ok "read returns all events as parseable JSON lines" "count=$read_count"
fi

# --- Test 7: read for non-existent spec ---
test_dir="$TMPDIR_BASE/t7"
mkdir -p "$test_dir"
output=$(LOG_DIR="$test_dir" python3 "$LOGGER" read nosuchspec 2>/dev/null)
rc=$?
if [ $rc -ne 0 ] || [ -z "$output" ]; then
  ok "read for non-existent spec returns error or empty"
else
  not_ok "read for non-existent spec returns error or empty" "rc=$rc output=$output"
fi

# --- Test 8: nested JSON in data field preserved ---
test_dir="$TMPDIR_BASE/t8"
mkdir -p "$test_dir"
LOG_DIR="$test_dir" python3 "$LOGGER" log nested ev '{"outer":{"inner":[1,2,{"deep":true}]}}'
line=$(cat "$test_dir/nested.log")
if echo "$line" | python3 -c "
import sys, json
d = json.loads(sys.stdin.read().strip())
assert d['data']['outer']['inner'][2]['deep'] is True
" 2>/dev/null; then
  ok "nested JSON in data field preserved correctly"
else
  not_ok "nested JSON in data field preserved correctly" "got: $line"
fi

# --- Summary ---
echo ""
echo "1..$TOTAL"
echo "# pass $PASS / $TOTAL"
if [ "$FAIL" -gt 0 ]; then
  echo "# FAIL $FAIL"
  exit 1
fi
exit 0
