---
title: "Test-Review Technique"
type: concept
sources:
  - firebreak-readme
  - firebreak-sdl-workflow
tags:
  - sdl-pipeline
  - pattern
  - technique-skill
  - testing
  - test-integrity
  - refactored-sdl
created: 2026-05-26
updated: 2026-05-29
---

## Test-Review Technique

The capability to validate that AI-written tests are actually useful tests — catching the failure modes that AI test authors are known to produce (test contains a copy of the implementation, weak assertions, magic-number assertions, internally-contradictory scenarios, mocked dependencies that bypass the behavior under test). A defined [[technique-skill]] invoked at multiple checkpoints: when test tasks are accepted (before [[test-integrity-locking]] is applied) and at final code review.

Promotes the existing [[fbk-test-reviewer]] agent persona into a callable technique with a stable interface. The agent persona is preserved; what changes is that the persona is now one of several technique skills called by phase skills rather than a single-purpose agent.

### Scope: all tests covering the changed module(s)

The review is scoped to the **full set of tests covering the module(s) the slice changes — not only the tests being added or modified.** If a slice changes a module that has ten tests and three need modifying, all ten are reviewed. This ensures every impacted test is still useful and valid, and it is how coverage and catching-power gaps surface — a gap is resolved by adding the needed tests within the slice's declared shape. This scoping is the mechanism behind the contract-preserving and contract-evolving coverage checks; there is no separate "coverage-review" step beyond this existing process applied at the right scope.

### Why this exists as a separate technique

AI-written tests have well-documented failure modes that are different from human-written tests. The same agent producing both code and tests is the worst configuration — the agent's biases propagate consistently to both. A separate reviewing pass, in isolated context, catches these failure modes before the test-lock is applied (locking a bad test is worse than no lock at all).

The technique is invoked at multiple points in the pipeline, not just once. Acceptance-time review catches the obvious failures before the hash-lock is applied. Final code-review re-review catches drift introduced during implementation (e.g., the implementation agent restructured the call site such that the locked test is no longer exercising what it claims to).

### Interaction shape

The technique is invoked with a set of test files plus the spec slice the tests are claiming to cover. The reviewer follows four checks:

1. **Implementation-embedding check.** Does the test contain a copy or near-copy of the implementation being tested? If yes, the test is testing the copy and the actual implementation is unverified. Fail.

2. **Assertion strength check.** Are assertions specific enough to fail when behavior breaks? Does the test assert against expected values rather than tautologies (e.g., `result == result`)? Are magic numbers in assertions named or documented? Is there at most one logical assertion concern per test, or are multiple unrelated concerns smushed together?

3. **Coverage-versus-claim check.** Do the tests actually exercise the behavior the slice claims to cover? Match each test to a behavior in the inventory or a contract clause in the spec. Are there behaviors in the slice with no covering test? Tests with no matching behavior?

4. **Mocking and contradiction check.** Are dependencies mocked in ways that bypass the behavior under test? Are test fixtures internally consistent (e.g., do the inputs and expected outputs align with the same scenario)? Are there mocks that the production code path doesn't actually call?

Each check produces structured findings. The reviewer does not fix the tests — fixes go back to the test-task authoring agent.

### Output shape

A structured markdown file with findings grouped by check:

```markdown
# Test Review: <feature-name> [<checkpoint>]

## Implementation-embedding findings
- <file>:<line range> — <issue>

## Assertion strength findings
- <file>:<line range> — <issue>

## Coverage-versus-claim findings
- <slice or behavior> — <issue>

## Mocking and contradiction findings
- <file>:<line range> — <issue>

## Verdict
- accepted / needs-revision
```

The file lives in the feature directory and is named for the checkpoint (e.g., `test-review-pre-lock.md`, `test-review-final.md`). The gate consuming the artifact reads the verdict line and the findings list.

### Multi-checkpoint invocation

| Checkpoint | When invoked | What it checks | Verdict consumed by |
|-----------|--------------|----------------|---------------------|
| Pre-lock | After test tasks produced, before [[test-integrity-locking]] applied | All four checks above | **Lock-application step.** Verdict gates whether the hashes get recorded into the test-lock manifest. If `needs-revision`, tests bounce back to the test-task agent for rework; locks are not applied. The breakdown gate downstream verifies the lock manifest exists, but the pre-lock verdict is enforced before the breakdown gate runs. |
| Final code review | After implementation complete, before code-review gate | All four checks, plus re-verification that locked tests still exercise claimed behavior given the implementation's final shape | **Code-review gate.** Verdict is one of two semantic anchors (alongside quality-scan top-five). |

The pre-lock checkpoint is the more substantive one — once tests are locked, they can't be modified, so problems caught at pre-lock are cheaper to address. The final checkpoint catches drift (test was correct against the slice as defined, but the slice's implementation drifted such that the test no longer exercises the intended path).

### What it does not do

- **Does not write tests.** The technique reviews tests written by the test-task authoring agent. Fixes go back to that agent.
- **Does not apply hash-locks.** Locking is a separate step performed after the technique's verdict is "accepted." The technique's verdict gates whether locking happens.
- **Does not run programmatic mutation sampling.** Catching power is judged here by reading (the coverage-versus-claim and assertion-strength checks). Programmatic mutation sampling as an empirical proof was considered and deferred — see the decision spine.
- **For contract-preserving slices, the pre-lock review covers the existing tests, not just new ones.** Even when a slice writes no new tests, the pre-lock review runs over all tests covering the module — validating they are useful and have catching power against the contract, locking them, and surfacing any coverage gap (resolved by adding tests, staying contract-preserving). Existing tests are not presumed already-valid. The final-code-review checkpoint still applies — it confirms the locked tests still exercise the claimed contract under the new implementation.

### Out-of-ceremony invocation

`/test-review <test-files> [--spec <spec-path>]` can be invoked on any set of tests. Operators may use this for ad-hoc inspection of legacy tests, third-party tests, or to audit a draft test before formal acceptance.

### Relationship to the existing test-reviewer agent

The existing [[fbk-test-reviewer]] agent persona was a single-purpose agent invoked at fixed points in the breakdown stage. This technique formalizes that persona as a callable capability — same persona, same checks, same outputs, now invokable by multiple phases and out-of-ceremony. The agent file itself remains as the implementation of the technique; the change is conceptual (technique-skill vs single-purpose-agent).

### Related

- [[fbk-test-reviewer]] — the existing agent persona this technique formalizes
- [[test-integrity-locking]] — the hash-lock mechanism applied after the technique accepts
- [[grilling-technique]] · [[fresh-eyes-technique]] · [[quality-scan-technique]] — sibling technique skills
- [[hybrid-gate-pattern]] — test-review output serves as one of two semantic anchors for the code-review gate
- [[fbk-breakdown]] · [[fbk-code-review]] — phase skills that invoke test-review
- [[ai-failure-modes]] — the catalog of failures this technique guards against
- [[firebreak-sdl-workflow]]
