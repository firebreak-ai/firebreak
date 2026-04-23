#!/usr/bin/env python3
"""
Aggregate 3 independent Sonnet judge runs into consensus results.

Reads multiple judge run JSON files (each a per-PR judgment array),
applies majority vote per (PR, golden), computes TP/FP/FN per PR.

Each judge run JSON has format:
[
  {
    "instance_id": "...",
    "pr_url": "...",
    "judgments": [
      {"golden_index": 1, "matched_candidate_index": N|null, "match": bool, "reasoning": "..."},
      ...
    ]
  },
  ...
]

Output JSON has format:
{
  "_metadata": {...},
  "_summary": {tp, fp, fn, precision, recall, f1, ...},
  "_per_repo": {repo: {tp, fp, fn, precision, recall, f1, prs}},
  "<pr_url>": {
    "instance_id": "...",
    "tp": N, "fp": N, "fn": N,
    "judgments": {
      "1": {"match": true, "candidate_index": 3, "votes": "3/3", "reasoning": "..."},
      ...
    },
    "false_positives": [{"candidate_index": N}, ...],
    "missing_judges": [...]   # judge IDs that didn't cover this PR
  }
}

Usage:
  python3 aggregate_consensus.py \
    --inputs /tmp/judge_run_1.json /tmp/judge_run_2.json /tmp/judge_run_3.json \
    --judge-input results/judge_input_v040sd.json \
    --output results/judge_consensus_v040sd.json \
    --tool firebreak-v0.4.0-single-detector \
    --model claude-sonnet-4-6
"""

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def load_judge_run(path: Path) -> dict:
    """Load a judge run; return {instance_id: {golden_index: judgment_dict}}."""
    with open(path) as f:
        data = json.load(f)
    out = {}
    for entry in data:
        iid = entry.get("instance_id")
        if not iid:
            continue
        judgments = {}
        for j in entry.get("judgments", []):
            gi = j.get("golden_index")
            if gi is None:
                continue
            judgments[int(gi)] = j
        out[iid] = judgments
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", nargs="+", required=True, help="Judge run JSON files")
    parser.add_argument("--judge-input", required=True, help="Original judge_input.json")
    parser.add_argument("--output", required=True, help="Aggregated consensus output JSON")
    parser.add_argument("--tool", default="firebreak", help="Tool name for metadata")
    parser.add_argument("--model", default="claude-sonnet-4-6", help="Judge model for metadata")
    args = parser.parse_args()

    with open(args.judge_input) as f:
        judge_input = json.load(f)

    # Load all judge runs
    judge_runs = []
    for path in args.inputs:
        try:
            judge_runs.append(load_judge_run(Path(path)))
        except Exception as e:
            print(f"WARN: failed to load {path}: {e}", file=sys.stderr)

    if not judge_runs:
        print("ERROR: no judge runs loaded", file=sys.stderr)
        sys.exit(1)

    n_judges = len(judge_runs)
    print(f"Aggregating {n_judges} judge runs across {len(judge_input)} PRs")

    out = {
        "_metadata": {
            "judge": f"consensus ({n_judges}x {args.model}, majority vote)",
            "model": args.model,
            "judges_per_pair": n_judges,
            "aggregation": "majority vote",
            "tool": args.tool,
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "judge_inputs": args.inputs,
            "notes": "Golden index and candidate index are 1-based. null candidate_index means no match.",
        },
    }

    per_repo = {}
    total_tp = total_fp = total_fn = 0

    for entry in judge_input:
        iid = entry["instance_id"]
        pr_url = entry["pr_url"]
        repo = entry.get("source_repo", "unknown")
        n_goldens = entry["golden_count"]
        n_candidates = entry["candidate_count"]

        # For each golden, collect the n_judges votes
        per_pr = {
            "instance_id": iid,
            "source_repo": repo,
            "golden_count": n_goldens,
            "candidate_count": n_candidates,
            "judgments": {},
            "missing_judges": [],
        }

        candidate_matched = [False] * n_candidates
        tp_for_pr = []
        fn_for_pr = []

        for gi in range(1, n_goldens + 1):
            verdicts = []
            cand_indices = []
            reasonings = []
            for ji, run in enumerate(judge_runs):
                pr_judgments = run.get(iid)
                if pr_judgments is None:
                    if ji + 1 not in per_pr["missing_judges"]:
                        per_pr["missing_judges"].append(ji + 1)
                    continue
                j = pr_judgments.get(gi)
                if j is None:
                    continue
                verdicts.append(bool(j.get("match", False)))
                ci = j.get("matched_candidate_index")
                if ci is not None:
                    cand_indices.append(int(ci))
                if j.get("reasoning"):
                    reasonings.append(j["reasoning"])

            if not verdicts:
                per_pr["judgments"][str(gi)] = {
                    "match": False,
                    "candidate_index": None,
                    "votes": "0/0",
                    "reason": "no judges evaluated",
                }
                fn_for_pr.append(gi)
                continue

            match_count = sum(verdicts)
            consensus = match_count > len(verdicts) / 2

            if consensus and cand_indices:
                # Pick most-voted candidate index, fall back to first
                ci_counter = Counter(cand_indices)
                best_ci = ci_counter.most_common(1)[0][0]
                per_pr["judgments"][str(gi)] = {
                    "match": True,
                    "candidate_index": best_ci,
                    "votes": f"{match_count}/{len(verdicts)}",
                    "candidate_index_votes": dict(ci_counter),
                    "reasoning": reasonings[0] if reasonings else "",
                }
                if 1 <= best_ci <= n_candidates:
                    candidate_matched[best_ci - 1] = True
                tp_for_pr.append(gi)
            else:
                per_pr["judgments"][str(gi)] = {
                    "match": False,
                    "candidate_index": None,
                    "votes": f"{match_count}/{len(verdicts)}",
                    "reasoning": reasonings[0] if reasonings else "",
                }
                fn_for_pr.append(gi)

        false_positives = [
            {"candidate_index": ci + 1}
            for ci, m in enumerate(candidate_matched) if not m
        ]
        per_pr["tp"] = len(tp_for_pr)
        per_pr["fp"] = len(false_positives)
        per_pr["fn"] = len(fn_for_pr)
        per_pr["false_positives"] = false_positives

        out[pr_url] = per_pr
        total_tp += per_pr["tp"]
        total_fp += per_pr["fp"]
        total_fn += per_pr["fn"]

        # Per-repo aggregation
        repo_stats = per_repo.setdefault(repo, {"tp": 0, "fp": 0, "fn": 0, "prs": 0})
        repo_stats["tp"] += per_pr["tp"]
        repo_stats["fp"] += per_pr["fp"]
        repo_stats["fn"] += per_pr["fn"]
        repo_stats["prs"] += 1

    def metrics(tp, fp, fn):
        p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
        return round(p, 4), round(r, 4), round(f1, 4)

    for repo, stats in per_repo.items():
        p, r, f1 = metrics(stats["tp"], stats["fp"], stats["fn"])
        stats["precision"] = p
        stats["recall"] = r
        stats["f1"] = f1

    p, r, f1 = metrics(total_tp, total_fp, total_fn)
    out["_summary"] = {
        "evaluated_prs": len(judge_input),
        "tp": total_tp,
        "fp": total_fp,
        "fn": total_fn,
        "precision": p,
        "recall": r,
        "f1": f1,
        "avg_findings_per_pr": round(sum(e["candidate_count"] for e in judge_input) / len(judge_input), 2),
    }
    out["_per_repo"] = per_repo

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print(f"\n{'=' * 60}")
    print(f"Consensus results: {args.tool}")
    print(f"  PRs evaluated:   {len(judge_input)}")
    print(f"  TP={total_tp}  FP={total_fp}  FN={total_fn}")
    print(f"  P={p:.1%}  R={r:.1%}  F1={f1:.1%}")
    print(f"  Avg findings/PR: {out['_summary']['avg_findings_per_pr']}")
    print(f"\nPer-repo:")
    for repo, stats in sorted(per_repo.items()):
        print(f"  {repo:20s}  P={stats['precision']:.1%}  R={stats['recall']:.1%}  F1={stats['f1']:.1%}  ({stats['tp']} TP, {stats['fp']} FP, {stats['fn']} FN)")
    print(f"\nWrote: {args.output}")


if __name__ == "__main__":
    main()
