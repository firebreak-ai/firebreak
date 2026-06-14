# Spec Review — Hook-Harvesting Remediation (re-run, 2026-06-12)

Perspectives: Architecture, Quality, Security

**Spec:** `ai-docs/hook-harvesting-remediation/hook-harvesting-remediation-spec.md`
**Source of truth for the defects:** `ai-docs/hook-harvesting/fbk-cr-hook-harvesting-remediation.md` (findings F-01…F-25)
**Prior-stage gate:** spec-gate `pass` (0 injection warnings)
**Date:** 2026-06-12
**Council session:** council-20260612-033027 (discussion mode: Architect, Guardian, Security)
**Overall result: PASS** — 2 blocking findings resolved by spec revision (operator-confirmed), 8 important findings applied, test strategy review pass after two revision rounds. Details in Resolution status at the end of this document.

## Summary

This re-run reviewed the revised spec. The revisions from the previous review held up under verification: the pre-fix demonstration reference is now the feature-branch tip (not the import-failing merge-base), the existing real-producer seam tests are folded in as strengthened rather than left as weakened twins, the warn-but-write source-validation decision is recorded with its rationale, and the import-cycle justification for homing the shared non-active-state constant in the state engine was confirmed true against the actual imports (the state engine does import the capture package at the top level; the lazy import inside the injector is the only thing keeping the alternative placement from failing at module load today). All sixteen cited existing tests exist at their cited paths and names. The contract-drift check is clean: all fourteen contracts are spec-originated, as the remediation's design page declares.

Two findings are **blocking**, by unanimous council vote, and both are instances of the failure class this remediation exists to eliminate — a contract left open or an invariant the planned guard test cannot see broken:

1. The spec leaves the duplicate gate event as an either/or ("remove the duplicate write… or document why both are needed"). The escape hatch is arithmetically incompatible with the spec's own exact-fraction gate-rate criterion: today one gate dispatch produces two pipeline-command events (the chokepoint's, carrying an outcome field, and the gate's own, carrying a result field with no outcome), so if both survive, every gate run double-counts and the gate's own event classifies as a failure.
2. The redaction recursion, as specced, cannot meet its own no-leak invariant. The redaction model is a key denylist, but per-round entries are copied verbatim from the round-log file — the input the project threat model designates untrusted — with no key restriction and no severity enum validated anywhere in the code. Once the rounds container stops being wholesale-stripped, free text under any unknown key passes through at the standard level, and the planned guard test passes anyway if its fixture only uses known keys.

Both blocking findings are cheap spec-text edits; the council's consensus resolutions are recorded below.

## Findings

### Architectural soundness

**1. The duplicate-gate-event escape hatch is incompatible with the gate-rate criterion** — `blocking`
Category: Architectural soundness.
The module touch policy and the gate-source acceptance criterion allow "remove the duplicate `PIPELINE_COMMAND` write… or document why both are needed." Today a single spec-gate run dispatched through `fbk.py` produces two `PIPELINE_COMMAND` events: the chokepoint's (`fbk/capture/chokepoint.py:137-145`, with `data["outcome"]`) and the gate's own (`fbk/gates/spec.py:314-322` and `342-350`, `fbk/gates/task_reviewer.py:347-359`, with `data["result"]` and no outcome key). The new rate classifier matches command names and reads outcomes — if both events survive, every gate run double-counts as an attempt and the gate's own event classifies as a fail, breaking the pinned exact fraction (one fail-then-pass beside one first-try pass must yield exactly 1/2). One dispatch must yield exactly one classifiable gate-outcome event.
**Resolution (council consensus, 3–0):** delete the "documented as intended" option from the spec; remove the gates' own writes and make the chokepoint's event the record. The chokepoint exists to be the single recording point per dispatch; its event already captures the gate's full JSON stdout in the output field, so the richer gate payload (such as injection-warning counts) is retained unparsed and can be promoted to its own event type if a consumer ever appears. The source-attribution slice and the source registry shrink accordingly, and the one-dispatch-one-event invariant becomes directly assertable. The alternative — keeping the gates' writes as the classifier's source — would create a new two-module agreement (which command names belong to which producer) of exactly the parallel-literal kind the spec's shared-constant fix exists to eliminate.

