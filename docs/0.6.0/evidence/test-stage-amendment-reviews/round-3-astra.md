Eight new major findings; no blockers.

Round-2 dispositions:

- **Astra N1 — resolved:** output artifacts are permitted review sources; the actual snapshot must contain complete output.
- **Astra N2 — resolved:** the stable writing-tests baseline survives relaunch and cancellation.
- **Astra N3 — resolved:** boundary comparisons exempt approved unlocks; existing implementation workers retain ownership.
- **Astra N4 — resolved:** unlock approvals supply preservation expectations, with a successful rework lifecycle check.
- **Astra N5 — resolved:** decision 9 defines all three outcomes and requires each to reach implementation close.
- **Astra N6 — resolved:** requirement-keyed assessments and mechanical omission rejection are specified.
- **Fable 1 — resolved:** mandatory checkpoint acceptance and baseline switching move to step 4.
- **Fable 2 — resolved:** checkpoint revision inputs and the identified review entry points are assigned.
- **Fable 3 — resolved:** approved unlocks are explicitly exempted from lock comparisons.
- **Fable 4 — resolved:** unlock approval clears acceptance while retaining rounds, budget, and generation.
- **Fable 5 — resolved:** captured output is admitted as review evidence and excluded from hygiene scanning.
- **Fable 6 — resolved:** literal-file matching and the positive Go ownership case are explicit.
- **Fable 7 — resolved:** checkpoint placement and initialization are explicit.
- **Fable 8 — resolved:** step 1 includes the lifecycle fixture correction.
- **Fable 9 — resolved:** the transitional allowance is restricted, and checkpoint baseline enforcement is assigned.
- **Fable 10 — resolved:** the version bump accompanies the first record-shape change; refusal names the archive remedy.
- **Fable 11 — resolved:** marker syntax and assessment-omission refusal are defined and tested.
- **Fable 12 — resolved:** captured output is explicitly git-ignored and hook-protected.
- **Fable 13 — partly resolved:** the separate commit and `check-tests` changes are specified, but the surviving lock producer still rejects non-1 exits; see new finding 5.
- **Fable 14 — resolved:** traceability parsing/coverage and task context/review-only behavior are separated into steps 7 and 8.
- **Fable 15 — resolved:** design files without the named section explicitly contribute no items.
- **Fable 16 — resolved:** running implementation workers retain write ownership during unlocks.
- **Fable 17 — partly resolved:** decision 6 adopts regions and shared files, but their integration remains inconsistent; see new findings 1–3.
- **Fable 18 — resolved:** upstream reopening resets checkpoint generation and budget explicitly.

New findings:

