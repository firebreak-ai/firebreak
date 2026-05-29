---
id: task-34
type: implementation
wave: 3
covers: [AC-09, AC-11, AC-24]
files_to_create:
  - assets/fbk-scripts/fbk/gates/code_review.py
test_tasks: [task-12]
dependencies: [task-26]
completion_gate: "the referenced test tasks pass"
---

## 1. Objective

Produces the new `assets/fbk-scripts/fbk/gates/code_review.py` module that checks the quality-scan and final test-review artifacts, delegates the hash + shadow-test check to `test_hash.verify_manifest`, fails only on a hash mismatch or shadow test (critical findings and drift do not block), and guards its path argument.

## 2. Context

The code-review gate (subcommand `code-review-gate`, registered by task-22) is a **new module** — not folded into `review.py` (which gates the spec-review council artifact, a different phase). It runs after the bug-finding loop and the two added passes. Same gate shape (pure check function, argparse `main()`, JSON to stdout, exit 0/2, path-arg validated, `errors="replace"` reads).

Pinned pure-function signature (copy verbatim — the paired test imports it with an ImportError guard):

```python
def validate_code_review(feature_dir: str) -> dict
```

Checks (read the task-12 test for exact fixtures and failure substrings):

1. **Quality-scan artifact present with severity field**: `<feature_dir>/quality-scan.md` exists AND contains a `Severity:` line somewhere. Absent file → failure mentioning "quality-scan"/"quality scan". File present but no `Severity:` field → failure.
2. **Final test-review verdict artifact present**: `<feature_dir>/test-review-final.md` exists (or any file matching `test-review-*.md` for the final-pass artifact — the test uses `test-review-final.md`). Absent → failure.
3. **Hash + shadow-test check via delegation**: call `verify_manifest(feature_dir)` imported from `fbk.gates.test_hash` (the restructured version from task-26 returning `list[dict]`). Do NOT implement a second hash-comparison path. Branch on the structured discrepancy kinds (Interface contract #4):
   - any item `kind == "modified"` → gate FAILS (hash mismatch / tampered locked test).
   - any item `kind == "unexpected"` → gate FAILS (shadow test).
   - any item `kind == "missing"` → surfaces as a FINDING (not a failure) — record it in a `findings`/`warnings` list in the result; do not add it to `failures`.

**Non-blocking conditions (AC-11):**
- A `Severity: critical` value in the quality-scan does NOT fail the gate — severity is for operator triage. The test `test_critical_severity_quality_finding_does_not_fail` asserts a critical-severity quality-scan still passes.
- A drifted-but-unmodified locked test surfaces as a `missing` discrepancy (the path changed but content unchanged) — a finding, not a failure. The test `test_missing_kind_discrepancy_does_not_fail` asserts the gate passes and the result records the missing file somewhere (a `findings` or `warnings` key, or empty failures with the missing item recorded).

**Delegation contract (load-bearing):** the hash/shadow check must go through `test_hash.verify_manifest` so the gate uses one hash path. The test `test_hash_check_delegates_to_verify_manifest` monkeypatches `fbk.gates.test_hash.verify_manifest` to record its call and asserts it was called exactly once with the feature-dir path. Therefore: call it as `from fbk.gates import test_hash` then `test_hash.verify_manifest(feature_dir)` (or `verify_manifest(feature_dir)` via a module attribute that the monkeypatch can intercept) — call it through the module so the monkeypatch on `fbk.gates.test_hash.verify_manifest` takes effect, and pass the feature_dir path as the argument exactly once.

**Path guard (AC-24):** `main()` validates the feature-dir path with `is_dir()` → `sys.exit(2)` if missing; all reads use `errors="replace"` so a binary quality-scan degrades to a structural failure (the no-severity-field path), not a traceback.

Result JSON shape: `{"gate": "code-review", "result": "pass"|"fail", "failures": [...], "findings": [...]}` (findings carries the non-blocking `missing` discrepancies). The test only requires the failures to be empty/non-empty appropriately and a record of the missing file to exist when a `missing` discrepancy occurs.

**Do not register anything here** — the dispatcher (task-22) owns the `COMMAND_MAP` entry `"code-review-gate": "fbk.gates.code_review"`.

## 3. Instructions

1. Read `assets/fbk-scripts/fbk/gates/spec.py` (gate shape), the restructured `assets/fbk-scripts/fbk/gates/test_hash.py` (the `verify_manifest -> list[dict]` from task-26), and the task-12 test (fixtures, `make_code_review_dir`, delegation monkeypatch, failure substrings).

2. Create `assets/fbk-scripts/fbk/gates/code_review.py`. Import: `from fbk.gates import test_hash`. (Calling `test_hash.verify_manifest(...)` through the module makes the monkeypatch on `fbk.gates.test_hash.verify_manifest` effective.)

3. Implement `def validate_code_review(feature_dir: str) -> dict`:
   - Quality-scan present + `Severity:` field check (read with `errors="replace"`).
   - Final test-review verdict artifact present check (`test-review-final.md` or `test-review-*.md` glob).
   - Call `test_hash.verify_manifest(feature_dir)` exactly once. Iterate the returned list: collect `modified` and `unexpected` items into `failures` (each a string naming the kind + path); collect `missing` items into `findings` (non-blocking).
   - Do not treat any quality-scan severity value as a failure.
   - Return `{"gate": "code-review", "result": "pass" if not failures else "fail", "failures": failures, "findings": findings}`.

4. Implement `main()` with argparse (positional `feature_dir`): `is_dir()` guard → `sys.exit(2)`; call `validate_code_review`; print JSON; exit 0/2. Add the `__main__` guard. Ensure a binary quality-scan degrades via `errors="replace"`.

5. Run the paired test: from `assets/fbk-scripts`, `python3 -m pytest tests/test_gates_code_review.py -q`. All classes must pass — full pass, missing/malformed artifacts, hash mismatch, shadow test, non-failing conditions (critical severity, missing-kind), the delegation-contract monkeypatch, and the path-guard subprocess tests.

## 4. Files to create/modify

- `assets/fbk-scripts/fbk/gates/code_review.py` (create)

## 5. Test requirements

This task makes `assets/fbk-scripts/tests/test_gates_code_review.py` (task-12) pass. It depends on the restructured `verify_manifest` from task-26 (wave 2) — the real-file hash tests need the `list[dict]` return. The subprocess path-guard tests run via `python3 -m fbk code-review-gate <args>` (registration is task-22). No new tests are written here. Do not edit the test file.

## 6. Acceptance criteria

- AC-09: requires a quality-scan artifact with the severity field populated and a final test-review verdict artifact; performs the hash + shadow-test check by calling `test_hash.verify_manifest` (one hash path, verified by the delegation monkeypatch).
- AC-11: a critical-severity quality finding or a drifted-but-unmodified locked test surfaces for triage; only a hash mismatch (`modified`) or a shadow test (`unexpected`) fails the gate.
- AC-24: validates the path arg (exit 2 on missing) and reads with `errors="replace"`.
- Primary criterion: the task-12 tests pass.

## 7. Model

Sonnet

## 8. Wave

Wave 3
