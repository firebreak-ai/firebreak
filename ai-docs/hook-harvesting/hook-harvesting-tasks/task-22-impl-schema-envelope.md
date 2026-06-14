---
id: task-22
type: implementation
wave: 2
covers: [AC-13, AC-26]
files_to_create:
  - assets/fbk-scripts/fbk/capture/__init__.py
  - assets/fbk-scripts/fbk/capture/schema.py
test_tasks: [task-02]
completion_gate: "task-02 tests pass"
---

# 1 Objective

Produce the capture subsystem's schema module: the closed event-type vocabulary, the registered-source tuple, a central level-based redactor that strips free-text payloads at `standard`, and a build/test-time drift check that flags any event-type literal not in the vocabulary. Also create the `fbk/capture/` package init so the subsystem is importable.

# 2 Context

The metrics plane records pipeline facts as a versioned JSON envelope, one object per line. Every envelope's `event_type` must be a member of a fixed, closed vocabulary; nothing else may be written. The schema module owns that vocabulary plus two guards: a redactor that enforces "payloads only at `full`" in ONE place (so no producer can leak by forgetting to strip), and a drift check that scans a source tree for event-type string literals that drifted out of the vocabulary.

This is the foundation of the capture subsystem under `fbk/capture/`, a new cohesive subpackage alongside the existing `fbk/gates/` and `fbk/hooks/`. Follow the existing package convention: each subpackage has an `__init__.py` (see `fbk/gates/__init__.py`). The module is pure functions over data — no filesystem except the drift check, which globs `.py` files under a scan root and reads them.

Invariants:
- The vocabulary is exactly six members and nothing more.
- Redaction at `standard` (and at `off`) removes free-text payload keys; at `full` the data passes through unchanged.
- The drift check returns a list (empty when clean) of out-of-vocabulary event-type literals it found.

# 3 Instructions

1. Create `fbk/capture/__init__.py` (a docstring line is enough — it marks the package). Completion: `from fbk.capture import schema` resolves.
2. In `fbk/capture/schema.py`, define the closed vocabulary tuple exactly:
   `EVENT_TYPES = ("PIPELINE_COMMAND", "VERIFICATION_RESULT", "CODE_REVIEW_ROUNDS", "TOOL_USE", "SUBAGENT_STOP", "LIFECYCLE")`.
   Completion: `set(EVENT_TYPES)` equals the six-member set and `len(set(EVENT_TYPES)) == 6`.
3. Define the registered-source tuple exactly:
   `SOURCES = ("hook_router", "chokepoint", "task_completed", "code_review")`.
   Completion: the tuple holds those four source names; the redaction test iterates it.
4. Implement `redact(data: dict, level: str) -> dict`. At `"full"` return the data unchanged (return it as-is or a shallow copy carrying every key verbatim). At any other level (`"standard"`, `"off"`, or unknown — treat unknown as at-least-standard-strict) return a copy with the free-text payload keys removed while structural/numeric keys survive. Define a module-level `FREETEXT_KEYS` set covering the free-text payload fields the producers carry — at minimum: `tool_input`, `tool_args`, `prompt_text`, `text`, `files`, `out_of_scope_files`, `scope_violations`, `round_detail`, `args`, `command`, `output`, `reason_text`. (These are the tool arguments, prompt text, scope-violation paths, and round detail the spec names; structural fields like `count`, numeric totals, and severity breakdowns are NOT free-text and must survive.) Completion: `redact({"tool_input": {...}, "count": 3}, "standard")` has no `tool_input` and keeps `count == 3`; `redact(same, "full")` returns `tool_input` verbatim; `redact(same, "off")` strips like standard.
5. Implement `check_drift(scan_root: str) -> list[str]`. Glob `*.py` under `scan_root` (recursively), read each file's text, and find string literals that look like event-type names but are not in `EVENT_TYPES`. Concretely: scan for ALL-CAPS-with-underscores quoted string literals appearing in a capture context, and return those not in the vocabulary. To stay robust and avoid false positives, restrict the match to quoted tokens that match the event-type shape (e.g. regex `["']([A-Z][A-Z_]+)["']`) AND that the test plants as a foreign event type — return any such matched literal not in `EVENT_TYPES`. The canonical shipped `fbk/capture/` tree must return an empty list (so do not emit false positives on legitimate constants; if needed, only flag literals that pair with an event-writing call or that the test's fixture file plants). Keep it simple: returning the set of ALL-CAPS quoted literals found minus `EVENT_TYPES` satisfies both tests as long as the shipped capture modules only ever quote canonical event-type names where they quote ALL-CAPS tokens. Completion: `check_drift(<fbk/capture dir>)` returns `[]`; `check_drift(<tmp dir with a file quoting "GHOST_EVENT">)` returns a non-empty list containing `"GHOST_EVENT"`.
6. Optionally expose `is_known_event_type(event_type) -> bool` returning `event_type in EVENT_TYPES` (the test asserts tuple membership primarily; this helper is a convenience). Completion: returns True for `"TOOL_USE"`, False for `"MADE_UP"`.

Note on drift-check false positives: every other capture module you and sibling tasks write must quote event-type strings ONLY from this vocabulary. If a module needs an ALL-CAPS constant that is not an event type, assign it to a named constant rather than quoting a bare ALL-CAPS literal inline, so `check_drift` stays clean.

# 4 Files to create/modify

- Create `fbk/capture/__init__.py`
- Create `fbk/capture/schema.py`

# 5 Test requirements

Makes task-02 (`tests/test_capture_schema.py`) pass: the six-member vocabulary equality and length, known/unknown membership, `check_drift` empty on shipped sources and non-empty (containing `"GHOST_EVENT"`) on a fixture, and `redact` stripping free-text at `standard`/`off` while preserving structural keys and returning payloads verbatim at `full`.

# 6 Acceptance criteria

Primary: task-02's tests pass. Covers AC-13 (closed vocabulary + drift check) and AC-26 (central level-based redaction).

# 7 Model

Haiku

# 8 Wave

2
