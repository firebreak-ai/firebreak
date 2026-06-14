"""Shared heading/section helpers for spec and contract gates.

Extracted here to break the potential circular import between spec.py and
contracts.py. Both modules import from this neutral module instead of from
each other.
"""

from typing import Optional


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
