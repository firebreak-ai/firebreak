## Process return values explicitly

When a called function returns data, handle every possible result. Use pattern matching, switch statements, or conditional branches that account for each return type. When a function returns typed events, handle each event type — do not silently ignore types the caller does not expect.

When the set of possible return values changes (a new event type is added, an error case is introduced), the caller must be updated. If the caller uses a catch-all or default branch, document what it handles and why unrecognized values are safe to ignore.

## Caller owns side effects

When implementing an orchestration layer, list the side effects for each result type. Each side effect is the caller's responsibility, triggered by the callee's return value. See `fbk-design-guidelines/function-design.md` for the underlying principle.

## Ordering and early exit

When the caller processes multiple results in sequence and ordering matters, add a test that verifies the expected order. If processing result A before result B produces different behavior than B before A, the ordering is a behavioral contract.

When an early exit prevents processing of subsequent results (a fatal condition stops the loop), the early exit is itself a behavior. Identify what gets skipped and confirm the skip is intentional. Test the early exit path explicitly — assert that subsequent side effects do not occur.

## Error propagation

When a called function can fail, the caller decides the error strategy: propagate, recover, transform, or absorb. Make the decision explicit in the implementation — do not let errors pass silently.

When composing multiple fallible functions, handle errors at each call site rather than wrapping the entire sequence in a single try/catch.

## Intermediate state

When the orchestrator accumulates state across sequential calls (running totals, collected results, status flags), declare the intermediate state at the top of the function with descriptive names. Include intermediate state in test assertions — verify not just the final result but the accumulated state after each step.

## Composition as a testable unit

Extract the composition logic into a function that receives its dependencies (the functions it calls, the state it manages) and returns or performs its results.

When the composition cannot be extracted (it is embedded in a framework entry point or lifecycle method), test it through the narrowest available interface. Prefer testing the composition directly over testing it only through e2e tests.
