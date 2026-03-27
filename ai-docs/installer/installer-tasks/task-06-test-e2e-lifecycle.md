---
id: T-06
type: test
wave: 6
covers: [AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-07, AC-08]
files_to_create: [tests/installer/test-e2e-lifecycle.sh]
completion_gate: "Tests compile and fail before implementation begins"
---

## Objective

Write a single end-to-end lifecycle test that exercises the full install, verify, upgrade, verify, uninstall, verify sequence in one continuous test run, confirming the complete user journey works correctly.

## Context

This test covers the spec's UV-1 through UV-4 verification steps as an automated sequence. It runs against `installer/install.sh` with a mock source tree and isolated temp target directory. The test verifies that each phase leaves the filesystem in the expected state before proceeding to the next phase.

Follow the TAP format pattern in `tests/sdl-workflow/test-spec-validator.sh`.

## Instructions

1. Create `tests/installer/test-e2e-lifecycle.sh`. Set up TAP boilerplate.

2. Define variables: `SCRIPT_DIR`, `PROJECT_ROOT`, `INSTALL_SCRIPT`. Create `setup_mock_source()` identical to T-04. Register cleanup trap.

3. Set up the mock source tree and a target directory with a pre-existing `settings.json` containing user hooks and env:
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{"type": "command", "command": "/usr/local/bin/user-guard.sh"}]
      }
    ]
  },
  "permissions": {
    "allow": ["Read"]
  },
  "env": {
    "USER_VAR": "keep-me"
  }
}
```

4. **Phase 1: Fresh install**. Run `bash "$INSTALL_SCRIPT" --target "$TARGET" --source "$MOCK_SOURCE/home/dot-claude"`. Assert exit 0.

5. Write test: **post-install: fbk files exist**. Assert at least 4 `fbk-`-prefixed files exist in the target (check `skills/fbk-spec/prompt.md`, `agents/fbk-code-review-detector.md`, `hooks/fbk-sdl-workflow/task-completed.sh`, `docs/fbk-sdl-workflow/guide.md`).

6. Write test: **post-install: CLAUDE.md not installed**. Assert `$TARGET/CLAUDE.md` does not exist.

7. Write test: **post-install: manifest exists**. Assert `$TARGET/.firebreak-manifest.json` exists and is valid JSON.

8. Write test: **post-install: hooks merged additively**. Parse `$TARGET/settings.json`. Assert `hooks.PreToolUse` contains the original user entry (command contains `user-guard.sh`). Assert `hooks.TaskCompleted` contains the firebreak entry (command contains `fbk-sdl-workflow`).

9. Write test: **post-install: permissions untouched**. Parse `$TARGET/settings.json`. Assert `permissions.allow` equals `["Read"]`.

10. Write test: **post-install: env merged**. Parse `$TARGET/settings.json`. Assert `env.USER_VAR` equals `"keep-me"`. Assert `env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` equals `"1"`.

11. Write test: **post-install: backup created**. Assert `$TARGET/settings.json.pre-firebreak` exists. Parse it and assert it contains the original user hooks (command contains `user-guard.sh`) and does NOT contain firebreak entries.

12. **Phase 2: Upgrade**. Modify one mock source file: change `$MOCK_SOURCE/home/dot-claude/skills/fbk-spec/prompt.md` to contain "updated spec prompt". Re-run install.

13. Write test: **post-upgrade: fbk file updated**. Assert `$TARGET/skills/fbk-spec/prompt.md` contains "updated spec prompt".

14. Write test: **post-upgrade: no duplicate hooks**. Parse `$TARGET/settings.json`. Assert `hooks.TaskCompleted` has exactly 1 entry.

15. Write test: **post-upgrade: user content preserved**. Assert `$TARGET/settings.json` still has `hooks.PreToolUse` with `user-guard.sh`, `permissions.allow` with `["Read"]`, and `env.USER_VAR` with `"keep-me"`.

16. **Phase 3: Uninstall**. Run `bash "$INSTALL_SCRIPT" --uninstall --target "$TARGET"`.

17. Write test: **post-uninstall: fbk files removed**. Assert `$TARGET/skills/fbk-spec/prompt.md` does not exist. Assert `$TARGET/agents/fbk-code-review-detector.md` does not exist.

18. Write test: **post-uninstall: manifest removed**. Assert `$TARGET/.firebreak-manifest.json` does not exist.

19. Write test: **post-uninstall: firebreak hooks removed from settings.json**. Parse `$TARGET/settings.json`. Assert `hooks.TaskCompleted` does not exist or is empty. Assert `hooks.PreToolUse` still contains the user entry (command contains `user-guard.sh`).

20. Write test: **post-uninstall: firebreak env removed, user env preserved**. Parse `$TARGET/settings.json`. Assert `env` does not contain `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`. Assert `env.USER_VAR` equals `"keep-me"`.

21. Write test: **post-uninstall: permissions still untouched**. Parse `$TARGET/settings.json`. Assert `permissions.allow` equals `["Read"]`.

22. Write test: **post-uninstall: backup retained**. Assert `$TARGET/settings.json.pre-firebreak` still exists.

23. End with summary and exit.

## Files to create/modify

- `tests/installer/test-e2e-lifecycle.sh` (create)

No existing file is the right location — this is a new e2e test in the new `tests/installer/` directory.

## Test requirements

Tests to write (all in `test-e2e-lifecycle.sh`):
1. Post-install: fbk-prefixed files exist
2. Post-install: CLAUDE.md not installed
3. Post-install: manifest exists and is valid JSON
4. Post-install: hooks merged additively (user + firebreak)
5. Post-install: permissions untouched
6. Post-install: env merged (user + firebreak)
7. Post-install: settings.json backup created with original content
8. Post-upgrade: fbk file updated to new version
9. Post-upgrade: no duplicate hooks
10. Post-upgrade: user content preserved
11. Post-uninstall: fbk files removed
12. Post-uninstall: manifest removed
13. Post-uninstall: firebreak hooks removed, user hooks preserved
14. Post-uninstall: firebreak env removed, user env preserved
15. Post-uninstall: permissions still untouched
16. Post-uninstall: backup retained

## Acceptance criteria

- AC-01: Permissions not modified at any stage.
- AC-02: Hooks and env contain all entries after install/upgrade.
- AC-03: CLAUDE.md not installed.
- AC-04: All assets use fbk- prefix.
- AC-05: Upgrade overwrites fbk files and updates manifest.
- AC-06: Manifest records all installed files and settings entries.
- AC-07: Backup created before modifying settings.json.
- AC-08: Uninstall removes only firebreak entries, preserves user content.

## Model

Sonnet

## Wave

3
