# Combined integration validation, 2026-09-09

The combined branch installs successfully and all current deterministic checks pass. It is **ready for a fresh bounded live-install trial**, with no claim that the current revision has already completed a live model lifecycle. This validation changed only the human-approved benchmark harness and fake-host setup plus these reports; it changed no production source, live project or global installation, and made no paid model calls.

The [machine-readable record](evidence/combined-validation-2026-09-09.json) identifies the source commit, installed workflow file hashes, commands and individual failing cases. The tested working tree contains uncommitted work: the commit alone does not identify the tested implementation.

## Current deterministic evidence

| Run | Result | Evidence |
| --- | --- | --- |
| Ordinary Python runner, from the repository root with its configured script cwd | 578 passed; no failures, errors or skips: 493 source cases, 61 workflow benchmark cases, 24 reporting cases | `/tmp/fbk-final-settled-python/run-t3qvrh5c/summary.json` |
| Additional deterministic remediation and structural evaluators | 8 passed; 24 subtests passed | `/tmp/fbk-final-settled-evaluators.log`, corresponding `.xml` |
| Fresh installed runtime, ten selected test modules | 98 passed | `/tmp/fbk-final-settled-installed-1rl19ope/test-result.json`, `tests.xml` |
| Installer shell suites | 66 assessment rows passed | `/tmp/fbk-final-settled-installer/run-418gs7hl/summary.json` |

The installer assessments are not Python test cases. The 98 installed cases overlap the source suite and do not replace it. The installed run imported `fbk` from the newly installed `.claude/fbk-scripts`, with copied test fixtures outside the source package. Every installed workflow Python file matched its source hash after validation. The actual installed CLI exposes `review-round run`, `remediation register-late` and `investigation conclude`; help checks passed. The installed snapshot includes the final provenance and late-registration changes, rather than the earlier host-fix snapshot.

Reproduce the ordinary suites with `python3 tests/run-tests.py --suite python` and `python3 tests/run-tests.py --suite installer`. Run the additional evaluators with `assets/fbk-scripts/.venv/bin/python -m pytest benchmark/remediation-review/tests benchmark/structural-review/tests -q`.

## Corrected integration gaps

The initial run reproduced seven known source failures: five acceptance-drift tests, the lifecycle whole-unit verification test and the telemetry verification-failure test. Their fixtures skipped reviewed task execution, so the new required-task gate correctly stopped before their intended assertions. With human approval, the owning agent migrated those setups to real task handoffs and retained their assertions. Two delegated native-worker mocks now supply realistic successful host envelopes; malformed, incomplete and truncated native output is rejected. Two older contributor helper fixtures also received approved migration to runtime execution. The final full run has no failures or exclusions.

The initial benchmark run had 16 setup errors because `test_live_smoke.py::completed` expected the old top-level native schema. The user approved updating its fake Claude to validate the final branch of `response.anyOf` and emit wrapped structured output. All original restricted-host, source-read, context and runtime-file exclusion assertions remain. Every false-completion mutation oracle remains unchanged.

The approved `live-smoke.py` migration now starts and finishes both the preparation task and its dependent implementation task through the real CLI. It validates actual four-test red/green output, submits task results for independent runtime checking, and retains the existing red classification, lock and whole-unit acceptance checks. All 19 smoke-harness tests pass. This deterministic fake-host lifecycle is useful integration evidence; it is not a new live model trial.

## Approved policies now implemented

- **Contributor provenance:** manual submissions are retained as supporting evidence and cannot satisfy required contributor completion. Runtime execution records bind the accepted response to its launch, contract and snapshot. An independent controlled-host CLI probe rejected a manual import and response tampering while permitting charged runtime completion.
- **Late registration:** explicit recovery ties an already-authorized fix to its original finding, pre-fix snapshot and existing scope. It records the missed registration, preserves the correct implementation and consumed budget, and still requires fresh independent verification. An independent probe rejected scope expansion and pre-fix snapshot tampering, created no approval event and completed only after real green/red checks through a controlled verifier.

These policies no longer await human decisions. Their independent probe summaries and source hashes are retained in the machine-readable evidence. The probes use deterministic host adapters and real isolated subprocess checks, not paid model verdicts.

## Rechecked host fixes

The native parser now rejects non-object structured output instead of converting arrays of key/value pairs into a dictionary. Six frozen regressions cover native structured output, a JSON result string and a managed response wrapper, including a duplicate findings field that previously erased a blocker. Valid object controls retain the finding and context. This was this evaluator's own fix; its test results are not independent review of the implementation.

Two peer fixes were independently rechecked with deterministic host adapters and real isolated Python processes:

- A failed continuation followed by retry receives retained investigation evidence, resolves it and does not repeat the experiment: `/tmp/fbk-retry-evidence-recheck-6qpx539m/.fbk/runtime/recheck.json`.
- SIGINT to the controller stops the already-started child before its delayed write. The round becomes inactive after cleanup and records 0.264875 seconds: `/tmp/fbk-interrupt-cleanup-recheck-fe6g6ajr/result.json`.

Both paths are also included in the combined and installed regression coverage. These probes do not establish semantic reliability of model conclusions.

## Live evidence boundary

Earlier native contributor execution completed successfully, including retained costs of failed schema launches. An actual fresh-verifier experiment produced behavior/regression artifacts but exhausted its 12-turn limit, so runtime verification remained unaccepted. A separate installed lifecycle trial accepted intent, then stopped at a spec host-output retry limit. Neither is a successful complete lifecycle for this combined revision; neither exhausted trial was rerun or extended here.

Older completed lifecycle evidence in `validation.md` retains its historical value, but predates the current runtime changes. The approved migrations and policy implementations are now covered by green deterministic checks. A fresh bounded installed lifecycle remains the next validation step; successful installation and fake-host completion do not guarantee model review quality, latency or freedom from new integration defects.
