Build a task's behaviour one test at a time. `testplan.py brief <task>` lists the task's tests in order, the commands that run the suite and the linter, and which owner holds each rule in this change.

`testplan.py next <task>` switches on the task's next test. For each test:

1. Make it pass with the smallest change that keeps every other test passing. A hard-coded value or a narrow condition is fine until a later test needs more. A test that passes as soon as it is switched on needs no code.
2. Review the code this step touched against the refactor guide, and make each change it calls for, one at a time.
3. Run `testplan.py next <task> --review "<each unit you reviewed, the boundary you tried or why there was none, and what you changed>"`. This command is the check for the step: it runs the task's test files and the linter, shows what failed, and only then records the step and switches on the next test. Run a single test yourself while working on it; leave the wider runs to this command. When the task's last test is done it runs the whole suite.

When the brief names a lint command, each step ends with no more lint findings than the plan started with, and the tool refuses the next step otherwise. Remove a finding your work added by restructuring the code; the rule and its settings stay as they are.

Build each rule in the owner the brief names for it. Before adding a helper, search by responsibility for one that already exists, starting with the owners in the brief.

The plan is fixed: test names, marks and docstrings stay as approved, and the tool refuses the next step when they differ. When a test contradicts the request in `.fbk/testplan/request.md`, stop and report the test, the request's words, and the contradiction.
