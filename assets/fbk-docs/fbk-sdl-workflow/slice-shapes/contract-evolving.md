Load condition: loaded by the breakdown skill when a slice's test-discipline is `contract-evolving`.

## contract-evolving shape

The slice changes both implementation and contract. Some existing behaviors are no longer guaranteed; new behaviors are introduced.

**Work-unit structure**: produces a retired-tests list (with per-entry rationale), new test tasks for the new behaviors, and an impl task.

**Retired-tests list**: the slice declaration must name every existing test being retired and explain why each one no longer applies to the new contract. A contract-evolving slice without a retirement list is malformed and must not proceed to breakdown.

**New test tasks**: the test-task agent writes tests for behaviors the new contract introduces. These follow new-contract test discipline (red required, hash-locking applies after review).

**Impl task**: the impl-task agent implements the new contract, retiring the listed tests and turning the new locked tests green.

**Hash-locking applies to**: the new tests written in the new test tasks. Retired tests are removed, not locked.
