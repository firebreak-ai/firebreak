# Test trim brief

You are cleaning up the tests for {target} in this project. Edit only the test files and test helpers listed below. Production code stays exactly as it is.

Tests add maintenance work and earn it by catching bugs, so use the fewest tests that together catch the plausible wrong implementations. Test behavior, not implementation, so the code can change and grow: a different correct implementation passes every test, and each plausible wrong one fails at least one.

The rules below are the contract, each with the evidence that makes it one. A detail they do not name is open, and a test may not pin it, since a test that pins it fails a correct rewrite. Your tests are checked afterwards against wrong versions of the code you do not see. A miss comes back as the rule it broke.

## Done means

Run with `{test_command}`, the cleaned-up suite:
- passes on the unchanged production code;
- has, for each rule, a test that fails on the plausible wrong implementations of that rule you can name;
- no longer contains the change detectors listed below as they are: each is rewritten to check only what the rules name, or removed.

To check that a test fails on a wrong implementation, apply that implementation in a disposable copy of the project, never in the working tree: a wrong version left in place changes production code, which this cleanup leaves as it is.

## How tests are written

A reader new to this code understands what each test checks from its name and body. Combine cases into one test only when they show the same behavior: cases that differ only in value show the same behavior, and cases that differ in reason, such as a different rule or a different branch of one, are separate behaviors. Keep tests separate when combining would make them harder to follow.

Write each test with ordinary inputs through the entry points. When a behavior can only be reached by patching library or operating-system calls, changing process limits, setting up files to outguess the code, or depending on the current time, such as files named for the seconds around now, leave it untested and list it as a follow-up with the production change that would let a plain test reach it. Such setups break when the code changes how it reaches the library or the clock, not when its behavior breaks, so they cost maintenance without guarding the rules. A test that is skipped in some environments, such as when run as root, leaves its rule untested there; when it is the only test of a rule, list the rule as a follow-up as well.

## Trim

- Merge tests that check the same behavior, and remove a test that catches nothing the rest miss.
- Rewrite each listed change detector so it checks only what the rules name. Remove it if nothing would remain.
- Move a test that calls an internal function to the entry points the rules name. When no named entry point can observe the behavior, leave the test as it is and list it as a follow-up with the production change that would let it move.
- Keep every check the old tests made that a rule names, in some test, unless only one of the setups under "How tests are written" reaches it. Then remove the test and list the check as a follow-up.

## Strengthen

After the trim, read `{test_integrity}` and apply its checks to the trimmed tests. For each rule, name the wrong implementations most likely to pass unnoticed, and add or strengthen a test where none fails on them. A new test that fails on the unchanged production code has found a possible bug: remove it from the suite and return it as a possible bug, with the test's text and its failure output, since whether to fix the code or accept the behavior is the operator's decision.

## Merge

Last, combine tests that show the same behavior, for example into one test that runs over a list of inputs, where the result stays easy to follow and every check the tests made remains.

## Stop and ask

Return a question instead of a change when the change needs a decision the rules do not settle, such as a new test that needs a rule the list does not contain. Make every other change.

## What to return

- **Changes:** one entry per removed, rewritten, moved, added or merged test. For a removed test, give the remaining test that now makes each check it made, or the reason the check is not one the rules name. For an added test, give the wrong implementation it catches.
- **Coverage:** for each rule, the test that checks it and the wrong implementations you confirmed it fails on.
- **Follow-ups:** behaviors left untested or tests left in place for lack of a plain way in, each with the production change that would fix it.
- **Possible bugs:** as described under Strengthen.
- **Questions:** as described under Stop and ask.

## Rules

{rules}

## Test files and helpers

{files}

## Change detectors

These tests fail on a correct rewrite of the code:

{change_detectors}
