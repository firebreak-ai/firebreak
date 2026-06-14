"""Tests for fbk.capture.retention — size-cap retention pruner.

The pruner drops oldest lines past a byte cap, protects lines whose spec
is in the locked set up to a ceiling fraction of that cap, and surfaces
a sentinel file when it drops locked lines past that ceiling.

Module is not yet implemented; every test skips in the red phase.
"""

import contextlib
import json
import os
import stat
import threading
import pytest

try:
    from fbk.capture import retention
except ImportError:
    retention = None

try:
    from fbk.capture import event_writer
except ImportError:
    event_writer = None

from tests import capture_fixtures


pytestmark = pytest.mark.skipif(
    retention is None,
    reason="fbk.capture.retention not yet implemented",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CAPTURE_DIR = ".fbk-capture"
_EVENTS_FILE = ".fbk-capture/events.jsonl"
_WARNING_SENTINEL = ".fbk-capture/.retention-warning"


def _events_path(base):
    return os.path.join(base, _EVENTS_FILE)


def _warning_path(base):
    return os.path.join(base, _WARNING_SENTINEL)


def _line_count(path):
    with open(path) as f:
        return sum(1 for line in f if line.strip())


def _specs_in_file(path):
    """Return a list of spec values, one per non-empty line."""
    specs = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                specs.append(json.loads(line)["spec"])
    return specs


def _read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_drops_oldest_lines_past_cap(tmp_path):
    """An over-cap file is pruned to <= max_bytes; newest lines survive; at least one line remains."""
    events_path = _events_path(str(tmp_path))

    # Write 20 events — each JSON line is well over the small cap we will use.
    events = [
        capture_fixtures.build_event(
            event_type="LIFECYCLE",
            source="pruner-test",
            spec="unprotected-spec",
            stage="QUEUED",
            timestamp=f"2026-01-01T00:00:{i:02d}+00:00",
        )
        for i in range(20)
    ]
    capture_fixtures.write_events(events_path, events)

    original_size = os.path.getsize(events_path)
    # cap is roughly a third of the file — forces pruning but leaves some lines
    max_bytes = original_size // 3

    retention.prune_if_needed(events_path, max_bytes, set())

    pruned_size = os.path.getsize(events_path)

    # upper bound: file is at or under cap
    assert pruned_size <= max_bytes, (
        f"file size {pruned_size} exceeds max_bytes {max_bytes}"
    )

    # lower bound: at least one line survived
    assert _line_count(events_path) >= 1, "pruner removed every line"

    # newest lines are retained: the last original line (timestamp :19) must be present
    surviving_specs = _specs_in_file(events_path)
    # The most-recent event was spec="unprotected-spec" with timestamp :19
    # We verify the newest event is in the surviving set by checking overall
    # that surviving lines are a suffix of the original ordering.
    with open(events_path) as f:
        lines = [l.strip() for l in f if l.strip()]
    last_event = json.loads(lines[-1])
    assert last_event["timestamp"] == "2026-01-01T00:00:19+00:00", (
        "newest line did not survive pruning"
    )

    # an early line (timestamp :00) must be gone
    first_event_ts = "2026-01-01T00:00:00+00:00"
    all_timestamps = [json.loads(l)["timestamp"] for l in lines]
    assert first_event_ts not in all_timestamps, (
        "oldest line was not dropped during pruning"
    )


def test_never_drops_protected_spec_under_ceiling(tmp_path):
    """Protected spec lines all survive when their byte total is under the ceiling."""
    events_path = _events_path(str(tmp_path))

    # 3 protected lines — small total
    protected_events = [
        capture_fixtures.build_event(
            event_type="LIFECYCLE",
            source="pruner-test",
            spec="locked-spec",
            stage="QUEUED",
            timestamp=f"2026-01-01T00:00:0{i}+00:00",
        )
        for i in range(3)
    ]
    # 30 unprotected lines — large enough to push the file well over cap
    unprotected_events = [
        capture_fixtures.build_event(
            event_type="LIFECYCLE",
            source="pruner-test",
            spec="unlocked-spec",
            stage="QUEUED",
            timestamp=f"2026-01-01T01:{i:02d}:00+00:00",
        )
        for i in range(30)
    ]
    # Write mixed: unprotected first (oldest), protected last (newest)
    capture_fixtures.write_events(events_path, unprotected_events + protected_events)

    protected_count_before = sum(
        1 for e in protected_events
    )  # == 3; fixed for comparison below

    # cap is sized so the 30 unlocked lines must be thinned, but 3 locked lines
    # are well under the protected-bytes ceiling (ceiling = e.g. 50% of cap)
    one_line_bytes = os.path.getsize(events_path) // (
        len(protected_events) + len(unprotected_events)
    )
    # cap: a bit more than just the 3 protected lines but far less than the full file
    max_bytes = one_line_bytes * 8

    retention.prune_if_needed(events_path, max_bytes, {"locked-spec"})

    # count surviving protected lines
    surviving = _specs_in_file(events_path)
    protected_surviving = surviving.count("locked-spec")
    unlocked_surviving = surviving.count("unlocked-spec")

    assert protected_surviving == protected_count_before, (
        f"expected all {protected_count_before} protected lines to survive, "
        f"got {protected_surviving}"
    )
    assert unlocked_surviving < 30, (
        "expected unprotected lines to be dropped to bring file under cap"
    )