**2. Two gate-envelope test classes are callers of the changed write path but absent from the impacted-tests list** — `important`
Category: Architectural soundness.
`tests/test_gates_spec.py:352-405` and `tests/test_gates_task_reviewer.py:393-496` directly assert the gates' own envelope writes, invoking each gate's entry point directly rather than through the chokepoint. Under the consensus resolution (gates' writes removed) these tests find zero envelopes and fail; under any resolution their assertions change. The spec's "Existing tests impacted" section names neither file. Resolution: add both files to the impacted list under the source-attribution slice, with their rebuilt assertions targeting whatever the resolved single producer writes.

**3. The spec contradicts itself on whether the state engine is modified** — `important`
Category: Architectural soundness.
The Dependencies section says the state engine is "read, not modified," while the module touch policy and the shared-state-set contract extend it with the new constant. A breakdown agent treating the dependency list as a touch boundary will either refuse to edit the file or home the constant elsewhere — the exact placement the spec's import-cycle rationale forbids. Resolution: correct the Dependencies entry to "extended with one pure constant; no behavioral change."

**4. The handoff-events promise is stronger than the design can keep** — `important`
Category: Architectural soundness.
The user-facing behavior section says events during inter-stage handoffs "are not silently dropped." After the resolver fix they are correctly stamped as no-stage — but they appear in no report row (the report renders only per-stage rows, and the non-goals forbid new rows), so they go from "misfiled" to "correctly stamped, still invisible." More consequentially, the gate-rate classifier filters by stage, so any gate dispatched while the state machine sits at a checkpoint boundary silently vanishes from the rates — the same silent-loss class this remediation targets. Resolution: reword the behavior bullet to "correctly stamped as no-stage," and state the assumption the design depends on (gates always run while their owning working stage is active) so the seam tests can pin it and the next person who moves a gate invocation across a transition boundary sees the constraint.

**5. Integration points verified; installer path note** — `informational`
Category: Architectural soundness.
All claimed integration points exist where the spec says: the sentinel constant at `fbk/capture/gate_check.py:44` (checked at line 193), no sentinel reference anywhere in the installer (the install gap is real), and the installer's current non-atomic copy at `installer/install.sh:369` from a temp file that defaults to `/tmp` — confirming the spec's same-directory-temp note is load-bearing. The installer lives at the repo root (`installer/install.sh`), not inside the scripts package; breakdown tasks should use the repo-root path. Every line number cited in the module touch policy matches reality. The caller-grep over the changed symbols found no caller the spec fails to enumerate beyond the two test classes in finding 2: the hardcoded terminal-states tuple has one reader (its own module), the dead round-count field has no reader anywhere, the chokepoint's `None` returns have one production caller (`fbk.py:43-44`) that already normalizes, and the stage-summary stub's sole caller is the injector, whose call shape matches the planned signature.

**6. The original design's stage-summary contract names a consumer that does not exist** — `informational`
Category: Architectural soundness.
The original design says the report command "reuses `stage_summary` for the full table"; in code, the injector is its only caller and the remediation keeps two parallel render paths over the same data (a controlled duplication the softened contract wording acknowledges). Resolution: correct the consumed-by line in the original design's contract during the documentation pass, so the duplication doesn't read as a defect to the next reviewer.

**7. Contract drift check** — `informational`
Category: Architectural soundness.
All fourteen spec-originated contracts are present and sequentially numbered with no design references, consistent with the remediation design page. Three places where the spec's "does not change the original design contracts" claim is not quite true and the documentation-impact section should own the edits: the gate-source work registers new sources while the original envelope contract enumerates a closed set of four; the cleanup criterion allows removing the rounds-to-quiet metric from the code-review round-log contract; and the same criterion allows rewording the chokepoint contract's "summarized at standard" promise.

### Quality: testing strategy and impact

**8. The zero-coverage claim for the stage resolver is overstated, and the router tests it overlooks are missing from the impacted list** — `important`
Category: Quality: testing strategy and impact.
No test references the resolver directly — that half is confirmed. But two router integration tests (`tests/test_capture_hook_router.py:270` and `:303`) assert the resolver's null-stage output through the real router for the parked and no-state-file cases — exactly the one terminal state the buggy hardcoded tuple gets right, which is why the suite stayed green. Resolution: qualify the spec's claim to "no direct coverage," and add the router test file to "Existing tests impacted" for the stage-attribution slice, since the shared-constant change alters stage stamping on the path those tests exercise.

**9. The end-to-end seam test's choreography breaks under the resolver fix** — `important`
Category: Quality: testing strategy and impact.
The two-source-cycle seam test transitions the run to a checkpoint state and then fires its router event. Under current buggy code that event is stamped with the checkpoint state's name; after the resolver fix it resolves to no stage and vanishes from the report table the test asserts on — so the strengthened test would fail for a reason unrelated to the injection stub it guards. Resolution: the injection-render slice must state that the router event fires while the working stage is still active, before the checkpoint transition.

**10. The atomic settings-write criterion has no planned test and no justification** — `important`
Category: Quality: testing strategy and impact.
The criterion requiring the same-directory temp-then-rename write of the settings file maps to no entry in the new-tests list, and the install-seam fixture only asserts sentinel-plus-capture arming. This is the same installer that shipped the capture-never-arms blocker precisely because nothing tested its end-to-end effects. Resolution: add an integration test that runs the install routine and asserts the merged result landed intact (and, if practical, that the temp file is created in the target's directory), or record an explicit verified-by-inspection justification. Silence is the one option that should not survive.

**11. The duplicate-event half of the gate-source criterion is untested** — `important`
Category: Quality: testing strategy and impact.
Nothing in the planned tests asserts the gates stop emitting the duplicate pipeline-command event, and the gate-rate fix turns a surviving duplicate metric-corrupting (it double-counts attempts in the pinned fractions). Resolution: under the consensus resolution of the blocking finding, add one assertion to the source-attribution slice — one real dispatch through the chokepoint yields exactly one pipeline-command event for that command. This falls out naturally once the gates' own writes are removed.

**12. The rebuilt redaction test pair has no owning slice** — `important`
Category: Quality: testing strategy and impact.
The rebuilt strip/preserve payload test pair carries both the nested-round redaction fixture and the registry-driven enumeration, but appears in no slice's retired-tests list — ownership is ambiguous between the per-round-redaction slice and the redaction-registry slice, so the red-then-green demonstration runs have no recorded home. Resolution: assign the registry enumeration to the redaction-coverage slice and the nested-round fixture to the per-round slice.

**13. Conditional criteria's "implement" branches have no test plan** — `informational`
Category: Quality: testing strategy and impact.
The cleanup criterion is either/or in three places (compute-or-remove the rounds-to-quiet metric, render-or-remove the dead round-count field, summarize-or-reword the gate output). The removal branches need no test, but an implemented-but-untested new metric would repeat the confidently-incorrect-numbers class. Resolution: one line noting the implement branch, if taken, gets a unit test pinning the computed value.

**14. The chokepoint return-type normalization is verified only by the type checker** — `informational`
Category: Quality: testing strategy and impact.
No planned test asserts the not-instrumented and redirect-fail fast paths return the integer zero. Risk is low (the sole production caller already normalizes); a two-line assertion in the existing chokepoint test file closes it cheaply.

**15. The no-mocking claim's stress point and the red-run mechanics** — `informational`
Category: Quality: testing strategy and impact.
The no-mocking claim holds for everything driven through temp directories and real subprocesses; the one stress point is the lock-during-write concurrency test, which is mock-free only if the implementation can invoke the prune step directly with a pre-created lock — the spec should say which. The red-then-green demonstration procedure is coherent (the feature-branch tip is the right pre-fix reference; the merge-base genuinely predates the capture package), but it never states how new test files run against the old code — name a single discipline (such as a second worktree at the recorded commit) so the slices don't each invent one. The rebuilt rework-boundary tests are corrected tests under the discipline but absent from the global criterion's enumerated list; the enumeration and the discipline should agree.

### Threat modeling

**16. The redaction recursion cannot meet its own no-leak invariant against the untrusted round-log file** — `blocking`
Category: Threat modeling.
Today the entire per-round structure is wholesale-stripped at the standard level, so the change starts from a safe baseline. But the redaction model is a key denylist, and round entries are copied verbatim from the round-log file (`fbk/gates/code_review.py:160`) — the input the project threat model designates untrusted at the skill-to-gate boundary — with no restriction on which keys an entry may carry and no severity enum validated anywhere. Once the rounds container is no longer wholesale-stripped, an entry like `{"raised": 1, "survived": 0, "notes": "<free text>"}` passes the recursive denylist at the standard level, violating the spec's own invariant, and the planned guard test passes anyway if its fixture uses only known keys — a guard structurally unable to see the hole it guards. Runtime exploitability is low (the round-log writer is the operator's own skill); the blocking vote is on sequencing grounds: central redaction is the structural control the threat model relies on, and this would be its first guard-invisible hole.
**Resolution (council consensus, 3–0):** producer-side allowlist projection at the code-review gate — project each round entry to exactly the known fields (raised, survived, severity validated against a fixed enum), dropping everything else, before the event is written. This is one projection loop at the boundary where the untrusted file enters, and it matches the input discipline the threat model already prescribes for this exact file. The per-round redaction criterion's wording and its guard fixture must cover the unknown-key case (a free-text value under an unknown key, asserted stripped or dropped) and an out-of-enum severity (asserted rejected or normalized), not just free text under a known key. Consumer-side allowlist recursion inside the redaction function is acceptable defense-in-depth but is not mandated.

**17. The bounded-read fix genuinely closes the threat model's named denial-of-service** — `informational`
Category: Threat modeling.
Both unbounded reads exist where the spec says: the config-level read (`fbk/capture/gate_check.py:102`) — the hostile-repo-reachable path the feature threat model names, read on every tool call — and the corroboration-marker reads (lines 152-153), which are far less exploitable since those files live outside the repository. The mitigation (a byte cap per read site) is proportional. One semantic note for the implementer: when the bounded read finds nothing parseable in a marked project, the safe default is the metadata-only standard level, not full — the guard test should pin that exact value so nobody later "fixes" it toward disclosure.

**18. Warn-but-write for unregistered sources is security-equivalent to dropping; the decision is sound** — `informational`
Category: Threat modeling.
Runtime source validation in the writer was never a security control: every actor who could forge a source label can already write lines into the events file directly. The enforcement point is the consumer side, which must treat the events file as untrusted regardless. Dropping events over a label would buy zero security and recreate silent data loss; warn-but-write preserves the fail-silent guarantee. The asymmetry with the event-type check (which discards) is defensible because event type drives consumer dispatch over a closed vocabulary.

**19. Installer changes cross no privilege boundary; one dotfile nuance** — `informational`
Category: Threat modeling.
The installer runs interactively as the operator inside trees the operator owns — no privilege boundary, no meaningful time-of-check adversary; same-directory temp-then-rename is the proportionate fix. The current temp file defaults to `/tmp`, validating the spec's cross-filesystem warning. One nuance worth a line in the installer's notes: rename replaces the target inode, so an operator whose settings file is a symlink into a dotfiles repo gets the symlink silently replaced by a regular file (safer than the current write-through-the-link copy, but a behavior change). The sentinel work does not weaken the symlink hardening: the gate still refuses a symlinked capture directory or config even with the sentinel present, and the spec's added not-instrumented assertion strengthens exactly that interaction.

**20. The in-tree-forgeable sentinel residual is unchanged and was accepted** — `informational`
Category: Threat modeling.
The sentinel fix completes the deployment of an already-designed gate-spoofing mitigation; it adds no surface. The standing residual — a hostile repo can ship the sentinel and obtain standard-level metadata capture into its own tree — was explicitly accepted in the original threat model because payload capture still requires the out-of-tree corroboration a cloned repo cannot ship, and nothing in this remediation touches that path. Restated here so a future review does not mistake it for a new gap.

## Council consensus

- Both blocking findings: unanimous (3–0) blocking votes, with consensus resolutions recorded inline above. Both are spec-text edits, not design changes.
- Duplicate-event default: unanimous for removing the gates' own writes; the chokepoint's event is the record.
- Redaction fix placement: unanimous for producer-side allowlist projection at the code-review gate.
- No unresolved dissent.

## Testing strategy coverage

**New tests needed:** present and specific — thirteen planned entries spanning unit, integration, and the two end-to-end seam guards, each tied to its acceptance criterion. Council additions required: an install-routine test (or recorded justification) for the atomic settings write (finding 10); a one-dispatch-one-event assertion in the source-attribution slice (finding 11); the unknown-key and out-of-enum-severity cases in the redaction guard fixture (finding 16).

**Existing tests impacted:** present and specific — all sixteen cited tests exist at their cited paths and names, and the spot-checked weaknesses (the agent-name envelope shape, the heading-only injection assertion, the second-line bounded-read payload) are real. Council additions required: the two gate-envelope test classes (finding 2) and the router integration tests (finding 8); the seam-test choreography correction (finding 9).

**Test infrastructure changes:** present — the real-producer-to-report fixture and the install-seam fixture, both reused across slices. No mocking, with one stress point to resolve in wording (finding 15).

**Acceptance-criteria coverage:** every criterion maps to at least one planned test or carries an explicit justification, with four gaps the findings above close: the duplicate-event half of the gate-source criterion (finding 11), the atomic-write criterion (finding 10), the conditional implement-branches (finding 13), and the type-normalization criterion's behavioral side (finding 14, low risk). The global suite-pass criterion is justified as global in the spec's uncovered-criteria section, which the council accepts.

## Test Strategy Review

**Round 1 (pre-revision spec): FAIL** — the independent test reviewer (checkpoint 1, no council context) returned five defects, all of the same shape: a planned test described loosely enough that it could pass against the unfixed code. Four were confirmed valid; one was refuted on adjudication. All four valid defects were resolved by spec revision in this session; the revised spec went back for a second independent round.

- **Injected-metrics assertion under-pinned** (affects the real-injected-metrics criterion, AC-04/AC-15) — `important, resolved by revision`: "extend to assert metric content" did not pin an assertion the label-only stub fails; loose "metric content" could match the stub's own output. Resolved: the spec now pins exact values (the literal first-try fraction and parks count computed from the fixture's events).
- **Divergence fixture could pass trivially** (affects the bounded-read criterion, AC-10) — `important, resolved by revision`: if the out-of-bounds token were the safe default `standard`, the bounded and unbounded reads agree and the test passes on both implementations. Resolved: the spec now mandates a non-default token (`full`), pins the fixture construction, and pins the asserted safe default to `standard`.
- **Subagent test allegedly cannot fail red** (affects the subagent-count criterion, AC-03) — `refuted on adjudication`: the reviewer claimed the count function's `or`-chain falls back to the identity field when the source is "not a known agent," so the rebuilt fixture would pass pre-fix. Verified against `fbk/report.py:198`: the fallback fires only on a *falsy* source; the production envelope's `source="hook_router"` is truthy, short-circuits the chain, is never a known agent, and yields the always-zero count — the rebuilt test fails red as 0 ≠ 2. The salvageable residue (state the red mechanics explicitly so the claim is not in doubt) was folded into the spec anyway.
- **Shared-constant test ambiguous between identity and value equality** (affects the single-definition criterion, AC-02) — `important, resolved by revision`: a value-equality assertion passes against two drifting copies — the exact failure the criterion exists to prevent. Resolved: the spec now mandates an object-identity assertion (`is`) plus an assertion that the old local tuple is gone.
- **Rewritten installer-migration tests had no specified assertion bodies** (affects the installer-test-corrections criterion, AC-19) — `important, resolved by revision`: "rewrite to exercise the production merge-only path" left the corrected tests' failure criteria undefined, risking empty replacements. Resolved: the spec now specifies each rewritten test's drive-and-assert shape and notes the merge-alone test needs only confirmation.

