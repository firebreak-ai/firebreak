---
id: task-01
type: test
wave: 1
covers: [AC-07, AC-15, AC-06]
files_to_create:
  - assets/fbk-scripts/tests/capture_fixtures.py
completion_gate: "fixtures import cleanly and the self-check test fails before the capture subsystem exists"
---

# Objective

Add a shared test-fixture helper module that builds the on-disk inputs the metrics-plane tests consume — an `events.jsonl` event stream, a matching state file, hand-authored transcript JSON, a temporary instrumented/uninstrumented project tree, and a stdin-payload helper for the router — so every later test task depends on one fixture source instead of rebuilding inputs.

# Context

The metrics plane records pipeline facts as one JSON object per line in `.fbk-capture/events.jsonl`, joins them to the state engine on `(spec, stage)`, and derives token totals from Claude Code session transcripts. Tests for this subsystem all need the same kinds of fixture input. The existing suite builds fixtures with plain `tmp_path` writes and pytest fixtures in `tests/conftest.py` (see `set_state_dir`, `valid_spec_text`). Follow that style: pure builder functions that take a base directory and write real files, returning the paths.

Event envelope shape (one JSON object per line), copied from the interface contract: fields `schema_version`, `event_type`, `timestamp`, `spec`, `stage`, `source`, `capture_level`, `data`. The fixed `event_type` vocabulary is exactly `PIPELINE_COMMAND`, `VERIFICATION_RESULT`, `CODE_REVIEW_ROUNDS`, `TOOL_USE`, `SUBAGENT_STOP`, `LIFECYCLE`.

The state file shape is what `fbk/state.py` writes: keys `spec_name`, `current_state`, `stage_timestamps` (a dict mapping stage name → ISO-8601 string), `agent_ids`, `verification_results`, `error_history` (a list of `{stage, error, timestamp}`), `parked_info`. Build fixtures with these exact keys so they match the real engine.

Transcript shape is the Claude Code session JSONL the harvester reads: assistant records carry `.message.usage` with `input_tokens`/`output_tokens`/`cache_read_input_tokens`/`cache_creation_input_tokens`, `.message.model`, `.timestamp`, `.isSidechain`; tool_use blocks live in assistant `.message.content[]`; tool results arrive in user records. Provide a small hand-authored transcript with a couple of assistant turns at known timestamps, plus the ability to write an unreadable transcript (a path that cannot be opened) to exercise the `unavailable` path.

# Instructions

1. Create `tests/capture_fixtures.py` as a plain helper module (not a conftest — import it by name from test files: `from tests import capture_fixtures` or `import capture_fixtures` consistent with the suite's import style; the suite has `tests/__init__.py`, so use `from tests import capture_fixtures`).
2. Add `def build_event(event_type, source, spec, stage, capture_level="standard", data=None, timestamp=None) -> dict` that returns a dict with all eight envelope fields populated; `schema_version` set to the string `"1.0"` (matching the value the real event writer stamps — keep the fixture consistent with the writer's envelope); `data` defaults to `{}`; `timestamp` defaults to a fixed valid ISO-8601 string. Completion: returns a dict whose keys are exactly the eight envelope field names.
3. Add `def write_events(path, events) -> None` that writes each event dict as one JSON line (`json.dumps(ev)` + newline) to `path`, creating parent dirs. Completion: the file has one line per event, each line round-trips through `json.loads`.
4. Add `def build_state(spec, stage_timestamps, error_history=None, parked_info=None, current_state=None) -> dict` returning a state dict with the exact `fbk/state.py` keys; `current_state` defaults to the last stage in `stage_timestamps`; `error_history` defaults to `[]`; `parked_info` defaults to `{}`. Completion: returns a dict containing `spec_name`, `current_state`, `stage_timestamps`, `error_history`, `parked_info`.
5. Add `def write_state(state_dir, state) -> str` that writes `<state_dir>/<spec_name>.json` as indented JSON and returns the path. Completion: the file exists and round-trips.
6. Add `def build_transcript(turns) -> list` and `def write_transcript(path, turns) -> str`, where each `turn` is a dict like `{"timestamp": <iso>, "model": <str>, "input_tokens": <int>, "output_tokens": <int>, "tools": [<name>...], "sidechain": <bool>}`, rendered as an assistant record matching the real transcript shape (`type="assistant"`, `message.usage`, `message.model`, `message.content[]` tool_use blocks, top-level `timestamp` and `isSidechain`). Completion: a written transcript parses as JSONL and each assistant line carries `message.usage.input_tokens`.
7. Add `def write_unreadable_transcript(path) -> str` that creates a file then makes it unreadable (e.g. `os.chmod(path, 0o000)`), returning the path; tolerate platforms where chmod is a no-op by also offering a path that simply does not exist. Completion: opening the returned path raises `OSError`, or the path does not exist.
8. Add `def make_project(base, instrumented=True, marked=False, capture_cfg=None) -> str` that builds a tmp project tree: when `instrumented`, creates `.claude/automation/` and (when `marked`) the Firebreak sentinel file `.claude/automation/.fbk-managed`; when `capture_cfg` is a level string, writes `.fbk-capture/capture.cfg` containing the single line `capture_level=<level>`. Returns the project root path. Completion: the requested files exist under the returned root and absent ones do not.
9. Add `def hook_payload(hook_event_name, cwd=None, tool_name=None, tool_input=None, agent_type=None, extra=None) -> str` that returns a JSON string suitable to feed the router on stdin, carrying `hook_event_name` and the optional fields. Completion: the returned string parses as JSON and carries `hook_event_name`.
10. Add a self-check test `tests/test_capture_fixtures.py` with one test `test_event_builder_yields_full_envelope` asserting `build_event(...)` returns a dict whose key set equals exactly the eight envelope field names; and `test_make_project_writes_sentinel_only_when_marked` asserting the sentinel exists only when `marked=True`. These confirm the fixtures themselves are correct (they do not depend on production code, so they will pass — they are the lone exception to the red-phase gate and serve as a smoke test the fixtures load).

# Files to create/modify

- `tests/capture_fixtures.py`
- `tests/test_capture_fixtures.py`

# Test requirements

- `test_event_builder_yields_full_envelope` (unit): the envelope builder returns all eight named fields — assert the key set equals `{schema_version, event_type, timestamp, spec, stage, source, capture_level, data}`.
- `test_make_project_writes_sentinel_only_when_marked` (unit): `make_project(..., marked=False)` produces no `.fbk-managed` sentinel; `marked=True` produces it — assert presence/absence exactly.

# Acceptance criteria

Supports AC-07, AC-15, AC-06 by providing their shared inputs. Gate: the fixture self-check tests pass (these validate the fixtures, which own no production dependency); every downstream test task that imports these fixtures is the one that must fail red against the absent implementation.

# Model

Sonnet — multi-shape fixture builder feeding many later tasks; needs judgment on shapes.

# Wave

1
