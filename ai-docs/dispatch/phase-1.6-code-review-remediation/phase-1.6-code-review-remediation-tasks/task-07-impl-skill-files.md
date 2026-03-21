---
id: T-07
type: implementation
wave: 4
covers: ["AC-01", "AC-02", "AC-05", "AC-06", "AC-07", "AC-09", "AC-10", "AC-11"]
files_to_create: ["home/dot-claude/skills/code-review/SKILL.md", "home/dot-claude/skills/code-review/references/existing-code-review.md", "home/dot-claude/skills/code-review/references/post-impl-review.md"]
files_to_modify: []
test_tasks: ["T-02", "T-03"]
completion_gate: "T-02 tests pass (skill structure validated) and T-03 integration tests pass (cross-file references consistent, detection-verification loop defined, cleanup mode handled)"
---

## Objective

Creates the `/code-review` skill entry point and both path-specific reference files: `home/dot-claude/skills/code-review/SKILL.md`, `home/dot-claude/skills/code-review/references/existing-code-review.md`, and `home/dot-claude/skills/code-review/references/post-impl-review.md`.

## Context

The `/code-review` skill has three files: the entry point (SKILL.md) that loads shared docs and routes to path-specific references, and two reference files for the conversational and post-implementation paths.

The skill follows the pattern established by existing skills (`/spec`, `/breakdown`) but uses the newer convention where skill-specific reference docs live in `references/` rather than in `docs/sdl-workflow/`. Shared methodology lives in `docs/sdl-workflow/` and is loaded by the skill.

The SKILL.md loads:
- `home/dot-claude/docs/sdl-workflow/code-review-guide.md` (behavioral comparison methodology, finding format, orchestration protocol)
- `home/dot-claude/docs/sdl-workflow/ai-failure-modes.md` (failure mode checklist for when no specs are available)

Then routes to:
- `references/existing-code-review.md` for standalone conversational review
- `references/post-impl-review.md` for post-implementation findings-only review

The skill spawns two agents: `code-review-detector` and `code-review-challenger`. It uses the Agent tool to spawn them. The skill's `allowed-tools` must include: Read, Grep, Glob, Write, Edit, Bash, Agent.

The skill creates 3 files which exceeds the 1-2 file target. Justification: the SKILL.md routes to its reference files — they are architecturally inseparable. Writing the entry point without the references it routes to would leave a broken skill.

**T-02 validates** (16 tests on skill structure):
- SKILL.md exists, has frontmatter with `description` and `allowed-tools` (including `Agent`)
- SKILL.md references both reference files by name
- SKILL.md loads shared code-review-guide and ai-failure-modes
- SKILL.md implements path routing between modes
- existing-code-review.md exists, contains conversational review guidance
- post-impl-review.md exists, contains findings-only guidance, excludes spec co-authoring

**T-03 validates** (17 integration tests):
- Skill defines the detection-verification loop
- Skill handles the no-spec scenario and references the checklist
- Cross-file reference consistency: skill references agents by correct name, guide by correct path, checklist by correct path
- All 7 context assets exist

## Instructions

1. Read the existing skill files for pattern reference:
   - `home/dot-claude/skills/spec/SKILL.md` for frontmatter convention (`description`, `argument-hint`)
   - `home/dot-claude/skills/breakdown/SKILL.md` for how skills load docs and route to sub-stages

2. Create the directory structure: `home/dot-claude/skills/code-review/references/`

3. Create `home/dot-claude/skills/code-review/SKILL.md`:

   Frontmatter:
   ```yaml
   ---
   description: >-
     Code review and remediation. Use when reviewing existing code, auditing
     for AI failure modes, performing post-implementation review, or
     co-authoring remediation specs from code review findings.
   argument-hint: "[target-path or feature-name]"
   allowed-tools: Read, Grep, Glob, Write, Edit, Bash, Agent
   ---
   ```

   Body sections:

   a. **Shared methodology loading**: "Read `home/dot-claude/docs/sdl-workflow/code-review-guide.md` for the behavioral comparison methodology, finding format, sighting format, orchestration protocol, and retrospective fields. Read `home/dot-claude/docs/sdl-workflow/ai-failure-modes.md` for the AI failure mode checklist used when no specs are available."

   b. **Entry and path routing**: "Determine the invocation context:
      - **Post-implementation review**: If invoked after `/implement` completion (the user accepted the stage-transition prompt), follow the post-implementation path in `references/post-impl-review.md`.
      - **Standalone review**: For all other invocations, follow the conversational review path in `references/existing-code-review.md`."

   c. **Source of truth handling**: "Check for existing specs — provided by the user or discovered in `ai-docs/`. If specs exist, use their ACs and UV steps as the comparison target. If no specs are available, use the AI failure mode checklist for structural issue detection. If no spec and no existing code context is provided, ask the user what to review."

   d. **Agent team**: "Spawn agents as a team with fresh context per invocation. Use two agents:
      - **Detector** (`code-review-detector`): Reads code, produces sightings. Tools: Read, Grep, Glob, Bash.
      - **Challenger** (`code-review-challenger`): Verifies or rejects sightings. Tools: Read, Grep, Glob.

      Inject the behavioral comparison methodology from `code-review-guide.md` and the relevant source of truth into each agent's spawn prompt. Agents do not inherit skills."

   e. **Detection-verification loop**: "Run the iterative detection and verification loop:
      1. Spawn Detector with target code scope + source of truth + behavioral comparison instructions
      2. Collect sightings
      3. Spawn Challenger with sightings + code + 'verify or reject each sighting with evidence'
      4. Collect verified findings and rejections
      5. Run additional rounds for weakened but unrejected sightings
      6. Terminate when a round produces only `nit`-category sightings (or no sightings), or after a maximum of 5 rounds

      Only verified findings surface to the user. Rejected sightings are excluded."

   f. **Broad-scope reviews**: "When the user requests a full codebase review rather than specific modules:
      1. Survey the project structure and identify reviewable units
      2. Propose a review order to the user
      3. Spawn fresh Detector/Challenger pairs per unit
      4. Accumulate verified findings across units, watching for cross-module patterns
      5. Checkpoint with the user after each unit"

   g. **Spec conflict detection**: "When multiple specs exist for the reviewed code, compare them for consistency. Surface conflicts between specs, or between specs and code, for user discussion during the conversational review."

   h. **Retrospective**: "After the review completes, produce a retrospective following the fields defined in `code-review-guide.md`."

