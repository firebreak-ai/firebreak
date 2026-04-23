"""Tests for fbk.council.session_state CLI."""

import json
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def council_dir(tmp_path, monkeypatch):
    """Point the session-state module at an isolated tmp dir."""
    d = tmp_path / "council-logs"
    d.mkdir()
    monkeypatch.setenv("COUNCIL_LOG_DIR", str(d))
    return d


def _run_cli(council_dir, *args):
    """Invoke fbk.py session-state via subprocess, returning CompletedProcess."""
    dispatcher = Path(__file__).parent.parent / "fbk.py"
    return subprocess.run(
        [sys.executable, str(dispatcher), "session-state", *args],
        capture_output=True,
        text=True,
        env={"COUNCIL_LOG_DIR": str(council_dir), "PATH": "/usr/bin:/bin"},
    )


class TestRecoveryCheck:
    def test_no_state_returns_not_recovering(self, council_dir):
        result = _run_cli(council_dir, "recovery-check")
        assert result.returncode == 0
        assert json.loads(result.stdout) == {"recovering": False}

    def test_missing_session_id_returns_not_recovering(self, council_dir):
        (council_dir / "council-state.json").write_text(json.dumps({"current_phase": "Phase-3"}))
        result = _run_cli(council_dir, "recovery-check")
        assert json.loads(result.stdout) == {"recovering": False}

    def test_reports_state_fields(self, council_dir):
        state = {
            "current_phase": "Phase-3-Discussion",
            "completed_phases": ["Phase-0", "Phase-1"],
            "key_decisions": ["Use JWT"],
            "transcript_summary": "summary text",
        }
        (council_dir / "council-state.json").write_text(json.dumps(state))
        (council_dir / "council-session-id").write_text("council-20260419-120000\n")

        result = _run_cli(council_dir, "recovery-check")
        assert result.returncode == 0
        payload = json.loads(result.stdout)
        assert payload["recovering"] is True
        assert payload["session_id"] == "council-20260419-120000"
        assert payload["current_phase"] == "Phase-3-Discussion"
        assert payload["completed_phases"] == ["Phase-0", "Phase-1"]
        assert payload["key_decisions"] == ["Use JWT"]
        assert payload["transcript_summary"] == "summary text"

    def test_corrupt_state_file_treated_as_empty(self, council_dir):
        (council_dir / "council-state.json").write_text("{not json")
        (council_dir / "council-session-id").write_text("sid")
        result = _run_cli(council_dir, "recovery-check")
        payload = json.loads(result.stdout)
        assert payload["recovering"] is True
        assert payload["current_phase"] is None
        assert payload["completed_phases"] == []


class TestCheckAbort:
    def test_no_abort_file_exits_zero(self, council_dir):
        result = _run_cli(council_dir, "check-abort")
        assert result.returncode == 0

    def test_empty_abort_file_exits_zero(self, council_dir):
        (council_dir / "council-abort").write_text("{}")
        result = _run_cli(council_dir, "check-abort")
        assert result.returncode == 0

    def test_abort_requested_exits_two_and_clears(self, council_dir):
        abort_file = council_dir / "council-abort"
        abort_file.write_text("stop now")

        result = _run_cli(council_dir, "check-abort")
        assert result.returncode == 2
        assert abort_file.read_text() == "{}"


class TestCheckpoint:
    def test_creates_state_file_with_fields(self, council_dir):
        result = _run_cli(
            council_dir,
            "checkpoint",
            "Phase-3-Discussion",
            "--completed", "Phase-0,Phase-1,Phase-2",
            "--summary", "Architect proposed X",
            "--decisions", "Use JWT,15min expiry",
            "--session-id", "council-20260419-120000",
        )
        assert result.returncode == 0, result.stderr

        state = json.loads((council_dir / "council-state.json").read_text())
        assert state["current_phase"] == "Phase-3-Discussion"
        assert state["completed_phases"] == ["Phase-0", "Phase-1", "Phase-2"]
        assert state["transcript_summary"] == "Architect proposed X"
        assert state["key_decisions"] == ["Use JWT", "15min expiry"]
        assert state["session_id"] == "council-20260419-120000"
        assert "last_checkpoint" in state

    def test_merges_without_clobbering_unspecified_fields(self, council_dir):
        state_file = council_dir / "council-state.json"
        state_file.write_text(json.dumps({
            "session_id": "keep-me",
            "key_decisions": ["existing"],
            "custom_field": "preserve",
        }))

        result = _run_cli(council_dir, "checkpoint", "Phase-4")
        assert result.returncode == 0

        state = json.loads(state_file.read_text())
        assert state["current_phase"] == "Phase-4"
        assert state["session_id"] == "keep-me"
        assert state["key_decisions"] == ["existing"]
        assert state["custom_field"] == "preserve"

    def test_ignores_empty_csv_entries(self, council_dir):
        result = _run_cli(
            council_dir,
            "checkpoint", "Phase-1",
            "--completed", "Phase-0,,  ,",
        )
        assert result.returncode == 0
        state = json.loads((council_dir / "council-state.json").read_text())
        assert state["completed_phases"] == ["Phase-0"]


class TestCleanup:
    def test_removes_state_file(self, council_dir):
        state_file = council_dir / "council-state.json"
        state_file.write_text("{}")
        result = _run_cli(council_dir, "cleanup")
        assert result.returncode == 0
        assert not state_file.exists()

    def test_missing_state_file_is_ok(self, council_dir):
        result = _run_cli(council_dir, "cleanup")
        assert result.returncode == 0

    def test_does_not_touch_other_files(self, council_dir):
        (council_dir / "council-state.json").write_text("{}")
        active = council_dir / "active-council"
        active.write_text(json.dumps({"sessions": {"s1": {}}}))
        session_id = council_dir / "council-session-id"
        session_id.write_text("s1")

        _run_cli(council_dir, "cleanup")

        assert active.exists()
        assert session_id.exists()
        assert json.loads(active.read_text()) == {"sessions": {"s1": {}}}


class TestShow:
    def test_prints_empty_when_no_state(self, council_dir):
        result = _run_cli(council_dir, "show")
        assert result.returncode == 0
        assert json.loads(result.stdout) == {}

    def test_prints_state_contents(self, council_dir):
        payload = {"current_phase": "Phase-2", "key_decisions": ["A"]}
        (council_dir / "council-state.json").write_text(json.dumps(payload))
        result = _run_cli(council_dir, "show")
        assert json.loads(result.stdout) == payload
