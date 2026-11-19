#!/usr/bin/env bash
# Prepare the common starting codebase every arm begins from: the EXACT lab's Python stack skeleton plus the problem's
# reference solution at one checkpoint, at the project root (the hidden tests run `python <entry_file>.py` from there).
# Usage: prepare-start.sh <problem> <checkpoint> [out-dir]   (default out-dir: local/starts/<problem>-cp<checkpoint>)
# If local/start-tests/<problem>-cp<checkpoint>/ exists, its contents become the start's tests/.
# Result: a git repository with one commit, tagged `start`. Pass it to chain-scb.sh as START=<out-dir>.
set -euo pipefail
. "$(dirname "$0")/../settings.sh"; need SCB_PROBLEMS EXACT_LAB
LAB=$EXACT_LAB/experiments
PROB=$1; CP=$2; O="$(realpath -m "${3:-$LOCAL/starts/$PROB-cp$CP}")"
SOL=$SCB_PROBLEMS/$PROB/solutions/checkpoint_$CP
[ -d "$SOL" ] || { echo "No reference solution at $SOL" >&2; exit 2; }
[ -e "$O" ] && { echo "Refusing: $O exists" >&2; exit 1; }
mkdir -p "$O"; cd "$O"
cp -r "$LAB/stacks/python-pytest/." .; rm -f install.sh
cp -r "$SOL/." .
# Drop the benchmark canary from the top of each reference file (three `#` lines, or the same three lines as a docstring).
(cd "$SOL" && find . -type f) | python3 -c '
import re, sys
pat = re.compile(r"\A(\"\"\"\n)?(# )?BENCHMARK DATA [A-Z ]+\.\n(# )?SENTINEL PHRASE: .*\n(# )?slop-code-bench-canary GUID .*\n(\"\"\"\n)?\n*")
for f in sys.stdin.read().split("\n"):
    if not f: continue
    try: s = open(f, encoding="utf-8").read()
    except UnicodeDecodeError: continue
    t = pat.sub("", s)
    if t != s: open(f, "w", encoding="utf-8").write(t)
'
# The skeleton imports production code from src/; this program lives at the project root, so tests import from there too.
sed -i 's/^pythonpath = \["src"\]$/pythonpath = [".", "src"]/' pyproject.toml
grep -q '^pythonpath = \["\.", "src"\]$' pyproject.toml || { echo "pyproject.toml: pythonpath line not found" >&2; exit 3; }
[ -d "$LOCAL/start-tests/$PROB-cp$CP" ] && cp -r "$LOCAL/start-tests/$PROB-cp$CP/." tests/
printf '.venv/\n__pycache__/\n.pytest_cache/\n.tdd-events*\nprompt.md\n' > .gitignore
git init -q; git config user.email e2e@example.invalid; git config user.name e2e
git add -A; git commit -qm "Starting codebase"; git tag start
echo "$O $(git rev-parse --short HEAD)"
