# instruction-hygiene — Feature Spec

## Problem

Code review detectors receive ~63 discrete instructions from 5 documents at ~3,950 tokens. Research confirms standard Claude Sonnet exhibits linear instruction compliance decay with a practical reliable threshold of ~20 instructions — we're at 3x that limit. An instruction trace identified 6 redundant definitions (dead infrastructure defined in 4 places, string-based classification in 3 places), a scope contradiction (ai-failure-modes.md says "only without specs" but the orchestrator injects it unconditionally), 3 detection heuristics trapped in an orchestrator-only document that agents never see, a compound checklist item combining two distinct concerns, no nit suppression in the Detector (wasting Challenger verification cycles), and no pattern-label handling in the Challenger (labels silently vanish during verification). Additionally, the orchestrator places instructions in the middle of the prompt between the agent system prompt and code files — Anthropic recommends data first/instructions last with a measured 30% improvement from this ordering.

## Goals

**Goals:**
- Reduce per-Detector instruction token volume through deduplication and redundancy removal
- Eliminate 1 scope contradiction and 6 redundant definitions across agent-facing documents
- Make 3 previously-invisible detection heuristics available to Detectors
- Split 1 compound checklist item into 2 separately-actionable items
- Add nit suppression to the Detector agent definition
- Add pattern-label handling to the Challenger agent definition
- Restructure the orchestrator's spawn prompt to place code content before instructions

The combined detection instruction count post-change (~30) still exceeds the ~20 reliable compliance threshold identified by research. This feature improves instruction *quality* (removes contradictions, redundancies, and invisible heuristics); `detector-decomposition` addresses instruction *quantity* by splitting the load across narrow-mandate agents.

