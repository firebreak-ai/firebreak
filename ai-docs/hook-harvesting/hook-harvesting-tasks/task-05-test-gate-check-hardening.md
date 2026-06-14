---
id: task-05
type: test
wave: 2
covers: [AC-22, AC-23]
files_to_create:
  - assets/fbk-scripts/tests/test_capture_gate_check_hardening.py
completion_gate: "tests compile and fail before implementation"
---

# Objective

Write the unit tests for the capture gate's three security hardenings: Firebreak detection requires a Firebreak-specific marker sentinel (not the bare `.claude/automation/` directory); the privileged `full` level is honored only with an out-of-tree operator signal; and the capture directory and config are realpath-confined under the project root, with symlinked dir/config refused.

# Context

The capture gate is the single control between "measure my own pipeline" and "record prompts in every repo I open," so three weaknesses are closed:

- **Firebreak-specific marker.** `.claude/automation/` is a shared Claude namespace a hostile repo could ship; the gate instead keys on a Firebreak-specific sentinel the installer writes (a file under `.claude/automation/`, e.g. `.fbk-managed`). The bare directory alone must not instrument the project.
- **Out-of-tree `full` corroboration.** Any in-tree file is attacker-shippable, so `full` is honored only when an operator-controlled signal living outside the repo working tree corroborates it. Two pinned channels: the environment variable `FBK_CAPTURE_LEVEL=full`, OR a marker in the operator's global Claude directory keyed to the project path. The gate reads the global dir via `CLAUDE_CONFIG_DIR` (default `~/.claude`), so a test redirects the global-dir lookup by setting `CLAUDE_CONFIG_DIR` to a fixture dir that holds the marker. An in-tree `capture.cfg` requesting `full` without either corroboration is clamped to `standard`. The low-harm off/standard opt-in stays in-tree.
- **Realpath confinement.** A symlinked `.fbk-capture/` directory or symlinked `capture.cfg` would let a write follow the link outside the project tree; the gate realpath-confines `.fbk-capture/` to a real directory under the resolved project root and refuses a symlinked config, treating either as uninstrumented.

Exercise through `tmp_path`, `monkeypatch` (for the env var and for the global-dir location), `capsys`. Import `from fbk.capture import gate_check` inside `try/except ImportError` with a module-level skipif. Use `capture_fixtures.make_project`.

Signatures called: `gate_check.project_is_instrumented(cwd) -> bool`, `gate_check.resolve_capture_level(cwd) -> "off"|"standard"|"full"`.

# Instructions

1. Create `tests/test_capture_gate_check_hardening.py`; import `gate_check` inside `try/except ImportError`; module-level skipif.
2. `test_bare_automation_dir_is_not_instrumented`: build a project with `.claude/automation/` present but NO `.fbk-managed` sentinel and no `capture.cfg`; assert `project_is_instrumented(root) is False`.
3. `test_sentinel_makes_project_instrumented`: add the `.fbk-managed` sentinel to that same dir; assert `project_is_instrumented(root) is True`. Pair with step 2 as the before/after of the marker hardening.
4. `test_in_tree_full_clamped_to_standard_without_corroboration`: build a project whose `capture.cfg` contains `capture_level=full`, with NO env var and NO global-dir marker; assert `resolve_capture_level(root) == "standard"`.
5. `test_full_honored_with_env_corroboration`: same in-tree `capture_level=full` cfg, plus `monkeypatch.setenv("FBK_CAPTURE_LEVEL", "full")`; assert `resolve_capture_level(root) == "full"`.
6. `test_full_honored_with_global_marker_corroboration`: same in-tree cfg, no env var; instead `monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(<fixture global dir>))` and place an operator marker keyed to the project path inside that fixture dir; assert `resolve_capture_level(root) == "full"`. Use the project-path-keyed marker form the gate reads (a file under the fixture `CLAUDE_CONFIG_DIR` named for or containing the project root path); state in the test the exact marker location/shape you wrote so the impl agent matches it.
7. `test_symlinked_capture_dir_treated_uninstrumented`: create a real directory outside the project root, symlink `<root>/.fbk-capture` to it (with a `capture.cfg` inside the link target); assert `project_is_instrumented(root) is False` AND `resolve_capture_level(root) == "off"` (the symlinked capture dir is refused). Skip the test on platforms without symlink support (`pytest.skip` when `os.symlink` raises).
8. `test_symlinked_config_refused`: create a real `.fbk-capture/` under the root but make `capture.cfg` a symlink pointing outside the tree; assert the project is treated as uninstrumented (`resolve_capture_level(root) == "off"`).

# Files to create/modify

- `tests/test_capture_gate_check_hardening.py`

# Test requirements

- `test_bare_automation_dir_is_not_instrumented` (unit): bare `.claude/automation/` → not instrumented.
- `test_sentinel_makes_project_instrumented` (unit): sentinel present → instrumented.
- `test_in_tree_full_clamped_to_standard_without_corroboration` (unit): in-tree full with no out-of-tree signal → standard.
- `test_full_honored_with_env_corroboration` (unit): in-tree full + env var → full.
- `test_full_honored_with_global_marker_corroboration` (unit): in-tree full + global-dir marker → full.
- `test_symlinked_capture_dir_treated_uninstrumented` (unit): symlinked `.fbk-capture/` → uninstrumented/off.
- `test_symlinked_config_refused` (unit): symlinked `capture.cfg` → uninstrumented/off.

# Acceptance criteria

AC-22 (Firebreak-specific marker + out-of-tree full corroboration), AC-23 (realpath confinement + symlink refusal). Gate: tests compile and fail before implementation.

# Model

Sonnet — symlink and out-of-tree-signal scenarios need judgment.

# Wave

2
