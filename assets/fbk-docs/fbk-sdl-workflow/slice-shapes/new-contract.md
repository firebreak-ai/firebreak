Load condition: loaded by the breakdown skill when a slice's test-discipline is `new-contract`.

## new-contract shape

The slice introduces behavior that does not exist in the codebase yet.

**Work-unit structure**: produces a test task AND an impl task.

**Test task**: the test-task agent writes new tests against the slice's defined contract and states the exact signatures the tests call, so the impl task can copy them verbatim. The tests must fail before the implementation exists (red phase required). In a typed or compiled language the tests cannot compile until the types and signatures they reference are declared, and a test task touches only test files — so the new tests stay red, failing or held pending, until the paired impl task supplies those declarations and then the behavior. Hash-locking applies to the new tests after they pass review — the impl-task agent may not modify them.

**Impl task**: the impl-task agent writes code that turns the locked tests green without modifying the tests. Classical red → green discipline.

**Hash-locking applies to**: the new tests written in the test task.

**No existing tests are retired**: this shape introduces net-new behavior; no prior tests cover it.
