# Retrospective — Hook-Harvesting Remediation

## Timeline

- **Spec** — authored directly from the independent code review (`fbk-cr-hook-harvesting-remediation.md`, 25 findings); passed spec-gate.
- **Spec Review** — 2026-06-11. Council (Architecture, Quality, Security, Measurability) + independent test-reviewer. Result: **FAIL**; operator chose to revise the spec.
- **Spec revision** — 2026-06-12. All blocking and important findings folded into the spec; spec gate re-passed.
- **Spec Review (re-run)** — 2026-06-12. Council (Architecture, Quality, Security, discussion mode) + independent test-reviewer (three rounds). Result: **PASS** — 2 new blocking findings resolved by in-session spec revision; review gate pass.
- **Breakdown** — 2026-06-12. Two independent compiler teammates produced 31 tasks (18 test, 13 implementation) across 9 waves; one bounce-back resolved through the test-task owner; checkpoint-2 test review PASS (2 minors fixed); pre-lock test review accepted on a narrowed lock set; task-reviewer and breakdown gates pass.
- **Implementation** — 2026-06-12. All 31 tasks across 9 waves completed by a wave-based agent team (one fresh teammate per task); every wave passed verification with zero baseline regressions; two scope-revision escalations on one task, both resolved in-wave; final suite 401 passed / 0 failed; per-slice red/green ledger verified and written to completion notes.
- **Code Review** — 2026-06-12. Post-implementation review: two independent detection rounds, zero verified behavioral findings; final test-review accepted on all six checks; doc reconcile 3 advisory drift items + 2 notes; code-review gate pass.

## Key decisions

1. **No standalone threat model** (Spec Review). Every security-relevant fix maps to a threat/mitigation already in the existing feature threat model; a status note suffices. Operator-confirmed.
2. **Revise rather than accept** (Spec Review). The blocking findings are concrete, cheap spec-authoring fixes; the operator chose to re-open the spec and re-run the review rather than carry the risk into breakdown.
3. **Source validation is warn-but-write** (Spec revision, operator-confirmed 2026-06-12). The writer checks the source label against the registry; an unregistered label is written unchanged with a stderr warning. Rationale: after the subagent fix nothing reads the source label to compute a metric, so dropping an event over a label mismatch would recreate the silent-data-loss class this remediation kills; the wrong-but-registered mislabel the review actually found is caught only by per-producer tests pinning each exact source string, which the spec now requires.
4. **The pre-fix demonstration reference is the feature-branch tip, not the review's merge-base** (Spec revision). The merge-base the review suggested predates the capture package — tests run there fail on imports, demonstrating nothing. Verified directly; the spec names the branch commit at implementation start and a red-then-green capture procedure.
5. **The pre-lock lock set is the 18 test task files plus the one untouched pre-existing suite** (Breakdown). The reviewer's blocking findings showed two candidate files cannot be locked yet — the retention suite gains the spec-mandated concurrency guard and the chokepoint-integration suite gains the single-writer guards — so those two are deferred lock obligations for the implement stage, to be locked the moment their owning test tasks land.
6. **The gate-rate fixture conflict resolved via the pass route** (Breakdown). The strengthened real-producers test's code-review-gate dispatch was failing for missing artifacts, which would have dragged the pinned first-try rate to one-half; the fixture now writes the two artifacts the gate requires so the dispatch passes deterministically and the pinned rate stays exactly 1.0. A failing-dispatch fixture re-pinned to 0.50 was rejected as fragile (the failure reason could drift).
7. **The retention lock-scope fix takes the retention-side shape** (Breakdown). Re-reading the locked-spec set inside one event-writer lock scope deadlocks (same-process flock re-entry) and breaks an existing prune-check test; the interface contract's permitted alternative — the prune re-reads the lock directory under its own lock and unions with the caller's snapshot — is pinned instead. The guard test asserts only the observable contract, not the mechanism.
8. **The unimplemented rounds-to-quiet metric is removed from its contract, not computed** (Breakdown). It has no consumer, and writing it would mint exactly the dead-field failure class the dead round-count finding documents.
9. **Latent stale tests surfaced mid-implementation are rebuilt under explicit team-lead authorization, not silently fixed** (Implementation). The round-projection task twice hit pre-existing defects in the test file it had to turn green — a missing fixture import hidden by a skip guard, and an assertion encoding the old strip-the-list contract that the retirement list missed. Each was verified by the team lead against the source, authorized as a tightly-scoped task-file revision, counted against the escalation cap, and logged in the review log — preserving the no-silent-scope-expansion invariant while keeping the wave moving.

