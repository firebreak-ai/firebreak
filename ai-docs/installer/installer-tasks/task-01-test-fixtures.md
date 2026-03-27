---
id: T-01
type: test
wave: 1
covers: []
files_to_create: [tests/fixtures/installer/settings-empty.json, tests/fixtures/installer/settings-existing-hooks.json, tests/fixtures/installer/settings-existing-env.json, tests/fixtures/installer/settings-malformed.json, tests/fixtures/installer/settings-with-permissions.json, tests/fixtures/installer/firebreak-settings.json]
completion_gate: "All fixture files exist and contain valid JSON (except malformed)"
---

## Objective

Create test fixture files that the JSON merge tests and integration tests use as inputs. These are static JSON files representing various `settings.json` states and the firebreak settings entries to merge.

## Context

The installer's JSON merge script takes an existing `settings.json` and firebreak's settings entries, and returns the merged result. Tests need known inputs to assert on outputs. A mock source tree is also needed for integration tests, but that is created at test runtime via a helper function (not static fixtures) because tests need to control directory structure dynamically.

No existing fixture directory covers installer scenarios — `tests/fixtures/` has subdirectories for `specs/`, `config/`, etc., but none for `installer/`. A new `tests/fixtures/installer/` directory is needed.

## Instructions

1. Create `tests/fixtures/installer/settings-empty.json` containing:
```json
{}
```

2. Create `tests/fixtures/installer/settings-existing-hooks.json` containing a settings object with one pre-existing hook event. This represents a user who already has hooks configured:
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "/usr/local/bin/my-bash-guard.sh"
          }
        ]
      }
    ]
  }
}
```

3. Create `tests/fixtures/installer/settings-existing-env.json` containing a settings object with pre-existing env keys, including one key that firebreak also sets (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`):
```json
{
  "env": {
    "MY_CUSTOM_VAR": "my-value",
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "0"
  }
}
```

4. Create `tests/fixtures/installer/settings-malformed.json` containing invalid JSON:
```
{this is not valid json
```

5. Create `tests/fixtures/installer/settings-with-permissions.json` containing a settings object with permissions entries:
```json
{
  "permissions": {
    "allow": ["Read", "Glob"],
    "deny": ["Bash"]
  },
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "/usr/local/bin/my-bash-guard.sh"
          }
        ]
      }
    ]
  }
}
```

6. Create `tests/fixtures/installer/firebreak-settings.json` containing the firebreak settings entries that the merge script adds. This represents what the installer passes as the "new entries" argument:
```json
{
  "hooks": {
    "TaskCompleted": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"$HOME\"/.claude/hooks/fbk-sdl-workflow/task-completed.sh"
          }
        ]
      }
    ]
  },
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

## Files to create/modify

- `tests/fixtures/installer/settings-empty.json` (create)
- `tests/fixtures/installer/settings-existing-hooks.json` (create)
- `tests/fixtures/installer/settings-existing-env.json` (create)
- `tests/fixtures/installer/settings-malformed.json` (create)
- `tests/fixtures/installer/settings-with-permissions.json` (create)
- `tests/fixtures/installer/firebreak-settings.json` (create)

## Test requirements

This is a fixture task. No test assertions — the fixtures are validated by the tests in T-02 and T-03 that consume them.

## Acceptance criteria

- All fixture files exist at the specified paths
- All files except `settings-malformed.json` contain valid JSON
- `settings-malformed.json` contains intentionally invalid JSON
- `firebreak-settings.json` contains a `TaskCompleted` hook entry and an `env` entry for `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`

## Model

Haiku

## Wave

1
