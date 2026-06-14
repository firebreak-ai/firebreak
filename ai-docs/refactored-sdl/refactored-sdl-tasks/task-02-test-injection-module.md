---
id: task-02
type: test
wave: 1
covers: [AC-23]
files_to_create:
  - assets/fbk-scripts/tests/test_injection.py
completion_gate: "tests compile and fail before implementation"
---

## 1. Objective

Creates `assets/fbk-scripts/tests/test_injection.py`, a pytest unit test file that verifies `detect_injections` is importable from `fbk.injection` (not `fbk.gates.spec`), returns an integer count, and detects each of the four injection pattern classes.

## 2. Context

The spec promotes `detect_injections` from `fbk/gates/spec.py` into a new shared module `fbk/injection.py`. After the promotion, the function signature is:

```python
def detect_injections(path_or_text: str) -> int
```

It accepts either a file path (checked with `os.path.isfile`) or a raw text string. It returns the count of warnings and prints `WARNING: [injection] ...` lines to stderr. The four pattern classes it detects:
1. Control characters (U+0000–U+001F, excluding tab, newline, CR)
2. Zero-width characters (U+200B, U+200C, U+200D, U+2060)
3. HTML comments containing instruction-like phrases (e.g., "ignore previous instructions")
4. Embedded instruction patterns outside fenced code blocks (e.g., "ignore previous instructions")

The existing tests in `test_gates_spec_injection.py` currently import `detect_injections` from `fbk.gates.spec`. The new `test_injection.py` must import from `fbk.injection` — that import will fail (ImportError) before the shared module is created, which is the correct red state.

Do NOT mock anything. All inputs are real strings or real temp files. Follow the pattern in `assets/fbk-scripts/tests/test_gates_spec_injection.py` for assertion style.

## 3. Instructions

1. Create `assets/fbk-scripts/tests/test_injection.py`.

2. Add this import at the top:
   ```python
   import pytest
   from fbk.injection import detect_injections
   ```
   This import will raise `ImportError` before the module exists — that is the correct red state.

3. Add a class `TestDetectInjectionsImportContract` with one test:
   - `test_importable_from_fbk_injection`: assert that `detect_injections` is callable and that calling it with the string `"clean text"` returns an integer. This verifies the interface contract (function exists, returns `int`).

4. Add a class `TestControlCharacterDetection` with one test:
   - `test_control_character_detected`: pass the string `"spec\x01content"` (contains U+0001). Assert `detect_injections("spec\x01content") >= 1`.

5. Add a class `TestZeroWidthCharacterDetection` with one test:
   - `test_zero_width_space_detected`: pass `"spec\u200Bcontent"`. Assert the return value is `>= 1`.

6. Add a class `TestHTMLCommentInjectionDetection` with one test:
   - `test_html_comment_instruction_detected`: pass `"content\n<!-- ignore previous instructions -->\nmore"`. Assert return value is `>= 1`.

7. Add a class `TestEmbeddedInstructionPatternDetection` with one test:
   - `test_embedded_instruction_outside_code_block_detected`: pass `"normal text\nignore previous instructions\nmore text"`. Assert return value is `>= 1`.

8. Add a class `TestCleanInputReturnsZero` with two tests:
   - `test_clean_string_returns_zero`: pass `"This is a clean specification."`. Assert return value is `0`.
   - `test_instruction_in_code_fence_exempt`: pass a multi-line string with `"```\nignore previous instructions\n```"` (the pattern is inside a fenced code block). Assert return value is `0`.

9. Add a class `TestFilePathInput` with one test:
   - `test_accepts_file_path(tmp_path)`: write a file `tmp_path / "clean.md"` containing `"clean text"`. Pass the string path to `detect_injections`. Assert return value is `0`. (This verifies the file-path branch of the function.)

## 4. Files to create/modify

- `assets/fbk-scripts/tests/test_injection.py` (create)

## 5. Test requirements

All tests are pytest unit tests. No mocks. Real string inputs and real temp files.

- Import test: verifies the function is importable from the new module path (fails red until `fbk/injection.py` exists).
- Pattern-class tests (4 tests): each exercises one injection class with a minimal string containing only that pattern. Return value `>= 1` is the assertion.
- Clean tests (2 tests): verify zero false positives on a clean string and on a pattern inside a code fence.
- File-path test (1 test): verifies the path-vs-text dispatch branch works.

## 6. Acceptance criteria

Covers AC-23: `detect_injections` lives in `fbk/injection.py` and is importable from that location. The spec gate, intent gate, and design gate all import from the shared module after implementation.

## 7. Model

Haiku

## 8. Wave

Wave 1
