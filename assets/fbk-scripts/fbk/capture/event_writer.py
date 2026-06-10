"""Single append path into .fbk-capture/events.jsonl for the metrics plane.

Every producer (hook router, chokepoint, verification hook, code-review gate,
spec/task-reviewer gates) writes through this one function so that all
privacy and safety invariants are enforced in one place rather than scattered
across producers.

The envelope schema has exactly eight fields:
    schema_version  always "1.0"
    event_type      must be in schema.EVENT_TYPES
    timestamp       ISO-8601 UTC
    spec            str or None (present, value null, when no SDL run is active)
    stage           str or None (same null-not-absent rule)
    source          the registered writer name
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
        source:         The registered source name for the envelope.
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
            # Dir does not yet exist — confirm the parent (project root) is real
            # and then create the capture dir there.
            real_root = os.path.realpath(project_root)
            os.makedirs(capture_dir, exist_ok=True)
            # Write .gitignore with exactly '*' on first creation.
            gitignore_path = os.path.join(capture_dir, ".gitignore")
            if not os.path.exists(gitignore_path):
                with open(gitignore_path, "w") as gi:
                    gi.write("*\n")

        # Central redaction — no caller needs to strip free-text themselves.
        redacted_data = schema.redact(data, capture_level)

        # Build the eight-field envelope.
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

        # Append exactly one line.
        with open(events_path, "a") as fh:
            fh.write(json.dumps(envelope) + "\n")

        # Resolve the set of protected specs from empty lock files under
        # <capture_dir>/locked/.  An absent locked/ dir yields an empty set.
        protect_specs = _locked_specs(capture_dir)

        # Prune after append — wired to retention module, never raises.
        retention.prune_if_needed(events_path, retention.DEFAULT_MAX_BYTES, protect_specs)

    except Exception:
        # Fail-silent: swallow everything, never raise, never write stdout.
        pass

    return None


def _locked_specs(capture_dir: str) -> set:
    """Return the set of spec names with an empty lock file under locked/.

    An absent or unreadable locked/ directory yields an empty set.
    """
    locked_dir = os.path.join(capture_dir, "locked")
    if not os.path.isdir(locked_dir):
        return set()

    specs = set()
    try:
        for entry in os.listdir(locked_dir):
            entry_path = os.path.join(locked_dir, entry)
            if os.path.isfile(entry_path) and os.path.getsize(entry_path) == 0:
                specs.add(entry)
    except OSError:
        pass

    return specs
