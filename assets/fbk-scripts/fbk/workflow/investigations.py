"""Durable experimental assignments; host permissions remain the security boundary.

Reservations charge the whole available time before spawning. A transport crash
therefore cannot replenish a budget. Commands run outside the project lock.
"""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

from .review import run_command
from .store import (
    WorkflowError,
    atomic_json,
    confined,
    digest,
    now,
    project_config,
    read_json,
    transaction,
)


def _load(root, round_id):
    from .review_rounds import load_round

    return load_round(root, round_id)


def _save(root, record):
    from .review_rounds import save_round

    save_round(root, record)


def _positive(config, key, default):
    value = config.get(key, default)
    if type(value) is not int or value <= 0:
        raise WorkflowError(f"{key} must be a positive integer.")
    return value


def start(root, round_id, request):
    identifier = request.get("id", "")
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", identifier):
        raise WorkflowError(
            "Investigation id must contain 1–80 letters, digits, underscores or hyphens."
        )
    if not request.get("question") or not request.get("requirements"):
        raise WorkflowError("Supply a concrete question and relevant requirements.")
    with transaction(root):
        record = _load(root, round_id)
        if record.get("superseded_by"):
            raise WorkflowError("Review round is superseded; use its successor.")
        entries = record.setdefault("investigations", {})
        if identifier in entries:
            raise WorkflowError(
                "Investigation already exists; resume its durable budget."
            )
        if needs_human_review(record):
            raise WorkflowError(
                "Investigation requires human disposition before starting another."
            )
        config = (
            record["configuration"]
            if "configuration" in record
            else project_config(root)
        )
        result = {
            "id": identifier,
            "question": request["question"],
            "requirements": request["requirements"],
            "contract_id": record["contract_id"],
            "attempt_limit": _positive(config, "investigation_max_attempts", 3),
            "seconds_limit": _positive(config, "investigation_timeout", 600),
            "spent_seconds": 0,
            "attempts": [],
            "authorizations": [],
            "created_at": now(),
        }
        entries[identifier] = result
        _save(root, record)
        return result


def status(root, round_id, identifier):
    with transaction(root):
        return _entry(_load(root, round_id), identifier)


def _entry(record, identifier):
    try:
        return record["investigations"][identifier]
    except KeyError as exc:
        raise WorkflowError(f"Unknown investigation: {identifier}") from exc


PER_QUESTION_LIMITS = frozenset({"attempts", "time"})


def exhausted_question(entry):
    """One question hit its own attempt or time limit: a caveat, not a stop.

    The entry keeps its ``human_review`` record because it cannot be retried
    without a human, but the reader carries on and finishes without the answer.
    """
    return entry.get("human_review", {}).get("limit") in PER_QUESTION_LIMITS


def needs_human_review(record):
    """Escalations that stop the round: the review clock and interrupted work."""
    return any(
        entry.get("human_review") and not exhausted_question(entry)
        for entry in record.get("investigations", {}).values()
    )


def _escalate(record, entry, limit):
    detail = {
        "limit": limit,
        "question": entry["question"],
        "at": now(),
        "evidence": [a["workspace"] for a in entry["attempts"] if a.get("workspace")],
    }
    entry["human_review"] = detail
    record["investigation_human_review"] = detail
    record.setdefault("events", []).append(
        {
            "type": "investigation-human-review-required",
            "investigation": entry["id"],
            **detail,
        }
    )


class InvestigationRefused(WorkflowError):
    """Declared external check lacks authorization; recorded as evidence, never launched."""


def _authorization(root, entry, request):
    external = request.get("external")
    if external is None:
        return
    if (
        not isinstance(external, dict)
        or not external.get("target")
        or not external.get("effects")
    ):
        # constraint: external-shape
        raise InvestigationRefused(
            "External checks require target and permitted effects authorization."
        )
    grant = request.get("authorization")
    if grant:
        source = grant.get("source", {})
        try:
            text = confined(root, source.get("path", "")).read_text()
        except (OSError, WorkflowError):
            text = ""
        if not source.get("quote") or source["quote"] not in text:
            # constraint: authorization-grant-quote
            raise InvestigationRefused(
                "External authorization needs a verifiable source quotation."
            )
        if grant.get("target") != external["target"] or not set(
            external["effects"]
        ).issubset(grant.get("effects", [])):
            # constraint: authorization-grant-covers
            raise InvestigationRefused(
                "External authorization does not cover target and effects."
            )
        entry["authorizations"].append(grant)
    if not any(
        g.get("target") == external["target"]
        and set(external["effects"]).issubset(g.get("effects", []))
        for g in entry["authorizations"]
    ):
        # constraint: authorization-refusal
        raise InvestigationRefused(
            "External check requires existing explicit authorization for target and effects."
        )


