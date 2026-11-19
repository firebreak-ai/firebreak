# Round 2 review of `docs/0.6.0/test-stage-amendment-plan.md` (Fable, 2026-10-22)

All paths are under ``. Workflow modules are in `assets/fbk-scripts/fbk/workflow/`; Python tests in `assets/fbk-scripts/tests/`. Plan line numbers refer to the revised plan as read today.

## Round-1 resolution

Astra 1-16:

1. **Resolved.** Build order is now additive: step 1 keeps breakdown locking (plan:76), step 2 adds the checkpoint beside it (plan:77 "both lock routes exist"), step 3 removes the breakdown route (plan:78).
2. **Resolved.** `lock-tests` and `check-tests` are removed and the checkpoint is the only lock route (plan:68, 78); done-means refuses any other route (plan:87).
3. **Resolved.** Decision 9 (plan:62) keeps plan validation at breakdown close and separates it from preparation readiness; step 3 makes the breakdown review's inputs and obligations plan-only (plan:78).
4. **Resolved.** Decision 1 walks every task declared in `tasks.json` (plan:25) and done-means covers a never-started task, a relaunched task after rejection, and an outstanding unlock (plan:88).
5. **Partly resolved.** Step 2 lists the sites to wire (plan:77). What remains: the record's placement is still worded "beside the phase records" (plan:27), and the revision/readiness calls the close machinery makes first (`evidence.subject`, `evidence.revision`, `decisions.binding`, `close._ready`) are not in the list; see new findings 2 and 7.
6. **Resolved.** Decision 3 retires `stubs`, has plan validation and the source-baseline check accept declared production files, and exposes the task run's before/after fingerprints to the reviewer (plan:33). Where the surviving source-baseline check lands is unassigned; see new finding 9.
7. **Partly resolved.** Decision 4 carries `nonzero` through expectations and task finish and keeps actual exit codes (plan:37); done-means has the Rust-shaped 101 case (plan:89). What remains: build/load-failure rejection is reviewer-judged and has no done-means line of its own.
8. **Resolved.** Full red stdout/stderr go to files whose fingerprints enter the evidence (plan:37); done-means has the oversize-with-early-evidence case (plan:89). The files' home has a code gap; see new finding 5.
9. **Resolved.** Decision 5 derives changed tests from test runs' before/after fingerprints and runs the whole-unit checks so every scoped test's outcome is on record (plan:44); done-means has the mixed-suite rejections (plan:89).
10. **Resolved** at decision level (plan:41-43; wildcard rule, hook refuses every scoped test path). The obvious implementation breaks Go units; see new finding 6.
11. **Resolved.** Decision 10 clears locks, copies and checkpoint acceptance on reopening breakdown or earlier (plan:65); done-means at plan:92.
12. **Partly resolved.** Historical-red lookup moves to checkpoint acceptance and the checkpoint snapshot becomes the implement review baseline (plan:27, 66). What remains: round reuse and "current" for the checkpoint need a revision definition the plan does not give; see new finding 2.
13. **Resolved.** Step 1 fixes continuation's default (plan:76); step 2 wires status, the stop hook and the retrospective (plan:77); done-means at plan:90.
14. **Resolved.** Decision 7 fixes the item convention (named section, heading per item, anchor links, correct-section rule) (plan:50-53); done-means refuses wrong-section, renamed and duplicate targets (plan:93).
15. **Resolved.** Decision 6 plus the Locks done-means line (plan:47, 91) name both boundaries, the in-check window, the event's contents, exact restore, deletion at close, and reopen behavior.
16. **Resolved.** Decision 11 bumps the state version and refuses older records naming the amendment; done-means checks the installed dispatcher lists the checkpoint command (plan:70, 94).

Fable I-1 to I-17:

