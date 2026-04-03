---
id: task-10
type: implementation
wave: 2
covers: [AC-36, AC-37, AC-38, AC-39, AC-40, AC-41, AC-42]
files_to_modify:
  - assets/fbk-docs/fbk-sdl-workflow/ai-failure-modes.md
test_tasks: [task-01]
completion_gate: "task-01 tests 1-8 pass"
---

## Objective

Expands the AI failure mode checklist from 5 items to 12 by splitting 2 existing items into broader+specific pairs and adding 5 new items.

## Context

The checklist covers failure modes detectable without a spec as source of truth. The current 5 items use a numbered list format (`1. **Bold title** — description`). The spec specifies 12 total items after changes.

AC-36 expands item 1 to cover string bare literals. To reach 12 total items, item 1 is broadened to "bare literals" (covering both numeric and string) and a new companion item is added for the specific string-literal variant.

AC-38 expands item 4 to cover non-enforcing tests. Item 4 is broadened from "test names that contradict their assertions" to "non-enforcing tests" and a new companion item covers the previously-uncovered sub-types (empty gates, advisory assertions, unconditional skips).

Five new items (AC-37, AC-39, AC-40, AC-41, AC-42) add: dead infrastructure, comment-code drift, zero-value sentinel ambiguity, context bypass, and string-based error classification.

Total: 5 original (2 broadened) + 2 companion items from splits + 5 new = 12.

## Instructions

1. Replace item 1's title from `**Magic numbers as bare literals**` to `**Bare literals (numeric and string)**`.

2. Replace item 1's entire description with: `Spec-defined values (thresholds, sizes, timings, discriminator strings) appear as bare literals instead of named constants. Check for numeric literals in conditional expressions or assignments that appear in multiple files without a corresponding constant declaration. Check for string property keys or discriminator values used in conditional logic without a named constant — bare string literals used for type discrimination are as fragile as bare numeric literals.`

3. Replace item 4's title from `**Test names that contradict their assertions**` to `**Non-enforcing tests (name-assertion mismatch)**`.

4. Replace item 4's entire description with: `The test's describe/it label claims to verify one behavior, but the assertion checks something different. Check for tests where the string in the test name references a behavior (e.g., "rejects expired tokens") that does not appear in any assertion within the test body.`

5. After item 5 ("Surface-level fixes that bypass core mechanisms" and its description), append these 7 new items:

```

6. **Bare string literal type discrimination** — A specialized bare literal pattern: conditional logic branches on string values (error messages, type names, status strings) that are not defined as constants. Check for string equality checks or substring matching in conditional expressions where the compared string is a bare literal that could be replaced by a named constant or typed value.

7. **Non-enforcing test variants** — Tests that provide less coverage than they appear to, beyond name-assertion mismatch. Includes: empty gate tests (test exists but contains zero assertion calls), advisory assertions (test logs or prints a behavioral check result but does not assert on it), and unconditionally skipped tests with behavioral names. Check for test functions whose body contains no assertion calls, or whose output statements produce behavioral check results without corresponding assertions.

8. **Dead infrastructure** — Code constructs, initializes, or declares components (structs, classes, handlers, middleware, configurations) that are never invoked, registered, or wired into the application's runtime path. Unlike dead code (unreachable branches), dead infrastructure is reachable code that is simply never called. Check for constructors or factory calls whose return values are assigned but never passed to any consumer.

9. **Comment-code drift** — Comments describe behavior the code does not implement, or code implements behavior the comments do not describe. Check for function-level or block-level comments whose behavioral claims (e.g., "retries on failure," "validates input") have no corresponding implementation in the code block they annotate.

10. **Zero-value sentinel ambiguity** — Zero, empty string, or nil/null serves as both "unset/missing" and a valid domain value, with no guard distinguishing the two cases. Check for conditional branches that treat a zero-like value as "not provided" when the domain permits that value as a legitimate input.

11. **Context bypass** — Functions use a background or detached context where the caller's context should be forwarded, discarding cancellation signals, deadlines, or trace propagation. Check for context.Background() or equivalent fresh-context constructors in functions that receive a context parameter.

12. **String-based error classification** — Error handling branches on string content (message substrings, format patterns) instead of typed errors, error codes, or sentinel values. Check for string matching operations (Contains, HasPrefix, ==) applied to error messages in conditional expressions.
```

## Files to create/modify

- `assets/fbk-docs/fbk-sdl-workflow/ai-failure-modes.md` (modify)

## Test requirements

Tests from task-01: Test 1 (item count >= 12), Test 2 (bare literal keyword), Test 3 (dead infrastructure keyword), Test 4 (non-enforcing keyword), Test 5 (comment-code drift keyword), Test 6 (sentinel keyword), Test 7 (context bypass keyword), Test 8 (string-based error keyword).

## Acceptance criteria

- AC-36: Item 1 broadened to "Bare literals (numeric and string)" covering string bare literals.
- AC-37: New item 8 covers dead infrastructure.
- AC-38: Item 4 broadened to "Non-enforcing tests"; item 7 covers additional non-enforcing variants.
- AC-39: New item 9 covers comment-code drift.
- AC-40: New item 10 covers zero-value sentinel ambiguity.
- AC-41: New item 11 covers context bypass.
- AC-42: New item 12 covers string-based error classification.
- Total numbered items = 12.

## Model

Haiku

## Wave

Wave 2
