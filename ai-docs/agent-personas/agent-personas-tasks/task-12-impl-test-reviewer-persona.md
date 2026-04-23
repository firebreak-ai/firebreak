---
id: task-12
type: implementation
wave: 1
covers: [AC-03, AC-06]
files_to_modify:
  - assets/agents/fbk-test-reviewer.md
test_tasks: [task-02]
completion_gate: "task-02 tests pass"
---

## Objective

Prepend a persona section to `assets/agents/fbk-test-reviewer.md` — role activation plus `## Output quality bars` — without altering the existing task-logic sections (`## Context isolation`, `## Evaluation criteria`, `## Override mechanism`, `## Override output format`, checkpoint sections, `## Output format`, `## Brownfield projects`). The persona section must sit at or below 40 lines measured from body start to the first existing task-logic heading.

## Context

The test-reviewer is an execution agent with pipeline-blocking authority across five checkpoints (CP1 through CP5). Its body currently begins with a bare instruction (`Validate test quality against spec requirements. You have pipeline-blocking authority — fail the checkpoint when defects exist.`) and proceeds directly into `## Context isolation`. There is no role activation.

The spec adds a persona at the top of the body. The persona must activate "senior QA engineer with authority to block releases" and enumerate quality bars that treat pipeline-blocking authority as an obligation to be thorough rather than a license for pedantry. The existing task-logic sections must be preserved byte-for-byte — the test reviewer's evaluation criteria, checkpoint definitions, and override mechanism are the agent's production behavior and are out of scope for this change.

The paired test `tests/sdl-workflow/test-test-reviewer-persona.sh` measures the persona section as the range from body start up to the line before the first `## ` heading. This means the persona must end before the first `## ` line; the first `## ` line must be an existing task-logic heading.

The load-bearing first sentence (`Validate test quality against spec requirements. You have pipeline-blocking authority — fail the checkpoint when defects exist.`) can remain as a transition line into the task-logic section, but the persona content must come first. The test requires the body to retain the case-insensitive phrase `pipeline-blocking` somewhere — preserving the existing sentence satisfies this.

## Instructions

1. Read the current file at `assets/agents/fbk-test-reviewer.md` in full.
2. Preserve the frontmatter block unchanged.
3. Preserve every `## ` task-logic heading and its content byte-for-byte in its existing order: `## Context isolation`, `## Evaluation criteria`, `## Override mechanism`, `## Override output format`, `## Checkpoint 1 — Spec review`, `## Checkpoint 2 — Task review`, `## Checkpoint 3 — Test code review`, `## Checkpoint 4 — Test integrity`, `## Checkpoint 5 — Mutation testing`, `## Output format`, `## Brownfield projects`, and any content under them.
4. Replace the body region from the line after the closing frontmatter `---` up to (but not including) the first `## Context isolation` heading with this new content (verbatim):

   ```
   You are a senior QA engineer at an enterprise software company with authority to block releases when test quality does not meet the bar. You evaluate test artifacts at pipeline checkpoints the way a QA lead evaluates a release candidate — thoroughly, but proportionate to the evidence in front of you.

   ## Output quality bars

   - Every finding cites the specific criterion violated and the evidence that proves the violation. Name the criterion by number and quote or reference the artifact location.
   - Pass results demonstrate that every checkpoint criterion was evaluated, not just that nothing was flagged. State which criteria you evaluated and what evidence cleared them.
   - Treat pipeline-blocking authority as an obligation to be thorough, not a license to be pedantic. Surface-level nits that do not affect test integrity are out of scope; defects that weaken regression protection are in scope.

   Validate test quality against spec requirements. You have pipeline-blocking authority — fail the checkpoint when defects exist.
   ```

5. The first `## ` heading following this new content must be the preserved `## Context isolation`. Do not introduce any intervening `## ` headings.
6. Verify the persona section (body start up to the line before the first `## ` heading) is at or below 40 lines using:
   ```bash
   awk '/^---$/{c++; if(c==2){found=1; next}} found' assets/agents/fbk-test-reviewer.md | awk '/^## /{exit} {print}' | wc -l
   ```
7. Verify the task-logic section preservation by confirming all of these headings still grep-match the file body:
   - `^## Context isolation$`
   - `^## Evaluation criteria$`
   - `^## Override mechanism$`
   - `^## Checkpoint 1`, `^## Checkpoint 2`, `^## Checkpoint 3`, `^## Checkpoint 4`, `^## Checkpoint 5`
8. Run `bash tests/sdl-workflow/test-test-reviewer-persona.sh`. All 10 assertions must pass.

## Files to create/modify

- **Modify**: `assets/agents/fbk-test-reviewer.md` — prepend persona section. All existing task-logic content preserved byte-for-byte below the persona.

## Test requirements

No new tests written by this task. The paired test task `task-02-test-test-reviewer-persona-section.md` covers persona presence, the 40-line ceiling, role-activation language, the `## Output quality bars` heading, preservation of four existing task-logic headings, and preservation of the load-bearing `pipeline-blocking` language.

## Acceptance criteria

- `tests/sdl-workflow/test-test-reviewer-persona.sh` — all 10 assertions pass (persona present, ≤40-line persona section, role-activation language, `## Output quality bars` heading, four preserved task-logic headings, `pipeline-blocking` language preserved)
- Covers AC-03 (persona added, existing checkpoint logic preserved) and the structural half of AC-06
- Frontmatter preserved byte-for-byte
- All task-logic content below the persona preserved byte-for-byte

## Model

Sonnet

## Wave

1
