# Running and diagnosing tests

From the repository root, run the ordinary suites with:

```bash
python3 tests/run-tests.py
```

This requires Python 3, Bash, and `uv`. It runs Python behavior and integration
tests, reporting regressions,
the installer shell suites, and the lint check. It does not invoke live
Claude sessions.

Select a family when investigating a change:

```bash
python3 tests/run-tests.py --suite python
python3 tests/run-tests.py --suite installer
python3 tests/run-tests.py --suite lint
```

Each invocation creates a unique directory under `test-results/`. Use
`--output-dir PATH` to choose another parent. Concurrent runs do not share scratch
directories or overwrite earlier reports.

## Reading a failure

The terminal and `summary.md` group results by subsystem. Python cases and shell
assessment rows are labeled separately; their totals measure different things.
`failed` means a check contradicted its expectation. `error` means collection,
setup, execution, teardown, or reporting could not complete reliably. A missing
required tool or incomplete report is an error. Explicit skips remain visible.

Start with the failed source and diagnostic, then use the printed rerun command.
Python reruns select the original case, including parameters. Shell reruns execute
the whole source suite because rows may share setup.

The report directory contains:

- `summary.md`: the readable summary and failure reruns.
- `summary.json`: normalized results, subsystem counts, commands, and artifact paths.
- `junit.xml`: combined results for test-report viewers.
- `python/`: native pytest XML and complete stdout/stderr.
- `shell/`: each shell suite's complete stdout/stderr and invocation.
- `scratch/`: retained fixtures and command evidence when a run fails or errors.

Shell command evidence includes the command, working directory, exit status,
stdout, and stderr. Terminal excerpts are bounded; the files preserve full output.
Successful scratch is removed. Failed scratch remains until explicitly deleted.

CI uses the same runner, publishes the Markdown summary on the job, and uploads
reports including hidden fixture files. The Python job includes integration tests;
its name reflects that scope.

## Maintaining the suite

Keep tests beside their existing subsystem filename families; the runner owns the
report grouping. Current state-driven runtime cases are `test_workflow_*`.
Workflow, standalone pipeline, review, installation, and reporting have separate
groups. Installer behavior includes both Python confinement/migration cases and
shell lifecycle suites. Test identities stay stable for imports and mutation targets.

Use pytest's value comparisons and isolated fixtures. Include subprocess status,
stdout, and stderr when those explain a failure. Shell suites use
`tests/lib/test-report.sh` for scratch ownership and command evidence; keep their
actual assertions in the suite. The [reporting contract](testing-report-contract.md)
defines the interface and outcome rules.

## The lint check

The lint suite checks the Python that Firebreak installs: every file under
`assets/fbk-scripts` outside a `tests` folder, and `installer/merge-settings.py`.
It runs one pinned version of ruff with rules for likely bugs, complexity above 10,
catch-everything error handlers, subprocess calls with no failure check, and files
opened without being closed. `tests/lint/check.py` holds the rules and the scope.

Functions that were above the complexity limit when the check was set up are
recorded with their scores in `tests/lint/complexity-backlog.json`. The record only
tightens. A new function above the limit fails the check, and so does a recorded
function that scores higher. When a recorded function gets simpler, the check fails
until the lower score is written down:

```bash
python3 tests/lint/check.py --lower
```

Where a finding marks code that is right as it stands, the reason goes beside it:
`# noqa: <RULE> - <reason>`.

## Handoff behavior evaluation

The managed retrospective and improvement commands are covered by the workflow
tests, including public command integration. The
[observability validation](0.6.0/observability-validation.md) records their evidence
boundaries and an independent use of the revised improvement skill.

The dispatcher lifecycle test (`test_workflow_cli_lifecycle.py`) runs `fbk.py` as a subprocess through a full feature with a fake review host on PATH. The fake host asserts the invocation contract, and the test checks the persisted record from outside: file digests, the revision hash, lock and check evidence, review provenance, and agreement between close, status, and report. Live model evaluations are explicit opt-ins outside the repository; their results are integration evidence, not proof of source inspection or long-term attention reliability.