def _refuse(record, entry, identifier, request, reason):
    """Keep the refusal as evidence: no launch, no time charged, one attempt spent."""
    # constraint: authorization-refusal
    index = len(entry["attempts"]) + 1
    entry.pop("resolution", None)
    entry["attempts"].append(
        {
            "status": "refused",
            "contract_id": record["contract_id"],
            # Identity without command text or authorization quotations, as for corrections.
            "request_digest": digest(request),
            "request_fields": sorted(request) if isinstance(request, dict) else [],
            "reserved_seconds": 0,
            "started_at": now(),
            "finished_at": now(),
            "result": {"error": reason, "seconds": 0, "refused": True},
        }
    )
    record.setdefault("events", []).append(
        {
            "type": "investigation-refused",
            "investigation": identifier,
            "attempt": index,
            "reason": reason,
            "at": now(),
        }
    )
    if len(entry["attempts"]) >= entry["attempt_limit"]:
        _escalate(record, entry, "attempts")


class InvestigationRequestError(WorkflowError):
    """Malformed declaration, before any experiment is reserved or launched."""


def validate_request(request, *, managed=False):
    def nonempty(value):
        return isinstance(value, str) and bool(value.strip())

    def strings(value):
        return (
            isinstance(value, list) and bool(value) and all(nonempty(v) for v in value)
        )

    if not isinstance(request, dict):
        # constraint: investigation-fields
        raise InvestigationRequestError(
            "Investigation request must be an object; supply named fields."
        )
    if managed:
        allowed = {
            "id",
            "question",
            "requirements",
            "mode",
            "argv",
            "prompt",
            "exploratory",
            "modifies_code",
            "external",
            "authorization",
        }
        if set(request) - allowed:
            # constraint: investigation-fields
            raise InvestigationRequestError(
                "Investigation request contains unknown fields; use the supplied request schema."
            )
        if not isinstance(request.get("id"), str) or not re.fullmatch(
            r"[a-zA-Z0-9_-]{1,67}", request["id"]
        ):
            # constraint: investigation-id
            raise InvestigationRequestError(
                "Investigation id must contain 1–67 letters, digits, underscores or hyphens (the runtime adds a reader prefix)."
            )
        if not nonempty(request.get("question")) or not strings(
            request.get("requirements")
        ):
            # constraint: investigation-question
            raise InvestigationRequestError(
                "Supply a nonempty question and requirements as a nonempty list of reference strings."
            )
    if managed and "prompt" in request and not isinstance(request["prompt"], str):
        # constraint: investigation-mode-delegated
        raise InvestigationRequestError("Investigation prompt must be a string.")
    for flag in ("exploratory", "modifies_code"):
        if flag in request and type(request[flag]) is not bool:
            # constraint: investigation-flags
            raise InvestigationRequestError(f"{flag} must be a JSON boolean.")
    for field in ("external", "authorization"):
        value = request.get(field)
        if value is None:
            continue
        allowed = {"target", "effects"} | (
            {"source"} if field == "authorization" else set()
        )
        if (
            not isinstance(value, dict)
            or set(value) - allowed
            or not nonempty(value.get("target"))
            or not strings(value.get("effects"))
        ):
            # constraint: external-shape
            raise InvestigationRequestError(
                f"{field} requires a nonempty target string and effects as a nonempty list of strings. Preserve the intended target and effects; do not remove external effects to bypass authorization."
            )
        if field == "authorization":
            source = value.get("source")
            if (
                not isinstance(source, dict)
                or set(source) != {"path", "quote"}
                or not all(nonempty(source[k]) for k in ("path", "quote"))
            ):
                # constraint: external-shape
                raise InvestigationRequestError(
                    "authorization.source requires nonempty path and quote strings identifying existing operator authorization; never invent permission."
                )
    argv = request.get("argv")
    mode = request.get("mode")
    if mode not in {"direct", "delegated"}:
        # constraint: investigation-mode
        raise InvestigationRequestError("Assignment mode must be direct or delegated.")
    if mode == "direct" and (
        not isinstance(argv, list)
        or not argv
        or not all(isinstance(a, str) and a for a in argv)
    ):
        # constraint: investigation-mode-direct
        raise InvestigationRequestError("Supply a nonempty argv list.")
    if mode == "delegated" and (
        argv is not None
        or not isinstance(request.get("prompt"), str)
        or not request["prompt"].strip()
    ):
        # constraint: investigation-mode-delegated
        raise InvestigationRequestError(
            "Delegated assignments require a prompt; Firebreak launches the fresh worker, not caller argv."
        )
    if (
        request.get("exploratory") or request.get("modifies_code")
    ) and mode != "delegated":
        # constraint: investigation-flags
        raise InvestigationRequestError(
            "Exploratory or code-changing experiments must be delegated to a fresh worker."
        )


