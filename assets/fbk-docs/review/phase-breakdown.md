# Breakdown review

The runtime sends this file's Decision, Check and Later deliverables sections to the breakdown reviewer. Keep each item on one line.

## Decision

Do the tasks divide the accepted specification into test tasks and implementation tasks with sufficient context, coherent ownership, and an order in which the tests are written and reviewed before code?

## Check

- Check each task's observable outcome, owned files, dependencies, and coverage of the accepted specification. Test tasks own the tests and only the production files their interface changes touch; an implementation task owns no scoped test.
- Review every task's definition of done in verification and concrete check_expectations. Implementation checks must pass (exit 0) for that task; focused commands may differ from whole-unit checks while unrelated planned work remains red. Expected red belongs only to test tasks: a check expected to fail declares an exact non-zero exit code or "nonzero", and a check preserving behavior already built declares exit 0. Do not demand whole-suite green for an intermediate task or permit easier replacement checks. Whole-unit checks execute independently at final closure. Firebreak accepts task criteria during breakdown; human approval to enter implementation covers the accepted plan without mandatory per-task approval.
- Check that test tasks cover specified behavior and failure cases, traced to intent as well as specification, and that task instructions preserve accepted requirements.
- Check that each test task's verification names, for each material requirement, a plausible incorrect implementation and shows its input, wrong output and failing assertion; judge from them whether the planned tests would fail it. A named bug the plan does not show a test failing is a blocker. Reject plans that would only confirm placeholders or mirror production algorithms. Do not prescribe incidental implementation details absent from the contract.
- Check ordering and references: test tasks depend only on test tasks, implementation tasks depend on the test tasks whose tests they make pass, and implementation task references include the accepted requirements they implement. Check that the test tasks together plan coherent shared contracts, fixtures, and integration coverage; independent unit tests alone do not establish collaboration behavior.
- Check that a documentation task's check_expectations include at least one command taken from the documented usage and run against the finished program; a substring grep detects an absent topic but never a wrong example.

## Later deliverables

- implementation
- delivery documentation
