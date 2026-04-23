---
id: task-31
type: implementation
wave: 4
covers: [AC-13, AC-14]
files_to_create:
  - ai-docs/detection-accuracy/martian-benchmark/run_reviews.sh
  - ai-docs/detection-accuracy/martian-benchmark/judge_anthropic.py
  - ai-docs/detection-accuracy/martian-benchmark/manifest.json
  - ai-docs/detection-accuracy/martian-benchmark/benchmark-prompt.md
test_tasks: [task-16]
completion_gate: "bash tests/sdl-workflow/test-benchmark-infrastructure.sh exits 0"
---

## Objective

Cherry-pick the Martian benchmark infrastructure from the `feature/0.4.0-detector-decomposition` branch so the benchmark runner, judge, manifest, diffs, and prompt are available on the current branch.

## Context

The benchmark infrastructure already exists on `feature/0.4.0-detector-decomposition`. Some files already exist on the current branch under `ai-docs/detection-accuracy/martian-benchmark/` (the `diffs/`, `logs/`, `results/` directories). The missing files are the scripts, manifest, and prompt that were added in the decomposition work.

The files to bring over are:
- `ai-docs/detection-accuracy/martian-benchmark/run_reviews.sh` (headless benchmark runner)
- `ai-docs/detection-accuracy/martian-benchmark/judge_anthropic.py` (LLM judge)
- `ai-docs/detection-accuracy/martian-benchmark/manifest.json` (50-PR corpus)
- `ai-docs/detection-accuracy/martian-benchmark/benchmark-prompt.md` (headless mode overrides)

Additional useful scripts on the decomposition branch (cherry-pick if present, skip if not critical):
- `ai-docs/detection-accuracy/martian-benchmark/aggregate_judge.py`
- `ai-docs/detection-accuracy/martian-benchmark/aggregate_tokens.py`

`inject_results.py` is handled separately in task-32 (rewritten, not cherry-picked).

## Instructions

### Step 1: Extract files from the decomposition branch

For each file, use `git show` to extract the content from the decomposition branch and write it to the current branch:

```bash
git show feature/0.4.0-detector-decomposition:ai-docs/detection-accuracy/martian-benchmark/run_reviews.sh > ai-docs/detection-accuracy/martian-benchmark/run_reviews.sh
git show feature/0.4.0-detector-decomposition:ai-docs/detection-accuracy/martian-benchmark/judge_anthropic.py > ai-docs/detection-accuracy/martian-benchmark/judge_anthropic.py
git show feature/0.4.0-detector-decomposition:ai-docs/detection-accuracy/martian-benchmark/manifest.json > ai-docs/detection-accuracy/martian-benchmark/manifest.json
git show feature/0.4.0-detector-decomposition:ai-docs/detection-accuracy/martian-benchmark/benchmark-prompt.md > ai-docs/detection-accuracy/martian-benchmark/benchmark-prompt.md
```

Cherry-pick the aggregate scripts if they exist:
```bash
git show feature/0.4.0-detector-decomposition:ai-docs/detection-accuracy/martian-benchmark/aggregate_judge.py > ai-docs/detection-accuracy/martian-benchmark/aggregate_judge.py 2>/dev/null || true
git show feature/0.4.0-detector-decomposition:ai-docs/detection-accuracy/martian-benchmark/aggregate_tokens.py > ai-docs/detection-accuracy/martian-benchmark/aggregate_tokens.py 2>/dev/null || true
```

### Step 2: Make scripts executable

```bash
chmod +x ai-docs/detection-accuracy/martian-benchmark/run_reviews.sh
```

### Step 3: Update run_reviews.sh for the new pipeline

After cherry-picking, update `run_reviews.sh` to reference the new pipeline. The benchmark runner needs to invoke the review pipeline and produce JSON output compatible with the inject script. Search the runner script for any hardcoded paths or markdown-based output references. Update:

- If the runner references a markdown-to-findings conversion, replace with `uv run assets/scripts/pipeline.py` invocation
- If the runner references old inject script patterns, update to reference the new JSON-based inject

The exact changes depend on the runner's current implementation. Read the cherry-picked file, identify references to the old pipeline, and update them. The runner must reference `pipeline.py` or `uv run` for test task-16 test 12 to pass.

### Step 4: Ensure results directory exists

```bash
mkdir -p ai-docs/detection-accuracy/martian-benchmark/results
```

### Step 5: Verify manifest

Confirm manifest.json contains 50 PR entries:
```bash
python3 -c "import json; d=json.load(open('ai-docs/detection-accuracy/martian-benchmark/manifest.json')); assert len(d)==50"
```

## Files to create/modify

Create (via cherry-pick): `ai-docs/detection-accuracy/martian-benchmark/run_reviews.sh`, `judge_anthropic.py`, `manifest.json`, `benchmark-prompt.md`
Modify: `ai-docs/detection-accuracy/martian-benchmark/run_reviews.sh` (update pipeline references)

## Test requirements

Test task-16 validates: benchmark directory, run_reviews.sh executable, inject_results.py exists, judge exists, manifest valid JSON with 50 entries, diffs populated, benchmark-prompt.md exists, results directory, inject script JSON consumption, no regex parsing, runner references pipeline.py.

Note: Test 3 (inject_results.py exists) and tests 10-11 (inject script content) are validated by task-32. This task satisfies tests 1, 2, 4, 5, 6, 7, 8, 9, 12.

## Acceptance criteria

- `run_reviews.sh` exists and is executable
- `judge_anthropic.py` exists and is non-empty
- `manifest.json` exists, is valid JSON, contains 50 PR entries
- `benchmark-prompt.md` exists and is non-empty
- `diffs/` directory contains diff files
- `results/` directory exists
- `run_reviews.sh` references `pipeline.py` or `uv run`

## Model

sonnet

## Wave

4
