NOT CLEAN: 0 blockers, 2 contradictions

1. **Contradiction — Relaunch resets the baseline that must survive relaunch.**

   Decision 1 says relaunching test tasks “returns the unit to writing tests” ([plan:22](../../../../docs/0.6.0/test-stage-amendment-plan.md#L22)). Decision 3 says “Each time the unit enters writing tests … Firebreak records a baseline” and compares against “the latest baseline” ([plan:40](../../../../docs/0.6.0/test-stage-amendment-plan.md#L40)). But Done means requires a relaunched task’s unchanged red test to remain “counted as changed” ([plan:127](../../../../docs/0.6.0/test-stage-amendment-plan.md#L127)).

   **Failure:** A task creates a red test, completes, then relaunches from ready-for-checkpoint. Resetting the baseline now makes that test untouched. With no previous accepted checkpoint, its red result is refused under decision 4. The same reset can hide earlier production changes. Relaunch already replaces the task record and its before-fingerprints at [handoff.py:713](../../../../assets/fbk-scripts/fbk/workflow/handoff.py#L713).

   **Smallest fix:** Specify baseline creation at the three named lifecycle events, explicitly retaining it across task relaunches, cancellations, and checkpoint rejection. Do not trigger baseline creation from every derived-stage transition.

2. **Contradiction — Permitted implementation work during an unlock fails the production-change gate.**

   Decision 5 says a running implementation worker “keeps writing within its ownership while an unlock is outstanding” ([plan:54](../../../../docs/0.6.0/test-stage-amendment-plan.md#L54)). Decision 3 takes the baseline at unlock approval and says “A production change outside every test task’s declared files is refused at the checkpoint” ([plan:40](../../../../docs/0.6.0/test-stage-amendment-plan.md#L40)). Done means confirms that approval “re-records the baseline” ([plan:131](../../../../docs/0.6.0/test-stage-amendment-plan.md#L131)).

   **Failure:** An implementation task already owns `src/service.py`, which no test task owns. After unlock approval captures the baseline, that worker makes an authorized change and finishes. The next checkpoint must refuse that change. Waiting for the worker to finish does not remove the baseline difference. Relevant enforcement sits in [test_preparation.py:250](../../../../assets/fbk-scripts/fbk/workflow/test_preparation.py#L250) and [handoff.py:1006](../../../../assets/fbk-scripts/fbk/workflow/handoff.py#L1006).

   **Smallest fix:** Exempt verified production changes attributable to implementation assignments already running at unlock approval from the test-authoring production restriction. Keep the test baseline fixed and retain enforcement against unrelated changes.

**Fitting notes (non-blocking)**

- [handoff.py:720](../../../../assets/fbk-scripts/fbk/workflow/handoff.py#L720), [handoff.py:888](../../../../assets/fbk-scripts/fbk/workflow/handoff.py#L888): Unlock rework needs scoped command arguments carried into runtime verification, alongside the overridden exit expectations.