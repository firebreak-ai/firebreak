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

cleanup_temps() {
  [ -n "$MERGE_OUTPUT_FILE" ] && rm -f "$MERGE_OUTPUT_FILE"
  [ -n "$SETTINGS_JSON_FILE" ] && rm -f "$SETTINGS_JSON_FILE"
  [ -n "$MANIFEST_RECORD_FILE" ] && rm -f "$MANIFEST_RECORD_FILE"
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

# Determine install mode from target path
if [ -n "$TARGET_DIR" ]; then
  if [ "$TARGET_DIR" = "$HOME/.claude" ]; then
    INSTALL_MODE=global
  else
    INSTALL_MODE=project
  fi
fi

# --- Prerequisite checking ---
check_pyyaml() {
  if python3 -c "import yaml" >/dev/null 2>&1; then
    return 0
  fi

  echo "Firebreak requires Python's pyyaml package at runtime (used by fbk/config.py)." >&2

  if [ "$DRY_RUN" = "1" ]; then
    echo "[dry-run] Would prompt to install pyyaml; skipping in dry-run." >&2
    return 0
  fi

  if [ ! -t 0 ]; then
    echo "  Install later with:  python3 -m pip install --user pyyaml" >&2
    return 0
  fi

  printf 'Install pyyaml now via python3 -m pip install --user pyyaml? [Y/n] ' >&2
  read -r answer
  case "$answer" in
    ""|y|Y|yes|YES)
      if python3 -m pip install --user pyyaml >&2; then
        echo "pyyaml installed." >&2
      else
        echo "Warning: pip install failed. Install manually: python3 -m pip install --user pyyaml" >&2
        echo "  (If your system uses PEP 668 externally-managed Python, use pipx or a venv.)" >&2
      fi
      ;;
    *)
      echo "Skipped. Install manually before running firebreak: python3 -m pip install --user pyyaml" >&2
      ;;
  esac
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

  check_pyyaml
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
    \( -type d \( -name .venv -o -name __pycache__ -o -name .pytest_cache \) -prune \) \
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
    sed 's|\\"\$HOME\\"/\.claude/|\\"\$CLAUDE_PROJECT_DIR\\"/\.claude/|g' "$firebreak_settings" > "$merge_source"
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

  # Write merged settings
  cp "$SETTINGS_JSON_FILE" "$TARGET_DIR/settings.json"
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
    'schema_version': '1.0.0',
    'installer_version': '0.1.0',
    'firebreak_version': '0.1.0',
    'install_mode': sys.argv[1],
    'installed_at': sys.argv[2],
    'updated_at': sys.argv[3],
    'target': sys.argv[4],
    'files': json.loads(sys.argv[5]),
    'settings_entries': json.loads(sys.argv[6]),
    'backups': json.loads(sys.argv[7]),
}

with open(sys.argv[8], 'w') as f:
    json.dump(manifest, f, indent=2)
" \
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

# Detect upgrade
IS_UPGRADE=0
if [ -f "$TARGET_DIR/.firebreak-manifest.json" ]; then
  IS_UPGRADE=1
  echo "Existing installation detected — upgrading" >&2
fi

enumerate_assets
merge_settings

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
  printf '  No changes made.\n' >&2
else
  printf 'Firebreak installed to %s/\n' "$TARGET_DIR" >&2
  printf '  Files installed: %d\n' "$files_count" >&2
  printf '  Hooks added: %d\n' "$hooks_added_count" >&2
  printf '  Backups: %s\n' "$backup_display" >&2
fi