**Round 2 (revised spec): needs-revision, narrow residue.** A fresh independent reviewer re-confirmed the weaknesses of the existing tests (which the revised spec already diagnoses and rebuilds — the strategy working, not failing) and surfaced exactly two genuinely new items: the migration test file's module-level skip guard keys on the helper the rewrite removes (it would silently skip production-path coverage), and the demonstration procedure should state that only the rebuilt test versions go red at the pre-fix commit (the originals are the masked guards and stay green by construction). Both were folded into the spec.

**Round 3 (revised spec): PASS.** A fresh independent reviewer walked every acceptance criterion: all planned tests are genuinely discriminating (red pre-fix, green post-fix), all six integration seams have at least one covering test, the UV-to-test mapping is correct, and the red-then-green procedure is sound. Test strategy review: **pass**.

Five non-blocking constraints from round 3 to propagate into breakdown task descriptions:

1. The shared-constant identity test should require the old attribute is *gone from the module namespace*, not merely renamed or shadowed.
2. The injection guard should pin the parks count explicitly alongside the rate, so a partially-broken summary that emits only the rate cannot satisfy a rate-only assertion.
3. The rework-boundary fixture must place at least one event in the interval between the first park and the re-entry timestamp — events only after the re-entry classify identically under both the old and new boundary and do not discriminate.
4. The bounded-read fix must cap **both** hot-path reads (the config-level read and the corroboration read), and the breakdown task should say so explicitly.
5. The atomic-write test verifies the postcondition (merged result intact, no temp residue); same-directory temp placement itself is a code-review check, since atomicity under interruption is not test-observable without mid-write interruption. Accepted as-is.

