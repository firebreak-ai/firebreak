---
id: task-03
type: implementation
wave: 1
covers: [AC-02, AC-04, AC-05, AC-06]
files_to_modify:
  - assets/skills/fbk-spec-review/SKILL.md
test_tasks: [task-01]
completion_gate: "task-01 assertions T3, T4, T4b, T9, T11b, T12, T13, T14, T15 pass"
---

## Objective

Refactor `assets/skills/fbk-spec-review/SKILL.md` to remove duplicated workflow prose (classification narrative, threat-model decision flow, transition decision tree and summarize-and-compact directive) while preserving all operational glue (frontmatter, `$ARGUMENTS` resolution, gate-script invocations, `/fbk-council` invocation, test-reviewer Agent Teams spawn, finding-synthesis write directive, retrospective write directive, exit prompt, chained `/breakdown` invocation).

## Context

The `fbk-spec-review` skill loads `review-perspectives.md` unconditionally on its first instruction (line 9). Workflow protocol restated in the skill body is therefore duplicated on the same load path. Spec §4.3 enumerates three duplicated sections to remove from this file; spec §4.2 enumerates the operational-glue sections that must remain.

**Must be retained verbatim per spec §4.2 (do NOT remove):**

- YAML frontmatter (lines 1-7).
- `Read \`.claude/fbk-docs/fbk-sdl-workflow/review-perspectives.md\`` pointer (line 9).
- `## Argument` section (lines 11-13): `$ARGUMENTS` empty-check ask-the-user fallback.
- `## Load spec` section (lines 15-17): spec read + missing-file report.
- `## Prior stage gate` section (lines 19-23): gate-script invocation block + failure handling.
- `## Re-run check` section (lines 25-27): the user-warning prompt "If `<feature-name>-review.md` already exists, warn the user it will be replaced entirely, then proceed." This is a skill-side operational concern; the user-facing warning is emitted by the skill before any work is done. **Must NOT be removed.**
- `## Council invocation` section (lines 33-39): the `/fbk-council` invocation directive with prompt-framing bullets.
- `## Finding synthesis` section (lines 41-45): the `Write ai-docs/...-review.md` directive with the `Perspectives:` metadata line and the `testing strategy` keyword. **Must NOT be removed** — this is the actual `Write` directive that produces the artifact, and the `testing strategy` keyword is load-bearing for `tests/sdl-workflow/test-review-integration.sh` Test 4 (per spec §4.2 and §5 T9).
- `## Test strategy review` section (lines 47-53): the test-reviewer Agent Teams spawn directive with checkpoint 1 context and PASS/FAIL handling.
- `## Gate invocation` section (lines 64-75): the `review-gate` invocation block.
- `## Retrospective` section (lines 77-79): the Stage 2 retrospective write directive and read-then-write file-handling rule. **Must NOT be removed.**
- The literal `/breakdown <feature-name>` chained invocation (currently embedded at line 89).
- The exit-prompt sentence `Would you like to proceed to task breakdown?` — currently at line 87 inside the `## Transition` decision-tree narrative; must survive in some form (T15 requires it).

**Must be removed per spec §4.3:**

- The `## Classification` section body (line 31): the entire decision narrative paragraph "Analyze the spec and project context using the classification signals and SDL concerns table from `review-perspectives.md`. Determine which agents to invoke and in which mode (solo / discussion / full council). Present the selection with a one-line rationale per agent. Proceed unless the user adjusts." This duplicates `review-perspectives.md` §"Classification process" (lines 5-19). The skill keeps the load-the-guide pointer; the classification logic itself reads from the guide.
- The `## Threat model determination` section body (lines 57-62): the entire summarize / ask / record-decision flow + yes/no branch instructions. This duplicates `review-perspectives.md` §"Threat model determination" (lines 63-78).
- The `## Transition` section body (lines 83-89): the "There are N blocking findings..." decision tree, the "all resolved → proceed to breakdown" prompt, and the "Before invoking the next stage..." summarize-and-compact directive. The decision-tree and prompt prose are already in guide §"Transition" (lines 114-121); the summarize-and-compact direction is consolidated into the same guide section by task-06. The literal `/breakdown <feature-name>` chained invocation is retained.

**Operational decision for the exit prompt and threat-model section:**

The current `## Threat model determination` body contains the user-facing question `Does this feature need a threat model?`. T3 of the test asserts this phrase is absent from the skill (consolidated to guide). The body is removed entirely; the section heading may be removed or retained — choose to remove the heading too, since no operational content remains under it. The threat-model question is asked from the guide-loaded protocol.

T15 asserts the skill `does` contain `Would you like to proceed to task breakdown?`. The skill must therefore retain this prompt sentence as a single operational instruction. The current `## Transition` body contains this prompt embedded in the decision tree. Remove the decision-tree prose and the summarize-and-compact directive, and replace with a minimal `## Transition` section that contains only: a one-line directive that on resolved blocking findings asks the user "Would you like to proceed to task breakdown?" and on agreement invokes `/breakdown <feature-name>`.

