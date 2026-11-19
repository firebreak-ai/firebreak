# Targeted review restoration, 2026-09-11

The user authorized preserving the legacy enumerated agentic failure searches,
restoring mechanism–trigger–caller-impact discipline, and correcting confirmation
rules that promoted pattern matches into findings. Review history remains excluded.

## Delivered behavior

Managed implementation review now loads five canonical guides from the Firebreak
installation: AI failure modes, detection audits, structural targets, security
targets, and the shared test-integrity audit. Their complete text is embedded in
the reviewer prompt, rather than relying on unavailable installed paths inside the
isolated project snapshot. The bundle is approximately 23 KB before JSON encoding;
it is supplied only for implementation. It is methodology, not project authority.
Guidance hashes participate in execution identity and are retained in the result.
Missing or empty installation guides stop before a model call with a repair action.
The project's source manifest and inspected-source requirements remain separate.

The Researcher must demonstrate mechanism, realistic trigger and caller impact in
existing fields. Structural/fragile claims instead identify concrete coupling and
a plausible maintenance change. The Challenger independently traces the values,
entry point, expectation and result. A consequential observed behavioral change
can remain established while its intent is referred to the operator.

All 16 AI failure-mode targets and the explicit audit families remain. Structural
searches also remain, with corrected qualification for mixed computation/I/O,
ambient state, private behavior, single-consumer abstractions, composition tests,
string assertions and discarded errors. Patterns direct investigation; the finding
needs the specific consequence. Sibling-fix confirmation now establishes a shared
obligation and broken mechanism instead of relying on absent asymmetry documentation.

Existing verdict statuses are retained. `verified-pending-execution` requires the
defect to be established through independent source reasoning; a necessary missing
runtime observation leaves it `unresolvable` with the deciding check. This is
consistent in the role, code guide, shared loop, test lens and code-review skill.
No stage, blanket execution requirement, or additional finding schema was added.

## Verification

Five new integration regressions exercise actual delivery into the isolated native
review adapter, canonical guide contents, recorded hashes, changed-guidance execution
identity, phase scoping, and failure before launch for missing/empty guides.

From `assets/fbk-scripts`:

```
uv run --no-project --with pytest --with pyyaml --with jsonschema python -m pytest tests -q
```

Result: **611 passed, one unchanged pre-existing failure** in
`test_workflow_code_review_pipeline.py::test_runtime_neutral_handoff_rejoins_full_records_for_material_declaration`
(reference under `finding`, full evidence under `finding_evidence`).

From the repository root:

```
PYTHONPATH=assets/fbk-scripts python3 -m pytest -q --import-mode=importlib benchmark/workflow/tests benchmark/remediation-review/tests benchmark/structural-review/tests benchmark/review-judgment/tests
```

Result: **75 passed, 24 subtests passed**. Importlib mode avoids the two benchmark
directories' same-named `test_evaluation.py` modules colliding during collection.
Scoped Ruff and whitespace checks passed. No live model calls or installation/trial
changes were made. These tests establish delivery and runtime integration, not
review quality, semantic enforcement, or the live token/time effect of the catalogs.
