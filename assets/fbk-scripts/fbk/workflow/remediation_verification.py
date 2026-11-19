"""Declared fix obligations, checked by a fresh bounded independent verifier."""

import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path

from . import investigations, review, review_rounds
from .store import WorkflowError, confined, digest, now, read_json, transaction


def _paths(root, values, label):
    if (
        not isinstance(values, list)
        or not values
        or any(not isinstance(p, str) or not p for p in values)
    ):
        raise WorkflowError(f"Declare concrete {label} paths.")
    for path in values:
        confined(root, path)
        if Path(path).parts[0] == ".fbk":
            raise WorkflowError(
                "Remediation scope cannot include workflow runtime state."
            )
    return sorted(set(values))


def _declaration(root, origin, request):
    identifier = request.get("id", "")
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,60}", identifier):
        raise WorkflowError(
            "Use a stable remediation id of 1–60 letters, digits, underscores or hyphens."
        )
    if not request.get("behavior") or not request.get("requirements"):
        raise WorkflowError("Declare accepted behavior and governing requirements.")
    scope = _paths(root, request.get("scope"), "authorized scope")
    siblings = _paths(root, request.get("siblings"), "known sibling")
    reference = request.get("finding", {})
    try:
        contributor = origin["contributors"][reference["contributor"]]
        if contributor["status"] != "complete":
            raise ValueError
        results = read_json(confined(root, contributor["result_path"]))["result"]
        if isinstance(results, dict):
            results = results["findings"]
        index = reference["index"]
        if type(index) is not int or index < 0:
            raise ValueError
        finding = results[index]
        if not isinstance(finding, dict) or finding.get("status") not in {
            "verified",
            "confirmed",
        }:
            raise ValueError
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise WorkflowError(
            "Reference a verified finding in a completed contributor artifact."
        ) from exc
    return {
        **copy.deepcopy(request),
        "scope": scope,
        "siblings": siblings,
        "finding_digest": digest(finding),
        "finding_evidence": copy.deepcopy(finding),
        "declared_round": origin["id"],
        "declared_contract": origin["contract_id"],
        "declared_at": now(),
        "status": "declared",
    }


def declare(root, round_id, request):
    """Register existing authorization; this does not grant new scope or effects."""
    review_rounds.require_complete(root, round_id)
    with transaction(root):
        record = review_rounds._inspect(root, review_rounds.load_round(root, round_id))
        if not record["remediation_allowed"]:
            raise WorkflowError(
                "Review changed before remediation declaration; refresh it."
            )
        result = _declaration(root, record, request)
        identifier = result["id"]
        entries = record.setdefault("remediations", {})
        if identifier in entries:
            raise WorkflowError(
                "Remediation already declared; preserve its verification obligation."
            )
        entries[identifier] = result
        record["events"].append(
            {
                "type": "material-remediation-declared",
                "id": identifier,
                "at": now(),
                "scope": result["scope"],
            }
        )
        review_rounds.save_round(root, record)
        return result


