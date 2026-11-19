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

For an unmodified sibling, trace whether it shares the affected obligation, trigger, and broken mechanism. Different contracts or existing safeguards can justify different code. Read any claimed exception in its governing source, but do not infer a defect merely from undocumented asymmetry. Emit a partial-fix sighting when the sibling still violates its actual obligation, with its caller impact.

At remediation, reuse this enumeration: record each relevant occurrence as fixed, already safe, or outside the accepted scope with a specific reason. An explicit compatibility exception can justify leaving a sibling unchanged; mere resemblance is not authority to change its contract. Inspect affected related paths even when they are outside the diff. When verifying a material fix, read `remediation-verification.md` for independent behavioral and regression evidence.

Sibling shapes this audit covers:
- Multiple methods of the same type sharing a helper (e.g., the level-specific methods on a logger all calling the same field-conversion helper).
- Multiple implementations of the same interface.
- Multiple call sites invoking the same external utility with similar argument shape.
- Parallel guard or error-handling patterns repeated across functions in the module.

## Affected durable documentation

Discover existing durable docs affected by the changed behavior, interfaces,
dependencies or layout, including documents omitted from the declared change set.
Search references by module, public names, paths and feature scope; inspect relevant
decisions, contracts, architecture/layout docs, specs and release documentation.
Compare their operative claims with delivered behavior and authorized changes.
Distinguish current obligations from superseded decisions and historical release
entries. Apply the project's release timing rules when checking changelog duties.
Report a concrete stale claim or unmet documentation obligation with its consequence;
an absent document or a preferred wording alone is not a defect. Carry this comparison
through fixes and account for inspected sources and unresolved evidence in the existing
review result. This duty belongs to the current review and requires no extra pass.