def run(root, round_id, identifier, request, *, purpose="investigation"):
    if purpose not in {"investigation", "independent-verification"}:
        raise WorkflowError("Unknown experimental worker purpose.")
    validate_request(request)
    argv = request.get("argv")
    mode = request.get("mode")
    with transaction(root):
        record = _load(root, round_id)
        if record.get("superseded_by"):
            raise WorkflowError("Review round is superseded; use its successor.")
        entry = _entry(record, identifier)
        if entry.get("disposition", {}).get("disposition") == "stop":
            raise WorkflowError("This investigation was stopped by human disposition.")
        active = any(
            a["status"] == "running"
            for e in record["investigations"].values()
            for a in e["attempts"]
        )
        if entry.get("human_review") or needs_human_review(record) or active:
            if active:
                _escalate(record, entry, "interrupted-or-active-assignment")
                _save(root, record)
            raise WorkflowError(
                "Investigation requires human review; an active assignment must finish or be reconciled."
            )
        remaining = record["budget"]["seconds"] - record["budget"]["spent_seconds"]
        limit = (
            "attempts"
            if len(entry["attempts"]) >= entry["attempt_limit"]
            else "review-time"
            if remaining <= 0
            else "time"
            if entry["spent_seconds"] >= entry["seconds_limit"]
            else None
        )
        if limit:
            _escalate(record, entry, limit)
            _save(root, record)
            # constraint: investigation-budgets
            raise WorkflowError(
                f"Investigation budget exhausted ({limit}); human help is required."
            )
        try:
            _authorization(root, entry, request)
        except InvestigationRefused as exc:
            _refuse(record, entry, identifier, request, str(exc))
            _save(root, record)
            exc.entry = entry
            raise
        # constraint: worker-limits
        timeout = min(remaining, entry["seconds_limit"] - entry["spent_seconds"])
        index = len(entry["attempts"]) + 1
        relative = f".fbk/runtime/investigations/{record['id']}/{identifier}/{index}"
        workspace = confined(root, relative)
        # No symlinks: copying a snapshot must not follow paths back into the deliverable.
        snapshot = confined(root, record["snapshot_path"])
        if any(p.is_symlink() for p in snapshot.rglob("*")):
            raise WorkflowError(
                "Experiment snapshot contains symlinks; use regular snapshot files."
            )
        shutil.copytree(snapshot, workspace)
        packet = {
            "question": entry["question"],
            "requirements": entry["requirements"],
            "contract_id": record["contract_id"],
            "mode": mode,
            "purpose": purpose,
            "request": request,
            "constraints": [
                "Experimental workspace only; no deliverable writes.",
                "Use only authorized external targets/effects.",
                "Return reproducible evidence and limitations; helper is not independent verification."
                if purpose == "investigation"
                else "You are the fresh independent verifier. Independently assess the remediation and tests; do not trust remediator claims.",
            ],
        }
        prompt = None
        if mode == "delegated":
            config = (
                record["configuration"]
                if "configuration" in record
                else project_config(root)
            )
            turns = _positive(config, "reviewer_max_turns", 100)
            worker_tools = "Read,Glob,Grep,Bash,Write,Edit,WebFetch,WebSearch"
            argv = [
                "claude",
                "-p",
                "--output-format",
                "json",
                "--tools",
                worker_tools,
                "--allowedTools",
                worker_tools,
                "--permission-mode",
                "dontAsk",
                "--strict-mcp-config",
                "--mcp-config",
                '{"mcpServers":{}}',
                "--settings",
                '{"disableAllHooks":true}',
                "--setting-sources",
                "",
                "--max-turns",
                str(turns),
                "--no-session-persistence",
            ]
            prompt = (
                json.dumps(packet, indent=2)
                + "\nExecute only this assignment. Read investigation-assignment.json. Do not spawn additional workers. "
                + request["prompt"]
            )
        atomic_json(workspace / "investigation-assignment.json", packet)
        attempt = {
            "status": "running",
            "workspace": relative,
            "contract_id": record["contract_id"],
            "request": request,
            "reserved_seconds": timeout,
            "started_at": now(),
        }
        entry.pop("resolution", None)
        entry["attempts"].append(attempt)
        entry["spent_seconds"] += timeout
        record["budget"]["spent_seconds"] += timeout
        record.setdefault("events", []).append(
            {
                "type": "investigation-assignment-started",
                "investigation": identifier,
                "attempt": index,
                "reserved_seconds": timeout,
                "at": now(),
            }
        )
        _save(root, record)
    failure = None
    try:
        result = (
            run_command(argv, workspace, timeout, prompt)
            if prompt is not None
            else run_command(argv, workspace, timeout)
        )
    except WorkflowError as exc:
        failure = exc
        result = dict(getattr(exc, "diagnostics", {}))
        result.setdefault("seconds", timeout)
        result["error"] = str(exc)
    if mode == "delegated":
        try:
            host = json.loads(result.get("stdout", ""))
        except (ValueError, TypeError):
            host = {}
        complete = (
            isinstance(host, dict)
            and host.get("subtype") == "success"
            and not host.get("is_error")
            and not result.get("stdout_omitted_bytes")
            and (
                isinstance(host.get("result"), str)
                or isinstance(host.get("structured_output"), dict)
            )
        )
        result["native_completion"] = "completed" if complete else "failed"
        if isinstance(host, dict):
            # Keep the host's subtype (for example error_max_turns) so a failed
            # attempt stays diagnosable without re-parsing stdout.
            result["native_subtype"] = host.get("subtype")
            result["usage"] = host.get("modelUsage", host.get("usage"))
            result["reported_cost_usd"] = host.get("total_cost_usd")
    with transaction(root):
        record = _load(root, round_id)
        if record.get("superseded_by"):
            raise WorkflowError("Review round is superseded; use its successor.")
        entry = _entry(record, identifier)
        attempt = entry["attempts"][index - 1]
        elapsed = min(timeout, max(0, result.get("seconds", timeout)))
        entry["spent_seconds"] -= timeout - elapsed
        record["budget"]["spent_seconds"] -= timeout - elapsed
        attempt.update(
            status="failed"
            if failure
            or result.get("exit_code") != 0
            or result.get("native_completion") == "failed"
            else "completed",
            result=result,
            finished_at=now(),
        )
        atomic_json(workspace / "investigation-result.json", result)
        # A worker that reaches its turn ceiling is a failed attempt like any other;
        # the attempt and time budgets below decide whether to escalate.
        record.setdefault("events", []).append(
            {
                "type": "investigation-assignment-finished",
                "investigation": identifier,
                "attempt": index,
                "seconds": elapsed,
                "status": attempt["status"],
                "at": now(),
            }
        )
        limit = (
            "review-time"
            if record["budget"]["spent_seconds"] >= record["budget"]["seconds"]
            else "time"
            if entry["spent_seconds"] >= entry["seconds_limit"]
            else "attempts"
            if len(entry["attempts"]) >= entry["attempt_limit"]
            else None
        )
        if limit:
            _escalate(record, entry, limit)
        _save(root, record)
    return entry


