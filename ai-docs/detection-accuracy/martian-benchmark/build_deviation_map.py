#!/usr/bin/env python3
"""
Build a deviation map from Martian benchmark results.

Cross-references manifest.json (golden comments), judge_manual.json (matches),
and review/*.md (Firebreak findings) to produce a structured deviation map
with automated pre-classification of every TP, FP, and FN.

Usage:
  python3 build_deviation_map.py [--output-json deviation_map.json] [--output-md deviation_map.md]
"""

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
MANIFEST_PATH = SCRIPT_DIR / "manifest.json"
JUDGE_PATH = SCRIPT_DIR / "results" / "judge_consensus.json"
REVIEWS_DIR = SCRIPT_DIR / "reviews"

# Golden severity → numeric for sorting/aggregation
GOLDEN_SEV_ORDER = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}
# Firebreak severity → numeric
FBK_SEV_ORDER = {"info": 0, "minor": 1, "major": 2, "critical": 3}


def parse_summary_table(text: str) -> list[dict]:
    """
    Parse the Findings Summary table from a review markdown file.

    Handles column variations where F-NN can appear in ANY column:
      | ID | Type | Severity | Description |
      | pattern | F-01 | Description |  (type/severity in other columns)

    Returns list of {id, type, severity, description}.
    """
    findings = []

    type_values = {"behavioral", "structural", "test-integrity", "fragile"}
    sev_values = {"critical", "major", "minor", "info"}

    # Find all markdown table rows containing F-NN anywhere
    for match in re.finditer(
        r'^\|(.+F-\d+.+)$', text, re.MULTILINE
    ):
        row = match.group(1)
        cells = [c.strip() for c in row.split("|")]
        cells = [c for c in cells if c]

        # Extract finding ID from whichever cell contains it
        finding_id = None
        finding_type = None
        severity = None
        remaining = []

        for cell in cells:
            cell_stripped = cell.strip()
            cell_lower = cell_stripped.lower()

            # Check for finding ID
            id_match = re.match(r'^(F-\d+)$', cell_stripped)
            if id_match and finding_id is None:
                finding_id = id_match.group(1)
                continue

            if cell_lower in type_values and finding_type is None:
                finding_type = cell_lower
            elif cell_lower in sev_values and severity is None:
                severity = cell_lower
            else:
                remaining.append(cell_stripped)

        if not finding_id:
            continue

        # Description is typically the longest remaining cell
        description = max(remaining, key=len) if remaining else ""

        if finding_type and severity:
            findings.append({
                "id": finding_id,
                "type": finding_type,
                "severity": severity,
                "description": description,
            })

    # Deduplicate: some reviews have the table printed twice (e.g., after retrospective)
    seen = set()
    unique = []
    for f in findings:
        if f["id"] not in seen:
            seen.add(f["id"])
            unique.append(f)
    return unique


def parse_review(review_path: Path) -> list[dict]:
    """Parse a review file and return its findings."""
    if not review_path.exists():
        return []
    text = review_path.read_text()

    # Try summary table first
    findings = parse_summary_table(text)
    if findings:
        return findings

    # Fallback: parse finding headers + nearby metadata
    # Formats:
    #   ### F-01 (S-01) | behavioral | major | pattern-label
    #   ### F-01 (behavioral, major) — Title
    #   ### F-01 (S-01) — Title  (type/severity in body below)
    #   ### F-01 — Title  (type/severity in body below)
    #   ### F-01: Title
    type_values = {"behavioral", "structural", "test-integrity", "fragile"}
    sev_values = {"critical", "major", "minor", "info"}

    findings = []
    header_pattern = re.compile(
        r'^#{2,4}\s+(F-\d+)\b.*$', re.MULTILINE
    )

    for match in header_pattern.finditer(text):
        finding_id = match.group(1)
        header_line = match.group(0)

        # Look at the header line + next ~10 lines for type/severity
        start = match.end()
        # Find end: next finding header or section header or 500 chars
        next_header = header_pattern.search(text, start)
        next_section = re.search(r'^#{1,3}\s+[^F]', text[start:], re.MULTILINE)
        end = min(
            next_header.start() if next_header else len(text),
            start + (next_section.start() if next_section else 500),
            start + 500,
        )
        block = header_line + "\n" + text[start:end]

        finding_type = None
        severity = None

        # Try inline in header: "(behavioral, major)" or "| behavioral | major"
        for val in type_values:
            if val in block[:500].lower():
                finding_type = val
                break
        for val in sev_values:
            if val in block[:500].lower():
                severity = val
                break

        # Extract description from header
        # Strip: ### F-NN, optional (S-NN), optional (type, severity), separator
        desc = re.sub(r'^#{2,4}\s+F-\d+\b', '', header_line).strip()
        # Strip parenthetical groups like (S-01), (critical, behavioral), (behavioral, major)
        desc = re.sub(r'\([^)]*\)', '', desc).strip()
        # Strip leading separators: —, :, |, -
        desc = re.sub(r'^[\u2014:\|—\-\s]+', '', desc).strip()

        if finding_type and severity:
            findings.append({
                "id": finding_id,
                "type": finding_type,
                "severity": severity,
                "description": desc,
            })

    # Deduplicate
    seen = set()
    unique = []
    for f in findings:
        if f["id"] not in seen:
            seen.add(f["id"])
            unique.append(f)
    return unique


