# Scoring kit brief

You are writing a scoring kit for the test suite of {target} in this project. The kit is a set of small code changes. Each one will be applied, one at a time, to a disposable copy of the project while its test suite runs against it. Write the kit to {kit_dir}; change no file in the project itself.

Read only the rules below and the production files listed. Read no test files and no test helpers. The kit judges the tests, so it must come from the rules and the code alone.

## What to write

- **Wrong versions.** For each rule, write one to three changes an implementer could plausibly make by misreading the rule, skipping part of it, or getting a boundary wrong. Each changes the behavior the rule describes for at least one input a user or caller could give, and leaves every other rule's behavior as it is, so a miss points to one rule. Prefer the mistakes most likely to pass unnoticed over obvious breakage such as a crash on every input, which fails any suite and so measures nothing. When a rule covers several entries, modes or channels, make at least one wrong version break a single entry or a single combination while its neighbors stay correct, since suites most often miss these.
- **Unsettled details.** When the rule's words do not decide whether a change is wrong, such as a missing value or a capitalization the rule does not mention, write no change for it and return the detail instead. A wrong version built on a guess would fail a correct suite.
- **Correct rewrites.** Write changes that keep every rule true for every input while changing what no rule fixes: at least one for each detail the rules leave open, such as an output's wording, order or layout, plus internal renames and restructures, at least eight in all, so that a test pinning any one detail meets a rewrite that changes it. Rename internal functions and helpers, inline or split them, reorder independent steps, change data structures inside the unit, and reword or reorder any output the rules leave open. Keep the entry points the rules name, with their names and signatures, unchanged. Rename internal names even when a comment says tests rely on them; a test that depends on an internal name is what the rewrites exist to find.

Each change is a unified diff against the current production files, made from the project root, and applies on its own with `git apply`. Check each with `git apply --check` in a disposable copy before writing it.

## What to return

Write each change as its own `.patch` file in {kit_dir}, and return one entry per file:

- the file name;
- `wrong` or `rewrite`;
- for a wrong version, the rule it breaks and an input where its behavior differs from the rule's;
- one sentence describing the change.

Then list each unsettled detail with the rule it falls under.

## Rules

{rules}

## Production files

{files}
