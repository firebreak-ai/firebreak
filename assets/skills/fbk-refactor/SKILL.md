---
description: >-
  Refactor one target in an existing project without changing its behavior:
  check first that its tests would catch a wrong change, then improve its
  structure by the four rules of simple design and a tried domain boundary.
argument-hint: "[module or directory]"
disable-model-invocation: true
# Source: the refactor method is adapted from EXACT Coding's Predictive TDD v1.2 (MIT) — https://github.com/marcoemrich/agentic_coding_lab/tree/main/research/workflow-dev/export/2026-10-29-exact-coding-ptdd-v1.2
---

Refactor one target the operator chooses. The result is a branch with a commit that changes production code only, and a committed report at `.fbk/refactor/<target>.md` listing every change and trial with run evidence.

Resolve `firebreak_dir`: use `${CLAUDE_PROJECT_DIR:-$PWD}/.claude` when it contains `fbk-docs/workflow/refactor.md`, otherwise `$HOME/.claude`. Steps 2 and 3 follow `$firebreak_dir/fbk-docs/scoring-kit/procedure.md`; the refactor method is `$firebreak_dir/fbk-docs/workflow/refactor.md`.

The steps run in order: each one's output is the next one's input.

## 1. Choose the target

Agree with the operator on one module or directory, using `$ARGUMENTS` as the starting point when given, and on the command that runs the tests covering it. Run that command on the unchanged code. When any test fails, show the failures and let the operator decide whether to proceed, since a refactor is judged by the tests staying green. Then create a branch named `refactor/<target>` from the current commit.

## 2. Settle the rules

Follow "Settle the rules" in the procedure.

## 3. Check the tests

Follow "Build the kit and measure the tests" in the procedure. The refactor is only as safe as these tests: a wrong version they miss is a behavior change a refactor could make unnoticed, and a test that fails a correct rewrite blocks restructuring the code it pins.

When any wrong version escapes or any test fails a correct rewrite, stop and show the operator the rules the escaped versions break and the tests that failed a rewrite, and recommend running `fbk-test-cleanup` on the target first. Proceed only when the operator chooses to; the report then lists the unguarded rules and the pinned details, and the refactor keeps every detail a failing-rewrite test pins.

## 4. Refactor

Start one subagent per folder of the target, or one for a small target, never two on the same file. Give each, as its prompt, the text of `refactor.md` followed by: the rules; the files it owns, and that it may create files only inside the target's folders; the test command; and any details the tests pin from step 3. It edits production code in the working tree.

## 5. Check the result

Run the test command yourself: every test passes, and `git diff` shows production files only. Read each subagent's review against the diff. Send back once any change the review claims that the diff does not show, and any believable boundary between independently changing policies that it neither tried nor explained; when the second answer still falls short, record the shortfall in the report.

## 6. Write the report and commit

Write `.fbk/refactor/<target>.md` with:
- the test check from step 3: which wrong versions the tests caught, and any unguarded rules or pinned details the operator chose to proceed over;
- each subagent's review: every unit's responsibility, each boundary tried and whether it was kept, and each other change with the rule of simple design it serves;
- the final test result.

When the file exists from an earlier run, update it. Write the rules from step 2, each with its evidence, and the open details into `.fbk/test-cleanup/<target>.md`, creating it when absent, so a later cleanup or refactor of the target starts from them. Commit the production changes, that file and the report together, staging their paths by name.
