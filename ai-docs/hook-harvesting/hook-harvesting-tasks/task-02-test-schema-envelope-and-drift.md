---
id: task-02
type: test
wave: 2
covers: [AC-13, AC-26]
files_to_create:
  - assets/fbk-scripts/tests/test_capture_schema.py
completion_gate: "tests compile and fail before implementation"
---

# Objective

Write the unit tests that pin the event-envelope vocabulary guard, the build/test-time schema-drift check, and the central level-based redactor that strips free-text payloads at `standard`.

# Context

The capture subsystem records events as a versioned envelope whose `event_type` must be one of a closed vocabulary: exactly `PIPELINE_COMMAND`, `VERIFICATION_RESULT`, `CODE_REVIEW_ROUNDS`, `TOOL_USE`, `SUBAGENT_STOP`, `LIFECYCLE`. The schema module owns this vocabulary, a build/test-time drift check that fails when any capture module references an event type absent from the canonical list, and a shared `redact(data, level)` that the writer calls so payload stripping lives in one place: at `standard`, no record carries a free-text payload field (tool arguments, prompt text, scope-violation file paths, round detail); at `full`, payloads pass through.

These are pure functions over data — no filesystem needed except for the drift check, which scans a source tree. New modules under `fbk/capture/` do not exist yet, so import them inside `try/except ImportError` and `pytest.skip` when absent, matching the suite's pattern in `tests/test_dispatcher.py` and `tests/test_gates_code_review.py`. Use `from tests import capture_fixtures` for the envelope builder.

Pinned schema contract (call these verbatim):
- `schema.EVENT_TYPES = ("PIPELINE_COMMAND", "VERIFICATION_RESULT", "CODE_REVIEW_ROUNDS", "TOOL_USE", "SUBAGENT_STOP", "LIFECYCLE")` — the closed vocabulary tuple.
- `schema.SOURCES = ("hook_router", "chokepoint", "task_completed", "code_review")` — the registered producer tuple the redaction test iterates.
- `schema.redact(data: dict, level: str) -> dict` — at `"standard"` strips free-text payload keys (tool args, prompt text, scope-violation paths, round detail); at `"full"` returns the data unchanged. The exact strip-set is owned by the implementation; the test asserts that the free-text keys it placed in the `full` fixture are ABSENT at `standard`.
- `schema.check_drift(scan_root: str) -> list[str]` — accepts a scan-root argument and returns the event-type string literals found under it that are not in `EVENT_TYPES` (empty when clean).

# Instructions

1. Create `tests/test_capture_schema.py`. At top, attempt `from fbk.capture import schema` inside `try/except ImportError` and set a module-level `pytestmark = pytest.mark.skipif(schema is None, reason="fbk.capture.schema not yet implemented")` so the whole file skips cleanly when the module is absent (red phase: collection succeeds, tests do not pass).
2. `test_vocabulary_is_exactly_the_six_known_types`: assert `set(schema.EVENT_TYPES)` (the exported vocabulary collection) equals exactly `{"PIPELINE_COMMAND", "VERIFICATION_RESULT", "CODE_REVIEW_ROUNDS", "TOOL_USE", "SUBAGENT_STOP", "LIFECYCLE"}`. Pair the equality with a length assertion `len(set(schema.EVENT_TYPES)) == 6`.
3. `test_known_event_type_is_recognized` and `test_unknown_event_type_is_rejected`: assert membership against the vocabulary tuple — `"TOOL_USE" in schema.EVENT_TYPES` is True and `"MADE_UP" not in schema.EVENT_TYPES` is True. (If the module also exposes an `is_known_event_type` predicate, assert it as well; the tuple-membership assertion is the load-bearing one.)
4. `test_drift_check_passes_on_canonical_sources`: call `schema.check_drift(<capture-package-source-dir>)` against the shipped `fbk/capture/` source tree and assert it returns an empty list. Pair with a presence assertion that the return value is a list (`isinstance(result, list)`).
5. `test_drift_check_flags_a_foreign_event_type`: write a `tmp_path` `.py` file referencing the string literal `"GHOST_EVENT"` (not in `EVENT_TYPES`); call `schema.check_drift(str(tmp_path))`; assert the returned list is non-empty and contains `"GHOST_EVENT"`.
6. `test_redact_strips_freetext_at_standard`: build a `data` dict carrying free-text payload fields (e.g. `{"tool_input": {"command": "rm -rf /"}, "prompt_text": "secret", "files": ["a.py"], "count": 3}`); call `schema.redact(data, "standard")` and assert the free-text payload fields (`tool_input`, `prompt_text`) are absent or emptied while structural/numeric fields (`count`) survive. Assert exact resulting key presence, not truthiness. (The free-text keys to assert ABSENT are exactly those you placed in the `full` fixture in the next test — keep the two fixtures' free-text key sets identical so "present at full, absent at standard" is a clean diff.)
7. `test_redact_preserves_payload_at_full`: call `schema.redact(data, "full")` and assert the free-text fields are present and equal to the input verbatim.
8. `test_redact_off_level_strips_like_standard_or_stricter`: call `schema.redact(data, "off")` and assert no free-text payload survives (off is at least as strict as standard).

# Files to create/modify

- `tests/test_capture_schema.py`

# Test requirements

- `test_vocabulary_is_exactly_the_six_known_types` (unit): closed vocabulary equality — assert the exact six-member set.
- `test_known_event_type_is_recognized` / `test_unknown_event_type_is_rejected` (unit): membership predicate — True for a vocabulary member, False for a foreign type.
- `test_drift_check_passes_on_canonical_sources` (unit): drift check returns empty list on shipped sources.
- `test_drift_check_flags_a_foreign_event_type` (unit): `check_drift(scan_root)` returns a non-empty list containing `"GHOST_EVENT"` for a fixture source.
- `test_redact_strips_freetext_at_standard` (unit): standard-level redaction drops free-text payload keys, keeps structural keys.
- `test_redact_preserves_payload_at_full` (unit): full-level redaction returns payload verbatim.
- `test_redact_off_level_strips_like_standard_or_stricter` (unit): off-level redaction carries no free-text payload.

# Acceptance criteria

AC-13 (vocabulary guard + drift check), AC-26 (central level-based redaction). Gate: tests compile and fail (skip on absent module, then fail on first real run against an empty implementation) before implementation.

# Model

Haiku — single-file unit tests over pure functions with exact assertions.

# Wave

2
