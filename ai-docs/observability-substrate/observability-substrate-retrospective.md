## Stage 1: Intent

The intent phase ran as an extended working conversation rather than a single grilling session; the full distilled reasoning lives in `handoff.md`.

**What the work is and why:** A deterministic observability substrate — one durable, shape-attributed per-run record that every consumer queries — so the pipeline can report how a run went from involuntary signals (harness hooks + code-defined orchestration), never from agent-narrated prose.

**Key decisions reached (see grilling-log-intent.md for the confirmed reflect-backs):**
1. One substrate, many readers — the retrospective is the first reader, not a separate data path.
2. Surfacing is querying; the involuntary guarantee lives at capture and at a harvest-at-close step, not at surfacing.
3. Harvest-at-close consolidates the scattered, out-of-repo journal with the in-repo capture spine into one durable, portable record.
4. Attribution unit = shape (capability) + orthogonal topology modifiers; instance key = the loaded Firebreak asset bundle.
5. Code-defined orchestration stamps attribution involuntarily; the SDL migrates onto code-defined workflows rather than being retrofitted.
6. First conformance case is a thin code-defined workflow with one reader (single-run retrospective view).

**Artifacts produced:** prd.md (10 sections), behavior-inventory.yaml (B-001..B-008), grilling-log-intent.md, fresh-eyes-intent.md. Intent gate: pass.

**Fresh-eyes resolutions:** three critical observations (B-006 metric mismatch, involuntariness stated as absolute, harvest success metric contradicting the crash edge case) were resolved by edits, not waived. See fresh-eyes-intent.md.

**Open questions deferred to design:** exact membership of the shape set (is "decompose" distinct?); whether the first workflow is purpose-built or adapted from a 0.5.1 example; which deterministic metrics are universal versus SDL-ceremony-specific. Glossary entries for shape / topology / asset bundle / workflow journal deferred until the vocabulary locks in design.

## Stage 2: Design

The design phase ran as a grounded interview: an architect proposed a module shape against the real capture spine, harness-behavior questions were verified against Claude Code docs and on-disk artifacts before any decision was locked, and four direction calls were put to the operator.

**Module shape:** four components along the data-flow stages — attribution channel (authoring-time stamps), harvest/finalization (the join at close), the durable per-run record, and the retrospective reader. Decomposition rationale: vertical slices by data-flow stage so each changes independently, which is what lets future readers attach without touching capture or harvest.

**Decisions recorded (see observability-substrate-decisions.md, D-01..D-07):**
1. Shape set is five members; decomposition folds into distill.
2. Asset bundle captured via a richer launch-prompt descriptor (instructions + persona + decision tree), read from the agent transcript — not just the persona name.
3. Finalization is per-run on three already-wired hooks (PostToolUse[Workflow] primary, SessionStart recovery, SessionEnd backstop); background runs on TaskCompleted.
4. Finalize only a closed run; clean-complete versus truncated; harvest overwrites until finalized.
5. One JSON file per run under .fbk-capture/runs/.
6. Universal per-unit metrics in every record; SDL-ceremony metrics in an optional field.
7. Conformance proven by a purpose-built minimal three-agent workflow.

**Harness facts that shaped the design (verified, not assumed):** no workflow-close hook exists and the sandbox forbids the script from running commands or writing files; the agent persona name is the one attribution field the harness records involuntarily, so the richer bundle identity rides the launch prompt; a session-uuid spans the whole TUI lifetime and holds many runs, so the run — not the session — is the finalization unit; a run id is never reopened, so a restart proves any old run is closed-forever (the basis for crash/restart recovery).

**Fresh-eyes resolutions:** three critical observations (shape-vocabulary divergence between intent artifacts and design; the PostToolUse run-id dependency stated as settled; implicit concurrent-run isolation) were resolved by edits, not waived — including propagating the five-shape decision back into the behavior inventory and PRD. See fresh-eyes-design.md. Design gate: pass.

**Carried into spec as verification items:** whether PostToolUse for the Workflow tool carries the run id in its response; whether TaskCompleted identifies the workflow run; SessionEnd behavior on crash; and that the launch prompt is the first message in the agent transcript. Glossary entries for shape / topology / asset bundle / workflow journal still pending until after spec.

## Stage 3: Spec

