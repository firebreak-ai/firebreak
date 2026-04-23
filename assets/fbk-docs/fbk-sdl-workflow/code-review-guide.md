# Code Review Guide

## Behavioral Comparison Methodology

Apply behavioral comparison to every code review: describe what the code does, then compare that behavior against the source of truth. The source of truth is the spec's acceptance criteria (ACs), a failure mode checklist, or the user-stated intent that drove the implementation. Start by observing the code's actual behavior, then test whether that behavior matches the intended design; surface any divergence as a finding. This grounds every finding: a reported mistake traces back to a specific divergence — a failed AC, a failure-mode pattern from the checklist, an architectural mismatch, or a contradiction with user-stated intent.

**Do**: Describe what processOrder() does. Compare that behavior to AC-03.

**Don't**: Find bugs in processOrder().

### AC verification precision

When reviewing against spec acceptance criteria, verify each AC individually. Produce a separate sighting for each AC that the code does not satisfy. Do not batch multiple AC violations into a single sighting — each AC represents a distinct behavioral contract.

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
- `detection_source`: one of `spec-ac`, `checklist`, `structural-target`, `audit-pass`, `intent`, `linter` (default: `intent`)
- `source_of_truth_ref`: the specific reference compared against, e.g., "AC-03", "intent claim 4" (default: `""`)
- `pattern`: cross-cutting pattern label (default: `""`)
- `remediation`: one-line fix direction (default: `""`)

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

## Finding Classification

Classification uses two orthogonal axes. Canonical definitions are here; Detector, Challenger, and existing-code-review.md reference this section.

### Type axis

Code review is adversarial: compare what the code is supposed to do (the feature's purpose, the caller's assumption, the user-facing promise) against what it will actually do in production. You are looking for mistakes — places where the developer's mental model and the code diverge. AI-generated code adds a second pattern worth watching for: plausible-looking code that doesn't fit the architecture.

Find the mistake first; classify it second. The primary classification test is the ship decision — would you block or request changes on this PR, or would you merge and flag for follow-up?

- `behavioral` — you would not ship. The code does not do what it is supposed to do under conditions it will actually encounter. Always critical or major.

  Includes (illustrative, not exhaustive): wrong/missing output, crash, hang, data loss, broken feature end-to-end, security bypass, state that should update but doesn't, missing guarantees callers depend on, race conditions, silent failures, code paths that cannot execute as designed. "Conditions it will actually encounter" means concurrent execution, database and network errors, resource limits, and attacker-controlled inputs at trust boundaries — these are normal operation, not hypothetical future changes.

- `fragile` — you would ship but flag for follow-up. Correct today; structure invites a future bug. Behavioral takes precedence when both apply. Always major or minor.

- `structural` — you would ship; flag only on request. No path to user-visible failure. Harder to read or maintain than necessary. Always minor or info.

- `test-integrity` — a test passes but does not verify what it claims. The test name, docstring, or surrounding context implies coverage that the assertions do not provide. Always critical, major, or minor.

**Disambiguation rules:**
- A naming issue that causes a runtime collision or wrong dispatch is `behavioral` — follow the consequence, not the pattern.
- A bug in a test file's assertion logic is `test-integrity`, not `behavioral`.
- The most common misclassification is downgrading to `fragile` because the trigger is runtime state (DB error, concurrent execution, untested path) rather than a constructible input. Runtime conditions are normal operation — these findings are `behavioral`.

**Type-severity validity matrix:**

|  | critical | major | minor | info |
|--|----------|-------|-------|------|
| **behavioral** | valid | valid | invalid | invalid |
| **structural** | invalid | invalid | valid | valid |
| **test-integrity** | valid | valid | valid | invalid |
| **fragile** | invalid | valid | valid | invalid |

Invalid combinations are rejected by the parser at both Detector and Challenger stages.

### Severity axis

Initial estimate by the Detector, validated or adjusted by the Challenger. Severity is defined by observability.

- `critical` — the next user who exercises the changed code path hits the bug. No special input or timing required. *A human reviewer would block the PR.*
- `major` — a developer can write a test that demonstrates the failure. The triggering input is constructible but not the default path. *A human reviewer would request changes.*
- `minor` — observable only through code reading. No runtime failure can be demonstrated against the current codebase. *A human reviewer might leave a comment.*
- `info` — accurate observation with no recommended action. Excluded from finding count by default. *A human reviewer would not comment.*

### Nit exclusion

Nits (naming, formatting, style, minor inconsistency with no behavioral or maintainability impact) are excluded from findings entirely. They do not receive type or severity classification. The Challenger rejects nit-level sightings from the findings list and counts them separately in the retrospective.

