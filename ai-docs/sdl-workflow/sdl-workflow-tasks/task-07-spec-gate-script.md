# Task 07: Create Spec Gate Validation Script

## Objective

Create a shell script that validates Stage 1 structural prerequisites for a spec artifact.

## Context

The `/spec` skill calls this script during the transition check. The script performs deterministic structural validation on the spec markdown file. It does NOT evaluate semantic quality — that is human judgment.

### What to validate

**Feature-level spec** (9 required sections):
- `## Problem`
- `## Goals` (or `## Goals / Non-goals`)
- `## User-facing behavior`
- `## Technical approach`
- `## Testing strategy`
- `## Documentation impact`
- `## Acceptance criteria`
- `## Open questions`
- `## Dependencies`

All sections must be present and non-empty (at least one non-whitespace line after the heading before the next heading or end of file).

**Open questions check**: The `## Open questions` section must be either:
- Empty (no content between this heading and the next heading / EOF), OR
- Every item has accompanying rationale text (not just a bare bullet point)

Heuristic for "deferred with rationale": each list item should contain more than just a question — look for additional text following the question on the same item or a sub-item.

**Project-level overview** (6 required sections):
- `## Vision`
- `## Architecture`
- `## Technology decisions`
- `## Feature map`
- `## Cross-cutting concerns`
- `## Open questions`

Additional check for project-level: `## Feature map` must contain at least one list item or sub-heading entry.

### Determining scope

The script must determine whether it's validating a feature-level spec or a project-level overview. Convention:
- Feature-level: file named `<name>-spec.md`
- Project-level: file named `<name>-overview.md`

### Input/output contract

- **Input**: Path to the spec file as the first positional argument. Called by the skill via: `"$HOME"/.claude/hooks/sdl-workflow/spec-gate.sh <path-to-spec>`
- **Exit 0**: All structural checks pass. Stdout: JSON summary of checks passed.
- **Exit 2**: One or more checks fail. Stderr: which checks failed and what is missing/invalid.

### Script location

`home/.claude/hooks/sdl-workflow/spec-gate.sh`

## Instructions

1. Create `home/.claude/hooks/sdl-workflow/spec-gate.sh`.
2. Use bash. The script should be portable (no exotic dependencies beyond standard Unix tools: grep, sed, awk).
3. Make the script executable (`chmod +x` equivalent — include a note in the file header or document this for the installer).
4. Implement these checks in order:

   a. **Argument check**: Verify the spec file path is provided and the file exists.
   b. **Scope detection**: Determine feature-level vs. project-level from the filename.
   c. **Section presence**: Check that all required `## ` headings exist in the file. Match by case-insensitive prefix: a required heading `## Problem` matches any line starting with `## Problem` (e.g., `## Problem Statement` also matches).
   d. **Section non-empty**: For each required heading, verify at least one non-whitespace content line exists between this heading and the next `## ` heading (or EOF).
   e. **Open questions**: Check the open questions section is empty or all items have rationale.
   f. **Feature map** (project-level only): Check for at least one list item under the feature map heading.

5. On failure: report ALL failures (don't stop at the first). The agent needs the complete picture.
6. On success: emit a brief JSON summary to stdout: `{"gate": "spec", "scope": "<feature|project>", "result": "pass"}`.
7. Keep the script focused and under 100 lines.

## Files to Create/Modify

- **Create**: `home/.claude/hooks/sdl-workflow/spec-gate.sh`

## Acceptance Criteria

- AC-11: Validates all Stage 1 structural prerequisites from the enforcement mapping
- AC-15: Follows authoring principles (for the script: clear, focused, one concern)

## Model

Sonnet

## Wave

1
