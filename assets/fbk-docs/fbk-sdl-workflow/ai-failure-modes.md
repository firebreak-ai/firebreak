# AI Failure Mode Checklist

Use this checklist when reviewing code without specs. When specs are available, use `fbk-design-guidelines/quality-detection.md` instead — it covers structural detection targets (re-implementation, duplication, dead code, ambient state, composition opacity) with framework-awareness.

This checklist covers failure modes detectable without a spec as source of truth.

1. **Magic numbers as bare literals** — Spec-defined values (thresholds, sizes, timings) appear as bare numeric literals instead of named constants, especially when the same value appears in multiple files. Check for numeric literals that appear in conditional expressions or assignments in more than one file without a corresponding constant declaration.

2. **Hardcoded coupling where abstraction was specified** — Direct references to concrete implementations where the spec called for abstraction (interface, configuration, dependency injection). Check for instantiation of specific classes or direct file references where the spec or architecture describes an abstraction layer.

3. **Middleware or layers defined but never connected** — Middleware, interceptors, or wrapper layers are implemented but never registered, mounted, or called in the application's initialization path. Check for middleware or layer classes/functions with no references in the application's entry point, router setup, or initialization code.

4. **Test names that contradict their assertions** — The test's `describe`/`it` label claims to verify one behavior, but the assertion checks something different. Check for tests where the string in the test name references a behavior (e.g., "rejects expired tokens") that does not appear in any assertion within the test body.

5. **Surface-level fixes that bypass core mechanisms** — Bug fixes that patch symptoms at the call site instead of correcting the root cause in the responsible module, creating a shadow implementation that diverges from the core. Look for conditional guards or value overrides added at call sites that duplicate logic already present in the function being called.
