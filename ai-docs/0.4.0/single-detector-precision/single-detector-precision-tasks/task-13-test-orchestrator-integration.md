---
id: task-13
type: test
wave: 2
covers: [AC-11]
files_to_create:
  - tests/sdl-workflow/test-orchestrator-pipeline-integration.sh
completion_gate: "bash tests/sdl-workflow/test-orchestrator-pipeline-integration.sh exits 0"
---

## Objective

Create a TAP-style bash test that validates SKILL.md's Detection-Verification Loop references the JSON pipeline: Detector produces JSON, `pipeline.py run` filters, Challenger receives JSON, `pipeline.py to-markdown` converts for the review report. Preset defaults to `behavioral-only`, severity to `minor`, both overridable.

## Context

The Detection-Verification Loop in `assets/skills/fbk-code-review/SKILL.md` is being updated to flow:
1. Detector produces JSON sightings
2. `uv run pipeline.py run --preset <preset> --min-severity <threshold>` validates, domain-filters, severity-filters
3. Challenger receives filtered JSON sightings (not markdown)
4. Validate Challenger output
5. Filter to verified, assign F-NN IDs
6. `uv run pipeline.py to-markdown` converts findings to markdown for review report
7. Repeat for weakened sightings; terminate per existing bounds

JSON is the working format throughout. Markdown conversion happens once at the end. Default preset is `behavioral-only`, default severity threshold is `minor`.

## Instructions

Create `tests/sdl-workflow/test-orchestrator-pipeline-integration.sh` following the TAP pattern.

Define:
```bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SKILL="$PROJECT_ROOT/assets/skills/fbk-code-review/SKILL.md"
```

**Test 1: SKILL.md references pipeline.py**
`grep -q 'pipeline.py' "$SKILL"`

**Test 2: SKILL.md references uv run for pipeline invocation**
`grep -q 'uv run' "$SKILL"`

**Test 3: SKILL.md references JSON as the working format**
`grep -qi 'JSON' "$SKILL"` — JSON must appear in the Detection-Verification Loop context.

**Test 4: SKILL.md references validate subcommand or run subcommand**
`grep -qE 'validate|\.py run' "$SKILL"`

**Test 5: SKILL.md references domain-filter or preset in pipeline context**
`grep -qiE 'domain.filter|preset' "$SKILL"`

**Test 6: SKILL.md references to-markdown for review report conversion**
`grep -qiE 'to.markdown|to-markdown' "$SKILL"`

**Test 7: SKILL.md specifies behavioral-only as default preset**
`grep -qi 'behavioral-only' "$SKILL"`

**Test 8: SKILL.md specifies minor as default severity threshold**
Extract the Detection-Verification Loop section: `section=$(sed -n '/## Detection-Verification Loop/,/^## /p' "$SKILL")`. Grep section for `minor` as default: `echo "$section" | grep -qiE 'minor|default.*severity'`.

**Test 9: SKILL.md states preset and severity are overridable**
`grep -qiE 'overrid|user.*instruction|user.*specify' "$SKILL"`

**Test 10: SKILL.md Challenger receives JSON, not markdown**
Grep for language indicating Challenger receives JSON: `grep -qiE 'Challenger.*JSON|filtered JSON|JSON sighting' "$SKILL"`.

**Test 11: SKILL.md markdown conversion happens once for review report**
Grep for language indicating single conversion: `grep -qiE 'markdown.*once|convert.*markdown.*report|to-markdown.*report' "$SKILL"`.

**Test 12: SKILL.md still contains stuck-agent recovery**
`grep -qiE 'stuck.agent|unresponsive|relaunch' "$SKILL"`. This verifies the orchestrator rewrite preserved existing functionality.

End with standard summary block.

## Files to create/modify

Create: `tests/sdl-workflow/test-orchestrator-pipeline-integration.sh` (make executable)

## Test requirements

Executable, exits 0/1. Grep-based content validation only.

## Acceptance criteria

- 12 TAP tests: pipeline.py reference, uv run, JSON format, validate/run, domain-filter/preset, to-markdown, behavioral-only default, minor default, overridable, Challenger JSON, single markdown conversion, stuck-agent preservation
- All tests validate `assets/skills/fbk-code-review/SKILL.md` content
- Tests confirm new pipeline integration without breaking existing orchestrator features

## Model

sonnet

## Wave

2
