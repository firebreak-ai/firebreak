# SDL Skill / Guide Dedup

Child spec for Finding 4 of `ai-docs/progressive-disclosure-refactor/progressive-disclosure-refactor-spec.md`.

Applies the parent spec's per-load-path Necessity Test and asset-type taxonomy (Decision 8, "topmost where always relevant" / single owner per instruction) to three SDL skill/guide pairs that currently duplicate workflow prose across both files.

---

## Problem

Three SDL pipeline skills each load their corresponding workflow guide unconditionally on the skill's first instruction:

- `assets/skills/fbk-spec/SKILL.md` → `assets/fbk-docs/fbk-sdl-workflow/feature-spec-guide.md`
- `assets/skills/fbk-spec-review/SKILL.md` → `assets/fbk-docs/fbk-sdl-workflow/review-perspectives.md`
- `assets/skills/fbk-implement/SKILL.md` → `assets/fbk-docs/fbk-sdl-workflow/implementation-guide.md`

Because the guide always loads when the skill fires, every workflow protocol described in the guide is on-context already. The skills additionally restate that protocol inline — wave loop steps, escalation protocol, threat-model decision flow, transition decision tree, final verification, team shutdown — producing two copies of the same instructions on the same load path. The duplication is largest in `fbk-implement` (≈40 lines), present but smaller in `fbk-spec-review` (threat-model determination + transition), and minimal in `fbk-spec` (transition flow only).

The result is twofold: per-load-path Necessity is violated (the second copy adds no new behavior), and the asset-type taxonomy is violated (the skill body holds workflow protocol content that belongs in the guide).

## Goals

**In scope:**

- Remove duplicated workflow prose from the three SDL skill files. Workflow protocol becomes single-sourced in the guide.
- Skills retain their operational glue: frontmatter, `$ARGUMENTS` / path resolution, gate-script invocations, `/fbk-council` invocation, native-task spawn-prompt template (in `fbk-implement`), chained skill invocations.
- Preserve every observable behavior: every gate runs, every council/test-reviewer invocation fires, every transition prompt is asked, every escalation cap holds, every output schema stays identical.

**Non-goals:**

- No changes to workflow semantics. No step is reordered, added, or removed.
- No rewrites of existing guide content. Guides receive only additive extensions required by progressive-disclosure consolidation (specifically: the summarize-and-compact transition step relocated from skill bodies into the guides that own the transition workflow). No existing guide prose is reworded or restructured.
- No `fbk-breakdown` work. Parent-spec verification confirmed `fbk-breakdown` does not exhibit duplication; it is excluded.
- No cross-route resolution (Finding 5 territory). The three guides each have a single parent skill; cross-route validity is not in question.
- No asset-graph-detector authoring. Verification uses a feature-specific structural test in the precedent of `council-decomposition`.
- No CLI / script changes. `fbk.py spec-gate`, `review-gate`, `breakdown-gate` are unchanged.
- No agent persona changes. No changes to `assets/agents/*.md`.

## User-facing behavior

Every observable surface is preserved by the operational-glue assertions in §5 and the three full-pipeline manual smoke verifications UV-1 / UV-2 / UV-3. Full LLM-orchestrated pipeline equivalence is not exercisable by the TAP shell-test infrastructure; the shell-test sentinels assert structural preservation, and the manual UV runs verify end-to-end behavior at gate.

- `/spec <name>` runs the same gate, asks the same "Would you like to move to spec review?" prompt, invokes `/spec-review` with the same argument.
- `/spec-review <name>` runs the same prior-stage gate, classifies via the same SDL concerns table, invokes `/fbk-council` with the same prompts, spawns the test-reviewer agent at the same point in the flow, asks the threat-model question with the same wording, runs the same review-gate script, asks the same blocking-findings transition prompt, invokes `/breakdown` with the same argument.
- `/implement <name>` runs the same breakdown-gate, performs the same Team Setup checks, executes waves with the same step ordering (test tasks → test compile check → implementation tasks → per-wave verification → wave checkpoint), follows the same escalation protocol with the same caps (2 escalations / 3 in-session retries / 10-minute unresponsiveness), runs the same final verification, writes the same retrospective, performs the same team shutdown.

