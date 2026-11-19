# 0.6.0 branch cleanup

The branch ships the managed `.fbk/` workflow and standalone review tools. Superseded execution paths and historical release bundles remain in git history.

## Retained surface

- Five phase skills, managed spec/council review entry points, and evidence-based improvement.
- Standalone code/test review, fresh-eyes, quality scan, documentation reconciliation, cross-model review, grilling, and context-asset authoring: 16 skills in total.
- Three agent definitions: improvement analyst, review researcher, and review challenger. Managed council responsibilities come from runtime prompts.
- The workflow package, standalone review pipeline, cross-model runner, and installer.

## Removed surface

- Eleven retired agent definitions, plus the legacy task/coherence review skills.
- Phase compatibility routes and guides; old gates, state engine, council session management, capture, harvesting, retrospective reporting, and task-completion hook.
- Unreachable authoring guidance, old review gate/report contracts, and a pipeline validation helper with only test callers.
- Tests and fixtures for those paths, obsolete existence/prose checks, unused shared fixtures, and the legacy shell-workflow CI job.
- Completed historical audit bundles, older release reports and their raw scoring archives, superseded glossary entries, and earlier decision-log sections. Current workflow evidence remains.

Standalone review guidance now writes advisory reports and uses the current unit format where needed. It does not provide managed acceptance or mutate test locks. Live review guidance moved from the retired SDL directory into `fbk-docs/review/`.

## Installation and verification

Upgrades remove unchanged hook/environment entries recorded in the previous ownership manifest before merging the new settings. Operator additions, including hooks sharing an owned group, and modified settings survive. The new manifest records current ownership. Existing file pruning removes retired shipped files.

The retained installer checks exercise real installed hook commands and verify that an upgrade removes a retired hook while preserving an operator hook. Local Markdown links, installed document references, internal imports, and unused production imports were checked. The ordinary suite uses deterministic review hosts; this cleanup did not run live model evaluations.

Use `python3 tests/run-tests.py` for current results. Installer verification can use an existing dependency cache with `UV_CACHE_DIR=<cache> UV_OFFLINE=1`; one initial online run encountered a PyPI timeout.