def register_late(root, round_id, request):
    """Recover missed registration against original scope without altering correct code."""
    if not request.get("reason"):
        raise WorkflowError(
            "Explain the missed registration; recovery does not grant approval."
        )
    with transaction(root):
        record = review_rounds._inspect(root, review_rounds.load_round(root, round_id))
        if (
            record["missing"]
            or record["historical"]
            or not record["snapshot_intact"]
            or record.get("superseded_by")
            or record["execution_pending"]
        ):
            raise WorkflowError(
                "Late registration requires completed current contributor results and an intact snapshot."
            )
        original_id = request.get("original_round")
        cursor = record.get("previous_round")
        seen = set()
        origin = None
        while cursor and cursor not in seen:
            seen.add(cursor)
            prior = review_rounds.load_round(root, cursor)
            if cursor == original_id:
                origin = review_rounds._inspect(root, prior)
                break
            cursor = prior.get("previous_round")
        if origin is None:
            raise WorkflowError(
                "Reference the original ancestor round, not a new source of authority."
            )
        if origin["missing"] or not origin["snapshot_intact"]:
            raise WorkflowError(
                "Original finding and pre-fix snapshot evidence must remain intact."
            )
        result = _declaration(root, origin, request)
        if not origin.get("authorized_scope") or not set(result["scope"]) <= set(
            origin["authorized_scope"]
        ):
            raise WorkflowError(
                "Original authorized scope is missing or narrower; reconcile authorization without expanding scope here."
            )
        if not set(result["scope"]) & set(record.get("changed_paths", [])):
            raise WorkflowError(
                "Late registration must account for actual changed files."
            )
        if result["id"] in record.setdefault("remediations", {}):
            raise WorkflowError(
                "Remediation already registered; preserve its verification obligation."
            )
        result["status"] = "pending"
        result["recovery"] = {
            "missed_registration": True,
            "original_round": origin["id"],
            "original_contract": origin["contract_id"],
            "pre_fix_snapshot": origin["snapshot_path"],
            "pre_fix_sources": {
                p: origin["snapshot_files"].get(p) for p in result["scope"]
            },
            "authorized_scope": list(origin["authorized_scope"]),
            "reason": request["reason"],
            "at": now(),
        }
        record["remediations"][result["id"]] = result
        record["events"].append(
            {
                "type": "missed-remediation-registration",
                "id": result["id"],
                **result["recovery"],
            }
        )
        review_rounds.save_round(root, record)
        return result


def inherited(prior, record):
    before = prior["snapshot_files"]
    after = record["snapshot_files"]
    record["changed_paths"] = sorted(
        set(prior.get("unaccounted_changes", []))
        | {p for p in set(before) | set(after) if before.get(p) != after.get(p)}
    )
    record["remediations"] = copy.deepcopy(prior.get("remediations", {}))
    for item in record["remediations"].values():
        if item["status"] != "verified" or set(item["scope"]) & set(
            record["changed_paths"]
        ):
            item["status"] = "pending"
            item.pop("verification", None)
        elif item.get("verification"):
            # A new review contract needs a new verifier even if edits appear unrelated:
            # semantic applicability is reviewed rather than inferred from paths alone.
            item["status"] = "pending"
            item.pop("verification", None)


def inspect(root, record):
    """Check accounting and durable evidence; semantic judgments belong to reviewers."""
    covered = set()
    for item in record.get("remediations", {}).values():
        covered.update(item["scope"])
    for contributor in record["contributors"].values():
        if contributor["status"] != "complete":
            continue
        result = read_json(confined(root, contributor["result_path"]))["result"]
        if not isinstance(result, dict):
            continue
        for item in result.get("change_accounting", []):
            if (
                isinstance(item, dict)
                and item.get("classification") == "nonmaterial"
                and item.get("reason")
            ):
                covered.add(item.get("path"))
    record["unaccounted_changes"] = sorted(
        set(record.get("changed_paths", [])) - covered
    )
    pending = []
    for identifier, item in record.get("remediations", {}).items():
        if item["status"] == "declared":
            continue  # Verification is post-fix, never a prerequisite to edit.
        verification = item.get("verification", {})
        current = verification.get("contract_id") == record["contract_id"]
        for evidence in verification.get("evidence_files", []):
            try:
                current = (
                    current
                    and hashlib.sha256(
                        confined(root, evidence["path"]).read_bytes()
                    ).hexdigest()
                    == evidence["sha256"]
                )
            except (OSError, WorkflowError):
                current = False
        if item["status"] != "verified" or not current:
            pending.append(identifier)
    record["pending_verifications"] = pending
    return record