## Threat model determination

**Decision: no separate threat model for this remediation** (operator decision, 2026-06-12).
**Rationale:** every fix lands on a trust boundary the existing feature threat model (`ai-docs/hook-harvesting/hook-harvesting-threat-model.md`) already names — hostile repo → capture gate, events file → report, installer → operator settings. No new entry points, listeners, or privilege levels are created; the bounded-read fix *implements* a mitigation that model names but the feature never shipped, and the sentinel fix completes deployment of an already-designed control. Security concerns surfaced through the Security perspective's review above (one blocking finding, resolved by spec revision; the accepted in-tree-sentinel residual restated unchanged).

Security-relevant characteristics supporting the determination: every fix lands on a boundary the existing feature threat model already names (hostile repo → capture gate; events file → report; installer → operator settings). No new listener, no new entry point, no new privilege level. One new data flow — real event-derived values flow into retrospective markdown for the first time — kept free-text-free by the redaction work plus the allowlist projection above. The feature threat model at `ai-docs/hook-harvesting/hook-harvesting-threat-model.md` already covers this surface; the bounded-read fix implements a mitigation that model names but the feature never shipped.

## Resolution status

**Both blocking findings resolved by spec revision in this session** (operator decision, 2026-06-12: revise for blocking + important findings rather than accept with rationale).

