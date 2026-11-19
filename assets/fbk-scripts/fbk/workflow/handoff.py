"""Bounded views and revision-bound worker contracts; callers lock mutations."""

import json
import uuid
from pathlib import Path

from . import decisions, engine, evidence, traceability
from .store import WorkflowError, confined, digest, event, now, read_json, save, unit_dir
from .traceability import anchor, headings

DISPOSITIONS = ("fix-now", "defer", "decline")
DISPOSITION_NEXT = (
    "Group these by what they are about, put each group to the operator, write the "
    "operator's words to a source file, and record them with decision-record "
    "--request <file> carrying dispositions."
)


def finding_digest(finding):
    """The stable identity of a review finding: what it says, where, and on what evidence."""
    return digest(
        {
            "title": finding["title"],
            "location": finding["location"],
            "evidence": finding["evidence"],
        }
    )


def _latest_dispositions(record):
    """Newest recorded disposition per finding digest, across every decision row."""
    latest = {}
    for row in record.get("decisions", []):
        for item in row.get("dispositions") or []:
            latest[item["finding"]] = {
                "disposition": item["disposition"],
                "owner": item.get("owner"),
                "decision_id": row["id"],
            }
    return latest


def _review_suggestions(findings, phase, latest):
    """The suggestions among one review's findings, each with its current disposition, if any."""
    result = []
    for index, finding in enumerate(findings or [], 1):
        if finding.get("severity") != "suggestion":
            continue
        key = finding_digest(finding)
        current = latest.get(key, {})
        result.append(
            {
                "digest": key,
                "phase": phase,
                "index": index,
                "title": finding["title"],
                "remedy_kind": finding.get("remedy_kind") or "artifact",
                "disposition": current.get("disposition"),
                "owner": current.get("owner"),
                "decision_id": current.get("decision_id"),
            }
        )
    return result


def _reviews(record):
    """The unit's phases in order, with the test checkpoint after breakdown when the unit implements."""
    phases = evidence.phases(record)
    if "implement" in phases:
        phases.insert(phases.index("implement"), evidence.CHECKPOINT)
    return phases


def suggestion_dispositions(record):
    """Every accepted suggestion across phases and the test checkpoint, with its current disposition, if any."""
    latest = _latest_dispositions(record)
    result = []
    for phase in _reviews(record):
        accepted = record["phases"][phase].get("evidence")
        if not accepted:
            continue
        review = (accepted.get("review") or {}).get("review") or {}
        result.extend(_review_suggestions(review.get("findings"), phase, latest))
    return result


def round_suggestions(record):
    """Suggestions from the open phase's latest recorded review, and while implement is open
    the test checkpoint's, before that review is accepted.

    A close can refuse after its review is recorded on the round; the operator then
    dispositions those suggestions so the retry reuses the review.
    """
    phase = record.get("open_phase")
    if phase not in evidence.phases(record):
        return []
    latest = _latest_dispositions(record)
    result = []
    for name in (phase, evidence.CHECKPOINT) if phase == "implement" else (phase,):
        rounds = record["phases"][name].get("rounds") or []
        latest_round = rounds[-1] if rounds else None
        if not latest_round or not latest_round.get("result") or latest_round.get("error"):
            continue
        review = latest_round["result"].get("review") or {}
        result.extend(_review_suggestions(review.get("findings"), name, latest))
    return result


def undispositioned_in(record, phase, findings, *, remedy_kind=None):
    """Suggestions among one review's findings still awaiting the operator's disposition.

    Used where a phase's own review is checked before it is accepted; `remedy_kind`
    limits the result to suggestions whose remedy is of that kind.
    """
    return [
        item
        for item in _review_suggestions(findings, phase, _latest_dispositions(record))
        if item["disposition"] is None
        and (remedy_kind is None or item["remedy_kind"] == remedy_kind)
    ]


def undispositioned(record, *, before=None, remedy_kind=None):
    """Accepted suggestions still awaiting the operator's disposition.

    `before` limits the search to phases earlier than the named phase; `remedy_kind`
    limits it to suggestions whose remedy is of that kind.
    """
    phases = evidence.phases(record)
    # The author sorted these before the phase was accepted; no operator disposition is owed.
    sorted_phases = {
        name for name, work in record["phases"].items()
        if (work.get("evidence") or {}).get("author_sorted")
    }
    return [
        item
        for item in suggestion_dispositions(record)
        if item["disposition"] is None
        and item["phase"] not in sorted_phases
        and (before is None or before not in phases
             or phases.index(evidence.ordered(item["phase"])) < phases.index(before))
        and (remedy_kind is None or item["remedy_kind"] == remedy_kind)
    ]


def disposition_blockers(record, unit, items, lead):
    """One message naming each undispositioned suggestion and how to record a disposition."""
    if not items:
        return None
    named = "; ".join(f"{item['phase']}#{item['index']} {item['title']}" for item in items)
    return (
        f"{lead}: {named}. Put each to the operator, write the operator's words to a "
        f"source file, and record them with decision-record {unit} --request <file> "
        "carrying dispositions (fix-now, defer with an owner, or decline)."
    )


def council_notes(result, number):
    """A council finding's dissent, whether its count tied, and the findings it is an
    alternative to, numbered from 1 as current-findings numbers them."""
    notes = (result.get("discussion") or {}).get("findings") or []
    if result.get("shape") != "council" or number >= len(notes):
        return {}
    note = notes[number]
    position = {n["proposal"]: i for i, n in enumerate(notes, 1)}
    council = {"dissent": note["dissent"], "tied": note["tied"]}
    if note.get("alternatives"):
        council["alternative_to"] = [position[p] for p in note["alternatives"] if p in position]
    return {"council": council}


def current_findings(record, phase=None):
    phase = phase or record.get("open_phase")
    work = record.get("phases", {}).get(phase, {})
    rounds = work.get("rounds", [])
    latest = rounds[-1] if rounds else {}
    result = latest.get("result") or {}
    review = result.get("review") or {}
    return {
        "phase": phase,
        "revision": latest.get("revision"),
        "generation": latest.get("generation"),
        "current_generation": latest.get("generation") == work.get("generation"),
        "error": latest.get("error") or result.get("error"),
        "summary": review.get("summary", ""),
        # Each finding carries the digest a disposition names it by, and a council finding
        # its dissent, so the author sorts it knowing who disagreed and why.
        "findings": [{**f, "digest": finding_digest(f), **council_notes(result, number)}
                     for number, f in enumerate(review.get("findings", []))],
        "remaining_attempts": max(0, work.get("round_limit", 3) - engine.spent_rounds(work)),
    }


