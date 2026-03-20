#!/usr/bin/env bash
# task-reviewer-gate.sh — Deterministic validation of task files
# chmod +x task-reviewer-gate.sh
set -euo pipefail

SPEC="${1:-}"
TASKS_DIR="${2:-}"

[[ -z "$SPEC" || -z "$TASKS_DIR" ]] && { echo "Usage: task-reviewer-gate.sh <spec-path> <tasks-dir>" >&2; exit 2; }
[[ -f "$SPEC" ]] || { echo "Spec file not found: $SPEC" >&2; exit 2; }
[[ -d "$TASKS_DIR" ]] || { echo "Tasks directory not found: $TASKS_DIR" >&2; exit 2; }
command -v python3 &>/dev/null || { echo "python3 required" >&2; exit 2; }

# Build task file content map
TASK_JSON="{"
FIRST=true
for f in "$TASKS_DIR"/task-*.md; do
  [[ -f "$f" ]] || continue
  FNAME="$(basename "$f")"
  CONTENT="$(python3 -c "import json,sys; print(json.dumps(open(sys.argv[1]).read()))" "$f")"
  if $FIRST; then FIRST=false; else TASK_JSON+=","; fi
  TASK_JSON+="\"$FNAME\":$CONTENT"
done
TASK_JSON+="}"

python3 - "$SPEC" "$TASKS_DIR" "$TASK_JSON" <<'PYEOF'
import json, sys, os, re

try:
    import yaml
except ImportError:
    print("Error: PyYAML required", file=sys.stderr)
    sys.exit(2)

spec_path = sys.argv[1]
tasks_dir = sys.argv[2]
task_json = json.loads(sys.argv[3])

# Derive project root from tasks_dir
# tasks_dir is like ai-docs/feature/tasks/ or tests/fixtures/tasks/valid/
project_root = os.path.dirname(os.path.dirname(os.path.abspath(tasks_dir)))

# Read category from task.json in tasks_dir
VALID_CATEGORIES = {"feature", "corrective", "testing-infrastructure"}
category = "feature"
task_json_path = os.path.join(tasks_dir, "task.json")
if os.path.isfile(task_json_path):
    with open(task_json_path) as _f:
        _manifest = json.load(_f)
    category = _manifest.get("category", "feature")

failures = []

# Parse YAML frontmatter from content
def parse_frontmatter(content):
    lines = content.split('\n')
    if not lines or lines[0].strip() != '---':
        return {}
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            end = i
            break
    if end is None:
        return {}
    fm_text = '\n'.join(lines[1:end])
    try:
        result = yaml.safe_load(fm_text)
        return result if isinstance(result, dict) else {}
    except yaml.YAMLError:
        return {}

# Parse all tasks
tasks = {}
for fname, content in task_json.items():
    fm = parse_frontmatter(content)
    tasks[fname] = fm

# Extract ACs from spec
with open(spec_path) as f:
    spec_content = f.read()

spec_acs = set()
in_ac_section = False
for line in spec_content.split('\n'):
    if re.match(r'^## [Aa]cceptance [Cc]riteria', line):
        in_ac_section = True
        continue
    if in_ac_section and line.startswith('## '):
        break
    if in_ac_section:
        for m in re.findall(r'AC-\d+', line):
            spec_acs.add(m)

# Per-task validation
required_fields = ['id', 'type', 'wave', 'covers', 'completion_gate']

