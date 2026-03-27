# Firebreak Installer

## Problem

Firebreak's context assets (skills, agents, hooks, docs, settings) must be copied into `~/.claude/` or a project's `.claude/` directory before they work. Manual installation is error-prone: users miss files, clobber existing settings, or can't cleanly upgrade or remove the tool. There is no way to install, upgrade, or uninstall firebreak without hand-copying files and manually editing JSON.

## Goals / Non-goals

**Goals**

- One-command install via `curl | bash` or clone-and-run. Supports `--dry-run` to preview changes without applying them.
- Support both global (`~/.claude/`) and project-level (`.claude/`) installation targets, chosen at install time.
- Namespace isolation: all firebreak assets use the `fbk-` prefix so they are identifiable and separable from user content.
- Additive hooks/env merging — add entries to `settings.json` without removing or altering existing entries.
- Idempotent: re-running the installer upgrades in place.
- Surgical uninstall that removes only `fbk-`-prefixed files and firebreak settings entries.
- Manifest-based tracking of all installed files and merged config entries.
- Backup `settings.json` before modification.
- Compatible with bash 3.2+ (stock macOS) without requiring newer bash versions.

**Non-goals**

- Modifying Claude Code permissions (`permissions.allow`, `permissions.deny`, `permissions.ask`). Users approve permissions interactively as needed.
- Installing or modifying CLAUDE.md. The repo's CLAUDE.md is a reference artifact, not an installed file.
- Managing `settings.local.json` (user-personal, gitignored).
- Auto-updating (no daemon, cron job, or version-check on session start).
- Supporting Windows (first rev targets macOS/Linux with POSIX shell).
- Interactive TUI or wizard beyond basic prompts.
- Automatic rollback on partial install failure (deferred to a future version).
- Checksum-based user-modification detection on uninstall (deferred to a future version).
- Orphan cleanup on upgrade (deferred to a future version).

## User-facing behavior

### Install

```bash
curl -fsSL https://raw.githubusercontent.com/<owner>/<repo>/main/installer/install.sh | bash
```

Or from a local clone:

```bash
./installer/install.sh
```

To preview without making changes:

```bash
./installer/install.sh --dry-run
```

The installer prompts:

```
Install firebreak globally (~/.claude) or into a project directory?
  [1] Global (~/.claude/)
  [2] Project directory (enter path)
>
```

On selection, the installer:

1. Checks prerequisites (Python 3 available, target directory writable).
2. If the target directory has an existing firebreak manifest, prints "Existing installation detected — upgrading" and runs the upgrade path.
3. Backs up `settings.json` if it exists (`.pre-firebreak` suffix). If a `.pre-firebreak` backup already exists, uses a timestamped suffix instead.
4. Copies `fbk-`-prefixed assets (skills, agents, hooks, docs) into the target directory.
5. Merges hooks and env into the target's `settings.json` — additive only.
6. Writes a manifest file recording everything that was installed or merged.
7. Prints a summary:
   ```
   Firebreak installed to ~/.claude/
     Files installed: 24
     Hooks added: 1
     Backups: ~/.claude/settings.json.pre-firebreak
   ```

### Upgrade

Re-running the installer on an existing installation:

1. Detects the existing manifest.
2. Overwrites all `fbk-`-prefixed files with new versions.
3. Re-merges hooks and env (adds new entries, skips entries already present).
4. Updates the manifest with new timestamps.
5. Prints a summary showing what changed.

Non-`fbk-` files in the target directory are never touched during upgrade.

### Uninstall

```bash
./installer/install.sh --uninstall
```

Or if installed via curl:

```bash
curl -fsSL https://raw.githubusercontent.com/<owner>/<repo>/main/installer/install.sh | bash -s -- --uninstall
```

The uninstaller:

1. Reads the manifest to determine what was installed.
2. Removes all `fbk-`-prefixed files recorded in the manifest.
3. Surgically removes firebreak hook and env entries from `settings.json` (using the entries recorded in the manifest). Does not restore the `.pre-firebreak` backup — surgical removal preserves user changes made after install.
4. Removes empty `fbk-`-prefixed directories left behind.
5. Removes the manifest file itself.
6. Prints a summary:
   ```
   Firebreak uninstalled from ~/.claude/
     Files removed: 24
     Hooks removed: 1
   ```