def findings_are_current(root, record, phase, findings=None):
    if phase not in evidence.REVIEWS:
        return False
    findings = findings or current_findings(record, phase)
    try:
        if not findings["current_generation"] or findings[
            "revision"
        ] != evidence.revision(root, record, phase):
            return False
        result = record["phases"][phase]["rounds"][-1].get("result") or {}
        if "snapshot_files" in result:
            from .review_context import snapshot_fresh

            return snapshot_fresh(root, result)
        return True
    except (WorkflowError, KeyError, IndexError):
        return False


def accepted_reviews(root, record):
    """Carry accepted review evidence across phases without promoting advice to scope."""
    result = []
    latest = _latest_dispositions(record)
    # The immediately preceding phase is the most useful boundary context.
    # _bounded removes entries from the end, preserving the newest first.
    for phase in reversed(_reviews(record)):
        accepted = record["phases"][phase].get("evidence")
        if not accepted:
            continue
        review = (accepted.get("review") or {}).get("review") or {}
        if not review.get("findings"):
            continue
        try:
            current = accepted["revision"] == evidence.revision(root, record, phase) and evidence.supporting_current(root, accepted)
        except WorkflowError:
            current = False
        findings = []
        for finding in review["findings"]:
            key = finding_digest(finding)
            findings.append({
                **finding,
                "digest": key,
                "disposition": latest.get(key, {}).get("disposition"),
            })
        result.append({
            "phase": phase,
            "accepted_at": accepted["at"],
            "revision": accepted["revision"],
            "source_current": current,
            "source": f".fbk/{record['unit']}/state.json",
            "pointer": f"/phases/{phase}/evidence/review/review",
            "findings": findings,
        })
    return result


def _bounded(view, maximum):
    """Drop complete optional items, expose omissions, always return valid JSON data."""
    view.setdefault("omitted", {})
    drift = view.get("acceptance_drift")
    if drift and len(json.dumps(view, ensure_ascii=False)) > maximum:
        view["acceptance_drift"] = {
            "change_count": len(drift["changes"]),
            "outside_scope_candidate_count": len(drift["outside_scope_test_candidates"]),
            "retrieve": f"status {view.get('unit')}",
        }
        view["omitted"]["acceptance_drift_details"] = True
    for field in ("other_units", "decisions", "tasks", "findings", "accepted_reviews", "undispositioned_suggestions", "sources"):
        items = view.get(field)
        while (
            isinstance(items, list)
            and items
            and len(json.dumps(view, ensure_ascii=False)) > maximum
        ):
            items.pop()
            view["omitted"][field] = view["omitted"].get(field, 0) + 1
    if len(json.dumps(view, ensure_ascii=False)) > maximum:
        # Free text is preserved on disk and fetched by the explicit continuation route.
        for field in ("pending", "objective", "review_summary", "reason"):
            if field in view:
                view.pop(field)
                view["omitted"][field] = 1
    if len(json.dumps(view, ensure_ascii=False)) > maximum:
        return {
            "unit": view.get("unit"),
            "next": "Run continuation for this unit and read its authoritative artifacts. Record pending phase observations before continuing.",
            "retrospective": view.get("retrospective"),
            "omitted": {"detail": True},
            **({"acceptance_drift": view["acceptance_drift"]} if view.get("acceptance_drift") else {}),
            "accepted_review_retrieval": f"continuation {view.get('unit')} --section accepted_reviews",
        }
    return view


