#!/usr/bin/env python3
"""
Fetch PR diffs for the Martian Code Review Benchmark.

Reads golden comment files from the cloned benchmark repo, extracts PR URLs,
and fetches each PR's diff via the GitHub CLI. Saves diffs to diffs/.

Prerequisites:
  - gh CLI authenticated (gh auth status)
  - Benchmark repo cloned to /tmp/code-review-benchmark

Usage:
  python3 fetch_pr_diffs.py [--limit N] [--repo REPO_NAME]
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

BENCHMARK_REPO = Path("/tmp/code-review-benchmark")
GOLDEN_DIR = BENCHMARK_REPO / "offline" / "golden_comments"
DIFFS_DIR = Path(__file__).parent / "diffs"


def parse_pr_url(url: str) -> tuple[str, str, str]:
    """Extract owner, repo, pr_number from a GitHub PR URL."""
    # https://github.com/calcom/cal.com/pull/8087
    parts = url.rstrip("/").split("/")
    pr_number = parts[-1]
    repo = parts[-3]
    owner = parts[-4]
    return owner, repo, pr_number


def fetch_diff(owner: str, repo: str, pr_number: str) -> str:
    """Fetch PR diff via gh CLI."""
    result = subprocess.run(
        [
            "gh", "api",
            f"repos/{owner}/{repo}/pulls/{pr_number}",
            "-H", "Accept: application/vnd.github.v3.diff",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"gh api failed for {owner}/{repo}#{pr_number}: {result.stderr}")
    return result.stdout


def load_golden_prs() -> list[dict]:
    """Load all PRs from golden comment files."""
    prs = []
    for f in sorted(GOLDEN_DIR.glob("*.json")):
        with open(f) as fh:
            data = json.load(fh)
        for entry in data:
            entry["source_file"] = f.stem
            prs.append(entry)
    return prs


def main():
    parser = argparse.ArgumentParser(description="Fetch PR diffs for Martian benchmark")
    parser.add_argument("--limit", type=int, help="Limit number of PRs to fetch")
    parser.add_argument("--repo", help="Only fetch from specific repo (e.g., cal_dot_com)")
    parser.add_argument("--force", action="store_true", help="Re-fetch existing diffs")
    args = parser.parse_args()

    if not GOLDEN_DIR.exists():
        print(f"Error: {GOLDEN_DIR} not found. Clone the benchmark repo first:")
        print("  git clone https://github.com/withmartian/code-review-benchmark /tmp/code-review-benchmark")
        sys.exit(1)

    DIFFS_DIR.mkdir(exist_ok=True)

    prs = load_golden_prs()
    if args.repo:
        prs = [p for p in prs if p["source_file"] == args.repo]

    if args.limit:
        prs = prs[:args.limit]

    print(f"Fetching diffs for {len(prs)} PRs...")

    # Also build a manifest for later use
    manifest = []

    for i, pr in enumerate(prs):
        url = pr["url"]
        owner, repo, pr_number = parse_pr_url(url)
        source = pr["source_file"]
        safe_name = f"{source}__{owner}__{repo}__PR{pr_number}"
        diff_path = DIFFS_DIR / f"{safe_name}.diff"

        if diff_path.exists() and not args.force:
            print(f"  [{i+1}/{len(prs)}] SKIP {owner}/{repo}#{pr_number} (exists)")
            manifest.append({
                "instance_id": safe_name,
                "source_repo": source,
                "pr_url": url,
                "owner": owner,
                "repo": repo,
                "pr_number": pr_number,
                "pr_title": pr["pr_title"],
                "diff_path": str(diff_path),
                "golden_comments": pr["comments"],
            })
            continue

        print(f"  [{i+1}/{len(prs)}] Fetching {owner}/{repo}#{pr_number}...", end=" ")
        try:
            diff = fetch_diff(owner, repo, pr_number)
            diff_path.write_text(diff)
            print(f"OK ({len(diff)} bytes)")
        except Exception as e:
            print(f"FAILED: {e}")
            continue

        manifest.append({
            "instance_id": safe_name,
            "source_repo": source,
            "pr_url": url,
            "owner": owner,
            "repo": repo,
            "pr_number": pr_number,
            "pr_title": pr["pr_title"],
            "diff_path": str(diff_path),
            "golden_comments": pr["comments"],
        })

    # Save manifest
    manifest_path = Path(__file__).parent / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nManifest saved: {manifest_path} ({len(manifest)} entries)")


if __name__ == "__main__":
    main()