def _evidence(root, workspace, reference, files):
    if not isinstance(reference, dict) or not reference.get("quote"):
        # constraint: remediation-evidence-quote
        raise WorkflowError(
            "Verification requires exact, attributed execution evidence."
        )
    path = confined(workspace, reference.get("path", ""))
    try:
        text = path.read_text()
        if reference["quote"] not in text:
            # constraint: remediation-evidence-quote
            raise ValueError
    except (OSError, ValueError) as exc:
        # constraint: remediation-evidence-quote
        raise WorkflowError("Verification evidence quotation is unavailable.") from exc
    files.append(
        {
            "path": path.relative_to(Path(root).resolve()).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    )


def _validate(root, record, item, workspace, report):
    """Structural checks apply to any report; the red/green and sibling proof
    only to a ``verified`` one, since a rejection accepts nothing."""
    files = []
    if (
        not isinstance(report, dict)
        or report.get("schema") != "remediation-verification-v1"
        or report.get("contract_id") != record["contract_id"]
        or report.get("remediation_id") != item["id"]
        or report.get("status") not in {"verified", "rejected"}
    ):
        # constraint: remediation-report-identity
        raise WorkflowError(
            "Independent verification is missing, has an unknown status, or belongs to another revision."
        )
    verified = report["status"] == "verified"
    try:
        if (
            not report["behavior"]["assessment"]
            or not report["regression"]["rejected_behavior"]
            or not report["limitations"]
        ):
            # constraint: remediation-report-fields
            raise ValueError
        _evidence(root, workspace, report["behavior"]["evidence"], files)
    except (KeyError, TypeError, ValueError, OSError) as exc:
        # constraint: remediation-report-fields
        raise WorkflowError(
            "Independent verification needs an assessment, the rejected behavior, limitations and attributed behavior evidence."
        ) from exc
    if not verified:
        return _with_report(root, workspace, files)
    try:
        for kind, expected in [("fixed", 0), ("defect", 1)]:
            check = report["regression"][kind]
            if (
                type(check["exit_code"]) is not int
                or check["exit_code"] != expected
                or not isinstance(check["argv"], list)
                or not check["argv"]
                or any(not isinstance(arg, str) or not arg for arg in check["argv"])
            ):
                # constraint: remediation-verified-proof
                raise ValueError
            _evidence(root, workspace, check["evidence"], files)
        mutation = confined(workspace, report["regression"]["defect_source"])
        files.append(
            {
                "path": mutation.relative_to(Path(root).resolve()).as_posix(),
                "sha256": hashlib.sha256(mutation.read_bytes()).hexdigest(),
            }
        )
        siblings = {s["path"]: s for s in report["siblings"]}
        if not set(item["siblings"]) <= set(siblings):
            # constraint: remediation-verified-proof
            raise ValueError
        for path, sibling in siblings.items():
            if (
                sibling["status"] not in {"fixed", "already-safe", "outside-scope"}
                or not sibling["reason"]
            ):
                # constraint: remediation-verified-proof
                raise ValueError
            if path not in item["scope"] and sibling["status"] == "fixed":
                # constraint: remediation-verified-proof
                raise ValueError
        exception = report["regression"].get("exception")
        if exception:
            if not exception["reason"]:
                # constraint: remediation-verified-proof
                raise ValueError
            _evidence(root, workspace, exception["evidence"], files)
    except (KeyError, TypeError, ValueError, OSError) as exc:
        # constraint: remediation-verified-proof
        raise WorkflowError(
            "Independent verification needs behavior evidence, meaningful red/green challenge and complete scoped sibling accounting."
        ) from exc
    return _with_report(root, workspace, files)


def _with_report(root, workspace, files):
    report_path = workspace / "verification.json"
    files.append(
        {
            "path": report_path.relative_to(Path(root).resolve()).as_posix(),
            "sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(),
        }
    )
    return files


VERIFIER_INSTRUCTIONS = """Independently verify this declared material fix in your disposable workspace.
You are a fresh verifier, not the remediator or its experimental helper. Apply the supplied remediation methodology.
Account for all known siblings with concrete reasons; discover relevant additional siblings.
Keep changes within your disposable workspace and accepted scope.
Write verification.json at the workspace root in this layout: schema, contract_id, remediation_id, status,
behavior {assessment,evidence:{path,quote}}, regression {fixed:{argv,exit_code,evidence:{path,quote}},
defect:{argv,exit_code,evidence:{path,quote}},defect_source,rejected_behavior,exception:null or {reason,evidence:{path,quote}}},
siblings:[{path,status,reason}], and limitations. Paths are relative to your workspace.
Preserve full log files and original/representative defective source.
Use verified only when the supplied methodology is satisfied; the rules block states what each verdict needs and does."""


def verify(root, round_id, identifier):
    record = review_rounds.status(root, round_id)
    if (
        record["historical"]
        or not record["snapshot_intact"]
        or record.get("superseded_by")
    ):
        raise WorkflowError(
            "Verification requires the current unmodified review snapshot."
        )
    try:
        item = record["remediations"][identifier]
    except KeyError as exc:
        raise WorkflowError("Unknown declared remediation.") from exc
    if item["status"] == "declared":
        raise WorkflowError("Start the post-fix follow-up round before verification.")
    methodology = review.remediation_guidance()
    investigation_id = "verify-" + identifier
    if investigation_id not in record["investigations"]:
        investigations.start(
            root,
            round_id,
            {
                "id": investigation_id,
                "question": item["behavior"],
                "requirements": item["requirements"],
            },
        )
    from .constraints import block_text, render

    entry = investigations.run(
        root,
        round_id,
        investigation_id,
        {
            "mode": "delegated",
            "modifies_code": True,
            "prompt": VERIFIER_INSTRUCTIONS
            + "\nSupplied remediation methodology:\n"
            + json.dumps(methodology)
            + "\nAccepted declaration:\n"
            + json.dumps(item)
            + block_text(render("remediation-verifier", record.get("configuration", {}))),
        },
        purpose="independent-verification",
    )
    attempt = entry["attempts"][-1]
    if attempt["status"] != "completed":
        raise WorkflowError(
            "Independent verifier did not complete; recover within the existing budget."
        )
    workspace = confined(root, attempt["workspace"])
    report = read_json(workspace / "verification.json")
    files = _validate(root, record, item, workspace, report)
    rejected = report["status"] == "rejected"
    rejected_behavior = report["regression"]["rejected_behavior"]
    investigations.conclude(
        root,
        round_id,
        investigation_id,
        {
            "conclusion": "Independent verifier rejected the remediation: "
            + rejected_behavior
            if rejected
            else "Independent verifier recorded behavior and regression challenge evidence.",
            "attempts": [len(entry["attempts"])],
        },
    )
    with transaction(root):
        latest = review_rounds._inspect(root, review_rounds.load_round(root, round_id))
        if (
            latest["historical"]
            or not latest["snapshot_intact"]
            or latest.get("superseded_by")
        ):
            raise WorkflowError(
                "Sources changed during verification; evidence is historical."
            )
        result = {
            "status": report["status"],
            "contract_id": record["contract_id"],
            "report": report,
            "evidence_files": files,
            "investigation": investigation_id,
            "at": now(),
        }
        if rejected:
            result["rejected_behavior"] = rejected_behavior
        latest["remediations"][identifier].update(
            status=report["status"], verification=result
        )
        latest["events"].append(
            {
                "type": "independent-remediation-rejected"
                if rejected
                else "independent-remediation-verified",
                "id": identifier,
                "at": now(),
                "contract_id": record["contract_id"],
            }
        )
        review_rounds.save_round(root, latest)
    if rejected:
        # constraint: remediation-rejected-verdict
        raise WorkflowError(
            "Remediation "
            + identifier
            + " not accepted: independent verifier returned rejected: "
            + rejected_behavior
        )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["declare", "register-late", "verify"])
    parser.add_argument("--root", default=".")
    parser.add_argument("--round", required=True)
    parser.add_argument("--request")
    parser.add_argument("--id")
    args = parser.parse_args()
    try:
        root = Path(args.root).resolve()
        result = (
            verify(root, args.round, args.id)
            if args.action == "verify"
            else (register_late if args.action == "register-late" else declare)(
                root, args.round, read_json(args.request)
            )
        )
        print(json.dumps(result, indent=2))
        return 0
    except (WorkflowError, OSError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
