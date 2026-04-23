# Detection Audits

Run these procedural audit passes on the diff before emitting sightings. Enumerate every site each audit covers; do not skip a site because the mistake is not obvious. Cite the audit as `audit-pass` in `detection_source`. When an audit and a pattern in `ai-failure-modes.md` or `security-patterns.md` match the same mechanism, emit one sighting and cite the audit.

## Concurrency audit

Findings from this audit are `behavioral` (see `code-review-guide.md` § Type axis — concurrent execution is normal operation, not a hypothetical future change). Do not classify as `fragile`.

For each mutation, shared-state read, or cached value the diff introduces or touches, enumerate concurrent execution scenarios and check invariants. Specifically look for: read-modify-write without atomicity, check-then-act without lock, missing double-checked locking, lazy init without memory barrier.

## Logic-inversion branch enumeration

For each conditional whose predicate, operator, or variable changed in the diff, write out the old decision table and the new decision table, then check whether any input now produces a different outcome than the code author intended.

## Test-integrity audit

For each modified test: (a) does the test name describe what the test actually asserts? (b) do any mocks, monkeypatches, or fixtures invalidate the assertion (e.g., `time.sleep` patched away)? (c) is the assertion strict enough to catch the behavior it claims to check? (d) are shared mutable defaults avoided?

## Cross-function API trace

For every exported or public symbol the diff modifies — removes, renames, changes signature, changes return shape — enumerate callers and verify shape compatibility. Use Grep and Read beyond the reviewed file to locate callers.
