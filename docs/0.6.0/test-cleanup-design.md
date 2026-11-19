# Test cleanup: a standalone skill that shrinks and strengthens an existing test suite

Branch `fbk/test-cleanup`, cut from `fix/review-inflation`. Decided with the operator on 2026-11-04 and 2026-11-05. Revised on 2026-11-05 after the first trial run: the skill settles the rules from evidence and asks only about conflicts, where it first asked the operator to confirm every rule; the trim subagent no longer sees the kit; and tests must be plain and easy to follow, with fragile setups turned into follow-ups. It builds on the decisions-log entries from 2026-11-02 to 2026-11-04 about test count, change detectors and the entry points tests use, and on the spec trim (`docs/0.6.0/spec-trim-design.md`).

## Why

The recent guide changes stop Firebreak units from writing excess tests. Existing projects already have them. Their suites test the same behavior through several entry points and many inputs per rule. They pin details nobody decided, such as message wording, so a correct rewrite fails them. These tests are called change detectors. The suites also reach into internal functions, so renaming one breaks a whole test file.

Nothing in Firebreak looks for these problems today. The standalone test review (`fbk-test-review`) and its criteria (`review/test-integrity.md`) look for tests that are too weak: tests that would miss a bug, mocks that hide behavior, skipped tests. They say not to demand redundant tests, but they never look for excess.

`fbk-test-cleanup` applies the same guidance to an existing suite, one target at a time, and changes only what that guidance and the evidence support.

## The shape

1. **Pick a target.** The skill and the operator agree, in conversation, on one module or one part of the suite. If the operator wants help choosing, the skill offers a survey. It reads the whole suite, changes nothing, and ranks modules by signs of excess: duplicate cases, tests that call internal functions, and tests that pin message wording. The survey looks only for these patterns and needs no rules.
2. **Settle the rules.** The skill writes, for each entry point in the target, the rules the code must follow in plain words. It looks for them in the order the code review skill uses: Firebreak unit specs, then repository docs, then the code itself. It decides every detail the code, tests or specs show from evidence. A detail is a rule when a document states it, when code or a skill outside the target depends on it, or when it guards safety or security. Everything else is open, and tests stop checking it. The skill asks the operator only when sources conflict, one question at a time through the grilling skill. The operator sees the rules, their evidence and the open details in the report, and corrects a call on the branch before merging. If an earlier report exists for the same target, its rules are the starting draft.
3. **Build the scoring kit.** A separate subagent receives only the rules and the production code. It never sees the tests. It writes two sets of changes:
   - **Wrong versions:** one or more plausible bugs per rule. Where a rule covers several entries, modes or channels, at least one breaks a single entry or combination while its neighbors stay correct, the removal question from EXACT Coding's test list; suites most often miss these. A detail the rule's words do not decide gets no wrong version; the subagent returns it as unsettled.
   - **Correct rewrites:** behavior-preserving changes, such as renaming an internal function, inlining a helper or rewording a message no rule fixes.

   The main session reads each wrong version against its rule before the baseline. When the rule's words do not settle that the change is wrong, it settles the detail from evidence as in step 2, rewording the rule or calling the detail open and dropping the kit file. In the second trial, the kit writer made a missing harness and a capitalized "Codex" into bugs, though no document decides either.

   The kit is fixed before any test changes, and the trimming subagent never sees it, so its tests cannot be aimed at the kit and the kit result measures them honestly. The main session runs the current suite against every kit entry, in a disposable copy of the project and never in the real one. That gives the baseline: which wrong versions the old suite catches, and which old tests fail a correct rewrite. A test that fails a correct rewrite is a confirmed change detector.