def test_protected_bytes_capped_past_ceiling(tmp_path):
    """When protected lines alone exceed the ceiling, the oldest locked lines are dropped."""
    events_path = _events_path(str(tmp_path))

    # 20 protected lines — intentionally large relative to the cap we will set
    protected_events = [
        capture_fixtures.build_event(
            event_type="LIFECYCLE",
            source="pruner-test",
            spec="heavy-locked-spec",
            stage="QUEUED",
            timestamp=f"2026-01-01T00:{i:02d}:00+00:00",
        )
        for i in range(20)
    ]
    capture_fixtures.write_events(events_path, protected_events)

    protected_count_before = len(protected_events)

    # cap is sized so protected bytes exceed the ceiling (cap * fraction)
    # Use a cap equal to roughly 4 lines — much smaller than 20 lines of protected data
    one_line_bytes = os.path.getsize(events_path) // len(protected_events)
    max_bytes = one_line_bytes * 4

    retention.prune_if_needed(events_path, max_bytes, {"heavy-locked-spec"})

    surviving = _specs_in_file(events_path)
    protected_surviving = len(surviving)

    # upper bound: some locked lines were dropped (not all survived)
    assert protected_surviving < protected_count_before, (
        "expected some locked lines to be dropped past the protected-bytes ceiling"
    )

    # lower bound: not all locked lines were dropped
    assert protected_surviving >= 1, (
        "pruner dropped every locked line — at least one should survive"
    )


def test_over_cap_condition_is_surfaced(tmp_path):
    """Sentinel .retention-warning is written only when locked lines are dropped past ceiling."""
    warning_path = _warning_path(str(tmp_path))

    # --- over-ceiling scenario: same setup as test_protected_bytes_capped_past_ceiling ---
    events_path = _events_path(str(tmp_path))

    protected_events = [
        capture_fixtures.build_event(
            event_type="LIFECYCLE",
            source="pruner-test",
            spec="heavy-locked-spec",
            stage="QUEUED",
            timestamp=f"2026-01-01T00:{i:02d}:00+00:00",
        )
        for i in range(20)
    ]
    capture_fixtures.write_events(events_path, protected_events)

    one_line_bytes = os.path.getsize(events_path) // len(protected_events)
    max_bytes = one_line_bytes * 4

    retention.prune_if_needed(events_path, max_bytes, {"heavy-locked-spec"})

    assert os.path.exists(warning_path), (
        "sentinel .retention-warning not written after over-ceiling prune"
    )

    # --- normal prune scenario: only unlocked lines dropped ---
    # Reset: remove events file and sentinel
    os.remove(events_path)
    if os.path.exists(warning_path):
        os.remove(warning_path)

    normal_events = [
        capture_fixtures.build_event(
            event_type="LIFECYCLE",
            source="pruner-test",
            spec="normal-spec",
            stage="QUEUED",
            timestamp=f"2026-01-01T01:{i:02d}:00+00:00",
        )
        for i in range(20)
    ]
    capture_fixtures.write_events(events_path, normal_events)

    one_line_bytes = os.path.getsize(events_path) // len(normal_events)
    normal_max_bytes = one_line_bytes * 4  # forces pruning of unlocked lines

    # protect_specs is empty — no locked lines at all
    retention.prune_if_needed(events_path, normal_max_bytes, set())

    assert not os.path.exists(warning_path), (
        "sentinel .retention-warning must not be written for a normal (no-locked-drop) prune"
    )


