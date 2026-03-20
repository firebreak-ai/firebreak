## Objective

Refactor the existing `spec-gate.sh` to add injection pattern detection while preserving all existing structural validation.

## Context

The existing `spec-gate.sh` validates spec structure: detects feature vs. project scope from filename, checks required sections are present and non-empty, validates open question rationale format, and validates feature map structure for project-scope specs. It exits 0 with JSON to stdout on pass, exit 2 with errors to stderr on fail.

The refactored script adds injection detection after structural validation passes — scanning spec content for mechanical vectors that could alter agent behavior. These are warnings to stderr, not hard failures. The structural exit code is preserved (if structure passes, exit 0 even with injection warnings). Structural validation itself is the sanitization: a spec that passes the gate has validated structure and content aligned with the spec template rules.

The existing `breakdown-gate.sh` demonstrates the pattern for embedding Python3 in a bash gate script: bash handles argument parsing, then delegates to Python via heredoc `python3 - "$ARGS" <<'PYEOF'`.

AC format validation (`AC-NN`) and testing strategy AC traceability are new structural checks being added alongside injection detection.

## Instructions

1. Read the current `home/dot-claude/hooks/sdl-workflow/spec-gate.sh` in full. Identify the existing validation flow: argument parsing, scope detection, section checks, open questions check, feature map check, pass/fail output.

2. Add AC identifier format validation after the existing section checks (within the `if [[ "$SCOPE" == "feature" ]]` block). Extract the Acceptance criteria section body. Use grep or awk to find all AC identifiers. Verify each matches the pattern `AC-[0-9][0-9]` (exactly `AC-` followed by two digits). If any identifiers are found that don't match this pattern, add to `FAILS`. If no AC identifiers are found at all in the Acceptance criteria section, add "Acceptance criteria: no AC identifiers found" to `FAILS`.

3. Add testing strategy AC traceability validation (feature scope only). Extract the Testing strategy section body. Check that it contains at least one `AC-NN` reference. If the Testing strategy section has no AC references, add "Testing strategy: does not trace to any ACs" to `FAILS`.

4. After the structural validation pass/fail decision point (after `if [[ ${#FAILS[@]} -gt 0 ]]`), add injection detection that runs only when structural validation passed (i.e., before the final JSON output line). Implement injection detection as embedded Python3 following the breakdown-gate.sh heredoc pattern.

5. The Python injection detection block receives the spec file path as an argument. It performs these checks:

   a. **Control character detection**: Scan for any byte in ranges 0x00-0x08, 0x0B-0x0C, 0x0E-0x1F (excluding 0x09 tab, 0x0A newline, 0x0D carriage return). Report each occurrence with line number.

   b. **Zero-width character detection**: Scan for U+200B (zero-width space), U+200C (zero-width non-joiner), U+200D (zero-width joiner), U+FEFF (BOM/zero-width no-break space, except at file position 0 where it's a legitimate BOM), U+2060 (word joiner). Report each occurrence with line number.

   c. **HTML comment instruction detection**: Find HTML comments (`<!-- ... -->`) whose content contains instruction-like phrases: "ignore", "disregard", "override", "new instructions", "forget", "approve", "you are", "act as", "pretend". Non-instructional comments (containing only "TODO", "FIXME", "NOTE", "HACK", or purely whitespace/punctuation) are exempt. Report each suspicious comment with line number.

   d. **Embedded instruction pattern detection**: Outside of fenced code blocks (``` ... ```) and inline code (`` ` ... ` ``), scan for these phrases (case-insensitive): "ignore previous instructions", "ignore previous", "disregard above", "disregard all", "you are now", "new instructions:", "forget everything", "override all constraints", "act as if". Report each with line number and matching phrase.

6. The Python block outputs each warning to stderr in format: `WARNING: [injection] <description> (line <N>)`. It prints the warning count to stdout as a JSON field `"injection_warnings": <count>`. The Python block always exits 0 — injection detection is advisory.

7. Modify the final JSON output line to include the injection warning count. Change from `printf '{"gate":"spec","scope":"%s","result":"pass"}\n'` to include `"injection_warnings":<N>`. If injection detection is not run (structural failure), the warning count is omitted.

9. After producing the final JSON result (pass or fail), log the result to the audit log. Determine the spec name from the filename (strip path and extension). Call `audit-logger.py log <spec-name> gate_result '<json>'` where `<json>` is the same JSON emitted to stdout (on pass) or a `{"gate":"spec","result":"fail","errors":[...]}` summary (on fail). Locate `audit-logger.py` relative to the script at `home/dot-claude/hooks/sdl-workflow/audit-logger.py`. If the logger is not available (file not found), skip logging silently — do not fail the gate.

10. Verify backward compatibility: the existing valid-spec fixture and overview-spec fixture from task-07 must still pass with exit 0 and no warnings. The existing argument parsing, scope detection, and section validation logic must not change behavior.

11. Ensure `set -uo pipefail` remains at the top. Ensure all existing functions (`heading_line`, `section_body`, `check_section`, `check_open_questions`, `check_feature_map`) are preserved unchanged.

## Files to create/modify

- `home/dot-claude/hooks/sdl-workflow/spec-gate.sh` (modify)

## Test requirements

Tests from task-07 (`tests/sdl-workflow/test-spec-validator.sh`) must pass:
- Valid feature spec: exit 0, no stderr warnings
- Missing sections: exit 2
- Bad AC format: exit 2
- No AC traceability in testing strategy: exit 2
- Injection patterns: exit 0 with stderr warnings (at least 3 distinct warnings)
- Legitimate HTML: exit 0, no stderr warnings
- Unicode spec: exit 0, no stderr warnings
- Overview spec: exit 0 with project scope
- Non-existent file: exit 2
- Unrecognized filename: exit 2

## Acceptance criteria

AC-04: Spec validator rejects specs that fail schema validation (missing sections, invalid AC format, missing testing strategy AC traceability) and detects injection patterns. Passes valid specs without false positives.

Primary AC: tests from task-07 pass.

## Model

Sonnet

## Wave

2
