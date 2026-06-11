"""Event-envelope vocabulary, drift checks, and redaction for metrics plane.

Defines the closed event-type vocabulary, registered sources, a central
redaction layer that strips free-text payloads at standard level, and a
build/test-time drift check that flags any event-type literal not in the
vocabulary.
"""

from pathlib import Path


# Closed vocabulary of event types allowed in envelopes.
EVENT_TYPES = (
    "PIPELINE_COMMAND",
    "VERIFICATION_RESULT",
    "CODE_REVIEW_ROUNDS",
    "TOOL_USE",
    "SUBAGENT_STOP",
    "LIFECYCLE",
)

# Registered sources that write envelopes to the metrics plane.
SOURCES = ("hook_router", "chokepoint", "task_completed", "code_review")

# Free-text payload keys that carry user input, prompts, scope violations,
# or other sensitive data that should not be recorded at standard or off levels.
FREETEXT_KEYS = {
    "tool_input",
    "tool_args",
    "prompt_text",
    "text",
    "files",
    "out_of_scope_files",
    "scope_violations",
    "round_detail",
    "args",
    "command",
    "output",
    "reason_text",
}


def redact(data: dict, level: str) -> dict:
    """Return a redacted copy of the envelope payload at the given level.

    At "full", return the data unchanged. At "standard", "off", or any unknown
    level, return a copy with free-text payload keys removed while structural
    and numeric keys survive.

    Args:
        data: The envelope payload dictionary to redact.
        level: The redaction level ("full", "standard", "off", etc.).

    Returns:
        A copy of data with free-text keys removed if level is not "full".
    """
    if level == "full":
        return data

    # For any other level (standard, off, or unknown), strip free-text keys.
    return {k: v for k, v in data.items() if k not in FREETEXT_KEYS}


def check_drift(scan_root: str) -> list[str]:
    """Scan for event-type string literals not in the vocabulary.

    Globs *.py files recursively under scan_root, reads each file's text,
    and returns a list of ALL-CAPS-with-underscores quoted string literals
    that match the event-type shape but are not in EVENT_TYPES.

    Args:
        scan_root: The directory root to scan for .py files.

    Returns:
        A list of out-of-vocabulary event-type literals found (empty if clean).
    """
    import re

    # Only flag ALL-CAPS literals that appear in an event-type *context*, so
    # unrelated ALL-CAPS constants (environment-variable names like
    # CLAUDE_CONFIG_DIR, datetime suffixes like "Z") are not mistaken for
    # drifted event types. The contexts that carry an event type are: a value
    # assigned to / keyed by an ``event_type`` name, and the first positional
    # argument to the envelope builder ``build_event(...)``.
    context_patterns = (
        re.compile(r'event_type\s*[=:]\s*["\']([A-Z][A-Z_]*)["\']'),
        re.compile(r'build_event\(\s*["\']([A-Z][A-Z_]*)["\']'),
    )

    found_literals = set()
    scan_path = Path(scan_root)

    # Recursively glob all .py files.
    for py_file in scan_path.glob("**/*.py"):
        try:
            text = py_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            # Skip files we cannot read.
            continue

        for pattern in context_patterns:
            for match in pattern.finditer(text):
                found_literals.add(match.group(1))

    # Return those not in the vocabulary.
    vocabulary = set(EVENT_TYPES)
    out_of_vocab = found_literals - vocabulary
    return sorted(list(out_of_vocab))


def is_known_event_type(event_type: str) -> bool:
    """Check if an event type is in the vocabulary.

    Args:
        event_type: The event type string to check.

    Returns:
        True if event_type is in EVENT_TYPES, False otherwise.
    """
    return event_type in EVENT_TYPES
