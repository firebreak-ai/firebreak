---
id: task-18
type: implementation
wave: 1
covers: [AC-14, AC-15]
files_to_create:
  - assets/skills/fbk-fresh-eyes/SKILL.md
  - assets/agents/fbk-fresh-eyes-reviewer.md
test_tasks: [task-03]
dependencies: []
completion_gate: "the referenced test tasks pass"
---

## 1. Objective

Produces the fresh-eyes technique skill (`assets/skills/fbk-fresh-eyes/SKILL.md`) and its cold-reviewer agent (`assets/agents/fbk-fresh-eyes-reviewer.md`), which spawns an isolated cold reviewer, returns a severity-categorized observation report, and never fixes.

## 2. Context

The fresh-eyes technique is a context-clear comprehension check: a reviewer reads an artifact cold — without authoring context — and surfaces what doesn't make sense as structured observations classified by severity. The reviewer has NO authority to fix; fixes go back to the authoring agent. It is the semantic anchor for the intent and design gates.

The skill spawns the isolated `fbk-fresh-eyes-reviewer` agent and writes the report to `ai-docs/<feature>/fresh-eyes-<artifact>.md`. The report uses the pinned section structure: `## Critical`, `## Substantive`, `## Minor` (the three severities are `critical`, `substantive`, `minor`). The gate bar is "the `## Critical` section has no observation entries after dedup" — so the report must use exactly these section headings for the gate to read it.

The agent is a thin cold reviewer with no specialist lens — its value is being uncontaminated. It is an **observe-only** agent: its frontmatter `tools:` line must list **only** `Read, Grep, Glob` — no `Write`, no `Edit` (AC-15: observe/scan agents cannot auto-fix). Model: sonnet.

Asset-type rules: the agent owns persona (cold, uncontaminated reviewer); the skill owns the workflow (spawn the agent, collect observations, write the artifact). Follow the existing agent frontmatter shape in `assets/agents/fbk-code-review-detector.md` (`name:`, `description:`, `tools:`, `model:` between `---` markers) and the existing skill shape. Use capability framing and plain language.

The paired test (`tests/sdl-workflow/test-technique-skills.sh`) asserts for the skill: exists non-empty (T4), has `description:` (T5), has `argument-hint:` (T6). For the agent it asserts (T19/T20) the `tools:` line declares no `Write` and no `Edit` (counted via `grep -c`, must be 0). The test also runs the same tool-list check on the two pre-existing agents — those already pass; this new agent is the one that must be authored to pass.

## 3. Instructions

1. Create `assets/agents/fbk-fresh-eyes-reviewer.md` with YAML frontmatter:
   - `name:` `fbk-fresh-eyes-reviewer`
   - `description:` a capability-framed one-liner: a cold reviewer that reads an artifact without authoring context and surfaces what does not make sense, classified by severity; no fix authority.
   - `tools: Read, Grep, Glob` (exactly these three; no Write, no Edit, no Bash).
   - `model: sonnet`
   Then a short persona body: read the artifact cold; surface observations; classify each as critical, substantive, or minor; do not propose or apply fixes. Completion: the `tools:` frontmatter line contains Read, Grep, Glob and contains neither `Write` nor `Edit` (`grep '^tools:' ... | grep -c Write` is 0 and same for Edit).

2. Create the directory `assets/skills/fbk-fresh-eyes/` and `assets/skills/fbk-fresh-eyes/SKILL.md` with frontmatter `description:` (trigger: cold comprehension review of a document/artifact, invocable standalone) and `argument-hint:` (e.g. `"[artifact-path or feature-name]"`).

3. In the skill body, document the workflow: spawn the `fbk-fresh-eyes-reviewer` agent in isolated context, pass it only the artifact under review, collect its observations, and write `ai-docs/<feature>/fresh-eyes-<artifact>.md` with the three sections `## Critical`, `## Substantive`, `## Minor`. State the no-fix rule (observations only; fixes return to the author). Completion: `grep -q '## Critical' assets/skills/fbk-fresh-eyes/SKILL.md` and the file documents the `fresh-eyes-<artifact>.md` output path.

4. Run the paired test and confirm the fresh-eyes assertions pass: `bash tests/sdl-workflow/test-technique-skills.sh` (T4–T6 for the skill; T19–T20 for the agent).

## 4. Files to create/modify

- `assets/skills/fbk-fresh-eyes/SKILL.md` (create)
- `assets/agents/fbk-fresh-eyes-reviewer.md` (create)

File-scope justification: two files, one cohesive technique (skill + its single dedicated agent). The skill has no value without the agent it spawns; authoring them separately would split one capability across two tasks with an artificial seam.

## 5. Test requirements

This task makes `tests/sdl-workflow/test-technique-skills.sh` assertions T4–T6 (skill structure) and T19–T20 (agent tool-list, no Write/Edit) pass. No new tests are written here. Do not edit the test file.

## 6. Acceptance criteria

- AC-14: `fbk-fresh-eyes` exists as a callable technique skill with a stable named output artifact (`fresh-eyes-<artifact>.md`) and is invocable out-of-ceremony.
- AC-15: `fbk-fresh-eyes-reviewer` declares no Write or Edit tool, so it cannot auto-fix.
- Primary criterion: the corresponding task-03 assertions pass.

## 7. Model

Sonnet

## 8. Wave

Wave 1
