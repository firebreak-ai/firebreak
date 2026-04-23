---
id: task-13
type: implementation
wave: 1
covers: [AC-04, AC-06]
files_to_modify:
  - assets/agents/fbk-improvement-analyst.md
test_tasks: [task-03]
completion_gate: "task-03 tests pass"
---

## Objective

Prepend a persona section to `assets/agents/fbk-improvement-analyst.md` — role activation plus `## Output quality bars` — without altering the existing task-logic sections (`## Input contract`, `## Workflow`, `## Proposal output format`, `## Cross-cutting scope`, `## Scope discipline`). The persona section must sit at or below 40 lines measured from body start to the first existing task-logic heading.

## Context

The improvement-analyst is a teammate spawned by the `/fbk-improve` skill. Its body currently begins with the bare instruction `Analyze assigned asset(s) against the retrospective observations to produce improvement proposals...` and proceeds into `## Input contract`. There is no role activation.

The spec adds a persona at the top of the body. The persona must activate "process improvement engineer analyzing production incidents" and enumerate quality bars that require every proposal to trace from a specific retrospective observation to a specific instruction gap, and that require necessity and removal arguments to pass the necessity test. The existing workflow, input contract, and proposal output format sections must be preserved byte-for-byte.

The paired test `tests/sdl-workflow/test-improvement-analyst-persona.sh` measures the persona section as the range from body start up to the line before the first `## ` heading. The persona must end before the first `## ` line; the first `## ` line must be an existing task-logic heading.

The existing body contains the load-bearing phrase `retrospective observation` in multiple places; preserving the existing paragraphs satisfies the test's case-insensitive grep for that phrase.

## Instructions

1. Read the current file at `assets/agents/fbk-improvement-analyst.md` in full.
2. Preserve the frontmatter block unchanged.
3. Preserve every `## ` task-logic heading and its content byte-for-byte in its existing order: `## Input contract`, `## Workflow`, `## Proposal output format`, `## Cross-cutting scope`, `## Scope discipline`, and any content under them.
4. Replace the body region from the line after the closing frontmatter `---` up to (but not including) the first `## Input contract` heading with this new content (verbatim):

   ```
   You are a process improvement engineer at an enterprise software company analyzing production incidents to improve the instructions, runbooks, and context assets that shape team behavior. You treat retrospective observations as incident reports — each observation points to an instruction gap that made the mistake likely.

   ## Output quality bars

   - Every proposal traces from a specific retrospective observation to a specific instruction gap. Cite the observation, name the instruction that was missing or unclear, and explain the connection.
   - Necessity arguments explain why the mistake recurs without the proposed instruction. The bar is: if this instruction were removed, would the observed mistake be more likely? Answer with the causal mechanism, not a restatement of the observation.
   - Removal proposals from the quality review justify why the existing instruction no longer passes the necessity test — either the mistake it guards against is no longer plausible, or another instruction now covers it.

   Analyze assigned asset(s) against the retrospective observations to produce improvement proposals. Each proposal is a single-instruction add, edit, or remove anchored to a specific retrospective observation.
   ```

5. The first `## ` heading following this new content must be the preserved `## Input contract`. Do not introduce any intervening `## ` headings.
6. Verify the persona section is at or below 40 lines:
   ```bash
   awk '/^---$/{c++; if(c==2){found=1; next}} found' assets/agents/fbk-improvement-analyst.md | awk '/^## /{exit} {print}' | wc -l
   ```
7. Verify preservation by confirming these headings still grep-match the file body:
   - `^## Input contract$`
   - `^## Workflow$`
   - `^## Proposal output format$`
   - `^## Scope discipline$`
8. Run `bash tests/sdl-workflow/test-improvement-analyst-persona.sh`. All 11 assertions must pass.

## Files to create/modify

- **Modify**: `assets/agents/fbk-improvement-analyst.md` — prepend persona section. All existing task-logic content preserved byte-for-byte below the persona.

## Test requirements

No new tests. The paired test task `task-03-test-improvement-analyst-persona-section.md` covers persona presence, the 40-line ceiling, role-activation phrase, `## Output quality bars` heading, preservation of four task-logic headings, and preservation of the load-bearing `retrospective observation` phrase.

## Acceptance criteria

- `tests/sdl-workflow/test-improvement-analyst-persona.sh` — all 11 assertions pass
- Covers AC-04 (persona added, existing workflow preserved) and the structural half of AC-06
- Frontmatter preserved byte-for-byte
- All task-logic content below the persona preserved byte-for-byte

## Model

Sonnet

## Wave

1
