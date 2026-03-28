# Installer Implementation Retrospective

## Factual Data

### Per-task results

| Task | Type | Model | Pass/Fail | Re-plans | Notes |
|------|------|-------|-----------|----------|-------|
| T-01 | test | Haiku | Pass | 0 | 6 fixture files |
| T-02 | test | Sonnet | Pass | 0 | 5 hook merge tests |
| T-03 | test | Sonnet | Pass | 0 | 6 env merge tests |
| T-07 | impl | Sonnet | Pass | 0 | merge-settings.py; updated test helpers for ---MANIFEST--- separator |
| T-04 | test | Sonnet | Pass | 0 | 10 install integration tests; test 3 had path-vs-content bug fixed by team lead |
| T-05 | test | Sonnet | Pass | 0 | 13 upgrade/uninstall tests |
| T-08 | impl | Sonnet | Pass | 0 | install.sh; 9/10 tests on first run (test bug, not impl bug) |
| T-06 | test | Sonnet | Pass | 0 | 16 e2e lifecycle tests; exposed manifest settings_entries preservation bug on upgrade |

### Task sizing accuracy

| Task | Declared files | Actual files modified |
|------|---------------|---------------------|
| T-01 | 6 | 6 |
| T-02 | 1 | 1 |
| T-03 | 1 | 1 |
| T-07 | 1 | 3 (merge-settings.py + both test files for separator format) |
| T-04 | 1 | 1 |
| T-05 | 1 | 1 |
| T-08 | 1 | 1 |
| T-06 | 1 | 1 |

T-07 exceeded declared scope: the ---MANIFEST--- separator format required updating both test files' helpers. This was a valid cross-task seam resolution.

### Model routing accuracy

- T-01 (Haiku): succeeded — correct routing for static fixture creation.
- All other tasks (Sonnet): succeeded — correct routing for complex logic.

### Verification gate pass rates

- Spec gate: 2 attempts (first failed on numbered headings)
- Review gate: 2 attempts (first failed on missing test subsections)
- Breakdown gate: 2 attempts (first failed on wave ordering — dependencies within same wave)
- Task reviewer gate: 1 attempt (pass)
- All per-wave verifications: pass on first run

### Test counts

| Suite | Tests |
|-------|-------|
| test-json-merge-hooks.sh | 5 |
| test-json-merge-env.sh | 6 |
| test-install.sh | 10 |
| test-upgrade-uninstall.sh | 13 |
| test-e2e-lifecycle.sh | 16 |
| **Total** | **50** |

## Upstream Traceability

- Stage 2 review: 1 iteration. 3 blocking findings, 12 important, 5 informational. All 3 blocking findings led to spec revisions (bash version, hook dedup, uninstall strategy). Builder pragmatism findings deferred rollback, checksum-on-uninstall, and orphan cleanup from v1.
- Stage 3 compilation: 2 attempts before gate passed (wave ordering fix).

## Failure Attribution

### Team lead fixes (not re-plans)

**test-install.sh test 3 bug**: Alpha's test used `grep -L "fbk-"` to check file contents instead of file paths. Team lead fixed directly — test logic error, not a task instruction gap.

**manifest settings_entries preservation on upgrade**: The e2e test (T-06) exposed that the upgrade path overwrote the manifest's `settings_entries` with empty entries when the merge found nothing new to add. Team lead fixed install.sh's `write_manifest()` to merge new records with existing manifest entries.

- **Root cause**: Compilation gap — the task instructions for T-08 did not specify that `write_manifest()` must preserve `settings_entries` from the existing manifest on upgrade. The spec covered this implicitly (the manifest records "every merged settings entry"), but the task file did not compile this into an explicit instruction for the upgrade path.

### T-07 test helper updates

Beta updated both test files' helpers to handle the ---MANIFEST--- output separator. This was a seam resolution between the test format expectations and the merge script's output format. Not a failure — the test tasks were written before the implementation decided on the separator format.

- **Root cause**: Expected seam mismatch. The test tasks (wave 2) and the implementation task (wave 3) were compiled independently. The separator format was specified in T-07's task file but not in T-02/T-03's task files since they were compiled first.

### Spec deviation: missing download path

The spec (AC-01, line 38) requires `curl -fsSL ... | bash` to work as a standalone one-liner — the script downloads the source tree from GitHub when run outside a local clone. The implementation only supports clone-and-run: `SOURCE_DIR` resolves to a relative path from the script's location within the repo (`$SCRIPT_DIR/../home/dot-claude`). There is no fetch/download step when the source tree is absent.

- **Root cause**: The spec describes two install paths ("bundled in the script for curl|bash, or in the local clone") but the task breakdown compiled only the local-clone path. Neither the test tasks nor the implementation task included a download step. The code review did not catch the omission because the test mocks provide a local `--source` directory, which bypasses the missing download logic entirely.
- **Impact**: The installer cannot be used via `curl | bash` as documented. Users must clone the full repo first.

## Deliverables

- `installer/install.sh` — bash 3.2+ installer script (install, upgrade, uninstall, dry-run)
- `installer/merge-settings.py` — Python 3 JSON merge script for additive hooks/env merging
- `tests/installer/` — 5 test suites, 50 tests total
- `tests/fixtures/installer/` — 6 test fixture files
