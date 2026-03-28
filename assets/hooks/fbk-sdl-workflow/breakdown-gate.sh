#!/usr/bin/env bash
# breakdown-gate.sh — Stage 3 structural prerequisite validation
# Usage: breakdown-gate.sh <spec-file> <tasks-dir>
# Exit 0: pass (stdout: JSON summary). Exit 2: failures (stderr: details).

set -euo pipefail

SPEC="${1:-}"; TASKS="${2:-}"
[[ -f "$SPEC" ]]   || { echo "Error: spec file not found: ${SPEC}" >&2; exit 2; }
[[ -d "$TASKS" ]]  || { echo "Error: tasks dir not found: ${TASKS}" >&2; exit 2; }
[[ -f "$TASKS/task.json" ]] || { echo "Error: task.json missing from ${TASKS}" >&2; exit 2; }
command -v python3 >/dev/null 2>&1 || { echo "Error: python3 required" >&2; exit 2; }

# Build task file content map as JSON: {"task-NN-name.md": "<content>", ...}
TASK_CONTENT="{"
for f in "$TASKS"/task-*.md; do
  [[ -f "$f" ]] || continue
  NAME=$(basename "$f")
  CONTENT=$(python3 -c "import sys,json; print(json.dumps(open(sys.argv[1]).read()))" "$f")
  TASK_CONTENT+="\"${NAME}\": ${CONTENT},"
done
TASK_CONTENT="${TASK_CONTENT%,}}"

python3 - "$SPEC" "$TASKS/task.json" "$TASK_CONTENT" <<'PYEOF'
import sys, re, json
from collections import defaultdict, deque

spec_text = open(sys.argv[1]).read()
manifest  = json.load(open(sys.argv[2]))
tfiles    = json.loads(sys.argv[3])
fails     = []

tasks = manifest.get("tasks", [])

# Validate task.json is well-formed
required_fields = ["id", "title", "file", "type", "wave_id", "dependencies", "covers", "model", "status"]
for t in tasks:
    missing = [f for f in required_fields if f not in t]
    if missing:
        fails.append(f"Schema: task {t.get('id','?')} missing fields: {', '.join(missing)}")

# Build lookup maps
task_by_id = {t["id"]: t for t in tasks}
id_by_file = {}
for t in tasks:
    m = re.match(r'task-0*(\d+)', t.get("file", ""))
    if m:
        id_by_file[t["file"]] = t["id"]

# 1. AC coverage — spec ACs must appear in covers with both test+impl tasks
ac_sec = re.search(r'## Acceptance criteria(.*?)(?=\n## |\Z)', spec_text, re.I|re.S)
spec_acs = set(re.findall(r'\bAC-\d+\b', ac_sec.group(1))) if ac_sec else set()

# Build coverage map from task.json covers fields
ac_tasks = defaultdict(list)  # AC-NN -> [task entries]
for t in tasks:
    for ac in t.get("covers", []):
        ac_tasks[ac].append(t)

category = manifest.get("category", "feature")

for ac in sorted(spec_acs):
    if ac not in ac_tasks:
        fails.append(f"AC coverage: {ac} not covered by any task"); continue
    has_test = any(t["type"] == "test" for t in ac_tasks[ac])
    has_impl = any(t["type"] == "implementation" for t in ac_tasks[ac])
    if not has_test: fails.append(f"AC coverage: {ac} has no test task")
    if category != "corrective" and not has_impl:
        fails.append(f"AC coverage: {ac} has no implementation task")

# Check for tasks covering ACs not in the spec
for ac in sorted(set(ac_tasks) - spec_acs):
    fails.append(f"AC coverage: {ac} referenced by tasks but not in spec")

# 2. DAG acyclicity
all_ids = set(t["id"] for t in tasks)
adj = defaultdict(list)
indeg = defaultdict(int, {tid: 0 for tid in all_ids})
for t in tasks:
    for dep in t.get("dependencies", []):
        if dep not in all_ids:
            fails.append(f"Dependency: {t['id']} depends on unknown task {dep}")
        else:
            adj[dep].append(t["id"])
            indeg[t["id"]] += 1