def classify_golden_comment(comment_text: str) -> str:
    """
    Classify a golden comment into a category based on its content.

    Categories ordered from specific to general:
    - security: SSRF, XSS, injection, auth bypass
    - race-condition: concurrency, race, thread-safety, atomic
    - null-safety: null/nil/None dereference, missing existence check
    - type-error: type mismatch, wrong parameter type, schema error, signature mismatch
    - resource-leak: context leak, unclosed resource, orphaned data, incomplete cleanup
    - data-integrity: data loss, corruption, stale data, normalization, migration
    - api-misuse: wrong API call, incorrect method, missing parameter, breaking change
    - error-handling: missing try-catch, unhandled error, error propagation
    - observability: logging, metrics, tracing issues
    - test-quality: test issue, flaky test, missing assertion
    - naming: typo, misspelling, inconsistent naming
    - style: dead code, magic numbers, redundant code, documentation mismatch
    - logic-error: incorrect logic, wrong condition, inverted check (broad catch-all)
    """
    text = comment_text.lower()

    # Security
    if any(w in text for w in ["ssrf", "xss", "injection", "clickjack", "x-frame",
                                "sanitiz", "vulnerability", "attack", "bypass"]):
        return "security"

    # Race condition / concurrency
    if any(w in text for w in ["race condition", "concurrent", "thread-safe",
                                "thread safety", "double-check", "atomic",
                                "mutex", "lock", "synchroniz"]):
        return "race-condition"

    # Null safety
    if any(w in text for w in ["null", "nil", "none", "nullpointer", "nosuchelement",
                                "attributeerror", "nomethoderror", "undefined",
                                "missing check", "without checking"]):
        return "null-safety"

    # Type errors
    if any(w in text for w in ["typeerror", "type mismatch", "wrong type",
                                "zod schema", "signature", "not a subclass",
                                "isinstance", "won't compile"]):
        return "type-error"

    # Resource / context leaks
    if any(w in text for w in ["context leak", "orphan", "fire-and-forget",
                                "unawaited", "promise rejection",
                                "skip terminating", "incomplete cleanup",
                                "leaving them running"]):
        return "resource-leak"

    # Data integrity
    if any(w in text for w in ["stale", "data loss", "corrupt",
                                "diverge", "normali", "case-sensitive",
                                "case-insensitive", "migration"]):
        return "data-integrity"

    # API misuse
    if any(w in text for w in ["wrong parameter", "incorrect method",
                                "wrong key", "wrong provider", "wrong alias",
                                "mismatch", "breaks.*contract", "interface contract",
                                "missing required", "missing the required",
                                "without.*parameter", "called without",
                                "breaking change", "not supported",
                                "does not support", "depends on",
                                "won't match", "key prop"]):
        return "api-misuse"

    # Error handling
    if any(w in text for w in ["try-catch", "try/catch", "error handling",
                                "unhandled", "gracefully", "error propagat"]):
        return "error-handling"

    # Observability
    if any(w in text for w in ["metric", "log level", "tracing", "traceid",
                                "recorder", "observability"]):
        return "observability"

    # Test quality
    if any(w in text for w in ["test ", "flaky", "assertion", "mock", "fixture"]):
        return "test-quality"

    # Naming / typo
    if any(w in text for w in ["typo", "misspell", "rename", "naming"]):
        return "naming"

    # Style / documentation
    if any(w in text for w in ["dead code", "magic number", "hardcod",
                                "unused", "unnecessary", "redundant",
                                "docstring", "javadoc", "consider"]):
        return "style"

    # Logic error (broad catch-all for behavioral issues)
    if any(w in text for w in ["logic", "incorrect", "wrong", "invert",
                                "unreachable", "always return", "always fail",
                                "silently", "instead of", "falsy", "misleading",
                                "exclude", "fail to"]):
        return "logic-error"

    return "other"


