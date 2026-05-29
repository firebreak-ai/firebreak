---
id: task-12
type: test
wave: 3
covers: [AC-08, AC-09, AC-11, AC-24]
files_to_create:
  - assets/fbk-scripts/tests/test_gates_code_review.py
completion_gate: "tests compile and fail before implementation"
---

## 1. Objective

Creates `assets/fbk-scripts/tests/test_gates_code_review.py`, a pytest unit test verifying that the code-review gate fails on missing/malformed quality-scan or test-review artifacts, fails on hash mismatches and shadow tests, passes when all are present and hashes intact, does not fail on a critical-severity quality finding or a drifted-but-unmodified locked test, and delegates hash/shadow checking to `test_hash.verify_manifest` (single-call delegation, per its `verify_manifest(feature_dir, manifest_path=None) -> list[dict]` signature).

## 2. Context

The `code_review.py` gate (new module, subcommand `code-review-gate`) runs after the bug-finding loop and checks:

1. **Quality-scan artifact present with a populated severity field**: `ai-docs/<feature>/quality-scan.md` exists with a `Severity:` field somewhere in the file. The gate only checks the artifact is present and carries the severity field — it does NOT enforce the ≤5-ranked-findings cap. That cap is the `fbk-quality-scan` SKILL's contract (AC-10, tested by task-03 and implemented by task-19), not a code-review-gate check.
2. **Test-review verdict artifact present**: `ai-docs/<feature>/test-review-final.md` exists (or matching the pattern `test-review-*.md` for the final-pass artifact).
3. **Hash + shadow-test check**: calls `test_hash.verify_manifest(feature_dir)` — imported from `fbk.gates.test_hash`. The signature is `verify_manifest(feature_dir, manifest_path=None) -> list[dict]`; calling it with the single `feature_dir` argument is valid (the manifest path defaults). Each returned item is a dict shaped `{"kind": ..., "path": ...}` where `kind` is one of `modified` / `unexpected` / `missing`. Branches on the structured discrepancy list:
   - Any item with `kind == "modified"` → gate FAILS
   - Any item with `kind == "unexpected"` → gate FAILS (shadow test)
   - Any item with `kind == "missing"` → surfaces as a finding, NOT a gate failure

The gate does NOT fail on:
- A `Severity: critical` value in the quality-scan (critical findings are for operator triage — AC-11)
- A drifted-but-unmodified locked test — this would appear as a `missing` discrepancy (the file path changed but content unchanged), which is a finding not a failure. Specifically: a test file with a new name but identical content would appear as `missing` (old path) + `unexpected` (new path). The "drifted-but-unmodified" concept in AC-11 refers to a test that has moved location or been renamed — surface it but don't fail.

The gate imports `verify_manifest` from `fbk.gates.test_hash`. After the test-hash restructure (Wave 2), `verify_manifest` returns `list[dict]` — the new structured return. The code-review gate test runs in Wave 3 because it needs the restructured `verify_manifest` to exist.

Import as: `from fbk.gates.code_review import validate_code_review` (following the existing gate convention). `code_review.py` does not yet exist — the import will fail before implementation.

No mocks for `verify_manifest`. Use real temp files so that `verify_manifest` runs against real filesystem state (matching the "no mocks" project convention). Build fixture manifests that reproduce the hash/shadow conditions using real files.

## 3. Instructions

1. Create `assets/fbk-scripts/tests/test_gates_code_review.py`.

2. Import:
   ```python
   import json, subprocess, sys, pytest, hashlib, datetime
   from pathlib import Path
   try:
       from fbk.gates.code_review import validate_code_review
   except ImportError:
       validate_code_review = None
   from fbk.gates.test_hash import create_manifest, verify_manifest
   ```
   `verify_manifest` is needed to build the "all hashes intact" positive case.

3. Write a `make_code_review_dir(tmp_path)` helper that creates:
   - `tmp_path / "ai-docs" / "sample" / "quality-scan.md"` — contains `Severity: minor` and a ranked list of 3 findings.
   - `tmp_path / "ai-docs" / "sample" / "test-review-final.md"` — contains the verdict line `accepted`.
   - A test file `tmp_path / "ai-docs" / "sample" / "tests" / "test_module.py"` — some content.
   - Calls `create_manifest(tmp_path / "ai-docs" / "sample")` to create `test-hashes.json` with the current test file's hash.
   Returns `(tmp_path, tmp_path / "ai-docs" / "sample")`.