## Scope changes

- None to the feature scope. The review surfaced spec-accuracy and test-design gaps to fix in place, not scope additions.
- Breakdown recorded one shape deviation rather than a scope change: the retention slice is contract-preserving yet carries one new spec-mandated concurrency guard test, and three contract-evolving slices (stage attribution, gate rate, token boundary) genuinely retire nothing, so they run through the gate's legacy checks instead of the shaped path.
- Implementation added one file to one task's declared scope (the round-projection task gained the gate test file, import fix and one stale-assertion rebuild only) via two logged escalation-protocol scope revisions. No feature-scope change.

---

## Stage: Spec Review

**Perspectives invoked.** Architecture, Quality (testing strategy & impact), Security (threat modeling), Measurability — discussion mode, four council agents in parallel, plus an independent `test-reviewer` at checkpoint 1 with no access to the council discussion. Builder and Advocate were deliberately excluded: the pragmatism question (fold all 25 findings vs. stop at a tier) was already resolved in the spec's scoping, and scope was tightly fenced by explicit non-goals.

**Result:** FAIL. Review gate passes structurally; the semantic verdict is fail on unresolved blocking findings. **Iteration count:** 1 (spec revised 2026-06-12; re-review pending).

**Blocking findings (2 council + 6 independent test-reviewer, two pairs corroborating):**

1. *Highest-impact test filed against a phantom file.* The impacted-tests list names `test_capture_active_stage.py`, which does not exist, and `resolve_active_stage` — the function behind the two criticals — has zero current test coverage. Verified directly. (Council + test-reviewer, independently.)
2. *An existing real-producer seam test already carries the heading-only masking weakness.* `test_capture_e2e_seam.py` asserts only the metrics heading and provenance marker, never a metric value — the exact F-12 weakness — yet the spec presents the injection-seam guard as net-new and never folds in this existing test. Verified directly. (Council + test-reviewer, independently.)
3. *The subagent-count rewrite can still pass on the buggy code* unless it pins `source="hook_router"`.
4. *The bounded-read test as planned cannot fail on correctness alone* — both bounded and unbounded reads return the right level. The fixture must put invalid bytes in the first 256 and valid config later in the same line so the two implementations diverge. (The test-reviewer's sharpest finding; supersedes the council's wall-clock framing.)
5. *"Demonstrated to fail against pre-fix code" has no procedure* — no named pre-fix reference (the review names merge-base `4437a6c`) and no defined run/capture step.
6. *The stage-attribution slice's retired-tests entry names a pattern, not a concrete test function.*

**Important findings (council).** Gate-rate fix depends on the tier-3 stage-attribution fix (a tier-boundary stop ships it broken); the rework-boundary contract names `error_history` for a re-entry it doesn't hold; the shared-constant move risks an import cycle (`state → retro_injector → report → active_stage → state`); the atomic-write fix loses atomicity across filesystems unless the temp file is created in the target directory; the redaction split leaks free text at the default level unless it strips *nested* per-round severity; the source-validation criterion's either/or is unfalsifiable; and a cluster of measurability criteria assert "non-zero"/"below 1.0"/"not understated" where exact values are computable.

