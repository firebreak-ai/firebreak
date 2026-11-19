---
description: >-
  Clean up an existing project's tests one target at a time: remove duplicates
  and change detectors, move tests to real entry points, and add tests only
  where a plausible bug would escape, all checked against a scoring kit.
argument-hint: "[module, directory or test path]"
disable-model-invocation: true
---

Clean up the tests for one target the operator chooses. The result is a branch with a test-only commit, a committed report at `.fbk/test-cleanup/<target>.md` explaining every change with run evidence, and, for each production change the operator approves, its own commit.

Resolve `firebreak_dir`: use `${CLAUDE_PROJECT_DIR:-$PWD}/.claude` when it contains `fbk-docs/review/test-integrity.md`, otherwise `$HOME/.claude`. Steps 2 and 3 follow `$firebreak_dir/fbk-docs/scoring-kit/procedure.md`. The trim brief, `test-trim.md`, is in this skill's directory. Fill every `{placeholder}` in a brief before passing it as a subagent's prompt.

The steps run in order: each one's output is the next one's input.

## 1. Choose the target

Agree with the operator on one module, directory or part of the suite. Use `$ARGUMENTS` as the starting point when given. When the operator wants help choosing, survey the whole suite without changing anything and rank modules by signs of excess: several tests checking the same behavior, tests calling internal functions rather than the entry points outside code uses, and tests asserting exact message wording. Agree on the command that runs only the target's tests.

Run that command on the unchanged code. When any test fails, show the failures and let the operator decide whether to proceed, since a failing baseline hides what the kit measures. Then create a branch named `test-cleanup/<target>` from the current commit.

## 2. Settle the rules

Follow "Settle the rules" in the procedure.

## 3. Build the scoring kit and baseline

Follow "Build the kit and measure the tests" in the procedure. Its result on the unchanged tests is the baseline. Before running the kit, move about a third of the wrong versions and a third of the correct rewrites into a `held` subfolder of the kit folder, spread across the rules. Run the baseline on both parts, the held part with `--kit <kit folder>/held` and its own log folder. Steps 4 and 5 use only the working part; the held part is scored once, in step 6, so its result is not fitted to the trim.

## 4. Trim, strengthen and merge

Start a subagent with `test-trim.md` as its prompt, giving it the rules, the target's test files and helpers, the change detectors from the baseline's working part, the test command and the path to `$firebreak_dir/fbk-docs/review/test-integrity.md`. Give it nothing else from the kit: not the kit files, their folder or which wrong versions the old suite caught, since the kit measures its tests. It edits the tests in the working tree.

Put each question it returns to the operator, then send the answer back to the same subagent. Hold each possible bug it returns for step 7.

## 5. Check the result

Run `$firebreak_dir/fbk-scripts/run-kit.py` again yourself, as in the procedure, with a new log folder; it picks up the cleaned-up tests from the working tree. Production code must be unchanged (`git diff` shows test files only). The cleaned-up suite passes on the unchanged code and with every correct rewrite applied, and fails with every wrong version. A wrong version the baseline suite caught and the new suite misses is a lost check, unless the subagent listed it as a follow-up because only a fragile setup reaches it; any other miss is a gap the strengthen pass left. Before treating a miss as a gap, check that some input through the entry points reaches the changed code with a different result; a version none can tell from correct code is equivalent, and is reported as such rather than sent back. Send any miss back to the trim subagent as the rule the escaped wrong version breaks, or the test that failed a correct rewrite, never the kit file itself. When a second attempt still misses, show the operator the results and let them decide.

Then read the new tests. Send back any test whose purpose is not clear from its name and body, any that uses a setup the "How tests are written" section of `test-trim.md` rules out, and any that skips itself in some environments while being the only test of its rule, so the subagent rewrites it plainly or lists it as a follow-up.

## 6. Write the report and commit

After the last change to the tests, run the held part once with a new log folder, and change no test after it. A held miss, checked for equivalence as in step 5, goes in the report as a finding, not back to the trim subagent.

Write `.fbk/test-cleanup/<target>.md` with:
- the rules, each with its evidence, and the details called open;
- every change with its evidence, from the subagent's list and your own check;
- the size of test helpers and fakes before and after, which the kit does not score;
- the kit check before and after, the working and held parts listed separately: for each kit file, its kind, what it changes, and whether the old and the new suite passed or failed with it;
- follow-ups: tests left in place for lack of an entry point, checks given up because only a fragile setup reaches them, and any plans the operator declines or defers in step 7.

When the file exists from an earlier run, update it. Commit the test changes and the report together, staging their paths by name.

## 7. Escalate production changes

Bring the operator the follow-ups and possible bugs, each with a plan:
- **For a missing entry point,** add one testable form that the real entry point itself calls, so tests run the production code the user runs. Expose an internal part only when outside code already calls it or the operator asks.
- **For a possible bug,** show the failing test and its output, and ask whether to fix the code or accept the behavior as a rule. An accepted behavior joins the rules.

For each approved plan, when it changes a signature, first make the bare change yourself, accepting the new parameters without using them, so the tests build. Then one subagent writes the tests through the planned entry point or for the fixed behavior, and you confirm they fail for the missing change and not for an import or build error. A different subagent then changes the production code until those tests pass, so the code is not written by the agent that shaped the tests it must pass. Rerun the kit on the changed code. Give a new scoring-kit subagent the patches that no longer apply, to port with the same intent, and the changed rule, to add wrong versions and rewrites for it; then rerun the step 5 check, update the report, and commit the plan as its own commit.
