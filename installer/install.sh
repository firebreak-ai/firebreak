#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Defaults
MODE=install
DRY_RUN=0
TARGET_DIR=""
SOURCE_DIR=""
INSTALL_MODE=global

# Indexed arrays for file tracking (bash 3.2+ compatible — no associative arrays)
SRC_FILES=()
DST_FILES=()
MANIFEST_FILES=()
PREV_FILES=()
PRUNED_COUNT=0
BACKUP_FILE=""

# Download state
DOWNLOAD_TMPDIR=""
SOURCE_EXPLICIT=0
GITHUB_REPO="${FIREBREAK_GITHUB_REPO:-firebreak-ai/firebreak}"
GITHUB_BRANCH="${FIREBREAK_GITHUB_BRANCH:-main}"

# Temp files for manifest assembly
MERGE_OUTPUT_FILE=""
SETTINGS_JSON_FILE=""
MANIFEST_RECORD_FILE=""
SETTINGS_TMP_FILE=""

cleanup_temps() {
  [ -n "$MERGE_OUTPUT_FILE" ] && rm -f "$MERGE_OUTPUT_FILE"
  [ -n "$SETTINGS_JSON_FILE" ] && rm -f "$SETTINGS_JSON_FILE"
  [ -n "$MANIFEST_RECORD_FILE" ] && rm -f "$MANIFEST_RECORD_FILE"
  [ -n "$SETTINGS_TMP_FILE" ] && rm -f "$SETTINGS_TMP_FILE"
  [ -n "$DOWNLOAD_TMPDIR" ] && rm -rf "$DOWNLOAD_TMPDIR"
}
trap cleanup_temps EXIT

# --- Download from GitHub ---
download_source() {
  local tarball_url="https://github.com/$GITHUB_REPO/archive/$GITHUB_BRANCH.tar.gz"

  if ! command -v curl >/dev/null 2>&1; then
    echo "Error: curl is required to download from GitHub." >&2
    exit 1
  fi

  DOWNLOAD_TMPDIR="$(mktemp -d)" || {
    echo "Error: Failed to create temp directory." >&2
    exit 1
  }

  echo "Downloading firebreak from $GITHUB_REPO ($GITHUB_BRANCH)..." >&2

  if ! curl -fsSL "$tarball_url" | tar xz -C "$DOWNLOAD_TMPDIR"; then
    echo "Error: Failed to download from GitHub." >&2
    echo "  URL: $tarball_url" >&2
    echo "  Check your network connection and that the repository exists." >&2
    exit 1
  fi

  local extracted
  extracted="$(find "$DOWNLOAD_TMPDIR" -mindepth 1 -maxdepth 1 -type d | head -1)"

  if [ -z "$extracted" ]; then
    echo "Error: Downloaded archive is empty." >&2
    exit 1
  fi

  if [ ! -d "${extracted}/assets" ]; then
    echo "Error: Downloaded archive does not contain expected source tree." >&2
    exit 1
  fi

  if [ ! -f "${extracted}/installer/merge-settings.py" ]; then
    echo "Error: Downloaded archive does not contain merge-settings.py." >&2
    exit 1
  fi

  SOURCE_DIR="${extracted}/assets"
  SCRIPT_DIR="${extracted}/installer"
}

# --- Argument parsing ---
while [ $# -gt 0 ]; do
  case "$1" in
    --target)
      TARGET_DIR="$2"
      shift 2
      ;;
    --source)
      SOURCE_DIR="$2"
      SOURCE_EXPLICIT=1
      shift 2
      ;;
    --uninstall)
      MODE=uninstall
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --help)
      cat >&2 <<'EOF'
Usage: install.sh [OPTIONS]

Options:
  --target <path>   Install target directory (skips interactive prompt)
  --source <path>   Source directory (default: auto-detected or downloaded)
  --uninstall       Remove a firebreak installation
  --dry-run         Print planned operations without making changes
  --help            Show this help

Environment:
  FIREBREAK_GITHUB_REPO    GitHub owner/repo (default: firebreak-ai/firebreak)
  FIREBREAK_GITHUB_BRANCH  Git branch to download (default: main)
EOF
      exit 0
      ;;
    *)
      echo "Error: Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

# If installing (not uninstalling) and source not available, download from GitHub
if [ "$MODE" != "uninstall" ] && [ "$SOURCE_EXPLICIT" = "0" ] && { [ -z "$SOURCE_DIR" ] || [ ! -d "$SOURCE_DIR" ]; }; then
  download_source
fi