4. Write class `TestCodeReviewGatePasses`:

   - `test_all_artifacts_present_and_hashes_intact_passes(tmp_path)`: build via helper. Call `validate_code_review(str(feature_dir))`. Assert `result["result"] == "pass"`.

5. Write class `TestMissingArtifacts`:

   - `test_missing_quality_scan_artifact_fails(tmp_path)`: build helper, delete `quality-scan.md`. Assert fail, failure mentions "quality-scan" or "quality scan".
   - `test_quality_scan_missing_severity_field_fails(tmp_path)`: write `quality-scan.md` without any `Severity:` line. Assert fail.
   - `test_missing_test_review_verdict_fails(tmp_path)`: delete `test-review-final.md` (or the matching test-review artifact). Assert fail.

6. Write class `TestHashMismatch`:

   - `test_modified_locked_test_fails(tmp_path)`: build helper (creates manifest). Modify `tests/test_module.py` content. Call `validate_code_review`. Assert fail, failure mentions "modified" or "hash mismatch".
   - `test_shadow_test_fails(tmp_path)`: build helper. Add a NEW file `tests/test_shadow.py` inside the same locked directory (creating an unexpected file). Call `validate_code_review`. Assert fail, failure mentions "shadow" or "unexpected".

7. Write class `TestNonFailingConditions`:

   - `test_critical_severity_quality_finding_does_not_fail(tmp_path)`: build helper. Replace `quality-scan.md` with one that has `Severity: critical` as the severity of a finding. Call `validate_code_review`. Assert `result["result"] == "pass"` (critical quality findings are for triage, not blocking).
   - `test_missing_kind_discrepancy_does_not_fail(tmp_path)`: simulate a `missing` discrepancy by building a manifest that lists a test file, then deleting that file (manifest says it should exist but it's gone — `kind: missing`). Call `validate_code_review`. Assert `result["result"] == "pass"` (missing surfaces as a finding only). Assert the result contains some record of the missing file (a `findings` or `warnings` key, or the failures list is empty but a findings list contains it).

8. Write class `TestVerifyManifestDelegation`:

   - `test_hash_check_delegates_to_verify_manifest(tmp_path, monkeypatch)` (AC-08): monkeypatch `fbk.gates.test_hash.verify_manifest` to record its call arguments and return `[]` (clean). Call `validate_code_review`. Assert `verify_manifest` was called exactly once. Assert the first positional argument was the feature dir path, and that the call is consistent with the pinned signature `verify_manifest(feature_dir, manifest_path=None)` — i.e. the gate calls it with the feature dir (one or two args, manifest path optional), not a hand-rolled second hash-comparison path. This covers AC-08: the gate's hash/shadow check must delegate to `test_hash.verify_manifest`, not a second path.

   Note: this is the only test that uses monkeypatch. The spec says "no mocks" for collaborators — this exception is permitted because it verifies the DELEGATION contract (that the gate uses the correct function rather than a second hash-comparison path), not the hash-comparison behavior itself. State this justification in the test docstring.

9. Write class `TestPathGuard`:

   - `test_missing_feature_dir_exits_2(tmp_path)`: call gate via subprocess with a non-existent path. Assert `returncode == 2`.
   - `test_binary_quality_scan_degrades_gracefully(tmp_path)`: write `quality-scan.md` as binary garbage bytes. Call gate. Assert no traceback; returncode is 0 or 2.

## 4. Files to create/modify

- `assets/fbk-scripts/tests/test_gates_code_review.py` (create)

## 5. Test requirements

All pytest unit tests except the two subprocess path-guard tests. No mocks except the single delegation-contract monkeypatch.

Failing before implementation: all tests that call `validate_code_review` (skipped via ImportError guard). This is in Wave 3 because the `verify_manifest` structured return (from the Wave 2 test-hash restructure) must exist for the real-file hash tests to work correctly.

## 6. Acceptance criteria

Covers AC-08 (the gate's hash/shadow check delegates to `test_hash.verify_manifest` — the single-call delegation contract — rather than a second hash-comparison path), AC-09 (quality-scan and test-review artifact checks — the gate verifies the quality-scan is present with a populated `Severity:` field, not the ≤5-findings cap), AC-11 (critical severity and drifted-but-unmodified do not fail; only modified or unexpected fails), AC-24 (exits 2 on missing path, degrades on binary). The ≤5-ranked-findings cap is the `fbk-quality-scan` SKILL's contract (AC-10), covered by task-03 and implemented by task-19 — not a code-review-gate check.

## 7. Model

Sonnet

## 8. Wave

Wave 3
