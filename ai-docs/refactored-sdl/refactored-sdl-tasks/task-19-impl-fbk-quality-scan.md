---
id: task-19
type: implementation
wave: 1
covers: [AC-10, AC-14, AC-15]
files_to_create:
  - assets/skills/fbk-quality-scan/SKILL.md
files_to_modify:
  - assets/agents/fbk-code-review-detector.md
test_tasks: [task-03]
dependencies: []
completion_gate: "the referenced test tasks pass"
---

## 1. Objective

Produces the quality-scan technique skill (`assets/skills/fbk-quality-scan/SKILL.md`) that returns at most five ranked, severity-tagged, scan-only findings, and reframes the existing detector agent persona to be mode-neutral so the quality-scan technique can reuse it.

## 2. Context

The quality-scan technique is a top-five code-quality scan (the Pocock pattern: surface the five highest-priority quality opportunities, ranked, and act on them as a separate decision). It surfaces at most five issues in the change set as structured findings, each with a severity (`critical` / `substantive` / `minor`). It is **scan-only** — it does not auto-fix; the operator decides what to do with each finding. It is invoked by code-review and is invocable out-of-ceremony for any diff. It writes `ai-docs/<feature>/quality-scan.md`, and that artifact must carry a `Severity:` field per finding (the code-review gate checks the severity field is populated).

The skill reuses the existing `fbk-code-review-detector` agent in a quality-opportunity mode, set via the spawn prompt (not a sibling note in the agent file). For that reuse to be clean, the detector agent gets a **mode-neutral persona reframe**: today its `name` and `description` are bug-focused ("reviewing code for bugs"). Reframe the persona so it reads as a general code-review detector whose specific mode (bug detection vs. quality-opportunity scan) comes from the orchestrator's spawn prompt. The bug-detection behavior is unchanged.

**Hard constraint — keep `test-code-review-structural.sh` green.** That test asserts on the detector agent's frontmatter: `name:` must still contain the substring `detector` (case-insensitive); the `tools:` line must list `Read`, `Grep`, `Glob` and must NOT contain `Bash`, `Write`, or `Edit`; `description:` must be non-empty. So when reframing: preserve `tools: Read, Grep, Glob`, keep `detector` in the name, keep model `sonnet`, and keep a non-empty description. Read `tests/sdl-workflow/test-code-review-structural.sh` (Tests 3, 4, 5, 6) before editing to confirm the exact assertions, and read the current `assets/agents/fbk-code-review-detector.md` so the reframe is minimal.

The paired technique-skills test (`tests/sdl-workflow/test-technique-skills.sh`) asserts for the quality-scan skill: exists non-empty (T7), `description:` (T8), `argument-hint:` (T9); body specifies a limit of five (T17: `grep -qE '\b5\b|five'`); body has a ranking/severity indicator (T18: `grep -qi 'ranked\|severity\|top'`). It also re-runs the no-Write/no-Edit tool-list check on the detector (T21/T22), which the preserved tools line satisfies.

## 3. Instructions

1. Read `tests/sdl-workflow/test-code-review-structural.sh` (the detector assertions) and the current `assets/agents/fbk-code-review-detector.md`.

2. In `assets/agents/fbk-code-review-detector.md`, reframe the persona to be mode-neutral. Edit the `description:` frontmatter so it describes a code-review detector that operates in a mode set by the spawn prompt (bug detection or quality-opportunity scan), keeping it non-empty. In the body, generalize the opening framing so it is not exclusively about bugs — state that the detector reads code closely and produces structured sightings in whichever mode the orchestrator's spawn prompt selects; preserve the existing bug-detection guidance (mechanism/trigger/caller-impact, type/severity definitions, audit passes) intact. Do NOT change the `tools:` line, do NOT remove `detector` from `name:`, do NOT change `model: sonnet`. Completion: `grep '^tools:' assets/agents/fbk-code-review-detector.md` shows `Read, Grep, Glob` with no Write/Edit/Bash; `grep -i '^name:.*detector' assets/agents/fbk-code-review-detector.md` succeeds; `bash tests/sdl-workflow/test-code-review-structural.sh` exits 0.

3. Create the directory `assets/skills/fbk-quality-scan/` and `assets/skills/fbk-quality-scan/SKILL.md` with frontmatter `description:` (trigger: top-five quality scan of a diff or change set, invocable standalone) and `argument-hint:` (e.g. `"[diff or feature-name]"`).

4. In the skill body, document the workflow: spawn the `fbk-code-review-detector` agent in quality-opportunity mode via the spawn prompt; return **at most five** ranked findings, each tagged with a severity (`critical`/`substantive`/`minor`); it is scan-only (no auto-fix — the operator decides). Write the report to `ai-docs/<feature>/quality-scan.md` with a `Severity:` field per finding. The body must contain the limit-of-five wording (the digit `5` or the word `five`) and a ranking/severity word (`ranked`, `severity`, or `top`). Completion: `grep -qE '\b5\b|five' assets/skills/fbk-quality-scan/SKILL.md` and `grep -qi 'ranked\|severity\|top' assets/skills/fbk-quality-scan/SKILL.md` both succeed.

5. Run both paired tests: `bash tests/sdl-workflow/test-technique-skills.sh` (T7–T9, T17, T18, T21, T22) and `bash tests/sdl-workflow/test-code-review-structural.sh` (must stay green).

## 4. Files to create/modify

- `assets/skills/fbk-quality-scan/SKILL.md` (create)
- `assets/agents/fbk-code-review-detector.md` (modify)

## 5. Test requirements

- New tests: none authored here. Make `tests/sdl-workflow/test-technique-skills.sh` assertions T7–T9, T17, T18, T21, T22 pass.
- Existing tests impacted: `tests/sdl-workflow/test-code-review-structural.sh` asserts the detector's name/description/tools — it must stay green after the persona reframe. Do not edit that test.

## 6. Acceptance criteria

- AC-10: `fbk-quality-scan` returns at most five ranked, severity-tagged findings and is scan-only.
- AC-14: it exists as a callable technique skill with a named output artifact and is invocable out-of-ceremony.
- AC-15: the reused detector still declares no Write or Edit tool.
- Primary criterion: the task-03 assertions pass and `test-code-review-structural.sh` stays green.

## 7. Model

Sonnet

## 8. Wave

Wave 1