## Instructions

Read the current file (`assets/skills/fbk-spec-review/SKILL.md`) before editing. The line ranges below match the current state of the file as of compilation time.

1. **Site 1 — Remove the `## Classification` section body (current lines 29-31).**

   Locate the section starting at line 29. The section currently reads:

   ```
   ## Classification

   Analyze the spec and project context using the classification signals and SDL concerns table from `review-perspectives.md`. Determine which agents to invoke and in which mode (solo / discussion / full council). Present the selection with a one-line rationale per agent. Proceed unless the user adjusts.
   ```

   Remove the entire heading and body (3 lines plus surrounding blank lines). The classification logic now lives only in `review-perspectives.md` §"Classification process".

   **Completion checks:**
   - `grep -qvF 'Present the selection with' assets/skills/fbk-spec-review/SKILL.md` succeeds.
   - `grep -qvF 'classification signals and SDL concerns table' assets/skills/fbk-spec-review/SKILL.md` succeeds.

2. **Site 2 — Remove the `## Threat model determination` section (current lines 55-62).**

   Locate the section starting at line 55. The section currently reads:

   ```
   ## Threat model determination

   Summarize the feature's security-relevant characteristics: data touched, trust boundaries crossed, new entry points, auth/access control changes.

   Ask the user: "Does this feature need a threat model?" Record the decision and rationale in the review document regardless of the answer.

   - **If yes**: Read `.claude/fbk-docs/fbk-sdl-workflow/threat-modeling.md`. Guide creation of `ai-docs/<feature-name>/<feature-name>-threat-model.md`.
   - **If no**: Record decision and rationale (e.g., "No new trust boundaries, no data handling changes"). Security findings from the Security agent still appear in the review.
   ```

   Remove the entire heading and body. The threat-model determination flow now lives only in `review-perspectives.md` §"Threat model determination". The `## Gate invocation` section (which conditionally accepts the threat-model file as the third gate-script argument via `[ai-docs/<feature-name>/<feature-name>-threat-model.md]`) remains untouched.

   **Completion checks:**
   - `grep -qvF 'Does this feature need a threat model?' assets/skills/fbk-spec-review/SKILL.md` succeeds.
   - `grep -qvF 'Summarize the feature' assets/skills/fbk-spec-review/SKILL.md` succeeds (no match for this opening phrase of the threat-model summary).
   - `grep -qF 'review-gate' assets/skills/fbk-spec-review/SKILL.md` succeeds (gate-invocation retained).

3. **Site 3 — Replace the `## Transition` section body (current lines 81-89).**

   The section currently reads:

   ```
   ## Transition

   If blocking findings exist: "There are N blocking findings. Would you like to revise the spec to address them, or accept with documented rationale?"

   If the user accepts blocking findings, record the rationale and risk owner in the review document before advancing.

   If all resolved: "The review is structurally complete. Would you like to proceed to task breakdown?"

   Before invoking the next stage: confirm all artifacts are written to disk, then summarize (feature name, number of findings by severity, threat model decision, gate result). Compact context before invoking the next skill. Then invoke `/breakdown <feature-name>`.
   ```

   Replace the entire body (lines 83-89) with:

   ```
   ## Transition

   On resolved blocking findings, ask: "Would you like to proceed to task breakdown?" If the user agrees, invoke `/breakdown <feature-name>`.
   ```

   The decision-tree narrative, the "If the user accepts blocking findings..." record-rationale instruction, and the "Before invoking the next stage..." summarize-and-compact directive are all removed (consolidated into `review-perspectives.md` §"Transition" by task-06). The `Would you like to proceed to task breakdown?` prompt is retained (T15 requires it). The literal `/breakdown <feature-name>` chained invocation is retained (T14 requires `/breakdown`).

   **Completion checks:**
   - `grep -qvF 'There are N blocking findings' assets/skills/fbk-spec-review/SKILL.md` succeeds.
   - `grep -qvF 'Before invoking the next stage' assets/skills/fbk-spec-review/SKILL.md` succeeds.
   - `grep -qvF 'Compact context before invoking the next skill' assets/skills/fbk-spec-review/SKILL.md` succeeds.
   - `grep -qF 'Would you like to proceed to task breakdown?' assets/skills/fbk-spec-review/SKILL.md` succeeds.
   - `grep -qF '/breakdown' assets/skills/fbk-spec-review/SKILL.md` succeeds.