# Normalize SOURCE_DIR: strip trailing slash and resolve to absolute path.
# Without this, --source "assets/" leaves SOURCE_DIR with a trailing slash, which
# breaks the rel_path strip in enumerate_assets (the prefix pattern stops matching),
# causing all files to be copied to $TARGET_DIR/assets/... instead of $TARGET_DIR/...
if [ -n "$SOURCE_DIR" ] && [ -d "$SOURCE_DIR" ]; then
  SOURCE_DIR="$(cd "$SOURCE_DIR" && pwd)"
fi
# Same normalization for TARGET_DIR so dst paths are predictable.
if [ -n "$TARGET_DIR" ]; then
  # Strip trailing slash; absolutify only if the directory already exists.
  TARGET_DIR="${TARGET_DIR%/}"
  if [ -d "$TARGET_DIR" ]; then
    TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"
  fi
fi

# Determine install mode from target path
if [ -n "$TARGET_DIR" ]; then
  if [ "$TARGET_DIR" = "$HOME/.claude" ]; then
    INSTALL_MODE=global
  else
    INSTALL_MODE=project
  fi
fi

# --- Release version ---
# The manifest records which Firebreak release an install carries. The version is
# the newest version heading in CHANGELOG.md — already the file that must be
# updated when a release or a new development line opens, so there is no second
# place to bump and nothing extra to remember. The installer cannot read the git
# tag: the normal path downloads a source tarball with no git metadata, and it
# fetches a branch rather than a tag, so repo content is the only version evidence
# available at install time. An install from a development branch therefore records
# the in-progress version, which is the intent — it keeps in-development assets
# distinguishable from a shipped release.
FIREBREAK_VERSION="unknown"

resolve_version() {
  # Prefer the CHANGELOG beside the asset tree being installed (it describes that
  # payload); fall back to the one beside this script.
  local changelog=""
  local candidate
  for candidate in \
    "${SOURCE_DIR:+$(dirname "$SOURCE_DIR")/CHANGELOG.md}" \
    "$(dirname "$SCRIPT_DIR")/CHANGELOG.md"
  do
    if [ -n "$candidate" ] && [ -f "$candidate" ]; then
      changelog="$candidate"
      break
    fi
  done

  if [ -z "$changelog" ]; then
    echo "Warning: no CHANGELOG.md found beside the source tree or the installer." >&2
    echo "  The manifest will record the version as \"unknown\"." >&2
    return 0
  fi

  local version
  # Matching on a version-numbered heading skips a non-numeric heading such as
  # "[Unreleased]" with no special case for it.
  version="$(python3 - "$changelog" <<'PYEOF'
import re, sys

heading = re.compile(r'^##\s*\[(\d+\.\d+\.\d+[^\]]*)\]')
try:
    with open(sys.argv[1], encoding='utf-8') as f:
        for line in f:
            match = heading.match(line)
            if match:
                print(match.group(1))
                break
except OSError:
    pass
PYEOF
)"

  if [ -z "$version" ]; then
    echo "Warning: no version heading found in $changelog." >&2
    echo "  The manifest will record the version as \"unknown\"." >&2
    return 0
  fi

  FIREBREAK_VERSION="$version"
}

# --- Prerequisite checking ---
check_uv() {
  if command -v uv >/dev/null 2>&1; then
    return 0
  fi
  echo "Error: Firebreak requires 'uv' for Python dependency management." >&2
  echo "  uv creates a project-local virtualenv so Firebreak's Python deps (pyyaml)" >&2
  echo "  do not depend on system-wide packages — which is incompatible with PEP 668" >&2
  echo "  (externally-managed) Python installations on recent Arch/Debian/Ubuntu/macOS." >&2
  echo "" >&2
  echo "Install uv: https://docs.astral.sh/uv/getting-started/installation/" >&2
  echo "Then re-run this installer." >&2
  exit 1
}

