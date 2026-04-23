---
id: task-44
type: implementation
wave: 1
covers: [AC-01, AC-08]
files_to_create:
  - assets/fbk-scripts/fbk/gates/review.py
test_tasks: [task-03]
completion_gate: "task-03 tests pass"
---

## Objective

Convert `assets/hooks/fbk-sdl-workflow/review-gate.sh` to `assets/fbk-scripts/fbk/gates/review.py`, reimplementing all bash logic in Python.

## Context

`review-gate.sh` (97 lines, pure bash) validates review documents with 4 checks: (1) perspective coverage — each comma-separated perspective name appears in the review text, (2) severity tags — at least one `blocking|important|informational` globally and per perspective section, (3) threat model determination — `## Threat Model` section with yes/no/skip decision and >= 10 words rationale, (4) testing strategy — section has all 3 categories (new tests, existing tests, test infrastructure). Optional threat model document validation (sections 5-6) when a third argument is provided.

The module must expose `validate_review(review_text, perspectives, threat_model_text=None)` returning a dict `{"result": "pass"|"fail", "failures": [...], "perspectives": [...], "threat_model": bool}`. The `main()` function accepts args: review path, perspectives string, optional threat model path.

## Instructions

1. Create `assets/fbk-scripts/fbk/gates/review.py`
2. Implement `section_of(heading_pattern, text)` — extract section content between heading matching pattern and next `## ` heading, using `re` instead of awk
3. Implement `validate_review(review_text, perspectives, threat_model_text=None)` with these checks:
   - Perspective coverage: for each perspective in comma-separated list, case-insensitive search in review text. Failure: `"Missing perspective in review: {p}"`
   - Severity tags: grep for `blocking|important|informational` globally and per perspective section. Failure: `"No severity tags (blocking/important/informational) found in review"` or `"No severity tag under perspective section: {p}"`
   - Threat model: check for `## Threat Model` heading, check for yes/no/skip decision word, check section has >= 10 words. Failures: `"Missing ## Threat Model ... section"`, `"Threat model determination missing decision (yes/no/skip)"`, `"Threat model determination section missing rationale"`
   - Testing strategy: check for `## Test` heading, check for 3 categories. Failures: `"Missing testing strategy section"`, `"Testing: missing 'new tests needed'"`, etc.
   - If threat_model_text provided: validate Assets, Threat Actors, Trust Boundaries, Threats sections exist and are non-empty
4. Return `{"result": "pass", "failures": [], "perspectives": [...], "threat_model": bool}` on pass, `{"result": "fail", "failures": [...]}` on fail
5. Implement `main()` with argparse: review path (required), perspectives (required), threat model path (optional). On fail: print `"FAIL: {f}"` lines to stderr, exit 2. On pass: print JSON to stdout, exit 0

## Files to create/modify

- **Create**: `assets/fbk-scripts/fbk/gates/review.py`

## Test requirements

- task-03: missing perspective detected, missing severity tags detected, missing threat model section detected, threat model without rationale detected, valid review passes

## Acceptance criteria

- AC-01: review-gate.sh converted to Python module
- AC-08: gate produces correct pass/fail for known inputs

## Model

Sonnet

## Wave

1
