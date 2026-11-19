"""Durable standalone review transport using the managed source snapshot policy.

Contributors publish whole JSON artifacts, never fragments of chat output. This
module checks transport completeness; the finding pipeline checks semantics.
"""

import argparse
import copy
import hashlib
import json
import re
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .review_context import snapshot, source_paths
from .store import (
    ROUND_ID,
    WorkflowError,
    atomic_json,
    confined,
    digest,
    now,
    project_config,
    read_json,
    transaction,
)


def round_dir(root, round_id):
    if not isinstance(round_id, str) or not ROUND_ID.fullmatch(round_id):
        raise WorkflowError("Invalid review round id.")
    return confined(root, f".fbk/runtime/review-rounds/{round_id}")


def load_round(root, round_id):
    return read_json(round_dir(root, round_id) / "round.json")


def save_round(root, record):
    atomic_json(round_dir(root, record["id"]) / "round.json", record)


def _manifest(root, required):
    return {
        p: hashlib.sha256(confined(root, p).read_bytes()).hexdigest()
        for p in source_paths(root, required)
    }


def _contract(
    manifest, instructions, config, contributors, required, scope=(), code_review=None
):
    return digest(
        {
            "sources": manifest,
            "instructions": instructions,
            "configuration": config,
            "contributors": sorted(contributors),
            "required": sorted(required),
            "authorized_scope": sorted(scope),
            "protocol": "review-contribution-v1",
            "code_review": code_review,
        }
    )