- **I-1 Resolved.** Step 1 is now additive and keeps breakdown locking; removal is step 3 (plan:76-78).
- **I-2 Resolved.** "Entering implement no longer requires locks" is in step 1 and done-means (plan:76, 86).
- **I-3 Resolved.** Same as Astra 11.
- **I-4 Partly resolved.** Same remainder as Astra 5.
- **I-5 Resolved.** Decision 2 names the fixed reviewer and drops "review-plan choice" from the record's fields (plan:27).
- **I-6 Resolved.** Same as Astra 7's resolved part.
- **I-7 Partly resolved.** Files plus required reading are specified (plan:37), but the snapshot policy refuses them where the plan puts them; see new finding 5.
- **I-8 Resolved.** Same as Astra 14.
- **I-9 Resolved.** Limit stays, chain carries each item's own section, oversize refuses naming the task (plan:58).
- **I-10 Partly resolved.** Decision 10 defines the crossing (unlock, writing tests, test task rework, checkpoint re-run) (plan:67). What remains: it contradicts decision 6 at task finish and leaves checkpoint acceptance in place; see new findings 3 and 4.
- **I-11 Resolved.** Step 1, last sentence (plan:76).
- **I-12 Resolved.** Decision 9 keeps the run reset on breakdown entry (plan:62); decision 3 retires `stubs` (plan:33).
- **I-13 Resolved.** Decision 6: git-ignored, hook-protected folder (plan:47).
- **I-14 Resolved.** Decision 2, last sentence (plan:27); step 2 (plan:77).
- **I-15 Resolved.** Decision 11 (plan:70).
- **I-16 Resolved.** Same as Astra 2.
- **I-17 Resolved.** Decision 2 routes test-remedy dispositions at the checkpoint (plan:27); step 2 lists "suggestion dispositions" (plan:77); done-means at plan:90.

Totals: 27 resolved, 6 partly resolved (Astra 5, 7, 12; Fable I-4, I-7, I-10), 0 unresolved.

## New findings

No blockers. Six major, twelve minor.

### 1 — major — Build order step 2: implement close demands a checkpoint while every fixture still locks through breakdown, so the step-2 commit cannot be green or usable end to end

Step 2 says "Implementation close requires a current accepted checkpoint" and, in the same step, "Both lock routes exist for this one commit" (plan:77); the fixtures that lock in breakdown are rewritten only in step 3 (plan:78). Today `close._ready` for implement requires locks (`close.py:43-47`); ten test files reach implement through `prepare_implementation`, which locks at breakdown close (`test_workflow_lifecycle.py:138-148, 151-161`). After step 2 as written, each of those closes is refused for lack of a checkpoint, unless the checkpoint can be run on tests that breakdown already locked. Whether it can is not stated: with a breakdown lock the stage derives "writing code" (plan:76), and nothing says the checkpoint command is allowed in that stage. The plan's own rule that every commit leaves the workflow usable end to end (plan:74) is broken for one commit.

Smallest fix: move "implementation close requires a current accepted checkpoint" and the baseline switch from step 2 to step 3, where the breakdown route and the fixtures change together; or, in step 2, state that the checkpoint may run on breakdown-locked tests and that implement close accepts either lock source until step 3.

### 2 — major — Decision 2 / step 2: the checkpoint has no revision, so "current accepted checkpoint", round reuse, and the first three calls of the close machinery are undefined for it

The plan reuses the phase review machinery for a record keyed `test-checkpoint` (plan:27, 77). That machinery's entry points take a phase name and compute a revision from it: `close._ready` refuses unless `phase_state` returns that name as the open phase (`close.py:18-22`); `evidence.structural` calls `evidence.subject`, whose loop never breaks for a name outside `PHASES` and so returns the wrong file set (`evidence.py:175-184`); `evidence.revision_inputs` calls `decisions.binding`, which does `phases.index(phase)` and raises `ValueError`, not `WorkflowError`, for the checkpoint key (`evidence.py:208, 213`; `decisions.py:68-71`); `grant_target` for close-over-findings also goes through `observed_revision` (`engine.py:132-143`). None of these are in step 2's site list. The plan also never says what the checkpoint's revision digests. It must include the locked test hashes and the breakdown revision and must exclude production sources (otherwise implementing code makes the accepted checkpoint stale, which is the exact defect Astra 12 described for the implement revision at `evidence.py:192-196`). Without that definition, "a current accepted checkpoint" (plan:27, 87) and "unchanged tests keep their red evidence from the previous accepted checkpoint" (plan:66) have no mechanical meaning.

