---
id: T-05
type: test
wave: 4
covers: [AC-02, AC-05, AC-08, AC-09]
files_to_create: [tests/installer/test-upgrade-uninstall.sh]
completion_gate: "Tests compile and fail before implementation begins"
---

## Objective

Write integration tests for `installer/install.sh` covering the upgrade (idempotent re-install) and uninstall paths, including manifest-driven surgical removal and env value-matching on uninstall.

## Context

**Upgrade**: Re-running the installer on an existing installation (detected by the presence of `.firebreak-manifest.json`) overwrites all `fbk-`-prefixed files, re-merges hooks/env (adds new entries, skips already-present), and updates the manifest. Non-`fbk-` files are never touched.

**Uninstall**: `install.sh --uninstall --target <path>` reads the manifest, removes all `fbk-`-prefixed files listed in it, surgically removes firebreak hook entries and env entries from `settings.json`, removes empty `fbk-` directories, and removes the manifest itself. Env keys are removed only if their current value matches what firebreak set (if the user changed the value, the key is left in place). The `.pre-firebreak` backup is retained.

These tests reuse the `setup_mock_source()` pattern from T-04. Each test creates fresh temp directories, installs, then runs upgrade or uninstall.

Follow the TAP format pattern in `tests/sdl-workflow/test-spec-validator.sh`.

## Instructions

1. Create `tests/installer/test-upgrade-uninstall.sh`. Set up TAP boilerplate.

2. Define variables: `SCRIPT_DIR`, `PROJECT_ROOT`, `INSTALL_SCRIPT`. Create `setup_mock_source()` and `setup_target()` functions identical to T-04. Register cleanup trap.

3. Write test: **upgrade overwrites fbk files**. Install into target. Modify `$TARGET/skills/fbk-spec/prompt.md` to contain "user modified this". Re-run install (upgrade path). Assert `$TARGET/skills/fbk-spec/prompt.md` contains "mock spec prompt" (overwritten back to source version), not "user modified this".

4. Write test: **upgrade updates manifest timestamp**. Install into target. Record the `installed_at` or `updated_at` timestamp from the manifest. Sleep 1 second. Re-run install. Parse the updated manifest and assert `updated_at` is different from (later than) the original.

5. Write test: **upgrade does not duplicate hooks**. Install into target. Re-run install. Parse `$TARGET/settings.json` and assert `hooks.TaskCompleted` has exactly 1 entry (not 2).

6. Write test: **upgrade preserves non-fbk files**. Set up target with `$TARGET/agents/my-agent.md` containing "user agent". Install. Re-run install. Assert `$TARGET/agents/my-agent.md` still contains "user agent".

7. Write test: **uninstall removes fbk files**. Install into target. Run `bash "$INSTALL_SCRIPT" --uninstall --target "$TARGET"`. Assert exit 0. Assert `$TARGET/skills/fbk-spec/prompt.md` does not exist. Assert `$TARGET/agents/fbk-code-review-detector.md` does not exist. Assert `$TARGET/hooks/fbk-sdl-workflow/task-completed.sh` does not exist.

8. Write test: **uninstall removes hooks from settings.json**. Install into target (which merges hooks into settings.json). Run uninstall. Parse `$TARGET/settings.json` and assert: the `TaskCompleted` key does not exist in `hooks` (or `hooks.TaskCompleted` is an empty array).

9. Write test: **uninstall removes env keys when value matches**. Install into target (which adds `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS: "1"` to env). Run uninstall. Parse `$TARGET/settings.json` and assert: `env` does not contain `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`.

10. Write test: **uninstall preserves env keys when user changed value**. Install into target. Manually edit `$TARGET/settings.json` to change `env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` from `"1"` to `"custom-value"` using `python3 -c` to modify the JSON. Run uninstall. Parse `$TARGET/settings.json` and assert: `env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` still equals `"custom-value"` (key was NOT removed because value differs from what firebreak set).

11. Write test: **uninstall removes manifest**. Install into target. Run uninstall. Assert `$TARGET/.firebreak-manifest.json` does not exist.

12. Write test: **uninstall removes empty fbk directories**. Install into target. Run uninstall. Assert `$TARGET/hooks/fbk-sdl-workflow/` directory does not exist. Assert `$TARGET/skills/fbk-spec/` directory does not exist.

13. Write test: **uninstall retains pre-firebreak backup**. Set up target with existing `settings.json`. Install (creates `.pre-firebreak` backup). Run uninstall. Assert `$TARGET/settings.json.pre-firebreak` still exists.

14. Write test: **uninstall with no manifest exits with error**. Set up empty target (no manifest). Run `bash "$INSTALL_SCRIPT" --uninstall --target "$TARGET"`. Assert exit code is non-zero. Assert stderr contains "No firebreak installation found" or similar.

15. Write test: **malformed settings.json on install exits with error**. Set up target with a `settings.json` containing invalid JSON. Run install. Assert exit code is non-zero. Assert stderr mentions malformed/invalid JSON. Assert no fbk files were created in the target.

16. End with summary and exit.

## Files to create/modify

- `tests/installer/test-upgrade-uninstall.sh` (create)

No existing file is the right location — this is a new integration test in the new `tests/installer/` directory.

## Test requirements

Tests to write (all in `test-upgrade-uninstall.sh`):
1. Upgrade overwrites fbk-prefixed files with current source versions
2. Upgrade updates manifest timestamp
3. Upgrade does not duplicate hooks in settings.json
4. Upgrade preserves non-fbk files
5. Uninstall removes all fbk-prefixed files from manifest
6. Uninstall removes firebreak hooks from settings.json
7. Uninstall removes env keys when current value matches installed value
8. Uninstall preserves env keys when user changed the value
9. Uninstall removes the manifest file
10. Uninstall removes empty fbk-prefixed directories
11. Uninstall retains .pre-firebreak backup
12. Uninstall with no manifest exits with error
13. Malformed settings.json on install exits with error, no changes made

## Acceptance criteria

- AC-02: After install, `hooks` and `env` contain all firebreak entries AND all pre-existing entries (verified via upgrade not duplicating).
- AC-05: Re-running the installer overwrites `fbk-` files with current versions and updates the manifest.
- AC-08: `--uninstall` removes only `fbk-`-prefixed files and settings entries recorded in the manifest. Env keys removed only if current value matches.
- AC-09: The installer exits with a clear error and makes no changes when target settings.json is malformed.

## Model

Sonnet

## Wave

2
