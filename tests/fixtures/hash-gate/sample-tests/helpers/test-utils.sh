#!/usr/bin/env bash
# Shared test utilities
set -euo pipefail

assert_eq() {
  local actual="$1" expected="$2" label="${3:-assertion}"
  if [ "$actual" = "$expected" ]; then
    echo "ok - $label"
  else
    echo "not ok - $label (expected '$expected', got '$actual')"
    return 1
  fi
}