The `.pre-firebreak` backup is retained as a safety net the user can restore manually if needed.

### Error states

| Condition | Behavior |
|-----------|----------|
| No Python 3 | Exits with error: "Requires Python 3 for JSON merging. Install Python 3 and retry." |
| Target settings.json is malformed JSON | Exits with error, does not modify the file. |
| Manifest missing during uninstall | Exits with error: "No firebreak installation found at <path>." |
| Permission denied on target directory | Exits with error: "Cannot write to <path>. Check permissions." |
| Partial install failure | Prints error describing what failed. Advises user to run `--uninstall` to clean up. The manifest and backup enable recovery. |
| `--dry-run` mode | Prints all operations that would be performed (files copied, hooks added, backups created) without executing them. Exits with 0. |
| Concurrent installation | Not supported. Second instance may produce inconsistent state. |

## Technical approach

### Architecture

The installer is a single shell script (`install.sh`) compatible with bash 3.2+. It avoids associative arrays and other bash 4+ features. Three operational modes: install, upgrade, and uninstall. JSON merging is delegated to an inline Python 3 script.

### Namespace convention

All firebreak assets use the `fbk-` prefix:

| Asset type | Current name | Installed name |
|------------|-------------|----------------|
| Skills | `skills/spec/` | `skills/fbk-spec/` |
| Skills | `skills/breakdown/` | `skills/fbk-breakdown/` |
| Agents | `agents/code-review-detector.md` | `agents/fbk-code-review-detector.md` |
| Hooks dir | `hooks/sdl-workflow/` | `hooks/fbk-sdl-workflow/` |
| Docs dir | `docs/` | `docs/fbk-sdl-workflow/`, `docs/fbk-context-assets/`, etc. |

The prefix serves three purposes:
1. **Identification**: any `fbk-*` asset is firebreak-managed.
2. **Isolation**: the installer never touches non-`fbk-` files. No collision risk with user content.
3. **Cleanup**: uninstall targets `fbk-*` entries in the manifest. No three-way file classification needed.

This requires renaming existing assets in the source tree (`home/dot-claude/`) before the installer can ship. Two classes of cross-references must be updated:
1. **Development-time references** (`home/dot-claude/docs/...`): used within this repo during firebreak development. These route the agent to source docs.
2. **Runtime references** (`"$HOME"/.claude/hooks/...`): used in installed artifacts. These reference the installed location.

Both must carry the `fbk-` prefix after renaming.

### Behaviors

**Prerequisite checking** (computation): Verifies Python 3 is available, validates target directory is writable. Returns a structured result (pass/fail with reasons).

**Target selection** (orchestration): Prompts user for global vs project install. Resolves the target path. Detects existing installation by checking for the manifest file. Routes to install or upgrade path.

**Asset enumeration** (computation): Walks the source `home/dot-claude/` directory tree and produces a list of source-to-destination path mappings. Excludes `CLAUDE.md` and `settings.json` (not installed as files — settings.json is merged, not copied). All destination paths carry the `fbk-` prefix.

**File installation** (orchestration): For each mapped file:
1. Creates the destination directory if needed.
2. Copies the source file to the destination.
3. Records the destination path in the manifest.

**JSON merging** (computation): An inline Python 3 script that takes the existing settings.json and firebreak's settings entries, and returns the merged result.

Merging rules:
- `hooks`: for each hook event, append firebreak's matcher groups to the existing array. Deduplicate by comparing the full matcher-group object (the tuple of `matcher` pattern + `hooks` array contents), not just the command string. Do not remove or reorder existing entries.
- `env`: add firebreak entries. Do not overwrite existing keys with the same name. Only record actually-added keys in the manifest (skip keys that already existed).
- `permissions`: not touched.
- All other top-level keys: preserve existing values, do not add new ones.

**Manifest management** (computation): Reads and writes the manifest file. The manifest tracks:

