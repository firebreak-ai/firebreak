---
id: task-27
type: implementation
wave: 3
covers: [AC-11]
files_to_modify:
  - assets/skills/fbk-code-review/SKILL.md
test_tasks: [task-13]
completion_gate: "bash tests/sdl-workflow/test-orchestrator-pipeline-integration.sh exits 0"
---

## Objective

Update the Detection-Verification Loop in SKILL.md to use the JSON pipeline: Detector produces JSON sightings, `pipeline.py run` validates and filters, Challenger receives and produces JSON, `pipeline.py to-markdown` converts for the review report. Preset defaults to `behavioral-only`, severity to `minor`.

## Context

`assets/skills/fbk-code-review/SKILL.md` (117 lines) orchestrates the code review. The Detection-Verification Loop section (currently lines 76-87) describes the iterative detection and verification flow. The current flow is markdown-based. The new flow uses JSON throughout with a single markdown conversion at the end.

All other sections in SKILL.md are unchanged: Entry and Path Routing, Source of Truth Handling, Agent Team, Review Report, Pre-Spawn Linter Execution, Intent Extraction, Post-Fix Verification, Broad-Scope Reviews, Stuck-Agent Recovery, Spec Conflict Detection, Retrospective.

## Instructions

Replace only the `## Detection-Verification Loop` section (lines 76-87 of the current file, from `## Detection-Verification Loop` up to but not including `## Post-Fix Verification`).

The Agent Team section (lines 25-31) already describes the Detector and Challenger agents. Update the Challenger description line to mention JSON:

Find: `- **Challenger** (`code-review-challenger`): Verifies or rejects sightings. Tools: Read, Grep, Glob.`
Replace with: `- **Challenger** (`code-review-challenger`): Verifies or rejects sightings using JSON verdict format. Tools: Read, Grep, Glob.`

Replace the Detection-Verification Loop section with:

```markdown
## Detection-Verification Loop

Resolve the active preset and severity threshold at the start of the review. Defaults: preset=`behavioral-only`, severity=`minor`. Both are overridable by user instruction.

Run the iterative detection and verification loop:

1. Spawn Detector with: target code file contents first, then linter output (if available), then intent register (from Intent Extraction), then source of truth + behavioral comparison instructions from `code-review-guide.md` + structural detection targets from `fbk-docs/fbk-design-guidelines/quality-detection.md` + the JSON sighting schema and type/severity definitions last. Instruct the Detector to tag each sighting with its detection source (`spec-ac`, `checklist`, `structural-target`, `intent`, or `linter`) and to output sightings as a JSON array.
2. Collect sightings as JSON.
3. Run `uv run assets/scripts/pipeline.py run --preset <preset> --min-severity <threshold>` to validate, domain-filter, and severity-filter the sightings in a single invocation. If >30% of sightings are rejected during validation, log a warning about prompt compliance.
4. Spawn Challenger with: target code file contents first, then the filtered JSON sightings to verify, then verification instructions + type/severity definitions + the type-severity validity matrix last. The Challenger receives and produces JSON — no format translation between agents.
5. Validate Challenger output: status and evidence fields present, matrix validation on any reclassified type-severity combinations.
6. Filter to `status: verified` or `verified-pending-execution`. Assign sequential finding IDs (F-01, F-02...).
7. Run `uv run assets/scripts/pipeline.py to-markdown` to convert verified findings to markdown once for the review report. Adjacent observations from the Challenger are rendered at the end of each finding and accumulated into the retrospective.
7a. After each verification round, append verified findings to the review report file.
8. When applying fixes for a verified finding, grep the same file and package for all instances of the identified pattern. Apply the fix to every instance.
9. Run additional rounds for weakened but unrejected sightings.
10. Terminate when a round produces no new sightings above `info` severity (or no sightings), or after a maximum of 5 rounds.

Only verified findings surface to the user. Rejected sightings are excluded. JSON is the working format throughout the pipeline. Markdown conversion happens once for the human-facing review report.
```

### Verification

After editing, confirm:
- `pipeline.py` appears in the Detection-Verification Loop section
- `uv run` appears in the Detection-Verification Loop section
- `JSON` appears in the Detection-Verification Loop section (multiple times)
- `behavioral-only` appears as the default preset
- `minor` appears as the default severity threshold
- The Stuck-Agent Recovery section (`## Stuck-Agent Recovery`) still exists and is unchanged
- The Broad-Scope Reviews section still exists and is unchanged

## Files to create/modify

Modify: `assets/skills/fbk-code-review/SKILL.md`

## Test requirements

Test task-13 validates: pipeline.py reference, uv run, JSON format, validate/run subcommand, domain-filter/preset, to-markdown, behavioral-only default, minor default, overridable, Challenger JSON, single markdown conversion, stuck-agent preservation.

## Acceptance criteria

- Detection-Verification Loop uses JSON throughout
- Detector produces JSON sightings
- `uv run pipeline.py run` validates, domain-filters, severity-filters
- Challenger receives filtered JSON sightings (not markdown)
- `uv run pipeline.py to-markdown` converts once for review report
- Default preset is `behavioral-only`, default severity is `minor`, both overridable
- Stuck-Agent Recovery section preserved
- All other sections unchanged

## Model

sonnet

## Wave

3
