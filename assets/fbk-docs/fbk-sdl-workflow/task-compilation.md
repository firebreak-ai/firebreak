## Compilation Principle

Tasks are compiled executable specifications, not summaries. Every instruction must be explicit enough that the implementation agent makes no design decisions. Ambiguity in a task is a compilation error — if you cannot write clear instructions for a task, the spec is underspecified. Stop and report the ambiguity; do not guess. Resolution requires returning to the spec or design phase before compilation continues.

Choose one implementation approach during compilation. If multiple valid approaches exist, select the one most consistent with the existing codebase and spec intent. Document the choice in the task's Context section.

## Codebase-Grounded Compilation

Read the actual files that tasks will reference or modify during compilation — not just compiling from the spec's claims about the codebase. This applies to files that already exist at compilation time. For greenfield tasks creating new files, interface contracts are derived from the spec.

When compiling interface contracts for existing files:
- **Read the referenced file** to determine the actual convention. If the spec says "spacebar input" but the InputHandler uses `event.key` returning `' '`, the task gets `' '`.
- **If the spec's claim doesn't match the code**, flag the mismatch. If the code is authoritative (existing convention), correct the task instruction to match the code. If the spec is authoritative (new design that intentionally changes the convention), present the mismatch to the user ("the spec says X but the code uses Y — which is correct?") and wait for resolution before continuing.
- **For brownfield work**, read existing test files to learn testing conventions, existing modules for import/export patterns, and existing configuration for environment requirements.
- **Compile every spec-identified impact into an explicit task.** When the spec's testing strategy, impact analysis, or dependency sections identify existing files that will be affected by the changes (tests requiring mock migration, assertions needing updates, callers requiring signature changes), create a task for each. Spec impact entries are mandatory work items, not informational context — if the spec says a file is affected, the breakdown must include a task that addresses it.
- **When a task removes, renames, or changes the signature of any symbol** (struct field, function, type), grep the codebase for all call sites of that symbol. Do not rely solely on the spec's impact analysis. Create a task for each call site not already covered. Spec impact sections are a starting point, not a complete enumeration.
- **When a task instruction requires passing or using a specific value** (a context object, a reference, a constructed instance), verify that value is reachable in the target file at compilation time. If the value does not yet exist — because it must be threaded through constructors or other files not yet modified — create a prerequisite task that establishes it and add it as a dependency. State the intended final value in the task instruction, even when a prerequisite must deliver it first.
- **When a task names an agent persona or a built-in workflow, copy the real identifier exactly.** A task that tells an agent to spawn a persona must use that installed agent's `name:` field verbatim; a task that builds a workflow defined in code must use the harness's actual workflow vocabulary. Read the installed agent file or the harness reference to confirm the spelling — a near-miss name or an invented workflow term produces an artifact that looks right and silently fails to run.

## Preparatory Refactor Compilation

When the spec's "Module touch policy" declares a module as *refactor-then-extend*, compile two distinct tasks:

1. A preparatory refactor task that performs only the structural change named in the spec, with no new feature behavior. Assign it to an earlier wave than the dependent feature task.
2. The dependent feature task, listing the preparatory refactor task in its `dependencies` field.

The preparatory refactor task's acceptance criteria reference the existing tests for the module — the refactor must preserve current behavior, verified by the existing test suite passing unchanged. When the existing test suite does not cover the affected behavior, compile a characterization-test task in an even earlier wave to capture current behavior before the refactor begins.

## Slice-Identification-Then-Pairing

Task compilation follows a two-step process when the spec contains a `## Slices` section:

**Step 1 — Slice identification**: Read each `## Slices` entry in the spec and record its `test-discipline` value and `covers:` list before authoring any work units. For `contract-evolving` slices, also record the `retired-tests:` list.

**Step 2 — Per-slice pairing**: For each slice, author the test task + implementation task pair shaped by that slice's `test-discipline`. Route to the matching shape leaf under `fbk-sdl-workflow/slice-shapes/` via `slice-shapes.md`. Load only the leaf for the current slice.

