"""Size-cap retention pruner for the metrics-plane events file.

Drops oldest lines once .fbk-capture/events.jsonl exceeds a byte cap, with
special treatment for lines whose spec is baseline-locked: locked lines are
never dropped under normal pruning, but cannot grow without bound — if locked
bytes alone exceed a defined fraction of the cap, the oldest locked lines are
also dropped and a durable sentinel is written to surface the condition.

Any failure leaves the original file byte-intact: all new content is built
fully in memory and written in a single operation at the very end, so a
failure before that write leaves the original file untouched.
"""

import json
import os

# Default byte cap for the events file (~5 MB).
DEFAULT_MAX_BYTES = 5 * 1024 * 1024

# Fraction of the cap that protected (locked) bytes may occupy.
# 0.5 keeps protected baselines from monopolizing the file while leaving
# headroom for current-session capture.
PROTECTED_FRACTION = 0.5


def prune_if_needed(events_path: str, max_bytes: int, protect_specs: set[str]) -> None:
    """Prune events_path to at most max_bytes, protecting locked-spec lines.

    - If the file does not exist or is already <= max_bytes, returns without
      touching the file.
    - Lines whose ``spec`` field is in protect_specs are protected; all others
      are unprotected.  A line that fails JSON parsing is treated as unprotected.
    - Normal pruning: keeps ALL protected lines and as many of the newest
      unprotected lines as fit within max_bytes, dropping oldest unprotected
      lines first.
    - Over-ceiling pruning: if protected bytes alone exceed
      max_bytes * PROTECTED_FRACTION after dropping all unprotected lines, the
      oldest protected lines are also dropped until protected bytes are at or
      under that ceiling; in that case the sentinel
      .fbk-capture/.retention-warning is written as a sibling of events_path.
    - The sentinel is written only when locked lines are actually dropped; a
      normal prune (unprotected lines only) must NOT create the sentinel.
    - Any exception is silently swallowed; the original file is never partially
      overwritten.

    Args:
        events_path: Absolute or relative path to the events JSONL file.
        max_bytes: Maximum allowed file size in bytes.
        protect_specs: Set of spec names whose lines must not be dropped under
            normal pruning conditions.
    """
    try:
        # Early exit: file absent or already within cap.
        if not os.path.exists(events_path):
            return
        if os.path.getsize(events_path) <= max_bytes:
            return

        # Read all raw lines preserving order (oldest first = top of file).
        with open(events_path, "rb") as fh:
            raw_lines = fh.readlines()

        # Classify each line as protected or unprotected.
        protected_lines = []
        unprotected_lines = []
        for raw in raw_lines:
            stripped = raw.strip()
            if not stripped:
                # Skip blank lines; treat as unprotected for accounting.
                unprotected_lines.append(raw)
                continue
            try:
                obj = json.loads(stripped)
                spec = obj.get("spec", "")
            except (json.JSONDecodeError, AttributeError):
                spec = ""

            if spec in protect_specs:
                protected_lines.append(raw)
            else:
                unprotected_lines.append(raw)

        protected_bytes = sum(len(b) for b in protected_lines)
        protected_ceiling = int(max_bytes * PROTECTED_FRACTION)

        # Determine whether we need to drop locked lines past the ceiling.
        dropped_locked = False

        if protected_bytes > protected_ceiling:
            # Protected lines alone exceed the ceiling; drop oldest locked lines
            # until protected bytes are at or under the ceiling.
            # oldest first in protected_lines (list order = file order)
            while protected_lines and protected_bytes > protected_ceiling:
                removed = protected_lines.pop(0)
                protected_bytes -= len(removed)
                dropped_locked = True

        # Now fit unprotected lines: keep ALL protected lines plus as many of
        # the newest unprotected lines as fit within max_bytes.
        current_protected_bytes = sum(len(b) for b in protected_lines)
        remaining_budget = max_bytes - current_protected_bytes

        if remaining_budget < 0:
            # Edge case: protected lines alone still exceed cap even after
            # ceiling enforcement; keep at least one protected line.
            protected_lines = protected_lines[-1:]
            current_protected_bytes = sum(len(b) for b in protected_lines)
            remaining_budget = max_bytes - current_protected_bytes

        # Keep newest unprotected lines that fit (unprotected_lines is oldest-first,
        # so we iterate from the end).
        kept_unprotected = []
        budget = remaining_budget
        for raw in reversed(unprotected_lines):
            if budget >= len(raw):
                kept_unprotected.append(raw)
                budget -= len(raw)
            # Oldest lines that don't fit are simply omitted.

        # Reverse to restore chronological (oldest-first) order.
        kept_unprotected.reverse()

        # Merge protected and unprotected lines back into original file order.
        # Walk the original line list and include only lines that survived.
        protected_set = set(id(b) for b in protected_lines)
        unprotected_set = set(id(b) for b in kept_unprotected)

        surviving = [
            raw for raw in raw_lines
            if id(raw) in protected_set or id(raw) in unprotected_set
        ]

        new_content = b"".join(surviving)

        # Single write — any failure before this point leaves the original intact.
        with open(events_path, "wb") as fh:
            fh.write(new_content)

        # Write the sentinel only when locked lines were actually dropped.
        if dropped_locked:
            capture_dir = os.path.dirname(events_path)
            sentinel_path = os.path.join(capture_dir, ".retention-warning")
            with open(sentinel_path, "w") as fh:
                fh.write("")

    except Exception:
        # Never raise; leave the original file untouched.
        return