**Non-goals:**
- Changing the detector agent topology (that's `detector-decomposition`)
- Adding new checklist items for the 4 identified methodology gaps (unbounded growth, migration idempotency, batch atomicity, intra-function redundancy) — those belong in `detector-decomposition` alongside the restructured agent types
- Changing forced enumeration or output format (that's `detector-decomposition`)
- Adding intent extraction or test reviewer agents (that's `detector-decomposition` and `tiered-detection`)

## User-facing behavior

No user-facing behavior changes. The code review skill invocation (`/fbk-code-review`), the sighting format, the finding format, and the retrospective output are all unchanged. The changes are internal to the instruction documents and the orchestrator's prompt construction.

The expected observable effect is higher detection coverage per round — more checklist items applied per file, fewer missed instances of patterns the methodology already covers. This is not directly visible to the user but is measurable via the evaluation methodology (overlap with filed issues on fresh repos).

## Technical approach

Twelve changes to existing context asset documents. No new files created. No new agent types.

### Deduplicate dead infrastructure (3 documents)

**Current state:** Dead infrastructure is defined independently in:
- `code-review-guide.md` lines 17-18 (section "Dead and disconnected infrastructure")
- `ai-failure-modes.md` item 7 (lines 17-18)
- `quality-detection.md` section "Dead infrastructure" (lines 35-37)

All three are injected into the Detector's context simultaneously.

**Change:** Canonicalize the full definition in `quality-detection.md` (which applies to all reviews). In `ai-failure-modes.md`, replace item 7 with a summary that preserves self-containment and the detection heuristic trigger: "**Dead infrastructure** — code constructs, initializes, or declares components never invoked in the application's runtime path. Check for constructors or factory calls whose return values are assigned but never passed to any consumer (full heuristic in quality-detection.md)." In `code-review-guide.md`, remove the "Dead and disconnected infrastructure" subsection entirely — the behavioral comparison methodology section should not contain detection targets; those belong in the detection target documents.

### Deduplicate string-based classification (2 documents)

**Current state:** String-based error classification is defined in:
- `ai-failure-modes.md` item 11 (line 25)
- `quality-detection.md` section "String-based type discrimination" (lines 47-49)

**Change:** Canonicalize the full definition in `quality-detection.md`. In `ai-failure-modes.md`, replace item 11 with a summary that preserves self-containment and the detection trigger: "**String-based error classification** — error handling branches on string content instead of typed errors, error codes, or sentinel values. Check for string matching operations applied to error messages or type discriminator strings in conditional expressions (full heuristic in quality-detection.md)."

### Deduplicate and split context bypass / silent error discard

**Current state:** `ai-failure-modes.md` item 10 ("Context bypass") and `quality-detection.md` ("Silent error and context discard") overlap on context replacement but diverge on error discard. quality-detection.md combines two distinct concerns in one section: (a) discarding errors without logging/propagating and (b) replacing a caller's context with a background context.

**Change:** Split the quality-detection.md section into two:
- **Silent error discard**: "Flag code that discards errors without logging or propagating them. Detect this when an error return is assigned to `_` or ignored without a comment justifying the discard."
- **Context discard**: "Flag code that replaces a caller-provided context with a fresh background context, discarding cancellation signals, deadlines, or trace propagation. Detect this when a function that receives a context parameter constructs a new context instead of forwarding the caller's."

In `ai-failure-modes.md`, replace item 10 with a summary-with-trigger: "**Context bypass** — functions replace a caller-provided context with a fresh background context, discarding cancellation signals, deadlines, or trace propagation. Check for background-context constructors in functions that receive a context parameter (full heuristic in quality-detection.md)."

### Resolve ai-failure-modes.md scope contradiction

**Current state:** Line 1 says "Use this checklist when reviewing code without specs. When specs are available, use quality-detection.md instead." But the orchestrator (SKILL.md line 40) injects both documents unconditionally. `quality-detection.md` line 1 says "Apply these structural detection targets to all code reviews, whether or not the spec contains design constraints."

**Change:** Remove the conditional scope instruction from `ai-failure-modes.md` line 1. Replace with: "Apply these detection targets to all code reviews." This aligns with the orchestrator's actual behavior (inject unconditionally), matches quality-detection.md's opening line for consistency, and removes the conflicting signal. The conditional routing logic (when specs are available vs not) belongs in SKILL.md's Source of Truth Handling section, where it already exists — not in a document the Detector receives.

### Promote trapped detection heuristics

**Current state:** Three detection heuristics exist only in `existing-code-review.md` (lines 37-57), which is loaded by the orchestrator for the conversational review flow but never injected into Detector spawn prompts:
- Dual-path verification (line 37-38)
- Test-production string alignment (lines 44-46)
- Dead code after field or function removal (lines 56-57)

**Change:** Move these three heuristics to `quality-detection.md` as new structural detection target sections, rewritten into quality-detection.md's established format (imperative + "Detect this when..." heuristic):

**Dual-path verification:**
"Flag operations that have both a bulk path and an incremental path for the same state. Detect this when the bulk path (initial load, full sync) sets fields that the incremental path (event-driven update, delta sync) ignores, or vice versa — this creates state divergence that manifests only under specific execution sequences."

**Test-production string alignment:**
"Flag test assertions that match on string values absent from the production code being tested. Detect this when a test asserts on an error message, status string, or format pattern that does not appear in the production module's source — these are phantom assertions that pass trivially because the production code never produces the matched string."

**Dead code after field or function removal:**
"Flag guards, conditionals, and logging branches that reference values from a removed field or changed function signature. Detect this when a field removal or parameter change leaves downstream checks on the removed value — the check is reachable code that can never evaluate to true."

Remove all six detection heuristic sections from `existing-code-review.md`:
- Dual-path verification (promoted above)
- Sentinel value confusion (duplicates ai-failure-modes.md item 9 — remove without promoting)
- Test-production string alignment (promoted above)
- String-based error classification (canonicalized in dedup step above)
- Dead infrastructure detection (canonicalized in dedup step above)
- Dead code after field or function removal (promoted above)

After removal, `existing-code-review.md` retains its conversational flow guidance, user interaction model, spec co-authoring, scope recognition, finding presentation, and retrospective sections.

### Split compound checklist item 12

**Current state:** `ai-failure-modes.md` item 12 combines two distinct detection concerns in one checklist item: (a) test input data that violates domain constraints (semantically incoherent fixtures) and (b) tests that pass through mock permissiveness rather than correct scenario modeling. These are separately detectable and separately actionable.

**Change:** Split item 12 into two items:
- Item 12: "**Semantically incoherent test fixtures** — Test input data satisfies the type system but violates domain constraints, producing false-passing scenarios. Check for test fixtures where related fields should be consistent by domain rules but are set independently with mismatched values."
- Item 13: "**Mock permissiveness masking constraints** — Tests pass because mocks do not validate constraints the production code relies on. Check for mocks that accept any input where the production dependency enforces domain rules (e.g., type discriminators, referential integrity, value ranges)."

Renumber current item 13 (dead conditional guards) to item 14.

### Add nit suppression to Detector

**Current state:** The Detector agent definition (`fbk-code-review-detector.md`) has no instruction to avoid producing nits. The Challenger rejects them (per code-review-guide.md line 88), but the Detector generates them, consuming Challenger attention.

**Change:** Add to the Detector agent definition, in the "Scope discipline" section: "Exclude nits (naming, formatting, style with no behavioral or maintainability impact) from sightings."

### Add pattern-label handling to Challenger and format templates

**Current state:** The Detector assigns cross-cutting pattern labels (agent definition line 11-12), but the Challenger has no instruction to preserve, validate, or carry forward labels during verification. Additionally, neither the Sighting Format nor the Finding Format templates in `code-review-guide.md` contain a `Pattern label:` field, so the label has no structural slot in the output schema agents follow.

**Change:**
1. Add two instructions to the Challenger agent definition, within the "Verified finding" section:
   - "Preserve the Detector's cross-cutting pattern label in each verified finding."
   - "When verification reveals that sightings sharing a pattern label are independent issues, note the label correction."
2. Add `Pattern label:` as an optional field to the Sighting Format template in `code-review-guide.md` (after the `Source of truth:` field).
3. Add `Pattern label:` as an optional field to the Finding Format template in `code-review-guide.md` (after the `Evidence:` field).

### Restructure orchestrator spawn prompt ordering

**Current state:** SKILL.md step 1 constructs the Detector spawn prompt as: "target code scope + source of truth + behavioral comparison instructions + structural detection targets + linter output." This places instructions in the middle (between system prompt and code content). Anthropic research measures a 30% improvement from placing data first and instructions last.

**Change:** Rewrite SKILL.md step 1 to embed the correct ordering directly:

Step 1 changes from:
> "Spawn Detector with target code scope + source of truth + behavioral comparison instructions + structural detection targets from quality-detection.md + linter output (if available). Remind the Detector to tag each sighting with its detection source."

To:
> "Spawn Detector with: target code file contents first, then linter output (if available), then source of truth + behavioral comparison instructions + structural detection targets from quality-detection.md last. Instruct the Detector to tag each sighting with its detection source."

Rewrite step 3 similarly:

Step 3 changes from:
> "Spawn Challenger with sightings + code + 'verify or reject each sighting with evidence'"

To:
> "Spawn Challenger with: target code file contents first, then sightings to verify, then verification instructions last."

No separate meta-instruction needed. The ordering is intrinsic to the step definitions, eliminating the risk of a meta-instruction contradicting step-level ordering.

### Ensure quality-detection.md is loaded in the conversational review path

**Current state:** SKILL.md line 10 instructs the orchestrator to read ai-failure-modes.md but does not mention quality-detection.md. quality-detection.md is only referenced in the context of Detector spawn prompts (SKILL.md line 40). In the conversational review flow (standalone path via existing-code-review.md), the orchestrator may never load quality-detection.md, meaning it lacks the structural detection targets when reviewing code directly.

**Change:** Add quality-detection.md to SKILL.md's initial read instructions (line 10 area): "Read `fbk-docs/fbk-design-guidelines/quality-detection.md` for structural detection targets applicable to all code reviews." This ensures both documents are loaded in every review path — Detector spawn flow and conversational flow alike.

### Align code-review-guide.md with SKILL.md and scope changes

**Current state:** code-review-guide.md has two sections that will contradict the other changes in this spec:
- Orchestration Protocol (lines 93-101): Describes step 1 payload without the new content-first ordering, diverging from the rewritten SKILL.md step 1.
- Source of Truth Handling (lines 110-112): Says "No spec available: Use the AI failure mode checklist... Supplement with the structural detection targets from quality-detection.md." This implies a hierarchy (checklist primary, quality-detection supplementary) that contradicts the new unconditional scope in ai-failure-modes.md line 1.

**Change:** Update both sections:
- Orchestration Protocol step 1: Align wording with the SKILL.md step 1 rewrite (code content first, instructions last).
- Source of Truth Handling "No spec available": Change to "Use both the AI failure mode checklist and the structural detection targets from quality-detection.md." Removes the primary/supplementary hierarchy to match the unconditional injection model.

These are small text alignments to a document already in scope (code-review-guide.md is being modified for dead infrastructure subsection removal).

### Integration seam declaration

- [ ] ai-failure-modes.md → quality-detection.md: deduplicated items use summaries with detection heuristic triggers and parenthetical reference to quality-detection.md section name; ai-failure-modes.md remains self-contained (Detector can detect the pattern from the summary alone without loading quality-detection.md)
- [ ] existing-code-review.md → quality-detection.md: promoted heuristics rewritten into quality-detection.md's established format (imperative + "Detect this when..." heuristic)
- [ ] SKILL.md steps 1 and 3: prompt component ordering embedded directly in step definitions, consistent with Anthropic's data-first/instructions-last recommendation
- [ ] SKILL.md steps 1/3 ↔ code-review-guide.md Orchestration Protocol: step definitions in SKILL.md are authoritative; code-review-guide.md Orchestration Protocol section must not contradict the ordering
- [ ] Detector agent definition → Challenger agent definition: pattern-label convention (Detector assigns, Challenger preserves; Challenger corrects when evidence contradicts grouping)

## Testing strategy

### New tests needed

Shell tests verify structural shape (sections exist, items split, documents loaded) not specific wording. Content correctness is verified via UV steps and code review.

- Shell test: Verify `ai-failure-modes.md` line 1 contains "Apply these detection targets" (positive) AND does not contain "When specs are available, use quality-detection.md instead" (absence) — covers AC-03.
- Shell test: Verify `quality-detection.md` contains section headings "Dual-path verification", "Test-production string alignment", "Dead code after field or function removal" AND each section contains "Detect this when" — covers AC-04 (presence + format).
- Shell test: Verify `existing-code-review.md` does not contain "Dual-path verification", "Sentinel value confusion", "String-based error classification", "Dead infrastructure detection", "Dead code after field or function removal", "test-production" — covers AC-04 (removal side, all 6 sections).
- Shell test: Verify `fbk-code-review-detector.md` contains "Exclude nits" AND "cross-cutting pattern label" — covers AC-05 + seam 4 Detector end.
- Shell test: Verify `fbk-code-review-challenger.md` contains "pattern label" AND ("label correction" or "independent issues") — covers AC-06.
- Shell test: Verify `ai-failure-modes.md` items 7, 10, 11 each reference "quality-detection.md" — covers AC-01, AC-02, AC-11 (dedup references exist).
- Shell test: Verify `ai-failure-modes.md` contains 14 numbered items AND item 12 contains "Semantically incoherent" AND item 13 contains "Mock permissiveness" — covers AC-09.
- Shell test: Grep the following agent-facing documents for each detection target name to confirm no target was lost during moves — covers AC-10. Agent-facing documents: `ai-failure-modes.md`, `quality-detection.md`, `code-review-guide.md`, `fbk-code-review-detector.md`, `fbk-code-review-challenger.md`. Target name list (grep substrings):
  - From ai-failure-modes.md: `bare literal`, `hardcoded coupling`, `never connected`, `name-assertion mismatch`, `surface-level fix`, `non-enforcing test`, `dead infrastructure`, `comment-code drift`, `sentinel`, `context bypass`, `string-based error`, `semantically incoherent`, `mock permissiveness`, `dead conditional`
  - From quality-detection.md: `mixed logic and side effects`, `ambient state`, `non-importable`, `multi-responsibility`, `caller re-implementation`, `composition opacity`, `parallel collection`, `dead infrastructure`, `semantic drift`, `silent error discard`, `context discard`, `string-based type discrimination`, `dual-path verification`, `test-production string`, `dead code after field`
- Shell test: Verify SKILL.md step 1 contains "contents first" or equivalent ordering language — covers AC-07.
- Shell test: Verify `quality-detection.md` contains "Silent error discard" and "Context discard" as separate sections — covers AC-11.
- Shell test: Verify SKILL.md initial read instructions reference both "ai-failure-modes" and "quality-detection" — covers AC-12.
- Shell test: Verify `code-review-guide.md` Source of Truth Handling does not contain "Supplement with" hierarchy language — covers AC-13.

### Existing tests impacted

- `tests/sdl-workflow/test-code-review-guide-extensions.sh` Test 3 — asserts `code-review-guide.md` contains "dead infrastructure" or "disconnected infrastructure". Will fail after the "Dead and disconnected infrastructure" subsection is removed. **Action**: Remove Test 3 or redirect to assert on `quality-detection.md`.
- `tests/sdl-workflow/test-code-review-guide-extensions.sh` Test 7 — asserts `code-review-guide.md` Source of Truth Handling contains "quality-detection". **Unaffected** — the modified section retains the quality-detection reference.
- `tests/sdl-workflow/test-detection-scope.sh` Test 15 — asserts `existing-code-review.md` contains "dual-path". Will fail after promotion to quality-detection.md. **Action**: Redirect to assert on `quality-detection.md`.
- `tests/sdl-workflow/test-detection-scope.sh` Test 16 — asserts `existing-code-review.md` contains "sentinel value". Will fail after removal (duplicate of ai-failure-modes.md item 9). **Action**: Remove test (covered by ai-failure-modes.md content tests).
- `tests/sdl-workflow/test-detection-scope.sh` Test 17 — asserts `existing-code-review.md` contains "string alignment" or "test-production". Will fail after promotion. **Action**: Redirect to `quality-detection.md`.
- `tests/sdl-workflow/test-detection-scope.sh` Test 18 — asserts `existing-code-review.md` contains "string-based error". Will fail after removal (canonicalized in quality-detection.md). **Action**: Remove test (covered by quality-detection.md content tests).
- `tests/sdl-workflow/test-detection-scope.sh` Test 19 — asserts `existing-code-review.md` contains "dead infrastructure". Will fail after removal (canonicalized in quality-detection.md). **Action**: Remove test (covered by quality-detection.md content tests).
- `tests/sdl-workflow/test-detection-scope.sh` Test 1 — asserts ai-failure-modes.md has >= 11 numbered items. Will still pass (14 >= 11) but is subsumed by the new exact-count test (AC-09). **Action**: Update threshold to >= 14 or remove in favor of the new test.
- `tests/sdl-workflow/test-detection-scope.sh` Test 20 — asserts `existing-code-review.md` contains "severity" or "critical first". **Unaffected** — the "Finding presentation" section survives all heuristic removals.
- `tests/sdl-workflow/test-code-review-structural.sh` Test 23 — asserts ai-failure-modes.md has >= 11 items. Same as above. **Action**: Update threshold to >= 14.

### Test infrastructure changes

None — existing shell test infrastructure is sufficient.

### User verification steps

UV-1: Open `ai-failure-modes.md` → item 7 is a summary with detection trigger and quality-detection.md reference, not a full standalone definition
UV-2: Open `ai-failure-modes.md` → line 1 says "Apply these detection targets to all code reviews" with no conditional scope instruction
UV-3: Open `quality-detection.md` → contains "Dual-path verification", "Test-production string alignment", and "Dead code after field or function removal" sections in standard format
UV-4: Open `existing-code-review.md` → no longer contains detection heuristic sections (sentinel, string-based, dead infrastructure, dual-path, test-production string, dead code after removal)
UV-5: Open `fbk-code-review-detector.md` → "Scope discipline" section contains nit exclusion instruction
UV-6: Open `fbk-code-review-challenger.md` → "Verified finding" section contains two pattern-label instructions (preserve + correct)
UV-7: Run code review on a test fixture → observe Detector spawn prompt has code content before instructions
UV-8: Open `ai-failure-modes.md` → items 12, 13, 14 are three separate items (incoherent fixtures, mock permissiveness, dead conditional guards)
UV-9: (Human-triggered, post-release) Run code review on the Project B evaluation repo. Compare against evaluation baseline: 53 total verified (13 major, 32 minor, 1 info), 6/24 maintainer issue overlap (25%). A drop of >25% in any severity category or reduced issue overlap across 2 runs indicates regression. Single-run variance is expected due to LLM non-determinism — compare 2 runs before concluding.

## Documentation impact

### Project documents to update
- `CHANGELOG.md` — add entry under v0.3.5 for instruction hygiene changes
- `README.md` — check whether detection methodology is referenced; update if the scope contradiction resolution changes any user-facing claims

### New documentation to create
None.

## Acceptance criteria

- AC-01: `ai-failure-modes.md` item 7 (dead infrastructure) is a summary with the detection heuristic trigger ("Check for constructors or factory calls...") and a parenthetical reference to `quality-detection.md`. The summary is self-contained: the Detector can detect dead infrastructure from the summary alone.
- AC-02: `ai-failure-modes.md` item 11 (string-based error classification) is a summary with the detection trigger ("Check for string matching operations...") and a parenthetical reference to `quality-detection.md`. Same self-containment requirement as AC-01.
- AC-03: `ai-failure-modes.md` line 1 does not contain a conditional scope instruction. The opening line is a single unconditional imperative consistent with quality-detection.md's opening line.
- AC-04: `quality-detection.md` contains the three promoted heuristics (dual-path verification, test-production string alignment, dead code after field removal) in the standard structural target format (imperative + "Detect this when..."). `existing-code-review.md` no longer contains any of the six removed detection heuristic sections.
- AC-05: `fbk-code-review-detector.md` contains a nit suppression instruction in the scope discipline section.
- AC-06: `fbk-code-review-challenger.md` contains two pattern-label instructions in the verified finding section: one for preservation, one for correction. `code-review-guide.md` Sighting Format and Finding Format templates both contain a `Pattern label:` field.
- AC-07: SKILL.md steps 1 and 3 specify prompt component ordering with code content first and instructions last. No separate meta-instruction exists that could contradict the step-level ordering.
- AC-08: Per-Detector instruction token volume is reduced relative to pre-change state. Verified by inspection: compare word counts of ai-failure-modes.md + quality-detection.md + code-review-guide.md before and after implementation. Not covered by automated tests — token reduction is a consequence of the structural changes verified by AC-01 through AC-07.
- AC-09: `ai-failure-modes.md` contains 14 numbered items (original items 1-11 with summaries for 7 and 11, split item 12 into 12+13, renumbered original 13 to 14).
- AC-10: Every detection target name that existed pre-change exists in at least one agent-facing document post-change. No detection capability lost during moves.

- AC-11: `quality-detection.md` "Silent error and context discard" section is split into two separate sections: "Silent error discard" and "Context discard". `ai-failure-modes.md` item 10 is a summary with detection trigger and parenthetical reference to quality-detection.md, same pattern as items 7 and 11.
- AC-12: SKILL.md initial read instructions include both `ai-failure-modes.md` and `quality-detection.md`, ensuring both are loaded in every review path including the conversational flow.
- AC-13: `code-review-guide.md` Orchestration Protocol and Source of Truth Handling sections do not contradict SKILL.md step definitions or ai-failure-modes.md scope. Orchestration Protocol step 1 reflects content-first ordering. Source of Truth Handling "No spec available" uses both documents without a primary/supplementary hierarchy.

## Open questions

None — all changes are to existing documents with clear current state and target state.

## Dependencies

- No external dependencies.
- Depends on: none (this is the first feature in the detection-accuracy project).
- Depended on by: `detector-decomposition` (v0.4.0) assumes the cleaned-up instruction set from this feature.
