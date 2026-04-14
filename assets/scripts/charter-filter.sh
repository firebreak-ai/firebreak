#!/usr/bin/env bash
set -euo pipefail

# Usage: charter-filter.sh <finding_type> <preset>
#   finding_type: behavioral | structural | test-integrity | fragile
#   preset:       behavioral-only | structural | test-only | full
#
# Output: pass | fail

TYPE="${1:?Usage: charter-filter.sh <finding_type> <preset>}"
PRESET="${2:?Usage: charter-filter.sh <finding_type> <preset>}"

case "$PRESET" in
  behavioral-only) [[ "$TYPE" == "behavioral" ]] && echo pass || echo fail ;;
  structural)      [[ "$TYPE" == "structural" || "$TYPE" == "fragile" ]] && echo pass || echo fail ;;
  test-only)       [[ "$TYPE" == "test-integrity" ]] && echo pass || echo fail ;;
  full)            echo pass ;;
  *)               echo fail ;;
esac
