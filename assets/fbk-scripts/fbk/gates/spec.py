#!/usr/bin/env python3
"""Spec gate — structural validation for spec artifacts.

Converts spec-gate.sh to Python. Accepts a single spec path argument,
determines scope from filename, runs structural checks, and outputs JSON.
Exit 0 on pass, exit 2 on failure.
"""

import argparse
import json
import os
import pathlib
import re
import sys
from typing import List, Optional

from fbk.injection import detect_injections
from fbk.slices import TEST_DISCIPLINES


# ---------------------------------------------------------------------------
# Heading and section helpers
# ---------------------------------------------------------------------------

def heading_line(spec_text: str, heading: str) -> Optional[int]:
    """Return 1-based line number of first line matching heading prefix (case-insensitive), or None."""
    heading_lower = heading.lower()
    for i, line in enumerate(spec_text.splitlines(), 1):
        if line.lower().startswith(heading_lower):
            return i
    return None


def section_body(spec_text: str, line_number: int) -> str:
    """Return content between heading at line_number and next '## ' heading."""
    lines = spec_text.splitlines()
    result = []
    in_section = False
    for i, line in enumerate(lines, 1):
        if i == line_number:
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

def check_section(spec_text: str, heading: str, allow_empty: bool = False) -> List[str]:
    """Return list of failures for a required section."""
    failures = []
    ln = heading_line(spec_text, heading)
    if ln is None:
        failures.append(f"Missing section: {heading}")
        return failures
    if not allow_empty:
        body = section_body(spec_text, ln)
        if not body.strip():
            failures.append(f"Empty section: {heading}")
    return failures


def check_open_questions(bullets_or_text) -> List[str]:
    """Check open questions bullets each have rationale.

    Accepts either a list of bullet strings or a spec text string.
    Empty section is fine. If populated, each bullet (-/*/ + prefixed) must
    have text after a '?' on the same line, or an indented continuation line.
    """
    if isinstance(bullets_or_text, list):
        lines = bullets_or_text
    else:
        spec_text = bullets_or_text
        ln = heading_line(spec_text, "## open questions")
        if ln is None:
            return []
        body = section_body(spec_text, ln)
        if not body.strip():
            return []
        lines = body.splitlines()

    prev_bullet = ""
    prev_ok = False
    bad = False

    for line in lines:
        if re.match(r"^[\ \t]*[-*+][\ \t]", line):
            if prev_bullet and not prev_ok:
                bad = True
            prev_bullet = line
            prev_ok = False
            # Rationale on same line: text after '?' that contains an alpha char
            bullet_text = re.sub(r"^[\ \t]*[-*+][\ \t]", "", line)
            if "?" in bullet_text:
                after_q = bullet_text[bullet_text.index("?") + 1:]
                if re.search(r"[A-Za-z]", after_q):
                    prev_ok = True
        elif prev_bullet and re.match(r"^[\ \t]", line) and line.strip():
            # Indented continuation counts as rationale
            prev_ok = True

    if prev_bullet and not prev_ok:
        bad = True

    if bad:
        return ["Open questions: items must include rationale, not just a bare question"]
    return []


def check_feature_map(spec_text: str) -> List[str]:
    """Check feature map section has at least one list item or ### sub-heading."""
    ln = heading_line(spec_text, "## feature map")
    if ln is None:
        return []
    body = section_body(spec_text, ln)
    has_content = re.search(r"^[\ \t]*[-*+][\ \t]|^###", body, re.MULTILINE)
    if not has_content:
        return ["Feature map: must contain at least one list item or sub-heading"]
    return []


def _check_ac_format(spec_text: str) -> List[str]:
    """Validate AC identifiers in acceptance criteria section."""
    failures = []
    ac_ln = heading_line(spec_text, "## acceptance criteria")
    if ac_ln is None:
        return failures

    ac_body = section_body(spec_text, ac_ln)
    ac_ids = re.findall(r"AC-[0-9]+|AC[0-9]+|Criteria-[0-9]+|REQ-[0-9]+", ac_body)

    if not ac_ids:
        failures.append("Acceptance criteria: no AC identifiers found")
    else:
        bad_acs = [ac for ac in ac_ids if not re.match(r"^AC-[0-9]+$", ac)]
        if bad_acs:
            bad_str = ", ".join(bad_acs)
            failures.append(
                f"Acceptance criteria: invalid AC identifier format (expected AC-NN, found: {bad_str})"
            )
    return failures


def _check_testing_strategy_traceability(spec_text: str) -> List[str]:
    """Verify testing strategy section references at least one AC."""
    ts_ln = heading_line(spec_text, "## testing strategy")
    if ts_ln is None:
        return []
    ts_body = section_body(spec_text, ts_ln)
    ts_acs = re.findall(r"AC-[0-9]+", ts_body)
    if not ts_acs:
        return ["Testing strategy: does not trace to any ACs"]
    return []


# ---------------------------------------------------------------------------
# Slice validation
# ---------------------------------------------------------------------------

