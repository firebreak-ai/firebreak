#!/usr/bin/env bash
# Beta test — validates arithmetic operations
set -euo pipefail

SUM=$((3 + 7))
EXPECTED=10

if [ "$SUM" -eq "$EXPECTED" ]; then
  echo "ok 1 - addition correct"
  exit 0
fi
echo "not ok 1 - expected $EXPECTED got $SUM"
exit 1
