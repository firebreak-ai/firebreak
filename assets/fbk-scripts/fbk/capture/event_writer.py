"""Single append path into .fbk-capture/events.jsonl for the metrics plane.

Every producer (hook router, chokepoint, verification hook, code-review gate)
writes through this one function so that all privacy and safety invariants are
enforced in one place rather than scattered across producers.  The spec and
task-reviewer gates do not write events directly — the chokepoint's dispatch
event is the single record for each gate invocation.

The envelope schema has exactly eight fields:
    schema_version  always "1.0"
    event_type      must be in schema.EVENT_TYPES
    timestamp       ISO-8601 UTC
    spec            str or None (present, value null, when no SDL run is active)
    stage           str or None (same null-not-absent rule)
    source          the registered writer name (warn-but-write if unregistered)
    capture_level   "standard" | "full"
    data            the redacted payload dict
"""

import datetime
import json
import os
import sys

from fbk.capture import retention, schema


def write(
    event_type: str,
    source: str,
    data: dict,
    spec,
    stage,
    capture_level: str,
    events_path: str,
) -> None:
    """Append one envelope line to events_path then run the retention prune check.

    Returns None in all cases (success or failure).  Failures are swallowed
    silently — no raise, no stdout.  Warnings (bad event type) go to stderr only.

    Args:
        event_type:     Must be in schema.EVENT_TYPES; otherwise the call is
                        discarded with a stderr warning.
        source:         The registered source name for the envelope.  If source
                        is not in schema.SOURCES, a warning is emitted to stderr
                        but the event is written unchanged (warn-but-write).
        data:           Raw payload dict; redacted by capture_level before write.
        spec:           Current SDL spec name, or None when no run is active.
        stage:          Current SDL stage name, or None when no run is active.
        capture_level:  "standard" strips free-text keys; "full" preserves all.
        events_path:    Absolute path to the JSONL file (the .fbk-capture/ dir
                        is derived as its parent).

    Returns:
        None
    """
    # Vocabulary guard — check BEFORE entering the try/except so the stderr
    # warning always surfaces even though failures inside are silenced.
    if event_type not in schema.EVENT_TYPES:
        print(
            f"event_writer: unknown event_type {event_type!r} — discarding write",
            file=sys.stderr,
        )
        return None

    # Source check — warn-but-write. Unlike the event-type guard above, an
    # unregistered source is surfaced on stderr but the event is still written
    # unchanged: source is provenance, not load-bearing, and dropping a real
    # event over a label would be silent data loss. Wrong-but-registered
    # labels are caught by the per-producer literal pins in the tests, not here.
    if source not in schema.SOURCES:
        print(
            f"event_writer: unregistered source {source!r} — writing anyway",
            file=sys.stderr,
        )

    try:
        capture_dir = os.path.dirname(os.path.abspath(events_path))
        project_root = os.path.dirname(capture_dir)

        # Confinement check: refuse if capture_dir is a symlink pointing outside
        # the project root.
        if os.path.exists(capture_dir):
            real_capture = os.path.realpath(capture_dir)
            real_root = os.path.realpath(project_root)
            # The real capture dir must sit directly under the project root.
            if not real_capture.startswith(real_root + os.sep) and real_capture != real_root:
                return None
            # Also refuse if it is a symlink (realpath differed from abspath).
            if real_capture != os.path.abspath(capture_dir):
                return None
        else:
            # Dir does not yet exist — apply the same confinement the existing-dir
            # branch uses before creating anything, so a symlinked project root
            # cannot place the capture dir (and its files) outside the real tree.
            # realpath resolves symlinks in the existing parent components even
            # though the final capture dir does not exist yet.
            real_root = os.path.realpath(project_root)
            real_capture = os.path.realpath(capture_dir)
            # The resolved capture dir must sit under the real project root.
            if not real_capture.startswith(real_root + os.sep) and real_capture != real_root:
                return None
            # Refuse if a symlink was traversed (realpath differs from abspath).
            if real_capture != os.path.abspath(capture_dir):
                return None
            os.makedirs(capture_dir, exist_ok=True)
            # Write .gitignore with exactly '*' on first creation.
            gitignore_path = os.path.join(capture_dir, ".gitignore")
            if not os.path.exists(gitignore_path):
                with open(gitignore_path, "w") as gi:
                    gi.write("*\n")

        # Central redaction — no caller needs to strip free-text themselves.
        redacted_data = schema.redact(data, capture_level)

        # Build the eight-field envelope. The timestamp shape must stay
        # identical to fbk.state.now_iso() ("+00:00" offset, never "Z"):
        # the report classifier orders events by string comparison and
        # compares event timestamps against state-file park timestamps.
        envelope = {
            "schema_version": "1.0",
            "event_type": event_type,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "spec": spec,
            "stage": stage,
            "source": source,
            "capture_level": capture_level,
            "data": redacted_data,
        }

        # Append exactly one line under the shared lock so the append cannot
        # land inside a concurrent prune's read-modify-write and be lost.
        with retention.file_lock(events_path):
            with open(events_path, "a") as fh:
                fh.write(json.dumps(envelope) + "\n")

        # Best-effort snapshot of locked specs; the prune re-reads the set under
        # its lock, so a lock file created after this read but before the prune
        # acquires the lock is still honored (IF-S-06).
        protect_specs = retention._locked_specs(capture_dir)

        # Prune after append — wired to retention module, never raises.
        retention.prune_if_needed(events_path, retention.DEFAULT_MAX_BYTES, protect_specs)

    except Exception:
        # Fail-silent: swallow everything, never raise, never write stdout.
        pass

    return None