The only observable difference is reduced token load on every invocation: the skill body shrinks; the guide is unchanged.

## Technical approach

### 4.1 Final structure

No new files. No file moves. No directory creation. Three skill files are edited in place; three guide files are unchanged.

```
assets/skills/fbk-spec/SKILL.md          (edited; ~30 lines, down from 53)
assets/skills/fbk-spec-review/SKILL.md   (edited; ~50 lines, down from 89)
assets/skills/fbk-implement/SKILL.md     (edited; ~50 lines, down from 97)
tests/sdl-workflow/test-skill-guide-dedup.sh  (new — see §5)
```

### 4.2 What stays in each skill

Every skill retains exactly this skeleton, with no workflow-protocol prose between sections:

- YAML frontmatter (description, argument-hint).
- One-line directive to read the guide.
- Conditional read directives for related guides where they exist (e.g., `fbk-spec` → corrective-workflow / brownfield-spec).
- Argument handling: `$ARGUMENTS` resolution, path computation, "ask the user" fallback when empty.
- Gate-script invocation block (the actual `python3 .../fbk.py <gate-name> ...` command).
- The chained skill invocation that ends the stage (`/spec-review $ARGUMENTS`, `/breakdown $ARGUMENTS`).

`fbk-spec-review` additionally retains:
- The `/fbk-council` invocation directive (skill is the only place where the council is actually called).
- The test-reviewer Agent Teams spawn directive (skill is the only place where the agent is actually spawned, with checkpoint 1 context).
- The `## Re-run check` user-warning prompt at current line 27 ("If `<feature-name>-review.md` already exists, warn the user it will be replaced entirely, then proceed."). Skill-side operational concern: the user-facing warning is emitted by the skill before any work is done; the guide states the policy at lines 97-99 but does not own the runtime emission.
- The `## Finding synthesis` operational directive at current lines 41-45 ("Write `ai-docs/<feature-name>/<feature-name>-review.md`. Start the file with a `Perspectives:` metadata line... Organize findings by SDL concern, not by agent. Tag each finding with severity..."). Skill-side concern: this is the actual `Write` directive that produces the artifact. The corresponding guide section (`review-perspectives.md` lines 80-95) describes the document structure as reader-facing reference; the skill's directive is the runtime producer. Retention also preserves the literal `testing strategy` keyword that `tests/sdl-workflow/test-review-integration.sh` Test 4 asserts.

`fbk-spec` and `fbk-spec-review` additionally retain:
- The `## Retrospective` skill-side write directive (`fbk-spec/SKILL.md:44-46`, `fbk-spec-review/SKILL.md:77-80`). Skill-side concern: this is the actual `Write` directive plus the read-then-write file-handling rule. The retrospective-guide describes the file's contents and stage structure; the skill emits the write at its boundary. Same reasoning extends to `fbk-implement/SKILL.md:91-93`.

`fbk-implement` additionally retains:
- The `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` env-flag check (operational gate, not workflow content).
- The native-task spawn-prompt template — the literal `Task file: ai-docs/$FEATURE/$FEATURE-tasks/task-NN-name.md / Read that file as your sole context and execute it. / Before your turn ends, send a work summary message...` block. This is concrete `Task` tool plumbing; the orchestrator is the only caller of the `Task` tool, so the prompt body lives at that boundary.
- The `task.json` read + JSON-validity check (operational gate).

### 4.3 What is removed from each skill

For each pair, the skill drops these sections / sentences. Section names below are current SKILL section headings.

**`fbk-spec/SKILL.md` (current 53 lines → ~30 lines):**

