"""Source-attributed decisions and standing repair authority, without invented consent."""

import re

from . import engine, evidence
from .store import WorkflowError, confined, digest, event, now


def mutable(record, session):
    engine.ownership(record, session)
    if record.get("pending_repair") or any(
        p.get("pending") for p in record["phases"].values()
    ):
        raise WorkflowError(
            "Finish or recover the pending operation before changing decisions or repairs."
        )
    if any(record["workers"].values()):
        raise WorkflowError("Stop active workers before changing decisions or repairs.")


def source(root, value):
    if not isinstance(value, dict) or set(value) != {"path", "quote"}:
        raise WorkflowError(
            "A decision source needs a repository-relative path and exact quote."
        )
    path, quote = value["path"], value["quote"]
    if (
        not isinstance(path, str)
        or not isinstance(quote, str)
        or not 1 <= len(quote) <= 4000
    ):
        raise WorkflowError("Use a bounded nonempty source quote and path.")
    if path.endswith("state.json") or "/runtime/" in path or path.startswith(".git/"):
        raise WorkflowError(
            "Use an original human decision source, not workflow history."
        )
    try:
        content = confined(root, path).read_text()
    except (OSError, UnicodeError) as exc:
        raise WorkflowError(f"Cannot read decision source {path}: {exc}") from exc
    if content.count(quote) != 1:
        raise WorkflowError("The exact decision quote must occur once in its source.")
    return {"path": path, "quote": quote, "hash": digest(content)}


def verify_source(root, saved):
    actual = source(root, {"path": saved["path"], "quote": saved["quote"]})
    if actual != saved:
        raise WorkflowError(
            "Decision source changed; record a sourced superseding decision before repair."
        )
    return actual


def active(record):
    rows = record.get("decisions", [])
    superseded = {r["supersedes"] for r in rows if r.get("supersedes")}
    return [r for r in rows if r["id"] not in superseded]


def current(root, record):
    rows = active(record)
    for row in rows:
        verify_source(root, row["source"])
    return rows


def binding(root, record, phase):
    phases = evidence.phases(record)
    position = phases.index(evidence.ordered(phase))
    rows = [
        r for r in active(record) if phases.index(r["phase"]) <= position
    ]
    for row in rows:
        verify_source(root, row["source"])
    return [
        {k: r[k] for k in ("id", "text", "phase", "source", "supersedes")} for r in rows
    ]


def dispositions(record, value):
    """Validate the operator's dispositions of accepted suggestions against the unit."""
    from .handoff import DISPOSITIONS, round_suggestions, suggestion_dispositions

    if not isinstance(value, list) or not value:
        raise WorkflowError(
            "Dispositions must be a nonempty list of {finding, disposition, owner} entries."
        )
    # The open phase's recorded review counts too: its close may have refused over one of
    # its own suggestions, and the disposition is what lets the retry proceed.
    known = {item["digest"]: item for item in suggestion_dispositions(record) + round_suggestions(record)}
    seen = set()
    result = []
    for entry in value:
        if not isinstance(entry, dict) or set(entry) - {"finding", "disposition", "owner"}:
            raise WorkflowError(
                "Each disposition carries only finding, disposition, and owner (owner when deferring)."
            )
        finding, choice = entry.get("finding"), entry.get("disposition")
        if not isinstance(finding, str) or not re.fullmatch(r"[0-9a-f]{64}", finding):
            raise WorkflowError(
                "A disposition names its finding by the 64-character digest shown in the continuation packet."
            )
        if choice not in DISPOSITIONS:
            raise WorkflowError(
                "A disposition is one of fix-now, defer, or decline."
            )
        owner = entry.get("owner")
        if choice == "defer" and (not isinstance(owner, str) or not owner.strip()):
            raise WorkflowError("A deferred suggestion names its owner as a nonempty string.")
        if choice != "defer" and "owner" in entry:
            raise WorkflowError("Only a deferred suggestion carries an owner.")
        if finding not in known:
            raise WorkflowError(
                f"Disposition digest {finding} matches no accepted suggestion in this unit; "
                "use the digests from continuation --section undispositioned_suggestions."
            )
        if finding in seen:
            raise WorkflowError(f"Disposition digest {finding} appears more than once in the request.")
        seen.add(finding)
        item = {"finding": finding, "disposition": choice}
        if choice == "defer":
            item["owner"] = owner.strip()
        result.append(item)
    return result


