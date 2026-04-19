---
id: task-02
type: test
wave: 1
covers: [AC-03, AC-06]
files_to_create:
  - tests/sdl-workflow/test-test-reviewer-persona.sh
completion_gate: "bash tests/sdl-workflow/test-test-reviewer-persona.sh exits non-zero before implementation"
---

## Objective

Create a TAP-style bash test that validates `assets/agents/fbk-test-reviewer.md` contains a persona section with role activation and an output quality bars subsection, bounded to 40 lines measured from body start to the first task-logic heading, while leaving the existing checkpoint and evaluation-criteria sections intact.

## Context

The test-reviewer is an execution agent with pipeline-blocking authority. It currently starts its body with a bare instruction ("Validate test quality against spec requirements...") and has no role activation. The spec adds a persona at the top of the body: role activation ("senior QA engineer with authority to block releases") and `## Output quality bars`. The persona section ends at the first task-logic heading — the existing `## Context isolation` and `## Evaluation criteria` headings are task logic and must remain unchanged below the persona.

The 40-line ceiling for task-logic agents measures only the persona section — from the first body line after frontmatter to the line before the first task-logic heading. The full file length is unconstrained. The existing task-logic sections (`## Context isolation`, `## Evaluation criteria`, `## Override mechanism`, and any checkpoint / criterion content beneath them) must be preserved byte-for-byte in their existing order.

This task covers AC-03 (persona added, existing checkpoint logic preserved) and the structural half of AC-06 (mechanical persona presence; persona-content quality is human judgment).

## Instructions

1. Create `tests/sdl-workflow/test-test-reviewer-persona.sh` executable (`chmod +x`).
2. Follow the TAP boilerplate from `tests/sdl-workflow/test-code-review-structural.sh` (`set -uo pipefail`, counters, `ok()`/`not_ok()`, `TAP version 13` header, `1..$TOTAL` summary, non-zero exit on failure). Reuse the `frontmatter()` helper.
3. Derive paths:
   ```bash
   SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
   PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
   AGENT="$PROJECT_ROOT/assets/agents/fbk-test-reviewer.md"
   ```
4. Provide `body_lines()` that emits the file body after the second `---`:
   ```bash
   body_lines() { awk '/^---$/{c++; if(c==2){found=1; next}} found' "$1"; }
   ```
5. Provide `persona_section()` that emits lines from body start up to (but excluding) the first `^## ` heading, using awk:
   ```bash
   persona_section() {
     body_lines "$1" | awk '/^## /{exit} {print}'
   }
   ```
6. Implement these tests:
   - **Test 1: file exists and is non-empty** — `[ -s "$AGENT" ]`.
   - **Test 2: has valid YAML frontmatter** — first line is `---`, at least two `---` lines exist.
   - **Test 3: persona section contains at least 5 lines (distinguishes a real persona block from the existing bare instruction)** — `[ "$(persona_section "$AGENT" | wc -l | tr -d ' ')" -ge 5 ]`. The current body has a single-sentence instruction before `## Context isolation`, giving 1-2 non-blank lines; a real persona block (activation + `## Output quality bars` heading + ≥3 bullet lines) exceeds 5 lines. This test fails pre-implementation and passes post-implementation.
   - **Test 4: persona section at or below 40 lines** — `[ "$(persona_section "$AGENT" | wc -l | tr -d ' ')" -le 40 ]`.
   - **Test 5: persona section contains role-activation language** — grep persona section case-insensitive for `QA engineer` (the spec's specified activation phrase).
   - **Test 6: persona section contains `## Output quality bars` heading** — grep body for `^## Output quality bars$`. (The heading lives inside the persona section, so matching against body covers it; task 04's approach could also scope to persona_section if stricter bounding is desired — here we use body to allow the heading to be the last line before a sibling section.)
   - **Test 7: existing task-logic section `## Evaluation criteria` preserved** — grep body for `^## Evaluation criteria$`.
   - **Test 8: existing task-logic section `## Context isolation` preserved** — grep body for `^## Context isolation$`.
   - **Test 9: existing task-logic section `## Override mechanism` preserved** — grep body for `^## Override mechanism$`.
   - **Test 10: pipeline-blocking authority reference preserved** — grep body for `pipeline-blocking` (case-insensitive). This is load-bearing language from the existing agent that must survive the persona addition.
7. Total tests: 10.
8. End with the standard summary block.
9. Run `bash tests/sdl-workflow/test-test-reviewer-persona.sh`. Tests 3, 5, and 6 must fail pre-implementation — the current body has fewer than 5 lines before the first task-logic heading, contains no `QA engineer` phrase, and has no `## Output quality bars` heading. Test 4 (40-line ceiling) passes pre-implementation (the existing body is well under 40 lines) and must continue to pass post-implementation. The preservation assertions (tests 7, 8, 9, 10) pass pre-implementation; that is expected. Overall exit status is non-zero.

## Files to create/modify

- **Create**: `tests/sdl-workflow/test-test-reviewer-persona.sh` — new test file. No existing test covers the persona section of `fbk-test-reviewer.md`. `tests/sdl-workflow/test-test-reviewer-agent.sh` exists but targets different behavior (test-reviewer evaluation criteria coverage); this test focuses on the persona section's structural presence and the 40-line ceiling.

## Test requirements

| Level | Behavior under test | Expected assertion |
|-------|--------------------|--------------------|
| Unit | Agent file exists | `[ -s "$AGENT" ]` |
| Unit | Agent has valid frontmatter | `head -1 == '---'` and `grep -c '^---$' >= 2` |
| Unit | Persona section has at least 5 lines (distinguishes real persona from existing bare instruction) | `wc -l` on `persona_section` ≥ 5 |
| Unit | Persona section at or below 40 lines | `wc -l` on `persona_section` ≤ 40 |
| Unit | Persona contains role-activation language | case-insensitive `grep` for `QA engineer` |
| Unit | Persona contains `Output quality bars` heading | `grep -q '^## Output quality bars$'` on body |
| Unit | Existing task-logic sections preserved | `grep -q` for each of three exact heading strings |
| Unit | Pipeline-blocking authority reference preserved | case-insensitive `grep` for `pipeline-blocking` |

All tests must be runnable pre-implementation; tests 3, 5, and 6 must fail against the current file. Test 4 passes pre-implementation and post-implementation (the persona-section ≤40-line ceiling is satisfied by both the pre-existing bare instruction and the post-implementation persona).

## Acceptance criteria

- 10 TAP tests covering persona presence, 40-line persona-section ceiling, role-activation language, required heading, and preservation of three existing task-logic headings plus load-bearing authority language
- Follows existing test suite conventions exactly
- All assertions are grep/awk/wc against file content
- Covers AC-03 (persona added, existing logic preserved) and the structural half of AC-06

## Model

Haiku

## Wave

1
