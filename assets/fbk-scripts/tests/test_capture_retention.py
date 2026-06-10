"""Tests for fbk.capture.retention — size-cap retention pruner.

The pruner drops oldest lines past a byte cap, protects lines whose spec
is in the locked set up to a ceiling fraction of that cap, and surfaces
a sentinel file when it drops locked lines past that ceiling.

Module is not yet implemented; every test skips in the red phase.
"""

import json
import os
import stat
import pytest

try:
    from fbk.capture import retention
except ImportError:
    retention = None

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