def conclude(root, round_id, identifier, request):
    """Record the reviewing agent's interpretation, separately from command success."""
    with transaction(root):
        record = _load(root, round_id)
        if record.get("superseded_by"):
            raise WorkflowError("Review round is superseded; use its successor.")
        entry = _entry(record, identifier)
        indices = request.get("attempts")
        if (
            not request.get("conclusion")
            or not isinstance(indices, list)
            or not indices
        ):
            raise WorkflowError(
                "Resolution needs an explicit conclusion and attempt evidence."
            )
        for index in indices:
            if type(index) is not int or index < 1 or index > len(entry["attempts"]):
                raise WorkflowError("Resolution cites unavailable attempt evidence.")
            attempt = entry["attempts"][index - 1]
            if attempt["status"] not in {
                "completed",
                "failed",
                "refused",
            } or not attempt.get("result"):
                raise WorkflowError("Resolution needs completed execution evidence.")
        if entry.get("human_review") and not exhausted_question(entry):
            raise WorkflowError(
                "Human disposition is required before resolving exhausted investigation."
            )
        entry["resolution"] = {**request, "at": now()}
        record.setdefault("events", []).append(
            {
                "type": "investigation-resolved",
                "investigation": identifier,
                **entry["resolution"],
            }
        )
        _save(root, record)
        return entry