4. **Must-NOT-be-removed sections** (verify these survive untouched after the edits above):

   - YAML frontmatter (lines 1-7) — first line `---`, `description:` field present.
   - `Read \`.claude/fbk-docs/fbk-sdl-workflow/review-perspectives.md\`` pointer.
   - `## Argument`, `## Load spec`, `## Prior stage gate` sections — `$ARGUMENTS` resolution + spec read + gate-script invocation.
   - `## Re-run check` section verbatim.
   - `## Council invocation` section verbatim — contains `/fbk-council`.
   - `## Finding synthesis` section verbatim — contains `Write ai-docs/...-review.md` directive AND the `testing strategy` keyword.
   - `## Test strategy review` section verbatim — contains `test-reviewer` and Agent Teams / checkpoint 1 context.
   - `## Gate invocation` section verbatim — contains `review-gate` invocation.
   - `## Retrospective` section verbatim — Stage 2 write directive + read-then-write rule.

   **Completion checks for retentions:**
   - `head -n 1 assets/skills/fbk-spec-review/SKILL.md` returns exactly `---`.
   - `grep -qF 'description:' assets/skills/fbk-spec-review/SKILL.md` succeeds.
   - `grep -qF '$ARGUMENTS' assets/skills/fbk-spec-review/SKILL.md` succeeds.
   - `grep -qF '/fbk-council' assets/skills/fbk-spec-review/SKILL.md` succeeds.
   - `grep -qF 'test-reviewer' assets/skills/fbk-spec-review/SKILL.md` succeeds.
   - `grep -qF 'testing strategy' assets/skills/fbk-spec-review/SKILL.md` succeeds.
   - `grep -qF 'review-gate' assets/skills/fbk-spec-review/SKILL.md` succeeds.
   - `grep -qF '## Re-run check' assets/skills/fbk-spec-review/SKILL.md` succeeds.
   - `grep -qF '## Retrospective' assets/skills/fbk-spec-review/SKILL.md` succeeds.

5. **Run task-01's test to verify post-refactor state:**

   ```
   bash tests/sdl-workflow/test-skill-guide-dedup.sh
   ```

   The assertions covering this file (T3, T4, T4b, T9, T12, T13, T14, T15) must all report `ok`. T11b's guide-side assertion (specifically the `` Before invoking `/breakdown` `` substring) is covered by task-06; do not be alarmed if it still reports `not ok` until task-06 lands. T3, T4, T4b specifically must flip from `not ok` (pre-refactor) to `ok` (post-refactor) as a direct result of this task's edits.

## Files to create/modify

- `assets/skills/fbk-spec-review/SKILL.md` (modify)

Do not modify any other file. Do not edit `review-perspectives.md` (that is task-06's scope).

## Test requirements

This task makes the following task-01 assertions flip from `not ok` to `ok`:

- T3 (AC-02) — `Does this feature need a threat model?` absent from `fbk-spec-review/SKILL.md`.
- T4 (AC-02) — `There are N blocking findings` absent from `fbk-spec-review/SKILL.md`.
- T4b (AC-02) — `Present the selection with` absent from `fbk-spec-review/SKILL.md`.

This task must keep the following task-01 assertions reporting `ok`:

- T9 (AC-04) — `/fbk-council` AND `test-reviewer` AND `testing strategy` all present in `fbk-spec-review/SKILL.md`.
- T10 (AC-04) — `review-gate` present in `fbk-spec-review/SKILL.md`.
- T12 (AC-04) — first line `---` and `description:` present in `fbk-spec-review/SKILL.md`.
- T13 (AC-04) — `$ARGUMENTS` present in `fbk-spec-review/SKILL.md`.
- T14 (AC-04) — `/breakdown` present in `fbk-spec-review/SKILL.md`.
- T15 (AC-04) — `Would you like to proceed to task breakdown?` present in `fbk-spec-review/SKILL.md`.

Pre-existing tests asserting `fbk-spec-review/SKILL.md` keywords (`tests/sdl-workflow/test-review-integration.sh` T3-T8 on `test-reviewer`, `Agent Teams` / `teammate`, `checkpoint 1`, `testing strategy`, `council`, `review-gate` / `gate invocation`, and the council → test-reviewer → gate positional ordering; `tests/sdl-workflow/test-council-skill-structure.sh` Test 61 on `/fbk-council`) must continue to pass without modification. The retentions enumerated in Step 4 ensure this.

## Acceptance criteria

- AC-02: `fbk-spec-review/SKILL.md` no longer contains the duplicated classification narrative, threat-model decision flow, or transition decision tree.
- AC-04: Operational glue is preserved — frontmatter, `$ARGUMENTS` resolution, prior-stage gate-script invocation, `/fbk-council` invocation, test-reviewer Agent Teams spawn, finding-synthesis write directive (with `testing strategy` keyword), gate-script invocation, retrospective write directive, exit prompt, chained `/breakdown` invocation.
- AC-05: Pre-existing `test-review-integration.sh` and `test-council-skill-structure.sh` assertions on this file continue to pass.
- task-01 assertions T3, T4, T4b flip to `ok`. T9, T10, T12, T13, T14, T15 remain `ok`.

## Model

Haiku

## Wave

Wave 1
