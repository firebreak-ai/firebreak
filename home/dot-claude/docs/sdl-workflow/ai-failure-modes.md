# AI Failure Mode Checklist

Use this checklist when reviewing code without specs or when auditing for structural issues.

1. **Tests that re-implement production logic** — Tests validate their own inline copy of the logic rather than exercising the actual system function. Look for test files that duplicate production function bodies or compute expected values using the same algorithm as the code under test.

2. **Copy-paste duplication across modules** — Near-identical code blocks appear in multiple files instead of calling a shared function. Look for functions in different files with similar structure, variable names, and control flow that differ only in minor details (status strings, return values).

3. **Magic numbers as bare literals** — Spec-defined values (thresholds, sizes, timings) appear as bare numeric literals instead of named constants, especially when the same value appears in multiple files. Check for numeric literals that appear in conditional expressions or assignments in more than one file without a corresponding constant declaration.

4. **Dead code from abandoned approaches** — Functions, imports, or variables that are defined but never called, typically left behind when an AI assistant tried a different approach. Look for unused imports, unreferenced function declarations, and commented-out code blocks that span more than 3 lines.

5. **Hardcoded coupling where abstraction was specified** — Direct references to concrete implementations where the spec called for abstraction (interface, configuration, dependency injection). Check for instantiation of specific classes or direct file references where the spec or architecture describes an abstraction layer.

6. **Inconsistent architectural patterns** — The correct pattern is followed in some files but bypassed in others (e.g., some modules use the service layer, others call the database directly). Look for modules that bypass established intermediaries (services, middleware, caches) that peer modules use for the same operation.

7. **Middleware or layers defined but never connected** — Middleware, interceptors, or wrapper layers are implemented but never registered, mounted, or called in the application's initialization path. Check for middleware or layer classes/functions with no references in the application's entry point, router setup, or initialization code.

8. **Trivially-true assertions** — Test assertions with OR-conditions where one branch is always true, or assertions that compare a value to a range so wide it cannot fail. Look for assertion expressions containing logical OR where one operand is a tautology, or range checks where the bounds exceed any possible value.

9. **Test names that contradict their assertions** — The test's `describe`/`it` label claims to verify one behavior, but the assertion checks something different. Check for tests where the string in the test name references a behavior (e.g., "rejects expired tokens") that does not appear in any assertion within the test body.

10. **Surface-level fixes that bypass core mechanisms** — Bug fixes that patch symptoms at the call site instead of correcting the root cause in the responsible module, creating a shadow implementation that diverges from the core. Look for conditional guards or value overrides added at call sites that duplicate logic already present in the function being called.
