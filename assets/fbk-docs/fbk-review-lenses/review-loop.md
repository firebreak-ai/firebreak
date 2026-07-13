# Review Loop — The Shared Spine

This document defines the find-challenge-confirm loop generically. Every review preset routes to this document. No review type re-implements these rules.

---

## Abstract definitions

### Finding

A finding is a candidate claim that a named artifact diverges from its expected behavior. At emission by the researcher, a finding carries:

- A mechanism: the exact expression in the artifact that is wrong, and what it does wrong.
- A consequence: the downstream impact of the mechanism.
- An evidence location: the specific spot in the artifact (file and line, or section reference).
- A type: one of the types defined in the loaded review lens.
- A severity: one of the severities defined in the loaded review lens.
- A source-of-truth reference: the specific document, contract, or criterion the finding compares against — may be empty when the researcher is working from general lens knowledge rather than a named document.

A finding at researcher output has no verdict field. Verdict fields are added by the challenger only.

### Challenger verdict

The challenger produces exactly one of five outcomes for each candidate finding:

- **Verified**: the challenger independently confirmed the mechanism by reading the artifact and, when applicable, the cited source. The challenger can describe the trigger and consequence in its own words, not the researcher's.
- **Verified-pending-execution**: the finding is credible from reading but requires test execution to confirm fully. Treated as verified with a caveat marker.
- **Rejected**: the challenger found concrete counter-evidence — the artifact does not behave as described, the trigger is unrealistic, or the behavior aligns with explicitly documented intent.
- **Rejected-as-nit**: the observation is technically accurate but functionally irrelevant. Counted separately; does not enter the findings list.
- **Unresolvable**: the finding turns on a cited source the challenger could not locate, so it can neither confirm nor reject. The challenger issues no verified-or-rejected ruling; the finding is surfaced as unadjudicated (the cited source could not be located) and remains open. See "The challenger reads cited sources before ruling" below.

The challenger does not generate new findings. It only rules on candidates it received.

### Confirmed finding

A finding is confirmed when the challenger returned verified or verified-pending-execution. Confirmed findings are the loop's output. Rejected findings and nit rejections do not surface to the caller.

---

## The loop

### Step-by-step

1. The loop coordinator spawns the researcher as a cleared agent, injecting: the artifact under review, the review lens for the active preset, any linter or static-analysis output (for review types where this applies), and the source of truth the researcher should compare against. The researcher produces a list of candidate findings.

