---
id: T-01
type: test
wave: 1
covers: ["AC-03", "AC-04", "AC-08", "AC-12"]
files_to_create: ["tests/sdl-workflow/test-code-review-structural.sh"]
completion_gate: "Test script runs and all tests fail (target files do not exist yet)"
---

## Objective

Creates a bash test script that validates the Detector and Challenger agent definitions, the code review guide, and the AI failure mode checklist contain all required structural elements.

## Context

Phase 1.6 creates four shared context assets that Wave 1-2 implementation tasks will produce:

- `home/dot-claude/agents/code-review-detector.md` — Detector agent definition with YAML frontmatter (`name`, `description`, `tools`, `model` fields) and a Markdown body. The `tools` field must list exactly `Read, Grep, Glob, Bash`. The `description` field must contain matchable language for code analysis and pattern detection.
- `home/dot-claude/agents/code-review-challenger.md` — Challenger agent definition with the same frontmatter structure. The `tools` field must list exactly `Read, Grep, Glob` (no Bash — read-only, no tool execution). The `description` field must contain matchable language for adversarial verification and evidence-based assessment.
- `home/dot-claude/docs/sdl-workflow/code-review-guide.md` — Shared reference doc containing the behavioral comparison methodology, finding format schema, orchestration protocol, and retrospective field requirements.
- `home/dot-claude/docs/sdl-workflow/ai-failure-modes.md` — Numbered checklist of 10 AI failure mode patterns with detection heuristics.

The existing agent definition at `home/dot-claude/agents/test-reviewer.md` provides the frontmatter convention: `name`, `description`, `tools`, `model` fields between `---` delimiters.

This test script covers four ACs:
- AC-08: Agent read-only constraint — Detector uses `Read, Grep, Glob, Bash`; Challenger uses `Read, Grep, Glob` only. Neither agent has Write or Edit tools.
- AC-12: Retrospective schema — the code review guide documents all required retrospective fields (sighting counts, verification rounds, scope assessment, context health proxies, tool usage, finding quality).
- AC-03: Finding format — the code review guide documents the complete finding schema (finding ID, sighting reference, location, category, current behavior, expected behavior, source of truth, evidence) with the four allowed category values (`semantic-drift`, `structural`, `test-integrity`, `nit`).
- AC-04: Behavioral comparison — both agent definitions and the code review guide use "describe what this does, then compare" framing. The guide must contain behavioral comparison language and must not contain "find bugs" or "defect detection" as instructional framing.

Follow the TAP format and boilerplate conventions established in `tests/sdl-workflow/test-test-reviewer-agent.sh`.

## Instructions

1. Create `tests/sdl-workflow/test-code-review-structural.sh` as a bash test script. Use `set -uo pipefail`. Define `PASS`, `FAIL`, `TOTAL` counters. Define `ok()` and `not_ok()` helper functions matching the pattern in `tests/sdl-workflow/test-test-reviewer-agent.sh`. Print `TAP version 13` before the first test.

2. Determine project root using `cd "$(dirname "$0")/../.." && pwd`. Define these path variables:
   - `DETECTOR="$PROJECT_ROOT/home/dot-claude/agents/code-review-detector.md"`
   - `CHALLENGER="$PROJECT_ROOT/home/dot-claude/agents/code-review-challenger.md"`
   - `GUIDE="$PROJECT_ROOT/home/dot-claude/docs/sdl-workflow/code-review-guide.md"`
   - `CHECKLIST="$PROJECT_ROOT/home/dot-claude/docs/sdl-workflow/ai-failure-modes.md"`

3. Define a `frontmatter()` helper that takes a file path argument and extracts lines between the first `---` and second `---` (exclusive of both delimiters). Use the same sed approach from the test-reviewer-agent test: `sed -n '2,/^---$/p' "$1" | sed '$d'`.

4. Write test: Detector agent file exists and is non-empty. Assert `-s "$DETECTOR"`.

5. Write test: Detector has YAML frontmatter. Assert line 1 is `---` and there are at least 2 `---` lines.

6. Write test: Detector frontmatter contains `name:` field with value containing `detector`. Extract frontmatter with the helper. Search for `^name:` and assert the value contains `detector` (case-insensitive).

7. Write test: Detector frontmatter contains `description:` with non-empty value. Assert frontmatter contains `^description:` with content after the colon.

8. Write test: Detector `tools:` field lists `Read, Grep, Glob, Bash`. Extract the `tools:` line from frontmatter. Assert it contains all four tool names: `Read`, `Grep`, `Glob`, `Bash`. Assert it does NOT contain `Write` or `Edit`.

9. Write test: Detector does not have Write or Edit tools. This is the AC-08 constraint. Parse the full `tools:` value. Assert no match for `Write` or `Edit` in the tools line (redundant with test 8 but makes the AC-08 assertion explicit for traceability).

10. Write test: Detector description contains code analysis language. Assert the `description:` value contains one of: `analysis`, `analyz`, `detect`, `code review`, `pattern` (case-insensitive).

11. Write test: Challenger agent file exists and is non-empty. Assert `-s "$CHALLENGER"`.

12. Write test: Challenger has YAML frontmatter. Same structure check as test 5.

13. Write test: Challenger frontmatter contains `name:` field with value containing `challenger`. Case-insensitive match.

14. Write test: Challenger frontmatter contains `description:` with non-empty value.

