---
id: task-43
type: implementation
wave: 1
covers: [AC-01, AC-08]
files_to_create:
  - assets/fbk-scripts/fbk/gates/spec.py
test_tasks: [task-01, task-02]
completion_gate: "task-01 and task-02 tests pass"
---

## Objective

Convert `assets/hooks/fbk-sdl-workflow/spec-gate.sh` to `assets/fbk-scripts/fbk/gates/spec.py`, reimplementing all bash logic in Python.

## Context

`spec-gate.sh` (242 lines) performs structural validation of spec documents. The bash portion (lines 1-126) implements: `heading_line()` (awk-based heading detection), `section_body()` (awk-based section extraction), `check_section(heading, allow_empty)`, `check_open_questions()`, `check_feature_map()`, AC format validation, testing strategy AC traceability, and audit logging. The embedded Python heredoc (lines 131-228) implements injection detection for control characters, zero-width characters, HTML comments, and embedded instruction patterns.

The Python module must expose: `check_section(spec_text, heading, allow_empty=False)` returning a list of failure strings, `check_open_questions(spec_text)` returning a list of failure strings, `detect_injections(spec_text)` returning an integer warning count with warnings printed to stderr. The `main()` function must accept a single positional argument (spec path), determine scope from filename, run all checks, and produce identical JSON output on stdout and exit codes (0 pass, 2 fail).

## Instructions

1. Create `assets/fbk-scripts/fbk/gates/spec.py`
2. Implement `heading_line(spec_text, heading)` — return line number (1-based) of first line matching heading prefix case-insensitively, or None
3. Implement `section_body(spec_text, line_number)` — return content between the heading at line_number and the next `## ` heading
4. Implement `check_section(spec_text, heading, allow_empty=False)` — return list of failures: `"Missing section: {heading}"` if heading not found, `"Empty section: {heading}"` if body is whitespace-only and allow_empty is False
5. Implement `check_open_questions(spec_text)` — parse bullets (`- `, `* `, `+ ` prefixed), check each has rationale (text after `?` on same line, or indented continuation on next line). Return `["Open questions: items must include rationale, not just a bare question"]` if any bullet lacks rationale
6. Implement `check_feature_map(spec_text)` — check section has at least one list item or `###` sub-heading
7. Implement AC format validation — extract AC identifiers from acceptance criteria section, verify they match `AC-NN` format
8. Implement testing strategy AC traceability — verify testing strategy section references at least one AC
9. Implement `detect_injections(spec_text)` — port the Python heredoc logic exactly: control chars (U+0000-U+0008, U+000B-U+000C, U+000E-U+001F), zero-width chars (U+200B/C/D, U+2060), BOM in non-BOM position, HTML comment instruction detection, embedded instruction patterns outside code blocks. Read the spec file in binary mode (`open(path, 'rb')`) for BOM and control-char detection to preserve fidelity with the existing implementation. Print WARNING lines to stderr. Return total warning count
10. Implement `main()` with argparse: accept spec path, determine scope from filename (`*-spec.md` → feature, `*-overview.md` → project), run appropriate section checks, run injection detection on pass, output JSON `{"gate":"spec","scope":"<scope>","result":"pass","injection_warnings":<N>}` on stdout, log to `fbk.audit.log_event` if available
11. On failure: print failures to stderr, exit 2. On pass: print JSON to stdout, exit 0

## Files to create/modify

- **Create**: `assets/fbk-scripts/fbk/gates/spec.py`

## Test requirements

- task-01: `check_section` detects missing/empty sections, validates present sections, `check_open_questions` detects bare questions and passes rationale
- task-02: `detect_injections` detects control chars, zero-width chars, HTML comments, embedded instructions, produces 0 for clean specs, exempts code blocks

## Acceptance criteria

- AC-01: spec-gate.sh converted to Python module
- AC-08: gate produces identical JSON output and exit codes for same inputs

## Model

Sonnet

## Wave

1
