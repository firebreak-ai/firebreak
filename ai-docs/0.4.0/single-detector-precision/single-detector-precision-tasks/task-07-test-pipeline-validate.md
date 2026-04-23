---
id: task-07
type: test
wave: 2
covers: [AC-01, AC-06, AC-10]
files_to_create:
  - tests/sdl-workflow/test-pipeline-validate.sh
  - tests/fixtures/pipeline/valid-sightings.json
completion_gate: "bash tests/sdl-workflow/test-pipeline-validate.sh exits 0"
---

## Objective

Create a TAP-style bash test with a shared JSON fixture that validates the `pipeline.py validate` subcommand correctly accepts valid sightings, rejects missing required fields, rejects invalid enum values, rejects invalid type-severity combinations, and assigns sequential S-NN IDs.

## Context

`assets/scripts/pipeline.py` provides a `validate` subcommand that reads a JSON array of sightings from stdin, validates required fields, enum values, and the type-severity validity matrix, and outputs valid sightings to stdout with sequential S-NN IDs assigned. Invalid sightings are rejected to stderr. The script runs via `uv run assets/scripts/pipeline.py validate`.

Required-or-reject fields: `id`, `title` (min 10 chars), `location` (must contain `file` and `start_line`), `type` (valid enum), `severity` (valid enum), `mechanism` (min 10 chars), `consequence` (min 10 chars), `evidence`.

Valid type enum values: `behavioral`, `structural`, `test-integrity`, `fragile`.
Valid severity enum values: `critical`, `major`, `minor`, `info`.

## Instructions

### Create fixture file `tests/fixtures/pipeline/valid-sightings.json`

This fixture is shared by multiple test tasks. Array of 3 valid sightings covering different types:
```json
[
  {
    "id": "X-99",
    "title": "forEach(async) drops return value silently",
    "location": {"file": "src/handler.ts", "start_line": 42, "end_line": 55},
    "type": "behavioral",
    "severity": "critical",
    "origin": "introduced",
    "detection_source": "intent",
    "source_of_truth_ref": "intent claim 3",
    "pattern": "async-in-sync-iterator",
    "mechanism": "forEach(async callback) discards the Promise returned by each iteration",
    "consequence": "Callbacks execute concurrently with no error propagation to the caller",
    "evidence": "Lines 42-48: bookingHandler.forEach(async (booking) => { await sendReminder(booking); })",
    "remediation": "Replace forEach(async) with for...of loop"
  },
  {
    "id": "ignored",
    "title": "Duplicated validation logic across three handlers",
    "location": {"file": "src/validate.ts", "start_line": 10},
    "type": "structural",
    "severity": "minor",
    "mechanism": "Three handlers each implement the same email validation regex inline",
    "consequence": "Updating validation requires changing three files with no shared reference",
    "evidence": "src/handler-a.ts:15, src/handler-b.ts:22, src/handler-c.ts:31 all contain /^[a-z]+@/"
  },
  {
    "id": "also-ignored",
    "title": "Test name claims full CRUD coverage but only tests create",
    "location": {"file": "tests/crud.test.ts", "start_line": 5},
    "type": "test-integrity",
    "severity": "major",
    "mechanism": "Test suite named 'CRUD operations' contains only a single test for the create path",
    "consequence": "Coverage report shows the suite as passed, implying read/update/delete are tested",
    "evidence": "Only one it() block: it('should create record'). No tests for read, update, or delete."
  }
]
```

### Create test file `tests/sdl-workflow/test-pipeline-validate.sh`

Follow the TAP pattern. Define:
```bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PIPELINE="$PROJECT_ROOT/assets/scripts/pipeline.py"
FIXTURES="$PROJECT_ROOT/tests/fixtures/pipeline"
```

Add cleanup trap: `trap 'rm -f /tmp/test-validate-*.json /tmp/test-validate-*-err.txt' EXIT`

**Test 1: pipeline.py exists and is non-empty**
`[ -s "$PIPELINE" ]`

**Test 2: validate accepts valid sightings and outputs JSON array**
Run `uv run "$PIPELINE" validate < "$FIXTURES/valid-sightings.json" > /tmp/test-validate-out.json 2>/dev/null`. Check exit code is 0. Check output is valid JSON: `python3 -c "import json,sys; json.load(sys.stdin)" < /tmp/test-validate-out.json`.