4. **Trim.** A trimming subagent follows the test trim brief (below). It receives the rules, the old tests and the list of change detectors, and nothing else from the kit. It removes duplicates, rewrites change detectors to check only the rules, and moves tests from internal functions to the real entry points.
5. **Strengthen.** The same subagent applies `review/test-integrity.md` to the trimmed suite. For each rule it names the wrong implementations most likely to pass unnoticed, as a unit's test author does, and adds or strengthens tests where none fails on them. Tests must be easy for a newcomer to follow and plain: a behavior reachable only by patching library or operating-system calls, changing process limits, setting up files to outguess the code or depending on the current time becomes a follow-up for step 9, not a test. Plain tests win over keeping a check: an old check that only such a setup reaches is removed, listed as a follow-up and recorded in the report, rather than kept as a patched test. This pass runs after the trim so it cannot turn into "add more tests" first.
6. **Merge.** A final pass may combine tests that show the same behavior, meaning cases that differ only in value; cases that differ in reason are separate behaviors (EXACT Coding's hidden-rule check), for example into one test that runs over a list of inputs, where the result stays easy to follow. It may not remove any check the tests make. The run does not loop after this pass.
7. **Check.** The main session reruns the kit against the new suite with real commands. The new suite must pass every correct rewrite and should catch every wrong version; one the old suite caught and the new one misses is a lost check. A miss goes back to the trim subagent as the rule it broke, never as the kit file. The main session also reads the new tests and sends back any whose purpose is unclear or that use the fragile setups above. The main session does this check itself and does not rely on a subagent's report.
8. **Commit the test-only change.** Changes are made on a new branch, and production code is identical to before. The skill stops to ask only when a change needs a decision the rules do not settle, such as a new test that would need a rule the list does not contain.
9. **Escalate production changes.** After the test-only commit, the skill brings the operator two kinds of problems, each with a plan:
   - **Testability problems:** tests that must reach internal functions because no usable entry point exists. The plan adds one testable form that the real entry point itself calls, following the design guide's entry-point rule.
   - **Real bugs:** a new test that fails on the current code. The operator decides whether it is a bug to fix or behavior to accept as a rule.

   For each plan the operator approves, one subagent writes the tests first. They fail because the change does not exist yet. A different subagent then writes the implementation. The kit subagent rebuilds the kit for the changed code, because the old patches may no longer apply, and the main session reruns the check. Each approved plan is its own commit.

## The report

`.fbk/test-cleanup/<target>.md`, committed on the branch. It is named by target, not date, so a later run on the same target finds it. A later run updates the file, and git keeps its history.

It holds:
- the rules, each with its evidence, and the details called open;
- every change with its evidence (for a removed test, the correct rewrite it failed, or the remaining test that still catches each wrong version it caught; for an added test, the wrong version it catches);
- the before-and-after kit results;
- the follow-ups: tests left in place because they need a missing entry point, and the plans the operator declined or deferred.

It is committed rather than kept in `.fbk/runtime/`, as the other review reports are, because it justifies deleting tests. Without a recorded reason, a deleted test looks like lost coverage to anyone reading the history later.

## How it runs

It is a plain skill whose main session starts ordinary Claude Code subagents. It does not use Firebreak's review engine (`fbk.py review-round`). It needs no `.fbk/config.json`, so it works in any git project, and the report folder is the only thing it creates. Subagent results are not checked by code. The main session reads and judges them, and the kit check in step 7 runs real commands.

## The kit runner

`run-kit.py`, in the skill folder, runs the tests against every kit file. It copies the project's current state, uncommitted and new files included, into one disposable git worktree, applies each kit file to a fresh copy of that state, runs the given test command, and writes each run's exit code and output to a log plus a summary line: passed, failed, timed out or did not apply. The unchanged state runs first. It does not read test names from the output, which depends on the test tool; the main session reads the logs. It needs only Python's standard library, so it works for any project language.

## The briefs

- **Scoring-kit brief:** the rules, the production code and what the two sets of changes must be. No tests.
- **Test trim brief:** adapts the spec trim's rules to test code. It covers merging tests that catch the same wrong version, removing a test that catches nothing the rest miss, moving tests to the real entry points, and never removing the last test that catches a rule's wrong version. It includes, word for word, the paragraph the spec and test-authoring guides gained on 2026-11-04:

  > Tests add maintenance work and earn it by catching bugs, so use the fewest tests that together catch the plausible wrong implementations; spec examples become those tests. Test behavior, not implementation, so the code can change and grow: a different correct implementation passes every test, and each plausible wrong one fails at least one.

  That makes three copies, in `workflow/spec.md`, `workflow/test-authoring.md` and the test trim brief. The copies exist because each reader receives only its own brief, the same reason the decisions log gave for the first two. The skill could instead read `test-authoring.md` directly, but most of that file covers stub code, expected failures and the test checkpoint, and those rules would be noise here. Moving the paragraph into a shared file would also change how `handoff.py` builds test-worker instructions, so a standalone skill would need workflow changes. That move is worth making the next time someone edits that code for another reason.

  The wording "spec examples become those tests" fits the workflow guides. If the trim brief needs different wording, the copies differ by decision, and the sync test records that difference.

## Keeping the copies in sync

A test in the Firebreak suite extracts the paragraph from each of the three files and fails if they differ, naming the files. Each copy must stay a separable block the test can find. A decisions-log entry names all three locations. No comment goes inside the copies, because `test-authoring.md` goes word for word into every test worker's instructions.

## Not in this note

- A durable per-module rules file that units and code reviews read as documented intent. It may come later if runs show those readers want it.
- Running on Firebreak's review engine, if subagent results prove unreliable.
- The test-checkpoint check that suggests removing change detectors and duplicates inside units, which the spec trim note lists as its own later note.

## Watch items

- The wrong versions come from a model, so they cover the bugs it thinks of. They support each cut but do not prove it.
- Kit runs multiply suite runs. Limiting each run to one target keeps this affordable. A slow suite may still need a narrower target.
- An approved production change makes the old kit stale. The rebuild is required, not optional.
- The skill has not run on a real brownfield suite yet. The first runs are on the operator's own projects, on a target larger than the cross-review module and in a language other than Python. The Agentic Coding Lab found that results do not carry over between models or language stacks, and that small prose additions can make an agent stop early with its own tests green, which only a unit with many rules shows.

## Build order

Use the context-asset authoring skill throughout.

1. The test trim brief and the scoring-kit brief.
2. The skill: picking the target, the survey, settling the rules, the subagent steps, the kit check, the commit, the escalation path and the report.
3. The test that the three copies of the paragraph match.
4. The installer and manifest entries for the new files, and the installer and workflow shell suites run locally.
5. The decisions-log entry naming the three copies, a glossary entry for test cleanup, the scoring kit and change detectors if they are not already defined, and the README if it lists skills.
6. A first run on one of the operator's projects, with the result recorded before release.