def record(root, record, session, request):
    """Mutate under the caller's transaction; attribution is not authenticated consent."""
    mutable(record, session)
    if not isinstance(request, dict) or set(request) - {
        "id",
        "text",
        "phase",
        "source",
        "kind",
        "amends",
        "supersedes",
        "dispositions",
    }:
        raise WorkflowError(
            "Decision request needs id, text, phase, kind, source, and optional amends, "
            "supersedes, or dispositions."
        )
    if any(
        not isinstance(request.get(k), str) or not request[k].strip()
        for k in ("id", "text", "phase")
    ):
        raise WorkflowError("Decision id, text, and phase must be nonempty strings.")
    if len(request["id"]) > 120 or len(request["text"]) > 4000:
        raise WorkflowError("Keep the decision id and statement bounded.")
    if request["phase"] not in evidence.phases(record):
        raise WorkflowError("Decision names an inapplicable phase.")
    rows = record.setdefault("decisions", [])
    if any(r["id"] == request["id"] for r in rows):
        raise WorkflowError(
            "Decision ids are immutable; create a superseding decision."
        )
    prior = request.get("supersedes")
    current_rows = {r["id"]: r for r in active(record)}
    if prior is not None and prior not in current_rows:
        raise WorkflowError("Supersedes must name exactly one current decision.")
    if prior is None:
        version_guard(request["id"], current_rows)
    replaced = current_rows[prior]["phase"] if prior is not None else None
    kind, amends = classify(record, request["phase"], request.get("kind"), request.get("amends"),
                            "dispositions" in request, replaced)
    row = {
        "id": request["id"],
        "text": request["text"],
        "phase": request["phase"],
        "kind": kind,
        **({"amends": amends} if amends else {}),
        "source": source(root, request.get("source")),
        "supersedes": prior,
        "at": now(),
    }
    if "dispositions" in request:
        # A disposition record leaves the phase revision alone, so it cannot also carry a
        # correction that must make accepted work stale; the correction is its own record.
        if prior is not None:
            raise WorkflowError(
                "A decision carrying dispositions answers reviewer suggestions only; "
                "record the superseding decision separately."
            )
        row["dispositions"] = dispositions(record, request["dispositions"])
    rows.append(row)
    event(record, "decision-recorded", session, decision=row)
    _returned_to_writing_tests(root, record, session)
    return row


def _returned_to_writing_tests(root, record, session):
    """A decision recorded while the checkpoint's locks still stand, and after which its
    acceptance is not current, returns the unit to writing tests, so the writing-tests
    baseline is recorded again over the code built so far. That holds even when an edited
    decision source had already made the acceptance not current; a changed locked test,
    or a baseline recorded since the latest pass, never triggers it."""
    if engine.unrecorded_return(root, record) and not engine.checkpoint_current(root, record):
        from .test_preparation import record_baseline

        record_baseline(root, record, session, "a governing decision made the test checkpoint stale")


KINDS = ("governs", "process")
KIND_HELP = (
    "kind is governs when the decision constrains the work product (behavior, scope, "
    "contracts, plan rules), or process when it records how the work was run (review "
    "plans, approvals, dispositions, overrides)."
)


def classify(record, phase, kind, amends, disposition, replaced=None):
    """Validate a decision's reader-facing kind and the earlier phase it amends."""
    if kind not in KINDS:
        raise WorkflowError(f"Decision needs a kind: {KIND_HELP}")
    if disposition and kind != "process":
        raise WorkflowError("A decision carrying dispositions is a process decision; set kind to process.")
    order = evidence.phases(record)
    # Replacing an earlier phase's decision changes what that phase's document must say.
    inferred = replaced if replaced is not None and order.index(replaced) < order.index(phase) else None
    if amends is not None and inferred is not None and amends != inferred:
        raise WorkflowError(
            f"This decision replaces a {inferred} decision, so it amends {inferred}; "
            f"amends must be {inferred} or omitted."
        )
    amends = amends if amends is not None else inferred
    if amends is None:
        return kind, None
    if amends not in order or order.index(amends) >= order.index(phase):
        raise WorkflowError("amends names an earlier phase than the decision's own phase.")
    if not record["phases"][amends]["evidence"] and amends != inferred:
        raise WorkflowError(
            f"amends names {amends}, which is not accepted; record the decision under that phase instead."
        )
    if kind != "governs":
        raise WorkflowError("An amendment changes an accepted document, so its kind is governs.")
    return kind, amends


VERSION = re.compile(r"^(.+)-v\d+$")


