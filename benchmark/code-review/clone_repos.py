#!/usr/bin/env python3
"""
Clone source repos as shared bare caches and create per-PR worktrees with the
PR diff applied. Supports two modes:

  --all           process every manifest entry (idempotent: skip if ready)
  --instance ID   process a single instance_id (used inline by run_reviews.sh)

For each unique owner/repo, creates a bare mirror with --filter=blob:none.
For each PR, creates a worktree at base_sha and applies the PR diff (3-way).

Writes `worktrees/<instance_id>/.fbk-benchmark-status` with one of:
  apply:clean          — diff applied cleanly
  apply:3way-merge     — applied with 3-way merge (minor conflicts resolved)
  apply:failed-fallback-head  — diff failed, fell back to head_sha checkout
  apply:failed                — both diff apply and head_sha checkout failed

Usage:
  python3 clone_repos.py --all
  python3 clone_repos.py --instance cal_dot_com__calcom__cal.com__PR8087
  python3 clone_repos.py --instance ID --refresh  # nuke + rebuild worktree
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
MANIFEST_PATH = SCRIPT_DIR / "manifest.json"
DIFFS_DIR = SCRIPT_DIR / "diffs"
REPOS_DIR = SCRIPT_DIR / "repos"
WORKTREES_DIR = SCRIPT_DIR / "worktrees"

STATUS_CLEAN = "apply:clean"
STATUS_3WAY = "apply:3way-merge"
STATUS_HEAD = "apply:failed-fallback-head"
STATUS_FAILED = "apply:failed"


def run(cmd, cwd=None, check=False, capture=True, timeout=300):
    result = subprocess.run(
        cmd, cwd=cwd, check=check,
        capture_output=capture, text=True, timeout=timeout,
    )
    return result


def bare_repo_path(owner: str, repo: str) -> Path:
    return REPOS_DIR / f"{owner}__{repo}.git"


def worktree_path(instance_id: str) -> Path:
    return WORKTREES_DIR / instance_id


def ensure_bare(owner: str, repo: str) -> Path:
    """Create the shared bare mirror for owner/repo if missing. Returns path."""
    bare = bare_repo_path(owner, repo)
    if bare.exists():
        return bare
    REPOS_DIR.mkdir(parents=True, exist_ok=True)
    url = f"https://github.com/{owner}/{repo}.git"
    print(f"  cloning bare: {url} → {bare}")
    r = run([
        "git", "clone", "--bare",
        "--filter=blob:none",
        url, str(bare),
    ], timeout=1800)
    if r.returncode != 0:
        raise RuntimeError(f"bare clone failed: {r.stderr.strip()}")
    return bare


def fetch_sha(bare: Path, sha: str) -> bool:
    """Ensure the given sha is in the bare repo. Returns True on success."""
    r = run(["git", "-C", str(bare), "cat-file", "-e", sha])
    if r.returncode == 0:
        return True
    r = run(["git", "-C", str(bare), "fetch", "origin", sha], timeout=600)
    if r.returncode == 0:
        return True
    # Some forks don't allow fetching arbitrary SHAs directly; try fetching the PR ref
    return False


def fetch_pr_ref(bare: Path, pr_number: str) -> bool:
    """Fallback: fetch the PR's head ref — works even when direct SHA fetch is blocked."""
    r = run([
        "git", "-C", str(bare), "fetch", "origin",
        f"+refs/pull/{pr_number}/head:refs/pull/{pr_number}/head",
    ], timeout=600)
    return r.returncode == 0


def create_worktree(bare: Path, instance_id: str, sha: str) -> Path:
    wt = worktree_path(instance_id)
    if wt.exists():
        return wt
    WORKTREES_DIR.mkdir(parents=True, exist_ok=True)
    r = run(["git", "-C", str(bare), "worktree", "add", "--detach", str(wt), sha])
    if r.returncode != 0:
        raise RuntimeError(f"worktree add failed: {r.stderr.strip()}")
    return wt