```json
{
  "schema_version": "1.0.0",
  "installer_version": "0.1.0",
  "firebreak_version": "0.1.0",
  "install_mode": "global",
  "installed_at": "2026-03-26T14:30:00Z",
  "updated_at": "2026-03-26T14:30:00Z",
  "target": "~/.claude",
  "files": [
    "skills/fbk-spec/prompt.md",
    "agents/fbk-code-review-detector.md",
    "hooks/fbk-sdl-workflow/task-completed.sh"
  ],
  "settings_entries": {
    "hooks_added": {
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
    "env_added": {
      "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
    }
  },
  "backups": {
    "settings.json": "settings.json.pre-firebreak"
  }
}
```

The `hooks_added` records complete matcher groups (including the optional `matcher` field when present) so uninstall can match and remove the correct entries. The `env_added` records only keys the installer actually added (not keys that already existed).

**Uninstallation** (orchestration): Reads the manifest, then:
1. For each file in `manifest.files`: delete it.
2. For `manifest.settings_entries.hooks_added`: remove the specific matcher groups from their hook event arrays in settings.json.
3. For `manifest.settings_entries.env_added`: remove each key only if its current value matches what firebreak set. If the user changed the value, leave it.
4. Remove empty `fbk-`-prefixed directories left behind.
5. Remove the manifest.

Does not restore the `.pre-firebreak` backup. Surgical removal preserves user changes made after install. The backup is retained as a manual recovery option.

### Composition

Target selection calls prerequisite checking first. On pass, it calls asset enumeration, then file installation for each mapped file. After file installation completes, it calls JSON merging on `settings.json`. After all operations succeed, it calls manifest management to write the manifest.

If any step fails after partial work, the installer prints the error, notes that `--uninstall` can clean up, and exits non-zero. The manifest (if written) and backup enable recovery.

Uninstallation reads the manifest first. It then removes files, then surgically removes settings entries, then cleans up empty directories, then removes the manifest.

### Integration seam declaration

- [ ] Asset enumeration -> File installation: path mapping format (source path, destination path pairs; all destination paths carry `fbk-` prefix)
- [ ] JSON merging -> Manifest management: the merged entries (complete matcher groups for hooks, actually-added keys for env) must be recorded in the manifest exactly as they were added to settings.json, so uninstall can reverse them
- [ ] Prerequisite checking -> Target selection: prerequisite failure prevents target selection from executing
- [ ] Manifest -> Uninstallation: manifest schema is the contract between install-time recording and uninstall-time reversal; env removal requires value-matching
- [ ] Source tree naming -> Installer path mapping: the `fbk-` prefix must be applied consistently between the source asset names and the installed destination names

### Key decisions

**Single script, Python 3 for JSON manipulation**: Keeps the curl|bash path simple. Python 3 is pre-installed on most Linux distributions and available on macOS. One JSON backend means one code path to test and maintain.

**bash 3.2+ compatibility**: macOS ships bash 3.2 due to Apple's GPLv3 licensing stance. Avoiding associative arrays and other bash 4+ features ensures the `curl | bash` path works on stock macOS without requiring Homebrew.

**No permissions modifications**: Follows the precedent set by GSD and BMAD — neither framework injects permission entries. Users approve permissions interactively as Claude Code prompts them.

**No CLAUDE.md installation**: The repo's `CLAUDE.md` is a reference artifact showing how to configure the always-on layer. Users who want firebreak's CLAUDE.md content can copy it manually.

**`fbk-` namespace prefix**: All installed assets are prefixed, following GSD's `gsd-*` convention. This eliminates the need for three-way file classification — anything `fbk-*` is ours, everything else is untouched.

**Surgical uninstall, not backup restoration**: Uninstall removes only the specific entries firebreak added to settings.json, preserving any user changes made after install. The `.pre-firebreak` backup is a safety net for manual recovery, not the uninstall mechanism. This avoids reverting weeks-old backups that would undo user settings changes.

**No rollback in v1**: Partial install failure is extremely unlikely (small text files to same-permission directories). If it occurs, `--uninstall` provides the recovery path via the manifest. Rollback adds significant implementation complexity for near-zero risk. Defer to a future version if users report partial-install problems.

