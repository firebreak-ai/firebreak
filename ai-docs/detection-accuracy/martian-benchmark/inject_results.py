#!/usr/bin/env python3
"""
Inject Firebreak review results into the Martian benchmark format.

Reads Firebreak review output files from reviews/, converts verified findings
to the benchmark's review_comments format, and injects them into benchmark_data.json.

Usage:
  python3 inject_results.py [--tool-name firebreak]
"""

import argparse
import json
import re
import sys
from pathlib import Path

BENCHMARK_DATA = Path("/tmp/code-review-benchmark/offline/results/benchmark_data.json")
REVIEWS_DIR = Path(__file__).parent / "reviews"
MANIFEST_PATH = Path(__file__).parent / "manifest.json"


def _is_metadata_line(line: str, fields: list[str]) -> bool:
    """
    Check if a line is a metadata-only line (should be stripped from body).

    Handles both single-field lines and pipe-delimited combined lines:
      - **Location**: `src/foo.ts:42`
      - **Round**: 1 | **Type**: behavioral | **Severity**: major
    """
    if not line.startswith("- **"):
        return False
    # Split on pipe delimiter and check each segment
    segments = [s.strip().lstrip("- ") for s in line.split("|")]
    return all(
        any(seg.startswith(f"**{field}**") for field in fields)
        for seg in segments
        if seg  # skip empty segments
    )


