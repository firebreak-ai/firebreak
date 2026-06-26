"""Shared strict verdict-line parsing for review gates.

A verdict-bearing artifact carries exactly one anchored, case-sensitive
``Verdict: <value>`` line. Zero is treated as absent; more than one is a
malformed artifact and must not be resolved by silently picking one.

This is the single parser the spec-review, code-review, and coherence gates
share, replacing three divergent inline scans (two took the first matching
line, one took the last, all were case-insensitive).
"""

import re

_VERDICT_LINE_RE = re.compile(r"^Verdict:\s*(.*?)\s*$")


def parse_single_verdict(text):
    """Return the single verdict value in *text*.

    - Returns the value string when exactly one anchored ``Verdict:`` line is present.
    - Returns ``None`` when no such line is present.
    - Raises ``ValueError`` when more than one ``Verdict:`` line is present.

    The match is anchored to the start of a line and case-sensitive (capital
    ``Verdict:``), so prose mentions of the word elsewhere in a line do not count.
    """
    values = [
        m.group(1)
        for line in text.splitlines()
        if (m := _VERDICT_LINE_RE.match(line))
    ]
    if len(values) > 1:
        raise ValueError(
            f"ambiguous verdict: {len(values)} 'Verdict:' lines found in artifact"
        )
    return values[0] if values else None
