---
id: task-27
type: implementation
wave: 3
covers: [AC-11, AC-13, AC-15, AC-24, AC-26, AC-23, AC-12, AC-02]
files_to_create:
  - assets/fbk-scripts/fbk/capture/event_writer.py
test_tasks: [task-09]
completion_gate: "task-09 tests pass"
dependencies: [task-22, task-23]
---

# 1 Objective

Produce the single append path into `.fbk-capture/events.jsonl`: it appends exactly one fully-formed envelope line per successful call then runs the retention prune check; discards an out-of-vocabulary `event_type` with a stderr warning; swallows ALL failures (returns `None`, never raises, never writes stdout); applies central level-based redaction; realpath-confirms the capture dir under the project root before creating or writing (so neither the dir creation nor the self-gitignore can follow a symlink out of tree); and on first creating `.fbk-capture/` writes `.fbk-capture/.gitignore` containing `*`.

# 2 Context

Five producers (the chokepoint, hook router, verification hook, code-review gate, and the migrated spec/task-reviewer gates) write through this one path, so every invariant that matters for privacy and safety is enforced HERE rather than duplicated across producers. The envelope is one JSON object per line with fields `schema_version` (`"1.0"`), `event_type`, `timestamp` (ISO-8601 UTC), `spec` (str or null), `stage` (str or null), `source`, `capture_level`, `data`. `spec`/`stage` are null (present, not absent) when no SDL run is active. Redaction and the vocabulary guard come from the schema module (task-22): `schema.EVENT_TYPES`, `schema.redact(data, level)`. Retention pruning comes from `retention.prune_if_needed` (task-23).

Capture writes must never reach the global config dir and must never escape the project tree — the writer confines `.fbk-capture/` to a real directory under the project root before doing anything in it.

# 3 Instructions

1. Create `fbk/capture/event_writer.py`. Import `from fbk.capture import schema, retention`.
2. Implement `write(event_type, source, data, spec, stage, capture_level, events_path) -> None`. Wrap the ENTIRE body in `try/except Exception` that returns `None` — never raise, never print to stdout (warnings go to stderr only). Completion: any internal failure returns `None`, raises nothing, writes nothing to stdout.
3. Vocabulary guard: if `event_type not in schema.EVENT_TYPES`, print a stderr warning naming the bad type and return `None` WITHOUT writing anything. Completion: an out-of-vocabulary type writes no line and warns on stderr.
4. Capture-dir confinement: derive the capture dir as `os.path.dirname(events_path)` (the `.fbk-capture/` dir). Before creating or writing, realpath-confirm: the project root is the parent of the capture dir; if the capture dir already exists, its realpath must be a real directory under the project root (refuse a symlink that escapes). If it does not exist yet, create it under the realpath-confirmed parent. If confinement fails (the dir is a symlink pointing out of tree), return `None` without writing. Completion: a symlinked `.fbk-capture/` causes the write to be skipped (no file created in the link target outside the root), no raise.
5. First-creation gitignore: when the writer creates `.fbk-capture/` for the first time (the dir did not exist before this call), write `.fbk-capture/.gitignore` containing exactly `*` (a single `*`, optionally with a trailing newline). Completion: after a write into a fresh project, `.fbk-capture/.gitignore` exists and its stripped content equals `*`.
6. Central redaction: apply `schema.redact(data, capture_level)` to the `data` payload before assembling the envelope, so no `standard`-level record carries a free-text payload field while `full` preserves it. Completion: a `standard` write strips `tool_input` and keeps `count`; a `full` write keeps `tool_input` verbatim.
7. Envelope assembly: build the dict with all eight fields — `schema_version="1.0"`, `event_type`, `timestamp` = current ISO-8601 UTC (`datetime.datetime.now(datetime.timezone.utc).isoformat()`), `spec` (None when not provided — keep the key present with value null), `stage` (same null-not-absent rule), `source`, `capture_level`, `data` = the redacted payload. Append it as one `json.dumps(...) + "\n"` line to `events_path` in append mode. Completion: one line per call carrying all eight fields; a second call appends rather than overwrites (two lines).
8. Prune after append: after a successful append, call `retention.prune_if_needed(events_path, retention.DEFAULT_MAX_BYTES, <protect_specs>)`. Resolve `protect_specs` from empty lock files under `<capture_dir>/locked/` (the set of spec names with an empty lock file); an absent `locked/` dir yields an empty set. Completion: the prune check runs exactly once after a successful write (a test monkeypatches `retention.prune_if_needed` and asserts one call with the events path).

# 4 Files to create/modify

- Create `fbk/capture/event_writer.py`

# 5 Test requirements

Makes task-09 (`tests/test_capture_event_writer.py`) pass: appends exactly one JSONL line with the full envelope (append, not overwrite); runs the prune check once after append; discards an out-of-vocabulary type with a stderr warning and writes nothing; swallows an unwritable-path failure (returns None, no raise, no stdout); writes `.gitignore` containing `*` on first dir creation; strips free-text at `standard` and preserves it at `full`; refuses a symlinked capture dir.

# 6 Acceptance criteria

Primary: task-09's tests pass. Covers AC-11 (fail-silent write), AC-13 (runtime vocabulary discard), AC-15 (the one joinable data source for both router and chokepoint), AC-24 (self-gitignore), AC-26 (central redaction), AC-23 (symlink confinement at write), AC-12 (envelope carries spec/stage null-not-absent), AC-02 (writes to the project capture file, never the global dir).

# 7 Model

Sonnet

# 8 Wave

3
