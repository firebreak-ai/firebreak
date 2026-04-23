---
id: task-14
type: test
wave: 2
covers: [AC-01, AC-06, AC-09, AC-10]
files_to_create:
  - tests/sdl-workflow/test-pipeline-integration.sh
  - tests/fixtures/pipeline/integration-input.json
completion_gate: "bash tests/sdl-workflow/test-pipeline-integration.sh exits 0"
---

## Objective

Create a deterministic fixture-driven integration test that passes a canned JSON sighting array through the full pipeline (validate, domain filter, severity filter, markdown conversion), verifying correct sightings survive, counts match, type-severity matrix rejects invalid combinations, and markdown output is well-formed. No LLM involvement.

## Context

This test exercises the end-to-end pipeline path with a fixture containing a mix of valid sightings, invalid matrix combinations, and various types/severities. It validates that the pipeline correctly chains validate (rejecting invalid sightings), domain-filter (keeping only preset-allowed types), severity-filter (dropping below threshold), and to-markdown (producing well-formed output).

## Instructions

### Create fixture file `tests/fixtures/pipeline/integration-input.json`

Array of 6 raw sightings with varied conditions:
```json
[
  {
    "id": "raw-1",
    "title": "forEach(async) drops return value in event handler",
    "location": {"file": "src/handler.ts", "start_line": 42, "end_line": 55},
    "type": "behavioral",
    "severity": "critical",
    "origin": "introduced",
    "detection_source": "intent",
    "pattern": "async-in-sync-iterator",
    "mechanism": "forEach(async callback) discards the Promise returned by each iteration",
    "consequence": "Callbacks execute concurrently with no error propagation to the caller",
    "evidence": "Lines 42-48: bookingHandler.forEach(async (booking) => ...)",
    "remediation": "Replace forEach(async) with for...of loop"
  },
  {
    "id": "raw-2",
    "title": "Race condition when two requests hit shared counter",
    "location": {"file": "src/counter.ts", "start_line": 10},
    "type": "behavioral",
    "severity": "major",
    "mechanism": "Shared mutable counter incremented without lock in concurrent path",
    "consequence": "Under concurrent requests the counter skips values or double-counts",
    "evidence": "Line 10: requestCount++ without mutex"
  },
  {
    "id": "raw-3",
    "title": "Duplicated email validation regex across three handlers",
    "location": {"file": "src/validate.ts", "start_line": 10},
    "type": "structural",
    "severity": "minor",
    "mechanism": "Three handlers each implement the same email validation regex inline",
    "consequence": "Updating validation requires changing three files with no shared reference",
    "evidence": "handler-a.ts:15, handler-b.ts:22, handler-c.ts:31"
  },
  {
    "id": "raw-4",
    "title": "Unused error code constant never referenced anywhere",
    "location": {"file": "src/constants.ts", "start_line": 55},
    "type": "structural",
    "severity": "info",
    "mechanism": "ERROR_TIMEOUT constant defined at module scope but no import references it",
    "consequence": "Dead code adds noise to the module without any behavioral impact",
    "evidence": "grep -r ERROR_TIMEOUT returns only the definition line"
  },
  {
    "id": "raw-5",
    "title": "INVALID: behavioral with minor severity should be rejected",
    "location": {"file": "src/invalid.ts", "start_line": 1},
    "type": "behavioral",
    "severity": "minor",
    "mechanism": "This sighting has an invalid type-severity combination for testing",
    "consequence": "The pipeline should reject this before domain filtering occurs",
    "evidence": "Intentionally invalid fixture entry"
  },
  {
    "id": "raw-6",
    "title": "Hardcoded page size will break when API changes",
    "location": {"file": "src/paginator.ts", "start_line": 22},
    "type": "fragile",
    "severity": "major",
    "mechanism": "Page size hardcoded to 10 matches current API default without contract",
    "consequence": "When API changes page size the paginator silently returns partial results",
    "evidence": "Line 22: const PAGE_SIZE = 10"
  }
]
```

