"""Unit tests for fbk.audit module."""

import json
import pytest
from fbk.audit import log_event, read_log, get_log_path


class TestLogEvent:
    """Tests for log_event() function."""

    def test_single_log_event_produces_valid_json_with_correct_fields(self, tmp_path, monkeypatch):
        """Single log event produces valid JSON with correct fields."""
        monkeypatch.setenv("LOG_DIR", str(tmp_path))

        log_event("myspec", "start", '{"key":"val"}')

        log_path = get_log_path("myspec")
        with open(log_path) as f:
            line = f.read().strip()

        entry = json.loads(line)
        assert "timestamp" in entry
        assert entry["spec"] == "myspec"
        assert entry["event_type"] == "start"
        assert entry["data"] == {"key": "val"}

    def test_multiple_log_calls_produce_independent_lines(self, tmp_path, monkeypatch):
        """Multiple log calls produce independent JSON lines."""
        monkeypatch.setenv("LOG_DIR", str(tmp_path))

        log_event("multi", "ev1", '{"n":1}')
        log_event("multi", "ev2", '{"n":2}')
        log_event("multi", "ev3", '{"n":3}')

        log_path = get_log_path("multi")
        with open(log_path) as f:
            lines = f.readlines()

        assert len(lines) == 3
        for line in lines:
            entry = json.loads(line.strip())
            assert "timestamp" in entry
            assert "spec" in entry
            assert "event_type" in entry
            assert "data" in entry

    def test_existing_entries_preserved_on_append(self, tmp_path, monkeypatch):
        """Existing entries preserved when appending new log event."""
        monkeypatch.setenv("LOG_DIR", str(tmp_path))

        from pathlib import Path
        log_path = Path(get_log_path("preserve"))
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Pre-populate with one line
        original_entry = {"timestamp": "pre", "spec": "preserve", "event_type": "seed", "data": {}}
        with open(log_path, "w") as f:
            f.write(json.dumps(original_entry) + "\n")

        log_event("preserve", "append", '{"x":1}')

        with open(log_path) as f:
            lines = f.readlines()

        assert len(lines) == 2

        # First line is the original
        first_entry = json.loads(lines[0].strip())
        assert first_entry["event_type"] == "seed"

        # Second line is the new entry
        second_entry = json.loads(lines[1].strip())
        assert second_entry["event_type"] == "append"

    def test_nested_json_preserved(self, tmp_path, monkeypatch):
        """Nested JSON data preserved in log."""
        monkeypatch.setenv("LOG_DIR", str(tmp_path))

        log_event("nested", "ev", '{"outer":{"inner":[1,2]}}')

        log_path = get_log_path("nested")
        with open(log_path) as f:
            line = f.read().strip()

        entry = json.loads(line)
        assert entry["data"]["outer"]["inner"] == [1, 2]

    def test_invalid_json_exits_with_error(self, tmp_path, monkeypatch):
        """Invalid JSON string raises SystemExit with code 1."""
        monkeypatch.setenv("LOG_DIR", str(tmp_path))

        with pytest.raises(SystemExit) as exc_info:
            log_event("invalid", "event", '{"bad json}')

        assert exc_info.value.code == 1