def continuation(root, record, *, max_chars=10000):
    status = engine.status_report(root, record)
    phase = status["phase"]
    # While the test checkpoint is running or out of rounds, its review is the one to hand off.
    reviewed = engine.review_in_focus(root, record, phase)
    findings = current_findings(record, reviewed)
    try:
        revision = (
            evidence.revision(root, record, reviewed) if reviewed in evidence.REVIEWS else None
        )
    except WorkflowError:
        revision = None
    base = unit_dir(root, record["unit"]).relative_to(root).as_posix()
    sources = [f"{base}/prd.md"]
    if record.get("design") and phase != "intent":
        sources.append(f"{base}/design/")
    if phase in {"spec", "breakdown", "implement", "closed"}:
        sources.extend([f"{base}/spec.md", f"{base}/scope.json"])
    if phase in {"breakdown", "implement", "closed"}:
        sources.append(f"{base}/tasks.json")
        try:
            declared = evidence.scope(root, record["unit"])
            sources.extend(evidence.test_files(root, declared))
        except WorkflowError:
            pass
    if record.get("parent"):
        sources.append(f".fbk/{record['parent']}/spec.md")
    pending = next(
        (
            e.get("reason")
            for e in reversed(record.get("events", []))
            if e.get("event") == "suspended"
        ),
        None,
    )
    # A later phase close resolves a prior suspension; resumption itself may still need its answer.
    last_suspend = max(
        (
            i
            for i, e in enumerate(record.get("events", []))
            if e.get("event") == "suspended"
        ),
        default=-1,
    )
    if any(
        e.get("event") == "closed" for e in record.get("events", [])[last_suspend + 1 :]
    ):
        pending = None
    current = findings_are_current(root, record, reviewed, findings)
    authority_problem = None
    try:
        current_decisions = [decisions.lean(row) for row in decisions.for_readers(
            root,
            record,
            phase if phase in evidence.PHASES else evidence.phases(record)[-1],
        )]
    except WorkflowError as exc:
        current_decisions = []
        authority_problem = str(exc)
        sources.extend(row["source"]["path"] for row in decisions.active(record))
    try:
        declared_tasks = (
            read_json(unit_dir(root, record["unit"]) / "tasks.json")
            if phase in {"breakdown", "implement", "closed"}
            else []
        )
        if not isinstance(declared_tasks, list):
            declared_tasks = []
    except WorkflowError:
        declared_tasks = []
    task_views = []
    for task in declared_tasks:
        if not isinstance(task, dict) or not task.get("id"):
            continue
        run = record.get("task_runs", {}).get(task["id"], {})
        task_views.append(
            {
                "task": task["id"],
                "description": task.get("description"),
                "status": run.get("status", "unassigned"),
                "worker_id": run.get("worker_id"),
                "outcome": run.get("outcome"),
                "files": task.get("files"),
                "depends_on": task.get("depends_on", []),
                "consumes": task.get("consumes", []),
                "stage": task.get("stage"),
                "verification": task.get("verification"),
                "check_expectations": task.get("check_expectations", []),
                "acceptance_refs": run.get(
                    "acceptance_refs", task.get("acceptance_refs")
                ),
                "unresolved": run.get("return", {}).get("unresolved", []),
            }
        )
    # Started work that is not done comes first, then unassigned, then completed.
    task_views.sort(key=lambda t: {"unassigned": 1, "completed": 2}.get(t["status"], 0))
    view = {
        **({"test_preparation": status["test_preparation"]} if "test_preparation" in status else {}),
        "unit": record["unit"],
        "phase": phase,
        "status": status["status"],
        "human_review": status["human_review"],
        "retrospective": status["retrospective"],
        "acceptance_drift": status["acceptance_drift"],
        "revision": revision,
        "owner": record.get("owner"),
        "next": status["next"],
        "objective": f"Deliver the accepted behavior defined in {base}/prd.md; use the current phase artifacts as authority.",
        "sources": sources,
        "pending": pending,
        "pending_guidance": "Check current sourced decisions before repeating a recorded suspension question.",
        "decisions": current_decisions,
        "remaining_attempts": findings["remaining_attempts"],
        "findings_revision": findings["revision"],
        "findings_current": current,
        "findings": list(findings["findings"]) if current else [],
        "accepted_reviews": accepted_reviews(root, record),
        "review_summary": findings["error"] or findings["summary"]
        if current
        else f"No review has run for {reviewed}. Prior accepted review findings are in accepted_reviews."
        if findings["revision"] is None
        else "Earlier findings require checking against the current sources.",
        "tasks": task_views,
        "undispositioned_suggestions": [
            {k: item[k] for k in ("digest", "phase", "index", "title", "remedy_kind")}
            for item in undispositioned(record, before=phase if phase in evidence.PHASES else None)
            # The checkpoint's recorded review needs its suggestions dispositioned before it locks.
            + [item for item in round_suggestions(record)
               if item["phase"] == evidence.CHECKPOINT and item["disposition"] is None]
        ],
        "detail": f"Use continuation {record['unit']} --section decisions|tasks|sources|pending|accepted_reviews|undispositioned_suggestions for omitted context, current-findings {record['unit']} for review details, and task-context for a worker; workflow-report --history retains the audit history.",
    }
    if view["undispositioned_suggestions"]:
        view["undispositioned_suggestions_next"] = DISPOSITION_NEXT
    if view["accepted_reviews"]:
        view["accepted_review_index"] = [
            {"phase": item["phase"], "finding_count": len(item["findings"]),
             "source_current": item["source_current"]}
            for item in view["accepted_reviews"]
        ]
        view["accepted_review_guidance"] = (
            "Prior accepted reviews are durable evidence, not a new task list. "
            "Check relevant concerns against current sources and recorded dispositions. "
            "Suggestions remain advisory. Retrieve omitted reviews with "
            f"continuation {record['unit']} --section accepted_reviews."
        )
    if authority_problem:
        view["authority_problem"] = authority_problem
        view["next"] = (
            "Restore the recorded decision source or record a sourced superseding decision before continuing; the unverified decision is withheld."
        )
    if record.get("pending_repair"):
        view["next"] = (
            "A repair is pending; finish it or use recover-repair before other work."
        )
    return _bounded(view, max_chars)


def session_context(root, records, session, max_chars=12000):
    unfinished = [
        r
        for r in records
        if engine.status_report(root, r)["status"] != "closed"
        or engine.status_report(root, r)["parent_problem"]
    ]
    if not unfinished:
        return {}
    # Ownership is decisive. Otherwise the most recently active unit is the useful default.
    ordered = sorted(
        unfinished,
        key=lambda r: (
            r.get("owner") == session and bool(session),
            r.get("opened_at") or "",
            (r.get("events") or [{}])[-1].get("at", ""),
        ),
        reverse=True,
    )
    view = continuation(root, ordered[0], max_chars=max_chars - 1500)
    view["other_units"] = [
        {
            "unit": r["unit"],
            "phase": r.get("open_phase"),
            "status": engine.status_report(root, r)["status"],
        }
        for r in ordered[1:]
    ]
    return _bounded(view, max_chars)


def _references(root, refs, name, specs=(), deferred=None):
    """The repository paths of ``refs``, each checked to exist, with any line or heading anchor
    it names. Anchored entries into ``specs`` are left to the requirement check; when
    ``deferred`` is given, only those of its entries are."""
    if (
        not isinstance(refs, list)
        or not refs
        or any(not isinstance(p, str) or not p.strip() for p in refs)
    ):
        raise WorkflowError(
            f"Task launch needs nonempty {name} pointing to authoritative source files."
        )
    paths = []
    for ref in refs:
        target, line = _reference_target(root, ref)
        if not target.is_file():
            raise WorkflowError(f"Task reference is missing: {ref}")
        if traceability.spec_entry(ref, specs) and (deferred is None or ref in deferred):
            pass
        elif line is not None or "#" in ref:
            try:
                content = target.read_text()
            except (OSError, UnicodeError) as exc:
                raise WorkflowError(
                    f"Task reference is not readable text: {ref}"
                ) from exc
            if line is not None and not 1 <= line <= len(content.splitlines()):
                raise WorkflowError(f"Task reference line does not exist: {ref}")
            if "#" in ref:
                slugs = [anchor(title) for _, _, title in headings(content)]
                fragment = ref.split("#", 1)[1]
                if slugs.count(fragment) != 1:
                    raise WorkflowError(
                        f"Task reference needs a unique heading anchor; use a valid line or file reference: {ref}"
                    )
        paths.append(target.relative_to(root).as_posix())
    return paths


def _reference_target(root, ref):
    """The file ``ref`` names, inside the repository, and the line number it gives, if any."""
    path = ref.split("#", 1)[0]
    line = None
    if ":" in path and path.rsplit(":", 1)[-1].isdigit():
        line = int(path.rsplit(":", 1)[-1])
        path = path.rsplit(":", 1)[0]
    return confined(root, path), line


def _hashes(root, paths):
    return {
        p: evidence.file_hashes(root, [p])[p] if confined(root, p).is_file() else None
        for p in paths
    }


def _task_files(root, patterns):
    paths = set(evidence.expand(root, patterns))
    for path in patterns:
        if not any(c in path for c in "*?[") and not confined(root, path).is_dir():
            paths.add(path)
    return sorted(paths)


