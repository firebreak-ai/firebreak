Load condition: loaded by the breakdown skill when a slice's test-discipline is `new-contract`.

## new-contract shape

The slice introduces behavior that does not exist in the codebase yet.

**Work-unit structure**: produces a test task AND an impl task.

**Test task**: the test-task agent writes new tests against the slice's defined contract. The tests must fail against an empty implementation (red phase required). Hash-locking applies to the new tests after they pass review — the impl-task agent may not modify them.

**Impl task**: the impl-task agent writes code that turns the locked tests green without modifying the tests. Classical red → green discipline.

**Hash-locking applies to**: the new tests written in the test task.

**No existing tests are retired**: this shape introduces net-new behavior; no prior tests cover it.
