---
id: task-07
type: test
wave: 2
covers: [AC-07]
files_to_modify:
  - assets/fbk-scripts/tests/test_gates_test_hash.py
completion_gate: "tests compile and fail before implementation"
---

## 1. Objective

Modifies `assets/fbk-scripts/tests/test_gates_test_hash.py` to replace the existing flat-map assertions with per-entry-object assertions and to add tests for list-driven lock mode, shadow-test detection, and the scoped-exclusion negative case.

## 2. Context

The current `test_gates_test_hash.py` imports `compute_hashes`, `create_manifest`, `verify_manifest` from `fbk.gates.test_hash`. After the test-lock-manifest-restructure slice implements the schema change, the per-file values in `test-hashes.json` change from bare hex strings to objects:

```json
{
  "sha256": "<64-char hex>",
  "slice": "<slice-name>",
  "test-discipline": "<mode>"
}
```

The existing tests assert `len(hash_value) == 64` and treat the value as a string — these assertions break after the schema change. The spec classifies this as contract-evolving: the old tests must be replaced, not merely extended.

Interface contract #4 pins the new `verify_manifest` return type:
```python
verify_manifest(feature_dir) -> list[dict]
```
Where each dict is `{"kind": "modified" | "unexpected" | "missing", "path": "<relpath>"}`. An empty list means clean. The old signature returned a string (`"pass"` or an error string). The current tests assert `result == "pass"` and `"MODIFIED" in result` — these also break.

The shadow-test detection constraint: an unlisted test file in a locked slice's **scope** (the locked set's directories) is flagged `unexpected`; an unlisted test file **outside** any locked scope is NOT flagged (the negative case).

New `create_manifest` signature accepts optional `locked_files` list (a list of absolute paths to pre-existing test files to include in the manifest):
```python
create_manifest(feature_dir, manifest_path=None, locked_files=None) -> dict
```

The existing tests for `test_first_run_creates_manifest_with_correct_structure`, `test_no_change_verification_passes`, `test_modified_file_detected`, `test_deleted_file_detected`, `test_unexpected_new_file_detected`, `test_empty_directory_passes_gracefully` must ALL be rewritten. The `len(hash_value) == 64` and `hash_value` string comparisons become object structure assertions.

## 3. Instructions

1. Open `assets/fbk-scripts/tests/test_gates_test_hash.py`.

2. Replace the import line:
   ```python
   from fbk.gates.test_hash import compute_hashes, create_manifest, verify_manifest
   ```
   Keep the same imports — the function names are unchanged, only the signatures and return shapes change.

3. Rewrite the class `TestComputeHashesAndCreateManifest`. Replace all methods:

   - **`test_first_run_creates_manifest_with_per_entry_objects(tmp_path)`**: Create 2 test files. Call `create_manifest(tmp_path, manifest_path)`. Read the manifest JSON. For each file entry, assert the value is a dict with keys `"sha256"`, `"slice"`, `"test-discipline"`. Assert `len(value["sha256"]) == 64`. Assert all chars in `value["sha256"]` are in `"0123456789abcdef"`.

   - **`test_no_change_verification_returns_empty_list(tmp_path)`**: Create 1 test file. Call `create_manifest`. Call `verify_manifest(tmp_path, manifest_path)`. Assert return value is `[]` (empty list, not the string `"pass"`).

   - **`test_modified_file_returns_modified_discrepancy(tmp_path)`**: Create 1 test file. Create manifest. Modify the file. Call `verify_manifest`. Assert result is a non-empty list. Assert at least one item has `{"kind": "modified", ...}` (check `item["kind"] == "modified"`).

   - **`test_deleted_file_returns_missing_discrepancy(tmp_path)`**: Create 1 test file. Create manifest. Delete the file. Call `verify_manifest`. Assert at least one item has `item["kind"] == "missing"`.

   - **`test_empty_directory_verify_returns_empty_list(tmp_path)`**: Create manifest on empty dir. Call `verify_manifest`. Assert `result == []`.

4. Add a new class `TestListDrivenLockMode`:

   - **`test_locked_pre_existing_file_appears_in_manifest(tmp_path)`**: Create a file at `tmp_path / "existing_tests" / "test_existing.py"` with some content. Call `create_manifest(tmp_path, manifest_path, locked_files=[str(tmp_path / "existing_tests" / "test_existing.py")])`. Assert the manifest contains an entry for `"existing_tests/test_existing.py"` (or similar relative path). Assert that entry has `"sha256"`, `"slice"`, `"test-discipline"` keys.

   - **`test_locked_file_tamper_detected(tmp_path)`**: Create and lock a pre-existing file. Create manifest. Modify the locked file. Call `verify_manifest`. Assert at least one item has `item["kind"] == "modified"`.

5. Add a new class `TestShadowTestDetection`:

   - **`test_unlisted_file_in_locked_scope_flagged_as_shadow(tmp_path)`**: Create a locked scope directory `tmp_path / "locked_tests"`. Create and lock `locked_tests/test_locked.py`. Create manifest. Then add a NEW file `locked_tests/test_shadow.py` (unlisted, inside the locked directory). Call `verify_manifest`. Assert at least one item has `item["kind"] == "unexpected"` with `"shadow"` or `"test_shadow.py"` in `item["path"]`.

   - **`test_unlisted_file_outside_locked_scope_not_flagged(tmp_path)`**: Create a locked scope `tmp_path / "locked_tests"`. Create and lock one file there. Create manifest. Add a file `tmp_path / "other_tests" / "test_unrelated.py"` (outside the locked scope entirely). Call `verify_manifest`. Assert result contains NO item with `item["kind"] == "unexpected"` (the unlisted file outside locked scope is not flagged). This is the load-bearing negative case from the spec.

6. Add a new class `TestVerifyManifestReturnStructure`:

   - **`test_discrepancy_dict_has_kind_and_path(tmp_path)`**: Create a test file. Create manifest. Modify the file. Call `verify_manifest`. Assert result is a `list`. Assert each item is a `dict`. Assert each item has keys `"kind"` and `"path"`. Assert each `item["kind"]` is one of `{"modified", "unexpected", "missing"}`.

## 4. Files to create/modify

- `assets/fbk-scripts/tests/test_gates_test_hash.py` (modify)

Justification for rewriting existing methods: the manifest schema change is contract-evolving; the spec's §Slices `retired-tests` field for this slice explicitly names "flat-map assertions (len==64 on the file value; direct hash-string comparison) — replaced by per-entry-object assertions."

## 5. Test requirements

All pytest unit tests. No mocks. Real temp files and directories.

Retired assertions (direct hash-string comparison, `len==64` on bare string, `result == "pass"` string, `"MODIFIED" in result` string): all removed.

New assertions: per-entry object shape, empty-list clean result, `item["kind"]` discrepancy typing, list-driven lock mode, shadow-test detection, scoped-exclusion negative case.

The new tests fail before implementation because the existing `test_hash.py` still returns strings and uses flat hash values.

## 6. Acceptance criteria

Covers AC-07: per-entry manifest objects, list-driven lock mode for pre-existing tests, tamper detection, shadow-test detection within scope, and the critical negative case that files outside the locked scope are NOT flagged.

## 7. Model

Sonnet

## 8. Wave

Wave 2