**Spec revisions required before re-review.** Rename/locate the resolver test home and correct the chokepoint filenames; fold the two existing seam tests into the impacted list and require their assertions be strengthened; pin `source="hook_router"` in the subagent rewrite; redesign the bounded-read fixture to force divergence; name the pre-fix reference and demonstration procedure; enumerate concrete retired tests; resolve the gate-rate/attribution tier coupling; reword the rework-boundary contract; name the constant's owning module and address the cycle; specify same-directory temp-then-rename; require nested redaction with a test fixture that carries a free-text severity string; resolve the source-validation enforcement decision; and pin exact expected metric/rate/count/token values.

**What worked.** Grounding every reviewer against the real source (`state.py`, `gate_check.py`, `install.sh`, the actual test files) rather than the spec's prose is what surfaced the phantom-file and masking-seam-test findings — the same "read the real source, not the prose" lesson this feature has produced at every stage. The independent test-reviewer, blind to the council, converged on the same two blocking findings and added the bounded-read divergence insight the council's wall-clock framing missed — evidence the dual-track (council + independent test-reviewer) review earns its cost on exactly this defect class.

**Process note for the pipeline.** This remediation exists because three release-blockers passed a green 359-test suite; the review found the remediation's *own* test plan re-encoding the same masking pattern (a net-new guard written alongside an unfixed weakened twin). The standing control the prior retrospective proposed — one end-to-end test per producer→store→consumer contract — is necessary but insufficient if a *second*, weakened test of the same seam is allowed to survive. The lesson: when adding a seam guard, the review must search for and fold in any existing test of that seam, not just add a new one.

---

## Stage: Spec Review (re-run, 2026-06-12)

**Perspectives invoked.** Architecture, Quality (testing strategy & impact), Security (threat modeling) — discussion mode, three council agents in parallel with one consensus round, plus the independent test-reviewer at checkpoint 1 (three rounds, fresh agent per round). Measurability was dropped from the re-run: the revised spec already pins exact fractions and counts throughout, which was the Measurability perspective's contribution last round.

**Result:** PASS. Review gate pass (Architecture, Quality, Security; no threat model document — operator-confirmed that the existing feature threat model covers every touched boundary). **Iteration count:** 2 for the stage overall (the 2026-06-11 fail, this pass).

**Blocking findings (2, unanimous council votes, both resolved by in-session revision):**

1. *The duplicate-gate-event escape hatch.* The spec allowed "remove the duplicate write… or document why both are needed" — but one gate dispatch currently yields two pipeline-command events (the chokepoint's with an outcome field, the gate's own without one), so the "documented as intended" branch arithmetically breaks the spec's own exact-fraction gate-rate criterion. Resolved: the gates' own writes are removed; the chokepoint's event is the single record per dispatch, with a one-dispatch-one-event assertion.
2. *The redaction denylist hole.* Round entries are copied verbatim from the untrusted round-log file, redaction is a key denylist, and no severity enum exists anywhere — so the planned recursion would let free text under an unknown key leak at the standard level while the planned guard fixture (known keys only) stayed green. Resolved: producer-side allowlist projection at the code-review gate; guard fixture extended to unknown-key and out-of-enum cases.

**The independent test-reviewer track.** Round 1 (FAIL) surfaced four valid under-specifications — un-pinned injection assertions, a divergence fixture that passes trivially if the out-of-bounds token equals the safe default, an ambiguous identity-vs-value shared-constant assertion, and unspecified rewritten migration-test bodies — plus one defect refuted on adjudication (a misread of the count function's `or`-chain semantics; verified against the code, the truthy production source short-circuits and the rebuilt test does fail red). Round 2 re-litigated already-diagnosed existing-test weaknesses but yielded two real residues (the migration file's skip guard; an explicit only-rebuilt-tests-go-red rule). Round 3: PASS, with five non-blocking fixture/assertion constraints recorded in the review document for breakdown to propagate.

