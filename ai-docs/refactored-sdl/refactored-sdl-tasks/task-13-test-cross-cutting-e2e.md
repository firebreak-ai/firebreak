---
id: task-13
type: test
wave: 4
covers: [AC-22]
files_to_create:
  - tests/installer/test-refactored-sdl-install.sh
files_to_modify:
  - tests/sdl-workflow/test-reference-integrity.sh
completion_gate: "tests compile and fail before implementation"
---

## 1. Objective

Creates `tests/installer/test-refactored-sdl-install.sh` asserting new skills/agents/docs install and uninstall via the installer's auto-discovery, and modifies `tests/sdl-workflow/test-reference-integrity.sh` to add an adversarial grep that rejects any `assets/` path prefix in installed asset bodies.

## 2. Context

AC-22 has three components:
1. **Auto-discovery install**: Every new skill (`fbk-grilling`, `fbk-fresh-eyes`, `fbk-quality-scan`, `fbk-test-review`, `fbk-intent`, `fbk-design`), agent (`fbk-product-author`, `fbk-architect`, `fbk-fresh-eyes-reviewer`), and doc (`fbk-sdl-workflow/intent-guide.md`, `fbk-sdl-workflow/design-guide.md`, `fbk-sdl-workflow/capability-entry.md`) installs to `~/.claude/` after running `installer/install.sh`, without any manual manifest-registration step.
2. **Uninstall**: After uninstall, the `fbk-scripts/` tree under `~/.claude/` is gone (the gate subcommands live there; a per-subcommand assertion would be redundant — the tree removal is sufficient).
3. **No `assets/` path prefix in installed asset bodies**: An adversarial grep over every installed asset body finds no occurrence of the literal string `assets/` — all path references inside installed assets must use the installed form (`~/.claude/fbk-scripts/...`, `.claude/fbk-docs/...`), never the source tree form.

The installer test follows the pattern from `tests/installer/test-e2e-lifecycle.sh`: create a temp `CLAUDE_HOME` directory, run `install.sh` with `HOME` pointed there, assert files are present, run uninstall (or re-run install with `--uninstall` flag if that flag exists, or remove manually via the installer), assert the tree is gone.

The reference-integrity test already exists. Extend it by adding a new Part 3 section at the end (before the summary block) that greps the installed assets tree — but since the tests run against the SOURCE tree (not an installed tree), and the installed-path constraint is enforced in the source form, the adversarial grep must run against `assets/` — checking that no SOURCE asset file contains the literal `assets/` prefix inside a path reference (which would install incorrectly). Specifically: grep all `.md` files under `assets/` for path references that begin with `assets/` (the pattern `\bassets/[a-zA-Z]`). Any match in a non-comment, non-metadata context is a failure.

Before implementation: the install test fails because the new skill/agent/doc files do not yet exist under `assets/`. The reference-integrity extension may pass or fail depending on current asset state — it is acceptable for it to pass immediately if the existing assets already satisfy the constraint (the check adds a forward guard for the new assets).

The install test is a shell script, not a pytest test. Follow the TAP pattern and the `test-e2e-lifecycle.sh` mock-HOME approach.

## 3. Instructions

**File 1: `tests/installer/test-refactored-sdl-install.sh`**

1. Create the file with standard TAP boilerplate (`#!/usr/bin/env bash`, `set -uo pipefail`, counters, helpers, `SCRIPT_DIR`, `PROJECT_ROOT`).

2. Define the install script path:
   ```bash
   INSTALL_SCRIPT="$PROJECT_ROOT/installer/install.sh"
   ```

3. Add a `setup_mock_home()` function that creates a temp directory for use as `HOME` during the install test:
   ```bash
   setup_mock_home() {
     MOCK_HOME=$(mktemp -d)
     TEMP_DIRS+=("$MOCK_HOME")
   }
   TEMP_DIRS=()
   cleanup() { for d in "${TEMP_DIRS[@]:-}"; do rm -rf "$d"; done; }
   trap cleanup EXIT
   ```

4. Call `setup_mock_home`. Run the installer with the mock HOME:
   ```bash
   HOME="$MOCK_HOME" bash "$INSTALL_SCRIPT" >/dev/null 2>&1
   INSTALL_EXIT=$?
   ```

5. Write assertions for installer exit and fbk-scripts presence:
   - T1: `[ "$INSTALL_EXIT" -eq 0 ]` — installer exits 0
   - T2: `[ -d "$MOCK_HOME/.claude/fbk-scripts" ]` — fbk-scripts tree present

6. Write assertions for each new skill (6 new skills):
   - T3: `[ -f "$MOCK_HOME/.claude/skills/fbk-intent/SKILL.md" ]` — fbk-intent installed
   - T4: `[ -f "$MOCK_HOME/.claude/skills/fbk-design/SKILL.md" ]` — fbk-design installed
   - T5: `[ -f "$MOCK_HOME/.claude/skills/fbk-grilling/SKILL.md" ]` — fbk-grilling installed
   - T6: `[ -f "$MOCK_HOME/.claude/skills/fbk-fresh-eyes/SKILL.md" ]` — fbk-fresh-eyes installed
   - T7: `[ -f "$MOCK_HOME/.claude/skills/fbk-quality-scan/SKILL.md" ]` — fbk-quality-scan installed
   - T8: `[ -f "$MOCK_HOME/.claude/skills/fbk-test-review/SKILL.md" ]` — fbk-test-review installed

