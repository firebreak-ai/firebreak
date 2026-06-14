#!/usr/bin/env python3
"""Intent gate — structural validation for intent-phase artifacts.

Validates a feature directory containing prd.md, behavior-inventory.yaml,
grilling-log-intent.md, and fresh-eyes-intent.md. Outputs JSON to stdout.
Exit 0 on pass, exit 2 on failure.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import List, Optional

from fbk.injection import detect_injections


# ---------------------------------------------------------------------------
# Heading helpers
# ---------------------------------------------------------------------------

def _heading_present(text: str, heading: str) -> bool:
    """Return True if text contains a '## <heading>' line (case-insensitive prefix match)."""
    prefix = f"## {heading}".lower()
    for line in text.splitlines():
        if line.lower().startswith(prefix):
            return True
    return False


def _section_body(text: str, heading: str) -> str:
    """Return content between the named heading and the next '## ' heading."""
    prefix = f"## {heading}".lower()
    lines = text.splitlines()
    in_section = False
    result = []
    for line in lines:
        if line.lower().startswith(prefix):
            in_section = True
            continue
        if in_section:
            if line.startswith("## "):
                break
            result.append(line)
    return "\n".join(result)


# ---------------------------------------------------------------------------
# Check functions
# ---------------------------------------------------------------------------

_PRD_SECTIONS = [
    "Vision",
    "Problem statement",
    "Goals and non-goals",
    "Use cases",
    "Functional requirements",
    "Non-functional requirements",
    "Edge cases and failure modes",
    "Dependencies",
    "Success metrics",
    "Open questions",
]


def _check_prd_sections(prd_text: str) -> List[str]:
    failures = []
    for section in _PRD_SECTIONS:
        if not _heading_present(prd_text, section):
            failures.append(f"Missing PRD section: {section}")
    return failures


def _extract_behavior_ids(text: str) -> set:
    return set(re.findall(r"B-\d+", text))


def _check_bidirectional_consistency(prd_text: str, inventory_text: str) -> List[str]:
    failures = []
    inventory_ids = _extract_behavior_ids(inventory_text)
    prd_ids = _extract_behavior_ids(prd_text)

    for bid in sorted(inventory_ids - prd_ids):
        failures.append(f"Behavior {bid} is in the inventory but not referenced in the PRD")
    for bid in sorted(prd_ids - inventory_ids):
        failures.append(f"Behavior {bid} is referenced in the PRD but not in the inventory")

    return failures


def _check_grilling_log(log_text: Optional[str]) -> List[str]:
    """Return failures for a missing or malformed grilling log.

    Well-formed requires both a '### ' decision-slug heading and a 'Confirmed:' line.
    """
    if log_text is None:
        return ["Missing grilling-log-intent.md — a grilling log is required"]

    has_decision_block = any(
        line.startswith("### ") for line in log_text.splitlines()
    )
    has_confirmed = "Confirmed:" in log_text

    if not has_decision_block or not has_confirmed:
        return [
            "grilling-log-intent.md is malformed: missing a well-formed decision block "
            "(requires a '### ' heading and a 'Confirmed:' reflect-back line)"
        ]
    return []


def _check_fresh_eyes(fresh_eyes_text: Optional[str]) -> List[str]:
    """Return failures if the fresh-eyes report has open critical observations."""
    if fresh_eyes_text is None:
        return ["Missing fresh-eyes-intent.md"]

    if not _heading_present(fresh_eyes_text, "Critical"):
        return []

    body = _section_body(fresh_eyes_text, "Critical")
    has_observations = any(
        line.strip().startswith("-") for line in body.splitlines()
    )
    if has_observations:
        return ["fresh-eyes-intent.md has open critical observations — resolve before proceeding"]
    return []


# ---------------------------------------------------------------------------
# Public gate function
# ---------------------------------------------------------------------------

def validate_intent(feature_dir: str) -> dict:
    """Validate the intent-phase artifact set under feature_dir.

    Returns a result dict with keys: gate, result, failures, injection_warnings.
    """
    base = Path(feature_dir)
    failures: List[str] = []
    injection_warnings = 0

    # --- Read artifacts (errors="replace" so binary degrades to structural failure) ---

    prd_path = base / "prd.md"
    if prd_path.exists():
        prd_text = prd_path.read_text(encoding="utf-8", errors="replace")
    else:
        failures.append("Missing prd.md")
        prd_text = ""

    inventory_path = base / "behavior-inventory.yaml"
    if inventory_path.exists():
        inventory_text = inventory_path.read_text(encoding="utf-8", errors="replace")
    else:
        failures.append("Missing behavior-inventory.yaml")
        inventory_text = ""

    grilling_path = base / "grilling-log-intent.md"
    if grilling_path.exists():
        grilling_text: Optional[str] = grilling_path.read_text(encoding="utf-8", errors="replace")
    else:
        grilling_text = None

    fresh_eyes_path = base / "fresh-eyes-intent.md"
    if fresh_eyes_path.exists():
        fresh_eyes_text: Optional[str] = fresh_eyes_path.read_text(encoding="utf-8", errors="replace")
    else:
        fresh_eyes_text = None

    # --- Checks ---

    if prd_text:
        failures.extend(_check_prd_sections(prd_text))

    if prd_text and inventory_text:
        failures.extend(_check_bidirectional_consistency(prd_text, inventory_text))

    failures.extend(_check_grilling_log(grilling_text))
    failures.extend(_check_fresh_eyes(fresh_eyes_text))

    # --- Injection scan (non-blocking) ---

    injection_warnings += detect_injections(prd_text)
    injection_warnings += detect_injections(inventory_text)
    if grilling_text is not None:
        injection_warnings += detect_injections(grilling_text)
    if fresh_eyes_text is not None:
        injection_warnings += detect_injections(fresh_eyes_text)

    return {
        "gate": "intent",
        "result": "pass" if not failures else "fail",
        "failures": failures,
        "injection_warnings": injection_warnings,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Structural validation for intent-phase artifacts."
    )
    parser.add_argument("feature_dir", help="Path to the feature directory")
    args = parser.parse_args()

    if not Path(args.feature_dir).is_dir():
        print(f"Directory not found: {args.feature_dir}", file=sys.stderr)
        sys.exit(2)

    result = validate_intent(args.feature_dir)
    print(json.dumps(result))
    sys.exit(0 if result["result"] == "pass" else 2)


if __name__ == "__main__":
    main()