1. **Major — Decisions 5–6 / step 6: shared files remain prohibited implementation ownership.**  
   [Plan:52](../../../../docs/0.6.0/test-stage-amendment-plan.md#L52) exempts only region-bearing files from the ownership prohibition; line 53 still prohibits writes to every scoped test path. [Decision 6’s shared fallback](../../../../docs/0.6.0/test-stage-amendment-plan.md#L61) supplies neither exception. A shared production/test file matching the test patterns therefore fails plan validation or cannot receive production edits. Leaving it outside test patterns and regions instead excludes it from decision 9’s definition of a test.

   **Smallest fix:** explicitly classify shared files as scoped tests with permitted production ownership and writes, subject to the promised review of test-code changes. Require a shared-file lifecycle that accepts production edits and rejects test edits; “the diff is shown” is insufficient.

2. **Major — Decision 6 / step 6: the accepted-evidence guard still freezes an entire region-bearing file.**  
   [Plan:104](../../../../docs/0.6.0/test-stage-amendment-plan.md#L104) assigns region fingerprints and after-edit comparison, but omits the representation of checkpoint acceptance. [hooks.py:138](../../../../assets/fbk-scripts/fbk/workflow/hooks.py#L138) rejects every edit to any path in accepted evidence before reaching task or lock checks. Meanwhile, [review_baseline.py:86](../../../../assets/fbk-scripts/fbk/workflow/review_baseline.py#L86) requires accepted file hashes to equal whole-file snapshot hashes. Including `src/foo.rs` freezes its production code; substituting a region hash makes baseline verification fail. A read-only probe confirms the early write refusal.

   **Smallest fix:** separate whole-file snapshot identity from region immutability, and adapt both guards in step 6. Test an above-region production edit **after actual checkpoint acceptance**, followed by successful implementation baseline loading.

3. **Major — Decisions 2 and 6 / step 6: shared-only units have no valid checkpoint freshness rule.**  
   [Plan:29](../../../../docs/0.6.0/test-stage-amendment-plan.md#L29) fingerprints every scoped test file and requires verified locks, while shared files contain production code and receive no mechanical locks. Hashing their whole contents makes ordinary implementation stale the checkpoint; omitting them leaves a shared-only unit with an empty lock map, which [engine.py:358](../../../../assets/fbk-scripts/fbk/workflow/engine.py#L358) rejects. Decision 9’s exception applies only when no scoped tests exist.

   **Smallest fix:** explicitly bind shared-file checkpoint copies without treating current production bytes as checkpoint revision inputs, and permit an accepted shared-only checkpoint with zero mechanical locks. Add a shared-only end-to-end case; the current diff-display check does not cover this.

4. **Major — Decision 3 / step 3: fingerprints cannot supply the promised production diffs.**  
   [Plan:40](../../../../docs/0.6.0/test-stage-amendment-plan.md#L40) records baseline fingerprints, then promises reviewers diffs against that baseline. No step retains the corresponding contents or binds them to a captured tree. Existing [test_preparation.py:80](../../../../assets/fbk-scripts/fbk/workflow/test_preparation.py#L80) stores hashes only; [review_baseline.py:13](../../../../assets/fbk-scripts/fbk/workflow/review_baseline.py#L13) has no first-checkpoint baseline selection. Git HEAD or an earlier breakdown snapshot can differ from the tree when writing tests actually begins. Consequently, the reviewer cannot establish whether a production edit preserved existing behavior.

   **Smallest fix:** retain baseline contents, or reference a verified snapshot matching every baseline fingerprint, when the baseline is established. Require the actual reviewer snapshot to expose the correct before/after diff, including initially dirty source.

5. **Major — Build step 2: nonzero red still fails at breakdown locking.**  
   [Plan:100](../../../../docs/0.6.0/test-stage-amendment-plan.md#L100) updates validation, task finish, and `check-tests`, but omits [engine.lock_tests:325](../../../../assets/fbk-scripts/fbk/workflow/engine.py#L325), which still requires exit 1. Breakdown close calls it at [close.py:287](../../../../assets/fbk-scripts/fbk/workflow/close.py#L287). Thus a task and `check-tests` can accept exit 101, only for breakdown close to fail. The existing [exit-127 rejection test](../../../../assets/fbk-scripts/tests/test_workflow_lifecycle.py#L277) also preserves the obsolete mechanical rule. The refusal was reproduced read-only.

   **Smallest fix:** include the still-live lock producer in step 2’s nonzero conversion. Prove exit 101 through task finish, preparation, and breakdown close before removing that route.

6. **Major — Decision 9 / step 8: dual-reader adjudication discards requirement assessments.**  
   [Plan:106](../../../../docs/0.6.0/test-stage-amendment-plan.md#L106) adds per-requirement assessments without assigning their propagation through the configured second-reader route. That route invokes adjudication at [review.py:1230](../../../../assets/fbk-scripts/fbk/workflow/review.py#L1230). Both the clean-result branch at [council.py:324](../../../../assets/fbk-scripts/fbk/workflow/council.py#L324) and the adjudicated branch at [council.py:440](../../../../assets/fbk-scripts/fbk/workflow/council.py#L440) reconstruct only `summary` and `findings`. Even complete reader assessments disappear, so the new omission gate refuses a valid review. A read-only probe confirms that loss.

   **Smallest fix:** assign assessment propagation and disagreement handling through both adjudication branches. Add dual-reader checks for complete passing assessments, omissions, and a requirement assessed as unmet.

7. **Major — Decision 9 / step 8: the no-tests exemption assumes shell writes cannot change the test inventory.**  
   [Plan:80](../../../../docs/0.6.0/test-stage-amendment-plan.md#L80) declares the outcome immutable because implementation workers cannot create scoped tests, but decision 7 expressly leaves shell commands unscreened. An initially empty test glob can acquire a file through a shell command or verification command. The no-tests outcome skips checkpoint and lock requirements, while the boundary rule compares locked content only. The existing inventory comparison is inside [engine.verify_locks:367](../../../../assets/fbk-scripts/fbk/workflow/engine.py#L367), precisely the route being skipped.

   **Smallest fix:** enforce that the accepted empty test inventory remains empty at task boundaries and implementation close, including after checks. Add a shell-created scoped-test refusal case for the no-tests outcome.

8. **Major — Decision 7 / steps 5–6: region restoration can discard valid production work.**  
   [Step 5](../../../../docs/0.6.0/test-stage-amendment-plan.md#L103) implements restoration while locks still cover whole files. [Step 6](../../../../docs/0.6.0/test-stage-amendment-plan.md#L104) adds regions but does not adapt restoration; decision 7 saves complete region-bearing files. After a valid production edit above the marker and shell corruption inside the locked region, replaying that saved file restores the tests **and overwrites the valid production edit**. The done-means checks never combine restoration with production changes.

   **Smallest fix:** make region restoration replace only the locked region while preserving the current production prefix. Add a check proving both exact region restoration and preservation of production edits.