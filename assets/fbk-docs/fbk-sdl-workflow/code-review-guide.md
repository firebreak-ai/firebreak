# Code Review Guide

## Behavioral Comparison Methodology

Apply behavioral comparison to every code review: describe what the code does, then compare that behavior against the source of truth. The source of truth is the spec's acceptance criteria (ACs), a failure mode checklist, or the user-stated intent that drove the implementation. Start by observing the code's actual behavior, then verify whether that behavior aligns with the intended design. This framing prevents fixation on "bugs" and focuses on behavioral alignment.

**Do**: Describe what processOrder() does. Compare that behavior to AC-03.

**Don't**: Find bugs in processOrder().

## Sighting Format

Sightings are the Detector's internal output — observations of potential behavioral misalignments discovered during code inspection. Sightings are not user-facing; they feed the verification loop.

```
Sighting ID: S-NN
Location: file path, line range
Category: [semantic-drift | structural | test-integrity | nit]
Origin: [introduced | pre-existing | unknown]
Detection source: [spec-ac | checklist | structural-target]
Observation: what the Detector observed — behavioral description
Expected: from spec AC or failure mode checklist
Source of truth: reference to the spec AC or checklist item
```

Origin values:
- `introduced` — issue was created by the changes under review (new code, new test, modified logic)
- `pre-existing` — issue existed before the changes under review; discovered incidentally during inspection
- `unknown` — insufficient evidence to determine; default when git history is unavailable

Detection source values:
- `spec-ac` — triggered by behavioral comparison against a spec acceptance criterion
- `checklist` — triggered by an AI failure mode checklist item
- `structural-target` — triggered by a quality-detection.md structural detection target

## Finding Format

Verified findings are the Challenger's output and surface in conversation or reports. Each finding is a sighting that survived verification with evidence.

```
Finding ID: F-NN
Sighting: reference to the sighting ID (e.g., S-01)
Location: file path, line range
Category: [semantic-drift | structural | test-integrity | nit]
Current behavior: confirmed behavioral description
Expected behavior: from spec AC or failure mode checklist
Source of truth: reference to the spec AC or checklist item
Evidence: Challenger's verification evidence — code path, test result, or behavioral proof
```

A `nit` is an observation that is accurate but functionally irrelevant — naming, formatting, style, or minor inconsistency that does not affect behavior or maintainability.

## Category Values

- `semantic-drift` — Code behavior has diverged from the spec or original design intent
- `structural` — Code organization issue (duplication, dead code, missing abstraction)
- `test-integrity` — Test does not adequately validate the behavior it claims to verify
- `nit` — Accurate observation that is functionally irrelevant

## Orchestration Protocol

The detection-verification loop operates iteratively across up to 5 rounds:

1. The orchestrator spawns the Detector with target code, source of truth, this guide's behavioral comparison instructions, and the structural detection targets from `fbk-docs/fbk-design-guidelines/quality-detection.md`
2. The Detector produces sightings
3. The orchestrator spawns the Challenger with the sightings, the target code, and instructions to verify or reject each sighting with evidence
4. The Challenger produces verified findings (with evidence) and rejections (with counter-evidence)
5. If sightings remain that were weakened but not rejected, run additional rounds
6. The loop terminates when a round produces only `nit`-category sightings (or no sightings), or after a maximum of 5 rounds

Only verified findings surface to the user. Rejected sightings and the internal sighting data are not user-facing.

## Source of Truth Handling

**Spec available**: Use the spec's acceptance criteria (ACs) and user-visible (UV) steps as the primary comparison target. These define the intended behavior against which the code is measured.

**No spec available**: Use the AI failure mode checklist (`fbk-docs/fbk-sdl-workflow/ai-failure-modes.md`) for structural issue detection. This checklist captures common failure patterns in agentic code when the feature spec is absent or incomplete.

**Post-implementation**: Use the feature spec that drove the implementation as the source of truth. When the spec is finalized after implementation (e.g., during recovery workflows), treat the spec as the authoritative baseline for behavioral comparison.

## Retrospective Fields

Each code review run produces a retrospective capturing these fields:

- **Sighting counts**: total sightings generated, verified findings at termination, rejections, and nits categorized by type. Include breakdown by detection source (spec-ac, checklist, structural-target)
- **Verification rounds**: how many detection/verification iterations before convergence; a measure of code opacity or reviewer uncertainty
- **Scope assessment**: code scope reviewed (files, modules, lines of code) relative to context usage (tokens, cache efficiency)
- **Context health**: round count, sightings-per-round trend, rejection rate per round, whether the hard cap (5 rounds) was reached
- **Tool usage**: which project-native tools (grep, file navigation, test runners) were available and used vs. grep/glob fallback
- **Finding quality**: false positive rate (findings the user dismissed), false negative signals (issues the user identified that the Detector missed)
