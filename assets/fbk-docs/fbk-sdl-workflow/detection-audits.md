# Detection Audits

Run these procedural audit passes on the diff before emitting sightings. Enumerate every site each audit covers; do not skip a site because the mistake is not obvious. Cite the audit as `audit-pass` in `detection_source`. When an audit and a pattern in `ai-failure-modes.md` or `security-patterns.md` match the same mechanism, emit one sighting and cite the audit.

## Concurrency audit

Findings from this audit are `behavioral` (see `code-review-guide.md` § Type axis — concurrent execution is normal operation, not a hypothetical future change). Do not classify as `fragile`.

For each mutation, shared-state read, or cached value the diff introduces or touches, enumerate concurrent execution scenarios and check invariants. Specifically look for: read-modify-write without atomicity, check-then-act without lock, missing double-checked locking, lazy init without memory barrier.

## Logic-inversion branch enumeration

For each conditional whose predicate, operator, or variable changed in the diff, write out the old decision table and the new decision table, then check whether any input now produces a different outcome than the code author intended.

The test-integrity audit has moved to `fbk-review-lenses/shared-detection.md` and is referenced there, not duplicated here.

## Cross-function API trace

For every exported or public symbol the diff modifies — removes, renames, changes signature, changes return shape — enumerate callers and verify shape compatibility. When the modified symbol is an interface, enumerate every type that implements it — including test doubles and fakes — and verify each still satisfies the interface. Use Grep and Read beyond the reviewed file to locate callers and implementers.

## Consistency audit

When the diff modifies the use of a helper, shared utility, or repeated pattern at a single site, enumerate every other site in the same module or package that uses the same helper, utility, or pattern. For each unmodified sibling site, check whether the same modification is required for the diff's intent to hold. Emit a sighting for every site where the answer is yes.

When an unmodified sibling site is intentionally asymmetric, the asymmetry must be documented in a spec, acceptance criterion, code comment, or design decision record that identifies which sites are intentionally asymmetric and why. A generic statement that does not identify specific sites does not satisfy this requirement. Undocumented asymmetry is a partial-fix sighting.

Sibling shapes this audit covers:
- Multiple methods of the same type sharing a helper (e.g., the level-specific methods on a logger all calling the same field-conversion helper).
- Multiple implementations of the same interface.
- Multiple call sites invoking the same external utility with similar argument shape.
- Parallel guard or error-handling patterns repeated across functions in the module.
