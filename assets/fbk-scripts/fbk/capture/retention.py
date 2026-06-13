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

import contextlib
import json
import os

try:
    import fcntl
except ImportError:  # pragma: no cover — non-Unix fallback
    fcntl = None  # type: ignore[assignment]

# Default byte cap for the events file (~5 MB).
DEFAULT_MAX_BYTES = 5 * 1024 * 1024

# Fraction of the cap that protected (locked) bytes may occupy.
# 0.5 keeps protected baselines from monopolizing the file while leaving
# headroom for current-session capture.
PROTECTED_FRACTION = 0.5


def _lock_path(events_path: str) -> str:
    """Return the sibling advisory-lock path for an events file."""
    return os.path.join(os.path.dirname(os.path.abspath(events_path)), ".events.lock")


@contextlib.contextmanager
def file_lock(events_path: str):
    """Hold an exclusive advisory lock that serialises appends against prunes.

    A prune reads the whole file then rewrites it; an append adds a line at the
    end.  If an append lands between a prune's read and its rewrite, the rewrite
    overwrites the appended line.  Every append and every prune takes this lock
    so the two never overlap.

    Best-effort: if locking is unavailable (no fcntl, or the lock file cannot be
    opened) the body still runs, unlocked, rather than dropping the write.
    """
    lock_fp = None
    if fcntl is not None:
        try:
            lock_fp = open(_lock_path(events_path), "w")
            fcntl.flock(lock_fp, fcntl.LOCK_EX)
        except Exception:
            if lock_fp is not None:
                lock_fp.close()
            lock_fp = None
    try:
        yield
    finally:
        if lock_fp is not None:
            try:
                fcntl.flock(lock_fp, fcntl.LOCK_UN)
            except Exception:
                pass
            lock_fp.close()


def _locked_specs(capture_dir: str) -> set[str]:
    """Return the set of spec names with an empty lock file under locked/.

    An absent or unreadable locked/ directory yields an empty set.
    """
    locked_dir = os.path.join(capture_dir, "locked")
    if not os.path.isdir(locked_dir):
        return set()

    specs: set[str] = set()
    try:
        for entry in os.listdir(locked_dir):
            entry_path = os.path.join(locked_dir, entry)
            if os.path.isfile(entry_path) and os.path.getsize(entry_path) == 0:
                specs.add(entry)
    except OSError:
        pass

    return specs


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
        protect_specs: Caller's snapshot of protected spec names.  The locked
            section re-reads locked/ and unions it with this set, so a lock
            file created after the caller read its snapshot but before the
            prune acquired the lock is honored (IF-S-06).
    """
    try:
        # Early exit: file absent or already within cap.
        if not os.path.exists(events_path):
            return
        if os.path.getsize(events_path) <= max_bytes:
            return

        # Hold the lock across the whole read-modify-write so a concurrent
        # append cannot land between the read and the rewrite (and be lost).
        with file_lock(events_path):
            _prune_locked(events_path, max_bytes, protect_specs)

    except Exception:
        # Never raise; leave the original file untouched.
        return


def _prune_locked(events_path: str, max_bytes: int, protect_specs: set[str]) -> None:
    """Perform the read-modify-write prune.  Caller holds the events lock."""
    try:
        # Re-check size under the lock — a concurrent prune may have already
        # brought the file within the cap while we waited for the lock.
        if os.path.getsize(events_path) <= max_bytes:
            return

        # Re-derive the locked set while holding the events lock and union it with
        # the caller's snapshot: a lock file dropped after the caller read its set
        # but before this prune acquired the lock is honored (IF-S-06 — the
        # protected set consulted by the prune is read under the lock).
        capture_dir = os.path.dirname(os.path.abspath(events_path))
        protect_specs = set(protect_specs) | _locked_specs(capture_dir)

        # Read all raw lines preserving order (oldest first = top of file).
        with open(events_path, "rb") as fh:
            raw_lines = fh.readlines()

        # Classify each line by its original index as protected or unprotected,
        # so the surviving set can be merged back in file order by index —
        # byte-identical duplicate lines stay distinct.
        protected_idx = []
        unprotected_idx = []
        for i, raw in enumerate(raw_lines):
            stripped = raw.strip()
            if not stripped:
                # Skip blank lines; treat as unprotected for accounting.
                unprotected_idx.append(i)
                continue
            try:
                obj = json.loads(stripped)
                spec = obj.get("spec", "")
            except (json.JSONDecodeError, AttributeError):
                spec = ""

            if spec in protect_specs:
                protected_idx.append(i)
            else:
                unprotected_idx.append(i)

        protected_bytes = sum(len(raw_lines[i]) for i in protected_idx)
        protected_ceiling = int(max_bytes * PROTECTED_FRACTION)

        # Determine whether we need to drop locked lines past the ceiling.
        dropped_locked = False

        if protected_bytes > protected_ceiling:
            # Protected lines alone exceed the ceiling; drop oldest locked lines
            # until protected bytes are at or under the ceiling.
            # oldest first in protected_idx (index order = file order)
            while protected_idx and protected_bytes > protected_ceiling:
                removed = protected_idx.pop(0)
                protected_bytes -= len(raw_lines[removed])
                dropped_locked = True

        # Now fit unprotected lines: keep ALL protected lines plus as many of
        # the newest unprotected lines as fit within max_bytes.
        current_protected_bytes = sum(len(raw_lines[i]) for i in protected_idx)
        remaining_budget = max_bytes - current_protected_bytes

        # Keep newest unprotected lines that fit (unprotected_idx is oldest-first,
        # so we iterate from the end). Oldest lines that don't fit are omitted.
        kept_unprotected_idx = []
        budget = remaining_budget
        for i in reversed(unprotected_idx):
            if budget >= len(raw_lines[i]):
                kept_unprotected_idx.append(i)
                budget -= len(raw_lines[i])

        # Merge survivors back into original file order by index.
        surviving_idx = sorted(set(protected_idx) | set(kept_unprotected_idx))
        new_content = b"".join(raw_lines[i] for i in surviving_idx)

        # Single write — any failure before this point leaves the original intact.
        with open(events_path, "wb") as fh:
            fh.write(new_content)

        # Write the sentinel only when locked lines were actually dropped.
        # capture_dir was derived once above (abspath) — the sentinel lands in
        # the same directory the locked-spec set was read from.
        if dropped_locked:
            sentinel_path = os.path.join(capture_dir, ".retention-warning")
            with open(sentinel_path, "w") as fh:
                fh.write("")

    except Exception:
        # Never raise; leave the original file untouched.
        return
