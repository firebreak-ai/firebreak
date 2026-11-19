"""Bounded standalone contributor batches on durable review snapshots."""

import hashlib
import json
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from . import review_execution, review, review_rounds
from .store import (
    WorkflowError,
    atomic_json,
    confined,
    digest,
    now,
    read_json,
    transaction,
)

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"result": {"anyOf": [{"type": "array"}, {"type": "object"}]}},
    "required": ["result"],
}


def _validate(data):
    if (
        not isinstance(data, dict)
        or set(data) != {"result"}  # constraint: response-properties
        or not isinstance(data["result"], (list, dict))
    ):
        # constraint: contributor-result
        raise WorkflowError(
            "Contributor must return its complete result object or array."
        )
    return data


def _worker(root, record, member, execution):
    directory = (
        review_rounds.round_dir(root, record["id"])
        / "workers"
        / member
        / str(record["contributors"][member]["attempts"])
    )
    shutil.copytree(confined(root, record["snapshot_path"]), directory)
    from .review_context import listing_inputs

    listing = listing_inputs(directory)
    available = {**record["snapshot_files"], **listing}
    inputs = []
    binding = record.get("code_review")
    challenger = binding and member == binding["challenger"]
    prepared = None
    role_instruction = ""
    if binding and member in (binding["detector"], binding["challenger"]):
        relative = "_review_inputs/lens.md"
        path = directory / relative
        path.parent.mkdir(exist_ok=True)
        path.write_text(binding["lens_text"])
        available[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        role_instruction = (
            "Read _review_inputs/lens.md. Your explicit role is Challenger: return one verdict per normalized input in order; do not return rewritten sightings. "
            if challenger
            else "Read _review_inputs/lens.md. Your explicit role is Detector: return the complete detection result using that lens output contract (sighting array unless the lens requires findings and coverage). "
        )
    if challenger:
        from .code_review_pipeline import prepare

        prepared = prepare(root, record, directory, execution)
        relative = "_review_inputs/normalized.json"
        available[relative] = hashlib.sha256(
            (directory / relative).read_bytes()
        ).hexdigest()
        inputs.append(
            {
                "path": relative,
                "role": "neutral sightings; return one verdict per input in order",
            }
        )
    for name, row in record["contributors"].items():
        if challenger or row["status"] != "complete":
            continue
        relative = f"_review_inputs/{name}.json"
        path = directory / relative
        path.parent.mkdir(exist_ok=True)
        shutil.copyfile(confined(root, row["result_path"]), path)
        available[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        inputs.append({"contributor": name, "path": relative})
    for index, row in enumerate(
        [] if challenger else record.get("supporting_results", [])
    ):
        relative = f"_review_inputs/import-{index}.json"
        source = confined(root, row["path"])
        if digest(read_json(source)) != row["sha256"]:
            raise WorkflowError(
                "Imported supporting evidence changed; restore its captured artifact."
            )
        path = directory / relative
        path.parent.mkdir(exist_ok=True)
        shutil.copyfile(source, path)
        available[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        inputs.append(
            {
                "path": relative,
                "classification": "supporting-only; independently assess this imported claim",
            }
        )
    required = sorted(
        set(record["required_files"] + (prepared["required"] if prepared else []) + list(listing))
    )
    config = {
        **record["configuration"],
        "_review_available_files": available,
        "_review_required_files": required,
        "_managed_project_root": str(root),
        "_managed_execution": execution,
    }
    from .constraints import block_text, render

    prompt = (
        f"Contributor: {member}\nComplete only your declared contribution on this immutable source copy. "
        "Return its full JSON array/object as the result field, plus required context inspection record. "
        "Use complete prior-result artifacts when your assigned role depends on them; do not infer missing results. "
        "Do not remediate deliverables. Request bounded investigations when direct evidence can resolve uncertainty.\n"
        + role_instruction
        + record["instructions"]
        + "\nAvailable completed peer artifacts:\n"
        + json.dumps(inputs)
        + "\nrequired_files:\n"
        + json.dumps(required)
        + block_text(render("contributor", config, SCHEMA))
    )
    response = review.claude_review(
        directory, prompt, config, schema=SCHEMA, validator=_validate
    )
    if prepared:
        from .code_review_pipeline import compose

        response = compose(root, directory, execution, prepared, response)
    if (response.get("context") or {}).get("status") == "incomplete":
        # The validator accepts an honest incomplete declaration; a contribution built on
        # missing evidence is recorded as not complete, with the reader's reason, not as done.
        # constraint: contributor-incomplete-context
        raise WorkflowError(
            f"Contributor {member} reported incomplete context; missing context: "
            + "; ".join(response["context"]["missing_context"])
        )
    result = _validate(response["review"])["result"]
    if binding and member == binding["detector"]:
        from .code_review_pipeline import detector_findings

        detector_findings(binding, result)
    envelope = {
        "schema": "review-contribution-v1",
        "round_id": record["id"],
        "contract_id": record["contract_id"],
        "contributor": member,
        "status": "complete",
        "result": result,
        "result_digest": digest(result),
    }
    path = directory / "contribution.json"
    atomic_json(path, envelope)
    review_rounds._submit_runtime(root, record["id"], path, execution, response)
    return response


def _reserve(root, round_id, members, execution):
    with transaction(root):
        record = review_rounds.load_round(root, round_id)
        for member in members:
            row = record["contributors"][member]
            if row["status"] == "complete":
                raise WorkflowError("Contributor already complete.")
            row.update(
                status="running", attempts=row.get("attempts", 0) + 1, started_at=now()
            )
            row["execution"] = {
                "execution_id": execution.execution_id,
                "contract_id": record["contract_id"],
                "snapshot_digest": digest(record["snapshot_files"]),
                "attempt": row["attempts"],
                "budget": dict(record["budget"]),
            }
        record["events"].append(
            {
                "type": "contributor-batch-started",
                "members": members,
                "at": now(),
                "execution_id": execution.execution_id,
            }
        )
        review_rounds.save_round(root, record)
        return record


def run(root, round_id, members):
    root = Path(root).resolve()
    record = review_rounds.status(root, round_id)
    if (
        not members
        or len(set(members)) != len(members)
        or any(m not in record["contributors"] for m in members)
    ):
        raise WorkflowError("Name the declared contributors to launch in this batch.")
    if any(record["contributors"][m]["status"] == "complete" for m in members):
        raise WorkflowError("Contributor already complete; resume only missing work.")
    if (
        record["historical"]
        or not record["snapshot_intact"]
        or record.get("superseded_by")
    ):
        raise WorkflowError(
            "Review snapshot is historical or changed; start a current review contract."
        )
    binding = record.get("code_review")
    if binding:
        from .code_review_pipeline import check

        check(binding)
        if (
            binding["challenger"] in members
            and record["contributors"][binding["detector"]]["status"] != "complete"
        ):
            raise WorkflowError(
                "Code-review challenger requires its completed detector first."
            )
    execution = review_execution.activate_round(root, round_id)
    try:
        record = _reserve(root, round_id, members, execution)
        with ThreadPoolExecutor(max_workers=len(members)) as pool:
            jobs = {
                pool.submit(_worker, root, record, m, execution): m for m in members
            }
            for job in as_completed(jobs):
                member = jobs[job]
                try:
                    job.result()
                except Exception as exc:  # noqa: BLE001 - retain every completed peer; fail closed on transport/worker errors.
                    review_rounds.fail(
                        root, round_id, member, str(exc) or type(exc).__name__
                    )
    finally:
        execution.finish()
    return review_rounds.status(root, round_id)
