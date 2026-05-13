# Authoring Rules BKM Update — Stage 2 Review

Perspectives: Architecture, Pragmatism, Quality

Overall result: **PASS** — blocking finding resolved in spec revision; non-blocking important findings A-2, A-6, P-2, P-6+Q-2, Q-3 also applied. Informational findings deferred or accepted with named cost.

---

## Architectural soundness

### Finding A-1: Citation format diverges from existing principle convention
- **Severity:** important
- **Category:** Architectural soundness
- **Spec section affected:** Change 1a, Change 2, Change 4
- **Description:** The existing six principles in `fbk-context-assets.md` carry zero citations. Change 1a introduces an italic parenthetical citation block as the final element of the new principle; Changes 2 and 4 adopt the same pattern in different host sections. This is a new structural element with no precedent in the parent doc or any leaf, and the spec's "Decisions resolved" entry justifies the format but does not declare the convention. Resolution: add a one-line meta-instruction near the top of `fbk-context-assets.md` declaring "citations are inline italic parentheticals on new content," making the pattern self-documenting for future authors. Cost: one line. Alternative — move citations to a References footer with inline slug anchors (rejected because it imposes more structure than the rule justifies and breaks the existing flat-file pattern).

### Finding A-2: Principle wording does not cover sole-consumer workflow case
- **Severity:** important
- **Category:** Architectural soundness
- **Spec section affected:** Change 1a workflow-routing paragraph; AC-01
- **Description:** The new principle names three legitimate workflow destinations (skills, referenced docs, spawn prompts) but does not give a heuristic for choosing between them when the workflow is small and has exactly one consumer. An author with a one-shot agent + 4-line workflow faces an unresolved choice: inline in the agent body (violates the principle), extract a 4-line skill (over-fragments), or use the spawn prompt (allowed but undocumented as the answer for this case). Resolution: extend the workflow-routing paragraph or follow it with one sentence pointing to `## Separation of Concerns` as the governing rule for inline-vs-extract decisions on workflow content: *"When the workflow is small and has one consumer, route it via the spawn prompt — `## Separation of Concerns` governs the inline-vs-extract decision for workflow content the same way it does for instruction content."* Trade-off: adds a sentence to an already-long paragraph (cf. Finding A-3).

### Finding A-3: New principle length is asymmetric with siblings
- **Severity:** informational
- **Category:** Architectural soundness
- **Spec section affected:** Change 1a
- **Description:** The new principle is ~17 lines of prose + a 2-row table + a citation block. Existing principles range from ~6 to ~14 lines. The new principle is the longest single-flow principle in the file. This is justified by consolidation (it absorbs three sub-rules), but the workflow-routing paragraph re-states material that `agents.md` `## Persona authoring` will partially carry. Accept with named cost or compress; choice depends on weight given to Finding A-2 (which would extend the paragraph further). Recommendation: accept current length — the principle is doing real architectural work and compression would lose generalization-aid material.

### Finding A-4: Trigger Types table cell length mismatch
- **Severity:** informational
- **Category:** Architectural soundness
- **Spec section affected:** Change 1b
- **Description:** Sibling Example cells in the Trigger Types table are noun-phrase fragments (longest ~50 chars: "Go coding standards triggered only when touching `**/*.go`"). The proposed replacement reaches ~85 chars. Voice fits; length is the discordant note. Resolution: trim to "Specialized personas; workflow routed in from skills, docs, or spawn prompt." Preserves AC-03c's substance while keeping the cell visually consistent with siblings.

### Finding A-5: Intra-file forward pointer is a new pattern in leaves
- **Severity:** informational
- **Category:** Architectural soundness
- **Spec section affected:** Change 3 Part A
- **Description:** Change 3 Part A introduces an intra-file forward pointer ("For body-content structure ... see `## Persona authoring` below") inside `agents.md`. Routing in the parent doc is tree-shaped (Routing Table at bottom routes to leaves; leaves currently have no intra-file routing). This pointer is lateral within a leaf — not a contradiction with progressive disclosure (content is co-loaded; pointer just orients the reader) but a new pattern. Accept; record in retrospective so future leaf-restructure specs inherit the precedent intentionally rather than by drift.

