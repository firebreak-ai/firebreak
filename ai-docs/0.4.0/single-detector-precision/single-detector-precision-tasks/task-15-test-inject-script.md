---
id: task-15
type: test
wave: 3
covers: [AC-12]
files_to_create:
  - tests/sdl-workflow/test-inject-script.sh
  - tests/fixtures/pipeline/verified-findings.json
completion_gate: "bash tests/sdl-workflow/test-inject-script.sh exits 0"
---

## Objective

Create a TAP-style bash test with a fixture that validates the rewritten `inject_results.py` reads JSON findings directly, maps unified schema fields to benchmark format, supports `--min-severity` filtering, and passes `type`, `origin`, and `reclassified_from` through to output.

## Context

`ai-docs/detection-accuracy/martian-benchmark/inject_results.py` is being rewritten to consume JSON findings instead of parsing markdown with regex. The new script:
- Reads JSON findings (verified findings with `status: verified`) from a file
- Maps: `location.file` to `path`, `location.start_line` to `line`, `mechanism` + `consequence` to `body`, `severity` to `severity`
- Passes through: `type`, `origin`, `reclassified_from` for post-hoc analysis
- Supports `--min-severity` for severity filtering
- Supports `--tool-name` for labeling the tool in output
- Supports `--dry-run` for preview without writing
- Runs via `uv run`
- No markdown parsing, no regex-based field extraction

## Instructions

### Create fixture file `tests/fixtures/pipeline/verified-findings.json`

Array of 3 verified findings with varied fields:
```json
[
  {
    "id": "S-01",
    "finding_id": "F-01",
    "title": "forEach(async) drops return value silently",
    "location": {"file": "src/handler.ts", "start_line": 42, "end_line": 55},
    "type": "behavioral",
    "severity": "critical",
    "origin": "introduced",
    "detection_source": "intent",
    "pattern": "async-in-sync-iterator",
    "mechanism": "forEach(async callback) discards the Promise returned by each iteration",
    "consequence": "Callbacks execute concurrently with no error propagation to the caller",
    "evidence": "Lines 42-48",
    "remediation": "Replace forEach(async) with for...of loop",
    "status": "verified",
    "verification_evidence": "Traced caller chain from router.ts:18 to handler.ts:42",
    "reclassified_from": {},
    "adjacent_observations": []
  },
  {
    "id": "S-02",
    "finding_id": "F-02",
    "title": "Race condition in shared counter without lock",
    "location": {"file": "src/counter.ts", "start_line": 10},
    "type": "behavioral",
    "severity": "major",
    "origin": "introduced",
    "mechanism": "Shared mutable counter incremented without lock in concurrent path",
    "consequence": "Under concurrent requests counter skips values or double-counts",
    "evidence": "Line 10: requestCount++",
    "status": "verified",
    "verification_evidence": "Confirmed two request handlers call increment without synchronization",
    "reclassified_from": {"type": "fragile", "severity": "minor"},
    "adjacent_observations": []
  },
  {
    "id": "S-03",
    "finding_id": "F-03",
    "title": "Duplicated validation logic across handlers",
    "location": {"file": "src/validate.ts", "start_line": 10},
    "type": "structural",
    "severity": "minor",
    "origin": "pre-existing",
    "mechanism": "Three handlers each implement the same email validation regex inline",
    "consequence": "Updating validation requires changing three files with no shared reference",
    "evidence": "handler-a.ts:15, handler-b.ts:22, handler-c.ts:31",
    "status": "verified",
    "verification_evidence": "Confirmed identical regex in all three files",
    "reclassified_from": {},
    "adjacent_observations": []
  }
]
```

### Create test file `tests/sdl-workflow/test-inject-script.sh`

Follow the TAP pattern. Define:
```bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
INJECT="$PROJECT_ROOT/ai-docs/detection-accuracy/martian-benchmark/inject_results.py"
FIXTURES="$PROJECT_ROOT/tests/fixtures/pipeline"
```

Cleanup trap: `trap 'rm -f /tmp/test-inject-*.json' EXIT`

**Test 1: inject_results.py exists and is non-empty**
`[ -s "$INJECT" ]`

**Test 2: inject script maps location.file to path field**
Run `uv run "$INJECT" --dry-run --input "$FIXTURES/verified-findings.json" --tool-name firebreak > /tmp/test-inject-out.json 2>/dev/null` (or the appropriate CLI invocation pattern — check the script's interface). Parse output and verify the first finding has `path` field containing `src/handler.ts`: `python3 -c "import json,sys; d=json.load(sys.stdin); assert d[0]['path']=='src/handler.ts'" < /tmp/test-inject-out.json`.

**Test 3: inject script maps location.start_line to line field**
`python3 -c "import json,sys; d=json.load(sys.stdin); assert d[0]['line']==42" < /tmp/test-inject-out.json`

**Test 4: inject script maps mechanism+consequence to body field**
`python3 -c "import json,sys; d=json.load(sys.stdin); b=d[0]['body']; assert 'forEach' in b and 'Callbacks execute' in b" < /tmp/test-inject-out.json`

**Test 5: inject script maps severity field directly**
`python3 -c "import json,sys; d=json.load(sys.stdin); assert d[0]['severity']=='critical'" < /tmp/test-inject-out.json`

**Test 6: inject script passes type field through**
`python3 -c "import json,sys; d=json.load(sys.stdin); assert d[0]['type']=='behavioral'" < /tmp/test-inject-out.json`

**Test 7: inject script passes origin field through**
`python3 -c "import json,sys; d=json.load(sys.stdin); assert d[0].get('origin')=='introduced'" < /tmp/test-inject-out.json`

**Test 8: inject script passes reclassified_from through**
Check the second finding (which has a non-empty reclassified_from): `python3 -c "import json,sys; d=json.load(sys.stdin); rf=d[1].get('reclassified_from',{}); assert rf.get('type')=='fragile'" < /tmp/test-inject-out.json`.

**Test 9: inject script --min-severity filters output**
Run `uv run "$INJECT" --dry-run --input "$FIXTURES/verified-findings.json" --tool-name firebreak --min-severity major > /tmp/test-inject-filtered.json 2>/dev/null`. Check output has 2 findings (critical and major, not minor): `python3 -c "import json,sys; d=json.load(sys.stdin); assert len(d)==2, f'expected 2, got {len(d)}'" < /tmp/test-inject-filtered.json`.

**Test 10: inject script does not use regex-based markdown parsing**
Grep the script for absence of the old regex patterns: `! grep -qE 're\.compile|re\.search|re\.findall|_is_metadata_line|parse_findings_flat' "$INJECT"`.

End with standard summary block.

## Files to create/modify

Create: `tests/sdl-workflow/test-inject-script.sh` (make executable)
Create: `tests/fixtures/pipeline/verified-findings.json`

## Test requirements

Executable, exits 0/1. Requires `uv` and `python3`. The exact CLI interface for `inject_results.py` may need adjustment during implementation — the `--dry-run` flag outputs to stdout instead of writing to a benchmark data file.

## Acceptance criteria

- 10 TAP tests: file existence, field mapping (path, line, body, severity), passthrough fields (type, origin, reclassified_from), severity filtering, no regex parsing
- Fixture file with 3 verified findings including one with reclassification
- Tests validate the rewritten inject script consumes JSON directly

## Model

sonnet

## Wave

3
