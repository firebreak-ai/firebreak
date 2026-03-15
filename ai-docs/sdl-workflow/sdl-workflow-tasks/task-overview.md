# SDL Workflow — Task Overview

## Acceptance Criteria

| ID | Criterion |
|----|-----------|
| AC-01 | `sdl-workflow.md` index routes to the correct leaf doc for each of the 4 pipeline stages plus the conditional threat-modeling doc |
| AC-02 | `feature-spec-guide.md` enables an agent to guide iterative spec authoring for both project-level and feature-level scope, with all required sections, testing strategy specificity, and verification gate behavior |
| AC-03 | `review-perspectives.md` enables an agent to classify council agents, frame review prompts per SDL concern, and manage threat model determination |
| AC-04 | `threat-modeling.md` enables an agent to produce STRIDE-based threat models and manage project model updates |
| AC-05 | `task-compilation.md` enables an agent to compile specs into sized, independent, wave-assigned tasks with coverage mapping |
| AC-06 | `implementation-guide.md` enables an agent to manage team-based wave execution with verification gates, re-plan protocol, and retrospective |
| AC-07 | `/spec` skill loads feature-spec-guide.md, handles both scopes, runs structural gate, offers stage transition |
| AC-08 | `/spec-review` skill loads review-perspectives.md, classifies council agents, invokes review, handles threat model determination, runs gate, offers transition |
| AC-09 | `/breakdown` skill loads task-compilation.md, compiles tasks, runs structural gate, offers transition |
| AC-10 | `/implement` skill loads implementation-guide.md, manages team waves, runs verification, produces retrospective |
| AC-11 | Spec gate script validates all Stage 1 structural prerequisites from the enforcement mapping |
| AC-12 | Review gate script validates all Stage 2 structural prerequisites from the enforcement mapping |
| AC-13 | Breakdown gate script validates all Stage 3 structural prerequisites including DAG validation and AC coverage |
| AC-14 | TaskCompleted script validates per-task prerequisites (test suite pass, no new lint errors, file scope respected) |
| AC-15 | All assets pass the Necessity Test and follow the 6 context asset authoring principles |

## Adaptation: Context Assets vs. Code

This breakdown compiles a specification into context asset creation tasks, not code implementation tasks. Key adaptations:

- **No test/impl split.** Context assets have no test suite. Each task creates a single asset. Verification criteria are embedded in each task's acceptance criteria.
- **Task T-15 (cross-asset validation) serves as the integration-level verification pass**, analogous to a final test suite run.
- **Sizing constraints apply differently.** Each task creates one file. The "files modified per task" constraint is inherently satisfied (1 file each). Line count varies by asset complexity but each task targets a bounded, single-concern output.
- **Within Wave 1, no ordering constraint applies** — docs and scripts are fully independent.

## Dependency DAG

```
T-01 ─────────────────────────────────────────────┐
T-02 ───────────────── T-11 ──────────────────────┤
T-03 ──────────┬────── T-12 ──────────────────────┤
T-04 ──────────┘                                   │
T-05 ───────────────── T-13 ──────────────────────┼── T-15
T-06 ───────────────── T-14 ──────────────────────┤
T-07 ──────────┬────── T-11 ──────────────────────┤
               └────── T-12 (prior-stage gate)     │
T-08 ──────────┬────── T-12 ──────────────────────┤
               └────── T-13 (prior-stage gate)     │
T-09 ──────────┬────── T-13 ──────────────────────┤
               └────── T-14 (prior-stage gate)     │
T-10 ───────────────── T-14 ──────────────────────┘
```

Dependencies:
- T-11 (`/spec` skill) ← T-02, T-07
- T-12 (`/spec-review` skill) ← T-03, T-04, T-07, T-08
- T-13 (`/breakdown` skill) ← T-05, T-08, T-09
- T-14 (`/implement` skill) ← T-06, T-09, T-10
- T-15 (validation) ← T-01 through T-14

Each skill depends on its own doc + gate script, plus the prior stage's gate script (used for fail-fast validation on entry).

No circular dependencies. All edges flow forward (Wave 1 → Wave 2 → Wave 3).

## Wave Assignments

### Wave 1 — Content Foundation (10 tasks, parallel)

| Task | Output file | Model |
|------|------------|-------|
| T-01 | `home/.claude/docs/sdl-workflow.md` | Haiku |
| T-02 | `home/.claude/docs/sdl-workflow/feature-spec-guide.md` | Sonnet |
| T-03 | `home/.claude/docs/sdl-workflow/review-perspectives.md` | Sonnet |
| T-04 | `home/.claude/docs/sdl-workflow/threat-modeling.md` | Sonnet |
| T-05 | `home/.claude/docs/sdl-workflow/task-compilation.md` | Sonnet |
| T-06 | `home/.claude/docs/sdl-workflow/implementation-guide.md` | Sonnet |
| T-07 | `home/.claude/hooks/sdl-workflow/spec-gate.sh` | Sonnet |
| T-08 | `home/.claude/hooks/sdl-workflow/review-gate.sh` | Sonnet |
| T-09 | `home/.claude/hooks/sdl-workflow/breakdown-gate.sh` | Sonnet |
| T-10 | `home/.claude/hooks/sdl-workflow/task-completed.sh` + `home/.claude/settings.json` | Sonnet |

No file scope conflicts — all output files are distinct.

### Resolved Design Decision: TaskCompleted Hook Scoping

The `TaskCompleted` hook is configured in user-global settings (`~/.claude/settings.json`) and fires on all `TaskCompleted` events. The script self-scopes via context check: it parses the task description for an SDL task file path pattern and exits 0 immediately (pass-through) when not in an SDL implementation context. Skill-scoped hooks were eliminated because they do not propagate to teammates (session-local). Dynamic configuration was eliminated due to fragility (orphaned config on crash).

### Wave 2 — Entry Points (4 tasks, parallel)

| Task | Output file | Model | Dependencies |
|------|------------|-------|-------------|
| T-11 | `home/.claude/skills/spec/SKILL.md` | Sonnet | T-02, T-07 |
| T-12 | `home/.claude/skills/spec-review/SKILL.md` | Sonnet | T-03, T-04, T-07, T-08 |
| T-13 | `home/.claude/skills/breakdown/SKILL.md` | Sonnet | T-05, T-08, T-09 |
| T-14 | `home/.claude/skills/implement/SKILL.md` | Sonnet | T-06, T-09, T-10 |

### Wave 3 — Validation (1 task)

| Task | Output file | Model | Dependencies |
|------|------------|-------|-------------|
| T-15 | (reads all, writes none) | Sonnet | T-01 through T-14 |

## Model Routing Summary

- **Haiku** (1 task): T-01 — routing table, mechanical structure
- **Sonnet** (14 tasks): T-02 through T-15 — architectural content, judgment, or precision validation

## Coverage Map

| AC | Primary Task | Supporting Tasks |
|----|-------------|-----------------|
| AC-01 | T-01 | — |
| AC-02 | T-02 | — |
| AC-03 | T-03 | — |
| AC-04 | T-04 | — |
| AC-05 | T-05 | — |
| AC-06 | T-06 | — |
| AC-07 | T-11 | T-02, T-07 |
| AC-08 | T-12 | T-03, T-04, T-07, T-08 |
| AC-09 | T-13 | T-05, T-08, T-09 |
| AC-10 | T-14 | T-06, T-09, T-10 |
| AC-11 | T-07 | — |
| AC-12 | T-08 | — |
| AC-13 | T-09 | — |
| AC-14 | T-10 | — |
| AC-15 | T-15 | T-01 through T-14 |