def build_deviation_map(manifest, judge_data, reviews_dir):
    """
    Build the full deviation map across all PRs.

    Returns a list of per-PR deviation records.
    """
    judge_metadata = judge_data.pop("_metadata", {})
    deviations = []

    for entry in manifest:
        instance_id = entry["instance_id"]
        pr_url = entry["pr_url"]
        source_repo = entry["source_repo"]
        golden_comments = entry["golden_comments"]

        # Get judge matches for this PR
        matches = judge_data.get(pr_url, {})

        # Parse Firebreak review
        review_path = reviews_dir / f"{instance_id}.md"
        # Try alternate naming with fbk-cr- prefix
        if not review_path.exists():
            review_path = reviews_dir / f"fbk-cr-{instance_id}.md"
        findings = parse_review(review_path)

        # Build finding index (1-based, matching judge_manual.json convention)
        finding_by_idx = {i + 1: f for i, f in enumerate(findings)}
        total_findings = len(findings)

        # Track which findings are matched (true positives)
        matched_finding_indices = set()
        true_positives = []
        false_negatives = []

        for golden_idx_str, finding_match in matches.items():
            golden_idx = int(golden_idx_str)
            golden = golden_comments[golden_idx - 1] if golden_idx <= len(golden_comments) else None
            if not golden:
                continue

            golden_category = classify_golden_comment(golden["comment"])

            if finding_match is not None:
                # Handle lists (multiple findings matching one golden)
                if isinstance(finding_match, list):
                    match_indices = finding_match
                else:
                    match_indices = [finding_match]

                for midx in match_indices:
                    matched_finding_indices.add(midx)

                matched_finding = finding_by_idx.get(match_indices[0])
                true_positives.append({
                    "golden_index": golden_idx,
                    "golden_comment": golden["comment"],
                    "golden_severity": golden["severity"],
                    "golden_category": golden_category,
                    "finding_indices": match_indices,
                    "finding_id": matched_finding["id"] if matched_finding else f"F-{match_indices[0]:02d}",
                    "finding_type": matched_finding["type"] if matched_finding else "unknown",
                    "finding_severity": matched_finding["severity"] if matched_finding else "unknown",
                    "finding_description": matched_finding["description"] if matched_finding else "",
                })
            else:
                false_negatives.append({
                    "golden_index": golden_idx,
                    "golden_comment": golden["comment"],
                    "golden_severity": golden["severity"],
                    "golden_category": golden_category,
                })

        # False positives: findings not matched to any golden comment
        false_positives = []
        for idx, finding in finding_by_idx.items():
            if idx not in matched_finding_indices:
                false_positives.append({
                    "finding_index": idx,
                    "finding_id": finding["id"],
                    "finding_type": finding["type"],
                    "finding_severity": finding["severity"],
                    "finding_description": finding["description"],
                })

        # Compute metrics
        tp_count = len(true_positives)
        fp_count = len(false_positives)
        fn_count = len(false_negatives)
        precision = tp_count / (tp_count + fp_count) if (tp_count + fp_count) > 0 else 0.0
        recall = tp_count / (tp_count + fn_count) if (tp_count + fn_count) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        deviations.append({
            "instance_id": instance_id,
            "pr_url": pr_url,
            "source_repo": source_repo,
            "pr_title": entry.get("pr_title", ""),
            "golden_count": len(golden_comments),
            "finding_count": total_findings,
            "tp_count": tp_count,
            "fp_count": fp_count,
            "fn_count": fn_count,
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1, 3),
            "true_positives": true_positives,
            "false_positives": false_positives,
            "false_negatives": false_negatives,
        })

    return deviations, judge_metadata