The spec phase was a verification-first brownfield pass: before drafting the technical approach, the harness verification items the design had flagged were resolved against real on-disk transcripts rather than carried as open questions.

**Verified at spec time (turned design assumptions into facts):**
- The Workflow tool result text carries the run directory (Transcript dir: .../<run-id>), so the run id is parseable from the PostToolUse response; background launches also return a Task ID mapped at launch. The session-sweep fallback removes any hard dependency.
- The agent transcript first line is the launch prompt (type user), confirming the descriptor channel.
- Token usage fields (input/output/cache-read/cache-creation) are present in agent transcripts, so the existing token_harvester parser applies.
- .fbk-capture/ carries its own .gitignore ignoring all contents, so runs/ records are untracked by inheritance — no .gitignore change.

**Shape of the build:** three new modules (fbk/shapes.py, fbk/harvest.py, fbk/run_retro.py) and two extensions (hook_router invokes finalize_runs and parses the run id; COMMAND_MAP registers run-retro; token_harvester gains a public per-transcript accessor). Seven slices cover B-001..B-008; the reader slice is contract-evolving because registering run-retro retires the exact-19-commands test.

**Contracts:** the six design contracts (IF-D-01..06) carried forward verbatim plus one spec-originated contract (IF-S-01, the token accessor). Twelve acceptance criteria; the end-to-end conformance criterion is listed as uncovered-by-single-contract with rationale (it spans every contract and is validated by the cross-cutting conformance slice).

**One deferred open question with rationale:** whether the TaskCompleted payload identifies the run id directly — non-blocking because the SessionStart/SessionEnd sweep finalizes background runs regardless.

Spec gate: pass (zero injection warnings). Spec at ai-docs/observability-substrate/observability-substrate-spec.md.

## Stage 4: Spec Review

A four-perspective council (Architect, Builder, Guardian, Security) in discussion mode plus an independent test-strategy review. Both the council and the test-reviewer returned fail — and corroborated each other on the most serious defects, which is the review working as intended.

**Blocking defects the review caught (all real, none cosmetic):**
- The TaskCompleted finalization trigger was dead — wired to the SDL gate, not the hook router (caught independently by Architect, Builder, and the test-reviewer).
- The reader had no main() entry, so the dispatcher could not invoke it (Architect).
- The run-directory resolver did not exist and could not be borrowed from the token harvester; the spec framed net-new work as reuse (Builder).
- The durable record was a new free-text sink bypassing the redaction that protects the event stream, and ignored the capture-level off switch (Security).
- The impacted-test list missed three tests (the command-resolution test and two e2e seam tests), and several planned tests were vacuous — idempotency without a between-harvest mutation, determinism reading one file twice, no round-trip join-key test (Guardian + test-reviewer).

**Operator decisions in response:** threat model produced; finalization cut to two triggers (PostToolUse + SessionStart); quiescence guard dropped (closed-forever invariant suffices, and it needed unowned cross-process state); minimal attribution descriptor (cardinality + stance only, shape derived from persona, rich asset-bundle fields reserved null for the future dynamic assembler rather than hand-declared now). The operator prioritized the durable vision over throwaway work.

**Spec revised to fix every blocking and important finding** — no blocking finding was accepted as-is. Added: capture-level redaction parity, _real_capture_dir confinement and unique temp names, reader main(), the glob-match resolver, bounded sweep within the 15s hook budget, the three missing impacted tests, and de-vacuumed tests (mutation-between-harvests, two-clock determinism, real-router round-trip join key). Decisions captured as D-08..D-12; the two most-affected design pages carry supersession notes.

**Threat model determination: yes** — produced observability-substrate-threat-model.md (assets, threat actors, trust boundaries, STRIDE threats with mitigations, proposed project-model updates), driven by the new unredacted-sink finding.

Spec gate: pass. Review gate: pass (4 perspectives, threat model present).

## Stage 5: Breakdown

The breakdown ran as a two-agent compilation (an independent test-task author, then an independent implementation-task author seeded only with the spec and the finished test tasks), followed by the deterministic task-reviewer and breakdown gates and an adversarial checkpoint-2 test review. Three operator decisions and two pipeline-tooling findings came out of it.

