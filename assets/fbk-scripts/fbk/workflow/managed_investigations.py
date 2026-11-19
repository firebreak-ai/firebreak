"""Managed reviewer request/continuation protocol for executable investigations."""

import json
import shutil
from pathlib import Path

from . import investigations, review_execution
from .store import WorkflowError, confined, digest, now, readable, transaction


REQUEST_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string", "pattern": "^[a-zA-Z0-9_-]{1,67}$"},
        "question": {"type": "string", "pattern": r"\S"},
        "requirements": {
            "type": "array", "minItems": 1,
            "items": {"type": "string", "pattern": r"\S"},
        },
        "mode": {"enum": ["direct", "delegated"]},
        "argv": {
            "type": ["array", "null"], "minItems": 1,
            "items": {"type": "string", "minLength": 1},
        },
        "prompt": {"type": "string"},
        "exploratory": {"type": "boolean"},
        "modifies_code": {"type": "boolean"},
        "external": {
            "type": ["object", "null"],
            "properties": {
                "target": {"type": "string", "pattern": r"\S"},
                "effects": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"type": "string", "pattern": r"\S"},
                },
            },
            "required": ["target", "effects"],
            "additionalProperties": False,
        },
        "authorization": {
            "type": ["object", "null"],
            "properties": {
                "target": {"type": "string", "pattern": r"\S"},
                "effects": {
                    "type": "array", "minItems": 1,
                    "items": {"type": "string", "pattern": r"\S"},
                },
                "source": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "pattern": r"\S"},
                        "quote": {"type": "string", "pattern": r"\S"},
                    },
                    "required": ["path", "quote"],
                    "additionalProperties": False,
                },
            },
            "required": ["target", "effects", "source"],
            "additionalProperties": False,
        },
    },
    # This schema sits under the flat native schema's investigation property; nested unions are supported.
    "anyOf": [
        {
            "properties": {
                "mode": {"enum": ["direct"]},
                "argv": {"type": "array"},
                "exploratory": {"enum": [False]},
                "modifies_code": {"enum": [False]},
            },
            "required": ["argv"],
        },
        {
            "properties": {
                "mode": {"enum": ["delegated"]},
                "argv": {"type": "null"},
                "prompt": {"type": "string", "pattern": r"\S"},
            },
            "required": ["prompt"],
        },
    ],
    "required": ["id", "question", "requirements", "mode"],
    "additionalProperties": False,
}


def managed_round_id(unit, phase, identity):
    """A managed round's id and folder name: its unit and phase, so an operator can match
    the folder, then the digest of everything the review depends on. The label never starts
    or ends with ".", "_" or "-", so the id cannot be read as a command-line option."""
    code = digest({"managed-review": identity})[:32]
    label = "-".join(part for part in (readable(unit).strip("-._"), phase) if part)
    return f"{label}-{code}" if label else code


def open_round(root, sources, config, identity, unit="", phase=""):
    """One durable active-wall clock, shared by all concurrent Council readers."""
    from .review import bounded_number

    # The round clock is the wall-clock safety net for the whole managed round and is
    # independent of the per-session review_timeout, which governs one subprocess.
    seconds = bounded_number(config, "review_round_timeout", 9999, 86400)
    round_id = managed_round_id(unit, phase, identity)
    root = Path(root)
    with transaction(root):
        try:
            record = investigations._load(root, round_id)
        except WorkflowError:
            directory = confined(root, f".fbk/runtime/review-rounds/{round_id}")
            if directory.exists():
                raise
            directory.mkdir(parents=True)
            shutil.copytree(sources, directory / "sources")
            record = {
                "id": round_id,
                "kind": "managed-phase-review",
                "contract_id": identity,
                "configuration": {
                    k: v for k, v in config.items() if not k.startswith("_")
                },
                "snapshot_path": (directory / "sources").relative_to(root).as_posix(),
                "budget": {"seconds": seconds, "spent_seconds": 0},
                "investigations": {},
                "events": [],
                "managed_clock": {
                    "worker_seconds": 0,
                    "worker_usage": [],
                    "created_at": now(),
                    "human_wait_seconds": 0,
                },
            }
        review_execution.activate_record(root, record)
    return review_execution.RoundExecution(root, record)


