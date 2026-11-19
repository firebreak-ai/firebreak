#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
INSTALL_SCRIPT="$PROJECT_ROOT/installer/install.sh"

ok() {
  TOTAL=$((TOTAL + 1))
  PASS=$((PASS + 1))
  echo "ok $TOTAL - $1"
}

not_ok() {
  TOTAL=$((TOTAL + 1))
  FAIL=$((FAIL + 1))
  echo "not ok $TOTAL - $1"
  fbk_diag "$1${2:+: $2}"
}

setup_mock_home() {
  MOCK_HOME=$(mktemp -d)
}

source "$PROJECT_ROOT/tests/lib/test-report.sh"
fbk_test_init "$0" || exit 2

for prerequisite in python3 uv; do
  if ! command -v "$prerequisite" >/dev/null 2>&1; then
    echo "Bail out! setup error: required command unavailable: $prerequisite"
    exit 2
  fi
done

echo "TAP version 13"

# Setup
setup_mock_home

# Phase 1: Install
HOME="$MOCK_HOME" fbk_run "install" bash "$INSTALL_SCRIPT" --source "$PROJECT_ROOT/assets" --target "$MOCK_HOME/.claude" >/dev/null 2>&1
INSTALL_EXIT=$?

# Installer exits 0
if [ "$INSTALL_EXIT" -eq 0 ]; then
  ok "Installer exits 0"
else
  not_ok "Installer exits 0" "exit code: $INSTALL_EXIT"
fi


# New skills installed
if [ -f "$MOCK_HOME/.claude/skills/fbk-intent/SKILL.md" ]; then
  ok "fbk-intent skill installed"
else
  not_ok "fbk-intent skill installed" "file not found"
fi

if [ -f "$MOCK_HOME/.claude/skills/fbk-design/SKILL.md" ]; then
  ok "fbk-design skill installed"
else
  not_ok "fbk-design skill installed" "file not found"
fi

if [ -f "$MOCK_HOME/.claude/skills/fbk-grilling/SKILL.md" ]; then
  ok "fbk-grilling skill installed"
else
  not_ok "fbk-grilling skill installed" "file not found"
fi

if [ -f "$MOCK_HOME/.claude/skills/fbk-fresh-eyes/SKILL.md" ]; then
  ok "fbk-fresh-eyes skill installed"
else
  not_ok "fbk-fresh-eyes skill installed" "file not found"
fi

if [ -f "$MOCK_HOME/.claude/skills/fbk-quality-scan/SKILL.md" ]; then
  ok "fbk-quality-scan skill installed"
else
  not_ok "fbk-quality-scan skill installed" "file not found"
fi

if [ -f "$MOCK_HOME/.claude/skills/fbk-test-review/SKILL.md" ]; then
  ok "fbk-test-review skill installed"
else
  not_ok "fbk-test-review skill installed" "file not found"
fi

for f in skills/fbk-refactor/SKILL.md fbk-docs/workflow/refactor.md skills/fbk-test-cleanup/SKILL.md skills/fbk-test-cleanup/test-trim.md fbk-docs/scoring-kit/procedure.md fbk-docs/scoring-kit/kit-writer.md fbk-scripts/run-kit.py; do
  if [ -f "$MOCK_HOME/.claude/$f" ]; then
    ok "$f installed"
  else
    not_ok "$f installed" "file not found"
  fi
done

# Reviewer role text installed; deprecated agent files are not
if [ -f "$MOCK_HOME/.claude/fbk-docs/review/researcher-role.md" ]; then
  ok "fbk-docs/review/researcher-role.md installed"
else
  not_ok "fbk-docs/review/researcher-role.md installed" "file not found"
fi

DEPRECATED_INSTALLED=$(find "$MOCK_HOME/.claude/agents" -name '*.deprecated-*' 2>/dev/null)
if [ -z "$DEPRECATED_INSTALLED" ]; then
  ok "no deprecated agent file installed"
else
  not_ok "no deprecated agent file installed" "found: $DEPRECATED_INSTALLED"
fi

if [ -f "$MOCK_HOME/.claude/fbk-docs/fbk-review-lenses/fresh-eyes-lens.md" ]; then
  ok "fbk-review-lenses/fresh-eyes-lens.md installed"
else
  not_ok "fbk-review-lenses/fresh-eyes-lens.md installed" "file not found"
fi

# New routed docs installed
if [ -f "$MOCK_HOME/.claude/fbk-docs/workflow/intent.md" ]; then
  ok "workflow/intent.md installed"
else
  not_ok "workflow/intent.md installed" "file not found"
fi

if [ -f "$MOCK_HOME/.claude/fbk-docs/workflow/design.md" ]; then
  ok "workflow/design.md installed"
else
  not_ok "workflow/design.md installed" "file not found"
fi

if [ -f "$MOCK_HOME/.claude/fbk-docs/workflow/handoffs.md" ]; then
  ok "workflow/handoffs.md installed"
else
  not_ok "workflow/handoffs.md installed" "file not found"
fi


# The installed dispatcher lists the test checkpoint command.
if HOME="$MOCK_HOME" fbk_run "list installed commands" python3 "$MOCK_HOME/.claude/fbk-scripts/fbk.py" --help 2>/dev/null | grep -qx '  test-checkpoint'; then
  ok "installed dispatcher lists test-checkpoint"
else
  not_ok "installed dispatcher lists test-checkpoint" "command missing from fbk.py --help"
fi

# Exercise the installed hook commands through their real entry point.
if HOME="$MOCK_HOME" fbk_run "execute installed hooks" python3 - "$MOCK_HOME/.claude" <<'PYEOF'
import json, os, subprocess, sys
from pathlib import Path
root = Path(sys.argv[1])
project = root.parent / 'hook-project'
project.mkdir()
dispatcher = root / 'fbk-scripts/fbk.py'
result = subprocess.run([sys.executable, str(dispatcher), 'workflow-init', '--root', str(project)], capture_output=True, text=True)
assert result.returncode == 0, result.stderr
settings = json.loads((root / 'settings.json').read_text())
for event, groups in settings['hooks'].items():
    # Expansion needs an actual unit; the lifecycle suite covers transition payloads.
    payload = {'hook_event_name': event, 'cwd': str(project), 'session_id': 'installed-hook'}
    for group in groups:
        for hook in group['hooks']:
            result = subprocess.run(hook['command'], shell=True, cwd=project,
                                    input=json.dumps(payload), text=True, capture_output=True)
            assert result.returncode == 0, (event, result.stderr)
events = project / '.fbk/runtime/events.jsonl'
assert events.is_file(), 'installed hooks did not record workflow activity'
PYEOF
then
  ok "installed hooks execute and record current workflow activity"
else
  not_ok "installed hooks execute and record current workflow activity"
fi

# Phase 2: Uninstall
HOME="$MOCK_HOME" fbk_run "uninstall" bash "$INSTALL_SCRIPT" --uninstall --target "$MOCK_HOME/.claude" >/dev/null 2>&1

# fbk-scripts tree gone after uninstall
if [ ! -d "$MOCK_HOME/.claude/fbk-scripts" ]; then
  ok "fbk-scripts tree absent after uninstall"
else
  not_ok "fbk-scripts tree absent after uninstall" "directory still exists"
fi

# Summary
echo ""
echo "# $PASS/$TOTAL tests passed"
echo "1..$TOTAL"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
