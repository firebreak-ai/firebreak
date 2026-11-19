## Why Firebreak exists

Firebreak is a firebreak against AI slop. People write tangled code too, but AI writes it faster, compounds it, and repeats its own bad patterns. Firebreak is a method for getting AI to produce code that is correct and maintainable.

Maintainability is the relative cost of future changes, bug fixes and feature work alike. Cost is human time, attention and effort: how much must be found and understood, how far an edit spreads, how much the tests resist the change, and how likely the change is to break something else. It covers the tests as well as the code. Dollars and agent minutes are a weak stand-in for that cost.

Every change in this repo serves that purpose. Judge each proposal, result and recommendation by what it does for correctness and for the cost of future changes.

## Working on the 0.6.0 branch

Read `docs/architecture-overview.md` for the current design and `docs/0.6.0/plan.md` for rationale. New `.fbk/` workflows follow `assets/fbk-docs/state-driven-workflow.md`. Current decisions are in `docs/decisions-log.md`. Superseded workflows and their assets live in git history.

For context asset authoring principles, read `assets/fbk-docs/fbk-context-assets.md`.

A change to phase names, skill names, how a phase is recorded as closed, or what the workflow asks the operator also needs the benchmark kit updated; see "When Firebreak changes" in `benchmark/maintainability/README.md`.

## Always-on disciplines

Apply these five disciplines in every session — writing, reviewing, or conversing on any firebreak work. Full rule at `.claude/fbk-docs/fbk-context-assets/always-on-disciplines.md`.

- **simple language** — write as if for a smart non-engineer; minimize jargon.
- **descriptions over identifiers** — refer to items by name or description, never by bare identifier (no "AC-1", "F-02", "B-NNN").
- **capability framing** — describe what a thing is and what it does, not what it forbids or is not.
- **interview before drafting** — surface open decisions and get answers before producing an artifact.
- **structural-principles awareness** — verify every context asset change against necessity test, progressive disclosure, separation of concerns, trust-the-agent, objectives-over-steps.

Python that Firebreak installs (`assets/fbk-scripts` outside `tests`, and `installer/merge-settings.py`) passes the lint check: `python3 tests/run-tests.py --suite lint`. A new function stays at or under complexity 10; `docs/testing.md` describes the rules and the recorded backlog.

`GLOSSARY.md` at the repo root is the canonical source for agreed terminology and definitions. Consult it before introducing a new term-of-art, and add an entry when a spec or context asset introduces one.

Update `CHANGELOG.md` when preparing tagged releases. Follow [keepachangelog.com](https://keepachangelog.com/) format: group changes under Added, Changed, Deprecated, Removed, Fixed, Security.
After any `CHANGELOG.md` update, check the `README.md` for any required updates. Discuss proposed readme changes with the user.