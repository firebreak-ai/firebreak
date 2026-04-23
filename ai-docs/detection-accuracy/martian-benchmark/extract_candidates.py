#!/usr/bin/env python3
"""
Extract candidate findings from Firebreak review markdown files.

Reads reviews/*.md, parses ### F-NN sections, and writes a judge_input JSON
matching the format used by prior consensus judge runs (batch_NN.json):

[
  {
    "instance_id": "...",
    "pr_url": "...",
    "source_repo": "...",
    "golden_count": N,
    "candidate_count": N,
    "golden_comments": [...],
    "golden_severities": [...],
    "candidates": [...]    # full finding body strings
  },
  ...
]
"""

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
REVIEWS_DIR = SCRIPT_DIR / "reviews"
MANIFEST_PATH = SCRIPT_DIR / "manifest.json"
RESULTS_DIR = SCRIPT_DIR / "results"

FINDING_HEADER = re.compile(r"^### (?:F|S)-\d+[^\n]*?(?:[:—]|\s+-\s+)\s*(.+)$", re.MULTILINE)
NEXT_H2 = re.compile(r"^## ", re.MULTILINE)


def extract_findings(md_text: str) -> list[str]:
    """Extract the body of each ### F-NN/S-NN finding heading anywhere in the doc.

    Verified findings use ### F-NN or ### S-NN h3 headings. Rejected/dropped
    sightings appear in retrospective sections as bold-numbered bullets, not
    h3 headings — so heading-based extraction implicitly filters to verified.
    """
    sections = []
    matches = list(FINDING_HEADER.finditer(md_text))
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.end()
        # End at the next finding heading, or at the next h2 (whichever comes first)
        next_finding = matches[i + 1].start() if i + 1 < len(matches) else len(md_text)
        next_h2_match = NEXT_H2.search(md_text, m.end())
        next_h2_pos = next_h2_match.start() if next_h2_match else len(md_text)
        end = min(next_finding, next_h2_pos)
        body = md_text[start:end].strip()
        body = re.sub(r"\n---\s*$", "", body).strip()
        candidate = f"{title}\n\n{body}".strip()
        if len(candidate) >= 20:
            sections.append(candidate)
    return sections


def main():
    parser = argparse.ArgumentParser(description="Extract candidates from review markdown files")
    parser.add_argument("--reviews-dir", default=str(REVIEWS_DIR))
    parser.add_argument("--manifest", default=str(MANIFEST_PATH))
    parser.add_argument(
        "--output",
        default=str(RESULTS_DIR / "judge_input.json"),
        help="Output JSON path",
    )
    parser.add_argument(
        "--missing-ok",
        action="store_true",
        help="Skip manifest entries without a corresponding review file",
    )
    args = parser.parse_args()

    with open(args.manifest) as f:
        manifest = json.load(f)

    reviews_dir = Path(args.reviews_dir)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    judge_input = []
    missing = []
    no_findings = []

    for entry in manifest:
        instance_id = entry["instance_id"]
        review_path = reviews_dir / f"{instance_id}.md"
        if not review_path.exists():
            missing.append(instance_id)
            continue

        md = review_path.read_text()
        candidates = extract_findings(md)
        if not candidates:
            no_findings.append(instance_id)

        golden = entry.get("golden_comments", [])
        golden_comments = [g.get("comment") if isinstance(g, dict) else g for g in golden]
        golden_severities = [g.get("severity") if isinstance(g, dict) else None for g in golden]

        judge_input.append({
            "instance_id": instance_id,
            "pr_url": entry.get("pr_url"),
            "source_repo": entry.get("source_repo"),
            "golden_count": len(golden_comments),
            "candidate_count": len(candidates),
            "golden_comments": golden_comments,
            "golden_severities": golden_severities,
            "candidates": candidates,
        })

    with open(output_path, "w") as f:
        json.dump(judge_input, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(judge_input)} entries to {output_path}")
    print(f"  Missing reviews: {len(missing)}")
    print(f"  Reviews with 0 findings: {len(no_findings)}")
    if missing and not args.missing_ok:
        print(f"  Missing IDs: {', '.join(missing[:5])}{'...' if len(missing) > 5 else ''}")
    if no_findings:
        print(f"  No-finding IDs: {', '.join(no_findings[:5])}{'...' if len(no_findings) > 5 else ''}")


if __name__ == "__main__":
    main()
