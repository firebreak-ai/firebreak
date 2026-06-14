---
id: task-23
type: implementation
wave: 2
covers: [AC-14, AC-25]
files_to_create:
  - assets/fbk-scripts/fbk/capture/retention.py
test_tasks: [task-03]
completion_gate: "task-03 tests pass"
---

# 1 Objective

Produce the size-cap retention pruner for `.fbk-capture/events.jsonl`: it drops the oldest lines once the file exceeds a byte cap, never drops lines whose spec is baseline-locked until those locked lines themselves exceed a defined fraction of the cap, then drops oldest locked lines past that ceiling and writes a durable over-cap sentinel, and leaves the file byte-intact on any failure.

# 2 Context

The events file self-prunes at a byte cap (default about 5MB) by dropping oldest lines. A baseline-comparison workflow protects a spec's lines via an empty lock file under `.fbk-capture/locked/`; the caller passes those locked spec names as `protect_specs`. Locked lines are never dropped under normal pruning — but a sandboxed agent can write a lock, so unbounded protected growth would exhaust the disk. The pruner therefore caps total protected bytes at a defined fraction of the cap; past that ceiling it drops oldest locked lines too and writes the durable sentinel `.fbk-capture/.retention-warning` (a normal prune, dropping only unlocked lines, never writes the sentinel — the report reads the sentinel to surface an over-cap warning). Any failure must leave the original bytes unchanged rather than corrupting the file.

This is a pure file operation, exercised through `tmp_path`. Each event line is a JSON object carrying a `spec` field; a line whose `spec` is in `protect_specs` is protected.

# 3 Instructions

1. Create `fbk/capture/retention.py`. Define module constants: `DEFAULT_MAX_BYTES = 5 * 1024 * 1024` and `PROTECTED_FRACTION = 0.5` (the defined fraction of the cap that protected bytes may occupy — document this choice in a comment; 0.5 keeps protected baselines from monopolizing the file while leaving headroom for current capture).
2. Implement `prune_if_needed(events_path: str, max_bytes: int, protect_specs: set[str]) -> None`. Wrap the entire body in a `try/except Exception` that returns `None` (never raises) and never partially overwrites — build the new content fully in memory and write it only once at the end, so a failure before the single write leaves the original file untouched. Completion: a call against a directory path or otherwise-failing target raises nothing and leaves bytes unchanged.
3. Early-exit when no pruning is needed: if the file does not exist or its size is `<= max_bytes`, return without rewriting (do not touch the file). Completion: an under-cap file is byte-for-byte unchanged after the call.
4. Read all lines preserving order (oldest first = top of file). For each line, parse its JSON to read the `spec` field; classify each line as protected (its `spec` in `protect_specs`) or unprotected. A line that fails to parse is treated as unprotected. Completion: protected vs unprotected classification matches the lines' `spec` values.
5. Pruning algorithm: keep ALL protected lines and as many of the NEWEST unprotected lines as fit, dropping oldest unprotected lines first, until total bytes `<= max_bytes`. If after dropping every unprotected line the protected lines alone still exceed `max_bytes * PROTECTED_FRACTION` (the protected-bytes ceiling), drop oldest protected lines too until protected bytes are at/under that ceiling, and in that case write the sentinel. Completion: an over-cap unprotected file is pruned to `<= max_bytes` with the newest lines retained and at least one line surviving; a protected spell under the ceiling keeps every protected line while unprotected lines drop.
6. Sentinel write: when (and only when) the algorithm dropped one or more protected/locked lines because protected bytes exceeded the ceiling, write `.fbk-capture/.retention-warning` (resolve it as a sibling of the events file: the `.fbk-capture/` dir is `os.path.dirname(events_path)`). A normal prune (only unprotected lines dropped) must NOT create the sentinel. Completion: the sentinel exists after an over-ceiling prune and is absent after a normal prune.
7. Write the surviving lines back to `events_path` in original order in a single write. Completion: the resulting file size is `<= max_bytes`, contains at least one line, and the last original line is still present while an early original line is gone.

# 4 Files to create/modify

- Create `fbk/capture/retention.py`

# 5 Test requirements

Makes task-03 (`tests/test_capture_retention.py`) pass: drops oldest past cap with newest retained; never drops protected lines under the ceiling; drops oldest protected lines past the ceiling with some surviving; writes the `.retention-warning` sentinel only on an over-ceiling prune; leaves the file intact on failure; no rewrite when under cap.

# 6 Acceptance criteria

Primary: task-03's tests pass. Covers AC-14 (size cap + baseline protection) and AC-25 (protected-bytes ceiling + surfaced over-cap warning sentinel).

# 7 Model

Sonnet

# 8 Wave

2