def parse_firebreak_review(review_path: Path) -> list[dict]:
    """
    Parse a Firebreak review markdown file into review_comments.

    Expects findings in the standard Firebreak format:
      ### F-NN: <title>
      - **Location**: path/to/file.py:NN-NN
      - **Type**: behavioral | structural | test-integrity | fragile
      - **Severity**: critical | major | minor | info
      ...
      **Current behavior**: ...
      **Expected behavior**: ...
      **Evidence**: ...

    Returns list of {"path": str|None, "line": int|None, "body": str, "severity": str|None}.
    """
    text = review_path.read_text()
    comments = []

    # Split on finding headers — multiple format variants:
    #   ### F-01 — Title (behavioral, major)
    #   ### F-01: Title
    #   #### F-01 — Title
    #   **F-01** | critical | behavioral | `path`
    finding_pattern = re.compile(
        r'^(?:#{2,4}\s+F-\d+[\s:\u2014(]|\*\*F-\d+\*\*\s*\|)',
        re.MULTILINE,
    )
    splits = list(finding_pattern.finditer(text))

    for i, match in enumerate(splits):
        start = match.start()
        end = splits[i + 1].start() if i + 1 < len(splits) else len(text)
        finding_text = text[start:end].strip()
        header_line = finding_text.split("\n")[0]

        # Extract severity — try formats in order of specificity:
        severity = None
        sev_re = r'(critical|major|minor|info)'

        # 1. "(type, severity)" in header: "### F-01 — Title (behavioral, major)"
        m = re.search(r'\((?:behavioral|structural|test-integrity|fragile),\s*' + sev_re + r'\)', header_line, re.I)
        if m:
            severity = m.group(1).lower()

        # 2. "(severity, type)" in header: "### F-01 (S-01) — critical, behavioral"
        if not severity:
            m = re.search(sev_re + r',\s*(?:behavioral|structural|test-integrity|fragile)', header_line, re.I)
            if m:
                severity = m.group(1).lower()

        # 3. "(Severity)" alone in header: "### F-01 (Critical) — Title"
        if not severity:
            m = re.search(r'\(' + sev_re + r'\)', header_line, re.I)
            if m:
                severity = m.group(1).lower()

        # 4. "severity / type" or "type / severity" in first 300 chars of body
        if not severity:
            m = re.search(sev_re + r'\s*/\s*(?:behavioral|structural|test-integrity|fragile)', finding_text[:300], re.I)
            if m:
                severity = m.group(1).lower()
        if not severity:
            m = re.search(r'(?:behavioral|structural|test-integrity|fragile)\s*/\s*' + sev_re, finding_text[:300], re.I)
            if m:
                severity = m.group(1).lower()

        # 5. Pipe-delimited header: "**F-01** | critical | behavioral | `path`"
        if not severity:
            m = re.search(r'\*\*F-\d+\*\*\s*\|\s*' + sev_re + r'\s*\|', header_line, re.I)
            if m:
                severity = m.group(1).lower()

        # 6. "| severity | type |" in pipe-delimited body lines (no bold)
        if not severity:
            m = re.search(r'\|\s*' + sev_re + r'\s*\|\s*(?:behavioral|structural|test-integrity|fragile)', finding_text[:500], re.I)
            if m:
                severity = m.group(1).lower()

        # 7. "**Severity**: major" or "- **Severity**: major" (list item)
        if not severity:
            m = re.search(r'\*\*Severity\*\*:?\s*' + sev_re, finding_text, re.I)
            if m:
                severity = m.group(1).lower()

        # 8. "| **Severity** | major |" (table row)
        if not severity:
            m = re.search(r'\*\*Severity\*\*\s*\|\s*' + sev_re, finding_text, re.I)
            if m:
                severity = m.group(1).lower()

        # 9. "| Field | Value |" table with severity in value column
        if not severity:
            m = re.search(r'\|\s*(?:\*\*)?Severity(?:\*\*)?\s*\|\s*(?:\*\*)?' + sev_re, finding_text[:500], re.I)
            if m:
                severity = m.group(1).lower()

        # 10. Sighting-format body line: "S-01) | behavioral | major | introduced"
        #     or "| major | behavioral |" bare pipe in first few lines
        if not severity:
            m = re.search(r'\|\s*(?:behavioral|structural|test-integrity|fragile)\s*\|\s*' + sev_re, finding_text[:300], re.I)
            if m:
                severity = m.group(1).lower()
        if not severity:
            m = re.search(r'\|\s*' + sev_re + r'\s*\|\s*(?:introduced|pre-existing)', finding_text[:300], re.I)
            if m:
                severity = m.group(1).lower()

        # 11. Bold-pipe variant: "**Type:** structural | **Severity:** minor"
        if not severity:
            m = re.search(r'\*\*Severity:?\*\*:?\s*' + sev_re, finding_text[:500], re.I)
            if m:
                severity = m.group(1).lower()

        # Extract file path and line from Location field or pipe-delimited header
        path = None
        line = None
        # Try "**Location**: `path`" first
        loc_match = re.search(
            r'\*\*Location\*\*:\s*`([^`]+)`',
            finding_text,
        )
        # Try pipe-delimited header: "**F-01** | sev | type | `path:lines`"
        if not loc_match:
            loc_match = re.search(
                r'\*\*F-\d+\*\*(?:\s*\|[^|]*){2}\|\s*`([^`]+)`',
                header_line,
            )
        # Try table row: "| **Location** | `path` |"
        if not loc_match:
            loc_match = re.search(
                r'\*\*Location\*\*\s*\|\s*`([^`]+)`',
                finding_text,
            )
        if loc_match:
            loc = loc_match.group(1).strip()
            # Parse "path/to/file.py:42-50" or "path/to/file.py:42"
            # Also handle "file.ts, description" (comma-separated location + context)
            loc = loc.split(",")[0].strip()
            loc_parts = loc.split(":")
            path = loc_parts[0]
            if len(loc_parts) > 1:
                line_str = loc_parts[1].split("-")[0]
                try:
                    line = int(line_str)
                except ValueError:
                    pass

        # Build comment body from the finding
        # Strip header, metadata fields, and structural markers
        # Keep substantive content (Observation/Current behavior, Expected, Evidence)
        metadata_fields = [
            "Location", "Type", "Severity", "Origin", "Detection source",
            "Pattern label", "Round", "Sighting", "Source of truth",
        ]
        body_lines = []
        for body_line in finding_text.split("\n"):
            stripped = body_line.strip()
            # Skip finding headers — extract title instead
            if re.match(r'^#{2,4}\s+F-\d+', body_line):
                # Extract title, stripping "F-NN — " or "F-NN: " prefix and trailing "(type, sev)"
                title = re.sub(r'^#{2,4}\s+F-\d+[\s:\u2014(]+', '', body_line).strip()
                title = re.sub(r'\s*\([^)]*\)\s*$', '', title).strip()
                if title:
                    body_lines.append(title)
            # Skip pipe-delimited header: "**F-01** | critical | behavioral | `path`"
            elif re.match(r'\*\*F-\d+\*\*\s*\|', stripped):
                continue
            # Skip bold title line immediately after pipe header (e.g., "**Title text**")
            elif re.match(r'^\*\*[^*]+\*\*$', stripped) and not body_lines:
                body_lines.append(re.sub(r'\*\*', '', stripped))
            # Skip metadata lines (both "- **Field**:" list and "**Field**:" plain)
            elif _is_metadata_line(stripped, metadata_fields):
                continue
            elif any(stripped.startswith(f"**{field}**:") for field in metadata_fields):
                continue
            # Skip "Pattern: `label`" lines
            elif re.match(r'^Pattern:\s*`', stripped):
                continue
            else:
                body_lines.append(body_line)

        body = "\n".join(body_lines).strip()
        if body:
            comments.append({"path": path, "line": line, "body": body, "severity": severity})

    return comments


