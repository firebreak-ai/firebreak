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

## Silent error discard

Flag code that discards errors without logging or propagating them. Detect this when an error return is assigned to `_` or ignored without a comment justifying the discard.

## Context discard

Flag code that replaces a caller-provided context with a fresh background context, discarding cancellation signals, deadlines, or trace propagation. Detect this when a function that receives a context parameter constructs a new context instead of forwarding the caller's.

## String-based type discrimination

Flag code that branches on string content (error messages, type name strings, format patterns) to determine control flow, instead of using typed errors, enums, constants, or interface checks. Detect this when a conditional expression applies string matching operations (substring check, prefix match, equality comparison) to an error message, type name, or status string to select a code path.

## Dual-path verification

Flag operations that have both a bulk path and an incremental path for the same state. Detect this when the bulk path (initial load, full sync) sets fields that the incremental path (event-driven update, delta sync) ignores, or vice versa — this creates state divergence that manifests only under specific execution sequences.

## Test-production string alignment

Flag test assertions that match on string values absent from the production code being tested. Detect this when a test asserts on an error message, status string, or format pattern that does not appear in the production module's source — these are phantom assertions that pass trivially because the production code never produces the matched string.

## Dead code after field or function removal

Flag guards, conditionals, and logging branches that reference values from a removed field or changed function signature. Detect this when a field removal or parameter change leaves downstream checks on the removed value — the check is reachable code that can never evaluate to true.

## Unbounded data structure growth

Flag long-lived data structures (Maps, Sets, arrays on module-scoped or class-scoped variables) and persistent tables that grow monotonically with no eviction, rotation, TTL, or size cap. Detect this when a collection or table receives insertions (add, set, push, INSERT) without any corresponding deletion, eviction, or size-limiting mechanism in the same module or a scheduled job.

## Migration/DDL idempotency

Flag schema migrations and one-time initialization code that lacks guards against re-execution. Detect this when a migration file contains ALTER TABLE, CREATE TABLE, ADD COLUMN, or equivalent DDL statements without IF NOT EXISTS, IF EXISTS, or equivalent idempotency guards.

## Batch transaction atomicity

Flag loops performing multiple independent write operations where partial completion leaves inconsistent state. Detect this when a loop body contains two or more write calls (database writes, file writes, API calls with side effects) without a surrounding transaction, batch construct, or rollback mechanism.

## Intra-function logical redundancy

Flag conditional checks within a single execution path that are fully subsumed by earlier checks in the same path. Detect this when a guard or branch condition tests a property that was already guaranteed by a preceding check, early return, or assignment in the same function.
