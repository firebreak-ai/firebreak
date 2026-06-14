# /fbk-improve Proposals — refactored-sdl retrospective

**Date:** 2026-05-29
**Status:** Deferred. None applied this session.
**Source retrospective:** `ai-docs/refactored-sdl/refactored-sdl-retrospective.md`
**Analysts:** 3 spawned (implementation-guide, code-review-guide, always-on-disciplines)

Three improvement-analyst teammates produced these 9 proposals after reading the retrospective. Each is tied to a specific retrospective observation. Apply selectively via Edit when ready.

---

## Implementation Guide changes

### 1. Add routing-reference integrity to per-wave verification

- **Target:** `assets/fbk-docs/fbk-sdl-workflow/implementation-guide.md`, Per-Wave Verification section, after the "File scope respected" bullet.
- **Change type:** add.
- **Diff to insert:**

  ```
  - Routing reference integrity: for each modified asset, verify that every path cited in routing instructions (`read`, `when … read`, skill routing tables) resolves to a file that exists and uses the installed-path form (`.claude/` prefix, not `assets/` repo path). Flag any routing reference that does not resolve or uses a source-repo path. This catches orphaned leaves and path-class violations before they survive into the next wave.
  ```

- **Observation:** "Routing leaks were the dominant defect class. Three of the five wave-fixes (capability-entry orphan, slice-shapes typo, council-test path form) involved leaf references that drifted from the installed-path convention… a wave-boundary lint over modified assets would have caught all three."
- **Necessity:** Without this instruction, per-wave verification checks test results and file scope but does not scan routing references in modified assets. An agent following the existing checklist exactly will miss orphaned leaves and wrong-path-form routes.

### 2. Add asset-surface completeness to final verification

- **Target:** `assets/fbk-docs/fbk-sdl-workflow/implementation-guide.md`, Final Verification → Semantic subsection.
- **Change type:** add.
- **Diff to insert:**

  ```
  - Asset-surface completeness: compare the set of assets created or modified against the spec's explicit asset-surface list (the enumerated files the spec says will exist after implementation). Confirm every named asset is present. AC-level test coverage does not guarantee this — a slice whose deliverables are a set of assets (skill + gate + guide + agent) can pass all its AC tests with one member absent if the absent member had no dedicated test.
  ```

- **Observation:** "AC-level coverage checks do not guarantee asset-surface completeness — a slice whose deliverables are a set of assets (skill + gate + guide + agent) can pass with a member missing." The Stage 3 fresh-eyes catch identified two missing SKILL.md files that survived all deterministic gates.
- **Necessity:** Final Verification's semantic step currently asks the agent to confirm "spec intent" in general terms. A general instruction does not prompt asset-list enumeration.

### 3. Add deferred-until-upstream handling for remote-operation tests

- **Target:** `assets/fbk-docs/fbk-sdl-workflow/implementation-guide.md`, Per-Wave Verification.
- **Change type:** add.
- **Diff to insert:**

  ```
  - Tests that exercise remote or upstream operations (e.g., installer scripts that download from a remote host) cannot pass in a local wave verification run. When such tests fail at wave verification, confirm whether the failure is expected-remote before treating it as a wave regression. If it is, record the count of deferred assertions in the wave summary and mark them with an explicit note: "deferred until upstream sync — N assertions." Do not block wave advancement on expected-remote failures, but do not silently omit them from the summary.
  ```

- **Observation:** "Wave 4, installer e2e test cannot pass locally: known limitation, not a gap… Class: process gap — the test exercises a remote operation; either a local-install harness or an explicit 'deferred until upstream' mark would have made this less surprising at wave verification."
- **Necessity:** Without this instruction, the per-wave rule "full test suite passes" gives no exception path for tests whose failure is expected.

### 4. Add a "Team-Lead Direct Edits" section