def check_slices(spec_text: str, inventory_behaviors: set = None) -> List[str]:
    """Return failure strings for slice-block violations; empty list = no failures.

    Only activates when the spec contains a '## Slices' heading. Legacy specs
    with no such heading return [] immediately (backward-compatible hinge).
    """
    if inventory_behaviors is None:
        inventory_behaviors = set()

    slices_ln = heading_line(spec_text, "## slices")
    if slices_ln is None:
        return []

    body = section_body(spec_text, slices_ln)
    lines = body.splitlines()

    failures = []
    slices = []
    current = None

    for line in lines:
        # Detect slice entry boundary: "- name: <x>" or "  - name: <x>"
        name_match = re.match(r"^\s*-\s+name:\s+(\S+)", line)
        if name_match:
            if current is not None:
                slices.append(current)
            current = {"name": name_match.group(1), "test-discipline": None, "covers": []}
            continue

        if current is None:
            continue

        td_match = re.match(r"^\s+test-discipline:\s+(\S+)", line)
        if td_match:
            current["test-discipline"] = td_match.group(1)
            continue

        covers_match = re.match(r"^\s+covers:\s*\[([^\]]*)\]", line)
        if covers_match:
            ids_text = covers_match.group(1)
            current["covers"] = [v.strip() for v in ids_text.split(",") if v.strip()]
            continue

    if current is not None:
        slices.append(current)

    all_covered = set()
    for s in slices:
        name = s["name"]
        td = s["test-discipline"]
        if td is None:
            failures.append(
                f"Slice '{name}': missing test-discipline field"
            )
        elif td not in TEST_DISCIPLINES:
            valid = ", ".join(TEST_DISCIPLINES)
            failures.append(
                f"Slice '{name}': invalid test-discipline '{td}' (valid: {valid})"
            )
        all_covered.update(s["covers"])

    for bid in sorted(inventory_behaviors):
        if bid not in all_covered:
            failures.append(f"Behavior '{bid}' not covered by any slice")

    return failures


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Structural validation for spec artifacts."
    )
    parser.add_argument("spec", help="Path to spec file (*-spec.md or *-overview.md)")
    args = parser.parse_args()

    spec_path = args.spec

    if not os.path.isfile(spec_path):
        print(f"File not found: {spec_path}", file=sys.stderr)
        sys.exit(2)

    base = os.path.basename(spec_path)
    if base.endswith("-spec.md"):
        scope = "feature"
    elif base.endswith("-overview.md"):
        scope = "project"
    else:
        print(
            f"Cannot determine scope: {base} (expected *-spec.md or *-overview.md)",
            file=sys.stderr,
        )
        sys.exit(2)

    with open(spec_path, "r", encoding="utf-8", errors="replace") as f:
        spec_text = f.read()

    fails = []

    if scope == "feature":
        for heading in [
            "## Problem",
            "## Goals",
            "## User-facing behavior",
            "## Technical approach",
            "## Testing strategy",
            "## Documentation impact",
            "## Acceptance criteria",
            "## Dependencies",
        ]:
            fails.extend(check_section(spec_text, heading))
        fails.extend(check_section(spec_text, "## Open questions", allow_empty=True))
        fails.extend(check_open_questions(spec_text))
        fails.extend(_check_ac_format(spec_text))
        fails.extend(_check_testing_strategy_traceability(spec_text))

        feature_dir = pathlib.Path(spec_path).parent
        inv_path = feature_dir / "behavior-inventory.yaml"
        if inv_path.exists():
            inv_text = inv_path.read_text(encoding="utf-8", errors="replace")
            inventory_behaviors = set(re.findall(r"^\s*-\s*id:\s*(\S+)", inv_text, re.M))
        else:
            inventory_behaviors = set()
        fails.extend(check_slices(spec_text, inventory_behaviors))
    else:
        for heading in [
            "## Vision",
            "## Architecture",
            "## Technology decisions",
            "## Feature map",
            "## Cross-cutting concerns",
        ]:
            fails.extend(check_section(spec_text, heading))
        fails.extend(check_section(spec_text, "## Open questions", allow_empty=True))
        fails.extend(check_feature_map(spec_text))
        fails.extend(check_open_questions(spec_text))

    spec_name = os.path.splitext(base)[0]

    if fails:
        for f in fails:
            print(f, file=sys.stderr)
        try:
            from fbk.capture import event_writer, gate_check
            _level = gate_check.resolve_capture_level(os.getcwd())
            _events_path = os.path.join(os.getcwd(), ".fbk-capture", "events.jsonl")
            event_writer.write(
                "PIPELINE_COMMAND",
                "chokepoint",
                {"gate": "spec", "result": "fail", "command_name": "spec-gate"},
                spec_name,
                None,
                _level,
                _events_path,
            )
        except Exception:
            pass
        sys.exit(2)

    # Injection detection (only on structural pass)
    injection_warnings = detect_injections(spec_path)

    result = {
        "gate": "spec",
        "scope": scope,
        "result": "pass",
        "injection_warnings": injection_warnings,
    }
    print(json.dumps(result))

    try:
        from fbk.capture import event_writer, gate_check
        _level = gate_check.resolve_capture_level(os.getcwd())
        _events_path = os.path.join(os.getcwd(), ".fbk-capture", "events.jsonl")
        event_writer.write(
            "PIPELINE_COMMAND",
            "chokepoint",
            {"gate": "spec", "result": "pass", "command_name": "spec-gate", **result},
            spec_name,
            None,
            _level,
            _events_path,
        )
    except Exception:
        pass


if __name__ == "__main__":
    main()