def parse_findings_flat(review_path: Path) -> list[dict]:
    """
    Fallback parser: extract any structured findings regardless of format.

    Looks for patterns like "**Finding**:" or "**F-NN**:" or numbered findings.
    """
    text = review_path.read_text()
    comments = []

    # If the file has a findings summary table, extract from that
    # Otherwise, treat the whole file as one comment
    if len(text.strip()) > 0:
        comments.append({"path": None, "line": None, "body": text})

    return comments


def match_pr_to_benchmark(manifest_entry: dict, benchmark_data: dict) -> str | None:
    """Find the matching PR URL key in benchmark_data for a manifest entry."""
    pr_url = manifest_entry["pr_url"]
    if pr_url in benchmark_data:
        return pr_url

    # Try matching by PR number and repo
    owner = manifest_entry["owner"]
    repo = manifest_entry["repo"]
    pr_number = manifest_entry["pr_number"]

    for key in benchmark_data:
        if f"/{owner}/{repo}/pull/{pr_number}" in key:
            return key
        # Also check original_url
        entry = benchmark_data[key]
        orig = entry.get("original_url") or ""
        if f"/{owner}/{repo}/pull/{pr_number}" in orig:
            return key

    return None


SEVERITY_ORDER = ["info", "minor", "major", "critical"]


def main():
    parser = argparse.ArgumentParser(description="Inject Firebreak results into benchmark format")
    parser.add_argument("--tool-name", default="firebreak", help="Tool name in benchmark (default: firebreak)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be injected without modifying")
    parser.add_argument(
        "--min-severity", default="minor",
        choices=SEVERITY_ORDER,
        help="Minimum severity to include (default: minor, excludes info)",
    )
    args = parser.parse_args()
    min_sev_idx = SEVERITY_ORDER.index(args.min_severity)

    if not MANIFEST_PATH.exists():
        print(f"Error: {MANIFEST_PATH} not found. Run fetch_pr_diffs.py first.")
        sys.exit(1)

    if not BENCHMARK_DATA.exists():
        print(f"Error: {BENCHMARK_DATA} not found.")
        sys.exit(1)

    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)

    with open(BENCHMARK_DATA) as f:
        benchmark = json.load(f)

    if not REVIEWS_DIR.exists():
        print(f"Error: {REVIEWS_DIR} not found. Run Firebreak reviews first.")
        sys.exit(1)

    injected = 0
    skipped = 0
    missing = 0

    for entry in manifest:
        instance_id = entry["instance_id"]
        review_path = REVIEWS_DIR / f"{instance_id}.md"

        if not review_path.exists():
            missing += 1
            continue

        # Parse Firebreak review output
        all_comments = parse_firebreak_review(review_path)
        if not all_comments:
            all_comments = parse_findings_flat(review_path)

        # Apply severity filter (exclude info-level by default)
        comments = []
        filtered_count = 0
        for c in all_comments:
            sev = c.get("severity")
            if sev and sev in SEVERITY_ORDER:
                if SEVERITY_ORDER.index(sev) < min_sev_idx:
                    filtered_count += 1
                    continue
            # Include findings with unknown severity (conservative)
            comments.append(c)

        # Find matching PR in benchmark data
        benchmark_key = match_pr_to_benchmark(entry, benchmark)
        if not benchmark_key:
            print(f"  WARN: No benchmark match for {entry['pr_url']}")
            skipped += 1
            continue

        # Check if tool already exists
        existing_tools = [r["tool"] for r in benchmark[benchmark_key].get("reviews", [])]
        if args.tool_name in existing_tools:
            print(f"  SKIP: {args.tool_name} already exists for {benchmark_key}")
            skipped += 1
            continue

        review_entry = {
            "tool": args.tool_name,
            "repo_name": f"{entry['owner']}__{entry['repo']}__{args.tool_name}__PR{entry['pr_number']}",
            "pr_url": entry["pr_url"],
            "review_comments": comments,
        }

        if args.dry_run:
            filtered_msg = f", {filtered_count} below {args.min_severity}" if filtered_count else ""
            print(f"  WOULD INJECT: {instance_id} ({len(comments)} comments{filtered_msg})")
        else:
            benchmark[benchmark_key]["reviews"].append(review_entry)
            injected += 1

    if not args.dry_run and injected > 0:
        with open(BENCHMARK_DATA, "w") as f:
            json.dump(benchmark, f, indent=2)

    print(f"\nDone: {injected} injected, {skipped} skipped, {missing} reviews not found")
    if missing:
        print(f"  Run Firebreak reviews for the {missing} missing PRs in {REVIEWS_DIR}/")


if __name__ == "__main__":
    main()
