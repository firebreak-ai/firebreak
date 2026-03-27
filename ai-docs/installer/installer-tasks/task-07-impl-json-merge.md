---
id: T-07
type: implementation
wave: 3
covers: [AC-01, AC-02, AC-09]
files_to_create: [installer/merge-settings.py]
files_to_modify: []
test_tasks: [T-02, T-03]
completion_gate: "Tests from T-02 and T-03 pass"
---

## Objective

Implement the Python 3 JSON merge script that additively merges firebreak hooks and env into an existing settings.json, outputs the merged result, and outputs a manifest record of what was actually added.

## Context

The installer delegates all JSON manipulation to this script. It takes two file paths as arguments: the existing settings.json and the firebreak settings entries JSON. It writes two JSON objects to stdout, separated by a newline: the first is the merged settings, the second is a manifest record of what was actually added (hooks added, env keys added). The test tasks T-02 and T-03 call this script directly with fixture files from `tests/fixtures/installer/`.

The existing codebase has Python scripts in `home/dot-claude/hooks/sdl-workflow/` (e.g., `config-loader.py`, `state-engine.py`). This script lives in `installer/` rather than `home/dot-claude/` because it is a build-time tool, not an installed runtime asset. The `installer/` directory does not exist yet.

Follow the pattern in `home/dot-claude/hooks/sdl-workflow/config-loader.py` for: shebang line, module docstring, `main()` function guarded by `if __name__ == "__main__"`, and argparse for CLI arguments.

## Instructions

1. Create `installer/merge-settings.py` with shebang `#!/usr/bin/env python3` and a module docstring: `"""Merge firebreak settings entries into an existing settings.json."""`

2. Import `json`, `sys`, `os`.

3. Implement `load_json(file_path)`:
   - Read and parse the file as JSON.
   - If the file does not exist or is empty, return an empty dict `{}`.
   - If the file contains malformed JSON, print an error to stderr: `"Error: Malformed JSON in <file_path>: <error detail>"` and call `sys.exit(1)`.
   - Return the parsed dict.

4. Implement `merge_hooks(existing_hooks, new_hooks)`:
   - `existing_hooks` and `new_hooks` are dicts where keys are hook event names (e.g., `"TaskCompleted"`) and values are arrays of matcher-group objects.
   - For each event key in `new_hooks`:
     - If the key does not exist in `existing_hooks`, add it with the full array from `new_hooks`.
     - If the key exists, append each matcher group from `new_hooks[key]` to `existing_hooks[key]` ONLY if no identical matcher group already exists in the array.
   - Deduplication comparison: two matcher groups are identical if they have the same set of keys with the same values. Use `json.dumps(group, sort_keys=True)` to produce a canonical string for comparison. This means a matcher group with a `matcher` field is different from one without, even if the `hooks` array is identical.
   - Return the merged hooks dict.
   - Also return a dict of hooks that were actually added (same structure: event name -> array of added matcher groups). This is the "hooks_added" manifest record.

   Signature: `def merge_hooks(existing_hooks, new_hooks)` returning `(merged_hooks, hooks_added)`.

5. Implement `merge_env(existing_env, new_env)`:
   - `existing_env` and `new_env` are dicts of string key-value pairs.
   - For each key in `new_env`:
     - If the key does not exist in `existing_env`, add it with the value from `new_env`.
     - If the key already exists, skip it (do not overwrite).
   - Return the merged env dict.
   - Also return a dict of env keys that were actually added (key -> value, only for keys that did not previously exist). This is the "env_added" manifest record.

   Signature: `def merge_env(existing_env, new_env)` returning `(merged_env, env_added)`.

6. Implement `merge_settings(existing, new_entries)`:
   - `existing` is the full parsed settings.json dict.
   - `new_entries` is the parsed firebreak settings JSON dict (contains `hooks` and/or `env` keys).
   - Merge hooks: call `merge_hooks(existing.get("hooks", {}), new_entries.get("hooks", {}))`.
   - Merge env: call `merge_env(existing.get("env", {}), new_entries.get("env", {}))`.
   - Build the result dict: start with a copy of `existing`, update `hooks` with the merged hooks, update `env` with the merged env. Do NOT modify `permissions` or any other top-level key. Do NOT add top-level keys that are not `hooks` or `env` from `new_entries`.
   - Build the manifest record: `{"hooks_added": hooks_added, "env_added": env_added}`.
   - Return `(merged_settings, manifest_record)`.

7. Implement `main()`:
   - Use `argparse` with two positional arguments: `existing_path` (path to existing settings.json) and `new_entries_path` (path to firebreak settings JSON).
   - Load both files with `load_json()`. For `existing_path`, if the file does not exist, treat it as `{}`. For `new_entries_path`, if the file does not exist, print error and exit 1.
   - Call `merge_settings(existing, new_entries)`.
   - Print the merged settings as pretty-printed JSON (indent=2) to stdout on the first output block.
   - Print a separator line: `---MANIFEST---`
   - Print the manifest record as pretty-printed JSON (indent=2) to stdout on the second output block.

8. Guard with `if __name__ == "__main__": main()`.

## Output format

The script writes to stdout in this format:

```
{
  "hooks": { ... },
  "env": { ... },
  "permissions": { ... }
}
---MANIFEST---
{
  "hooks_added": { ... },
  "env_added": { ... }
}
```

The test scripts split on `---MANIFEST---` to parse each JSON block independently.

On malformed JSON input, the script writes to stderr and exits with code 1. Stdout is empty.

## Files to create/modify

- `installer/merge-settings.py` (create) -- New file in new `installer/` directory. This is a build-time tool, not a runtime asset, so it does not belong in `home/dot-claude/`.

## Test requirements

Run `bash tests/installer/test-json-merge-hooks.sh` from project root. All 5 tests pass.
Run `bash tests/installer/test-json-merge-env.sh` from project root. All 6 tests pass.

## Acceptance criteria

- AC-01: The merge script does not modify `permissions.allow`, `permissions.deny`, or `permissions.ask` in the output. The `permissions` key in the output is byte-for-byte identical to the input.
- AC-02: After merge, `hooks` contains all firebreak entries AND all pre-existing entries. `env` contains all firebreak entries AND all pre-existing entries. Existing env keys are not overwritten.
- AC-09: The merge script exits non-zero with a clear error on stderr when the input settings.json is malformed JSON. Stdout is empty on error.

## Model

Sonnet

## Wave

1