def version_guard(new_id, current_rows):
    """Refuse an informal new version of an active decision; it would leave both current."""
    match = VERSION.match(new_id)
    if not match:
        return
    base = match.group(1)
    for existing in current_rows:
        if existing == base or (VERSION.match(existing) and VERSION.match(existing).group(1) == base):
            raise WorkflowError(
                f"Decision {new_id} looks like a new version of active decision {existing}. "
                f"Set \"supersedes\": \"{existing}\" to replace it, or choose an id that is not a version of it."
            )


def annotate(root, record, session, request):
    """Classify a decision recorded before kinds existed; once, with the operator's reason."""
    mutable(record, session)
    if not isinstance(request, dict) or set(request) - {"id", "kind", "amends", "reason"} \
            or not isinstance(request.get("reason"), str) or not request["reason"].strip():
        raise WorkflowError("Annotation needs id, kind, the operator's reason, and optional amends.")
    row = next((r for r in record.get("decisions", []) if r["id"] == request.get("id")), None)
    if row is None:
        raise WorkflowError(f"No decision {request.get('id')} is recorded in this unit.")
    if "kind" in row:
        raise WorkflowError(f"Decision {row['id']} already has a kind; annotation is only for earlier records.")
    replaced = next((r["phase"] for r in record["decisions"] if r["id"] == row.get("supersedes")), None)
    kind, amends = classify(record, row["phase"], request.get("kind"), request.get("amends"),
                            bool(row.get("dispositions")), replaced)
    row["kind"] = kind
    if amends:
        row["amends"] = amends
    event(record, "decision-annotated", session, decision=row["id"], decision_kind=kind, amends=amends,
          reason=request["reason"].strip())
    _returned_to_writing_tests(root, record, session)
    return row


def for_readers(root, record, phase):
    """The decisions a reader of this phase needs: its own governing ones and live amendments.

    Earlier phases' decisions reach later phases through their accepted documents.
    An amendment changes an accepted document without reopening it, so it travels to
    every later phase, and to the amended phase if reopened, until that phase is
    accepted again after it was recorded.
    """
    rows = active(record)
    if not rows:
        return []
    order = evidence.phases(record)
    phase = evidence.ordered(phase)
    position = order.index(phase) if phase in order else len(order) - 1
    shown = []
    for row in rows:
        if row.get("kind", "governs") != "governs" or row.get("dispositions"):
            continue
        own = row["phase"] == order[position]
        amended = row.get("amends")
        live = (
            amended in order and order.index(amended) <= position
            and not absorbed(record, row)
        )
        if own or live:
            verify_source(root, row["source"])
            shown.append(row)
    return shown


def governing_through(root, record, phase):
    """Every active governing decision from this phase and every earlier one.

    For a session that cuts a document: an earlier phase's decision may live on only
    in the very line it would cut, so it cannot rely on accepted documents to carry it.
    """
    order = evidence.phases(record)
    position = order.index(evidence.ordered(phase))
    shown = []
    for row in active(record):
        if (row.get("kind", "governs") != "governs" or row.get("dispositions")
                or order.index(row["phase"]) > position):
            continue
        verify_source(root, row["source"])
        shown.append(row)
    return shown


def absorbed(record, row):
    accepted = record["phases"][row["amends"]]["evidence"]
    return bool(accepted and accepted["at"] > row["at"])


def lean(row):
    """A decision as a reader sees it: no fingerprints or replacement history."""
    return {"id": row["id"], "text": row["text"], "phase": row["phase"],
            **({"amends": row["amends"]} if row.get("amends") else {}),
            "path": row["source"]["path"],
            **({"quote": row["source"]["quote"]} if "quote" in row["source"] else {})}


def policy(root, record, session, request):
    mutable(record, session)
    if not isinstance(request, dict) or set(request) != {"classes", "source"}:
        raise WorkflowError(
            "Repair policy needs classes and a source for the human's authorization."
        )
    classes = request["classes"]
    if (
        not isinstance(classes, list)
        or any(c not in {"reference", "contradiction"} for c in classes)
        or len(classes) != len(set(classes))
    ):
        raise WorkflowError(
            "Repair classes are reference and contradiction; an empty list revokes authority."
        )
    value = {
        "classes": sorted(classes),
        "source": source(root, request["source"]),
        "at": now(),
    }
    record["repair_policy"] = value
    event(record, "repair-policy-recorded", session, policy=value)
    return value


def source_paths(root, record, phase):
    return sorted({row["source"]["path"] for row in binding(root, record, phase)})