**Test 3: validate assigns sequential S-NN IDs**
Run `python3 -c "import json,sys; d=json.load(sys.stdin); ids=[s['id'] for s in d]; assert ids==['S-01','S-02','S-03'], f'got {ids}'" < /tmp/test-validate-out.json 2>/dev/null`.

**Test 4: validate preserves all required fields**
Run `python3 -c "import json,sys; d=json.load(sys.stdin); s=d[0]; assert all(k in s for k in ['id','title','location','type','severity','mechanism','consequence','evidence'])" < /tmp/test-validate-out.json 2>/dev/null`.

**Test 5: validate rejects sightings with missing required fields**
Generate the invalid fixture inline via heredoc into a temp file:
```bash
cat > /tmp/test-validate-missing-input.json <<'EOJSON'
[
  {"id":"S-01","title":"Missing mechanism field entirely","location":{"file":"src/a.ts","start_line":1},"type":"behavioral","severity":"critical","consequence":"No mechanism field","evidence":"Lines 1-5"},
  {"id":"S-02","location":{"file":"src/b.ts","start_line":1},"type":"structural","severity":"minor","mechanism":"Title is empty","title":"","consequence":"Below 10 char min","evidence":"Lines 1-5"}
]
EOJSON
```
Run `uv run "$PIPELINE" validate < /tmp/test-validate-missing-input.json > /tmp/test-validate-missing.json 2>/tmp/test-validate-missing-err.txt`. Check 0 valid sightings in output. Check stderr is non-empty.

**Test 6: validate rejects sightings with invalid enum values**
Generate inline:
```bash
cat > /tmp/test-validate-enum-input.json <<'EOJSON'
[
  {"id":"S-01","title":"Invalid type enum value sighting","location":{"file":"src/c.ts","start_line":1},"type":"performance","severity":"critical","mechanism":"Invalid type not in enum","consequence":"Parser should reject this","evidence":"Lines 1-5"},
  {"id":"S-02","title":"Invalid severity enum value sighting","location":{"file":"src/d.ts","start_line":1},"type":"behavioral","severity":"high","mechanism":"Invalid severity not in enum","consequence":"Parser should reject this","evidence":"Lines 1-5"}
]
EOJSON
```
Run validate, check 0 valid, stderr non-empty.

**Test 7: validate rejects invalid type-severity matrix combinations**
Generate inline:
```bash
cat > /tmp/test-validate-matrix-input.json <<'EOJSON'
[
  {"id":"S-01","title":"Behavioral minor is invalid combination","location":{"file":"src/e.ts","start_line":1},"type":"behavioral","severity":"minor","mechanism":"behavioral+minor invalid per matrix","consequence":"Parser should reject this","evidence":"Lines 1-5"},
  {"id":"S-02","title":"Structural critical is invalid combination","location":{"file":"src/f.ts","start_line":1},"type":"structural","severity":"critical","mechanism":"structural+critical invalid per matrix","consequence":"Parser should reject this","evidence":"Lines 1-5"}
]
EOJSON
```
Run validate, check 0 valid, stderr non-empty.

**Test 8: validate fills defaults for optional fields**
Run `python3 -c "import json,sys; d=json.load(sys.stdin); s=d[1]; assert s.get('origin') in ['introduced','pre-existing','unknown',''], f'origin={s.get(\"origin\")}'" < /tmp/test-validate-out.json 2>/dev/null`. The second sighting in valid-sightings.json has no `origin` field — validate should fill the default.

**Test 9: validate outputs rejected sightings to stderr as complete JSON**
Run validate on the matrix input (from test 7), capture stderr. Check stderr contains the full rejected sighting data: `grep -q 'behavioral' /tmp/test-validate-matrix-err.txt && grep -q 'minor' /tmp/test-validate-matrix-err.txt`.

End with standard summary block.

## Files to create/modify

Create: `tests/sdl-workflow/test-pipeline-validate.sh` (make executable)
Create: `tests/fixtures/pipeline/valid-sightings.json`

## Test requirements

Executable, exits 0/1. Requires `uv` and `python3`. Invalid fixture data generated inline via heredocs. Temp files cleaned up via trap.

## Acceptance criteria

- 9 TAP tests: file existence, valid acceptance, ID assignment, field preservation, missing field rejection, invalid enum rejection, matrix rejection, default filling, stderr completeness
- 1 shared fixture file for valid sightings; invalid test data generated inline
- All tests validate `assets/scripts/pipeline.py validate` behavior via subprocess invocation

## Model

sonnet

## Wave

2
