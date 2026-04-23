"""Test hash gate — compute SHA-256 manifest and detect test file modifications."""

import argparse
import datetime
import hashlib
import json
import sys
from pathlib import Path


def compute_hashes(feature_dir) -> dict:
    """Find test files and compute SHA-256 hex digests.

    Matches files where the path contains /tests/ or the filename contains
    'test', excluding test-hashes.json. Returns {relative_path: hex_hash}.
    """
    base = Path(feature_dir)
    candidates = sorted(
        p for p in base.rglob("*")
        if p.is_file()
        and p.name != "test-hashes.json"
        and ("/tests/" in str(p.as_posix()) or "test" in p.name)
    )

    hashes = {}
    for path in candidates:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        rel = path.relative_to(base)
        hashes[str(rel)] = digest
    return hashes


def create_manifest(feature_dir, manifest_path=None) -> dict:
    """Create test-hashes.json manifest in feature_dir.

    Args:
        feature_dir: Directory to scan for test files
        manifest_path: Where to write the manifest. Defaults to feature_dir/test-hashes.json.

    Returns gate result dict.
    """
    files = compute_hashes(str(feature_dir))
    manifest = {
        "files": files,
        "computed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    if manifest_path is None:
        manifest_path = Path(feature_dir) / "test-hashes.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    return {"gate": "test-hash", "result": "pass", "action": "created", "files": len(files)}


def verify_manifest(feature_dir, manifest_path=None) -> dict:
    """Verify current test files against existing manifest.

    Args:
        feature_dir: Directory to scan for test files
        manifest_path: Path to manifest file. Defaults to feature_dir/test-hashes.json.

    Returns 'pass' string on success, or error string describing discrepancies.
    """
    if manifest_path is None:
        manifest_path = Path(feature_dir) / "test-hashes.json"
    with open(manifest_path) as f:
        manifest = json.load(f)

    old_files = manifest.get("files", {})
    current = compute_hashes(feature_dir)

    errors = []
    for path in sorted(old_files):
        if path not in current:
            errors.append(f"MISSING: {path}")

    for path in sorted(current):
        if path not in old_files:
            errors.append(f"UNEXPECTED: {path}")

    for path in sorted(current):
        if path in old_files and current[path] != old_files[path]:
            errors.append(
                f"MODIFIED: {path} (expected: {old_files[path]}, actual: {current[path]})"
            )

    if errors:
        return "\n".join(errors)

    return "pass"


def main():
    parser = argparse.ArgumentParser(
        description="Compute or verify SHA-256 manifest for test files."
    )
    parser.add_argument("feature_dir", help="Feature directory to scan")
    args = parser.parse_args()

    feature_dir = args.feature_dir
    if not Path(feature_dir).is_dir():
        print(f"Directory not found: {feature_dir}", file=sys.stderr)
        sys.exit(2)

    hashes = compute_hashes(feature_dir)
    if not hashes:
        print(
            json.dumps(
                {"gate": "test-hash", "result": "pass", "files": 0, "note": "no test files found"}
            )
        )
        sys.exit(0)

    manifest_path = Path(feature_dir) / "test-hashes.json"
    if not manifest_path.exists():
        result = create_manifest(feature_dir)
        print(json.dumps(result))
    else:
        verify_result = verify_manifest(feature_dir)
        if verify_result == "pass":
            print(json.dumps({"gate": "test-hash", "result": "pass", "action": "verified", "files": len(compute_hashes(feature_dir))}))
        else:
            for line in verify_result.splitlines():
                print(line, file=sys.stderr)
            sys.exit(2)


if __name__ == "__main__":
    main()
