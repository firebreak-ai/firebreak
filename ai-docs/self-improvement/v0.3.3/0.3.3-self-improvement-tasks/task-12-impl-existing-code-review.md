---
id: task-12
type: implementation
wave: 2
covers: [AC-43, AC-44, AC-45, AC-46, AC-47, AC-48]
files_to_modify:
  - assets/skills/fbk-code-review/references/existing-code-review.md
test_tasks: [task-01]
completion_gate: "task-01 tests 15-20 pass"
---

## Objective

Adds 6 new review instructions to `existing-code-review.md` covering dual-path verification, sentinel value confusion, test-production string alignment, string-based error classification, dead infrastructure detection, and severity-ordered finding presentation.

## Context

The file is the standalone conversational review path reference. It has sections: Conversational Review Flow, User Interaction Model, Spec Co-Authoring, Spec Output, Scope Recognition, When Only Structural Issues Surface, and Retrospective. It has YAML frontmatter with `path: standalone`.

New instructions should be added as new sections before "Retrospective" (which should remain the last section). Each section uses a level-2 heading and imperative-voice instructions.

AC-48 (severity-ordered presentation) references the canonical severity values defined in `code-review-guide.md` (critical, major, minor, info). This instruction tells the reviewer to present findings ordered by severity and grouped by type.

## Instructions

1. Before the `## Retrospective` section, insert these 6 new sections:

```
## Dual-path verification

When the codebase has both a bulk path and an incremental path for the same operation (e.g., initial load vs. event-driven update, full sync vs. delta sync), verify that both paths populate the same state. Flag cases where the bulk path sets fields that the incremental path ignores, or vice versa, as this creates state divergence that manifests only under specific execution sequences.

## Sentinel value confusion

When reviewing guard conditions, verify that the code distinguishes "unset" or "missing" from "explicitly zero" (or empty string, or nil). Flag sentinel value confusion where a zero-like value serves as both a default and a valid domain value without a guard that differentiates the two cases.

## Test-production string alignment

When reviewing tests that assert on string values (error messages, status strings, format patterns), verify that the asserted strings actually exist in the production code being tested. Flag test assertions that reference string values absent from the production code — these are phantom assertions that pass trivially because the production code never produces the string being matched.

## String-based error classification

Flag error handling that branches on error message content (substring matching, prefix checking, string equality) instead of using typed errors, error codes, or sentinel values. String-based error classification is fragile — any change to the error message text silently breaks the dispatch logic.

## Dead infrastructure detection

Flag code that constructs, initializes, or declares components that are never invoked in the application's runtime path. Distinguish from dead code (unreachable branches): dead infrastructure is reachable code that is simply never called. Look for constructors or factory calls whose return values are assigned but never passed to any consumer, and for registered handlers with no route or event that triggers them.

## Finding presentation

Present verified findings ordered by severity (critical first, then major, minor, info), grouped by type within each severity tier. This ensures behavioral bugs with production impact are reviewed before structural debt.
```

## Files to create/modify

- `assets/skills/fbk-code-review/references/existing-code-review.md` (modify)

## Test requirements

Tests from task-01: Test 15 (dual-path keyword), Test 16 (sentinel value keyword), Test 17 (string alignment or test-production keyword), Test 18 (string-based error keyword), Test 19 (dead infrastructure keyword), Test 20 (severity or critical first keyword).

## Acceptance criteria

- AC-43: Dual-path verification instruction present.
- AC-44: Sentinel value confusion instruction present.
- AC-45: Test-production string alignment instruction present.
- AC-46: String-based error classification instruction present.
- AC-47: Dead infrastructure detection instruction present.
- AC-48: Finding presentation ordered by severity (critical first), grouped by type.

## Model

Haiku

## Wave

Wave 2
