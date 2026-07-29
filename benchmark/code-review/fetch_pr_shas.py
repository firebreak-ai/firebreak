#!/usr/bin/env python3
"""
Enrich manifest.json with base_sha, head_sha, and base_ref for each PR.

Uses `gh api` to query the GitHub API — requires gh CLI with a valid auth token.
Idempotent: skips entries that already have base_sha populated.

Usage:
  python3 fetch_pr_shas.py            # enrich all missing entries
  python3 fetch_pr_shas.py --force    # re-fetch all entries (overwrite)
  python3 fetch_pr_shas.py --dry-run  # print what would change, don't write
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
MANIFEST_PATH = SCRIPT_DIR / "manifest.json"


def fetch_sha(owner: str, repo: str, pr_number: str) -> dict:
    cmd = [
        "gh", "api",
        f"repos/{owner}/{repo}/pulls/{pr_number}",
        "--jq", '{base_sha:.base.sha, head_sha:.head.sha, base_ref:.base.ref}',
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"gh api failed for {owner}/{repo}#{pr_number}: {result.stderr.strip()}")
    return json.loads(result.stdout)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true",
                        help="Re-fetch even entries that already have base_sha")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print planned fetches without writing")
    args = parser.parse_args()

    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)

    enriched = 0
    skipped = 0
    failed = []

    for entry in manifest:
        if entry.get("base_sha") and not args.force:
            skipped += 1
            continue

        instance_id = entry["instance_id"]
        owner = entry["owner"]
        repo = entry["repo"]
        pr_number = str(entry["pr_number"])

        if args.dry_run:
            print(f"WOULD FETCH: {owner}/{repo}#{pr_number} ({instance_id})")
            enriched += 1
            continue

        try:
            sha_info = fetch_sha(owner, repo, pr_number)
            entry["base_sha"] = sha_info["base_sha"]
            entry["head_sha"] = sha_info["head_sha"]
            entry["base_ref"] = sha_info["base_ref"]
            print(f"OK   {instance_id}: base={sha_info['base_sha'][:12]} head={sha_info['head_sha'][:12]} ref={sha_info['base_ref']}")
            enriched += 1
        except Exception as e:
            print(f"FAIL {instance_id}: {e}", file=sys.stderr)
            failed.append(instance_id)

    if not args.dry_run and enriched > 0:
        with open(MANIFEST_PATH, "w") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
            f.write("\n")

    print(f"\n{'=' * 60}")
    print(f"Enriched: {enriched}")
    print(f"Skipped (already had base_sha): {skipped}")
    print(f"Failed:   {len(failed)}")
    if failed:
        print(f"Failed IDs: {', '.join(failed[:10])}")
        sys.exit(1)


if __name__ == "__main__":
    main()
