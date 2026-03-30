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

## Parallel collection coupling

Flag parallel collections (arrays, slices, maps) whose elements correspond by index or key, where reordering one collection silently breaks the correspondence with the other. Detect this when two or more collections are iterated in lockstep by index, or when a value from one collection is used to look up a corresponding entry in another without a structural binding (e.g., a struct or tuple) that enforces the relationship.

## Dead infrastructure

Flag code that constructs, initializes, or declares components (structs, classes, handlers, configurations, middleware) that are never invoked in the application's runtime path. Unlike dead code (unreachable branches), dead infrastructure is reachable code that is simply never called. Detect this when a constructor, factory, or initialization call produces a value that is assigned but never passed to any consumer, or when a registered handler has no route or event that triggers it.

## Semantic drift

Flag code whose documented or named meaning diverges from its actual behavior. This includes function names that describe an action the function does not perform, variable names that describe a property the value does not hold, and module names that describe a responsibility the module does not own. Detect this when reading the name or documentation produces a behavioral expectation that the code contradicts.

## Silent error and context discard

Flag code that discards errors without logging or propagating them, or that replaces a caller-provided context with a fresh background context, discarding cancellation signals, deadlines, or trace propagation. Detect this when an error return is assigned to `_` or ignored without a comment justifying the discard, or when a function that receives a context parameter constructs a new context instead of forwarding the caller's.

## String-based type discrimination

Flag code that branches on string content (error messages, type name strings, format patterns) to determine control flow, instead of using typed errors, enums, constants, or interface checks. Detect this when a conditional expression applies string matching operations (substring check, prefix match, equality comparison) to an error message, type name, or status string to select a code path.