q = deque(tid for tid in all_ids if indeg[tid] == 0)
seen = []
while q:
    n = q.popleft(); seen.append(n)
    for nb in adj[n]:
        indeg[nb] -= 1
        if indeg[nb] == 0: q.append(nb)
if len(seen) != len(all_ids):
    cycle = sorted(all_ids - set(seen))
    fails.append(f"DAG: cycle detected among: {', '.join(cycle)}")

# 3. Wave ordering respects dependencies
for t in tasks:
    for dep in t.get("dependencies", []):
        dep_task = task_by_id.get(dep)
        if dep_task and dep_task["wave_id"] >= t["wave_id"]:
            fails.append(f"Wave ordering: {dep} (wave {dep_task['wave_id']}) must precede {t['id']} (wave {t['wave_id']})")

# 4. Test-before-impl within each wave
wave_tasks = defaultdict(list)
for t in tasks:
    wave_tasks[t["wave_id"]].append(t)

for wave, wtasks in wave_tasks.items():
    saw_impl = False
    for t in wtasks:
        if t["type"] == "implementation": saw_impl = True
        elif t["type"] == "test" and saw_impl:
            fails.append(f"Test ordering: {t['id']} (test) listed after implementation task in wave {wave}")

# 5. Every file reference points to an existing task file
for t in tasks:
    fname = t.get("file", "")
    if fname not in tfiles:
        fails.append(f"File reference: {t['id']} references {fname} which does not exist in tasks dir")

# Parse file lists from individual task files for scope checks
task_file_list = {}  # task id -> [files]
for t in tasks:
    fname = t.get("file", "")
    content = tfiles.get(fname, "")
    sec = re.search(r'## Files to (?:create|modify|create/modify)(.*?)(?=\n## |\Z)', content, re.I|re.S)
    files = []
    if sec:
        for ln in sec.group(1).splitlines():
            fm = re.match(r'\s*[-*]\s+(?:\*{0,2}(?:Create|Modify|Update)?\*{0,2}:?\s*)?`([^`]+)`', ln, re.I)
            if fm: files.append(fm.group(1))
            else:
                fm2 = re.match(r'\s*[-*]\s+\*{0,2}(?:Create|Modify)?\*{0,2}:?\s*(\S+\.\w+)', ln, re.I)
                if fm2: files.append(fm2.group(1))
    task_file_list[t["id"]] = files
    # 6. File count constraint
    if len(files) > 2:
        has_just = bool(re.search(r'justif|rationale|because|reason|multiple.*file|touches.*file', content, re.I))
        if not has_just:
            fails.append(f"File count: {t['id']} ({fname}) has {len(files)} files without justification")

# 7. File scope conflicts within same wave
for wave, wtasks in wave_tasks.items():
    seen_files = {}
    for t in wtasks:
        for f in task_file_list.get(t["id"], []):
            if f in seen_files: fails.append(f"File conflict: {f} in both {seen_files[f]} and {t['id']} (wave {wave})")
            else: seen_files[f] = t["id"]

# 8. Every code-modifying task has a test task
test_covered = set()
for ac, ac_t in ac_tasks.items():
    if any(t["type"] == "test" for t in ac_t):
        test_covered.update(t["id"] for t in ac_t)
for tid, files in task_file_list.items():
    t = task_by_id.get(tid)
    if not t or t["type"] == "test": continue
    code_files = [f for f in files if not re.search(r'\.(md|json|yaml|yml|toml)$', f)]
    if code_files and tid not in test_covered:
        fails.append(f"Test coverage: code-modifying task {tid} has no corresponding test task")

if fails:
    for f in fails: print(f, file=sys.stderr)
    sys.exit(2)

print(json.dumps({
    "gate": "breakdown",
    "result": "pass",
    "spec_acs": len(spec_acs),
    "tasks": len(tasks),
    "waves": len(wave_tasks)
}))
PYEOF
