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

1. Spawn Detector with modified files + feature spec ACs
2. Spawn Challenger to verify sightings
3. Loop until a round produces only `nit`-category sightings or no sightings, or after 5 rounds
4. Present verified findings to the user

## Output

Produce findings only — structured issues the implementation introduced or left unaddressed. The user triages findings through the existing corrective workflow. Do not produce a remediation specification. Do not write or iterate on specification sections with the user.