# Create a project-local venv inside the install target and populate it with
# Firebreak's Python deps. Called after install_files copies pyproject.toml to
# the target. The dispatcher (fbk.py) discovers this venv via sys.path injection.
setup_python_venv() {
  local fbk_scripts_dir="$TARGET_DIR/fbk-scripts"
  local venv_dir="$fbk_scripts_dir/.venv"

  if [ ! -d "$fbk_scripts_dir" ]; then
    echo "Warning: $fbk_scripts_dir does not exist; skipping venv setup." >&2
    return 0
  fi

  if [ "$DRY_RUN" = "1" ]; then
    echo "[dry-run] Would create venv at $venv_dir and install pyyaml via uv." >&2
    return 0
  fi

  # Create venv if it doesn't already exist (idempotent for upgrades).
  if [ ! -d "$venv_dir" ]; then
    echo "Creating Python venv at $venv_dir..." >&2
    if ! uv venv "$venv_dir" --python ">=3.11" --quiet 2>&1; then
      echo "Error: failed to create venv at $venv_dir." >&2
      echo "  Run 'uv venv $venv_dir --python \">=3.11\"' manually to diagnose." >&2
      exit 1
    fi
  fi

  echo "Installing Firebreak Python dependencies into venv..." >&2
  if ! uv pip install --python "$venv_dir/bin/python" --quiet "pyyaml>=6.0" 2>&1; then
    echo "Error: failed to install pyyaml into $venv_dir." >&2
    echo "  Run 'uv pip install --python $venv_dir/bin/python pyyaml>=6.0' to diagnose." >&2
    exit 1
  fi
}

check_prerequisites() {
  if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: Requires Python 3 for JSON merging. Install Python 3 and retry." >&2
    exit 1
  fi

  if [ -d "$TARGET_DIR" ]; then
    if [ ! -w "$TARGET_DIR" ]; then
      echo "Error: Cannot write to $TARGET_DIR. Check permissions." >&2
      exit 1
    fi
  else
    local parent
    parent="$(dirname "$TARGET_DIR")"
    if [ ! -w "$parent" ]; then
      echo "Error: Cannot write to $TARGET_DIR. Check permissions." >&2
      exit 1
    fi
  fi

  # Pre-validate target settings.json if it exists
  if [ -f "$TARGET_DIR/settings.json" ]; then
    if ! python3 -c "import json, sys; json.load(open(sys.argv[1]))" "$TARGET_DIR/settings.json" 2>/dev/null; then
      echo "Error: Malformed JSON in $TARGET_DIR/settings.json. Fix or remove it before installing." >&2
      exit 1
    fi
  fi

  check_uv
}

# --- Interactive target selection ---
prompt_target() {
  printf 'Install firebreak globally (~/.claude) or into a project directory?\n' >&2
  printf '  [1] Global (~/.claude/)\n' >&2
  printf '  [2] Project directory (enter path)\n' >&2
  printf '> ' >&2
  read -r choice
  case "$choice" in
    1)
      TARGET_DIR="$HOME/.claude"
      INSTALL_MODE=global
      ;;
    2)
      printf 'Enter project directory path: ' >&2
      read -r proj_path
      if [[ "$proj_path" == */.claude ]]; then
        TARGET_DIR="$proj_path"
      else
        TARGET_DIR="$proj_path/.claude"
      fi
      INSTALL_MODE=project
      ;;
    *)
      echo "Error: Invalid selection." >&2
      exit 1
      ;;
  esac
}

# --- Asset enumeration ---
enumerate_assets() {
  SRC_FILES=()
  DST_FILES=()

  while IFS= read -r src_file; do
    local base
    base="$(basename "$src_file")"
    # Skip CLAUDE.md and settings.json
    if [ "$base" = "CLAUDE.md" ] || [ "$base" = "settings.json" ]; then
      continue
    fi
    # Compute relative path by stripping SOURCE_DIR prefix
    local rel_path="${src_file#$SOURCE_DIR/}"
    local dst_file="$TARGET_DIR/$rel_path"
    SRC_FILES+=("$src_file")
    DST_FILES+=("$dst_file")
  done < <(find "$SOURCE_DIR" \
    \( -type d \( \
         -name .venv -o -name venv -o -name __pycache__ -o -name .pytest_cache \
         -o -name .ruff_cache -o -name '*.egg-info' -o -name tests \
         -o -name .claude -o -name .git \
       \) -prune \) \
    -o \( -type f ! -name '*.pyc' ! -name '.DS_Store' -print \))
}

