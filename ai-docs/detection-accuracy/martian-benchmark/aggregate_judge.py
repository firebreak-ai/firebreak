#!/usr/bin/env python3
"""
Aggregate consensus judge results.

Reads judge_consensus.jsonl (from run_judge.sh consensus mode) and produces:
1. judge_consensus.json — same format as judge_manual.json (majority vote)
2. judge_variance.json — disagreements between judges, split votes, confidence

Usage:
  python3 aggregate_judge.py
"""

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
RESULTS_DIR = SCRIPT_DIR / "results"
MANIFEST_PATH = SCRIPT_DIR / "manifest.json"


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Aggregate consensus judge results")
    parser.add_argument("--input", default=str(RESULTS_DIR / "judge_consensus.jsonl"))
    parser.add_argument("--output", default=str(RESULTS_DIR / "judge_consensus.json"))
    parser.add_argument("--variance-output", default=str(RESULTS_DIR / "judge_variance.json"))
    parser.add_argument("--manual", default=str(RESULTS_DIR / "judge_manual.json"),
                       help="Compare against manual judge (optional)")
    args = parser.parse_args()

    # Load manifest for PR URL mapping
    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)
    id_to_url = {e["instance_id"]: e["pr_url"] for e in manifest}
    id_to_goldens = {e["instance_id"]: e["golden_comments"] for e in manifest}

    # Load consensus results
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: {input_path} not found. Run run_judge.sh first.", file=sys.stderr)
        sys.exit(1)

    consensus_map = {}
    variance_records = []
    total_judgments = 0
    unanimous_count = 0
    split_count = 0
    parse_errors = 0

    with open(input_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            instance_id = entry["instance_id"]
            pr_url = id_to_url.get(instance_id)

            if entry.get("status") == "no_candidates":
                golden_count = entry.get("golden_count", 0)
                consensus_map[pr_url] = {str(i + 1): None for i in range(golden_count)}
                continue

            if entry.get("status") != "ok":
                parse_errors += 1
                continue

            consensus = entry.get("consensus", {})
            result = {}

            for golden_idx, vote_data in consensus.items():
                total_judgments += 1
                candidate = vote_data.get("candidate_index")
                vote_count = vote_data.get("vote_count", 0)
                total_votes = vote_data.get("total_votes", 0)
                all_votes = vote_data.get("all_votes", [])

                result[golden_idx] = candidate

                is_unanimous = vote_count == total_votes
                if is_unanimous:
                    unanimous_count += 1
                else:
                    split_count += 1

                    # Record the split for variance analysis
                    goldens = id_to_goldens.get(instance_id, [])
                    gi = int(golden_idx) - 1
                    golden_text = goldens[gi]["comment"][:150] if gi < len(goldens) else "?"
                    golden_sev = goldens[gi]["severity"] if gi < len(goldens) else "?"

                    variance_records.append({
                        "instance_id": instance_id,
                        "pr_url": pr_url,
                        "golden_index": golden_idx,
                        "golden_severity": golden_sev,
                        "golden_comment": golden_text,
                        "consensus": candidate,
                        "vote_count": vote_count,
                        "total_votes": total_votes,
                        "all_votes": all_votes,
                    })

            if pr_url:
                consensus_map[pr_url] = result

    # Write consensus judge JSON
    output = {
        "_metadata": {
            "judge": "consensus (3x Opus sub-agents, majority vote)",
            "date": "2026-04-09",
            "firebreak_version": "v0.3.5",
            "threshold": "minor+",
            "judges_per_pr": 3,
            "aggregation": "majority vote",
            "notes": "Golden index and candidate index are 1-based. null means no match.",
        }
    }
    output.update(consensus_map)

    output_path = Path(args.output)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Consensus judge: {output_path} ({len(consensus_map)} PRs)")
    print(f"  Total judgments: {total_judgments}")
    print(f"  Unanimous: {unanimous_count} ({unanimous_count/total_judgments*100:.1f}%)")
    print(f"  Split vote: {split_count} ({split_count/total_judgments*100:.1f}%)")
    if parse_errors:
        print(f"  Parse errors: {parse_errors}")

    # Write variance report
    variance_path = Path(args.variance_output)
    with open(variance_path, "w") as f:
        json.dump(variance_records, f, indent=2)

    print(f"\nVariance report: {variance_path} ({len(variance_records)} split votes)")

    # Breakdown of split votes
    if variance_records:
        match_splits = [v for v in variance_records if v["consensus"] is not None]
        null_splits = [v for v in variance_records if v["consensus"] is None]
        high_splits = [v for v in variance_records if v["golden_severity"] in ("High", "Critical")]
        print(f"  Split → match: {len(match_splits)}")
        print(f"  Split → null: {len(null_splits)}")
        print(f"  High/Critical splits: {len(high_splits)}")

        print(f"\n=== SPLIT VOTES (non-unanimous) ===")
        for v in sorted(variance_records, key=lambda x: -{"Critical": 4, "High": 3, "Medium": 2, "Low": 1}.get(x["golden_severity"], 0)):
            votes_str = ", ".join(str(x) if x is not None else "null" for x in v["all_votes"])
            consensus_str = f"→ {v['consensus']}" if v["consensus"] is not None else "→ null"
            print(f"  [{v['golden_severity']}] {v['instance_id']} G{v['golden_index']}: [{votes_str}] {consensus_str} ({v['vote_count']}/{v['total_votes']})")
            print(f"    {v['golden_comment'][:120]}")

    # Compare against manual judge if available
    manual_path = Path(args.manual)
    if manual_path.exists():
        with open(manual_path) as f:
            manual_data = json.load(f)
        manual_data.pop("_metadata", None)

        agreements = 0
        new_matches = 0
        lost_matches = 0
        different = 0

        all_urls = set(consensus_map.keys()) | set(manual_data.keys())
        for pr_url in sorted(all_urls):
            auto = consensus_map.get(pr_url, {})
            manual = manual_data.get(pr_url, {})
            for idx in set(auto.keys()) | set(manual.keys()):
                a = auto.get(idx)
                m = manual.get(idx)
                if a == m:
                    agreements += 1
                elif m is None and a is not None:
                    new_matches += 1
                elif m is not None and a is None:
                    lost_matches += 1
                else:
                    different += 1

        total_compared = agreements + new_matches + lost_matches + different
        print(f"\n=== VS MANUAL JUDGE ===")
        print(f"  Agreements:      {agreements} ({agreements/total_compared*100:.1f}%)")
        print(f"  New matches:     {new_matches} (consensus found, manual missed)")
        print(f"  Lost matches:    {lost_matches} (manual had, consensus missed)")
        print(f"  Different match: {different} (both matched, different candidate)")


if __name__ == "__main__":
    main()
