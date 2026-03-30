---
id: task-11
type: implementation
wave: 2
covers: [AC-31, AC-32, AC-33, AC-34, AC-35]
files_to_modify:
  - assets/fbk-docs/fbk-design-guidelines/quality-detection.md
test_tasks: [task-01]
completion_gate: "task-01 tests 9-14 pass"
---

## Objective

Adds 5 new structural detection targets to `quality-detection.md`, bringing the total from 6 to 11.

## Context

The file uses level-2 headings (`## Title`) for each detection target, followed by a description paragraph and a "Detect this when..." or "Flag..." sentence. The current 6 targets are: Mixed logic and side effects, Ambient state access, Non-importable behaviors, Multi-responsibility modules, Caller re-implementation, Composition opacity.

New targets must follow the same format: `## Title` heading, then imperative-voice description with a detection heuristic.

## Instructions

1. After the last existing section ("## Composition opacity" and its content), append the following 5 sections:

```
## Parallel collection coupling

Flag parallel collections (arrays, slices, maps) whose elements correspond by index or key, where reordering one collection silently breaks the correspondence with the other. Detect this when two or more collections are iterated in lockstep by index, or when a value from one collection is used to look up a corresponding entry in another without a structural binding (e.g., a struct or tuple) that enforces the relationship.

## Dead infrastructure

Flag code that constructs, initializes, or declares components (structs, classes, handlers, configurations, middleware) that are never invoked in the application's runtime path. Unlike dead code (unreachable branches), dead infrastructure is reachable code that is simply never called. Detect this when a constructor, factory, or initialization call produces a value that is assigned but never passed to any consumer, or when a registered handler has no route or event that triggers it.

## Semantic drift

Flag code whose documented or named meaning diverges from its actual behavior. This includes function names that describe an action the function does not perform, variable names that describe a property the value does not hold, and module names that describe a responsibility the module does not own. Detect this when reading the name or documentation produces a behavioral expectation that the code contradicts.

## Silent error and context discard

Flag code that discards errors without logging or propagating them, or that replaces a caller-provided context with a fresh background context, discarding cancellation signals, deadlines, or trace propagation. Detect this when an error return is assigned to `_` or ignored without a comment justifying the discard, or when a function that receives a context parameter constructs a new context instead of forwarding the caller's.

## String-based type discrimination

Flag code that branches on string content (error messages, type name strings, format patterns) to determine control flow, instead of using typed errors, enums, constants, or interface checks. Detect this when a conditional expression applies string matching operations (Contains, HasPrefix, ==) to an error message, type name, or status string to select a code path.
```

## Files to create/modify

- `assets/fbk-docs/fbk-design-guidelines/quality-detection.md` (modify)

## Test requirements

Tests from task-01: Test 9 (heading count >= 11), Test 10 (parallel collection keyword), Test 11 (dead infrastructure keyword), Test 12 (semantic drift keyword), Test 13 (silent error or context discard keyword), Test 14 (string-based type keyword).

## Acceptance criteria

- AC-31: "Parallel collection coupling" detection target present.
- AC-32: "Dead infrastructure" detection target present.
- AC-33: "Semantic drift" detection target present.
- AC-34: "Silent error and context discard" detection target present.
- AC-35: "String-based type discrimination" detection target present.
- Total level-2 headings >= 11.

## Model

Haiku

## Wave

Wave 2
