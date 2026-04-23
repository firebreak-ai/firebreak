---
id: task-11
type: test
wave: 2
covers: [AC-10]
files_to_create:
  - tests/sdl-workflow/test-pipeline-to-markdown.sh
  - tests/fixtures/pipeline/finding-for-markdown.json
completion_gate: "bash tests/sdl-workflow/test-pipeline-to-markdown.sh exits 0"
---

## Objective

Create a TAP-style bash test that validates the `pipeline.py to-markdown` subcommand correctly converts sightings (S-NN format) and findings (F-NN format with verification evidence and reclassification notes) to well-formed markdown, and excludes rejected-as-nit findings.

## Context

The `to-markdown` subcommand converts a JSON array to human-readable markdown for review reports. It handles two cases:
- **Sightings** (pre-Challenger): Rendered with S-NN ID, no verification section
- **Findings** (post-Challenger): Rendered with F-NN ID, verification evidence, and reclassification note when `reclassified_from` is non-empty

Expected markdown format for a finding:
```markdown
### F-01: forEach(async) drops return value — promises fire-and-forget

- **Location**: `src/handlers/workflow.ts:42-55`
- **Type**: behavioral | **Severity**: critical | **Origin**: introduced
- **Detection source**: intent | **Pattern**: `async-in-sync-iterator`

**Mechanism**: ...
**Consequence**: ...
**Evidence**: ...
**Verification**: ...
**Remediation**: ...
```

## Instructions

### Create fixture file `tests/fixtures/pipeline/finding-for-markdown.json`

Array with one verified finding (with reclassification) and one rejected-as-nit finding:
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
    "evidence": "Lines 42-48: bookingHandler.forEach(async (booking) => ...)",
    "remediation": "Replace forEach(async) with for...of loop",
    "status": "verified",
    "verification_evidence": "Traced caller chain from router.ts:18 to handler.ts:42. Caller awaits void.",
    "reclassified_from": {"type": "fragile", "severity": "minor"},
    "adjacent_observations": ["Adjacent to S-01: sendReminder also lacks error boundary"]
  },
  {
    "id": "S-02",
    "title": "Style nit that was rejected",
    "location": {"file": "src/utils.ts", "start_line": 5},
    "type": "structural",
    "severity": "minor",
    "mechanism": "Variable name uses abbreviation instead of full word",
    "consequence": "Slightly less readable but no behavioral impact",
    "evidence": "Line 5: const req = request",
    "status": "rejected-as-nit",
    "rejection_reason": "Technically accurate but functionally irrelevant naming preference"
  }
]
```

### Create test file `tests/sdl-workflow/test-pipeline-to-markdown.sh`

Follow the TAP pattern. Define:
```bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PIPELINE="$PROJECT_ROOT/assets/scripts/pipeline.py"
FIXTURES="$PROJECT_ROOT/tests/fixtures/pipeline"
```

Cleanup trap: `trap 'rm -f /tmp/test-md-*.md /tmp/test-md-sighting-input.json' EXIT`

**Test 1: to-markdown converts sighting to markdown with S-NN header**
Generate a sighting fixture inline via heredoc:
```bash
cat > /tmp/test-md-sighting-input.json <<'EOJSON'
[{"id":"S-01","title":"forEach(async) drops return value silently","location":{"file":"src/handler.ts","start_line":42,"end_line":55},"type":"behavioral","severity":"critical","origin":"introduced","detection_source":"intent","pattern":"async-in-sync-iterator","mechanism":"forEach(async callback) discards the Promise returned by each iteration","consequence":"Callbacks execute concurrently with no error propagation to the caller","evidence":"Lines 42-48: bookingHandler.forEach(async (booking) => ...)","remediation":"Replace forEach(async) with for...of loop"}]
EOJSON
```
Run `uv run "$PIPELINE" to-markdown < /tmp/test-md-sighting-input.json > /tmp/test-md-sighting.md 2>/dev/null`. Check output contains `### S-01`: `grep -q '### S-01' /tmp/test-md-sighting.md`.

**Test 2: to-markdown sighting output contains mechanism field**
`grep -q 'Mechanism' /tmp/test-md-sighting.md`

**Test 3: to-markdown sighting output contains consequence field**
`grep -q 'Consequence' /tmp/test-md-sighting.md`

**Test 4: to-markdown sighting output contains location with file and lines**
`grep -q 'src/handler.ts' /tmp/test-md-sighting.md`

**Test 5: to-markdown sighting output contains type and severity**
`grep -q 'behavioral' /tmp/test-md-sighting.md && grep -q 'critical' /tmp/test-md-sighting.md`

**Test 6: to-markdown converts finding to markdown with F-NN header**
Run `uv run "$PIPELINE" to-markdown < "$FIXTURES/finding-for-markdown.json" > /tmp/test-md-finding.md 2>/dev/null`. Check output contains `### F-01`: `grep -q '### F-01' /tmp/test-md-finding.md`.

**Test 7: to-markdown finding output contains verification evidence**
`grep -q 'Verification' /tmp/test-md-finding.md && grep -q 'Traced caller chain' /tmp/test-md-finding.md`

**Test 8: to-markdown finding output contains reclassification note**
`grep -qiE 'reclassif|originally' /tmp/test-md-finding.md`

**Test 9: to-markdown excludes rejected-as-nit findings from output**
The finding-for-markdown.json fixture contains a second entry with status `rejected-as-nit`. Check the markdown output does NOT contain `S-02` or the nit title: `! grep -q 'Style nit' /tmp/test-md-finding.md`.

**Test 10: to-markdown on empty array produces empty or minimal output**
Run `echo '[]' | uv run "$PIPELINE" to-markdown > /tmp/test-md-empty.md 2>/dev/null`. Check exit code is 0. Check output file is empty or contains no finding headers: `! grep -q '### ' /tmp/test-md-empty.md`.

End with standard summary block.

## Files to create/modify

Create: `tests/sdl-workflow/test-pipeline-to-markdown.sh` (make executable)
Create: `tests/fixtures/pipeline/finding-for-markdown.json`

## Test requirements

Executable, exits 0/1. Requires `uv`. Sighting test data generated inline via heredoc.

## Acceptance criteria

- 10 TAP tests: sighting S-NN header, 4 field checks, finding F-NN header, verification evidence, reclassification note, nit exclusion, empty input
- 1 fixture file for findings (with reclassification and nit); sighting data generated inline
- Tests validate `pipeline.py to-markdown` output format via grep

## Model

sonnet

## Wave

2
