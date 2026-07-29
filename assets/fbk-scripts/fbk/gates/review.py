"""Review gate validation logic."""

import argparse
import glob
import json
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from fbk.gates.verdict import parse_single_verdict


def read_test_review_verdict(feature_dir: Path) -> Optional[str]:
    """Locate the spec-stage test-review artifact and return its verdict marker.

    Prefer the canonical artifact name, fall back to the newest
    `test-review-*.md`, then parse its verdict with the shared strict parser.

    Returns the verdict string (e.g. "accepted"), or None when no artifact is
    present or no verdict line is found. Raises ValueError when the artifact
    carries more than one verdict line (an ambiguous artifact must not be
    resolved by silently picking one); the caller turns that into a gate failure.

    Freshness note: this checks presence + verdict only — it does NOT verify the
    spec was unchanged after the verdict was written. Staleness detection is a
    known follow-on.
    """
    canonical = feature_dir / "test-review-spec.md"
    if canonical.exists():
        artifact = canonical
    else:
        fallback_matches = sorted(glob.glob(str(feature_dir / "test-review-*.md")))
        if not fallback_matches:
            return None
        artifact = Path(fallback_matches[-1])

    text = artifact.read_text(encoding="utf-8", errors="replace")
    return parse_single_verdict(text)


def section_of(heading_pattern: str, text: str) -> str:
    """Extract section content between a heading matching pattern and the next ## heading.

    Args:
        heading_pattern: Regex pattern (case-insensitive) matched against ## headings
        text: Full document text

    Returns:
        Content between the matched heading line and the next ## heading (exclusive),
        or empty string if heading not found.
    """
    lines = text.splitlines()
    capturing = False
    section_lines = []
    for line in lines:
        if re.search(heading_pattern, line, re.IGNORECASE):
            capturing = True
            continue
        if capturing and re.match(r'^## ', line):
            break
        if capturing:
            section_lines.append(line)
    return '\n'.join(section_lines)