### Shape routing

| Slice `test-discipline` | Shape | Routing rule |
|---|---|---|
| `new-contract` | New contract | Load `slice-shapes/new-contract.md`. Author test task declaring the new interface signature; implementation task copies it verbatim. |
| `contract-preserving` | Contract preserving | Load `slice-shapes/contract-preserving.md`. No new test task required; implementation task locks existing tests via `test-hash-gate`. |
| `contract-evolving` | Contract evolving | Load `slice-shapes/contract-evolving.md`. Include a `retired_tests` list in the implementation task's manifest entry. |
| `cross-cutting` | Cross-cutting | Load `slice-shapes/cross-cutting.md`. Test task only; no implementation task for this slice. |

When the spec has no `## Slices` section, skip this step and compile from ACs directly.

## Interface Contracts

When a task references files created or modified by other tasks, the task instructions must specify cross-task interface contracts. At minimum: import/export convention (default vs. named), module type (ESM/CJS), key string or enum conventions used by the referenced module, and any rendering or update-loop wiring patterns the task must follow. Extend this list with any additional cross-task assumptions specific to the project's technology stack — these are a floor, not an exhaustive set.

**New interfaces**: When a test task and implementation task share a function or interface that does not yet exist in the codebase at compilation time, state the exact signature in both task files. The test task declares the signature; the implementation task copies it verbatim. Do not leave the signature for either agent to infer from the spec — agents compiling independently from the same spec text will produce incompatible signatures.

**Nested field paths**: When a task reads or writes a field inside a structured record, quote the full path to that field — `bundle.persona`, not "the persona field." An agent given the short name guesses the nesting, and the one place a task leaves the path implicit is the place a test drifts from the schema. Restate the nesting in every task that touches the field.

**Shared test helpers**: When several test tasks call the same shared helper, pin the helper's exact signature in each of those task files. Independent test authors who are left to infer a helper's shape invent slightly different versions, and the drift only surfaces when their tasks link against each other. Stating the signature in full at every call site keeps the parallel authors aligned.

**Orchestrator tasks**: When a task modifies the orchestrator file (the file that wires all modules together), it is higher-risk and requires additional specification: an explicit wiring checklist stating what must be imported, what must be initialized, what must be updated per frame/tick, and what must be cleaned up. Orchestrator tasks are routed to Sonnet minimum (regardless of other sizing heuristics) and include the wiring checklist as a dedicated section in the task file.

## Cross-Task Contracts and Conventions

Anything shared across tasks — a package-wide rule, an invented interface, a shared symbol, a test double, an execution-order constraint — is pinned once at full precision and must reach every task it touches. A shared thing stated in only one task file is invisible to every other task's agent.

