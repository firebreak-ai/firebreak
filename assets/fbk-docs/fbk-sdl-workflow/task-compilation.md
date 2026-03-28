## Compilation Principle

Tasks are compiled executable specifications, not summaries. Every instruction must be explicit enough that the implementation agent makes no design decisions. Ambiguity in a task is a compilation error — if you cannot write clear instructions for a task, the spec is underspecified. Stop and report the ambiguity; do not guess. Resolution requires returning to Stage 1 or Stage 2 before compilation continues.

Choose one implementation approach during compilation. If multiple valid approaches exist, select the one most consistent with the existing codebase and spec intent. Document the choice in the task's Context section.

## Codebase-Grounded Compilation

Read the actual files that tasks will reference or modify during compilation — not just compiling from the spec's claims about the codebase. This applies to files that already exist at compilation time. For greenfield tasks creating new files, interface contracts are derived from the spec.

When compiling interface contracts for existing files:
- **Read the referenced file** to determine the actual convention. If the spec says "spacebar input" but the InputHandler uses `event.key` returning `' '`, the task gets `' '`.
- **If the spec's claim doesn't match the code**, flag the mismatch. If the code is authoritative (existing convention), correct the task instruction to match the code. If the spec is authoritative (new design that intentionally changes the convention), present the mismatch to the user ("the spec says X but the code uses Y — which is correct?") and wait for resolution before continuing.
- **For brownfield work**, read existing test files to learn testing conventions, existing modules for import/export patterns, and existing configuration for environment requirements.
- **Compile every spec-identified impact into an explicit task.** When the spec's testing strategy, impact analysis, or dependency sections identify existing files that will be affected by the changes (tests requiring mock migration, assertions needing updates, callers requiring signature changes), create a task for each. Spec impact entries are mandatory work items, not informational context — if the spec says a file is affected, the breakdown must include a task that addresses it.

## Interface Contracts

When a task references files created or modified by other tasks, the task instructions must specify cross-task interface contracts. At minimum: import/export convention (default vs. named), module type (ESM/CJS), key string or enum conventions used by the referenced module, and any rendering or update-loop wiring patterns the task must follow. Extend this list with any additional cross-task assumptions specific to the project's technology stack — these are a floor, not an exhaustive set.

**Orchestrator tasks**: When a task modifies the orchestrator file (the file that wires all modules together), it is higher-risk and requires additional specification: an explicit wiring checklist stating what must be imported, what must be initialized, what must be updated per frame/tick, and what must be cleaned up. Orchestrator tasks are routed to Sonnet minimum (regardless of other sizing heuristics) and include the wiring checklist as a dedicated section in the task file.

## Sizing Constraints

File count is the sharpest predictor of agent success. Target these constraints for each task:

| Constraint | Target | Rationale |
|-----------|--------|-----------|
| Files modified per task | 1-2 | Sharp decline above 3 files; frontier models drop to ~11% at 10+ files |
| Lines changed per task | <55 | 11x difficulty scaling from easy (<10) to hard (55+) |
| Hunks per task | 1-6 | Moderate reliability zone |
| Independence | Full | Each task executes without reading other tasks or the full spec |

If a task exceeds these constraints, split it. If splitting creates artificial boundaries (e.g., a schema migration necessarily touching 4 files), document the justification in the task file.

### Interface Change Splits

When a task changes an interface (function signature, constructor, API contract), split the definition change from caller migration. The definition task modifies the interface. Caller migration tasks update call sites in batches of 4-5 files or 80 lines, whichever is reached first. Apply this split when 5 or more callers must change.

Migration batches that modify the same file must be assigned to sequential waves. Each migration test task verifies only that its batch's callers use the new interface — do not assert absence of the old interface until the final verification gate.

## Task File Structure

Each `task-NN-<description>.md` is the complete instruction set for one implementation agent. Include these 8 sections in order:

**1. Objective**
One sentence stating what this task produces. Not what it does — what it produces. Example: "Adds the `validateToken` function to `auth/tokens.go` that rejects expired JWTs."

**2. Context**
Written by you (the compiling agent) for the implementation agent. Comprehend and distill the relevant spec content — do not paste raw excerpts. Include:
- The behavioral intent being implemented
- Constraints or invariants the agent must respect
- Relevant existing code patterns to follow
- Nothing the agent can discover by reading the target files

Acceptable context: "Tokens expire after 15 minutes. Treat clock skew up to 30 seconds as valid. The existing `parseToken` function handles base64 decoding — call it, then check the `exp` claim."
Unacceptable context: "See the spec's Security Requirements section for token expiry rules."

