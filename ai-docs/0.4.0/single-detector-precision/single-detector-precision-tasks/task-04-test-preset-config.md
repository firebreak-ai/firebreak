---
id: task-04
type: test
wave: 1
covers: [AC-09]
files_to_create:
  - tests/sdl-workflow/test-preset-config.sh
completion_gate: "bash tests/sdl-workflow/test-preset-config.sh exits 0"
---

## Objective

Create a TAP-style bash test that validates the preset configuration file contains all four presets with correct allowed_types arrays and default_severity_threshold values.

## Context

Detection presets are being formalized in `assets/config/presets.json`. The file must contain four presets:

| Preset | allowed_types | default_severity_threshold |
|--------|--------------|---------------------------|
| behavioral-only | ["behavioral"] | "minor" |
| structural | ["structural"] | "minor" |
| test-only | ["test-integrity"] | "minor" |
| full | ["behavioral", "structural", "test-integrity", "fragile"] | "minor" |

The file is standard-library JSON, parseable by `python3 -c 'import json, sys; ...'` without external dependencies.

## Instructions

Create `tests/sdl-workflow/test-preset-config.sh` following the TAP pattern in `tests/sdl-workflow/test-code-review-structural.sh`.

Define variables:
```bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PRESETS="$PROJECT_ROOT/assets/config/presets.json"
```

Implement these tests:

**Test 1: presets.json exists and is non-empty**
`[ -s "$PRESETS" ]`

**Test 2: presets.json is valid JSON**
Run `python3 -c "import json, sys; json.load(sys.stdin)" < "$PRESETS" 2>/dev/null`. Test passes if exit code is 0.

**Test 3: presets.json contains behavioral-only preset**
Run `python3 -c "import json, sys; d=json.load(sys.stdin); assert 'behavioral-only' in d" < "$PRESETS" 2>/dev/null`. Test passes if exit code is 0.

**Test 4: behavioral-only preset has allowed_types ["behavioral"]**
Run `python3 -c "import json, sys; d=json.load(sys.stdin); assert d['behavioral-only']['allowed_types'] == ['behavioral']" < "$PRESETS" 2>/dev/null`.

**Test 5: behavioral-only preset has default_severity_threshold "minor"**
Run `python3 -c "import json, sys; d=json.load(sys.stdin); assert d['behavioral-only']['default_severity_threshold'] == 'minor'" < "$PRESETS" 2>/dev/null`.

**Test 6: structural preset has allowed_types ["structural"]**
Run `python3 -c "import json, sys; d=json.load(sys.stdin); assert d['structural']['allowed_types'] == ['structural']" < "$PRESETS" 2>/dev/null`.

**Test 7: test-only preset has allowed_types ["test-integrity"]**
Run `python3 -c "import json, sys; d=json.load(sys.stdin); assert d['test-only']['allowed_types'] == ['test-integrity']" < "$PRESETS" 2>/dev/null`.

**Test 8: full preset has all four types in allowed_types**
Run `python3 -c "import json, sys; d=json.load(sys.stdin); assert set(d['full']['allowed_types']) == {'behavioral','structural','test-integrity','fragile'}" < "$PRESETS" 2>/dev/null`.

**Test 9: all four presets have default_severity_threshold "minor"**
Run `python3 -c "import json, sys; d=json.load(sys.stdin); assert all(d[k]['default_severity_threshold']=='minor' for k in ['behavioral-only','structural','test-only','full'])" < "$PRESETS" 2>/dev/null`.

**Test 10: presets.json contains exactly four presets**
Run `python3 -c "import json, sys; d=json.load(sys.stdin); assert len(d) == 4" < "$PRESETS" 2>/dev/null`.

End with standard summary block.

## Files to create/modify

Create: `tests/sdl-workflow/test-preset-config.sh` (make executable)

## Test requirements

Executable, exits 0/1. Uses `python3` (available in standard environments) for JSON parsing. No external Python dependencies.

## Acceptance criteria

- 10 TAP tests: file existence, valid JSON, each of 4 presets present with correct allowed_types and threshold, count validation
- Follows existing test suite conventions
- All tests validate `assets/config/presets.json` structure

## Model

sonnet

## Wave

1