def _evidence_prompt(original, execution, reader_root, evidence, config):
    if not evidence:
        return original
    packet = []
    manifests = []
    for identifier, entry in evidence.items():
        manifests.append(
            expose_evidence(execution.root, reader_root, identifier, entry, config)
        )
        attempts = []
        for attempt in entry["attempts"]:
            if attempt.get("status") == "refused":
                attempts.append(
                    {
                        "status": "refused",
                        "reason": attempt["result"]["error"],
                        "note": "Not authorized; no command was run. Proceed without "
                        "this evidence, or report the question as unresolved in your review.",
                    }
                )
                continue
            if not attempt.get("result"):
                raise WorkflowError(
                    "Unresolved investigation execution requires recovery before review continuation."
                )
            result = attempt["result"]
            attempts.append(
                {
                    "workspace": attempt["workspace"],
                    "result": {
                        **result,
                        "stdout": result.get("stdout", "")[-12000:],
                        "stderr": result.get("stderr", "")[-4000:],
                        "continuation_stdout_omitted_chars": max(
                            0, len(result.get("stdout", "")) - 12000
                        ),
                    },
                }
            )
        item = {
            "id": identifier,
            "question": entry["question"],
            "attempts": attempts,
            "human_disposition": entry.get("disposition"),
        }
        if investigations.exhausted_question(entry):
            item["exhausted"] = {
                "limit": entry["human_review"]["limit"],
                "attempts": len(entry["attempts"]),
                "note": "This investigation reached its "
                + entry["human_review"]["limit"]
                + " limit; no further attempts are possible in this round. Proceed "
                "without this evidence or report the question as unresolved in your review.",
            }
        packet.append(item)
    return (
        original
        + "\nInvestigation evidence (interpret actual observations and limitations before the final verdict):\n"
        + json.dumps(packet)
        + "\nFull reproducible evidence, including omitted output and experimental files, is available inside this snapshot at "
        + json.dumps(manifests)
        + ". Inspect it when excerpts are insufficient."
    )


def require_resolved(execution):
    """A clean verdict cannot erase questions left open by interrupted readers."""
    with transaction(execution.root):
        record = investigations._load(execution.root, execution.round_id)
        pending = [
            identifier
            for identifier, entry in record["investigations"].items()
            if not entry.get("resolution")
            and entry.get("disposition", {}).get("disposition") != "stop"
        ]
        if pending or investigations.needs_human_review(record):
            raise WorkflowError(
                "Unresolved investigation questions prevent review completion: "
                + ", ".join(pending)
            )


def _correction(execution, reader_key, error, request=None):
    """Spend one durable protocol correction, never an extra review round."""
    details = {
        "category": "investigation-request-validation"
        if isinstance(error, investigations.InvestigationRequestError)
        else "inspection-declaration-validation",
        "message": str(error),
        "at": now(),
    }
    if request is not None:
        # Preserve identity without retaining arbitrary command text or authorization quotes.
        details["request_digest"] = digest(request)
        details["request_fields"] = sorted(request) if isinstance(request, dict) else []
    missing = getattr(error, "inspection_missing_paths", None)
    if missing:
        details["missing_inspection_paths"] = missing
    unknown = getattr(error, "inspection_unknown_paths", None)
    if unknown:
        details["unknown_inspection_paths"] = unknown
    with transaction(execution.root):
        record = investigations._load(execution.root, execution.round_id)
        corrections = record.setdefault("reader_corrections", {})
        prior = corrections.setdefault(reader_key, [])
        if prior:
            error.args = (
                str(error) + " This reader's one protocol correction for this round "
                "has already been used; automatic continuation stopped. Inspect the "
                "saved review diagnostics and correct the cause before any authorized retry.",
            )
            error.diagnostics = {
                **getattr(error, "diagnostics", {}),
                **details,
                "investigation_round": execution.round_id,
                "protocol_correction_exhausted": True,
            }
            # constraint: protocol-correction
            raise error
        prior.append(details)
        investigations._save(execution.root, record)
    return (
        "\nProtocol correction (the one correction allowed for this reader in this round; "
        "the original round clock still applies): "
        + str(error)
        + " Correct the reported declaration using the supplied schema and actual source reads. "
        "Do not invent inspected files, observations, or authorization. "
        "A timeout, exhausted turn budget, or missing operator authorization is not eligible for this correction."
    )


