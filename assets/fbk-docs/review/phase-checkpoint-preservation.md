# Preservation test checkpoint review

The runtime sends this file's Decision, Check and Later deliverables sections to the preservation test checkpoint reviewer. Keep each item on one line.

## Decision

This is a preservation checkpoint: every requirement of the unit is review-only and its plan has no test task, so no test was written and the scoped tests are locked as they are. Do the scoped tests protect the code the unit will change?

## Check

- Read every scoped test against the accepted requirements and design, and read the production files the implementation tasks own, which are the code the unit will change; they are in required_files.
- Judge whether the scoped tests protect the code the unit will change: for each change the implementation tasks plan, identify a plausible regression in behavior already built and check that a scoped test would fail on it. Report each change the scoped tests leave unprotected, with the remedy of reopening breakdown to plan a test task for it.
- Read the saved output of every check in full; its files are in required_files. Every scoped test must have run and passed: a scoped test missing from the saved output, skipped, or failing is a blocker.

## Later deliverables

- implementation
- delivery documentation