def compute_aggregates(deviations):
    """Compute aggregate statistics from the deviation map."""
    total_tp = sum(d["tp_count"] for d in deviations)
    total_fp = sum(d["fp_count"] for d in deviations)
    total_fn = sum(d["fn_count"] for d in deviations)
    total_golden = sum(d["golden_count"] for d in deviations)
    total_findings = sum(d["finding_count"] for d in deviations)

    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    # FP breakdown by finding type
    fp_by_type = {}
    for d in deviations:
        for fp in d["false_positives"]:
            t = fp["finding_type"]
            fp_by_type[t] = fp_by_type.get(t, 0) + 1

    # FP breakdown by severity
    fp_by_severity = {}
    for d in deviations:
        for fp in d["false_positives"]:
            s = fp["finding_severity"]
            fp_by_severity[s] = fp_by_severity.get(s, 0) + 1

    # FN breakdown by golden severity
    fn_by_golden_severity = {}
    for d in deviations:
        for fn in d["false_negatives"]:
            s = fn["golden_severity"]
            fn_by_golden_severity[s] = fn_by_golden_severity.get(s, 0) + 1

    # FN breakdown by category
    fn_by_category = {}
    for d in deviations:
        for fn in d["false_negatives"]:
            c = fn["golden_category"]
            fn_by_category[c] = fn_by_category.get(c, 0) + 1

    # TP breakdown by golden severity
    tp_by_golden_severity = {}
    for d in deviations:
        for tp in d["true_positives"]:
            s = tp["golden_severity"]
            tp_by_golden_severity[s] = tp_by_golden_severity.get(s, 0) + 1

    # Per-repo aggregates
    repo_stats = {}
    for d in deviations:
        repo = d["source_repo"]
        if repo not in repo_stats:
            repo_stats[repo] = {"tp": 0, "fp": 0, "fn": 0, "golden": 0, "findings": 0, "prs": 0}
        repo_stats[repo]["tp"] += d["tp_count"]
        repo_stats[repo]["fp"] += d["fp_count"]
        repo_stats[repo]["fn"] += d["fn_count"]
        repo_stats[repo]["golden"] += d["golden_count"]
        repo_stats[repo]["findings"] += d["finding_count"]
        repo_stats[repo]["prs"] += 1

    for repo, stats in repo_stats.items():
        tp, fp, fn = stats["tp"], stats["fp"], stats["fn"]
        stats["precision"] = round(tp / (tp + fp), 3) if (tp + fp) > 0 else 0.0
        stats["recall"] = round(tp / (tp + fn), 3) if (tp + fn) > 0 else 0.0
        p, r = stats["precision"], stats["recall"]
        stats["f1"] = round(2 * p * r / (p + r), 3) if (p + r) > 0 else 0.0

    # Severity-stratified recall
    recall_by_severity = {}
    for sev in ["Low", "Medium", "High", "Critical"]:
        tp_sev = tp_by_golden_severity.get(sev, 0)
        fn_sev = fn_by_golden_severity.get(sev, 0)
        total_sev = tp_sev + fn_sev
        recall_by_severity[sev] = round(tp_sev / total_sev, 3) if total_sev > 0 else 0.0

    return {
        "total_prs": len(deviations),
        "total_golden": total_golden,
        "total_findings": total_findings,
        "total_tp": total_tp,
        "total_fp": total_fp,
        "total_fn": total_fn,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "fp_by_type": dict(sorted(fp_by_type.items(), key=lambda x: -x[1])),
        "fp_by_severity": dict(sorted(fp_by_severity.items(), key=lambda x: -x[1])),
        "fn_by_golden_severity": dict(sorted(fn_by_golden_severity.items(),
                                             key=lambda x: -GOLDEN_SEV_ORDER.get(x[0], 0))),
        "fn_by_category": dict(sorted(fn_by_category.items(), key=lambda x: -x[1])),
        "tp_by_golden_severity": tp_by_golden_severity,
        "recall_by_severity": recall_by_severity,
        "repo_stats": repo_stats,
    }


