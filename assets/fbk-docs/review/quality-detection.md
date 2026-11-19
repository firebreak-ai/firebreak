Apply these structural detection targets to all code reviews, whether or not the spec contains design constraints.

Before producing a sighting, verify the pattern is avoidable in the codebase's framework and architecture. Framework-idiomatic state access patterns (hooks, dependency injection, engine-provided context) are not violations.

These targets are investigation prompts, not automatic findings. Establish the responsibility or policy involved, the actual coupling, and a concrete maintenance consequence under a plausible change. For example, one accepted policy copied into several error paths requires synchronized edits and invites drift. Cite the affected owners and governing contract; passing behavior tests does not remove that risk. Consequential structural defects can warrant changes before acceptance.

File length, helper count, a single consumer, mixed computation and I/O, or a preferred naming convention alone do not establish a defect. A small orchestrator with composition coverage, an intentional test seam, and framework-required adapters can be sound choices. Consider the cost and contract impact of extraction. Do not demand a new abstraction merely to satisfy a target. Exclude model preferences and cosmetic nitpicks from findings, including suggestions; user-stated preferences recorded as requirements remain authoritative.

## Mixed logic and side effects

Inspect functions that compute results and perform side effects. Identify the computation and effects, then trace whether their coupling makes a concrete behavior hard to verify or a plausible change require error-prone synchronized edits. Separability alone does not qualify; show the affected responsibility and consequence.

## Ambient state access

Inspect functions that access module variables, global state, singletons or closure-captured mutable state. Trace ownership and lifetime: identify conflicting callers, order-dependent behavior, or a concrete maintenance change affected by hidden dependencies. Framework-managed context or global access alone is not a defect.

## Non-importable behaviors

Inspect behaviors embedded inside larger functions for verification or reuse obstacles. Identify which required behavior cannot be meaningfully exercised through the public interface, or which legitimate consumer must duplicate policy. Inability to import a private helper alone is not a defect.

## Multi-responsibility modules

Flag modules that own unrelated responsibilities. Detect this when modifications to unrelated features both require changing the same module.

## Caller re-implementation

Flag code where a caller re-implements logic that exists as an importable function elsewhere, or where multiple callers independently implement the same behavior. This includes test files that manually construct logic instead of calling the production function they claim to test.

Detect duplication of behavioral logic across call sites, not duplication of data or configuration.

## Premature abstraction

Inspect shared abstractions with one concrete consumer. Trace the cost of indirection and a plausible change requiring coordinated edits, then check whether a shared contract, framework boundary, or useful test seam justifies it. A single consumer is a search target, not proof of premature abstraction.

A planned second consumer is relevant evidence, not a prerequisite for a justified abstraction. Judge the current responsibility and concrete cost.

## Composition opacity

Inspect orchestration coverage: trace whether changing call order, a result type, or an error handler could violate the contract while existing tests still pass. Name the wrong behavior and why assertions miss it. End-to-end coverage can be sufficient; test level alone is not a finding.

## Parallel collection coupling

Flag parallel collections (arrays, slices, maps) whose elements correspond by index or key, where reordering one collection silently breaks the correspondence with the other. Detect this when two or more collections are iterated in lockstep by index, or when a value from one collection is used to look up a corresponding entry in another without a structural binding (e.g., a struct or tuple) that enforces the relationship.

## Dead infrastructure

Flag code that constructs, initializes, or declares components (structs, classes, handlers, configurations, middleware) that are never invoked in the application's runtime path. Unlike dead code (unreachable branches), dead infrastructure is reachable code that is simply never called. Detect this when a constructor, factory, or initialization call produces a value that is assigned but never passed to any consumer, or when a registered handler has no route or event that triggers it.

## Semantic drift

Flag code whose documented or named meaning diverges from its actual behavior. This includes function names that describe an action the function does not perform, variable names that describe a property the value does not hold, and module names that describe a responsibility the module does not own. Detect this when reading the name or documentation produces a behavioral expectation that the code contradicts.

## Silent error discard

Inspect discarded errors and trace the caller guarantee, recovery behavior, and any compensating mechanism. Report a lost failure signal or broken obligation with its consequence. Missing logging or a justification comment alone is insufficient.

## Context discard

Flag code that replaces a caller-provided context with a fresh background context, discarding cancellation signals, deadlines, or trace propagation. Detect this when a function that receives a context parameter constructs a new context instead of forwarding the caller's.

## String-based type discrimination

Flag code that branches on string content (error messages, type name strings, format patterns) to determine control flow, instead of using typed errors, enums, constants, or interface checks. Detect this when a conditional expression applies string matching operations (substring check, prefix match, equality comparison) to an error message, type name, or status string to select a code path.

## Dual-path verification

Flag operations that have both a bulk path and an incremental path for the same state. Detect this when the bulk path (initial load, full sync) sets fields that the incremental path (event-driven update, delta sync) ignores, or vice versa — this creates state divergence that manifests only under specific execution sequences.

## Test-production string alignment

Inspect assertions about strings absent literally from the production source. Trace formatting, imported constants, dependency outputs, and the actual assertion path. Establish whether the assertion is unreachable, skipped, or checks the wrong result; absence of a literal alone neither proves a vacuous test nor implies it passes.

## Dead code after field or function removal

Flag guards, conditionals, and logging branches that reference values from a removed field or changed function signature. Detect this when a field removal or parameter change leaves downstream checks on the removed value — the check is reachable code that can never evaluate to true.

## Parallel sentinel definitions

Flag a newly introduced named error, status constant, or sentinel value that duplicates the meaning of an existing sentinel defined in a different module or package. Detect this when a boundary function (an error translator, a status mapper) already branches on the existing sentinel by identity or type, and the new sentinel is not wired into that same boundary.
