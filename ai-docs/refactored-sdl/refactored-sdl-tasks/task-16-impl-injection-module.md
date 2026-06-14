---
id: task-16
type: implementation
wave: 1
covers: [AC-23]
files_to_create:
  - assets/fbk-scripts/fbk/injection.py
  - assets/fbk-scripts/fbk/slices.py
files_to_modify:
  - assets/fbk-scripts/fbk/gates/spec.py
test_tasks: [task-02]
dependencies: []
completion_gate: "the referenced test tasks pass"
---

## 1. Objective

Produces the shared `fbk/injection.py` module (with `detect_injections` moved verbatim out of `spec.py`) and the shared `fbk/slices.py` constant module (`TEST_DISCIPLINES`), and rewires `spec.py` to import `detect_injections` from `fbk.injection` instead of defining it inline.

## 2. Context

Two cross-cutting shared symbols are extracted so the spec, intent, design, breakdown, and test-hash gates all import one copy and can't drift:

1. `detect_injections` is promoted out of `spec.py` into a new `fbk/injection.py`. Its only current consumers are `spec.py` internals and the spec-gate injection test, so the move has no hidden caller. The function body moves **verbatim** — do not re-implement or change its behavior. The pinned signature (Interface contract #3) is:

   ```python
   def detect_injections(path_or_text: str) -> int
   ```

   It accepts a file path (checked with `os.path.isfile`) or raw text, returns the warning count, and prints `WARNING: [injection] ...` lines to stderr. The four pattern classes it detects (already implemented in the current `spec.py`): control characters (U+0000–U+0008, U+000B–U+000C, U+000E–U+001F), zero-width characters (U+200B, U+200C, U+200D, U+2060) plus BOM-not-at-position-0, HTML comments containing instruction-like phrases, and embedded instruction patterns outside fenced code blocks. The current parameter name in `spec.py` is `spec_path_or_text`; the pinned public signature names it `path_or_text`. Rename the parameter to `path_or_text` when moving (the body uses the name throughout — update all references), so the moved function matches the pinned signature exactly.

2. The shared slice-discipline constant (Interface contract #2) lives in a new `fbk/slices.py`:

   ```python
   TEST_DISCIPLINES = ("new-contract", "contract-preserving", "contract-evolving", "cross-cutting")
   ```

   This is the single source of truth imported by the spec, breakdown, and test-hash gates so adding a shape later is a one-file change. No gate hard-codes the four strings. This task only creates the constant module; the importing gates are wired by their own tasks (task-29 spec, task-30 breakdown, task-26 test-hash).

Existing code to read before editing: `assets/fbk-scripts/fbk/gates/spec.py` — the `detect_injections` function spans the block under the `# Injection detection` header (currently lines ~157–284), and it is called once inside `main()` on the structural-pass path (currently `injection_warnings = detect_injections(spec_path)`).

The paired test (`assets/fbk-scripts/tests/test_injection.py`) imports `from fbk.injection import detect_injections` and asserts: callable returning `int`; `>= 1` on each of the four pattern classes; `0` on clean text and on an instruction inside a code fence; `0` on a clean file path passed as a string. The existing `test_gates_spec_injection.py` (which imports `detect_injections` from `fbk.gates.spec`) must keep working — so `spec.py` must re-export the name (it imports it at module level, which makes `fbk.gates.spec.detect_injections` resolvable). Confirm `test_gates_spec_injection.py` still passes after the move.

## 3. Instructions

1. Create `assets/fbk-scripts/fbk/slices.py` containing the module docstring and the constant exactly: `TEST_DISCIPLINES = ("new-contract", "contract-preserving", "contract-evolving", "cross-cutting")`. Completion: `python3 -c "from fbk.slices import TEST_DISCIPLINES; assert TEST_DISCIPLINES == ('new-contract','contract-preserving','contract-evolving','cross-cutting')"` exits 0 (run from `assets/fbk-scripts`).

2. Create `assets/fbk-scripts/fbk/injection.py`. Move the entire `detect_injections` function from `spec.py` into it verbatim, including its required imports (`re`, `sys`, and the inline `import os as _os` it uses — or hoist `import os` to module level). Rename the parameter from `spec_path_or_text` to `path_or_text` and update every reference inside the body. Add a module docstring. Completion: `python3 -c "from fbk.injection import detect_injections; assert detect_injections('clean text') == 0; assert detect_injections('a\x01b') >= 1"` exits 0 (run from `assets/fbk-scripts`).

3. In `assets/fbk-scripts/fbk/gates/spec.py`, remove the inline `detect_injections` function definition (the entire block under the `# Injection detection` header). Add a module-level import near the top imports: `from fbk.injection import detect_injections`. Leave the single call site in `main()` unchanged (`detect_injections(spec_path)` still resolves via the import). Completion: `grep -c 'def detect_injections' assets/fbk-scripts/fbk/gates/spec.py` returns 0, and `grep -q 'from fbk.injection import detect_injections' assets/fbk-scripts/fbk/gates/spec.py` succeeds.

4. Verify the spec gate still runs end-to-end and the re-export works: from `assets/fbk-scripts`, `python3 -c "from fbk.gates.spec import detect_injections; assert detect_injections('clean') == 0"` exits 0.

5. Run the paired test and the impacted existing test: from `assets/fbk-scripts`, `python3 -m pytest tests/test_injection.py tests/test_gates_spec_injection.py -q`. Both must pass.

## 4. Files to create/modify

- `assets/fbk-scripts/fbk/injection.py` (create)
- `assets/fbk-scripts/fbk/slices.py` (create)
- `assets/fbk-scripts/fbk/gates/spec.py` (modify)

File-scope justification: three files for one shared-infrastructure extraction. The move of `detect_injections` is inseparable from the `spec.py` edit that imports it (leaving spec.py's inline copy would defeat the de-duplication); the `slices.py` constant is the second shared symbol declared in the same slice (`shared-gate-infrastructure`) and is a single-line file with no behavior.

## 5. Test requirements

- New tests: none authored here. Make `assets/fbk-scripts/tests/test_injection.py` (from task-02) pass.
- Existing tests impacted: `assets/fbk-scripts/tests/test_gates_spec_injection.py` imports `detect_injections` from `fbk.gates.spec`; it must keep passing via the re-export (the module-level import in spec.py exposes the name). Do not modify that test file.

## 6. Acceptance criteria

- AC-23: `detect_injections` lives in `fbk/injection.py` and is importable from that location; verified by `test_injection.py` importing it from there. The constant module `fbk/slices.py` exists for downstream gates to import.
- Primary criterion: the task-02 tests pass and `test_gates_spec_injection.py` stays green.

## 7. Model

Sonnet

## 8. Wave

Wave 1
