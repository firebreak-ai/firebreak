---
id: task-05
type: test
wave: 1
covers: [AC-08, AC-20]
files_to_create:
  - tests/sdl-workflow/test-code-review-ordering.sh
  - assets/fbk-scripts/tests/test_retro.py
completion_gate: "tests compile and fail before implementation"
---

## 1. Objective

Creates one TAP-format shell test and one pytest unit test: `test-code-review-ordering.sh` asserts the code-review skill invokes quality scan then test-review then the gate in the correct order after the bug-finding pass; `test_retro.py` asserts that `fbk.retro.append_section` appended for two successive stages preserves both stage sections (read-before-write preservation).

## 2. Context

**AC-08 (code-review ordering):** The spec requires `fbk-code-review/SKILL.md` to invoke the bug-finding pass first, then `fbk-quality-scan`, then `fbk-test-review` (final pass), then `code-review-gate` — in that exact order. The current `fbk-code-review/SKILL.md` does not yet invoke the quality-scan, test-review, or gate steps. The test greps the skill body for the relative ordering of four sentinel strings. The sentinel approach mirrors `test-skill-guide-dedup.sh` which checks ordering by finding line numbers of exact substrings.

The four ordered sentinels, in the required sequence:
1. **The bug-finding loop's detector-invocation marker** — do NOT grep a bare word like `Detector`. A bare word can survive in a comment or prose line after the bug-finding loop is removed or reordered, defeating the ordering check. Anchor on the exact detector-invocation line/heading present in the current `assets/skills/fbk-code-review/SKILL.md`: at implementation time, open the skill, find the line that actually invokes the bug-finding detection pass (currently the `## Detection-Verification Loop` heading and its `Spawn Detector with:` invocation step), and grep that exact string. The sentinel must be a string that cannot survive removal of the bug-finding loop — i.e. if the loop is deleted, the grep must return nothing. Prefer the invocation-step string (`Spawn Detector with:`) over the section heading, since prose mentions of "detector" are not invocations.
2. `fbk-quality-scan`
3. `fbk-test-review`
4. `code-review-gate`

The test must assert the bug-finding marker appears AND precedes the `fbk-quality-scan`, `fbk-test-review` (final pass), and `code-review-gate` markers.

**AC-20 (retrospective append preserves prior stages):** The spec requires each phase skill to append its stage section to the retrospective file and for prior stages to survive. The mechanism is `append_section` in `fbk.retro` (created by task-25), which reads the retrospective file before writing so prior stage sections survive. The replacement test is a real pytest unit test that imports `append_section` and exercises read-before-write preservation against a temp file — not a self-fulfilling shell test that writes its own success. The prior shell test (`test-retrospective-preservation.sh`) appended to its own temp file and then asserted on that same file, so it always passed regardless of the production code; it is removed.

Because the ordering sentinel test checks `fbk-code-review/SKILL.md` for sentinels that are not yet present (the quality-scan, test-review, and gate invocations), the ordering test fails on the `fbk-quality-scan` sentinel before implementation. The `test_retro.py` test fails before implementation because `fbk.retro.append_section` does not yet exist (ImportError) — the correct red state.

Follow the TAP pattern from `test-code-review-structural.sh` for the shell test.

## 3. Instructions

**File 1: `tests/sdl-workflow/test-code-review-ordering.sh`**

1. Create the file with standard TAP boilerplate (shebang, `set -uo pipefail`, counters, helpers, `PROJECT_ROOT`).

2. Define: `CODE_REVIEW_SKILL="$PROJECT_ROOT/assets/skills/fbk-code-review/SKILL.md"`

3. Write a helper function `line_of_first_match()` that finds the line number of the first occurrence of a pattern in a file:
   ```bash
   line_of_first_match() {
     grep -n "$1" "$2" 2>/dev/null | head -1 | cut -d: -f1
   }
   ```

4. Assert that the skill file exists: T1 `[ -s "$CODE_REVIEW_SKILL" ]` — skill file exists.

5. Determine the bug-finding detector-invocation sentinel by reading the live skill. Open `assets/skills/fbk-code-review/SKILL.md` and find the exact line that invokes the bug-finding detection pass (currently the `Spawn Detector with:` invocation step under the `## Detection-Verification Loop` heading). Use that exact string as the bug-finding sentinel — a string that cannot survive removal of the bug-finding loop. Do NOT use a bare word like `Detector` (it can survive in a comment or prose line after the loop is removed). Extract line numbers for the four sentinels:
   ```bash
   # BUG_FINDING_SENTINEL must be the real invocation string from the current skill body,
   # e.g. 'Spawn Detector with:' — not the bare word 'Detector'.
   line_bug_finding=$(line_of_first_match 'Spawn Detector with:' "$CODE_REVIEW_SKILL")
   line_quality_scan=$(line_of_first_match 'fbk-quality-scan' "$CODE_REVIEW_SKILL")
   line_test_review=$(line_of_first_match 'fbk-test-review' "$CODE_REVIEW_SKILL")
   line_gate=$(line_of_first_match 'code-review-gate' "$CODE_REVIEW_SKILL")
   ```