- **Package-wide rules reach every subject task.** When a rule applies to every task implementing a shared concern (every method logs unexpected errors, every row iteration checks the iteration's error signal), either centralize it behind a shared helper each consuming task is instructed to call, or restate it verbatim in the Instructions section of every task it applies to. A rule visible in only one of several sibling task files is a rule the other siblings will not follow.
- **Sibling consistency.** After drafting tasks — or steps within one task — that apply the same pattern at multiple sites, read the set side by side and confirm the prescribed error-wrapping, logging, and return-value handling match at every occurrence. When one site specifies a step (wrapping a sentinel, checking an error) that another omits, add the missing step or state the reason for the difference.
- **Exclusion lists derived from the complete outcome set.** When a task defines which outcomes are "expected" versus "unexpected" (for example, which errors are not logged at Error level), derive the list from the full enumeration of the operation's outcomes — every declared sentinel plus standard cross-cutting conditions such as cancellation and deadline expiry — not from the cases the spec's prose happens to mention.
- **Invented seams carry a signal inventory.** When an interface's shape is invented during compilation rather than dictated by the spec (an internal helper, a shared return type), first enumerate every task that will consume it and what data each needs from it. The pinned signature carries the union of those needs before either task file is written — an under-powered seam forces every consumer to work around a missing signal.
- **Shared invented symbols are defined once.** When two or more tasks construct or reference the same struct, type, or constant the spec does not define, pin its exact name and full shape once and copy it verbatim into every referencing task. Independent authors given only the concept invent incompatible shapes.
- **Test doubles pin behavior, not just signatures.** When a shared helper is a double standing in for a collaborator, state its observable behavior — return values per input, error and panic conditions, field casing, and whether it actually intercepts the method it exists to guard. A double that only matches the signature can satisfy the compiler while the test it supports passes vacuously.
- **Dependencies beyond file overlap.** Declared dependencies include every real ordering constraint: tasks sharing a compilation unit that will not build until all of them land, and orderings a project convention requires (one canonical implementation landing before its adopters), not only tasks touching the same file. Never rely on wave-number proximity to guarantee an order.

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

When a task removes a struct field or makes a field unexported, the implementing agent will fix all downstream compile errors in the same pass rather than leaving the build broken — downstream caller-migration tasks will be superseded. Either combine the field removal and all caller migrations into one task (document the file-scope justification), or mark each downstream caller task as `expected-superseded` in the task.json `note` field.

### Same-Wave Same-File Writes

When two or more tasks in the same wave would each edit the same file — for example, each task removing its own stub from a shared registry — they race against each other, and the parallel teammates have no way to coordinate. Detect this during compilation by checking whether any file appears in more than one task's scope within a wave.

When you find it, restructure so the shared edit happens once. Move the common change into a single prep task in an earlier wave (it does the whole shared edit), then leave each remaining task to create only its own file. This keeps every wave's file scopes disjoint, which is what lets the per-wave file-scope check stay meaningful.

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

**Per-site completion conditions**: When a task modifies multiple mutation sites (multiple locations in one file, or locations across two files), each site must have its own numbered step with a concrete completion condition. The agent verifies each site independently rather than treating the task as a single atomic change. Example: "Step 1: In `auth.go` line 45, replace X with Y. Completion: `grep -q 'Y' auth.go` succeeds. Step 2: In `auth_test.go` line 12, update the assertion. Completion: test compiles."

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

## Manual Operator-Verification Gate

Some behavior only runs end to end when the real wiring and real fixtures are in play — the glue between live components that no isolated test reaches. When automated tests can cover everything else and only this final glue needs a live run, a written manual procedure the operator follows is a legitimate completion gate. State it as concrete steps with an observable expected result.

Reach for this only when the genuine glue is what's under test. Do not write a test that mocks the very wiring it claims to verify — a test that stands in a fake for the connection it exists to check passes whether or not the real connection works, which is worse than an honest manual step.

## Quantifier ACs

When an AC uses "all," "every," or plural nouns (e.g., "E2E tests use deterministic sync"), enumerate the specific instances in the codebase that match. Create a task for each instance, or explicitly document which instances are out of scope with justification in the task file.

Do not satisfy a quantifier AC with a single task that addresses a subset of instances.

## Test/Implementation Task Separation

For every code-modifying change, create two tasks: a test task and an implementation task.

**Test task**: Write or update tests that specify the expected behavior. Tests must compile and fail (or be skipped) before implementation begins. Test tasks modify only test files. If the test requires a new exported function or accessor that does not yet exist, create an extraction task in an earlier wave and add it as a dependency. Read `fbk-docs/fbk-design-guidelines/test-authoring.md` when designing test task instructions.

**Implementation task**: Write the code that makes the test task's tests pass.

Within each wave, order test tasks before their corresponding implementation tasks. Test tasks and implementation tasks in the same wave may run in parallel with other pairs, but a test task must complete before its paired implementation task begins.

**E2E harness exception**: When a task creates an E2E test harness (test infrastructure setup + the tests that exercise it), combine the harness setup and its tests into a single task. Separating harness creation from harness-dependent tests creates an artificial boundary — the harness has no value without its tests, and the tests cannot compile without the harness. This exception applies only to E2E harness creation, not to standard unit or integration test tasks.

Name paired tasks consistently: `task-NN-test-<behavior>.md` and `task-MM-impl-<behavior>.md`.

## Task Manifest (task.json)

`task.json` is the machine-readable manifest for the task directory. The gate script and the `/fbk-implement` team lead both consume it. The `/fbk-breakdown` skill produces it; the `/fbk-implement` skill updates `status` and `summary` fields during execution.

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
| `not_started` | Initial state after breakdown | `/fbk-breakdown` |
| `in_progress` | Agent is actively working on this task | `/fbk-implement` on assignment |
| `complete` | Task verified done | `/fbk-implement` after verification |
| `tests_fail` | Implementation done but tests don't pass | `/fbk-implement` (triggers escalation) |
| `parked` | Needs human intervention (escalation cap exhausted) | `/fbk-implement` on escalation |
| `superseded` | Task no longer needed | Human or escalation |

### Invariants

The gate script validates these properties from task.json:

- Every spec AC ID appears in `covers` across at least one test task and one implementation task.
- No circular dependencies in the task DAG.
- Wave assignments respect dependency ordering — every declared dependency must be in a strictly earlier wave (lower `wave_id`). A dependency on a task in the same wave fails the gate.
- Within each wave, test tasks are ordered before corresponding implementation tasks.
- Every `file` value references an existing task file in the same directory.
- No task may be unlinked from an AC. No AC may be uncovered.

## Model Routing

**Haiku**: Bounded single-file tasks. Clear instructions, no architectural judgment needed. Typical uses: adding a function, updating a config file, writing a test for a specific behavior.

**Sonnet**: Multi-file tasks, tasks requiring architectural judgment, or tasks touching integration points. When in doubt, choose Sonnet — the cost of under-routing (Haiku fails and requires escalation) exceeds the cost of over-routing.

## Ambiguity Handling

When you encounter a spec section that could be interpreted multiple ways, two acceptance criteria (or an acceptance criterion and a stated design invariant) that prescribe mutually exclusive behavior for the same operation, or a task where the instructions would require the implementation agent to make a design choice, stop.

Report the specific ambiguity: quote the ambiguous spec text, describe the two or more valid interpretations, and state the information needed to resolve it. Include which AC is affected. Do not choose an interpretation and continue. Compilation resumes only after the ambiguity is resolved in the spec or design phase.

## Verification Gate

**Structural prerequisites** (deterministic — the `/fbk-breakdown` skill calls a gate script against `task.json`):

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

### Known Gate-Tooling Limitations

Two gaps in the current gate tooling are worth routing around until the tooling itself is repaired. These are stopgap notes, not the permanent answer — the real fix is to harden the gate.

- **The files-to-modify existence check can't tell a typo from a not-yet-created file.** The check confirms each listed file exists, but a file an earlier task is meant to create does not exist yet at check time, and that looks identical to a misspelled path. Double-check by hand that every `files_to_modify` path is either present now or genuinely produced by a declared earlier task.
- **The per-task reviewer gate lacks the cross-cutting exemption the breakdown gate has.** The breakdown gate knows a cross-cutting slice has a test task with no paired implementation task; the task reviewer does not, and may flag the missing pair as an error. Expect that false flag on cross-cutting work and confirm the pairing is intentional rather than reshaping the task to satisfy the reviewer.

## Transition

After producing `task.json` and all task files, run structural prerequisites against `task.json`. If they pass, offer: "The task breakdown covers all spec requirements across N tasks in M waves. Structural checks pass. Would you like to review individual tasks, invoke council for validation, or proceed to implementation?" If the user agrees, invoke `/fbk-implement <feature-name>`.
