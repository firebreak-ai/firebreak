---
id: task-09
type: test
wave: 2
covers: [AC-09, AC-10]
files_to_create:
  - tests/sdl-workflow/test-pipeline-domain-filter.sh
  - tests/fixtures/pipeline/mixed-types.json
completion_gate: "bash tests/sdl-workflow/test-pipeline-domain-filter.sh exits 0"
---

## Objective

Create a TAP-style bash test that validates the `pipeline.py domain-filter` subcommand correctly filters sightings by type based on preset configuration, logs dropped sightings to stderr, and reads preset definitions from `assets/config/presets.json`.

## Context

The `domain-filter` subcommand reads a JSON array of validated sightings from stdin and a `--preset` argument. It looks up the preset's `allowed_types` from `assets/config/presets.json` and drops sightings whose `type` is not in the allow list. Dropped sightings are logged to stderr. Valid sightings pass through to stdout.

## Instructions

### Create fixture file `tests/fixtures/pipeline/mixed-types.json`

Array of 4 pre-validated sightings, one of each type. All have valid type-severity combinations:
```json
[
  {
    "id": "S-01",
    "title": "forEach(async) drops return value silently",
    "location": {"file": "src/handler.ts", "start_line": 42},
    "type": "behavioral",
    "severity": "critical",
    "mechanism": "forEach(async callback) discards the Promise returned by each iteration",
    "consequence": "Callbacks execute concurrently with no error propagation to the caller",
    "evidence": "Lines 42-48"
  },
  {
    "id": "S-02",
    "title": "Duplicated validation logic across three handlers",
    "location": {"file": "src/validate.ts", "start_line": 10},
    "type": "structural",
    "severity": "minor",
    "mechanism": "Three handlers each implement the same email validation regex inline",
    "consequence": "Updating validation requires changing three files with no shared reference",
    "evidence": "handler-a.ts:15, handler-b.ts:22, handler-c.ts:31"
  },
  {
    "id": "S-03",
    "title": "Test name claims full CRUD but only tests create",
    "location": {"file": "tests/crud.test.ts", "start_line": 5},
    "type": "test-integrity",
    "severity": "major",
    "mechanism": "Test suite named CRUD operations contains only a single test for create path",
    "consequence": "Coverage report implies read/update/delete are tested when they are not",
    "evidence": "Only one it() block for create"
  },
  {
    "id": "S-04",
    "title": "Hardcoded page size breaks when API changes default",
    "location": {"file": "src/paginator.ts", "start_line": 22},
    "type": "fragile",
    "severity": "major",
    "mechanism": "Page size hardcoded to 10 matches current API default but has no contract",
    "consequence": "When API changes page size, paginator silently returns partial results",
    "evidence": "Line 22: const PAGE_SIZE = 10"
  }
]
```

### Create test file `tests/sdl-workflow/test-pipeline-domain-filter.sh`

Follow the TAP pattern. Define:
```bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PIPELINE="$PROJECT_ROOT/assets/scripts/pipeline.py"
FIXTURES="$PROJECT_ROOT/tests/fixtures/pipeline"
```

Add cleanup trap: `trap 'rm -f /tmp/test-domain-*.json /tmp/test-domain-*-err.txt' EXIT`

**Test 1: behavioral-only preset passes only behavioral sightings**
Run `uv run "$PIPELINE" domain-filter --preset behavioral-only < "$FIXTURES/mixed-types.json" > /tmp/test-domain-behavioral.json 2>/dev/null`. Check output has exactly 1 sighting: `python3 -c "import json,sys; d=json.load(sys.stdin); assert len(d)==1 and d[0]['type']=='behavioral'" < /tmp/test-domain-behavioral.json`.

**Test 2: structural preset passes only structural sightings**
Run with `--preset structural`. Check output has exactly 1 sighting with type `structural`.

**Test 3: test-only preset passes only test-integrity sightings**
Run with `--preset test-only`. Check output has exactly 1 sighting with type `test-integrity`.

**Test 4: full preset passes all sightings**
Run with `--preset full`. Check output has exactly 4 sightings.

**Test 5: domain-filter logs dropped sightings to stderr**
Run `uv run "$PIPELINE" domain-filter --preset behavioral-only < "$FIXTURES/mixed-types.json" > /dev/null 2>/tmp/test-domain-stderr.txt`. Check stderr is non-empty: `[ -s /tmp/test-domain-stderr.txt ]`. Check stderr mentions the dropped types: `grep -q 'structural\|test-integrity\|fragile' /tmp/test-domain-stderr.txt`.

**Test 6: domain-filter with unknown preset exits non-zero**
Run `uv run "$PIPELINE" domain-filter --preset nonexistent < "$FIXTURES/mixed-types.json" > /dev/null 2>/dev/null`. Check exit code is non-zero.

**Test 7: domain-filter on empty array outputs empty array**
Run `echo '[]' | uv run "$PIPELINE" domain-filter --preset behavioral-only > /tmp/test-domain-empty.json 2>/dev/null`. Check output is `[]`: `python3 -c "import json,sys; d=json.load(sys.stdin); assert d==[]" < /tmp/test-domain-empty.json`.

End with standard summary block.

## Files to create/modify

Create: `tests/sdl-workflow/test-pipeline-domain-filter.sh` (make executable)
Create: `tests/fixtures/pipeline/mixed-types.json`

## Test requirements

Executable, exits 0/1. Requires `uv` and `python3`.

## Acceptance criteria

- 7 TAP tests: 4 preset type-filtering tests, stderr logging, unknown preset error, empty input
- Fixture file with 4 sightings covering all types
- Tests validate `pipeline.py domain-filter` via subprocess invocation with presets from `assets/config/presets.json`

## Model

sonnet

## Wave

2
