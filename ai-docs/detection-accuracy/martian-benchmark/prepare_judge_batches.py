#!/usr/bin/env python3
"""
Prepare judge batches for sub-agent evaluation.

Reads manifest.json (golden comments) and reviews/*.md (Firebreak findings),
produces a JSONL file with one entry per PR containing the data each judge
agent needs to evaluate.

Usage:
  python3 prepare_judge_batches.py [--output judge_batches.jsonl]
"""

import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
MANIFEST_PATH = SCRIPT_DIR / "manifest.json"
REVIEWS_DIR = SCRIPT_DIR / "reviews"

# Reuse the summary table parser from build_deviation_map
sys.path.insert(0, str(SCRIPT_DIR))
from build_deviation_map import parse_review


def extract_finding_detail(review_path: Path, finding_id: str) -> str:
    """Extract the full finding section for a given finding ID."""
    if not review_path.exists():
        return ""
    text = review_path.read_text()

    # Find the finding section header
    pattern = re.compile(
        rf'^(#{2,4})\s+{re.escape(finding_id)}\b.*$',
        re.MULTILINE
    )
    match = pattern.search(text)
    if not match:
        return ""

    header_level = len(match.group(1))
    start = match.start()

    # Find end: next header of same or higher level, or "## Findings Summary", or "## Retrospective"
    rest = text[match.end():]
    end_pattern = re.compile(
        rf'^#{{{1},{header_level}}}\s+',
        re.MULTILINE
    )
    end_match = end_pattern.search(rest)
    if end_match:
        end = match.end() + end_match.start()
    else:
        end = len(text)

    section = text[start:end].strip()
    # Truncate very long sections
    if len(section) > 2000:
        section = section[:2000] + "\n[truncated]"
    return section


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Prepare judge batches")
    parser.add_argument("--output", default=str(SCRIPT_DIR / "results" / "judge_batches.jsonl"))
    parser.add_argument("--limit", type=int, default=0, help="Limit to N PRs (0=all)")
    parser.add_argument("--repo", default="", help="Filter to one source repo")
    args = parser.parse_args()

    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)

    batches = []
    skipped = 0

    for entry in manifest:
        if args.repo and entry["source_repo"] != args.repo:
            continue

        instance_id = entry["instance_id"]
        review_path = REVIEWS_DIR / f"{instance_id}.md"

        findings = parse_review(review_path)
        if not findings and not review_path.exists():
            skipped += 1
            continue

        # Build candidate list with detail for each finding
        candidates = []
        for i, f in enumerate(findings):
            detail = extract_finding_detail(review_path, f["id"])
            candidates.append({
                "index": i + 1,
                "id": f["id"],
                "type": f["type"],
                "severity": f["severity"],
                "description": f["description"],
                "detail": detail,
            })

        batch = {
            "instance_id": instance_id,
            "pr_url": entry["pr_url"],
            "pr_title": entry.get("pr_title", ""),
            "source_repo": entry["source_repo"],
            "golden_comments": [
                {"index": i + 1, "comment": g["comment"], "severity": g["severity"]}
                for i, g in enumerate(entry["golden_comments"])
            ],
            "candidates": candidates,
            "golden_count": len(entry["golden_comments"]),
            "candidate_count": len(candidates),
        }
        batches.append(batch)

        if args.limit and len(batches) >= args.limit:
            break

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        for batch in batches:
            f.write(json.dumps(batch) + "\n")

    total_pairs = sum(b["golden_count"] * b["candidate_count"] for b in batches)
    print(f"Prepared {len(batches)} batches ({skipped} skipped, no review)")
    print(f"Total golden: {sum(b['golden_count'] for b in batches)}")
    print(f"Total candidates: {sum(b['candidate_count'] for b in batches)}")
    print(f"Total pairs to judge: {total_pairs}")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()
