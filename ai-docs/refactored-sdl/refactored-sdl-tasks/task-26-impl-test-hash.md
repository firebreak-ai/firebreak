---
id: task-26
type: implementation
wave: 2
covers: [AC-07]
files_to_modify:
  - assets/fbk-scripts/fbk/gates/test_hash.py
test_tasks: [task-07]
dependencies: [task-16]
completion_gate: "the referenced test tasks pass"
---

## 1. Objective

Restructures `assets/fbk-scripts/fbk/gates/test_hash.py` so each manifest entry is an object `{sha256, slice, test-discipline}`, adds a list-driven lock mode for named pre-existing test files, scopes shadow-test detection to the locked set's directories, and gives `verify_manifest` a structured discrepancy-list return.

## 2. Context

This is a refactor-then-extend of the shipped flat-map manifest. The current `test-hashes.json` is `{"files": {path: hex-hash}, "computed_at": iso}`. The new schema (Interface contract #5):

```json
{"computed_at": "<iso8601>", "files": {"<relpath>": {"sha256": "<hex>", "slice": "<slice-name>", "test-discipline": "<mode>"}}}
```

The per-file value becomes an object, not a bare hash string. Read the current `assets/fbk-scripts/fbk/gates/test_hash.py` before editing — `compute_hashes`, `create_manifest`, `verify_manifest`, `main`.

Pinned interfaces (copy the exact signatures the paired test declares):

```python
def create_manifest(feature_dir, manifest_path=None, locked_files=None) -> dict
def verify_manifest(feature_dir, manifest_path=None) -> list[dict]
```

- `create_manifest` gains an optional `locked_files` list — absolute paths to pre-existing test files (outside the feature dir's rglob discovery) to include in the manifest. The default discovery (rglob for files under `/tests/` or with `test` in the name, excluding `test-hashes.json`) still runs; `locked_files` are added on top. This is the **list-driven lock mode** for contract-preserving slices that lock named pre-existing project tests.
- `verify_manifest` returns `list[dict]` (Interface contract #4): each dict `{"kind": "modified" | "unexpected" | "missing", "path": "<relpath>"}`; empty list means clean. The current string return (`"pass"` / error blob) is replaced entirely.
  - `modified` = a manifest entry whose file exists but whose current sha256 differs from the recorded one (hash mismatch).
  - `missing` = a manifest entry whose file is gone.
  - `unexpected` = a test file present **in a locked slice's scope** but absent from the manifest (a shadow test).

**Shadow-test scoping (load-bearing).** In list-driven mode, "scope" is the **directories of the locked set** — not a repo-wide rglob. The negative case the test asserts: an unlisted test file OUTSIDE any locked scope is NOT flagged `unexpected`. So the unexpected check must enumerate test files only within the parent directories of the manifest's recorded entries (the locked scope), and flag any such file not in the manifest. A file in an unrelated directory must never be flagged. Concretely: derive the set of scope directories = the parent dirs of every relpath recorded in the manifest; for the unexpected check, scan only those directories for test files; any test file in a scope directory not present in the manifest is `unexpected`.

Import the shared constant: `from fbk.slices import TEST_DISCIPLINES` (created by task-16). Use it for the default `test-discipline` value or for validation; the per-entry `slice` and `test-discipline` fields default to a sensible value when not supplied (the create path may set `slice` to `""` or `"default"` and `test-discipline` to a value from `TEST_DISCIPLINES`, e.g. `"new-contract"` — the test only asserts the keys exist and round-trip, and that `sha256` is 64 hex chars).

`main()` must be updated for the new `verify_manifest` return: on an empty list, print the pass JSON and exit 0; on a non-empty list, print the discrepancies to stderr and `sys.exit(2)`. Preserve the runtime filename `test-hashes.json` and the no-test-files-found pass path.

## 3. Instructions

1. Read the current `assets/fbk-scripts/fbk/gates/test_hash.py`.

2. Add the import `from fbk.slices import TEST_DISCIPLINES` near the top.

3. Refactor `compute_hashes(feature_dir, locked_files=None)` (or add a helper) so that, in addition to the existing rglob discovery, it includes any absolute paths in `locked_files`. For each included file compute the sha256 hex and key it by a relative path.

   **Relpath rule — follow §Interface contracts #5 verbatim.** This is the spec's pinned interface contract, not a task-local invention; `breakdown-gate` reads `test-hashes.json` directly against this schema (it does not import `test_hash`), so the relpath rule must match the spec's pin or the two slices diverge:
   - For a locked file *inside* `feature_dir` (the rglob-discovered files and any `locked_files` entry under `feature_dir`), the key is the path relative to `feature_dir` (e.g. `tests/test_module.py`).
   - For a list-driven-locked file *outside* `feature_dir` (a contract-preserving slice locking a pre-existing project test), the key is the last two path components joined with `/` (e.g. `existing_tests/test_existing.py`).

   State the relpath rule in a code comment that points back to §Interface contracts #5 so future readers see this is contract-pinned, not arbitrary. The test creates locked files like `tmp_path/"existing_tests"/"test_existing.py"` and asserts the manifest contains an entry for `"existing_tests/test_existing.py"` — the contract's last-two-components rule for files outside feature_dir delivers exactly this key.

4. Rewrite `create_manifest(feature_dir, manifest_path=None, locked_files=None) -> dict` so each `files` entry is an object `{"sha256": <hex>, "slice": <slice-name>, "test-discipline": <mode>}`. Default `slice` to `""` (or a passed value) and `test-discipline` to `TEST_DISCIPLINES[0]` (`"new-contract"`) for discovered files. Write `{"computed_at": <iso>, "files": {...}}`. Return the existing gate-result dict shape (`{"gate": "test-hash", "result": "pass", "action": "created", "files": <count>}`). Completion: a manifest written by `create_manifest` has each file value as a dict with keys `sha256`, `slice`, `test-discipline`, and `len(value["sha256"]) == 64`.

5. Rewrite `verify_manifest(feature_dir, manifest_path=None) -> list[dict]`:
   - Load the manifest; `old = manifest["files"]` (objects).
   - For each recorded relpath: resolve the actual file (the same resolution rule used at create time). If the file is gone → append `{"kind": "missing", "path": relpath}`. Else compute current sha256; if it differs from `old[relpath]["sha256"]` → append `{"kind": "modified", "path": relpath}`.
   - Shadow detection scoped to the locked set: compute `scope_dirs` = the set of parent directories of the actual files for every recorded relpath. For each scope dir, enumerate its test files (filename contains `test` or under a `/tests/` path, excluding `test-hashes.json`); for any such file whose relpath is not in `old`, append `{"kind": "unexpected", "path": relpath}`. Do NOT rglob the whole feature dir — only the scope dirs. This guarantees a file outside any locked scope is never flagged.
   - Return the list (empty if clean).
   Completion: the function returns a list; each item has keys `kind` and `path`; `kind` is one of `modified`/`unexpected`/`missing`.

6. Update `main()`: call the new `verify_manifest`; if the returned list is empty, print the verified-pass JSON and exit 0; otherwise print each discrepancy (`f"{d['kind'].upper()}: {d['path']}"`) to stderr and `sys.exit(2)`. Preserve the create-on-first-run and no-test-files-found branches.

7. Run the paired test: from `assets/fbk-scripts`, `python3 -m pytest tests/test_gates_test_hash.py -q`. All rewritten and new test classes must pass — especially `test_unlisted_file_outside_locked_scope_not_flagged` (the load-bearing negative case) and `test_unlisted_file_in_locked_scope_flagged_as_shadow`.

## 4. Files to create/modify

- `assets/fbk-scripts/fbk/gates/test_hash.py` (modify)

## 5. Test requirements

- New tests: none authored here. Make `assets/fbk-scripts/tests/test_gates_test_hash.py` (task-07, rewritten) pass.
- Retired assertions (handled by task-07): the flat-map `len==64`-on-bare-string and direct hash-string comparisons, and the `result == "pass"` / `"MODIFIED" in result` string checks are replaced by per-entry-object and structured-discrepancy assertions. Do not re-introduce the string return.

## 6. Acceptance criteria

- AC-07: per-entry manifest objects record `sha256`, `slice`, `test-discipline`; list-driven lock mode locks named pre-existing test files; tamper detection trips; an unlisted file in a locked slice's scope is flagged as a shadow test; an unlisted file outside any locked scope is not flagged.
- Primary criterion: the task-07 tests pass.

## 7. Model

Sonnet

## 8. Wave

Wave 2
