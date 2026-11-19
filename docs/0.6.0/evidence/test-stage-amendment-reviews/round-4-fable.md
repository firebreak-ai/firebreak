NOT CLEAN: 1 blockers, 1 contradictions

# Round 4 (final, targeted) review of `docs/0.6.0/test-stage-amendment-plan.md` (Fable, 2026-10-22)

All paths are under ``. Workflow modules are in `assets/fbk-scripts/fbk/workflow/`. Plan line numbers refer to the plan as read today. Every round-3 finding from both reviewers is resolved in the current plan; both items below are interactions between fixes made in rounds 2 and 3, not repeats.

## Contradiction 1 — Decision 3 vs decision 5: the checkpoint refuses the production edits decision 5 lets a running implementation worker make during an unlock

**Decision 3 (plan:40):** "Each time the unit enters writing tests (first entry into implement, an unlock approval, the return after a reopen), Firebreak records a baseline ... A production change outside every test task's declared files is refused at the checkpoint."

**Decision 5 (plan:54):** "A running implementation task's worker keeps writing within its ownership while an unlock is outstanding; no new implementation task starts."

**Decision 11 (plan:91):** "correct code is never undone to recreate red."

Sequence: an implementation task is running; the operator approves an unlock; the baseline is recorded from the tree at that moment (decision 3, confirmed by step 4, plan:112 "the baseline is re-recorded at the unlock"); the implementation worker keeps writing `src/app.py` and finishes (decision 5 permits this); the rework test task finishes; the checkpoint re-runs and compares the tree with the baseline. `src/app.py` differs from the baseline and is in no test task's declared `files`, so decision 3 refuses the checkpoint. The only ways out are to undo the implementation (decision 11 forbids) or to approve a second unlock purely to re-record the baseline. Nothing in the record attributes the change to the authorized worker at checkpoint time: each task run fingerprints only its own files at start and return (`handoff.py:733`, `handoff.py:790-794`), and the plan gives the checkpoint no instruction to read those runs. The done-means "Unlock rework" line (plan:131) runs no implementation task during the unlock, so the suite would be green with the three sentences in conflict.

**Smallest fix:** one clause in decision 3: "A production change outside every test task's declared files, and outside the ownership of an implementation task that was running when the baseline was recorded, is refused at the checkpoint." Add to done-means Unlock rework: "with an implementation task that was running at the approval finishing its production edits before the re-run, the checkpoint accepts."

## Blocker 1 — Decision 11: "the lead scopes the rework task's commands to the named tests" has no mechanism, and the one existing lever (editing `tasks.json`) is the reopen decision 11 is designed to avoid

**Decision 11 (plan:93):** "Firebreak sees only command exit codes, so the approval's expectations apply per command: the lead scopes the rework task's commands to the named tests; a command whose named tests are all expected to pass must exit zero, and any other must exit non-zero."

**Decision 11 (plan:90):** "Reopening breakdown or any earlier phase clears the locks, the saved copies, and the checkpoint's acceptance ... Reopening implement only keeps them."

**Decision 10 (plan:87):** "Entering or re-entering breakdown supersedes earlier task runs."

A task's check commands live only in `tasks.json`; a task run copies them at start (`handoff.py:720`) and task finish compares each returned check's exit code against that copy, with a default expectation of 0 for any command the task did not declare (`handoff.py:905-912`), so a worker cannot substitute a scoped command either. `tasks.json` is breakdown's accepted evidence (`close.py:141` stores `evidence.subject`, which for breakdown is `tasks.json`: `evidence.py:171`), and the write hook refuses every write to an accepted-evidence file for every session, before any task or lock check (`hooks.py:138-141`). `task-start` accepts a worker, an outcome and two reference lists, no command or expectation override (`cli.py:127-131`). The unlock approval carries only test paths (`cli.py:159-160`, `engine.py:161-176`). So the lead's only route to a scoped command is to reopen breakdown and edit `tasks.json`, which clears the locks and the checkpoint's acceptance and supersedes every completed test run (decision 10 and 11 text above), turning the named unlock into the full reopen it exists to avoid. The step-4 builder cannot write the done-means case "with two named tests, one expected to pass and one to fail, scoped commands complete against their expectations" (plan:131) without first deciding where the scoped commands and their expectations are recorded; that is a decision about the approval's shape, not a code-fitting detail, which is why it does not fit inside one step's tests-first work.

**Smallest fix:** one sentence in decision 11: "The unlock approval records, per command, the argv and its expected result (`pass` or `fail`); the rework task's run uses those in place of the task's declared check expectations, and task finish compares against them." Step 4 then names the approval's new fields and the task-run substitution.

## Fitting notes (non-blocking)

- Decision 3 (plan:40) names a baseline folder of saved copies but, unlike decisions 4 and 7 for their folders, does not say it is git-ignored and refused to the write hook; `hooks.py:101-104` lets the owning session write anything under the unit directory.
- Step 3 (plan:111) runs the checkpoint on breakdown-locked tests, but a breakdown lock derives writing code at implement entry (step 1, plan:109), so no writing-tests baseline exists for that commit's checkpoint comparison; step 3 should say what the comparison uses in that transitional case.
- Decision 1's stage rule (plan:21-23) derives writing tests when no checkpoint has accepted; decision 9's no-tests outcome (plan:85) starts implement in writing code with no checkpoint. Step 9 should name the recorded empty inventory as an input to the stage derivation and task start (`handoff.py:608-660`).
- Done-means Refused orderings (plan:124) still says "a test task after [the lock]"; step 1 (plan:109) gates on the derived stage, and a test task must start while locks exist during an unlock. Word the done-means line by stage.
- Decision 4/11 "previous accepted checkpoint whose saved output shows it failing" (plan:48, 91): acceptance is cleared at unlock and reopen, and the named output folder is overwritten by each run, so the historical-red lookup must read the pass events and the stored round snapshots, not the live folder or the acceptance field (`close.py:257-262` is the only place an accepted snapshot is bound today).
- `engine.verify_locks` refuses when the scoped test set differs from the lock map (`engine.py:367-371`); steps 6 and 9 both need it changed (regions add non-test files to the lock; the no-tests outcome has an empty lock map), and neither names it.
