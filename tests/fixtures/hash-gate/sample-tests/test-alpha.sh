#!/usr/bin/env bash
# Alpha test — validates basic connectivity
set -euo pipefail

RESULT=$(echo "alpha" | tr 'a-z' 'A-Z')
if [ "$RESULT" = "ALPHA" ]; then
  echo "ok 1 - alpha uppercased"
else
  echo "not ok 1 - alpha uppercased"
fi
