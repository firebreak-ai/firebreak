Write the body of every test in the plan marked `add`, `change` or `protect`. The operator approved each test's name, mark and docstring, so those stay exactly as they are; the tool refuses a plan that differs from the approved one. The request is in `.fbk/testplan/request.md`.

Each test checks what its docstring says, through the owner its mark names, using the real interface and real collaborators. Reuse the project's existing test helpers.

Test behaviour, so the code can change and grow: a different correct implementation passes every test, and each plausible wrong one fails at least one. Assert what the example states and leave everything else open, including details the request does not fix. Keep fixtures consistent with each other, and assert results the code must produce, not values the test just assigned.

Change production code only as far as the suite needs to load against a new or changed interface: signatures, types and fields, with new code doing nothing meaningful. A stub returns a value no test expects, so each new test fails on its assertion.

Planned tests are skipped until an implementer switches them on. Set `FBK_TESTPLAN_ALL=1` to run them all. You are done when:

- the suite passes without that variable;
- with it, every `add` and `change` test fails on an assertion about behaviour not built yet, with imports and collection working;
- every `protect` test passes.

When an example cannot be checked through its named owner, or the plan looks wrong against the request, report the test and the reason in place of changing its mark.

Return the tests written, the production files touched, and any such reports.
