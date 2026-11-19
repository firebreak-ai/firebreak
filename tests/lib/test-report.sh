#!/usr/bin/env bash
# Shared reporting and scratch ownership. Keep assertions in the calling suite.

fbk_test_init() {
  FBK_TEST_SUITE="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
  FBK_TEST_CWD="$PWD"
  local parent="${FBK_REPORT_DIR:-${TMPDIR:-/tmp}}"
  mkdir -p "$parent" || return 2
  parent="$(cd "$parent" && pwd)" || return 2
  FBK_TEST_TMP="$(mktemp -d "$parent/$(basename "$1" .sh).XXXXXX")" || return 2
  mkdir -p "$FBK_TEST_TMP/commands" "$FBK_TEST_TMP/tmp" || return 2
  export FBK_TEST_TMP
  export TMPDIR="$FBK_TEST_TMP/tmp"
  trap 'fbk_test_finish "$?"' EXIT
}

fbk_run() {
  local label="$1"
  shift
  local entry rc
  entry="$(mktemp -d "$FBK_TEST_TMP/commands/command.XXXXXX")" || return 2
  printf '%s\n' "$label" > "$entry/label"
  { printf 'cd %q && ' "$PWD"; printf '%q ' "$@"; printf '\n'; } > "$entry/command.txt"
  if "$@" > "$entry/stdout.txt" 2> "$entry/stderr.txt"; then
    rc=0
  else
    rc=$?
  fi
  printf '%s\n' "$rc" > "$entry/exit-code.txt"
  cat "$entry/stdout.txt"
  cat "$entry/stderr.txt" >&2
  return "$rc"
}

fbk_diag() {
  printf 'failure: %s\n' "$1" | sed 's/^/# /'
  if [ "$#" -ge 2 ]; then printf 'expected: %s\n' "$2" | sed 's/^/# /'; fi
  if [ "$#" -ge 3 ]; then printf 'actual: %s\n' "$3" | sed 's/^/# /'; fi
  printf '# artifacts: %s\n' "$FBK_TEST_TMP"
  printf '# rerun: cd %q && bash %q\n' "$FBK_TEST_CWD" "$FBK_TEST_SUITE"
  local entry
  for entry in "$FBK_TEST_TMP"/commands/command.*; do
    [ -d "$entry" ] || continue
    printf '# command evidence: %s\n' "$entry"
    sed 's/^/# /' "$entry/label" "$entry/command.txt" "$entry/exit-code.txt"
    # Keep terminal output bounded; full streams remain available as artifacts.
    tail -n 12 "$entry/stderr.txt" | sed 's/^/# stderr: /'
    tail -n 12 "$entry/stdout.txt" | sed 's/^/# stdout: /'
  done
}

fbk_test_finish() {
  local rc="$1"
  trap - EXIT
  if [ "${FAIL:-0}" -gt 0 ] && [ "$rc" -eq 0 ]; then rc=1; fi
  if [ "$rc" -ne 0 ]; then
    if [ "${FAIL:-0}" -eq 0 ]; then
      printf '# execution error: suite exited %s without a recorded assertion failure\n' "$rc" >&2
    fi
    printf '# artifacts retained: %s\n' "$FBK_TEST_TMP" >&2
    printf '# rerun: cd %q && bash %q\n' "$FBK_TEST_CWD" "$FBK_TEST_SUITE" >&2
  else
    rm -rf "$FBK_TEST_TMP"
  fi
  exit "$rc"
}
