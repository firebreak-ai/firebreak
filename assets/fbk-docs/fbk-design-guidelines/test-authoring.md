## Production-path exercise

Import the production module and call its exported function with known inputs. Assert on the return value or the observable state change.

When a test file does not import the module it claims to test, or imports it but does not call the function under test, flag it as not exercising the production path.

## Recognizing re-implementation

A test re-implements production logic when the test body contains computation that mirrors what the production function does internally. Signals:

- The test contains a loop, conditional branch, or arithmetic that replicates the production function's algorithm
- The test manually constructs the expected behavior step-by-step instead of calling a function and asserting on its output
- The test's assertions verify the test's own inline logic rather than the production function's behavior
- Comments in the test say "we implement the logic here" or "replicate the production behavior"

## Self-assignment assertions

An assertion that sets a value and immediately asserts it is trivially true. Signals:

- The test assigns `obj.prop = value` then asserts `expect(obj.prop).toBe(value)`
- The assertion verifies the test's own setup, not a production function's output
- A contract comment explains why the test simulates a behavior from another module

When the production path that produces the side effect is not callable from the test, do not simulate it with a self-assignment. Add a contract comment documenting the expected behavior and omit the trivially-true assertion.

## When production code is not importable

When the behavior under test lives inside a function that cannot be imported in the test environment (a framework lifecycle method, a monolithic function mixing multiple concerns, a browser-only code path), flag it as a blocker: "This behavior is not testable through a direct function call. The production code needs to be restructured to expose this behavior as an importable function."

Report the blocker to the orchestrator or user to trigger an escalation that adds an extraction task.

## E2e tests

The production-path exercise principle applies to unit and integration tests, not e2e tests.

## Test isolation

Each test asserts on one behavior.

Receive test dependencies as setup, not as ambient state. Use beforeEach/setUp to create fresh state for each test.

## Assertion specificity

Assert on specific expected values, not truthiness or type alone. `expect(result).toBe(42)` catches regressions that `expect(result).toBeTruthy()` misses — any non-zero value would pass the truthiness check. When the expected value is not a fixed literal (e.g., it depends on input), assert on a derived property that is specific enough to catch behavioral changes: length, key presence, substring, or structural shape.

Weak assertion: `assert result is not None`
Specific assertion: `assert result.status_code == 200 and result.body["user_id"] == expected_id`

## Test name accuracy

Name tests after the behavior they verify, not the implementation mechanism they exercise. A test named "calls the database query function" describes an implementation detail; "returns user by email" describes the behavior. When the implementation changes but the behavior remains the same, implementation-named tests appear broken even though the behavior is intact.

When reviewing test names, check that the name would remain accurate if the implementation were rewritten to produce the same behavior through a different mechanism.
