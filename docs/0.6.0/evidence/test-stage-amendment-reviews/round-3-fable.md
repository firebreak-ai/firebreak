# Round 3 review of `docs/0.6.0/test-stage-amendment-plan.md` (Fable, 2026-10-22)

All paths are under ``. Workflow modules are in `assets/fbk-scripts/fbk/workflow/`; Python tests in `assets/fbk-scripts/tests/`. Plan line numbers refer to the revised plan as read today. Executed checks ran read-only against the workflow modules.

## Round-2 resolution

Astra N1-N6:

- **N1 Partly resolved.** Decision 4 (plan:46) and step 3 (plan:101) allow the output folder as a review source and exclude it from the hygiene scan; done-means has the oversize-snapshot case (plan:117). What remains: the baseline loader re-applies the same policy on the stored round tree (`review_baseline.py:90` calls `source_paths(stored, manifest)`), where the standalone branch of `_unit_source` (`review_context.py:299-307`) returns False for `.fbk/<unit>/<folder>/stdout.txt` (executed: False), so the implement review's comparison baseline would silently come back "unavailable"; no done-means line covers the implement review receiving the checkpoint snapshot. See new finding 3.
- **N2 Resolved.** Decision 3 records a writing-tests baseline and compares the checkpoint against it, not against task runs (plan:40); done-means Baseline covers relaunch and cancel-and-relaunch (plan:116).
- **N3 Resolved.** Decision 7 exempts files with an outstanding unlock from the boundary comparison (plan:63); decision 5 lets running implementation workers keep their ownership during an unlock (plan:56); done-means Unlock rework (plan:120).
- **N4 Partly resolved.** Decision 11 routes the rework through the approval's per-test expectation and task finish compares against it (plan:90); done-means has the pass-against-correct-code case (plan:120). What remains: task finish sees only command exit codes (`handoff.py:905-913`) and the plan forbids runner-output parsing, so "per named test" cannot be checked as written. See new finding 2.
- **N5 Resolved.** Decision 9 defines the three outcomes, including no test tasks with and without scoped tests (plan:80-83); done-means Review-only runs each to implementation close (plan:124).
- **N6 Resolved.** Decision 9 requires an assessment per review-only requirement keyed by anchor and refuses a result that omits one (plan:79); done-means Review-only (plan:124).

Fable 1-18:

