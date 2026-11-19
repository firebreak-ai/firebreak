"""An auditable evaluation ledger; recorded judgments do not prove causality."""

import hashlib
import json
from copy import deepcopy

from . import retrospective
from .store import WorkflowError, confined, event, now


def _request(value, required, optional=()):
    if (
        not isinstance(value, dict)
        or set(value) - set(required) - set(optional)
        or set(required) - set(value)
    ):
        raise WorkflowError(f"Expected improvement fields: {', '.join(required)}.")


def _text(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 8000:
        raise WorkflowError(
            "Use a nonempty improvement statement of at most 8000 characters."
        )
    return value


def _targets(root, paths):
    if (
        not isinstance(paths, list)
        or len(paths) > 50
        or any(not isinstance(p, str) for p in paths)
        or len(set(paths)) != len(paths)
    ):
        raise WorkflowError(
            "Targets must be up to 50 distinct repository-relative file paths."
        )
    result = {}
    for path in paths:
        target = confined(root, path)
        if path.startswith((".git/", ".fbk/runtime/")) or target.name == "state.json":
            raise WorkflowError(
                "Improvement targets must be source files, not runtime records."
            )
        try:
            result[path] = (
                hashlib.sha256(target.read_bytes()).hexdigest()
                if target.exists()
                else None
            )
        except OSError as exc:
            raise WorkflowError(
                f"Cannot inspect improvement target {path}: {exc}"
            ) from exc
    return result


def _row(record, ident):
    for row in record.get("improvements", []):
        if row["id"] == ident:
            return row
    raise WorkflowError("Unknown improvement proposal; record it first.")


def record_proposal(root, record, session, request):
    retrospective.require_writer(record, session)
    _request(
        request,
        ("id", "hypothesis", "evidence", "targets", "change_kind", "change", "check"),
    )
    for key in ("id", "hypothesis", "change"):
        _text(request[key])
    if len(request["id"]) > 120:
        raise WorkflowError("Keep proposal ids within 120 characters.")
    if any(r["id"] == request["id"] for r in record.get("improvements", [])):
        raise WorkflowError("Proposal ids are immutable; record a new proposal.")
    _text(request["change_kind"])
    if request["change_kind"] not in {"add", "edit", "remove", "simplify", "no-change"}:
        raise WorkflowError("Unknown improvement change kind.")
    _request(request["check"], ("method", "success_criterion", "baseline"))
    for value in request["check"].values():
        _text(value)
    refs = retrospective.validate_references(root, record, request["evidence"])
    targets = _targets(root, request["targets"])
    if request["change_kind"] != "no-change" and not targets:
        raise WorkflowError("A change proposal needs at least one target.")
    row = {
        **deepcopy(request),
        "evidence": refs,
        "baseline_targets": targets,
        "at": now(),
        "adoptions": [],
        "evaluations": [],
        "decisions": [],
    }
    record.setdefault("improvements", []).append(row)
    event(record, "improvement-proposed", session, proposal_id=row["id"])
    return deepcopy(row)


def record_adoption(root, record, session, request):
    retrospective.require_writer(record, session)
    _request(request, ("id", "reason"))
    _text(request["reason"])
    row = _row(record, request["id"])
    if row["change_kind"] == "no-change":
        raise WorkflowError("A no-change proposal can be evaluated directly.")
    targets = _targets(root, row["targets"])
    previous = (
        row["adoptions"][-1]["targets"] if row["adoptions"] else row["baseline_targets"]
    )
    if targets == previous:
        raise WorkflowError(
            "Adoption needs an actual target change; an unchanged file is not implementation."
        )
    adoption = {
        "sequence": len(row["adoptions"]) + 1,
        "targets": targets,
        "reason": request["reason"],
        "at": now(),
    }
    row["adoptions"].append(adoption)
    event(
        record, "improvement-adopted", session, proposal_id=row["id"], adoption=adoption
    )
    return deepcopy(adoption)


def record_evaluation(root, record, session, request):
    retrospective.require_writer(record, session)
    _request(
        request, ("id", "outcome", "evidence", "comparison", "limitations", "stage")
    )
    row = _row(record, request["id"])
    _text(request["outcome"])
    _text(request["stage"])
    if request["outcome"] not in {
        "improved",
        "regressed",
        "inconclusive",
        "no-change",
    } or request["stage"] not in {"check", "followup"}:
        raise WorkflowError(
            "Use a supported evaluation outcome and stage (check or followup)."
        )
    for key in ("comparison", "limitations"):
        _text(request[key])
    if row["change_kind"] != "no-change" and not row["adoptions"]:
        raise WorkflowError(
            "Record implementation adoption before evaluating its effect."
        )
    targets = _targets(root, row["targets"])
    adoption = row["adoptions"][-1] if row["adoptions"] else None
    if adoption and targets != adoption["targets"]:
        raise WorkflowError(
            "Targets changed since adoption; record the new adoption before evaluation."
        )
    refs = retrospective.validate_references(root, record, request["evidence"])
    if row["change_kind"] != "no-change" and all(
        ref in row["evidence"] for ref in refs
    ):
        raise WorkflowError(
            "Evaluation needs new check or follow-up evidence beyond the proposal baseline."
        )
    evaluation = {
        **deepcopy(request),
        "evidence": refs,
        "targets": targets,
        "adoption": adoption["sequence"] if adoption else None,
        "at": now(),
    }
    row["evaluations"].append(evaluation)
    event(
        record,
        "improvement-evaluated",
        session,
        proposal_id=row["id"],
        evaluation=evaluation,
    )
    return deepcopy(evaluation)


def record_decision(root, record, session, request):
    retrospective.require_writer(record, session)
    _request(request, ("id", "decision", "reason"))
    _text(request["decision"])
    if request["decision"] not in {"retain", "rollback", "defer"}:
        raise WorkflowError(
            "Choose retain, rollback, or defer; this records a decision without editing files."
        )
    _text(request["reason"])
    row = _row(record, request["id"])
    decision = {**request, "at": now(), "evaluation_count": len(row["evaluations"])}
    row["decisions"].append(decision)
    event(
        record,
        "improvement-decision",
        session,
        proposal_id=row["id"],
        decision=decision,
    )
    return deepcopy(decision)


def _status(root, record, row):
    evaluations = row["evaluations"]
    status = "implemented-unverified" if row["adoptions"] else "proposed"
    if not evaluations:
        return status
    latest = evaluations[-1]
    try:
        if _targets(root, row["targets"]) != latest["targets"]:
            return "needs-re-evaluation"
        if latest["adoption"] != (
            row["adoptions"][-1]["sequence"] if row["adoptions"] else None
        ):
            return "needs-re-evaluation"
        if (
            retrospective.validate_references(root, record, latest["evidence"])
            != latest["evidence"]
        ):
            return "needs-re-evaluation"
    except WorkflowError:
        return "needs-re-evaluation"
    return "evaluated-" + latest["outcome"]


def report(root, record, index=None):
    rows = record.get("improvements", [])
    if index is not None:
        if type(index) is not int or index < 1 or index > len(rows):
            raise WorkflowError("Improvement index is out of range.")
        return {
            **deepcopy(rows[index - 1]),
            "status": _status(root, record, rows[index - 1]),
            "proof_boundary": "Outcomes are recorded assessments; evidence binding does not establish empirical causality.",
        }
    result = {
        "unit": record["unit"][:120],
        "total": len(rows),
        "items": [
            {
                "index": i,
                "id": r["id"],
                "status": _status(root, record, r),
                "change_kind": r["change_kind"],
                "evaluations": len(r["evaluations"]),
            }
            for i, r in enumerate(rows[-20:], start=max(1, len(rows) - 19))
        ],
        "omitted": max(0, len(rows) - 20),
        "retrieve": "improvement-report <unit> --index N (one-based)",
        "proof_boundary": "Implemented changes and evaluated outcomes are separate; schema checks do not establish causality.",
    }
    while len(json.dumps(result, ensure_ascii=False)) > 12000 and result["items"]:
        result["items"].pop(0)
        result["omitted"] += 1
    return result