**3. Instructions**
Step-by-step implementation instructions. Number each step. Each step is a concrete action with a clear completion condition. The agent must be able to execute every step without making a design choice. If a step requires judgment ("design the interface"), the task is underspecified — resolve in the spec before completing compilation.

Acceptable step: "Add a `validateToken(token string) (Claims, error)` function to `auth/tokens.go` after the `parseToken` function."
Unacceptable step: "Add a token validation function with appropriate error handling."

**4. Files to create/modify**
Explicit scope boundary. List each file with its path relative to the project root. The agent must not touch files outside this list.

**5. Test requirements**
For test tasks: list the new tests to write, specifying level (unit/integration/e2e), the behavior under test, and the expected assertion.
For implementation tasks: list existing tests to update (specify file, what changes, why). Reference the corresponding test task's test requirements.

**6. Acceptance criteria**
Verifiable conditions. Reference spec AC IDs (AC-01, AC-02, ...). For implementation tasks, the primary AC is: "the tests from the corresponding test task pass." Add any additional structural or behavioral criteria not captured by the tests.

**7. Model**
State `Haiku` or `Sonnet`. One word. See Model Routing section for the decision rule.

**8. Wave**
State the wave number. Example: `Wave 2`. Determines when this task executes relative to others.

### Task File Frontmatter

Task files use YAML frontmatter between `---` markers.

**Required fields (all tasks):**

- `id`: string. Task identifier matching `task-NN` format (e.g., `task-01`).
- `type`: `test` or `implementation`.
- `wave`: integer. Execution wave number.
- `covers`: list of `AC-NN` strings. Acceptance criteria this task satisfies.
- `completion_gate`: string. What proves this task is done.

At least one of `files_to_create` (list of paths) or `files_to_modify` (list of paths) must be present and non-empty.

**Additional fields for implementation tasks:**

- `test_tasks`: list of task ID strings referencing test tasks this implementation depends on.

### Frontmatter Examples

**Test task:**

```yaml
---
id: task-01
type: test
wave: 1
covers: [AC-01]
files_to_create:
  - tests/feature/test-alpha.sh
completion_gate: "tests compile and fail before implementation"
---
```

**Implementation task:**

```yaml
---
id: task-02
type: implementation
wave: 1
covers: [AC-01]
files_to_create:
  - src/alpha.py
test_tasks: [task-01]
completion_gate: "task-01 tests pass"
---
```

A task file does NOT contain:

- References to "read the spec for details" or "see the spec for context"
- Open design questions left for the implementation agent
- Multiple valid implementation approaches (choose one during compilation)
- Context from other tasks (each task is fully independent)

## Importability Verification

Before creating a test-only task, verify the target behavior is importable from the test environment. Read the source file and confirm the function or method is exported and callable.

When the behavior is embedded inside a non-importable function (module-level side effects, framework lifecycle method, orchestrator internals):

1. Check whether an existing test hook (`__e2e*`, harness helper) exposes the behavior.
2. If no hook exists, create an extraction or hook task in an earlier wave.
3. Add the extraction task as a dependency of the test task.

Do not create a test task that requires simulating a side effect from another module. If the test cannot call the production function that produces the behavior, the test task is not ready.

## Quantifier ACs

When an AC uses "all," "every," or plural nouns (e.g., "E2E tests use deterministic sync"), enumerate the specific instances in the codebase that match. Create a task for each instance, or explicitly document which instances are out of scope with justification in the task file.

Do not satisfy a quantifier AC with a single task that addresses a subset of instances.

## Test/Implementation Task Separation

For every code-modifying change, create two tasks: a test task and an implementation task.

**Test task**: Write or update tests that specify the expected behavior. Tests must compile and fail (or be skipped) before implementation begins. Read `fbk-docs/fbk-design-guidelines/test-authoring.md` when designing test task instructions.

**Implementation task**: Write the code that makes the test task's tests pass.

Within each wave, order test tasks before their corresponding implementation tasks. Test tasks and implementation tasks in the same wave may run in parallel with other pairs, but a test task must complete before its paired implementation task begins.

Name paired tasks consistently: `task-NN-test-<behavior>.md` and `task-MM-impl-<behavior>.md`.

## Task Manifest (task.json)

`task.json` is the machine-readable manifest for the task directory. The gate script and the `/implement` team lead both consume it. The `/breakdown` skill produces it; the `/implement` skill updates `status` and `summary` fields during execution.

### Schema

