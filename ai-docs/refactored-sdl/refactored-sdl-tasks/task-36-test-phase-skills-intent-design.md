---
id: task-36
type: test
wave: 2
covers: [AC-01, AC-03]
files_to_create:
  - tests/sdl-workflow/test-phase-skills-intent-design.sh
completion_gate: "tests compile and fail before implementation"
---

## 1. Objective

Creates `tests/sdl-workflow/test-phase-skills-intent-design.sh`, a TAP-format shell integration test asserting that both phase skills — `assets/skills/fbk-intent/SKILL.md` and `assets/skills/fbk-design/SKILL.md` — exist with the required frontmatter and route to / compose / delegate / gate the assets the spec pins for each phase.

## 2. Context

Two new phase skills are being authored (by task-37 and task-38). They are prompt assets, so the "test" is a shell integration test that greps the skill bodies for the structural markers the spec pins — the assertion fails before the skill exists and passes after (a real red→green).

**`fbk-intent` (the first SDL phase)** — what the test must assert is present (from spec §New skills and design/fbk-intent.md):
- frontmatter `description:` and `argument-hint:` fields;
- routes to its phase guide `intent-guide.md` (references the guide leaf);
- composes the two technique skills `fbk-grilling` and `fbk-fresh-eyes` (references both by name);
- delegates PRD drafting to the `fbk-product-author` agent (references the agent);
- runs `intent-gate` (references the gate command);
- reads and (when intent shifts) updates the durable architecture/intent overview (`docs/architecture-overview.md`).

`fbk-intent` is the FIRST phase — it has no upstream, so it does NOT call the prerequisite probe. The test must NOT assert a `check_prerequisites` call in `fbk-intent` (asserting its absence is acceptable but not required; the load-bearing point is the test does not require it).

**`fbk-design` (the second SDL phase)** — what the test must assert is present (from spec §New skills and design/fbk-design.md):
- frontmatter `description:` and `argument-hint:` fields;
- routes to its phase guide `design-guide.md`;
- composes `fbk-grilling` and `fbk-fresh-eyes` (references both by name);
- delegates to the `fbk-architect` agent;
- runs `design-gate`;
- appends enduring decisions to the durable decisions log (`docs/decisions-log.md`);
- invokes the prerequisite probe at mid-pipeline entry — references `check_prerequisites` (the intent-missing-at-design case, AC-12).

Follow the TAP helper pattern from `tests/sdl-workflow/test-technique-skills.sh` and `tests/sdl-workflow/test-code-review-structural.sh`: `#!/usr/bin/env bash`, `set -uo pipefail`, `PASS`/`FAIL`/`TOTAL` counters, `ok()`/`not_ok()` functions, `echo "TAP version 13"`, a `frontmatter()` helper, `SCRIPT_DIR`/`PROJECT_ROOT`, and a TAP summary block.

Before implementation these assertions all fail because the two skill directories and `SKILL.md` files do not exist (the file-exists check fails, and every grep over a missing file fails). That is the correct red state.

## 3. Instructions

1. Create `tests/sdl-workflow/test-phase-skills-intent-design.sh` with the standard TAP boilerplate (`#!/usr/bin/env bash`, `set -uo pipefail`, `PASS=0`, `FAIL=0`, `TOTAL=0`, `ok()`, `not_ok()`, `SCRIPT_DIR`, `PROJECT_ROOT`, `echo "TAP version 13"`).

2. Add the `frontmatter()` helper (copy the pattern from `test-technique-skills.sh`):
   ```bash
   frontmatter() {
     sed -n '2,/^---$/p' "$1" | sed '$d'
   }
   ```

3. Define the path variables:
   ```bash
   INTENT="$PROJECT_ROOT/assets/skills/fbk-intent/SKILL.md"
   DESIGN="$PROJECT_ROOT/assets/skills/fbk-design/SKILL.md"
   SPEC="$PROJECT_ROOT/assets/skills/fbk-spec/SKILL.md"
   BREAKDOWN="$PROJECT_ROOT/assets/skills/fbk-breakdown/SKILL.md"
   ```

