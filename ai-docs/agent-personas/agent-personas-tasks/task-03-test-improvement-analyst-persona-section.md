---
id: task-03
type: test
wave: 1
covers: [AC-04, AC-06]
files_to_create:
  - tests/sdl-workflow/test-improvement-analyst-persona.sh
completion_gate: "bash tests/sdl-workflow/test-improvement-analyst-persona.sh exits non-zero before implementation"
---

## Objective

Create a TAP-style bash test that validates `assets/agents/fbk-improvement-analyst.md` contains a persona section with role activation and output quality bars, bounded to 40 lines measured from body start to the first task-logic heading, while leaving the existing input contract, workflow, proposal output format, and scope discipline sections intact.

## Context

The improvement-analyst is an execution agent that traces retrospective observations to instruction gaps. It currently starts with a bare instruction ("Analyze assigned asset(s)...") and has no role activation. The spec adds a persona at the top of the body: role activation ("process improvement engineer analyzing production incidents") and `## Output quality bars`. The persona section ends at the first task-logic heading — the existing `## Input contract`, `## Workflow`, `## Proposal output format`, `## Cross-cutting scope`, and `## Scope discipline` sections are task logic and must remain unchanged below the persona.

The 40-line ceiling for task-logic agents measures only the persona section (body start to the line before the first task-logic heading). The full file length is unconstrained. The existing task-logic sections must be preserved byte-for-byte in their existing order.

This task covers AC-04 (persona added, existing workflow preserved) and the structural half of AC-06.

## Instructions

1. Create `tests/sdl-workflow/test-improvement-analyst-persona.sh` executable (`chmod +x`).
2. Follow the TAP boilerplate from `tests/sdl-workflow/test-code-review-structural.sh` (`set -uo pipefail`, counters, `ok()`/`not_ok()`, `TAP version 13` header, `1..$TOTAL` summary, non-zero exit on failure).
3. Derive paths:
   ```bash
   SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
   PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
   AGENT="$PROJECT_ROOT/assets/agents/fbk-improvement-analyst.md"
   ```
4. Provide `body_lines()` and `persona_section()` helpers identical to the ones in `task-02-test-test-reviewer-persona-section.md`:
   ```bash
   body_lines() { awk '/^---$/{c++; if(c==2){found=1; next}} found' "$1"; }
   persona_section() { body_lines "$1" | awk '/^## /{exit} {print}'; }
   ```
5. Implement these tests:
   - **Test 1: file exists and is non-empty** — `[ -s "$AGENT" ]`.
   - **Test 2: has valid YAML frontmatter** — first line is `---`, at least two `---` lines exist.
   - **Test 3: persona section contains at least 5 lines (distinguishes a real persona block from the existing bare instruction)** — `[ "$(persona_section "$AGENT" | wc -l | tr -d ' ')" -ge 5 ]`. The current body has a single-sentence instruction before `## Input contract`, giving 1-2 non-blank lines; a real persona block (activation + `## Output quality bars` heading + ≥3 bullet lines) exceeds 5 lines. This test fails pre-implementation and passes post-implementation.
   - **Test 4: persona section at or below 40 lines** — `[ "$(persona_section "$AGENT" | wc -l | tr -d ' ')" -le 40 ]`.
   - **Test 5: persona contains role-activation language** — grep persona section case-insensitive for `process improvement engineer`.
   - **Test 6: persona contains `## Output quality bars` heading** — grep body for `^## Output quality bars$`.
   - **Test 7: existing task-logic section `## Input contract` preserved** — grep body for `^## Input contract$`.
   - **Test 8: existing task-logic section `## Workflow` preserved** — grep body for `^## Workflow$`.
   - **Test 9: existing task-logic section `## Proposal output format` preserved** — grep body for `^## Proposal output format$`.
   - **Test 10: existing task-logic section `## Scope discipline` preserved** — grep body for `^## Scope discipline$`.
   - **Test 11: retrospective-observation grounding preserved** — grep body case-insensitive for `retrospective observation`. This is load-bearing language from the existing agent that must survive the persona addition.
6. Total tests: 11.
7. End with the standard summary block.
8. Run `bash tests/sdl-workflow/test-improvement-analyst-persona.sh`. Tests 3, 5, and 6 must fail pre-implementation — the current body has fewer than 5 lines before the first task-logic heading, contains no `process improvement engineer` phrase, and has no `## Output quality bars` heading. Test 4 (40-line ceiling) passes pre-implementation (the existing body is well under 40 lines) and must continue to pass post-implementation. The preservation assertions (tests 7-11) pass pre-implementation; that is expected. Overall exit status is non-zero.

## Files to create/modify

- **Create**: `tests/sdl-workflow/test-improvement-analyst-persona.sh` — new test file. No existing test covers the persona section of `fbk-improvement-analyst.md`. `tests/sdl-workflow/test-improvement-agent.sh` exists but focuses on proposal-format behavior, not persona structure.

## Test requirements

| Level | Behavior under test | Expected assertion |
|-------|--------------------|--------------------|
| Unit | Agent file exists | `[ -s "$AGENT" ]` |
| Unit | Agent has valid frontmatter | `head -1 == '---'` and `grep -c '^---$' >= 2` |
| Unit | Persona section has at least 5 lines (distinguishes real persona from existing bare instruction) | `wc -l` on `persona_section` ≥ 5 |
| Unit | Persona section at or below 40 lines | `wc -l` on `persona_section` ≤ 40 |
| Unit | Persona contains role-activation language | case-insensitive `grep` for `process improvement engineer` |
| Unit | Persona contains `Output quality bars` heading | `grep -q '^## Output quality bars$'` on body |
| Unit | Existing task-logic sections preserved | `grep -q` for each of four exact heading strings |
| Unit | Retrospective-observation grounding preserved | case-insensitive `grep` for `retrospective observation` |

## Acceptance criteria

- 11 TAP tests covering persona presence, 40-line persona-section ceiling, role-activation language, required heading, preservation of four existing task-logic headings, and preservation of load-bearing workflow language
- Follows existing test suite conventions exactly
- All assertions are grep/awk/wc against file content
- Covers AC-04 (persona added, existing workflow preserved) and the structural half of AC-06

## Model

Haiku

## Wave

1
