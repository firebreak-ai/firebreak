Build the approved plan yourself, in this session. What you learned in the survey carries into the code, so nothing is read twice.

Read `steps.md` and `steps-own-tests.md` beside this file, and `../workflow/refactor.md`.

## Tasks

`testplan.py tasks` lists the tasks: the planned tests grouped by owner. Work through them in order, each to completion before the next, following `steps.md`. A test that contradicts the request goes to the operator.

## Closing tidy-up

When every task is complete, all the production code this change touched, as `git diff` names it, is reviewed against `../workflow/refactor.md`. The particular job is what no single task showed: the same knowledge written in two owners, and new functions that hold more than one decision.

`testplan.py status` says who does it. When it says this session, do the review yourself. When it says a fresh subagent, launch one subagent that has seen none of this work: give it `../workflow/refactor.md`, the diff's file list, the command that runs the suite and the lint command, and have it make the changes. A reader who did not write the code sees its shape as the next maintainer will. `testplan.py finish` refuses while the code has more lint findings than the plan started with.

## Finish

Run `testplan.py finish`. When it lists tests the plan marks for removal, delete exactly those tests and run it again. On success it replaces each `planned` mark with the lasting label `@pytest.mark.acceptance(rule=...)`. Then tell the operator what was built, which tests were added, changed and removed, and what is parked.
