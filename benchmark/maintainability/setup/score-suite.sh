#!/usr/bin/env bash
# Score a test suite's catching power: run it on the unchanged program and on each wrong copy (one patch each).
# Usage: score-suite.sh <project-with-tests-and-.venv> <patch-dir> [out.tsv]   (prints caught/total; a copy is caught when any test fails)
set -uo pipefail
W=$(realpath "$1"); PD=$(realpath "$2"); OUT=${3:-/dev/stdout}
run() { (cd "$1" && "$W/.venv/bin/python" -m pytest -q -p no:cacheprovider -x tests 2>&1 | tail -1); }
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
mk() { mkdir "$T/$1"; (cd "$W" && git ls-files -co --exclude-standard | grep -v '^tests/NOTES' | tar -cf - -T - | tar -xf - -C "$T/$1"); }
mk base; echo -e "unchanged\t$(run "$T/base")" > "$T/res.tsv"
caught=0; total=0
for p in "$PD"/*.patch; do n=$(basename "$p" .patch); mk "$n"
  (cd "$T/$n" && patch -p1 -s < "$p") || { echo -e "$n\tPATCH FAILED" >> "$T/res.tsv"; continue; }
  r=$(run "$T/$n"); total=$((total+1)); case "$r" in *failed*|*error*) caught=$((caught+1)); s=caught;; *) s=MISSED;; esac
  echo -e "$n\t$s\t$r" >> "$T/res.tsv"; done
cat "$T/res.tsv" > "$OUT"; echo "caught $caught/$total"
