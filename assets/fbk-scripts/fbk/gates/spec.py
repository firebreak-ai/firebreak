#!/usr/bin/env python3
"""Spec gate — structural validation for spec artifacts.

Converts spec-gate.sh to Python. Accepts a single spec path argument,
determines scope from filename, runs structural checks, and outputs JSON.
Exit 0 on pass, exit 2 on failure.
"""

import argparse
import json
import os
import re
import sys
from typing import List, Optional


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
# Injection detection
# ---------------------------------------------------------------------------

def detect_injections(spec_path_or_text: str) -> int:
    """Detect injection patterns in spec file or text. Prints WARNINGs to stderr. Returns warning count.

    Accepts either a file path or raw spec text string. If the argument is an
    existing file path, reads and decodes it; otherwise treats it as raw text.
    """
    import os as _os
    warnings = 0

    if _os.path.isfile(spec_path_or_text):
        with open(spec_path_or_text, "rb") as f:
            raw = f.read()
        text = raw.decode("utf-8", errors="replace")
    else:
        text = spec_path_or_text
        raw = text.encode("utf-8")

    lines = text.split("\n")

    # 1. Control character detection (U+0000-U+0008, U+000B-U+000C, U+000E-U+001F)
    for i, line in enumerate(lines, 1):
        for ch in line:
            code = ord(ch)
            if (0x00 <= code <= 0x08) or (0x0B <= code <= 0x0C) or (0x0E <= code <= 0x1F):
                print(
                    f"WARNING: [injection] control character U+{code:04X} detected (line {i})",
                    file=sys.stderr,
                )
                warnings += 1
                break  # one warning per line

    # 2. Zero-width character detection
    zw_chars = {
        "\u200B": "zero-width space",
        "\u200C": "zero-width non-joiner",
        "\u200D": "zero-width joiner",
        "\u2060": "word joiner",
    }
    for i, line in enumerate(lines, 1):
        for ch, name in zw_chars.items():
            if ch in line:
                print(
                    f"WARNING: [injection] {name} (U+{ord(ch):04X}) detected (line {i})",
                    file=sys.stderr,
                )
                warnings += 1
                break

    # BOM not at position 0
    if len(raw) > 3:
        bom = "\uFEFF"
        for i, line in enumerate(lines, 1):
            if bom in line and not (i == 1 and line.startswith(bom)):
                print(
                    f"WARNING: [injection] BOM/zero-width no-break space in non-BOM position (line {i})",
                    file=sys.stderr,
                )
                warnings += 1
                break

    # 3. HTML comment instruction detection
    comment_pattern = re.compile(r"<!--(.*?)-->", re.DOTALL)
    exempt_words = {"todo", "fixme", "note", "hack"}
    instruction_words = [
        "ignore", "disregard", "override", "new instructions",
        "forget", "approve", "you are", "act as", "pretend",
    ]

    for m in comment_pattern.finditer(text):
        content = m.group(1).strip().lower()
        words = set(re.findall(r"\w+", content))
        if words and words.issubset(exempt_words | {"", " "}):
            continue
        for phrase in instruction_words:
            if phrase in content:
                start = m.start()
                line_num = text[:start].count("\n") + 1
                print(
                    f"WARNING: [injection] HTML comment contains instruction-like phrase '{phrase}' (line {line_num})",
                    file=sys.stderr,
                )
                warnings += 1
                break

    # 4. Embedded instruction patterns outside code blocks
    instruction_patterns = [
        "ignore previous instructions",
        "ignore previous",
        "disregard above",
        "disregard all",
        "you are now",
        "new instructions:",
        "forget everything",
        "override all constraints",
        "act as if",
        "disregard above constraints",
    ]

    # Strip fenced code blocks
    in_fence = False
    clean_lines = []
    for line in lines:
        if line.strip().startswith("```"):
            in_fence = not in_fence
            clean_lines.append("")
            continue
        if in_fence:
            clean_lines.append("")
        else:
            # Strip inline code
            clean_lines.append(re.sub(r"`[^`]+`", "", line))

    for i, line in enumerate(clean_lines, 1):
        lower = line.lower()
        for pattern in instruction_patterns:
            if pattern in lower:
                print(
                    f"WARNING: [injection] embedded instruction pattern '{pattern}' (line {i})",
                    file=sys.stderr,
                )
                warnings += 1
                break

    return warnings


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
            from fbk import audit
            audit.log_event(spec_name, "gate_result", json.dumps({"gate": "spec", "result": "fail"}))
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
        from fbk import audit
        audit.log_event(spec_name, "gate_result", json.dumps(result))
    except Exception:
        pass


if __name__ == "__main__":
    main()