def test_leaves_file_intact_on_failure(tmp_path):
    """A failing prune raises nothing and the file bytes are unchanged."""
    # Use a directory path as the events_path — reading it as a file will fail
    bad_path = str(tmp_path / ".fbk-capture" / "events.jsonl")
    os.makedirs(os.path.dirname(bad_path), exist_ok=True)

    events = [
        capture_fixtures.build_event(
            event_type="LIFECYCLE",
            source="pruner-test",
            spec="spec-a",
            stage="QUEUED",
        )
        for _ in range(5)
    ]
    capture_fixtures.write_events(bad_path, events)

    original_bytes = _read_bytes(bad_path)

    # Make the file read-only so any attempted rewrite will fail
    os.chmod(bad_path, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

    try:
        # prune_if_needed must not raise even when write fails
        max_bytes = len(original_bytes) // 3  # forces a prune attempt
        retention.prune_if_needed(bad_path, max_bytes, set())
    finally:
        # Restore write permission so tmp_path cleanup can remove the file
        os.chmod(bad_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)

    assert _read_bytes(bad_path) == original_bytes, (
        "file bytes changed after a failed prune"
    )


def test_no_prune_when_under_cap(tmp_path):
    """A file already under max_bytes is left byte-for-byte unchanged."""
    events_path = _events_path(str(tmp_path))

    events = [
        capture_fixtures.build_event(
            event_type="LIFECYCLE",
            source="pruner-test",
            spec="small-spec",
            stage="QUEUED",
        )
        for _ in range(3)
    ]
    capture_fixtures.write_events(events_path, events)

    original_bytes = _read_bytes(events_path)

    # cap is well above the current file size
    max_bytes = len(original_bytes) * 10

    retention.prune_if_needed(events_path, max_bytes, set())

    assert _read_bytes(events_path) == original_bytes, (
        "file was modified even though it was under the byte cap"
    )


@pytest.mark.skipif(event_writer is None, reason="fbk.capture.event_writer not importable")
def test_lock_created_during_active_write_protects_spec_lines(tmp_path):
    """A baseline lock file created while an active write is in progress protects its spec's lines.

    Contract: once a lock file exists on disk, lines whose spec matches that
    lock file name must survive the prune that follows the write — regardless
    of exactly when during the write's execution the lock file was created.

    Sequencing guarantee: the test holds the events lock until after the lock
    file exists on disk.  The prune's protected-set determination happens inside
    a lock scope that cannot begin until the test releases.  By the time the
    prune acquires the lock, the lock file is already present, so the protection
    is honored regardless of thread scheduling — no sleeps required.

    This test does not assert on internal mechanisms (_locked_specs, _prune_locked
    call shapes, or any implementation detail).  It is valid under any compliant
    implementation.
    """
    events_path = _events_path(str(tmp_path))
    capture_dir = os.path.join(str(tmp_path), ".fbk-capture")

    # -----------------------------------------------------------------------
    # Build the events file.
    #
    # Arithmetic:
    #   Each line carries data={"pad_field": "y" * 1000}, making each line
    #   roughly 1.1 KB.
    #
    #   - 2000 lines with spec="locked-spec"  → ~2.2 MB protected bytes
    #   - 4000 lines with spec="other-spec"   → ~4.4 MB unprotected bytes
    #   - total                               → ~6.6 MB > 5 MB (DEFAULT_MAX_BYTES)
    #
    #   Protected ceiling = DEFAULT_MAX_BYTES * PROTECTED_FRACTION = 2.5 MB.
    #   ~2.2 MB protected bytes stay UNDER the 2.5 MB ceiling, so no locked
    #   lines are dropped and no sentinel is written.
    #   Total exceeds the 5 MB cap, so the prune fires and trims other-spec lines.
    # -----------------------------------------------------------------------
    pad = "y" * 1000

    locked_events = [
        capture_fixtures.build_event(
            event_type="TOOL_USE",
            source="retention-concurrency-test",
            spec="locked-spec",
            stage="QUEUED",
            data={"pad_field": pad},
        )
        for _ in range(2000)
    ]
    other_events = [
        capture_fixtures.build_event(
            event_type="TOOL_USE",
            source="retention-concurrency-test",
            spec="other-spec",
            stage="QUEUED",
            data={"pad_field": pad},
        )
        for _ in range(4000)
    ]
    capture_fixtures.write_events(events_path, locked_events + other_events)

    # -----------------------------------------------------------------------
    # Acquire the events lock in the main thread so the writer thread blocks
    # on it, then create the lock file while holding the events lock.
    # -----------------------------------------------------------------------
    with retention.file_lock(events_path):
        # Start the writer thread; it will block trying to acquire file_lock.
        thread = threading.Thread(
            target=event_writer.write,
            args=("LIFECYCLE", "hook_router", {}, "other-spec", None, "standard", events_path),
        )
        thread.start()

        # Create the baseline lock file while the events lock is still held.
        # This is "the lock created during an active write."
        locked_dir = os.path.join(capture_dir, "locked")
        os.makedirs(locked_dir, exist_ok=True)
        open(os.path.join(locked_dir, "locked-spec"), "w").close()

    # Release of the events lock happens on exit from the with block above.
    # The writer thread can now proceed: it will append, read locked_specs,
    # and trigger the prune — at which point the lock file is already on disk.
    thread.join(timeout=30)
    assert not thread.is_alive(), "writer thread did not complete within 30 s"

    # -----------------------------------------------------------------------
    # Assertions.
    # -----------------------------------------------------------------------
    with open(events_path) as fh:
        lines = [ln for ln in fh if ln.strip()]

    events_by_spec = {}
    events_by_type = {}
    for ln in lines:
        obj = json.loads(ln)
        spec = obj.get("spec")
        etype = obj.get("event_type")
        events_by_spec[spec] = events_by_spec.get(spec, 0) + 1
        events_by_type[etype] = events_by_type.get(etype, 0) + 1

    locked_surviving = events_by_spec.get("locked-spec", 0)
    other_surviving = events_by_spec.get("other-spec", 0)
    lifecycle_count = events_by_type.get("LIFECYCLE", 0)

    # All 2000 locked-spec lines must have survived.
    assert locked_surviving == 2000, (
        f"expected all 2000 locked-spec lines to survive, got {locked_surviving}"
    )

    # The prune must have fired: file is at or under the 5 MB cap.
    final_size = os.path.getsize(events_path)
    assert final_size <= retention.DEFAULT_MAX_BYTES, (
        f"file size {final_size} exceeds DEFAULT_MAX_BYTES {retention.DEFAULT_MAX_BYTES} "
        "(prune did not fire or did not reduce the file)"
    )

    # The prune dropped some other-spec lines (upper bound) but at least one survived
    # (lower bound — confirms the file was not fully cleared).
    assert other_surviving < 4001, (
        f"expected fewer than 4001 other-spec lines after prune, got {other_surviving}"
    )
    assert other_surviving >= 1, (
        "expected at least 1 other-spec line to survive, got none"
    )

    # The thread's appended LIFECYCLE event survived as the newest unprotected line.
    assert lifecycle_count == 1, (
        f"expected exactly 1 LIFECYCLE line (the thread's append), got {lifecycle_count}"
    )

    # No retention-warning sentinel: locked bytes stayed under the ceiling,
    # so no locked lines should have been dropped.
    warning_path = _warning_path(str(tmp_path))
    assert not os.path.exists(warning_path), (
        ".retention-warning sentinel exists — locked lines were wrongly dropped"
    )
