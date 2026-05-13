---
id: task-04
type: implementation
wave: 2
covers: [AC-04]
files_to_create:
  - assets/fbk-docs/fbk-council/consensus-failure.md
test_tasks: [task-01]
completion_gate: "task-01 assertions 31 (consensus-failure.md exists) and 34-42 (consensus-failure.md content terms) pass"
---

## 1. Objective

Creates `assets/fbk-docs/fbk-council/consensus-failure.md` — a new conditional leaf that merges the existing decision-protocol and conflict-resolution sections from `assets/skills/fbk-council/SKILL.md` into a single file dispatched from the rewritten SKILL when Round 1 of Phase 3 ends without consensus.

## 2. Context

The `/fbk-council` skill is being decomposed: content that does not need to load on every invocation moves to conditional leaves under `assets/fbk-docs/fbk-council/`. This leaf consolidates two sections that are part of the same code path — when the discussion fails to converge, the orchestrator first applies the decision protocol (weighted voting for reasoning tasks, evidence-based consensus for knowledge tasks); if the decision protocol surfaces an unresolved conflict between agents, the orchestrator then applies the resolution-by-conflict-type rules. Merging both into one leaf eliminates leaf-to-leaf dispatch chains and removes ambiguity about where the second-stage routing fires.

The source text for this leaf already exists in the current `assets/skills/fbk-council/SKILL.md`:
- Decision Protocol section: lines 500–554 (`## Decision Protocol` heading through the end of the Decision Documentation schema, before the `---` divider at line 556).
- Conflict Resolution section: lines 558–613 (`## Conflict Resolution` heading through the end of the Conflict Documentation markdown block, before the `---` divider at line 615).

Both sections are migrated verbatim — the content has been authored and validated; this task only relocates and merges. A short leading paragraph is added at the top of the leaf to state that both sections live in this leaf and to describe the in-leaf sequencing (decision protocol first; conflict resolution applied if the decision protocol surfaces unresolved conflict).

The leaf is loaded by a single dispatch from the rewritten SKILL (authored separately in task-07) of the form: "When Round 1 of Phase 3 ends without consensus, read `assets/fbk-docs/fbk-council/consensus-failure.md` and apply the decision protocol for the task type; if the decision protocol surfaces an unresolved conflict between agents, apply the resolution-by-conflict-type rules in the same leaf."

The directory `assets/fbk-docs/fbk-council/` does not yet exist on `main`. Creating any of the three new leaf files implicitly creates the directory; either this task or one of the parallel sibling leaf tasks (task-05, task-06) will be the first to create it. No explicit `mkdir` step is required — `Write` to a path under the new directory creates the parent directory.

## 3. Instructions

1. Read the current source SKILL at `assets/skills/fbk-council/SKILL.md`. Capture the exact text of lines 500 through 554 (the `Decision Protocol` section, beginning with the `## Decision Protocol` header and continuing through the end of the Decision Documentation markdown block on line 554). Capture the exact text of lines 558 through 613 (the `Conflict Resolution` section, beginning with the `## Conflict Resolution` header and continuing through the end of the Conflict Documentation markdown block on line 613).

2. Create `assets/fbk-docs/fbk-council/consensus-failure.md` with the following structure, in this order:
   - A top-level `# Consensus Failure` heading.
   - A leading paragraph (2–4 sentences) stating: this leaf is loaded when Round 1 of Phase 3 ends without consensus; it contains both the decision protocol (always applied first to break the deadlock by task type) and the conflict-resolution rules (applied if the decision protocol surfaces unresolved conflict between specific agents); both live in the same file under a single dispatch from the SKILL so there is no leaf-to-leaf chaining.
   - The Decision Protocol section copied verbatim from current SKILL lines 500–554. Preserve the `## Decision Protocol` header and every subsection (`### Task Classification`, `### Protocol by Task Type`, `### Decision Documentation`), every table, every code fence, and every literal string — including the literal substrings `Reasoning`, `Knowledge`, `Weighted Voting`, `Evidence-Based Consensus` that the structural smoke test asserts on.
   - The Conflict Resolution section copied verbatim from current SKILL lines 558–613. Preserve the `## Conflict Resolution` header and every subsection (`### Resolution by Conflict Type`, `### Deadlock Protocol`, `### Conflict Documentation`), every numbered conflict-type rule, every code fence, and every literal string — including the literal substrings `Technical Disagreement`, `Security vs Usability`, `Quality vs Speed`, `Feature Scope`, `Deadlock` that the structural smoke test asserts on.

3. Do not modify any text in the migrated content. Do not rename headers. Do not collapse subsections. The text was authored and validated as part of the current SKILL; this task is a pure content relocation plus a leading paragraph.

4. Do not author dispatch instructions or refer back to the SKILL beyond the leading paragraph's statement that this leaf is loaded under a single dispatch. The SKILL-side dispatch reference is owned by task-07.

5. Verify completion: run `bash tests/sdl-workflow/test-council-skill-structure.sh`. The leaf-existence assertion (Test 31) and the nine `consensus-failure.md` content assertions (Tests 34–42) should now pass. SKILL-side assertions remain failing until task-07 lands; that is expected.

## 4. Files to create/modify

- **Create**: `assets/fbk-docs/fbk-council/consensus-failure.md`

## 5. Test requirements

This implementation task makes the following assertions from `task-01` (`tests/sdl-workflow/test-council-skill-structure.sh`) pass:

- Test 31: `consensus-failure.md` exists and is non-empty.
- Test 34: `consensus-failure.md` contains `Weighted Voting`.
- Test 35: `consensus-failure.md` contains `Evidence-Based Consensus`.
- Test 36: `consensus-failure.md` contains `Reasoning`.
- Test 37: `consensus-failure.md` contains `Knowledge`.
- Test 38: `consensus-failure.md` contains `Technical Disagreement`.
- Test 39: `consensus-failure.md` contains `Security vs Usability`.
- Test 40: `consensus-failure.md` contains `Quality vs Speed`.
- Test 41: `consensus-failure.md` contains `Feature Scope`.
- Test 42: `consensus-failure.md` contains `Deadlock`.

No new tests are authored by this task. Test extension to `tests/sdl-workflow/test-old-locations-empty.sh` (Test 7 — `consensus-failure.md` exists) and to `tests/sdl-workflow/test-no-old-path-patterns.sh` (file added to the scanned `files=()` array) are owned by task-02 and task-03 respectively; this task makes those assertions pass implicitly by creating the file.

## 6. Acceptance criteria

- AC-04: `assets/fbk-docs/fbk-council/consensus-failure.md` exists. Its decision-protocol section contains the task-classification table (Reasoning vs Knowledge), the weighted voting protocol with vote weights and tie-breaker, the Evidence-Based Consensus protocol, and the decision documentation schema. Its conflict-resolution section contains the four resolution-by-conflict-type rules (Technical, Security-vs-Usability, Quality-vs-Speed, Feature Scope), the Deadlock Protocol steps, and the Conflict Documentation schema. Both sections live in the same file under a single dispatch from the SKILL.
- task-01 assertions 31 and 34–42 pass when run against the created file.
- The migrated content is byte-equivalent to the source ranges (current SKILL lines 500–554 and 558–613) modulo the leading paragraph this task adds at the top of the leaf.

## 7. Model

Haiku

## 8. Wave

Wave 2
