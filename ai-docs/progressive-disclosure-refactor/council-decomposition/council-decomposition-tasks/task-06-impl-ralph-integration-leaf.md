---
id: task-06
type: implementation
wave: 2
covers: [AC-07]
files_to_create:
  - assets/fbk-docs/fbk-council/ralph-integration.md
test_tasks: [task-01]
completion_gate: "task-01 assertions 33 (ralph-integration.md exists) and 47-50 (ralph-integration.md content terms) pass"
---

## 1. Objective

Creates `assets/fbk-docs/fbk-council/ralph-integration.md` — a new conditional leaf that holds the Ralph Wiggum multi-iteration integration content for the `/fbk-council` skill, loaded only when the orchestrator is running inside a Ralph loop.

## 2. Context

Ralph Wiggum is an Anthropic Claude Code plugin that creates autonomous iteration loops by intercepting Claude's exit and re-feeding the same prompt until a completion marker is detected or `max_iterations` is reached. The `/fbk-council` skill supports being invoked inside such a loop — across iterations the council's discussion state, decisions, and remaining work are persisted in `~/.claude/council-logs/council-state.json`, and each iteration emits one of two HTML-comment status markers (`<!-- COUNCIL_STATUS: CONTINUE -->` or `<!-- COUNCIL_STATUS: COUNCIL_COMPLETE -->`) that Ralph inspects to decide whether to continue or exit.

This content is loaded only when the orchestrator detects Ralph context — by default Ralph mode is not active, so the entire integration guide is conditional. The rewritten SKILL holds only a one-line dispatch plus a one-sentence "When to use Ralph" decision pointer (so the always-relevant decision aid is reachable before the leaf loads); this leaf holds everything else.

The source text for this leaf already exists in the current `assets/skills/fbk-council/SKILL.md` `Ralph Wiggum Integration` section, lines 771–947. The migration is near-verbatim with one small carve-out: the "When to Use Ralph + Council" subsection is **kept** in this leaf because the structural smoke test asserts the literal substring `When to Use Ralph` appears here; the SKILL's one-sentence decision pointer (a separate sentence authored by task-07, not a section title) does not duplicate this section's content.

The leaf is loaded by a single dispatch from the rewritten SKILL of the form: "When invoked inside a Ralph loop, read `assets/fbk-docs/fbk-council/ralph-integration.md` and follow its checkpointing and exit-marker protocol. Detection: state file `~/.claude/council-logs/council-state.json` exists AND its `status` field equals `CONTINUE` AND `iteration` < `max_iterations`, OR explicit invocation via `/ralph-loop`."

The directory `assets/fbk-docs/fbk-council/` may not yet exist when this task runs; `Write` to a path under it creates the parent directory implicitly.

## 3. Instructions

1. Read the current source SKILL at `assets/skills/fbk-council/SKILL.md`, lines 771–947 (the entire `## Ralph Wiggum Integration (Multi-Iteration Mode)` section, from its `## Ralph Wiggum Integration` header through the final `jq` monitoring command at line 946 inclusive).

2. Create `assets/fbk-docs/fbk-council/ralph-integration.md` with the following structure:
   - A top-level `# Ralph Integration` heading.
   - A leading paragraph (2–4 sentences) stating: this leaf is loaded only when the orchestrator detects Ralph mode (state file `~/.claude/council-logs/council-state.json` exists with `status: CONTINUE` and `iteration` below `max_iterations`, or explicit `/ralph-loop` invocation); the leaf documents the multi-iteration checkpointing and exit-marker protocol; if you are reading this without Ralph context you may have been loaded by mistake — verify the state file before continuing.
   - Then copy the source content from current SKILL lines 773–946 verbatim, beginning with the `### What is Ralph Wiggum?` subsection. Preserve every subsection header (`### What is Ralph Wiggum?`, `### How Council + Ralph Works`, `### Usage`, `### Guardrails (Mandatory)`, `### Escape Hatches`, `### State File Format`, `### Best Practices`, `### When to Use Ralph + Council`, `### Monitoring Progress`), every code fence, every diagram, and every literal string.
   - Promote each `###` subsection header by one level to `##` so they read as direct subsections of this leaf rather than sub-subsections of an outer "Ralph Wiggum Integration" header (which no longer exists in the leaf — replaced by the `# Ralph Integration` top-level heading and the leading paragraph).

3. **Required header substrings.** The structural smoke test asserts that the leaf contains the literal substrings `What is Ralph Wiggum`, `Guardrails`, `Escape Hatches`, and `When to Use Ralph` (Tests 47–50 of task-01). After the header-level promotion in step 2, the resulting headers will be `## What is Ralph Wiggum?`, `## Guardrails (Mandatory)`, `## Escape Hatches`, and `## When to Use Ralph + Council` — each contains the asserted substring. Do not rewrite or shorten these headers in a way that drops the asserted substring.

4. Do not modify the diagrams, the JSON state-file schema, the example invocations, or the monitoring commands. The text was authored and validated as part of the current SKILL; this task is a pure content relocation plus a leading paragraph.

5. Do not author dispatch instructions or refer to the SKILL beyond the leading paragraph's note about how the leaf is loaded. The SKILL-side dispatch reference and the one-sentence "When to use Ralph" decision pointer are owned by task-07.

6. Verify completion: run `bash tests/sdl-workflow/test-council-skill-structure.sh`. The leaf-existence assertion (Test 33) and the four `ralph-integration.md` content assertions (Tests 47–50) should now pass. SKILL-side assertions remain failing until task-07 lands; that is expected.

## 4. Files to create/modify

- **Create**: `assets/fbk-docs/fbk-council/ralph-integration.md`

## 5. Test requirements

This implementation task makes the following assertions from `task-01` (`tests/sdl-workflow/test-council-skill-structure.sh`) pass:

- Test 33: `ralph-integration.md` exists and is non-empty.
- Test 47: `ralph-integration.md` contains `What is Ralph Wiggum`.
- Test 48: `ralph-integration.md` contains `Guardrails`.
- Test 49: `ralph-integration.md` contains `Escape Hatches`.
- Test 50: `ralph-integration.md` contains `When to Use Ralph`.

Also makes Test 9 of `tests/sdl-workflow/test-old-locations-empty.sh` (ralph-integration.md exists) pass implicitly by creating the file. Adding the file to the scanned array of `tests/sdl-workflow/test-no-old-path-patterns.sh` is owned by task-03; the file's content must contain no legacy path substrings (`hooks/fbk-sdl-workflow`, `scripts/fbk-pipeline`, `uv run`, `~/.claude/skills/fbk-council/`) to keep that test passing — verbatim copy of the source preserves the modern `python3 "$HOME"/.claude/fbk-scripts/fbk.py` invocation form already used throughout the section.

No new tests are authored by this task.

## 6. Acceptance criteria

- AC-07: `assets/fbk-docs/fbk-council/ralph-integration.md` exists and contains the Ralph overview and diagram, the basic and phased invocation examples, the Guardrails table, the three Escape Hatches, the multi-iteration State File JSON schema, the Best Practices and "When to Use" guidance, and the monitoring command reference.
- task-01 assertions 33 and 47–50 pass when run against the created file.
- The leaf does not contain any of the legacy path substrings scanned by `test-no-old-path-patterns.sh`.

## 7. Model

Sonnet

## 8. Wave

Wave 2
