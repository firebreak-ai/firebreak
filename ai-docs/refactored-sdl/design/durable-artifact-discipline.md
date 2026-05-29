---
title: "Durable-Artifact Discipline"
type: concept
sources:
  - firebreak-sdl-workflow
tags:
  - sdl-pipeline
  - pattern
  - durable-docs
  - refactored-sdl
created: 2026-05-29
updated: 2026-05-29
---

## Durable-Artifact Discipline

The lightweight answer to "where does content that outlives a feature live?" — a small, curated set of plain git-tracked markdown docs, not a memory system. It replaces the heavier project-memory layer cut from this cycle (see the decision spine and [[project-memory-brainstorm]]).

### The durable set

- **Glossary** — aligned terminology. Edited in place.
- **Decisions log** — the *why* behind enduring choices. Append-only, chronological.
- **Architecture/intent overview** — what the project is and how it works, now. Living, edited in place, kept to onboarding length — the doc a new human hire (or a cold agent) reads to come up to speed. This is where sticky project intent lives (see [[fbk-intent]]).

Everything else the SDL produces — the spec, the design pages, the design manifest, the breakdown task list, the test-lock manifest, the reports, the retrospective — is spent scaffolding: it lives in the feature directory and is deleted at squash-merge.

### Governing rules

- **Plain markdown, no tooling.** No index, no frontmatter graph, no install contract, no semantic-search dependency. Just files in the repo's normal doc locations.
- **Comprehensibility.** Simple language, bounded file length, intuitive names and folder structure — readable by both human teams and cold agents.
- **No clutter.** Durable does not mean append-everything; the overview is revised in place to stay at onboarding length, and only enduring decisions go in the decisions log.
- **CLAUDE.md is not a durable-intent store.** It carries agent behavioral rules; project intent lives in the overview.

### Git co-location is the sync mechanism

Durable docs are **updated in the feature branch and merge into main with the change they describe.** Branch docs describe the branch; main docs describe main — they stay as in-sync as the code because they are part of the same change. This is what makes the discipline categorically better than the cut wiki on the wiki's own failure mode (silent drift):

- A stale overview shows up in the PR diff as "this PR changed behavior but didn't touch the overview," where a human or agent reviewer can catch it.
- Parallel edits across branches resolve as ordinary git merge conflicts — the conflict-resolution mechanism the wiki never had.

Maintenance rides on the work that changes the docs (the intent and design phases update them in-branch); the [[fresh-eyes-technique]] check doubles as the overview's comprehension test.

### Related

- [[project-memory-brainstorm]] — the heavier layer this replaces, deferred
- [[fbk-intent]] · [[fbk-design]] — the phases that read and update the durable docs
- [[fresh-eyes-technique]] — the overview's comprehension check
- [[firebreak-sdl-workflow]]
