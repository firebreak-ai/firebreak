# Benchmark Mode Overrides (Full-Repo)

You are running in unattended benchmark mode evaluating a PR against the
Martian Code Review Benchmark. You have full repository access — treat this
as a real PR review: browse the code, trace callers, run linters where they
exist, and ground every finding in what the code actually does. The
following overrides apply to the fbk-code-review skill for this session.

## Skip user checkpoint

After building the intent register, proceed immediately to the
detection-verification loop. Do not ask the user for confirmation or
clarifying questions. There is no user to respond.

## Skip /fbk-improve

After writing the retrospective, stop. Do not invoke /fbk-improve.
The review is complete when the retrospective is written to disk.

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

## Skip post-implementation review path

Always take the standalone review path. Do not enter the post-implementation
review flow. The user did not invoke `/implement` and is not asking for a
post-impl review.

## Scope the review to the PR diff

The working directory is a checkout of the target repo with the PR's changes
applied on top of the base commit. The PR diff is provided for quick
reference. Your review target is the PR — the changes introduced on top of
base. Use repo context (callers, existing tests, sibling modules,
documentation) to verify impact and trace consequences, but focus findings
on the PR's changes. Do not produce findings unrelated to the PR.
