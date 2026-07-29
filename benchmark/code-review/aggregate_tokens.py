#!/usr/bin/env python3
"""Aggregate token logs from benchmark runs into summary CSV.

Reads JSONL files produced by run_reviews.sh and generates:
- A CSV summary with per-review token breakdowns
- Stdout: per-repo aggregation table and overall totals
"""

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path


def count_findings(reviews_dir: Path, instance_id: str) -> int:
    """Count ### F- headers in a review markdown file."""
    review_path = reviews_dir / f"{instance_id}.md"
    if not review_path.exists():
        return 0
    return len(re.findall(r"^### F-", review_path.read_text(), re.MULTILINE))


def flatten_model_usage(model_usage: dict) -> dict:
    """Flatten modelUsage into per-model columns."""
    flat = {}
    for model_key, usage in model_usage.items():
        # Shorten model name: claude-opus-4-6[1m] -> opus-4-6
        short = model_key.split("-", 1)[-1].split("[")[0] if "-" in model_key else model_key
        flat[f"{short}_input"] = usage.get("inputTokens", 0)
        flat[f"{short}_output"] = usage.get("outputTokens", 0)
        flat[f"{short}_cache_read"] = usage.get("cacheReadInputTokens", 0)
        flat[f"{short}_cache_create"] = usage.get("cacheCreationInputTokens", 0)
        flat[f"{short}_cost"] = usage.get("costUSD", 0)
    return flat


def fmt_tokens(n: int) -> str:
    """Format token count for display."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def main():
    parser = argparse.ArgumentParser(description="Aggregate benchmark token logs")
    parser.add_argument("token_log", type=Path, help="Path to JSONL token log")
    parser.add_argument("--output", type=Path, help="CSV output path (default: auto-generated)")
    parser.add_argument("--reviews-dir", type=Path, default=None,
                        help="Reviews directory for findings count (default: sibling of logs/)")
    args = parser.parse_args()

    if not args.token_log.exists():
        print(f"ERROR: {args.token_log} not found", file=sys.stderr)
        sys.exit(1)

    # Derive reviews directory from token log location
    if args.reviews_dir is None:
        args.reviews_dir = args.token_log.parent.parent / "reviews"

    # Default output path: same dir as token log, .csv extension
    if args.output is None:
        args.output = args.token_log.with_suffix(".csv")

    # Read JSONL entries
    entries = []
    for line in args.token_log.read_text().strip().split("\n"):
        if not line.strip():
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError as e:
            print(f"WARNING: skipping malformed line: {e}", file=sys.stderr)

    if not entries:
        print("No entries found in token log.", file=sys.stderr)
        sys.exit(1)

    # Collect all model keys for CSV headers
    all_model_keys = set()
    for entry in entries:
        model_usage = entry.get("modelUsage", {})
        for model_key in model_usage:
            short = model_key.split("-", 1)[-1].split("[")[0] if "-" in model_key else model_key
            all_model_keys.add(short)
    all_model_keys = sorted(all_model_keys)

    # Build CSV rows
    rows = []
    for entry in entries:
        instance_id = entry.get("instance_id", "unknown")
        source_repo = entry.get("source_repo", "unknown")
        status = entry.get("benchmark_status", "unknown")

        # Use findings_count from log if available, otherwise count from file
        findings = entry.get("findings_count")
        if findings is None:
            findings = count_findings(args.reviews_dir, instance_id)

        flat_models = flatten_model_usage(entry.get("modelUsage", {}))

        row = {
            "instance_id": instance_id,
            "source_repo": source_repo,
            "status": status,
            "duration_ms": entry.get("duration_ms", 0),
            "num_turns": entry.get("num_turns", 0),
            "total_cost_usd": entry.get("total_cost_usd", 0),
            "findings_count": findings,
        }

        # Add per-model columns
        for model_key in all_model_keys:
            for suffix in ["input", "output", "cache_read", "cache_create", "cost"]:
                col = f"{model_key}_{suffix}"
                row[col] = flat_models.get(col, 0)

        rows.append(row)

    # Write CSV
    if rows:
        fieldnames = list(rows[0].keys())
        with open(args.output, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"CSV written to: {args.output}")

    # Print summary to stdout
    ok_rows = [r for r in rows if r["status"] == "ok"]
    failed_rows = [r for r in rows if r["status"] != "ok"]

    print("")
    print("=" * 70)
    print("  Benchmark Token Summary")
    print("=" * 70)
    print(f"  Reviews:    {len(ok_rows)} ok, {len(failed_rows)} failed")

    if ok_rows:
        total_cost = sum(r["total_cost_usd"] for r in ok_rows)
        total_findings = sum(r["findings_count"] for r in ok_rows)
        total_duration = sum(r["duration_ms"] for r in ok_rows) / 1000
        avg_cost = total_cost / len(ok_rows)
        avg_findings = total_findings / len(ok_rows)

        print(f"  Total cost: ${total_cost:.2f}  (avg ${avg_cost:.2f}/review)")
        print(f"  Findings:   {total_findings}  (avg {avg_findings:.1f}/review)")
        print(f"  Duration:   {total_duration:.0f}s  ({total_duration/60:.1f}m)")

        if total_findings > 0:
            print(f"  Cost/finding: ${total_cost / total_findings:.2f}")

    # Per-repo breakdown
    print("")
    print(f"  {'Repo':<15} {'Reviews':>7} {'Findings':>8} {'Cost':>10} {'Avg Cost':>10}")
    print(f"  {'-'*15} {'-'*7} {'-'*8} {'-'*10} {'-'*10}")

    by_repo = defaultdict(list)
    for r in ok_rows:
        by_repo[r["source_repo"]].append(r)

    for repo in sorted(by_repo.keys()):
        repo_rows = by_repo[repo]
        repo_cost = sum(r["total_cost_usd"] for r in repo_rows)
        repo_findings = sum(r["findings_count"] for r in repo_rows)
        repo_avg = repo_cost / len(repo_rows) if repo_rows else 0
        print(f"  {repo:<15} {len(repo_rows):>7} {repo_findings:>8} ${repo_cost:>9.2f} ${repo_avg:>9.2f}")

    # Per-model token breakdown
    if all_model_keys and ok_rows:
        print("")
        print(f"  {'Model':<15} {'Input':>10} {'Output':>10} {'Cache-R':>10} {'Cache-W':>10} {'Cost':>10}")
        print(f"  {'-'*15} {'-'*10} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")

        for model_key in all_model_keys:
            m_input = sum(r.get(f"{model_key}_input", 0) for r in ok_rows)
            m_output = sum(r.get(f"{model_key}_output", 0) for r in ok_rows)
            m_cache_r = sum(r.get(f"{model_key}_cache_read", 0) for r in ok_rows)
            m_cache_w = sum(r.get(f"{model_key}_cache_create", 0) for r in ok_rows)
            m_cost = sum(r.get(f"{model_key}_cost", 0) for r in ok_rows)
            print(f"  {model_key:<15} {fmt_tokens(m_input):>10} {fmt_tokens(m_output):>10} "
                  f"{fmt_tokens(m_cache_r):>10} {fmt_tokens(m_cache_w):>10} ${m_cost:>9.2f}")

    print("")
    print("=" * 70)


if __name__ == "__main__":
    main()
