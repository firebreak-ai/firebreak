---
id: T-04
type: implementation
wave: 2
covers: ["AC-06"]
files_to_create: ["home/dot-claude/docs/sdl-workflow/ai-failure-modes.md"]
files_to_modify: []
test_tasks: ["T-01"]
completion_gate: "T-01 tests 25-27 pass (checklist exists, contains 10+ numbered items, contains key failure mode keywords)"
---

## Objective

Creates `home/dot-claude/docs/sdl-workflow/ai-failure-modes.md` — a numbered checklist of 10 AI failure mode patterns with detection heuristics for each.

## Context

The AI failure mode checklist is a shared reference document used by the code review skill when no specs are available (cleanup mode). It is also available to other flows — the test reviewer, spec reviewer, and task reviewer can reference it. The checklist formalizes patterns observed in retrospective data from Phase 1 and Phase 1.5.

The 10 failure modes are defined in the spec. Each entry needs a pattern description and a detection heuristic (what to look for in code). The checklist is not a prompt — it is a reference document that agents read when instructed by the orchestrator.

T-01 validates this file with three tests:
- File exists and is non-empty
- Contains at least 10 numbered items (lines matching `^[0-9]+\.` or similar numbered list patterns)
- Contains at least 5 of these keywords (case-insensitive): `re-implement`, `duplication`, `magic number`, `dead code`, `hardcoded`, `inconsistent`, `middleware`, `trivially-true`, `test name`, `surface-level`

## Instructions

1. Read `home/dot-claude/docs/sdl-workflow/corrective-workflow.md` to understand the existing doc conventions in this directory: direct-address imperatives, no preambles, start with content.

2. Create `home/dot-claude/docs/sdl-workflow/ai-failure-modes.md` with the following structure:

3. Start with a one-line heading: `# AI Failure Mode Checklist`

4. Add a one-sentence purpose line: `Use this checklist when reviewing code without specs or when auditing for structural issues.`

5. Write 10 numbered entries. Each entry has this structure:
   - **Number and pattern name** as a bold heading on the numbered line
   - **Description**: One sentence describing the failure mode
   - **Detection heuristic**: One sentence starting with "Look for" or "Check for" describing what to search for in code

6. The 10 entries, in order:

   1. **Tests that re-implement production logic** — Tests validate their own inline copy of the logic rather than exercising the actual system function. Detection: Look for test files that duplicate production function bodies or compute expected values using the same algorithm as the code under test.

   2. **Copy-paste duplication across modules** — Near-identical code blocks appear in multiple files instead of calling a shared function. Detection: Look for functions in different files with similar structure, variable names, and control flow that differ only in minor details (status strings, return values).

   3. **Magic numbers as bare literals** — Spec-defined values (thresholds, sizes, timings) appear as bare numeric literals instead of named constants, especially when the same value appears in multiple files. Detection: Check for numeric literals that appear in conditional expressions or assignments in more than one file without a corresponding constant declaration.

   4. **Dead code from abandoned approaches** — Functions, imports, or variables that are defined but never called, typically left behind when an AI assistant tried a different approach. Detection: Look for unused imports, unreferenced function declarations, and commented-out code blocks that span more than 3 lines.

   5. **Hardcoded coupling where abstraction was specified** — Direct references to concrete implementations where the spec called for abstraction (interface, configuration, dependency injection). Detection: Check for instantiation of specific classes or direct file references where the spec or architecture describes an abstraction layer.

   6. **Inconsistent architectural patterns** — The correct pattern is followed in some files but bypassed in others (e.g., some modules use the service layer, others call the database directly). Detection: Look for modules that bypass established intermediaries (services, middleware, caches) that peer modules use for the same operation.

   7. **Middleware or layers defined but never connected** — Middleware, interceptors, or wrapper layers are implemented but never registered, mounted, or called in the application's initialization path. Detection: Check for middleware or layer classes/functions with no references in the application's entry point, router setup, or initialization code.

   8. **Trivially-true assertions** — Test assertions with OR-conditions where one branch is always true, or assertions that compare a value to a range so wide it cannot fail. Detection: Look for assertion expressions containing logical OR where one operand is a tautology, or range checks where the bounds exceed any possible value.

   9. **Test names that contradict their assertions** — The test's `describe`/`it` label claims to verify one behavior, but the assertion checks something different. Detection: Check for tests where the string in the test name references a behavior (e.g., "rejects expired tokens") that does not appear in any assertion within the test body.

   10. **Surface-level fixes that bypass core mechanisms** — Bug fixes that patch symptoms at the call site instead of correcting the root cause in the responsible module, creating a shadow implementation that diverges from the core. Detection: Look for conditional guards or value overrides added at call sites that duplicate logic already present in the function being called.

7. End the file after item 10. No summary section, no closing paragraph.

## Files to create/modify

- `home/dot-claude/docs/sdl-workflow/ai-failure-modes.md` (create)

## Test requirements

This is an implementation task. The corresponding test task T-01 validates:
- Test 25: File exists and is non-empty
- Test 26: Contains at least 10 numbered items
- Test 27: Contains at least 5 key failure mode keywords

## Acceptance criteria

- AC-06 (partial): The AI failure mode checklist exists as a shared reference document containing all 10 defined failure modes with detection heuristics

## Model

Haiku

## Wave

Wave 2
