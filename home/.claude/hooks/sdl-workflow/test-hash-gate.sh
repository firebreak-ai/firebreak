#!/usr/bin/env bash
# test-hash-gate.sh — Compute SHA-256 manifest and detect test file modifications
# chmod +x test-hash-gate.sh
set -uo pipefail

FEATURE_DIR="${1:-}"

[[ -z "$FEATURE_DIR" ]] && { echo "Usage: test-hash-gate.sh <feature-dir>" >&2; exit 2; }
[[ -d "$FEATURE_DIR" ]] || { echo "Directory not found: $FEATURE_DIR" >&2; exit 2; }

MANIFEST="$FEATURE_DIR/test-hashes.json"

# Find test files: under tests/ dir or with *test* in name
mapfile -t FILES < <(find "$FEATURE_DIR" -type f \( -path "*/tests/*" -o -name "*test*" \) ! -name "test-hashes.json" | sort)

# No test files
if [[ ${#FILES[@]} -eq 0 ]]; then
  printf '{"gate":"test-hash","result":"pass","files":0,"note":"no test files found"}\n'
  exit 0
fi

# Compute hashes — build "relative_path hash" lines
HASH_LINES=""
for f in "${FILES[@]}"; do
  rel="${f#$FEATURE_DIR/}"
  hash=$(sha256sum "$f" | cut -d' ' -f1)
  HASH_LINES+="$rel $hash"$'\n'
done

if [[ ! -f "$MANIFEST" ]]; then
  # First run — create manifest
  echo "$HASH_LINES" | python3 -c "
import json, sys, datetime

hash_data = sys.stdin.read().strip()
manifest_path = sys.argv[1]

files = {}
for line in hash_data.split('\n'):
    if line.strip():
        parts = line.strip().split(' ', 1)
        files[parts[0]] = parts[1]

manifest = {
    'files': files,
    'computed_at': datetime.datetime.now(datetime.timezone.utc).isoformat()
}

with open(manifest_path, 'w') as f:
    json.dump(manifest, f, indent=2)

count = len(files)
print(json.dumps({'gate': 'test-hash', 'result': 'pass', 'action': 'created', 'files': count}))
" "$MANIFEST"
  exit 0
else
  # Subsequent run — compare
  RESULT=$(echo "$HASH_LINES" | python3 -c "
import json, sys

manifest_path = sys.argv[1]
hash_data = sys.stdin.read().strip()

with open(manifest_path) as f:
    manifest = json.load(f)

old_files = manifest.get('files', {})

current = {}
for line in hash_data.split('\n'):
    if line.strip():
        parts = line.strip().split(' ', 1)
        current[parts[0]] = parts[1]

errors = []

for path in sorted(old_files):
    if path not in current:
        errors.append(f'MISSING: {path}')

for path in sorted(current):
    if path not in old_files:
        errors.append(f'UNEXPECTED: {path}')

for path in sorted(current):
    if path in old_files and current[path] != old_files[path]:
        errors.append(f'MODIFIED: {path} (expected: {old_files[path]}, actual: {current[path]})')

if errors:
    for e in errors:
        print(e, file=sys.stderr)
    sys.exit(2)
else:
    print(json.dumps({'gate': 'test-hash', 'result': 'pass', 'action': 'verified', 'files': len(current)}))
" "$MANIFEST" 2>&1)
  RC=$?
  if [[ $RC -ne 0 ]]; then
    echo "$RESULT" >&2
    exit 2
  fi
  echo "$RESULT"
  exit 0
fi