### Finding A-6: Convention visibility for the task compiler
- **Severity:** important
- **Category:** Architectural soundness
- **Spec section affected:** Technical approach → Module touch policy
- **Description:** When this spec is broken into tasks, the implementer needs conventions the spec does not enumerate: heading level (all principles are `##`), section spacing (one blank line between paragraphs and between sections), italic citation block placement (end of section, blank line above), table column count convention, and the parent doc's existing imperative-voice convention. A task compiler relying on the spec alone will silently default rather than match. Resolution: add a "Conventions in modified files" subsection under Technical approach naming heading level, blank-line spacing, citation block placement, and imperative voice. Estimated cost: ~6 lines.

---

## Over-engineering / pragmatism

### Finding P-1: Scope expansion stayed within "three files" steer
- **Severity:** informational
- **Category:** Over-engineering / pragmatism
- **Spec section affected:** Scope / Module touch policy
- **Description:** The spec still touches the same three context-asset files plus CHANGELOG.md (implied by repo convention). Change 1b (Trigger Types table cell) lives inside `fbk-context-assets.md`, so the file count is unchanged. Post-council expansion did not violate "three files" at the file level. Drift is at the paragraph level in Change 1a (workflow-routing addition), which the user explicitly approved. No cut needed.

### Finding P-2: AC count is one or two slots too high for a ~50-line diff
- **Severity:** important
- **Category:** Over-engineering / pragmatism
- **Spec section affected:** Acceptance criteria (12 ACs)
- **Description:** Twelve ACs for five concrete code-change blocks is over-granular. Recommended merges: (a) **AC-03 and AC-03b** both verify content inside Change 1a's inserted block — merge into one AC against the full section. (b) **AC-06a and AC-06b** verify two halves of the same restructure — merge into one AC against Change 3 as a unit. Result: 12 → 10 ACs, no loss of checkability. AC-03c (table cell) stays standalone as a separate-location change with verbatim-required cell value.

### Finding P-3: UV steps are proportionate after AC merges land
- **Severity:** informational
- **Category:** Over-engineering / pragmatism
- **Spec section affected:** User verification steps (9 UVs)
- **Description:** UV mappings simplify naturally if Finding P-2's AC merges land. No standalone cut needed.

### Finding P-4: Spawn-prompt-author decisions entry is borderline ceremony
- **Severity:** informational
- **Category:** Over-engineering / pragmatism
- **Spec section affected:** Decisions resolved during scoping
- **Description:** The entry "Should we constrain spawn-prompt authors too?" pre-empts a question the new principle does not actually invite (the principle says workflow lives in spawn prompts, so constraining them is a clear out-of-scope question). Resolution: cut, or fold into the "Why does the new principle include asset-type routing" entry as a one-line aside. Saves ~6 lines.

### Finding P-5: Implementation cost is 60–90 minutes
- **Severity:** informational
- **Category:** Over-engineering / pragmatism
- **Spec section affected:** Overall structure
- **Description:** Concrete breakdown: Change 4 ~5 min; Change 1a ~15 min; Change 1b ~3 min; Change 2 ~5 min; Change 3 ~20 min; Change 5 ~5 min; self-application audit (AC-08) ~15–20 min. Total ~70 min focused work. The spec is ~5:1 spec-to-diff ratio, signaling more time than the work requires. Accept as a quality-discipline trade-off; named for awareness.