**What worked.** The council consensus round converged unanimously in one exchange on both blocking severities and both default resolutions — evidence the independent-review-then-cross-share structure (rather than a joint first pass) produces genuinely independent corroboration. Adjudicating the test-reviewer's refuted defect against the actual code, rather than recording it as-is, kept a false constraint out of the spec while still salvaging its useful residue (stating red-run mechanics explicitly).

**Friction for the pipeline.**
- The test-reviewer needed re-framing between rounds: at checkpoint 1 on a *remediation* spec, diagnosed-and-planned weaknesses in existing tests are the strategy working, not findings — without that framing, round 2 spent most of its budget re-confirming the spec's own diagnosis. A remediation-aware framing note in the checkpoint-1 prompt would have gotten round 3's clean verdict one round earlier.
- The review-gate parser requires the literal category labels ("new tests needed", "existing tests impacted", "test infrastructure changes") inside the first `## Test…` section; paraphrased labels cost one gate round-trip.
- A stale council session checkpoint (40 days old, different task) triggered the council skill's compaction-recovery path and had to be recognized and cleaned manually; a staleness window in the recovery check would remove the manual step.

---

## Stage: Breakdown (2026-06-12)

**Compilation structure.** Two independent teammates with separated context: the test-task compiler received only the spec (no review, threat model, or design artifacts) plus the brownfield, test-authoring, and slice-shape rules; the implementation-task compiler received the spec and the finished test task files as artifacts. Both compiled codebase-grounded — every referenced production file, line anchor, envelope shape, and existing test was read before pinning. Output: 31 tasks (18 test, 13 implementation) in 9 waves, all 21 acceptance criteria covered.

**Wave structure and rationale.** Seven implementation tasks touch the report module — one per wave from 2 through 8, forced by the no-two-tasks-share-a-file-per-wave invariant. The real dependency chain threads through the same span: the gate-rate classifier needs the resolved-stage fix and the single-writer gate events first; the injection render needs the classifier and the rework boundary; the token-boundary fix needs the shared constant. Test tasks sit in waves 1–3 (staggered where two tasks rebuild tests in the same file), and the global verification task closes wave 9.

**The bounce-back loop worked.** The implementation compiler refused to compile against an internally inconsistent test instruction: the strengthened real-producers test pinned a first-try rate of exactly 1.0 while its own fixture's code-review-gate dispatch failed for missing artifacts (post-fix true value: 0.50). It emitted the bounce-back marker instead of guessing; the test-task owner amended the fixture (pass route, see Key decision 6); the marker was then cleared. Two further cross-compiler corrections: the retention lock shape (Key decision 7) and the spec's own divergence-fixture example, whose suggested filler bytes would have made the bounded and unbounded reads agree — the test task substitutes strip-transparent whitespace filler so the divergence is real.

**Reviews.** Checkpoint-2 test review (independent test-reviewer over all 18 test tasks): PASS with two minors, both fixed in place — the seam guard's completion gate now states the true first pre-fix failure (the duplicate-envelope sanity count, not the stub block), and the retention fixture pins its event type so a final exactly-one-lifecycle assertion cannot misfire. Pre-lock test review: initial verdict needs-revision on lock scope — two of three candidate pre-existing suites are extended by test tasks and cannot be locked yet; re-issued accepted on the narrowed set (Key decision 5). Hand-verified by the reviewer: all pinned fixture arithmetic, the identity (not value-equality) shared-constant guard, and the absence of owned-code mocking across all tasks.

**Gate iterations.** Task-reviewer gate failed twice on mechanical conventions before passing: the compilers wrote package-relative file paths where the gate resolves from the repo root, and the schema requires a non-empty test-task reference on every implementation task — including contract-preserving ones whose real gates are a pinned mypy baseline and the suite staying green; those two reference the final full-suite verification task, with the rationale recorded in the manifest. Breakdown gate: pass first run after the lock manifest landed.