7. Write assertions for each new agent (3 new agents):
   - T9: `[ -f "$MOCK_HOME/.claude/agents/fbk-product-author.md" ]` — fbk-product-author installed
   - T10: `[ -f "$MOCK_HOME/.claude/agents/fbk-architect.md" ]` — fbk-architect installed
   - T11: `[ -f "$MOCK_HOME/.claude/agents/fbk-fresh-eyes-reviewer.md" ]` — fbk-fresh-eyes-reviewer installed

8. Write assertions for new routed docs:
   - T12: `[ -f "$MOCK_HOME/.claude/fbk-docs/fbk-sdl-workflow/intent-guide.md" ]`
   - T13: `[ -f "$MOCK_HOME/.claude/fbk-docs/fbk-sdl-workflow/design-guide.md" ]`
   - T14: `[ -f "$MOCK_HOME/.claude/fbk-docs/fbk-sdl-workflow/capability-entry.md" ]`

9. Write the adversarial path-prefix grep: scan ALL installed asset bodies for any occurrence of the literal `assets/` path prefix (which would indicate a source-path leak):
   ```bash
   LEAKED_PATHS=$(grep -rl '\bassets/' "$MOCK_HOME/.claude" --include="*.md" --include="*.py" 2>/dev/null | head -5)
   if [ -z "$LEAKED_PATHS" ]; then
     ok "T15: No installed asset body contains 'assets/' path prefix"
   else
     not_ok "T15: No installed asset body contains 'assets/' path prefix" "leaked in: $LEAKED_PATHS"
   fi
   ```

10. Write an uninstall assertion: re-run the installer with `--uninstall` flag (or `ACTION=uninstall bash "$INSTALL_SCRIPT"` if that is the convention — read `installer/install.sh` to determine the uninstall invocation; use the pattern from `test-upgrade-uninstall.sh`). After uninstall: `[ ! -d "$MOCK_HOME/.claude/fbk-scripts" ]` — fbk-scripts tree gone (T16).

11. Add TAP summary.

**File 2: `tests/sdl-workflow/test-reference-integrity.sh` (extend)**

1. Open the existing file. Locate the `# --- Summary ---` block near the end.

2. Insert a new `# --- Part 3: No source-path prefix in asset bodies ---` section BEFORE the summary block.

3. Add this check:
   ```bash
   # --- Part 3: No source-path prefix in asset bodies ---
   # Scan every .md file in assets/ for path references that use the source-tree
   # 'assets/' prefix. Any such reference would install with the wrong path.
   # Exempt: comment lines (starting with #), YAML front-matter lines, and the
   # installer script itself (which legitimately references assets/).
   leaked=0
   while IFS= read -r source_file; do
     # Skip the installer itself
     [[ "$source_file" == *"installer/"* ]] && continue
     while IFS= read -r matched_line; do
       # Strip leading whitespace for comment detection
       trimmed="${matched_line#"${matched_line%%[![:space:]]*}"}"
       # Skip comment lines and metadata lines
       [[ "$trimmed" == "#"* ]] && continue
       [[ "$trimmed" == ">"* ]] && continue
       TOTAL=$((TOTAL + 1))
       FAIL=$((FAIL + 1))
       leaked=$((leaked + 1))
       echo "not ok $TOTAL - Source-path leak in ${source_file#$ASSETS_DIR/}: $matched_line"
     done < <(grep -nE '\bassets/[a-zA-Z]' "$source_file" 2>/dev/null)
   done < <(find "$ASSETS_DIR" -name "*.md" -type f | sort)

   if [ "$leaked" -eq 0 ]; then
     TOTAL=$((TOTAL + 1))
     PASS=$((PASS + 1))
     echo "ok $TOTAL - No source-path 'assets/' prefix found in any asset body"
   fi
   ```

4. Leave the existing summary block (`echo "# $PASS/$TOTAL tests passed"`, `if [ "$FAIL" -eq 0 ]`) unchanged.

## 4. Files to create/modify

- `tests/installer/test-refactored-sdl-install.sh` (create)
- `tests/sdl-workflow/test-reference-integrity.sh` (modify)

Justification for two files: these are the two distinct test surfaces for AC-22 — the installer test and the reference-integrity extension. They are logically paired (both verify AC-22) but must live in different directories, so they cannot be one file.

## 5. Test requirements

`test-refactored-sdl-install.sh` — 16 TAP assertions:
- T1–T2: installer success and fbk-scripts tree presence
- T3–T8: 6 new skills present under `~/.claude/skills/`
- T9–T11: 3 new agents present under `~/.claude/agents/`
- T12–T14: 3 new routed docs present under `~/.claude/fbk-docs/`
- T15: adversarial path-prefix grep over installed assets
- T16: fbk-scripts tree absent after uninstall

T3–T14 fail before implementation (new skills/agents/docs do not exist in `assets/`).

`test-reference-integrity.sh` extension: adds a streaming check over all asset `.md` files. May pass immediately if no existing assets contain `assets/` path leaks; provides a forward guard for new assets.

## 6. Acceptance criteria

Covers AC-22: new assets install under `~/.claude/` via auto-discovery (no manifest-registration step); no `assets/` path prefix appears in installed asset bodies; the installer uninstalls cleanly (fbk-scripts tree removed).

## 7. Model

Haiku

## 8. Wave

Wave 4