### Finding P-6: AC-08 should be reframed as a batched table, not per-instruction prose
- **Severity:** important
- **Category:** Over-engineering / pragmatism
- **Spec section affected:** AC-08; Testing strategy → Self-application review
- **Description:** AC-08 currently requires the author to document the Necessity Test outcome for each added instruction in either inline comments or the retrospective. Eight new instructions × ~5-8 lines of prose each = ~50 lines of artifact with low marginal information when most pass the test obviously. Resolution: reframe AC-08 to require a single batched **Self-application audit** table in the implementation retrospective with one row per added/replacement instruction: `| instruction | removed-would-cause | framing | single-constraint | why-clause-load-bearing |`. Preserves auditability (per-row granularity, fixed location) while cutting artifact to ~10 lines. This finding combines with Quality Finding Q-1 — see resolution path below.

---

## Quality: testing strategy and impact

### Finding Q-1: BLOCKING — Existing TAP tests not enumerated as impacted
- **Severity:** **blocking**
- **Category:** Quality: testing strategy and impact
- **Spec section affected:** Testing strategy → "Existing tests impacted"; AC-06a, AC-06b
- **Description:** The spec asserts "There are no automated tests over `assets/fbk-docs/fbk-context-assets.md` or its leaves." This is factually wrong. Two existing TAP scripts test the modified files:
  - **`tests/sdl-workflow/test-agents-md-persona-guidance.sh`** — 12 assertions directly against `agents.md`. Three relevant to this spec: Test 2 (`grep -qE '^## .*[Pp]ersona'` — survives the restructure since `## Persona authoring` is preserved); Test 9 (`grep -q 'Detector' && grep -q 'Challenger'` — survives, both names remain in `## Persona authoring`); **Test 10 (`grep -qiE 'what not to include|not to include'`)** — at risk: the "What not to include" subsection lives inside the `## Persona authoring` section the spec preserves, so the test *should* survive, but the spec did not verify this and listed the test as not impacted at all.
  - **`tests/sdl-workflow/test-reference-integrity.sh`** — walks every asset file for path references; no file paths change, but the test must still pass post-restructure.
  
  Resolution: replace "Existing tests impacted: None" with an enumerated list naming both scripts, and add a Sequence step to run both pre-commit. Both should pass without modification; the spec's "None" claim is the defect, not the testing reality.

  Source: independently flagged by Guardian (Stage 2 finding 4) and the test reviewer at CP1 (which returned FAIL on this point).

### Finding Q-2: AC-08 documentation artifact location and granularity unpinned
- **Severity:** important
- **Category:** Quality: testing strategy and impact
- **Spec section affected:** AC-08; Testing strategy → Self-application review; UV-7
- **Description:** AC-08 says the author documents the Necessity Test outcome "inline with the implementation work or in the implementation retrospective, whichever the implementer prefers." Two failure modes: (a) a single sentence like "All added instructions pass the Necessity Test" satisfies the literal AC without per-instruction outcomes; (b) reviewer has no canonical location to read. Resolution: combine with Finding P-6 — require a per-instruction record in a fixed location: a **Self-application audit** table in the implementation retrospective with one row per added/replacement instruction documenting Necessity outcome, positive framing, single-constraint, and load-bearing why-clause. UV-7 tightens to "verify the audit table contains one row per added/replacement instruction; reject if any instruction is unrepresented."

### Finding Q-3: AC-06b "no incidental edits" lacks deterministic verification
- **Severity:** important
- **Category:** Quality: testing strategy and impact
- **Spec section affected:** AC-06b; UV-3
- **Description:** AC-06b says five sections "survive the restructure with no incidental edits." UV-3 covers this via human reading of a 150-line file with a 30-line deletion + a paragraph extension. Eyeballing is high-effort and prone to silent-rewording misses (comma-splice reformat, single-word substitution in `## Persona authoring`). Resolution: add a deterministic verification step to the Sequence — run `git diff` scoped to the preserved sections post-edit, with pass criterion "zero lines changed in `## When to Use an Agent vs. Alternatives`, `## Capability Scoping`, `## Persona authoring`, `## Scope`, `## Security`." Alternative: capture pre-change section snapshots via `sed -n 'M,Np'` and assert post-change content matches.

