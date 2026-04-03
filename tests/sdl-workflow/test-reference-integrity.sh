#!/usr/bin/env bash
set -uo pipefail

PASS=0
FAIL=0
TOTAL=0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ASSETS_DIR="$PROJECT_ROOT/assets"

ok() {
  TOTAL=$((TOTAL + 1))
  PASS=$((PASS + 1))
  echo "ok $TOTAL - $1"
}

not_ok() {
  TOTAL=$((TOTAL + 1))
  FAIL=$((FAIL + 1))
  echo "not ok $TOTAL - $1"
  [ -n "${2:-}" ] && echo "# $2"
}

echo "TAP version 13"

# --- Part 1: Every leaf doc is referenced by at least one other asset file ---
#
# Leaf docs: files inside fbk-docs/fbk-*/ at two levels of nesting
# (i.e., fbk-docs/fbk-*/something.md or fbk-docs/fbk-*/subdir/something.md)
# Index docs (excluded): files directly in fbk-docs/ or directly in fbk-docs/fbk-*/
#
# Also includes: files under skills/fbk-*/references/

while IFS= read -r leaf; do
  # Relative path from ASSETS_DIR for display
  rel="${leaf#$ASSETS_DIR/}"

  # The filename alone (e.g., claude-md.md)
  filename="$(basename "$leaf")"

  # Path segment relative to fbk-docs/ or skills/ for searching
  # e.g., fbk-context-assets/claude-md.md
  if [[ "$leaf" == *"/fbk-docs/"* ]]; then
    seg="${leaf#*fbk-docs/}"
  else
    seg="${leaf#*skills/}"
  fi

  # Search all other .md files in the asset tree for a reference to this filename or path segment
  match=$(grep -rl --include="*.md" -e "$filename" -e "$seg" "$ASSETS_DIR" 2>/dev/null \
    | grep -v "^$leaf$" | head -1)

  if [ -n "$match" ]; then
    ok "Leaf doc referenced: $rel"
  else
    not_ok "Orphaned leaf doc: $rel — not referenced by any asset file"
  fi
done < <(
  # Two-level nesting under fbk-docs/fbk-*/: fbk-docs/fbk-name/subdir/file.md
  find "$ASSETS_DIR/fbk-docs" -mindepth 3 -maxdepth 3 -name "*.md" -type f 2>/dev/null | sort
  # One additional level: fbk-docs/fbk-name/file.md (inside a subdirectory, not top-level index)
  # These are leaf docs when the parent dir itself is named after an fbk- collection
  find "$ASSETS_DIR/fbk-docs" -mindepth 2 -maxdepth 2 -name "*.md" -type f 2>/dev/null | sort
  # Top-level standalone docs (not index files): fbk-docs/fbk-brownfield-*.md etc.
  # Index files (fbk-context-assets.md, fbk-design-guidelines.md, fbk-sdl-workflow.md) are excluded
  # because they are routing tables referenced by skills, not leaf content.
  find "$ASSETS_DIR/fbk-docs" -mindepth 1 -maxdepth 1 -name "fbk-*.md" -type f 2>/dev/null \
    | grep -v -E '(fbk-context-assets|fbk-design-guidelines|fbk-sdl-workflow)\.md$' | sort
  # Skill reference docs
  find "$ASSETS_DIR/skills" -path "*/references/*.md" -type f 2>/dev/null | sort
)

# --- Part 2: All fbk-docs/ and fbk-* path references in asset files resolve ---
#
# Scan every .md file in assets/ for references that look like:
#   - .claude/fbk-docs/...
#   - fbk-docs/fbk-*/...
#   - backtick-quoted paths containing fbk-
# Strip .claude/ prefix (maps to assets/ in source tree), then check the file exists.

declare -A SEEN_REFS

while IFS= read -r source_file; do
  # Extract path-like references from the file.
  # Three forms appear in the asset tree:
  #   1. `.claude/fbk-docs/fbk-name/file.md`  — skills referencing docs by install path
  #   2. `fbk-docs/fbk-name/file.md`           — full relative path from assets/
  #   3. `fbk-name/file.md`                    — relative path used in index docs (relative to fbk-docs/)
  while IFS= read -r raw_ref; do
    # Strip backticks, quotes, trailing punctuation
    ref="${raw_ref//\`/}"
    ref="${ref//\"/}"
    ref="${ref//\'/}"
    ref="${ref%,}"
    ref="${ref%.}"
    ref="${ref%:}"
    ref="${ref%\)}"
    ref="$(echo "$ref" | tr -d '[:space:]')"

    [ -z "$ref" ] && continue

    # Normalize to a path relative to ASSETS_DIR.
    # Form 1a: .claude/fbk-docs/... -> fbk-docs/...
    # Form 1b: .claude/<other-dir>/fbk-*.md -> <other-dir>/fbk-*.md (e.g. agents/)
    normalized="${ref#.claude/}"
    # Strip leading assets/ if present
    normalized="${normalized#assets/}"

    # Form 3: if it still starts with fbk- but NOT fbk-docs/, it is a relative
    # reference from an index doc (e.g. fbk-context-assets/claude-md.md).
    # Resolve it under fbk-docs/.
    if [[ "$normalized" == fbk-* ]] && [[ "$normalized" != fbk-docs/* ]]; then
      normalized="fbk-docs/$normalized"
    fi

    # Deduplicate: same normalized path in same source file
    key="${source_file}:${normalized}"
    if [ -n "${SEEN_REFS[$key]+x}" ]; then
      continue
    fi
    SEEN_REFS[$key]=1

    target="$ASSETS_DIR/$normalized"

    if [ -f "$target" ]; then
      ok "Path resolves: $ref in ${source_file#$ASSETS_DIR/}"
    else
      not_ok "Broken path: $ref in ${source_file#$ASSETS_DIR/} — file not found at $ASSETS_DIR/$normalized"
    fi
  done < <(
    # Extract path references to fbk- assets. Three forms:
    #   1. .claude/<dir>/fbk-*.md    — install-path reference from any asset type
    #   2. fbk-docs/fbk-*/...        — full source-tree relative path
    #   3. fbk-name/file.md          — relative path used inside index docs (relative to fbk-docs/)
    grep -oE '(`[^`]*fbk-[^`]*`|\b\.claude/[a-zA-Z0-9_-]+/fbk-[a-zA-Z0-9_./-]+\.md\b|\bfbk-docs/[a-zA-Z0-9_./-]+\.md\b|\bfbk-[a-zA-Z0-9_-]+/[a-zA-Z0-9_./-]+\.md\b)' "$source_file" 2>/dev/null \
      | grep -oE '(\.claude/[a-zA-Z0-9_-]+/fbk-[a-zA-Z0-9_./-]+\.md|(fbk-docs/)?fbk-[a-zA-Z0-9_./-]+\.md)'
  )
done < <(find "$ASSETS_DIR" -name "*.md" -type f | sort)

# --- Summary ---
echo ""
echo "# $PASS/$TOTAL tests passed"
if [ "$FAIL" -eq 0 ]; then
  exit 0
fi
exit 1