Smallest fix: in decision 2 or step 2, define the checkpoint revision as the accepted breakdown revision plus the hashes of every scoped test file; "current" means that revision matches and `verify_locks` passes. Add `close._ready`, `evidence.subject`, `evidence.revision_inputs`/`decisions.binding`, and `grant_target` to step 2's site list.

### 3 — major — Decision 6 contradicts decision 10: comparing "every locked test" at task finish refuses the test task that reworks an unlocked test

Decision 6: "Task start and task finish compare every locked test against its lock ... A mismatch refuses the finish" (plan:47). Decision 10: after `approve unlock-test`, "a test task reworks the named tests, and the checkpoint runs again" (plan:67). The reworked file is still in `locks` with its old hash until the checkpoint re-locks, so the rework task's finish is refused by decision 6's rule and the checkpoint can never be reached. Today's code already exempts outstanding unlocks in both places that compare hashes against locks: `lock_tests` (`engine.py:338-342`) and the write hook (`hooks.py:157`); only `verify_locks` compares all (`engine.py:362-366`), and it refuses close while any unlock is outstanding anyway (`engine.py:358-361`). No done-means line exercises "a test task finishes after reworking an unlocked test".

Smallest fix: in decision 6, add "except a file with an approved unlock outstanding"; add that case to the Locks done-means line.

### 4 — major — Decision 10 / step 2: approving an unlock does not clear the checkpoint's acceptance, so the hook refuses the rework write and the re-run has no defined state

The checkpoint's accepted evidence must list the scoped tests in its `files` (it is the implement review's baseline, and `review_baseline._bodies` requires `accepted["files"]` to be in the snapshot manifest: `review_baseline.py:86`). The write hook refuses any write to a file named in any accepted evidence's `files` with "reopen its phase before changing it" (`hooks.py:138-141`), so once the checkpoint has passed, the test task reworking an unlocked test cannot write it. Decision 10 says the unit "is in writing tests" during an unlock and "the checkpoint runs again" (plan:67) but never says the acceptance is cleared. With evidence still present, `review_budget_exhausted` can never report exhaustion (`engine.py:379-382`), and `_close_phase`'s reuse test (`close.py:117-130`) and the implement-close requirement for a "current" checkpoint have no state to distinguish "accepted earlier, unlock outstanding" from "accepted".

Smallest fix: `approve unlock-test` clears the checkpoint's accepted evidence (keeping rounds, budget and generation) with an event; implement close then needs a fresh acceptance. One sentence in decision 10 and one in step 2.

### 5 — major — Decision 4 / step 2: red output files "in the unit's `.fbk/` folder" are refused as review sources by the snapshot policy, and would be hygiene-scanned as authored artifacts

The reviewer reads a snapshot built from `required`, and `source_paths` refuses any `.fbk/` path that `_unit_source` does not allow-list: only `prd.md`, `spec.md`, `scope.json`, `tasks.json`, and files under `design/` or `decisions/` (`review_context.py:261-264, 284-308`). A file such as `.fbk/<unit>/checks/red-stdout.txt` raises "Workflow history cannot be a review source" before any round starts. Separately, `_close_phase` runs the invisible-character scan over every subject file under the unit folder (`close.py:151-153`, `_unit_artifacts` at 345-348), and that scan reports any control character below 0x20 except tab, newline and carriage return (`artifact_hygiene.py:14, 36-41`); a test runner's ESC color codes or a form feed in captured output would fail the checkpoint before a round. Step 2 names neither module.

Smallest fix: in step 2, name the folder (one under the unit directory), add it to `_unit_source`'s allow-list, and exclude it from the hygiene scan (it is captured evidence, not an authored artifact).

### 6 — major — Decision 5 / done-means: the Go-shaped positive case is missing, and the implementation round 1 pointed at rejects every Go implementation task

