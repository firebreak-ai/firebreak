---
id: task-10
type: test
wave: 2
covers: [AC-10]
files_to_create:
  - tests/sdl-workflow/test-pipeline-severity-filter.sh
  - tests/fixtures/pipeline/mixed-severities.json
completion_gate: "bash tests/sdl-workflow/test-pipeline-severity-filter.sh exits 0"
---

## Objective

Create a TAP-style bash test that validates the `pipeline.py severity-filter` subcommand correctly filters sightings by severity threshold, logs dropped sightings to stderr, and handles edge cases.

## Context

The `severity-filter` subcommand reads a JSON array from stdin and a `--min-severity` argument. Severity ordering is: info < minor < major < critical. The filter drops sightings below the minimum threshold. For example, `--min-severity minor` drops info-level sightings. `--min-severity major` drops info and minor. `--min-severity critical` drops everything below critical.

## Instructions

### Create fixture file `tests/fixtures/pipeline/mixed-severities.json`

Array of 4 sightings, one of each severity, all with valid type-severity combinations:
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
    "title": "Race condition in concurrent request handler path",
    "location": {"file": "src/queue.ts", "start_line": 88},
    "type": "behavioral",
    "severity": "major",
    "mechanism": "Shared mutable counter incremented without lock in concurrent handler",
    "consequence": "Under concurrent requests counter skips values or double-counts",
    "evidence": "Line 88: requestCount++ without mutex"
  },
  {
    "id": "S-03",
    "title": "Duplicated validation logic across three handlers",
    "location": {"file": "src/validate.ts", "start_line": 10},
    "type": "structural",
    "severity": "minor",
    "mechanism": "Three handlers each implement the same email validation regex inline",
    "consequence": "Updating validation requires changing three files with no shared reference",
    "evidence": "handler-a.ts:15, handler-b.ts:22, handler-c.ts:31"
  },
  {
    "id": "S-04",
    "title": "Unused error code constant defined but never referenced",
    "location": {"file": "src/constants.ts", "start_line": 55},
    "type": "structural",
    "severity": "info",
    "mechanism": "ERROR_TIMEOUT constant defined at module scope but no import references it",
    "consequence": "Dead code adds noise to the module without any behavioral impact",
    "evidence": "grep -r ERROR_TIMEOUT returns only the definition line"
  }
]
```

### Create test file `tests/sdl-workflow/test-pipeline-severity-filter.sh`

Follow the TAP pattern. Define:
```bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PIPELINE="$PROJECT_ROOT/assets/scripts/pipeline.py"
FIXTURES="$PROJECT_ROOT/tests/fixtures/pipeline"
```

Cleanup trap: `trap 'rm -f /tmp/test-severity-*.json /tmp/test-severity-*-err.txt' EXIT`

**Test 1: --min-severity minor drops info, keeps minor+major+critical**
Run `uv run "$PIPELINE" severity-filter --min-severity minor < "$FIXTURES/mixed-severities.json" > /tmp/test-severity-minor.json 2>/dev/null`. Check output has 3 sightings: `python3 -c "import json,sys; d=json.load(sys.stdin); assert len(d)==3, f'expected 3, got {len(d)}'" < /tmp/test-severity-minor.json`.

**Test 2: --min-severity major drops info+minor, keeps major+critical**
Run with `--min-severity major`. Check output has 2 sightings.

**Test 3: --min-severity critical drops everything below critical**
Run with `--min-severity critical`. Check output has 1 sighting and its severity is `critical`.

**Test 4: --min-severity info keeps all sightings**
Run with `--min-severity info`. Check output has 4 sightings.

**Test 5: severity-filter logs dropped sightings to stderr**
Run `uv run "$PIPELINE" severity-filter --min-severity major < "$FIXTURES/mixed-severities.json" > /dev/null 2>/tmp/test-severity-stderr.txt`. Check stderr is non-empty.

**Test 6: severity-filter on empty array outputs empty array**
Run `echo '[]' | uv run "$PIPELINE" severity-filter --min-severity minor > /tmp/test-severity-empty.json 2>/dev/null`. Check output is `[]`.

**Test 7: severity-filter preserves sighting field content**
Run `uv run "$PIPELINE" severity-filter --min-severity critical < "$FIXTURES/mixed-severities.json" > /tmp/test-severity-fields.json 2>/dev/null`. Verify the surviving sighting has all fields: `python3 -c "import json,sys; d=json.load(sys.stdin); s=d[0]; assert s['title']=='forEach(async) drops return value silently' and s['type']=='behavioral'" < /tmp/test-severity-fields.json`.

End with standard summary block.

## Files to create/modify

Create: `tests/sdl-workflow/test-pipeline-severity-filter.sh` (make executable)
Create: `tests/fixtures/pipeline/mixed-severities.json`

## Test requirements

Executable, exits 0/1. Requires `uv` and `python3`.

## Acceptance criteria

- 7 TAP tests: 4 threshold levels (info/minor/major/critical), stderr logging, empty input, field preservation
- Fixture file with 4 sightings at each severity level with valid type-severity combinations
- Tests validate `pipeline.py severity-filter` via subprocess invocation

## Model

sonnet

## Wave

2
