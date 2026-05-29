"""Test hash gate — compute SHA-256 manifest and detect test file modifications."""

import argparse
import datetime
import hashlib
import json
import sys
from pathlib import Path

from fbk.slices import TEST_DISCIPLINES


def _is_test_file(path: Path) -> bool:
    return path.name != "test-hashes.json" and (
        "/tests/" in str(path.as_posix()) or "test" in path.name
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _relpath_for(file_path: Path, feature_dir: Path) -> str:
    # Relpath rule — see §Interface contracts #5.
    # Inside feature_dir: path relative to feature_dir (e.g. "tests/test_module.py").
    # Outside feature_dir: last two path components joined with "/" (e.g. "existing_tests/test_existing.py").
    try:
        return str(file_path.relative_to(feature_dir))
    except ValueError:
        return "/".join(file_path.parts[-2:])


def compute_hashes(feature_dir, locked_files=None) -> dict:
    """Find test files and compute SHA-256 hex digests.

    Matches files where the path contains /tests/ or the filename contains
    'test', excluding test-hashes.json. Returns {relative_path: hex_hash}.
    locked_files: optional list of absolute paths to include on top of rglob discovery.
    """
    base = Path(feature_dir)
    candidates = sorted(
        p for p in base.rglob("*")
        if p.is_file() and _is_test_file(p)
    )

    hashes = {}
    for path in candidates:
        digest = _sha256(path)
        rel = _relpath_for(path, base)
        hashes[str(rel)] = digest

    if locked_files:
        for lf in locked_files:
            path = Path(lf)
            if path.is_file() and _is_test_file(path):
                rel = _relpath_for(path, base)
                hashes[str(rel)] = _sha256(path)

    return hashes


def create_manifest(feature_dir, manifest_path=None, locked_files=None) -> dict:
    """Create test-hashes.json manifest in feature_dir.

    Args:
        feature_dir: Directory to scan for test files.
        manifest_path: Where to write the manifest. Defaults to feature_dir/test-hashes.json.
        locked_files: Optional list of absolute paths to pre-existing test files to include.

    Returns gate result dict.
    """
    base = Path(feature_dir)
    flat_hashes = compute_hashes(feature_dir, locked_files=locked_files)

    files = {
        relpath: {
            "sha256": digest,
            "slice": "",
            "test-discipline": TEST_DISCIPLINES[0],
        }
        for relpath, digest in flat_hashes.items()
    }

    manifest = {
        "computed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "files": files,
    }
    if manifest_path is None:
        manifest_path = base / "test-hashes.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    return {"gate": "test-hash", "result": "pass", "action": "created", "files": len(files)}


def verify_manifest(feature_dir, manifest_path=None) -> list[dict]:
    """Verify current test files against existing manifest.

    Returns a list of discrepancy dicts with keys 'kind' and 'path'.
    kind is one of: 'modified', 'missing', 'unexpected'.
    Empty list means clean.
    """
    base = Path(feature_dir)
    if manifest_path is None:
        manifest_path = base / "test-hashes.json"
    with open(manifest_path) as f:
        manifest = json.load(f)

    old = manifest.get("files", {})
    discrepancies = []

    # Resolve each recorded relpath to an actual file path and check modified/missing.
    # For inside-feature_dir entries, actual path = feature_dir / relpath.
    # For outside-feature_dir entries (last-two-components keys), we use feature_dir / relpath
    # as a best-effort resolution; callers using truly external locked files should verify
    # via their own mechanism.
    actual_paths = {}
    for relpath, entry in old.items():
        actual = base / relpath
        actual_paths[relpath] = actual

        if not actual.exists():
            discrepancies.append({"kind": "missing", "path": relpath})
        else:
            recorded_hash = entry["sha256"]
            if _sha256(actual) != recorded_hash:
                discrepancies.append({"kind": "modified", "path": relpath})

    # Shadow-test detection scoped to locked set's directories only.
    # scope_dirs = parent dirs of actual files for every recorded relpath.
    scope_dirs = {
        actual_paths[relpath].parent
        for relpath in old
        if actual_paths[relpath].exists()
    }

    for scope_dir in scope_dirs:
        if not scope_dir.is_dir():
            continue
        for path in scope_dir.iterdir():
            if path.is_file() and _is_test_file(path):
                rel = _relpath_for(path, base)
                if rel not in old:
                    discrepancies.append({"kind": "unexpected", "path": rel})

    return discrepancies


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
        discrepancies = verify_manifest(feature_dir)
        if not discrepancies:
            current_count = len(compute_hashes(feature_dir))
            print(json.dumps({"gate": "test-hash", "result": "pass", "action": "verified", "files": current_count}))
        else:
            for d in discrepancies:
                print(f"{d['kind'].upper()}: {d['path']}", file=sys.stderr)
            sys.exit(2)


if __name__ == "__main__":
    main()