def run_reader(root, prompt, config, session, *, schema, validator):
    import re

    execution = config["_managed_execution"]
    # Verification evidence filenames are transport locations, not reader identity.
    stable_prompt = re.sub(
        r"\.review-verification-[^/\"\s]+", ".review-verification", prompt
    )
    reader_key = digest({"prompt": stable_prompt, "schema": schema})[:12]
    original = prompt
    responses = []
    with transaction(execution.root):
        record = investigations._load(execution.root, execution.round_id)
        evidence = {
            identifier: entry
            for identifier, entry in record["investigations"].items()
            if identifier.startswith(reader_key + "-")
        }
    prompt = _evidence_prompt(original, execution, root, evidence, config)
    repeated = {}
    while True:
        remaining = execution.remaining()
        try:
            response = session(
                root,
                prompt,
                {
                    **config,
                    "review_timeout": min(config.get("review_timeout", 1200), remaining),
                },
                schema=schema,
                validator=validator,
            )
        except WorkflowError as exc:
            exc.diagnostics = {
                **getattr(exc, "diagnostics", {}),
                "investigation_round": execution.round_id,
            }
            execution.record_worker(exc.diagnostics)
            if exc.diagnostics.get("category") == "timeout":
                # A session cut short by the shared round clock is that clock's
                # exhaustion, which pauses for human help; a session that reached its
                # own review_timeout is an ordinary failed attempt.
                execution.remaining()
            if getattr(exc, "inspection_missing_paths", None) or getattr(
                exc, "inspection_unknown_paths", None
            ):
                responses.append(exc.diagnostics)
                prompt = _evidence_prompt(
                    original, execution, root, evidence, config
                ) + _correction(execution, reader_key, exc)
                continue
            raise
        responses.append(response)
        execution.record_worker(response)
        if "investigation" not in response:
            for identifier, entry in evidence.items():
                if entry.get("disposition", {}).get("disposition") == "stop":
                    continue
                investigations.conclude(
                    execution.root,
                    execution.round_id,
                    identifier,
                    {
                        "conclusion": json.dumps(response["review"]),
                        "attempts": list(range(1, len(entry["attempts"]) + 1)),
                    },
                )
            response["investigation_round"] = execution.round_id
            response["investigations"] = list(evidence)
            response["seconds"] = sum(r.get("seconds", 0) for r in responses)
            response["continuation_usage"] = [r.get("usage") for r in responses]
            return response
        request = response["investigation"]
        identifier = reader_key + "-" + str(
            request.get("id", "") if isinstance(request, dict) else ""
        )
        if identifier in evidence and investigations.exhausted_question(
            evidence[identifier]
        ):
            # The same unresolved evidence comes back once for free; a reader that
            # ignores the exhausted note twice is looping, and the session stops.
            repeated[identifier] = repeated.get(identifier, 0) + 1
            if repeated[identifier] > 1:
                error = WorkflowError(
                    "Reader requested exhausted investigation "
                    + identifier
                    + " twice after being told no further attempts are possible; "
                    "automatic continuation stopped. Finish the review without it."
                )
                error.diagnostics = {
                    "investigation_round": execution.round_id,
                    "exhausted_question_repeated": identifier,
                    "reader_responses": _responses_summary(responses, request),
                }
                # constraint: exhausted-question-repeat
                raise error
            prompt = _evidence_prompt(original, execution, root, evidence, config)
            continue
        try:
            identifier, entry = execution.investigate(request, reader_key)
        except investigations.InvestigationRequestError as exc:
            prompt = _evidence_prompt(
                original, execution, root, evidence, config
            ) + _correction(execution, reader_key, exc, request)
            continue
        except investigations.InvestigationRefused as exc:
            # An unanswered question is a caveat in the review, not a dead reader.
            evidence[exc.identifier] = exc.entry
            prompt = _evidence_prompt(original, execution, root, evidence, config)
            continue
        except WorkflowError as exc:
            exc.diagnostics = {
                **getattr(exc, "diagnostics", {}),
                "investigation_round": execution.round_id,
                "reader_responses": _responses_summary(responses, request),
            }
            execution.record_worker(exc.diagnostics)
            raise
        evidence[identifier] = entry
        prompt = _evidence_prompt(original, execution, root, evidence, config)


def _responses_summary(responses, request):
    """What the reader had said before it died, kept off the top-level clock fields."""
    return {
        "count": len(responses),
        "seconds": sum(r.get("seconds", 0) for r in responses),
        "usage": [r.get("usage") for r in responses],
        "last_investigation_request_digest": digest(request),
        "last_investigation_request_fields": sorted(request)
        if isinstance(request, dict)
        else [],
    }


def expose_evidence(live_root, reader_root, identifier, entry, config):
    """Make full experiment artifacts readable by the restricted reviewer host."""
    import hashlib
    from .store import atomic_json

    prefix = f".review-investigations/{identifier}"
    files = []
    for index, attempt in enumerate(entry["attempts"], 1):
        if not attempt.get("workspace"):
            continue  # A refused attempt launched nothing and has no files.
        source = confined(live_root, attempt["workspace"])
        for path in sorted(source.rglob("*")):
            if path.is_symlink() or not path.is_file():
                continue
            relative = f"{prefix}/{index}/{path.relative_to(source).as_posix()}"
            target = confined(reader_root, relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())
            checksum = hashlib.sha256(target.read_bytes()).hexdigest()
            config["_review_available_files"][relative] = checksum
            files.append(
                {
                    "path": relative,
                    "sha256": checksum,
                    "origin": path.relative_to(live_root).as_posix(),
                }
            )
    manifest_path = f"{prefix}/manifest.json"
    atomic_json(confined(reader_root, manifest_path), {"files": files})
    config["_review_available_files"][manifest_path] = digest(files)
    return manifest_path