**One spec contradiction caught before any task was written.** The finalization trigger was fixed everywhere at a two-argument shape (event name + working directory), yet its own acceptance criterion required it to parse the run id out of the Workflow tool response — which lives only in the hook payload the two-argument shape can't see. Operator chose to pass the payload as a third argument (the router stays a thin observer; run-id parsing lives in the harvest side). Recorded as D-13; spec, contract, and seam updated.

**Five spec gaps surfaced by the test author, all resolved without guessing.** A projects-root env seam (FBK_PROJECTS_ROOT) for redirecting the run-directory glob in tests; a monkeypatchable clock helper for the harvest timestamp; explicit runs/-subdir symlink confinement (the existing helper guards only .fbk-capture/); fixed reader output literals ("no harvest record", "partial record"); and the conformance execution model — operator chose a manual operator verification over a CI simulator, since the harvest/reader logic already has fixture-based CI coverage and only a manual run exercises the real glue against the live harness.

**Module-split refinement (D-14).** The spec homed three functions (parse, harvest, finalize) in one file. Building one new file across three tasks trips the task-reviewer gate, and one cohesive harvest task would run ~280 lines across eight criteria — past the sizing target that most predicts implement success. Operator chose to split along natural seams: fbk/attribution.py (parse), fbk/harvest.py (engine), fbk/finalize.py (trigger). Every signature and behavior is preserved; only file homes changed.

**Two SDL gate gaps found and recorded (D-15).** The task-reviewer gate lacks the cross-cutting exemption the breakdown gate has, so a cross-cutting test-only criterion can't clear both gates — the conformance and record-extensibility criteria were given implementation coverage to route around it. And the task-reviewer's files_to_modify existence check can't distinguish a typo from a file an earlier task in the same breakdown creates. Both routed around for this slice; recorded for later reconciliation.

**Checkpoint-2 test review (accepted after one revision round).** The adversarial reviewer caught one blocking and three important issues. The blocking one was substantive: the determinism test pinned its catching power to monkeypatching a clock seam in the reader — but the reader is a pure function of the record and holds no clock, so the patch would be a no-op and the test vacuous; worse, it would have steered the implementer into giving the reader a wall-clock dependency, undermining the read-twice-get-identical guarantee. Replaced with a two-call byte-identical assertion plus a no-current-timestamp assertion. The persona-mapping finding surfaced a real cross-task gap: the conformance personas (implementer, test-reviewer, code-review-detector) must be mapped by the shape resolver, which the breakdown had left to implementer discretion — now pinned as load-bearing in the shapes task.

**Wave structure (4 waves, 24 tasks: 17 test, 7 implementation).**
- Wave 1 — leaf modules with no dependencies: shape vocabulary, attribution parse, the per-transcript token accessor, and the fake-run-directory fixture builder.
- Wave 2 — the harvest engine (resolve, join, record, redaction, confined write) and the single-run reader + COMMAND_MAP registration, depending on the Wave-1 leaves.
- Wave 3 — the finalize trigger and the hook_router wiring, depending on the harvest engine.
- Wave 4 — the conformance workflow and its manual verification procedure, the end-to-end proof.

**Scope adjustments from compilation.** The conformance slice split into a manual-verification test artifact and a workflow-script implementation artifact (to satisfy both gates while honoring the manual-run decision). AC-10 (record extensibility) took implementation coverage on the reader; AC-11 (conformance) took implementation coverage on the workflow script. No behavioral scope changed.

**Gate results:** task-reviewer gate pass (24 tasks, 14 criteria, 4 waves); checkpoint-2 test-reviewer verdict accepted (zero open findings); breakdown gate pass. Pre-lock test-hash locking deferred to implementation, where the test code is actually authored (the breakdown produced task specifications, not yet test files).

## Stage 5 Addendum: External-Review Remediation

After the breakdown gates passed, an external cross-model review (GPT-5.5) was run over the full task set. It caught several real defects the internal Stage-4 council, the deterministic gates, and the adversarial checkpoint-2 test-reviewer had all missed — a useful signal about where the SDL's own review has blind spots.

