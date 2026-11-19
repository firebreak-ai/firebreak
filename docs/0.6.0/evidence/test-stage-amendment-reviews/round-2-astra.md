Round-1 dispositions:

- **Astra 1 — partly resolved:** additive ordering preserves the old route, but step 2 requires checkpoint acceptance while lifecycle-fixture conversion waits until step 3.
- **Astra 2 — resolved:** step 3 removes standalone locking; implementation close requires a current accepted checkpoint.
- **Astra 3 — resolved:** step 3 explicitly preserves plan validation and makes breakdown review inputs and obligations plan-only.
- **Astra 4 — resolved:** readiness covers every declared test task, requires current completion, and permits relaunch for rework.
- **Astra 5 — resolved:** step 2 explicitly includes checkpoint recovery, budgets, pending guards, findings approval, dispositions, and reporting.
- **Astra 6 — resolved:** Decision 3 explicitly changes ownership validation and source-baseline checks.
- **Astra 7 — partly resolved:** nonzero semantics and exit-101 coverage are specified; explicit compile/link/load-failure rejection tests remain absent.
- **Astra 8 — resolved:** complete durable streams and oversized-output checks replace truncated saved evidence.
- **Astra 9 — partly resolved:** running all declared commands is specified, but that does not establish execution of every scoped test; missing/skipped-test rejection remains untested.
- **Astra 10 — resolved:** ownership-pattern intersection and refusal of writes to new scoped tests are explicit.
- **Astra 11 — resolved:** upstream reopen clears locks and checkpoint acceptance; implementation-only reopen retains them.
- **Astra 12 — partly resolved:** historical lookup and review baseline move to the checkpoint, but checkpoint-specific revision/reuse inputs and their invalidation checks remain unspecified.
- **Astra 13 — resolved:** continuation correction, checkpoint reporting, and retrospective integration are assigned.
- **Astra 14 — resolved:** named item sections, retained anchors, upstream target kinds, section extraction, and coverage checks are specified.
- **Astra 15 — resolved:** both task boundaries, post-check comparison, durable attribution, restoration, cleanup, and reopen checks are specified.
- **Astra 16 — partly resolved:** version refusal and installed-command coverage are added, but the version boundary arrives in step 3 after checkpoint state is introduced in step 2.
- **Fable I-1 — partly resolved:** the additive split helps, but step 1 rejects the shared fixture’s implementation ownership of `tests/check.py`; fixture rewriting is deferred to step 3.
- **Fable I-2 — resolved:** step 1 explicitly removes the implementation-entry lock prerequisite.
- **Fable I-3 — resolved:** upstream reopen explicitly clears locks and checkpoint acceptance.
- **Fable I-4 — resolved:** checkpoint integration sites are explicitly assigned without adding a workflow phase.
- **Fable I-5 — resolved:** the checkpoint uses the fixed reviewer; review-plan selection was removed.
- **Fable I-6 — resolved:** task expectations, completion semantics, reviewer guidance, guides, and exit-101 coverage are addressed.
- **Fable I-7 — partly resolved:** durable files and required reading are specified, but the existing snapshot source policy rejects those files; see N1.
- **Fable I-8 — resolved:** item inventories, Markdown links, design-file enumeration, and parent-item eligibility are specified.
- **Fable I-9 — resolved:** section-only context, the retained packet cap, and explicit oversize refusal are settled.
- **Fable I-10 — partly resolved:** the unlock route is defined, but lock enforcement and accepted task expectations still obstruct it; see N3–N4.
- **Fable I-11 — resolved:** step 1 removes the false completion default.
- **Fable I-12 — resolved:** breakdown entry continues superseding task runs, and `stubs` is explicitly retired.
- **Fable I-13 — resolved:** saved copies must be git-ignored and hook-protected.
- **Fable I-14 — resolved:** the checkpoint snapshot becomes implementation’s baseline test contract.
- **Fable I-15 — partly resolved:** schema refusal is specified one commit later than the new state structure.
- **Fable I-16 — resolved:** standalone locking commands are removed and checkpoint acceptance becomes a close prerequisite.
- **Fable I-17 — resolved:** checkpoint suggestion dispositions are explicitly included in step 2.

New findings:

