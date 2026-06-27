# Firebreak

[![CI](https://github.com/firebreak-ai/firebreak/actions/workflows/ci.yml/badge.svg)](https://github.com/firebreak-ai/firebreak/actions/workflows/ci.yml)

**Firebreak is my Claude Code workflow to wrangle the agent into creating more maintainable, readable code** — a growing library of skills and agents that bring real software-lifecycle discipline to AI-generated code.

Pointed at a Go project that passed CI but barely worked, its review found:

- **Tests that tested nothing** — all wired to a deprecated mock that production code never called.
- **A "thread-safe" wrapper that wasn't** — it shared collections by reference, a race static analysis missed.
- **A core feature wired to nothing** — one nil parameter left it permanently inert, tests still green.

Firebreak is my personal workflow. I experimented with spec-driven development early on and decided to build my own (both to adapt my personal preferences and to develop my own skills). I use it on my own projects and share it so others can use it or provide feedback. The evidence here is based only on my own personal projects and limited benchmark runs - all claims are unverified and tentative until/unless contributors would like to submit their own results, which I would very much welcome. [Full results, methodology, and caveats →](results.md)

## Install

Requires [Claude Code](https://docs.anthropic.com/en/docs/claude-code), Python 3.11+, and [`uv`](https://docs.astral.sh/uv/).

```bash
# Global install (~/.claude/)
curl -fsSL https://raw.githubusercontent.com/firebreak-ai/firebreak/main/installer/install.sh | bash

# Into a single project
curl -fsSL https://raw.githubusercontent.com/firebreak-ai/firebreak/main/installer/install.sh | bash -s -- --target ./my-project/.claude

# Preview without changing anything
curl -fsSL https://raw.githubusercontent.com/firebreak-ai/firebreak/main/installer/install.sh | bash -s -- --dry-run
```

Then just ask Claude Code:

```
"Let's create a new feature..."
"Let's turn this into a design..."
"Review the tests in this project..."
```

## How it works

Firebreak applies ordinary software-lifecycle discipline — independent review, explicit gates, test-driven development, retrospectives — to AI-generated code. The catch it's built around: the agents doing the reviewing can fail the same way the code does, so nothing is trusted on one agent's word.

It's a library of skills, not a single prescriptive process. Many stand on their own, and several compose into a full spec-driven pipeline when a change is big enough to earn it:

- **Adversarial review** — standalone or in the pipeline. A researcher agent surfaces candidate issues; a challenger re-reads the code cold and promotes only what it can prove. It targets the bugs static analysis has no signal for — vacuous tests, call-graph races, dead wiring. This works to review code, specifications, plans, designs - it's the same general process with a few different lenses based on what is being reviewed.
- **A gated pipeline for the hard changes.** Intent → design → spec → review → breakdown → implementation, with a deterministic gate between each stage and context-isolated agents to prevent context rot and pollution. Reviewed tests are hash-locked before implementation, so tests can't be rewritten to "just pass." The "intent" alignment phase is particularly helpful; overall the pipeline works to progressively distill the *right* context, strip away ambiguity, and create clear executable tasks for AI implementation.
- **Retrospectives that feed back.** When capture is enabled, each run records what worked, what broke, and where I had to step in. This is a combination of deterministic observability metrics from hooks, plus the agents' own analysis. I then let an agent triage the findings: trivial fixes are quick to approve and apply, larger ones run through the full pipeline when I prioritize them.

**Where it's heading:** many changes don't require the full pipeline ceremony (especially as models improve), and today you still pick the ceremony level yourself. I'm working toward skills an agent can assemble on the fly — right-sizing the process to the job, so a one-line fix doesn't pay for a six-stage workflow and a risky refactor doesn't get a single-shot prompt. My real inspiration here is the Anthropic Dynamic Workflows feature - I'd like the Firebreak assets to integrate with Dynamic Workflows to automatically adapt to the current task.

A focused code review takes around half an hour; a full pipeline run, a few hours. Code review works in any language; the post-task test and lint gate depends on a toolchain Firebreak recognizes, but it tries to use the tools available on the system (without making them actual Firebreak dependencies). [Architecture overview →](docs/architecture-overview.md) · [token usage and cost →](results.md#token-usage-and-cost)

## Commands

**Start here:** `/fbk-code-review` — adversarial review of any code, from one module to the whole repo.

For complex changes (remediation, new features, etc), a structured pipeline carries them from intent through gated implementation: `/fbk-intent` → `/fbk-design` → `/fbk-spec` → `/fbk-spec-review` → `/fbk-breakdown` → `/fbk-implement`. Then `/fbk-improve` turns each run's retrospective into pipeline fixes for Firebreak itself.

Other standalone helpers include context-asset authoring (ask Claude to write or review a CLAUDE.md, skill, hook, or agent, in any project), plus `/fbk-quality-scan`, `/fbk-council`, `/fbk-test-review`, `/fbk-fresh-eyes`, and `/fbk-grilling`.

## Security

- Firebreak adds no telemetry or analytics of its own. (The installer downloads dependencies, and Claude Code reaches the model as usual.)
- Local run records under `.fbk-capture/` (timings, gate outcomes, token usage) stay on your machine; the default `standard` level redacts free text, and you can set `capture_level=off` in `.fbk-capture/capture.cfg`.
- Gates parse markdown and JSON — they don't execute it — and the intent, design, and spec gates screen for prompt-injection patterns. After each task, a hook runs your project's test suite and linter when it recognizes the toolchain (npm, cargo, go, pytest, and the like).
- The pipeline edits your source and tests when you ask it to implement — review its changes like any contributor's.
- **Known limit:** Claude Code's permissions control which *tools* an agent has, not its *intent*. Firebreak restricts analysis agents to read-only tools to limit the blast radius, but the gap is real. [Details →](docs/evidence/brownfield-validation/analysis.md)

## Docs

- [Results, methodology, and raw data](results.md)
- [Architecture overview](docs/architecture-overview.md)
- [Context-asset authoring guide](assets/fbk-docs/fbk-context-assets.md)

## Feedback

Firebreak is under active development, and I'd genuinely value feedback from others. Most useful: results from real runs, false positives and false negatives, where the gates were effective vs got in the way, comparisons with other agent workflows, etc. [Open an issue →](https://github.com/firebreak-ai/firebreak/issues)

## License

MIT — see [LICENSE](LICENSE).
