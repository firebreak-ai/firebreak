---
id: task-40
type: implementation
wave: 1
covers: [AC-02, AC-09]
files_to_create:
  - assets/fbk-scripts/fbk/config.py
test_tasks: [task-10]
completion_gate: "task-10 tests pass"
---

## Objective

Relocate `assets/hooks/fbk-sdl-workflow/config-loader.py` to `assets/fbk-scripts/fbk/config.py` with PyYAML import guarding.

## Context

`config-loader.py` (157 lines) implements layered config merging with `merge_configs(*dicts)`, `load_yaml(file_path)`, `parse_frontmatter(spec_path)`, `load_config(project_root, spec_path)`, `load_verify(project_root)`, and `cold_start_check(project_root)`. It uses `import yaml` at the top level. Per AC-09, the import must be guarded with try/except to produce exit code 2 and "PyYAML required" on stderr if PyYAML is missing. The `DEFAULTS` dict has keys: `token_budget`, `max_concurrent_agents`, `escalation_cap`, `model`.

## Instructions

1. Create `assets/fbk-scripts/fbk/config.py` by copying the content of `assets/hooks/fbk-sdl-workflow/config-loader.py`
2. Replace the bare `import yaml` with a try/except guard:
   ```python
   try:
       import yaml
   except ImportError:
       print("Error: PyYAML required. Install: pip install pyyaml", file=sys.stderr)
       sys.exit(2)
   ```
3. Replace the `if __name__ == "__main__":` block with a `main()` function containing the same argparse logic
4. Keep all function signatures identical: `merge_configs(*dicts)`, `load_yaml(file_path)`, `parse_frontmatter(spec_path)`, `load_config(project_root, spec_path=None)`, `load_verify(project_root)`, `cold_start_check(project_root)`
5. Preserve exit codes: `sys.exit(1)` for YAML parse errors, `sys.exit(2)` for unknown command, `sys.exit(2)` for missing PyYAML

## Files to create/modify

- **Create**: `assets/fbk-scripts/fbk/config.py`

## Test requirements

- task-10: `merge_configs` merges disjoint keys, later overrides earlier, deep merge for nested dicts, three-layer precedence, `load_yaml` with non-existent path returns `{}`, `parse_frontmatter` returns parsed dict, missing PyYAML exits 2 with "PyYAML required"

## Acceptance criteria

- AC-02: config-loader.py relocated and importable as `fbk.config`
- AC-09: missing PyYAML produces exit code 2 with clear error

## Model

Haiku

## Wave

1
