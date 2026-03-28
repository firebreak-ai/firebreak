---
id: T-07
type: test
wave: 3
covers: [AC-01, AC-02, AC-05]
depends_on: [T-02, T-04]
files_to_create: [tests/sdl-workflow/test-reference-integrity.sh]
completion_gate: "Test script runs and all assertions pass against the current asset tree"
---

## Objective

Creates a structural test that validates every Firebreak leaf doc is referenced by at least one other asset file, and that all inter-asset path references resolve correctly under the installation path convention.

## Context

Firebreak assets use progressive disclosure: CLAUDE.md references index docs, index docs reference leaf docs, skills and agents reference docs by path. References use `.claude/fbk-docs/...` convention from skills/agents (resolving relative to the installation root). If a leaf doc is orphaned (unreferenced) or a path reference points to a file that doesn't exist, the progressive disclosure chain is broken — agents will never load the orphaned doc, or will fail to load a referenced doc.

This test validates the entire installed asset tree, not just the self-improvement additions. It catches:
- Orphaned leaf docs added but never wired into routing
- Path typos, renames, or moves that break references
- Path conventions that work in the source repo (`assets/`) but would break after installation to `.claude/`

Follow the TAP test pattern from `tests/sdl-workflow/test-code-review-integration.sh`.

## Instructions

1. Create `tests/sdl-workflow/test-reference-integrity.sh` following the TAP test pattern.

2. Set `ASSETS_DIR="$PROJECT_ROOT/assets"` as the root of the asset tree.

3. **Enumerate leaf docs**: Find all `.md` files under `$ASSETS_DIR/fbk-docs/` that are inside a subdirectory (not top-level index files). Also include files under `$ASSETS_DIR/skills/fbk-*/references/`. These are the leaf docs that must be referenced by at least one other file.

   Heuristic for identifying leaf vs index docs: files directly inside `$ASSETS_DIR/fbk-docs/fbk-*/` (one level of nesting) are index docs. Files inside `$ASSETS_DIR/fbk-docs/fbk-*/*/` (two levels) are leaf docs. Top-level files in `$ASSETS_DIR/fbk-docs/` (like `fbk-context-assets.md`) are index docs.

4. **Check each leaf doc is referenced**: For each leaf doc, extract its filename (e.g., `claude-md.md`) and its relative path from the `fbk-docs/` or `skills/` root (e.g., `fbk-context-assets/claude-md.md`). Search all other `.md` files under `$ASSETS_DIR/` for a reference containing either the filename or the relative path segment. Use `grep -rl` across the asset tree excluding the leaf doc itself.

   - If at least one reference found: `ok "Leaf doc referenced: <relative-path>"`
   - If no reference found: `not_ok "Orphaned leaf doc: <relative-path> — not referenced by any asset file"`

5. **Validate path references resolve**: Search all `.md` files under `$ASSETS_DIR/` for path-like references to `fbk-docs/` or `fbk-` prefixed files. Extract each reference that looks like a path (matches patterns like `fbk-docs/fbk-*/...`, `.claude/fbk-docs/...`, or backtick-quoted paths containing `fbk-`). For each extracted path reference:

   - Normalize: strip `.claude/` prefix if present (since in the source tree, `.claude/` maps to `$ASSETS_DIR/`). Strip backticks and quotes.
   - Check if the referenced file exists under `$ASSETS_DIR/` at the normalized path.
   - If exists: `ok "Path resolves: <reference> in <source-file>"`
   - If not: `not_ok "Broken path: <reference> in <source-file> — file not found at $ASSETS_DIR/<normalized-path>"`

6. Add TAP summary and exit with non-zero if any test fails.

## Files to create/modify

- Create: `tests/sdl-workflow/test-reference-integrity.sh`

## Test requirements

This IS the test task. It validates:
- AC-01: The improvement skill's path references to retrospective location patterns are structurally valid
- AC-02: The improvement agent's reference to authoring rules (`fbk-context-assets.md`) resolves correctly
- AC-05: The authoring rules reference chain (index → leaves) is intact, ensuring the improvement agent can follow the progressive disclosure path

This test has no paired implementation task — it validates the structural integrity of the existing + new asset tree.

## Acceptance criteria

- AC-01: Path references in the improvement skill resolve to existing files
- AC-02: The improvement agent's authoring rules reference resolves
- AC-05: The progressive disclosure routing chain for authoring rules is intact (no orphaned leaf docs, no broken paths)

## Model

Sonnet

## Wave

Wave 3