for fname, fm in tasks.items():
    # Required fields
    for field in required_fields:
        if field not in fm or fm[field] is None:
            failures.append(f"{fname}: missing required field '{field}'")

    # files_to_create or files_to_modify
    ftc = fm.get('files_to_create', []) or []
    ftm = fm.get('files_to_modify', []) or []
    if not ftc and not ftm:
        failures.append(f"{fname}: must have files_to_create or files_to_modify (neither present or both empty)")

    # type validation
    task_type = fm.get('type', '')
    if task_type not in ('test', 'implementation'):
        failures.append(f"{fname}: type must be 'test' or 'implementation', got '{task_type}'")

    # covers validation
    covers = fm.get('covers', []) or []
    if not covers:
        if 'covers' in fm:
            pass  # already flagged as missing if None
    else:
        for ac in covers:
            if not re.match(r'^AC-\d+$', str(ac)):
                failures.append(f"{fname}: invalid AC identifier '{ac}' in covers (expected AC-NN)")

    # Implementation tasks need test_tasks
    if task_type == 'implementation':
        tt = fm.get('test_tasks')
        if not tt:
            failures.append(f"{fname}: implementation task missing 'test_tasks'")

    # files_to_modify paths must exist
    for path in ftm:
        full_path = os.path.join(project_root, path)
        if not os.path.exists(full_path):
            failures.append(f"{fname}: files_to_modify path does not exist: {path}")

# Cross-task validation

# AC coverage
test_acs = set()
impl_acs = set()
for fname, fm in tasks.items():
    covers = fm.get('covers', []) or []
    task_type = fm.get('type', '')
    for ac in covers:
        if task_type == 'test':
            test_acs.add(str(ac))
        elif task_type == 'implementation':
            impl_acs.add(str(ac))

# Validate category
if category not in VALID_CATEGORIES:
    failures.append(
        f"Unrecognized category '{category}'. Valid categories: {', '.join(sorted(VALID_CATEGORIES))}"
    )
else:
    for ac in sorted(spec_acs):
        if category == "feature":
            # Standard: every AC needs both test and implementation coverage
            if ac not in test_acs:
                failures.append(f"AC coverage: {ac} not covered by any test task")
            if ac not in impl_acs:
                failures.append(f"AC coverage: {ac} not covered by any implementation task")
        elif category == "corrective":
            # Corrective: test tasks can cover ACs without paired implementation
            if ac not in test_acs and ac not in impl_acs:
                failures.append(f"AC coverage: {ac} not covered by any test task or implementation task")
        elif category == "testing-infrastructure":
            # Testing infra: test tasks can satisfy ACs directly
            if ac not in test_acs and ac not in impl_acs:
                failures.append(f"AC coverage: {ac} not covered by any test task or implementation task")

# File scope conflicts within same wave
wave_files = {}  # wave -> {path: [task_fnames]}
for fname, fm in tasks.items():
    wave = fm.get('wave', 0)
    if wave not in wave_files:
        wave_files[wave] = {}
    all_paths = (fm.get('files_to_create', []) or []) + (fm.get('files_to_modify', []) or [])
    for path in all_paths:
        if path not in wave_files[wave]:
            wave_files[wave][path] = []
        wave_files[wave][path].append(fname)

for wave, files in wave_files.items():
    for path, fnames in files.items():
        if len(fnames) > 1:
            failures.append(f"File scope conflict in wave {wave}: {path} claimed by {', '.join(fnames)}")

# test_tasks reference validation
all_task_ids = {fm.get('id') for fm in tasks.values() if fm.get('id')}
for fname, fm in tasks.items():
    if fm.get('type') == 'implementation':
        for ref in (fm.get('test_tasks', []) or []):
            if ref not in all_task_ids:
                failures.append(f"{fname}: test_tasks reference '{ref}' does not match any task id")

if failures:
    for f in failures:
        print(f, file=sys.stderr)
    sys.exit(2)

# Pass
result = {
    "gate": "task-reviewer",
    "result": "pass",
    "tasks": len(tasks),
    "acs_covered": len(spec_acs & (test_acs | impl_acs)),
    "waves": max((fm.get('wave', 0) for fm in tasks.values()), default=0),
}
print(json.dumps(result))
PYEOF

RC=$?
if [[ $RC -ne 0 ]]; then
  exit 2
fi

# Log to audit logger
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOGGER="$SCRIPT_DIR/audit-logger.py"
if [[ -f "$LOGGER" ]]; then
  SPEC_NAME="$(basename "$SPEC" .md)"
  python3 "$LOGGER" log "$SPEC_NAME" gate_result '{"gate":"task-reviewer","result":"pass"}' 2>/dev/null || true
fi