def apply_diff(wt: Path, diff_path: Path) -> str:
    """Apply the PR diff in the worktree. Returns status string."""
    # Try --3way first (handles minor context drift)
    r = run([
        "git", "-C", str(wt), "apply", "--3way",
        str(diff_path),
    ], timeout=120)
    if r.returncode == 0:
        # Distinguish clean apply from 3-way-resolved apply
        # git apply doesn't tell us; inspect stderr for "Falling back to three-way merge"
        if "three-way merge" in r.stderr.lower() or "fell back" in r.stderr.lower():
            return STATUS_3WAY
        return STATUS_CLEAN
    return "failed"


def remove_worktree(bare: Path, wt: Path):
    if wt.exists():
        run(["git", "-C", str(bare), "worktree", "remove", "--force", str(wt)])


def process_entry(entry: dict, refresh: bool = False) -> str:
    """Set up the worktree for one manifest entry. Returns status string."""
    instance_id = entry["instance_id"]
    owner = entry["owner"]
    repo = entry["repo"]
    pr_number = str(entry["pr_number"])
    base_sha = entry.get("base_sha")
    head_sha = entry.get("head_sha")

    if not base_sha:
        return STATUS_FAILED + ":missing-base-sha"

    wt = worktree_path(instance_id)
    status_file = wt / ".fbk-benchmark-status"

    if wt.exists() and not refresh and status_file.exists():
        return status_file.read_text().strip()

    if refresh:
        bare = bare_repo_path(owner, repo)
        remove_worktree(bare, wt)

    bare = ensure_bare(owner, repo)

    # Ensure base_sha is fetched
    if not fetch_sha(bare, base_sha):
        # Try fetching the PR ref as a fallback
        if not fetch_pr_ref(bare, pr_number):
            return STATUS_FAILED + ":base-fetch-failed"
        # Try base_sha again — pulling the PR ref may have pulled the base too
        if not fetch_sha(bare, base_sha):
            return STATUS_FAILED + ":base-sha-unreachable"

    # Create worktree at base
    try:
        wt = create_worktree(bare, instance_id, base_sha)
    except Exception as e:
        return STATUS_FAILED + f":worktree-add:{e}"

    # Apply the PR diff
    diff_path = DIFFS_DIR / f"{instance_id}.diff"
    if not diff_path.exists():
        status_file.write_text(STATUS_FAILED + ":missing-diff")
        return status_file.read_text().strip()

    status = apply_diff(wt, diff_path)
    if status in (STATUS_CLEAN, STATUS_3WAY):
        status_file.write_text(status)
        return status

    # Fallback: try checking out head_sha instead of applying diff
    if head_sha and fetch_sha(bare, head_sha):
        remove_worktree(bare, wt)
        try:
            wt = create_worktree(bare, instance_id, head_sha)
            status_file.write_text(STATUS_HEAD)
            return STATUS_HEAD
        except Exception:
            pass

    # Both failed — leave worktree at base, mark failed (caller may fall back to diff-only)
    if wt.exists():
        status_file.write_text(STATUS_FAILED + ":apply-and-head-failed")
    return STATUS_FAILED + ":apply-and-head-failed"


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true")
    group.add_argument("--instance", help="process a single instance_id")
    parser.add_argument("--refresh", action="store_true",
                        help="nuke and rebuild worktree even if it exists")
    args = parser.parse_args()

    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)

    if args.instance:
        entry = next((e for e in manifest if e["instance_id"] == args.instance), None)
        if not entry:
            print(f"ERROR: instance not found: {args.instance}", file=sys.stderr)
            sys.exit(1)
        entries = [entry]
    else:
        entries = manifest

    counts = {}
    for entry in entries:
        print(f"[{entry['instance_id']}]")
        status = process_entry(entry, refresh=args.refresh)
        print(f"  status: {status}")
        counts[status] = counts.get(status, 0) + 1

    print(f"\n{'=' * 60}")
    for status, count in sorted(counts.items()):
        print(f"  {status}: {count}")
    print(f"  Total: {len(entries)}")


if __name__ == "__main__":
    main()
