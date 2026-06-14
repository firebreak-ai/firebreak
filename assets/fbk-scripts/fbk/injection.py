"""Shared injection-detection module for spec and gate artifacts."""

import os
import re
import sys


def detect_injections(path_or_text: str) -> int:
    """Detect injection patterns in a file or text. Prints WARNINGs to stderr. Returns warning count.

    Accepts either a file path or raw text string. If the argument is an
    existing file path, reads and decodes it; otherwise treats it as raw text.
    """
    warnings = 0

    if os.path.isfile(path_or_text):
        with open(path_or_text, "rb") as f:
            raw = f.read()
        text = raw.decode("utf-8", errors="replace")
    else:
        text = path_or_text
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
        "​": "zero-width space",
        "‌": "zero-width non-joiner",
        "‍": "zero-width joiner",
        "⁠": "word joiner",
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
        bom = "﻿"
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
