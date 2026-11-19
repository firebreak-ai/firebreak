# Test reporting contract

Keep current behavior tests and mutation targets discoverable. Group results by subsystem, preserve failure evidence, and report setup errors separately from failed behavior checks.

This contract defines the reporting interface for the local runner and shell suites. The [testing guide](testing.md) provides the everyday
commands and explains how to read failures.

## Grouping and entry points

Keep Python tests in `assets/fbk-scripts/tests`. Moving them changes imports and
fixture discovery. Assign reporting groups from paths and filename
families in one runner-owned mapping. Every collected test belongs to one group;
unmatched Python files remain visible under `python/other`.

Use `python/workflow`, `python/pipeline`, `python/installer`, `python/dispatcher`,
`python/review`, `python/other`, `reporting/infrastructure`, and `shell/installer`. Filename families are assigned in the runner; reporting
infrastructure uses the `python_cases` count unit. Keep each source filename and original pytest node ID or TAP
row description in the result. Shell rows may contain several checks or loop
variants: label their totals as assessment rows, separately from Python cases.

Provide `python3 tests/run-tests.py` from the repository root, with optional
`--suite python` or `--suite installer` selection and
`--output-dir PATH`. Repeated invocations create unique child directories even
when they share an output parent. The default runs the same two families as CI:

- Python: `uv run python -m pytest -q tests ../../tests/reporting`, with
  working directory `assets/fbk-scripts`, plus runner-owned JUnit and temporary
  directory arguments.
- Installer: `bash tests/installer/test-*.sh`, one expanded file per process.

Use the existing native outputs as inputs: pytest JUnit XML and shell TAP.
Preserve raw output alongside parsed results. Run all selected suites even when
one fails. CI can invoke these selections and upload the run directory on failure.

## Outcomes and diagnostics

| Outcome | Meaning | Evidence |
| --- | --- | --- |
| `passed` | A check executed and met its assertion | Native test result |
| `failed` | Executed behavior differed from its expectation | Assertion, expected and observed values where available, traceback or command output |
| `error` | Setup, collection, teardown, execution, or reporting could not complete reliably | Failing phase, command, exit status or exception, output |
| `skipped` | A deliberately unexecuted check | Explicit native skip and reason |

A missing required tool or broken fixture is an error. A test deliberately
checking a missing tool or a rejected product command can pass: the assertion
determines its outcome. A nonzero product command alone does not establish either
a failure or an error. Unexpected shell termination, TAP bailout, incomplete or
inconsistent TAP plan, missing JUnit, and zero discovery for a requested suite are
errors. Preserve already completed results when adding a suite-level error.
Keep pytest expected-failure details in the native report; an expected failure is
not an executed pass.

The runner exits `0` when all selected checks pass or explicitly skip, `1` when
there are assertion failures, and `2` when any execution/reporting error occurs.
Keep the original subprocess exit status in the report. Error takes precedence
over failure for the aggregate exit code; both remain visible in counts.

Print one summary per group with passed, failed, error, skipped, and duration,
then the overall result and report directory. For each failure or error, show its
source, actual diagnostic, artifact paths, and a shell-quoted rerun command with
the working directory. An assertion message without the observed result is
insufficient when the underlying command output was discarded.

Rerun Python cases using their original node IDs from `assets/fbk-scripts`, for
example `uv run python -m pytest -vv tests/test_workflow_commands.py`. Prefer the
exact failing node ID when available. Rerun a shell row through its entire source
suite, such as `bash tests/installer/test-install.sh` from the repository root;
rows often depend on earlier setup. Record argument arrays and working directory
as data as well as rendering a safely quoted command. Never execute a rendered
command through `eval`.

## Machine reports and artifacts

Write `summary.md`, `summary.json`, and `junit.xml` beneath the unique run directory.
Publish the Markdown summary on the CI job. Retain native
pytest XML, each shell suite's TAP/stdout and stderr, and command logs. The combined
JUnit uses subsystem names for suites, original test identities for cases,
`failure` for assertion failures, `error` for setup/execution failures, and
`skipped` with its reason. Preserve native diagnostics when converting or merging;
the JSON report links to full logs rather than repeating them. Shell durations
measure whole suites; the runner does not estimate durations for individual TAP rows.

The minimal JSON shape is:

