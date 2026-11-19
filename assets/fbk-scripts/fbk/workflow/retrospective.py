"""Phase observations and retrospective evidence. Readers never write file bodies.

Mutation helpers change the supplied record only; callers hold the project
transaction and save it. References bind content, not authenticity or causality.
CLI indexes are one-based; legacy event_index references are explicitly zero-based.
"""

import copy
import hashlib
import json
import re
from collections import Counter

from .store import WorkflowError, confined, digest, event, now


def mutable(record, session):
    if not isinstance(session, str) or not session.strip():
        raise WorkflowError("A session is required for an attributed audit entry.")
    if record.get("owner") not in (None, session):
        raise WorkflowError("Another session owns this unit; use takeover first.")
    if record.get("pending_repair") or any(
        p.get("pending") for p in record.get("phases", {}).values()
    ):
        raise WorkflowError(
            "Finish or recover the pending operation before recording audit entries."
        )


require_writer = mutable


def pending_phases(record):
    """A phase's latest acceptance needs a subsequent, source-bound observation."""
    latest = {}
    for item in record.get("events", []):
        if item.get("event") == "closed" and item.get("phase"):
            latest[item["phase"]] = item
    covered = {
        (row.get("detection_phase"), ref.get("event_id"))
        for row in record.get("observations", [])
        for ref in row.get("evidence", [])
        if ref.get("type") == "event"
    }
    return [
        {"phase": phase, "event_id": "event:" + digest(item), "session": item.get("session")}
        for phase, item in latest.items()
        if (phase, "event:" + digest(item)) not in covered
    ]


def phase_progress(record):
    pending = pending_phases(record)
    return {
        "pending": pending,
        "retrieve": f"retrospective {record['unit']}",
        "record": f"observation-record {record['unit']} --request <file>",
        "guidance": (
            "Append your own observations for each phase, including its review outcome, "
            "what worked, friction and uncertainty. Read workflow/retrospective.md. "
            "For each pending phase, set detection_phase and cite its event_id. "
            "A clean phase still needs an observation; do not invent a defect."
        ),
    }


def require_phase_observations(record):
    pending = pending_phases(record)
    if pending:
        phases = ", ".join(row["phase"] for row in pending)
        raise WorkflowError(
            f"Record your retrospective observations for {phases} before continuing. "
            f"Run retrospective {record['unit']}, then observation-record {record['unit']} "
            "--request <file>, with detection_phase and the pending acceptance event reference."
        )


def _capture(root, unit):
    from . import telemetry

    health = telemetry.capture_health(root)
    rows, unattributed, malformed = [], 0, 0
    try:
        path = confined(root, ".fbk/runtime/events.jsonl")
        if path.exists():
            with path.open("rb") as stream:
                raw = stream.read(telemetry.CAP_BYTES + 1)
            if len(raw) > telemetry.CAP_BYTES:
                health["scan_truncated"] = True
                raw = raw[: telemetry.CAP_BYTES].rsplit(b"\n", 1)[0]
            for idx, line in enumerate(raw.splitlines()):
                try:
                    row = json.loads(line)
                    if not isinstance(row, dict):
                        raise TypeError("not an object")
                except (TypeError, ValueError, UnicodeError):
                    malformed += 1
                    continue
                if row.get("unit") == unit:
                    rows.append(
                        {"capture_index": idx, "sha256": digest(row), "value": row}
                    )
                elif row.get("unit") is None:
                    unattributed += 1
    except (OSError, WorkflowError):
        health["read_error"] = "Runtime evidence unavailable."
    health.update(
        observed_unit_records=len(rows),
        unattributed_records=unattributed,
        malformed_records=malformed,
        interpretation="Observed lower bounds; unassigned records excluded; total coverage unknown.",
    )
    return rows, health


