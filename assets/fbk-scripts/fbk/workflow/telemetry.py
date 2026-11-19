"""Optional bounded capture. Observations never establish complete host coverage."""

import hashlib
import json
import os

from .store import atomic_json, confined, now, project_config

CAP_BYTES = 10_000_000
MAX_EVENT_BYTES = 16_000


def _mark(root, state, reason):
    try:
        atomic_json(
            confined(root, ".fbk/runtime/capture-health.json"),
            {"state": state, "reason": reason, "at": now()},
        )
    except Exception:  # noqa: BLE001 - capture never propagates an error into a workflow decision
        pass


def record(root, item):
    """Never propagate capture errors into workflow decisions."""
    try:
        if project_config(root).get("capture", True) is False:
            return
        path = confined(root, ".fbk/runtime/events.jsonl")
        path.parent.mkdir(parents=True, exist_ok=True)
        data = (
            json.dumps({"schema_version": 1, "at": now(), **item}, ensure_ascii=False)
            + "\n"
        ).encode()
        if len(data) > MAX_EVENT_BYTES:
            _mark(root, "degraded", "An oversized capture record was omitted.")
            return
        # Independent lock: capture never takes or controls the workflow lock.
        import fcntl

        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if os.fstat(fd).st_size + len(data) > CAP_BYTES:
                _mark(
                    root,
                    "capped",
                    "Capture byte limit reached; subsequent records may be absent.",
                )
                return
            if os.write(fd, data) != len(data):
                raise OSError("short capture write")
        finally:
            os.close(fd)
    except Exception:  # noqa: BLE001 - capture never propagates an error into a workflow decision
        _mark(root, "degraded", "A capture write failed; records may be absent.")


def capture_health(root):
    result = {
        "state": "not-observed",
        "complete": False,
        "cap_bytes": CAP_BYTES,
        "coverage": "Best effort only; missing host events cannot be detected.",
    }
    try:
        if project_config(root).get("capture", True) is False:
            return {**result, "state": "disabled"}
        marker = confined(root, ".fbk/runtime/capture-health.json")
        if marker.exists():
            status = json.loads(marker.read_text())
            if status.get("state") in {"degraded", "capped"}:
                return {**result, **status, "complete": False}
        path = confined(root, ".fbk/runtime/events.jsonl")
        size = path.stat().st_size if path.exists() else 0
        result.update(
            bytes=size,
            state="capped"
            if size >= CAP_BYTES
            else "recording"
            if size
            else "not-observed",
        )
    except Exception:  # noqa: BLE001 - capture never propagates an error into a workflow decision
        result.update(state="unknown", reason="Capture health could not be read.")
    return result


def record_context(
    root, *, kind, packet, session, unit=None, task=None, section=None, worker=None
):
    """Hash canonical JSON; retain only identity, size, and numeric omission metadata."""
    try:
        data = json.dumps(
            packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
        omissions = packet.get("omitted", {}) if isinstance(packet, dict) else {}
        omissions = dict(omissions)
        if isinstance(packet, dict) and isinstance(packet.get("omitted_findings"), int):
            omissions["findings"] = packet["omitted_findings"]
        metadata = {
            key: packet[key]
            for key in ("revision", "phase")
            if isinstance(packet, dict)
            and isinstance(packet.get(key), str)
            and len(packet[key]) <= 256
        }
        record(
            root,
            {
                **metadata,
                "delivery": "emitted; consumption unverified",
                "event": "context-delivered",
                "kind": kind,
                "session": session,
                "unit": unit,
                "task": task,
                "section": section,
                "worker": worker
                or (packet.get("worker_id") if isinstance(packet, dict) else None),
                "packet_version": 1,
                "hash_encoding": "canonical-json-utf8-v1",
                "sha256": hashlib.sha256(data).hexdigest(),
                "size_bytes": len(data),
                "omitted": {
                    k: int(v)
                    for k, v in omissions.items()
                    if isinstance(v, (int, bool)) and v >= 0
                },
            },
        )
    except Exception:  # noqa: BLE001 - capture never propagates an error into a workflow decision
        _mark(root, "degraded", "Context metadata capture failed.")
