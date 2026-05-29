---
title: "Slice Shapes"
type: concept
sources:
  - firebreak-sdl-workflow
tags:
  - sdl-pipeline
  - pattern
  - breakdown
  - testing
  - refactored-sdl
created: 2026-05-26
updated: 2026-05-29
---

## Slice Shapes

The four test-discipline modes a slice declaration can take. Each shape implies a different test-task structure, a different relationship to existing tests, and a different test-review behavior at the [[test-review-technique]] checkpoints. Declared per-slice in the spec, read by [[fbk-breakdown]] to drive test-task and impl-task structure.

The four shapes resolve the brownfield-vs-greenfield TDD tension: when the slice is creating a new contract, tests precede code (classical red-green-refactor). When the slice is preserving an existing contract, the existing tests stand and no new tests are written. When the contract is evolving or cross-cutting, the shape adapts.

### The four shapes

#### New-contract

The slice introduces behavior that does not exist in the codebase. The test-task agent writes new tests against the slice's defined contract (signatures, types, behaviors). The tests must fail against an empty implementation (red). A test-review checkpoint reviews the tests by reading before [[test-integrity-locking]] applies to them. The impl-task agent then writes code that turns the tests green without modifying them.

Test-discipline: classical red → green.

#### Contract-preserving

The slice changes implementation while preserving an existing contract. Existing tests cover the contract and must continue to pass; no new tests are written for the contract itself (the contract didn't change). [[test-integrity-locking]] applies to the *existing* tests — they're hashed at slice acceptance and the impl-task agent cannot modify them.

The slice's authored work is the implementation change, followed by verification that the locked tests still pass. The test review happens first, at the test-review checkpoint: the existing [[test-review-technique]] process runs over **all tests covering the module(s) this slice touches** (not just the ones near the change), validating they are useful and have catching power, and producing the test-lock manifest entries. If that review surfaces a coverage gap, the needed tests are added and the slice **stays contract-preserving** — adding tests does not change the contract. No separate "coverage-review unit" is introduced; this is the existing test-review process, scoped to the full impacted test set.

Test-discipline: existing tests are the contract; impl must not break them; no red phase because the tests are already green against the old implementation. The test-review (over the full impacted set) judges by reading whether those tests have catching power; weak coverage or a gap is resolved by adding tests, still contract-preserving.

#### Contract-evolving

The slice changes both implementation *and* contract. Some existing tests may need to be retired (they tested behavior the new contract no longer guarantees); new tests are written for behaviors the new contract introduces. The shape is a hybrid: retired tests are removed from the lock manifest before locking; new tests follow the new-contract discipline.

Test-discipline: explicit retirement list + new tests. The spec's slice declaration must list which existing tests are retired and why. [[test-review-technique]] — run over the full set of tests covering the module — checks both directions: retired tests should not cover behavior still in scope; new tests should cover only behavior actually new; surviving tests remain useful.

#### Cross-cutting

The slice modifies behavior that spans multiple existing modules or seams. Tests live at the seams — integration tests, contract tests between modules, or e2e tests for a flow. New seam tests are written; relevant existing tests are hashed and locked as supporting context. **Cross-cutting is test-only — there is no paired implementation unit**: the implementation already exists across the other slices, and the seam tests must pass against it.

Test-discipline: seam-level tests; emphasis on integration scope. The test-review checkpoint (over the tests covering the touched seams/modules) validates and locks them; no implementation unit is produced for this slice.

### Declaration in the spec

Each slice declaration in the spec includes a `test-discipline:` field with one of the four shape names. The spec gate's mechanical check enforces that every slice has a shape declared. Slices missing a shape declaration fail the gate.

```yaml
slices:
  - name: <slice-name>
    description: <one-line>
    test-discipline: new-contract  # or contract-preserving, contract-evolving, cross-cutting
    contract: <pointer to spec section defining contract>
    retired-tests: []  # contract-evolving only
```

### Progressive disclosure of shape instructions

Each shape's work-unit instructions live in their own leaf. Once a slice is classified into a shape (its `test-discipline:` field), the [[fbk-breakdown]] agent loads only that shape's instruction leaf — it does not carry the rules for the other three shapes into context while building the slice. This keeps the breakdown agent reasoning about one discipline at a time and follows the same reference-leaf-on-demand pattern ([[progressive-disclosure]]) the rest of Firebreak's skills already use.

### Why the four shapes (and not three or five)

**Greenfield-only mode (new-contract) is insufficient.** Most real code changes touch existing code. A discipline that only handles greenfield cases is operationally narrow.

**Greenfield-vs-brownfield is not the right axis.** Both axes mix two concerns: whether the slice creates a contract and whether it preserves an existing one. A brownfield slice that adds new behavior is closer in test-discipline to greenfield than to brownfield-refactor.

**Five shapes would over-fragment.** Each additional shape adds asset-management cost (separate documentation, separate breakdown logic). The four shapes cover the cases that have meaningfully different test discipline; adding a fifth would split one of these into sub-cases that share the same discipline.

### Slice declarations and breakdown bounce-back

When breakdown finds a slice's work units oversized — too large for a less-familiar agent to execute correctly — that's a signal the slice itself is poorly scoped, not that the work units need to be smaller. "Less-familiar agent" here is a check on **spec completeness**, not a model-tier constraint: if the spec is complete enough that a reader without the authoring context can execute it, the spec is well-scoped. The breakdown skill bounces the slice back to the spec for re-decomposition.

The shape declaration affects what "well-scoped" means: a contract-preserving slice can be larger (no new test authoring — the existing tests are reviewed and locked) than a new-contract slice (which carries new-test authoring overhead per behavior).

This bounce-back is the executability check that serves as the breakdown gate's semantic anchor — see [[hybrid-gate-pattern]].

### Related

- [[fbk-spec]] — declares slices with shapes
- [[fbk-breakdown]] — consumes shapes to drive test-task and impl-task structure
- [[test-integrity-locking]] — applies differently per shape
- [[test-review-technique]] — checks per shape (especially contract-evolving's retirement list)
- [[hybrid-gate-pattern]] — breakdown's bounce-back mechanism is the gate's semantic anchor
- [[brownfield-discipline]] · [[codebase-grounded-compilation]] — adjacent concepts for brownfield work
- [[firebreak-sdl-workflow]]
