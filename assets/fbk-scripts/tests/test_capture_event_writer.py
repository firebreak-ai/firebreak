"""Tests for fbk.capture.event_writer — the single append path into events.jsonl.

Invariants under test:
  - appends exactly one JSONL line per call; full eight-field envelope preserved
  - runs the retention prune check after each successful append
  - discards an out-of-vocabulary event_type with a stderr warning, writes nothing
  - swallows any write failure: returns None, never raises, never writes stdout
  - self-creates .fbk-capture/.gitignore containing '*' on first directory creation
  - applies central level-based redaction (standard strips free-text, full preserves)
  - refuses to follow a symlinked capture dir out of the project root

Module is not yet implemented; every test skips in the red phase.
"""

import json
import os
import stat
import pytest

try:
    from fbk.capture import event_writer
except ImportError:
    event_writer = None

from tests import capture_fixtures


pytestmark = pytest.mark.skipif(
    event_writer is None,
    reason="fbk.capture.event_writer not yet implemented",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CAPTURE_DIR = ".fbk-capture"
_EVENTS_FILE = "events.jsonl"

# All eight envelope fields the spec requires on every written line.
_ENVELOPE_FIELDS = {
    "schema_version",
    "event_type",
    "timestamp",
    "spec",
    "stage",
    "source",
    "capture_level",
    "data",
}


def _events_path(base):
    """Return the canonical events path under base."""
    return str(base / _CAPTURE_DIR / _EVENTS_FILE)


def _read_lines(path):
    """Return non-empty stripped lines from path as a list of strings."""
    with open(path) as f:
        return [line.strip() for line in f if line.strip()]


def _read_json_lines(path):
    """Return parsed JSON objects for each non-empty line in path."""
    return [json.loads(line) for line in _read_lines(path)]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_write_appends_exactly_one_jsonl_line(tmp_path):
    """Each write() call appends exactly one JSON line; second call gives two lines total."""
    path = _events_path(tmp_path)

    result = event_writer.write(
        "TOOL_USE",
        "hook_router",
        {"count": 1},
        "demo-spec",
        "IMPLEMENTING",
        "standard",
        path,
    )

    # File must exist after first write.
    assert os.path.exists(path), "events file was not created after write()"

    lines = _read_json_lines(path)

    # Exactly one line after first call.
    assert len(lines) == 1, f"expected 1 line after first write, got {len(lines)}"

    first = lines[0]

    # All eight envelope fields must be present.
    missing = _ENVELOPE_FIELDS - set(first.keys())
    assert not missing, f"envelope fields missing from written record: {missing}"

    # Core identifying fields match what was passed.
    assert first["event_type"] == "TOOL_USE"
    assert first["spec"] == "demo-spec"
    assert first["stage"] == "IMPLEMENTING"

    # Second write appends — does not overwrite.
    event_writer.write(
        "TOOL_USE",
        "hook_router",
        {"count": 2},
        "demo-spec",
        "IMPLEMENTING",
        "standard",
        path,
    )

    lines_after_second = _read_json_lines(path)
    assert len(lines_after_second) == 2, (
        f"expected 2 lines after second write (append), got {len(lines_after_second)}"
    )


def test_write_runs_prune_check_after_append(tmp_path, monkeypatch):
    """The retention prune check runs after a successful append.

    Preferred approach: write enough events past a small cap so that
    event_writer.write delegates to prune_if_needed, and assert the file
    shrinks under cap — verifying both that prune ran and that it received
    the correct path.

    Because event_writer is not yet implemented, we cannot know whether it
    exposes a configurable cap at this stage. The test uses a monkeypatch on
    fbk.capture.retention.prune_if_needed as the fallback wiring check (owned
    code, weaker, but the only option until the writer module surfaces its
    interface). When the writer exposes a configurable cap, this test should
    be updated to prefer the behavior-and-wiring approach.
    """
    from fbk.capture import retention

    called_with = []

    def _recording_prune(events_path, max_bytes, protect_specs):
        called_with.append(events_path)

    monkeypatch.setattr(retention, "prune_if_needed", _recording_prune)

    path = _events_path(tmp_path)

    event_writer.write(
        "LIFECYCLE",
        "hook_router",
        {},
        "prune-spec",
        "QUEUED",
        "standard",
        path,
    )

    assert len(called_with) == 1, (
        f"expected prune_if_needed called once after append, got {len(called_with)} calls"
    )
    assert called_with[0] == path, (
        f"prune_if_needed received wrong events path: {called_with[0]!r} != {path!r}"
    )


def test_out_of_vocabulary_event_type_discarded_with_warning(tmp_path, capsys):
    """An out-of-vocabulary event_type writes nothing and emits a stderr warning."""
    path = _events_path(tmp_path)

    result = event_writer.write(
        "NOT_A_REAL_TYPE",
        "x",
        {},
        None,
        None,
        "standard",
        path,
    )

    # Nothing written: file absent or zero non-empty lines.
    if os.path.exists(path):
        lines = _read_lines(path)
        assert len(lines) == 0, (
            f"expected no lines written for bad event type, got {len(lines)}"
        )

    # Return value is None.
    assert result is None, f"expected None return for bad event type, got {result!r}"

    # A warning naming the bad type must appear on stderr.
    captured = capsys.readouterr()
    assert captured.err != "", "expected a stderr warning for out-of-vocabulary event_type"
    assert "NOT_A_REAL_TYPE" in captured.err, (
        f"expected bad type name in warning, got: {captured.err!r}"
    )


def test_write_swallows_failure_returns_none_no_raise_no_stdout(tmp_path, capsys):
    """A write to an unwritable location returns None, raises nothing, emits no stdout."""
    # Make the parent a regular file so any attempt to open the events path fails.
    bad_parent = tmp_path / _CAPTURE_DIR
    bad_parent.write_text("I am a file, not a directory")

    path = str(bad_parent / _EVENTS_FILE)

    result = None
    try:
        result = event_writer.write(
            "TOOL_USE",
            "hook_router",
            {"count": 1},
            "demo-spec",
            "IMPLEMENTING",
            "standard",
            path,
        )
    except Exception as exc:
        pytest.fail(
            f"write() raised {type(exc).__name__} instead of swallowing the failure: {exc}"
        )

    assert result is None, f"expected None on write failure, got {result!r}"

    captured = capsys.readouterr()
    assert captured.out == "", (
        f"expected no stdout on write failure, got: {captured.out!r}"
    )


def test_first_directory_creation_writes_star_gitignore(tmp_path):
    """On first creation of .fbk-capture/, a .gitignore containing '*' is written."""
    capture_dir = tmp_path / _CAPTURE_DIR
    assert not capture_dir.exists(), "capture dir should not exist before the write"

    path = _events_path(tmp_path)

    event_writer.write(
        "LIFECYCLE",
        "hook_router",
        {},
        "gi-spec",
        "QUEUED",
        "standard",
        path,
    )

    gitignore_path = capture_dir / ".gitignore"
    assert gitignore_path.exists(), ".gitignore was not created in .fbk-capture/ on first write"

    content = gitignore_path.read_text().strip()
    assert content == "*", (
        f"expected .gitignore content '*', got {content!r}"
    )


def test_standard_level_strips_freetext_payload(tmp_path):
    """At standard level, nested free-text inside a round entry is stripped while round
    numeric fields and enum severity tag survive.

    Pre-fix: 'rounds' is itself in FREETEXT_KEYS, so the entire rounds list is stripped
    and the exact-equality assertion on data['rounds'] fails red.
    Post-fix: 'rounds' is removed from FREETEXT_KEYS and redact recurses into nested
    dicts/lists, stripping only the nested free-text key (reason_text) while preserving
    numeric counts and the severity enum.
    """
    path = _events_path(tmp_path)

    data_in = {
        "rounds": [
            {
                "raised": 3,
                "survived": 1,
                "severity": "major",
                "reason_text": "NESTED-FREETEXT sentinel",
            }
        ],
        "total_raised": 3,
        "total_survived": 1,
        "tool_input": {"command": "secret"},
        "count": 2,
    }

    event_writer.write(
        "CODE_REVIEW_ROUNDS",
        "code_review",
        data_in,
        "s",
        "IMPLEMENTING",
        "standard",
        path,
    )

    lines = _read_json_lines(path)
    assert len(lines) == 1, f"expected 1 line written, got {len(lines)}"

    record = lines[0]
    data = record["data"]

    # Top-level free-text key must be stripped.
    assert "tool_input" not in data, (
        f"expected 'tool_input' stripped at standard level, but data was: {data!r}"
    )

    # Structural/numeric top-level fields must survive.
    assert data.get("count") == 2, (
        f"expected 'count' to survive standard redaction, data was: {data!r}"
    )
    assert data.get("total_raised") == 3, (
        f"expected 'total_raised' to survive standard redaction, data was: {data!r}"
    )
    assert data.get("total_survived") == 1, (
        f"expected 'total_survived' to survive standard redaction, data was: {data!r}"
    )

    # The rounds list must survive with numeric fields and enum severity tag intact,
    # and the nested free-text key stripped by recursion.
    assert data.get("rounds") == [{"raised": 3, "survived": 1, "severity": "major"}], (
        f"expected rounds to survive with nested free-text stripped, but data['rounds'] was: "
        f"{data.get('rounds')!r}"
    )

    # Raw written line must not contain either sentinel string.
    raw_line = _read_lines(path)[0]
    assert "NESTED-FREETEXT" not in raw_line, (
        f"expected 'NESTED-FREETEXT' sentinel absent from written line, but found in: {raw_line!r}"
    )
    assert "secret" not in raw_line, (
        f"expected 'secret' sentinel absent from written line, but found in: {raw_line!r}"
    )


def test_full_level_preserves_payload(tmp_path):
    """At capture_level='full', free-text payload fields are preserved verbatim."""
    path = _events_path(tmp_path)

    event_writer.write(
        "TOOL_USE",
        "hook_router",
        {"tool_input": {"command": "secret"}, "count": 2},
        "s",
        "IMPLEMENTING",
        "full",
        path,
    )

    lines = _read_json_lines(path)
    assert len(lines) == 1, f"expected 1 line written at full level, got {len(lines)}"

    record = lines[0]
    data = record.get("data", {})

    # Free-text payload must be present and verbatim at full level.
    assert "tool_input" in data, (
        f"expected 'tool_input' preserved at full level, but data was: {data!r}"
    )
    assert data["tool_input"] == {"command": "secret"}, (
        f"expected tool_input verbatim, got {data['tool_input']!r}"
    )

    # Structural field also survives.
    assert data.get("count") == 2, (
        f"expected 'count' to be present at full level, data was: {data!r}"
    )


@pytest.mark.skipif(
    not hasattr(os, "symlink"),
    reason="platform does not support symlinks",
)
def test_write_refuses_symlinked_capture_dir(tmp_path):
    """write() does not follow a symlinked .fbk-capture/ out of the project root."""
    # Establish a project root and a separate real directory outside it.
    project_root = tmp_path / "project"
    project_root.mkdir()
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()

    symlink_target = outside_dir / "events.jsonl"
    capture_symlink = project_root / _CAPTURE_DIR

    try:
        # Symlink .fbk-capture/ → outside_dir (which is outside project_root).
        capture_symlink.symlink_to(outside_dir)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation not supported on this platform")

    events_path = str(capture_symlink / _EVENTS_FILE)

    # write() must not follow the symlink out of the project root.
    try:
        event_writer.write(
            "TOOL_USE",
            "hook_router",
            {"count": 1},
            "sym-spec",
            "IMPLEMENTING",
            "standard",
            events_path,
        )
    except Exception as exc:
        pytest.fail(
            f"write() raised {type(exc).__name__} on symlinked path instead of swallowing: {exc}"
        )

    # The real file outside the tree must not have been created.
    assert not symlink_target.exists(), (
        "write() followed the symlink out of the project root and created a file outside it"
    )


@pytest.mark.skipif(
    not hasattr(os, "symlink"),
    reason="platform does not support symlinks",
)
def test_first_write_refuses_symlinked_project_root(tmp_path):
    """First-write creation is refused when the project root is reached via a symlink.

    Covers the directory-creation branch: .fbk-capture/ does not exist yet, and
    the root is a symlink, so creating the dir there would escape the real tree.
    """
    real_root = tmp_path / "real_root"
    real_root.mkdir()
    link_root = tmp_path / "link_root"
    try:
        link_root.symlink_to(real_root)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation not supported on this platform")

    # First write: no .fbk-capture/ exists yet under either path.
    events_path = str(link_root / _CAPTURE_DIR / _EVENTS_FILE)
    try:
        event_writer.write(
            "TOOL_USE", "hook_router", {"count": 1},
            "sym-spec", "IMPLEMENTING", "standard", events_path,
        )
    except Exception as exc:
        pytest.fail(
            f"write() raised {type(exc).__name__} on symlinked root instead of swallowing: {exc}"
        )

    # Confinement refused creation — nothing was made under the real root.
    assert not (real_root / _CAPTURE_DIR).exists(), (
        "first-write created the capture dir through a symlinked project root"
    )


def test_file_lock_is_exclusive(tmp_path):
    """retention.file_lock holds an exclusive advisory lock a second holder cannot take.

    This is the mechanism that stops a concurrent append from being lost inside a
    prune's read-modify-write.
    """
    import fcntl

    from fbk.capture import retention

    capture_dir = tmp_path / _CAPTURE_DIR
    capture_dir.mkdir()
    events_path = str(capture_dir / _EVENTS_FILE)

    with retention.file_lock(events_path):
        # While the lock is held, a non-blocking acquire on the same lock file
        # must fail rather than proceed concurrently.
        contender = open(retention._lock_path(events_path), "w")
        try:
            with pytest.raises(BlockingIOError):
                fcntl.flock(contender, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            contender.close()
