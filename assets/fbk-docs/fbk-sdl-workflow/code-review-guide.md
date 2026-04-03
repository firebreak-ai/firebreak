# Code Review Guide

## Behavioral Comparison Methodology

Apply behavioral comparison to every code review: describe what the code does, then compare that behavior against the source of truth. The source of truth is the spec's acceptance criteria (ACs), a failure mode checklist, or the user-stated intent that drove the implementation. Start by observing the code's actual behavior, then verify whether that behavior aligns with the intended design. This framing prevents fixation on "bugs" and focuses on behavioral alignment.

**Do**: Describe what processOrder() does. Compare that behavior to AC-03.

**Don't**: Find bugs in processOrder().

### AC verification precision

When reviewing against spec acceptance criteria, verify each AC individually. Produce a separate sighting for each AC that the code does not satisfy. Do not batch multiple AC violations into a single sighting — each AC represents a distinct behavioral contract.

### Dead and disconnected infrastructure

Check for components that are constructed, initialized, or declared but never invoked in the application's runtime path. Dead infrastructure is reachable code that is simply never called — distinct from dead code (unreachable branches). Produce a `structural` type sighting for each instance.

## Sighting Format

Sightings are the Detector's internal output — observations of potential behavioral misalignments discovered during code inspection. Sightings are not user-facing; they feed the verification loop.

```
Sighting ID: S-NN
Location: file path, line range
Type: [behavioral | structural | test-integrity | fragile]
Severity: [critical | major | minor | info]
Origin: [introduced | pre-existing | unknown]
Detection source: [spec-ac | checklist | structural-target | linter]
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
- `linter` — triggered by project-native linter or static analysis tool output provided as supplementary context

## Finding Format

Verified findings are the Challenger's output and surface in conversation or reports. Each finding is a sighting that survived verification with evidence.

```
Finding ID: F-NN
Sighting: reference to the sighting ID (e.g., S-01)
Location: file path, line range
Type: [behavioral | structural | test-integrity | fragile]
Severity: [critical | major | minor | info]
Current behavior: confirmed behavioral description
Expected behavior: from spec AC or failure mode checklist
Source of truth: reference to the spec AC or checklist item
Evidence: Challenger's verification evidence — code path, test result, or behavioral proof
```

## Finding Classification

Classification uses two orthogonal axes. Canonical definitions are here; Detector, Challenger, and existing-code-review.md reference this section.

### Type axis

Assigned by the Detector. Describes what kind of issue was found.

- `behavioral` — code does something different from what its name, documentation, or spec says
- `structural` — code organization issue (duplication, dead code, dead infrastructure, bare literals)
- `test-integrity` — test provides less coverage than it appears to. Includes name-scope mismatch: test name claims broader scope than its assertions actually cover
- `fragile` — code works now but breaks under likely future changes (string-based dispatch, sentinel confusion, context bypass)

**Disambiguation rule:** When an issue fits multiple types, classify by the primary risk. If the code produces wrong results now, it is `behavioral`. If it produces correct results but will break under realistic changes, it is `fragile`. If it is a code organization problem with no correctness risk, it is `structural`. If a test provides less coverage than it appears to, it is `test-integrity`.

### Severity axis

Initial estimate by the Detector, validated or adjusted by the Challenger.

- `critical` — affects production correctness, security, or data integrity now
- `major` — significant risk under realistic conditions
- `minor` — should be addressed but not urgently
- `info` — informational; accurate observation but no action required

### Nit exclusion

Nits (naming, formatting, style, minor inconsistency with no behavioral or maintainability impact) are excluded from findings entirely. They do not receive type or severity classification. The Challenger rejects nit-level sightings from the findings list and counts them separately in the retrospective.

## Orchestration Protocol

The detection-verification loop operates iteratively across up to 5 rounds:

1. The orchestrator spawns the Detector with target code, source of truth, this guide's behavioral comparison instructions, and the structural detection targets from `fbk-docs/fbk-design-guidelines/quality-detection.md`
2. The Detector produces sightings
3. The orchestrator spawns the Challenger with the sightings, the target code, and instructions to verify or reject each sighting with evidence
4. The Challenger produces verified findings (with evidence) and rejections (with counter-evidence)
5. When applying fixes for a verified finding, grep the same file and package for all instances of the identified pattern. Apply the fix to every instance, not only the location cited in the sighting.
6. If sightings remain that were weakened but not rejected, run additional rounds
7. The loop terminates when a round produces no new sightings above `info` severity, or after a maximum of 5 rounds

Only verified findings surface to the user. Rejected sightings and the internal sighting data are not user-facing.

**Post-output steps**: After the loop terminates:
1. Append a findings summary to the feature retrospective (`ai-docs/<feature>/<feature>-retrospective.md`): finding count, rejection count, false positive rate, and each verified finding's ID, type, severity, and one-line description.
2. If a retrospective exists, offer: "Would you like to run `/fbk-improve` to analyze this retrospective for workflow improvements?"

## Source of Truth Handling

**Spec available**: Use the spec's acceptance criteria (ACs) and user-visible (UV) steps as the primary comparison target. These define the intended behavior against which the code is measured.

**No spec available**: Use the AI failure mode checklist (`fbk-docs/fbk-sdl-workflow/ai-failure-modes.md`) for structural issue detection. This checklist captures common failure patterns in agentic code when the feature spec is absent or incomplete. Supplement with the structural detection targets from `fbk-docs/fbk-design-guidelines/quality-detection.md` for framework-aware pattern detection.

**Post-implementation**: Use the feature spec that drove the implementation as the source of truth. When the spec is finalized after implementation (e.g., during recovery workflows), treat the spec as the authoritative baseline for behavioral comparison.

**Codebase-wide reviews**: When reviewing code that is not tied to a specific change set (e.g., a full codebase audit), default the origin field to `pre-existing` for all sightings. Override to `introduced` only when git history or PR context confirms the issue was created by a recent change.

## Retrospective Fields

Each code review run produces a retrospective capturing these fields:

- **Sighting counts**: total sightings generated, verified findings at termination, rejections, and nit count (raw count, not categorized by type — nits are excluded from the classification system). Include breakdown by detection source (spec-ac, checklist, structural-target, linter). For structural-type findings, include sub-categorization (duplication, dead code, dead infrastructure, bare literals, composition opacity)
- **Verification rounds**: how many detection/verification iterations before convergence; a measure of code opacity or reviewer uncertainty
- **Scope assessment**: code scope reviewed (files, modules, lines of code) relative to context usage (tokens, cache efficiency)
- **Context health**: round count, sightings-per-round trend, rejection rate per round, whether the hard cap (5 rounds) was reached
- **Tool usage**: which project-native tools (grep, file navigation, test runners) were available and used vs. grep/glob fallback
- **Finding quality**: false positive rate (findings the user dismissed), false negative signals (issues the user identified that the Detector missed), breakdown by origin (introduced vs. pre-existing)
