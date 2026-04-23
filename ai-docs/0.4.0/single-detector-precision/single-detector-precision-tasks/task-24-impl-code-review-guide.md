---
id: task-24
type: implementation
wave: 2
covers: [AC-08]
files_to_modify:
  - assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md
test_tasks: [task-03]
completion_gate: "bash tests/sdl-workflow/test-guide-precision-alignment.sh exits 0"
---

## Objective

Update the code review guide to contain consequence-based type definitions, observability-based severity definitions, JSON sighting schema reference, unified finding format with `reclassified_from`, type-severity validity matrix, and updated orchestration protocol referencing `pipeline.py`.

## Context

The code review guide at `assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md` (130 lines) is the canonical reference injected into both Detector and Challenger spawn prompts. Five sections need updating: Sighting Format, Finding Format, Finding Classification (type axis + severity axis), and Orchestration Protocol. Sections not listed here (Behavioral Comparison Methodology, AC verification precision, Nit exclusion, Source of Truth Handling, Retrospective Fields) are unchanged.

## Instructions

### Section: Sighting Format (currently lines 15-43)

Replace the current markdown template block and field descriptions with a JSON schema reference. Keep the section heading `## Sighting Format` and the introductory sentence. Replace the content with:

```markdown
## Sighting Format

Sightings are the Detector's output — observations of potential behavioral misalignments discovered during code inspection. Sightings are not user-facing; they feed the verification loop. The Detector produces sightings as a JSON array.

**Required-or-reject** (parser rejects the sighting if missing or empty):
- `id`: sequential, reassigned by orchestrator (S-01, S-02...)
- `title`: mechanism-first, min 10 characters
- `location`: object with `file` (string) and `start_line` (integer); optional `end_line`
- `type`: one of `behavioral`, `structural`, `test-integrity`, `fragile`
- `severity`: one of `critical`, `major`, `minor`, `info`
- `mechanism`: the exact code expression that misbehaves and what it does wrong, min 10 characters
- `consequence`: downstream impact of the mechanism, min 10 characters
- `evidence`: specific code path, line reference, or test case

**Required-with-defaults** (parser fills a default if missing):
- `origin`: one of `introduced`, `pre-existing`, `unknown` (default: `unknown`)
- `detection_source`: one of `spec-ac`, `checklist`, `structural-target`, `intent`, `linter` (default: `intent`)
- `source_of_truth_ref`: the specific reference compared against, e.g., "AC-03", "intent claim 4" (default: `""`)
- `pattern`: cross-cutting pattern label (default: `""`)
- `remediation`: one-line fix direction (default: `""`)
```

### Section: Finding Format (currently lines 44-59)

Replace the current markdown template with a description of the unified schema. Findings are sightings with Challenger verdict fields added:

```markdown
## Finding Format

Findings are sightings that survived Challenger verification. The Challenger adds verdict fields to the same JSON objects — no format translation.

**Challenger verdict fields:**
- `status`: one of `verified`, `verified-pending-execution`, `rejected`, `rejected-as-nit`
- `verification_evidence`: required when status is `verified` or `verified-pending-execution`, min 10 characters — the Challenger's own reasoning from the code
- `rejection_reason`: required when status is `rejected`, min 10 characters
- `reclassified_from`: object with `type` and `severity` when the Challenger changed either; empty object `{}` when no reclassification
- `adjacent_observations`: array of strings; empty array `[]` when none observed
- `finding_id`: assigned by orchestrator after verification (F-01, F-02...)

`verified-pending-execution` indicates the finding is credible from code reading but requires test execution for confirmation — used for test-integrity sightings. The orchestrator treats it like `verified` with a caveat marker. `rejected-as-nit` indicates the sighting is technically accurate but functionally irrelevant. The orchestrator treats it like `rejected` but counts nit rejections separately.
```

### Section: Finding Classification > Type axis (currently lines 63-74)

Replace the four type definitions with consequence-based definitions. Keep the section heading and intro sentence. Replace the bullet list:

```markdown
### Type axis

Assigned by the Detector. Classification is determined by runtime consequence, not pattern shape.

- `behavioral` — the code produces wrong output, data loss, crash, or security bypass for a **concrete, constructible input** using the codebase as it exists in the diff. Behavioral findings are always critical or major.
- `structural` — the code has no wrong output under any input, but is harder to maintain than necessary. Removing or renaming the code would not change any observable output. Structural findings are always minor or info.
- `test-integrity` — a test passes but does not verify what it claims. The test name, docstring, or surrounding context implies coverage that the assertions do not provide. Test-integrity findings are critical, major, or minor.
- `fragile` — the code produces correct output today, but will break under a **specific, plausible change** you can name. Fragile findings are always major or minor.

**Disambiguation rules:**
- If a naming issue causes a runtime collision or wrong dispatch, it is `behavioral` — follow the consequence, not the pattern.
- If the code under review is a test file, a bug in the test's assertion logic is `test-integrity`, not `behavioral`.
- To distinguish behavioral from fragile: can you construct a failing input using only the current code? Yes → behavioral. No, you need a hypothetical code change → fragile.

**Type-severity validity matrix:**

|  | critical | major | minor | info |
|--|----------|-------|-------|------|
| **behavioral** | valid | valid | invalid | invalid |
| **structural** | invalid | invalid | valid | valid |
| **test-integrity** | valid | valid | valid | invalid |
| **fragile** | invalid | valid | valid | invalid |

Invalid combinations are rejected by the parser at both Detector and Challenger stages.
```

