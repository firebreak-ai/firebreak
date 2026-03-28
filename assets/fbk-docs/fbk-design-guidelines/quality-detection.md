Apply these structural detection targets to all code reviews, whether or not the spec contains design constraints.

Before producing a sighting, verify the pattern is avoidable in the codebase's framework and architecture. Framework-idiomatic state access patterns (hooks, dependency injection, engine-provided context) are not violations.

## Mixed logic and side effects

Flag functions that compute a result AND perform side effects. Identify which parts are computation and which are side effects. If they can be separated (computation returns data, caller performs side effects), produce a sighting.

## Ambient state access

Flag functions that read from or write to module-level variables, global state, singletons, or closure-captured mutable state instead of receiving values as parameters. Detect this when a function accesses state it did not receive as input.

## Non-importable behaviors

Flag behaviors embedded inside a larger function that cannot be imported and called independently. Detect this when a test cannot import and call a specific behavior without importing the entire enclosing function and simulating its full execution context.

## Multi-responsibility modules

Flag modules that own unrelated responsibilities. Detect this when modifications to unrelated features both require changing the same module.

## Caller re-implementation

Flag code where a caller re-implements logic that exists as an importable function elsewhere, or where multiple callers independently implement the same behavior. This includes test files that manually construct logic instead of calling the production function they claim to test.

Detect duplication of behavioral logic across call sites, not duplication of data or configuration.

## Composition opacity

Flag orchestration code where no test verifies the composition as a unit. Detect this when changing the order of calls, adding a new result type, or removing an error handler would not be caught by any test. If the composition is only exercised through end-to-end tests or not tested at all, produce a sighting.
