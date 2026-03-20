## Objective

Implement the config loader as a Python script that merges layered configuration and performs cold-start detection, and create the config.yml schema documentation.

## Context

The config loader merges three configuration layers with more-specific-wins precedence: hardcoded defaults < project `.claude/automation/config.yml` < spec YAML frontmatter. It also loads `verify.yml` independently and checks for cold-start prerequisites. The loader must handle missing files gracefully (use defaults), detect malformed YAML clearly, and never block on missing prerequisites (warn only).

The script uses Python 3 with PyYAML (`import yaml`) for YAML parsing. PyYAML is an accepted project dependency.

The config.yml schema documentation is part of this task because it documents the format the loader parses. The verify.yml schema documentation is created in task-10 alongside the hash gate.

## Instructions

1. Create `home/dot-claude/hooks/sdl-workflow/config-loader.py`. Add shebang `#!/usr/bin/env python3` and module docstring.

2. Define `DEFAULTS` as a dictionary constant:
   ```python
   DEFAULTS = {
       "token_budget": None,
       "max_concurrent_agents": 1,
       "replan_cap": 2,
       "model": "sonnet",
   }
   ```

3. Implement `load_yaml(file_path)`: Read and parse a YAML file. Return a dictionary. On parse error, print a clear error message to stderr including the file path and error detail, then exit 1. Return empty dict if file doesn't exist.

4. Implement `parse_frontmatter(spec_path)`: Read the spec file. If the file starts with `---` on the first line, find the closing `---` and parse the content between them as YAML. Return the parsed dict. Return empty dict if no frontmatter or file doesn't exist.

5. Implement `merge_configs(*dicts)`: Merge dictionaries left to right (later dicts override earlier). For each key, if the value in the later dict is a dict and the existing value is also a dict, merge recursively. Otherwise, the later value replaces the earlier value unconditionally — every key present in the override dict wins regardless of its value, including None.

6. Implement `load_config(project_root, spec_path=None)`:
   - Start with `DEFAULTS`.
   - Load project config from `<project_root>/.claude/automation/config.yml` if it exists.
   - If `spec_path` provided, parse frontmatter from the spec file.
   - Merge: defaults <- project config <- spec frontmatter.
   - Print merged config as JSON (indented) to stdout.

7. Implement `load_verify(project_root)`:
   - Load `<project_root>/.claude/automation/verify.yml`.
   - If file doesn't exist, print `{}` to stdout and exit 0.
   - Print contents as JSON to stdout.

8. Implement `cold_start_check(project_root)`:
   - Check for test runner: look for any of `package.json`, `Cargo.toml`, `go.mod`, `pytest.ini`, `pyproject.toml` in project root, or `Makefile` containing a `test` target (grep for `test:` in Makefile).
   - Check for linting config: look for files matching `.eslintrc*` in project root, or `pyproject.toml` containing `ruff` or `flake8`, or `.golangci.yml`.
   - Check for `CLAUDE.md` in project root.
   - For each missing category, print a warning to stderr: `"Warning: No <category> detected in <project_root>"`.
   - Always exit 0 regardless of findings.

9. Implement `main()` with `argparse`:
   - Subcommands: `load`, `load-verify`, `cold-start-check`.
   - `load` takes positional `project-root` and optional positional `spec-path`.
   - `load-verify` takes positional `project-root`.
   - `cold-start-check` takes positional `project-root`.
   - Route to corresponding function.

10. Guard with `if __name__ == "__main__": main()`.

11. Create `home/dot-claude/docs/sdl-workflow/config-yml-schema.md` with the following content:

    Document the config.yml schema. Structure:
    - `token_budget`: integer or null (null = no limit). Default: null.
    - `max_concurrent_agents`: integer. Default: 1.
    - `replan_cap`: integer, max replan attempts per task. Default: 2.
    - `model`: string or object. As string: default model for all stages. As object: `default` key plus per-stage overrides.
    - State the layering order: hardcoded defaults < project config.yml < spec YAML frontmatter.
    - Include one complete example config.yml.

12. Create `home/dot-claude/docs/sdl-workflow/task-file-schema.md` documenting the task file format used by the breakdown and task reviewer:

    - Task files are Markdown with YAML frontmatter between `---` markers.
    - Required frontmatter fields for all tasks: `id` (string, task identifier), `type` (`test` or `implementation`), `wave` (integer, execution wave), `covers` (list of `AC-NN` strings), `completion_gate` (string, what proves this task is done).
    - At least one of `files_to_create` (list of paths) or `files_to_modify` (list of paths) must be present and non-empty.
    - Implementation tasks (`type: implementation`) additionally require `test_tasks` (list of task ID strings referencing test tasks this implementation depends on).
    - Markdown body sections: Objective, Context, Instructions, Files to create/modify, Test requirements, Acceptance criteria, Model, Wave.
    - Include one complete example showing a test task and one implementation task.

## Files to create/modify

- `home/dot-claude/hooks/sdl-workflow/config-loader.py` (create)
- `home/dot-claude/docs/sdl-workflow/config-yml-schema.md` (create)
- `home/dot-claude/docs/sdl-workflow/task-file-schema.md` (create)

## Test requirements

Tests from task-05 must pass. Run `bash tests/sdl-workflow/test-config-loader.sh` from project root and verify all tests pass.

## Acceptance criteria

AC-03: Project configuration loads `config.yml` and `verify.yml` with layered precedence (global -> project -> spec). Cold-start detection warns on missing prerequisites without blocking.

Primary AC: all tests from task-05 pass.

## Model

Sonnet

## Wave

1