15. Write test: Challenger `tools:` field lists exactly `Read, Grep, Glob`. Extract the `tools:` line. Assert it contains `Read`, `Grep`, `Glob`. Assert it does NOT contain `Bash`, `Write`, or `Edit`.

16. Write test: Challenger does not have Bash, Write, or Edit tools. AC-08 constraint. Parse the `tools:` value. Assert no match for `Bash`, `Write`, or `Edit`.

17. Write test: Challenger description contains adversarial verification language. Assert the `description:` value contains one of: `adversarial`, `verif`, `challenger`, `skeptic`, `evidence` (case-insensitive).

18. Write test: Code review guide exists and is non-empty. Assert `-s "$GUIDE"`.

19. Write test: Guide documents finding format with all required fields. Search the guide for each of these field names (case-insensitive): `finding id`, `sighting`, `location`, `category`, `current behavior`, `expected behavior`, `source of truth`, `evidence`. Assert all 8 are present. This covers AC-03.

20. Write test: Guide documents allowed category values. Search the guide for each of the four category values as exact strings: `semantic-drift`, `structural`, `test-integrity`, `nit`. Assert all 4 are present. This covers AC-03.

21. Write test: Guide documents sighting format with all required fields. Search for: `sighting id`, `location`, `category`, `observation`, `expected`, `source of truth`. Assert all are present.

22. Write test: Guide documents behavioral comparison methodology. Search for `behavioral comparison` or `describe what` combined with `compare` (case-insensitive). Assert at least one match. This covers AC-04.

23. Write test: Guide does not use defect-detection framing. Search the guide for `find bugs` or `defect.detection` as instructional framing (not as a negative example). Use `grep -c` to count occurrences of `find bugs` that are NOT preceded by "Don't" or "not" or "never" within 20 characters. A simple approach: assert that `find bugs` appears only in lines also containing `don't` or `not` or `never` or `avoid` (i.e., only as negative examples), or does not appear at all. This covers AC-04.

24. Write test: Guide documents retrospective fields. Search the guide for each required retrospective field (case-insensitive): `sighting counts`, `verification rounds`, `scope assessment`, `tool usage`, `finding quality`. Assert all 5 are present. Note: `context health` is the sixth field per the spec — also assert its presence. This covers AC-12.

25. Write test: AI failure mode checklist exists and is non-empty. Assert `-s "$CHECKLIST"`.

26. Write test: Checklist contains numbered items. Count lines matching a numbered list pattern (`^[0-9]+\.` or `^[0-9]+\)` or `^- **[0-9]+`). Assert the count is at least 10 (the spec defines 10 failure modes).

27. Write test: Checklist contains key failure mode patterns. Search for at least 5 of these keywords from the 10 defined modes (case-insensitive): `re-implement`, `duplication`, `magic number`, `dead code`, `hardcoded`, `inconsistent`, `middleware`, `trivially-true`, `test name`, `surface-level`. Assert at least 5 matches.

28. End the script with a summary: print `echo ""`, then `echo "# $PASS/$TOTAL tests passed"`. Exit 0 if `$FAIL` is 0, exit 1 otherwise.

## Files to create/modify

- `tests/sdl-workflow/test-code-review-structural.sh` (create)

## Test requirements

This is a test task. Tests to write (all in `test-code-review-structural.sh`):

1. Structural: Detector agent file exists and is non-empty
2. Structural: Detector has YAML frontmatter
3. Structural: Detector name field contains "detector"
4. Structural: Detector description field is non-empty
5. Structural: Detector tools field lists Read, Grep, Glob, Bash (AC-08)
6. Structural: Detector tools field excludes Write and Edit (AC-08)
7. Structural: Detector description contains code analysis language
8. Structural: Challenger agent file exists and is non-empty
9. Structural: Challenger has YAML frontmatter
10. Structural: Challenger name field contains "challenger"
11. Structural: Challenger description field is non-empty
12. Structural: Challenger tools field lists Read, Grep, Glob only (AC-08)
13. Structural: Challenger tools field excludes Bash, Write, Edit (AC-08)
14. Structural: Challenger description contains adversarial verification language
15. Structural: Code review guide exists and is non-empty
16. Structural: Guide documents finding format with all 8 required fields (AC-03)
17. Structural: Guide documents all 4 allowed category values (AC-03)
18. Structural: Guide documents sighting format with required fields
19. Structural: Guide documents behavioral comparison methodology (AC-04)
20. Structural: Guide does not use defect-detection framing as instructions (AC-04)
21. Structural: Guide documents all required retrospective fields (AC-12)
22. Structural: AI failure mode checklist exists and is non-empty
23. Structural: Checklist contains at least 10 numbered items
24. Structural: Checklist contains key failure mode keywords

## Acceptance criteria

- AC-03: Finding format validation — the code review guide documents the complete finding schema (all 8 fields, all 4 category values)
- AC-04: Behavioral comparison — the guide uses "describe and compare" framing, not "find bugs" framing; agent descriptions use matchable language
- AC-08: Agent read-only constraint — Detector tools are `Read, Grep, Glob, Bash`; Challenger tools are `Read, Grep, Glob`. Neither has Write or Edit.
- AC-12: Retrospective schema — the guide documents all required retrospective fields (sighting counts, verification rounds, scope assessment, context health, tool usage, finding quality)

## Model

Haiku

## Wave

Wave 1