**Real defects fixed (the ones that would have produced incompatible or non-running code):**
- The shape resolver and conformance workflow used persona names (`implementer`, `product-author`) that don't match installed agent identities (`fbk-implementer`, `fbk-product-author`); harvest derives shape from the recorded agent type, so the conformance run would have produced null shapes and failed its own criterion.
- The conformance workflow was specified in Python; code-defined workflows in this harness are the JavaScript Workflow DSL. Rewritten as `workflow.mjs`.
- The finalizer was wired to run after every hook event with no event-name gate, so ordinary events would sweep and could finalize a live run. Gated to two triggers; the PostToolUse path now finalizes only the parsed run (no mid-session sweep, which has no closure proof for a concurrent workflow). Closure authority moved entirely into the trigger (D-16); harvest always writes finalized=true and takes no closure parameter.
- Task field names drifted from the canonical record schema (flat topology, `duration` vs `duration_s`); pinned to record-schema.md verbatim across the harvest writer, the reader, and the tests.
- `attribution_absent` was conflated with a missing journal result, including in spec AC-04 — a crashed agent still has its launch descriptor. Split into independent facts (D-17).
- Three weak tests: the token test ran on all-zero cache fields (a cache-ignoring impl would pass); the anti-forgery protection was only unit-tested on one string, never end-to-end through harvest; the concurrency temp-name test was a sequential no-op. All three strengthened.
- Missing coverage added: harvest error paths (missing journal, unreadable events), start/stop pairing and duration math, and the malformed-vs-missing record distinction in the reader (a new `malformed record` literal).

**Recorded as accepted scope, not fixed:** full asset-bundle identity stays deferred to the dynamic assembler (D-10); run-resolution is not project-isolated and gate units have no producer (both out of the thin slice). Documentation updates tracked as a release-time doc-reconcile deliverable (D-18) rather than a code task.

**Disagreed with:** the nested-JSON regex finding (the `-->` anchor correctly handles nested objects) and the portability-vs-gitignore finding (portable means survives a folder move, not git-tracked — clarified in the spec).

**Remediation executed via six parallel subagents** with disjoint file ownership and the canonical schema/closure/identity facts embedded in each directive to prevent drift. Decisions D-16, D-17, D-18 added. Both gates re-passed (24 tasks, 14 criteria, 4 waves); cross-package consistency verified.

## Stage 5 Addendum: Opus Re-Review

The checkpoint-2 test review was re-run with the model overridden to Opus (the standing test-reviewer agent is pinned to Sonnet). Same adversarial persona, stronger capability — and it caught a real coverage hole that the Sonnet pass, the external GPT-5.5 review, and the orchestrator had all missed: the harvest engine's start/stop-pairing-and-dedup algorithm (started_at, stopped_at, duration_s) had only negative-path coverage (mismatch → null). No test proved harvest COMPUTES a correct non-null duration, on a field the reader contract (UV-3) displays — so that logic could break silently. Fixed by adding a positive timing-join test to task-05 (matched SubagentStart LIFECYCLE + SubagentStop pair with known timestamps, asserting exact started_at/stopped_at/duration_s) plus a duplicate-event case asserting the earliest-start/latest-stop rule. Three cosmetic staleness items were also cleaned (task.json task-11 'fallback' wording, task-08 'overwrite-until-finalized' prose, task-22 'mocked clock values' leftover). The Opus pass also independently verified, against known_agents.py, that the recorded agent identity is the agent's `name:` frontmatter field — confirming the agent-identity mappings the prior remediation set are correct. Both gates re-passed. Process note: a stronger-model review pass is worth its cost at the pre-implementation gate; capability, not just context-isolation, determines what a reviewer catches. See memory feedback_external_review_before_implement.

## Stage 6: Implementation

### Outcome

All 24 tasks complete and verified. Final full suite: **518 passed, 0 failed, 0 skipped** (baseline at Wave-1 start was 436 passing; +82 net new passing tests). Zero formal escalations, zero in-session hook-rejection retries. Four waves, each passing its verification gate on the first attempt. Every acceptance criterion that can be checked automatically is covered and green; the end-to-end conformance criterion is verified by a manual operator procedure by design (running the real workflow against the live harness is the one thing a fixture cannot do).

### Factual data

**Per-task results** — all 24 tasks: pass, 0 escalations, 0 in-session retries.

