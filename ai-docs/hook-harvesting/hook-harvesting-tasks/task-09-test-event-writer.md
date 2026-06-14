---
id: task-09
type: test
wave: 3
covers: [AC-11, AC-13, AC-15, AC-24, AC-26, AC-23]
files_to_create:
  - assets/fbk-scripts/tests/test_capture_event_writer.py
completion_gate: "tests compile and fail before implementation"
---

# Objective

Write the unit tests for the single event-writer append path: it appends exactly one JSONL line on success and runs the prune check; discards an out-of-vocabulary `event_type` with a stderr warning and writes nothing; swallows any write failure (returns `None`, never raises, never writes stdout); self-creates `.fbk-capture/.gitignore` containing `*` on first directory creation; applies central level-based redaction; and never follows a symlinked capture dir out of the project tree.

# Context

`event_writer.write` is the one append path into `.fbk-capture/events.jsonl`. It is consumed by the chokepoint, the hook router, the verification hook, the code-review gate, and the spec/task-reviewer gates. Its invariants: any failure is caught and discarded, never propagated, never written to stdout; an out-of-vocabulary `event_type` is discarded with a stderr warning rather than written; it enforces level-based payload redaction centrally (delegating to the schema redactor) so no `standard`-level record carries a free-text payload; it creates `.fbk-capture/` and writes only after the directory is realpath-confirmed under the project root, and on first creating the directory it writes a `.gitignore` containing `*`. After a successful append it runs the retention prune check.

Exercise through `tmp_path`. Import `from fbk.capture import event_writer` inside `try/except ImportError` with a module-level skipif. Capture stderr with `capsys`. Build envelope inputs with `capture_fixtures` where convenient.

Signature to call verbatim: `event_writer.write(event_type, source, data, spec, stage, capture_level, events_path)`.

# Instructions

1. Create `tests/test_capture_event_writer.py`; import `event_writer` inside `try/except ImportError`; module-level skipif.
2. `test_write_appends_exactly_one_jsonl_line`: call `write("TOOL_USE", "hook_router", {"count": 1}, "demo-spec", "IMPLEMENTING", "standard", str(tmp_path/".fbk-capture"/"events.jsonl"))`; assert the events file has exactly one line AND that line parses as JSON carrying `event_type == "TOOL_USE"`, `spec == "demo-spec"`, `stage == "IMPLEMENTING"`, and all eight envelope fields present. Call `write` a second time and assert the file then has exactly two lines (append, not overwrite).
3. `test_write_runs_prune_check_after_append`: assert the prune check runs after append. PREFER the behavior-and-wiring approach: write enough events past a small `max_bytes` cap that the writer passes to `prune_if_needed` (use the configurable cap if `write`/the writer module exposes one) and assert the resulting file is under that cap — this verifies both that the prune ran AND that it received the correct path/cap, without standing in for owned code. Only if the writer exposes no configurable cap, fall back to a recording-monkeypatch on `fbk.capture.retention.prune_if_needed` asserting it was invoked once with the events path after a successful write (a wiring-only check; `retention` is owned code, so this is the weaker option used solely when the cap is not reachable).
4. `test_out_of_vocabulary_event_type_discarded_with_warning`: call `write("NOT_A_REAL_TYPE", "x", {}, None, None, "standard", path)`; assert the events file does not exist or has zero lines (nothing written) AND a warning appears on stderr (`capsys.readouterr().err` non-empty / names the bad type). Return value is `None`.
5. `test_write_swallows_failure_returns_none_no_raise_no_stdout`: point `events_path` at an unwritable location (e.g. a path whose parent is a file, or a read-only directory); call `write(...)`; assert it returns `None`, raises nothing, and writes nothing to stdout (`capsys.readouterr().out == ""`).
6. `test_first_directory_creation_writes_star_gitignore`: call `write(...)` into a fresh `tmp_path` where `.fbk-capture/` does not yet exist; assert that after the call `.fbk-capture/.gitignore` exists AND its content is exactly `*` (or `*\n` — assert the stripped content equals `*`).
7. `test_standard_level_strips_freetext_payload`: call `write("TOOL_USE", "hook_router", {"tool_input": {"command": "secret"}, "count": 2}, "s", "IMPLEMENTING", "standard", path)`; read the written line; assert the free-text payload field (`tool_input`) is absent or emptied while the structural field (`count == 2`) survives — central redaction applied at write time.
8. `test_full_level_preserves_payload`: same call with `capture_level="full"`; assert the written line carries `tool_input` verbatim.
9. `test_write_refuses_symlinked_capture_dir`: create a real dir outside `tmp_path`'s project root and symlink `<root>/.fbk-capture` to it; call `write(...)` with an events path under that symlinked dir; assert no file is created in the link target outside the root (the write does not follow the link out of tree) and the call raises nothing. Skip on platforms without symlink support.

# Files to create/modify

- `tests/test_capture_event_writer.py`

# Test requirements

- `test_write_appends_exactly_one_jsonl_line` (unit): one line per call, full envelope, append not overwrite.
- `test_write_runs_prune_check_after_append` (unit): prune check invoked once after a successful append.
- `test_out_of_vocabulary_event_type_discarded_with_warning` (unit): bad type → nothing written + stderr warning.
- `test_write_swallows_failure_returns_none_no_raise_no_stdout` (unit): unwritable path → None, no raise, no stdout.
- `test_first_directory_creation_writes_star_gitignore` (unit): first dir creation writes `.gitignore` containing `*`.
- `test_standard_level_strips_freetext_payload` (unit): standard write strips free-text, keeps structural.
- `test_full_level_preserves_payload` (unit): full write keeps payload verbatim.
- `test_write_refuses_symlinked_capture_dir` (unit): symlinked capture dir is not followed out of tree.

# Acceptance criteria

AC-11 (fail-silent write), AC-13 (vocabulary discard at runtime), AC-15 (events file is the joinable data source), AC-24 (self-gitignore), AC-26 (central redaction), AC-23 (symlink confinement at write). Gate: tests compile and fail before implementation.

# Model

Sonnet — multiple invariants including fail-silent, redaction, and symlink confinement.

# Wave

3