- **Target:** `assets/fbk-docs/fbk-sdl-workflow/implementation-guide.md`, after the "Pause on Scope Discrepancy" section.
- **Change type:** add (new section).
- **Diff to insert:**

  ```
  ## Team-Lead Direct Edits

  The team lead may make direct edits to assets or tests without spawning a teammate in two cases:

  1. **Mechanical stale-test update**: A wave task's deliberate-by-design change (schema rewrite, criteria removal, path-form correction) renders an existing baseline test sentinel stale. The update is fully determined by the wave task's own declared output — there is no design judgment involved. Make the edit, record it in the wave summary with the class label "stale-test update", and do not count it as an escalation.
  2. **Isolated typo or naming inconsistency**: A single-token correction (wrong path segment, wrong phase number, wrong filename) that has no behavioral ambiguity and is verifiable by re-running the affected test. Make the edit, record it in the wave summary with the class label "typo fix", and do not count it as an escalation.

  All other team-lead edits — including any change that modifies file scope beyond the wave's declared task files, adds new behavior, or resolves a spec ambiguity by choosing between alternatives — are treated as escalations. Record them in `ai-docs/<feature-name>/<feature-name>-review.md` with the class label "team-lead escalation" and count toward the failure attribution in the retrospective.

  Do not silently absorb team-lead edits into the wave summary without labeling them. Unlabeled edits are invisible to retrospective analysis.
  ```

- **Observation:** "Five small team-lead-level edits to baseline tests/assets that were rendered stale by deliberate-by-design changes" (six total across the run). The retrospective classified them after the fact.
- **Necessity:** The "Pause on Scope Discrepancy" section governs teammates only. Without this instruction, the team lead has no criteria for distinguishing legitimate mechanical updates from scope expansions.

### 5. Add leaf-routing reachability to the readiness check

- **Target:** `assets/fbk-docs/fbk-sdl-workflow/implementation-guide.md`, Per-Task Readiness Check, after item 4 ("Contract staleness check").
- **Change type:** add (new item 5).
- **Diff to insert:**

  ```
  5. **Leaf-routing reachability**: If this task creates a new routed-leaf file (a file that will be loaded only when another asset routes to it), verify that at least one routing instruction pointing to the new leaf exists in an already-installed asset or in another task in the same wave. If no such routing instruction exists yet — because the intended router is built in a later wave — report the gap to the team lead before proceeding. The team lead either adds a temporary routing site within the current wave or accepts the one-wave orphan window and notes it explicitly in the wave summary.
  ```

- **Observation:** "Wave 1, capability-entry orphan: Task-25 created `capability-entry.md` as a routed leaf, but no Wave 1 task included a route to it from any installed asset. The intended router (the phase skills) were built only in Wave 2."
- **Necessity:** Without this instruction, implementation agents create leaf files without checking whether a routing instruction for them exists in the current wave.

---

## Code Review Guide changes

### 6. Make the Challenger non-optional with explicit rationale

- **Target:** `assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md`, Orchestration Protocol section, between step 3 and step 4.
- **Change type:** add.
- **Diff to insert:**

  ```
  **Challenger is required.** Do not substitute direct orchestrator verification for the Challenger spawn. The Challenger catches classes the orchestrator cannot catch by reading sightings alone: severity misclassification (the Detector may downgrade a behavioral issue to fragile because the trigger is a runtime state the orchestrator does not examine); invalid type-severity combinations that the pipeline validator rejects in the sighting but would silently pass if the orchestrator reclassified inline; and rejection of sightings whose evidence does not survive re-reading the code in isolation. If conversation budget is the constraint, reduce the scope of the detection round (fewer files, higher severity threshold) — do not skip the Challenger.
  ```

- **Observation:** The code review run in this session skipped the Challenger "due to conversation budget" — documented as a process deviation. The guide had no rule against it.
- **Necessity:** Without this instruction, an agent running a review under budget pressure will substitute summary judgment for the Challenger spawn.

### 7. Require multi-file Detector context for shared-contract assets

