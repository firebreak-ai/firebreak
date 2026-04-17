---
id: task-12
type: test
wave: 2
covers: [AC-10]
files_to_create:
  - tests/sdl-workflow/test-pipeline-run.sh
completion_gate: "bash tests/sdl-workflow/test-pipeline-run.sh exits 0"
---

## Objective

Create a TAP-style bash test that validates the `pipeline.py run` subcommand (full pipeline in single invocation) produces the same output as sequential subcommand invocations, and handles edge cases: empty input, all-filtered output, unknown preset, malformed JSON input, and unicode in field values.

## Context

The `run` subcommand executes validate, domain-filter, and severity-filter in a single invocation. It accepts `--preset` and `--min-severity` arguments. Optionally, `--output-markdown` appends markdown conversion. The subcommand must produce identical output to running the three subcommands sequentially via pipes.

Edge cases the spec requires testing:
- Empty input arrays: output `[]`
- All sightings filtered: output `[]`
- Unknown preset name: clear error to stderr, non-zero exit
- Malformed JSON input: clear error, non-zero exit
- Unicode in field values: passes through correctly

## Instructions

Create `tests/sdl-workflow/test-pipeline-run.sh` following the TAP pattern. Reuse the fixture at `tests/fixtures/pipeline/valid-sightings.json` (created by task-07) which has 3 sightings: behavioral+critical, structural+minor, test-integrity+major.

Define:
```bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PIPELINE="$PROJECT_ROOT/assets/scripts/pipeline.py"
FIXTURES="$PROJECT_ROOT/tests/fixtures/pipeline"
```

Cleanup trap: `trap 'rm -f /tmp/test-run-*.json /tmp/test-run-*.md /tmp/test-run-*-err.txt' EXIT`

**Test 1: run --preset behavioral-only produces same result as sequential pipeline**
Run sequential: `uv run "$PIPELINE" validate < "$FIXTURES/valid-sightings.json" 2>/dev/null | uv run "$PIPELINE" domain-filter --preset behavioral-only 2>/dev/null | uv run "$PIPELINE" severity-filter --min-severity minor 2>/dev/null > /tmp/test-run-sequential.json`. Run combined: `uv run "$PIPELINE" run --preset behavioral-only --min-severity minor < "$FIXTURES/valid-sightings.json" > /tmp/test-run-combined.json 2>/dev/null`. Compare: `python3 -c "import json,sys; a=json.load(open('/tmp/test-run-sequential.json')); b=json.load(open('/tmp/test-run-combined.json')); assert a==b, f'sequential={a} combined={b}'"`.

**Test 2: run --preset behavioral-only filters to behavioral sightings only**
Check combined output contains exactly 1 sighting with type behavioral: `python3 -c "import json,sys; d=json.load(sys.stdin); assert len(d)==1 and d[0]['type']=='behavioral'" < /tmp/test-run-combined.json`.

**Test 3: run --preset full --min-severity minor keeps all non-info sightings**
Run `uv run "$PIPELINE" run --preset full --min-severity minor < "$FIXTURES/valid-sightings.json" > /tmp/test-run-full.json 2>/dev/null`. Check output has 3 sightings (none are info-level in the fixture).

**Test 4: run --output-markdown produces markdown instead of JSON**
Run `uv run "$PIPELINE" run --preset behavioral-only --min-severity minor --output-markdown < "$FIXTURES/valid-sightings.json" > /tmp/test-run-md.md 2>/dev/null`. Check output contains markdown headers: `grep -q '### ' /tmp/test-run-md.md`.

**Test 5: run on empty array outputs empty JSON array**
Run `echo '[]' | uv run "$PIPELINE" run --preset behavioral-only --min-severity minor > /tmp/test-run-empty.json 2>/dev/null`. Check: `python3 -c "import json,sys; assert json.load(sys.stdin)==[]" < /tmp/test-run-empty.json`.

**Test 6: run where all sightings are filtered outputs empty array**
Run `uv run "$PIPELINE" run --preset structural --min-severity major < "$FIXTURES/valid-sightings.json" > /tmp/test-run-allfiltered.json 2>/dev/null`. The fixture has structural+minor which gets dropped by `--min-severity major`. Check output is `[]` or empty array.

**Test 7: run with unknown preset exits non-zero**
Run `uv run "$PIPELINE" run --preset nonexistent < "$FIXTURES/valid-sightings.json" > /dev/null 2>/dev/null`. Check exit code is non-zero.

**Test 8: run with malformed JSON input exits non-zero**
Run `echo 'not json at all' | uv run "$PIPELINE" run --preset behavioral-only > /dev/null 2>/tmp/test-run-malformed-err.txt`. Check exit code is non-zero. Check stderr is non-empty.

**Test 9: run preserves unicode in field values**
Create a temp file with a sighting containing unicode in the title:
```bash
cat > /tmp/test-run-unicode-input.json <<'EOJSON'
[{
  "id": "S-01",
  "title": "Mishandled encoding in path \u2014 drops non-ASCII characters",
  "location": {"file": "src/encoder.ts", "start_line": 10},
  "type": "behavioral",
  "severity": "critical",
  "mechanism": "encodeURI() strips characters outside Basic Latin \u2014 loses CJK input",
  "consequence": "User-submitted names with non-Latin characters are silently truncated",
  "evidence": "Line 10: encodeURI(input) with \u00e9\u00e8\u00ea test values"
}]
EOJSON
```
Run `uv run "$PIPELINE" run --preset behavioral-only --min-severity minor < /tmp/test-run-unicode-input.json > /tmp/test-run-unicode-out.json 2>/dev/null`. Check output is valid JSON with 1 sighting: `python3 -c "import json,sys; d=json.load(sys.stdin); assert len(d)==1" < /tmp/test-run-unicode-out.json`.

End with standard summary block.

## Files to create/modify

Create: `tests/sdl-workflow/test-pipeline-run.sh` (make executable)

## Test requirements

Executable, exits 0/1. Requires `uv` and `python3`. Depends on fixture from task-07 (`tests/fixtures/pipeline/valid-sightings.json`).

## Acceptance criteria

- 9 TAP tests: sequential/combined equivalence, behavioral filtering, full preset, markdown output, empty input, all-filtered, unknown preset, malformed JSON, unicode preservation
- Tests validate `pipeline.py run` as the combined pipeline entry point
- Edge cases cover all items from the spec's testing strategy

## Model

sonnet

## Wave

2