Decision 5's rule is correct as worded: an implementation task is rejected when its owned paths "can match any path the scope's test patterns can match" (plan:41). Round 1 (Fable ruling 10) told the implementer to use prefix-overlap validation, and the existing helper is prefix-based. Executed today: `ownership_overlaps(["pkg/foo.go"], ["pkg/**/*_test.go"])` returns `True`, and `ownership_overlaps(["src/x.go"], ["**/*_test.go"])` returns `True` (`handoff.py:749-764`), while `evidence.matches("pkg/foo.go", ["pkg/**/*_test.go"])` returns `False` (`evidence.py:93-125`). Go keeps `foo.go` and `foo_test.go` in the same directory, so prefix-overlap rejects every Go implementation task in a package with tests. Done-means lists only refusals ("owning a test path, including by wildcard", plan:87) and no acceptance case, so the suite would pass with the broken rule.

Smallest fix: add to done-means "an implementation task owning `pkg/foo.go` beside the test pattern `pkg/**/*_test.go` is accepted"; in decision 5, say literal owned paths are checked with `matches`, and only globs and directories are checked for pattern intersection (a literal directory includes its descendants: `evidence.py:119-122`).

### 7 — minor — Decision 2: "beside the phase records" leaves the record's placement ambiguous, and every guard that must see it loops over `record["phases"]`

Pending-operation guards, accepted-evidence checks, reopen and suspend guards, task start/finish guards, and the CLI's own pending checks all iterate `record["phases"].values()` (`hooks.py:133, 138`; `engine.py:256, 304`; `handoff.py:625, 776`; `cli.py:391, 447`; `decisions.py:12`; `review_plan.py:91`). A record stored as a sibling key of `phases` is invisible to all of them; a record stored as `record["phases"]["test-checkpoint"]` is covered by all of them without change. Plan:27 says "beside the phase records, keyed `test-checkpoint`", which reads either way.

Smallest fix: say `record["phases"]["test-checkpoint"]`, not in `evidence.PHASES`, and have `engine.initialize` (`engine.py:35-44`) create it.

### 8 — minor — Build order step 1: the shared lifecycle fixture's implementation task owns a test file, so step 1's validator rejects it, and step 1 does not name the fixture change

The fixture's `cancel` task owns `["src/app.py", "tests/check.py"]` (`test_workflow_lifecycle.py:92-98`) while scope tests are `["tests"]`. Step 1's "Plan validation rejects implementation tasks that can own a test path" (plan:76) refuses it at breakdown close (`close.py:37-41` via `plan`), at task start (`handoff.py:647-651`), and in the hook (`hooks.py:161-166`), so every test reaching breakdown close through this fixture fails. Step 3's "Test fixtures that prepare and lock in breakdown are rewritten" (plan:78) is two commits later.