def _return_paths(root, record, run):
    """The paths a task's return fingerprints: its owned files now, those at task start, and
    the owned paths in the writing-tests baseline, so a file created after task start, caught
    by a baseline, and deleted again is recorded as deleted."""
    baseline = (record.get("writing_tests_baseline") or {}).get("files", {})
    owned = [path for path in baseline if evidence.matches(path, run["files"])]
    return sorted(set(_task_files(root, run["files"])) | set(run["before"]) | set(owned))


def _plan_binding(root, record, tasks, task_id, consumes):
    """An assignment binds the governing inputs plus its own plan entry and the
    entries it depends on or consumes from; an unrelated task edit leaves it valid.
    Phase acceptance still digests the whole plan through evidence.subject."""
    from .store import digest

    inputs = evidence.revision_inputs(root, record, "breakdown")
    base = unit_dir(root, record["unit"]).relative_to(root).as_posix()
    inputs["files"].pop(f"{base}/tasks.json", None)
    by_id = {t["id"]: t for t in tasks if isinstance(t, dict) and "id" in t}
    task = by_id.get(task_id, {})
    related = {task_id, *task.get("depends_on", [])}
    related.update(
        other_id
        for other_id, other in by_id.items()
        if other_id != task_id
        and ownership_overlaps(other.get("files", []), consumes)
    )
    inputs["tasks"] = {i: by_id.get(i) for i in sorted(related)}
    return digest(inputs)


def _plan_current(root, record, task_id, run, tasks=None):
    if "plan_input" not in run:  # assignments recorded before per-task binding
        return evidence.revision(root, record, "breakdown") == run["revision"]
    if tasks is None:
        tasks = read_json(unit_dir(root, record["unit"]) / "tasks.json")
    return _plan_binding(root, record, tasks, task_id, run.get("consumes", [])) == run["plan_input"]


def _fresh(root, record, task_id, run):
    if not _plan_current(root, record, task_id, run):
        raise WorkflowError(
            "Task inputs changed; launch the task again against the current accepted breakdown."
        )
    if "routing" in run and traceability.routing(root, record) != run["routing"]:
        raise WorkflowError(
            "Task traceability routing changed (a unit's design route or parent); refresh its context and launch it again."
        )
    if _hashes(root, run["inputs"]) != run["inputs"]:
        raise WorkflowError(
            "Task supporting inputs changed; refresh its context before accepting the result."
        )
    consumed_paths = sorted(
        set(_task_files(root, run.get("consumes", [])))
        | set(run.get("consumed_files", {}))
    )
    if run.get("status") == "running" and _hashes(root, consumed_paths) != run.get("consumed_files", {}):
        raise WorkflowError(
            "Unexpected interference: task supporting inputs changed (consumed files); refresh its context and revalidate before accepting the result."
        )
    for task_id in run["dependencies"]:
        if record.get("task_runs", {}).get(task_id, {}).get("status") != "completed":
            raise WorkflowError("Task dependency is no longer completed; refresh the assignment.")


def _authoring_guidance(name="repository-grounding.md"):
    path = (
        Path(__file__).resolve().parents[3]
        / "fbk-docs/workflow"
        / name
    )
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise WorkflowError(
            f"Cannot read worker authoring guidance at {path}; restore the installed file and retry."
        ) from exc
    if not text.strip():
        raise WorkflowError(
            f"Worker authoring guidance at {path} is empty; restore the installed file and retry."
        )
    return text


# The chain carries linked requirements, design choices and commitments word for word; the
# rest is the task's own fields and guidance, and stays tight so bloated guidance surfaces.
CHAIN_LIMIT = 64000
CONTEXT_LIMIT = 16000
# A planned task has no worker yet; this stands in for its id at a standard id's 36 characters,
# so a plan that passes breakdown close is not refused at launch over its worker id.
PLANNED_WORKER = "(the worker agent id, set at launch)"


def task_packet(root, record, task_id):
    run = record.get("task_runs", {}).get(task_id)
    if not run:
        raise WorkflowError("Task has no assignment; launch it with task-start first.")
    _fresh(root, record, task_id, run)
    packet, chains = _packet(root, record, task_id, run)
    problem = _oversize(task_id, packet, chains, "launch again")
    if problem:
        raise WorkflowError(problem)
    return packet


def _packet(root, record, task_id, run):
    """The task packet for ``run``, an assignment or a planned task shaped like one, and each
    linked requirement's whole-chain size. Launch and breakdown close both build it here."""
    packet = {
        "unit": record["unit"],
        "task": task_id,
        **{
            k: run[k]
            for k in (
                "description",
                "status",
                "worker_id",
                "outcome",
                "acceptance_refs",
                "input_refs",
                "files",
                "revision",
                "dependencies",
            )
        },
        "return_contract": "Return the observable outcome, exact changed files, check commands with exit codes and evidence, and unresolved issues. Preserve accepted requirements; surface consequential changes.",
        "consumes": run.get("consumes", []),
        "consumed_files": run.get("consumed_files", {}),
        "stage": run.get("stage", "implementation"),
        "verification": run.get("verification"),
        "check_expectations": run.get("check_expectations", []),
        "authoring_guidance": _authoring_guidance(),
    }
    if packet["outcome"] == packet["description"]:
        # The outcome defaults to the description; the packet carries that text once.
        del packet["outcome"]
    if run.get("refactor"):
        # A refactor task improves the structure of the files it owns, which earlier
        # implementation tasks built, and returns its review as the outcome.
        packet["refactor"] = True
        packet["refactor_guidance"] = _authoring_guidance("refactor.md")
        # The rules come from the accepted spec and design, read whole by the worker rather
        # than carried as linked sections, which would not fit the context limit.
        base = unit_dir(root, record["unit"])
        packet["rules_sources"] = [
            path.relative_to(root).as_posix()
            for path in [base / "spec.md", *sorted((base / "design").glob("*.md"))]
            if path.is_file()
        ]
        packet["return_contract"] = (
            "Return the review refactor_guidance asks for as the outcome, the exact changed files, "
            "check commands with exit codes and evidence, and unresolved issues."
        )
    if packet["stage"] == "tests":
        packet["test_authoring_guidance"] = _authoring_guidance("test-authoring.md")
        if evidence.scope(root, record["unit"]).get("test_regions"):
            packet["test_region_guidance"] = _authoring_guidance("test-regions.md")
    packet["traceability"], chains, _ = traceability.task_chain(root, record, task_id, run["acceptance_refs"])
    return packet, chains


def _size(value):
    return len(json.dumps(value, ensure_ascii=False))