### Finding Q-4: UV-5 calibration leaks vague-criterion patterns
- **Severity:** informational
- **Category:** Quality: testing strategy and impact
- **Spec section affected:** UV-5
- **Description:** Named rejection criteria ("appropriate", "reasonable", "good", "clean", "thorough") cover obvious adjectives but leak on adverbs ("properly", "correctly", "adequately"), satisfaction qualifiers ("acceptable", "robust"), and process verbs without output checks ("ensures", "validates"). Resolution: restate as a positive rule — "the AC must name an observable input and observable output state, both checkable by reading the artifact." UV-5 remains optional; the calibration broadening preserves its sanity-check value.

### Finding Q-5: Edge-case scope for hooks and rules unstated
- **Severity:** informational
- **Category:** Quality: testing strategy and impact
- **Spec section affected:** AC-01, AC-03b, User-facing behavior
- **Description:** The new principle implicitly applies to all asset types loaded under these rules. Hook scripts are by nature ordered procedural code (PreToolUse validators, etc.); the carve-out ("runbooks, deterministic verification sequences, audit trails") covers hooks implicitly but does not name them. Resolution: extend the carve-out sentence to name "hook scripts, rule body sections where step order is load-bearing" alongside runbooks. Low risk because hook authors are unlikely to misapply the principle, but explicit is cheap.

### Finding Q-6: Historical SDL artifacts reference deleted section name
- **Severity:** informational
- **Category:** Quality: testing strategy and impact
- **Spec section affected:** Technical approach → Change 3 Part B; Documentation impact
- **Description:** Grep finds historical SDL artifacts in `ai-docs/agent-personas/agent-personas-tasks/task-05-...` and `task-17-...` that reference `## Instruction Design` by name. These are point-in-time SDL records, not live cross-links. No runtime breakage. Resolution: add one sentence to Documentation impact: "Historical SDL artifacts in `ai-docs/agent-personas/agent-personas-tasks/` reference the deleted `## Instruction Design` section by name; left unchanged because those artifacts are point-in-time records, not live context."

### Finding Q-7: CHANGELOG entry shape unverified
- **Severity:** informational
- **Category:** Quality: testing strategy and impact
- **Spec section affected:** AC-09; UV-6
- **Description:** AC-09 requires "one-paragraph 'Changed' entry under the next unreleased version." UV-6 verifies presence by reading. The project's CLAUDE.md mandates keepachangelog.com format (Added/Changed/Deprecated/Removed/Fixed/Security groupings). UV-6 doesn't check the format. Resolution: extend UV-6 to "A 'Changed' subheading exists under the next unreleased version section, and contains a one-paragraph entry summarizing the rules update." Low risk; AC is technically rubber-stampable as written.

---

## Test reviewer (CP1) result

**Result: FAIL** — one defect, overlapping with Finding Q-1.

Details: The CP1 reviewer flagged `tests/sdl-workflow/test-agents-md-persona-guidance.sh` as an automated test the spec claims doesn't exist. Test 10 (`grep -qiE 'what not to include|not to include'`) is the highest-risk assertion if the restructure inadvertently removes the "What not to include" subsection inside `## Persona authoring`. The CP1 reviewer confirmed all 12 ACs map to UV steps and that UV-5 demotion is appropriate; the only defect is the existing-tests-impacted misstatement.

Resolution path: same as Finding Q-1 — enumerate both scripts as impacted tests, add a Sequence step for pre-commit run.

---

## Testing strategy

### New tests needed

- **Self-application review** (manual, pre-commit, per Finding Q-2 reframe): documented as a Self-application audit table in the implementation retrospective, one row per added/replacement instruction, columns for Necessity Test outcome, positive framing, single-constraint, and load-bearing why-clause. Covers AC-07 and AC-08.
- **Integrity check on `agents.md`** (manual + `git diff` deterministic, per Finding Q-3): verify five preserved sections show zero diff lines; verify body-content paragraph at lines 27–29 retains its two existing sentences and adds exactly two items. Covers AC-06b.

