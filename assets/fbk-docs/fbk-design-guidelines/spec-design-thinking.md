## Behavior identification

Identify the distinct behaviors the feature introduces or modifies. Name each behavior before describing its implementation.

For each behavior, determine whether it is computation (transforms input to output) or orchestration (calls other behaviors and manages their results). Assign computation and orchestration to separate functions.

## Testability as a design input

Evaluate testability while designing the technical approach, not after. For each behavior: can a test import this function and call it directly with known inputs? If not, the design needs to change — either extract the behavior into a callable function, or explain to the user why extraction is impractical and what the testing tradeoff is.

When a behavior is embedded in an untestable context (a large function, a framework lifecycle method, a browser-only code path), propose extraction. Describe the extraction as a pattern: "pure function that returns typed results; caller handles side effects." Require an importable function for each extractable behavior; integration tests supplement but do not replace direct-call testability.

## Side effect separation

For each behavior in the technical approach, state whether it has side effects. If it does, identify which side effects can be moved to the caller and which are inherent to the behavior. See `fbk-design-guidelines/function-design.md` for the implementation-level principle.

## Composition

After identifying individual behaviors, identify how they interact. Ask:
- Which function calls which?
- What data flows between them — what does each caller receive and what does it do with each possible result?
- Does ordering matter? If behavior A must happen before behavior B, state why.
- What happens when a called function produces an error or an unexpected result?

Describe all composition explicitly — which function calls which, what each caller does with each result, and what ordering or error handling applies. Unspecified composition results in inlining.

When the technical approach threads a value from one component to another (a context, a lifecycle signal, a configuration reference), identify the concrete source of that value at the outermost wiring point. State which component creates or obtains the value and passes it inward.

## Brownfield considerations

When the feature modifies existing code, read the existing code before designing. Identify behaviors that are currently embedded in monolithic functions. Design toward the target structure, not the current structure — the target location of a behavior is where it should live after implementation, which may require extraction from where it currently lives.

When proposing extraction from existing monolithic code, describe the extraction boundary: what moves out, what stays, what interface connects them. The implementing agent needs this boundary to be precise enough to execute without re-inlining the logic.

## Level of detail

Describe design patterns and behavioral contracts. Let the implementing agent determine file paths, function names, and parameter lists unless the user provides them or existing code constrains them. Be precise about *what* each behavior does and *how behaviors relate to each other*.
