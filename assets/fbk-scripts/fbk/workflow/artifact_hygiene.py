"""Deterministic scan of phase artifacts for characters a reviewer cannot see.

Raw control characters, invisible format characters, Unicode line boundaries,
spaces other than the ordinary one, and undecodable bytes survive review rounds
unnoticed because the reader cannot see them or cannot tell them from a space. This scan
is byte-level and project-agnostic; it makes no judgment about artifact content.
"""

import unicodedata

from .store import WorkflowError, confined

FINDINGS_LIMIT = 50
SIZE_LIMIT = 4 * 1024 * 1024
BINARY_PROBE = 8 * 1024
ALLOWED_CONTROLS = {"\t", "\n", "\r"}
# Unicode categories reported: controls, format characters (zero-width characters,
# byte-order mark, direction marks), line and paragraph separators, and every space
# but the ordinary one, since the others look like it.
REPORTED_CATEGORIES = {"Cc", "Cf", "Zl", "Zp", "Zs"}
REPLACEMENT = "�"

# Control characters carry no Unicode name; these are their standard aliases.
CONTROL_NAMES = {
    0x00: "NULL", 0x01: "START OF HEADING", 0x02: "START OF TEXT",
    0x03: "END OF TEXT", 0x04: "END OF TRANSMISSION", 0x05: "ENQUIRY",
    0x06: "ACKNOWLEDGE", 0x07: "BELL", 0x08: "BACKSPACE",
    0x09: "CHARACTER TABULATION", 0x0A: "LINE FEED", 0x0B: "LINE TABULATION",
    0x0C: "FORM FEED", 0x0D: "CARRIAGE RETURN", 0x0E: "SHIFT OUT",
    0x0F: "SHIFT IN", 0x10: "DATA LINK ESCAPE", 0x11: "DEVICE CONTROL ONE",
    0x12: "DEVICE CONTROL TWO", 0x13: "DEVICE CONTROL THREE",
    0x14: "DEVICE CONTROL FOUR", 0x15: "NEGATIVE ACKNOWLEDGE",
    0x16: "SYNCHRONOUS IDLE", 0x17: "END OF TRANSMISSION BLOCK", 0x18: "CANCEL",
    0x19: "END OF MEDIUM", 0x1A: "SUBSTITUTE", 0x1B: "ESCAPE",
    0x1C: "INFORMATION SEPARATOR FOUR", 0x1D: "INFORMATION SEPARATOR THREE",
    0x1E: "INFORMATION SEPARATOR TWO", 0x1F: "INFORMATION SEPARATOR ONE",
    0x7F: "DELETE", 0x85: "NEXT LINE",
}


def suspicious(char):
    """True for a character the scan reports."""
    if char in ALLOWED_CONTROLS or char == " ":
        return False
    return unicodedata.category(char) in REPORTED_CATEGORIES or char == REPLACEMENT


def codepoint(char):
    return f"U+{ord(char):04X}"


def character_name(char):
    return CONTROL_NAMES.get(ord(char)) or unicodedata.name(char, "CONTROL CHARACTER")


def scan_text(text, path, *, limit=FINDINGS_LIMIT):
    """Findings for one decoded text; line and column are 1-based character positions.

    Only a line feed ends a line here, so an allowed carriage return and the
    reported line boundaries never shift the numbering the author sees in an editor.
    """
    findings, total = [], 0
    for line_number, line in enumerate(text.split("\n"), 1):
        for column, char in enumerate(line, 1):
            if not suspicious(char):
                continue
            total += 1
            if len(findings) < limit:
                findings.append({
                    "path": path,
                    "line": line_number,
                    "column": column,
                    "codepoint": codepoint(char),
                    "name": character_name(char),
                })
    return findings, total


def scan_files(root, paths, *, limit=FINDINGS_LIMIT):
    """Scan repository-relative text files; binary-looking or oversized files are reported as skipped."""
    findings, total, skipped, scanned = [], 0, [], []
    for relative in sorted(set(paths)):
        target = confined(root, relative)
        try:
            size = target.stat().st_size
            if size > SIZE_LIMIT:
                skipped.append({"path": relative, "reason": f"larger than {SIZE_LIMIT} bytes"})
                continue
            data = target.read_bytes()
        except OSError as exc:
            skipped.append({"path": relative, "reason": f"unreadable: {exc}"})
            continue
        if b"\x00" in data[:BINARY_PROBE]:
            skipped.append({"path": relative, "reason": "binary content"})
            continue
        found, count = scan_text(data.decode("utf-8", errors="replace"), relative, limit=limit)
        scanned.append(relative)
        total += count
        findings.extend(found[: max(0, limit - len(findings))])
    outcome = "findings" if total else ("skipped" if skipped else "clean")
    return {
        "outcome": outcome,
        "scanned": scanned,
        "skipped": skipped,
        "findings": findings,
        "total": total,
    }


def describe(finding):
    return f"{finding['path']}:{finding['line']}:{finding['column']} {finding['codepoint']} {finding['name']}"


def failure_message(report):
    lines = [describe(f) for f in report["findings"]]
    omitted = report["total"] - len(lines)
    if omitted > 0:
        lines.append(f"... and {omitted} more")
    return (
        f"Artifact hygiene scan found {report['total']} invisible character(s) a reviewer cannot see:\n"
        + "\n".join(lines)
        + "\nWrite each character as an escape (for example \\v or U+000B) or remove it, then close again."
    )


def require_clean(root, paths, *, limit=FINDINGS_LIMIT):
    """Return the scan report, or raise a WorkflowError naming every finding."""
    report = scan_files(root, paths, limit=limit)
    if report["findings"]:
        raise WorkflowError(failure_message(report))
    return report
