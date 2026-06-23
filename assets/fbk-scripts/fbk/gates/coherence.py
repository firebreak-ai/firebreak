#!/usr/bin/env python3
"""Coherence gate — verifies coherence-review.md exists and carries an accepted verdict."""

import argparse
import json
import sys
from pathlib import Path
from typing import List


def validate_coherence(feature_dir: str) -> dict:
    feature_path = Path(feature_dir)
    failures: List[str] = []

    review_path = feature_path / "coherence-review.md"
    if not review_path.exists():
        failures.append("coherence-review.md not found")
        return {"gate": "coherence", "result": "fail", "failures": failures}

    text = review_path.read_text(encoding="utf-8", errors="replace")

    # Scan all lines and keep the last one whose stripped form starts with "verdict:".
    last_verdict_value = None
    for line in text.splitlines():
        if line.lower().startswith("verdict:"):
            last_verdict_value = line.split(":", 1)[1].strip()

    if last_verdict_value is None:
        failures.append("coherence-review.md has no Verdict: line")
        return {"gate": "coherence", "result": "fail", "failures": failures}

    if last_verdict_value.lower() != "accepted":
        failures.append(f"coherence-review.md final verdict is '{last_verdict_value}', expected 'accepted'")

    return {"gate": "coherence", "result": "pass" if not failures else "fail", "failures": failures}


def main():
    parser = argparse.ArgumentParser(
        description="Coherence gate: verifies coherence-review.md exists with an accepted verdict."
    )
    parser.add_argument("feature_dir", help="Path to feature directory")
    args = parser.parse_args()

    feature_path = Path(args.feature_dir)
    if not feature_path.is_dir():
        print(f"Directory not found: {args.feature_dir}", file=sys.stderr)
        sys.exit(2)

    result = validate_coherence(args.feature_dir)
    print(json.dumps(result))
    sys.exit(0 if result["result"] == "pass" else 2)


if __name__ == "__main__":
    main()