def _oversize(task_id, packet, chains, then):
    """Why a task's context is too large, or None. The traceability chain and the rest of the
    packet each have their own limit; a task over both gets one message reporting both. ``then``
    finishes each remedy (what to run again)."""
    chain = packet["traceability"]
    rest = {k: v for k, v in packet.items() if k != "traceability"}
    parts = []
    if _size(chain) > CHAIN_LIMIT:
        sections = sorted(
            (entry for entries in chain.values() for entry in entries), key=lambda e: len(e["text"]), reverse=True
        )[:5]
        parts.append(
            f"Task {task_id}'s traceability chain is {_size(chain):,} characters, over its 64,000-character limit."
            "\nEach linked requirement's chain (its section, design choices and commitments):\n"
            + "\n".join(f"- {ref}: {n:,} characters" for ref, n in chains)
            + "\nLargest linked sections:\n"
            + "\n".join(f"- {e['ref']}: {len(e['text']):,} characters" for e in sections)
            + "\nSplit the task so each part links fewer requirements, or tighten an oversized item section "
            f"in its accepted document, then {then}."
        )
    if _size(rest) > CONTEXT_LIMIT:
        fields = sorted(rest, key=lambda k: _size(rest[k]), reverse=True)[:5]
        parts.append(
            f"Task {task_id}'s context outside its traceability chain is {_size(rest):,} characters, "
            "over its 16,000-character limit.\nLargest fields:\n"
            + "\n".join(f"- {k}: {_size(rest[k]):,} characters" for k in fields)
            + "\nShorten the task's own fields (description, verification, check expectations, references) "
            f"or split the task, then {then}. If the shared guidance alone is the bulk, report that as a "
            "Firebreak defect."
        )
    return "\n".join(parts) or None


def planned_oversize(root, record, tasks):
    """Breakdown close's size check: each task's context, built from tasks.json as launch would
    build it, against both limits. Returns one refusal naming every task that is oversized or
    whose context cannot be built, or None.
    Launch-only values take what launch would give where known; the worker is a placeholder, and
    a consumed file a later task produces adds no hash."""
    revision = evidence.revision(root, record, "breakdown")
    authoritative = _authoritative(root, record)
    problems = []
    for task in tasks:
        try:
            problem = _planned_problem(root, record, task, revision, authoritative)
        except WorkflowError as exc:
            problem = f"Task {task['id']}'s context cannot be built: {exc}"
        if problem:
            problems.append(problem)
    if not problems:
        return None
    return (
        f"Breakdown cannot close: {len(problems)} task context(s) are over a size limit "
        "or cannot be built.\n\n" + "\n\n".join(problems)
    )


def _planned_problem(root, record, task, revision, authoritative):
    """Why one planned task's context is too large, or None."""
    acceptance_refs = list(dict.fromkeys(task.get("acceptance_refs", [])))
    input_refs = task.get("input_refs", acceptance_refs)
    if not isinstance(input_refs, list) or any(not isinstance(r, str) or not r.strip() for r in input_refs):
        raise WorkflowError("its input_refs must be a list of nonempty file references.")
    input_refs = list(dict.fromkeys(input_refs))
    # Each reference's path counts, including a future input a later task produces; launch
    # checks the references themselves once they resolve.
    paths = [_reference_target(root, ref)[0].relative_to(root).as_posix() for ref in input_refs]
    consumes = list(dict.fromkeys([
        *task.get("consumes", []),
        *(p for p in paths if p not in authoritative and not evidence.matches(p, task["files"])),
    ]))
    hashes = _hashes(root, _task_files(root, consumes))
    run = {
        "description": task.get("description"),
        "stage": task.get("stage", "implementation"),
        **({"refactor": True} if task.get("refactor") else {}),
        "verification": task.get("verification"),
        "check_expectations": task.get("check_expectations", []),
        "status": "running",
        "worker_id": PLANNED_WORKER,
        "outcome": task.get("outcome") or task.get("description"),
        "acceptance_refs": acceptance_refs,
        "input_refs": input_refs,
        "files": task["files"],
        "revision": revision,
        "consumes": consumes,
        "consumed_files": {p: h for p, h in hashes.items() if h is not None},
        "dependencies": {d: {} for d in task.get("depends_on", [])},
    }
    packet, chains = _packet(root, record, task["id"], run)
    return _oversize(task["id"], packet, chains, "close breakdown again")


def _authoritative(root, record):
    """The accepted artifacts and sourced decisions a task's acceptance references may point to."""
    authoritative = set(evidence.subject(root, record, "breakdown"))
    if record.get("parent"):
        authoritative.add(f".fbk/{record['parent']}/spec.md")
    authoritative.update(decisions.source_paths(root, record, "breakdown"))
    return authoritative


