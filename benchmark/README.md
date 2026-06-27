# Benchmarks

Reproducible evaluations that back Firebreak's public claims. Each subdirectory is
one benchmark, scoped by what it measures, so methodology and results for different
kinds of evaluation stay cleanly separated.

| Benchmark | What it measures |
|-----------|------------------|
| [`code-review/`](code-review/) | Code-review detection accuracy (precision / recall / F1) against the Martian Code Review Benchmark — 50 real pull requests across five public repositories. |

Future benchmarks (for other parts of the pipeline) live beside `code-review/` as
their own scoped directories.

Each benchmark directory holds its **harness** (the scripts and prompts that run the
evaluation) and its **results**, archived per Firebreak release so that re-running a
benchmark on a new release shows the delta against earlier baselines.
