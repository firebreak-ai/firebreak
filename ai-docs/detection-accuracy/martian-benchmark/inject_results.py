import json
import sys
import argparse
import pathlib

SEVERITY_ORDER = {"info": 0, "minor": 1, "major": 2, "critical": 3}
MANIFEST_PATH = pathlib.Path(__file__).parent / "manifest.json"
BENCHMARK_DATA = pathlib.Path("/tmp/code-review-benchmark/offline/results/benchmark_data.json")

VERIFIED_STATUSES = {"verified", "verified-pending-execution"}


def convert_finding(finding):
    mechanism = finding.get("mechanism", "")
    consequence = finding.get("consequence", "")
    body = f"{mechanism} {consequence}".strip()

    return {
        "path": finding["location"]["file"],
        "line": finding["location"].get("start_line", 0),
        "body": body,
        "severity": finding.get("severity", "unknown"),
        "type": finding.get("type", "unknown"),
        "origin": finding.get("origin", "unknown"),
        "reclassified_from": finding.get("reclassified_from", {}),
    }


def filter_by_severity(findings, min_severity):
    threshold = SEVERITY_ORDER.get(min_severity, 0)
    return [f for f in findings if SEVERITY_ORDER.get(f.get("severity", "info"), 0) >= threshold]


def load_manifest():
    if not MANIFEST_PATH.exists():
        return []
    with open(MANIFEST_PATH) as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description="Inject JSON findings into benchmark data")
    parser.add_argument("--input", required=True, help="Path to JSON findings file")
    parser.add_argument("--tool-name", default="firebreak", help="Tool label in output")
    parser.add_argument("--min-severity", default="info", help="Minimum severity threshold")
    parser.add_argument("--dry-run", action="store_true", help="Output to stdout instead of writing to benchmark_data.json")
    args = parser.parse_args()

    input_path = pathlib.Path(args.input)
    with open(input_path) as f:
        all_findings = json.load(f)

    # Filter to verified findings only
    verified = [f for f in all_findings if f.get("status") in VERIFIED_STATUSES]

    # Apply severity filter
    filtered = filter_by_severity(verified, args.min_severity)

    # Convert to benchmark format
    converted = [convert_finding(f) for f in filtered]

    if args.dry_run:
        json.dump(converted, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write('\n')
        return

    # Non-dry-run: inject into benchmark_data.json
    BENCHMARK_DATA.parent.mkdir(parents=True, exist_ok=True)

    if BENCHMARK_DATA.exists():
        with open(BENCHMARK_DATA) as f:
            benchmark = json.load(f)
    else:
        benchmark = {"runs": []}

    manifest = load_manifest()

    # Build a lookup from pr_id to manifest entry
    pr_lookup = {entry.get("pr_id"): entry for entry in manifest}

    run_entry = {
        "tool_name": args.tool_name,
        "findings": converted,
    }
    benchmark["runs"].append(run_entry)

    with open(BENCHMARK_DATA, "w") as f:
        json.dump(benchmark, f, indent=2, ensure_ascii=False)
        f.write('\n')


if __name__ == "__main__":
    main()
