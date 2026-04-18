"""Breakdown gate validation logic."""

import argparse
import json
import re
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Dict, List


def validate_breakdown(spec_text: str, manifest: dict, task_files: Dict[str, str]) -> dict:
    """Validate a task breakdown against its spec.

    Args:
        spec_text: The spec markdown content as a string.
        manifest: The parsed task.json dict.
        task_files: Dict mapping task filename to file content string.

    Returns:
        On pass: {"gate": "breakdown", "result": "pass", "spec_acs": N, "tasks": N, "waves": N}
        On fail: {"gate": "breakdown", "result": "fail", "failures": [...]}
    """
    fails: List[str] = []
    tasks = manifest.get("tasks", [])
    category = manifest.get("category", "feature")

    # Schema validation
    required_fields = ["id", "title", "file", "type", "wave_id", "dependencies", "covers", "model", "status"]
    for t in tasks:
        missing = [f for f in required_fields if f not in t]
        if missing:
            fails.append(f"Schema: task {t.get('id', '?')} missing fields: {', '.join(missing)}")

    # Build lookup maps
    task_by_id = {t["id"]: t for t in tasks}

    # 1. AC coverage — spec ACs must appear in covers with both test+impl tasks
    ac_sec = re.search(r"## Acceptance criteria(.*?)(?=\n## |\Z)", spec_text, re.I | re.S)
    spec_acs = set(re.findall(r"\bAC-\d+\b", ac_sec.group(1))) if ac_sec else set()

    ac_tasks: Dict[str, list] = defaultdict(list)
    for t in tasks:
        for ac in t.get("covers", []):
            ac_tasks[ac].append(t)

    for ac in sorted(spec_acs):
        if ac not in ac_tasks:
            fails.append(f"AC coverage: {ac} not covered by any task")
            continue
        has_test = any(t["type"] == "test" for t in ac_tasks[ac])
        has_impl = any(t["type"] == "implementation" for t in ac_tasks[ac])
        if not has_test:
            fails.append(f"AC coverage: {ac} has no test task")
        if category != "corrective" and not has_impl:
            fails.append(f"AC coverage: {ac} has no implementation task")

    for ac in sorted(set(ac_tasks) - spec_acs):
        fails.append(f"AC coverage: {ac} referenced by tasks but not in spec")

    # 2. DAG acyclicity via topological sort
    all_ids = set(t["id"] for t in tasks)
    adj: Dict[str, list] = defaultdict(list)
    indeg: Dict[str, int] = defaultdict(int, {tid: 0 for tid in all_ids})
    for t in tasks:
        for dep in t.get("dependencies", []):
            if dep not in all_ids:
                fails.append(f"Dependency: {t['id']} depends on unknown task {dep}")
            else:
                adj[dep].append(t["id"])
                indeg[t["id"]] += 1

    q = deque(tid for tid in all_ids if indeg[tid] == 0)
    seen: List[str] = []
    while q:
        n = q.popleft()
        seen.append(n)
        for nb in adj[n]:
            indeg[nb] -= 1
            if indeg[nb] == 0:
                q.append(nb)
    if len(seen) != len(all_ids):
        cycle = sorted(all_ids - set(seen))
        fails.append(f"DAG: cycle detected among: {', '.join(cycle)}")

    # 3. Wave ordering respects dependencies (dep wave must be strictly less)
    for t in tasks:
        for dep in t.get("dependencies", []):
            dep_task = task_by_id.get(dep)
            if dep_task and dep_task["wave_id"] >= t["wave_id"]:
                fails.append(
                    f"Wave ordering: {dep} (wave {dep_task['wave_id']}) must precede {t['id']} (wave {t['wave_id']})"
                )

    # 4. Test-before-impl within each wave
    wave_tasks: Dict[str, list] = defaultdict(list)
    for t in tasks:
        wave_tasks[t["wave_id"]].append(t)

    for wave, wtasks in wave_tasks.items():
        saw_impl = False
        for t in wtasks:
            if t["type"] == "implementation":
                saw_impl = True
            elif t["type"] == "test" and saw_impl:
                fails.append(
                    f"Test ordering: {t['id']} (test) listed after implementation task in wave {wave}"
                )

    # 5. File reference existence
    for t in tasks:
        fname = t.get("file", "")
        if fname not in task_files:
            fails.append(f"File reference: {t['id']} references {fname} which does not exist in tasks dir")

    # Parse file lists from individual task files for scope checks
    task_file_list: Dict[str, list] = {}
    for t in tasks:
        fname = t.get("file", "")
        content = task_files.get(fname, "")
        sec = re.search(r"## Files to (?:create|modify|create/modify)(.*?)(?=\n## |\Z)", content, re.I | re.S)
        files = []
        if sec:
            for ln in sec.group(1).splitlines():
                fm = re.match(r"\s*[-*]\s+(?:\*{0,2}(?:Create|Modify|Update)?\*{0,2}:?\s*)?`([^`]+)`", ln, re.I)
                if fm:
                    files.append(fm.group(1))
                else:
                    fm2 = re.match(r"\s*[-*]\s+\*{0,2}(?:Create|Modify)?\*{0,2}:?\s*(\S+\.\w+)", ln, re.I)
                    if fm2:
                        files.append(fm2.group(1))
        task_file_list[t["id"]] = files

        # 6. File count constraint (max 2 without justification)
        if len(files) > 2:
            has_just = bool(
                re.search(r"justif|rationale|because|reason|multiple.*file|touches.*file", content, re.I)
            )
            if not has_just:
                fails.append(f"File count: {t['id']} ({fname}) has {len(files)} files without justification")

    # 7. File scope conflicts within same wave
    for wave, wtasks in wave_tasks.items():
        seen_files: Dict[str, str] = {}
        for t in wtasks:
            for f in task_file_list.get(t["id"], []):
                if f in seen_files:
                    fails.append(f"File conflict: {f} in both {seen_files[f]} and {t['id']} (wave {wave})")
                else:
                    seen_files[f] = t["id"]

    # 8. Every code-modifying impl task has a corresponding test task
    test_covered: set = set()
    for ac, ac_t in ac_tasks.items():
        if any(t["type"] == "test" for t in ac_t):
            test_covered.update(t["id"] for t in ac_t)
    for tid, files in task_file_list.items():
        t = task_by_id.get(tid)
        if not t or t["type"] == "test":
            continue
        code_files = [f for f in files if not re.search(r"\.(md|json|yaml|yml|toml)$", f)]
        if code_files and tid not in test_covered:
            fails.append(f"Test coverage: code-modifying task {tid} has no corresponding test task")

    if fails:
        return {"gate": "breakdown", "result": "fail", "failures": fails}

    return {
        "gate": "breakdown",
        "result": "pass",
        "spec_acs": len(spec_acs),
        "tasks": len(tasks),
        "waves": len(wave_tasks),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a task breakdown against its spec.")
    parser.add_argument("spec", help="Path to the spec markdown file.")
    parser.add_argument("tasks_dir", help="Path to the tasks directory containing task.json and task-*.md files.")
    args = parser.parse_args()

    spec_path = Path(args.spec)
    tasks_dir = Path(args.tasks_dir)

    if not spec_path.is_file():
        print(f"Error: spec file not found: {spec_path}", file=sys.stderr)
        sys.exit(2)
    if not tasks_dir.is_dir():
        print(f"Error: tasks dir not found: {tasks_dir}", file=sys.stderr)
        sys.exit(2)

    manifest_path = tasks_dir / "task.json"
    if not manifest_path.is_file():
        print(f"Error: task.json missing from {tasks_dir}", file=sys.stderr)
        sys.exit(2)

    spec_text = spec_path.read_text()
    manifest = json.loads(manifest_path.read_text())

    task_files: Dict[str, str] = {}
    for f in sorted(tasks_dir.glob("task-*.md")):
        task_files[f.name] = f.read_text()

    result = validate_breakdown(spec_text, manifest, task_files)

    if result["result"] == "fail":
        for failure in result.get("failures", []):
            print(failure, file=sys.stderr)
        sys.exit(2)

    print(json.dumps(result))


if __name__ == "__main__":
    main()