- The duplicate-gate-event either/or was replaced with the council's consensus resolution: the gates' own pipeline-command writes are removed, the chokepoint's event is the single record per dispatch, and the one-dispatch-one-event invariant is asserted on a real dispatch. Recorded as a scoping decision in the spec.
- The redaction denylist hole was closed with the producer-side allowlist projection at the code-review gate (raised, survived, enum-validated severity; every other key dropped), with the redaction recursion retained as defense-in-depth and the guard fixture extended to the unknown-key and out-of-enum cases. Recorded as a scoping decision in the spec.

All eight important findings were also applied as spec revisions: the impacted-tests additions (gate-envelope tests, router tests), the state-engine dependency wording, the handoff-events rewording plus the gates-run-during-working-stage assumption, the seam-test choreography correction, the atomic-write test, the redaction-pair slice ownership, the one-dispatch-one-event assertion, and the resolver-coverage qualification. The four valid test-reviewer defects from round 1 and the two round-2 residues were folded in as well.

The structural spec gate re-ran clean on the revised spec (pass, 0 injection warnings). Test strategy review: pass (round 3).

**Overall result: PASS** — no unresolved blocking findings; test strategy review pass; threat model determination recorded.

## Stage 4 escalation log

### task-26 — scope revision (attempt 1), 2026-06-12

