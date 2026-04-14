# Martian Benchmark Evaluation

Comparative evaluation of Firebreak against 38 code review tools using the
[Martian Code Review Benchmark](https://github.com/withmartian/code-review-benchmark).

## Benchmark Summary

- **50 PRs** across 5 repos (Cal.com/TS, Sentry/Python, Grafana/Go, Discourse/Ruby, Keycloak/Java)
- **136 golden comments** (human-verified ground truth) with severity labels
- Automated LLM-as-judge scoring: precision, recall, F1
- 38 tools already evaluated; Claude Code baseline: **34.8% F1** (30.7% precision, 40.1% recall)

## Evaluation Hypothesis

Firebreak's adversarial verification (Detector + Challenger) should produce higher **precision**
than raw Claude Code, because the Challenger suppresses false positives. If Firebreak also
maintains or improves recall, F1 will exceed the Claude Code baseline — demonstrating that
the methodology adds measurable value beyond the base model.

## Key Baselines

| Tool | Precision | Recall | F1 |
|---|---|---|---|
| cubic-v2 (leader) | 55.6% | 68.6% | 61.4% |
| augment | 46.0% | 63.5% | 53.4% |
| devin | 54.2% | 38.0% | 44.6% |
| claude (raw) | 35.7% | 40.1% | 37.8% |
| claude-code | 30.7% | 40.1% | 34.8% |

## Pipeline

### Step 1: Fetch PR diffs

```bash
cd ai-docs/detection-accuracy/martian-benchmark
python3 fetch_pr_diffs.py
```

Reads golden comment files from the cloned benchmark repo, fetches each PR diff
via `gh api`, saves to `diffs/`. Requires `gh` CLI authenticated.

### Step 2: Run Firebreak reviews

Run the automated batch reviewer against each PR diff. Reviews go to `reviews/`.
This is the expensive step (~$2-5 per review, ~$100-250 total for 50 PRs).

```bash
# Dry run — verify command construction
./run_reviews.sh --dry-run --limit 3

# Single test review (smallest diff)
./run_reviews.sh --limit 1 --start-from grafana__grafana__grafana__PR90939

# One repo at a time
./run_reviews.sh --repo grafana

# Full run with default model (opus orchestrator, sonnet agents)
./run_reviews.sh

# Model comparison: sonnet orchestrator
./run_reviews.sh --model sonnet --tool-name firebreak-sonnet

# Full pipeline: reviews + inject + judge
./run_reviews.sh --full-pipeline
```

Uses `claude -p` (headless mode) with semantic skill invocation of `/fbk-code-review`.
Each review runs as an independent session. Resume-safe — skips PRs with existing
review files. Token usage logged to `logs/tokens_{model}_{timestamp}.jsonl`.

Flags: `--model`, `--limit`, `--repo`, `--start-from`, `--delay`, `--max-budget`,
`--max-retries`, `--tool-name`, `--full-pipeline`, `--dry-run`. Run `--help` for details.

#### Token aggregation

```bash
python3 aggregate_tokens.py logs/tokens_opus_*.jsonl
```

Produces a CSV summary and prints per-repo/per-model breakdowns to stdout.

### Step 3: Inject results into benchmark format

```bash
python3 inject_results.py
```

Converts Firebreak review output to the benchmark's `benchmark_data.json` format.

### Step 4: Score with LLM judge

```bash
python3 judge_anthropic.py
```

Adapted from the benchmark's step3_judge_comments.py to use Anthropic API directly.
Computes precision/recall/F1 against golden comments.

### Step 5: Consensus judge (recommended)

```bash
python3 prepare_judge_batches.py
./run_judge.sh
python3 aggregate_judge.py
```

Spawns 3 independent Opus sub-agents per PR to evaluate golden-to-finding matches.
Majority vote aggregation. Produces `judge_consensus.json` (use with `build_deviation_map.py`)
and `judge_variance.json` (split vote analysis). 95.6% unanimous rate on v0.3.5 baseline.

### Step 6: Deviation analysis

```bash
python3 build_deviation_map.py
```

Reads `judge_consensus.json` + `manifest.json` + `reviews/*.md`. Produces
`deviation_map.json` and `deviation_map.md` with per-PR TP/FP/FN detail and
auto-classified FN categories.

## Scoping Notes

**Context disparity**: All competing tools on the benchmark receive the full repository
via `step0_fork_prs.py` (clones repo, forks to org, recreates PR). Firebreak runs
diff-only — `run_reviews.sh` passes just the diff file. This suppresses recall on
issues requiring cross-file or framework-specific knowledge (~21 of 43 FNs).

**Judge methodology**: Single-pass LLM judging shows ~25% variance across runs.
The consensus protocol (3x independent agents, majority vote) produces a stable baseline
with 95.6% unanimous agreement. Use `run_judge.sh` for all evaluations.
