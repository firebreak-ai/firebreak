# Task 05: Create Task Compilation Guide

## Objective

Create the leaf doc that provides detailed Stage 3 (Task Breakdown) guidance for agents compiling specs into executable task specifications.

## Context

This doc is loaded by the `/breakdown` skill when Stage 3 is active. It guides the agent through compiling a reviewed spec into individual task files — self-contained instructions that implementation agents follow with no remaining ambiguity.

### Core principle

Tasks are **compiled executable specifications**, not summaries. Ambiguity in a task is a compilation error. If the compiling agent cannot write clear instructions for a task, the spec is underspecified — stop and report rather than guess.

### Task sizing constraints (empirical basis)

File count is the sharpest predictor of agent success:

| Constraint | Target | Rationale |
|-----------|--------|-----------|
| Files modified per task | 1-2 | Sharp decline above 3 files; frontier models drop to ~11% at 10+ files |
| Lines changed per task | <55 | 11x difficulty scaling from easy (<10) to hard (55+) |
| Hunks per task | 1-6 | Moderate reliability zone |
| Independence | Full | Each task executes without reading other tasks or the full spec |

If a task exceeds constraints, split it. If splitting creates artificial boundaries (e.g., a schema migration necessarily touching 4 files), document the justification.

### Task file structure (each `task-NN-<description>.md`)

Each task file is the complete instruction set for an implementation agent:

1. **Objective** — One sentence: what this task produces.
2. **Context** — Written by the compiling agent for the implementation agent. Comprehended and distilled from the spec, not raw excerpts. Include only what the agent needs to execute the instructions.
3. **Instructions** — Step-by-step implementation instructions. Explicit enough that the agent makes no design decisions.
4. **Files to create/modify** — Explicit scope boundary. The agent must not touch files outside this list.
5. **Test requirements** — New tests to write (specify level: unit/integration/e2e) and existing tests to update (specify file, what changes, why).
6. **Acceptance criteria** — Verifiable conditions. Reference spec AC IDs (AC-01, AC-02, ...). For implementation tasks: the primary AC is "the tests from the corresponding test task pass."
7. **Model** — Haiku or Sonnet, based on structural complexity.
8. **Wave** — Which parallel execution wave.

A task file does NOT contain:
- References to "read the spec for details"
- Open design questions
- Multiple valid implementation approaches (choose one during compilation)
- Context from other tasks (each task is independent)

### Test/implementation task separation

Separate test tasks (write/update tests) from implementation tasks (write the code that makes tests pass). Within each wave, test tasks execute before implementation tasks — tests are written first, then implementation makes them pass.

Every code-modifying task must have a corresponding test task.

### Task overview structure (`task-overview.md`)

- **Dependency DAG**: Task ordering constraints. Must be acyclic.
- **Wave assignments**: Groups of tasks that execute in parallel. Waves execute sequentially. Test tasks before impl tasks within each wave.
- **Model routing summary**: Haiku vs. Sonnet per task. Haiku for bounded single-file work; Sonnet for multi-file or architecturally significant.
- **Coverage map**: Every spec AC ID (AC-01, AC-02, ...) → test task + implementation task(s). No AC may be uncovered.

### Required formats for gate-parseable sections

The breakdown gate script parses task-overview.md programmatically. Use these exact formats:

**Coverage map** — markdown table with these columns:
```
| AC | Primary Task | Supporting Tasks |
```

**Dependencies** — a `Dependencies:` label followed by lines matching:
```
- T-NN (description) ← T-NN, T-NN
```

**Wave assignments** — markdown tables under `### Wave N` headings. Each table must include a `Task` column with `T-NN` identifiers.

### Model routing guidance

- **Haiku**: Bounded single-file tasks. Clear instructions, no architectural judgment needed. Typically: adding a function, updating a config file, writing a test for a specific behavior.
- **Sonnet**: Multi-file tasks, tasks requiring architectural judgment, tasks touching integration points. When in doubt, choose Sonnet — the cost of under-routing (Haiku fails, requires escalation) exceeds the cost of over-routing.

### Ambiguity as signal

If the compiling agent encounters ambiguity — a spec section that could be interpreted multiple ways, or a task where the instructions would require the agent to make a design choice — that is signal the spec is underspecified. The compiling agent stops and reports the ambiguity. Resolution requires returning to Stage 1 or Stage 2 to clarify before compilation continues.

### Verification gate

**Structural prerequisites** (deterministic — the `/breakdown` skill calls a gate script):
- Every spec AC ID appears in the coverage map with both a test task and an implementation task
- No circular dependencies in the task DAG
- Wave assignments respect dependency ordering
- Within each wave, test tasks ordered before corresponding implementation tasks
- File scope declarations don't conflict across tasks in the same wave
- No task exceeds file count constraint without documented justification
- Every code-modifying task has a corresponding test task

**Semantic evaluation** (human or council review):
- Task instructions are unambiguous — implementation agent makes no design decisions
- Task context is sufficient — agent doesn't need to read the full spec
- Task boundaries are natural — splits don't create artificial seams
- Impacted existing tests from the spec's testing strategy are assigned to test tasks
- Test tasks cover behavioral intent of referenced ACs, not just surface assertions

### Transition

After presenting the task overview:
1. Run structural prerequisites.
2. If pass: "The task breakdown covers all spec requirements across N tasks in M waves. Structural checks pass. Would you like to review individual tasks, invoke council for validation, or proceed to implementation?"
3. If agreed: invoke `/implement <feature-name>`.

## Instructions

1. Create `home/.claude/docs/sdl-workflow/task-compilation.md`.
2. Read `home/.claude/docs/context-assets.md` for authoring principles. Apply them.
3. Write for the agent running Stage 3 — direct imperatives.
4. Structure the doc:

   - **Compilation principle** — Tasks are compiled specs, not summaries. Ambiguity is a compilation error.
   - **Sizing constraints** — The table with targets and rationale. This is essential reference — include the numbers.
   - **Task file structure** — The 8-section format with content requirements for each. Include the "does NOT contain" list.
   - **Test/impl separation** — How to split and order within waves.
   - **Task overview structure** — DAG, waves, model routing, coverage map.
   - **Model routing** — Haiku vs. Sonnet guidance.
   - **Ambiguity handling** — Stop and report, don't guess.
   - **Verification gate** — Structural checks and semantic criteria.
   - **Transition** — Next-stage offer.

5. The sizing constraints table and task file structure are the highest-value content — include them completely. The compilation principle prevents the most common mistake (producing summaries instead of specifications).
6. Target: 140-180 lines.

## Files to Create/Modify

- **Create**: `home/.claude/docs/sdl-workflow/task-compilation.md`

## Acceptance Criteria

- AC-05: Enables spec compilation into sized, independent, wave-assigned tasks with coverage mapping
- AC-15: Follows authoring principles

## Model

Sonnet

## Wave

1
