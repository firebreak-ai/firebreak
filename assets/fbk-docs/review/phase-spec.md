# Spec review

The runtime sends this file's Decision, Check and Later deliverables sections to the spec reviewer. Keep each item on one line.

## Decision

Does the specification define observable contracts and a verification strategy faithful to accepted intent and design?

## Check

- Check observable acceptance examples, boundaries, failure cases, shared contracts, scope, and the proposed verification strategy.
- Check that shared-policy examples would detect consumers drifting and that the specification preserves accepted responsibility boundaries. Correct a specification departure locally; reopen design only when the correction changes an accepted architectural decision or contract.
- Revisit accepted architecture only with evidence it cannot satisfy requirements.
- Check every scope.json creates entry against the design and the existing code: new paths follow the design's module layout, existing files, modules, and functions are extended where they fit, and a new one appears only where the design calls for a new responsibility. A parallel file holding an existing file's responsibility, or an entry contradicting the design's layout, is a blocker.
- Check where the unit's tests live: whole test files matching scope.json tests, or end-of-file test regions declared in test_regions whose start expression finds the line where the tests begin. Tests interleaved with code throughout a file (for example Zig test blocks or D unittest blocks) are unsupported; a spec relying on that layout is a blocker until its tests move to end-of-file regions or separate test files.

## Later deliverables

- task breakdown
- implementation
- executable tests
- delivery documentation