```json
{
  "schema_version": 1,
  "status": "failed",
  "duration_seconds": 1.2,
  "counts": {"passed": 0, "failed": 1, "error": 0, "skipped": 0},
  "groups": [{
    "name": "shell/installer",
    "count_unit": "assessment_rows",
    "counts": {"passed": 0, "failed": 1, "error": 0, "skipped": 0}
  }],
  "results": [{
    "group": "shell/installer",
    "source": "tests/installer/test-install.sh",
    "name": "fresh install creates fbk-prefixed files in target",
    "status": "failed",
    "diagnostic": "Expected installed prompt; file missing",
    "cwd": "/checkout",
    "argv": ["bash", "tests/installer/test-install.sh"],
    "exit_code": 1,
    "artifacts": ["shell/installer/test-install.stdout.log"]
  }]
}
```

Top-level counts combine reported records; group count units explain their limits.
Use `python_cases` for Python groups. `exit_code` is the originating suite process
status, not an assertion status. Artifact paths are relative to the report
directory when copied there; retained external paths are absolute. Additional
fields may retain native details. The runner owns normalization; shell suites
need not implement JSON or XML serializers.

Create isolated scratch directories for each run and shell suite. Put fixture
directories beneath that suite's scratch root, including those created inside
command substitutions. Pytest receives a unique `--basetemp`; use its existing
fixtures. Successful scratch data is disposable; keep final reports. Failed and
errored runs retain command logs and scratch fixtures, with their locations in
the report. Preserve interruption evidence where the process can handle the
signal. A later run must never clear an earlier failed run's directory.

## Shared shell helper

Implement `tests/lib/test-report.sh`, sourced after existing harness definitions
and before the first fixture allocation. Preserve existing assertion functions,
TAP counters, and plans. Change each `not_ok` function to call `fbk_diag` with its
available failure details. Adopt this small API:

| Function or variable | Contract |
| --- | --- |
| `fbk_test_init "$0"` | Resolve the suite path, create a unique `FBK_TEST_TMP` beneath `FBK_REPORT_DIR` (default `/tmp`), export `TMPDIR` beneath it, and install the EXIT handler. |
| `FBK_REPORT_DIR` | Optional artifact parent supplied by the caller; the unified runner supplies a directory beneath its unique run directory. Each suite creates its own unique child. |
| `FBK_TEST_TMP` | Absolute suite scratch directory; fixture and command evidence survive failures here. |
| `fbk_run "label" command args...` | Save cwd, quoted argv, stdout, stderr, and actual exit status in a unique command directory; replay stdout/stderr to their original streams; return the command status unchanged. |
| `fbk_diag "reason" ["expected" "actual"]` | Emit TAP comments with failure details, command evidence paths, and the exact suite rerun command. |
| `fbk_test_finish EXIT_STATUS` | Called by the EXIT handler; retain scratch on nonzero status or positive `FAIL`, otherwise remove scratch. Preserve setup-error status and force failure when `FAIL` is positive. Nonzero exit without an assertion failure is an execution error. |

Allocate command directories with `mktemp`, so calls inside command substitutions
cannot collide or lose evidence through subshell-local counters. Diagnostic lookup
must use files, not only a variable assigned inside `fbk_run`. If several commands
contribute to a check, retain all of them and identify their labels. Raw output
stays in files; only TAP comment-prefixed diagnostics enter the TAP stream.

Replace existing cleanup traps when adopting the helper. Fold required non-file
cleanup into the suite's exit handling without deleting failed fixtures. Source
and initialize before `mktemp` calls; merely installing a new trap after setup
leaves earlier fixtures outside retention. Convert discarded product output to
`fbk_run` capture. Output-sensitive tests can continue capturing the replayed
streams; use conditional execution where `set -e` would terminate an intentional
negative test. Do not use `fbk_run` as a new assertion engine.

## Validation of reporting changes

Exercise real passing and deliberately failing commands through the helper and
runner. Verify preserved output, original exit status, accurate outcome counts,
usable rerun commands, and retained failure fixtures. Exercise one setup error,
explicit skip, and concurrent runs to check isolation. Use small synthetic runner
inputs where needed; validate semantic fields and artifacts instead of exact
summary wording. Keep existing behavioral assertions unchanged. A report that looks successful while checks failed, failed to
start, or were never discovered is a reporting defect.