1. **Resolved.** "Implementation close requires a current accepted checkpoint" and the baseline switch moved to step 4 (plan:102); step 3 says the checkpoint may run on breakdown-locked tests so both routes work (plan:101).
2. **Resolved.** Decision 2 defines the revision (accepted breakdown revision plus scoped test and region fingerprints, production excluded) and "current" (plan:29); step 3 lists `close._ready`, `evidence.subject`, `evidence.revision_inputs`/`decisions.binding`, `grant_target` (plan:101).
3. **Resolved.** Same as Astra N3.
4. **Resolved.** Approving an unlock clears the checkpoint's accepted evidence while keeping rounds, budget and generation (plan:90); done-means Unlock rework (plan:120).
5. **Resolved.** Decision 4 names a folder under the unit, allowed as a review source and excluded from the hygiene scan (plan:46); done-means covers color codes passing the scan (plan:117). The baseline-loading branch is Astra N1's remainder.
6. **Resolved.** Decision 5: literal owned files are checked against the test patterns as files; only folders and wildcards use overlap (plan:54); done-means Accepted ownership has the `pkg/foo.go` case (plan:114).
7. **Resolved.** `record["phases"]["test-checkpoint"]`, created at initialize, not in the phase list (plan:28).
8. **Resolved.** Step 1 names the fixture change (plan:99).
9. **Resolved.** Step 1 limits the allowance to implement until step 4 (plan:99); decision 3 puts the undeclared-production-change refusal at the checkpoint against the baseline (plan:40).
10. **Resolved.** Decision 12 names the archive remedy (plan:93); the version bump is in step 3, the first step that changes the record shape (plan:101).
11. **Resolved.** Decision 9 fixes the marker (`Checked by review: <reason>`) and the refusal of an omitted assessment (plan:77, 79); done-means Review-only (plan:124).
12. **Resolved.** Decision 4 makes the output folder git-ignored and hook-protected (plan:46). The mechanism for existing projects is new finding 11.
13. **Resolved.** Non-zero red is its own step 2, including `check-tests` (plan:100).
14. **Resolved.** Split into steps 7 and 8 (plan:105-106). Step 8 still bundles two unrelated changes; see new finding 9.
15. **Resolved.** Decision 8: a design file without the section contributes no items and is not refused (plan:67).
16. **Resolved.** Decision 5: a running implementation worker keeps writing within its ownership; no new implementation task starts (plan:56).
17. **Resolved** by decision 6 (operator's answer).
18. **Resolved.** Decision 11 resets the checkpoint's generation and budget the way a later phase's are reset (plan:88).

Totals: 22 resolved, 2 partly resolved (Astra N1, Astra N4), 0 unresolved.

## New findings

Three major, no blockers. Twelve minor.

### 1 — major — Decisions 3, 5 and 11: "untouched scoped tests must pass" contradicts the carried-forward red at every re-run checkpoint, and the writing-tests baseline's lifetime decides which way the re-run breaks

Decision 5 says "tests that differ from the writing-tests baseline must be red ...; untouched scoped tests must pass" (plan:55), decision 4 has the reviewer confirm "every untouched scoped test passed" (plan:47), and done-means Red rejects a checkpoint where "an untouched test fails" (plan:117). Decision 11 says that at the re-run checkpoint "tests unchanged since the previous accepted checkpoint keep its red evidence" and "correct code is never undone to recreate red" (plan:89). Take the done-means Unlock rework case (plan:120): the checkpoint passed, implementation tasks built part of the behavior, one test is unlocked and reworked, the checkpoint re-runs. The other locked tests for behavior not yet built are still red and unchanged. Under decision 5 they are untouched and must pass, so the re-run is refused; under decision 11 they keep their red. The plan does not say which rule wins. The baseline's lifetime makes it worse: decision 3 records it "when writing tests begins" (plan:40) and refuses "a production change outside every test task's declared files". If the baseline is kept from the first implement entry, every finished implementation task is an undeclared production change at the re-run, so the re-run is refused on that ground instead (`handoff.py:713-734` shows each task run snapshots only its own files, so nothing else records the authorized changes). If the baseline is re-recorded at the unlock, the untouched-must-pass rule bites as above. The same holds for a reopen of breakdown after code exists (done-means Reopen, plan:121). Today's code re-takes the breakdown baseline on every entry (`test_preparation.py:80-86`) and the lineage history carries authorized production hashes forward (`test_preparation.py:47-64`), which is the mechanism the amendment retires.

Smallest fix: in decision 3, say the baseline is re-recorded at every entry into writing tests (first implement entry, unlock approval, return after a reopen) and the production-change check compares against the latest. In decision 5, change "untouched scoped tests must pass" to "untouched scoped tests must pass, or be unchanged since the previous accepted checkpoint whose saved output shows them failing for the right reason". Mirror the sentence in decision 4's reviewer obligation and in the Red done-means line, and add to Unlock rework: "with other locked tests for unbuilt behavior still red and the built code untouched".

### 2 — major — Decision 11: task finish cannot compare "those tests' results with the approval's expectation" per test, because Firebreak sees only command exit codes and the plan forbids parsing runner output

The approval "states, per named test, whether its corrected form is expected to fail ... or pass", and the rework task's "finish compares those tests' results with the approval's expectation" (plan:90). A named test is a locked path, so a file (`engine.py:161` requires `--tests` to be existing locked paths). Task finish compares each check command's exit code with the task's `check_expectations` by `argv` (`handoff.py:905-913`); it has no per-test results, and decision 6 and decision 4 keep Firebreak language-agnostic ("never by parsing a language", plan:59; "mechanically, a red check exits non-zero", plan:45). When the approval names two files with different expectations and the rework task's one command runs both, or the command also runs still-red tests for unbuilt behavior, no exit code satisfies "per test". Done-means Unlock rework (plan:120) exercises only the single-file case, which happens to work at command level, so the suite would pass with an unimplementable rule left in the decision.

Smallest fix: in decision 11, state the comparison at command level: for the rework task's checks, the approval's expectation replaces the task's own expectation; a command whose covered named tests are all expected to pass must exit zero, any other must exit non-zero; the lead scopes the rework task's commands to the named tests; per-test judgment stays with the checkpoint reviewer reading the saved output. Add the mixed case (two named files, one expected to pass and one to fail) to done-means.

### 3 — major — Steps 3 and 4: the implement review's comparison baseline silently reports "unavailable" when the checkpoint snapshot is loaded, and nothing in done-means proves the implement review receives it

Step 4 makes "the checkpoint snapshot ... the implement review baseline" (plan:102; decision 2, plan:33). The checkpoint's required files include the saved output folder (plan:46), so its accepted snapshot manifest contains `.fbk/<unit>/<folder>/stdout.txt`. When the implement review loads that baseline, `review_baseline._bodies` re-applies the source policy to the stored round tree (`review_baseline.py:90`), and on a tree without `state.json` `_unit_source` takes its standalone branch (`review_context.py:299-307`), which admits only `prd.md`, `spec.md`, `scope.json`, `tasks.json`, `design/` and `decisions/`. Executed today: `_unit_source(<dir without state.json>, ".fbk/feature/checkpoint-output/stdout.txt")` returns False, so `source_paths` raises, `_comparison` catches it and returns `status: unavailable` (`review_baseline.py:55-56`), and the reviewer is told no comparison tree exists. Step 3 names "allowed as a review source" without naming both branches of `_unit_source`, and the done-means Checkpoint and Review-only lines (plan:118, 124) never check that the implement review's `comparison_baseline` is the checkpoint snapshot.

Smallest fix: in step 3, name both branches of `_unit_source` (live root and stored snapshot) for the output folder; in done-means Checkpoint, add "the implement review's comparison baseline is the accepted checkpoint snapshot, including the saved output".

### 4 — minor — Decision 4 / step 3: the existing check runner stops at the first failing command and the close refuses any non-zero exit; the checkpoint needs its own runner, and done-means never checks that later declared checks still run

`review.verify` breaks out of the loop on the first non-zero exit (`review.py:315-316`), and `_close_phase` runs commands only for implement and refuses on any non-zero (`close.py:142, 154-160`). The checkpoint expects the declared whole-unit checks to fail, and decision 4 needs every one of them run to completion so the reviewer can confirm "every scoped test ran" (plan:46-47). Step 3's site list (plan:101) omits the runner, and done-means Red (plan:117) has no case with two declared checks where the first is red.

Smallest fix: name `review.verify` and the close's verification block in step 3 as sites the checkpoint replaces (run every declared check, never stop early, never refuse on exit code); add to done-means Red: "with two declared checks and the first red, the second's complete output is saved too".

### 5 — minor — Decision 6 / step 6: a unit whose tests are all in-file cannot declare its scope, because `scope.json` refuses unknown fields and feature scope requires a nonempty `tests` list

`evidence.scope` rejects any field outside sources, tests, checks, docs, context (`evidence.py:23-31`; executed: a `regions` field raises "remove unknown fields"), and `structural` refuses a feature whose `tests` is empty at spec, breakdown and implement close (`evidence.py:246-253`; executed: "Feature scope.json must declare sources, tests, and executable checks"). Step 6 says "Region declarations in the scope" (plan:104) but not that the nonempty-tests rule becomes "tests patterns or region declarations". Done-means Regions (plan:122) uses one Rust-shaped file and never closes spec on a regions-only scope.

Smallest fix: in step 6, say feature scope needs test patterns or region declarations, and add "a regions-only scope closes spec" to done-means Regions.

### 6 — minor — Decision 6: what the write hook does when it cannot compute the file "as it would be after an edit" is unstated

The hook sees `Edit` (`old_string`, `new_string`, `replace_all`), `Write` (full content) and `NotebookEdit` payloads (`hooks.py:315-320`). For `Edit` the after-state exists only when `old_string` occurs exactly once (or `replace_all`); the host may also apply its own normalization before writing, so the hook's simulation can differ from the written file. For `NotebookEdit` the file is JSON cells. Decision 6 (plan:60) and done-means Regions (plan:122) cover only the clean case.

Smallest fix: one sentence in decision 6: a region-bearing or declared production file whose after-state the hook cannot compute is refused, and the task-boundary comparison (decision 7) is the backstop for any simulation mismatch.

### 7 — minor — Decision 4: "a test absent from the output is a blocker" assumes the declared checks print every test's name, which depends on runner flags the spec never constrains

`pytest -q` prints dots, `go test` without `-v` prints only package lines, `cargo test --quiet` and `jest --silent` suppress names. With such a check, the reviewer cannot confirm "every scoped test ran" (plan:47) and must block every checkpoint. The spec guide's scope section (`assets/fbk-docs/workflow/spec.md`, "Scope and verification") says nothing about output verbosity, and step 3's guide changes (plan:101) address only the reviewer.

Smallest fix: in step 3, add one sentence to the spec guide: declared whole-unit checks must name each test in their output (for example `pytest -v`, `go test -v`), and the per-language notes in the test-authoring guide give the flag.

### 8 — minor — Steps 7 and 8: breakdown coverage is built one step before the task links it counts, and the fixture rewrite that "a task with no requirement link" forces is unnamed

Step 7 builds "coverage checks at design, spec, and breakdown close" (plan:105), but a requirement is "covered by at least one implementation task and ... one test task" only through task links, which step 8 introduces (plan:106). In the step-7 commit the breakdown check is either vacuous (no requirements) or refuses every unit that has a Requirements section. Separately, once step 8 lands, every fixture `tasks.json` fails breakdown close: 12 test files write a `tasks.json` and 9 use file-level `acceptance_refs` without anchors (for example `test_workflow_lifecycle.py:84-103`), and their `prd.md`/`spec.md` are one-line strings with no Commitments or Requirements section (`test_workflow_lifecycle.py:66-71`). Step 8 names no fixture change, unlike steps 1 and 4.

Smallest fix: move breakdown coverage from step 7 to step 8, and in step 8 name the shared fixture change (a Commitments heading with one item, a Requirements heading with one item, anchored task links).

### 9 — minor — Step 8 bundles the three test outcomes with task-context traceability; neither can be observed red-then-green alone

Outcomes 2 and 3 of decision 9 change stage derivation, the hook, the checkpoint (preservation mode) and implementation close (checkpoint not required); task-context chain sections and the packet refusal change `task_packet`. These have no shared code and separate done-means lines (plan:123, 124).

Smallest fix: split into 8a (requirement-anchored task links, chain sections, packet refusal) and 8b (review-only marker, breakdown coverage rule, three outcomes, implement review assessment).

### 10 — minor — Decision 9 / step 8: the per-requirement assessment changes the review result shape at four sites step 8 does not name

The result shape is exactly `{"summary","findings"}` (`review.py:61-66`; schema `additionalProperties: False`, `review.py:28-57`); `council.adjudicate` builds the final review in the same shape (`council.py:283, 317-321`), the second reader is validated with `validate_single` (`review.py:1219`), and every enforced rule on a reviewer response is rendered from the constraint registry (`constraints.py`; its two tests fail on an unregistered rejection site). A refusal of an omitted assessment (plan:79) touches all four.

Smallest fix: in step 8, name the schema, `adjudicate`, the second-reader validation and the registry entry.

### 11 — minor — Decisions 4 and 7: "git-ignored" has no mechanism for projects that already have `.fbk/.gitignore`

`workflow-init` writes `.fbk/.gitignore` (`runtime/`) only when the file is absent (`cli.py:195`). Every initialized project, including this repository's own `.fbk/`, keeps its existing file, so a rule added there by step 3 or 5 never reaches them, and the saved output and locked copies are committed. Steps 3 and 5 (plan:101, 103) say "git-ignored" without saying how.

Smallest fix: have the command that creates each folder write a `.gitignore` containing `*` inside it.

### 12 — minor — Decision 2: whether a checkpoint pass needs a phase observation is undecided, and reusing the close path answers it by accident

If the checkpoint commits through `_close_phase`, it emits a `closed` event (`close.py:306`); `pending_phases` then lists `test-checkpoint` (`retrospective.py:33-49`) and `require_phase_observations` refuses implementation close, phase entry and the Stop hook until one is recorded (`close.py:25`, `engine.py:213`, `hooks.py:322-332`). `record_observation` would accept it, since `detection_phase` validates against `record["phases"]` keys (`retrospective.py:410-414`). Each unlock re-run would add another. Step 3 lists "retrospective" (plan:101) without this decision.

Smallest fix: one sentence in decision 2: a checkpoint acceptance does or does not require a phase observation; if not, it records its own event kind, not `closed`.

### 13 — minor — Decisions 10 and 11: after a reopen, test tasks for behavior already built cannot complete against their `nonzero` expectation

Re-entering breakdown clears `task_runs` (`test_preparation.py:87-95`, kept by decision 10, plan:85), so every test task runs again in implement. A test task whose tests already pass exits 0 against its `nonzero` expectation and is left needing attention (`handoff.py:906-913`), so the unit never reaches "ready for checkpoint". Today's lineage test avoids this by editing the expectation to 0 in the reopened breakdown (`test_preparation_lineage.py:49`). Decision 11 (plan:89) and done-means Reopen (plan:121) say unchanged tests carry their red but not how their test tasks complete.

Smallest fix: in decision 11, say that in a reopened breakdown a test task whose tests already pass declares exit 0 and the breakdown reviewer checks it; add that case to done-means Reopen.

### 14 — minor — Step 1: "refuses a test task once the tests are locked" is the wrong gate during an unlock, which step 1 already supports

Step 1 (plan:99) gates task start on "locked", but decision 1 (plan:22) derives writing tests while "a locked test has an approved unlock outstanding", and `approve unlock-test` plus `lock-tests` in implement exist today (`engine.py:153, 161`; `cli.py:390`). A test task reworking an unlocked test must start while locks are non-empty. Done-means Refused orderings ("a test task after it", plan:113) invites the literal reading.

Smallest fix: in step 1 and the done-means line, gate on the derived stage (writing code) rather than on locks being present.

### 15 — minor — Decision 8: "the remedy is to split the task" does not shrink a chain that belongs to one requirement

The packet already carries 5,620 characters of fixed guidance for a test task (executed: `repository-grounding.md` plus `test-authoring.md` as JSON) under the 16,000 limit (`handoff.py:601-604`). A single requirement's chain (its section, its design choices' sections, their commitments' sections) travels whole with any task that links it, so splitting the task leaves the same chain in each half (plan:74).

Smallest fix: say the remedy is fewer linked requirements per task or shorter item sections, and have the refusal name the chain's size per requirement.