## Orchestration Protocol

The detection-verification loop operates iteratively across up to 5 rounds:

0. Complete Intent Extraction before the first detection round. The intent register feeds into step 1's Detector spawn prompt.
1. The orchestrator spawns the Detector with target code file contents first, then linter output (if available), then intent register, then source of truth + this guide's behavioral comparison instructions + structural detection targets from `fbk-docs/fbk-design-guidelines/quality-detection.md` + the JSON schema and type/severity definitions last. Instruct the Detector to output sightings as a JSON array.
2. The Detector produces sightings as JSON.
3. The orchestrator runs `python3 "$HOME"/.claude/fbk-scripts/fbk.py pipeline run --preset <preset> --min-severity <threshold>` to validate, domain-filter, and severity-filter the sightings in a single invocation. Default preset is `behavioral-only`, default severity threshold is `minor`.
4. The orchestrator spawns the Challenger with target code file contents first, then the filtered JSON sightings, then verification instructions + type/severity definitions + the type-severity validity matrix last. The Challenger receives and produces JSON.
5. The orchestrator validates Challenger output (status, evidence fields, matrix validation on reclassified type-severity).
6. The orchestrator filters to `status: verified` or `verified-pending-execution`, assigns sequential finding IDs (F-01, F-02...).
7. The orchestrator runs `python3 "$HOME"/.claude/fbk-scripts/fbk.py pipeline to-markdown` to convert verified findings to markdown for the review report. JSON is the working format throughout; markdown conversion happens once for the human-facing report.
8. When applying fixes for a verified finding, grep the same file and package for all instances of the identified pattern. Apply the fix to every instance.
9. Run additional rounds for weakened but unrejected sightings.
10. The loop terminates when a round produces no new sightings above `info` severity, or after a maximum of 5 rounds.

Only verified findings surface to the user. Rejected sightings and internal sighting data are not user-facing.

**Post-output steps**: After the loop terminates:
1. Append a findings summary to the review report file: finding count, rejection count, false positive rate, and each verified finding's ID, type, severity, and one-line description.
2. If a retrospective exists, offer: "Would you like to run `/fbk-improve` to analyze this retrospective for workflow improvements?"

## Source of Truth Handling

**Spec available**: Use the spec's acceptance criteria (ACs) and user-visible (UV) steps as the primary comparison target. These define the intended behavior against which the code is measured.

**No spec available**: Use both the AI failure mode checklist (`fbk-docs/fbk-sdl-workflow/ai-failure-modes.md`) and the structural detection targets from `fbk-docs/fbk-design-guidelines/quality-detection.md` for structural issue detection.

**Intent register**: When an intent register has been extracted, include it as an additional comparison target for Detectors alongside specs or the checklist. Challengers verify intent-sourced sightings against the cited claim and the code — reject the sighting if the intent claim itself is inaccurate.

**Post-implementation**: Use the feature spec that drove the implementation as the source of truth. When the spec is finalized after implementation (e.g., during recovery workflows), treat the spec as the authoritative baseline for behavioral comparison.

**Codebase-wide reviews**: When reviewing code that is not tied to a specific change set (e.g., a full codebase audit), default the origin field to `pre-existing` for all sightings. Override to `introduced` only when git history or PR context confirms the issue was created by a recent change.

## Retrospective Fields

Each code review run produces a retrospective capturing these fields:

- **Sighting counts**: total sightings generated, verified findings at termination, rejections, and nit count (raw count, not categorized by type — nits are excluded from the classification system). Include breakdown by detection source (spec-ac, checklist, structural-target, audit-pass, linter). For structural-type findings, include sub-categorization (duplication, dead code, dead infrastructure, bare literals, composition opacity). For audit-pass findings, include sub-categorization by audit (concurrency, logic-inversion, test-integrity, cross-function-api)
- **Verification rounds**: how many detection/verification iterations before convergence; a measure of code opacity or reviewer uncertainty
- **Scope assessment**: code scope reviewed (files, modules, lines of code) relative to context usage (tokens, cache efficiency)
- **Context health**: round count, sightings-per-round trend, rejection rate per round, whether the hard cap (5 rounds) was reached
- **Tool usage**: which project-native tools (grep, file navigation, test runners) were available and used vs. grep/glob fallback
- **Finding quality**: false positive rate (findings the user dismissed), false negative signals (issues the user identified that the Detector missed), breakdown by origin (introduced vs. pre-existing)
- **Intent register**: claims extracted (count and sources), findings attributed to intent comparison (detection source: intent), intent claims invalidated during verification
