---
description: >-
  Review a test set for integrity at a pipeline checkpoint or standalone.
  Use when validating that AI-written tests actually catch the behavior they
  claim to cover, at either the pre-lock gate (before hash-locking) or the
  final gate (after implementation, invoked by code-review).
argument-hint: "[feature-name or test-path]"
---

Route the `test-reviewer` agent in **spec**, **pre-lock**, or **final** mode. The caller or operator selects the mode based on where in the pipeline the review occurs.

## Mode routing

**Spec checkpoint** — invoked during spec review, after the council is clean and the review document is stable. Reviews the spec's planned testing strategy against its own requirements, criteria, and integration seams: for each requirement, does the planned test actually prove the behavior? Only an `accepted` spec verdict lets the spec gate pass.

**Pre-lock mode** — invoked by the breakdown agent before applying hash locks to test files. Reviews test tasks and test implementations to verify they are ready to lock. Only an `accepted` pre-lock verdict triggers lock application downstream.

**Final mode** — invoked by the code-review gate after implementation is complete. Reviews the full set of tests covering the changed module, including pre-existing locked tests that the contract-preserving slice keeps. Only an `accepted` final verdict allows the code-review gate to close.

When invoked standalone (outside the pipeline), the caller specifies the mode explicitly. If mode is not specified, ask before proceeding.

## What the agent reviews

**Spec checkpoint:** the stabilized spec — its requirements, acceptance criteria, and declared integration seams. The agent walks each requirement and asks whether its planned test would actually prove the behavior, and whether each declared seam has end-to-end coverage planned. It works from the spec alone, with no council memory or findings.

**Pre-lock:** test task files and test implementations for the current slice. Checks that implementations faithfully translate tasks, trace to ACs, pass Tier 1 mechanical checks, and are structured to fail before implementation (red before implementation).

**Final:** the full set of tests covering the changed module — both tests written in this slice and pre-existing tests the manifest locks. Checks for weakened assertions, trivially-passing tests, unauthorized test modification, drift from the locked manifest, and (for contract-evolving slices) that the retired-tests list is justified and the surviving tests protect the surviving contract.

## Artifact

Every mode writes an artifact to `ai-docs/<feature>/test-review-<checkpoint>.md`.

- The spec checkpoint writes `ai-docs/<feature>/test-review-spec.md` — the canonical spec-checkpoint artifact name the spec/review gate reads.
- The pre-lock pass writes `ai-docs/<feature>/test-review-pre-lock.md` (or the checkpoint label the breakdown supplies).
- The final pass writes `ai-docs/<feature>/test-review-final.md` — the canonical final-checkpoint artifact name the code-review gate reads.

The artifact carries a verdict line, exactly one of:

```
accepted | needs-revision
```

A `needs-revision` verdict at any checkpoint blocks the downstream gate. The verdict is load-bearing — downstream gates read the artifact file, not the agent's conversation output. Both the spec gate and the code-review gate locate the artifact in the feature folder and read its `Verdict:` line, so the verdict must be emitted as a `Verdict:` line for the gate to find it.
