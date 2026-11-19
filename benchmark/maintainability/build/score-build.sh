#!/usr/bin/env bash
# Score one finished build, serially, with the lock off: score-build.sh <run-dir>
# For each checkpoint tag of <run-dir>/project (the start's tag included when the run began from a common start) the tag
# is cloned to a scratch folder, so the project itself is left as it is, and:
#   hidden-tests.sh on the clone        -> hidden-cpN.json (hidden-start.json for the start's tag)
#   quality.py                          -> quality.json, quality.txt
#   measure/state.py, every tag, the start as reference -> state.json, state.txt
#   the same with --mutants on the first and the last tag only, each with a fresh .venv from its own requirements
#                                       -> state-mutants.json, state-mutants.txt   (MUTANTS=<n>, default 150; 0 leaves it out)
#   audit-build.py on the session records -> audit.json, audit.txt
# and all of it together in score.txt (to read) and score.json. The problem is read from arm.txt.
# Refuses while lock.sh's lock is on: the hidden tests and the finished runs cannot be read then.
set -uo pipefail
[ $# -eq 1 ] || { echo "usage: score-build.sh <run-dir>" >&2; exit 2; }
. "$(dirname "$0")/../settings.sh"; need SCB_PROBLEMS; R=$(realpath "$1"); W="$R/project"; MUTANTS=${MUTANTS:-150}
[ -e "$LOCAL/.locked" ] && { echo "refusing: the answers are locked; run $K/change/lock.sh unlock first" >&2; exit 2; }
[ -d "$W/.git" ] || { echo "no project in $R" >&2; exit 2; }
PROB=$(sed -n 's/.* claude-opus-5-5 \([^ ]*\).*/\1/p' "$R/arm.txt"); [ -n "$PROB" ] || { echo "no problem named in $R/arm.txt" >&2; exit 2; }
S=; [ -f "$R/start-first-cp.txt" ] && S=cp$(( $(cat "$R/start-first-cp.txt") - 1 ))
TAGS=$(git -C "$W" tag | grep -x 'cp[0-9]*' | grep -vx cp0 | sort -V); [ -n "$TAGS" ] || { echo "no checkpoint tags in $W" >&2; exit 2; }
FIRST=$(head -1 <<< "$TAGS"); LAST=$(tail -1 <<< "$TAGS")
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
venv() {  # a fresh environment for one clone, from the requirements it holds
  (cd "$1" && uv venv -q .venv && { [ -f requirements-dev.txt ] && uv pip install -q --python .venv/bin/python -r requirements-dev.txt
     grep -qv '^[[:space:]]*\(#.*\)\?$' requirements.txt 2>/dev/null && uv pip install -q --python .venv/bin/python -r requirements.txt
     .venv/bin/python -c 'import pytest' 2>/dev/null || uv pip install -q --python .venv/bin/python pytest; }) >> "$R/score-venv.log" 2>&1
}
: > "$T/hidden.txt"; : > "$R/score-venv.log"
for t in $TAGS; do
  git -c advice.detachedHead=false clone -q --branch "$t" "$W" "$T/$t" || exit 2
  out=hidden-$t.json; [ "$t" = "$S" ] && out=hidden-start.json
  rm -f "$R/$out"; echo "$t $("$K/build/hidden-tests.sh" "$T/$t" "${t#cp}" "$PROB" "$R/$out" 2>&1 | tail -1)" | tee -a "$T/hidden.txt"
done
python3 "$K/build/quality.py" "$R" > "$R/quality.txt" 2>&1
(cd "$T" && uv run -q --script "$K/measure/state.py" ${S:+--ref $S} --json "$R/state.json" $TAGS) > "$R/state.txt" 2>&1
rm -f "$R/state-mutants.json" "$R/state-mutants.txt"
if [ "$MUTANTS" != 0 ]; then
  for t in $(printf '%s\n' "$FIRST" "$LAST" | uniq); do venv "$T/$t"; done
  (cd "$T" && uv run -q --script "$K/measure/state.py" ${S:+--ref $S} --mutants "$MUTANTS" --json "$R/state-mutants.json" $(printf '%s\n' "$FIRST" "$LAST" | uniq)) > "$R/state-mutants.txt" 2>&1
fi
python3 "$K/build/audit-build.py" "$R" > "$R/audit.txt" 2>&1
{ echo "$(basename "$R"): $(cat "$R/arm.txt")"; echo "scored $(date -u +%FT%TZ); start tag ${S:-none}; commits $(for t in $TAGS; do echo "$t=$(git -C "$W" rev-parse --short "$t")"; done | tr '\n' ' ')"
  printf '\nHidden tests, passed/total by group (regression = earlier checkpoints\x27 cases)\n'; cat "$T/hidden.txt"
  printf '\nPer checkpoint (quality.py)\n'; cat "$R/quality.txt"
  printf '\nCode state at each tag (state.py)\n'; grep -v '^wrote ' "$R/state.txt"
  [ -f "$R/state-mutants.txt" ] && { printf '\nTest quality at the first and last tag (state.py --mutants %s)\n' "$MUTANTS"; grep -v '^wrote ' "$R/state-mutants.txt"; }
  printf '\nAudit: paths outside the work folder that the sessions named (audit-build.py)\n'; cat "$R/audit.txt"; } > "$R/score.txt"
python3 - "$R" "$T/hidden.txt" "${S:-}" <<'PY'
import json, pathlib, sys
R, start = pathlib.Path(sys.argv[1]), sys.argv[3]
load = lambda f: json.loads((R / f).read_text()) if (R / f).exists() else None
hidden = {}
for line in open(sys.argv[2]):
    tag, *groups = line.split()
    hidden[tag] = {g.split("=")[0]: [int(x) for x in g.split("=")[1].split("/")] for g in groups if "=" in g and g.split("=")[1].replace("/", "").isdigit()}
(R / "score.json").write_text(json.dumps({"run": R.name, "arm": (R / "arm.txt").read_text().strip(), "start_tag": start or None, "hidden": hidden,
    "quality": load("quality.json"), "state": load("state.json"), "state_mutants": load("state-mutants.json"), "audit": load("audit.json")}, indent=1))
PY
cat "$R/score.txt"
