Turn the operator's request into a list of behavioural acceptance tests and get the operator's approval of the printed plan. The operator reads the printout, not the code, so each test's mark and docstring must say in plain words everything needed to judge it.

## Start

Save the request word for word in a file, then run `testplan.py init --request <file> --check "<the command that runs the project's whole test suite>"`. Add `--bodies implementer` or `--session one` only when the operator asks for that setting. When the project configures a linter, add `--lint "<its command over the production code, in a format that prints path:line:col: RULE message>"`: the build then leaves no more lint findings than the code has now.

## Survey the code first

Read the code and tests the request touches before proposing any test. For each rule in the request, find:

- **Its owner:** the function or module that already does this job. Search by responsibility as well as by name, and read the plausible alternatives before choosing. The rule then extends that owner or changes it. A rule gets a new owner only when no existing one fits, and the plan states why.
- **The tests that describe the behaviour today.** A test the change makes wrong is changed or removed in the plan; the change does not add a second test beside it.
- **Existing behaviour the change puts at risk** in an owner it alters. Where no test covers that behaviour, the plan adds a protective test.

When the request starts a new program or a new area with no code to survey, the first test is one end-to-end example through the real entry point, marked `skeleton=True`. Building it makes the layout, top-level interfaces and data flow exist before any rule depends on them.

## Rules and examples come from the operator

Each test comes from the request's own words or from an answer the operator gave. Scale the questions to the request: a request that already states its rules with examples may need none.

- Where the request leaves open something that changes what the program does, ask the operator, then record it: `testplan.py answer "<question>" "<answer>"`.
- A detail the request leaves open, such as the wording of a message, stays untested, so the implementation is free to choose it.
- Behaviour worth having that the request does not ask for is parked: `testplan.py park "<title>"`.
- When the examples under one rule differ in reason and not only in values, ask the operator whether a second rule is hiding there.

## Write the list

Each planned test carries one `planned` mark. Every field is a plain string literal. A test from an earlier change carries `@pytest.mark.acceptance(rule=...)`: leave that label as it is, and add a `planned` mark above it only when this change alters or removes the test.

```python
@pytest.mark.planned(
    rule="Cancelling a policy refunds the unused months",
    source="request: a cancelled policy refunds every full month not yet used",
    owner="policy.cancel",
)
def test_cancel_in_month_three_refunds_nine_months():
    """A 12-month policy at 10 a month, cancelled in month 3, refunds 90."""
```

- `rule`: the rule in the operator's terms. Tests of one rule share the same text.
- The docstring: one example with its concrete values, readable without the code.
- `source`: `request: <exact words from the request>` or `answer: <number>`.
- `owner`: the function or module the test goes through. Add `new_owner="<why no existing owner fits>"` when the owner does not exist yet.
- `action`: `add` (the default) for a new test, written now as a docstring with no body.
- `action="change"`: put the mark on the existing test, set the docstring to what it will say, add `was="<what it says today>"` and `reason`. Leave its body as it is.
- `action="remove"`: put the mark on the existing test with `reason`. Leave the test as it is.
- `action="protect"`: a test guarding existing behaviour. It takes `rule` and `owner` and no `source`.

Cover every example the request gives, and beyond those use the fewest tests that together would catch the plausible wrong implementations. Order a file's new tests from simplest to most complex: tests are built in that order, grouped by owner.

## Approval

`testplan.py plan` prints the plan and names anything that keeps it from approval. Show the operator the printout whole and unedited. When the operator approves, record it with `testplan.py approve --reason "<the operator's words>"`; it also confirms the existing suite passes with the planned tests switched off. When the operator asks for changes, edit the marks and print again.

Then run `testplan.py status`. When it says one session does the work, read `build-one-context.md` beside this file; otherwise read `build.md`.