- `## Authoring Loop` (lines 26-30): the "co-author iteratively" instruction and the "refuse to write code" instruction. Both already in `feature-spec-guide.md` §"Iterative Authoring" (lines 82-92). Skill keeps the read-the-guide pointer; the guide handles the rest.
- `## Gate` decision narrative (lines 40-42): "If the gate fails: report ... If the gate passes: present the semantic criteria ... Verify that the testing strategy enumerates all callers ... If the user is satisfied: ask 'Would you like to move to spec review?'" — already in guide §"Verification Gate" (137-141) and §"Transition" (147-153). Skill keeps the gate-script invocation block; removes the surrounding decision prose.
- `## Transition` (lines 48-52): the "Before invoking the next stage: confirm all artifacts are written to disk, then summarize ... Compact context before invoking the next skill." directive is workflow-protocol content (it describes the stage→stage transition behavior). It is consolidated into `feature-spec-guide.md` §"Transition" as one additive step (see §4.3a below). Skill keeps only the literal `/spec-review $ARGUMENTS` invocation line.

**`fbk-spec-review/SKILL.md` (current 89 lines → ~50 lines):**

- `## Classification` narrative (lines 30-31): "Analyze the spec and project context using the classification signals and SDL concerns table from `review-perspectives.md`. Determine which agents to invoke and in which mode ... Present the selection with a one-line rationale per agent. Proceed unless the user adjusts." — already in guide §"Classification process" (5-19). Skill keeps the load-the-guide pointer; the classification logic itself reads from the guide.
- `## Threat model determination` (lines 56-62): the entire "summarize security characteristics, ask the user the question, record decision and rationale" decision flow is in guide §"Threat model determination" (63-78). Skill removes the duplicated prose; if a single concrete instruction remains operationally needed at the skill level (e.g., the gate-script invocation depends on whether a threat model file was created), the skill retains only the conditional file-existence note that gates the third gate-script argument.
- `## Transition` (lines 81-89): the "blocking-findings → revise vs accept" decision tree, the "all resolved → proceed to breakdown" prompt, and the "before invoking the next stage: confirm artifacts, summarize, compact" direction. The decision-tree and prompt prose are already in guide §"Transition" (114-121); the summarize-and-compact direction is consolidated into the same guide section as one additive step (see §4.3a below). Skill keeps only the literal `/breakdown <feature-name>` invocation line.

The keywords currently asserted by `tests/sdl-workflow/test-review-integration.sh` (T3-T8: `test-reviewer`, `Agent Teams` / `teammate`, `checkpoint 1`, `testing strategy`, `council`, `review-gate` / `gate invocation`, and the council → test-reviewer → gate positional ordering) all survive in the operational-glue sections that remain. The `testing strategy` keyword survives via the retained `## Finding synthesis` operational directive (per §4.2). Verified during refactoring; tests pass without modification.

**`fbk-implement/SKILL.md` (current 97 lines → ~50 lines):**

