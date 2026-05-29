---
description: >-
  Task breakdown for implementation. Use when breaking down, decomposing,
  or planning implementation of a reviewed feature specification. Compiles
  specs into sized, wave-assigned task files.
argument-hint: "[feature-name]"
---

Read `.claude/fbk-docs/fbk-sdl-workflow/task-compilation.md` before proceeding.

If `$ARGUMENTS` is empty, ask for the feature name before continuing.

Set `FEATURE=$ARGUMENTS`. Locate inputs:
- Spec: `ai-docs/$FEATURE/$FEATURE-spec.md`
- Review: `ai-docs/$FEATURE/$FEATURE-review.md`
- Threat model (if present): `ai-docs/$FEATURE/$FEATURE-threat-model.md`

## Prerequisite probe (mid-pipeline entry)

When this skill is invoked directly (not chained from `/fbk-spec-review`), call the capability-entry prerequisite probe before proceeding:

```
fbk.precheck.check_prerequisites("breakdown", <feature_dir>)
```

If the spec artifact (`ai-docs/$FEATURE/$FEATURE-spec.md`) is missing, name that file explicitly and offer to run the upstream phase: "The spec file is missing — would you like me to run `/fbk-spec` to produce it?" This is non-blocking: never hard-block on a missing spec; always offer rather than halt.

Verify both the spec and review files exist. If either is missing, report which file is absent and stop.

Run the Stage 2 gate:
```
python3 "$HOME"/.claude/fbk-scripts/fbk.py review-gate \
  "ai-docs/$FEATURE/$FEATURE-review.md" \
  "<perspectives>" \
  ["ai-docs/$FEATURE/$FEATURE-threat-model.md"]
```
Read the `Perspectives:` metadata line from the first line of the review file and pass its value as the comma-separated perspectives string. If the gate fails, report which checks failed and offer to run `/fbk-spec-review $FEATURE`.

## Slice identification

Before authoring any work units, read the `## Slices` section of the spec. For each slice entry:

1. Record the slice name and its `test-discipline` value (one of: `new-contract`, `contract-preserving`, `contract-evolving`, `cross-cutting`).
2. Record the slice's contract pointer (the interface or behavior it owns).

Produce a slice list before continuing. This identification step completes first; per-slice authoring follows.

## Per-slice work-unit authoring

For each slice identified above, load the routing index at `.claude/fbk-docs/fbk-sdl-workflow/slice-shapes.md` and follow the routing rule for the slice's `test-discipline`:

| `test-discipline` | Shape leaf |
|---|---|
| `new-contract` | `slice-shapes/new-contract.md` |
| `contract-preserving` | `slice-shapes/contract-preserving.md` |
| `contract-evolving` | `slice-shapes/contract-evolving.md` |
| `cross-cutting` | `slice-shapes/cross-cutting.md` |

Load **only** the leaf for the current slice's discipline. Author the test task + implementation task pair for that slice according to the leaf's instructions. Process one slice at a time; do not load all four leaves at once.

**Bounce-back-to-spec**: If breakdown cannot write a work unit executable by a less-familiar agent — because the spec is too vague to produce unambiguous instructions — do not produce an oversized or open-ended task. Instead, name the specific gap ("spec section X does not define the error shape for Y") and emit a `BOUNCE-BACK:` marker in the task file:

```
<!-- BOUNCE-BACK: <specific spec gap that prevents unambiguous authoring> -->
```

The breakdown gate fails on any unresolved `BOUNCE-BACK:` marker (see task-30). Resolve by returning to spec.

## Test task agent

Invoke an Agent Teams teammate with independent context. The teammate receives only the spec file (`ai-docs/$FEATURE/$FEATURE-spec.md`). It does NOT receive the review document, threat model, or any other artifacts.

Load brownfield instructions from `.claude/fbk-docs/fbk-brownfield-breakdown.md` and include them in the teammate's prompt.

The teammate produces test tasks from the spec's testing strategy and acceptance criteria. One task per AC or logical test group. Each test task specifies: files to create, test framework conventions to follow, AC identifiers covered, and a completion gate (tests compile and fail before implementation).

Output: task files written to `ai-docs/$FEATURE/$FEATURE-tasks/` as `task-NN-test-<behavior>.md`. Task files use the frontmatter schema and body sections defined in `.claude/fbk-docs/fbk-sdl-workflow/task-compilation.md`.

