Load condition: loaded by the breakdown skill when a slice's test-discipline is `new-contract`.

## new-contract shape

The slice introduces behavior that does not exist in the codebase yet.

**Work-unit structure**: produces a test task AND an impl task.

**Test task**: the test-task agent writes new tests against the slice's defined contract and states the exact signatures the tests call, so the impl task can copy them verbatim. The tests must fail before the implementation exists (red phase required). In a typed or compiled language the tests cannot compile until the types and signatures they reference are declared, and a test task touches only test files — so the new tests stay red, failing or held pending, until the paired impl task supplies those declarations and then the behavior. Hash-locking applies to the new tests after they pass review — the impl-task agent may not modify them.

**Assertion grounding**: for any assertion at a boundary or extreme parameter value, the test-task agent hand-derives and states the expected value in the task rather than asserting a qualitative bound (`!=`, a strict inequality) — a qualitative bound can pass against both a correct and an incorrect implementation.

**Path coverage**: when the contract branches on a condition, the test-task agent writes a case that actually traverses each branch — a case whose expected value happens to match another branch's output does not verify the branch, because deleting it would not fail the test.

**Durable-state assertions**: when the contract specifies both a persisted effect and an emitted event for the same behavior, the test-task agent asserts the persisted state directly, not only the event — an event-only assertion passes even when the write never reaches storage.

**Shipped-behavior equivalence**: when a new test's expected value depends on existing shipped code (not the new contract being introduced), the test-task agent derives that value by reading or executing the shipped code directly — never by mentally simulating it.

**Impl task**: the impl-task agent writes code that turns the locked tests green without modifying the tests. Classical red → green discipline.

**Hash-locking applies to**: the new tests written in the test task.

**No existing tests are retired**: this shape introduces net-new behavior; no prior tests cover it.
