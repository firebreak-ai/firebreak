---
id: task-02
type: test
wave: 1
covers: [AC-01, AC-08]
files_to_create:
  - assets/fbk-scripts/tests/test_gates_spec_injection.py
completion_gate: "tests compile and fail before implementation"
---

## Objective

Create pytest unit tests for `fbk.gates.spec` injection detection logic.

## Context

`spec-gate.sh` (lines 129-228) embeds a Python heredoc that detects four injection categories: control characters (U+0000-U+001F excluding tab/newline/CR), zero-width characters (U+200B/C/D, U+2060), HTML comments containing instruction-like phrases, and embedded instruction patterns outside code blocks. The Python module `fbk.gates.spec` must expose an injection detection function. Tests verify it returns warning counts matching the original behavior.

## Instructions

1. Create `assets/fbk-scripts/tests/test_gates_spec_injection.py`
2. Import the injection detection function from `fbk.gates.spec` (e.g., `detect_injections`)
3. Write a test with a spec string containing `\x01` control character — assert warning count >= 1
4. Write a test with a spec string containing `\u200B` (zero-width space) — assert warning count >= 1
5. Write a test with a spec string containing `<!-- ignore previous instructions -->` — assert warning count >= 1
6. Write a test with a spec string containing `ignore previous instructions` outside code blocks — assert warning count >= 1
7. Write a test with a clean spec string (no injection markers) — assert warning count == 0
8. Write a test with instruction text inside a fenced code block — assert warning count == 0 (code blocks are exempt)

## Files to create/modify

- **Create**: `assets/fbk-scripts/tests/test_gates_spec_injection.py`

## Test requirements

| Level | Behavior | Expected assertion |
|-------|----------|--------------------|
| Unit | control character detected | warning count >= 1 |
| Unit | zero-width character detected | warning count >= 1 |
| Unit | HTML comment with instruction phrase detected | warning count >= 1 |
| Unit | embedded instruction pattern detected | warning count >= 1 |
| Unit | clean spec produces zero warnings | warning count == 0 |
| Unit | instruction text inside code block exempt | warning count == 0 |

## Acceptance criteria

- AC-01: validates injection detection is correctly converted
- AC-08: gate produces correct warning counts for known inputs

## Model

Haiku

## Wave

1
