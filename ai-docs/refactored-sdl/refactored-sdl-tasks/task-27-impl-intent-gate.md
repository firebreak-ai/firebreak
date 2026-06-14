---
id: task-27
type: implementation
wave: 2
covers: [AC-01, AC-02, AC-13, AC-24]
files_to_create:
  - assets/fbk-scripts/fbk/gates/intent.py
  - assets/fbk-docs/fbk-sdl-workflow/intent-guide.md
test_tasks: [task-08]
dependencies: [task-16]
completion_gate: "the referenced test tasks pass"
---

## 1. Objective

Produces the intent gate module (`assets/fbk-scripts/fbk/gates/intent.py`) that validates a PRD + behavior inventory + a present-and-well-formed grilling log + fresh-eyes report, runs the shared injection scan, and guards its path argument; and the routed `intent-guide.md` phase guide.

## 2. Context

The intent gate (subcommand `intent-gate`, registered by task-22) is the front-of-pipeline phase gate. It follows the established gate shape (`fbk/gates/*.py`): a pure check function returning a result dict, an argparse `main()`, JSON to stdout, exit 0/2, path-arg validated before opening, reads with `errors="replace"`.

Pinned pure-function signature (copy verbatim — the paired test imports it and falls back to subprocess for path-guard tests):

```python
def validate_intent(feature_dir: str) -> dict
```

JSON result shape: `{"gate": "intent", "result": "pass"|"fail", "failures": [...], "injection_warnings": N}`.

Checks the gate performs (read the task-08 test for the exact fixtures and failure-message expectations):

**Mechanical:**
1. PRD (`<feature_dir>/prd.md`) present with all 10 required sections as `## ` headings: Vision, Problem statement, Goals and non-goals, Use cases, Functional requirements, Non-functional requirements, Edge cases and failure modes, Dependencies, Success metrics, Open questions. Each missing section is a failure naming that section. Use the same case-insensitive heading-prefix matching style as `spec.py` (`heading_line`-style) so a `## Vision` heading matches "Vision".
2. Behavior inventory (`<feature_dir>/behavior-inventory.yaml`) present, with bidirectional PRD↔inventory reference consistency: every behavior ID (pattern `B-\d+`) listed in the inventory must be referenced somewhere in the PRD body, and every behavior ID referenced in the PRD must appear in the inventory. A behavior in the inventory not referenced in the PRD → failure; a behavior referenced in the PRD but absent from the inventory → failure.
3. Grilling log (`<feature_dir>/grilling-log-intent.md`) present AND well-formed. Absent → failure mentioning "grilling". Present but malformed → failure: the gate checks the log contains a well-formed decision block — a `### ` decision-slug heading together with a `Confirmed:` reflect-back line. A log with neither a `### ` decision block nor a `- Confirmed:` line is malformed and fails the gate (AC-13). This matches task-08's seam case: a malformed grilling log fails while a well-formed one passes.

**Semantic anchor:**
4. Fresh-eyes report (`<feature_dir>/fresh-eyes-intent.md`) present with no open critical observation: the `## Critical` section must be empty (no bullet/observation lines under it) or absent. A non-empty `## Critical` section → failure.

**Injection scan:**
5. Run `detect_injections` (imported from `fbk.injection`, created by task-16) on the PRD, inventory, and grilling log text; sum the counts into `injection_warnings` in the result. Injection detection is non-blocking — a positive count does not by itself fail the gate (the test injects "ignore previous instructions" into the PRD and asserts `injection_warnings >= 1`, not that the gate fails).

**Path guard (AC-24):**
6. In `main()`, validate the feature-dir path with `is_dir()` before opening; `sys.exit(2)` if missing.
7. Read all files with `errors="replace"` so a binary/garbage artifact degrades to a structural failure (the missing-section / parse path), not a traceback. The binary-PRD test asserts the gate returns valid JSON or exits 2, never an unhandled exception.

The fresh-eyes section bar (no open critical after dedup) is shared with the design gate — the phase skill's dedup step reduces the report before the gate's check; the gate only checks the `## Critical` section is empty.

