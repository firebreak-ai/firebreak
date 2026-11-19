# Test checkpoint review

The runtime sends this file's Decision, Check and Later deliverables sections to the test checkpoint reviewer. Keep each item on one line.

## Decision

Are the authored tests useful: would they detect code that deviates from the accepted design and requirements, and does each test expected to fail fail on an assertion about missing behavior?

## Check

- Read every scoped test, and each production change a test task declared, against the accepted requirements and design.
- For each material requirement, identify a plausible wrong implementation that deviates from the design and check that the tests reject it. A wrong or vacuous test is a blocker: one that asserts nothing material, mirrors the production algorithm, passes on a placeholder's empty result, or mocks away the behavior it claims to check.
- For each plausible bug a test task's verification names, judge whether a test catches it. Where reading is not convincing, use a bounded investigation to write that wrong implementation in a disposable workspace and run the tests against it; a named bug no test catches is a blocker.
- Read the saved output of every check in full; its files are in required_files. test_comparison splits the scoped tests into those changed by test tasks since the writing-tests baseline and those untouched. Confirm from the saved output that each changed test expected to fail fails on an assertion about missing behavior, and that each untouched scoped test passes or carries earlier red forward as described below. A failure to build or load (compile, link, import, or collect) is not meaningful red and is a blocker, and so is a skipped test or a scoped test missing from the saved output.
- When test_comparison lists unchanged_since_accepted_checkpoint, the checkpoint has accepted these tests before, and the saved output of that acceptance, listed in accepted_checkpoint_output, is required reading. Such a test carries that earlier red forward: it may pass now because code built since does the right thing, and correct code is never undone to recreate red. A new or changed test for behavior not yet built needs fresh red in this run's output; a changed test that passes because the code already does the right thing is accepted as preservation when you judge that it protects that behavior. Whole-unit checks carry no expected exit after an earlier acceptance, so judge each test's result from the fresh and carried-forward output.
- When test_comparison lists approved_rework, the operator unlocked those tests and approved, for each, whether its corrected form is expected to fail (behavior not yet built) or pass (behavior already built), and which tests each rework command covers. A command's exit cannot show a reversal among the tests it covers, so confirm from the saved output that each reworked test has its approved outcome; one that does not is a blocker.
- Read each diff in test_comparison's production_diffs, which shows a declared production change against its copy in the writing-tests baseline. A test task's production change may only let the suite build and load against the planned interface: existing code keeps its behavior and new code does nothing meaningful. A diff that adds behavior, or a placeholder that carries the finished behavior, is a blocker. Files listed in test_comparison's verified_implementation_changes were changed by an implementation task that was running when the baseline was recorded and completed with verified checks; they are implementation work, not a test task's change.
- Where a test task expects its checks to pass, judge whether the tests protect the behavior this unit will change, instead of demanding artificial failures.

## Later deliverables

- implementation
- delivery documentation