6. Write four ordering assertions (T2–T5):
   - T2: `[ -n "$line_bug_finding" ]` — bug-finding invocation sentinel found in skill body
   - T3: `[ -n "$line_quality_scan" ] && [ "$line_quality_scan" -gt "$line_bug_finding" ]` — `fbk-quality-scan` follows bug-finding
   - T4: `[ -n "$line_test_review" ] && [ "$line_test_review" -gt "$line_quality_scan" ]` — `fbk-test-review` (final pass) follows quality scan
   - T5: `[ -n "$line_gate" ] && [ "$line_gate" -gt "$line_test_review" ]` — `code-review-gate` follows test-review

7. Add a sixth assertion (T6) in the same shell test file: the capability-entry prerequisite probe is wired into the code-review skill body. This is the impl-missing-at-code-review case task-24 wires (AC-12 — the four upstream-missing prerequisite cases). Anchor on the verbatim probe-call name:
   ```bash
   grep -q 'check_prerequisites' "$CODE_REVIEW_SKILL" && ok "fbk-code-review/SKILL.md references check_prerequisites (capability-entry probe wired by task-24)" || not_ok "..."
   ```

8. Add TAP summary.

**File 2: `assets/fbk-scripts/tests/test_retro.py`**

This is a pytest unit test that replaces the prior self-fulfilling shell test. It exercises the real append mechanism (`fbk.retro.append_section`, created by task-25) so it actually verifies read-before-write preservation rather than re-asserting an append the test itself performed.

1. Create `assets/fbk-scripts/tests/test_retro.py` with imports:
   ```python
   import pytest
   from pathlib import Path
   try:
       from fbk.retro import append_section
   except ImportError:
       append_section = None
   ```

2. Write a test that appends two successive stage sections and asserts both survive:
   ```python
   @pytest.mark.skipif(append_section is None, reason="fbk.retro not yet implemented")
   def test_second_append_preserves_first(tmp_path):
       """append_section reads before writing; a second stage append preserves the first."""
       retro = tmp_path / "retrospective.md"
       append_section(str(retro), "Intent", "Intent stage content.")
       append_section(str(retro), "Design", "Design stage content.")
       text = retro.read_text()
       assert "Intent" in text, "first stage section was overwritten"
       assert "Design" in text, "second stage section missing"
       assert "Intent stage content." in text
       assert "Design stage content." in text
   ```
   The two appends represent stage section A (Intent) then stage section B (Design); the assertion that BOTH are present after the second append is the read-before-write preservation contract. The test fails before implementation via the `skipif`/ImportError guard until `fbk.retro.append_section` exists.

3. Confirm the file compiles: `python3 -m py_compile assets/fbk-scripts/tests/test_retro.py` exits 0.

## 4. Files to create/modify

- `tests/sdl-workflow/test-code-review-ordering.sh` (create)
- `assets/fbk-scripts/tests/test_retro.py` (create)

Multiple files created by one task: these two tests are logically one AC-08 + AC-20 test set authored together. The ordering check is a shell/grep assertion over the skill body; the preservation check is a pytest unit test against the real `fbk.retro.append_section` mechanism. Authoring them separately would create an artificial boundary since they cover two ACs of the same slice.

## 5. Test requirements

`test-code-review-ordering.sh` — 6 TAP assertions:
- T1: skill file exists
- T2–T5: the four ordered sentinels appear in the required sequence, with the bug-finding sentinel anchored on the real detector-invocation string (`Spawn Detector with:`), not a bare word. T3–T5 fail before implementation because the quality-scan, test-review, and gate invocations do not yet exist in the skill body.
- T6: `check_prerequisites` appears in the skill body — the capability-entry probe wired by task-24 (the impl-missing-at-code-review case of AC-12). Fails before task-24 wires the probe call.

`test_retro.py` — 1 pytest unit test:
- `test_second_append_preserves_first`: appends two stage sections via `fbk.retro.append_section` and asserts both survive (read-before-write preservation). Fails before implementation via the ImportError/`skipif` guard until `fbk.retro.append_section` exists.

## 6. Acceptance criteria

- The code-review skill body will contain the four ordered invocations after the phase-skill-modifications slice is implemented; T2–T5 will then pass. The bug-finding sentinel is a string that cannot survive removal of the bug-finding loop.
- The retrospective append preservation is verified against the real `fbk.retro.append_section` mechanism (not a self-fulfilling shell test); it passes after task-25 implements `append_section`.

## 7. Model

Haiku

## 8. Wave

Wave 1
