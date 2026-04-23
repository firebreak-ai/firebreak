---
id: task-04
type: test
wave: 1
covers: [AC-05, AC-06]
files_to_create:
  - tests/sdl-workflow/test-new-persona-agents.sh
completion_gate: "bash tests/sdl-workflow/test-new-persona-agents.sh exits non-zero before implementation"
---

## Objective

Create a TAP-style bash test that validates the three new persona-only agent files (`fbk-spec-author.md`, `fbk-task-compiler.md`, `fbk-implementer.md`) exist with valid frontmatter, bodies at or below the 40-line persona ceiling, role-activation language, an `## Output quality bars` heading, and the tool allowlists specified in the spec.

## Context

The spec creates three new agent definition files under `assets/agents/`. Each is persona-only — it defines the agent's role activation, quality bars, and optional anti-defaults; no task logic. The 40-line ceiling applies to the entire body of each file. The spec specifies tool allowlists per agent:

- `fbk-spec-author.md` — tools: Read, Grep, Glob (read-only; the skill handles writes). Role activation: "principal engineer writing technical specifications."
- `fbk-task-compiler.md` — tools: Read, Grep, Glob (read-only). Role activation: "tech lead decomposing a reviewed spec into implementable units." This single agent serves both the test-task and impl-task roles in `/fbk-breakdown`; only one file exists.
- `fbk-implementer.md` — tools: Read, Grep, Glob, Edit, Write, Bash (full implementation capability). Role activation: "senior engineer implementing against a reviewed specification."

This task covers AC-05 (three new files exist with activation-focused personas) and the structural half of AC-06 (mechanical presence/absence; persona-content quality is human judgment).

## Instructions

1. Create `tests/sdl-workflow/test-new-persona-agents.sh` executable (`chmod +x`).
2. Follow the TAP boilerplate from `tests/sdl-workflow/test-code-review-structural.sh` (`set -uo pipefail`, counters, `ok()`/`not_ok()`, `TAP version 13` header, `1..$TOTAL` summary, non-zero exit on failure). Reuse the `frontmatter()` helper from that file.
3. Derive paths:
   ```bash
   SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
   PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
   SPEC_AUTHOR="$PROJECT_ROOT/assets/agents/fbk-spec-author.md"
   TASK_COMPILER="$PROJECT_ROOT/assets/agents/fbk-task-compiler.md"
   IMPLEMENTER="$PROJECT_ROOT/assets/agents/fbk-implementer.md"
   ```
4. Provide `body_lines()` and `body_line_count()` helpers:
   ```bash
   body_lines() { awk '/^---$/{c++; if(c==2){found=1; next}} found' "$1"; }
   body_line_count() { body_lines "$1" | wc -l | tr -d ' '; }
   ```
5. For EACH of the three agent files, emit these 6 tests:
   - **Test A — file exists and is non-empty**: `[ -s "$FILE" ]`.
   - **Test B — has valid YAML frontmatter**: first line is `---`, at least two `---` lines exist.
   - **Test C — body at or below 40 lines**: `body_line_count "$FILE" -le 40`.
   - **Test D — body contains `## Output quality bars` heading**: `grep -q '^## Output quality bars$'` on body.
   - **Test E — frontmatter contains required `name:` and `description:` fields** (non-empty values): extract via `frontmatter()`, then `grep -q '^name:.*[^[:space:]]'` and `grep -q '^description:.*[^[:space:]]'`.
   - **Test F — frontmatter `tools:` field matches the spec's allowlist** (per-file; see below).
6. For EACH agent file, emit one role-activation test (3 additional tests):
   - `fbk-spec-author.md` — body contains case-insensitive `principal engineer`.
   - `fbk-task-compiler.md` — body contains case-insensitive `tech lead`.
   - `fbk-implementer.md` — body contains case-insensitive `senior engineer`.
7. The per-file `tools:` checks for Test F:
   - `fbk-spec-author.md`: frontmatter tools contain `Read`, `Grep`, `Glob` and do NOT contain `Edit`, `Write`, `Bash`. Use two grep checks — a positive check that all three allowed tools appear, and a negated check that none of the forbidden tools appear.
   - `fbk-task-compiler.md`: same requirement as spec-author (Read, Grep, Glob only).
   - `fbk-implementer.md`: frontmatter tools contain all six — `Read`, `Grep`, `Glob`, `Edit`, `Write`, `Bash`.
8. Total tests: 21 (3 files x 6 structural + 3 role-activation).
9. End with the standard summary block.
10. Run `bash tests/sdl-workflow/test-new-persona-agents.sh`. All tests must fail pre-implementation — the three files do not yet exist.

## Files to create/modify

- **Create**: `tests/sdl-workflow/test-new-persona-agents.sh` — new test file. No existing test covers these three agent files because they do not yet exist. The pattern follows `tests/sdl-workflow/test-code-review-structural.sh` for frontmatter/structural validation.

## Test requirements

| Level | Behavior under test | Expected assertion |
|-------|--------------------|--------------------|
| Unit | Each new agent file exists | `[ -s "$FILE" ]` passes |
| Unit | Each file has valid YAML frontmatter | `head -1 == '---'` and `grep -c '^---$' >= 2` |
| Unit | Each body at or below 40 lines | `body_line_count` ≤ 40 |
| Unit | Each body contains `Output quality bars` heading | `grep -q '^## Output quality bars$'` |
| Unit | Each frontmatter has non-empty name and description | `grep` against extracted frontmatter |
| Unit | Each frontmatter tools field matches the per-file allowlist | positive `grep` for required tools + negated `grep` for forbidden tools |
| Unit | Each body contains the spec-specified role-activation phrase | case-insensitive `grep` for phrase |

## Acceptance criteria

- 21 TAP tests (6 structural x 3 files + 3 role-activation)
- Follows existing test suite conventions exactly
- All assertions are grep/awk/wc against file content
- Covers AC-05 (new agent files exist with activation-focused personas) and the structural half of AC-06

## Model

Haiku

## Wave

1
