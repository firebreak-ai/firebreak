---
id: task-05
type: test
wave: 1
covers: [AC-01]
files_to_create:
  - tests/sdl-workflow/test-agents-md-persona-guidance.sh
completion_gate: "bash tests/sdl-workflow/test-agents-md-persona-guidance.sh exits non-zero before implementation"
---

## Objective

Create a TAP-style bash test that validates `assets/fbk-docs/fbk-context-assets/agents.md` contains a persona authoring guidance section covering each required subsection from the spec: enterprise activation baseline, correctness-vs-maintainability rationale, persona structure (role activation, output quality bars, anti-defaults), personas and spawn prompts, reference implementations, what not to include, and when personas are unnecessary.

## Context

`assets/fbk-docs/fbk-context-assets/agents.md` is the authoring guidance document for Firebreak agents. It currently has top-level sections `## Agent Definition Structure`, `## When to Use an Agent vs. Alternatives`, `## Capability Scoping`, `## Instruction Design`, `## Scope`, and `## Security`. The spec adds a new section covering persona authoring guidance with seven required subsections. Each subsection can be identified by a content anchor phrase chosen for low false-positive risk — the test greps for the anchor phrase within the file, confirming the conceptual coverage is present.

The spec's required coverage (from AC-01 and section 4.1 of the spec):

1. Enterprise activation as the baseline (persona grounds the agent in a professional enterprise role; this is the highest-leverage persona instruction)
2. Correctness-vs-maintainability rationale (personas improve maintainability, pipeline gates engineer correctness)
3. Persona structure (role activation, output quality bars, anti-defaults)
4. Personas and spawn prompts precedence (persona defines quality; spawn prompt defines task; quality bars in the persona take precedence)
5. Reference implementations (Detector and Challenger)
6. What not to include (expertise lists, communication style, personality descriptions, generic professional advice)
7. When a persona is unnecessary (purely mechanical tasks)

This task covers AC-01 only. The persona-guidance section is a new top-level heading in `agents.md`; pre-implementation, the section does not exist and every subsection test must fail.

## Instructions

1. Create `tests/sdl-workflow/test-agents-md-persona-guidance.sh` executable (`chmod +x`).
2. Follow the TAP boilerplate from `tests/sdl-workflow/test-code-review-structural.sh` (`set -uo pipefail`, counters, `ok()`/`not_ok()`, `TAP version 13` header, `1..$TOTAL` summary, non-zero exit on failure).
3. Derive paths:
   ```bash
   SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
   PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
   DOC="$PROJECT_ROOT/assets/fbk-docs/fbk-context-assets/agents.md"
   ```
4. Implement these tests. For each, grep the full file case-insensitive unless stated otherwise.
   - **Test 1: file exists and is non-empty** — `[ -s "$DOC" ]`.
   - **Test 2: contains a top-level persona authoring guidance section** — grep for `^## .*[Pp]ersona` (case-insensitive, a top-level `##` heading whose text references persona). This confirms a dedicated section heading exists; the subsection checks below verify coverage within it.
   - **Test 3: enterprise activation baseline coverage** — grep case-insensitive for both `enterprise` AND `activation` appearing in the file (separate grep invocations, both must succeed). Anchor phrase: "enterprise activation."
   - **Test 4: correctness-vs-maintainability rationale** — grep case-insensitive for `maintainability` AND separately for `correctness`. Both required.
   - **Test 5: persona structure — role activation** — grep case-insensitive for `role activation`.
   - **Test 6: persona structure — output quality bars** — grep for `output quality bars` (case-insensitive).
   - **Test 7: persona structure — anti-defaults** — grep case-insensitive for `anti-default` (accepts `anti-default` or `anti-defaults`).
   - **Test 8: personas and spawn prompts precedence** — grep case-insensitive for `spawn prompt`.
   - **Test 9: reference implementations — Detector and Challenger named** — grep for both `Detector` and `Challenger` (case-sensitive; these are proper nouns in the spec).
   - **Test 10: what not to include** — grep case-insensitive for `not to include` or `what not to include` (accepts either). Use: `grep -qiE 'what not to include|not to include'`.
   - **Test 11: when personas are unnecessary** — grep case-insensitive for `unnecessary`. This is the spec's exact phrasing for the subsection.
   - **Test 12: mechanical-task example named** — grep case-insensitive for `mechanical` (the spec's criterion for when a persona adds no value).
5. Total tests: 12.
6. End with the standard summary block.
7. Run `bash tests/sdl-workflow/test-agents-md-persona-guidance.sh`. All subsection tests (3-12) must fail against the current `agents.md` — no persona authoring guidance exists yet. Test 1 and 2 may fail (2 definitely fails pre-implementation; 1 passes because the file already exists). Overall exit status is non-zero.

## Files to create/modify

- **Create**: `tests/sdl-workflow/test-agents-md-persona-guidance.sh` — new test file. No existing test validates `agents.md` content. The closest pattern is `test-code-review-structural.sh`, which validates agent-file structure rather than context-asset docs.

## Test requirements

| Level | Behavior under test | Expected assertion |
|-------|--------------------|--------------------|
| Unit | `agents.md` exists | `[ -s "$DOC" ]` |
| Unit | `agents.md` has a top-level persona authoring guidance section | `grep -qE '^## .*[Pp]ersona'` |
| Unit | Doc covers enterprise activation baseline | `grep -qi enterprise` AND `grep -qi activation` |
| Unit | Doc covers correctness-vs-maintainability rationale | `grep -qi maintainability` AND `grep -qi correctness` |
| Unit | Doc covers persona structure elements | `grep -qi` for `role activation`, `output quality bars`, `anti-default` |
| Unit | Doc covers personas and spawn prompts precedence | `grep -qi 'spawn prompt'` |
| Unit | Doc names Detector and Challenger as reference implementations | `grep -q Detector` AND `grep -q Challenger` |
| Unit | Doc covers what not to include | `grep -qiE 'what not to include\|not to include'` |
| Unit | Doc covers when personas are unnecessary | `grep -qi unnecessary` |
| Unit | Doc names mechanical tasks as persona-unnecessary | `grep -qi mechanical` |

All assertions in tests 2-12 must fail pre-implementation.

## Acceptance criteria

- 12 TAP tests covering presence of the persona authoring guidance section and each of the seven required content anchors from the spec
- Follows existing test suite conventions exactly
- All assertions are grep-based against `assets/fbk-docs/fbk-context-assets/agents.md`
- Covers AC-01 exclusively

## Model

Haiku

## Wave

1
