---
name: fbk-testplan
description: >-
  Trial workflow in which the test files are the plan: turn a request into
  behavioural acceptance tests the operator approves, then build against them
  one test at a time. Use when the human invokes /fbk-testplan.
argument-hint: "[request, or path to a file holding it]"
# Source: the interview and test list are adapted from EXACT Coding's example-mapping and test-list skills (MIT) — https://github.com/marcoemrich/agentic_coding_lab — which build on Matt Wynne's Example Mapping.
---

Resolve `firebreak_dir`: use `${CLAUDE_PROJECT_DIR:-$PWD}/.claude` when it contains `fbk-scripts/testplan.py`, otherwise `$HOME/.claude`. Every `testplan.py` command below means `python3 $firebreak_dir/fbk-scripts/testplan.py <command>`, run from the project root. This trial supports pytest projects.

The plan for a change is its behavioural acceptance tests: pytest tests marked `@pytest.mark.planned` while the change is under way, and labelled `@pytest.mark.acceptance` once it is finished. The operator approves a printout the tool makes from those marks, so the tests are the only planning record.

Run `testplan.py status`.

- When it reports no plan, or a plan that is not approved, read `$firebreak_dir/fbk-docs/testplan/plan.md`.
- When it reports an approved plan done by one session, read `$firebreak_dir/fbk-docs/testplan/build-one-context.md`.
- When it reports an approved plan done by a subagent for each piece, read `$firebreak_dir/fbk-docs/testplan/build.md`.