def validate_reference(root, record, ref, *, _seen=None):
    """Return an immutable content binding; reject missing or stale evidence."""
    if not isinstance(ref, dict):
        raise WorkflowError("Evidence references must be objects.")
    value = None
    if "capture_index" in ref:
        if (
            set(ref) - {"type", "capture_index", "sha256", "snapshot"}
            or type(ref["capture_index"]) is not int
            or not ref.get("sha256")
        ):
            raise WorkflowError(
                "Capture evidence needs a zero-based capture_index and event sha256."
            )
        rows, _ = _capture(root, record["unit"])
        match = next(
            (r for r in rows if r["capture_index"] == ref["capture_index"]), None
        )
        if match is None:
            raise WorkflowError(
                "Runtime capture evidence is unavailable; retained snapshots are historical claims."
            )
        value = match["value"]
        if "snapshot" in ref and ref["snapshot"] != value:
            raise WorkflowError("Capture snapshot does not match the original.")
        binding = {
            "type": "capture",
            "capture_index": ref["capture_index"],
            "sha256": digest(value),
            "snapshot": copy.deepcopy(value),
        }
    elif "event_id" in ref or "event_index" in ref:
        if set(ref) - {"type", "event_id", "event_index", "sha256"}:
            raise WorkflowError("Unknown event reference fields.")
        rows = record.get("events", [])
        if "event_index" in ref:
            idx = ref["event_index"]
            if (
                type(idx) is not int
                or not 0 <= idx < len(rows)
                or not ref.get("sha256")
            ):
                raise WorkflowError(
                    "A zero-based event_index needs its event content sha256."
                )
            value = rows[idx]
        else:
            value = next(
                (e for e in rows if ref["event_id"] == "event:" + digest(e)), None
            )
        if value is None:
            raise WorkflowError("Event reference is missing or stale.")
        binding = {
            "type": "event",
            "event_id": "event:" + digest(value),
            "sha256": digest(value),
        }
        if ref.get("event_id", binding["event_id"]) != binding["event_id"]:
            raise WorkflowError("Event reference is stale.")
        seen = set() if _seen is None else set(_seen)
        identity = binding["event_id"]
        if identity in seen:
            raise WorkflowError("Event evidence contains a reference cycle.")
        seen.add(identity)
        _validate_claim(root, record, value, seen)
    elif "observation_id" in ref:
        if set(ref) - {"type", "observation_id", "sha256"}:
            raise WorkflowError("Unknown observation reference fields.")
        value = next(
            (
                r
                for r in record.get("observations", [])
                if r["id"] == ref["observation_id"]
            ),
            None,
        )
        if value is None:
            raise WorkflowError("Observation reference is missing.")
        seen = set() if _seen is None else set(_seen)
        if "observation:" + value["id"] in seen:
            raise WorkflowError("Observation evidence contains a reference cycle.")
        seen.add("observation:" + value["id"])
        for underlying in value.get("evidence", []):
            validate_reference(root, record, underlying, _seen=seen)
        binding = {
            "type": "observation",
            "observation_id": value["id"],
            "sha256": digest(value),
        }
    elif "path" in ref:
        if set(ref) - {
            "type",
            "path",
            "sha256",
            "start_line",
            "end_line",
        } or not isinstance(ref["path"], str):
            raise WorkflowError("Invalid file evidence reference.")
        path = confined(root, ref["path"])
        if path.name == "state.json":
            raise WorkflowError(
                "Reference workflow events or observations directly instead of mutable state.json."
            )
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise WorkflowError(
                f"Cannot read evidence file {ref['path']}: {exc}"
            ) from exc
        binding = {
            "type": "file",
            "path": ref["path"],
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
        if "start_line" in ref or "end_line" in ref:
            start, end = ref.get("start_line"), ref.get("end_line")
            if (
                type(start) is not int
                or type(end) is not int
                or not 1 <= start <= end <= len(raw.splitlines())
            ):
                raise WorkflowError(
                    "Evidence line range must name existing inclusive lines."
                )
            binding.update(start_line=start, end_line=end)
    else:
        raise WorkflowError("Use an event, file, or observation evidence reference.")
    if ref.get("type", binding["type"]) != binding["type"]:
        raise WorkflowError("Evidence reference type does not match its fields.")
    if "sha256" in ref and ref["sha256"] != binding["sha256"]:
        raise WorkflowError("Evidence content changed; this reference is stale.")
    return binding


def _validate_claim(root, record, event_value, seen=None):
    """Event existence proves recording; typed assessments also need live sources."""
    kind = event_value.get("event")
    if kind == "observation-recorded":
        claim = event_value.get("observation", {})
    elif kind == "improvement-evaluated":
        claim = event_value.get("evaluation", {})
        for path, expected in claim.get("targets", {}).items():
            if expected is None:
                if confined(root, path).exists():
                    raise WorkflowError("Evaluation target changed; evidence is stale.")
            else:
                validate_reference(
                    root, record, {"path": path, "sha256": expected}, _seen=seen
                )
    else:
        return
    for ref in claim.get("evidence", []):
        validate_reference(root, record, ref, _seen=seen)


def _freshness(root, record, section, selected):
    """Report current binding validity separately from the retained historical claim."""
    try:
        if section == "observations":
            validate_reference(root, record, {"observation_id": selected["id"]})
        elif section == "events" and selected.get("event") in {
            "observation-recorded",
            "improvement-evaluated",
        }:
            validate_reference(root, record, {"event_id": "event:" + digest(selected)})
        else:
            return {
                "status": "not-assessed",
                "reason": "Historical record content; source freshness has not been assessed.",
            }
    except WorkflowError as exc:
        reason = str(exc)
        status = (
            "unavailable"
            if any(
                word in reason.lower()
                for word in ("unavailable", "cannot read", "missing")
            )
            else "stale"
        )
        return {
            "status": status,
            "reason": reason[:400],
            "meaning": "Historical claim retained; it is not current assessment proof.",
        }
    return {
        "status": "current",
        "reason": "Cited content bindings currently match; this does not establish correctness or causality.",
    }


def _select_pointer(value, pointer):
    if (
        not isinstance(pointer, str)
        or len(pointer) > 4000
        or (pointer and not pointer.startswith("/"))
    ):
        raise WorkflowError(
            "Use an RFC6901 JSON Pointer beginning with /, or an empty pointer."
        )
    if not pointer:
        return value
    for encoded in pointer[1:].split("/"):
        if re.search(r"~(?![01])", encoded):
            raise WorkflowError("JSON Pointer uses only ~0 and ~1 escapes.")
        key = encoded.replace("~1", "/").replace("~0", "~")
        if isinstance(value, dict) and key in value:
            value = value[key]
        elif (
            isinstance(value, list)
            and re.fullmatch(r"0|[1-9][0-9]*", key)
            and len(key) <= len(str(len(value)))
            and int(key) < len(value)
        ):
            value = value[int(key)]
        # Extension to RFC6901: -1 is the last element, -2 the one before, and so on.
        elif (
            isinstance(value, list)
            and re.fullmatch(r"-[1-9][0-9]*", key)
            and len(key) <= len(str(len(value))) + 1
            and -int(key) <= len(value)
        ):
            value = value[int(key)]
        else:
            raise WorkflowError("JSON Pointer does not identify an existing value.")
    return value


def _suggested_pointers(value, pointer):
    """Pointers that reach the useful part of an oversized selection in one step.

    A phase entry holds its review rounds under /value/rounds; the last round is
    where an exhausted budget's failure lives. A list's last element is -1.
    """
    base = pointer or ""
    if isinstance(value, dict) and isinstance(value.get("value"), dict):
        value, base = value["value"], base + "/value"
    if isinstance(value, dict) and isinstance(value.get("rounds"), list) and value["rounds"]:
        return [base + "/rounds", base + "/rounds/-1"]
    if isinstance(value, list) and value:
        return [base + "/-1"]
    return []


def _pointer_children(value, pointer):
    keys = (
        list(value)
        if isinstance(value, dict)
        else range(len(value))
        if isinstance(value, list)
        else []
    )
    return [
        (pointer or "") + "/" + str(key).replace("~", "~0").replace("/", "~1")
        for key in list(keys)[:12]
    ]


def validate_references(root, record, refs):
    if not isinstance(refs, list) or not 1 <= len(refs) <= 30:
        raise WorkflowError("Supply between 1 and 30 evidence references.")
    return [validate_reference(root, record, ref) for ref in refs]


def record_observation(root, record, session, request):
    """Append an attributed claim and event, under caller's transaction/save."""
    mutable(record, session)
    allowed = {
        "id",
        "observation",
        "evidence",
        "suspected_cause",
        "uncertainty",
        "category",
        "detection_phase",
        "origin_phase",
        "human_question",
    }
    if not isinstance(request, dict) or set(request) - allowed:
        raise WorkflowError("Observation request has unknown fields.")
    for key in ("id", "observation"):
        if (
            not isinstance(request.get(key), str)
            or not request[key].strip()
            or len(request[key]) > (120 if key == "id" else 4000)
        ):
            raise WorkflowError(f"Supply a bounded nonempty {key}.")
    if any(r["id"] == request["id"] for r in record.get("observations", [])):
        raise WorkflowError("Observation ids are immutable; use a new id.")
    for key in ("suspected_cause", "uncertainty", "category"):
        if key in request and (
            not isinstance(request[key], str) or not 1 <= len(request[key]) <= 4000
        ):
            raise WorkflowError(f"Use bounded text for {key}.")
    for key in ("detection_phase", "origin_phase"):
        if key in request and request[key] not in record.get("phases", {}):
            raise WorkflowError(
                f"{key} must name a workflow phase; omit it when unknown."
            )
    row = copy.deepcopy(request)
    row["evidence"] = validate_references(root, record, request.get("evidence"))
    if "human_question" in row:
        question = row["human_question"]
        if not isinstance(question, dict) or set(question) - {
            "classification",
            "decision_refs",
            "reason",
        }:
            raise WorkflowError(
                "Human question attribution needs classification, reason and optional decision_refs."
            )
        classes = {
            "necessary",
            "unnecessary",
            "already-settled",
            "unresolved",
            "unknown",
        }
        if (
            question.get("classification") not in classes
            or not isinstance(question.get("reason"), str)
            or not 1 <= len(question["reason"]) <= 4000
        ):
            raise WorkflowError("Human question classification needs a bounded reason.")
        refs = question.get("decision_refs", [])
        decisions = {d["id"]: d for d in record.get("decisions", [])}
        if not isinstance(refs, list) or any(
            not isinstance(r, str) or r not in decisions for r in refs
        ):
            raise WorkflowError("Question decision_refs must name recorded decisions.")
        if question["classification"] == "already-settled" and not refs:
            raise WorkflowError(
                "An already-settled question needs a recorded decision reference."
            )
        question["decisions"] = [
            {"id": r, "sha256": digest(decisions[r])} for r in refs
        ]
        question["attribution"] = (
            "session claim, not an independently established classification"
        )
    row.update(
        at=now(),
        session=session,
        epistemic_status="agent-reported observation; cause and phase attribution are hypotheses",
    )
    record.setdefault("observations", []).append(row)
    event(record, "observation-recorded", session, observation=row)
    return row


def _sections(record):
    sections = {
        "events": list(record.get("events", [])),
        "observations": list(record.get("observations", [])),
        "decisions": list(record.get("decisions", [])),
        "grants": list(record.get("grants", [])),
    }
    for name, key in (
        ("phases", "phases"),
        ("tasks", "task_runs"),
        ("review_plans", "review_plans"),
    ):
        sections[name] = [
            {"name": k, "value": v} for k, v in record.get(key, {}).items()
        ]
    # File bindings already in observations are discoverable without opening files.
    sections["files"] = [
        r
        for o in record.get("observations", [])
        for r in o.get("evidence", [])
        if r.get("type") == "file"
    ]
    return sections


def _ref(section, value):
    return ("event:" if section == "events" else section + ":") + digest(value)


def _size(value):
    return len(json.dumps(value, ensure_ascii=False))


def packet(root, record, *, section=None, index=None, pointer=None, max_chars=12000, offset=None):
    """Bound JSON output, preserving exact-reference retrieval and explicit omissions.

    `offset` pages a section index: a non-negative offset skips that many entries,
    a negative one starts that many entries before the end. Entries keep their
    one-based index in the full section regardless of paging.
    """
    if type(max_chars) is not int or max_chars < 2000 or max_chars > 100000:
        raise WorkflowError("max_chars must be between 2000 and 100000.")
    if pointer is not None and (section is None or index is None):
        raise WorkflowError("A pointer requires both section and index.")
    if offset is not None and (type(offset) is not int or section is None or index is not None):
        raise WorkflowError("An offset pages one section index; give --section without --index.")
    sections = _sections(record)
    capture, health = _capture(root, record["unit"])
    sections["capture"] = capture
    if section is not None and section not in sections:
        raise WorkflowError("Choose section: " + ", ".join(sections))
    if index is not None and section is None:
        raise WorkflowError("An index requires a section.")
    start = 0
    if offset is not None:
        total = len(sections[section])
        start = offset if offset >= 0 else max(0, total + offset)
        if start > total:
            raise WorkflowError(f"Offset {offset} exceeds the {total} entries in {section}.")
    result = {
        "unit": record["unit"],
        "purpose": "retrospective-only",
        "phase_observations": pending_phases(record),
        "provenance": {
            "record_sha256": digest(
                {k: v for k, v in record.items() if k != "content_hash"}
            ),
            "source": f".fbk/{record['unit']}/state.json",
        },
        "unknowns": [
            "Unrecorded events, question frequency denominators and causal effects are unknown.",
            "Recorded reviews and observations contain agent claims; recording establishes occurrence, not correctness.",
            "Runtime capture is optional and cannot establish complete session history.",
        ],
        "capture_health": health,
        "omissions": [],
        "sections": {},
    }
    if index is not None:
        rows = sections[section]
        if isinstance(index, str) and index.isdecimal():
            index = int(index)
        if type(index) is int:
            selected = rows[index - 1] if 1 <= index <= len(rows) else None
        else:
            selected = next((r for r in rows if _ref(section, r) == index), None)
        if selected is None:
            raise WorkflowError("Evidence index/reference does not exist.")
        result.update(
            section=section,
            ref=_ref(section, selected),
            evidence=copy.deepcopy(
                _select_pointer(selected, pointer) if pointer is not None else selected
            ),
            freshness=_freshness(root, record, section, selected),
        )
        if pointer is not None:
            result["pointer"] = pointer
        if section == "files" and pointer is None:
            binding = validate_reference(root, record, selected)
            try:
                content = confined(root, binding["path"]).read_text()
            except (OSError, UnicodeError) as exc:
                raise WorkflowError(f"Cannot retrieve text evidence: {exc}") from exc
            if "start_line" in binding:
                content = "\n".join(
                    content.splitlines()[
                        binding["start_line"] - 1 : binding["end_line"]
                    ]
                )
            result["content"] = content
        if _size(result) > max_chars:
            result.pop("content", None)
            oversized = result.pop("evidence", None)
            suggested = _suggested_pointers(oversized, pointer)
            result["omissions"].append(
                {
                    "reason": "Selected original exceeds max_chars; select a child with --pointer (a negative list index such as /rounds/-1 counts from the end), raise --max-chars, or read the exact source for an oversized scalar.",
                    "pointer_children": _pointer_children(oversized, pointer),
                    **({"suggested_pointers": suggested,
                        "next": f"retrospective {record['unit']} --section {section} --index {index} --pointer {suggested[-1]}"}
                       if suggested else {}),
                    "ref": result["ref"],
                    "section": section,
                    "index": index,
                }
            )
        if _size(result) > max_chars:
            result["omissions"][-1].pop("pointer_children", None)
            result["omissions"][-1].pop("suggested_pointers", None)
        if _size(result) > max_chars:
            return {
                "ref": result["ref"],
                "section": section,
                "omissions": [
                    {
                        "reason": "Selected metadata exceeds max_chars; use a shorter pointer or a larger max_chars."
                    }
                ],
            }
        return result
    counts = Counter(
        o.get("category", "uncategorized") for o in record.get("observations", [])
    )
    result["observation_summary"] = {
        "total": len(record.get("observations", [])),
        "source_freshness": "Not checked in the index; select an observation to check current, stale, or unavailable sources while retaining the historical claim.",
        "categories": dict(counts.most_common(20)),
        "human_question_classifications": dict(
            Counter(
                o.get("human_question", {}).get("classification", "unclassified")
                for o in record.get("observations", [])
                if "human_question" in o
            )
        ),
        "reported_cross_phase_observations": sum(
            bool(
                o.get("origin_phase")
                and o.get("detection_phase")
                and o["origin_phase"] != o["detection_phase"]
            )
            for o in record.get("observations", [])
        ),
        "denominators": "unknown; neither total questions nor total escaped defects are established",
        "meaning": "Counts of attributed reports, not independently measured defect or unnecessary-question rates.",
    }
    if len(counts) > 20:
        result["omissions"].append(
            {"reason": "Only the 20 most frequent observation categories are shown."}
        )
    names = [section] if section else list(sections)
    # Reserve omission metadata before filling indexes so every missing row is visible.
    for name in names:
        # Paging detail is spelled out on a single-section request; the summary stays terse.
        result["sections"][name] = {
            "total": len(sections[name]),
            **({"order": "oldest-first; index 1 is the earliest entry", "offset": start} if section else {}),
            "entries": [],
            "omitted": len(sections[name]) - start,
            "retrieve": f"retrospective {record['unit']} --section {name} --index N (one-based)"
            + ("; --offset N skips N entries, --offset -N starts N entries before the end" if section else ""),
        }
    result["omissions"].append(
        {
            "reason": "Indexes omit original bodies; select an entry by index or exact ref. File contents and runtime log bodies are omitted from the default packet; capture metadata comes from a bounded scan."
        }
    )
    for name in names:
        dest = result["sections"][name]
        for i, value in enumerate(sections[name][start:], start + 1):
            entry = {"index": i, "ref": _ref(name, value), "sha256": digest(value)}
            for key in (
                "event",
                "at",
                "phase",
                "id",
                "name",
                "category",
                "session",
                "path",
                "capture_index",
            ):
                if isinstance(value.get(key), (str, int, bool)):
                    entry[key] = str(value[key])[:160]
            dest["entries"].append(entry)
            dest["omitted"] -= 1
            if name == "capture":
                entry["capture_sha256"] = value["sha256"]
                entry["event"] = str(value["value"].get("event", "unknown"))[:120]
            if _size(result) > max_chars:
                dest["entries"].pop()
                dest["omitted"] += 1
                break
        # A truncated page names the exact command that continues it; the hint
        # itself must fit, so it may cost the page its last entry.
        while dest["omitted"] > 0:
            dest["next"] = (
                f"retrospective {record['unit']} --section {name} "
                f"--offset {start + len(dest['entries'])}"
            )
            if _size(result) <= max_chars or not dest["entries"]:
                break
            dest["entries"].pop()
            dest["omitted"] += 1
    # Very small bounds or large unit names still produce a bounded, usable envelope.
    if _size(result) > max_chars:
        return {
            "unit": record["unit"][:120],
            "omissions": [
                {
                    "reason": "Summary exceeds max_chars; request one section.",
                    "sections": names,
                }
            ],
        }
    return result
