"""Shared helpers for plans that need a refactor task.

Breakdown close refuses a plan unless every production path an implementation task owns is
also owned by a refactor task depending on it. Fixtures that are not about refactoring add one
covering task with ``with_refactor`` and finish it with ``complete_refactor_tasks``.
"""

import sys

from fbk.workflow import handoff, review, store

REFACTOR_ID = "refactor"


def refactor_task(tasks, task_id=REFACTOR_ID):
    """A refactor task owning every production path the plan's implementation tasks own,
    depending on each of them and linking the requirements they link."""
    builders = [t for t in tasks if t.get("stage") == "implementation" and not t.get("refactor")]
    return {
        "id": task_id,
        "stage": "implementation",
        "refactor": True,
        "description": "Refactor the code the implementation tasks built.",
        "files": list(dict.fromkeys(path for t in builders for path in t["files"])),
        "depends_on": [t["id"] for t in builders],
        "acceptance_refs": list(dict.fromkeys(
            ref.split("#", 1)[0] for t in builders for ref in t.get("acceptance_refs", []))),
        "verification": "The structure improves and every test still passes.",
        "check_expectations": [{"argv": [sys.executable, "-c", "pass  # refactor"], "exit_code": 0}],
    }


def with_refactor(tasks, task_id=REFACTOR_ID):
    """``tasks`` plus one covering refactor task, unless it has no implementation task or
    already plans a refactor."""
    if any(t.get("refactor") for t in tasks) or not any(t.get("stage") == "implementation" for t in tasks):
        return tasks
    return [*tasks, refactor_task(tasks, task_id)]


def complete_refactor_tasks(root, unit="feature", session="s"):
    """Start and finish every refactor task, with real checks and no change. A refactor runs
    again each time, since code an implementation task changed after it makes it stale."""
    for task in store.read_json(root / f".fbk/{unit}/tasks.json"):
        if not task.get("refactor"):
            continue
        with store.transaction(root):
            record = store.load(root, unit)
            handoff.start_task(root, record, session, task["id"], f"{task['id']}-worker")
        checks = [review.run_command(item["argv"], root, 10) for item in task["check_expectations"]]
        result = handoff.complete_task(
            root, unit, session, task["id"], changed_files=[],
            checks=[{**check, "evidence": "The refactor task's check ran."} for check in checks],
            unresolved=[], outcome="No improvement: the code is one cohesive decision.")
        assert result["status"] == "completed", result