```json
{
  "spec": "ai-docs/<feature-name>/<feature-name>-spec.md",
  "category": "feature | corrective | testing-infrastructure",
  "tasks": [
    {
      "id": "task-NN",
      "title": "Human-readable task title",
      "file": "task-NN-<description>.md",
      "type": "test | implementation",
      "wave_id": 1,
      "dependencies": ["task-MM", "task-PP"],
      "covers": ["AC-01"],
      "model": "Haiku | Sonnet | Opus",
      "model_rationale": "Brief rationale for model choice",
      "status": "not_started",
      "summary": null,
      "note": null
    }
  ]
}
```

### Field definitions

| Field | Required | Description |
|---|---|---|
| `spec` | yes | Path to the spec this task set implements |
| `category` | no | Feature category: `feature` (default), `corrective`, or `testing-infrastructure`. Controls which gate invariants apply. Absent = `feature`. |
| `tasks` | yes | Array of task entries |
| `id` | yes | Task identifier matching `task-NN` format |
| `title` | yes | One-line description of what the task produces |
| `file` | yes | Filename of the task's `.md` file in the same directory |
| `type` | yes | `test` or `implementation` |
| `wave_id` | yes | Integer wave number for execution ordering |
| `dependencies` | yes | Array of task IDs that must complete before this task starts. Empty array if none |
| `covers` | yes | Array of `AC-NN` identifiers this task satisfies |
| `model` | yes | Model assignment: `Haiku`, `Sonnet`, or `Opus` |
| `model_rationale` | yes | Brief rationale for the model choice |
| `status` | yes | Current task status. `/breakdown` sets all to `not_started` |
| `summary` | no | Free-text implementation summary written by the executing agent. `null` until task completes |
| `note` | no | Annotation for `parked` or `superseded` tasks explaining the reason |

### Status values

| Status | Meaning | Set by |
|---|---|---|
| `not_started` | Initial state after breakdown | `/breakdown` |
| `in_progress` | Agent is actively working on this task | `/implement` on assignment |
| `complete` | Task verified done | `/implement` after verification |
| `tests_fail` | Implementation done but tests don't pass | `/implement` (triggers escalation) |
| `parked` | Needs human intervention (escalation cap exhausted) | `/implement` on escalation |
| `superseded` | Task no longer needed | Human or escalation |

### Invariants

The gate script validates these properties from task.json:

- Every spec AC ID appears in `covers` across at least one test task and one implementation task.
- No circular dependencies in the task DAG.
- Wave assignments respect dependency ordering — no task depends on a task in a later wave.
- Within each wave, test tasks are ordered before corresponding implementation tasks.
- Every `file` value references an existing task file in the same directory.
- No task may be unlinked from an AC. No AC may be uncovered.

## Model Routing

**Haiku**: Bounded single-file tasks. Clear instructions, no architectural judgment needed. Typical uses: adding a function, updating a config file, writing a test for a specific behavior.

**Sonnet**: Multi-file tasks, tasks requiring architectural judgment, or tasks touching integration points. When in doubt, choose Sonnet — the cost of under-routing (Haiku fails and requires escalation) exceeds the cost of over-routing.

## Ambiguity Handling

When you encounter a spec section that could be interpreted multiple ways, or a task where the instructions would require the implementation agent to make a design choice, stop.

Report the specific ambiguity: quote the ambiguous spec text, describe the two or more valid interpretations, and state the information needed to resolve it. Include which AC is affected. Do not choose an interpretation and continue. Compilation resumes only after the ambiguity is resolved in Stage 1 or Stage 2.

## Verification Gate

**Structural prerequisites** (deterministic — the `/breakdown` skill calls a gate script against `task.json`):

- `task.json` is valid JSON and conforms to the schema above
- Every spec AC ID appears in `covers` across at least one test task and one implementation task
- No circular dependencies in the dependency DAG
- Wave assignments respect dependency ordering
- Within each wave, test tasks are ordered before corresponding implementation tasks
- Every `file` references an existing task file in the directory
- File scope declarations don't conflict across tasks in the same wave
- No task exceeds the file count constraint without documented justification in that task file
- Every code-modifying task has a corresponding test task

**Semantic evaluation** (human or council review):

- Task instructions are unambiguous — implementation agent makes no design decisions
- Task context is sufficient — agent doesn't need to read the full spec
- Task boundaries are natural — splits don't create artificial seams
- Impacted existing tests from the spec's testing strategy are assigned to test tasks
- Test tasks cover behavioral intent of referenced ACs, not just surface assertions

## Transition

After producing `task.json` and all task files, run structural prerequisites against `task.json`. If they pass, offer: "The task breakdown covers all spec requirements across N tasks in M waves. Structural checks pass. Would you like to review individual tasks, invoke council for validation, or proceed to implementation?" If the user agrees, invoke `/implement <feature-name>`.
