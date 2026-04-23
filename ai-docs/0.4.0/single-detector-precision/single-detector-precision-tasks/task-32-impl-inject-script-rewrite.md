---
id: task-32
type: implementation
wave: 4
covers: [AC-12]
files_to_create:
  - ai-docs/detection-accuracy/martian-benchmark/inject_results.py
test_tasks: [task-15]
completion_gate: "bash tests/sdl-workflow/test-inject-script.sh exits 0"
---

## Objective

Rewrite `inject_results.py` to consume JSON findings directly instead of parsing markdown with regex. The script maps unified JSON schema fields to the benchmark format, supports severity filtering, and passes type/origin/reclassified_from through for analysis.

## Context

The current `inject_results.py` on the decomposition branch uses 11 regex patterns for severity extraction, 6 for location, and heuristic body parsing from markdown. This produced 104 "unknown" type findings across 50 PRs. The rewrite eliminates all regex parsing by consuming the JSON findings produced by `pipeline.py`.

The existing script's interface includes `--tool-name` for labeling, `--dry-run` for preview, and writes to `benchmark_data.json`. The rewrite preserves these interfaces and adds `--input` for specifying the JSON findings file and `--min-severity` for filtering.

The existing `match_pr_to_benchmark` function (matching PRs to benchmark entries via the manifest) and the output format into `benchmark_data.json` are preserved.

## Instructions

Create `ai-docs/detection-accuracy/martian-benchmark/inject_results.py` as a new file (replacing whatever was cherry-picked in task-31, if anything). The script runs via `uv run`. Standard library only (`json`, `sys`, `argparse`, `pathlib`).

### Constants

```python
SEVERITY_ORDER = {"info": 0, "minor": 1, "major": 2, "critical": 3}
MANIFEST_PATH = pathlib.Path(__file__).parent / "manifest.json"
BENCHMARK_DATA = pathlib.Path("/tmp/code-review-benchmark/offline/results/benchmark_data.json")
```

### Core function: `convert_finding(finding)`

Map a single JSON finding to the benchmark format:

```python
def convert_finding(finding):
    mechanism = finding.get("mechanism", "")
    consequence = finding.get("consequence", "")
    body = f"{mechanism} {consequence}".strip()

    return {
        "path": finding["location"]["file"],
        "line": finding["location"].get("start_line", 0),
        "body": body,
        "severity": finding.get("severity", "unknown"),
        "type": finding.get("type", "unknown"),
        "origin": finding.get("origin", "unknown"),
        "reclassified_from": finding.get("reclassified_from", {}),
    }
```

### Core function: `filter_by_severity(findings, min_severity)`

Filter findings by minimum severity threshold using `SEVERITY_ORDER`:

```python
def filter_by_severity(findings, min_severity):
    threshold = SEVERITY_ORDER.get(min_severity, 0)
    return [f for f in findings if SEVERITY_ORDER.get(f.get("severity", "info"), 0) >= threshold]
```

### Main function

Parse arguments:
- `--input` (required): path to JSON findings file
- `--tool-name` (default: `"firebreak"`): tool label in output
- `--min-severity` (default: `"info"`): minimum severity threshold
- `--dry-run` (flag): output to stdout instead of writing to benchmark_data.json

Read the JSON findings file. Filter to findings with `status: verified` or `status: verified-pending-execution` (skip rejected findings). Apply severity filter. Convert each finding via `convert_finding()`.

If `--dry-run`:
- Output the converted findings as a JSON array to stdout

If not `--dry-run`:
- Read existing `benchmark_data.json` (or create empty structure)
- Inject findings into the appropriate PR entry using the manifest for matching
- Write updated `benchmark_data.json`

### What this script does NOT contain

- No `import re`
- No `re.compile()`, `re.search()`, `re.findall()`
- No `_is_metadata_line()` function
- No `parse_findings_flat()` function
- No regex patterns for severity or location extraction
- No markdown parsing of any kind

### Output format for `--dry-run`

When `--dry-run` is used, the script outputs a JSON array to stdout where each element has the fields: `path`, `line`, `body`, `severity`, `type`, `origin`, `reclassified_from`. This is the format the test expects.

When `--input` points to a file with 3 findings (critical, major, minor) and `--min-severity major` is used, the output should contain only the critical and major findings (2 items).

## Files to create/modify

Create: `ai-docs/detection-accuracy/martian-benchmark/inject_results.py`

## Test requirements

Test task-15 validates: file existence, field mapping (path from location.file, line from location.start_line, body from mechanism+consequence, severity direct, type passthrough, origin passthrough, reclassified_from passthrough), severity filtering with --min-severity, no regex parsing (absence of re.compile/re.search/re.findall/_is_metadata_line/parse_findings_flat).

## Acceptance criteria

- Script reads JSON findings directly via `--input` flag
- Maps `location.file` to `path`, `location.start_line` to `line`, `mechanism`+`consequence` to `body`
- Passes `type`, `origin`, `reclassified_from` through to output
- `--min-severity` filters by severity threshold
- `--dry-run` outputs converted findings to stdout as JSON
- `--tool-name` accepted (used in non-dry-run mode)
- No `import re`, no regex patterns, no `_is_metadata_line`, no `parse_findings_flat`
- Runs via `uv run`

## Model

sonnet

## Wave

4
