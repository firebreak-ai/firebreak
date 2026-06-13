---
id: task-37
type: implementation
wave: 5
covers: [AC-19]
files_to_modify:
  - installer/merge-settings.py
  - assets/settings.json
  - installer/install.sh
test_tasks: [task-20]
completion_gate: "task-20 tests pass"
dependencies: [task-29]
---

# 1 Objective

Migrate the installer to register the global hook router for Claude's hook events, remove any leftover project-level router registration anchored to the old command string (net-new removal logic — today's merge is add-only), gitignore `.fbk-capture/`, and keep all of it idempotent across re-runs with unrelated hook entries left byte-intact. Three files participate; the removal capability lives in `merge-settings.py` so it is hermetically testable.

# 2 Context

The installer is `installer/install.sh`, which delegates the settings merge to `installer/merge-settings.py` merging the `assets/settings.json` template (the merged template, currently registering only the `TaskCompleted` hook). Three changes:
1. **Register the router** for the Claude hook events by adding entries to `assets/settings.json`. The router command must resolve to the router under the GLOBAL fbk-scripts tree on BOTH global and project installs — but `install.sh`'s `sed` rewrites `\"$HOME\"/.claude/` → `\"$CLAUDE_PROJECT_DIR\"/.claude/` for project installs (line 343). So the router command must be written in a form the sed does NOT rewrite to a per-project path, i.e. it must resolve to the one global fbk-scripts path regardless of the rewrite (use a `$HOME`-anchored path the sed would rewrite ONLY if it matched the `\"$HOME\"/.claude/` pattern — choose a form that the existing sed leaves pointing at the global tree; the simplest is to anchor the router command on `$HOME/.claude/fbk-scripts/...` and EXCLUDE the router entry from the project-install sed rewrite, or write it so the rewrite is a no-op for it). The test asserts the merged router command is NOT the old per-project `$CLAUDE_PROJECT_DIR/hooks/hook_router.py` form and points under the global fbk-scripts tree.
2. **Remove the leftover project-level router registration** from the earlier capture experiment, anchored to the EXACT old command string `$CLAUDE_PROJECT_DIR/hooks/hook_router.py`, leaving every other hook entry byte-intact and idempotent across re-runs. This is NET-NEW logic — `merge_hooks` is add-only (canonicalize-and-append), so removal is a new capability with its own home.
3. **Gitignore `.fbk-capture/`** (data, `capture.cfg`, and `locked/`).

The router is registered for the Claude hook events the router records: tool use (`PreToolUse`, `PostToolUse`, `PostToolUseFailure`), prompt submission (`UserPromptSubmit`), subagent lifecycle (`SubagentStart`, `SubagentStop`), and session lifecycle (`SessionStart`, `SessionEnd`, `Stop`, `Notification`). The router lives at `fbk/capture/hook_router.py` under the global fbk-scripts tree, invoked as `python3 "$HOME"/.claude/fbk-scripts/fbk/capture/hook_router.py`.

This task touches THREE files — justified: the removal capability is net-new Python in `merge-settings.py` (so it is unit-testable hermetically), the template entries live in `assets/settings.json`, and the gitignore step plus invoking the removal pass live in `install.sh`. They are one coherent migration; splitting would scatter a single feature across uncoordinated tasks. The hermetic test (task-20) exercises the `merge-settings.py` layer (the removal function + merge) and the template, NOT the shell.

# 3 Instructions

1. **`installer/merge-settings.py` — add `remove_hook_command`.** Implement `remove_hook_command(existing_hooks: list, command_anchor: str) -> list`. It takes a hooks structure (the per-event list of hook groups) and returns it with any hook group whose command equals (or contains) `command_anchor` removed, leaving all other groups byte-intact and in order. Make it operate per-event-list so the merge path can apply it to each event's groups. Completion: a hooks list carrying the old `$CLAUDE_PROJECT_DIR/hooks/hook_router.py` command has that group removed; unrelated groups survive deep-equal.
2. **Invoke removal in the merge path.** Wire `remove_hook_command` into `merge_hooks`/`merge_settings` so the merge applies the removal (anchored to the old command string `$CLAUDE_PROJECT_DIR/hooks/hook_router.py`) BEFORE/AFTER adding the new global router entries — such that after a merge: the old per-project router registration is gone, exactly ONE (global) router registration remains, and a second merge over the output is idempotent (no duplicate, no destructive re-removal). Keep `merge_hooks`'s existing add-only behavior for everything else. Completion: after merge exactly one router registration remains; a second run deep-equals the first; an unrelated operator hook entry is unchanged.
3. **`assets/settings.json` — add router registration.** Add hook entries registering `python3 "$HOME"/.claude/fbk-scripts/fbk/capture/hook_router.py` under each of the router's Claude hook events (`PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `UserPromptSubmit`, `SubagentStart`, `SubagentStop`, `SessionStart`, `SessionEnd`, `Stop`, `Notification`), in the same shape as the existing `TaskCompleted` entry (a `{"hooks": [{"type": "command", "command": ...}]}` group). The command must resolve to the single global fbk-scripts path on both install modes; ensure the project-install `sed` rewrite does not turn the router command into a per-project path (coordinate the path form with the install.sh handling in step 5). Completion: the merged template carries the global router registration and the test's global-path assertion passes (not the old per-project form).
4. **Gitignore directive for `.fbk-capture/`.** Ensure `.fbk-capture/` is gitignored by the installer. If the gitignore is a directive the template carries that `install.sh` consumes, add the `.fbk-capture/` ignore line where the merge/template declares it so the test can assert it at the Python/template layer; otherwise add the gitignore write to `install.sh` and carry a `.fbk-capture/` token in the template the test reads. The test asserts the `.fbk-capture/` ignore directive is present in the merged/template output. Completion: `.fbk-capture/` is covered by the installer's gitignore handling and the directive is present where the test reads it.
5. **`installer/install.sh` — invoke removal + handle the router path under sed.** Ensure the merge path invokes the new removal (it does automatically if step 2 wires it into `merge_settings`, which `install.sh` already calls). Adjust the project-install `sed` (line 343) so the router command resolves to the GLOBAL fbk-scripts path on project installs too — the router must point at the one global tree regardless of install mode (the prototype's per-project path is what we are removing, so re-introducing a per-project path via the rewrite would defeat the migration). Add the `.fbk-capture/` gitignore step here if it is not handled purely at the template layer. Completion: a project install leaves the router command pointing at the global fbk-scripts tree, and `.fbk-capture/` is gitignored.

# 4 Files to create/modify

- Modify `installer/merge-settings.py` (add `remove_hook_command`; wire it into the merge path)
- Modify `assets/settings.json` (add the global router hook registration)
- Modify `installer/install.sh` (invoke removal via the merge; keep the router command global under the sed rewrite; gitignore `.fbk-capture/`)

# 5 Test requirements

Makes task-20 (`tests/test_install_migration.py`) pass: the old `$CLAUDE_PROJECT_DIR/hooks/hook_router.py` registration is removed with exactly one global router registration remaining; an unrelated operator hook entry survives deep-equal; a second merge is idempotent; the merged router command resolves to the global fbk-scripts path (not the per-project form); `.fbk-capture/` is gitignored (directive present in the merged/template output). The test loads `merge-settings.py` by path and calls `remove_hook_command` + the merge directly.

# 6 Acceptance criteria

Primary: task-20's tests pass. Covers AC-19 (anchored duplicate-registration removal, byte-intact siblings, idempotent re-run, global-path resolution, `.fbk-capture/` gitignored).

# 7 Model

Sonnet

# 8 Wave

5
