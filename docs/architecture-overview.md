# Architecture Overview

Living, onboarding-length overview of the Firebreak project. Update this in-branch when intent or structure shifts; new hires and cold agents read it first.

## What this is

Firebreak is a structured development loop (SDL) implemented as a set of Claude Code context assets — skills, agents, and configuration — that a human operator invokes to drive high-quality AI-assisted software work. The pipeline runs inside a git repository; its deliverables are code changes, tests, and this small set of durable docs. Firebreak is not a framework the target project installs; it is a set of `.claude/` assets the operator brings to any project.

## How the pipeline works

The six phases run in order. The human enters at the phase that fits the work — a small bugfix may enter at spec; a large change starts at intent.

1. **Intent** — Grounds the work in project context; runs grilling and fresh-eyes to surface ambiguity before any spec is written.
2. **Design** — Explores technical approaches; produces design pages and a design manifest; anchors the gate on a fresh-eyes artifact.
3. **Spec** — Formalizes the chosen approach as slice declarations with test-discipline modes; gate runs council review.
4. **Breakdown** — Decomposes slices into paired test-tasks and impl-tasks, assigns waves, produces the test-lock manifest.
5. **Code-review** — Validates the implementation set: hash check against the test-lock manifest, quality scan, test review.
6. **Implement** — Executes tasks wave by wave; impl-tasks write code to turn failing tests green without modifying them.

## Gates

Every phase gate follows the hybrid-gate pattern: a **mechanical anchor** (deterministic structure check — file presence, hash match, manifest bidirectionality) plus a **semantic anchor** anchored on a verifiable artifact produced by a technique skill. The mechanical part is hook-ready; the semantic part has something concrete to inspect rather than re-running judgment from scratch.

## Technique skills

Technique skills are the capability layer between phase skills and agent personas — extracted into their own callable skills because at least two phases benefit from invoking them with a stable interface.

- **Grilling** (`/fbk-grilling`) — one-question-at-a-time ambiguity resolution; invoked by intent, design, and spec phases, and by the operator out-of-ceremony via `/grill-me`.
- **Fresh-eyes** (`/fbk-fresh-eyes`) — context-clear comprehension check; a subagent reads the artifact cold and surfaces structured observations by severity; no fix authority.
- **Quality scan** (`/fbk-quality-scan`) — top-five code-quality scan at code review time (the Pocock pattern); findings are ranked, scan-only.
- **Test review** (`/fbk-test-review`) — validates AI-written tests for known failure modes; runs pre-lock at breakdown and as a final pass at code review.

## Durable docs

Durable docs are the small curated set of git-tracked markdown that outlives a feature. The governing conventions:

Durable docs are **plain markdown**, kept to **bounded length**, and updated **in-branch** so they merge with the change.

The three durable docs are:
- `GLOSSARY.md` — canonical agreed terminology and definitions.
- `docs/decisions-log.md` — append-only chronological record of constraining decisions.
- `docs/architecture-overview.md` — this file; living project overview.

Spent scaffolding (spec, breakdown, manifests, reports, retrospective) lives under `ai-docs/<feature-name>/` and is deleted at squash-merge.

## Python runtime

Firebreak's Python code (the dispatcher `fbk.py`, the gate modules under `fbk/gates/`, the helpers, and the test suite) runs through `uv` — the project does not depend on system-wide Python packages.

The constraint is that Firebreak is most often installed globally on systems where the system Python may be locked down (PEP 668 / externally-managed-environment, common on recent Arch/Debian/Ubuntu and Homebrew macOS). `pip install --user` fails on those systems; `python3 -c "import yaml"` returns ImportError unless the user has manually set up a venv outside Firebreak's awareness. `uv` handles project-local virtualenv creation, Python-version pinning (`requires-python = ">=3.11"` in `pyproject.toml`), and dependency resolution without touching system packages.

The installer, shell tests, and skill body invocations currently use `python3` directly — a pre-existing pattern from before this constraint was made explicit. A migration to `uv run` at every Python invocation point is tracked as a follow-up in `docs/decisions-log.md` under the 2026-05-29 "Python runtime must not depend on system-wide packages" entry.

## Measurement (in progress)

Firebreak is gaining a deterministic metrics plane so the pipeline measures itself from code rather than relying on agents to narrate the retrospective. Two capture sources — a Claude-level hook router and a wrapper around the dispatcher's single command chokepoint — feed one report command that aggregates per-stage durations, gate first-pass rates, parks, rework, scope violations, code-review detection rounds, and tokens. The report is runnable ad-hoc and auto-injected into the retrospective.

Capture is **globally armed but per-project gated**: the router installs globally yet records only in Firebreak-managed or explicitly-marked projects, always into a project-local gitignored directory, never the global config directory. Payloads (tool-call arguments and prompt text) are captured only at the `full` level; the default is `standard`. This is a governing constraint — see the 2026-06-10 decisions-log entry. Feature intent and behaviors live under `ai-docs/hook-harvesting/`.