def start_task(
    root,
    record,
    session,
    task_id,
    worker_id,
    *,
    outcome=None,
    acceptance_refs=None,
    input_refs=None,
):
    engine.ownership(record, session)
    if record.get("pending_repair"):
        raise WorkflowError("Finish or recover-repair before task handoffs.")
    if record.get("open_phase") == "breakdown":
        raise WorkflowError(
            f"Task {task_id} cannot start while breakdown is open: breakdown writes tasks only, and every task, "
            "test or implementation, runs in implement. Close breakdown, then enter implement to start it."
        )
    if (
        record.get("owner") != session
        or record.get("open_phase") != "implement"
        or any(p.get("pending") for p in record["phases"].values())
    ):
        raise WorkflowError(
            "Enter implementation and finish any close before assigning tasks."
        )
    if not isinstance(worker_id, str) or not worker_id.strip():
        raise WorkflowError("Task launch needs a worker identity.")
    if worker_id == session:
        raise WorkflowError(
            "Tasks run in subagents; launch a subagent and assign the task to its agent id, not the lead session."
        )
    accepted = record["phases"]["breakdown"]["evidence"]
    revision = evidence.revision(root, record, "breakdown")
    if not accepted or accepted["revision"] != revision:
        raise WorkflowError("Task launch requires the current accepted breakdown.")
    tasks = read_json(unit_dir(root, record["unit"]) / "tasks.json")
    task = next((t for t in tasks if t["id"] == task_id), None)
    if not task:
        raise WorkflowError("Task is missing from the accepted breakdown.")
    from .test_preparation import check_listed_paths, check_locked_tests

    # Before the stage is read: a changed locked test makes the checkpoint stale, and the
    # refusal must name the test, not the stage.
    check_locked_tests(root, record, session, task_id, "start")
    stage = task.get("stage", "implementation")
    current = engine.implement_stage(root, record)
    if stage == "tests" and current == "writing-code":
        raise WorkflowError(
            f"Task {task_id} writes tests, and the tests are locked; obtain an unlock-test approval for the tests it must rework before starting it."
        )
    if stage != "tests" and current != "writing-code":
        raise WorkflowError(
            f"Task {task_id} is an implementation task, and the unit is {current}; finish the test tasks and pass "
            "test-checkpoint, which reviews and locks the tests, before starting it."
        )
    declared = evidence.scope(root, record["unit"])
    check_listed_paths(root, task, declared, evidence.declared_kinds(declared))
    runs = record.setdefault("task_runs", {})
    if runs.get(task_id, {}).get("status") == "running":
        raise WorkflowError(
            "Task already has a running assignment; finish its handoff before relaunching."
        )
    files = task["files"]
    for other in runs.values():
        if other.get("status") == "running" and (
            other["worker_id"] == worker_id or ownership_overlaps(files, other["files"])
        ):
            raise WorkflowError(
                "Running tasks require distinct workers and nonoverlapping file ownership."
            )
    # Launch may add relevant context, but cannot discard the accepted task's
    # intent or requirement references to make a smaller packet.
    specs = traceability.requirement_specs(root, record)

    def references(refs, name, deferred=None):
        try:
            return _references(root, refs, name, specs, deferred)
        except WorkflowError as exc:
            raise WorkflowError(f"Task {task_id}: {exc}") from exc

    if acceptance_refs is not None:
        references(acceptance_refs, "acceptance_refs")
    acceptance_refs = list(dict.fromkeys([*task.get("acceptance_refs", []), *(acceptance_refs or [])]))
    # Input references keep the line and heading checks, except entries the requirement
    # check already judges as acceptance references.
    if input_refs is not None:
        references(input_refs, "input_refs", acceptance_refs)
    input_refs = list(dict.fromkeys([*task.get("input_refs", acceptance_refs), *(input_refs or [])]))
    acceptance_paths = references(acceptance_refs, "acceptance_refs")
    authoritative = _authoritative(root, record)
    if set(acceptance_paths) - authoritative:
        raise WorkflowError(
            "Task acceptance references must point to accepted artifacts or sourced decisions."
        )
    paths = acceptance_paths + (references(input_refs, "input_refs", acceptance_refs) if input_refs else [])
    # Governing references stay immutable; consumed sources bind this assignment. Every
    # document the traceability chain is read from binds it too, a parent's included.
    _, _, chain_sources = traceability.task_chain(root, record, task_id, acceptance_refs)
    inputs = evidence.file_hashes(
        root, list(dict.fromkeys([*(p for p in paths if p in authoritative), *chain_sources]))
    )
    consumes = list(dict.fromkeys([
        *task.get("consumes", []),
        *(p for p in paths if p not in authoritative and not evidence.matches(p, files)),
    ]))
    consumed_files = _hashes(root, _task_files(root, consumes))
    if any(value is None for value in consumed_files.values()) or any(not evidence.expand(root, [p]) for p in consumes):
        raise WorkflowError(f"Task {task_id} consumed input is missing; finish its producer before launch: " + ", ".join(p for p in consumes if not evidence.expand(root, [p])))
    for other in runs.values():
        if other.get("status") == "running" and (
            ownership_overlaps(files, list(other.get("inputs", {})) + other.get("consumes", []))
            or ownership_overlaps(consumes + list(inputs), other["files"])
        ):
            raise WorkflowError("Running writer and consumer tasks conflict; finish the dependency handoff before launch.")
    dependencies = {}
    for dependency in task.get("depends_on", []):
        previous = runs.get(dependency, {})
        if previous.get("status") != "completed":
            raise WorkflowError("Finish dependency tasks before launching this task.")
        dependencies[dependency] = {}
    from .task_graph import follows

    relevant_paths = set(consumed_files) | set(_task_files(root, files))
    for previous_id, previous in runs.items():
        if previous.get("status") == "completed" and follows(tasks, task_id, previous_id):
            _verify_completed(root, record, previous_id, paths=relevant_paths)
    outcome = outcome or task.get("outcome") or task["description"]
    if not isinstance(outcome, str) or not outcome.strip():
        raise WorkflowError("Task launch needs an observable outcome.")
    # While an unlock of a test it owns is outstanding, a test task's run uses the
    # approved rework commands in place of the ones tasks.json declares.
    rework = engine.rework_commands(record, files) if stage == "tests" else None
    runs[task_id] = {
        "assignment_id": str(uuid.uuid4()),
        "started_at": now(),
        "description": task["description"],
        "stage": stage,
        **({"refactor": True} if task.get("refactor") else {}),
        "verification": task.get("verification"),
        "check_expectations": task.get("check_expectations", []) if rework is None else rework,
        **({"rework": True} if rework is not None else {}),
        "status": "running",
        "worker_id": worker_id,
        "outcome": outcome,
        "acceptance_refs": acceptance_refs,
        "input_refs": input_refs,
        "files": files,
        "revision": revision,  # whole-plan digest, kept for audit
        "plan_input": _plan_binding(root, record, tasks, task_id, consumes),
        "inputs": inputs,
        "routing": traceability.routing(root, record),
        "consumes": consumes,
        "consumed_files": consumed_files,
        "dependencies": dependencies,
        "before": _hashes(root, _task_files(root, files)),
    }
    packet = task_packet(root, record, task_id)
    event(
        record,
        "task-started",
        session,
        task=task_id,
        worker=worker_id,
        revision=revision,
        contract=packet,
    )
    save(root, record)
    return packet


def ownership_overlaps(first, second):
    """Permit parallelism only when static path prefixes prove disjoint ownership."""

    def prefix(pattern):
        parts = []
        for part in Path(pattern).parts:
            if any(char in part for char in "*?["):
                break
            parts.append(part)
        return tuple(parts)

    for a in map(prefix, first):
        for b in map(prefix, second):
            if a[: len(b)] == b or b[: len(a)] == a:
                return True
    return False


