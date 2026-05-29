---
id: task-04
type: test
wave: 1
covers: [AC-01, AC-03]
files_to_modify:
  - assets/fbk-scripts/tests/test_dispatcher.py
completion_gate: "tests compile and fail before implementation"
---

## 1. Objective

Modifies `assets/fbk-scripts/tests/test_dispatcher.py` to add positive-presence assertions that `intent-gate`, `design-gate`, and `code-review-gate` are each individually present in `COMMAND_MAP` with their exact module paths, and to rename the existing count test to reflect the new total (18).

## 2. Context

The current `COMMAND_MAP` in `assets/fbk-scripts/fbk/__init__.py` contains 15 entries (including `session-state`). After implementation it must contain 3 additional entries per Interface contract #1:
- `"intent-gate": "fbk.gates.intent"`
- `"design-gate": "fbk.gates.design"`
- `"code-review-gate": "fbk.gates.code_review"`

Note: `code-review-gate` maps to `fbk.gates.code_review` (underscore module path, not hyphen). This is pinned in Interface contract #1 and must be asserted exactly.

The existing count test is misnamed `test_command_map_contains_all_14_commands` (the live map already holds 15 entries, not 14). It uses a subset check (`issubset`) which would pass even if the new commands are absent. The spec requires positive-presence assertions — individual `in` checks — plus a renamed count test that asserts the exact total. After implementation adds the three new gates the map holds 18 entries, so the count test is renamed to `test_command_map_contains_all_18_commands` and asserts `len(COMMAND_MAP) == 18`.

The existing test class `TestDispatcherCommandMap` already contains the method to modify. The existing `test_command_map_available` test is unchanged.

The new tests must fail (the keys are absent from `COMMAND_MAP`) before implementation and pass after. That is the correct red state.

## 3. Instructions

1. Open `assets/fbk-scripts/tests/test_dispatcher.py`.

2. In the class `TestDispatcherCommandMap`, rename the existing method `test_command_map_contains_all_14_commands` to `test_command_map_contains_all_18_commands`. Inside it, update the `expected_commands` set to add `"intent-gate"`, `"design-gate"`, and `"code-review-gate"` (the live map already has 15 entries; the three additions bring the total to 18). Replace the subset (`issubset`) check with an exact-count assertion `assert len(fbk.COMMAND_MAP) == 18` so the test catches both missing and extra entries. Keep the baseline membership check for the prior-contract commands.

3. Still inside `TestDispatcherCommandMap`, add three new methods, each importing `fbk` inside a try/except as the existing pattern does:

   ```python
   def test_intent_gate_maps_to_exact_module(self):
       """COMMAND_MAP["intent-gate"] == "fbk.gates.intent"."""
       try:
           import fbk
       except ImportError:
           pytest.skip("fbk module not yet implemented")
       assert "intent-gate" in fbk.COMMAND_MAP, \
           "intent-gate missing from COMMAND_MAP"
       assert fbk.COMMAND_MAP["intent-gate"] == "fbk.gates.intent", \
           f"Expected 'fbk.gates.intent', got '{fbk.COMMAND_MAP.get('intent-gate')}'"

   def test_design_gate_maps_to_exact_module(self):
       """COMMAND_MAP["design-gate"] == "fbk.gates.design"."""
       try:
           import fbk
       except ImportError:
           pytest.skip("fbk module not yet implemented")
       assert "design-gate" in fbk.COMMAND_MAP, \
           "design-gate missing from COMMAND_MAP"
       assert fbk.COMMAND_MAP["design-gate"] == "fbk.gates.design", \
           f"Expected 'fbk.gates.design', got '{fbk.COMMAND_MAP.get('design-gate')}'"

   def test_code_review_gate_maps_to_exact_module(self):
       """COMMAND_MAP["code-review-gate"] == "fbk.gates.code_review" (underscore)."""
       try:
           import fbk
       except ImportError:
           pytest.skip("fbk module not yet implemented")
       assert "code-review-gate" in fbk.COMMAND_MAP, \
           "code-review-gate missing from COMMAND_MAP"
       assert fbk.COMMAND_MAP["code-review-gate"] == "fbk.gates.code_review", \
           f"Expected 'fbk.gates.code_review', got '{fbk.COMMAND_MAP.get('code-review-gate')}'"
   ```

4. Verify the file compiles with no syntax errors (the implementing agent should confirm `python3 -m py_compile assets/fbk-scripts/tests/test_dispatcher.py` exits 0).

## 4. Files to create/modify

- `assets/fbk-scripts/tests/test_dispatcher.py` (modify)

## 5. Test requirements

Three new pytest unit tests, one per new `COMMAND_MAP` key:
- `test_intent_gate_maps_to_exact_module`: asserts key present and maps to `"fbk.gates.intent"`. Fails before implementation.
- `test_design_gate_maps_to_exact_module`: asserts key present and maps to `"fbk.gates.design"`. Fails before implementation.
- `test_code_review_gate_maps_to_exact_module`: asserts key present and maps to `"fbk.gates.code_review"`. Fails before implementation.

The renamed `test_command_map_contains_all_18_commands` also fails before implementation (the live map has 15 entries, so `len(COMMAND_MAP) == 18` is false until the three keys are added).

## 6. Acceptance criteria

Covers routing of AC-01 (intent-gate) and AC-03 (design-gate), plus the code-review-gate registration that AC-09 depends on.

The exact module path for `code-review-gate` is `fbk.gates.code_review` (underscore) per Interface contract #1 — this is the load-bearing value the test must assert, not merely key presence.

## 7. Model

Haiku

## 8. Wave

Wave 1
