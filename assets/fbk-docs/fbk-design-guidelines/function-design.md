## Inputs through parameters

Receive everything the function needs as parameters. Do not read from module-level variables, global state, or imported mutable singletons.

When a function needs a single field from a large state object, accept the field, not the object.

## Outputs through return values

Return the result of the computation. Do not mutate input parameters, write to module-level state, or perform side effects as the primary way of communicating results.

When a function must communicate multiple results, return a structured value (an object, a typed event, an array of events).

## Side effects at the boundary

When a function must perform side effects (I/O, audio, rendering, network calls, logging), push them to the caller. The function computes and returns what should happen; the caller makes it happen.

When side effects are inherent to the function's purpose (a function whose job is to write to disk), isolate them: accept the data to write as a parameter, perform the write, return the result. Do not mix the computation of what to write with the act of writing.

When multiple side effects must succeed or fail atomically, keep the transactional execution together. Extract the computation that determines what to do, but keep the coordinated execution in one function.

## Export for testability

Export functions that encapsulate behaviors a test should verify, unless exporting would expand a published API surface with internal implementation details.

When a helper function is small and used only within one module, export it rather than leaving testable logic hidden in application code.

## Function scope

Each function does one thing. If describing what a function does requires "and" — "it validates the input AND processes the order AND sends the confirmation" — it is doing too much. Extract each responsibility into its own function; compose them in the caller.

When reading or modifying existing code, identify functions that handle multiple responsibilities. Propose extraction when the function's multiple concerns can be meaningfully separated. Accept co-location when the concerns are genuinely inseparable at the current level of abstraction, or when separation would add indirection without improving testability.
