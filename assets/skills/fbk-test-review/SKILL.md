---
description: >-
  Review a test set for integrity at a pipeline checkpoint or standalone.
  Use when validating that AI-written tests actually catch the behavior they
  claim to cover, at either the pre-lock gate (before hash-locking) or the
  final gate (after implementation, invoked by code-review).
argument-hint: "[feature-name or test-path]"
---

Route the `test-reviewer` agent in either **pre-lock** or **final** mode. The caller or operator selects the mode based on where in the pipeline the review occurs.

## Mode routing

**Pre-lock mode** — invoked by the breakdown agent before applying hash locks to test files. Reviews test tasks and test implementations to verify they are ready to lock. Only an `accepted` pre-lock verdict triggers lock application downstream.

**Final mode** — invoked by the code-review gate after implementation is complete. Reviews the full set of tests covering the changed module, including pre-existing locked tests that the contract-preserving slice keeps. Only an `accepted` final verdict allows the code-review gate to close.

When invoked standalone (outside the pipeline), the caller specifies the mode explicitly. If mode is not specified, ask before proceeding.

## What the agent reviews

**Pre-lock:** test task files and test implementations for the current slice. Checks that implementations faithfully translate tasks, trace to ACs, pass Tier 1 mechanical checks, and are structured to fail before implementation (red before implementation).

**Final:** the full set of tests covering the changed module — both tests written in this slice and pre-existing tests the manifest locks. Checks for weakened assertions, trivially-passing tests, unauthorized test modification, drift from the locked manifest, and (for contract-evolving slices) that the retired-tests list is justified and the surviving tests protect the surviving contract.

## Artifact

Both modes write an artifact to `ai-docs/<feature>/test-review-<checkpoint>.md`.

- The pre-lock pass writes `ai-docs/<feature>/test-review-pre-lock.md` (or the checkpoint label the breakdown supplies).
- The final pass writes `ai-docs/<feature>/test-review-final.md` — this is the canonical final-checkpoint artifact name the code-review gate reads (task-34 reads `test-review-final.md`).

The artifact's last line is the verdict, which is exactly one of:

```
accepted | needs-revision
```

A `needs-revision` verdict at either checkpoint blocks the downstream gate. The verdict is load-bearing — downstream gates read the artifact file, not the agent's conversation output.
