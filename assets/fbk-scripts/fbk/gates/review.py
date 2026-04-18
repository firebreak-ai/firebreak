"""Review gate validation logic."""

import argparse
import json
import re
import sys
from typing import List, Optional, Tuple


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
) -> Tuple[str, List[str]]:
    """Validate review content against review gate requirements.

    Args:
        review_text: The review markdown content as a string
        perspectives: List of perspective names that should appear in review
        threat_model_text: Optional threat model document content to validate

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

    result, failures = validate_review(review_text, perspectives, threat_model_text)

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
