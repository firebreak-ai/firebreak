---
id: task-20
type: implementation
wave: 1
covers: [AC-14, AC-15]
files_to_create:
  - assets/skills/fbk-test-review/SKILL.md
files_to_modify:
  - assets/agents/fbk-test-reviewer.md
test_tasks: [task-03]
dependencies: []
completion_gate: "the referenced test tasks pass"
---

## 1. Objective

Produces the test-review technique skill (`assets/skills/fbk-test-review/SKILL.md`) with pre-lock and final modes and an accepted/needs-revision verdict, and rewires the existing `fbk-test-reviewer` agent from its fixed CP1/CP2/CP3 checkpoint model to the new pre-lock/final modes with widened scope and contract-evolving retirement awareness.

## 2. Context

The test-review technique validates that AI-written tests actually catch the behavior they claim to cover (known AI test failure modes: implementation-embedding, weak assertions, magic-number assertions, internally-contradictory fixtures, mocked dependencies that bypass the behavior under test). It formalizes the existing test-reviewer agent persona as a callable capability with a **widened invocation contract**: two modes — **pre-lock** (before hash-locking, invoked by breakdown) and **final** (a final pass invoked by code-review). It reviews the full set of tests covering the changed module, **including the pre-existing tests a contract-preserving slice locks**. It writes `ai-docs/<feature>/test-review-<checkpoint>.md` with a verdict line that is exactly one of `accepted` | `needs-revision`.

This is a **refactor-then-extend** of the agent, not a description tweak. The current `assets/agents/fbk-test-reviewer.md` is built around fixed checkpoints CP1 (spec review), CP2 (task review), CP3 (test code review), CP4 (test integrity), CP5 (mutation testing). The rewire maps its criteria-to-checkpoint structure onto the two new modes:
- **pre-lock mode** absorbs the CP2/CP3 concerns (test tasks faithfully translate the strategy; test implementations have no Tier-1 violations; tests trace to ACs; tests are structured to fail before implementation) — this is the checkpoint that gates lock application in breakdown.
- **final mode** absorbs the CP4/CP3-final concerns (no weakened assertions, no trivially-passing tests, no unauthorized test modification) plus the widened scope (review all tests covering the changed module, including pre-existing locked tests) and **contract-evolving retirement-list awareness** (when a slice is contract-evolving, verify the declared retired-tests list is justified and that remaining tests still protect the surviving contract).

Preserve: the persona (senior QA engineer with pipeline-blocking authority), the four core mechanical checks (silent-failure detection, stale failure annotations, empty gate tests, advisory assertions), and the current tools `Read, Grep, Glob, Bash` (no Write/Edit — AC-15). Read the current agent file fully before editing; the CP5 mutation-testing checkpoint maps to nothing in the new model (mutation sampling is a standing non-goal) — drop it as part of the rewire.

Asset-type rules: the agent owns persona + evaluation criteria; the skill owns the mode routing and artifact write. The skill must produce the `test-review-<checkpoint>.md` artifact with the verdict line.

The paired test (`tests/sdl-workflow/test-technique-skills.sh`) asserts for the skill: exists non-empty (T10), `description:` (T11), `argument-hint:` (T12). For the agent it re-checks the no-Write/no-Edit tool list (T23/T24) — the preserved `Read, Grep, Glob, Bash` line satisfies it.

## 3. Instructions

1. Read the current `assets/agents/fbk-test-reviewer.md` in full and `tests/sdl-workflow/test-technique-skills.sh` (T23/T24, the tool-list check).

2. In `assets/agents/fbk-test-reviewer.md`, rewire the checkpoint structure to two modes. Keep the frontmatter `name`, `model: sonnet`, and the `tools: Read, Grep, Glob, Bash` line unchanged (no Write/Edit added). Keep the persona section and the "Evaluation criteria" Tier-1 four checks (Criteria 1–4) and the Tier-2 structured-judgment checks. Replace the five `## Checkpoint N` sections with two sections: `## Pre-lock mode` (the criteria that gate lock application: faithful test-task translation, AC traceability, Tier-1 checks against test implementations, tests structured to fail pre-implementation) and `## Final mode` (the criteria for the final pass: no weakened assertions / trivially-passing tests / unauthorized modification, widened scope over all tests covering the changed module including pre-existing locked tests, and contract-evolving retirement-list awareness). Remove the CP5 mutation-testing section entirely. Keep the override mechanism and output format sections. Completion: `grep -q '## Pre-lock mode' assets/agents/fbk-test-reviewer.md` and `grep -q '## Final mode' assets/agents/fbk-test-reviewer.md` succeed; `grep -c 'Checkpoint 5' assets/agents/fbk-test-reviewer.md` returns 0; `grep '^tools:' assets/agents/fbk-test-reviewer.md` shows `Read, Grep, Glob, Bash` with no Write/Edit.

3. Add contract-evolving retirement awareness to the Final mode section: when reviewing a contract-evolving slice, verify the slice's declared retired-tests list has a rationale per entry and that the surviving tests still protect the unchanged part of the contract. Completion: `grep -qi 'retired' assets/agents/fbk-test-reviewer.md` succeeds.

4. Create the directory `assets/skills/fbk-test-review/` and `assets/skills/fbk-test-review/SKILL.md` with frontmatter `description:` (trigger: reviewing a test set for integrity at a pipeline checkpoint or standalone) and `argument-hint:` (e.g. `"[feature-name or test-path]"`).

5. In the skill body, document: it routes the test-reviewer agent in either pre-lock or final mode (the caller or the operator selects the mode); it reviews the full set of tests covering the changed module; it writes `ai-docs/<feature>/test-review-<checkpoint>.md` with a verdict line that is exactly `accepted` or `needs-revision`. State that only an `accepted` pre-lock verdict triggers lock application downstream. Completion: `grep -qE 'accepted|needs-revision' assets/skills/fbk-test-review/SKILL.md` and the body documents both modes and the artifact path.

6. Run the paired test: `bash tests/sdl-workflow/test-technique-skills.sh` (T10–T12 for the skill; T23–T24 for the agent).

## 4. Files to create/modify

- `assets/skills/fbk-test-review/SKILL.md` (create)
- `assets/agents/fbk-test-reviewer.md` (modify)

## 5. Test requirements

- New tests: none authored here. Make `tests/sdl-workflow/test-technique-skills.sh` assertions T10–T12 and T23–T24 pass.
- Existing tests impacted: search `tests/sdl-workflow/` for any test that greps the test-reviewer agent's checkpoint names (`Checkpoint 1`..`Checkpoint 5`). If such a sentinel test exists and references checkpoints removed by the rewire, that test belongs to the phase-skill-modifications slice (task-31/task-32 re-sentinel prose tests) — do NOT modify it here; instead confirm with the implementing context whether a sentinel update is needed. The technique-skills test (task-03) does not assert checkpoint names, so this task's paired test is unaffected.

## 6. Acceptance criteria

- AC-14: `fbk-test-review` exists as a callable technique skill with a named output artifact carrying an `accepted | needs-revision` verdict, invocable out-of-ceremony, with pre-lock and final modes.
- AC-15: the test-reviewer agent still declares no Write or Edit tool through the rewire.
- Primary criterion: the corresponding task-03 assertions pass.

## 7. Model

Sonnet

## 8. Wave

Wave 1
