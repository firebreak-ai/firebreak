# Benchmark Results

Results are archived per Firebreak release. Each `<release>/` folder holds the written
reports for that release's benchmark cycle, plus the full scoring chain behind them.
To see how detection accuracy changed between releases, compare the headline tables of
the same benchmark across two folders.

| Release | Folder | Headline |
|---------|--------|----------|
| v0.4.0 | [`0.4.0/`](0.4.0/) | Full-repo 50-PR pilot: **F1 41.3%** (precision 36.3%, recall 47.8%), up from the v0.3.5 diff-only baseline (F1 31.6%). |

## Layout of a release folder

```
<release>/
  *.md          written reports — read these first
  scoring/      the evidence chain for every number: judge input, the three
                independent judge runs, and the consensus verdict
  runners/      the exact scripts used to drive that release's run (historical
                record; they reference the harness at the benchmark root)
```

Reports cite their scoring files by name (e.g. `scoring/judge_consensus_*.json`), so
any reported figure can be traced back to the per-PR judge verdicts it came from.

## The 0.4.0 cycle

The 0.4.0 work restructured the detector architecture around agent
instruction-following limits and switched the benchmark to full-repo review (matching
how the benchmark's peer tools operate). The reports, in reading order:

| Report | What it covers |
|--------|----------------|
| `0.4.0-single-detector-23pr-results.md` | First single-detector run, 23 PRs. |
| `0.4.0-single-detector-50pr-results.md` | Single-detector at full scale, 50 PRs, diff-only. |
| `0.4.0-broad-behavioral-comparison.md` | Effect of a broader behavioral finding definition, 20 PRs. |
| `0.4.0-challenger-fix-comparison.md` | Effect of a fix to the Challenger verification step, 20 PRs. |
| `0.4.0-fullrepo-50pr-results.md` | The headline pilot: switch to full-repo review, 50 PRs. Precision and recall both improved. |
| `0.4.0-fullrepo-50pr-fn-retrospective.md` | Retrospective on the 71 remaining false negatives — where recall still falls short and why. |
| `0.4.0-audit-passes-21pr-results.md` | Targeted re-run of 21 PRs covering the false-negative buckets the retrospective identified. |

Every number in these reports comes from a single benchmark cycle. As the headline
report notes, orchestrator non-determinism, judge spread (±3–5 points across the three
judges), and sample size mean a single run's small movements sit within the margin of
error — treat absolute figures as directional until additional cycles establish a
confidence interval.
