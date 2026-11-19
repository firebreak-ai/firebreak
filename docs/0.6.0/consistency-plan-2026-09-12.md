# Consistency plan, 2026-09-12

Branch: `develop/0.6.0-astra`. Source: the first complete live unit on this branch (the task-tracker CLI under `test-results/live-install/`), its 36 recorded observations, and the validator-versus-prompt audit run the same day. Written 2026-09-12.

## Objective

Make the managed workflow behave the same way every time before any cost or scope optimization. A unit should fail only on its artifact. Every failure the harness itself causes is a defect in this plan's scope. Review-scope and amendment cost belong to the slice-orchestration plan recorded in the firebreak wiki (`review-slice-orchestration-plan`) and are out of scope here.

## Rules this plan applies

1. **A deterministic check may test harness-supplied data or artifact structure at any project scale.** It may not embed a project-scale assumption or a judgment call. Magnitude limits are config-settable safety nets whose breach is a failed attempt; the one exception is the managed round clock (`review_round_timeout`), whose exhaustion still pauses for human help.
2. **Every enforced constraint is stated in the prompt, generated from the data the validator reads.** The unstated-rule class caused three of the five harness failures in the unit.
3. **An honest negative from a model is a verdict, never a protocol failure.** Incomplete context, refused checks, exhausted questions, and verifier rejections are recorded and carried, not punished.
4. **A judgment that is neither accept nor reject gets a recorded disposition.** The unit lost a spec acceptance to a suggestion nobody dispositioned.

## Shipped today, uncommitted

Twelve dated entries in `decisions-log.md` record the harness fixes and audit batches 1 to 3. Suite: 674 passed, one pre-existing failure in the code-review pipeline test, installer suite green. The installed copy needs a reinstall to pick these up. Nothing is committed.

## Decisions taken 2026-09-12

- Accepted suggestions require a recorded disposition. The process asks the operator, who dispositions one at a time or in semantic groups. The agent proposes groupings and records the operator's words as the source, through the existing decision-record mechanism.
- A suggestion whose remedy is a test must be dispositioned before breakdown locks the suite. No later phase can add a test.
- Documentation tasks must execute at least one documented command as a check. This is authoring guidance plus a breakdown-review obligation, not a runtime gate.
- The breakdown guide's red-check example changes to match the runtime: the red check is one of the declared scope checks.

## Batch 4: runtime defects, no decisions needed

| Item | Defect observed | Change | Deterministic check | Test |
| --- | --- | --- | --- | --- |
| Breakdown re-entry stubs | Re-entering breakdown after the first round snapshots the stubs that round created into the source baseline, so the same plan is refused with "a stub cannot overwrite an existing source file" | On re-entry, stubs created by completed test assignments (recorded in `task_runs` with stage tests and status completed) are excluded from the pre-existing check and carried as authorized stubs | Baseline excludes recorded stubs; unchanged plan re-enters cleanly | Close breakdown once with a stub, reopen spec, re-enter breakdown, task-start succeeds |
| Review time limit | `review_timeout` default 9999 s; breach pauses for human help | Default 1200 s; breach is an ordinary failed attempt with diagnostics; value stated in the prompt from config | No `budget_exhausted` marker on a timeout | Timeout records a failed round and the next close runs again |
| Clean-round provenance | A council with zero candidates skips challenge; a clean verdict and a challenged verdict are recorded identically | Round result carries `challenge` and `adjudication` with the stage's outcome (`ran`, `skipped-no-candidates`, `not-configured`, `incomplete`, `failed`, `not-reached`); status shows them | Fields present once a stage's outcome is known; a round that stops before candidates exist carries an error and neither field | Both shapes asserted |
| Changed-files window | Task-finish rejects a file edited before relaunch with a message that does not name the window | Message names the task-start time and says edits before it are declared as nothing; guide says the same | Unchanged rule | Message asserted |
| Assignment invalidation granularity | Editing one task's check invalidated three unrelated test assignments | First, a test proving or disproving whole-file binding. If proven: bind assignment evidence to the task's own entry, its acceptance refs, input refs, and consumed files | Unrelated task edit leaves an assignment valid | Edit task B, task A's assignment stays valid |
| Red-check guide | Guide example is a per-file command the runtime rejects | Example becomes a declared scope check; the focused-commands sentence excludes the red check | None | Doc-only |