**Friction for the pipeline.**
- The deterministic gates encode two conventions the compilation docs don't state: file paths resolve from the repo root, and `test_tasks` must be non-empty on every implementation task. Both cost a gate round-trip each; a sentence in the task-compilation guide would zero that.
- The shaped-slice gate path requires a non-empty retired-tests list on every contract-evolving task, but a remediation legitimately produces contract-evolving slices that retire nothing (no prior coverage existed — the absence is the defect). Those slices ride the legacy checks with an explanatory note; a shaped path that accepts an explicit empty-with-rationale retirement would be more honest.
- The skill's capability-entry prerequisite probe names a command (`precheck`) the installed scripts don't expose; the manual check (spec exists) is trivial, but the skill text and the installed surface have drifted.
- The pre-lock review's lock-scope finding — candidate lock files that test tasks must still extend — is structural for any remediation that adds guards to existing suites. The deferred-lock obligation (lock the file the moment its owning test task lands) now lives only in prose; a manifest field the implement stage reads would make it mechanical.

## Implementation (2026-06-12)

**Team shape.** Wave-based execution per the implementation guide: the orchestrating session as team lead (no task execution), one fresh teammate spawned per task (31 teammates total), Sonnet for 28 tasks and Haiku for 3 per the manifest's model routing. Baseline snapshot captured before Wave 1: 359/359 passing at the pre-fix commit (40ec021), which doubled as the red-run reference.

**Per-task metrics (factual).**
- 31/31 tasks complete; 0 parked, 0 superseded, 0 reassignments, 0 unresponsive-teammate timeouts.
- Escalations: 1 task (the round-projection implementation) used both of its 2 escalation attempts, as operator-authorized scope revisions rather than failures — (1) a missing `capture_fixtures` import in the wave-1 gate test file, hidden by the projection skip guard; (2) a stale `"rounds" not in data` assertion encoding the pre-fix contract, missed by the slice's retirement list. Both logged in the review log with root-cause classification. Every other task: 0 escalations, first-attempt completion.
- In-session retry count: 0 hook-rejection retries reported by any teammate.
- One readiness-check halt worked as designed: the round-projection teammate stopped and reported instead of silently expanding scope — the pause-on-scope-discrepancy protocol's intended behavior.

**Task sizing accuracy.** Every task's actual modified files matched its declared scope, with the one exception above (+1 test file added to the round-projection task by logged revision). No task touched an undeclared file; the per-wave `git diff` scope check was clean at all 9 waves.

**Model routing accuracy.** 3/3 Haiku tasks (subagent identity-field read, bounded config reads, decisions-log entry) succeeded without escalation — the bounded single-file routing held.

**Verification gate pass rates.** Per-wave verification: 9/9 waves passed on the first attempt; zero baseline regressions at every wave boundary. Test-compilation checks (waves with test tasks): clean every time. Expected reds tracked per wave: 25 after Wave 1, burned down to 0 after Wave 8 exactly on the planned schedule; zero skips remained after Wave 4. Final verification (Wave 9): full suite 401 passed / 0 failed / 0 collection errors; the per-slice red/green ledger cross-checked, with the five documented expected-green exceptions verified as test-fidelity corrections over already-correct production code; ledger at `hook-harvesting-remediation-tasks/completion-notes.md`.

**Wall-clock.** Waves ran 3–8 minutes each (12-way parallel test authoring in Wave 1 took ~6 minutes); end-to-end the implementation spanned one day with an operator pause between Waves 2 and 3. Each wave was committed at its checkpoint (8 commits, Wave 4 amended twice — see friction).

**Upstream traceability (factual).**
- Stage spec review: 2 iterations (fail 2026-06-11, pass 2026-06-12); 8 blocking findings in round 1 (all spec-revised), 2 in round 2 (resolved in-session).
- Stage breakdown: task-reviewer gate passed on the third run (two mechanical-convention failures), breakdown gate first run.
- Implementation consumed the breakdown cleanly: no bounce-backs to the spec, no task file was internally inconsistent, and the two pre-fix-commit-pinned red-run procedures the spec defined were executable exactly as written.