During its readiness check, the implementation teammate found that the wave-1 round-projection
integration test (`tests/test_gates_code_review.py::TestRoundLogProjectedBeforeEventWrite`) uses
`capture_fixtures.make_project(...)` without importing `capture_fixtures`. The defect was latent in
wave 1 because the test skips while `project_round_entries` is absent — the skip guard meant the
missing import was never executed, so the test-authoring task's collection check could not catch it.
Resolution: task-26's scope revised to permit adding the one-line `from tests import capture_fixtures`
import to that test file (import only, no other test modification). Counts as escalation attempt 1
for task-26 under the protocol. Root-cause class: compilation gap in the wave-1 test task (task-08) —
the skip guard hid an unexecuted name reference.

### task-26 — scope revision (attempt 2), 2026-06-12

Second discrepancy from the same teammate: `tests/test_gates_code_review.py::TestCodeReviewRoundsEvent::
test_valid_round_file_emits_event` asserts `"rounds" not in data` — written under the old model where the
whole rounds list was stripped at standard level. The remediation's new contract is the opposite: rounds
survives in projected form (raised, survived, enum severity). The slice's retired-tests list missed this
stale assertion — a compilation gap (the breakdown should have listed it for rebuild alongside task-09's
strip test). Resolution: task-26 authorized to replace the stale negative assertion with assertions of the
projected shape (rounds present, only the three allowlisted keys per entry, no free text). Counts as
escalation attempt 2 for task-26 — the cap; any further failure parks the task for operator review.
