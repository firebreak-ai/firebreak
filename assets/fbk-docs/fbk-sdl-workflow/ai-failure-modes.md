# AI Failure Mode Checklist

Apply these detection targets to all code reviews.

1. **Bare literals (numeric and string)** — Spec-defined values (thresholds, sizes, timings, discriminator strings) appear as bare literals instead of named constants. Check for numeric literals in conditional expressions or assignments that appear in multiple files without a corresponding constant declaration. Check for string property keys or discriminator values used in conditional logic without a named constant — bare string literals used for type discrimination are as fragile as bare numeric literals.

2. **Hardcoded coupling where abstraction was specified** — Direct references to concrete implementations where the spec called for abstraction (interface, configuration, dependency injection). Check for instantiation of specific classes or direct file references where the spec or architecture describes an abstraction layer.

3. **Middleware or layers defined but never connected** — Middleware, interceptors, or wrapper layers are implemented but never registered, mounted, or called in the application's initialization path. Check for middleware or layer classes/functions with no references in the application's entry point, router setup, or initialization code.

4. **Non-enforcing tests (name-assertion mismatch)** — The test's describe/it label claims to verify one behavior, but the assertion checks something different. Check for tests where the string in the test name references a behavior (e.g., "rejects expired tokens") that does not appear in any assertion within the test body.

5. **Surface-level fixes that bypass core mechanisms** — Bug fixes that patch symptoms at the call site instead of correcting the root cause in the responsible module, creating a shadow implementation that diverges from the core. Look for conditional guards or value overrides added at call sites that duplicate logic already present in the function being called.

6. **Non-enforcing test variants** — Tests that provide less coverage than they appear to, beyond name-assertion mismatch. Includes: empty gate tests (test exists but contains zero assertion calls), advisory assertions (test logs or prints a behavioral check result but does not assert on it), and unconditionally skipped tests with behavioral names. Check for test functions whose body contains no assertion calls, or whose output statements produce behavioral check results without corresponding assertions.

7. **Dead infrastructure** — Code constructs, initializes, or declares components never invoked in the application's runtime path. Check for constructors or factory calls whose return values are assigned but never passed to any consumer (full heuristic in quality-detection.md).

8. **Comment-code drift** — Comments describe behavior the code does not implement, or code implements behavior the comments do not describe. Check for function-level or block-level comments whose behavioral claims (e.g., "retries on failure," "validates input") have no corresponding implementation in the code block they annotate.

9. **Zero-value sentinel ambiguity** — Zero, empty string, or nil/null serves as both "unset/missing" and a valid domain value, with no guard distinguishing the two cases. Check for conditional branches that treat a zero-like value as "not provided" when the domain permits that value as a legitimate input.

10. **Context bypass** — Functions replace a caller-provided context with a fresh background context, discarding cancellation signals, deadlines, or trace propagation. Check for background-context constructors in functions that receive a context parameter (full heuristic in quality-detection.md).

11. **String-based error classification** — Error handling branches on string content instead of typed errors, error codes, or sentinel values. Check for string matching operations applied to error messages or type discriminator strings in conditional expressions (full heuristic in quality-detection.md).
12. **Semantically incoherent test fixtures** — Test input data satisfies the type system but violates domain constraints, producing false-passing scenarios. Check for test fixtures where related fields should be consistent by domain rules but are set independently with mismatched values.

13. **Mock permissiveness masking constraints** — Tests pass because mocks do not validate constraints the production code relies on. Check for mocks that accept any input where the production dependency enforces domain rules (e.g., type discriminators, referential integrity, value ranges).

14. **Dead conditional guards** — Guards or early-return conditions whose triggering state can no longer be reached because upstream code was changed or removed. Unlike dead infrastructure (item 7), the guard itself is reachable code inside an active function — it can never evaluate to true. When reviewing code after a field or parameter removal, check for sentinel checks on values that are always assigned before the call site, or on fields removed from the type they guarded.