### Existing tests impacted

- **`tests/sdl-workflow/test-agents-md-persona-guidance.sh`** — 12 TAP assertions against `agents.md`. All should pass post-restructure (Test 2 / Test 9 / Test 10 verified by inspection to live inside the preserved `## Persona authoring` section). Pre-commit run required to confirm. *Source: Finding Q-1.*
- **`tests/sdl-workflow/test-reference-integrity.sh`** — walks asset files for path references; no file paths change in this spec. Pre-commit run required to confirm.

### Test infrastructure changes

None.

---

## Threat model determination

**Decision: No threat model required.**

**Rationale:** Documentation-only change. The feature modifies three Markdown files governing how authors compose context assets. No code is added or modified. No new entry points, trust boundaries, auth/access-control changes, data handling changes, or external API surfaces. Security-relevant characteristics: none. The Security agent was not invoked in classification because no signals fired; this is consistent.

Determination made autonomously by the spec-review orchestrator per the user's direction to run the review without checkpoint interruption. User may override by requesting a threat model artifact.

---

## Summary

- **1 blocking finding** (Q-1, confirmed by independent CP1 reviewer): existing TAP tests not enumerated as impacted.
- **5 important findings** (A-1, A-2, A-6, P-2, P-6, Q-2, Q-3): citation convention not declared; sole-consumer workflow heuristic missing; task-compiler conventions not enumerated; AC count over-granular; AC-08 framing combines with Q-2 to need a fixed-location batched audit table; AC-06b lacks deterministic check.
- **9 informational findings**: length/voice/precedent observations and edge-case scopings.

Test reviewer result: FAIL (1 defect, same as Q-1).

Spec result: **fail pending revision.** Blocking finding Q-1 must be resolved before Stage 3 task breakdown.

---

## Revision applied (post-review)

The blocking finding Q-1 was resolved in spec revision: `## Testing strategy → Existing tests impacted` now enumerates `tests/sdl-workflow/test-agents-md-persona-guidance.sh` and `tests/sdl-workflow/test-reference-integrity.sh` with the expectation that both pass post-restructure; a pre-commit run step was added to the Sequence section.

Additional findings applied in the same revision pass:

- **A-2 (sole-consumer workflow heuristic):** Added one sentence to the workflow-routing paragraph in Change 1a pointing to `## Separation of Concerns` as the governing rule for inline-vs-extract decisions on small single-consumer workflows.
- **A-6 (task-compiler conventions):** Added `### Conventions in modified files` subsection under §Technical approach naming heading level, blank-line spacing, citation block placement, imperative voice, and table column counts.
- **P-2 (AC merges):** Merged AC-03 + AC-03b into AC-03 (output-structure paragraph + workflow-routing paragraph as one AC against Change 1a). Merged AC-06a + AC-06b into AC-06 (agents.md restructure as a unit including the body-content paragraph extension and the preserved-sections invariant). AC count dropped from 12 to 10.
- **P-6 + Q-2 combined (AC-08 reframe):** AC-08 now requires a `## Self-application audit` table in the implementation retrospective with five named columns (instruction, Necessity outcome, framing, single-constraint, why-clause status). UV-7 updated accordingly. Replaces the prior "inline or retrospective, whichever the implementer prefers" ambiguity.
- **Q-3 (AC-06b deterministic check):** Folded into AC-06 — verification now includes a `git diff` scoped to the preserved sections with pass criterion zero lines changed. Sequence step 5 makes this deterministic. UV-3 references the diff check.

Informational findings (A-1, A-3, A-4, A-5, P-1, P-3, P-4, P-5, Q-4, Q-5, Q-6, Q-7) were not applied in this revision pass; they are documented in this review for transparency and may be addressed in the implementation pass or carried forward to the corpus-audit follow-up spec.

Post-revision spec gate: **pass**.

Revised spec result: **pass** — ready for Stage 3 task breakdown.