| Wave | Tests (model) | Implementations (model) |
| --- | --- | --- |
| 1 | fixture builder (Sonnet); shape-vocab, token-accessor, attribution-parse unit tests (Haiku, Haiku, Haiku) | shape vocabulary (Haiku), token accessor (Haiku), attribution parse (Sonnet) |
| 2 | 12 tests: roster join, round-trip join-key, completeness, atomic/idempotent, redaction, confined write, finalize trigger, crash recovery, router resilience, reader, dispatcher-count, record-extensibility (11 Sonnet + 1 Haiku for the dispatcher count edit) | harvest engine (Sonnet), run-retro reader + COMMAND_MAP (Sonnet) |
| 3 | (none — finalize tests authored in Wave 2) | finalize trigger + hook_router wiring (Sonnet) |
| 4 | manual verification procedure (Sonnet) | conformance workflow script (Sonnet) |

**Model routing accuracy.** Haiku tasks: 6/6 succeeded without escalation (three Wave-1 unit tests, the dispatcher-count edit, shape vocabulary, token accessor). Sonnet tasks: 18/18 succeeded. No task required a model upgrade.

**Task sizing accuracy.** Every task stayed within its declared file scope; no agent triggered the scope-discrepancy pause. Declared-vs-actual file scope matched exactly for all 24 tasks. The harvest agent briefly wrote a redundant top-level `persona` field to satisfy a mis-authored test (still inside its own declared file) — removed by the team lead during the gate, see below.

**Verification gate pass rates.** Per-wave verification: 4/4 waves passed (full suite green, file scopes respected, no merge conflicts, ruff clean) before advancing. Two waves needed team-lead corrections to test-authoring defects before the gate passed (Waves 1 and 2) — these were lead-applied fixes, not task escalations.

**Wall-clock per wave** (approximate, dominated by the slowest parallel agent since tasks run concurrently): Wave 1 ~2 min test step + ~1 min impl step; Wave 2 ~3.5 min test step (12 concurrent) + ~4 min impl step; Wave 3 ~2 min; Wave 4 ~2.5 min. Total active orchestration well under 20 minutes.