Smallest fix: in step 1, name the one-line fixture change (drop `tests/check.py` from the implementation task's `files`).

### 9 — minor — Decision 3: the surviving source-baseline check is assigned to no build step; in step 1 breakdown's existing check still refuses the allowance

Decision 3 says "plan validation and the source-baseline check accept changes to a test task's declared production files and still refuse undeclared ones" (plan:33). Step 1 changes plan validation only (plan:76); step 3 retires `stubs` (plan:78); no step builds the new source-baseline check. In step 1, breakdown still runs test tasks and `validate_sources` refuses any changed baseline source at `check-tests` and close (`test_preparation.py:243-259`), so a test task that uses the allowance during breakdown cannot close breakdown.

Smallest fix: in step 1, say the allowance is usable only in implement's writing-tests stage until step 3; in step 2, say the checkpoint is where undeclared production changes are refused, computed from the test runs' before/after fingerprints (`handoff.py:733, 892-896`) against each task's declared `files`.

### 10 — minor — Decision 11: refusing an old record at load denies every file write in the repository for every session until the unit is archived; the version bump should land with the first shape change

Every hook call loads every discovered unit (`hooks.py:236`); a `WorkflowError` from `store.load` (`store.py:118-121`) is caught and turned into a deny for `PreToolUse` (`hooks.py:362-367`). So one pre-amendment unit left under `.fbk/` blocks all Edit/Write calls project-wide, not just that unit. Also, step 2 adds the checkpoint key to the record shape while the version bump is in step 3 (plan:77-78): a record written by step-1 code and read by step-2 code fails with a `KeyError`, not the promised message.

Smallest fix: have the refusal message name the remedy (move the unit under `.fbk/archive/`, which `discover` skips: `store.py:152-160`), and bump the version in the step that first changes the record shape (step 2).

### 11 — minor — Decision 8: the review-only marker has no defined syntax, and "omitting one is a blocker" has no done-means line and no mechanical check

Breakdown coverage must read the marker to accept "only an implementation task" (plan:60), so the marker must be machine-readable; the plan does not say what it looks like. The implement review "must name each such requirement ... omitting one is a blocker": the review result schema has no field for it, and done-means (plan:86-95) has no item for an implement review result that omits a review-only requirement.

Smallest fix: define the marker (for example a fixed line under the requirement heading: `Checked by review: <reason>`), and add a done-means line: an implement review result that does not name every review-only requirement is refused.

### 12 — minor — Decision 4: whether the saved red output files are committed is unspecified

Only `.fbk/runtime/` is git-ignored (`cli.py:195`; `.fbk/.gitignore`). Files under `.fbk/<unit>/` enter any commit, and the done-means case requires output above 1 MiB (plan:89). Decision 6 settles the question for the saved test copies (plan:47); decision 4 does not for the output files.

Smallest fix: one clause in decision 4 saying the output folder is git-ignored and hook-protected like the copies folder, or committed deliberately.

### 13 — minor — Build order step 2 bundles the nonzero-red semantics with the checkpoint, and in the step-2 commit the still-live `check-tests` rejects a `nonzero` expectation

The nonzero change touches the plan validator (`test_preparation.py:206-225`), task finish (`handoff.py:905-913`), `check-tests` (`cli.py:417-424, 429`), the reviewer obligation sentence (`review.py:971`), and three guides; none of it depends on the checkpoint record. In step 2 as written, `check-tests` still forces the red check to 1 and compares each expectation's `exit_code` by equality, so a test task declaring `nonzero` fails the breakdown route that step 2 keeps alive.

Smallest fix: make nonzero-red its own commit before step 2 (including `check-tests`), so step 2 is only the checkpoint.

### 14 — minor — Build order step 5 is one commit for a parser, three close checks, the review-only exception, task-link anchors, task-context chains, three guides and the glossary

Each of these has its own tests and its own failure modes; one commit cannot be observed red-then-green in a way that isolates them. Smallest fix: split into 5a (section and link parser; design, spec and breakdown coverage checks; intent, design and spec guides; glossary) and 5b (review-only exception; requirement-anchored task links; chain sections in task context; breakdown and implementation guides).

### 15 — minor — Decision 7: "each design file has Design choices" is undefined for a design directory with files that carry no choices

Design is a directory (`evidence.py:169`), and a unit may keep a diagram or notes file there. Plan:50 can be read as "every file must have the section" (a new structural refusal) or "any file may". Smallest fix: say a design file without the section contributes no items and is not refused.

### 16 — minor — Decisions 1 and 5: during an outstanding unlock, whether a still-running implementation worker may keep writing its production files is unstated

Decision 10 says running implementation tasks "may finish" during an unlock (plan:67); step 1's hook rule for writing tests only says what a test task's worker may write (plan:76). Today's hook refuses non-test writes when there are no locks (`hooks.py:170-172`); with locks and an outstanding unlock it allows them. Smallest fix: say "a running implementation worker keeps writing within its task ownership; no new implementation task starts".

### 17 — minor — Decisions 5 and 6 assume tests live in files separate from production code; the plan calls only decision 3 language-agnostic

Rust unit tests conventionally live inside the production file (`#[cfg(test)] mod tests` in `src/foo.rs`). A scope whose `tests` pattern reaches those files makes every production file a locked test and every implementation task an owner of a test path. Smallest fix: one sentence in the spec or test-authoring guide (step 5 or step 2): scope `tests` patterns must not match production files; languages with in-file unit tests use separate test files for unit work.

### 18 — minor — Step 3: reopening breakdown clears checkpoint acceptance, but the checkpoint's generation and round budget reset are unstated

`engine.reopen` bumps the generation and resets `round_limit` to spent rounds plus three for each later phase (`engine.py:270-276`); the checkpoint record is outside that loop. Without the same treatment, a reopened unit's checkpoint reuses an old round's result (generation unchanged) or starts exhausted. Smallest fix: in decision 10 or step 3, say the checkpoint record is reset the way a later phase is.
