#!/usr/bin/env python3
"""Design gate — structural validation for design phase artifacts."""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import List

from fbk.injection import detect_injections


def _parse_manifest_pages(manifest_text: str) -> List[str]:
    """Return slugs listed in the manifest as '- design/<slug>.md' lines."""
    return re.findall(r"- design/([\w-]+\.md)", manifest_text)


def _decisions_recorded_count(manifest_text: str):
    """Return the integer from 'Decisions recorded: N', or None if absent."""
    m = re.search(r"^Decisions recorded:\s*(\d+)", manifest_text, re.MULTILINE)
    if m is None:
        return None
    return int(m.group(1))


def _has_decomposition_rationale(text: str) -> bool:
    return bool(re.search(r"Decomposition rationale:", text, re.MULTILINE))


def _critical_section_has_content(fresh_eyes_text: str) -> bool:
    """Return True if the ## Critical section has non-blank list items."""
    lines = fresh_eyes_text.splitlines()
    in_critical = False
    for line in lines:
        if line.startswith("## Critical"):
            in_critical = True
            continue
        if in_critical:
            if line.startswith("## "):
                break
            if line.strip().startswith("-") or (line.strip() and not line.strip().startswith("#")):
                return True
    return False


def validate_design(feature_dir: str) -> dict:
    feature_path = Path(feature_dir)
    failures: List[str] = []
    injection_warnings = 0

    # 1. Manifest present
    manifest_path = feature_path / "design-manifest.md"
    if not manifest_path.exists():
        failures.append("design-manifest.md not found")
        return {
            "gate": "design",
            "result": "fail",
            "failures": failures,
            "injection_warnings": injection_warnings,
        }

    manifest_text = manifest_path.read_text(encoding="utf-8", errors="replace")
    injection_warnings += detect_injections(manifest_text)

    # 2. Bidirectional manifest <-> directory check
    listed_pages = _parse_manifest_pages(manifest_text)
    design_dir = feature_path / "design"
    disk_pages = [p.name for p in design_dir.glob("*.md")] if design_dir.is_dir() else []

    listed_set = set(listed_pages)
    disk_set = set(disk_pages)

    for page in listed_pages:
        if page not in disk_set:
            failures.append(f"Manifest lists {page} but file not found in design/")

    for page in disk_pages:
        if page not in listed_set:
            failures.append(f"design/{page} exists but is not listed in the manifest")

    # 3. Decomposition rationale
    if not _has_decomposition_rationale(manifest_text):
        failures.append("Decomposition rationale: not found in design-manifest.md")

    # 4. Decisions recorded non-zero
    count = _decisions_recorded_count(manifest_text)
    if count is None:
        failures.append("Decisions recorded: line absent from design-manifest.md")
    elif count == 0:
        failures.append("Decisions recorded: count is 0")

    # 5. Injection scan on design pages
    if design_dir.is_dir():
        for page_path in design_dir.glob("*.md"):
            page_text = page_path.read_text(encoding="utf-8", errors="replace")
            injection_warnings += detect_injections(page_text)

    # 6. Fresh-eyes no open critical
    fresh_eyes_path = feature_path / "fresh-eyes-design.md"
    if not fresh_eyes_path.exists():
        failures.append("fresh-eyes-design.md not found")
    else:
        fresh_text = fresh_eyes_path.read_text(encoding="utf-8", errors="replace")
        if _critical_section_has_content(fresh_text):
            failures.append("fresh-eyes-design.md has open critical observations")

    return {
        "gate": "design",
        "result": "pass" if not failures else "fail",
        "failures": failures,
        "injection_warnings": injection_warnings,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Structural validation for design phase artifacts."
    )
    parser.add_argument("feature_dir", help="Path to feature directory")
    args = parser.parse_args()

    feature_path = Path(args.feature_dir)
    if not feature_path.is_dir():
        print(f"Directory not found: {args.feature_dir}", file=sys.stderr)
        sys.exit(2)

    result = validate_design(args.feature_dir)
    print(json.dumps(result))
    sys.exit(0 if result["result"] == "pass" else 2)


if __name__ == "__main__":
    main()