Routed guide: `assets/fbk-docs/fbk-sdl-workflow/intent-guide.md` is the phase guide the `fbk-intent` skill routes to (the skill itself is out of this slice's scope, but the guide is a routed leaf this slice produces). Mirror the shape of `feature-spec-guide.md`: describe the intent phase (open an interview, draw out what the work is and why, write the PRD + behavior inventory in plain language; for an established project read the architecture/intent overview first and ask only about the delta), the required PRD sections, the artifacts produced, and the gate. Use installed path forms, not `assets/...` (AC-22).

## 3. Instructions

1. Read `assets/fbk-scripts/fbk/gates/spec.py` for the gate shape (heading helpers, `main()` argparse + path guard + `errors="replace"`, JSON-to-stdout, exit 0/2) and the task-08 test for exact fixtures and failure-message substrings.

2. Create `assets/fbk-scripts/fbk/gates/intent.py`. Add `from fbk.injection import detect_injections`. Implement helper(s) for heading detection (reuse the `## ` prefix, case-insensitive approach) and behavior-ID extraction (`re.findall(r"B-\d+", text)`).

3. Implement `def validate_intent(feature_dir: str) -> dict`:
   - Resolve the four artifact paths under `feature_dir`.
   - Run the 10-section PRD check; the PRD↔inventory bidirectional check; the grilling-log presence-and-well-formedness check; the fresh-eyes no-open-critical check. Accumulate failure strings (each naming the missing section / mismatch / missing-or-malformed artifact).
   - Grilling-log well-formedness: when the log is present, verify it contains a well-formed decision block — a `### ` decision-slug heading AND a `Confirmed:` reflect-back line. If both are absent, add a failure naming the grilling log as malformed / missing its decision block or `Confirmed:` line (matching task-08's `test_malformed_grilling_log_fails`). A well-formed log (the one task-08's `make_feature_dir` writes) passes.
   - Read each text file with `errors="replace"`; if PRD/inventory/grilling-log is missing, that is a failure (not a crash).
   - Run `detect_injections` on the PRD, inventory, and grilling-log text; sum to `injection_warnings`.
   - Return `{"gate": "intent", "result": "pass" if not failures else "fail", "failures": failures, "injection_warnings": injection_warnings}`.

4. Implement `main()` with argparse (positional `feature_dir`): if `not Path(feature_dir).is_dir()` → print error to stderr and `sys.exit(2)`. Call `validate_intent`; print the JSON result to stdout; `sys.exit(0)` on pass, `sys.exit(2)` on fail. Add the `if __name__ == "__main__": main()` guard. Ensure a binary artifact path degrades to a structural failure (covered by `errors="replace"` reads) rather than raising.

5. Create `assets/fbk-docs/fbk-sdl-workflow/intent-guide.md` mirroring `feature-spec-guide.md` shape: the intent phase's purpose, the 10 required PRD sections, the behavior inventory + grilling log + fresh-eyes artifacts, the gate (`intent-gate`), and the read-the-overview-first-for-established-projects behavior. Use installed path forms. Completion: `[ -s assets/fbk-docs/fbk-sdl-workflow/intent-guide.md ]` and `grep -c '\bassets/' assets/fbk-docs/fbk-sdl-workflow/intent-guide.md` returns 0.

6. Run the paired test: from `assets/fbk-scripts`, `python3 -m pytest tests/test_gates_intent.py -q`. All classes must pass — full pass, the 10 missing-section cases, the bidirectional consistency cases, missing AND malformed grilling log, well-formed grilling log passes, open-critical fresh-eyes, injection warning count, and the path-guard subprocess tests (missing-dir exit 2, binary degrades gracefully).

## 4. Files to create/modify

- `assets/fbk-scripts/fbk/gates/intent.py` (create)
- `assets/fbk-docs/fbk-sdl-workflow/intent-guide.md` (create)

File-scope justification: two files, one phase (gate + its routed guide). The guide is the leaf the phase skill routes to and pairs naturally with the gate it documents; both are produced in the `intent-gate` slice.

## 5. Test requirements

This task makes `assets/fbk-scripts/tests/test_gates_intent.py` (task-08) pass. The subprocess path-guard tests require the gate CLI to exist and be registered (registration is task-22) — run them via `python3 -m fbk intent-gate <args>`. No new tests are written here. Do not edit the test file.

## 6. Acceptance criteria

- AC-01: the gate exists and passes a well-formed artifact set.
- AC-02: fails on any missing PRD section, on PRD↔inventory inconsistency, on a missing grilling log, on an open-critical fresh-eyes; emits an `injection_warnings` count via the shared scan.
- AC-13: fails when the grilling log exists but is malformed (lacks a well-formed decision block with a `Confirmed:` reflect-back line), while a well-formed log passes.
- AC-24: validates the path arg (exit 2 on missing) and reads with `errors="replace"` so binary input degrades to a structural failure.
- Primary criterion: the task-08 tests pass.

## 7. Model

Sonnet

## 8. Wave

Wave 2
