---
id: task-16
type: test
wave: 3
covers: [AC-13, AC-14]
files_to_create:
  - tests/sdl-workflow/test-benchmark-infrastructure.sh
completion_gate: "bash tests/sdl-workflow/test-benchmark-infrastructure.sh exits 0"
---

## Objective

Create a TAP-style bash test that validates the Martian benchmark infrastructure files are present and runnable from the project directory, including the benchmark runner, manifest, diffs directory, inject script, and judge script.

## Context

The benchmark infrastructure is being cherry-picked from the `feature/0.4.0-detector-decomposition` branch into the project. Required files:
- `ai-docs/detection-accuracy/martian-benchmark/run_reviews.sh` — headless benchmark runner
- `ai-docs/detection-accuracy/martian-benchmark/inject_results.py` — JSON-consuming inject script
- `ai-docs/detection-accuracy/martian-benchmark/judge_anthropic.py` — LLM judge
- `ai-docs/detection-accuracy/martian-benchmark/manifest.json` — 50-PR corpus
- `ai-docs/detection-accuracy/martian-benchmark/diffs/` — PR diffs directory
- `ai-docs/detection-accuracy/martian-benchmark/benchmark-prompt.md` — headless mode overrides

Per-run metadata fields to capture: `run_date`, `pipeline_version`, `pr_id`, `finding_id`, `detector_type`, `detector_severity`, `challenger_type`, `challenger_severity`, `reclassified`, `origin`, `judge_verdict`, `matched_golden_index`.

## Instructions

Create `tests/sdl-workflow/test-benchmark-infrastructure.sh` following the TAP pattern.

Define:
```bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BENCHMARK_DIR="$PROJECT_ROOT/ai-docs/detection-accuracy/martian-benchmark"
```

**Test 1: Benchmark directory exists**
`[ -d "$BENCHMARK_DIR" ]`

**Test 2: run_reviews.sh exists and is executable**
`[ -x "$BENCHMARK_DIR/run_reviews.sh" ]`

**Test 3: inject_results.py exists and is non-empty**
`[ -s "$BENCHMARK_DIR/inject_results.py" ]`

**Test 4: judge_anthropic.py exists and is non-empty**
`[ -s "$BENCHMARK_DIR/judge_anthropic.py" ]`

**Test 5: manifest.json exists and is valid JSON**
`[ -s "$BENCHMARK_DIR/manifest.json" ] && python3 -c "import json,sys; json.load(sys.stdin)" < "$BENCHMARK_DIR/manifest.json" 2>/dev/null`

**Test 6: manifest.json contains 50 PR entries**
`python3 -c "import json,sys; d=json.load(sys.stdin); assert len(d)==50, f'expected 50, got {len(d)}'" < "$BENCHMARK_DIR/manifest.json" 2>/dev/null`

**Test 7: diffs directory exists and contains diff files**
`[ -d "$BENCHMARK_DIR/diffs" ] && [ "$(ls "$BENCHMARK_DIR/diffs/" 2>/dev/null | wc -l)" -gt 0 ]`

**Test 8: benchmark-prompt.md exists and is non-empty**
`[ -s "$BENCHMARK_DIR/benchmark-prompt.md" ]`

**Test 9: results directory exists or can be created**
`[ -d "$BENCHMARK_DIR/results" ] || mkdir -p "$BENCHMARK_DIR/results"`. Then: `[ -d "$BENCHMARK_DIR/results" ]`.

**Test 10: inject_results.py does not contain old regex-based markdown parsing**
Confirm the rewritten script has no regex patterns for severity or location extraction: `! grep -qE 're\.compile.*severity|re\.compile.*location|_is_metadata_line|parse_findings_flat' "$BENCHMARK_DIR/inject_results.py"`.

**Test 11: inject_results.py references JSON consumption**
`grep -qi 'json' "$BENCHMARK_DIR/inject_results.py"`

**Test 12: run_reviews.sh references pipeline.py or uv run**
`grep -qE 'pipeline\.py|uv run' "$BENCHMARK_DIR/run_reviews.sh"`

End with standard summary block.

## Files to create/modify

Create: `tests/sdl-workflow/test-benchmark-infrastructure.sh` (make executable)

## Test requirements

Executable, exits 0/1. Uses `python3` for JSON validation. Does not execute the benchmark (no LLM calls).

## Acceptance criteria

- 12 TAP tests: directory existence, 5 required files present, manifest count, diffs populated, results directory, inject script JSON consumption, no regex parsing, runner references pipeline
- Tests validate benchmark infrastructure presence without running the benchmark
- Confirms cherry-pick from decomposition branch was successful

## Model

sonnet

## Wave

3