1. **N1 — major — Build order, step 2: the new red-output artifacts cannot enter the reviewer snapshot.**  
   Plan: [test-stage-amendment-plan.md:77](../../../../docs/0.6.0/test-stage-amendment-plan.md#L77). Code: [review_context.py:261](../../../../assets/fbk-scripts/fbk/workflow/review_context.py#L261), [review_context.py:283](../../../../assets/fbk-scripts/fbk/workflow/review_context.py#L283).

   Adding `.fbk/<unit>/checkpoint-output/stdout.txt` to required reading currently raises `Workflow history cannot be a review source`. The allowlist admits unit documents and design/decision files, not execution artifacts. This rejection was reproduced read-only. The proposed storage fix therefore fails before review starts.

   **Smallest fix:** assign step 2 a narrow, hash-verified exception for checkpoint execution artifacts in snapshot creation and baseline loading. Add a done-means check that the actual reviewer snapshot contains the complete streams.

2. **N2 — major — Build order, step 2: deriving changed tests from current task runs loses changes on relaunch.**  
   Plan: [test-stage-amendment-plan.md:44](../../../../docs/0.6.0/test-stage-amendment-plan.md#L44), [test-stage-amendment-plan.md:77](../../../../docs/0.6.0/test-stage-amendment-plan.md#L77). Code: [handoff.py:713](../../../../assets/fbk-scripts/fbk/workflow/handoff.py#L713), [handoff.py:733](../../../../assets/fbk-scripts/fbk/workflow/handoff.py#L733).

   Relaunch overwrites `task_runs[task_id]` and captures a new `before` fingerprint. Suppose a task creates a valid red test, the checkpoint rejects another aspect of its work, and the task is relaunched without changing that test. Its latest before/after hashes now match. The revised inventory classifies the newly authored red test as untouched and consequently requires it to pass. Cancellation followed by relaunch has the same problem. The task-start event does not retain the overwritten `before` map.

   **Smallest fix:** derive the inventory against a stable pre-test baseline, or retain cumulative assignment provenance through checkpoint acceptance. Test rejection/relaunch and cancellation/relaunch with an unchanged newly authored test.

3. **N3 — major — Build order, steps 3–4: unconditional lock comparison prevents authorized unlock rework.**  
   Plan: [test-stage-amendment-plan.md:47](../../../../docs/0.6.0/test-stage-amendment-plan.md#L47), [test-stage-amendment-plan.md:67](../../../../docs/0.6.0/test-stage-amendment-plan.md#L67), [test-stage-amendment-plan.md:79](../../../../docs/0.6.0/test-stage-amendment-plan.md#L79). Code: [engine.py:175](../../../../assets/fbk-scripts/fbk/workflow/engine.py#L175), [engine.py:357](../../../../assets/fbk-scripts/fbk/workflow/engine.py#L357), [hooks.py:174](../../../../assets/fbk-scripts/fbk/workflow/hooks.py#L174).

   Unlock approval leaves the original hash in `locks` and adds the path to `unlocks`. Reusing `verify_locks` at task start immediately refuses the authorized rework. Even a new comparison that merely checks every locked hash refuses the test task’s finish after its approved edit. The existing production-write hook also calls `verify_locks`, obstructing running implementation tasks that Decision 10 permits to finish.

   **Smallest fix:** distinguish boundary integrity checks from close readiness: exempt exactly the approved unlocked paths during rework, enforce every other lock, and permit existing implementation assignments to finish. Add an unlock → test rework → checkpoint → relock lifecycle check.

4. **N4 — major — Build order, step 3: preservation acceptance is unreachable through an unchanged red task expectation.**  
   Plan: [test-stage-amendment-plan.md:66](../../../../docs/0.6.0/test-stage-amendment-plan.md#L66), [test-stage-amendment-plan.md:78](../../../../docs/0.6.0/test-stage-amendment-plan.md#L78). Code: [handoff.py:905](../../../../assets/fbk-scripts/fbk/workflow/handoff.py#L905); existing workaround: test_preparation_lineage.py:49 (`assets/fbk-scripts/tests/test_preparation_lineage.py:49`, since removed).

   A test task originally completes against stubs with a nonzero expectation. Later, an approved unlock corrects a wrong assertion while the implementation already satisfies the requirement. The corrected check exits zero, so task finish records `needs-attention`; checkpoint readiness requires a completed run. The checkpoint never gets to apply the promised preservation judgment. Existing lineage tests avoid this by editing expectations during breakdown reopen, which the named-unlock route does not do.

   **Smallest fix:** carry the settled preservation exception through rework task completion, retaining actual results for checkpoint judgment. Add a check where an approved correction passes against already-correct code and reaches checkpoint acceptance without undoing that code.

5. **N5 — major — Build order, step 5: the review-only exception still requires a test task.**  
   Plan: [test-stage-amendment-plan.md:60](../../../../docs/0.6.0/test-stage-amendment-plan.md#L60), [test-stage-amendment-plan.md:80](../../../../docs/0.6.0/test-stage-amendment-plan.md#L80). Code: [test_preparation.py:233](../../../../assets/fbk-scripts/fbk/workflow/test_preparation.py#L233), [evidence.py:248](../../../../assets/fbk-scripts/fbk/workflow/evidence.py#L248), [engine.py:317](../../../../assets/fbk-scripts/fbk/workflow/engine.py#L317).

   A unit whose requirements are all legitimately checked by review needs only implementation tasks under Decision 8. The retained plan validator nevertheless requires a test-stage task. Empty scoped-test cases also encounter mandatory test/check declarations and the lock producer’s refusal of an empty test set. Step 5 changes coverage but assigns no corresponding changes to these prerequisites; the done-means list omits this case.

   **Smallest fix:** explicitly adapt the prerequisites for an all-review requirement inventory, including checkpoint treatment of zero test tasks and an empty test set. Prove the resulting lifecycle without inventing a meaningless test responsibility.

6. **N6 — major — Build order, step 5: omission of a review-only requirement has no acceptance gate.**  
   Plan: [test-stage-amendment-plan.md:60](../../../../docs/0.6.0/test-stage-amendment-plan.md#L60), [test-stage-amendment-plan.md:80](../../../../docs/0.6.0/test-stage-amendment-plan.md#L80). Code: [review.py:28](../../../../assets/fbk-scripts/fbk/workflow/review.py#L28), [review.py:60](../../../../assets/fbk-scripts/fbk/workflow/review.py#L60), [close.py:230](../../../../assets/fbk-scripts/fbk/workflow/close.py#L230).

   Decision 8 makes omission of any review-only requirement a blocker. Step 5 names coverage checks at design, spec, and breakdown close, but no implementation-result completeness check. The existing validator accepts `{"summary":"Accepted.","findings":[]}` without assessing a single requirement; close accepts it if other prerequisites pass. Prompt guidance alone cannot detect an omitted assessment, and successful assessments cannot be represented as defect findings.

   **Smallest fix:** specify an implementation-review assessment list keyed by requirement anchors and validate it against the review-only inventory before acceptance. Add done-means cases rejecting an otherwise clean review that omits an item and accepting a complete assessment.