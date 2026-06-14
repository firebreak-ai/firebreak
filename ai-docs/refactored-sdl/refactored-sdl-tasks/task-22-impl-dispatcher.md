---
id: task-22
type: implementation
wave: 1
covers: [AC-01, AC-03]
files_to_modify:
  - assets/fbk-scripts/fbk/__init__.py
test_tasks: [task-04]
dependencies: []
completion_gate: "the referenced test tasks pass"
---

## 1. Objective

Adds the three new gate subcommand entries to `COMMAND_MAP` in `assets/fbk-scripts/fbk/__init__.py` so the dispatcher routes `intent-gate`, `design-gate`, and `code-review-gate` to their modules.

## 2. Context

This is the orchestrator/dispatcher wiring task. `fbk/__init__.py` defines `COMMAND_MAP`, the dict the `fbk.py` dispatcher uses to map a hyphenated subcommand name to a dotted module path. The three new entries are pinned exactly (Interface contract #1):

```python
"intent-gate": "fbk.gates.intent",
"design-gate": "fbk.gates.design",
"code-review-gate": "fbk.gates.code_review",
```

Note the load-bearing detail: `code-review-gate` (hyphen) maps to `fbk.gates.code_review` (underscore module path). The test asserts this exact value, not just key presence.

This task registers the COMMAND_MAP entries only. The gate modules themselves (`fbk/gates/intent.py`, `fbk/gates/design.py`, `fbk/gates/code_review.py`) are created by their own tasks (task-27, task-28, task-34). A registered command whose module does not yet exist is fine for the dispatcher test (task-04 asserts only the dict contents, importing `fbk` not the gate modules) — the dict is just data. This is the "soft runtime dep" the spec notes: the dispatcher slice has no build-order dependency on the gate modules.

The current `COMMAND_MAP` has 15 entries (read the file: spec-gate, review-gate, breakdown-gate, task-reviewer-gate, test-hash-gate, task-completed, dispatch-status, pipeline, audit, config, state, session-logger, session-manager, session-state, ralph). Adding three brings it to 18. The task-04 test renames the misnamed `test_command_map_contains_all_14_commands` to `test_command_map_contains_all_18_commands` and asserts `len(COMMAND_MAP) == 18` after the three new keys are added. The three positive-presence tests (`test_intent_gate_maps_to_exact_module`, `test_design_gate_maps_to_exact_module`, `test_code_review_gate_maps_to_exact_module`) are the load-bearing assertions and require the three exact entries above.

## 3. Instructions

1. Open `assets/fbk-scripts/fbk/__init__.py`.

2. Add these three entries to the `COMMAND_MAP` dict. Place them with the other gate entries (after `"test-hash-gate": "fbk.gates.test_hash",`), exactly:
   ```python
   "intent-gate": "fbk.gates.intent",
   "design-gate": "fbk.gates.design",
   "code-review-gate": "fbk.gates.code_review",
   ```
   Completion: `python3 -c "import fbk; assert fbk.COMMAND_MAP['intent-gate']=='fbk.gates.intent'; assert fbk.COMMAND_MAP['design-gate']=='fbk.gates.design'; assert fbk.COMMAND_MAP['code-review-gate']=='fbk.gates.code_review'"` exits 0 (run from `assets/fbk-scripts`).

3. Run the paired test: from `assets/fbk-scripts`, `python3 -m pytest tests/test_dispatcher.py -q`. The renamed count test and the three positive-presence tests must pass.

## 4. Files to create/modify

- `assets/fbk-scripts/fbk/__init__.py` (modify)

## 5. Test requirements

This task makes `assets/fbk-scripts/tests/test_dispatcher.py` (task-04) pass: the renamed `test_command_map_contains_all_18_commands` (which asserts `len(COMMAND_MAP) == 18`) and the three `test_*_gate_maps_to_exact_module` methods. No new tests are written here. Do not edit the test file.

## 6. Acceptance criteria

- AC-01: `intent-gate` is registered in `COMMAND_MAP` (routing for the intent phase).
- AC-03: `design-gate` is registered in `COMMAND_MAP` (routing for the design phase).
- The `code-review-gate` → `fbk.gates.code_review` (underscore) mapping is present, which AC-09 depends on.
- Primary criterion: the task-04 tests pass.

## 7. Model

Haiku

## 8. Wave

Wave 1