def resolve(root, round_id, identifier, request):
    """Record a sourced human disposition; never infer approval from elapsed time."""
    source = request.get("source", {})
    try:
        text = confined(root, source.get("path", "")).read_text()
    except (OSError, WorkflowError):
        text = ""
    if not source.get("quote") or source["quote"] not in text:
        raise WorkflowError("Human disposition needs a verifiable source quotation.")
    if request.get("disposition") not in {"stop", "extend"} or not request.get(
        "reason"
    ):
        raise WorkflowError("Human disposition requires stop or extend and a reason.")
    with transaction(root):
        record = _load(root, round_id)
        if record.get("superseded_by"):
            raise WorkflowError("Review round is superseded; use its successor.")
        entry = _entry(record, identifier)
        active = [a for a in entry["attempts"] if a["status"] == "running"]
        if active and request.get("confirm_stopped") is not True:
            raise WorkflowError(
                "Confirm the interrupted process group has stopped before recovery."
            )
        if request["disposition"] == "extend":
            attempts = _positive(request, "additional_attempts", None)
            seconds = _positive(request, "additional_seconds", None)
            entry["attempt_limit"] += attempts
            entry["seconds_limit"] += seconds
            review_seconds = request.get("additional_review_seconds", 0)
            if type(review_seconds) is not int or review_seconds < 0:
                raise WorkflowError(
                    "additional_review_seconds must be a nonnegative integer."
                )
            record["budget"]["seconds"] += review_seconds
        for attempt in active:
            attempt.update(status="interrupted", finished_at=now())
        entry["disposition"] = {**request, "at": now()}
        entry.setdefault("dispositions", []).append(entry["disposition"])
        entry.pop("human_review", None)
        unresolved = [
            e["human_review"]
            for e in record["investigations"].values()
            if e.get("human_review")
        ]
        if unresolved:
            record["investigation_human_review"] = unresolved[0]
        else:
            record.pop("investigation_human_review", None)
        record.setdefault("events", []).append(
            {
                "type": "investigation-human-disposition",
                "investigation": identifier,
                **entry["disposition"],
            }
        )
        _save(root, record)
        return entry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=["start", "run", "status", "resolve", "conclude"]
    )
    parser.add_argument("--root", required=True)
    parser.add_argument("--round", required=True)
    parser.add_argument("--id")
    parser.add_argument("--request", help="JSON assignment request path")
    args = parser.parse_args()
    try:
        root = Path(args.root).resolve()
        if args.action == "start":
            result = start(root, args.round, read_json(args.request))
        elif args.action == "run":
            result = run(root, args.round, args.id, read_json(args.request))
        elif args.action == "conclude":
            result = conclude(root, args.round, args.id, read_json(args.request))
        elif args.action == "resolve":
            result = resolve(root, args.round, args.id, read_json(args.request))
        else:
            result = status(root, args.round, args.id)
        print(json.dumps(result, indent=2))
        return 0
    except (WorkflowError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
