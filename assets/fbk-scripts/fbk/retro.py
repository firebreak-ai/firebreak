#!/usr/bin/env python3
"""Retrospective append module — adds stage sections without overwriting prior stages."""

import os


def append_section(retrospective_path, stage_name, content):
    """Append a stage section to the retrospective file, preserving all prior sections.

    Reads the file before writing (read-before-write). Creates the file if it does not exist.
    """
    if os.path.exists(retrospective_path):
        with open(retrospective_path, encoding="utf-8", errors="replace") as f:
            existing = f.read()
    else:
        existing = ""

    section = f"## {stage_name}\n\n{content}\n"
    combined = existing + ("\n" if existing and not existing.endswith("\n\n") else "") + section

    with open(retrospective_path, "w", encoding="utf-8") as f:
        f.write(combined)
