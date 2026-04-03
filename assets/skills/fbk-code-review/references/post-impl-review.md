---
path: post-implementation
---

## Post-Implementation Review Flow

This path is non-interactive. Run a structural quality check against the implementation output. Do not initiate a conversation or collaborative remediation planning.

## Scope

Review the files modified by the implementation.

## Source of Truth

Use the feature spec that drove the implementation — its ACs and UV steps.

## Execution

Run the full Detector/Challenger detection-verification loop without user involvement:

1. Run the project's full test suite and confirm zero failures before proceeding. Surface any failures to the user before starting detection.
2. Spawn Detector with modified files + feature spec ACs
3. Spawn Challenger to verify sightings
4. Loop until a round produces no new sightings above `info` severity or no sightings, or after 5 rounds
5. Present verified findings to the user

## Output

Produce findings only — structured issues the implementation introduced or left unaddressed. The user triages findings through the existing corrective workflow. Do not produce a remediation specification. Do not write or iterate on specification sections with the user.

## Retrospective

Append a findings summary to the feature retrospective (`ai-docs/<feature>/<feature>-retrospective.md`): finding count, rejection count, false positive rate, and each verified finding's ID, category, and one-line description.

After the findings summary is written, invoke `/fbk-improve <feature-name>` to analyze the retrospective for pipeline improvement opportunities.