2. The loop coordinator runs the candidate list through schema validation and type-severity matrix checks. Any candidate that fails required-field checks, enum validation, or the type-severity validity matrix is rejected and not passed to the challenger. If more than 30% of the original candidate count is rejected during this validation step, the coordinator logs a warning about research prompt compliance. The coordinator then applies domain filtering (removing types not allowed by the active preset) and severity filtering (removing findings below the preset's minimum threshold) to the surviving validated candidates.

3. The loop coordinator normalizes the surviving candidates (the isolation invariant: framing is stripped; only mechanism, consequence, evidence location, type, severity, and source-of-truth reference pass through). The loop coordinator also collects the documents named in each candidate's `source_of_truth_ref` field and will inject those documents into the challenger spawn in step 4.

4. The loop coordinator spawns the challenger as a cleared agent, injecting in this order: the artifact under review (the challenger reads this cold, before anything else); the review lens for the active preset; the normalized candidate findings; the content of any cited source documents collected in step 3. The challenger produces a verdict for each candidate.

5. The loop coordinator validates challenger output (required fields, verdict values, reclassification matrix if the lens defines one). It filters to verified and verified-pending-execution, assigns sequential finding identifiers, and converts to the human-facing format for the review report. The coordinator computes any verdict-count summary itself from the validated per-candidate verdicts; a summary count the challenger writes is not carried forward as authoritative.

6. The loop coordinator appends confirmed findings to the review report and records the round in the round history.

7. Repeat from step 1 if the round produced confirmed findings at or above the preset's minimum severity threshold, and the round cap has not been reached.

8. When the loop terminates, write the round history artifact at the path declared by the preset.

### Termination rule

The loop terminates when either of these conditions is true:

- A round produces no confirmed findings at or above the preset's minimum severity threshold (a clean round).
- The round count reaches the preset's round cap.

The loop always terminates. A loop that reaches its round cap without a clean round is not a failure — it is the expected behavior when a deeply defective artifact cycles through multiple passes. The caller sees the confirmed findings from all rounds.

### Round cap

The default round cap is 5. The fresh-eyes preset overrides this to 1 (a single pass, always — no iteration). Presets may override the default to a lower value; no preset may set a round cap of 0 (which would prevent any review from running) or remove the cap (which would allow unbounded cycling).

### Cardinality

Each preset declares a researcher count and a challenger count.

- Researcher count is always at least 1.
- Challenger count may be 0 for named degenerate presets (fresh-eyes is the only currently defined degenerate preset). Zero challengers is a legitimate configuration, not an error. A preset with zero challengers runs a single-round find-only pass.
- For all other presets, challenger count is 1.

Future presets may declare higher counts for parallel researcher or challenger configurations. Raising cardinality never reduces isolation: each researcher still reads cold, each challenger still receives only normalized claims and cited sources, no researcher sees another researcher's output during its own pass, no challenger inherits framing from any researcher.

### Degenerate cardinality (zero challengers)

Zero-challenger presets are fresh-eyes plus the two scan-only presets folded in at spec review — quality scan and doc reconcile. When a preset declares zero challengers, the following loop steps do not run and must not be attempted:

- Step 2 (candidate validation via `validate_sighting()`) — **skipped for any preset whose lens declares output mode `scan`** (quality scan, doc reconcile). A scan lens carries a non-finding output schema, so the finding-shaped validator does not apply; the candidates are checked only against the lens's own structural output schema. Fresh-eyes' lens is also read-only; its observations are checked against the observation-format schema, not `validate_sighting()`.
- Step 3 (normalization and handoff) — there is no recipient for normalized findings.
- Step 4 (challenger spawn) — no challenger exists.
- Step 5 (challenger output validation and reclassification check) — no output to validate.

The following steps also behave differently:

- Step 6 (sequential ID assignment) — candidate findings from the researcher are the final output; they are not promoted to "confirmed findings" in the sense used for two-role runs. They are observations, not findings with challenger verdicts. Sequential identifiers are assigned to observations for report purposes.
- Round history — the round history artifact records the researcher's observation count under `raised`; `survived` is set equal to `raised` (no challenger filter was applied). This is the correct record for a single-pass read-only run.

The loop still terminates after step 6 (no step 7 re-iteration) because the round cap is 1 for all zero-challenger presets.

**Lens output mode.** Each lens declares an `output_mode` of `finding` or `scan` (added at spec review; see the spec's output-mode subsection and `lens-format.md`). `finding`-mode lenses route candidates through `validate_sighting()` with the lens's machine-readable type-severity matrix; `scan`-mode lenses (fresh-eyes, quality scan, doc reconcile) bypass `validate_sighting()` and are validated only against their own structural output schema. This is what lets a scan preset's native output (quality scan's ranked sightings, doc reconcile's `class`/`doc`/… records) survive without being forced into the finding schema.

---

## Generic challenger disciplines

These disciplines apply to every review type that runs a challenge stage. They live here, not in any lens. The lens may supply type-specific content for each discipline (for example, what provenance means for dead code in a test file vs. a task document) but the discipline itself is generic.

### The challenger reads cited sources before ruling

When a candidate finding turns on what a named document contains — a design document, a contract specification, a prior version of the artifact — the challenger opens and reads that document before issuing a verdict. A ruling based on what a source probably says is not acceptable. The cited source is injected into the challenger's spawn prompt by the loop coordinator. When the cited source cannot be located, the challenger returns `unresolvable` and does not issue a verified or rejected ruling on that finding.

### Dead-code provenance trace

When a candidate finding identifies material that appears unused — unreachable code, a task with no implementation path, a declared interface with no consumer — the challenger traces its provenance through the artifact's known history before ruling. For code review, the provenance chain includes requirements, design, spec, task history, and git log. For other types, the chain is whatever prior SDL artifacts exist for the feature. If the trace confirms the material is genuinely dead, the finding is verified. If the trace is ambiguous — for example, infrastructure shipped ahead of its first consumer, or a task written against a planned dependency that has not arrived — the finding is surfaced with the ambiguity noted in the evidence field rather than rejected.

---

## Evidence discipline (all roles)

These rules apply to every role the loop runs — researcher, challenger, coordinator — and to the caller consuming the loop's output.

**A claim about the artifact comes from reading the artifact.** At any role, a statement about what the artifact, a cited source, or a neighboring file contains — including a claim that a file, path, or reference is missing — is grounded in text actually opened and read during this run, not memory, plausibility, or one file's account of another file's content. A researcher reports a path as absent only after opening it and confirming nothing is there.

**Historical narration is not a live claim.** Text describing a past or superseded state — a remediation note, a dated correction, a comment explaining what an earlier defect was — is historical context. Before reporting or ruling on a problem such text describes, confirm the problem is still present in the artifact's current content.

**A clean result without a challenge stage is an unverified read.** A zero-challenger preset's clean result ("no drift," "no findings") is one agent's unchallenged reading, structurally weaker than a clean round that survived a challenger. Before treating it as final, the caller spot-checks the claim against the artifact directly.

**An empty candidate list is not automatically a clean round.** A researcher that stops responding before finishing its pass can return an empty list that looks identical to a genuine clean read. Before the coordinator records a zero-candidate round as clean, it checks that the researcher's run actually completed — for example, by confirming a completion signal or reading the run's transcript — rather than accepting an empty list at face value.

**Disagreement between instruments is resolved by the artifact.** When two instruments disagree about the same claim — a challenger's rejection against another reviewer's verification, an adjudicator's ruling against a direct reading, a scan observation against a finding verdict — the caller resolves it by reading the artifact itself before accepting either side. Neither verdict outranks the other by default; the artifact does.

---

## Post-fix reentry rule

The loop reviews what it is given. It never applies fixes. Remediation is entirely the caller's responsibility.

When the caller applies fixes after a loop run, the post-fix artifact is new material. It must go through a fresh loop invocation — with a new round count, a new round cap, and no memory of the prior run's candidates. The prior run's confirmed findings are not automatically closed.

The fresh invocation may scope the artifact it injects to the fix set applied since the prior round instead of the full artifact. A scoped reentry costs a fraction of a full reentry and has caught the same class of fix-introduced residue; scope the reentry to the fix set by default, and fall back to a full-artifact reentry only when the fix touched enough of the artifact that drift outside the fix set is a realistic concern.

The code review preset documents the fix-then-re-invoke step explicitly. All other presets are read-only: they do not modify the artifact under review, and re-invocation after external changes is the caller's decision, not the loop's.

**Why this matters for the "remediation earns its own adversarial pass" behavior:** the loop-reentry rule is what satisfies this. The original pass reviewed pre-fix material. The re-invocation reviews post-fix material under the same find-challenge-confirm discipline. The behavior is a property of when the loop is called, not of what happens inside the loop.

---

## Fix pairing rule (confirm-stage discipline)

When the loop confirms a behavioral finding or a test-integrity finding, the caller is expected to pair any fix with a regression test that would catch the same defect returning. This expectation has two named exceptions:

- The finding is not executable (a documentation change, a naming correction, a wording fix).
- The caller records explicitly why no meaningful regression test is feasible for this finding.

This is a confirm-stage discipline that applies across all review types that can produce behavioral or test-integrity findings. The lens for each type defines which of its finding types are "behavioral" or "test-integrity" in this sense.

---

## Cross-model review — generic role slot

The loop names no model. Model selection is a per-preset setting declared in the preset configuration.

A future review preset may assign a different model family to the researcher role, the challenger role, or both. When it does, that model family is the sole role-holder for that role in that round. It is not a bolted-on extra round, and it is not an addition to the standard researcher or challenger. The loop's cardinality rules apply: the preset declares one researcher and one challenger (or one researcher and zero challengers for degenerate presets); model selection is independent of cardinality.

This design constraint exists because the value of a cross-model reviewer is model-family diversity — a structurally different perspective — not additional rounds or a "stronger" model. Baking in "run an extra round with a different model" would conflate cardinality with diversity and undermine the intent.

---

## Isolation invariant

The isolation invariant is a hard constraint on all loop runs. It is not a quality goal. Any loop configuration that violates it is defective, not merely suboptimal.

The invariant has three parts:

1. Every researcher reads the artifact cold. No researcher receives prior-round output, another researcher's output, or any framing beyond the artifact, the lens, and the source of truth.

2. Every challenger reads the artifact cold before receiving candidate findings. The challenger is spawned with the artifact first; it reads it independently before the candidate list reaches it.

3. The candidate findings the challenger receives contain no researcher framing. The loop coordinator's normalization step (step 3 in the loop above) enforces this by stripping reasoning fields and passing only the factual claim fields.

At zero challengers (fresh-eyes), the invariant reduces to part 1 only: the researcher reads cold.