**Team-lead corrections applied at the gate** (caught by impl agents refusing to silently work around contradictions, plus the lead's full-suite + lint runs — none reached the escalation cap):
1. Wave 1, fixture builder: two unused imports and two ambiguous single-letter loop variables (ruff). Trivially fixed in place.
2. Wave 2, roster-join test: asserted `unit["persona"]` while the authoritative record schema nests persona under `asset_bundle.persona`. The harvest agent flagged the contradiction rather than guessing and added a compensating write; the lead instead fixed the test to the schema path and removed the compensating write, keeping the record schema clean.
3. Wave 2, record-extensibility test: the import bound the module instead of the reader function, and the test read `captured.stderr` where pytest exposes `.err`. Both fixed in place; the reader agent had correctly identified both and declined to edit a file outside its scope.

### Upstream traceability

- The breakdown gate passed cleanly at implementation entry (24 tasks, 14 criteria, 4 waves); no recompilation was needed.
- Pre-implementation review was unusually deep for this feature (recorded in the Stage 5 addenda): the internal council and deterministic gates, then an external cross-model (GPT-5.5) review, then an Opus re-run of the test-reviewer. Those passes caught and fixed several real defects *before* implementation — agent-identity mismatches, the Python-vs-JS workflow language error, the ungated finalizer, record-schema field drift, and weak tests. The clean implementation run (zero escalations) is largely attributable to that front-loaded review catching the failure modes that would otherwise have surfaced here.
- Decisions carried into implementation and honored: closure authority lives entirely in the trigger (harvest always writes finalized=true, takes no closure parameter); `attribution_absent` is independent of a missing journal result; documentation updates are a release-time reconcile deliverable, not a code task.

### Failure attribution

No task was formally escalated. The three team-lead corrections classify as:
- Fixture-builder lint cruft — **implementation error** (the agent left unused imports; instructions were adequate). Minor, mechanical.
- Roster-join persona-path mismatch — **compilation gap**. The test task did not pin the nested `asset_bundle.persona` schema path, so the test author inferred a flat top-level field. The fix belongs in the task's interface contract, which should cite the record-schema nesting explicitly.
- Record-extensibility import/capsys bugs — **implementation error** (Python/pytest API mistakes by the test author; the task instructions were correct).

The one systemic signal: the single compilation gap was a schema-nesting detail. Pointing both implementation agents at the authoritative `design/record-schema.md` (which the lead did at spawn time) is what kept the harvest writer and the reader in agreement; the one place a test drifted from it was the place the breakdown task hadn't restated the nesting. A small breakdown-stage improvement — quote the exact record-schema path in any task that reads or writes a unit field — would have closed it.

### Documentation impact — pending operator review

The spec lists four durable-doc updates (architecture-overview measurement section, GLOSSARY entries for shape/topology/asset-bundle/workflow-journal, CHANGELOG under Added for 0.5.2, README command-list check). These are deliberately **not** auto-applied: the spec flags the architecture overview as an operator-review change and the project convention is to discuss README changes before applying. They are best handled at the upcoming code-review / doc-reconcile step.

## Stage 7: Code Review

Full report: `fbk-cr-observability-substrate.md`. Gate: **pass**.

### Sighting counts
- Raised (round 1): 9, across 4 parallel Detectors (harvest; finalize+router; run_retro+init; leaf modules).
- Verified findings: 6 — 4 behavioral/major, 2 structural/minor.
- Rejected: 3 (false-positive rate 33%) — roster non-dedup (runtime emits one started per agent), realpath-vs-write TOCTOU (outside the single-user threat model), non-dict usage AttributeError (runtime never emits a non-dict usage; nit).
- Detection-source breakdown: spec-ac = F-01, F-03, F-05, F-06; audit-pass = F-02, F-04. Pre-spawn ruff + mypy clean, so no linter-sourced findings.

### Verification rounds
- One thorough round to convergence (per-file targeted detectors plus an adversarial Challenger pass). Convergence was judged sufficient because the four detectors collectively covered every changed production module with the spec ACs as the comparison target.

### Findings and disposition
- F-01 (behavioral/major) — harvest silently overwrote an unreadable existing record with a new harvested_at. Fixed: refuse and return an error. Regression test added and proven non-vacuous.
- F-02 (behavioral/major) — SessionStart sweep harvests other projects' runs into the current project's capture dir. **Held for an operator decision**: a correct fix reverses the spec's deliberate no-project-hash decision and reworks fixtures; documented as accepted thin-slice scope in the breakdown.
- F-03 (behavioral/major) — PostToolUse finalize had no Workflow tool-name gate, so any tool response mentioning a workflow path could finalize a possibly-live run. Fixed: gate on tool_name == "Workflow".
- F-04 (behavioral/major) — run_retro raised on a PermissionError/TOCTOU instead of printing a line. Fixed: catch OSError.
- F-05 (structural/minor) — completeness ignored transcript readability; root cause is a spec-internal contradiction (AC-04 text vs record-schema.md / decision D-04 / technical-approach prose). Fixed the code to require readable transcripts (matching the majority intent); regression test added and proven non-vacuous. The AC-04 wording still needs an operator edit to fully reconcile.
- F-06 (structural/minor) — reader read/printed a unit_id field absent from the schema (dead code). Fixed: removed; ordering test now asserts on agent_id.

### Finding quality
- Origin: all 6 introduced by this feature. False-positive rate this round 33% — the three rejects were all "real mechanism, unrealistic trigger" calls the Challenger made correctly against the runtime contract and threat model.
- False negatives surfaced by later passes: the final test-review (run independently) caught that the F-01 and F-05 fixes shipped without regression coverage — a real gap the detection loop did not flag because it reviewed the pre-fix code. Both gaps were closed and the tests verified to catch the regression. Process note: applying a fix should always pair with a regression test, and the final test-review is the backstop that enforces it.

### Closeout passes
- Quality scan: 5 minor/info opportunities, dominated by duplicated path/glob/env knowledge between harvest and finalize and twin timestamp helpers (no action taken; advisory).
- Final test-review: changes-requested → after adding the two regression tests, re-run returned **accepted**.
- Doc reconcile (advisory): 4 durable-doc drifts — architecture-overview, CHANGELOG (no 0.5.2 section), GLOSSARY (missing shape/topology/asset-bundle/workflow-journal), README (no run-retro) — plus confirmation of the AC-04 spec inconsistency. All left for operator review per the discuss-before-apply convention.

### Tooling
- Project-native ruff and mypy run pre-spawn (both clean on production modules); pytest used as the test runner; Read/Grep/Glob for navigation. No fallbacks needed.