**No checksum tracking in v1**: The manifest records file paths but not checksums. On uninstall, all manifest files are removed without modification detection. Users who want to preserve customized firebreak files should copy them before uninstalling. Checksum-based modification detection can be added in a future version.

**No orphan cleanup in v1**: Orphaned `fbk-` files from a previous version are inert — they do not break anything. Users can `--uninstall` and reinstall for a clean state. Automatic orphan cleanup can be added in a future version.

**Manifest stored at `<target>/.firebreak-manifest.json`**: Co-located with the installation target. Hidden file to stay out of the way.

**Backup naming: `.pre-firebreak`**: Follows the oh-my-zsh convention. Timestamped if a `.pre-firebreak` backup already exists.

**Installer lives at `installer/install.sh` in the repo**: The `installer/` directory houses the script and any supporting files. The curl one-liner points to this path on the repo's main branch.

**Source tree renamed before installer ships**: The `fbk-` prefix is applied to the source tree (`home/dot-claude/`) as a prerequisite task. Both development-time references (`home/dot-claude/docs/...`) and runtime references (`"$HOME"/.claude/hooks/...`) are updated. The installer copies files as-is with no path translation.

**`--dry-run` supported**: Prints all planned operations (files to copy, hooks to add, backups to create) without executing them.

## Testing strategy

### New tests needed

- **Integration test**: Python 3 JSON merge script adds hooks to an empty `hooks` object — covers AC-02.
- **Integration test**: Python 3 JSON merge script appends matcher groups to existing hook event arrays without removing entries — covers AC-02.
- **Integration test**: Python 3 JSON merge script deduplicates by full matcher-group comparison: re-adding an existing matcher group does not create duplicates, but different matchers with the same command are preserved — covers AC-02.
- **Integration test**: Python 3 JSON merge script adds `env` keys without overwriting existing keys — covers AC-02.
- **Integration test**: Python 3 JSON merge script does not touch `permissions` — covers AC-01.
- **Integration test**: Python 3 JSON merge script records only actually-added env keys (skips pre-existing) — covers AC-02, seam: JSON merging -> Manifest.
- **Integration test**: Asset enumeration excludes CLAUDE.md and settings.json from the file list — covers AC-03.
- **Integration test**: Asset enumeration applies `fbk-` prefix to all destination paths — covers AC-04.
- **Integration test**: Fresh install into empty target directory creates all expected `fbk-`-prefixed files and a valid manifest — covers AC-04, AC-06, UV-1.
- **Integration test**: Fresh install into a project-level `.claude/` directory creates files at the correct project-relative path — covers AC-10, UV-1.
- **Integration test**: Fresh install into target with existing `settings.json` merges hooks additively and creates `.pre-firebreak` backup — covers AC-02, AC-07, UV-2.
- **Integration test**: Fresh install into target with existing non-`fbk-` files leaves them untouched — covers AC-04.
- **Integration test**: Fresh install where `.pre-firebreak` backup already exists creates a timestamped backup instead of overwriting — covers AC-07.
- **Integration test**: Install records merged hooks and env in manifest, then uninstall removes exactly those entries from settings.json — covers seam: JSON merging -> Manifest -> Uninstallation, AC-08.
- **Integration test**: Uninstall env removal checks current value: if user changed the value after install, the key is left in place — covers AC-08.
- **Integration test**: Re-running install on existing installation overwrites `fbk-` files and updates manifest — covers AC-05, UV-3.
- **Integration test**: Uninstall removes only `fbk-`-prefixed files and settings entries recorded in the manifest — covers AC-08, UV-4.
- **Integration test**: Install with no Python 3 available exits with clear error and makes no changes — covers AC-09.
- **Integration test**: Install with malformed target settings.json exits with error and makes no changes — covers AC-09.
- **Integration test**: Install into target with no pre-existing settings.json creates a new settings.json with firebreak entries — covers AC-02.
- **Integration test**: `--dry-run` prints planned operations and makes no changes to the target directory — covers AC-11, UV-6.
- **E2e test**: Full install -> verify files exist and hooks merged -> upgrade with new version -> verify updated -> uninstall -> verify clean state (no `fbk-` files, settings.json has no firebreak entries) — covers UV-1, UV-3, UV-4.

