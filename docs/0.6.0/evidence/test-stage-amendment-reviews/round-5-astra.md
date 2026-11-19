CLEAN: no blockers or contradictions

1. **Baseline re-recorded on relaunch — resolved.** [Decision 3](../../../../docs/0.6.0/test-stage-amendment-plan.md#L40) limits baseline capture to three lifecycle events and explicitly excludes relaunches, cancellations, and checkpoint rejections. The [Baseline acceptance criterion](../../../../docs/0.6.0/test-stage-amendment-plan.md#L127) exercises all three cases.

2. **Running implementation work refused after unlock — resolved.** [Decision 3](../../../../docs/0.6.0/test-stage-amendment-plan.md#L40) exempts owned-file changes from implementation assignments running at baseline capture once they complete with verified changes. [Step 4](../../../../docs/0.6.0/test-stage-amendment-plan.md#L112) includes the exemption, and [Unlock rework](../../../../docs/0.6.0/test-stage-amendment-plan.md#L131) requires acceptance of that sequence.

3. **No mechanism for scoped rework commands — resolved.** [Decision 11](../../../../docs/0.6.0/test-stage-amendment-plan.md#L93) makes command argument arrays and expectations part of the approved unlock request and substitutes them into the rework run without changing `tasks.json`. Step 4 implements this; Unlock rework tests mixed pass/fail expectations.

No new blocker or contradiction follows from these edits under the targeted-round definitions.

**Fitting notes (non-blocking)**

- [handoff.py:714](../../../../assets/fbk-scripts/fbk/workflow/handoff.py#L714): Capture eligible assignment identities with the baseline and check their verified completion fingerprints when applying the production-change exemption.
- [handoff.py:720](../../../../assets/fbk-scripts/fbk/workflow/handoff.py#L720): Populate the rework run’s `check_expectations` from the approval; task context, runtime execution, and finish comparison must consistently use that substituted set.