- **Target:** `assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md`, Orchestration Protocol step 1.
- **Change type:** edit.
- **Diff (extend existing step 1):**

  ```
  When the wave authors a new asset that shares a function contract, schema, or semantic anchor with an existing asset (for example: a new gate that calls a function defined in a sibling module, or a new manifest consumer that reads a file written by an existing producer), include both files in the Detector's context. Behavioral divergences between shared-contract files — mismatched assumptions about return types, call signatures, or file-path conventions — are only detectable when both sides are visible in the same context.
  ```

- **Observation:** "Wave 3, test_hash.verify_manifest scope mismatch: the task-26 contract assumed create and verify share a base directory. Task-34's code-review-gate calls verify_manifest(feature_dir) against manifests created with a tests/ subdir scope." The cross-gate predicate divergence in the code review (intent vs design's "open critical observation" check) was found only because the Detector saw both files in one context.
- **Necessity:** Without this rule, the Detector is routinely spawned with only the new file under review and misses contract-divergence patterns.

### 8. Require an adversarial-input pass during detection

- **Target:** `assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md`, Behavioral Comparison Methodology section.
- **Change type:** add.
- **Diff to insert:**

  ```
  **Adversarial input pass.** For every function or code path that handles external inputs (file reads, path arguments, manifest lookups, artifact existence checks), construct at least one adversarial case: the file is absent, the file is empty, or the input is the zero-value for its type. Test whether the code handles that case explicitly, not whether the happy path works. A crash or silent wrong-answer on an absent or empty input is a behavioral finding — it will happen in the first run that reaches the unexercised path. This pass is required even when the test suite exists and passes; test suites that fixture only the pre-populated case cannot detect crashes on missing inputs.
  ```

- **Observation:** Stage 2 blocking finding on AC-09: "the capability-entry test only checks 'no hard failure,' not the required content." Code-review finding F-01 (verify_manifest crash on missing test-hashes.json) — all test fixtures supplied a pre-populated manifest. The recurring pattern: fixtures that always supply the happy-path input.
- **Necessity:** Without this instruction, the Detector reads only the existing test suite as evidence of coverage. When every fixture supplies a pre-populated artifact, the Detector sees green tests and moves on.

---

## Always-On Disciplines change

### 9. Add a sixth always-on discipline: uniform-pattern enforcement

- **Target:** `assets/fbk-docs/fbk-context-assets/always-on-disciplines.md`, appended after the fifth discipline.
- **Change type:** add.
- **Diff to insert:**

  ```
  **uniform-pattern enforcement** — When a spec defines a contract that applies uniformly to a class of files (a gate shape, a path-reference convention, a read-mode requirement), add a mechanical check — a grep sentinel, a lint script, or a test assertion — over that file class. Do not rely on prose discipline or AC coverage alone to hold the pattern; without a runnable check, implementers apply the pattern to the named examples and miss the unnamed ones.
  ```

- **Observation:** "Routing leaks were the dominant defect class… the path-class-1 invariant from the spec (installed assets reference installed paths) is correct; what's missing is *automated enforcement* — a wave-boundary lint over modified assets would have caught all three. The task-13 forward guard (Part 3 of test-reference-integrity) is exactly this discipline retrofitted as a sentinel."
- **Necessity:** Without this discipline, an agent writing a spec defining a uniform contract has no instruction telling it that prose-only coverage is insufficient. The observed failure mode this run: the gate-shape contract (`errors='replace'`, path validation) was specified as a pattern; the new gates followed it, the unnamed helpers did not, because no runnable check swept the file class. This discipline changes behavior by requiring a runnable check as part of the deliverable whenever a uniform pattern is defined.

---

## Cross-proposal relationships

- Proposal 9 (the discipline) is the general principle; Proposal 1 (routing integrity in wave verification) and Proposal 5 (leaf-routing reachability in readiness check) are the specific instances applied at the implementation phase. All three reinforce each other.
- Proposal 6 (Challenger required) and Proposal 8 (adversarial-input pass) both address the same class — patterns the orchestrator misses because the happy path passed.
- Proposal 4 (team-lead direct edits) is a process protocol the others depend on for clean retrospective attribution.