4. Create `home/dot-claude/skills/code-review/references/existing-code-review.md`:

   a. **Conversational review flow**: "This path is a guided conversation. The user directs the review — defining scope, indicating focus areas, and providing design intent. Follow the user's direction."

   b. **User interaction model**: "Present verified findings as conversation evidence. The user discusses findings, provides corrections, and supplies design intent that the agent cannot infer from code alone. Example user inputs: 'Focus on the auth module', 'That duplication is actually the bigger problem', 'The caching layer bypass is the real issue.'"

   c. **Spec co-authoring**: "As the conversation progresses, draft spec sections from the findings and user-stated intent:
      - Problem section: emerges from confirmed findings
      - Goals section: emerges from the user's stated design intent
      - Technical approach: emerges from discussion of how things should work

      Periodically present draft spec sections for user confirmation before moving to the next area."

   d. **Spec output**: "The remediation spec uses the standard 9-section template defined in `home/dot-claude/docs/sdl-workflow/feature-spec-guide.md`. When complete, run the spec through `spec-gate.sh` to validate structure. The spec enters the existing SDL pipeline: `/spec-review` → `/breakdown` → `/implement`."

   e. **Scope recognition**: "A focused review produces a feature-level spec. A broad review may produce a project overview with child feature specs. Follow the same scope recognition used by the `/spec` skill."

   f. **When only structural issues surface**: "If the review reveals only structural issues and the user confirms no design intent is needed, stay lightweight — present findings against the AI failure mode checklist and let the user confirm or dismiss. If the user later provides design intent, transition naturally into spec co-authoring."

5. Create `home/dot-claude/skills/code-review/references/post-impl-review.md`:

   a. **Post-implementation review flow**: "This path is non-interactive. Run a structural quality check against the implementation output. Do not initiate a conversation or spec co-authoring."

   b. **Scope**: "Review the files modified by the implementation."

   c. **Source of truth**: "Use the feature spec that drove the implementation — its ACs and UV steps."

   d. **Execution**: "Run the full Detector/Challenger detection-verification loop without user involvement:
      1. Spawn Detector with modified files + feature spec ACs
      2. Spawn Challenger to verify sightings
      3. Loop until a round produces only `nit`-category sightings or no sightings, or after 5 rounds
      4. Present verified findings to the user"

   e. **Output**: "Produce findings only — structured issues the implementation introduced or left unaddressed. The user triages findings through the existing corrective workflow. Do not draft a remediation spec. Do not co-author spec sections."

## Files to create/modify

- `home/dot-claude/skills/code-review/SKILL.md` (create)
- `home/dot-claude/skills/code-review/references/existing-code-review.md` (create)
- `home/dot-claude/skills/code-review/references/post-impl-review.md` (create)

## Test requirements

This is an implementation task. The corresponding test tasks validate:

T-02 tests (skill structure):
- Tests 1-11: SKILL.md exists, frontmatter, allowed-tools with Agent, references both path files, loads shared docs, implements routing
- Tests 12-13: existing-code-review.md exists, contains conversational review guidance
- Tests 14-16: post-impl-review.md exists, contains findings-only guidance, excludes spec co-authoring

T-03 tests (integration):
- Tests 2-6: Skill defines detection-verification loop, agents define sighting/finding output, guide defines loop protocol
- Tests 7-9: existing-code-review reference includes spec drafting, spec-gate, 9-section template
- Tests 10-12: Skill handles no-spec scenario, references checklist, checklist has heuristics
- Tests 13-17: All 7 context assets exist, cross-file references consistent

## Acceptance criteria

- AC-01: The skill defines the detection-verification loop and spawns Detector/Challenger agents to produce confirmed findings
- AC-02: The skill excludes rejected sightings from user-facing output (the loop only surfaces verified findings)
- AC-05: The existing-code-review reference includes spec drafting guidance, spec-gate reference, and 9-section template reference
- AC-06: The skill routes to the AI failure mode checklist when no specs are provided
- AC-07: The skill routes between standalone (existing-code-review.md) and post-implementation (post-impl-review.md) modes
- AC-09: The detection-verification loop terminates on nit-only rounds or after 5 rounds maximum
- AC-10: The skill includes spec conflict detection for multi-spec scenarios
- AC-11: The skill handles broad-scope reviews by decomposing into reviewable units with fresh agent pairs per unit

## Model

Sonnet

## Wave

Wave 4
