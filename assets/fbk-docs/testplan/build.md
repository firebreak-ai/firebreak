Build the approved plan. The lead coordinates: each piece of work below runs in its own subagent, one at a time, and the lead's part is launching them, reading what they return, and running `testplan.py`.

`testplan.py status` shows who writes the test bodies. When it is the implementer, start at "Tasks".

## Test bodies

Launch one subagent to write the bodies. Give it `test-author.md` beside this file, the path `.fbk/testplan/request.md`, and the output of `testplan.py plan`.

Then launch a fresh subagent to review them, with `test-review.md` beside this file and the same two inputs. There is one review pass: have the author correct what the reviewer reports, then run `testplan.py lock`.

A report that the plan itself is wrong, from the author or the reviewer, goes to the operator, since the plan is what the operator approved. A changed plan needs `testplan.py plan` and `approve` again.

## Tasks

`testplan.py tasks` lists the tasks: the planned tests grouped by owner. Run them in order, each to completion before the next starts, so each implementer sees the code the last one left.

Give each implementer the output of `testplan.py brief <task>`, `steps.md` beside this file, and `../workflow/refactor.md`. Ask it to return what it built, the tool's last message, and anything it noticed outside its task. When the implementer writes the test bodies, also give it `steps-own-tests.md` beside this file.

An implementer that reports a test contradicting the request has stopped on purpose. Take the report to the operator.

## Closing tidy-up

When every task is complete, launch one subagent with `../workflow/refactor.md` to review all the production code this change touched, as `git diff` names it. Its particular job is what no single task could see: the same knowledge written in two owners. Tell it the lint command when the plan has one: `testplan.py finish` refuses while the code has more lint findings than the plan started with.

## Finish

Run `testplan.py finish`. When it lists tests the plan marks for removal, delete exactly those tests and run it again. On success it replaces each `planned` mark with the lasting label `@pytest.mark.acceptance(rule=...)`. Then tell the operator what was built, which tests were added, changed and removed, and what is parked.
