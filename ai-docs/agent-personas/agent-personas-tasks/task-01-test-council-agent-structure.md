---
id: task-01
type: test
wave: 1
covers: [AC-02, AC-06]
files_to_create:
  - tests/sdl-workflow/test-council-agent-personas.sh
completion_gate: "bash tests/sdl-workflow/test-council-agent-personas.sh exits non-zero before implementation"
---

## Objective

Create a TAP-style bash test that validates each of the 6 council agent files has valid frontmatter, a full-file body at or below the 40-line persona ceiling, and contains neither forbidden description-heavy headings nor forbidden section patterns from the current template.

## Context

The 6 council agent files (`fbk-council-architect.md`, `fbk-council-analyst.md`, `fbk-council-builder.md`, `fbk-council-guardian.md`, `fbk-council-security.md`, `fbk-council-advocate.md`) currently follow a ~75-line description-heavy template with headings like `## Your Identity`, `## Your Expertise`, `## How You Contribute`, `## Your Communication Style`, `## In Council Discussions`, and `## Critical Behaviors`. The restructuring replaces them with an activation-focused pattern: role activation line, `## Output quality bars`, optional `## Anti-defaults`, optional `## Authority`. The full file (frontmatter excluded for line counting of body) must not exceed 40 lines of body, measured from the first content line after the closing `---` of the frontmatter to end-of-file.

Council agents are persona-only — they contain no task logic, so the 40-line ceiling applies to the entire body. This is the structural check for AC-02 and the structural half of AC-06 (sections exist and match the target pattern; the quality of persona content is human judgment).

All 6 files live under `assets/agents/`. Test runs before any implementation, so every assertion should currently fail.

## Instructions

1. Create `tests/sdl-workflow/test-council-agent-personas.sh` executable (`chmod +x`).
2. Follow the TAP boilerplate from `tests/sdl-workflow/test-code-review-structural.sh`: `#!/usr/bin/env bash`, `set -uo pipefail`, `PASS`/`FAIL`/`TOTAL` counters, `ok()`/`not_ok()` helpers, `echo "TAP version 13"` header, final `1..$TOTAL` summary, non-zero exit on any failure. Reuse the `frontmatter()` helper from that file.
3. Derive `PROJECT_ROOT` the same way as the reference test:
   ```bash
   SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
   PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
   ```
4. Define an array of the 6 council agent file paths under `$PROJECT_ROOT/assets/agents/`:
   - `fbk-council-architect.md`
   - `fbk-council-analyst.md`
   - `fbk-council-builder.md`
   - `fbk-council-guardian.md`
   - `fbk-council-security.md`
   - `fbk-council-advocate.md`
5. Provide a helper `body_lines()` that prints the file body (everything after the second `---` line) and a helper `body_line_count()` that prints the line count of the body:
   ```bash
   body_lines() { awk '/^---$/{c++; if(c==2){found=1; next}} found' "$1"; }
   body_line_count() { body_lines "$1" | wc -l | tr -d ' '; }
   ```
6. For each of the 6 files, emit these tests (24 total across the 6 files, plus 6 forbidden-section tests below):
   - **Test A — file exists and non-empty**: `[ -s "$FILE" ]`.
   - **Test B — has valid YAML frontmatter**: first line is `---` and at least two `---` lines exist.
   - **Test C — body at or below 40 lines**: `[ "$(body_line_count "$FILE")" -le 40 ]`.
   - **Test D — body contains an `## Output quality bars` heading**: grep body for `^## Output quality bars$`.
7. For each of the 6 files, emit one compound forbidden-section test that fails if ANY of these headings are found in the body (use `grep -qE` against a pipe-separated alternation, negating the match):
   - `^## Your Identity`
   - `^## Your Expertise`
   - `^## How You Contribute`
   - `^## Your Communication Style`
   - `^## In Council Discussions`
   - `^## Critical Behaviors`
   The test passes when the grep returns non-zero (no forbidden heading present).
8. Total tests: 30 (6 files x 5 checks).
9. End with the standard summary block:
   ```bash
   echo "1..$TOTAL"
   echo "# tests $TOTAL"
   echo "# pass  $PASS"
   echo "# fail  $FAIL"
   [ "$FAIL" -eq 0 ] || exit 1
   ```
10. Run `bash tests/sdl-workflow/test-council-agent-personas.sh`. Confirm the script exits non-zero against the pre-restructuring files. Record the expected-failure state in the task summary when handing off.

## Files to create/modify

- **Create**: `tests/sdl-workflow/test-council-agent-personas.sh` — new test file. No existing test covers the council agents' structural shape. The closest existing file is `test-code-review-structural.sh`, which tests only the Detector and Challenger.

## Test requirements

| Level | Behavior under test | Expected assertion |
|-------|--------------------|--------------------|
| Unit | Each council file exists and is non-empty | `[ -s "$FILE" ]` passes |
| Unit | Each council file has YAML frontmatter with two `---` delimiters | `head -1 == '---'` and `grep -c '^---$' >= 2` |
| Unit | Each council file body is at or below 40 lines | `body_line_count <= 40` |
| Unit | Each council body contains an `Output quality bars` section heading | `grep -q '^## Output quality bars$'` on body |
| Unit | Each council body contains no forbidden description-heavy headings | negated `grep -qE` against the 6-pattern alternation |

All tests must fail before implementation (bodies currently exceed 40 lines and still contain the forbidden headings).

## Acceptance criteria

- 30 TAP tests (5 per agent x 6 agents) covering existence, frontmatter validity, body-length ceiling, required-heading presence, and forbidden-heading absence
- Test file follows the conventions in `tests/sdl-workflow/test-code-review-structural.sh` (TAP header, helpers, summary, exit code)
- All assertions are local grep/awk/wc against file content — no network or LLM involvement
- Covers AC-02 (structural shape of council agents) and the structural half of AC-06 (mechanical presence/absence checks; persona-content quality is human judgment)

## Model

Haiku

## Wave

1
