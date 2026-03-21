---
id: T-05
type: implementation
wave: 2
covers: ["AC-03", "AC-04", "AC-12"]
files_to_create: ["home/dot-claude/docs/sdl-workflow/code-review-guide.md"]
files_to_modify: []
test_tasks: ["T-01"]
completion_gate: "T-01 tests 18-24 pass (guide exists, documents finding format with 8 fields, 4 category values, sighting format, behavioral comparison methodology, no defect-detection framing, all retrospective fields)"
---

## Objective

Creates `home/dot-claude/docs/sdl-workflow/code-review-guide.md` — the shared methodology reference for the code review skill, documenting behavioral comparison methodology, finding format, sighting format, orchestration protocol, and retrospective field requirements.

## Context

The code review guide is a shared reference document loaded by the `/code-review` skill and injected into Detector/Challenger agents at spawn time. It defines the methodology (behavioral comparison), the data formats (sightings and findings), the orchestration protocol (iterative detection-verification loop), and the retrospective schema.

This document is the authoritative source for the behavioral comparison framing. The spec requires "describe what this does, then compare" framing and prohibits "find bugs" as instructional framing. Any mention of "find bugs" must appear only in a negative example (paired with "don't" or "avoid").

The guide does not define agent personas — agents get their identity from their own definition files. The guide provides the shared methodology that the orchestrator injects into both agents.

T-01 validates this file with tests 18-24:
- File exists and is non-empty
- Contains all 8 finding format fields (case-insensitive): `finding id`, `sighting`, `location`, `category`, `current behavior`, `expected behavior`, `source of truth`, `evidence`
- Contains all 4 category values as exact strings: `semantic-drift`, `structural`, `test-integrity`, `nit`
- Contains all sighting format fields: `sighting id`, `location`, `category`, `observation`, `expected`, `source of truth`
- Contains `behavioral comparison` or `describe what` combined with `compare`
- Does not use `find bugs` except in lines also containing `don't`, `not`, `never`, or `avoid`
- Contains all 6 retrospective fields (case-insensitive): `sighting counts`, `verification rounds`, `scope assessment`, `context health`, `tool usage`, `finding quality`

## Instructions

1. Read `home/dot-claude/docs/sdl-workflow/corrective-workflow.md` to understand the existing doc conventions: direct-address imperatives, no preambles.

2. Create `home/dot-claude/docs/sdl-workflow/code-review-guide.md` with the sections below.

3. Start with heading: `# Code Review Guide`

4. **Section: Behavioral Comparison Methodology**

   Write 3-5 sentences explaining the behavioral comparison approach. Include the phrase "behavioral comparison" in the first sentence. Use this framing: describe what the code does, then compare that behavior against the source of truth (spec ACs, failure mode checklist, or user-stated intent).

   Include a "Do / Don't" example pair:
   - Do: `Describe what processOrder() does. Compare that behavior to AC-03.`
   - Don't: `Find bugs in processOrder().`

   This satisfies AC-04. The "Don't" line contains both "find bugs" and "Don't", which satisfies T-01 test 23's requirement that "find bugs" appears only on lines containing a negation word.

5. **Section: Sighting Format**

   Write a brief intro sentence: sightings are the Detector's output, not user-facing.

   Include the sighting template as a code block or structured list with these fields:
   - `Sighting ID`: format `S-NN` (S-01, S-02, ...)
   - `Location`: file path and line range
   - `Category`: one of `semantic-drift`, `structural`, `test-integrity`, `nit`
   - `Observation`: what the Detector observed — behavioral description
   - `Expected`: from spec AC or failure mode checklist
   - `Source of truth`: reference to the spec AC or checklist item

6. **Section: Finding Format**

   Write a brief intro sentence: verified findings are the Challenger's output and surface in conversation or reports.

   Include the finding template with these fields:
   - `Finding ID`: format `F-NN` (F-01, F-02, ...)
   - `Sighting`: reference to the sighting ID (e.g., S-01)
   - `Location`: file path and line range
   - `Category`: one of `semantic-drift`, `structural`, `test-integrity`, `nit`
   - `Current behavior`: confirmed behavioral description
   - `Expected behavior`: from spec AC or failure mode checklist
   - `Source of truth`: reference to the spec AC or checklist item
   - `Evidence`: Challenger's verification evidence — code path, test result, or behavioral proof

   After the template, add a line defining `nit`: "A `nit` is an observation that is accurate but functionally irrelevant — naming, formatting, style, or minor inconsistency that does not affect behavior or maintainability."

   This satisfies AC-03.

7. **Section: Category Values**

   List the four allowed category values with one-sentence definitions:
   - `semantic-drift` — Code behavior has diverged from the spec or original design intent
   - `structural` — Code organization issue (duplication, dead code, missing abstraction)
   - `test-integrity` — Test does not adequately validate the behavior it claims to verify
   - `nit` — Accurate observation that is functionally irrelevant

8. **Section: Orchestration Protocol**

   Describe the iterative detection-verification loop:

   1. The orchestrator spawns the Detector with target code, source of truth, and this guide's behavioral comparison instructions
   2. The Detector produces sightings
   3. The orchestrator spawns the Challenger with the sightings, the target code, and instructions to verify or reject each sighting with evidence
   4. The Challenger produces verified findings (with evidence) and rejections (with counter-evidence)
   5. If sightings remain that were weakened but not rejected, run additional rounds
   6. The loop terminates when a round produces only `nit`-category sightings (or no sightings), or after a maximum of 5 rounds

   State that only verified findings surface to the user. Rejected sightings and the internal sighting data are not user-facing.

9. **Section: Source of Truth Handling**

   Describe the three scenarios in 2-3 sentences each:
   - **Spec available**: Use the spec's ACs and UV steps as the primary comparison target
   - **No spec available**: Use the AI failure mode checklist (`docs/sdl-workflow/ai-failure-modes.md`) for structural issue detection
   - **Post-implementation**: Use the feature spec that drove the implementation as the source of truth

10. **Section: Retrospective Fields**

    State that each code review run produces a retrospective capturing these fields:
    - **Sighting counts**: total sightings, verified findings, rejections, nits at termination
    - **Verification rounds**: how many detection/verification iterations before convergence
    - **Scope assessment**: code scope reviewed (files, modules, lines) relative to context usage
    - **Context health**: round count, sightings-per-round trend, rejection rate per round, whether the hard cap was reached
    - **Tool usage**: which project-native tools were available and used vs. grep/glob fallback
    - **Finding quality**: false positive rate (findings the user dismissed), false negative signals (issues the user identified that the Detector missed)

    This satisfies AC-12.

11. End the file after the retrospective section. No summary or closing paragraph.

## Files to create/modify

- `home/dot-claude/docs/sdl-workflow/code-review-guide.md` (create)

## Test requirements

This is an implementation task. The corresponding test task T-01 validates:
- Test 18: File exists and is non-empty
- Test 19: Contains all 8 finding format field names
- Test 20: Contains all 4 category values
- Test 21: Contains all sighting format field names
- Test 22: Contains behavioral comparison methodology language
- Test 23: Does not use "find bugs" as instructional framing
- Test 24: Contains all 6 retrospective field names

## Acceptance criteria

- AC-03: The guide documents the complete finding schema (all 8 fields) and all 4 allowed category values
- AC-04: The guide uses behavioral comparison framing ("describe what this does, then compare") and does not use "find bugs" as instructional framing
- AC-12: The guide documents all 6 required retrospective fields

## Model

Haiku

## Wave

Wave 2
