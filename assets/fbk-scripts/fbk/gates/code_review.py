#!/usr/bin/env python3
"""Code-review gate — checks quality-scan and test-review artifacts, delegates hash verification."""

import argparse
import glob
import json
import sys
from pathlib import Path

from fbk.gates import test_hash


def validate_code_review(feature_dir: str) -> dict:
    base = Path(feature_dir)
    failures = []
    findings = []

    # Check 1: quality-scan.md present with a Severity: field.
    quality_scan = base / "quality-scan.md"
    if not quality_scan.exists():
        failures.append("quality-scan artifact missing: quality-scan.md not found")
    else:
        text = quality_scan.read_text(encoding="utf-8", errors="replace")
        if "Severity:" not in text:
            failures.append("quality-scan artifact missing Severity: field")

    # Check 2: test-review final-pass artifact present.
    test_review_canonical = base / "test-review-final.md"
    if test_review_canonical.exists():
        pass  # found canonical name
    else:
        fallback_matches = sorted(glob.glob(str(base / "test-review-*.md")))
        if not fallback_matches:
            failures.append("test-review verdict artifact missing: test-review-final.md not found")

    # Check 3: delegate hash + shadow-test check to test_hash.verify_manifest.
    discrepancies = test_hash.verify_manifest(feature_dir)
    for item in discrepancies:
        kind = item.get("kind")
        path = item.get("path", "")
        if kind == "modified":
            failures.append(f"modified locked test: {path}")
        elif kind == "unexpected":
            failures.append(f"shadow test (unexpected): {path}")
        elif kind == "missing":
            findings.append(f"missing locked test (non-blocking): {path}")

    return {
        "gate": "code-review",
        "result": "pass" if not failures else "fail",
        "failures": failures,
        "findings": findings,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Code-review gate: checks quality-scan, test-review, and hash manifest."
    )
    parser.add_argument("feature_dir", help="Path to feature directory")
    args = parser.parse_args()

    feature_dir = args.feature_dir
    if not Path(feature_dir).is_dir():
        print(f"Directory not found: {feature_dir}", file=sys.stderr)
        sys.exit(2)

    result = validate_code_review(feature_dir)
    print(json.dumps(result))
    sys.exit(0 if result["result"] == "pass" else 2)


if __name__ == "__main__":
    main()