- `## Team Setup` (lines 37-42): the `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` check + max-wave-width spawn instruction is duplicated with guide §"Team Setup" (1-12). Skill retains the env-flag operational check (it is a gate-like invocation, not narrative — only the orchestrator at the skill boundary actually performs the check); the env-flag prerequisite line at `implementation-guide.md:9` is removed (see §4.3a). The wave-width selection logic and team-lead role description remain in the guide.
- `## Wave Loop` Steps 1-7 (lines 44-69): every step's narrative — "Read this wave's test task list", "Set each task's `status` to `in_progress`", "wait for all to reach completed status", "Set each completed task's `status` to `complete`", "verify new tests exist and compile", "Tests are expected to fail", "create native tasks for this wave's implementation tasks", per-wave verification list, wave checkpoint summary — duplicated with guide §"Wave Execution" (15-33), §"Status Tracking" (37-49), §"Per-Wave Verification" (126-137), §"Wave Checkpoint" (143-153). Skill retains exactly two operational artifacts: (a) the literal `Task file: ai-docs/$FEATURE/$FEATURE-tasks/task-NN-name.md / Read that file as your sole context...` spawn-prompt template, since this is the concrete `Task` tool prompt body; (b) a one-line "for each wave, follow the protocol in the implementation guide" pointer.
- `## Escalation Protocol` (lines 71-80): the 6-step numbered list is duplicated with guide §"Escalation Protocol" (157-170). Skill removes the numbered list and retains only the one-line pointer.
- `## Final Verification` (lines 82-89): the structural / semantic checklist is duplicated with guide §"Final Verification" (174-187). Skill removes the bullets and retains only the one-line pointer.
- `## Retrospective` (lines 91-93): the "factual data, upstream traceability, failure attribution" enumeration is duplicated with guide §"Retrospective" (191-219). Skill removes the field summary and retains only the literal write-Stage-4-section directive plus the read-then-write file-handling rule (since the file-handling rule is operational at the skill boundary).
- `## Team Shutdown` (lines 95-97): the 3-step list is duplicated with guide §"Team Shutdown" (223-229). Skill removes the steps and retains only the one-line pointer plus the literal user-prompt sentence "Would you like to review the implementation with /code-review?" (since the chained-prompt is the skill's exit hand-off).

### 4.3a Guide edits

Three guide edits, all narrow and progressive-disclosure-driven. No existing guide prose is reworded except as listed.

**Additive transition steps (consolidating skill-side summary-and-compact prose):**

- `assets/fbk-docs/fbk-sdl-workflow/feature-spec-guide.md` §"Transition" — insert one step before the existing "If agreed: invoke `/spec-review <feature-name>`" line: *"Before invoking `/spec-review`: confirm all artifacts are written to disk; summarize the completed spec (feature name, artifact path, key decisions); compact context."*
- `assets/fbk-docs/fbk-sdl-workflow/review-perspectives.md` §"Transition" — insert one step before the existing "If agreed: invoke `/breakdown <feature-name>`" line: *"Before invoking `/breakdown`: confirm all artifacts are written to disk; summarize (feature name, number of findings by severity, threat model decision, gate result); compact context."*

**Removal (consolidating bidirectional env-flag duplication to skill side):**

- `assets/fbk-docs/fbk-sdl-workflow/implementation-guide.md:9` — remove the sentence *"Require the `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` flag before spawning any teammates. If the flag is not set, stop and inform the user."* The env-flag check is a gate-like operational invocation owned by `fbk-implement/SKILL.md`. Surrounding `## Team Setup` prose (wave-width selection, team-lead role description) is unchanged.

`fbk-breakdown` is out of scope (parent-spec verification confirmed it does not exhibit the full duplication pattern); its abbreviated transition prose at `fbk-breakdown/SKILL.md:97` stays as is.

### 4.4 Module touch policy

Three skill files are refactored (duplicated prose removed); two guides receive additive transition steps; one guide has a single line removed. Six touched files:

- [ ] `assets/skills/fbk-spec/SKILL.md` — refactor per §4.2 + §4.3.
- [ ] `assets/skills/fbk-spec-review/SKILL.md` — refactor per §4.2 + §4.3.
- [ ] `assets/skills/fbk-implement/SKILL.md` — refactor per §4.2 + §4.3.
- [ ] `assets/fbk-docs/fbk-sdl-workflow/feature-spec-guide.md` — extend per §4.3a.
- [ ] `assets/fbk-docs/fbk-sdl-workflow/review-perspectives.md` — extend per §4.3a.
- [ ] `assets/fbk-docs/fbk-sdl-workflow/implementation-guide.md` — extend (line removal) per §4.3a.

### 4.5 Integration seam

At each skill→guide seam, the skill owns operational glue (gate-script invocations, env-flag check, `Task file:` spawn-prompt template, chained skill invocations) and the guide owns workflow narrative (decision flows, classification process, transition prompts, wave-loop steps, escalation protocol, final-verification checklists). The structural test in §5 asserts the partition holds. LLM-behavioral seam coverage — the orchestrator actually following the guide-loaded protocol on a live pipeline — is verified manually via UV-1, UV-2, UV-3.

### 4.6 Runtime values preserved

Every literal runtime string in the current SKILL files is preserved. The structural test in §5 asserts the load-bearing subset (gate-script invocations, env-flag, spawn-prompt template, exit prompts, chained-skill invocations); other strings are preserved by the implementer reading the existing file before editing.

The classification rationale-presentation phrasing ("Present the classification with rationale and proceed") is owned solely by `review-perspectives.md` lines 17-19; the skill no longer carries it. The orchestrator emits the rationale from the guide-loaded process on every invocation.

## Testing strategy

### New tests needed

- Structural test (`tests/sdl-workflow/test-skill-guide-dedup.sh`, TAP-format shell, auto-discovered by CI):

  - **T1 (AC-01):** `assets/skills/fbk-spec/SKILL.md` does not contain the phrase "If the gate fails:" (sentinel for the duplicated gate decision flow).
  - **T1b (AC-01):** `assets/skills/fbk-spec/SKILL.md` does not contain the phrase "Verify that the testing strategy enumerates all callers" (paraphrase-catcher for the duplicated gate-pass narrative; phrase remains in guide).
  - **T2 (AC-01):** `assets/skills/fbk-spec/SKILL.md` does not contain the phrase "Refuse to write code" (sentinel for the duplicated authoring-loop prose; the equivalent guide phrase remains).
  - **T3 (AC-02):** `assets/skills/fbk-spec-review/SKILL.md` does not contain the phrase "Does this feature need a threat model?" (sentinel for the duplicated threat-model decision flow; phrase remains in guide).
  - **T4 (AC-02):** `assets/skills/fbk-spec-review/SKILL.md` does not contain the phrase "There are N blocking findings" (sentinel for the duplicated transition decision tree; phrase remains in guide).
  - **T4b (AC-02):** `assets/skills/fbk-spec-review/SKILL.md` does not contain the phrase "Present the selection with" (sentinel for the duplicated classification rationale-presentation prose; phrase ownership moved entirely to guide per §4.6).
  - **T5 (AC-03):** `assets/skills/fbk-implement/SKILL.md` does not contain "Step 1 — Test tasks" or "Step 2 — Test compilation check" wave-loop step headings (sentinels for duplicated wave-loop steps; equivalents remain in guide).
  - **T5b (AC-03):** `assets/skills/fbk-implement/SKILL.md` does not contain the phrase "Tests are expected to fail" (paraphrase-catcher for the duplicated step-2 narrative; phrase remains in guide).
  - **T6 (AC-03):** `assets/skills/fbk-implement/SKILL.md` does not contain "Cap: 2 escalation attempts per task" (sentinel for the duplicated escalation cap; phrase remains in guide).
  - **T7 (AC-04):** `assets/skills/fbk-implement/SKILL.md` *does* contain `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` (operational env-flag check must remain).
  - **T8 (AC-04):** `assets/skills/fbk-implement/SKILL.md` *does* contain the literal `Task file:` spawn-prompt template marker (operational glue must remain).
  - **T9 (AC-04):** `assets/skills/fbk-spec-review/SKILL.md` *does* contain `/fbk-council` (council invocation must remain), `test-reviewer` (test-reviewer spawn must remain), and `testing strategy` (operational sentinel pinning the `## Finding synthesis` retention; load-bearing for `test-review-integration.sh` Test 4).
  - **T9b (AC-04):** `assets/skills/fbk-implement/SKILL.md` *does* contain `review the implementation with /code-review` (operational sentinel pinning the exit-prompt; load-bearing for `test-code-review-skill.sh` Tests 15-16).
  - **T10 (AC-04):** Each skill *does* contain its respective gate-script command substring (`spec-gate`, `review-gate`, `breakdown-gate` respectively).
  - **T11a (AC-01):** `assets/fbk-docs/fbk-sdl-workflow/feature-spec-guide.md` contains all of `If the gate fails:`, `Refuse to write code`, and `Before invoking \`/spec-review\`` (positive guide-side assertions paired with T1, T2, and the §4.3a additive transition step).
  - **T11b (AC-02):** `assets/fbk-docs/fbk-sdl-workflow/review-perspectives.md` contains all of `Does this feature need a threat model?`, `There are N blocking findings`, `Present the classification with`, and `Before invoking \`/breakdown\`` (positive guide-side assertions paired with T3, T4, T4b, and the §4.3a additive transition step).
  - **T11c (AC-03):** `assets/fbk-docs/fbk-sdl-workflow/implementation-guide.md` contains all of `Step 1 — Test tasks`, `Cap: 2 escalation attempts per task`, and `No dead code introduced` (positive guide-side assertions paired with T5, T6, and the final-verification structural list).
  - **T11d (AC-03 / AC-04):** `assets/fbk-docs/fbk-sdl-workflow/implementation-guide.md` does NOT contain `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` (consolidation to skill-side operational gate per §4.3a).
  - **T12 (AC-04):** Each of the three skills (`fbk-spec/SKILL.md`, `fbk-spec-review/SKILL.md`, `fbk-implement/SKILL.md`) opens with a `---` line and contains a `description:` field within its frontmatter (frontmatter operational-glue preservation).
  - **T13 (AC-04):** `assets/skills/fbk-spec/SKILL.md` contains `$ARGUMENTS`; `assets/skills/fbk-spec-review/SKILL.md` contains `$ARGUMENTS`; `assets/skills/fbk-implement/SKILL.md` contains `FEATURE=$ARGUMENTS` (argument-resolution operational glue).
  - **T14 (AC-04):** `assets/skills/fbk-spec/SKILL.md` contains `/spec-review $ARGUMENTS`; `assets/skills/fbk-spec-review/SKILL.md` contains `/breakdown` (chained-skill invocation operational glue).
  - **T15 (AC-04):** `assets/skills/fbk-spec/SKILL.md` contains `Would you like to move to spec review?`; `assets/skills/fbk-spec-review/SKILL.md` contains `Would you like to proceed to task breakdown?` (exit-prompt operational glue; pairs with T9b which covers `fbk-implement` exit prompt).

  Each assertion fits in a single shell line (`grep -q` / `grep -qv`) with a TAP `ok` / `not ok` line. Test runs in <1 second.

  **AC-05 verification path.** AC-05 ("All pre-existing tests pass without modification") has no new sentinel. AC-05 is verified procedurally by re-running the enumerated existing tests post-refactor; the pre-existing tests are themselves the assertion. UV-5 captures the manual run.

  **UV-1 / UV-2 / UV-3 schema rationale.** UV-1, UV-2, and UV-3 are full LLM-orchestrated pipeline runs and are not exercisable by the TAP shell-test infrastructure (the harness runs Python gate scripts against fixtures, not LLM behavioral chains). They are manual smoke verifications at gate. They have no corresponding entry in "New tests needed" because the failure modes they catch (orchestrator hand-off correctness, prompt-emission verbatim) require a live pipeline.

  **Integration-seam coverage rationale.** The 10 declared seams in §4.5 are LLM-behavioral (skill loads guide, orchestrator follows guide-loaded protocol). They are not automatable in the current TAP infrastructure. UV-1, UV-2, UV-3 are the seam verification path.

### Existing tests impacted

- `tests/sdl-workflow/test-implementation-pipeline.sh` — asserts `implementation-guide.md` contains hook retry cap, fresh-agent rule, and foreground-execution rule. Guide is unchanged; tests pass without modification. **Verified, no edit required.**
- `tests/sdl-workflow/test-review-integration.sh` — T3-T8 assert `fbk-spec-review/SKILL.md` contains keyword sentinels (`test-reviewer`, `testing strategy`, `Agent Teams` / `teammate`, `council`, `review-gate` / `gate invocation`) and the council → test-reviewer → gate positional ordering. Skill retains every sentinel in the operational-glue sections that survive the refactor (the `testing strategy` keyword is pinned by the §4.2 retention of `## Finding synthesis` and by §5 T9); positional ordering is preserved (the rewrite does not reorder the operational-glue sequence). **Verified, no edit required, but T3-T8 are part of the smoke verification at gate.**
- `tests/sdl-workflow/test-code-review-skill.sh` — Tests 15-16 grep `fbk-implement/SKILL.md` for `review the implementation` / `code review` / `would you like` / `ask.*review`. The exit prompt at current line 97 ("Would you like to review the implementation with /code-review?") satisfies them; §4.2 retains it verbatim and §5 T9b pins it. **Verified, no edit required.**
- `tests/sdl-workflow/test-council-skill-structure.sh` — Test 61 greps `fbk-spec-review/SKILL.md` for `/fbk-council`. §4.2 retains the `/fbk-council` invocation and §5 T9 pins it. **Verified, no edit required.**
- `tests/sdl-workflow/test-no-old-path-patterns.sh`, `tests/sdl-workflow/test-code-review-integration.sh`, `tests/sdl-workflow/test-new-persona-agents.sh` — surface-mention the same path strings via grep but do not assert on the skill body content this spec edits. **Verified, no edit required.**

No existing test file is modified.

### Test infrastructure changes

None. New test uses the existing TAP-format shell-test pattern already in `tests/sdl-workflow/`. CI auto-discovers via the existing glob `for test in tests/sdl-workflow/test-*.sh`.

### Mocking justifications

None. All assertions are static `grep` against committed files. No mocks; the real files are the test subjects.

### User verification steps

- **UV-1:** Run `/spec sample-feature` against an existing or new feature directory → spec gate runs; on pass, the user is asked "Would you like to move to spec review?"; on yes, `/spec-review sample-feature` invokes. Identical observable flow to today.
- **UV-2:** Run `/spec-review sample-feature` against a passing spec → classification is presented with per-agent rationale; `/fbk-council` fires; test-reviewer spawns with checkpoint 1 context; threat-model question is asked; review-gate runs; on resolved blocking findings, the user is asked "Would you like to proceed to task breakdown?"; on yes, `/breakdown sample-feature` invokes. Identical observable flow to today.
- **UV-3:** Run `/implement sample-feature` against a compiled feature with a wave structure → breakdown-gate runs; team spawns at max wave width; wave 1 test tasks are created with the literal `Task file:` spawn template; per-wave verification fires; wave checkpoint asks for commit; remaining waves execute; final verification runs; retrospective is written; team shuts down. Identical observable flow to today.
- **UV-4:** Run `tests/sdl-workflow/test-skill-guide-dedup.sh` directly → all 22 assertions pass (T1, T1b, T2, T3, T4, T4b, T5, T5b, T6, T7, T8, T9, T9b, T10, T11a, T11b, T11c, T11d, T12, T13, T14, T15).
- **UV-5:** Run the existing tests enumerated under "Existing tests impacted" — `test-implementation-pipeline.sh`, `test-review-integration.sh`, `test-code-review-skill.sh`, `test-council-skill-structure.sh` — all assertions pass without modification.

UV-1, UV-2, UV-3 map to AC-04 (operational behavior preserved end-to-end via manual smoke). UV-4 maps to AC-01, AC-02, AC-03, AC-04 (duplicated prose removed; operational glue pinned). UV-5 maps to AC-05 (pre-existing tests pass).

## Documentation impact

### Project documents to update

Release tasks (performed on completion; not gate-checked):

- `CHANGELOG.md` — add entry under the next release section: `Changed: deduplicated SDL skill/guide pairs (fbk-spec, fbk-spec-review, fbk-implement); workflow protocol now single-sourced in the guide files. Skills retain operational glue only. Two guides receive additive transition steps; one guide has the env-flag prerequisite line consolidated to the skill-side operational gate.`
- `ai-docs/progressive-disclosure-refactor/progressive-disclosure-refactor-spec.md` — append `**State:** IMPLEMENTED <date>` line to the Finding 4 entry per the convention used for Finding 1.

### New documentation to create

- None.

### Documents reviewed for impact, no change required

- `assets/fbk-docs/fbk-sdl-workflow.md` — references the three guides correctly; routing table is accurate post-refactor.
- `README.md` — reviewed; no path references to skill-body content. No change.

## Acceptance criteria

- **AC-01:** `assets/skills/fbk-spec/SKILL.md` no longer contains the duplicated authoring-loop prose, gate decision narrative, or transition narrative; the equivalent prose remains in `assets/fbk-docs/fbk-sdl-workflow/feature-spec-guide.md`.
- **AC-02:** `assets/skills/fbk-spec-review/SKILL.md` no longer contains the duplicated classification narrative, threat-model decision flow, or transition decision tree; the equivalent prose remains in `assets/fbk-docs/fbk-sdl-workflow/review-perspectives.md`.
- **AC-03:** `assets/skills/fbk-implement/SKILL.md` no longer contains the duplicated wave-loop steps, status-tracking transitions, escalation-protocol numbered list, final-verification list, retrospective field summary, or team-shutdown list; the equivalent prose remains in `assets/fbk-docs/fbk-sdl-workflow/implementation-guide.md`.
- **AC-04:** Operational glue is preserved in every skill: frontmatter, `$ARGUMENTS` resolution, gate-script invocations, `/fbk-council` invocation (`fbk-spec-review`), test-reviewer Agent Teams spawn (`fbk-spec-review`), env-flag check (`fbk-implement`), `Task file:` spawn-prompt template (`fbk-implement`), chained skill invocations (`/spec-review`, `/breakdown`), exit-prompt sentences.
- **AC-05:** All pre-existing tests in `tests/sdl-workflow/` pass without modification — specifically `test-implementation-pipeline.sh`, `test-review-integration.sh` (T3-T8 on `fbk-spec-review/SKILL.md` keywords + positional ordering), `test-code-review-skill.sh` (Tests 15-16 on `fbk-implement/SKILL.md` exit prompt), and `test-council-skill-structure.sh` (Test 61 on `fbk-spec-review/SKILL.md` `/fbk-council` reference).
- **AC-06:** New `tests/sdl-workflow/test-skill-guide-dedup.sh` exists, is auto-discovered by CI, and all 22 assertions pass.

Each AC is independently verifiable by a single command (grep / shell test / file diff). No vague qualities. CHANGELOG and parent-spec State-line updates are tracked under Documentation impact as release tasks, not as gate-checked acceptance criteria.

## Open questions

None.

## Dependencies

- No new external libraries, APIs, or features.
- Reads on existing assets only: `feature-spec-guide.md`, `review-perspectives.md`, `implementation-guide.md` are unchanged in this spec.
- Existing CI test glob `tests/sdl-workflow/test-*.sh` discovers the new test automatically; no workflow file edit needed.
- No precedent dependency on `asset-graph-detectors`. The parent spec lists it as a preceding child spec; `council-decomposition` shipped without it by writing a feature-specific structural test, and this spec follows that precedent.

---

## Decisions resolved during scoping

The following meaningful design decisions were resolved before drafting and are captured here for traceability (they are not open questions):

- **Asset-graph-detectors prerequisite skipped.** `council-decomposition` precedent: write a feature-specific structural test instead of blocking on the general-purpose detectors.
- **Spawn-prompt template stays in `fbk-implement/SKILL.md`.** It is concrete `Task` tool plumbing; the orchestrator is the only caller of the `Task` tool, so the prompt body lives at that boundary rather than in the guide.
- **All three pairs in one child spec.** Parent spec frames Finding 4 as a single child; the edits are independent (no shared-file conflicts), so co-locating the three pair edits is the lowest-overhead structure.
- **`fbk-breakdown` Transition prose asymmetry left in place.** `assets/skills/fbk-breakdown/SKILL.md:97` retains a shorter "Before invoking the next stage..." Transition pattern matching the prose this refactor removes from `fbk-spec` and `fbk-spec-review`. Parent-spec verification confirmed `fbk-breakdown` does not exhibit the full sectional duplication this finding addresses; the asymmetry is acknowledged and out of scope for Finding 4. A future audit may standardize all four skills' Transition patterns as a separate child spec.
- **Read-then-write retrospective rule cross-skill duplication out of scope.** The phrase "Read the file before writing to preserve existing content from prior stages" appears in all three skills plus `retrospective-guide.md:1`. Resolving this requires a cross-skill retrospective-routing decision that is not Finding 4's scope. Surfaced for the parent spec's tracking; addressed in a future child spec or future-work note.
