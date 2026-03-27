Perspectives: Architecture, Pragmatism, Quality

# Installer Spec Review

## Architectural Soundness

### R-01: Hook merge semantics mismatch — deduplication by command is insufficient
**Severity**: blocking

Claude Code hooks use three-level nesting: `hooks[event] -> matcher_group[] -> hooks[]`. A matcher group contains an optional `matcher` regex and a `hooks` array. Two hook entries with the same `command` could legitimately exist under different matchers. The spec's "deduplicate by comparing the `command` field" would silently drop legitimate hooks or create false duplicates when matchers differ.

The deduplication key must be the full matcher-group object, not just the command string. The manifest's `hooks_added` must record the complete matcher group so uninstall can match and remove the correct entry.

### R-02: Uninstall conflict between backup restoration and surgical removal
**Severity**: blocking

The uninstall procedure has a contradiction:
- Step 2: "Remove firebreak hook entries from settings.json" (surgical removal)
- Step 3: "Restore settings.json.pre-firebreak backup if it exists" (wholesale replacement)

These are mutually exclusive. Restoring the backup would undo user settings changes made *after* install (new hooks, env vars, etc.). On a long-lived installation the backup could be weeks stale.

**Resolution**: Make surgical removal the sole uninstall mechanism for settings.json. Keep the backup for rollback-on-install-failure only. If backup restoration is desired, make it an explicit opt-in (`--restore-backup`) with a warning.

### R-03: env merge semantics need value-matching on uninstall
**Severity**: important

The spec says "do not overwrite existing keys with the same name" for env, but the uninstall path has no handling for the case where the installer *didn't* add a key because it already existed. Uninstall should only remove keys that are in `env_added` AND whose current value matches what firebreak set.

### R-04: Rollback does not handle missing pre-install settings.json
**Severity**: important

If the target had no settings.json before install, rollback should delete the installer-created settings.json rather than looking for a nonexistent backup. The spec implies this but does not state it explicitly.

### R-05: Manifest schema missing installer_version and install_mode
**Severity**: informational

The manifest should record which installer version created it (for schema migration) and whether it was a global or project install (for diagnostics). Add `installer_version` and `install_mode` fields.

### R-06: curl|bash bundling strategy unspecified
**Severity**: informational

The spec says the source tree must be "either bundled in the script (for curl|bash) or in the local clone." The bundling mechanism (git clone to temp dir? tarball download? embedded files?) is unspecified. The task breakdown must resolve this before implementation.

## Over-engineering / Pragmatism

### R-07: bash >= 4 requirement excludes stock macOS
**Severity**: blocking