def begin(
    root,
    contributors,
    instructions,
    config,
    required=(),
    *,
    previous=None,
    scope=(),
    code_review=None,
):
    from .review import bounded_number

    if (
        not contributors
        or len(contributors) != len(set(contributors))
        or any(
            not isinstance(c, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", c)
            for c in contributors
        )
    ):
        raise WorkflowError("Declare unique named review contributors.")
    if not isinstance(instructions, str) or not instructions.strip():
        raise WorkflowError("Review instructions must be captured before starting.")
    from .code_review_pipeline import capture

    code_review = capture(code_review, contributors)
    seconds = bounded_number(config, "review_round_timeout", 9999, 86400)
    root = Path(root).resolve()
    if not isinstance(scope, (list, tuple)) or any(
        not isinstance(p, str) or not p for p in scope
    ):
        raise WorkflowError("Declare existing authorized scope as concrete file paths.")
    for path in scope:
        confined(root, path)
    # A standalone round has no unit; its start time lets an operator match the folder.
    round_id = f"review-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex}"
    with snapshot(root, required) as (sources, manifest):
        directory = round_dir(root, round_id)
        directory.mkdir(parents=True)
        shutil.copytree(sources, directory / "sources")
    record = {
        "id": round_id,
        "created_at": now(),
        "status": "incomplete",
        "contract_id": _contract(
            manifest, instructions, config, contributors, required, scope, code_review
        ),
        "instructions": instructions,
        "code_review": code_review,
        "configuration": config,
        "snapshot_files": manifest,
        "required_files": sorted(required),
        "authorized_scope": sorted(set(scope)),
        "snapshot_path": (directory / "sources").relative_to(root).as_posix(),
        "contributors": {c: {"status": "pending"} for c in contributors},
        "budget": {"seconds": seconds, "spent_seconds": 0},
        "investigations": {},
        "events": [],
    }
    with transaction(root):
        if previous:
            prior = _inspect(root, load_round(root, previous))
            if (
                prior["missing"]
                or prior["investigation_pending"]
                or prior.get("execution_pending")
                or prior.get("superseded_by")
            ):
                raise WorkflowError(
                    "Previous round needs completion or human disposition before follow-up."
                )
            record["budget"] = copy.deepcopy(prior["budget"])
            if prior.get("managed_clock"):
                record["managed_clock"] = copy.deepcopy(prior["managed_clock"])
            record["previous_round"] = previous
            record["prior_results"] = copy.deepcopy(prior["contributors"])
            from .remediation_verification import inherited

            inherited(prior, record)
            prior["superseded_by"] = round_id
            save_round(root, prior)
        save_round(root, record)
    return record


def _inspect(root, record):
    if record.get("kind") == "managed-phase-review":
        raise WorkflowError(
            "This is a managed phase review; use the phase workflow for status and acceptance."
        )
    try:
        live = _manifest(root, record["required_files"])
    except (OSError, WorkflowError) as exc:
        live = {"unavailable": str(exc)}
    original = record["snapshot_files"]
    if live != original and not record.get("drift"):
        record["drift"] = {
            "paths": sorted(
                p for p in set(original) | set(live) if original.get(p) != live.get(p)
            ),
            "detected_at": now(),
            "original_revision": digest(original),
            "current_revision": digest(live),
        }
        record["events"].append({"type": "unexpected-source-change", **record["drift"]})
    snapshot_root = confined(root, record["snapshot_path"])
    try:
        intact = _manifest(snapshot_root, record["required_files"]) == original
    except (OSError, WorkflowError):
        intact = False
    missing = []
    for name, row in record["contributors"].items():
        if row["status"] == "complete":
            try:
                intact_result = (
                    digest(read_json(confined(root, row["result_path"])))
                    == row["artifact_digest"]
                )
                provenance = row.get("provenance", {})
                intact_result = (
                    intact_result
                    and provenance.get("contract_id") == record["contract_id"]
                    and provenance.get("snapshot_digest")
                    == digest(record["snapshot_files"])
                    and provenance.get("execution_id")
                    == row.get("execution", {}).get("execution_id")
                    and bool(provenance.get("execution_id"))
                    and digest(read_json(confined(root, provenance["response_path"])))
                    == provenance["response_digest"]
                )
            except (WorkflowError, KeyError):
                intact_result = False
            if not intact_result:
                row.update(
                    status="failed",
                    error="Durable result or runtime execution provenance changed or is unavailable.",
                )
        if row["status"] != "complete":
            missing.append(name)
    record.update(
        missing=missing,
        status="incomplete" if missing else "complete",
        historical=bool(record.get("drift")),
        snapshot_intact=intact,
    )
    from .investigations import needs_human_review

    investigating = needs_human_review(record) or any(
        (
            not investigation.get("resolution")
            and investigation.get("disposition", {}).get("disposition") != "stop"
        )
        or any(
            attempt.get("status") == "running"
            for attempt in investigation.get("attempts", [])
        )
        for investigation in record.get("investigations", {}).values()
    )
    record["investigation_pending"] = investigating
    record["execution_pending"] = bool(record.get("managed_clock", {}).get("active"))
    record["execution_exhausted"] = (
        record["budget"]["spent_seconds"] >= record["budget"]["seconds"]
    )
    from .remediation_verification import inspect

    inspect(root, record)
    record["remediation_allowed"] = (
        not missing
        and not record["historical"]
        and intact
        and not investigating
        and not record.get("superseded_by")
        and not record["pending_verifications"]
        and not record["unaccounted_changes"]
        and not record["execution_pending"]
        and not record["execution_exhausted"]
    )
    return record


def status(root, round_id):
    with transaction(root):
        record = _inspect(root, load_round(root, round_id))
        save_round(root, record)
        return record


def require_complete(root, round_id):
    record = status(root, round_id)
    if record["execution_pending"]:
        raise WorkflowError(
            "Review execution is active or interrupted; complete or recover it before proceeding."
        )
    if record["execution_exhausted"]:
        raise WorkflowError(
            "Review execution budget exhausted; human help is required."
        )
    if record["investigation_pending"]:
        raise WorkflowError(
            "Unresolved investigation requires completion or human disposition."
        )
    if record.get("superseded_by"):
        raise WorkflowError("Review round superseded; use its current follow-up.")
    if record["missing"]:
        raise WorkflowError(
            "Review incomplete; missing or invalid result: "
            + ", ".join(record["missing"])
        )
    if not record["snapshot_intact"]:
        raise WorkflowError(
            "Review snapshot changed; results cannot authorize remediation."
        )
    if record["historical"]:
        raise WorkflowError(
            "Review is historical: unexpected source change; review current sources before remediation."
        )
    if record["pending_verifications"]:
        raise WorkflowError(
            "Independent remediation verification is incomplete or stale: "
            + ", ".join(record["pending_verifications"])
        )
    if record["unaccounted_changes"]:
        raise WorkflowError(
            "Review has unaccounted changes: "
            + ", ".join(record["unaccounted_changes"])
        )
    return record


def resume(root, round_id, instructions, config):
    with transaction(root):
        record = _inspect(root, load_round(root, round_id))
        save_round(root, record)
        try:
            contract = _contract(
                _manifest(root, record["required_files"]),
                instructions,
                config,
                record["contributors"],
                record["required_files"],
                record.get("authorized_scope", []),
                record.get("code_review"),
            )
        except OSError as exc:
            raise WorkflowError(f"Review contract unavailable: {exc}") from exc
        if contract != record["contract_id"] or not record["snapshot_intact"]:
            raise WorkflowError(
                "Review contract changed; start a new round. Historical evidence retained."
            )
        record["events"].append(
            {
                "type": "round-resumed",
                "at": now(),
                "reused": [
                    c for c in record["contributors"] if c not in record["missing"]
                ],
                "missing": record["missing"],
            }
        )
        save_round(root, record)
        return record


def _read_envelope(round_id, path):
    envelope = read_json(path)
    required = {
        "schema",
        "round_id",
        "contract_id",
        "contributor",
        "status",
        "result",
        "result_digest",
    }
    if (
        not isinstance(envelope, dict)
        or set(envelope) != required
        or envelope["schema"] != "review-contribution-v1"
        or envelope["round_id"] != round_id
        or envelope["status"] != "complete"
        or not isinstance(envelope["result"], (list, dict))
        or digest(envelope["result"]) != envelope["result_digest"]
    ):
        raise WorkflowError(
            "Incomplete or invalid review result envelope; publish a complete artifact."
        )
    return envelope


def submit(root, round_id, path):
    """Import supporting evidence without impersonating a runtime reviewer."""
    envelope = _read_envelope(round_id, path)
    with transaction(root):
        record = load_round(root, round_id)
        if record.get("kind") == "managed-phase-review":
            raise WorkflowError("Use the phase workflow for managed review evidence.")
        if (
            envelope["contract_id"] != record["contract_id"]
            or envelope["contributor"] not in record["contributors"]
        ):
            raise WorkflowError(
                "Supporting result belongs to a different contract or contributor."
            )
        destination = (
            round_dir(root, round_id) / "supporting" / (digest(envelope) + ".json")
        )
        atomic_json(destination, envelope)
        reference = {
            "path": destination.relative_to(Path(root).resolve()).as_posix(),
            "sha256": digest(envelope),
            "contributor": envelope["contributor"],
            "classification": "supporting-only",
            "imported_at": now(),
        }
        record.setdefault("supporting_results", []).append(reference)
        record["events"].append(
            {"type": "supporting-review-result-imported", **reference}
        )
        _inspect(root, record)
        save_round(root, record)
        return record


def _submit_runtime(root, round_id, path, execution, response):
    """Private transport endpoint after the runtime's native session returns."""
    envelope = _read_envelope(round_id, path)
    with transaction(root):
        record = load_round(root, round_id)
        if record.get("kind") == "managed-phase-review":
            raise WorkflowError(
                "Managed contributor results belong to the phase workflow."
            )
        member = envelope["contributor"]
        if (
            envelope["contract_id"] != record["contract_id"]
            or member not in record["contributors"]
        ):
            raise WorkflowError(
                "Result belongs to a different review contract or contributor."
            )
        row = record["contributors"][member]
        if row["status"] == "complete":
            raise WorkflowError(
                "Contributor already complete; late or duplicate result refused."
            )
        launch = row.get("execution", {})
        clock = record.get("managed_clock", {})
        if (
            not clock.get("active")
            or clock.get("execution_id") != execution.execution_id
            or execution.round_id != round_id
            or launch.get("execution_id") != execution.execution_id
            or launch.get("contract_id") != record["contract_id"]
            or launch.get("snapshot_digest") != digest(record["snapshot_files"])
            or row["status"] != "running"
            or response.get("review", {}).get("result") != envelope["result"]
        ):
            raise WorkflowError(
                "Runtime result lacks its active snapshot-bound execution reservation."
            )
        response_path = (
            round_dir(root, round_id) / "results" / f"{member}.execution.json"
        )
        atomic_json(response_path, response)
        row["provenance"] = {
            **launch,
            "response_path": response_path.relative_to(Path(root).resolve()).as_posix(),
            "response_digest": digest(response),
        }
        destination = round_dir(root, round_id) / "results" / f"{member}.json"
        atomic_json(destination, envelope)
        row.update(
            status="complete",
            result_path=destination.relative_to(Path(root).resolve()).as_posix(),
            artifact_digest=digest(envelope),
            completed_at=now(),
        )
        row.pop("error", None)
        record["events"].append(
            {"type": "contributor-complete", "at": now(), "contributor": member}
        )
        _inspect(root, record)
        save_round(root, record)
        return record


def fail(root, round_id, contributor, reason):
    if not reason.strip():
        raise WorkflowError("Record why the contributor failed.")
    with transaction(root):
        record = load_round(root, round_id)
        if record.get("kind") == "managed-phase-review":
            raise WorkflowError(
                "Managed contributor results belong to the phase workflow."
            )
        if contributor not in record["contributors"]:
            raise WorkflowError("Unknown contributor.")
        if record["contributors"][contributor]["status"] == "complete":
            raise WorkflowError("Contributor already complete.")
        record["contributors"][contributor].update(status="failed", error=reason)
        record["events"].append(
            {
                "type": "contributor-failed",
                "at": now(),
                "contributor": contributor,
                "reason": reason,
            }
        )
        save_round(root, record)
        return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=[
            "begin",
            "run",
            "recover",
            "extend",
            "submit",
            "status",
            "resume",
            "require-complete",
            "fail",
        ],
    )
    parser.add_argument("--root", default=".")
    parser.add_argument("--round")
    parser.add_argument(
        "--previous",
        help="Completed predecessor; retain cumulative budget and evidence",
    )
    parser.add_argument("--contributors", nargs="+")
    parser.add_argument("--code-review", nargs=2, metavar=("DETECTOR", "CHALLENGER"))
    parser.add_argument("--lens")
    parser.add_argument("--preset", default="behavioral-only")
    parser.add_argument("--lens-only", action="store_true",
                        help="Use the captured lens types without a code-domain preset")
    parser.add_argument("--min-severity", default="minor")
    parser.add_argument(
        "--instructions",
        help="File containing complete review instructions and governing guidance",
    )
    parser.add_argument("--required", nargs="*", default=[])
    parser.add_argument(
        "--scope",
        nargs="*",
        default=[],
        help="Existing user-authorized edit paths; records scope, does not grant new authority",
    )
    parser.add_argument("--result", help="Complete contribution JSON envelope")
    parser.add_argument("--contributor")
    parser.add_argument("--reason")
    parser.add_argument(
        "--rounds",
        type=int,
        default=1,
        help="Human-authorized budget extension in configured round allowances",
    )
    args = parser.parse_args()
    try:
        root = Path(args.root).resolve()
        if args.action in {"begin", "resume"}:
            if not args.instructions:
                raise WorkflowError("--instructions is required.")
            instructions = Path(args.instructions).read_text()
            config = (
                project_config(root) if (root / ".fbk/config.json").exists() else {}
            )
            if args.action == "begin":
                result = begin(
                    root,
                    args.contributors,
                    instructions,
                    config,
                    args.required,
                    previous=args.previous,
                    scope=args.scope,
                    code_review=(
                        {
                            "detector": args.code_review[0],
                            "challenger": args.code_review[1],
                            "lens": args.lens,
                            "preset": None if args.lens_only else args.preset,
                            "min_severity": args.min_severity,
                        }
                        if args.code_review
                        else None
                    ),
                )
            else:
                result = resume(root, args.round, instructions, config)
        elif args.action == "run":
            from .review_contributors import run

            result = run(root, args.round, args.contributors)
        elif args.action in {"recover", "extend"}:
            from .review_execution import recover_execution, extend_round

            if args.action == "recover":
                recover_execution(root, args.round, args.reason or "")
            else:
                extend_round(root, args.round, args.rounds, args.reason or "")
            result = status(root, args.round)
        elif args.action == "submit":
            result = submit(root, args.round, args.result)
        elif args.action == "fail":
            result = fail(root, args.round, args.contributor, args.reason or "")
        else:
            result = (
                require_complete if args.action == "require-complete" else status
            )(root, args.round)
        print(json.dumps(result, indent=2))
        if args.action == "run" and any(
            result["contributors"][m]["status"] == "failed" for m in args.contributors
        ):
            return 2
        return 0
    except (WorkflowError, OSError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