# --- File installation ---
install_files() {
  local i=0
  local count=${#SRC_FILES[@]}
  while [ $i -lt $count ]; do
    local src="${SRC_FILES[$i]}"
    local dst="${DST_FILES[$i]}"
    i=$((i + 1))

    if [ "$DRY_RUN" = "1" ]; then
      echo "Would copy: $src -> $dst"
      continue
    fi

    mkdir -p "$(dirname "$dst")"
    if ! cp "$src" "$dst"; then
      echo "Error: Failed to copy $src. Run --uninstall to clean up." >&2
      exit 1
    fi
  done
}

# --- Orphan pruning (upgrade only) ---
# The manifest is the single record of what the installer owns, so an upgrade can
# tell which files the previous version installed that the current one no longer
# ships. Without this, a dropped asset lingers in the target forever: write_manifest
# replaces the old file list before install_files runs, so the only evidence that
# the file was ever ours is erased in the same run that orphans it. Pruning reuses
# the manifest rather than inventing a second rule for what belongs to Firebreak
# (e.g. "anything named fbk-*"), which would disagree with the manifest eventually.

# Read the previous install's file list. Must run before write_manifest overwrites it.
collect_previous_files() {
  local manifest_path="$TARGET_DIR/.firebreak-manifest.json"
  PREV_FILES=()

  [ -f "$manifest_path" ] || return 0

  local listing
  if ! listing="$(python3 -c "
import json, sys
d = json.load(open(sys.argv[1]))
for f in d.get('files', []):
    if isinstance(f, str) and f:
        print(f)
" "$manifest_path" 2>/dev/null)"; then
    # A damaged manifest must not fail the upgrade — installing the current files
    # is the essential job. Say so loudly rather than leaving stale files silently.
    echo "Warning: could not read the previous file list from $manifest_path." >&2
    echo "  Files dropped in this version were left in place. Run --uninstall and reinstall to clear them." >&2
    return 0
  fi

  while IFS= read -r rel_path; do
    [ -n "$rel_path" ] && PREV_FILES+=("$rel_path")
  done <<< "$listing"
}

# Remove files the previous install owned that the current one no longer ships,
# then drop any directory left empty. Runs after install_files so nothing old is
# removed until the new files are in place.
prune_orphans() {
  PRUNED_COUNT=0

  [ "${#PREV_FILES[@]}" -eq 0 ] && return 0

  # Python decides which paths are orphans and rejects any that escape the target;
  # bash does the deleting.
  local orphans
  if ! orphans="$(python3 -c "
import os, sys

target = os.path.realpath(sys.argv[1])
sep = sys.argv.index('--', 2)
previous = sys.argv[2:sep]
current = set(sys.argv[sep + 1:])

for rel in previous:
    if rel in current:
        continue
    full = os.path.realpath(os.path.join(target, rel))
    if full != target and not full.startswith(target + os.sep):
        sys.stderr.write('Warning: manifest entry resolves outside the install target, skipping: ' + rel + '\n')
        continue
    print(rel)
" "$TARGET_DIR" ${PREV_FILES[@]+"${PREV_FILES[@]}"} -- ${MANIFEST_FILES[@]+"${MANIFEST_FILES[@]}"})"; then
    echo "Warning: could not compare the previous file list against this install." >&2
    echo "  Files dropped in this version were left in place. Run --uninstall and reinstall to clear them." >&2
    return 0
  fi

  local removed_dirs
  removed_dirs=()
  while IFS= read -r rel_path; do
    [ -n "$rel_path" ] || continue
    local full="$TARGET_DIR/$rel_path"
    # Only regular files are ever deleted; directories go through rmdir below.
    [ -f "$full" ] || continue

    if [ "$DRY_RUN" = "1" ]; then
      echo "Would remove (no longer shipped): $full"
      PRUNED_COUNT=$((PRUNED_COUNT + 1))
      continue
    fi

    if rm -f "$full"; then
      echo "Removed (no longer shipped): $full" >&2
      PRUNED_COUNT=$((PRUNED_COUNT + 1))
      removed_dirs+=("$(dirname "$rel_path")")
    else
      echo "Warning: failed to remove $full." >&2
    fi
  done <<< "$orphans"

  [ "$DRY_RUN" = "1" ] && return 0
  [ "${#removed_dirs[@]}" -eq 0 ] && return 0

  # rmdir refuses non-empty directories, so a directory still holding user files
  # (or files the current version ships) survives untouched.
  while IFS= read -r empty_dir; do
    rmdir "$empty_dir" 2>/dev/null || true
  done < <(python3 -c "
import os, sys
target = sys.argv[1]
dirs = set()
for d in sys.argv[2:]:
    p = d
    while p and p != '.':
        dirs.add(os.path.join(target, p))
        p = os.path.dirname(p)
for d in sorted(dirs, key=lambda x: x.count(os.sep), reverse=True):
    print(d)
" "$TARGET_DIR" ${removed_dirs[@]+"${removed_dirs[@]}"})
}

# --- Settings merging ---
merge_settings() {
  local merge_script="$SCRIPT_DIR/merge-settings.py"
  local firebreak_settings="$SOURCE_DIR/settings.json"

  if [ ! -f "$firebreak_settings" ]; then
    return
  fi

  if [ "$DRY_RUN" = "1" ]; then
    echo "Would merge settings from $firebreak_settings into $TARGET_DIR/settings.json"
    return
  fi

  # The same-directory temp file below requires the target directory to exist.
  mkdir -p "$TARGET_DIR"

  # Create backup of existing settings.json
  if [ -f "$TARGET_DIR/settings.json" ]; then
    if [ ! -f "$TARGET_DIR/settings.json.pre-firebreak" ]; then
      cp "$TARGET_DIR/settings.json" "$TARGET_DIR/settings.json.pre-firebreak"
      BACKUP_FILE="settings.json.pre-firebreak"
    else
      local ts
      ts="$(date +%Y%m%d%H%M%S)"
      cp "$TARGET_DIR/settings.json" "$TARGET_DIR/settings.json.pre-firebreak.$ts"
      BACKUP_FILE="settings.json.pre-firebreak.$ts"
    fi
  fi

  # For project installs, rewrite $HOME hook paths to $CLAUDE_PROJECT_DIR
  # before merging so the manifest records the correct value for uninstall
  local merge_source="$firebreak_settings"
  if [ "$INSTALL_MODE" = "project" ]; then
    merge_source="$(mktemp)"
    # Rewrite "$HOME"/.claude/ → "$CLAUDE_PROJECT_DIR"/.claude/ for project installs,
    # but skip hook_router.py lines — the router always resolves to the global fbk-scripts tree.
    sed '/hook_router\.py/!s|\\"\$HOME\\"/\.claude/|\\"\$CLAUDE_PROJECT_DIR\\"/\.claude/|g' "$firebreak_settings" > "$merge_source"
  fi

  # Run merge script — stdout gets merged JSON, stderr gets errors
  MERGE_OUTPUT_FILE="$(mktemp)"
  local merge_stderr_file
  merge_stderr_file="$(mktemp)"
  if ! python3 "$merge_script" "$TARGET_DIR/settings.json" "$merge_source" > "$MERGE_OUTPUT_FILE" 2>"$merge_stderr_file"; then
    cat "$merge_stderr_file" >&2
    rm -f "$merge_stderr_file"
    [ "$merge_source" != "$firebreak_settings" ] && rm -f "$merge_source"
    exit 1
  fi
  rm -f "$merge_stderr_file"
  [ "$merge_source" != "$firebreak_settings" ] && rm -f "$merge_source"

  # Split on ---MANIFEST---
  SETTINGS_JSON_FILE="$(mktemp)"
  MANIFEST_RECORD_FILE="$(mktemp)"

  awk '/^---MANIFEST---$/{exit} {print}' "$MERGE_OUTPUT_FILE" > "$SETTINGS_JSON_FILE"
  awk 'found{print} /^---MANIFEST---$/{found=1}' "$MERGE_OUTPUT_FILE" > "$MANIFEST_RECORD_FILE"

  # Write merged settings atomically: temp file in the SAME directory as the
  # target, then rename. Same-directory placement is load-bearing — a /tmp
  # temp would sit on another filesystem and mv would silently degrade to a
  # non-atomic copy, recreating the truncation hazard this exists to close.
  SETTINGS_TMP_FILE="$(mktemp "$TARGET_DIR/.settings.json.tmp.XXXXXX")" || {
    echo "Error: failed to create temp file in $TARGET_DIR." >&2
    exit 1
  }
  if ! cp "$SETTINGS_JSON_FILE" "$SETTINGS_TMP_FILE"; then
    echo "Error: failed to stage merged settings.json." >&2
    exit 1
  fi
  # The rename must not fail silently: the script does not run set -e, and a
  # quiet mv failure would leave capture disarmed while the install reports
  # success — the pre-merge backup stays intact, so failing loudly is safe.
  if ! mv -f "$SETTINGS_TMP_FILE" "$TARGET_DIR/settings.json"; then
    echo "Error: failed to rename merged settings.json into place." >&2
    exit 1
  fi
  SETTINGS_TMP_FILE=""
}

# --- Capture sentinel ---
# Marks the target as Firebreak-managed so the per-project capture gate arms
# with no manual step. The filename is the shared token the gate keys on:
# gate_check.FBK_MARKER_SENTINEL = ".fbk-managed"
# (assets/fbk-scripts/fbk/capture/gate_check.py). $TARGET_DIR is the .claude
# directory, so this lands at .claude/automation/.fbk-managed in the project.
create_capture_sentinel() {
  if [ "$DRY_RUN" = "1" ]; then
    echo "Would create capture sentinel at $TARGET_DIR/automation/.fbk-managed"
    return
  fi
  mkdir -p "$TARGET_DIR/automation"
  : > "$TARGET_DIR/automation/.fbk-managed"
}

# --- Gitignore ---
write_gitignore() {
  # Read gitignore entries from the merged settings JSON and append any missing
  # lines to the target directory's .gitignore file.
  if [ -z "$SETTINGS_JSON_FILE" ] || [ ! -f "$SETTINGS_JSON_FILE" ]; then
    return
  fi

  if [ "$DRY_RUN" = "1" ]; then
    echo "Would write gitignore entries from merged settings to $TARGET_DIR/.gitignore"
    return
  fi

  local gitignore_path="$TARGET_DIR/.gitignore"

  python3 - "$SETTINGS_JSON_FILE" "$gitignore_path" <<'EOF'
import json, sys
from pathlib import Path

settings_path = sys.argv[1]
gitignore_path = Path(sys.argv[2])

with open(settings_path) as f:
    settings = json.load(f)

entries = settings.get("gitignore", [])
if not entries:
    sys.exit(0)

existing_lines = set()
if gitignore_path.exists():
    existing_lines = {line.rstrip("\n") for line in gitignore_path.read_text().splitlines()}

to_add = [e for e in entries if e not in existing_lines]
if not to_add:
    sys.exit(0)

with open(gitignore_path, "a") as f:
    for entry in to_add:
        f.write(entry + "\n")
EOF
}

# --- Manifest writing ---
write_manifest() {
  local manifest_path="$TARGET_DIR/.firebreak-manifest.json"

  if [ "$DRY_RUN" = "1" ]; then
    echo "Would write manifest to $manifest_path"
    return
  fi

  local now
  now="$(python3 -c "import datetime; print(datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'))")"

  # Preserve installed_at from existing manifest on upgrade
  local installed_at="$now"
  if [ -f "$manifest_path" ]; then
    local existing_installed_at
    existing_installed_at="$(python3 -c "import json, sys; d=json.load(open(sys.argv[1])); print(d.get('installed_at',''))" "$manifest_path" 2>/dev/null || true)"
    if [ -n "$existing_installed_at" ]; then
      installed_at="$existing_installed_at"
    fi
  fi

  # Build files JSON array
  local files_json
  files_json="$(python3 -c "
import json, sys
files = sys.argv[1:]
print(json.dumps(files))
" "${MANIFEST_FILES[@]+"${MANIFEST_FILES[@]}"}")"

  # Build settings_entries from manifest record, preserving existing manifest entries on upgrade
  local settings_entries_json='{"hooks_added":{},"env_added":{}}'
  local new_record='{"hooks_added":{},"env_added":{}}'
  if [ -n "$MANIFEST_RECORD_FILE" ] && [ -f "$MANIFEST_RECORD_FILE" ] && [ -s "$MANIFEST_RECORD_FILE" ]; then
    new_record="$(python3 -c "
import json, sys
d = json.load(sys.stdin)
print(json.dumps({'hooks_added': d.get('hooks_added', {}), 'env_added': d.get('env_added', {})}))
" < "$MANIFEST_RECORD_FILE" 2>/dev/null || echo '{"hooks_added":{},"env_added":{}}')"
  fi
  # On upgrade, merge with existing manifest's settings_entries so we don't lose prior records
  if [ -f "$manifest_path" ]; then
    settings_entries_json="$(python3 -c "
import json, sys
existing = json.load(open(sys.argv[1])).get('settings_entries', {'hooks_added':{}, 'env_added':{}})
new = json.loads(sys.argv[2])
# Accumulate: preserve all existing entries, add any new ones
merged = {'hooks_added': dict(existing.get('hooks_added', {})), 'env_added': dict(existing.get('env_added', {}))}
for event, groups in new.get('hooks_added', {}).items():
    if event in merged['hooks_added']:
        # Accumulate: add new groups not already recorded
        existing_canonical = {json.dumps(g, sort_keys=True) for g in merged['hooks_added'][event]}
        for g in groups:
            if json.dumps(g, sort_keys=True) not in existing_canonical:
                merged['hooks_added'][event].append(g)
    elif groups:
        merged['hooks_added'][event] = groups
for key, val in new.get('env_added', {}).items():
    if key not in merged['env_added']:
        merged['env_added'][key] = val
print(json.dumps(merged))
" "$manifest_path" "$new_record" 2>/dev/null || echo "$new_record")"
  else
    settings_entries_json="$new_record"
  fi

  # Build backups entry
  local backups_json='{}'
  if [ -n "$BACKUP_FILE" ]; then
    backups_json="$(python3 -c "import json, sys; print(json.dumps({'settings.json': sys.argv[1]}))" "$BACKUP_FILE")"
  fi

  python3 -c "
import json, sys

manifest = {
    # Manifest format version — describes this file's shape, not the product.
    'schema_version': '1.0.0',
    # The installer ships from the same repo at the same version as the assets it
    # installs; there is no separate installer release, so both carry the release
    # version rather than a hand-maintained number that drifts.
    'installer_version': sys.argv[1],
    'firebreak_version': sys.argv[1],
    'install_mode': sys.argv[2],
    'installed_at': sys.argv[3],
    'updated_at': sys.argv[4],
    'target': sys.argv[5],
    'files': json.loads(sys.argv[6]),
    'settings_entries': json.loads(sys.argv[7]),
    'backups': json.loads(sys.argv[8]),
}

with open(sys.argv[9], 'w') as f:
    json.dump(manifest, f, indent=2)
" \
    "$FIREBREAK_VERSION" \
    "$INSTALL_MODE" \
    "$installed_at" \
    "$now" \
    "$TARGET_DIR" \
    "$files_json" \
    "$settings_entries_json" \
    "$backups_json" \
    "$manifest_path"
}

# --- Uninstall ---
uninstall() {
  local manifest_path="$TARGET_DIR/.firebreak-manifest.json"

  if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: Requires Python 3 for uninstallation. Install Python 3 and retry." >&2
    exit 1
  fi

  if [ ! -f "$manifest_path" ]; then
    echo "Error: No firebreak installation found at $TARGET_DIR." >&2
    exit 1
  fi

  # Remove installed files
  local removed_files=0
  while IFS= read -r rel_path; do
    local full_path="$TARGET_DIR/$rel_path"
    if [ -f "$full_path" ]; then
      rm -f "$full_path"
      removed_files=$((removed_files + 1))
    fi
  done < <(python3 -c "
import json, sys
d = json.load(open(sys.argv[1]))
for f in d.get('files', []):
    print(f)
" "$manifest_path")

  # Remove settings entries
  if [ -f "$TARGET_DIR/settings.json" ]; then
    python3 -c "
import json, sys

manifest_path = sys.argv[1]
settings_path = sys.argv[2]

manifest = json.load(open(manifest_path))
settings = json.load(open(settings_path))

settings_entries = manifest.get('settings_entries', {})
hooks_added = settings_entries.get('hooks_added', {})
env_added = settings_entries.get('env_added', {})

hooks_removed = 0
env_removed = 0

# Remove hooks entries
existing_hooks = settings.get('hooks', {})
for event, added_groups in hooks_added.items():
    if event not in existing_hooks:
        continue
    added_canonical = {json.dumps(g, sort_keys=True) for g in added_groups}
    kept = [g for g in existing_hooks[event]
            if json.dumps(g, sort_keys=True) not in added_canonical]
    hooks_removed += len(existing_hooks[event]) - len(kept)
    if kept:
        existing_hooks[event] = kept
    else:
        del existing_hooks[event]
if existing_hooks:
    settings['hooks'] = existing_hooks
elif 'hooks' in settings:
    del settings['hooks']

# Remove env entries only if value matches what was installed
existing_env = settings.get('env', {})
for key, installed_value in env_added.items():
    if key in existing_env and existing_env[key] == installed_value:
        del existing_env[key]
        env_removed += 1
if existing_env:
    settings['env'] = existing_env
elif 'env' in settings:
    del settings['env']

with open(settings_path, 'w') as f:
    json.dump(settings, f, indent=2)

print(str(hooks_removed) + ' hooks removed, ' + str(env_removed) + ' env keys removed')
" "$manifest_path" "$TARGET_DIR/settings.json"
    if [ $? -ne 0 ]; then
      echo "Warning: Failed to remove settings entries. Check $TARGET_DIR/settings.json manually." >&2
    fi
  fi

  # Remove the project-local venv the installer created under fbk-scripts.
  # It is generated by setup_python_venv after the file copy, so it is not in
  # the manifest; without this the fbk-scripts directory is left orphaned and
  # the empty-directory prune below cannot remove it.
  if [ -d "$TARGET_DIR/fbk-scripts/.venv" ]; then
    rm -rf "$TARGET_DIR/fbk-scripts/.venv"
  fi

  # Remove runtime-generated bytecode caches under fbk-scripts. Like the venv,
  # these appear after install (the first time fbk.py runs) and are not in the
  # manifest, so without this the empty-directory prune below cannot remove the
  # fbk-scripts tree — leaving it orphaned exactly as the venv once was.
  if [ -d "$TARGET_DIR/fbk-scripts" ]; then
    find "$TARGET_DIR/fbk-scripts" -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
  fi

  # Remove empty directories that held firebreak files (bottom-up by depth)
  # Collect unique parent dirs from manifest, then rmdir deepest-first
  while IFS= read -r empty_dir; do
    rmdir "$empty_dir" 2>/dev/null || true
  done < <(python3 -c "
import json, sys, os
d = json.load(open(sys.argv[1]))
target = sys.argv[2]
dirs = set()
for f in d.get('files', []):
    p = os.path.dirname(f)
    while p:
        dirs.add(os.path.join(target, p))
        p = os.path.dirname(p)
for d in sorted(dirs, key=lambda x: x.count(os.sep), reverse=True):
    print(d)
" "$manifest_path" "$TARGET_DIR")

  # Remove manifest
  rm -f "$manifest_path"

  echo "Firebreak uninstalled from $TARGET_DIR. $removed_files files removed." >&2
}

# --- Main flow ---

if [ "$MODE" = "uninstall" ]; then
  if [ -z "$TARGET_DIR" ]; then
    prompt_target
  fi
  uninstall
  exit 0
fi

# Install / upgrade mode
if [ -z "$TARGET_DIR" ]; then
  prompt_target
fi

check_prerequisites

# Create the target directory before merging settings or writing the manifest.
# Both merge_settings and write_manifest write into TARGET_DIR but run before
# install_files, which is otherwise what first creates it via mkdir -p. On a
# fresh target those earlier writes fail silently (set -e is off), leaving no
# settings.json and no manifest — and a manifest-less install cannot be uninstalled.
if [ "$DRY_RUN" != "1" ]; then
  mkdir -p "$TARGET_DIR"
fi

# Detect upgrade
IS_UPGRADE=0
if [ -f "$TARGET_DIR/.firebreak-manifest.json" ]; then
  IS_UPGRADE=1
  echo "Existing installation detected — upgrading" >&2
  # Capture the outgoing file list before write_manifest replaces it.
  collect_previous_files
fi

resolve_version
enumerate_assets
merge_settings
create_capture_sentinel
write_gitignore

# Pre-populate MANIFEST_FILES from enumerated assets so write_manifest can record them
MANIFEST_FILES=()
i=0
count=${#DST_FILES[@]}
while [ $i -lt $count ]; do
  MANIFEST_FILES+=("${DST_FILES[$i]#$TARGET_DIR/}")
  i=$((i + 1))
done

write_manifest
install_files
prune_orphans
setup_python_venv

# Build summary counts
hooks_added_count=0
env_added_count=0
if [ -n "$MANIFEST_RECORD_FILE" ] && [ -f "$MANIFEST_RECORD_FILE" ] && [ -s "$MANIFEST_RECORD_FILE" ]; then
  hooks_added_count="$(python3 -c "
import json, sys
d = json.load(open(sys.argv[1]))
total = sum(len(v) for v in d.get('hooks_added', {}).values())
print(total)
" "$MANIFEST_RECORD_FILE" 2>/dev/null || echo 0)"
  env_added_count="$(python3 -c "
import json, sys
d = json.load(open(sys.argv[1]))
print(len(d.get('env_added', {})))
" "$MANIFEST_RECORD_FILE" 2>/dev/null || echo 0)"
fi

files_count=${#MANIFEST_FILES[@]}
backup_display="${BACKUP_FILE:-none}"

if [ "$DRY_RUN" = "1" ]; then
  printf '[DRY RUN] Firebreak would be installed to %s/\n' "$TARGET_DIR" >&2
  printf '  Files to install: %d\n' "$files_count" >&2
  printf '  Files to remove: %d\n' "$PRUNED_COUNT" >&2
  printf '  No changes made.\n' >&2
else
  printf 'Firebreak installed to %s/\n' "$TARGET_DIR" >&2
  printf '  Files installed: %d\n' "$files_count" >&2
  printf '  Files removed: %d\n' "$PRUNED_COUNT" >&2
  printf '  Hooks added: %d\n' "$hooks_added_count" >&2
  printf '  Backups: %s\n' "$backup_display" >&2
fi
