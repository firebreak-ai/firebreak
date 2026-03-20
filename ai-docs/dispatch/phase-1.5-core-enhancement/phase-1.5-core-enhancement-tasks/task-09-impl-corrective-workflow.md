---
id: T-09
type: implementation
wave: 2
covers: ["AC-10"]
files_to_create: ["../../home/dot-claude/docs/sdl-workflow/corrective-workflow.md"]
test_tasks: ["T-02"]
completion_gate: "corrective-workflow.md exists with sections for full diagnostic mode, fast-track mode, escalation criteria, entry-point classification, and pipeline integration"
---

## Objective

Creates the corrective workflow documentation formalizing the diagnostic and fast-track workflows for bugfixes and quality issues.

## Context

The greenfield bug-fix cycle validated a diagnostic workflow distinct from the standard spec-driven flow. This workflow is currently documented only in the spec's Problem section and the harness patterns analysis. It needs to be formalized as a context asset that the `/spec` skill references when the developer is doing corrective work.

## Instructions

1. Create `home/dot-claude/docs/sdl-workflow/corrective-workflow.md` with these sections:

2. **Full diagnostic workflow** (new bug class, unknown root cause): 7 steps — write behavioral tests, run tests, root cause analysis by context-independent agents, spec the fix, review, breakdown and implement with `category: corrective`, retest (return to step 3 if failures remain).

3. **Fast-track** (known root cause, validated fix pattern): criteria (known root cause identical to reviewed fix, mechanical, validated test patterns, no design decisions) and process (identify → fix → test → verify, single agent, no pipeline ceremony).

4. **Escalation**: Fast-track to full diagnostic on first-attempt failure. Do not iterate within fast-track.

5. **Entry-point classification**: The `/spec` skill detects corrective language (bug report, failing tests, fix intent) and asks the developer to confirm the diagnostic workflow. The spec records `workflow: corrective` in frontmatter, propagating to breakdown (`category: corrective` in task.json) and gate (relaxed invariants). Fast-track bypasses `/spec` entirely.

6. **Pipeline integration**: Reference the test reviewer's Tier 2 corrective guidance (existing failing/passing test variants), the task reviewer gate's category support, and the baseline-snapshot's automatic exclusion of failing diagnostic tests.

## Files to create/modify

Create:
- `home/dot-claude/docs/sdl-workflow/corrective-workflow.md`

## Test requirements

Structural review: verify all required sections are present. Semi-manual: during brownfield testing, confirm `/spec` recognizes corrective intent and prompts for the diagnostic workflow.

## Acceptance criteria

AC-10: Corrective workflow documented with both modes, escalation criteria, entry-point classification, and pipeline integration points.

## Model

Sonnet

## Wave

Wave 2