## Batch 5: process gaps, decisions taken above

| Item | Change | Deterministic check | Test |
| --- | --- | --- | --- |
| Suggestion disposition | At phase entry, the continuation packet lists undispositioned accepted suggestions from prior phases, grouped by the agent semantically. The agent asks the operator and records each disposition (fix now, defer with owner, decline) with the operator's words as a decision source. A new `disposition-record` command, or `decision-record` with a `disposition` field, stores it against the finding id | Close refuses while any accepted suggestion from a prior phase is undispositioned; the refusal and the continuation packet name them, and status counts them | Undispositioned suggestion blocks close; recorded one unblocks; grouped record covers several ids |
| Test-remedy suggestions before lock | The breakdown reviewer tags suggestions whose remedy is a test (`remedy: test`); `lock-tests` refuses while one is undispositioned | Deterministic on the tag and the disposition record | Tagged suggestion blocks lock; disposition unblocks |
| Documentation task checks | Breakdown guide: a documentation task's `check_expectations` includes at least one command from the documented usage, executed against the finished program. Breakdown reviewer obligations name it | None (guidance and review obligation) | Prompt assertion on the obligation text |
| Stated exhausted-review hand-off at close | The close-time raise still uses fixed text; consult the suspend note there too | Same rule as status | Existing note-after test extended to the close path |

## Standing practice: constraint registry

Every validator constraint on model output is registered once with its prompt sentence. A test walks the registry and asserts each entry has both a validator reference and a prompt sentence present in the assembled prompt. New constraints cannot land without a stated sentence. This turns today's audit from a one-off into a suite check. Implement after batch 4; it touches prompt assembly and should not race the batches.

Agreed 2026-09-12: a rule the agent is held to is a rule the agent is told, and the telling is generated from the registry, never hand-maintained. Design choices:

- Register per rule, render grouped. One entry per enforced rule keeps the test precise; rendering groups related entries (for example the four authorization conditions) so the prompt stays readable.
- Render as a structured section of the packet next to `required_files`, not as prose sentences in a paragraph. The managed instruction block is already a wall of text; structured entries are denser and mechanically checkable, and match how the packet presents everything else.
- Seed from the 2026-09-12 audit inventory (about twenty entries across the review, context, council, investigation, and verifier contracts). Most already have sentences; the work is moving them into entries and pointing the existing tests at the list.
- Second test: every rejection site inside a parse-and-validate function must carry a registry reference, so a new rule cannot land without an entry. Host-side JSON schema constraints are covered by the existing schema walker, not by annotation.

## Status 2026-09-12, end of day

Batches 4 and 5 and the constraint registry are implemented in the working tree, uncommitted. Suite: 735 passed, one pre-existing failure in the code-review pipeline test, installer suite green. Seventeen dated decision-log entries for the day. The installed copy was refreshed after batch 4 and the registry; batch 5 needs one more reinstall. The acceptance test for this plan is the next live unit's retrospective: zero rounds lost to harness failures.

## Sequencing

1. Batch 4, two subagents by file ownership, then reinstall.
2. Constraint registry.
3. Batch 5, two subagents: disposition mechanism and lock gate first, guidance second.
4. Second live unit on the reinstalled copy. Its retrospective is the acceptance test for this plan: zero rounds lost to harness failures.

## Out of scope, recorded elsewhere

Amendment route and review effort scaled to the changed region, one-blocker-per-round yield, spec reviewer scope on a mid-breakdown reopen, and a first-class way to read a failed round's retained output. All four are review-scope questions and belong to the slice-orchestration plan.
