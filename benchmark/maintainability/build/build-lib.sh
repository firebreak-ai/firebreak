# Shared by chain-scb.sh and fbk-drive.sh (sourced): the pieces of a build that are the same whoever drives it.
# The caller sets K, LAB, ARM, PROB, START, FIRST, W (work folder), L (the run's files) and defines install_arm, wf_label, log.
CLEAN_ENV=(env -u CLAUDE_CODE_CHILD_SESSION -u CLAUDE_CODE_SESSION_ID -u CLAUDECODE -u CLAUDE_CODE_BRIDGE_SESSION_ID
  -u CLAUDE_CODE_MESSAGING_SOCKET -u CLAUDE_CODE_MESSAGING_TOKEN -u CLAUDE_CODE_SESSION_ATTENDED)
name() { od -An -N8 -tx1 /dev/urandom | tr -d ' \n'; }
SP=; await() { SP=$!; wait "$SP"; local rc=$?; SP=; return $rc; }  # the session runs in the background, so an interrupt reaches the script at once
result() { jq -cR 'fromjson? | select(.type == "result")' "$1.jsonl" 2>/dev/null | tail -1 > "$1.json"; }
clone_start() {  # a new workspace in $W from the common start, the arm's workflow installed, tagged cp<FIRST-1>; leaves the shell in $W
  git clone -q "$START" "$W" || return 1; cd "$W" || return 1; git remote remove origin
  rm -rf .git/logs; echo 'tdd-events*' >> .git/info/exclude  # the clone's log names the kit; the skeleton's test recorder writes tdd-events.jsonl
  git config user.email e2e@example.invalid; git config user.name e2e
  "$LAB/stacks/python-pytest/install.sh" > "$L/venv.log" 2>&1
  grep -qv '^[[:space:]]*\(#\|$\)' requirements.txt 2>/dev/null && uv pip install --python .venv/bin/python -r requirements.txt >> "$L/venv.log" 2>&1
  install_arm
  git add -A; git commit -qm "Start: $ARM workflow" --allow-empty; git tag cp$((FIRST-1))
  echo "$ARM $(wf_label) claude-opus-5-5 $PROB start $(basename "$START") $(git rev-parse --short start)" > "$L/arm.txt"
  echo "$FIRST" > "$L/start-first-cp.txt"
  log "start tagged cp$((FIRST-1))"
}
