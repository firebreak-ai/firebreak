#!/usr/bin/env bash
# Hide the answers while maintainer sessions run: lock.sh lock | unlock | add <path>... | status
# lock    records the mode of every answer location listed below in local/.locked ("<octal mode> <path>" a line,
#         written before the mode is touched) and then removes all its permissions (chmod 000). Refuses when the
#         record exists.
# unlock  puts every recorded mode back, last locked first, and removes the record; does nothing without a record.
# add     locks more paths under the same record while the lock is on (run.sh and chain-scb.sh add each run as it
#         finishes); does nothing when the lock is off.
# status  says locked or unlocked and how many paths the record holds.
# A locked folder cannot be listed, entered or read by this user's programs until unlock; sessions run as the same
# user, so this stops browsing and searching, not a program that calls chmod itself. Symbolic links are left alone.
# What stays readable: each change's request.md (prompts/), the base repos (local/anchors/<problem>/<base>), each
# problem's config.yaml, the common starts (local/starts/), the Firebreak assets (local/assets-*), the settings and
# the kit's scripts. score.sh and score-build.sh refuse to run while
# the record exists.
set -uo pipefail
. "$(dirname "$0")/../settings.sh"; need SCB_PROBLEMS; S=$LOCAL/.locked; P=$SCB_PROBLEMS

hide() {
  for p in "$@"; do
    [ -e "$p" ] && [ ! -L "$p" ] || continue
    m=$(stat -c %a "$p"); [ "$m" = 0 ] && continue  # already without permissions: nothing to record or put back
    printf '%s %s\n' "$m" "$p" >> "$S" && chmod 000 "$p"
  done
}

answers() {
  ls -d "$LOCAL"/changes-*/* 2>/dev/null  # each change's hidden tests, reference and notes (its request.md is in prompts/)
  find "$LOCAL"/runs-* -mindepth 1 -maxdepth 1 2>/dev/null  # finished runs, their logs and tables
  ls -d "$LOCAL"/anchors/*/tools-* "$LOCAL"/wrong-copies "$LOCAL"/start-tests 2>/dev/null
  for p in ${EXTRA_ANSWER_PATHS:-}; do echo "$p"; done  # more answer locations on this machine (settings.env)
  find "$P" -mindepth 2 -maxdepth 2 ! -name config.yaml ! -path "$P/.git/*" ! -path "$P/.pi/*" ! -path "$P/scripts/*"  # specs, tests, solutions
  echo "$P/.git"  # the same files, in the problem set's history
}

case ${1:-} in
  lock)   [ -e "$S" ] && { echo "refusing: already locked ($S exists)" >&2; exit 1; }
          : > "$S"; answers | { mapfile -t paths; hide "${paths[@]}"; }; echo "locked $(wc -l < "$S") paths" ;;
  add)    shift; [ -e "$S" ] && hide "$@"; exit 0 ;;
  unlock) [ -e "$S" ] || { echo "not locked"; exit 0; }
          bad=0; while read -r m p; do chmod "$m" "$p" || bad=1; done < <(tac "$S")
          [ $bad = 0 ] || { echo "some modes were not put back; record kept: $S" >&2; exit 1; }
          echo "unlocked $(wc -l < "$S") paths"; rm -f "$S" ;;
  status) if [ -e "$S" ]; then echo "locked: $(wc -l < "$S") paths"; else echo unlocked; fi ;;
  *)      echo "usage: lock.sh lock | unlock | add <path>... | status" >&2; exit 2 ;;
esac
