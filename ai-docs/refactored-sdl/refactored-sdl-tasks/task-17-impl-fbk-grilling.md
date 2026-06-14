---
id: task-17
type: implementation
wave: 1
covers: [AC-13, AC-16]
files_to_create:
  - assets/skills/fbk-grilling/SKILL.md
test_tasks: [task-03]
dependencies: []
completion_gate: "the referenced test tasks pass"
---

## 1. Objective

Produces `assets/skills/fbk-grilling/SKILL.md`, the grilling technique skill that asks one question at a time with a recommendation, reflects each answer back before recording it, writes a grilling log in the pinned shape, and credits Matt Pocock with the source link in its frontmatter.

## 2. Context

The grilling technique is the one-question-at-a-time ambiguity-resolution capability that intent, design, and spec phases compose, and that the operator can invoke out-of-ceremony on any topic. It surfaces each open decision with full natural-language context, the agent's recommendation and justification, then waits for the operator's answer and reflects it back to confirm before recording it and moving on. Soft cap ~10 questions.

When invoked in-ceremony it writes a decision log to `ai-docs/<feature>/grilling-log-<phase>.md`. The log shape is pinned (Interface contract #6): markdown, one `### <decision-slug>` block per decision, each with the lines `- Question:`, `- Recommendation:`, `- Answer:`, and `- Confirmed:` (the reflect-back line). The `Confirmed:` line is load-bearing — it makes "reflected back before recording" an observable property of the log rather than an unverifiable behavior. The intent/design gates check the file is present; the grilling-log seam test checks at least one well-formed block; the phase-skill dedup step reads the `Answer`/`Confirmed` lines.

This is a NEW firebreak asset adapted from Matt Pocock's grill-me skill (not a change to the external `/grill-me`). Firebreak ships and installs its own assets; the external grill-me is itself an adaptation of Pocock's skill and carries a source-link credit, so `fbk-grilling` sits in the same lineage and carries the same attribution. The frontmatter must credit **Matt Pocock** and contain the exact source URL `https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md`.

Asset-type rules (from `fbk-context-assets.md`): a skill has frontmatter `description` + `argument-hint` and a thin body that owns its workflow (this is a technique skill — the capability layer). Follow the shape of the existing `assets/skills/fbk-*/SKILL.md` files (frontmatter block delimited by `---`, then body). Use the always-on disciplines: simple language, descriptions over identifiers, capability framing.

The paired test (`tests/sdl-workflow/test-technique-skills.sh`) asserts for this skill: the file exists and is non-empty (T1); frontmatter has `description:` (T2) and `argument-hint:` (T3); `grep -qF 'Matt Pocock'` (T13); the exact URL is present (T14); `grep -qi 'one question at a time'` (T15); `grep -qF 'Confirmed:'` (T16). The `Confirmed:` token must appear literally in the body (it is part of the grilling-log block template the body documents).

## 3. Instructions

1. Create the directory `assets/skills/fbk-grilling/` and the file `assets/skills/fbk-grilling/SKILL.md`.

2. Write the YAML frontmatter between `---` markers with:
   - `description:` a one-paragraph capability-framed description that triggers on grilling/stress-testing a plan or design and on resolving ambiguity one decision at a time.
   - `argument-hint:` e.g. `"[topic or feature-name]"`.
   - An attribution line inside the frontmatter (as a YAML comment or a `source:` field) reading `Source: adapted from Matt Pocock's grill-me skill — https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md`. The exact URL and the literal string `Matt Pocock` must both appear. Completion: `grep -qF 'Matt Pocock' assets/skills/fbk-grilling/SKILL.md` and `grep -qF 'https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md' assets/skills/fbk-grilling/SKILL.md` both succeed.

3. Write the body. Encode the loop: ask **one question at a time** (use that exact phrase), each question paired with the agent's recommendation and justification, in plain language and referring to items by description not identifier. After the operator answers, **reflect the answer back** to confirm, then record it. Soft cap ~10 questions. Completion: `grep -qi 'one question at a time' assets/skills/fbk-grilling/SKILL.md` succeeds.

4. In the body, document the in-ceremony output: when invoked with a feature/phase, write the decision log to `ai-docs/<feature>/grilling-log-<phase>.md`, one `### <decision-slug>` block per decision, each block containing the lines `- Question:`, `- Recommendation:`, `- Answer:`, `- Confirmed:`. Show the block template literally so the `Confirmed:` token appears in the file. Completion: `grep -qF 'Confirmed:' assets/skills/fbk-grilling/SKILL.md` succeeds.

5. Run the paired test and confirm the grilling assertions pass: `bash tests/sdl-workflow/test-technique-skills.sh` (T1–T3, T13–T16 for this skill).

## 4. Files to create/modify

- `assets/skills/fbk-grilling/SKILL.md` (create)

## 5. Test requirements

This task makes `tests/sdl-workflow/test-technique-skills.sh` assertions for fbk-grilling pass: T1 (exists), T2 (description), T3 (argument-hint), T13 (Matt Pocock), T14 (source URL), T15 (one question at a time), T16 (Confirmed:). No new tests are written here. Do not edit the test file.

## 6. Acceptance criteria

- AC-13: the skill asks one question at a time with a recommendation and records a reflect-back `Confirmed:` line per decision; it is invocable out-of-ceremony.
- AC-16: the frontmatter credits Matt Pocock and links the exact source grill-me URL.
- Primary criterion: the corresponding task-03 assertions pass.

## 7. Model

Sonnet

## 8. Wave

Wave 1
