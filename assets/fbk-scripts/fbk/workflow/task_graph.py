"""Scheduling edges order writers and readers; file inputs are declared separately."""

from .store import WorkflowError, confined


def follows(tasks, later, earlier):
    by_id = {task["id"]: task for task in tasks}
    # Every test task finishes before any implementation task runs.
    if (
        by_id[later].get("stage") == "implementation"
        and by_id[earlier].get("stage") == "tests"
    ):
        return True
    pending = list(by_id[later].get("depends_on", []))
    seen = set()
    while pending:
        item = pending.pop()
        if item == earlier:
            return True
        if item not in seen:
            seen.add(item)
            pending.extend(by_id[item].get("depends_on", []))
    return False


def consumed_patterns(task):
    refs = task.get("input_refs", [])
    return list(
        dict.fromkeys(
            [
                *task.get("consumes", []),
                *(
                    ref.split("#", 1)[0].rsplit(":", 1)[0]
                    if ref.split("#", 1)[0].rsplit(":", 1)[-1].isdigit()
                    else ref.split("#", 1)[0]
                    for ref in refs
                ),
            ]
        )
    )


def check_input_shapes(task):
    """Refuse malformed file inputs before any path is read from them."""
    consumes = task.get("consumes", [])
    if not isinstance(consumes, list) or any(
        not isinstance(p, str) or not p for p in consumes
    ):
        raise WorkflowError(
            "Task consumes must be an array of repository-relative file paths or patterns."
        )
    refs = task.get("input_refs", [])
    if not isinstance(refs, list) or any(
        not isinstance(ref, str) or not ref for ref in refs
    ):
        raise WorkflowError(
            "Task input_refs must be an array of nonempty references."
        )


def validate(root, tasks):
    from . import evidence
    from .handoff import _references, ownership_overlaps

    for task in tasks:
        check_input_shapes(task)
        consumes = task.get("consumes", [])
        for path in consumes:
            confined(root, path)
        if ownership_overlaps(consumes, task["files"]):
            raise WorkflowError(
                "Task consumes are read-only inputs from outside its ownership; owned files already carry their initial snapshot."
            )
    # An ordered writer may create a file or change its headings and line count.
    # Validate other references now; launch resolves every reference against the
    # actual producer output before assigning work.
    for task in tasks:
        for ref in task.get("input_refs", []):
            path = consumed_patterns({"input_refs": [ref]})[0]
            target = confined(root, path)
            if any(
                other["id"] != task["id"]
                and follows(tasks, task["id"], other["id"])
                and evidence.matches(path, other["files"])
                for other in tasks
            ):
                continue
            if target.exists():
                try:
                    _references(root, [ref], "input_refs")
                except WorkflowError as exc:
                    raise WorkflowError(f"Task {task['id']}: {exc}") from exc
            else:
                raise WorkflowError(
                    f"Task {task['id']} input reference is missing with no ordered producer: {ref}. "
                    "Correct the reference or declare its producer and dependency."
                )
        for path in task.get("consumes", []):
            if not evidence.expand(root, [path]) and not any(
                other["id"] != task["id"]
                and follows(tasks, task["id"], other["id"])
                and (evidence.matches(path, other["files"])
                     or any(evidence.matches(output, [path]) for output in other["files"]))
                for other in tasks
            ):
                raise WorkflowError(
                    f"Task {task['id']} consumed input is missing with no ordered producer: {path}. "
                    "Correct the path or declare its producer and dependency."
                )
    for index, first in enumerate(tasks):
        for second in tasks[index + 1 :]:
            conflicts = (
                ownership_overlaps(first["files"], second["files"])
                or ownership_overlaps(first["files"], consumed_patterns(second))
                or ownership_overlaps(second["files"], consumed_patterns(first))
            )
            if (
                conflicts
                and not follows(tasks, first["id"], second["id"])
                and not follows(tasks, second["id"], first["id"])
            ):
                raise WorkflowError(
                    f"Task dependency order is missing between {first['id']} and {second['id']}: "
                    "overlapping writers or a writer and consumer must be ordered before breakdown acceptance."
                )