def _prepare_task_return(
    root, record, session, task_id, *, changed_files, checks, unresolved, outcome
):
    engine.ownership(record, session)
    if record.get("pending_repair"):
        raise WorkflowError("Finish or recover-repair before task handoffs.")
    if (
        record.get("owner") != session
        or record.get("open_phase") != "implement"
        or any(p.get("pending") for p in record["phases"].values())
    ):
        raise WorkflowError(
            "Resume implementation and finish any close before returning a task."
        )
    run = record.get("task_runs", {}).get(task_id)
    if not run or run["status"] != "running":
        raise WorkflowError("Task has no running assignment to finish.")
    from .test_preparation import check_locked_tests

    # Checked before the task's checks run and again after, when the return is committed.
    check_locked_tests(root, record, session, task_id, "finish")
    _fresh(root, record, task_id, run)
    if (
        not isinstance(changed_files, list)
        or any(not isinstance(p, str) for p in changed_files)
        or len(set(changed_files)) != len(changed_files)
    ):
        raise WorkflowError("Task return needs a unique changed-files array.")
    after = _hashes(root, _return_paths(root, record, run))
    actual = {p for p, value in after.items() if run["before"].get(p) != value}
    if set(changed_files) != actual:
        started_at = run.get("started_at") or next(
            (
                e.get("at")
                for e in reversed(record.get("events", []))
                if e.get("event") == "task-started" and e.get("task") == task_id
            ),
            "an unrecorded time",
        )
        unchanged = sorted(set(changed_files) - actual) or ["none"]
        undeclared = sorted(actual - set(changed_files)) or ["none"]
        raise WorkflowError(
            "Task changed-files return does not match its actual owned-file changes. "
            f"Changes are measured from the task-start snapshot taken at {started_at}. "
            f"Declared but unchanged since that snapshot: {', '.join(unchanged)}. "
            f"Changed since that snapshot but not declared: {', '.join(undeclared)}. "
            "Edits made before task-start are already in the snapshot and are declared as nothing."
        )
    if (
        not isinstance(checks, list)
        or not checks
        or any(
            not isinstance(c, dict)
            or not isinstance(c.get("argv"), list)
            or not c["argv"]
            or any(not isinstance(a, str) or not a for a in c["argv"])
            or type(c.get("exit_code")) is not int
            or not isinstance(c.get("evidence"), str)
            or not c["evidence"].strip()
            for c in checks
        )
    ):
        raise WorkflowError(
            "Task return needs check commands, exit codes, and concrete evidence."
        )
    if (
        not isinstance(unresolved, list)
        or any(not isinstance(v, str) or not v.strip() for v in unresolved)
        or not isinstance(outcome, str)
        or not outcome.strip()
    ):
        raise WorkflowError(
            "Task return needs an outcome and an unresolved-issues array."
        )
    return run, after


def _execute_task_checks(root, expectations):
    from . import review
    from .store import project_config

    timeout = review.bounded_number(project_config(root), "check_timeout", 300, 3600)
    results = []
    for expectation in expectations:
        result = review.run_command(expectation["argv"], root, timeout)
        for stream in ("stdout", "stderr"):
            result[stream] = result[stream][-2000:]
        results.append(result)
    return results


def complete_task(root, unit, session, task_id, **report):
    """Verify outside the project lock, then commit only current task evidence."""
    from .store import load, transaction

    with transaction(root):
        record = load(root, unit)
        run, files = _prepare_task_return(root, record, session, task_id, **report)
        assignment = json.loads(json.dumps(run))
    try:
        results = _execute_task_checks(root, assignment.get("check_expectations", []))
    except Exception as exc:
        # A check that timed out or failed to run still leaves a locked test to compare.
        with transaction(root):
            _check_locks_after_failure(root, load(root, unit), session, task_id, exc)
        raise
    with transaction(root):
        record = load(root, unit)
        return finish_task(
            root, record, session, task_id,
            _verification={"assignment": assignment, "files": files, "checks": results},
            **report,
        )


def _check_locks_after_failure(root, record, session, task_id, exc):
    """When a task's completion checks fail to run, compare the locks anyway, keeping the
    failure in the refusal; a locked test changed by then is a lock violation."""
    from .test_preparation import check_locked_tests

    check_locked_tests(root, record, session, task_id, "finish", failure=str(exc))


def finish_task(
    root, record, session, task_id, *, changed_files, checks, unresolved, outcome,
    _verification=None,
):
    """Commit a task return; public callers use complete_task for unlocked checks."""
    run, after = _prepare_task_return(
        root, record, session, task_id, changed_files=changed_files,
        checks=checks, unresolved=unresolved, outcome=outcome,
    )
    if _verification is not None:
        if run != _verification["assignment"] or after != _verification["files"]:
            raise WorkflowError("Task assignment or outputs changed while completion checks ran; inspect changes and retry.")
        verified_checks = _verification["checks"]
    else:
        try:
            verified_checks = _execute_task_checks(root, run.get("check_expectations", []))
        except Exception as exc:
            _check_locks_after_failure(root, record, session, task_id, exc)
            raise
        from .test_preparation import check_locked_tests

        check_locked_tests(root, record, session, task_id, "finish")
        _fresh(root, record, task_id, run)
        if _hashes(root, _return_paths(root, record, run)) != after:
            raise WorkflowError("Task outputs changed while completion checks ran; inspect changes and retry.")
    # A test task whose tests are all unchanged since the previous accepted checkpoint
    # carries that checkpoint's red forward: code built since may make a red check pass,
    # and correct code is never undone to recreate red. Every other expectation still
    # applies; the checkpoint reviewer judges.
    carried = None if run.get("rework") or run.get("stage") != "tests" else carried_forward(root, record, run["files"])
    run["return"] = {
        "outcome": outcome,
        "changed_files": changed_files,
        "files": after,
        "checks": checks,
        "unresolved": unresolved,
        "verified_checks": verified_checks,
        "evidence_kind": "Worker reports plus runtime-executed accepted task checks; final close runs whole-unit checks.",
        **({"carried_forward_red": carried} if carried else {}),
    }
    if len(json.dumps(run["return"], ensure_ascii=False)) > 16000:
        raise WorkflowError(
            "Task return exceeds 16,000 characters; keep verbose logs in runtime files and return concise, source-linked evidence."
        )
    from .test_preparation import keep_verified_return

    keep_verified_return(root, record, task_id, run)
    expectations = run.get("check_expectations", [])
    def expected(check):
        return next((c["exit_code"] for c in expectations if c["argv"] == check["argv"]), 0)

    def met(check):
        # Carried-forward red adds one outcome: a red check that now passes.
        return evidence.exit_matches(expected(check), check["exit_code"]) or (
            carried and check["exit_code"] == 0 and expected(check) != 0)

    missing_checks = any(not any(c["argv"] == e["argv"] for c in checks) for e in expectations)
    run["status"] = (
        "needs-attention"
        if unresolved or not expectations or missing_checks
        or not all(met(c) for c in checks + verified_checks)
        else "completed"
    )
    event(
        record,
        "task-returned",
        session,
        task=task_id,
        status=run["status"],
        result=run["return"],
    )
    save(root, record)
    return {"task": task_id, "status": run["status"], **run["return"]}