### Create test file `tests/sdl-workflow/test-pipeline-integration.sh`

Follow the TAP pattern. Cleanup trap for temp files.

**Test 1: Full pipeline with behavioral-only preset produces expected count**
Run `uv run "$PIPELINE" run --preset behavioral-only --min-severity minor < "$FIXTURES/integration-input.json" > /tmp/test-integ-behavioral.json 2>/tmp/test-integ-behavioral-err.txt`. Expected: raw-1 (behavioral+critical) and raw-2 (behavioral+major) survive. raw-3 (structural) dropped by domain filter. raw-4 (structural+info) dropped. raw-5 (behavioral+minor) rejected by matrix. raw-6 (fragile) dropped by domain filter. Result: 2 sightings. Check: `python3 -c "import json,sys; d=json.load(sys.stdin); assert len(d)==2, f'expected 2, got {len(d)}'" < /tmp/test-integ-behavioral.json`.

**Test 2: Surviving sightings have sequential S-NN IDs**
Check: `python3 -c "import json,sys; d=json.load(sys.stdin); ids=[s['id'] for s in d]; assert ids==['S-01','S-02'], f'got {ids}'" < /tmp/test-integ-behavioral.json`.

**Test 3: Invalid matrix combination was rejected (stderr mentions it)**
Check: `grep -qi 'behavioral.*minor\|reject\|invalid' /tmp/test-integ-behavioral-err.txt`.

**Test 4: Full pipeline with full preset and minor threshold produces expected count**
Run `uv run "$PIPELINE" run --preset full --min-severity minor < "$FIXTURES/integration-input.json" > /tmp/test-integ-full.json 2>/dev/null`. Expected: raw-1, raw-2, raw-3, raw-6 survive (4 sightings). raw-4 dropped by severity (info). raw-5 rejected by matrix. Check: `python3 -c "import json,sys; d=json.load(sys.stdin); assert len(d)==4, f'expected 4, got {len(d)}'" < /tmp/test-integ-full.json`.

**Test 5: Full pipeline with full preset and info threshold keeps info sightings**
Run `uv run "$PIPELINE" run --preset full --min-severity info < "$FIXTURES/integration-input.json" > /tmp/test-integ-info.json 2>/dev/null`. Expected: raw-1, raw-2, raw-3, raw-4, raw-6 survive (5 sightings). raw-5 rejected by matrix. Check: `python3 -c "import json,sys; d=json.load(sys.stdin); assert len(d)==5, f'expected 5, got {len(d)}'" < /tmp/test-integ-info.json`.

**Test 6: Pipeline output converted to markdown is well-formed**
Run `uv run "$PIPELINE" run --preset behavioral-only --min-severity minor --output-markdown < "$FIXTURES/integration-input.json" > /tmp/test-integ-md.md 2>/dev/null`. Check markdown contains expected headers: `grep -c '### S-' /tmp/test-integ-md.md` returns 2. Check markdown contains mechanism: `grep -q 'Mechanism' /tmp/test-integ-md.md`.

**Test 7: Pipeline stderr reports rejection count or warning when >30% rejected**
The fixture has 1 invalid out of 6 (16.7%), which is below the 30% threshold. Verify stderr does NOT contain a warning about prompt drift: `! grep -qi 'prompt drift\|>30%\|warning.*rate' /tmp/test-integ-behavioral-err.txt` (this is a negative test — no warning expected).

End with standard summary block.

## Files to create/modify

Create: `tests/sdl-workflow/test-pipeline-integration.sh` (make executable)
Create: `tests/fixtures/pipeline/integration-input.json`

## Test requirements

Executable, exits 0/1. Requires `uv` and `python3`. Deterministic — no LLM involvement.

## Acceptance criteria

- 7 TAP tests: behavioral-only count, ID assignment, matrix rejection in stderr, full preset count, info threshold count, markdown well-formedness, no false warning
- Fixture with 6 sightings covering valid types, matrix violation, info severity, and multiple presets
- End-to-end validation of the complete pipeline without LLM calls

## Model

sonnet

## Wave

2
