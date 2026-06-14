Load condition: loaded by the breakdown skill when a slice's test-discipline is `contract-preserving`.

## contract-preserving shape

The slice changes implementation while an existing contract is preserved. The observable behavior does not change.

**Work-unit structure**: produces an impl task only. No new test task.

**Impl task**: the impl-task agent modifies the implementation. The existing tests already cover the contract and must continue to pass throughout the change.

**Hash-locking applies to**: the existing tests identified in the slice declaration. They are locked before the impl task begins; the impl-task agent may not modify them.

**No red phase**: the locked tests are already green against the old implementation. The impl task keeps them green against the new one.

**No new tests**: the contract is unchanged, so no new tests are written for it.
