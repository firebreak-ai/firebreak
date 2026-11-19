#!/usr/bin/env bash
# Check that a Firebreak version still has what the benchmark's prompts and driver name:
#   check-fbk-interface.sh [commit | absolute path of an assets folder]     (default: the working tree's assets/)
# It reads files only and costs nothing. It checks: every skill a prompt file names exists; the guide the council
# prompts point to exists; the phase names the driver sends are the workflow's phase names; the installer still
# takes --target and --source. It cannot check what only a real session shows (how a closed phase is recorded in
# .fbk/<unit>/state.json, what the skills ask the operator), so after it passes, run one checkpoint for real:
#   CPS="6 6" FBK_ASSETS=<commit> build/fbk-drive.sh start <run>   and the five turns, as the README describes.
set -uo pipefail
. "$(dirname "$0")/../settings.sh"
V=${1:-}; T=
case $V in
  "") A="$REPO/assets" ;;
  /*) A=$V ;;
  *)  T=$(mktemp -d) && git -C "$REPO" archive "$V" assets | tar -x -C "$T" && A="$T/assets" || { echo "cannot export assets of $V" >&2; exit 2; } ;;
esac
trap '[ -n "$T" ] && rm -rf "$T"' EXIT
[ -d "$A/skills" ] || { echo "no skills folder in $A" >&2; exit 2; }
bad=0; miss() { echo "MISSING: $*"; bad=1; }

for f in "$K"/prompts/fbk*/[1-5]-*.txt; do
  for s in $(grep -o 'fbk-[a-z-]* skill' "$f" | cut -d' ' -f1 | sort -u); do
    [ -f "$A/skills/$s/SKILL.md" ] || miss "skill $s, named in ${f#"$K"/}"
  done
done
if grep -qi 'review selection guide' "$K"/prompts/fbk*/*.txt; then
  [ -n "$(find "$A" -iname '*review-selection*' -print -quit)" ] || miss "a review selection guide, named in the council prompts"
fi
for p in intent design spec breakdown implement; do
  [ -f "$A/skills/fbk-$p/SKILL.md" ] || miss "phase skill fbk-$p (the driver's turn names and the stand-in session assume these five phases)"
done
for o in --target --source; do
  grep -q -- "$o)" "$REPO/installer/install.sh" || miss "installer option $o (used by build/fbk-drive.sh)"
done
[ $bad = 0 ] && echo "ok: the prompts and driver match $A" || { echo "update the prompts or the driver (README, \"When Firebreak changes\") before building"; exit 1; }
