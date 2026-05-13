---
id: task-05
type: implementation
wave: 2
covers: [AC-06]
files_to_create:
  - assets/fbk-docs/fbk-council/compaction-recovery.md
test_tasks: [task-01]
completion_gate: "task-01 assertions 32 (compaction-recovery.md exists) and 43-46 (compaction-recovery.md content terms) pass"
---

## 1. Objective

Creates `assets/fbk-docs/fbk-council/compaction-recovery.md` — a new conditional leaf that holds the READ-side of the compaction-recovery protocol, loaded when `recovery-check` returns `recovering: true` after auto-compaction has truncated the orchestrator's context.

## 2. Context

Long council sessions can trigger Claude's auto-compaction, which discards in-context discussion transcripts. The `/fbk-council` skill survives this via a write-then-read pattern: each phase writes its progress to `~/.claude/council-logs/council-state.json` (the WRITE side, always-relevant, stays inline in the rewritten SKILL); on session resume, the orchestrator runs `recovery-check` and — if the JSON says `recovering: true` — reads this leaf to learn the recovery protocol (the READ side, only relevant after a compaction actually occurred).

This split is structurally critical: if the recovery-protocol READ content also lived in this leaf instead of inline, the orchestrator would not load the leaf until after compaction, but compaction would have already discarded the context where it learned to load the leaf. The READ/WRITE split is what breaks that cycle. **This leaf must NOT contain the per-phase `session-state checkpoint` invocation pattern** — that is the WRITE side and lives inline in the rewritten SKILL (authored separately in task-07, item 5a of the SKILL's nineteen-item structure).

The source text for the READ-side content already exists in the current `assets/skills/fbk-council/SKILL.md` `Compaction Resilience` section, lines 420–497. The migration is selective: copy the recovery protocol, recovery acknowledgment phrase, Session State Footer markdown templates, the JSON schema reference, and the cleanup commands; **omit** the `Phase-Level Checkpointing` subsection's `session-state checkpoint` bash invocation (lines 423–432 of the source) which is the WRITE-side and stays inline in the SKILL.

The leaf is loaded by a single dispatch from the rewritten SKILL of the form: "Before initializing a new session, run `python3 \"$HOME\"/.claude/fbk-scripts/fbk.py session-state recovery-check`. If `recovering` is `true` in the JSON output, read `assets/fbk-docs/fbk-council/compaction-recovery.md` and resume from the returned `current_phase`."

The directory `assets/fbk-docs/fbk-council/` may not yet exist when this task runs; `Write` to a path under it creates the parent directory implicitly.

## 3. Instructions

1. Read the current source SKILL at `assets/skills/fbk-council/SKILL.md`, lines 420–497 (the `### Compaction Resilience` section). Identify and capture the following sub-blocks separately:
   - **Recovery Protocol** — the numbered protocol steps stating: run `recovery-check`; if `recovering: true`, resume from `current_phase` and skip phases listed in `completed_phases`; acknowledge recovery in output with the phrase "Resumed from checkpoint after context compaction" (lines 438–441 of source).
   - **Session State Footer markdown templates** — both variants: the `<!-- COUNCIL_STATUS: CONTINUE -->` template and the `<!-- COUNCIL_STATUS: COUNCIL_COMPLETE -->` template (lines 443–470 of source).
   - **State Persistence JSON schema** — the documented schema for `~/.claude/council-logs/council-state.json` (lines 472–484 of source).
   - **Session Cleanup commands** — both `session-manager unregister` and the on-task-completion `session-state cleanup` block (lines 486–496 of source).

2. Identify and **omit** the following sub-block from the migration: the `**Phase-Level Checkpointing**` subsection (lines 423–432 of source) including the `session-state checkpoint` bash invocation. This content is the WRITE side and stays inline in the rewritten SKILL (task-07's responsibility, item 5a). Also omit the standalone "Session ID Persistence" sentence at line 434 and the "Compaction Detection" sentence at line 436 — both are SKILL-inline material superseded by the rewritten SKILL's recovery dispatch one-liner.

3. Create `assets/fbk-docs/fbk-council/compaction-recovery.md` with the following structure, in this order:
   - A top-level `# Compaction Recovery` heading.
   - A leading paragraph (2–4 sentences) stating: this leaf is loaded only when `recovery-check` returns `recovering: true`, indicating the orchestrator's previous context was discarded by auto-compaction; the leaf contains only the READ side of the recovery protocol — the WRITE side (per-phase `session-state checkpoint`) lives inline in the SKILL because it must run on every phase regardless of whether a compaction has occurred.
   - A `## Recovery Protocol` subsection containing the recovery-protocol numbered steps from step 1 above. Preserve the literal acknowledgment phrase `Resumed from checkpoint after context compaction` verbatim (one of the few load-bearing literal strings in this section).
   - A `## Session State Footer` subsection containing both markdown template blocks (CONTINUE and COUNCIL_COMPLETE) verbatim. Preserve the literal HTML comments `<!-- COUNCIL_STATUS: CONTINUE -->` and `<!-- COUNCIL_STATUS: COUNCIL_COMPLETE -->` exactly — the structural smoke test asserts on the substrings `COUNCIL_STATUS: CONTINUE` and `COUNCIL_STATUS: COUNCIL_COMPLETE`.
   - A `## State Persistence` subsection containing the JSON schema for `~/.claude/council-logs/council-state.json`. Preface it with one sentence stating that this schema is the READ-side reference (the SKILL inline checkpoint instruction populates the same file using the same fields).
   - A `## Session Cleanup` subsection containing the two cleanup invocations (`session-manager unregister` and the on-task-completion `session-state cleanup` block).

4. The required section header in the leaf must be exactly `## Recovery Protocol` and exactly `## Session State Footer` so that `grep -F 'Recovery Protocol'` and `grep -F 'Session State Footer'` (Tests 43 and 44 of task-01) succeed.

5. Do not author dispatch instructions or refer to the SKILL beyond the leading paragraph's note about the WRITE side staying inline. The SKILL-side dispatch reference is owned by task-07.

6. Verify completion: run `bash tests/sdl-workflow/test-council-skill-structure.sh`. The leaf-existence assertion (Test 32) and the four `compaction-recovery.md` content assertions (Tests 43–46) should now pass. SKILL-side assertions remain failing until task-07 lands; that is expected.

## 4. Files to create/modify

- **Create**: `assets/fbk-docs/fbk-council/compaction-recovery.md`

## 5. Test requirements

This implementation task makes the following assertions from `task-01` (`tests/sdl-workflow/test-council-skill-structure.sh`) pass:

- Test 32: `compaction-recovery.md` exists and is non-empty.
- Test 43: `compaction-recovery.md` contains `Recovery Protocol`.
- Test 44: `compaction-recovery.md` contains `Session State Footer`.
- Test 45: `compaction-recovery.md` contains `COUNCIL_STATUS: CONTINUE`.
- Test 46: `compaction-recovery.md` contains `COUNCIL_STATUS: COUNCIL_COMPLETE`.

Also makes Test 8 of `tests/sdl-workflow/test-old-locations-empty.sh` (compaction-recovery.md exists) pass implicitly by creating the file. Adding the file to the scanned array of `tests/sdl-workflow/test-no-old-path-patterns.sh` is owned by task-03; the file's content must contain no legacy path substrings (`hooks/fbk-sdl-workflow`, `scripts/fbk-pipeline`, `uv run`, `~/.claude/skills/fbk-council/`) to keep that test passing — the migration source uses the modern `python3 "$HOME"/.claude/fbk-scripts/fbk.py` invocation form throughout, so straight verbatim copy of the relevant subblocks satisfies this constraint.

No new tests are authored by this task.

## 6. Acceptance criteria

- AC-06: `assets/fbk-docs/fbk-council/compaction-recovery.md` exists and contains the recovery protocol steps, the Session State Footer markdown templates (CONTINUE and COUNCIL_COMPLETE), the State Persistence JSON schema, and the Session Cleanup commands.
- task-01 assertions 32 and 43–46 pass when run against the created file.
- The leaf does **not** contain a `session-state checkpoint` bash invocation (the WRITE side lives inline in the SKILL — authored by task-07). Verifiable by `grep -F 'session-state checkpoint' assets/fbk-docs/fbk-council/compaction-recovery.md` returning no matches.
- The leaf does not contain any of the legacy path substrings scanned by `test-no-old-path-patterns.sh` (`hooks/fbk-sdl-workflow`, `scripts/fbk-pipeline`, `uv run`, `~/.claude/skills/fbk-council/`).

## 7. Model

Sonnet

## 8. Wave

Wave 2
