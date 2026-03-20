---
id: T-06
type: implementation
wave: 2
covers: ["AC-05"]
files_to_modify: ["../../home/dot-claude/docs/sdl-workflow/task-compilation.md"]
test_tasks: ["T-02"]
completion_gate: "task-compilation.md contains verified interface contracts section, orchestrator risk flagging with Sonnet routing, codebase-grounded compilation section with mismatch-resolution flow, and category field in task.json schema"
---

## Objective

Updates the task compilation guide with verified interface contracts, codebase-grounded compilation, orchestrator task handling, and the `category` field in the task.json schema.

## Context

The current task compilation guide at `home/dot-claude/docs/sdl-workflow/task-compilation.md` specifies task file structure, sizing constraints, and the task manifest schema. It does not specify interface contracts between tasks, does not require the breakdown agent to read actual source files during compilation, and the task.json schema does not include a `category` field.

The greenfield test showed 4 of 5 bugs were contract-level mismatches: tasks made assumptions about conventions (import styles, key strings, wiring patterns) that didn't match the actual code. The fix is two-fold: (1) tasks must specify interface contracts explicitly, and (2) the breakdown agent must verify those contracts against actual code.

## Instructions

1. After the "Task File Structure" section's item 5 (Test requirements), add a new item or expand item 2 (Context):

   **Interface contracts**: When a task references files created or modified by other tasks, specify at minimum: import/export convention (default vs named), module type (ESM/CJS), key string or enum conventions, and wiring patterns. This list is a floor — extend with project-specific contract types.

2. Add an "Orchestrator tasks" subsection to the task file structure or sizing section:

   When a task modifies the orchestrator file (the file that wires all modules together), route to Sonnet minimum. Include a wiring checklist section in the task file: what must be imported, initialized, updated per frame/tick, and cleaned up.

3. Add a "Codebase-grounded compilation" section after the existing compilation principle:

   The breakdown agent reads actual files that tasks reference during compilation. This applies to files that exist at compilation time — greenfield tasks creating new files use spec-derived contracts.

   When compiling interface contracts for existing files: read the file, determine actual convention, write it in the task. If the spec's claim doesn't match the code: if code is authoritative (existing convention), correct the task. If spec is authoritative (new design), present the mismatch to the user ("the spec says X but the code uses Y — which is correct?") and wait for resolution before continuing.

   For brownfield: read existing test files for testing conventions, existing modules for import/export patterns, existing config for environment requirements.

4. In the task.json schema section, add `category` as a top-level field:

   ```json
   {
     "spec": "...",
     "category": "feature | corrective | testing-infrastructure",
     "tasks": [...]
   }
   ```

   Default: `feature`. Document that the gate reads this field to determine which invariant set to apply.

## Files to create/modify

Modify:
- `home/dot-claude/docs/sdl-workflow/task-compilation.md`

## Test requirements

Semi-manual: During brownfield testing, confirm the breakdown agent reads actual source files and that compiled tasks contain interface contracts matching real code conventions.

## Acceptance criteria

- AC-05: Interface contract requirements present with minimum contract types listed
- AC-05: Orchestrator task handling with Sonnet routing and wiring checklist
- AC-05: Codebase-grounded compilation section with mismatch-resolution flow

## Model

Sonnet

## Wave

Wave 2