def carried_forward(root, record, owned):
    """The red a test task's owned tests carry from the previous accepted checkpoint: when
    that checkpoint exists and every scoped test the task owns is unchanged since it, the
    checkpoint's time and those tests; otherwise None."""
    accepted = engine.accepted_checkpoint(record)
    declared = evidence.scope(root, record["unit"])
    mine = evidence.held_tests(declared, evidence.test_fingerprints(
        root, declared, [path for path in evidence.test_files(root, declared) if evidence.matches(path, owned)]))
    before = {path: value for path, value in evidence.held_tests(declared, (accepted or {}).get("tests", {})).items()
              if evidence.matches(path, owned)}
    from .test_preparation import retargeted_since

    if not mine or mine != before or retargeted_since(root, accepted, mine):
        return None
    return {"checkpoint_at": accepted["at"], "tests": sorted(mine)}


def _verify_completed(root, record, task_id, *, paths=None):
    from .task_graph import follows

    runs = record.get("task_runs", {})
    run = runs[task_id]
    _fresh(root, record, task_id, run)
    tasks = read_json(unit_dir(root, record["unit"]) / "tasks.json")
    expected = {**run.get("consumed_files", {}), **run["return"]["files"]}
    for path in _task_files(root, run["files"] + run.get("consumes", [])):
        expected.setdefault(path, None)
    if paths is not None:
        expected = {path: value for path, value in expected.items() if path in paths}
    actual = _hashes(root, expected)
    for path, previous in expected.items():
        if actual[path] == previous:
            continue
        superseded = any(
            other_id != task_id
            and other.get("status") == "completed"
            and _plan_current(root, record, other_id, other, tasks)
            and follows(tasks, other_id, task_id)
            and evidence.matches(path, other["files"])
            and path in other["return"]["files"]
            and other["return"]["files"][path] == actual[path]
            for other_id, other in runs.items()
        )
        if not superseded:
            raise WorkflowError(
                "Unexpected interference: task evidence changed after completion without a completed dependent task; refresh the handoff."
            )


def task_run_blockers(root, record):
    """Report current handoff problems without changing assignment provenance."""
    runs = record.get("task_runs", {})
    problems = []
    if record.get("open_phase") == "implement":
        tasks = read_json(unit_dir(root, record["unit"]) / "tasks.json")
        for task in tasks:
            if task.get("stage", "implementation") == "implementation" and task["id"] not in runs:
                problems.append({"task": task["id"], "reason": "Implementation task is unassigned.",
                                 "next": "Run task-start, complete the work, and task-finish before closing."})
    lead_sessions = {e.get("session") for e in record.get("events", [])} - {None}
    for task_id, run in runs.items():
        if run.get("worker_id") in lead_sessions:
            problems.append({"task": task_id, "reason": "Task ran in the lead session instead of a subagent.",
                             "next": "Run task-start for a subagent, have it redo and verify the work, and task-finish."})
            continue
        fresh = False
        try:
            _fresh(root, record, task_id, run)
            fresh = True
            if run["status"] != "completed":
                raise WorkflowError("Finish assigned tasks and resolve their handoffs before closing.")
            _verify_completed(root, record, task_id)
        except WorkflowError as exc:
            problems.append({
                "task": task_id,
                "reason": str(exc),
                "next": (
                    "Finish the current task and submit task-finish with its required checks."
                    if fresh and run["status"] == "running" else
                    "Stop the worker, task-cancel this stale running assignment, then task-start "
                    "against current inputs, inspect existing work, rerun checks, and task-finish."
                    if run["status"] == "running" else
                    "Run task-start again against current inputs, inspect existing work, rerun checks, and task-finish."
                ),
            })
    return problems


def verify_task_runs(root, record):
    problems = task_run_blockers(root, record)
    if problems:
        raise WorkflowError("Task handoffs block closing: " + " ".join(
            f"{item['task']}: {item['reason']} {item['next']}" for item in problems
        ))


def check_task_write(record, relative, worker_id, session):
    runs = record.get("task_runs", {})
    assigned = [
        r
        for r in runs.values()
        if r["status"] == "running" and r["worker_id"] == (worker_id or session)
    ]
    if not worker_id:
        raise WorkflowError(
            "The lead does not edit project files during implementation; launch a subagent with a task assignment."
        )
    if not assigned:
        raise WorkflowError(
            "Assign this worker a revision-bound task before implementation writes."
        )
    if assigned and not any(evidence.matches(relative, r["files"]) for r in assigned):
        raise WorkflowError("File is outside this worker's assigned task ownership.")
    for run in runs.values():
        if run["status"] == "running" and run["worker_id"] != (worker_id or session) and evidence.matches(
            relative, list(run.get("inputs", {})) + run.get("consumes", [])
        ):
            raise WorkflowError("File is consumed by another running task; finish its handoff before editing this input.")
        if (
            run["status"] == "running"
            and run["worker_id"] != (worker_id or session)
            and evidence.matches(relative, run["files"])
        ):
            raise WorkflowError(
                "File belongs to another running task; finish its handoff before editing."
            )


def cancel_task(root, record, session, task_id, reason):
    """Retain failed/stale work and allow a deliberate fresh assignment."""
    engine.ownership(record, session)
    if not isinstance(reason, str) or not reason.strip():
        raise WorkflowError(
            "Task cancellation needs a reason describing the remaining work."
        )
    run = record.get("task_runs", {}).get(task_id)
    if not run or run.get("status") != "running":
        raise WorkflowError("Only a running task can be canceled.")
    if (
        record.get("pending_repair")
        or any(p.get("pending") for p in record["phases"].values())
        or record.get("workers", {}).get(run["worker_id"])
    ):
        raise WorkflowError(
            "Stop the task worker and finish pending operations before canceling its assignment."
        )
    run["status"] = "needs-attention"
    run["return"] = {
        "unresolved": [reason],
        "outcome": "Assignment canceled; inspect existing changes before relaunch.",
    }
    event(record, "task-canceled", session, task=task_id, reason=reason)
    save(root, record)
    return {"task": task_id, "status": run["status"], "reason": reason}
