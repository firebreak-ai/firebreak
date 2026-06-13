#!/usr/bin/env python3
"""Code-review gate — checks quality-scan and test-review artifacts, delegates hash verification."""

import argparse
import glob
import json
import os
import sys
from pathlib import Path

from fbk.gates import test_hash

# Bounds for the round-log file — set comfortably above any realistic run.
MAX_ROUNDS = 100
MAX_ROUND_FILE_BYTES = 64 * 1024

# Fixed severity vocabulary for round entries (matches fbk.pipeline.VALID_SEVERITIES).
ROUND_SEVERITIES = ("critical", "major", "minor", "info")


def project_round_entries(rounds: list) -> list:
    """Allowlist-project round entries read from the untrusted round log.

    Returns a new list: each entry becomes {"raised": ..., "survived": ...}
    plus "severity" only when entry.get("severity") is a member of
    ROUND_SEVERITIES.  Every other key is dropped.  Order is preserved.
    raised/survived are already int-validated by _read_round_log.
    """
    projected = []
    for entry in rounds:
        slim = {"raised": entry.get("raised"), "survived": entry.get("survived")}
        if entry.get("severity") in ROUND_SEVERITIES:
            slim["severity"] = entry["severity"]
        projected.append(slim)
    return projected


def _read_round_log(feature_dir: str) -> dict | None:
    """Read and validate .code-review-rounds.json from feature_dir.

    Returns the parsed dict when the file is present and valid.
    Returns None when the file is absent (no warning) or malformed (with a
    stderr warning).
    """
    round_file = os.path.join(feature_dir, ".code-review-rounds.json")

    if not os.path.exists(round_file):
        return None

    # Reject oversized files before parsing.
    try:
        file_size = os.path.getsize(round_file)
    except OSError as exc:
        print(f"code-review-gate: could not stat round log: {exc}", file=sys.stderr)
        return None

    if file_size > MAX_ROUND_FILE_BYTES:
        print(
            f"code-review-gate: round log exceeds {MAX_ROUND_FILE_BYTES} bytes — treating as malformed",
            file=sys.stderr,
        )
        return None

    # Parse JSON.
    try:
        with open(round_file, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"code-review-gate: round log is not valid JSON — treating as malformed: {exc}", file=sys.stderr)
        return None

    # Validate shape.
    rounds = data.get("rounds")
    if not isinstance(rounds, list):
        print("code-review-gate: round log 'rounds' is not a list — treating as malformed", file=sys.stderr)
        return None

    if len(rounds) > MAX_ROUNDS:
        print(
            f"code-review-gate: round log has {len(rounds)} rounds (max {MAX_ROUNDS}) — treating as malformed",
            file=sys.stderr,
        )
        return None

    for entry in rounds:
        raised = entry.get("raised")
        survived = entry.get("survived")
        if not (isinstance(raised, int) and not isinstance(raised, bool)) or not (isinstance(survived, int) and not isinstance(survived, bool)):
            print(
                "code-review-gate: round entry raised/survived must be integers — treating as malformed",
                file=sys.stderr,
            )
            return None
        if raised < 0 or survived < 0:
            print(
                "code-review-gate: round entry raised/survived must be non-negative — treating as malformed",
                file=sys.stderr,
            )
            return None

    return data


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

    # Emit CODE_REVIEW_ROUNDS event when a valid round log is present.
    # This is a pure side effect — any failure here must not change pass/fail.
    try:
        from fbk.capture import event_writer, gate_check

        round_log = _read_round_log(feature_dir)
        if round_log is not None:
            # The round log is untrusted input; only raised/survived/enum-valid severity
            # may reach the events file.
            rounds = project_round_entries(round_log.get("rounds", []))
            total_raised = sum(r.get("raised", 0) for r in rounds)
            total_survived = sum(r.get("survived", 0) for r in rounds)
            spec = round_log.get("spec")
            events_path = os.path.join(os.getcwd(), ".fbk-capture", "events.jsonl")
            capture_level = gate_check.resolve_capture_level(os.getcwd())
            event_writer.write(
                "CODE_REVIEW_ROUNDS",
                "code_review",
                {
                    "spec": spec,
                    "rounds": rounds,
                    "total_raised": total_raised,
                    "total_survived": total_survived,
                },
                spec,
                None,
                capture_level,
                events_path,
            )
    except Exception:
        # Fail-silent: event emission must never change gate pass/fail.
        pass

    sys.exit(0 if result["result"] == "pass" else 2)


if __name__ == "__main__":
    main()
