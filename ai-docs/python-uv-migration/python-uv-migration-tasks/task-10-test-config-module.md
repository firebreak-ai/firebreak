---
id: task-10
type: test
wave: 1
covers: [AC-02, AC-09]
files_to_create:
  - assets/fbk-scripts/tests/test_config.py
completion_gate: "tests compile and fail before implementation"
---

## Objective

Create pytest unit tests for `fbk.config` layered config merging and PyYAML error handling.

## Context

`config-loader.py` implements `load_config()` which merges DEFAULTS, project config (`.claude/automation/config.yml`), and spec frontmatter with correct precedence — later sources override earlier ones, with deep merge for nested dicts. Follow test scenarios from `tests/sdl-workflow/test-config-loader.sh`. The module requires PyYAML — AC-09 requires that a missing PyYAML produces exit code 2 with "PyYAML required" on stderr.

## Instructions

1. Create `assets/fbk-scripts/tests/test_config.py`
2. Import `merge_configs`, `load_yaml`, `parse_frontmatter` from `fbk.config`
3. Write a test: `merge_configs({"a": 1}, {"b": 2})` → assert result is `{"a": 1, "b": 2}`
4. Write a test: `merge_configs({"a": 1}, {"a": 2})` → assert result is `{"a": 2}` (later wins)
5. Write a test: `merge_configs({"x": {"y": 1}}, {"x": {"z": 2}})` → assert result is `{"x": {"y": 1, "z": 2}}` (deep merge)
6. Write a test: `merge_configs(DEFAULTS, project, spec)` where spec overrides a DEFAULTS key — assert spec value wins
7. Write a test: `load_yaml` with a non-existent path → assert returns `{}`
8. Write a test: `parse_frontmatter` with valid YAML frontmatter → assert returns parsed dict
9. Write a test: patch `yaml` as unimportable, import `fbk.config` → assert `SystemExit` with code 2 and stderr contains "PyYAML required"

## Files to create/modify

- **Create**: `assets/fbk-scripts/tests/test_config.py`

## Test requirements

| Level | Behavior | Expected assertion |
|-------|----------|--------------------|
| Unit | disjoint configs merged | result has both keys |
| Unit | later config overrides earlier | result["a"] == 2 |
| Unit | nested dicts deep merged | result["x"] has both y and z |
| Unit | three-layer precedence correct | spec value overrides default |
| Unit | non-existent path returns empty dict | result == {} |
| Unit | valid frontmatter parsed | returns dict matching YAML content |
| Unit | missing PyYAML exits with clear error | SystemExit code 2, stderr has "PyYAML required" |

## Acceptance criteria

- AC-02: validates config-loader.py relocated and importable as `fbk.config`
- AC-09: modules requiring PyYAML fail with clear error when PyYAML missing

## Model

Haiku

## Wave

1