### Section: Finding Classification > Severity axis (currently lines 76-83)

Replace the four severity definitions with observability-based definitions:

```markdown
### Severity axis

Initial estimate by the Detector, validated or adjusted by the Challenger. Severity is defined by observability.

- `critical` — the next user who exercises the changed code path hits the bug. No special input or timing required. *A human reviewer would block the PR.*
- `major` — a developer can write a test that demonstrates the failure. The triggering input is constructible but not the default path. *A human reviewer would request changes.*
- `minor` — observable only through code reading. No runtime failure can be demonstrated against the current codebase. *A human reviewer might leave a comment.*
- `info` — accurate observation with no recommended action. Excluded from finding count by default. *A human reviewer would not comment.*
```

### Section: Orchestration Protocol (currently lines 89-106)

Replace the orchestration steps with the JSON pipeline flow. Keep the section heading. Replace from step 0 through the end of the Post-output steps:

```markdown
## Orchestration Protocol

The detection-verification loop operates iteratively across up to 5 rounds:

0. Complete Intent Extraction before the first detection round. The intent register feeds into step 1's Detector spawn prompt.
1. The orchestrator spawns the Detector with target code file contents first, then linter output (if available), then intent register, then source of truth + this guide's behavioral comparison instructions + structural detection targets from `fbk-docs/fbk-design-guidelines/quality-detection.md` + the JSON schema and type/severity definitions last. Instruct the Detector to output sightings as a JSON array.
2. The Detector produces sightings as JSON.
3. The orchestrator runs `uv run pipeline.py run --preset <preset> --min-severity <threshold>` to validate, domain-filter, and severity-filter the sightings in a single invocation. Default preset is `behavioral-only`, default severity threshold is `minor`.
4. The orchestrator spawns the Challenger with target code file contents first, then the filtered JSON sightings, then verification instructions + type/severity definitions + the type-severity validity matrix last. The Challenger receives and produces JSON.
5. The orchestrator validates Challenger output (status, evidence fields, matrix validation on reclassified type-severity).
6. The orchestrator filters to `status: verified` or `verified-pending-execution`, assigns sequential finding IDs (F-01, F-02...).
7. The orchestrator runs `uv run pipeline.py to-markdown` to convert verified findings to markdown for the review report. JSON is the working format throughout; markdown conversion happens once for the human-facing report.
8. When applying fixes for a verified finding, grep the same file and package for all instances of the identified pattern. Apply the fix to every instance.
9. Run additional rounds for weakened but unrejected sightings.
10. The loop terminates when a round produces no new sightings above `info` severity, or after a maximum of 5 rounds.

Only verified findings surface to the user. Rejected sightings and internal sighting data are not user-facing.

**Post-output steps**: After the loop terminates:
1. Append a findings summary to the review report file: finding count, rejection count, false positive rate, and each verified finding's ID, type, severity, and one-line description.
2. If a retrospective exists, offer: "Would you like to run `/fbk-improve` to analyze this retrospective for workflow improvements?"
```

### Verification

After editing, confirm these conditions:
- The old phrase "does something different from what its name, documentation, or spec says" does NOT appear anywhere in the file
- The old phrase "significant risk under realistic conditions" does NOT appear anywhere in the file
- The words `mechanism`, `consequence`, `evidence` appear in the Sighting Format section
- `reclassified_from` and `verification_evidence` appear in the Finding Format section
- `pipeline.py` and `JSON` appear in the Orchestration Protocol section
- `matrix` or `validity matrix` appears in the Type axis section

## Files to create/modify

Modify: `assets/fbk-docs/fbk-sdl-workflow/code-review-guide.md`

## Test requirements

Test task-03 validates: 3 consequence-based type definitions, 3 observability severity definitions, JSON schema reference, `reclassified_from`, `verification_evidence`, validity matrix, orchestration `pipeline.py`, orchestration JSON, 2 negative tests for old language removal.

## Acceptance criteria

- Type definitions use consequence-based language for behavioral, structural, fragile
- Severity definitions use observability language for critical, major, minor
- JSON sighting schema documented with required and default fields
- Finding format documents Challenger verdict fields including `reclassified_from` and `verification_evidence`
- Type-severity validity matrix present
- Orchestration protocol references `pipeline.py` and JSON as working format
- Old pattern-shape type definitions and subjective severity definitions removed

## Model

sonnet

## Wave

2