**Failure attribution (AI judgment).** No task failed verification, so attribution applies to the two scope-revision escalations:
- *Missing fixture import* — implementation error in the wave-1 test-authoring task, with a process-gap component: the test's skip guard meant pytest collection could not execute the name reference, so the wave-1 compilation gate was structurally blind to it. Any skip-guarded test authored against a not-yet-existing symbol has this blind spot.
- *Stale strip-the-list assertion* — compilation gap: the breakdown's retired-tests enumeration for the per-round slice listed the event-writer strip test but missed the gate-side test asserting the same old contract. The spec's own lesson ("when adding a seam guard, search for and fold in any existing test of that seam") applies one level down: when a slice flips a contract, enumerate every test asserting the old contract, not just the ones in the slice's primary files.

**Friction for the pipeline.**
- Teammate message ordering is not guaranteed: the round-projection teammate's revert-and-reapply straddled the team lead's wave commit, so the Wave-4 commit twice captured a mid-revert tree state and had to be amended after the dust settled. Wave checkpoints should confirm the reporting teammate is idle *and* its task's files are quiescent (`git diff` re-check immediately before `git add`) before committing.
- Two teammates' final summaries contained stale claims (a test reported red that the suite showed green) because they ran their last verification before a concurrent teammate's fix landed. The team lead's own full-suite re-verification caught both; worth keeping as a standing rule that the lead never records a wave on teammate-reported test results alone.
- The completion-notes location was unspecified by the task schema — red/green evidence lived in task.json summaries and the team lead's prompts had to point the final-verification task at them. A manifest field naming the evidence file from the start would remove the indirection.

## Code Review (2026-06-12)

**Mode.** Post-implementation review (non-interactive): two independent Detector rounds against the spec's 21 acceptance criteria, the failure-mode checklist, security targets, the five procedural audits, and structural targets; preset `behavioral-only`, threshold `minor`. Pre-review state: 401 tests green, mypy clean on touched lines.

**Findings summary.** Verified findings: **0**. Sightings: 4 across 2 rounds, all domain-filtered by the preset (none rejected on merit, 0 nits): one test-integrity major (the installer global-path test's redundant remove-call — routed to the final test-review, adjudicated acceptable documented residual debt with the merge-only companions guarding the strip), one fragile minor (unguarded `mv` in the installer's atomic write), two structural minors (constant-site exclusion comment; retention `capture_dir` derivation asymmetry). False-positive rate: n/a (no verified findings to dismiss). Rejection count: 0.

**Closing passes.** Quality scan: 2 substantive + 3 minor opportunities (`quality-scan.md`, scan-only). Final test-review: **accepted** on all six checks — all 13 retirements justified and replaced by stronger guards, hash-locked chokepoint suite intact (`test-review-final.md`). Doc reconcile: 3 drift items, all stale design-subdoc claims whose contract-file counterparts were corrected this cycle, + 2 benign notes (`doc-reconcile.md`). Code-review gate: **pass**, one non-blocking finding (the gate probes for the lock manifest at the feature root; breakdown wrote it under the `-tasks/` subdirectory).

**Detection source breakdown.** spec-ac 2, checklist 1, audit-pass 1, structural-target 0, linter 0, intent 0 (no intent register — spec ACs were the source of truth).

**Contrast with the prior cycle.** The review that spawned this remediation found 25 findings (3 release blockers) behind a green 359-test suite. The remediation implementation — built test-first from the reviewed spec with red-run demonstrations at the pinned pre-fix commit — surfaced zero behavioral findings across two independent adversarial detection rounds. Review report: `fbk-cr-hook-harvesting-remediation-impl.md`.
