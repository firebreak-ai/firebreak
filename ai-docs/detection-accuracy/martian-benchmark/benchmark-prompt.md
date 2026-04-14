# Benchmark Mode Overrides

You are running in unattended benchmark mode evaluating a PR diff against the
Martian Code Review Benchmark. The following overrides apply to the
fbk-code-review skill for this session.

## Skip user checkpoint

After building the intent register, proceed immediately to the
detection-verification loop. Do not ask the user for confirmation or
clarifying questions. There is no user to respond.

## Skip /fbk-improve

After writing the retrospective, stop. Do not invoke /fbk-improve.
The review is complete when the retrospective is written to disk.

## Skip linter discovery

Do not search for or execute project-native linters. This is an isolated
diff review with no project tooling available. Record linter output as N/A
in the retrospective.

## Review report path

Create the review report at the path specified in the user prompt, not the
default date-based naming convention (fbk-code-review-YYYY-MM-DD-HHMM.md).

## Skip spec co-authoring

This is a detection-only benchmark run. Do not enter the spec co-authoring
flow. After the retrospective, stop.

## No conversational interaction

Do not ask clarifying questions. Do not pause for user input at any point.
When ambiguity exists in the intent register, use your best judgment and
note the ambiguity in the retrospective. Run the full detection-verification
loop to convergence or the 5-round cap, write the retrospective, and stop.

## Diff-only context

The only source material is the PR diff file specified in the user prompt.
There are no specs, no project documentation, and no repository to browse.
Use the AI failure mode checklist and structural detection targets as the
source of truth. Read the diff file contents using the Read tool.