## Implementation task agent

Invoke a second Agent Teams teammate with independent context, after the test task agent completes. The teammate receives the spec file AND the test task files produced by the test task agent. It receives the test task files as artifacts — not the test task agent's reasoning or conversation.

Load brownfield instructions from `.claude/fbk-docs/fbk-brownfield-breakdown.md` and include them in the teammate's prompt.

The teammate produces implementation tasks from the spec's technical approach and acceptance criteria. Each task specifies: files to create/modify (explicit paths — include all callers of any changed symbol, not only those the spec enumerates), AC identifiers satisfied, references to specific test tasks as completion gates, and constraints (file scope, no test modification).

Each implementation task references specific test task IDs. The completion gate for each implementation task is: the referenced tests pass.

Output: task files written to `ai-docs/$FEATURE/$FEATURE-tasks/` as `task-NN-impl-<behavior>.md`. Task files use the frontmatter schema and body sections defined in `.claude/fbk-docs/fbk-sdl-workflow/task-compilation.md`.

Wave N+1 tasks may reference files or behaviors produced by Wave N.

## Pre-lock test review

Before populating the test-lock manifest for any slice, invoke `fbk-test-review` in pre-lock mode over the full set of tests covering the changed module — including pre-existing tests that a contract-preserving slice will lock:

```
/fbk-test-review --mode pre-lock <module>
```

Only an `accepted` verdict from `fbk-test-review` triggers `test-hash-gate` manifest population. If the verdict is not `accepted`, report the findings and do not populate the lock manifest for that slice. The `test-hash-gate` command writes the manifest only after a confirmed `accepted` verdict.

## Task manifest assembly

After both agents complete, assemble `ai-docs/$FEATURE/$FEATURE-tasks/task.json` conforming to the task manifest schema in `.claude/fbk-docs/fbk-sdl-workflow/task-compilation.md`.

For each task file produced by the agents, create a task entry with:
- `id`: from the task file's frontmatter `id` field (matching `task-NN` format)
- `title`: one-line description of what the task produces
- `file`: the task file's filename
- `type`: from the task file's frontmatter `type` field
- `wave_id`: from the task file's frontmatter `wave` field
- `dependencies`: parsed from the task file's dependency references (empty array if none)
- `covers`: from the task file's frontmatter `covers` field
- `model`: model assignment based on the model routing rules in the task compilation guide
- `model_rationale`: brief rationale for the model choice
- `status`: `"not_started"` for all tasks
- `summary`: `null`
- `note`: `null`

Set the top-level `spec` field to `"ai-docs/$FEATURE/$FEATURE-spec.md"`.

## Task review

Run the task reviewer's deterministic layer: `python3 "$HOME"/.claude/fbk-scripts/fbk.py task-reviewer-gate "ai-docs/$FEATURE/$FEATURE-spec.md" "ai-docs/$FEATURE/$FEATURE-tasks"`. If it fails, report each failure. Return to the test task agent step with specific feedback.

Invoke the test reviewer agent (`test-reviewer`) as an Agent Teams teammate with checkpoint 2 context. Pass the spec file and the task files as artifacts. If it fails, add the test reviewer's findings to the feedback. Return to the test task agent step.

If both pass, proceed to the existing breakdown gate.

Run the Stage 3 gate:
```
python3 "$HOME"/.claude/fbk-scripts/fbk.py breakdown-gate \
  "ai-docs/$FEATURE/$FEATURE-spec.md" \
  "ai-docs/$FEATURE/$FEATURE-tasks"
```
If the gate fails, report each failure and fix before proceeding.

## Retrospective

After the breakdown gate passes, write the Stage 3 section to `ai-docs/$FEATURE/$FEATURE-retrospective.md` following `.claude/fbk-docs/fbk-sdl-workflow/retrospective-guide.md`. Create the file with the feature header if it does not exist. Read the file before writing to preserve existing content from prior stages.

## Transition

Summarize completed work before offering next steps: total task count, wave count, any council recommendation. Offer: review individual tasks, invoke council, or proceed.

Before invoking the next stage: confirm all artifacts are written to disk, then compact context. If the user agrees to proceed, invoke `/fbk-implement $FEATURE`.