def render_markdown(deviations, aggregates, metadata):
    """Render the deviation map as a markdown report."""
    lines = []
    lines.append("# Martian Benchmark Deviation Map")
    lines.append("")
    lines.append(f"**Firebreak version**: {metadata.get('firebreak_version', 'unknown')}")
    lines.append(f"**Judge**: {metadata.get('judge', 'unknown')}")
    lines.append(f"**Date**: {metadata.get('date', 'unknown')}")
    lines.append(f"**Threshold**: {metadata.get('threshold', 'unknown')}")
    lines.append("")

    # Aggregate summary
    a = aggregates
    lines.append("## Aggregate Summary")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| PRs evaluated | {a['total_prs']} |")
    lines.append(f"| Golden comments | {a['total_golden']} |")
    lines.append(f"| Firebreak findings | {a['total_findings']} |")
    lines.append(f"| True positives | {a['total_tp']} |")
    lines.append(f"| False positives | {a['total_fp']} |")
    lines.append(f"| False negatives | {a['total_fn']} |")
    lines.append(f"| **Precision** | **{a['precision']:.1%}** |")
    lines.append(f"| **Recall** | **{a['recall']:.1%}** |")
    lines.append(f"| **F1** | **{a['f1']:.1%}** |")
    lines.append("")

    # Recall by golden severity
    lines.append("## Recall by Golden Severity")
    lines.append("")
    lines.append("| Severity | TP | FN | Recall |")
    lines.append("|----------|----|----|--------|")
    for sev in ["Critical", "High", "Medium", "Low"]:
        tp = a["tp_by_golden_severity"].get(sev, 0)
        fn = a["fn_by_golden_severity"].get(sev, 0)
        total = tp + fn
        recall = a["recall_by_severity"].get(sev, 0)
        lines.append(f"| {sev} | {tp} | {fn} | {recall:.1%} |")
    lines.append("")

    # FP breakdown
    lines.append("## False Positive Breakdown")
    lines.append("")
    lines.append("### By Finding Type")
    lines.append("")
    lines.append("| Type | Count | % of FPs |")
    lines.append("|------|-------|----------|")
    for t, count in a["fp_by_type"].items():
        pct = count / a["total_fp"] * 100 if a["total_fp"] > 0 else 0
        lines.append(f"| {t} | {count} | {pct:.1f}% |")
    lines.append("")

    lines.append("### By Finding Severity")
    lines.append("")
    lines.append("| Severity | Count | % of FPs |")
    lines.append("|----------|-------|----------|")
    for s, count in a["fp_by_severity"].items():
        pct = count / a["total_fp"] * 100 if a["total_fp"] > 0 else 0
        lines.append(f"| {s} | {count} | {pct:.1f}% |")
    lines.append("")

    # FN breakdown
    lines.append("## False Negative Breakdown")
    lines.append("")
    lines.append("### By Golden Severity")
    lines.append("")
    lines.append("| Severity | Count | % of FNs |")
    lines.append("|----------|-------|----------|")
    for s, count in a["fn_by_golden_severity"].items():
        pct = count / a["total_fn"] * 100 if a["total_fn"] > 0 else 0
        lines.append(f"| {s} | {count} | {pct:.1f}% |")
    lines.append("")

    lines.append("### By Issue Category (auto-classified)")
    lines.append("")
    lines.append("| Category | Count | % of FNs |")
    lines.append("|----------|-------|----------|")
    for c, count in a["fn_by_category"].items():
        pct = count / a["total_fn"] * 100 if a["total_fn"] > 0 else 0
        lines.append(f"| {c} | {count} | {pct:.1f}% |")
    lines.append("")

    # Per-repo summary
    lines.append("## Per-Repo Summary")
    lines.append("")
    lines.append("| Repo | PRs | Golden | Findings | TP | FP | FN | P | R | F1 |")
    lines.append("|------|-----|--------|----------|----|----|----|---|---|---|")
    for repo, stats in sorted(a["repo_stats"].items()):
        lines.append(
            f"| {repo} | {stats['prs']} | {stats['golden']} | {stats['findings']} "
            f"| {stats['tp']} | {stats['fp']} | {stats['fn']} "
            f"| {stats['precision']:.1%} | {stats['recall']:.1%} | {stats['f1']:.1%} |"
        )
    lines.append("")

    # Per-PR detail
    lines.append("---")
    lines.append("")
    lines.append("## Per-PR Deviation Detail")
    lines.append("")

    for d in deviations:
        lines.append(f"### {d['instance_id']}")
        lines.append(f"**{d['pr_title']}** — [{d['pr_url']}]({d['pr_url']})")
        lines.append(f"Golden: {d['golden_count']} | Findings: {d['finding_count']} "
                     f"| TP: {d['tp_count']} | FP: {d['fp_count']} | FN: {d['fn_count']} "
                     f"| P={d['precision']:.0%} R={d['recall']:.0%} F1={d['f1']:.0%}")
        lines.append("")

        if d["true_positives"]:
            lines.append("**True Positives:**")
            for tp in d["true_positives"]:
                lines.append(
                    f"- G{tp['golden_index']} ({tp['golden_severity']}) → "
                    f"{tp['finding_id']} ({tp['finding_type']}/{tp['finding_severity']})"
                )
                lines.append(f"  Golden: {tp['golden_comment'][:120]}{'...' if len(tp['golden_comment']) > 120 else ''}")
                if tp["finding_description"]:
                    lines.append(f"  Finding: {tp['finding_description'][:120]}{'...' if len(tp['finding_description']) > 120 else ''}")
            lines.append("")

        if d["false_negatives"]:
            lines.append("**False Negatives (missed golden):**")
            for fn in d["false_negatives"]:
                lines.append(
                    f"- G{fn['golden_index']} ({fn['golden_severity']}) "
                    f"[{fn['golden_category']}]: "
                    f"{fn['golden_comment'][:150]}{'...' if len(fn['golden_comment']) > 150 else ''}"
                )
            lines.append("")

        if d["false_positives"]:
            lines.append("**False Positives (unmatched findings):**")
            for fp in d["false_positives"]:
                lines.append(
                    f"- {fp['finding_id']} ({fp['finding_type']}/{fp['finding_severity']}): "
                    f"{fp['finding_description'][:150]}{'...' if len(fp['finding_description']) > 150 else ''}"
                )
            lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Build deviation map from Martian benchmark results")
    parser.add_argument("--output-json", default=str(SCRIPT_DIR / "results" / "deviation_map.json"),
                       help="Output JSON path")
    parser.add_argument("--output-md", default=str(SCRIPT_DIR / "results" / "deviation_map.md"),
                       help="Output markdown path")
    args = parser.parse_args()

    # Load data
    if not MANIFEST_PATH.exists():
        print(f"Error: {MANIFEST_PATH} not found", file=sys.stderr)
        sys.exit(1)
    if not JUDGE_PATH.exists():
        print(f"Error: {JUDGE_PATH} not found", file=sys.stderr)
        sys.exit(1)

    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)
    with open(JUDGE_PATH) as f:
        judge_data = json.load(f)

    # Build deviation map
    deviations, metadata = build_deviation_map(manifest, judge_data, REVIEWS_DIR)
    aggregates = compute_aggregates(deviations)

    # Output JSON
    output = {
        "metadata": metadata,
        "aggregates": aggregates,
        "deviations": deviations,
    }
    json_path = Path(args.output_json)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"JSON: {json_path}")

    # Output markdown
    md_path = Path(args.output_md)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_text = render_markdown(deviations, aggregates, metadata)
    with open(md_path, "w") as f:
        f.write(md_text)
    print(f"Markdown: {md_path}")

    # Print summary
    a = aggregates
    print(f"\n=== Summary ===")
    print(f"PRs: {a['total_prs']} | Golden: {a['total_golden']} | Findings: {a['total_findings']}")
    print(f"TP: {a['total_tp']} | FP: {a['total_fp']} | FN: {a['total_fn']}")
    print(f"Precision: {a['precision']:.1%} | Recall: {a['recall']:.1%} | F1: {a['f1']:.1%}")
    print(f"\nRecall by severity:")
    for sev in ["Critical", "High", "Medium", "Low"]:
        print(f"  {sev}: {a['recall_by_severity'].get(sev, 0):.1%}")


if __name__ == "__main__":
    main()
