---
id: task-04
type: test
wave: 2
covers: [AC-01, AC-09, AC-10]
files_to_create:
  - assets/fbk-scripts/tests/test_capture_gate_check.py
completion_gate: "tests compile and fail before implementation"
---

# Objective

Write the unit tests for the per-project capture gate's two core questions: is this project instrumented, and what capture level resolves — covering the Firebreak/marked detection, the shipped `standard` default, the `off` for uninstrumented projects, and the single bounded-read of `capture.cfg`.

# Context

Capture runs only in an opted-in project. The gate answers two things using only filesystem existence checks plus one bounded single-line read of `.fbk-capture/capture.cfg` (read one line, never the whole file, so a hostile multi-gigabyte file cannot stall the hot path) — no YAML, no state-engine import. A project counts as instrumented when it carries a Firebreak marker sentinel under `.claude/automation/` OR a `.fbk-capture/capture.cfg` file. Level resolution returns the cfg value when valid (`off`/`standard`), `standard` for a Firebreak project with an absent or invalid cfg (with a stderr warning on an invalid value), and `off` for an uninstrumented project. Any filesystem error resolves to the safe default (not instrumented / off).

(The `full`-level out-of-tree corroboration and symlink confinement are covered by a separate hardening task; this task covers the off/standard/instrumentation core. The Firebreak-marker-sentinel-vs-bare-directory hardening also has its own task — here, build instrumented projects WITH the sentinel so this task's instrumentation-positive cases are unambiguous.)

Exercise through `tmp_path` project trees built by `capture_fixtures.make_project`. Import `from fbk.capture import gate_check` inside `try/except ImportError` with a module-level skipif. Capture stderr with pytest's `capsys`.

Signatures to call verbatim: `gate_check.project_is_instrumented(cwd) -> bool` and `gate_check.resolve_capture_level(cwd) -> "off"|"standard"|"full"`.

# Instructions

1. Create `tests/test_capture_gate_check.py`; import `gate_check` inside `try/except ImportError`; module-level `pytestmark = pytest.mark.skipif(...)`.
2. `test_instrumented_true_for_firebreak_marked_project`: build a project with `.claude/automation/.fbk-managed` sentinel (`make_project(..., instrumented=True, marked=True)`); assert `project_is_instrumented(root) is True`.
3. `test_instrumented_true_for_capture_cfg_project`: build a project with only `.fbk-capture/capture.cfg` (`make_project(..., instrumented=False, capture_cfg="standard")`); assert `project_is_instrumented(root) is True`.
4. `test_instrumented_false_for_bare_project`: build a bare `tmp_path` project with neither marker; assert `project_is_instrumented(root) is False`.
5. `test_instrumented_false_on_filesystem_error`: pass a path that triggers an error (e.g. a non-existent path, or a file where a directory is expected); assert `project_is_instrumented(...) is False` and that nothing is raised.
6. `test_level_returns_cfg_value_when_valid`: build a project with `capture.cfg` containing `capture_level=off`; assert `resolve_capture_level(root) == "off"`. Repeat with `capture_level=standard` → `"standard"`.
7. `test_level_defaults_standard_for_firebreak_without_cfg`: build a Firebreak-marked project (sentinel present) with no `capture.cfg`; assert `resolve_capture_level(root) == "standard"`.
8. `test_level_invalid_cfg_warns_and_defaults_standard`: build a project whose `capture.cfg` contains `capture_level=banana`; assert `resolve_capture_level(root) == "standard"` AND a warning appears on stderr (`capsys.readouterr().err` is non-empty / contains the offending value).
9. `test_level_off_for_uninstrumented_project`: bare project; assert `resolve_capture_level(root) == "off"`.
10. `test_level_reads_only_one_line`: write a `capture.cfg` whose first line is `capture_level=standard` followed by a very large second line (e.g. several megabytes of filler); assert `resolve_capture_level(root) == "standard"` and that the call returns promptly — assert the resolved value (the bounded-read behavior is observable because the giant trailing bytes do not change the answer). Do not assert wall-clock here; the overhead-budget task owns timing.

# Files to create/modify

- `tests/test_capture_gate_check.py`

# Test requirements

- `test_instrumented_true_for_firebreak_marked_project` (unit): sentinel present → instrumented True.
- `test_instrumented_true_for_capture_cfg_project` (unit): capture.cfg present → instrumented True.
- `test_instrumented_false_for_bare_project` (unit): neither marker → False.
- `test_instrumented_false_on_filesystem_error` (unit): error path → False, no raise.
- `test_level_returns_cfg_value_when_valid` (unit): valid cfg value returned for off and standard.
- `test_level_defaults_standard_for_firebreak_without_cfg` (unit): marked project, no cfg → standard.
- `test_level_invalid_cfg_warns_and_defaults_standard` (unit): invalid value → standard + stderr warning.
- `test_level_off_for_uninstrumented_project` (unit): bare project → off.
- `test_level_reads_only_one_line` (unit): giant trailing bytes do not change the resolved value.

# Acceptance criteria

AC-01 (per-project gate), AC-09 (shipped default standard inside Firebreak), AC-10 (level resolution via filesystem checks + one single-line read). Gate: tests compile and fail before implementation.

# Model

Haiku — single-file unit tests over `tmp_path` trees with exact return-value assertions.

# Wave

2