def validate_review(
    review_text: str,
    perspectives: List[str],
    threat_model_text: Optional[str] = None,
    test_review_verdict: Optional[str] = None,
) -> Tuple[str, List[str]]:
    """Validate review content against review gate requirements.

    Args:
        review_text: The review markdown content as a string
        perspectives: List of perspective names that should appear in review
        threat_model_text: Optional threat model document content to validate
        test_review_verdict: The verdict read from the spec-stage test-review
            artifact, or None when the artifact is absent. An accepted verdict is
            required for the gate to pass; missing or non-accepted is blocking.

    Returns:
        Tuple of (result_status, failures_list) where result_status is "pass" or "fail"
        and failures_list is a list of failure messages. Empty failures list means "pass".
    """
    failures = []

    # 1. Perspective coverage — each perspective name appears in the review
    for perspective in perspectives:
        if not re.search(re.escape(perspective), review_text, re.IGNORECASE):
            failures.append(f"Missing perspective in review: {perspective}")

    # 2. Severity tags — at least one overall, then one per perspective section
    if not re.search(r'\b(blocking|important|informational)\b', review_text, re.IGNORECASE):
        failures.append("No severity tags (blocking/important/informational) found in review")
    else:
        for perspective in perspectives:
            sec = section_of(rf'^## .*{re.escape(perspective)}', review_text)
            if sec.strip():
                if not re.search(r'\b(blocking|important|informational)\b', sec, re.IGNORECASE):
                    failures.append(f"No severity tag under perspective section: {perspective}")

    # 3. Threat model determination section
    if not re.search(r'^##\s+threat\s+model', review_text, re.IGNORECASE | re.MULTILINE):
        failures.append("Missing ## Threat Model ... section")
    else:
        sec = section_of(r'^## threat model', review_text)
        if not re.search(r'\b(yes|no|skip)\b', sec, re.IGNORECASE):
            failures.append("Threat model determination missing decision (yes/no/skip)")
        if len(sec.split()) < 10:
            failures.append("Threat model determination section missing rationale")

    # 4. Testing strategy — all 3 categories required
    if not re.search(r'^##\s+test', review_text, re.IGNORECASE | re.MULTILINE):
        failures.append("Missing testing strategy section (## Testing / ## Test ...)")
    else:
        sec = section_of(r'^## test', review_text)
        if not re.search(r'new\s+tests?\s+needed|tests?\s+needed', sec, re.IGNORECASE):
            failures.append("Testing: missing 'new tests needed'")
        if not re.search(r'existing\s+tests?\s+impacted|tests?\s+impacted', sec, re.IGNORECASE):
            failures.append("Testing: missing 'existing tests impacted'")
        if not re.search(r'test\s+infrastructure|infrastructure\s+changes?', sec, re.IGNORECASE):
            failures.append("Testing: missing 'test infrastructure changes'")

    # 5 & 6. Threat model document checks (only when threat_model_text provided)
    if threat_model_text is not None:
        tm_sections = [
            (r'^##\s+assets', "## Assets"),
            (r'^##\s+threat\s+actors?', "## Threat Actors"),
            (r'^##\s+trust\s+boundaries?', "## Trust Boundaries"),
            (r'^##\s+threats', "## Threats"),
        ]
        for pattern, label in tm_sections:
            if not re.search(pattern, threat_model_text, re.IGNORECASE | re.MULTILINE):
                failures.append(f"Threat model missing: {label}")
            else:
                sec = section_of(pattern.lstrip('^'), threat_model_text)
                if not sec.strip():
                    failures.append(f"Threat model section is empty: {label}")

    # 7. Independent test-review verdict — blocking at the spec gate.
    # Unlike the code-review gate (where a non-accepted verdict is informational),
    # the spec gate treats a missing or non-accepted verdict as a hard failure.
    if test_review_verdict is None:
        failures.append(
            "Independent test-review artifact missing: test-review-spec.md not found "
            "(run the test-review pass after the council is clean)"
        )
    elif test_review_verdict.lower() != "accepted":
        failures.append(
            f"Independent test-review verdict is '{test_review_verdict}', not 'accepted'"
        )

    result = "pass" if not failures else "fail"
    return result, failures


def main() -> None:
    """CLI entry point: validate a review document and optionally a threat model document."""
    parser = argparse.ArgumentParser(
        description="Validate a review document against Firebreak review gate requirements."
    )
    parser.add_argument("review", help="Path to the review markdown file")
    parser.add_argument("perspectives", help="Comma-separated list of perspective names")
    parser.add_argument("threat_model", nargs="?", help="Path to the threat model document (optional)")
    args = parser.parse_args()

    try:
        review_text = open(args.review).read()
    except OSError as exc:
        print(f"review-gate: review file not found: {args.review}", file=sys.stderr)
        sys.exit(2)

    perspectives = [p.strip() for p in args.perspectives.split(",") if p.strip()]

    threat_model_text: Optional[str] = None
    if args.threat_model:
        try:
            threat_model_text = open(args.threat_model).read()
        except OSError:
            print(f"review-gate: threat model file not found: {args.threat_model}", file=sys.stderr)
            sys.exit(2)

    # Derive the feature directory from the review file's own folder — the
    # spec-stage test-review artifact lives alongside the review document.
    feature_dir = Path(args.review).resolve().parent
    try:
        test_review_verdict = read_test_review_verdict(feature_dir)
    except ValueError as e:
        print(f"FAIL: spec-stage test-review artifact is malformed: {e}", file=sys.stderr)
        sys.exit(2)

    result, failures = validate_review(
        review_text, perspectives, threat_model_text, test_review_verdict
    )

    if failures:
        for f in failures:
            print(f"FAIL: {f}", file=sys.stderr)
        sys.exit(2)

    output = {
        "gate": "review",
        "result": result,
        "failures": failures,
        "perspectives": perspectives,
        "threat_model": threat_model_text is not None,
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