### Existing tests impacted

None — no existing installer tests. The project's `tests/sdl-workflow/` directory uses bash TAP-format test scripts; the installer tests adopt this same pattern.

### Test infrastructure changes

- Test directory: `tests/installer/`.
- Test harness: bash TAP-format scripts, consistent with existing `tests/sdl-workflow/` pattern.
- Test fixture: a mock source tree with representative `fbk-`-prefixed files (3-5 files across skills/, agents/, hooks/, docs/).
- Test fixture: sample `settings.json` files — empty object `{}`, populated with existing hooks and env, malformed JSON.
- Test fixture: sample `settings.json` with pre-existing `.pre-firebreak` backup file.
- Test harness utility: temporary directory creation/cleanup for isolated install targets.
- Test harness utility: PATH manipulation to hide Python 3 for prerequisite-failure tests.

### User verification steps

- UV-1: Run `./installer/install.sh`, select global install -> all `fbk-`-prefixed files appear in `~/.claude/`, manifest exists at `~/.claude/.firebreak-manifest.json`.
- UV-2: Run `./installer/install.sh` with pre-existing `settings.json` containing custom hooks -> after install, original hooks still present AND firebreak hooks added.
- UV-3: Modify a firebreak source file, re-run `./installer/install.sh` -> installed file is updated to new version.
- UV-4: Run `./installer/install.sh --uninstall` -> all `fbk-`-prefixed files removed, firebreak entries removed from settings.json, user's own settings entries preserved.
- UV-5: (Deferred — checksum-based modification detection removed from v1.)
- UV-6: Run `./installer/install.sh --dry-run` -> lists all files that would be copied and hooks that would be added, target directory is unchanged.

## Documentation impact

### Project documents to update

- `README.md`: Add installation instructions with the `curl | bash` one-liner and manual clone instructions.

### New documentation to create

- None — the installer's `--help` output and the README section are sufficient for first rev.

## Acceptance criteria

- AC-01: The installer does not modify `permissions.allow`, `permissions.deny`, or `permissions.ask` in the target `settings.json`.
- AC-02: After install, `hooks` and `env` in target `settings.json` contain all firebreak entries AND all pre-existing entries.
- AC-03: The installer does not install or modify CLAUDE.md in the target directory.
- AC-04: After install, all firebreak assets exist in the target directory with `fbk-` prefixed names. No non-`fbk-` files are created, modified, or removed (except `settings.json` for hook/env merging and the manifest).
- AC-05: Re-running the installer overwrites `fbk-` files with current versions and updates the manifest.
- AC-06: A manifest file at `<target>/.firebreak-manifest.json` records every installed file path and every merged settings entry (complete matcher groups for hooks, actually-added keys for env).
- AC-07: Before modifying `settings.json`, a `.pre-firebreak` backup is created. If a backup already exists, a timestamped backup is created instead.
- AC-08: `--uninstall` removes only `fbk-`-prefixed files and settings entries recorded in the manifest. Env keys are removed only if their current value matches what firebreak set.
- AC-09: The installer exits with a clear error and makes no changes when Python 3 is missing or target settings.json is malformed.
- AC-10: The installer supports both global (`~/.claude/`) and project-level (`.claude/`) targets.
- AC-11: `--dry-run` prints all planned operations without modifying any files or settings.

## Open questions

None — all resolved.

## Dependencies

- bash 3.2+ (avoids bash 4 features to support stock macOS).
- Python 3 for JSON manipulation.
- Standard POSIX utilities: cp, mv, rm, mkdir, sha256sum (or shasum on macOS), grep, sed.
- The firebreak source tree (`home/dot-claude/`) must be available — either bundled in the script (for curl|bash) or in the local clone.
- **Prerequisite**: source tree assets in `home/dot-claude/` renamed with `fbk-` prefix and all internal cross-references updated before the installer can ship. This includes both development-time references (skill prompts, doc routing tables) and runtime references (hook commands, agent definitions). This is a separate task with its own acceptance criteria.