macOS ships bash 3.2 (Apple won't update due to GPLv3). The spec requires bash >= 4 for associative arrays, but the installer copies ~51 files and merges some JSON. Associative arrays are not necessary for this scope — indexed arrays of `key=value` strings or temporary files handle everything needed.

**Resolution**: Target bash 3.2 compatibility. Avoid associative arrays. This removes a prerequisite, removes version-check code, and eliminates friction for the `curl | bash` path on stock macOS.

### R-08: Rollback/transaction pattern is over-engineered for v1
**Severity**: important

The installer copies small text files to same-permission directories. Partial failure is extremely unlikely, and when it occurs the existing uninstall path already handles cleanup via the manifest. The rollback machinery adds real implementation cost (tracking operations, handling rollback failures, testing rollback paths) for a risk that is near-zero.

**Resolution**: For v1, if any step fails, print a clear error and tell the user to run `--uninstall`. Defer rollback to a later version if users actually hit partial-install problems.

### R-09: jq + Python dual code paths double test surface
**Severity**: important

Two JSON merge implementations means two code paths to test and maintain. Pick one for v1. Python 3 is the safer bet for availability (pre-installed on most Linux, available on macOS). Add jq as an optimization later.

### R-10: Features to defer from v1
**Severity**: important

Cut from v1 without impacting core value:
1. **Rollback** (AC-11) — "error + uninstall" achieves the same outcome with no extra code.
2. **Checksum verification on uninstall** (AC-09) — for v1, uninstall deletes everything in the manifest. Users can copy files before uninstalling if they want to preserve modifications.
3. **Orphan cleanup** (partial AC-05) — orphaned `fbk-` files are inert. Users can `--uninstall` and reinstall for a clean state.

Keep: install, settings.json merge, backup, manifest (simplified), uninstall, `--dry-run`, global/project target selection.

### R-11: Source tree rename is under-scoped as a prerequisite
**Severity**: informational

The rename touches ~51 files and requires updating all internal cross-references. It should be its own task with acceptance criteria, not a bullet in the dependencies section.

## Testing Strategy and Impact

### R-12: AC-12 (dual target support) has no dedicated test
**Severity**: important

No test validates project-level installation. Add an integration test that installs to a project-level `.claude/` directory and verifies correct path handling.

### R-13: Integration seam 2 (JSON merge -> manifest recording) untested
**Severity**: important

No test verifies that the exact hook entries written to settings.json are recorded in the manifest in a form that enables correct uninstall reversal. Add an integration test that installs, inspects `manifest.settings_entries.hooks_added`, asserts it matches what was written to settings.json, then runs `--uninstall` and asserts settings.json is fully restored.

### R-14: jq/Python fallback parity untested
**Severity**: important

If dual code paths are kept (see R-09), add a test that runs the same merge scenario through both paths and asserts identical output. If Python-only is chosen per R-09, this finding is moot.

### R-15: JSON merge tests labeled as unit tests but require external dependencies
**Severity**: important

The JSON merge shells out to jq or Python — these are integration tests, not unit tests. The spec should relabel them or extract the merge logic into standalone scripts that can be tested independently with known inputs/outputs.

### R-16: No test for `--force` flag during uninstall
**Severity**: important

The spec describes `--force` for uninstall (delete user-modified files regardless) but no test covers it. Add an integration test: modify a `fbk-` file, run `--uninstall --force`, verify the modified file is deleted.

### R-17: Pre-existing `.pre-firebreak` backup scenario untested
**Severity**: important

The spec mentions timestamped backups when `.pre-firebreak` already exists, but no test covers this. Add a test to verify the backup naming logic does not silently overwrite existing backups.

### R-18: Test infrastructure section defers framework decision
**Severity**: important

The section says "examine existing test infrastructure" — an instruction to investigate, not a specification. The existing tests use bash TAP-format scripts. The spec should state the test harness, invocation method, and directory structure so a task compiler can derive implementation tasks without follow-up.

### R-19: JSONC input (comments/trailing commas) behavior unspecified
**Severity**: informational

Users' settings.json may contain `//` comments or trailing commas. Both jq and Python reject these. The spec should either acknowledge this as an explicit error case or add JSONC preprocessing. Either way, add a test fixture.

### R-20: Concurrent install and symlink edge cases
**Severity**: informational

Concurrent installs to the same target and symlinked settings.json are unsupported edge cases. Document "concurrent installation is not supported" in error states. Consider one integration test for symlinked settings.json to verify backup captures content, not the symlink.

## Test Strategy Review

### New tests needed

Per findings R-12 through R-17: add tests for AC-12 (dual target), JSON merge -> manifest seam, jq/Python parity, --force flag, pre-existing backup, and relabel JSON merge tests as integration tests.

### Existing tests impacted

None — no existing installer tests. The project's `tests/sdl-workflow/` bash TAP harness should be adopted as the pattern for installer tests.

### Test infrastructure changes

Adopt the existing bash TAP test harness from `tests/sdl-workflow/`. Create test directory at `tests/installer/`. Create fixtures: mock source tree with `fbk-`-prefixed files, sample `settings.json` variants (empty, populated, malformed). Create temp directory harness for isolated install targets.

**Independent test reviewer result**: FAIL

Defects identified by independent test reviewer:
1. **AC-12 uncovered** — no test exercises project-level installation.
2. **Integration seam 2 untested** — JSON merge -> manifest recording round-trip not verified.
3. **Prerequisite checking -> target selection seam undeclared** — module boundary exists but is not declared as an integration seam.
4. **jq/Python fallback parity undeclared as seam** — two implementations of the same computation with no parity test.
5. **Test infrastructure defers framework decision** — insufficiently specific for task compilation.

## Two Cross-Reference Classes Need Distinct Renaming Strategies

**Severity**: important

The `fbk-` rename affects two structurally different reference types:
1. **Development-time references** (`home/dot-claude/docs/...`): used within this repo when developing firebreak. These route the agent to source docs.
2. **Runtime references** (`"$HOME"/.claude/hooks/...`): used in installed artifacts at runtime.

Both must be updated, but the source-tree rename changes the developer experience for this repo, not just installed artifacts. The task breakdown should enumerate both classes explicitly.

## Threat Model Determination

**Security-relevant characteristics**: The installer copies files to the user's home directory and modifies settings.json. It runs with the user's permissions. No network connections (except curl for download). No authentication. No data storage beyond local files. No new trust boundaries beyond the existing shell execution model.

**Decision**: No threat model required. No new trust boundaries, no data handling changes, no external API interaction, no authentication. The installer operates entirely within the user's local filesystem with existing permissions. The `curl | bash` download is the only network touchpoint and follows standard distribution patterns.

---

## Findings Summary

| ID | Category | Severity | Summary |
|----|----------|----------|---------|
| R-01 | Architecture | blocking | Hook dedup must compare full matcher group, not just command |
| R-02 | Architecture | blocking | Uninstall backup restore conflicts with surgical removal |
| R-07 | Pragmatism | blocking | bash >= 4 excludes stock macOS |
| R-03 | Architecture | important | env uninstall needs value-matching |
| R-04 | Architecture | important | Rollback must handle missing pre-install settings.json |
| R-08 | Pragmatism | important | Rollback over-engineered for v1 |
| R-09 | Pragmatism | important | Dual jq/Python code paths — pick one |
| R-10 | Pragmatism | important | Defer rollback, checksum-on-uninstall, orphan cleanup |
| R-12 | Testing | important | AC-12 untested |
| R-13 | Testing | important | JSON merge -> manifest seam untested |
| R-14 | Testing | important | jq/Python parity untested |
| R-15 | Testing | important | JSON merge tests mislabeled as unit |
| R-16 | Testing | important | --force flag untested |
| R-17 | Testing | important | Pre-existing backup scenario untested |
| R-18 | Testing | important | Test infrastructure underspecified |
| Cross-ref | Architecture | important | Two reference classes need distinct rename strategies |
| R-05 | Architecture | informational | Manifest missing installer_version, install_mode |
| R-06 | Architecture | informational | curl\|bash bundling unspecified |
| R-11 | Pragmatism | informational | Source rename under-scoped |
| R-19 | Testing | informational | JSONC behavior unspecified |
| R-20 | Testing | informational | Concurrent/symlink edge cases |