4. Write the `fbk-intent` assertions (AC-01). T1: `[ -s "$INTENT" ]` — skill file exists and non-empty. T2: `frontmatter "$INTENT" | grep -q 'description:'` — has description. T3: `frontmatter "$INTENT" | grep -q 'argument-hint:'` — has argument-hint. T4: `grep -q 'intent-guide.md' "$INTENT"` — routes to the intent guide. T5: `grep -q 'fbk-grilling' "$INTENT"` — composes grilling. T6: `grep -q 'fbk-fresh-eyes' "$INTENT"` — composes fresh-eyes. T7: `grep -q 'fbk-product-author' "$INTENT"` — delegates PRD drafting to the product-author agent. T8: `grep -q 'intent-gate' "$INTENT"` — runs the intent gate. T9: `grep -q 'architecture-overview.md' "$INTENT"` — reads/updates the architecture/intent overview.

5. Write the `fbk-design` assertions (AC-03). T10: `[ -s "$DESIGN" ]` — skill file exists and non-empty. T11: `frontmatter "$DESIGN" | grep -q 'description:'` — has description. T12: `frontmatter "$DESIGN" | grep -q 'argument-hint:'` — has argument-hint. T13: `grep -q 'design-guide.md' "$DESIGN"` — routes to the design guide. T14: `grep -q 'fbk-grilling' "$DESIGN"` — composes grilling. T15: `grep -q 'fbk-fresh-eyes' "$DESIGN"` — composes fresh-eyes. T16: `grep -q 'fbk-architect' "$DESIGN"` — delegates to the architect agent. T17: `grep -q 'design-gate' "$DESIGN"` — runs the design gate. T18: `grep -q 'decisions-log.md' "$DESIGN"` — appends to the decisions log. T19: `grep -q 'check_prerequisites' "$DESIGN"` — invokes the prerequisite probe (the intent-missing-at-design case, AC-12).

6. Write the cross-skill prerequisite-probe wiring assertions (AC-12 — the four upstream-missing cases). Keeping these under one shell test consolidates the prereq-wiring sentinels for the spec and breakdown skills that the rewrite touches. The intent-design and code-review cases are asserted elsewhere (T19 above for design; task-05 T6 for code-review).
   - T20: `grep -q 'check_prerequisites' "$SPEC"` — `fbk-spec/SKILL.md` references the prerequisite probe (the design-missing-at-spec case wired by task-31).
   - T21: `grep -q 'check_prerequisites' "$BREAKDOWN"` — `fbk-breakdown/SKILL.md` references the prerequisite probe (the spec-missing-at-breakdown case wired by task-32).

7. Add the TAP summary block at the end (same pattern as the existing shell tests): print `1..$TOTAL` and exit non-zero if `FAIL` > 0.

8. Confirm the script is syntactically valid: `bash -n tests/sdl-workflow/test-phase-skills-intent-design.sh` exits 0. Before the skills exist, running the script must produce failing assertions (red), not a parse error.

## 4. Files to create/modify

- `tests/sdl-workflow/test-phase-skills-intent-design.sh` (create)

## 5. Test requirements

21 TAP assertions:
- `fbk-intent` structure (T1–T9, AC-01): exists + description + argument-hint; routes to intent-guide; composes fbk-grilling + fbk-fresh-eyes; delegates to fbk-product-author; runs intent-gate; reads/updates architecture-overview.
- `fbk-design` structure (T10–T19, AC-03 + the AC-12 probe wiring): exists + description + argument-hint; routes to design-guide; composes fbk-grilling + fbk-fresh-eyes; delegates to fbk-architect; runs design-gate; appends to decisions-log; invokes check_prerequisites.
- Cross-skill prerequisite-probe wiring (T20–T21, AC-12): `fbk-spec/SKILL.md` and `fbk-breakdown/SKILL.md` each reference `check_prerequisites` (the design-missing-at-spec case wired by task-31; the spec-missing-at-breakdown case wired by task-32).

All assertions fail before the relevant skills exist or are wired — the correct red state. The test must not assert a prerequisite-probe call in `fbk-intent` (intent is the first phase, no upstream).

## 6. Acceptance criteria

- `assets/skills/fbk-intent/SKILL.md` exists with `description` + `argument-hint`, routes to `intent-guide.md`, composes `fbk-grilling` and `fbk-fresh-eyes`, delegates to `fbk-product-author`, runs `intent-gate`, and references `architecture-overview.md`.
- `assets/skills/fbk-design/SKILL.md` exists with `description` + `argument-hint`, routes to `design-guide.md`, composes `fbk-grilling` and `fbk-fresh-eyes`, delegates to `fbk-architect`, runs `design-gate`, references `decisions-log.md`, and invokes `check_prerequisites`.
- The script is a valid bash TAP test and is red before the skills are authored.

## 7. Model

Haiku

## 8. Wave

Wave 2
