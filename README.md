# Firebreak

[![CI](https://github.com/firebreak-ai/firebreak/actions/workflows/ci.yml/badge.svg)](https://github.com/firebreak-ai/firebreak/actions/workflows/ci.yml)

Firebreak is a Claude Code workflow for developing readable, maintainable code against explicit human intent. Version 0.6.0 keeps requirements, decisions, task handoffs, and independently reviewed acceptance evidence under `.fbk/`.

## Install

Requires [Claude Code](https://docs.anthropic.com/en/docs/claude-code), Python 3.11+, and [`uv`](https://docs.astral.sh/uv/).

```bash
# Global install (~/.claude/)
curl -fsSL https://raw.githubusercontent.com/firebreak-ai/firebreak/main/installer/install.sh | bash

# Into a single project
curl -fsSL https://raw.githubusercontent.com/firebreak-ai/firebreak/main/installer/install.sh | bash -s -- --target ./my-project/.claude

# From a checkout of this repository
bash installer/install.sh --source ./assets --target /path/to/project/.claude
```

Then initialize the workflow in the project:

```bash
cd /path/to/project
uv run --project .claude/fbk-scripts python .claude/fbk-scripts/fbk.py workflow-init
```

Restart Claude Code to load the installed hooks. Repeat installation to upgrade; use `--dry-run` to preview or `--uninstall --target <installation>` to remove an installation. Upgrades remove retired files and unchanged installer-owned settings while preserving operator additions.

## Develop a change

Start with `/fbk-intent <unit-name>`. Work proceeds through intent, optional design, spec, breakdown, and implementation. Small changes can use short documents and a single task. Project units define a parent contract and end after spec.

The runtime manages ownership, scoped authorization, test locks, task dependencies, and acceptance bound to current source files. Intent, design, spec and breakdown can each use one reviewer or a council; design and spec must record the choice. A council is a short discussion the runtime runs: the builder and one or two other members propose corrections, each takes one turn to contest or replace them, then each supports or contests every proposal, and what a majority supports becomes a finding.

Use the phase skills (`fbk-intent`, `fbk-design`, `fbk-spec`, `fbk-breakdown`, `fbk-implement`) for authoring. `fbk-spec-review` and `fbk-council` route managed review through `phase-close`. Continuation packets restore current work after a session change. `/fbk-improve` investigates recorded process issues and tracks whether adopted changes help.

See the [workflow guide](assets/fbk-docs/state-driven-workflow.md) and [architecture overview](docs/architecture-overview.md). Superseded workflows, agents, and release reports are available in git history; this release ships the `.fbk/` workflow and the standalone tools below.

## Standalone tools

`/fbk-code-review <target>` runs independent detection and challenge against code and its governing requirements. Other tools provide focused capabilities:

- `fbk-test-review`: test integrity and meaningful behavioral coverage.
- `fbk-test-cleanup`: a skill made to clean up excessive or weaker-quality tests. If your test suite has been cluttered by AI slop, give this a try.
- `fbk-refactor`: refactors one module without changing its behavior, after checking that its tests would catch a mistake.
- `fbk-fresh-eyes`: an independent read of a document.
- `fbk-quality-scan`: up to five ranked quality opportunities.
- `fbk-doc-reconcile`: documentation drift against shipped behavior.
- `fbk-cross-model-review`: an explicitly enabled second-model opinion.
- `fbk-council`: council review of a planning phase, or a council you convene to discuss an open question.
- `fbk-grilling`: clarification of unresolved decisions.
- `fbk-testplan`: a trial flow in which the test files are the plan. You approve a list of tests, and the code is built one test at a time. It runs beside the managed workflow and is the basis planned for 0.7.0.

Context-asset authoring guidance loads when relevant. Standalone review reports are advisory and do not substitute for managed phase acceptance.

## Evidence and limits

Hooks support phase entry, covered write checks, worker tracking, and continuation. Shell writes, external tools, disabled hooks, and hook timeouts can bypass prevention; close independently rechecks acceptance evidence. Host permissions and sandboxing supply the security boundary.

Optional local telemetry lives in `.fbk/runtime/`. It omits prompts and tool arguments and never determines policy. Usage reports cover recorded review usage, not total authoring cost. Model claims about source inspection and passing tests are limited evidence, not proof of maintainability.

Run deterministic checks with `python3 tests/run-tests.py`. See [testing](docs/testing.md) and [workflow validation](docs/0.6.0/validation.md). Live model evaluations are explicit opt-ins.

## Documentation and feedback

- [Changelog](CHANGELOG.md)
- [Current decisions](docs/decisions-log.md)
- [Glossary](GLOSSARY.md)
- [Context-asset authoring](assets/fbk-docs/fbk-context-assets.md)
- [Report an issue](https://github.com/firebreak-ai/firebreak/issues)

## About the 0.6.0 release

0.6.0 took a long time, most of it spent on trials and evaluations. It started as a major refactor to add the underlying state machine I had originally planned. New phases and some new skills followed.

Then came the evaluations. I was never quite happy with the results. I could get reasonably good, useful code, but it took a lot of time and attention, and the ceremony felt too heavy and too inflexible. So I built a hybrid benchmark from the SlopCodeBench and EXACT approaches. The results were telling: we had gone off the rails. Parts of the flow worked, and other parts were actively detrimental. The problem was more than rigid ceremony. We were also writing code that was harder to maintain.

The same evaluations showed a path forward, and 0.7.0 should come much more quickly.

MIT — see [LICENSE](LICENSE).
