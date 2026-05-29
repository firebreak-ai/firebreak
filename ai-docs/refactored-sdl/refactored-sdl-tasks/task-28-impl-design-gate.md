---
id: task-28
type: implementation
wave: 2
covers: [AC-03, AC-24]
files_to_create:
  - assets/fbk-scripts/fbk/gates/design.py
  - assets/fbk-docs/fbk-sdl-workflow/design-guide.md
test_tasks: [task-09]
dependencies: [task-16]
completion_gate: "the referenced test tasks pass"
---

## 1. Objective

Produces the design gate module (`assets/fbk-scripts/fbk/gates/design.py`) that enforces a bidirectional manifest↔directory check, a decomposition rationale, a non-zero "Decisions recorded" count, a clean fresh-eyes report, and the injection scan with a path guard; and the routed `design-guide.md` phase guide.

## 2. Context

The design gate (subcommand `design-gate`, registered by task-22) gates the design phase. Same gate shape as the other gates (pure check function, argparse `main()`, JSON to stdout, exit 0/2, path-arg validated, `errors="replace"` reads).

Pinned pure-function signature (copy verbatim — the paired test imports it with an ImportError guard):

```python
def validate_design(feature_dir: str) -> dict
```

JSON result shape: `{"gate": "design", "result": "pass"|"fail", "failures": [...], "injection_warnings": N}`.

Checks (read the task-09 test for exact fixtures and failure substrings):

1. **Manifest present**: `<feature_dir>/design-manifest.md` exists.
2. **Bidirectional check, both directions, reporting both**:
   - Forward (manifest→file): every page the manifest lists (lines matching `- design/<slug>.md`) must resolve to a file at `<feature_dir>/design/<slug>.md`. A listed-but-missing page → failure naming the page.
   - Backward (file→manifest): every `.md` file under `<feature_dir>/design/` must appear in the manifest. An unlisted page → failure naming the file.
   - The combined case (both a missing listed page AND an unlisted file present) must report BOTH failures — do not short-circuit on the first. The test asserts `len(result["failures"]) >= 2` with one mentioning the missing file and one the unlisted file.
3. **Decomposition rationale present**: the manifest (or a design page) contains a `Decomposition rationale:` line/section. Absent → failure.
4. **"Decisions recorded" count non-zero**: the manifest contains a line `Decisions recorded: <int>` with a non-zero integer. Zero → failure; absent → failure.
5. **Injection scan**: run `detect_injections` (from `fbk.injection`, task-16) on the design pages + manifest text; sum into `injection_warnings`. Non-blocking (a positive count alone does not fail the gate).
6. **Semantic anchor**: `<feature_dir>/fresh-eyes-design.md` present with no open critical (the `## Critical` section empty or absent). Non-empty `## Critical` → failure.
7. **Path guard (AC-24)**: `main()` validates the feature-dir path with `is_dir()` → `sys.exit(2)` if missing; all reads use `errors="replace"` so a binary manifest degrades to a structural failure, not a traceback.

Routed guide: `assets/fbk-docs/fbk-sdl-workflow/design-guide.md` is the phase guide the `fbk-design` skill routes to (the skill is out of scope; the guide is the routed leaf this slice produces). Mirror `feature-spec-guide.md` shape: the design phase (propose a module shape, contracts, decomposition rationale; surface each real choice one at a time with a recommendation and tradeoff; write design pages + a manifest into the feature directory; append enduring decisions to the durable decisions log), the manifest format (the `- design/<slug>.md` listing, the `Decomposition rationale:` line, the `Decisions recorded: N` line), the fresh-eyes anchor, and the gate. Use installed path forms (AC-22).

## 3. Instructions

1. Read `assets/fbk-scripts/fbk/gates/spec.py` (gate shape) and the task-09 test (fixtures, `make_design_dir`, failure substrings).

2. Create `assets/fbk-scripts/fbk/gates/design.py`. Add `from fbk.injection import detect_injections`. Implement helpers: parse the manifest for listed pages (`re.findall(r"design/([\w-]+\.md)", manifest_text)` or a line-by-line `- design/...` parse), enumerate `*.md` under `<feature_dir>/design/`, extract the `Decisions recorded:` integer, detect `Decomposition rationale:`, and check the `## Critical` section emptiness in the fresh-eyes report.

3. Implement `def validate_design(feature_dir: str) -> dict`:
   - Manifest present check.
   - Forward and backward drift checks, accumulating ALL failures (do not return early) so the both-directions case reports both.
   - Decomposition-rationale present check.
   - Decisions-recorded non-zero check (absent or zero both fail).
   - Fresh-eyes no-open-critical check.
   - Read every text file with `errors="replace"`. Run `detect_injections` on the manifest text and each design page; sum to `injection_warnings`.
   - Return `{"gate": "design", "result": "pass" if not failures else "fail", "failures": failures, "injection_warnings": injection_warnings}`.

4. Implement `main()` with argparse (positional `feature_dir`): `is_dir()` guard → `sys.exit(2)`; call `validate_design`; print JSON; exit 0/2. Add the `__main__` guard. Ensure binary manifest degrades via `errors="replace"`.

5. Create `assets/fbk-docs/fbk-sdl-workflow/design-guide.md` mirroring `feature-spec-guide.md` shape with the design phase content, the manifest format (page listing + decomposition rationale + decisions-recorded count), the decisions-log append behavior, the fresh-eyes anchor, and the gate. Use installed path forms. Completion: `[ -s assets/fbk-docs/fbk-sdl-workflow/design-guide.md ]` and `grep -c '\bassets/' assets/fbk-docs/fbk-sdl-workflow/design-guide.md` returns 0.

6. Run the paired test: from `assets/fbk-scripts`, `python3 -m pytest tests/test_gates_design.py -q`. All classes must pass — full pass, manifest→dir drift, dir→manifest drift, both-directions-reports-both, decomposition rationale, decisions-recorded (zero/absent/nonzero), open-critical fresh-eyes, injection scan, and path-guard subprocess tests.

## 4. Files to create/modify

- `assets/fbk-scripts/fbk/gates/design.py` (create)
- `assets/fbk-docs/fbk-sdl-workflow/design-guide.md` (create)

File-scope justification: two files, one phase (gate + its routed guide), produced together in the `design-gate` slice.

## 5. Test requirements

This task makes `assets/fbk-scripts/tests/test_gates_design.py` (task-09) pass. The subprocess path-guard tests run via `python3 -m fbk design-gate <args>` (registration is task-22). No new tests are written here. Do not edit the test file.

## 6. Acceptance criteria

- AC-03: enforces the bidirectional manifest↔directory check (failing on drift in either direction and reporting both when both drift), requires a decomposition rationale, requires a non-zero "Decisions recorded" count, requires a clean fresh-eyes report, runs the injection scan.
- AC-24: validates the path arg (exit 2 on missing) and reads with `errors="replace"`.
- Primary criterion: the task-09 tests pass.

## 7. Model

Sonnet

## 8. Wave

Wave 2
